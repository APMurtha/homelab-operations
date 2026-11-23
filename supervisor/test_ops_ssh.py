"""Opt-in black-box staging exercise: one unprivileged inetd-style sshd per connection.

No system configuration, permanent listener, real key, real host or service manager.
"""
import json
import os
import pwd
import socket
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from github import Unavailable
from operations import advance, exchange, parse_enrollment, ssh_argv
from ops_protocol import TAG
from test_operations import Remote, task
from worker import Store


@unittest.skipUnless(os.environ.get('SAMWISE_TEST_SSH') == '1', 'requires staging OpenSSH')
class StagingSSH(unittest.TestCase):
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
