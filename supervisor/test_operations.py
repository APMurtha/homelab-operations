import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from github import Denied, Unavailable, sha
from operations import OperationsGithub, advance, exchange, parse_enrollment, ssh_argv
from ops_collector import collect
from ops_protocol import TAG, decode, reply
from test_worker import BASE, Hub
from worker import Store, tick

PIN = 'SHA256:' + 'A' * 43


def task():
    return dict(version='operations-v1', base=BASE, host_key=PIN, target='rivendell-dispatcharr',
                observations=['guard'], seconds=3, bytes=256, attempts=2, expires=int(time.time())+300)


class Remote(OperationsGithub, Hub):
    def __init__(self):
        Hub.__init__(self)
        self.pin = PIN
        self.body = json.dumps(task())
        self.comments.clear()
        self.events[0]['label']['name'] = self.label
        self.posts = 0
        self.drop = False

    def get(self, path, method='GET', data=None):
        result = super().get(path, method, data)
        if path == 'issues/8':
            result['labels'] = [{'name':self.label}]
        if path == 'issues/8/comments' and method == 'POST':
            self.posts += 1
            if self.drop:
                raise Unavailable()
        return result


class Operations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.db = Store(self.directory)
        self.addCleanup(lambda: self.db.db.close())
        self.api = Remote()
        self.calls = 0

    def observe(self, spec):
        self.calls += 1
        return b'{"guard":"verified"}'

    def advance(self, observe=None):
        advance(8, self.api, self.db, observe or self.observe)
        return self.db.get(8)

    def approve(self):
        self.assertIsNone(self.advance())
        self.assertEqual(self.calls, 0)
        challenge = self.api.comments[0]['body'].splitlines()[-1]
        self.assertEqual(challenge, f'approve operations-v1 #8 17 {sha(self.api.body)} {BASE}')
        self.api.comments.append(dict(self.api.comments[0], body=challenge, id=21))

    def test_uncertain_post_restart_and_replay(self):
        self.approve()
        self.api.drop = True
        self.assertEqual(self.advance()['phase'], 'posting')
        self.db.db.close()
        self.db = Store(self.directory)
        self.assertEqual(self.advance()['phase'], 'published')
        self.assertEqual(self.advance()['phase'], 'published')
        self.assertEqual((self.calls, self.api.posts), (1, 2))  # Challenge plus one report.

    def test_pre_post_crash_does_not_guess(self):
        self.approve()
        original = self.api.get
        with patch.object(self.api, 'get') as get:
            def fail_before_post(path, method='GET', data=None):
                if method == 'POST':
                    raise Unavailable()
                return original(path, method, data)
            get.side_effect = fail_before_post
            self.assertEqual(self.advance()['phase'], 'posting')
        for _ in range(5):
            self.advance()
        self.assertEqual(self.db.get(8)['phase'], 'escalated')
        self.assertEqual(self.api.posts, 1)

    def test_cancellation_before_publication(self):
        self.approve()
        def revoked(spec):
            self.api.comments.append(dict(self.api.comments[0], body='cancel operations-v1 #8', id=22))
            return self.observe(spec)
        self.assertEqual(self.advance(revoked)['phase'], 'cancelled')
        self.assertEqual(self.api.posts, 1)

    def test_expiry_during_collection(self):
        self.approve()
        with patch('operations.time.time', return_value=time.time()) as clock:
            def late(spec):
                clock.return_value = spec['expires']
                return self.observe(spec)
            self.assertEqual(self.advance(late)['phase'], 'escalated')
        self.assertEqual(self.api.posts, 1)

    def test_attempt_limit(self):
        self.approve()
        def outage(spec):
            raise Unavailable()
        self.assertEqual(self.advance(outage)['phase'], 'collect')
        self.assertEqual(self.advance(outage)['phase'], 'escalated')
        self.assertEqual(self.db.get(8)['attempt'], 2)

    def test_unknown_or_unapproved_data_is_never_saved(self):
        self.approve()
        result = self.advance(lambda _: b'{"guard":"verified","log":"private-canary"}')
        self.assertEqual(result['last'], 'reply-invalid')
        self.assertNotIn('result', result)
        self.assertNotIn('private-canary', json.dumps(result))
        self.assertEqual(self.api.posts, 1)

    def test_strict_grant(self):
        for extra in [dict(target='other'), dict(host_key='another'), dict(seconds=True), dict(attempts=3),
                      dict(bytes=999999), dict(observations=['logs','logs']), dict(expires=0),
                      dict(expires=int(time.time())+7200), dict(command='unused'), dict(observations=['guard;unused'])]:
            with self.subTest(extra=extra), self.assertRaises(Denied):
                self.api.parse_spec(json.dumps(task() | extra))
        with self.assertRaises(ValueError):
            decode('{"a":1,"a":2}')
        for invalid in [b'{"logs":"secret"}', b'{"guard":"secret"}', b'{"guard":[]}', b'\xff']:
            with self.assertRaises(ValueError):
                reply(invalid, ['guard'])

    def test_changed_event_or_edited_grant(self):
        self.approve()
        self.api.events[0]['id'] += 1
        self.assertIsNone(self.advance())
        self.api.edit = 'edited'
        self.assertIsNone(self.advance())
        self.assertEqual(self.calls, 0)

    def test_enabled_tick_isolated_from_engineering(self):
        with patch.dict(os.environ, {'SAMWISE_OPERATIONS_V1':'enabled'}), patch('worker.Runner'), \
                patch('worker.Github') as eng, patch('operations.enrollment', return_value=(PIN,b'')), \
                patch('operations.OperationsGithub', return_value=self.api), \
                patch.object(self.api, 'candidates', return_value=[8]):
            eng.return_value.candidates.return_value=[]
            tick(self.directory)
            self.assertTrue((self.directory/'operations-v1'/'state.sqlite3').is_file())
            self.assertIsNone(self.db.get(8))
            self.assertEqual(self.api.posts, 1)
            self.assertEqual(self.calls, 0)

    def test_disabled_by_default(self):
        with patch.dict(os.environ, {'SAMWISE_OPERATIONS_V1':'off'}), patch('worker.Runner'), \
                patch('worker.Github') as gh, patch('operations.poll') as ops:
            gh.return_value.candidates.return_value=[]
            tick(self.directory)
            ops.assert_not_called()


class Boundary(unittest.TestCase):
    def test_projections(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            inputs = {'logs':'INFO\nERROR', 'playlist':'#EXTM3U\n#EXTINF:-1 tvg-id="dw-english-permanent",DW English\nprivate-canary',
                      'celery':json.dumps(dict.fromkeys(('output_complete','reply_output_valid','default_present','dvr_present'), True)),
                      'guard':'withdrawn','jellyfin-channel':'{"TotalRecordCount":1,"Items":[{"Name":"DW English","Number":"9001"}]}',
                      'jellyfin-guide':'{"TotalRecordCount":0}'}
            for n, data in inputs.items():
                (p/n).write_text(data)
                (p/n).chmod(0o600)
            req=json.dumps({'observations':list(inputs)})
            result=collect(req,p,os.getuid())
            self.assertEqual(list(result.values()), ['warning-or-error','present','unavailable','unavailable','unavailable','unavailable'])
            (p/'celery').write_text('{}')
            (p/'logs').write_text('token private-canary')
            (p/'playlist').write_text('#EXTM3U\n')
            (p/'jellyfin-channel').write_text('{"TotalRecordCount":0,"Items":[]}')
            result=collect(req,p,os.getuid())
            self.assertEqual([result[k] for k in ('logs','celery','playlist','jellyfin-channel')],
                             ['unavailable','unavailable','absent','unavailable'])

    def test_partial_inventory_and_unrelated_playlist_attribute(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            (p/'jellyfin-channel').write_text('{"TotalRecordCount":2,"Items":[]}')
            (p/'playlist').write_text('#EXTM3U\n#EXTINF:-1 other-tvg-id="dw-english-permanent",DW English')
            for source in p.iterdir():
                source.chmod(0o600)
            self.assertEqual(collect('{"observations":["playlist","jellyfin-channel"]}',p,os.getuid()),
                             {'playlist':'absent','jellyfin-channel':'unavailable'})

    def test_file_scope_freshness_and_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            (p/'guard').symlink_to('/dev/null')
            os.mkfifo(p/'vpn')
            (p/'backend').write_bytes(b'A'*65537)
            (p/'logs').write_text('INFO'); (p/'logs').chmod(0o600); os.utime(p/'logs',(1,1))
            (p/'relay').write_text('running'); (p/'relay').chmod(0o666)
            names=['guard','vpn','backend','logs','relay','celery']
            req=json.dumps({'observations':names})
            self.assertEqual(list(collect(req,p,os.getuid()).values()),
                             ['unavailable','unavailable','unavailable','stale','unavailable','unavailable'])
            with self.assertRaises(ValueError):
                collect('{"observations":["../file"]}',p,os.getuid())

    def test_transport_budget_timeout_and_failure(self):
        for code, error in [('print("a"*4096)',Denied), ('import time; time.sleep(5)',Unavailable),
                            ('raise SystemExit(65)',Unavailable)]:
            with self.assertRaises(error):
                exchange([sys.executable,'-c',code], b'{}', 0.3, 256)
        self.assertEqual(exchange([sys.executable,'-c','print("ok")'],b'{}',1,256),b'ok\n')

    def test_single_host_exact_key(self):
        raw = b'\0\0\0\x0bssh-ed25519\0\0\0 ' + b'x'*32
        entry = b'10.10.20.30 ssh-ed25519 ' + base64.b64encode(raw) + b'\n'
        expected = 'SHA256:' + base64.b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
        self.assertEqual(parse_enrollment(entry), (expected,entry))
        for wrong in (entry + entry, entry.replace(b'10.10.20.30',b'*'), entry.replace(b'ed25519',b'rsa'),
                      entry.replace(base64.b64encode(raw),b'INVALID!')):
            with self.assertRaises(Denied):
                parse_enrollment(wrong)

    def test_fixed_transport_and_forced_command(self):
        args=ssh_argv('/key','/known')
        self.assertEqual(args[-2:], ['samwise-observe@10.10.20.30',TAG])
        for option in ['StrictHostKeyChecking=yes','VerifyHostKeyDNS=no','IdentityAgent=none',
                       'ClearAllForwardings=yes','GlobalKnownHostsFile=/dev/null','BatchMode=yes']:
            self.assertIn(option,args)
        for cmd in ('','alternate','samwise-observe-v1;other','internal-sftp'):
            p=subprocess.run([sys.executable,str(Path(__file__).with_name('ops_collector.py'))],
                             env={'SSH_ORIGINAL_COMMAND':cmd},input=b'{}',capture_output=True)
            self.assertEqual((p.returncode,p.stdout,p.stderr),(64,b'',b''))
