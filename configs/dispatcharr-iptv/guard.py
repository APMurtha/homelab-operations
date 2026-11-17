#!/usr/bin/env python3
"""Trusted one-shot guard lifecycle. Installation requires a matched pin transition.
No daemon; never restores an old authorization after a failed transaction.
"""
import argparse
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from security import TABLE, load_policy, read_peer, render_rules

ROOT = Path('/docker/dispatcharr-iptv')
PRIVATE = Path('/run/dispatcharr-guard')
PUBLIC = Path('/run/dispatcharr-guard-status')
BOOT = Path('/proc/sys/kernel/random/boot_id')
VPN_ID = 'sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209'
VPN_IMAGE = 'qmcgaw/gluetun@' + VPN_ID
G_FIELDS = {'schema','boot_id','generation','policy_sha256'}
N_FIELDS = G_FIELDS | {'netns_dev','netns_ino'}
TRANSITIONAL = {'applying','publishing','granting'}


def command(args):
    p = subprocess.run(args,capture_output=True,text=True,timeout=30)
    if p.returncode: raise ValueError('trusted_read_failed')
    return p.stdout


def require_managed(stack_only=False):
    if os.geteuid()!=0: raise ValueError('root_required')
    allowed={'/system.slice/dispatcharr-stack.service'}
    if not stack_only: allowed.add('/system.slice/dispatcharr-egress-guard.service')
    rows=Path('/proc/self/cgroup').read_text().splitlines()
    if not any(row.startswith('0::') and row[3:] in allowed for row in rows):
        raise ValueError('managed_unit_required')


def netns_identity(pid):
    st=Path('/proc/'+str(pid)+'/ns/net').stat()
    return st.st_dev,st.st_ino


def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def checked_json(path,mode=0o600,limit=16384):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        st=os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=mode or st.st_nlink!=1:
            raise ValueError('unsafe_trusted_file')
        data=f.read(limit+1)
    if len(data)>limit: raise ValueError('trusted_file_limit')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result: raise ValueError('duplicate_JSON_field')
            result[k]=v
        return result
    return json.loads(data,object_pairs_hook=pairs)


def semantic_table(policy,live=None):
    # Pure existing exact-table contract; no candidate import or policy change.
    path=ROOT/'minimal-phase6b3d/contracts.py'
    spec=importlib.util.spec_from_file_location('accepted_guard_contract',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.verify_table(json.loads(command(['nft','-j','list','table','inet',TABLE])) if live is None else live,policy)


class Publisher:
    def __init__(self,private=PRIVATE,public=PUBLIC,boot_file=BOOT):
        self.private,self.public,self.boot_file=Path(private),Path(public),Path(boot_file)

    @property
    def boot(self):
        value=self.boot_file.read_text().strip()
        if not re.fullmatch('[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',value):raise ValueError('boot_identity_invalid')
        return value

    def directories(self,create=False):
        if os.geteuid()!=0: raise ValueError('root_required')
        for path,mode in [(self.private,0o700),(self.public,0o755)]:
            if create:
                try:os.mkdir(path,mode);os.chmod(path,mode)
                except FileExistsError:pass
            st=path.lstat()
            if not stat.S_ISDIR(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=mode:
                raise ValueError('unsafe_guard_directory')
        if self.private.stat().st_dev!=self.public.stat().st_dev:raise ValueError('guard_filesystem_mismatch')
        if any(path.name not in {'guard.json','grant.json'} for path in self.public.iterdir()):raise ValueError('unexpected_public_status_file')

    def atomic(self,target,data,mode=0o600):
        fd,name=tempfile.mkstemp(prefix='.transaction-',dir=self.private)
        try:
            with os.fdopen(fd,'wb') as f:
                os.fchown(f.fileno(),0,0);os.fchmod(f.fileno(),mode);f.write(data);f.flush();os.fsync(f.fileno())
            os.replace(name,target)
            for parent in {self.private,Path(target).parent}:
                d=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:os.fsync(d)
                finally:os.close(d)
        finally:Path(name).unlink(missing_ok=True)

    def write(self,target,value,mode=0o600):
        self.atomic(target,(json.dumps(value,sort_keys=True,allow_nan=False)+'\n').encode(),mode)

    def anchor(self,create=False):
        st=self.public.stat();value={'schema':1,'boot_id':self.boot,'dev':st.st_dev,'ino':st.st_ino}
        path=self.private/'anchor.json'
        if path.exists() or path.is_symlink():
            if checked_json(path)!=value:raise ValueError('unexplained_public_anchor')
        elif create and not any(self.public.iterdir()) and not any((self.private/name).exists() or (self.private/name).is_symlink() for name in ['transaction.json','owner-intent.json']):self.write(path,value)
        else:raise ValueError('uninitialized_public_anchor')

    @contextlib.contextmanager
    def locked(self):
        self.directories(create=True)
        fd=os.open(self.private/'writer.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:
            st=os.fstat(fd)
            if st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o600 or st.st_nlink!=1 or not stat.S_ISREG(st.st_mode):
                raise ValueError('unsafe_writer_lock')
            fcntl.flock(fd,fcntl.LOCK_EX)
            self.anchor(create=True)
            yield
        finally:os.close(fd)

    def transaction(self):
        path=self.private/'transaction.json'
        value=checked_json(path) if path.exists() or path.is_symlink() else {'phase':'revoked','blocked':False}
        if not isinstance(value,dict) or value.get('phase') not in {'revoked','applying','publishing','applied','granting','granted'} or type(value.get('blocked')) is not bool:
            raise ValueError('private_transaction_invalid')
        return value

    def withdraw(self,legacy=True):
        errors=[];valid_old=True
        try:old=self.transaction()
        except (OSError,ValueError):
            valid_old=False;old={'phase':'unknown','blocked':True};errors.append(ValueError('private_transaction_unreadable'))
        paths=[self.public/'guard.json',self.public/'grant.json',self.private/'owner-intent.json']
        if legacy:paths.append(self.private/'ready')
        for path in paths:
            try:path.unlink(missing_ok=True)
            except OSError as exc:errors.append(exc)
        blocked=old.get('blocked',False) or old.get('phase') in TRANSITIONAL
        try:
            if valid_old:self.write(self.private/'transaction.json',{'phase':'revoked','blocked':blocked,'prior_phase':old.get('prior_phase',old.get('phase')) if old.get('blocked') else old.get('phase'),'prior_generation':old.get('prior_generation',old.get('generation')) if old.get('blocked') else old.get('generation')})
        except OSError as exc:errors.append(exc)
        for directory in [self.public,self.private]:
            try:
                fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:os.fsync(fd)
                finally:os.close(fd)
            except OSError as exc:errors.append(exc)
        if errors:raise ValueError('revocation_failed')

    def revoke(self,legacy=True):
        with self.locked():
            # Withdraw first; an unmanaged attempted mutation cannot retain old authorization.
            self.withdraw(legacy);require_managed()

    def apply(self,policy_path,wireguard_path):
        with self.locked():
            self.withdraw(True)
            try:
                require_managed()
                if self.transaction().get('blocked'):raise ValueError('incomplete_guard_transaction_requires_review')
                self.write(self.private/'transaction.json',{'phase':'applying','blocked':False})
                # Validation intentionally follows withdrawal.
                for name in [policy_path,wireguard_path]:
                    st=Path(name).lstat()
                    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o600:
                        raise ValueError('unsafe_private_input')
                policy,digest=load_policy(policy_path)
                if read_peer(wireguard_path)!=(policy['wg_endpoint_ipv4'],policy['wg_endpoint_port']):raise ValueError('wireguard_peer_mismatch')
                exists=subprocess.run(['nft','list','table','inet',TABLE],capture_output=True,timeout=30).returncode==0
                rules=('delete table inet '+TABLE+'\n' if exists else '')+render_rules(policy)
                for args in [['nft','--check','--file','-'],['nft','--file','-']]:
                    subprocess.run(args,input=rules,text=True,check=True,capture_output=True,timeout=30)
                semantic_table(policy)
                generation=__import__('secrets').token_hex(32)
                record={'schema':1,'boot_id':self.boot,'generation':generation,'policy_sha256':digest}
                self.write(self.private/'transaction.json',dict(record,phase='publishing',blocked=False))
                self.atomic(self.private/'ready',(digest+'\n').encode(),0o644)
                self.write(self.public/'guard.json',record,0o644)
                self.write(self.private/'transaction.json',dict(record,phase='applied',blocked=False))
                return record
            except BaseException:
                self.withdraw(True)
                raise

    def coherence(self,policy_path,live=None):
        self.directories();self.anchor()
        policy,digest=load_policy(policy_path);semantic_table(policy,live)
        record=checked_json(self.public/'guard.json',0o644,2048)
        txn=self.transaction()
        if set(record)!=G_FIELDS or type(record.get('schema')) is not int or record.get('schema')!=1 or record.get('boot_id')!=self.boot or record.get('policy_sha256')!=digest:
            raise ValueError('guard_record_mismatch')
        if not re.fullmatch('[a-f0-9]{64}',record.get('generation','')):raise ValueError('guard_generation_invalid')
        if txn.get('phase') not in {'applied','granted'} or txn.get('blocked') or any(txn.get(k)!=v for k,v in record.items()):raise ValueError('guard_transaction_incomplete')
        fd=os.open(self.private/'ready',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd) as f:
            st=os.fstat(f.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o644 or st.st_nlink!=1 or f.read(66)!=digest+'\n':raise ValueError('legacy_ready_mismatch')
        return record

    def remember_owner(self,owner,network,policy_path):
        with self.locked():
            require_managed(True);record=self.coherence(policy_path)
            if owner['Image']!=VPN_ID or owner['Config'].get('Image')!=VPN_IMAGE or owner['State']['Running']:
                raise ValueError('stopped_pinned_owner_required')
            if not re.fullmatch('[a-f0-9]{64}',owner['Id']):raise ValueError('owner_identity_invalid')
            value={'guard':record,'owner':owner['Id'],'config':sha(owner['Config']),'host_config':sha(owner['HostConfig']),'network':network['Id']}
            self.write(self.private/'owner-intent.json',value)

    def grant(self,policy_path):
        with self.locked():
            try:
                require_managed(True);record=self.coherence(policy_path)
                intent=checked_json(self.private/'owner-intent.json')
                if intent['guard']!=record:raise ValueError('owner_intent_generation_mismatch')
                owner=json.loads(command(['docker','inspect','rivendell-iptv-vpn']))[0]
                network=json.loads(command(['docker','network','inspect','rivendell-iptv-egress']))[0]
                if (owner['Id']!=intent['owner'] or owner['Image']!=VPN_ID or owner['Config'].get('Image')!=VPN_IMAGE or
                    sha(owner['Config'])!=intent['config'] or sha(owner['HostConfig'])!=intent['host_config'] or
                    network['Id']!=intent['network'] or network.get('Name')!='rivendell-iptv-egress' or network.get('Driver')!='bridge' or network.get('EnableIPv6') is not False):
                    raise ValueError('VPN_owner_identity_changed')
                if not owner['State']['Running'] or owner['State'].get('Health',{}).get('Status')!='healthy' or type(owner['State'].get('Pid')) is not int or owner['State']['Pid']<=0:
                    raise ValueError('VPN_owner_not_healthy')
                attached=owner['NetworkSettings']['Networks']
                if set(attached)!={'rivendell-iptv-egress'} or attached['rivendell-iptv-egress'].get('IPAddress')!='172.16.70.2' or attached['rivendell-iptv-egress'].get('NetworkID')!=network['Id'] or set(network.get('Containers',{}))!={owner['Id']}:
                    raise ValueError('VPN_network_changed')
                run=lambda args:command(['docker','exec','rivendell-iptv-vpn',*args])
                if not any('default' in line and 'tun0' in line for line in run(['ip','route','show','table','all']).splitlines()):raise ValueError('VPN_route_missing')
                output=run(['iptables','-S','OUTPUT'])
                if '-P OUTPUT DROP' not in output or '127.0.0.11/32' not in output or 'REJECT' not in output:raise ValueError('VPN_killswitch_changed')
                for flag in ['all','default']:
                    if run(['cat','/proc/sys/net/ipv6/conf/'+flag+'/disable_ipv6']).strip()!='1':raise ValueError('VPN_IPv6_enabled')
                if [x.split()[1] for x in run(['cat','/etc/resolv.conf']).splitlines() if x.startswith('nameserver ')]!=['127.0.0.1']:raise ValueError('VPN_DNS_changed')
                run(['/gluetun-entrypoint','healthcheck'])
                ns=netns_identity(owner['State']['Pid']);host=netns_identity(1)
                if ns==host:raise ValueError('host_namespace_forbidden')
                # Recheck guard and owner after security observations before committing.
                if self.coherence(policy_path)!=record:raise ValueError('guard_changed_during_owner_check')
                again=json.loads(command(['docker','inspect','rivendell-iptv-vpn']))[0]
                if any(again[k]!=owner[k] for k in ['Id','Image','Config','HostConfig','NetworkSettings']) or again['State']['Pid']!=owner['State']['Pid'] or not again['State']['Running'] or again['State'].get('Health',{}).get('Status')!='healthy':raise ValueError('owner_changed_during_grant')
                if netns_identity(again['State']['Pid'])!=ns:raise ValueError('owner_namespace_changed_during_grant')
                value=dict(record,netns_dev=ns[0],netns_ino=ns[1])
                self.write(self.private/'transaction.json',dict(record,phase='granting',blocked=False))
                self.write(self.public/'grant.json',value,0o644)
                self.write(self.private/'transaction.json',dict(record,phase='granted',blocked=False))
                return value
            except BaseException:
                self.withdraw(False)
                raise


def main():
    # Early withdrawal also covers malformed apply arguments, before argparse.
    if len(sys.argv)>1 and sys.argv[1]=='apply':Publisher().revoke(True)
    p=argparse.ArgumentParser();p.add_argument('action',choices=['check','apply','revoke','revoke-public','assert-revoked','grant'])
    p.add_argument('--policy',default=str(ROOT/'private/egress-policy.json'))
    p.add_argument('--wireguard',default=str(ROOT/'private/wg0.conf'));a=p.parse_args()
    publisher=Publisher()
    if a.action=='check':
        policy,_=load_policy(a.policy)
        exists=subprocess.run(['nft','list','table','inet',TABLE],capture_output=True,timeout=30).returncode==0
        rules=('delete table inet '+TABLE+'\n' if exists else '')+render_rules(policy)
        subprocess.run(['nft','--check','--file','-'],input=rules,text=True,check=True,capture_output=True,timeout=30)
    elif a.action=='apply':publisher.apply(a.policy,a.wireguard)
    elif a.action in {'revoke','revoke-public'}:publisher.revoke(a.action=='revoke')
    elif a.action=='grant':publisher.grant(a.policy)
    else:
        require_managed()
        if any((PUBLIC/name).exists() or (PUBLIC/name).is_symlink() for name in ['guard.json','grant.json']):raise ValueError('revocation_incomplete')
    print('Scoped guard operation completed; private values withheld.')

if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Guard operation refused; inspect private transaction and unit state. No automatic retry.')
