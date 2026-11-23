import json
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import unittest

from celery_readiness import LIMIT, Witness, acquire, argv, capture, pongs
from dispatcharr_project import NS
import test_dispatcharr_project as fixtures

BOOT = fixtures.BOOT


class Readiness(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.Pipeline()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.out = f.output
        self.names = ('default@fixture', 'dvr@fixture')
        self.pids = {name: (101 + i, 1001 + i) for i, name in enumerate(self.names)}
        self.row = f.rows['backend']
        # Existing unrelated file; candidate must never change it.
        self.unrelated_bytes = (self.out / 'relay').read_bytes()

    def result(self, names=None):
        return 0, json.dumps({n: {'ok': 'pong'} for n in (names or self.names)}).encode(), b''

    def run_capture(self, result=None, before=None, after=None, clock=None, mono=None):
        witness = Witness(BOOT, self.row, self.pids)
        snapshots = iter((before or witness, after or witness))
        now = self.fixture.now
        clocks = iter(clock or (now, now+NS, now+2*NS))
        monos = iter(mono or (NS, 3*NS))
        value = acquire(self.out, os.getuid(), BOOT, self.names, lambda: next(snapshots),
                        lambda names: result(names) if callable(result) else
                        self.result() if result is None else result,
                        now=lambda: next(clocks), monotonic=lambda: next(monos))
        self.assertEqual((self.out/'relay').read_bytes(), self.unrelated_bytes)
        return value

    def test_entry_point_publishes_only_sanitized_projection_and_expires(self):
        self.assertEqual(self.run_capture(), 'both-ready')
        expiry = self.fixture.s + 60*NS
        self.assertEqual(self.fixture.read('celery', now=expiry-1)['celery'], 'both-ready')
        self.assertEqual(self.fixture.read('celery', now=expiry+1)['celery'], 'stale')
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

    def test_overlap_refuses_new_probe_without_disturbing_owner(self):
        calls = []
        def ping(_):
            return capture([sys.executable, '-c', 'print("not called")'], '/', {}, 1)
        with (self.out/'.celery-acquisition.lock').open('wb') as lock:
            os.fchmod(lock.fileno(), 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(acquire(self.out, os.getuid(), BOOT, self.names,
                             lambda: calls.append('unexpected'), ping), 'busy')
        self.assertEqual(calls, [])

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
