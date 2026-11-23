"""Rootless Podman boundary. Inference and untrusted Python tests never share a container."""
import contextlib
import hashlib
import http.client
import json
import os
import re
import socketserver
import stat
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from github import Denied, Unavailable, require

IMAGE = 'sha256:9cb180cb36bd45dc786105b834d3cb5f3b1d69a6a63c79ca10fc64f108aa649a'
LABEL = 'io.samwise.engineering-v1=owned'
INSIDE = Path(__file__).resolve().with_name('inside.py')


class Relay(socketserver.UnixStreamServer):
    """Task can request inference only, using a fixed upstream/model, no hosted tools."""
    def __init__(self, path, upstream, model):
        self.upstream = upstream
        self.model = model
        self.remaining = 3
        super().__init__(str(path), Request)


class Request(BaseHTTPRequestHandler):
    timeout = 10

    def log_message(self, *args):
        pass

    def do_POST(self):
        try:
            n = int(self.headers.get('Content-Length', 0))
            if self.path != '/v1/responses' or not 0 < n <= 1500000 or self.server.remaining <= 0:
                self.send_error(403)
                return
            self.server.remaining -= 1
            obj = json.loads(self.rfile.read(n))
            if obj.get('model') != self.server.model or not isinstance(obj.get('input'), list):
                self.send_error(403)
                return
            # Rebuild the request. In particular never forward tools, file references,
            # callbacks, previous_response_id, metadata or caller-selected authentication.
            messages = []
            for msg in obj['input']:
                if msg.get('role') not in ('system', 'developer', 'user', 'assistant'):
                    continue
                content = msg.get('content')
                if isinstance(content, list):
                    content = '\n'.join(x['text'] for x in content if x.get('type') in ('input_text', 'output_text'))
                if isinstance(content, str):
                    messages.append({'role': msg['role'], 'content': content})
            clean = dict(model=self.server.model, instructions=str(obj.get('instructions', '')),
                         input=messages, store=False, stream=True, max_output_tokens=16000)
            with self.server.upstream(clean) as response:
                self.send_response(response.status)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                if response.status == 200:
                    remaining = 4000000
                    while remaining and (part := response.read1(min(remaining, 65536))):
                        self.wfile.write(part)
                        remaining -= len(part)
        except (ValueError, TypeError, KeyError, OSError, http.client.HTTPException):
            self.close_connection = True


def model_key():
    try:
        key = (Path(os.environ['CREDENTIALS_DIRECTORY']) / 'openai.key').read_text().strip()
    except (KeyError, OSError):
        raise Unavailable('inference-auth') from None
    if not key:
        raise Unavailable('inference-auth')
    return key


@contextlib.contextmanager
def openai(body):
    key = model_key()
    conn = http.client.HTTPSConnection('api.openai.com', timeout=90)
    try:
        conn.request('POST', '/v1/responses', json.dumps(body),
                     {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        yield conn.getresponse()
    finally:
        conn.close()


class Runner:
    def __init__(self, directory, upstream=openai):
        self.directory = directory
        self.upstream = upstream
        self.model = os.environ.get('SAMWISE_MODEL', 'gpt-5.4')

    def cleanup(self, sweep=True):
        try:
            cmd = ['podman', 'ps', '-aq', '--filter', 'label=' + LABEL]
            ids = subprocess.check_output(cmd, timeout=15, stderr=subprocess.DEVNULL).split()
            if ids:
                subprocess.run(['podman', 'rm', '-f', *ids], check=True, timeout=30,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not sweep:
                return
            for folder in self.directory.glob('relay-*'):
                if not stat.S_ISDIR(folder.lstat().st_mode):
                    continue
                socket = folder / 'model.sock'
                if socket.exists() and stat.S_ISSOCK(socket.lstat().st_mode):
                    socket.unlink()
                folder.rmdir()
        except (OSError, subprocess.SubprocessError):
            raise Unavailable('runner-cleanup') from None

    def run(self, n, mode, payload, extra):
        name = f'samwise-engineering-v1-{n}-{mode}'
        cmd = ['podman', 'run', '--rm', '--pull=never', '--name', name, '--label', LABEL,
               '--network=none', '--http-proxy=false', '--read-only', '--cap-drop=all',
               '--security-opt=no-new-privileges', '--pids-limit=96', '--cpus=1', '--memory=768m',
               '--memory-swap=768m', '--timeout=170', '--log-driver=none', '--userns=keep-id',
               '--user', f'{os.getuid()}:{os.getgid()}', '--tmpfs', '/tmp:rw,nosuid,nodev,size=96m',
               '-e', 'HOME=/tmp/home', '-e', 'CODEX_HOME=/tmp/home/.codex',
               '-v', f'{INSIDE}:/opt/inside.py:ro', *extra, '-i', IMAGE,
               'python', '-I', '/opt/inside.py', mode]
        try:
            # Drain output with a hard memory cap; never copy a candidate's logs to disk.
            with tempfile.TemporaryFile(dir=self.directory) as source:
                source.write(json.dumps(payload).encode())
                source.seek(0)
                proc = subprocess.Popen(cmd, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                output = bytearray()

                def drain():
                    while part := proc.stdout.read(65536):
                        output.extend(part[:max(0, 500001 - len(output))])

                thread = threading.Thread(target=drain, daemon=True)
                thread.start()
                try:
                    proc.wait(timeout=180)
                finally:
                    if proc.poll() is None:
                        proc.kill()
                    proc.wait()
                    thread.join()
                    proc.stdout.close()
                return subprocess.CompletedProcess(cmd, proc.returncode, bytes(output))
        except (OSError, subprocess.SubprocessError):
            raise Unavailable('runner') from None
        finally:
            # --timeout also expires orphaned containers if the supervisor itself is killed.
            self.cleanup(sweep=False)

    def propose(self, n, d, files, feedback):
        if self.upstream is openai:
            model_key()
        binary = Path(os.environ['SAMWISE_CODEX_BINARY']).resolve()
        with binary.open('rb') as f:
            require(hashlib.file_digest(f, 'sha256').hexdigest() == os.environ['SAMWISE_CODEX_SHA256'], 'cli-pin')
        with tempfile.TemporaryDirectory(prefix='relay-', dir=self.directory) as temp:
            socket = Path(temp) / 'model.sock'
            with Relay(socket, self.upstream, self.model) as relay:
                thread = threading.Thread(target=relay.serve_forever, daemon=True)
                thread.start()
                try:
                    res = self.run(n, 'propose', dict(goal=d['goal'], paths=d['paths'], files=files, last=feedback),
                                   ['-v', f'{binary}:/opt/codex:ro', '-v', f'{temp}:/relay:ro',
                                    '-e', 'SAMWISE_MODEL=' + self.model])
                finally:
                    relay.shutdown()
                    thread.join()
        if res.returncode:
            raise Unavailable('inference')
        try:
            return json.loads(res.stdout)
        except ValueError:
            raise Denied('invalid-proposal') from None

    def test(self, n, files):
        res = self.run(n, 'test', files, [])
        if res.returncode in (125, 126, 127):
            raise Unavailable('runner')
        if res.returncode == 0 and res.stdout == b'suite-passed':
            return 'passed'
        if res.returncode == 1 and len(res.stdout) < 160:
            detail = res.stdout.decode('ascii', errors='replace')
            match = re.fullmatch(r'(engineering/[a-z0-9_/]+\.py)@([1-9][0-9]{0,5})', detail)
            if match and match[1] in files:
                return 'offline-test-failure ' + detail
        return 'offline-test-failure'
