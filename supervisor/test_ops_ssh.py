"""Opt-in black-box staging exercise: one unprivileged inetd-style sshd per connection.

No system configuration, permanent listener, real key, real host or service manager.
"""
import json
import platform
import shlex
import struct
import time
import os
import pwd
import socket
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from celery_handoff import ANCHOR, DROP
from celery_readiness import Witness, leased_acquisition
from github import Unavailable
from operations import advance, exchange, parse_enrollment, ssh_argv
from ops_protocol import TAG
from test_operations import Remote, task
from worker import Store


# Fixed Linux x86_64 staging filter. It installs inside the bubblewrap payload
# after namespace setup. Connection and broker access cannot be delegated via
# io_uring. The production forced-account launcher/profile is a separate gate.
def no_network_filter():
    if platform.machine() != 'x86_64':
        raise RuntimeError('Linux x86_64 staging filter required')
    # Native syscall numbers for the independently checked deployed deny list.
    denied = (41, 53, 42, 49, 50, 43, 288, 44, 46, 307, 47, 299,
              425, 426, 427, 101, 310, 311, 438, 321, 272, 308)
    errno_eperm = 0x00050001
    ins = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xC000003E), (0x06, 0, 0, 0x80000000),
           (0x20, 0, 0, 0), (0x45, 0, 1, 0x40000000), (0x06, 0, 0, errno_eperm)]
    for nr in denied:
        ins += [(0x15, 0, 1, nr), (0x06, 0, 0, errno_eperm)]
    ins.append((0x06, 0, 0, 0x7FFF0000))
    return b''.join(struct.pack('HBBI', *code) for code in ins)


STAGE_ENTRY = """
import errno, json, os, socket, sys
from pathlib import Path

sys.path.insert(0, '/app')
from celery_handoff import DROP, LEASE, lease_write
from ops_collector import EVIDENCE, collect
from ops_protocol import TAG, check

for family in (socket.AF_UNIX, socket.AF_INET, socket.AF_INET6):
    try:
        with socket.socket(family):
            raise AssertionError('collector socket creation was not denied')
    except OSError as error:
        check(error.errno == errno.EPERM)
check(not Path('/run/docker.sock').exists() and not Path('/var/run/docker.sock').exists())
check(not Path('/home').exists() and not Path('/etc').exists())
check(not Path('/run/redis/redis-server.sock').exists())
check(set(os.environ) <= {'PATH', 'PWD', 'LC_CTYPE', 'SSH_ORIGINAL_COMMAND'})
check(os.getuid() != 0 and os.environ.get('SSH_ORIGINAL_COMMAND') == TAG)
lease = EVIDENCE / DROP / LEASE
if lease.exists():
    fd = os.open(lease, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            lease_write(fd)
        except OSError as error:
            check(error.errno == errno.EBADF)
        else:
            raise AssertionError('read-only descriptor forged publisher eligibility')
    finally:
        os.close(fd)
    try:
        fd = os.open(lease, os.O_RDWR | os.O_NOFOLLOW)
    except OSError as error:
        check(error.errno == errno.EROFS)
    else:
        os.close(fd)
        raise AssertionError('fixture evidence view is writable')
raw = sys.stdin.buffer.read(1025)
check(len(raw) <= 1024)
# Same collector core and fixed evidence path; fixture owner substitutes for
# production root because the disposable SSH test uses no privileged account.
print(json.dumps(collect(raw, EVIDENCE, os.getuid()), separators=(',', ':')))
"""


@unittest.skipUnless(os.environ.get('SAMWISE_TEST_SSH') == '1', 'requires staging OpenSSH')
class StagingSSH(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('SAMWISE_CELERY_CGROUP_STAGE') == '1',
                         'opt-in fixed filesystem and seccomp staging fixture')
    def test_forced_ssh_reads_live_lease_without_socket_or_write_access(self):
        self.assertNotEqual(os.getuid(), 0)
        self.assertFalse(Path('/run/samwise-observations').exists(), 'requires isolated staging')
        user = pwd.getpwuid(os.getuid()).pw_name
        source = Path(__file__).resolve().parent
        with (tempfile.TemporaryDirectory(dir=Path.home()) as tmp,
              tempfile.TemporaryDirectory(dir='/tmp') as fixture):
            p = Path(tmp)
            evidence = Path(fixture)/'evidence'
            drop = evidence/DROP
            drop.mkdir(mode=0o750, parents=True)
            evidence.chmod(0o750)
            (drop/ANCHOR).touch()
            (drop/ANCHOR).chmod(0o640)
            entry = p/'entry.py'
            entry.write_text(STAGE_ENTRY)
            seccomp = p/'filter'
            seccomp.write_bytes(no_network_filter())
            for name in ('client', 'host'):
                subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-f',str(p/name)], check=True)
            (p/'allowed').write_text('restrict ' + (p/'client.pub').read_text())
            # All mount/command choices are trusted local fixture paths, never SSH input.
            command = ['/usr/bin/bwrap', '--unshare-user', '--unshare-pid', '--die-with-parent',
                       '--clearenv', '--setenv', 'PATH', '/usr/bin',
                       '--ro-bind', '/usr', '/usr', '--symlink', 'usr/lib', '/lib',
                       '--symlink', 'usr/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
                       '--dir', '/run', '--dir', '/app', '--chdir', '/app',
                       '--ro-bind', str(entry), '/stage.py',
                       '--ro-bind', str(evidence), '/run/samwise-observations',
                       '--seccomp', '3']
            for name in ('ops_collector.py', 'ops_protocol.py', 'celery_handoff.py'):
                command += ['--ro-bind', str(source/name), '/app/'+name]
            command += ['/usr/bin/env', 'SSH_ORIGINAL_COMMAND=TOKEN',
                        '/usr/bin/python3', '-I', '-B', '/stage.py']
            forced = p/'force'
            shell = shlex.join(command).replace('SSH_ORIGINAL_COMMAND=TOKEN',
                                                'SSH_ORIGINAL_COMMAND="$SSH_ORIGINAL_COMMAND"')
            forced.write_text('#!/bin/sh\nexec ' + shell + ' 3<' + shlex.quote(str(seccomp)) + '\n')
            forced.chmod(0o700)
            config = p/'config'
            config.write_text('\n'.join([
                'HostKey ' + str(p/'host'), 'AuthorizedKeysFile ' + str(p/'allowed'),
                'ForceCommand ' + str(forced), 'UsePAM no', 'DisableForwarding yes',
                'PermitTTY no', 'PermitUserRC no', 'PermitUserEnvironment no',
                'AuthenticationMethods publickey', 'PasswordAuthentication no',
                'KbdInteractiveAuthentication no', 'AllowUsers '+user,
            ])+'\n')
            payload = b'{"observations":["celery"]}'

            def read(tag=TAG):
                with socket.socket() as server:
                    server.bind(('127.0.0.1', 0))
                    server.listen(1)
                    server.settimeout(8)
                    port = server.getsockname()[1]
                    def serve():
                        conn, _ = server.accept()
                        with conn:
                            subprocess.run(['/usr/sbin/sshd','-i','-e','-f',str(config)],
                                           stdin=conn, stdout=conn, stderr=subprocess.DEVNULL, timeout=12)
                    thread = threading.Thread(target=serve)
                    thread.start()
                    try:
                        hosts = p/'known_hosts'
                        pub = (p/'host.pub').read_text().split()[:2]
                        hosts.write_text(f'[127.0.0.1]:{port} ' + ' '.join(pub) + '\n')
                        args = ssh_argv(p/'client', hosts)[:-2] + ['-p',str(port),user+'@127.0.0.1',tag]
                        return json.loads(exchange(args,payload,8,256))
                    finally:
                        thread.join(15)
                        self.assertFalse(thread.is_alive())

            boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            names = ('default@ssh-fixture','dvr@ssh-fixture')
            base = time.time_ns()-1_000_000
            row = dict(Name='/dispatcharr', Id='a'*64, Status='running', Running=True,
                       Pid=6, StartedNs=base, Health='healthy', HealthEndNs=base, HealthExitCode=0)
            witness = Witness(boot, row, {names[0]: (7, 10), names[1]: (8, 11)})
            pong = json.dumps({name: {'ok':'pong'} for name in names}).encode()
            with leased_acquisition(drop, os.getuid(), boot, names, lambda:witness,
                                    lambda _: (0,pong,b'')) as status:
                self.assertEqual(status,'both-ready')
                self.assertEqual(read(), {'celery':'both-ready'})
                with self.assertRaises(Unavailable):
                    read('other-command')
            self.assertEqual(read(), {'celery':'unavailable'})

    def test_pinned_identity_and_remote_boundary(self):
        self.assertNotEqual(os.getuid(), 0)
        self.assertFalse(Path('/run/samwise-observations').exists(), 'use a host without live evidence')
        user = pwd.getpwuid(os.getuid()).pw_name
        with tempfile.TemporaryDirectory(dir=Path.home()) as tmp:
            p = Path(tmp)
            for name in ('client', 'host', 'wrong'):
                subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(p/name)], check=True)
            (p/'allowed').write_text('restrict ' + (p/'client.pub').read_text())
            collector = Path(__file__).resolve().with_name('ops_collector.py')
            config = p/'config'
            config.write_text('\n'.join([
                'HostKey ' + str(p/'host'), 'AuthorizedKeysFile ' + str(p/'allowed'),
                'ForceCommand /usr/bin/python3 -IB ' + str(collector), 'UsePAM no',
                'DisableForwarding yes', 'PermitTTY no', 'PermitUserRC no', 'PermitUserEnvironment no',
                'AuthenticationMethods publickey', 'PasswordAuthentication no',
                'KbdInteractiveAuthentication no', 'AllowUsers ' + user,
            ]) + '\n')

            def connect(tag, payload, host='host', identity='client'):
                with socket.socket() as server:
                    server.bind(('127.0.0.1', 0))
                    server.listen(1)
                    server.settimeout(8)
                    port = server.getsockname()[1]
                    def serve():
                        conn, _ = server.accept()
                        with conn:
                            subprocess.run(['/usr/sbin/sshd','-i','-e','-f',str(config)],
                                           stdin=conn,stdout=conn,stderr=subprocess.DEVNULL,timeout=12)
                    thread = threading.Thread(target=serve)
                    thread.start()
                    try:
                        hosts = p/'known_hosts'
                        pub = (p/(host+'.pub')).read_text().split()[:2]
                        hosts.write_text(f'[127.0.0.1]:{port} ' + ' '.join(pub) + '\n')
                        cmd = ssh_argv(p/identity, hosts)[:-2] + ['-p',str(port),user+'@127.0.0.1',tag]
                        return exchange(cmd,payload,8,256)
                    finally:
                        thread.join(15)
                        self.assertFalse(thread.is_alive())

            # No evidence is provisioned on the staging machine.
            req=b'{"observations":["guard"]}'
            self.assertEqual(json.loads(connect(TAG,req)), {'guard':'unavailable'})
            for args in [(TAG,req,'wrong'), (TAG,req,'host','wrong'), ('another-command',req),
                         (TAG,b'{"observations":["invalid"],"command":"unused"}')]:
                with self.subTest(args=args), self.assertRaises(Unavailable):
                    connect(*args)

            # Full approval -> SSH -> validated report -> replay, with no real GitHub writes.
            api = Remote()
            pub = (p/'host.pub').read_bytes().split()[:2]
            api.pin, _ = parse_enrollment(b'10.10.20.30 ' + b' '.join(pub))
            api.body = json.dumps(task() | {'host_key': api.pin})
            db = Store(p/'state')
            calls = []
            def observe(d):
                calls.append(d['observations'])
                return connect(TAG, json.dumps({'observations':d['observations']}).encode())
            try:
                advance(8, api, db, observe)
                self.assertEqual(calls, [])
                api.comments.append(dict(api.comments[0], id=21, body=api.comments[0]['body'].splitlines()[-1]))
                advance(8, api, db, observe)
                advance(8, api, db, observe)
                self.assertEqual(db.get(8)['phase'], 'published')
                self.assertEqual(db.get(8)['result'], {'guard':'unavailable'})
                self.assertEqual(calls, [['guard']])
                self.assertEqual(api.posts, 2)
            finally:
                db.db.close()
