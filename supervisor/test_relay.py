import contextlib
import http.client
import io
import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from runner import Relay


class Transport(unittest.TestCase):
    def test_only_fixed_text_inference(self):
        requests = []
        @contextlib.contextmanager
        def upstream(body):
            requests.append(body)
            stream = io.BytesIO(b'event: completed\n\n')
            stream.status = 200
            yield stream

        with tempfile.TemporaryDirectory() as temp:
            sock = Path(temp) / 'model.sock'
            with Relay(sock, upstream, 'reviewed-model') as server:
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                try:
                    def post(path, obj):
                        conn = http.client.HTTPConnection('localhost')
                        conn.sock = socket.socket(socket.AF_UNIX)
                        conn.sock.connect(str(sock))
                        conn.request('POST', path, json.dumps(obj), {'Authorization': 'ignored'})
                        response = conn.getresponse()
                        status = response.status
                        response.read()
                        conn.close()
                        return status

                    msg = {'role': 'user', 'content': [{'type': 'input_text', 'text': 'goal'},
                                                      {'type': 'input_file', 'file_id': 'unused'}]}
                    obj = dict(model='reviewed-model', input=[msg], tools=[{'type': 'web_search'}],
                               previous_response_id='unused', store=True)
                    self.assertEqual(post('/unapproved', obj), 403)
                    self.assertEqual(post('/v1/responses', dict(obj, model='other')), 403)
                    self.assertEqual(post('/v1/responses', obj), 200)
                    self.assertEqual(post('/v1/responses', obj), 200)
                    self.assertEqual(post('/v1/responses', obj), 403)
                    self.assertEqual(len(requests), 2)
                    self.assertEqual(requests[0]['input'], [{'role': 'user', 'content': 'goal'}])
                    self.assertFalse(requests[0]['store'])
                    self.assertFalse({'previous_response_id', 'tools'} & requests[0].keys())
                finally:
                    server.shutdown()
                    thread.join()
