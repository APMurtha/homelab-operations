"""Opt-in independent acceptance using the real CLI and real rootless containers, offline."""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from runner import LABEL, Runner
from test_worker import CODE, TEST, CHANGES, Hub
from worker import Store, advance


@contextlib.contextmanager
def scripted_response(body, attempt):

    assert set(body) == {'model', 'instructions', 'input', 'stream', 'store', 'max_output_tokens'}
    assert 'host-canary-173' not in json.dumps(body)
    candidate = dict(CHANGES)
    if attempt == 1:
        candidate[CODE] = 'def triple(n): return 0'
    else:
        assert 'offline-test-failure' in json.dumps(body)
    content = json.dumps(candidate)
    msg = dict(type='message', id='msg_1', role='assistant',
               content=[dict(type='output_text', text=content, annotations=[])], status='completed')
    events = [('response.created', {'response': {'id': 'resp_1'}}),
              ('response.output_item.added', {'item': dict(msg, content=[]), 'output_index': 0}),
              ('response.output_text.delta', {'item_id': 'msg_1', 'output_index': 0, 'content_index': 0,
                                             'delta': content}),
              ('response.output_item.done', {'item': msg, 'output_index': 0}),
              ('response.completed', {'response': {'id': 'resp_1', 'status': 'completed', 'output': [msg]}})]
    stream = io.BytesIO(''.join('event: ' + typ + '\ndata: ' + json.dumps({'type': typ, **data})
                                 + '\n\n' for typ, data in events).encode())
    stream.status = 200
    yield stream


@unittest.skipUnless(os.getenv('SAMWISE_ISOLATION_TEST') == '1', 'requires pinned runner and CLI')
class Isolated(unittest.TestCase):
    def test_cli_iteration_recovery_publication(self):
        calls = []
        def upstream(body):
            calls.append(body)
            return scripted_response(body, len(calls))

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            runner, api = Runner(directory, upstream), Hub()
            api.fail = 'pulls'
            for phase in ['generate', 'publish', 'published', 'published']:
                store = Store(directory)
                try:
                    advance(8, api, runner, store)
                    self.assertEqual(store.get(8)['phase'], phase, store.get(8)['last'])
                finally:
                    store.db.close()
            self.assertEqual(len(calls), 2)
            self.assertEqual(api.pr['number'], 19)
            self.assertFalse(list(directory.glob('tmp*')))
            self.assertEqual(subprocess.check_output(['podman', 'ps', '-aq', '--filter', 'label=' + LABEL]), b'')

    def test_host_secrets_and_network_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            canary = p / 'private'
            canary.write_text('host-canary-173')
            code = ('import os,pathlib,socket,unittest\nclass Isolation(unittest.TestCase):\n'
                    ' def test_boundary(self):\n'
                    f'  self.assertFalse(pathlib.Path({str(canary)!r}).exists())\n'
                    '  self.assertGreater(os.getuid(),0)\n'
                    '  self.assertFalse(any(k in os.environ for k in '
                    '("GH_TOKEN","GITHUB_TOKEN","SSH_AUTH_SOCK","SAMWISE_OPENAI_API_KEY","OPENAI_API_KEY")))\n'
                    '  self.assertFalse(pathlib.Path("/relay").exists())\n'
                    '  self.assertEqual(os.listdir("/sys/class/net"),["lo"])\n'
                    '  with self.assertRaises(OSError): pathlib.Path("/opt/write").touch()\n')
            self.assertEqual(Runner(p).test(9, {TEST: code}), 'passed')
