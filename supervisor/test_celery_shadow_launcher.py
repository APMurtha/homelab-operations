"""Fixture-only tests of the exact launcher validation/orchestration."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from celery_handoff import ANCHOR, DROP
import celery_shadow_launcher as shadow
from dispatcharr_project import NS
from ops_collector import collect

BOOT = '6c280c06-acf0-4d52-aeb4-ead34b170f46'
PAIR = ['default@fixture', 'dvr@fixture']


class ShadowLauncher(unittest.TestCase):
    def setUp(self):
        self.now = time.time_ns()
        self.p = dict(version='celery-shadow-once-v1', host='rivendell',
                      target='rivendell-dispatcharr', boot=BOOT, nonce='f'*64,
                      not_before_ns=self.now-NS, expires_ns=self.now+60*NS,
                      backend_id='a'*64, backend_pid=202,
                      backend_start_ns=self.now-2*NS, net_inode=300,
                      names=PAIR, broker_endpoint=shadow.ENDPOINT,
                      broker_scope_sha256='b'*64, witness_sha256='c'*64, ping_sha256='d'*64)

    def parse(self, **changes):
        return shadow.permit(json.dumps(self.p | changes).encode(), BOOT, self.now)

    def test_fixed_scope_time_command_and_no_data_arguments(self):
        p = self.parse()
        args = shadow.unit_command(p,'e'*64,123)
        self.assertEqual(args[0], '/usr/bin/systemd-run')
        self.assertIn('--unit=samwise-celery-shadow-once.service',args)
        self.assertIn('-pRuntimeMaxSec=17s',args)
        self.assertIn('-pKillMode=control-group',args)
        self.assertIn('-pKillSignal=SIGKILL',args)
        self.assertIn('-pRestart=no',args)
        self.assertIn('-pNetworkNamespacePath=/proc/202/ns/net',args)
        self.assertIn('-pIPAddressDeny=any',args)
        self.assertEqual(args[-6:], ['/usr/bin/python3','-IB',
                                    '/opt/samwise-celery-shadow/celery_shadow_launcher.py','--worker','e'*64,'123'])
        for private in self.p.values():
            if type(private) is str and len(private) == 64:
                self.assertNotIn(private,' '.join(args))
        for changes in (dict(boot='stale'),dict(not_before_ns=self.now+1),
                        dict(expires_ns=self.now+5*NS),dict(expires_ns=self.now+301*NS),
                        dict(host='other'),dict(names=['dvr@x','default@y']),
                        dict(broker_endpoint='127.0.0.1:6378'),dict(backend_pid=True),
                        dict(extra='execute arbitrary command')):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.parse(**changes)

    def test_permit_exclusive_no_retry_even_when_not_used(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            shadow.claim(p,self.parse(),os.getuid())
            with self.assertRaises(FileExistsError):
                shadow.claim(p,self.parse(),os.getuid())
            self.assertEqual(len(list(p.iterdir())),1)

    def test_entry_never_acts_outside_enrolled_cgroup_or_namespace(self):
        with patch('celery_shadow_launcher.os.geteuid',return_value=999), \
             patch('celery_shadow_launcher.claim') as claim:
            with self.assertRaises(ValueError):
                shadow.entry('--worker')
            claim.assert_not_called()

    def test_fixed_launcher_exec_only_after_enrollment_and_without_io(self):
        def check_launch(mode, now):
            uname = SimpleNamespace(nodename=shadow.HOST)
            with patch.object(shadow.os,'geteuid',return_value=0), \
                 patch.object(shadow.os,'uname',return_value=uname), \
                 patch.object(shadow,'trusted_bytes',return_value=json.dumps(self.p).encode()), \
                 patch.object(shadow.Path,'read_text',return_value=BOOT), \
                 patch.object(shadow.time,'time_ns',return_value=now), \
                 patch.object(shadow.time,'monotonic_ns',return_value=123), \
                 patch.object(shadow,'preflight_observer'), \
                 patch.object(shadow.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as execute:
                if mode == 'expired':
                    with self.assertRaises(ValueError):
                        shadow.entry('--launch')
                    execute.assert_not_called()
                else:
                    result = shadow.entry(mode)
                    if mode == '--launch':
                        self.assertEqual(result,'shadow-finished')
                        pin = hashlib.sha256(json.dumps(self.p).encode()).hexdigest()
                        execute.assert_called_once_with(shadow.unit_command(self.p,pin,123),
                            cwd='/',env=shadow.CAPTURE_ENV,stdin=shadow.subprocess.DEVNULL,
                            stdout=shadow.subprocess.DEVNULL,stderr=shadow.subprocess.DEVNULL,
                            timeout=18,check=False)
                    else:
                        self.assertEqual(result,'plan-valid')
                        execute.assert_not_called()

        check_launch('--plan-only',self.now)
        check_launch('--launch',self.now)
        check_launch('expired',self.now+60*NS)

    def test_exact_observer_identity_and_group_refuses_drift(self):
        user = b'samwise-observe:x:999:985::/nonexistent:/opt/samwise-observe/login\n'
        group = b'samwise-observe:x:985:\n'
        shadow.observer_ids(user,group)
        for wrong in (user.replace(b':999:',b':1000:'),user.replace(b':985:',b':986:')):
            with self.assertRaises(ValueError):
                shadow.observer_ids(wrong,group)
        with self.assertRaises(ValueError):
            shadow.observer_ids(user,group+b'docker:x:988:samwise-observe\n')
        outer = SimpleNamespace(st_uid=0,st_gid=985,st_mode=0o40750)
        drop = SimpleNamespace(st_uid=0,st_gid=985,st_mode=0o42750)
        shadow.evidence_ids(outer,drop)
        with self.assertRaises(ValueError):
            shadow.evidence_ids(outer,SimpleNamespace(st_uid=0,st_gid=988,st_mode=0o42750))

    def test_outer_timeout_deducts_preflight(self):
        uname = SimpleNamespace(nodename=shadow.HOST)
        with patch.object(shadow.os,'geteuid',return_value=0), \
             patch.object(shadow.os,'uname',return_value=uname), \
             patch.object(shadow.Path,'read_text',return_value=BOOT), \
             patch.object(shadow,'trusted_bytes',return_value=json.dumps(self.p).encode()), \
             patch.object(shadow.time,'time_ns',return_value=self.now), \
             patch.object(shadow.time,'monotonic_ns',side_effect=[NS,NS+NS//4]), \
             patch.object(shadow,'preflight_observer'), \
             patch.object(shadow.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(shadow.entry('--launch'),'shadow-finished')
            self.assertEqual(run.call_args.kwargs['timeout'],17.75)

    def test_worker_refuses_replaced_permit_before_nonce_or_capture(self):
        uname = SimpleNamespace(nodename=shadow.HOST)
        with patch.object(shadow.os,'geteuid',return_value=0), \
             patch.object(shadow.os,'uname',return_value=uname), \
             patch.object(shadow.Path,'read_text',return_value=BOOT), \
             patch.object(shadow,'trusted_bytes',return_value=json.dumps(self.p).encode()), \
             patch.object(shadow,'claim') as claim, patch.object(shadow,'pinned_worker') as worker:
            with self.assertRaises(ValueError):
                shadow.entry('--worker','0'*64,str(time.monotonic_ns()))
            claim.assert_not_called()
            worker.assert_not_called()
        with patch.object(shadow,'trusted_bytes') as read:
            with self.assertRaises(ValueError):
                shadow.entry('--worker','0'*64,str(time.monotonic_ns()-2*NS))
            read.assert_not_called()

    def test_real_bounded_witness_and_capture_fixture(self):
        row = dict(Name='/dispatcharr', Id=self.p['backend_id'], Status='running',
                   Running=True, Pid=self.p['backend_pid'],
                   StartedNs=self.p['backend_start_ns'], Health='healthy',
                   HealthEndNs=self.now-NS, HealthExitCode=0)
        frame = dict(boot=BOOT, backend=row, workers={PAIR[0]:[5,6],PAIR[1]:[7,8]},
                     net_inode=self.p['net_inode'], endpoint=shadow.ENDPOINT,
                     scope_sha256=self.p['broker_scope_sha256'])
        expected = {'observations':['celery']}

        def as_program(path, payload, requirements=''):
            data = ('#!/usr/bin/python3 -I\nimport sys\n'+requirements+
                    '\nprint('+repr(json.dumps(payload))+')\n').encode()
            path.write_bytes(data)
            path.chmod(0o755)
            return hashlib.sha256(data).hexdigest()

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            output = folder/DROP
            output.mkdir(mode=0o700)
            (output/ANCHOR).touch()
            (output/ANCHOR).chmod(0o640)
            left,right = folder/'witness',folder/'pidbox-ping'
            witness_sha = as_program(left,frame, 'assert len(sys.argv) == 1')
            ping_sha = as_program(right,{n:{'ok':'pong'} for n in PAIR},
                'assert sys.argv[1:] == '+repr(['--destination='+','.join(PAIR),'--timeout=8','--json']))
            p = self.parse(witness_sha256=witness_sha,ping_sha256=ping_sha)
            with patch.multiple(shadow,WITNESS=left,PING=right,DROP=output):
                def read(value, deadline):
                    self.assertGreater(deadline,time.monotonic())
                    self.assertEqual(collect(json.dumps(expected),folder,os.getuid()),{'celery':value})
                    return value
                self.assertEqual(shadow.pinned_worker(p,os.getuid(),read),'both-ready')
                self.assertEqual(collect(json.dumps(expected),folder,os.getuid()),{'celery':'unavailable'})
                wrong = as_program(left,frame | {'scope_sha256':'0'*64})
                self.assertEqual(shadow.pinned_worker(p | {'witness_sha256':wrong},
                                 os.getuid(),read),'unavailable')
                with self.assertRaises(ValueError):
                    shadow.pinned_worker(p,os.getuid(),read)

    def test_independent_witness_deadline_passed_to_capture_and_fail_closed(self):
        # The integration above uses actual bounded process capture. This failure
        # injects the independently signalled witness deadline at that boundary.
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/DROP
            output.mkdir(mode=0o700)
            (output/ANCHOR).touch()
            (output/ANCHOR).chmod(0o640)
            p = self.parse()
            with patch.object(shadow,'DROP',output), \
                 patch.object(shadow,'trusted_bytes',return_value=b''), \
                 patch.object(shadow,'capture',side_effect=TimeoutError('fixture')) as runner:
                empty = hashlib.sha256(b'').hexdigest()
                p |= dict(witness_sha256=empty,ping_sha256=empty)
                self.assertEqual(shadow.pinned_worker(p,os.getuid(),None),'unavailable')
                runner.assert_called_once_with([str(shadow.WITNESS)],'/',shadow.CAPTURE_ENV,1)
                self.assertFalse((output/'celery').exists())


@unittest.skipUnless(os.environ.get('SAMWISE_CELERY_CGROUP_STAGE') == '1',
                     'requires disposable bubblewrap staging')
class FlatProductionEntrypoint(unittest.TestCase):
    def test_exact_isolated_argv_bootstraps_flat_package_from_hostile_cwd(self):
        from shutil import copyfile
        actual_boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        now = time.time_ns()
        with tempfile.TemporaryDirectory(prefix='celery-flat-stage-') as tmp:
            base = Path(tmp)
            package = base/'package'
            hostile = base/'hostile'
            package.mkdir(mode=0o755)
            hostile.mkdir(mode=0o755)
            for name in ('celery_shadow_launcher.py','celery_readiness.py','dispatcharr_project.py',
                         'ops_protocol.py','celery_handoff.py'):
                copyfile(Path(__file__).with_name(name),package/name)
                (package/name).chmod(0o644)
                (hostile/name).write_text("raise RuntimeError('HOSTILE_IMPORT')\n")
            raw = json.dumps(dict(version='celery-shadow-once-v1', host=shadow.HOST,
                      target=shadow.TARGET, boot=actual_boot, nonce='f'*64,
                      not_before_ns=now-NS, expires_ns=now+60*NS, backend_id='a'*64,
                      backend_pid=202, backend_start_ns=now-2*NS, net_inode=300,
                      names=PAIR, broker_endpoint=shadow.ENDPOINT, broker_scope_sha256='b'*64,
                      witness_sha256='c'*64, ping_sha256='d'*64)).encode()
            enrolled = package/'one-shot.json'
            enrolled.write_bytes(raw)
            enrolled.chmod(0o600)
            def invoke(argv):
                command = ['/usr/bin/bwrap','--unshare-user','--uid','0','--gid','0',
                           '--unshare-uts','--hostname',shadow.HOST,'--unshare-net',
                           '--clearenv','--setenv','PYTHONPATH','/hostile',
                           '--ro-bind','/usr','/usr','--symlink','usr/lib','/lib',
                           '--symlink','usr/lib64','/lib64','--proc','/proc','--dev','/dev',
                           '--dir','/opt','--ro-bind',str(package),str(shadow.INSTALL),
                           '--ro-bind',str(hostile),'/hostile','--chdir','/hostile',*argv]
                return subprocess.run(command,timeout=4,stdin=subprocess.DEVNULL,
                                      capture_output=True,text=True)
            exec_argv = shadow.unit_command(
                {'backend_pid':202},hashlib.sha256(raw).hexdigest(),time.monotonic_ns())[-6:]
            good = invoke(exec_argv[:3]+['--plan-only'])
            self.assertEqual((good.returncode,good.stdout,good.stderr),(0,'plan-valid\n',''))
            # Exact generated worker argv on the wrong cgroup must refuse,
            # with no import traceback or capture; the plan proves imports.
            exec_argv[-1] = str(time.monotonic_ns())
            denied = invoke(exec_argv)
            self.assertEqual((denied.returncode,denied.stdout,denied.stderr),(1,'unavailable\n',''))
            (package/'ops_protocol.py').chmod(0o664)
            unsafe = invoke(exec_argv[:3]+['--plan-only'])
            self.assertEqual((unsafe.returncode,unsafe.stdout,unsafe.stderr),(1,'unavailable\n',''))
