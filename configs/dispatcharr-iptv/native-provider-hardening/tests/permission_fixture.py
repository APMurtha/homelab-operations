"""Permission-faithful offline tests: mapped root/UID1000, private tmpfs only."""
import base64
import copy
import errno
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
import publish_policy as writer
sys.path.insert(0,str(BASE.parent))
import provider_control
from runtime import provider_policy as policy,provider_security as security,provider_transport as transport
spec=importlib.util.spec_from_file_location('packaging_recipe',BASE.parent/'hardened-image-integration/build_once.py')
recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)
spec=importlib.util.spec_from_file_location('source_prepare',BASE/'prepare.py')
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)
spec=importlib.util.spec_from_file_location('context_prepare',BASE.parent/'hardened-image-integration/prepare_context.py')
context_prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(context_prepare)


def uid1000(fn):
    r,w=os.pipe();pid=os.fork()
    if pid==0:
        os.close(r)
        try:
            os.setgroups([]);os.setgid(1000);os.setuid(1000)
            assert os.geteuid()==os.getegid()==1000 and os.getgroups()==[]
            assert 'CapEff:\t0000000000000000' in Path('/proc/self/status').read_text()
            result={'ok':True,'value':fn()}
        except BaseException as e:result={'ok':False,'error':type(e).__name__,'errno':getattr(e,'errno',None)}
        os.write(w,json.dumps(result).encode());os.close(w);os._exit(0)
    os.close(w);data=os.read(r,16384);os.close(r);_,code=os.waitpid(pid,0)
    assert code==0
    return json.loads(data)


class Permissions(unittest.TestCase):
    def setUp(self):
        if os.environ.get('PROVIDER_PERMISSION_FIXTURE')!='1' or os.geteuid()!=0:raise RuntimeError('isolated_namespace_runner_required')
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        subprocess.run(['mount','-t','tmpfs','-o','size=16m,mode=0755,nosuid,nodev','tmpfs',str(self.root)],check=True)
        self.mounts=[];self.addCleanup(self.cleanup)
        self.private=self.root/'private';self.private.mkdir(mode=0o700)
        self.public=self.root/'public';self.guard=self.root/'guard';self.guard.mkdir(mode=0o755)
        self.key='a'*64
        ns=Path('/proc/self/ns/net').stat()
        self.p=json.loads((BASE/'policy.example.json').read_text());self.p.update(provider_key=self.key,netns=[ns.st_dev,ns.st_ino],host_netns=[1,1],boot_id=policy.boot(),expires_epoch=time.time()+1000,review_reference='SYNTHETIC PRIVATE REVIEW TOKEN DO NOT PUBLISH')
        for e in self.p['endpoints']:e['ipv4']=['93.184.216.34']
        self.private_file=self.private/(self.key+'.json');self.save_private()
        self.g={'schema':1,'boot_id':self.p['boot_id'],'generation':'b'*64,'policy_sha256':self.p['policy_review_sha256']}
        self.save_guard()
        self.publisher=writer.Publisher(self.private,self.public,self.guard);self.publisher.initialize();self.publisher.publish(self.key)
    def cleanup(self):
        for p in reversed(self.mounts):subprocess.run(['umount',str(p)],check=True)
        subprocess.run(['umount',str(self.root)],check=True);self.temp.cleanup()
    def save_private(self):self.private_file.write_text(json.dumps(self.p));self.private_file.chmod(0o600)
    def save_guard(self):
        for name,v in [('guard.json',self.g),('grant.json',{**self.g,'netns_dev':self.p['netns'][0],'netns_ino':self.p['netns'][1]})]:
            p=self.guard/name;p.write_text(json.dumps(v));p.chmod(0o644)
    def reader(self):return policy.Reader(self.public,self.guard)
    def load(self):return json.loads((self.public/(self.key+'.json')).read_text())
    def save(self,value):
        p=self.public/(self.key+'.json');p.write_text(json.dumps(value));p.chmod(0o644)
    def allowed(self,fn):
        r=uid1000(fn);self.assertTrue(r['ok'],r);return r['value']
    def denied(self,fn):self.assertFalse(uid1000(fn)['ok'])
    def bind(self,source):
        target=self.root/'mounted';target.mkdir()
        subprocess.run(['mount','--bind',str(source),str(target)],check=True);self.mounts.append(target)
        subprocess.run(['mount','-o','remount,bind,ro,nosuid,nodev,noexec',str(target)],check=True)
        return target

    def test_uid1000_current_public_policy_and_private_denial(self):
        p=self.allowed(lambda:self.reader().read(self.key));self.assertEqual(p['provider_key'],self.key)
        self.denied(lambda:self.private_file.read_bytes())
        self.assertEqual(self.private.stat().st_mode&0o777,0o700)
        self.assertNotIn('SYNTHETIC PRIVATE',json.dumps(self.load()))
        self.assertNotIn('review_reference',self.load()['policy'])
        self.assertNotIn('path',self.load()['policy']['endpoints'][0])
    def test_no_secret_field_is_projected(self):
        self.p['password']='synthetic-secret';self.save_private()
        with self.assertRaises(Exception):self.publisher.publish(self.key)
        self.assertFalse((self.public/(self.key+'.json')).exists())
    def test_unprivileged_writes_and_publisher_refused(self):
        self.denied(lambda:(self.public/(self.key+'.json')).write_text('{}'))
        self.denied(lambda:(self.public/'forged.json').write_text('{}'))
        self.denied(lambda:self.publisher.publish(self.key))
        self.denied(lambda:self.publisher.revoke())
    def test_missing_malformed_and_duplicate_status(self):
        path=self.public/(self.key+'.json')
        for raw in ['{','{}','{"schema":1,"schema":1}','[]','NaN']:
            path.write_text(raw);self.denied(lambda:self.reader().read(self.key))
        path.unlink();self.denied(lambda:self.reader().read(self.key))
    def test_exact_modes_and_owners(self):
        path=self.public/(self.key+'.json')
        for mode in [0o600,0o666,0o444,0o755]:
            path.chmod(mode);self.denied(lambda:self.reader().read(self.key))
        path.chmod(0o644)
        for uid,gid in [(1000,0),(0,1000),(1000,1000)]:
            os.chown(path,uid,gid);self.denied(lambda:self.reader().read(self.key))
        os.chown(path,0,0)
        self.public.chmod(0o777);self.denied(lambda:self.reader().read(self.key))
    def test_link_and_special_file_rejection(self):
        path=self.public/(self.key+'.json');source=self.root/'record';path.rename(source)
        path.symlink_to(source);self.denied(lambda:self.reader().read(self.key));path.unlink()
        os.link(source,path);self.denied(lambda:self.reader().read(self.key));path.unlink()
        os.mkfifo(path,0o644);self.denied(lambda:self.reader().read(self.key))
    def test_stale_boot_expiry_future_and_overlong_lease(self):
        original=self.load()
        mutations=[lambda r:r['policy'].update(expires_epoch=0),lambda r:r['policy'].update(boot_id='00000000-0000-0000-0000-000000000000'),lambda r:r.update(issued_epoch=time.time()+1),lambda r:r['policy'].update(expires_epoch=time.time()+301)]
        for change in mutations:
            r=copy.deepcopy(original);change(r);self.save(r);self.denied(lambda:self.reader().read(self.key))
    def test_wrong_policy_provider_or_namespace(self):
        original=self.load()
        for field,value in [('provider_key','f'*64),('netns',[1,2]),('policy_review_sha256','f'*64),('network_owner','WAN')]:
            r=copy.deepcopy(original);r['policy'][field]=value;self.save(r);self.denied(lambda:self.reader().read(self.key))
    def test_revocation_reopened_through_readonly_directory_bind(self):
        mount=self.bind(self.public);reader=policy.Reader(mount,self.guard)
        self.allowed(lambda:reader.read(self.key));self.publisher.revoke(self.key)
        self.denied(lambda:reader.read(self.key))
    def test_readonly_bind_prevents_even_root_write(self):
        mount=self.bind(self.public)
        with self.assertRaises(OSError) as e:(mount/(self.key+'.json')).write_text('{}')
        self.assertEqual(e.exception.errno,errno.EROFS)
    def test_new_generation_rejects_active_job(self):
        security.AUTHORIZATION=self.reader();r=type('R',(),{'account_type':'XC','server_url':'https://fixture.invalid','username':'u','is_active':True,'custom_properties':{'provider_cli':{'key':self.key,'owner':'dispatcharr-provider/v1/native-v1'}}})()
        with patch.object(security,'resource_key',return_value=self.key),patch.object(security,'GUARD',str(self.guard)):
            with security.job('refresh',r,True):
                before=security.check()['policy']['authorization_generation'];self.publisher.publish(self.key)
                self.assertNotEqual(before,self.load()['generation'])
                with self.assertRaises(security.Denied):security.check()
    def test_revocation_during_active_job(self):
        security.AUTHORIZATION=self.reader()
        r=type('R',(),{'account_type':'XC','is_active':True})()
        with patch.object(security,'resource_key',return_value=self.key),patch.object(security,'GUARD',str(self.guard)):
            with security.job('refresh',r,True):
                self.publisher.revoke(self.key)
                with self.assertRaises(security.Denied):security.check()
    def test_guard_replacement_or_revocation(self):
        self.g['generation']='c'*64;self.save_guard();self.denied(lambda:self.reader().read(self.key))
        self.publisher.publish(self.key);self.allowed(lambda:self.reader().read(self.key))
        (self.guard/'grant.json').unlink();self.denied(lambda:self.reader().read(self.key))
    def test_anchor_replacement_rejected_reader_and_writer(self):
        reader=self.reader();reader.read(self.key)
        old=self.root/'old';self.public.rename(old);shutil.copytree(old,self.public)
        self.denied(lambda:reader.read(self.key))
        # Even a new worker rejects copied records on an unapproved inode.
        self.denied(lambda:self.reader().read(self.key))
        with self.assertRaises(Exception):self.publisher.publish(self.key)
        with self.assertRaises(Exception):self.publisher.initialize()
    def test_stale_directory_bind_is_bounded_not_claimed_instantaneous(self):
        mounted=self.bind(self.public);reader=policy.Reader(mounted,self.guard)
        self.allowed(lambda:reader.read(self.key))
        old=self.root/'old-anchor';self.public.rename(old);self.public.mkdir(mode=0o755)
        # Old directory binds cannot observe a replacement host path. The
        # trusted writer refuses the new anchor; the old lease still expires.
        with self.assertRaises(Exception):self.publisher.publish(self.key)
        self.allowed(lambda:reader.read(self.key))
        path=old/(self.key+'.json');r=json.loads(path.read_text());r['issued_epoch']-=301;r['policy']['expires_epoch']-=301;path.write_text(json.dumps(r))
        self.denied(lambda:reader.read(self.key))
    def test_unknown_existing_anchor_never_adopted(self):
        (self.private/'.status-anchor.json').unlink()
        with self.assertRaises(Exception):self.publisher.initialize()
        with self.assertRaises(Exception):self.publisher.publish(self.key)
    def test_early_validation_failure_withdraws_old_authorization(self):
        self.p['network_owner']='WAN';self.save_private()
        with self.assertRaises(Exception):self.publisher.publish(self.key)
        self.denied(lambda:self.reader().read(self.key))
    def test_guard_validation_failure_withdraws_old_authorization(self):
        (self.guard/'guard.json').unlink()
        with self.assertRaises(Exception):self.publisher.publish(self.key)
        self.assertFalse((self.public/(self.key+'.json')).exists())
    def test_publication_failure_withdraws_and_never_extends_private_expiry(self):
        with patch.object(self.publisher,'write',side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):self.publisher.publish(self.key)
        self.assertFalse((self.public/(self.key+'.json')).exists())
        self.p['expires_epoch']=time.time()+10;self.save_private();self.publisher.publish(self.key)
        self.assertLessEqual(self.load()['policy']['expires_epoch'],self.p['expires_epoch'])
    def test_crash_retained_lease_is_bounded_not_instantly_revoked(self):
        record=self.load();self.assertLessEqual(record['policy']['expires_epoch']-record['issued_epoch'],300)
        # A crashed publisher can leave the current record valid until expiry.
        self.allowed(lambda:self.reader().read(self.key))
        record['issued_epoch']-=301;record['policy']['expires_epoch']-=301;self.save(record)
        self.denied(lambda:self.reader().read(self.key))
    def test_guard_changes_during_publication_remove_record(self):
        real=writer.guard_snapshot;calls=[]
        def changing(*a):
            calls.append(1);return real(*a) if len(calls)==1 else 'f'*64
        with patch.object(writer,'guard_snapshot',side_effect=changing),self.assertRaises(Exception):self.publisher.publish(self.key)
        self.assertFalse((self.public/(self.key+'.json')).exists())
    def test_live_destination_authorization_uses_public_projection_not_private_file(self):
        reader=self.reader()
        with patch.object(transport.MetadataHTTPS,'context_checks'),patch.object(transport.MetadataHTTPS,'vpn_route'),patch.object(transport,'resolve',return_value={'93.184.216.34'}),patch.object(transport,'private_read',side_effect=AssertionError('private read forbidden')):
            client=transport.MetadataHTTPS(None,approval_reader=lambda:reader.read(self.key))
            u,ip=client.authorize('https://approved-provider.example.invalid/player_api.php?password=synthetic')
            self.assertEqual(ip,'93.184.216.34')
            for target in ['https://approved-provider.example.invalid/forbidden','https://other.invalid/player_api.php','http://approved-provider.example.invalid/player_api.php']:
                with self.assertRaises(Exception):client.authorize(target)
            self.publisher.revoke(self.key)
            with self.assertRaises(Exception):client.authorize('https://approved-provider.example.invalid/player_api.php')
    def test_crash_after_withdrawal_cannot_leave_old_record(self):
        pid=os.fork()
        if pid==0:
            self.publisher.write=lambda *a:os._exit(77)
            self.publisher.publish(self.key);os._exit(99)
        _,status=os.waitpid(pid,0);self.assertEqual(os.waitstatus_to_exitcode(status),77)
        self.assertFalse((self.public/(self.key+'.json')).exists())
        # Kernel releases the writer lock on exit; explicit reconciliation may
        # publish a fresh generation, never blindly replay an API mutation.
        self.publisher.publish(self.key);self.allowed(lambda:self.reader().read(self.key))
    def test_crash_after_publication_leaves_only_finite_lease(self):
        pid=os.fork()
        if pid==0:self.publisher.publish(self.key);os._exit(77)
        _,status=os.waitpid(pid,0);self.assertEqual(os.waitstatus_to_exitcode(status),77)
        self.allowed(lambda:self.reader().read(self.key))
        self.assertLessEqual(self.load()['policy']['expires_epoch']-time.time(),300)
    def test_failed_withdrawal_never_enters_publication(self):
        old=self.load()
        with patch.object(self.publisher,'withdraw',side_effect=OSError('synthetic withdrawal failure')),patch.object(self.publisher,'write') as write:
            with self.assertRaises(OSError):self.publisher.publish(self.key)
            write.assert_not_called()
        self.assertEqual(self.load(),old)  # Not instantaneous revocation.
    def test_revoke_all_attempts_other_records_after_failure(self):
        other='c'*64;record=self.load();record['policy']['provider_key']=other
        (self.public/(other+'.json')).write_text(json.dumps(record));(self.public/(other+'.json')).chmod(0o644)
        original=self.publisher.withdraw;attempts=[]
        def fail_one(fd,key):
            attempts.append(key)
            if key==self.key:raise OSError('synthetic')
            return original(fd,key)
        with patch.object(self.publisher,'withdraw',side_effect=fail_one),self.assertRaises(Exception):self.publisher.revoke()
        self.assertEqual(set(attempts),{other,self.key});self.assertFalse((self.public/(other+'.json')).exists())
    def test_lock_and_anchor_metadata_cannot_be_substituted(self):
        path=self.private/'.status-anchor.json';path.chmod(0o644)
        with self.assertRaises(Exception):self.publisher.publish(self.key)
        path.chmod(0o600)
        lock=self.private/'.status-writer.lock';lock.unlink();lock.symlink_to(self.private_file)
        with self.assertRaises(Exception):self.publisher.publish(self.key)
    def test_public_anchor_symlink_and_wrong_owner(self):
        old=self.root/'old';self.public.rename(old);self.public.symlink_to(old,target_is_directory=True)
        self.denied(lambda:self.reader().read(self.key));self.public.unlink();old.rename(self.public)
        os.chown(self.public,1000,1000);self.denied(lambda:self.reader().read(self.key))
    def test_size_limit_and_inconsistent_schema(self):
        path=self.public/(self.key+'.json');original=self.load()
        path.write_bytes(b' '*65537);self.denied(lambda:self.reader().read(self.key))
        for change in [lambda r:r.update(schema=True),lambda r:r.update(generation='bad'),lambda r:r['policy'].update(operations=['discover','discover']),lambda r:r['policy'].update(extra='secret')]:
            value=copy.deepcopy(original);change(value);self.save(value);self.denied(lambda:self.reader().read(self.key))
    def test_baseline_packaging_failure_is_reproduced(self):
        legacy=self.root/'legacy';legacy.mkdir(mode=0o755);old=os.umask(0o077)
        try:
            (legacy/'apps/api').mkdir(parents=True);(legacy/'apps/api/__init__.py').write_text('')
        finally:os.umask(old)
        self.assertEqual((legacy/'apps').stat().st_mode&0o777,0o700)
        self.denied(lambda:(legacy/'apps/api/__init__.py').read_bytes())

    def test_control_preserves_anchor_and_revokes_via_directory_mount(self):
        with patch.object(provider_control,'PRIVATE',self.private),patch.object(provider_control,'PUBLIC',self.public):
            before=self.public.stat().st_ino;mount=self.bind(self.public)
            provider_control.revoke();provider_control.prepare();provider_control.prepare()
            self.assertEqual(self.public.stat().st_ino,before)
            self.denied(lambda:policy.Reader(mount,self.guard).read(self.key))
            self.denied(lambda:self.private_file.read_bytes())
    def test_actual_guard_withdrawal_revokes_provider_assertions_first(self):
        spec=importlib.util.spec_from_file_location('guard_policy_bridge',BASE.parent/'guard.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
        private=self.root/'guard-private';private.mkdir(mode=0o700)
        instance=guard.Publisher(private,self.guard)
        with patch.object(provider_control,'PRIVATE',self.private),patch.object(provider_control,'PUBLIC',self.public):instance.withdraw()
        self.assertFalse((self.public/(self.key+'.json')).exists())
        self.assertFalse((self.guard/'guard.json').exists())
        self.denied(lambda:self.reader().read(self.key))
    def test_completed_change_receipt_cannot_hide_subsequent_policy_drift(self):
        self.staged();self.publisher.replace_policy(self.key)
        value=json.loads(self.private_file.read_text());value['operations']=['epg'];self.private_file.write_text(json.dumps(value))
        with self.assertRaises(Exception):self.publisher.publish(self.key)
        self.assertFalse((self.public/(self.key+'.json')).exists())
    def test_control_prepare_creates_no_authorization(self):
        private=self.root/'new-private';public=self.root/'new-public'
        with patch.object(provider_control,'PRIVATE',private),patch.object(provider_control,'PUBLIC',public):
            provider_control.prepare();provider_control.assert_revoked()
            self.assertFalse(list(public.iterdir()));self.assertEqual(private.stat().st_mode&0o777,0o700)
    def staged(self):
        value=copy.deepcopy(self.p);value['operations']=['discover'];path=self.private/(self.key+'.staged.json');path.write_text(json.dumps(value));path.chmod(0o600);return value
    def test_policy_change_withdraws_without_automatic_publication(self):
        value=self.staged();self.publisher.replace_policy(self.key)
        self.assertEqual(json.loads(self.private_file.read_text()),value)
        prior=self.private/(self.key+'.prior.json')
        self.assertEqual(json.loads(prior.read_text()),self.p);self.denied(lambda:prior.read_bytes())
        self.assertFalse((self.public/(self.key+'.json')).exists())
        self.publisher.publish(self.key);self.allowed(lambda:self.reader().read(self.key))
    def test_unprivileged_policy_change_refused(self):
        self.staged();self.denied(lambda:self.publisher.replace_policy(self.key));self.denied(lambda:self.publisher.reconcile_change(self.key))
    def test_interrupted_policy_change_blocks_publication_until_reconciled(self):
        self.staged();real=self.publisher.write
        def interrupted(fd,name,*args):
            if name==self.key+'.json':raise OSError('synthetic')
            return real(fd,name,*args)
        with patch.object(self.publisher,'write',side_effect=interrupted),self.assertRaises(OSError):self.publisher.replace_policy(self.key)
        with self.assertRaises(Exception):self.publisher.publish(self.key)
        self.publisher.reconcile_change(self.key)
        self.assertFalse((self.public/(self.key+'.json')).exists())
        self.publisher.publish(self.key);self.allowed(lambda:self.reader().read(self.key))
    def test_conflicting_policy_change_is_retained_and_refused(self):
        self.staged();receipt={'schema':1,'state':'pending','old':'d'*64,'new':'e'*64}
        path=self.private/(self.key+'.change.json');path.write_text(json.dumps(receipt));path.chmod(0o600)
        with self.assertRaises(Exception):self.publisher.reconcile_change(self.key)
        self.assertEqual(json.loads(path.read_text()),receipt)
        self.assertFalse((self.public/(self.key+'.json')).exists())

    def test_code_packaging_uid1000_traverse_compile_and_import(self):
        overlay=self.root/'overlay';hashes=prepare.prepare(Path('/tmp/dispatcharr-native-hardening-input'),overlay)
        files={str(Path('app')/name):{'data':base64.b64encode((overlay/name).read_bytes()).decode(),'sha256':sha} for name,sha in hashes.items()}
        context=self.root/'private-transport';old=os.umask(0o077)
        try:recipe.write_context(context,files)
        finally:os.umask(old)
        image=self.root/'image';image.mkdir();shutil.copytree(context/'app',image/'app')
        self.assertEqual(context.stat().st_mode&0o777,0o700)
        self.denied(lambda:(context/'app/core/provider_security.py').read_bytes())
        for p in (image/'app').rglob('*'):
            st=p.stat();self.assertEqual((st.st_uid,st.st_gid),(0,0));self.assertEqual(st.st_mode&0o777,0o755 if p.is_dir() else 0o644)
        def consume():
            for name,sha in hashes.items():
                data=(image/'app'/name).read_bytes()
                assert hashlib.sha256(data).hexdigest()==sha
                compile(data,name,'exec')
            import types
            package=types.ModuleType('uid_fixture_core');package.__path__=[str(image/'app/core')];sys.modules['uid_fixture_core']=package
            for module in ['provider_security','provider_transport','provider_policy','provider_dns','provider_readiness']:importlib.import_module('uid_fixture_core.'+module)
            return len(hashes)
        self.assertEqual(self.allowed(consume),len(hashes))
    def test_prepare_context_under_private_umask(self):
        inspector=context_prepare.HERE/'inspect_image.py';spec=importlib.util.spec_from_file_location('pins',inspector);pins=importlib.util.module_from_spec(spec);spec.loader.exec_module(pins)
        evidence={'base':{'id':pins.IMAGE},'hashes':{**pins.PINS,**pins.READINESS}}
        output=self.root/'context';old=os.umask(0o077)
        try:context_prepare.prepare(Path('/tmp/dispatcharr-native-hardening-input'),output,evidence)
        finally:os.umask(old)
        self.assertEqual(output.stat().st_mode&0o777,0o700)
        for p in (output/'app').rglob('*'):self.assertEqual(p.stat().st_mode&0o777,0o755 if p.is_dir() else 0o644)

if __name__=='__main__':
    if os.environ.get('PROVIDER_PERMISSION_FIXTURE')!='1':raise SystemExit('isolated_namespace_runner_required')
    # The host /tmp owner is outside the mapped user namespace. Give this
    # namespace its own root-owned /tmp, not a bypass in production ancestry
    # validation. Retain only the public pinned source inputs before hiding it.
    originals={name:(Path('/tmp/dispatcharr-native-hardening-input')/name).read_bytes() for name in prepare.PINS}
    subprocess.run(['mount','-t','tmpfs','-o','size=32m,mode=1777,nosuid,nodev','tmpfs','/tmp'],check=True)
    for name,data in originals.items():
        f=Path('/tmp/dispatcharr-native-hardening-input')/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    unittest.main()
