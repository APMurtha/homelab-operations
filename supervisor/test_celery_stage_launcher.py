"""Opt-in Bag-End staging: fixed fixture, no production access or installation."""
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import unittest

CGROUP = Path('/sys/fs/cgroup')
SYSTEMCTL = ['/usr/bin/systemctl', '--user']
# Never substitute commands, identity, host, broker or credentials from a request.
FIXTURE = '''
import errno, os, socket, subprocess, sys, time
from pathlib import Path

mode = sys.argv[1]
assert mode in ('clean', 'timeout')
assert set(os.environ) <= {'PATH', 'HOME', 'LC_ALL', 'LC_CTYPE', 'PWD'}
assert os.environ.get('PWD') == '/'
assert not Path('/run/docker.sock').exists()
assert not Path('/var/run/docker.sock').exists()
assert not Path(sys.argv[2]).exists()
assert not Path('/home').exists()
assert not Path('/sys').exists()
with open('/proc/self/status') as data:
    status = dict(line.rstrip().split(':', 1) for line in data if ':' in line)
assert int(status['NoNewPrivs']) == 1
assert int(status['CapEff'],16) == 0
assert int(status['Seccomp']) == 2
for family in (socket.AF_INET, socket.AF_INET6):
    try:
        with socket.socket(family) as sock:
            raise AssertionError('internet socket unexpectedly allowed')
    except OSError as error:
        assert error.errno == errno.EAFNOSUPPORT
with socket.socket(socket.AF_UNIX):
    pass

# Exercise the per-witness process deadline independently of RuntimeMaxSec.
for _ in range(2):
    started = time.monotonic()
    try:
        subprocess.run(['/usr/bin/python3', '-I', '-c', 'import time; time.sleep(30)'],
                       timeout=.10, check=True, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        assert time.monotonic() - started < 1.0
    else:
        raise AssertionError('witness exceeded its deadline')

r, w = os.pipe()
pid = os.fork()
if pid == 0:
    os.close(r)
    os.setsid()
    assert os.getsid(0) == os.getpid()
    os.write(w, b'1')
    os.close(w)
    for fd in (0, 1, 2):
        os.close(fd)
    time.sleep(20)
    os._exit(2)
os.close(w)
assert os.read(r, 1) == b'1'
os.close(r)
print('ISOLATED SETSID WITNESSES_BOUNDED', flush=True)
time.sleep(.5 if mode == 'clean' else 20)
'''


def show(unit, key):
    result = subprocess.run(SYSTEMCTL + ['show', '--value', '-p', key, unit],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=3, text=True)
    return result.stdout.strip()


def pids(path):
    try:
        return {int(pid) for pid in (path/'cgroup.procs').read_text().split()}
    except FileNotFoundError:
        return set()


def running(pid):
    try:
        return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[0] not in ('X', 'Z')
    except FileNotFoundError:
        return False


@unittest.skipUnless(os.environ.get('SAMWISE_CELERY_CGROUP_STAGE') == '1',
                     'requires Bag-End user systemd and bubblewrap')
class StageLauncher(unittest.TestCase):
    def exercise(self, mode, limit=2, wall_cap=None):
        with tempfile.TemporaryDirectory(prefix='celery-cgroup-stage-') as tmp:
            root = Path(tmp)
            fixture = root/'fixture.py'
            fixture.write_text(FIXTURE)
            (root/'hidden-canary').touch()
            unit = 'samwise-celery-stage-'+secrets.token_hex(6)+'.service'
            command = [
                '/usr/bin/systemd-run', '--user', '--unit='+unit, '--quiet', '--wait',
                '--pipe', '-p', 'RuntimeMaxSec='+str(limit)+'s', '-p', 'KillMode=control-group',
                '-p', 'KillSignal=SIGKILL', '-p', 'TimeoutStopSec=1s',
                '-p', 'NoNewPrivileges=yes',
                '-p', 'RestrictAddressFamilies=AF_UNIX AF_NETLINK', '-p', 'IPAddressDeny=any',
                '/usr/bin/bwrap', '--unshare-user', '--unshare-pid', '--unshare-net',
                '--die-with-parent', '--clearenv', '--setenv', 'PATH', '/usr/bin',
                '--setenv', 'HOME', '/nonexistent', '--setenv', 'LC_ALL', 'C',
                '--ro-bind', '/usr', '/usr', '--symlink', 'usr/lib', '/lib',
                '--symlink', 'usr/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
                '--dir', '/tmp', '--chdir', '/', '--ro-bind', str(fixture), '/fixture.py',
                '/usr/bin/python3', '-I', '-B', '/fixture.py', mode, str(root/'hidden-canary'),
            ]
            begun = time.monotonic()
            wrapper = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL, text=True)
            group = None
            observed = set()
            escaped = set()
            try:
                deadline = begun + limit + 4
                while wrapper.poll() is None and time.monotonic() < deadline:
                    if group is None:
                        cg = show(unit, 'ControlGroup')
                        if cg.startswith('/') and cg.endswith('/'+unit):
                            group = CGROUP / cg.lstrip('/')
                    if group:
                        for pid in pids(group):
                            observed.add(pid)
                            try:
                                fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
                                if int(fields[3]) == pid and int(fields[1]) in observed:
                                    escaped.add(pid)
                            except (FileNotFoundError, ProcessLookupError):
                                pass
                    time.sleep(.025)
                output, _ = wrapper.communicate(timeout=2)
                elapsed = time.monotonic() - begun
                self.assertEqual(output.strip(), 'ISOLATED SETSID WITNESSES_BOUNDED',
                                 'fixture did not reach the sanitized completion marker')
                self.assertIsNotNone(group)
                self.assertTrue(escaped, 'no session-escaped descendant observed inside the unit')
                self.assertEqual(wrapper.returncode == 0, mode == 'clean')
                if mode == 'timeout':
                    self.assertEqual(show(unit, 'Result'), 'timeout')
                    self.assertLess(elapsed, limit + 2)
                if wall_cap is not None:
                    self.assertLess(elapsed,wall_cap)
                self.assertFalse(pids(group), 'unit cgroup is not empty')
                self.assertFalse(any(running(pid) for pid in escaped),
                                 'session-escaped descendant remained live')
                print(f'launcher_{mode}_{limit}s_wall_seconds={elapsed:.3f} cgroup_empty=yes')
            finally:
                subprocess.run(SYSTEMCTL + ['stop', unit], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=3)
                subprocess.run(SYSTEMCTL + ['reset-failed', unit], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=3)
                if wrapper.poll() is None:
                    wrapper.kill()
                wrapper.communicate(timeout=2)

    def test_clean_teardown(self):
        self.exercise('clean')

    def test_runtime_limit_teardown(self):
        self.exercise('timeout')

    def test_exact_shadow_runtime_limit_teardown(self):
        from celery_shadow_launcher import HARD_SECONDS, UNIT_SECONDS
        self.exercise('timeout', UNIT_SECONDS, wall_cap=HARD_SECONDS)


if __name__ == '__main__':
    unittest.main()
