import json
import fcntl
import os
import select
import signal
from pathlib import Path
import subprocess
import time
import sys
import unittest

from celery_handoff import ANCHOR, COMMIT, DROP, LEASE, lease_write
from celery_readiness import LIMIT, Witness, leased_acquisition, argv, capture
from unittest.mock import patch
from dispatcharr_project import NS
import test_dispatcharr_project as fixtures

BOOT = fixtures.BOOT


class Readiness(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.Pipeline()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.out = f.output/DROP
        self.out.mkdir(mode=0o700)
        self.anchor = self.out/ANCHOR
        self.anchor.touch(mode=0o640)
        self.anchor.chmod(0o640)
        self.names = ('default@fixture', 'dvr@fixture')
        self.pids = {name: (101 + i, 1001 + i) for i, name in enumerate(self.names)}
        self.row = f.rows['backend']
        # Existing unrelated file; candidate must never change it.
        self.unrelated_bytes = (f.output / 'relay').read_bytes()

    def result(self, names=None):
        return 0, json.dumps({n: {'ok': 'pong'} for n in (names or self.names)}).encode(), b''

    def run_capture(self, result=None, before=None, after=None, clock=None, mono=None, verify=None):
        witness = Witness(BOOT, self.row, self.pids)
        snapshots = iter((before or witness, after or witness))
        now = self.fixture.now
        clocks = iter(clock or (now, now+NS, now+2*NS))
        monos = iter(mono or (NS, 3*NS))
        with leased_acquisition(self.out, os.getuid(), BOOT, self.names, lambda: next(snapshots),
                        lambda names: result(names) if callable(result) else
                        self.result() if result is None else result,
                        now=lambda: next(clocks), monotonic=lambda: next(monos)) as value:
            if verify is not None:
                verify()
        self.assertEqual((self.fixture.output/'relay').read_bytes(), self.unrelated_bytes)
        return value

    def test_entry_point_publishes_only_sanitized_projection_and_expires(self):
        expiry = self.fixture.s + 60*NS
        def verify():
            self.assertEqual(self.fixture.read('celery', now=expiry-1)['celery'], 'both-ready')
            self.assertEqual(self.fixture.read('celery', now=expiry+1)['celery'], 'stale')
        self.assertEqual(self.run_capture(verify=verify), 'both-ready')
        self.assertEqual(self.fixture.read('celery')['celery'], 'unavailable')
        self.assertEqual((self.out/'celery').stat().st_mtime_ns, self.fixture.s)
        self.assertNotIn(b'fixture', (self.out/'celery').read_bytes())
        self.assertEqual((self.out/'celery').stat().st_mode & 0o777, 0o640)

    def test_valid_partial_has_positive_witness_but_not_ready(self):
        self.assertEqual(self.run_capture(self.result(self.names[:1])), 'readiness-failed')

    def test_failed_acquisition_withdraws_last_success(self):
        cases = [
            (69, b'', b'broker error: never preserve raw output'),
            (0, b'{}', b''), (0, b'garbage', b''), (0, b'\xff', b''),
            (0, b' ' * (LIMIT + 1), b''),
            (0, b'{"default@fixture":{"ok":"pong"},"default@fixture":{"ok":"pong"}}', b''),
            (0, b'{"default@fixture":{"ok":"pong","ok":"pong"}}', b''),
            (0, b'{"default@fixture":{"ok":"pong"}}{}', b''),
            (0, b'{"dvr@wrong":{"ok":"pong"}}', b''),
            (0, b'{"default@fixture":{"ok":"pong","extra":true}}', b''),
            (0, b'{"default@fixture":{"ok":NaN}}', b''),
            (0, self.result()[1], b'unexpected warning'),
        ]
        for result in cases:
            with self.subTest(result=result[:1]):
                self.assertEqual(self.run_capture(), 'both-ready')
                self.assertEqual(self.run_capture(result), 'unavailable')
                self.assertFalse((self.out/'celery').exists())
        def timeout(_):
            self.assertFalse((self.out/'celery').exists())
            raise TimeoutError('private text')
        self.assertEqual(self.run_capture(), 'both-ready')
        self.assertEqual(self.run_capture(timeout), 'unavailable')
        self.assertFalse((self.out/'celery').exists())

    def test_restart_reuse_temporal_and_health_fail_closed(self):
        cases = [
            Witness(BOOT, self.row | {'Id': 'b'*64}, self.pids),
            Witness(BOOT, self.row | {'Pid': 999}, self.pids),
            Witness(BOOT, self.row | {'StartedNs': self.row['StartedNs']+1}, self.pids),
            Witness(BOOT, self.row, self.pids | {self.names[0]: (101, 99999)}),
            Witness(BOOT, self.row, self.pids | {self.names[1]: (500, 2000)}),
            Witness('00000000-0000-0000-0000-000000000000', self.row, self.pids),
            Witness(BOOT, self.row | {'HealthEndNs': self.fixture.now-60*NS}, self.pids),
            Witness(BOOT, self.row | {'HealthEndNs': self.fixture.now+60*NS}, self.pids),
            Witness(BOOT, self.row | {'Health': 'unhealthy', 'HealthExitCode': 1}, self.pids),
        ]
        for after in cases:
            with self.subTest(after=after):
                self.assertEqual(self.run_capture(after=after), 'unavailable')
        n = self.fixture.now
        self.assertEqual(self.run_capture(clock=(n, n+NS, n+3*NS)), 'unavailable')
        self.assertEqual(self.run_capture(clock=(n, n+NS, n-NS)), 'unavailable')
        self.assertEqual(self.run_capture(mono=(NS, 20*NS)), 'unavailable')

    def observed(self):
        return self.fixture.read('celery', now=self.fixture.now+3*NS)['celery']

    def test_overlap_refuses_new_probe_without_disturbing_owner(self):
        calls = []
        with self.anchor.open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.run_capture(lambda _: calls.append('unexpected')), 'busy')
        def verify():
            self.assertEqual(self.run_capture(lambda _: calls.append('unexpected')), 'busy')
            self.assertEqual(self.observed(), 'both-ready')
        self.assertEqual(self.run_capture(verify=verify), 'both-ready')
        self.assertEqual(calls, [])

    def test_readonly_collector_cannot_forge_missing_writer(self):
        self.assertEqual(self.run_capture(), 'both-ready')
        with (self.out/LEASE).open('rb') as reader:
            with self.assertRaises(OSError):
                lease_write(reader.fileno())
            self.assertEqual(self.observed(), 'unavailable')

    def test_capture_cannot_inherit_publisher_lease(self):
        def ping(_):
            code = """
from pathlib import Path
import os
for item in Path('/proc/self/fd').iterdir():
    try:
        assert not os.readlink(item).endswith('.celery-publisher.lease')
    except FileNotFoundError:
        pass
"""
            rc, stdout, stderr = capture([sys.executable,'-c',code], '/', {})
            self.assertEqual((rc,stdout,stderr),(0,b'',b''))
            return self.result()
        self.assertEqual(self.run_capture(ping), 'both-ready')

    def test_invalid_lock_output_or_marker_rejects_current_result(self):
        for target, tamper in (
            (ANCHOR, lambda p: p.chmod(0o644)),
            (ANCHOR, lambda p: (p.unlink(), p.touch(mode=0o640))),
            (ANCHOR, lambda p: p.unlink()),
            (LEASE, lambda p: p.unlink()),
            (COMMIT, lambda p: p.write_bytes(b'not JSON')),
            ('.', lambda p: (p.chmod(0o777), p.chmod(0o700))),
            ('celery', lambda p: os.utime(p, ns=(1, 1))),
            ('.', lambda p: p.chmod(0o777)),
        ):
            self.out.chmod(0o700)
            self.anchor.unlink(missing_ok=True)
            self.anchor.touch()
            self.anchor.chmod(0o640)
            def verify():
                self.assertEqual(self.observed(), 'both-ready')
                tamper(self.out/target)
                self.assertEqual(self.observed(), 'unavailable')
            with self.subTest(target=target):
                self.assertEqual(self.run_capture(verify=verify), 'both-ready')
        self.out.chmod(0o700)

    def test_interrupted_commit_never_exposes_receipt_and_recovery_is_fresh(self):
        import celery_readiness
        original = celery_readiness.atomic_control
        self.assertEqual(self.run_capture(), 'both-ready')
        with patch('celery_readiness.atomic_control', side_effect=lambda fd, name, body=b'':
                   original(fd,name,body) if name != COMMIT else
                   (_ for _ in ()).throw(OSError('interrupted'))):
            self.assertEqual(self.run_capture(), 'unavailable')
        self.assertTrue((self.out/'celery').exists())
        self.assertFalse((self.out/COMMIT).exists())
        self.assertEqual(self.observed(), 'unavailable')
        self.assertEqual(self.run_capture(verify=lambda: self.assertEqual(
                         self.observed(), 'both-ready')), 'both-ready')
        self.assertEqual(self.observed(), 'unavailable')

    def test_killed_publisher_loses_eligibility_before_and_after_commit(self):
        def kill_at(gate, child_work, expected):
            reader, writer = os.pipe()
            child = os.fork()
            if child == 0:
                os.close(reader)
                def wait_for_kill():
                    os.write(writer, gate)
                    time.sleep(15)
                try:
                    child_work(wait_for_kill)
                finally:
                    os._exit(1)
            os.close(writer)
            try:
                self.assertTrue(select.select([reader],[],[],3)[0], 'fixture gate not reached')
                self.assertEqual(os.read(reader,1), gate)
                self.assertEqual(self.observed(), expected)
            finally:
                os.kill(child, signal.SIGKILL)
                os.waitpid(child, 0)
                os.close(reader)
            self.assertEqual(self.observed(), 'unavailable')

        # Kernel releases the exclusive lease even if killed after COMMIT and
        # the receipt's acquisition timestamp still looks fresh.
        kill_at(b'C', lambda wait: self.run_capture(verify=wait), 'both-ready')
        self.assertTrue((self.out/COMMIT).exists())
        old = (self.out/COMMIT).read_bytes()

        # New writer is killed after locking the anchor but before withdrawal.
        # It must never inherit the earlier writer's liveness.
        import celery_readiness
        original = celery_readiness.vacuum
        def before_withdrawal(wait):
            def intercept(fd, name):
                if name == COMMIT:
                    wait()
                return original(fd,name)
            with patch('celery_readiness.vacuum', side_effect=intercept):
                self.run_capture()
        kill_at(b'W', before_withdrawal, 'unavailable')
        self.assertEqual((self.out/COMMIT).read_bytes(), old)
        self.assertEqual(self.run_capture(verify=lambda: self.assertEqual(
                         self.observed(), 'both-ready')), 'both-ready')
        self.assertNotEqual((self.out/COMMIT).read_bytes(), old)
        self.assertEqual(self.observed(), 'unavailable')

    def test_success_terminates_same_group_descendant_that_closed_pipes(self):
        # A positive result cannot leave a second process executing after the
        # non-overlap lock is released. Child starts in our original PGID.
        code = """
import os, time
pid = os.fork()
if pid:
    print(pid, flush=True)
else:
    for fd in (0, 1, 2):
        os.close(fd)
    time.sleep(20)
"""
        rc, stdout, stderr = capture([sys.executable, '-c', code], '/', {}, 3)
        self.assertEqual((rc, stderr), (0, b''))
        child = int(stdout)
        proc = Path(f'/proc/{child}/stat')
        deadline = time.monotonic()+1
        while time.monotonic() < deadline:
            try:
                state = proc.read_text().rsplit(')', 1)[1].split()[0]
            except FileNotFoundError:
                return
            if state in ('Z', 'X'):  # Terminated; the system will reap it.
                return
            time.sleep(.01)
        self.fail('capture left a live same-group descendant')

    def test_real_subprocess_bounds_and_fixed_argv(self):
        def python(code, seconds=1):
            return capture([sys.executable, '-c', code], '/', {}, seconds)
        self.assertEqual(python('print("ok")'), (0,b'ok\n',b''))
        with self.assertRaises((TimeoutError, subprocess.TimeoutExpired)):
            python('import time; time.sleep(5)', .1)
        with self.assertRaises(ValueError):
            python('print("x"*20000)')
        command = argv(sys.executable, 'fixture.app', self.names)
        self.assertEqual(command[-5:], ['inspect', 'ping',
                         '--destination=default@fixture,dvr@fixture', '--timeout=8', '--json'])
        with self.assertRaises(ValueError):
            argv(sys.executable, 'fixture.app', ('default@x,dvr@x','dvr@y'))


if __name__ == '__main__':
    unittest.main()
