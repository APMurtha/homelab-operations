"""Actual trusted publisher/reader, real DAC/mounts/crashes; nft/Docker mocked."""
import copy
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch,Mock

BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE),str(BASE/'permanent-streaming'),str(BASE/'guard-interface-review')]
spec=importlib.util.spec_from_file_location('implementation_guard',BASE/'guard.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
import guard_readiness
import relay_main
import bounded_server
from test_feasibility import unprivileged

class Actual(unittest.TestCase):
    def setUp(self):
        self.assertEqual(os.environ.get('TRUSTED_GUARD_IMPLEMENTATION_NS'),'1')
        self.temp=tempfile.TemporaryDirectory(prefix='trusted-guard-actual-');self.root=Path(self.temp.name)
        subprocess.run(['mount','-t','tmpfs','-o','size=8m,nosuid,nodev','tmpfs',str(self.root)],check=True)
        self.root.chmod(0o755);self.private=self.root/'private';self.public=self.root/'public'
        self.private.mkdir(mode=0o700);self.public.mkdir(mode=0o755)
        self.bound=self.root/'bound';self.bound.mkdir(mode=0o755)
        subprocess.run(['mount','--bind',str(self.public),str(self.bound)],check=True)
        subprocess.run(['mount','-o','remount,bind,ro,nosuid,nodev,noexec',str(self.bound)],check=True)
        self.policy=self.root/'policy.json';self.wg=self.root/'wg0.conf'
        policy={'schema':1,'bridge':'br-iptv-eg','subnet':'172.16.70.0/24','vpn_ip':'172.16.70.2','wg_endpoint_ipv4':'93.184.216.34','wg_endpoint_port':443,'local_reply_cidrs':['10.10.20.30/32','10.10.30.0/24','172.20.0.0/16']}
        self.policy.write_text(json.dumps(policy));self.policy.chmod(0o600)
        key='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
        self.wg.write_text('[Interface]\nPrivateKey='+key+'\nAddress=10.7.0.2/32\n[Peer]\nPublicKey='+key+'\nPresharedKey='+key+'\nAllowedIPs=0.0.0.0/0\nEndpoint=93.184.216.34:443\n');self.wg.chmod(0o600)
        self.digest=guard.load_policy(self.policy)[1]
        self.publisher=guard.Publisher(self.private,self.public)
        self.owner={'Id':'a'*64,'Image':guard.VPN_ID,'Config':{'Image':guard.VPN_IMAGE},'HostConfig':{'NetworkMode':'rivendell-iptv-egress'},'State':{'Running':False,'Pid':os.getpid(),'Health':{'Status':'healthy'}},'NetworkSettings':{'Networks':{'rivendell-iptv-egress':{'IPAddress':'172.16.70.2','NetworkID':'b'*64}}}}
        self.network={'Id':'b'*64,'Name':'rivendell-iptv-egress','Driver':'bridge','EnableIPv6':False,'Containers':{'a'*64:{}}}
        self.calls=[];self.fail=None;self.route='default dev tun0';self.output='-P OUTPUT DROP\n-A OUTPUT -d 127.0.0.11/32 -j REJECT';self.dns='nameserver 127.0.0.1\n';self.ipv6='1';self.health_ok=True
        self.ctx=patch.object(guard,'require_managed');self.ctx.start();self.addCleanup(self.ctx.stop)
        patcher=patch.object(guard,'ROOT',BASE);patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(guard,'subprocess',types.SimpleNamespace(run=self.fake_run));patcher.start();self.addCleanup(patcher.stop)
        actual_ns=guard.netns_identity
        patcher=patch.object(guard,'netns_identity',side_effect=lambda pid:(1,2) if pid==1 else actual_ns(pid));patcher.start();self.addCleanup(patcher.stop)
        # Build live semantic evidence using unchanged accepted table template.
        spec=importlib.util.spec_from_file_location('expected_contract',BASE/'minimal-phase6b3d/contracts.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        self.table=m.expected_table(policy)
        self.publish()
    def tearDown(self):
        subprocess.run(['umount',str(self.bound)],check=True);subprocess.run(['umount',str(self.root)],check=True);self.temp.cleanup()
    def fake_run(self,args,**kw):
        self.calls.append(args)
        if args[0]=='nft':
            if self.fail and ((self.fail=='check' and '--check' in args) or (self.fail=='apply' and args[1]=='--file')):raise subprocess.CalledProcessError(1,args)
            stdout=json.dumps(self.table) if '-j' in args else ''
        elif args[:2]==['docker','inspect']:stdout=json.dumps([self.owner])
        elif args[:3]==['docker','network','inspect']:stdout=json.dumps([self.network])
        elif args[:3]==['docker','exec','rivendell-iptv-vpn']:
            tail=args[3:]
            if tail[0]=='ip':stdout=self.route
            elif tail[0]=='iptables':stdout=self.output
            elif 'resolv.conf' in tail[-1]:stdout=self.dns
            elif tail[0]=='cat':stdout=self.ipv6
            else:return subprocess.CompletedProcess(args,0 if self.health_ok else 1,stdout='',stderr='')
        else:raise AssertionError('unexpected synthetic command')
        return subprocess.CompletedProcess(args,0,stdout=stdout,stderr='')
    def publish(self):
        self.owner['State']['Running']=False
        self.publisher.apply(self.policy,self.wg)
        self.publisher.remember_owner(self.owner,self.network,self.policy)
        self.owner['State']['Running']=True
        self.publisher.grant(self.policy)
        self.reader=guard_readiness.Readiness(self.bound,self.digest)
    def read(self,reader=None):return unprivileged(lambda:(reader or self.reader).check())
    def closed(self):self.assertFalse(self.read()['ok'])
    def crash(self,point,grant=False):
        read,write=os.pipe();pid=os.fork()
        if pid==0:
            os.close(read)
            def pause():os.write(write,b'!');signal.pause()
            real=self.publisher.atomic
            def atomic(target,data,mode=0o600):
                if point=='temporary' and target==self.public/'guard.json':
                    original=guard.os.replace
                    def replace(src,dst):
                        if Path(dst)==target:pause()
                        return original(src,dst)
                    with patch.object(guard.os,'replace',replace):return real(target,data,mode)
                result=real(target,data,mode)
                if (point=='legacy' and target==self.private/'ready') or (point=='guard' and target==self.public/'guard.json') or (point=='grant' and target==self.public/'grant.json'):pause()
                return result
            self.publisher.atomic=atomic
            withdrawal=self.publisher.withdraw
            def withdraw(*a,**k):
                if point=='before':pause()
                value=withdrawal(*a,**k)
                if point=='after':pause()
                return value
            self.publisher.withdraw=withdraw
            if grant:self.publisher.grant(self.policy)
            else:self.publisher.apply(self.policy,self.wg)
            os._exit(90)
        os.close(write);import select
        self.assertTrue(select.select([read],[],[],3)[0]);self.assertEqual(os.read(read,1),b'!');os.close(read)
        os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
    def test_valid_UID1000_and_private_root_compatibility(self):
        self.assertTrue(self.read()['ok']);self.assertEqual((self.private/'ready').read_text(),self.digest+'\n')
        self.assertEqual(unprivileged(lambda:(self.private/'ready').read_text())['error'],'PermissionError')
        self.assertEqual(self.private.stat().st_mode & 0o777,0o700)
        self.assertEqual(set(p.name for p in self.public.iterdir()),{'guard.json','grant.json'})
        (self.public/'unexpected').write_text('synthetic')
        self.closed()
        with self.assertRaises(ValueError):self.publisher.apply(self.policy,self.wg)
        (self.public/'unexpected').unlink()
    def test_fresh_generation_same_policy_and_no_adoption(self):
        old=self.reader;generation=old.expected['generation'];self.publish()
        self.assertNotEqual(generation,self.reader.expected['generation'])
        self.assertFalse(self.read(old)['ok']);self.assertTrue(self.read()['ok'])
    def test_old_reader_rejects_new_guard_generation(self):
        old=self.reader;self.publish();self.assertFalse(self.read(old)['ok']);self.assertTrue(self.read()['ok'])
    def test_early_policy_failure_revokes_and_latches(self):
        self.policy.write_text('{}')
        with self.assertRaises(ValueError):self.publisher.apply(self.policy,self.wg)
        self.closed();self.assertTrue(self.publisher.transaction()['blocked'])
    def test_early_WireGuard_mismatch_revokes(self):
        self.wg.write_text(self.wg.read_text().replace('93.184.216.34','93.184.216.35'))
        with self.assertRaises(ValueError):self.publisher.apply(self.policy,self.wg)
        self.closed()
    def test_unsafe_private_input_revokes(self):
        self.policy.chmod(0o644)
        with self.assertRaises(ValueError):self.publisher.apply(self.policy,self.wg)
        self.closed()
    def test_late_nft_check_failure(self):
        self.fail='check'
        with self.assertRaises(subprocess.CalledProcessError):self.publisher.apply(self.policy,self.wg)
        self.closed()
    def test_late_nft_apply_failure(self):
        self.fail='apply'
        with self.assertRaises(subprocess.CalledProcessError):self.publisher.apply(self.policy,self.wg)
        self.closed()
    def test_exact_kernel_readback_is_required(self):
        self.table['nftables'].pop()
        with self.assertRaises(Exception):self.publisher.apply(self.policy,self.wg)
        self.closed()
    def test_unmanaged_apply_revokes_before_refusal(self):
        with patch.object(guard,'require_managed',side_effect=ValueError('unmanaged')):
            with self.assertRaises(ValueError):self.publisher.apply(self.policy,self.wg)
        self.closed()
    def test_real_managed_context_check_refuses_fixture_cgroup(self):
        self.ctx.stop()
        try:
            with self.assertRaises(ValueError):guard.require_managed()
        finally:self.ctx.start()
    def test_wrong_owner_identity_blocks_grant(self):
        self.owner['Id']='c'*64
        with self.assertRaises(ValueError):self.publisher.grant(self.policy)
        self.closed()
    def test_wrong_owner_image_blocks_grant(self):
        self.owner['Image']='wrong'
        with self.assertRaises(ValueError):self.publisher.grant(self.policy)
        self.closed()
    def test_wrong_owner_configuration_blocks_grant(self):
        self.owner['HostConfig']['NetworkMode']='host'
        with self.assertRaises(ValueError):self.publisher.grant(self.policy)
        self.closed()
    def test_wrong_network_identity_blocks_grant(self):
        self.network['Id']='changed'
        with self.assertRaises(ValueError):self.publisher.grant(self.policy)
        self.closed()
    def test_unhealthy_owner_blocks_grant(self):
        self.owner['State']['Health']['Status']='unhealthy'
        with self.assertRaises(ValueError):self.publisher.grant(self.policy)
        self.closed()
    def test_VPN_route_DNS_IPv6_killswitch_and_health_required(self):
        cases=[('route','default dev eth0'),('dns','nameserver 127.0.0.11\n'),('ipv6','0'),('output','-P OUTPUT ACCEPT'),('health_ok',False)]
        # Each isolated subcase restores a known successful transaction first.
        for attr,value in cases:
            with self.subTest(attr=attr):
                old=getattr(self,attr);setattr(self,attr,value)
                with self.assertRaises(ValueError):self.publisher.grant(self.policy)
                self.closed();setattr(self,attr,old)
                # Explicit test reset of PRIVATE fixture latch, never a production reset path.
                self.publisher.write(self.private/'transaction.json',{'phase':'revoked','blocked':False});self.publish()
    def test_missing_malformed_duplicate_oversized_or_writable_status(self):
        path=self.public/'guard.json';original=path.read_bytes()
        values=[b'bad',b'{"schema":1,"schema":1}',b'x'*2049,json.dumps(dict(json.loads(original),schema=True)).encode(),json.dumps(dict(json.loads(original),extra=1)).encode()]
        for value in values:
            path.write_bytes(value);self.closed()
        path.write_bytes(original);path.chmod(0o666);self.closed();path.chmod(0o644);path.unlink();self.closed()
    def test_symlink_and_hardlink_status_rejected(self):
        path=self.public/'guard.json';os.link(path,self.private/'extra');self.closed()
        (self.private/'extra').unlink();path.unlink();path.symlink_to(self.private/'ready');self.closed()
    def test_wrong_boot_digest_or_namespace_rejected(self):
        path=self.public/'grant.json';old=json.loads(path.read_text());record=dict(old,netns_ino=old['netns_ino']+1);path.write_text(json.dumps(record));self.closed()
        path.write_text(json.dumps(old))
        with self.assertRaises(ValueError):guard_readiness.Readiness(self.bound,'f'*64)
        with patch.object(guard_readiness,'boot_identity',return_value='22222222-2222-4222-8222-222222222222'):
            with self.assertRaises(ValueError):guard_readiness.Readiness(self.bound,self.digest)
    def test_directory_bind_is_read_only(self):
        with self.assertRaises(OSError):(self.bound/'guard.json').write_text('tamper')
    def test_missing_grant_during_startup_blocks_reader(self):
        self.publisher.apply(self.policy,self.wg)
        with self.assertRaises(OSError):guard_readiness.Readiness(self.bound,self.digest)
    def test_safe_anchor_retirement_revokes_old_bind(self):
        self.publisher.revoke(False);self.public.rename(self.root/'retired');self.public.mkdir(mode=0o755);self.closed()
        with self.assertRaises(ValueError):self.publisher.apply(self.policy,self.wg)
    def test_unexplained_populated_anchor_is_not_adopted(self):
        (self.private/'anchor.json').unlink()
        with self.assertRaises(ValueError):self.publisher.apply(self.policy,self.wg)
        for name in ['guard.json','grant.json']:(self.public/name).unlink()
        with self.assertRaises(ValueError):self.publisher.apply(self.policy,self.wg)
    def test_boot_metadata_replay_not_adopted(self):
        value=guard.checked_json(self.private/'anchor.json');value['boot_id']='22222222-2222-4222-8222-222222222222';self.publisher.write(self.private/'anchor.json',value)
        with self.assertRaises(ValueError):self.publisher.apply(self.policy,self.wg)
    def test_partial_withdrawal_failure_still_attempts_every_file(self):
        real=Path.unlink
        def failure(path,*a,**kw):
            if path==self.public/'guard.json':raise PermissionError('synthetic')
            return real(path,*a,**kw)
        with patch.object(Path,'unlink',failure):
            with self.assertRaises(ValueError):self.publisher.revoke()
        self.assertFalse((self.public/'grant.json').exists());self.assertFalse((self.private/'ready').exists());self.closed()
    def test_corrupt_private_transaction_does_not_prevent_public_withdrawal(self):
        (self.private/'transaction.json').write_text('bad')
        with self.assertRaises(ValueError):self.publisher.revoke()
        self.closed()
    def test_failed_publication_revokes_and_latches(self):
        real=self.publisher.write
        def failure(path,value,mode=0o600):
            if path==self.public/'guard.json':raise OSError('synthetic')
            return real(path,value,mode)
        with patch.object(self.publisher,'write',failure):
            with self.assertRaises(OSError):self.publisher.apply(self.policy,self.wg)
        self.closed();self.assertTrue(self.publisher.transaction()['blocked'])
    def test_crash_before_first_withdraw_requires_manager_cleanup(self):
        self.crash('before');self.assertTrue(self.read()['ok']);self.publisher.revoke();self.closed()
    def test_crash_after_withdraw(self):self.crash('after');self.closed()
    def test_crash_after_legacy_publish(self):self.crash('legacy');self.closed();self.publisher.revoke();self.closed()
    def test_crash_during_public_atomic_replace(self):self.crash('temporary');self.closed();self.publisher.revoke();self.closed()
    def test_crash_after_guard_commit_without_grant(self):self.crash('guard');self.closed();self.publisher.revoke();self.closed()
    def test_crash_after_grant_commit_manager_cleanup(self):
        self.crash('grant',True);self.assertTrue(self.read()['ok']);self.publisher.revoke(False);self.closed()
    def test_incomplete_crash_latch_prevents_next_apply(self):
        self.crash('guard');self.publisher.revoke()
        with self.assertRaises(ValueError):self.publisher.apply(self.policy,self.wg)
        self.closed()
    def test_FIFO_status_is_rejected_without_blocking(self):
        path=self.public/'guard.json';path.unlink();os.mkfifo(path,0o644)
        self.closed()
    def test_UID1000_owned_status_is_rejected(self):
        os.chown(self.public/'guard.json',1000,1000);self.closed()
    def test_total_withdrawal_failure_needs_supervisor_compensation(self):
        real=Path.unlink
        def failed(path,*a,**kw):
            if path in (self.public/'guard.json',self.public/'grant.json'):raise PermissionError('synthetic')
            return real(path,*a,**kw)
        with patch.object(Path,'unlink',failed):
            with self.assertRaises(ValueError):self.publisher.revoke()
        self.assertTrue(self.read()['ok'])  # Accepted asynchronous compensation limit.
    def test_writer_lock_rejects_hardlink_and_symlink(self):
        lock=self.private/'writer.lock';os.link(lock,self.private/'lock-alias')
        with self.assertRaises(ValueError):self.publisher.revoke()
        (self.private/'lock-alias').unlink();lock.unlink();lock.symlink_to(self.private/'ready')
        with self.assertRaises(OSError):self.publisher.revoke()
    def test_existing_private_directory_permissions_are_never_relaxed(self):
        self.private.chmod(0o755)
        with self.assertRaises(ValueError):self.publisher.revoke()
        self.assertEqual(self.private.stat().st_mode & 0o777,0o755)
    def test_actual_relay_UID1000_start_revoke_shutdown(self):
        runtime=self.root/'runtime';exports=self.root/'exports'
        for p,mode in [(runtime,0o700),(exports,0o750)]:p.mkdir(mode=mode);os.chown(p,1000,1000)
        config={'source':'https://'+__import__('hls_relay').HOST+'/synthetic/live.m3u8','guard_status_dir':str(self.bound),'ready_hash':self.digest,'manifest_deadline_seconds':12,'segment_deadline_seconds':12}
        pid=os.fork()
        if pid==0:
            os.setgroups([]);os.setgid(1000);os.setuid(1000)
            try:status=relay_main.run(config,runtime,exports)
            except Exception:status=99
            os._exit(status)
        import time
        try:
            end=time.monotonic()+4
            while not (runtime/'stats.json').exists():
                if time.monotonic()>end:self.fail('fixture relay startup timeout')
                time.sleep(.02)
            stats=json.loads((runtime/'stats.json').read_text());self.assertEqual(stats['guard_generation'],self.reader.expected['generation'])
            self.assertEqual(stats['counts'].get('requests',0),0)
            self.publisher.revoke(False)
            end=time.monotonic()+6
            while True:
                ended,status=os.waitpid(pid,os.WNOHANG)
                if ended:break
                if time.monotonic()>end:self.fail('fixture relay revocation timeout')
                time.sleep(.02)
            self.assertNotEqual(status,0);self.assertFalse((runtime/'endpoint.json').exists())
            self.assertTrue(json.loads((runtime/'stats.json').read_text())['stopped'])
        finally:
            try:os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
            except ProcessLookupError:pass
            except ChildProcessError:pass

class Lifecycle(unittest.TestCase):
    def test_candidate_owner_grant_registration_gateway_order(self):
        import lifecycle
        events=[];publisher=Mock()
        publisher.grant.side_effect=lambda *a:events.append('grant')
        with patch.object(lifecycle,'trusted',return_value=publisher),patch.object(lifecycle,'execute',side_effect=lambda c,*a:events.append(c[-1])),patch.object(lifecycle,'inside',side_effect=lambda name,*a,**k:events.append(name)):
            lifecycle.start()
        self.assertLess(events.index('iptv-vpn'),events.index('grant'))
        self.assertLess(events.index('grant'),events.index('relay'))
        self.assertLess(events.index('register.py'),events.index('gateway'))
    def test_failed_grant_never_starts_AIO_relay_or_gateway(self):
        import lifecycle
        publisher=Mock();publisher.grant.side_effect=ValueError('synthetic')
        with patch.object(lifecycle,'trusted',return_value=publisher),patch.object(lifecycle,'execute') as execute:
            with self.assertRaises(ValueError):lifecycle.start()
        self.assertEqual(len(execute.call_args_list),1);self.assertEqual(execute.call_args.args[0][-1],'iptv-vpn')
    def test_candidate_cleanup_attempts_all_actions_after_each_failure(self):
        import lifecycle
        for failure in ('withdraw','stop','assert'):
            publisher=Mock();events=[]
            if failure=='withdraw':publisher.revoke.side_effect=ValueError('synthetic')
            def execute(c,*a):
                kind='stop' if 'compose' in c else 'assert';events.append(kind)
                if kind==failure:raise ValueError('synthetic')
            with patch.object(lifecycle,'trusted',return_value=publisher),patch.object(lifecycle,'execute',side_effect=execute):
                with self.assertRaises(ValueError):lifecycle.stop()
            publisher.revoke.assert_called_once_with(False);self.assertEqual(events,['assert','stop','assert','assert'])
    def test_original_cleanup_attempts_scoped_stop_after_guard_program_failure(self):
        spec=importlib.util.spec_from_file_location('original_cleanup',BASE/'minimal-phase6b3d/cleanup.py');cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
        for failed in range(5):
            calls=[]
            def run(c,**k):
                calls.append(c);return subprocess.CompletedProcess(c,1 if len(calls)-1==failed else 0)
            with patch.object(cleanup,'managed'),patch.object(cleanup.subprocess,'run',side_effect=run):
                with self.assertRaises(ValueError):cleanup.cleanup()
            self.assertEqual(len(calls),5);self.assertEqual(calls[2][-3:],['gateway','dispatcharr','iptv-vpn'])
    def test_original_cleanup_attempts_scoped_stop_after_timeout(self):
        spec=importlib.util.spec_from_file_location('cleanup_timeout',BASE/'minimal-phase6b3d/cleanup.py');cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup);calls=[]
        def run(c,**k):
            calls.append(c)
            if len(calls)==1:raise subprocess.TimeoutExpired(c,10)
            return subprocess.CompletedProcess(c,0)
        with patch.object(cleanup,'managed'),patch.object(cleanup.subprocess,'run',side_effect=run):
            with self.assertRaises(ValueError):cleanup.cleanup()
        self.assertEqual(len(calls),5)
    def test_exact_effective_hook_order_and_runtime_preservation(self):
        base=BASE/'minimal-phase6b3d/units'
        guard_drop=(base/'dispatcharr-egress-guard.service.d/20-trusted-readiness.conf').read_text()
        self.assertIn('RuntimeDirectoryPreserve=yes',guard_drop);self.assertIn('RuntimeDirectoryMode=0755',guard_drop)
        for file in [BASE/'boot-admission-phase6b3k/20-resource-admission.conf',BASE/'permanent-streaming/30-permanent-streaming.conf']:
            text=file.read_text();steps=[line for line in text.splitlines() if line.startswith('ExecStartPre=') and line!='ExecStartPre=']
            self.assertTrue(steps[0].endswith('provider_control.py revoke'))
            self.assertLess(text.index('admit.py'),text.index('guard.py apply'))
            self.assertNotIn('Timeout',text);self.assertIn('ExecStopPost=-/usr/bin/rm -f --',text)
        self.assertIn('ExecStopPost=/usr/bin/python3 -B /docker/dispatcharr-iptv/guard.py revoke',guard_drop)
    def test_schema_mount_images_and_rollback_base_are_deliberate(self):
        import hashlib
        self.assertEqual(hashlib.sha256((BASE/'minimal-phase6b3d/units/dispatcharr-stack.service').read_bytes()).hexdigest(),'30e7f5e64b7a6ce3f8ec3cf80572d74bb2dd1ed67083929276cf55fbb65c357e')
        self.assertEqual(hashlib.sha256((BASE/'security.py').read_bytes()).hexdigest(),'e7a92e7753e666a6f8cafd1b0292cec5e65f1431b09fc92ba10678c26e5ef8e2')
        retired=(BASE/'persistence-phase6b3/controller.py').read_text()
        self.assertIn('df53629a537e66fcbdf664076b9fa58de47d590e4a0f0d0128fd15f46f3088bd',retired)
        schema=json.loads((BASE/'permanent-streaming/relay-config.schema.json').read_text())
        self.assertEqual(schema['properties']['guard_status_dir'],{'const':'/guard-status'});self.assertNotIn('ready_file',schema['properties'])
    def test_release_manifest_and_protected_pins_are_consistent(self):
        import hashlib,ast
        repo=BASE.parents[1]
        release=json.loads((BASE/'trusted-guard-tests/transition-manifest.json').read_text())
        for name,digest in release['source_files'].items():
            self.assertEqual(hashlib.sha256((repo/name).read_bytes()).hexdigest(),digest,name)
        for target,item in release['installed_files'].items():
            self.assertEqual(hashlib.sha256((repo/item['source']).read_bytes()).hexdigest(),item['sha256'],target)
            self.assertEqual((item['uid'],item['gid'],item['mode']),(0,0,'0644'))
        tree=ast.parse((BASE/'minimal-phase6b3d/verify.py').read_text())
        extra=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXTRA_PINS' for t in n.targets))
        for target,digest in extra.items():self.assertEqual(release['installed_files'][target]['sha256'],digest)
    def test_historical_permission_baseline_uses_exact_accepted_references(self):
        import hashlib
        refs=BASE/'guard-interface-review/reference'
        for name,digest in [('guard_accepted.py','df53629a537e66fcbdf664076b9fa58de47d590e4a0f0d0128fd15f46f3088bd'),('relay_776f984.py','5eb958dbcf1ef6d2b92fa47ba4fb737511042486601969b955f7940241fb4b36'),('relay_main_776f984.py','b273dd21d1ea8a89010a7304138046d7426c61a98d8aaeb0be3188cd38e69473')]:
            self.assertEqual(hashlib.sha256((refs/name).read_bytes()).hexdigest(),digest)

if __name__=='__main__':unittest.main()
