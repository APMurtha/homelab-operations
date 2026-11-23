"""Read-only capability for the existing Samwise tick. No model, code checkout or shell."""
import base64
import hashlib
import json
import os
import selectors
import stat
import subprocess
import tempfile
import time
from pathlib import Path

from github import Denied, Github, OWNER, SHA, Unavailable, require
from ops_protocol import MAX_REPLY, TAG, TARGET, decode, observations, reply

ADDRESS = '10.10.20.30'
HOSTS = Path('/etc/samwise/operations-v1/known_hosts')
VERSION = 'operations-v1'
CANCEL = {'inactive', 'cancelled', 'ready', 'authorization-changed', 'awaiting-approval'}


def enrollment():
    # This file is deliberately outside the service account's writable checkout.
    for path in (HOSTS, *HOSTS.parents):
        info = path.lstat()
        kind = stat.S_ISREG if path == HOSTS else stat.S_ISDIR
        require(kind(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022, 'host-policy')
    require(HOSTS.stat().st_size <= 512, 'host-policy')
    return parse_enrollment(HOSTS.read_bytes())


def parse_enrollment(record):
    fields = record.split()
    require(len(fields) == 3 and fields[:2] == [ADDRESS.encode(), b'ssh-ed25519'], 'host-policy')
    try:
        key = base64.b64decode(fields[2], validate=True)
    except ValueError:
        raise Denied('host-policy') from None
    require(len(key) == 51 and key[:19] == b'\0\0\0\x0bssh-ed25519\0\0\0 ', 'host-policy')
    pin = 'SHA256:' + base64.b64encode(hashlib.sha256(key).digest()).decode().rstrip('=')
    return pin, b' '.join(fields) + b'\n'


class OperationsGithub(Github):
    version = VERSION
    label = 'samwise:operations-v1-ready'
    challenge_intro = ('Read-only Dispatcharr observations requested. Check the target fingerprint, '
                       'observation list, attempts, per-attempt limits and UTC expiration in the issue. '
                       'Reply with this exact line to authorize collection and a public status report.')

    def __init__(self, pin):
        self.pin = pin

    def parse_spec(self, body):
        try:
            require(isinstance(body, str) and len(body) <= 2048, 'spec-size')
            d = decode(body)
            require(type(d) is dict and set(d) == {'version', 'target', 'host_key', 'base', 'observations',
                    'seconds', 'bytes', 'attempts', 'expires'}, 'fields')
            require(d['version'] == VERSION and d['target'] == TARGET and d['host_key'] == self.pin, 'target')
            require(isinstance(d['base'], str) and SHA.fullmatch(d['base']), 'base')
            observations(d['observations'])
            for k, lo, hi in [('seconds', 1, 20), ('bytes', 256, MAX_REPLY), ('attempts', 1, 2)]:
                require(type(d[k]) is int and lo <= d[k] <= hi, 'limits')
            require(type(d['expires']) is int and time.time() < d['expires'] <= time.time()+3600, 'expiry')
            return d
        except (TypeError, ValueError, KeyError):
            raise Denied('operations-spec') from None

    def reports(self, n, body):
        return [c['id'] for c in self.pages(f'issues/{n}/comments') if c['user']['id'] == OWNER
                and c['body'] == body and c['created_at'] == c['updated_at']]


def ssh_argv(key, hosts):
    options = ['BatchMode=yes', 'IdentitiesOnly=yes', 'IdentityAgent=none', 'StrictHostKeyChecking=yes',
               f'UserKnownHostsFile={hosts}', 'GlobalKnownHostsFile=/dev/null', 'UpdateHostKeys=no', 'VerifyHostKeyDNS=no',
               'HostKeyAlgorithms=ssh-ed25519', 'PreferredAuthentications=publickey', 'ControlMaster=no',
               'ControlPath=none', 'ForwardAgent=no', 'ClearAllForwardings=yes', 'ForwardX11=no',
               'PermitLocalCommand=no', 'ProxyCommand=none', 'ConnectionAttempts=1', 'ConnectTimeout=5']
    return ['/usr/bin/ssh', '-F', '/dev/null', '-T', '-i', str(key),
            *(arg for opt in options for arg in ('-o', opt)), 'samwise-observe@' + ADDRESS, TAG]


def exchange(cmd, request, seconds, limit):
    deadline = time.monotonic() + seconds
    try:
        with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}, bufsize=0) as p:
            try:
                p.stdin.write(request)
                p.stdin.close()
                data = bytearray()
                with selectors.DefaultSelector() as wait:
                    wait.register(p.stdout, selectors.EVENT_READ)
                    while True:
                        left = deadline - time.monotonic()
                        if left <= 0 or not wait.select(left):
                            raise Unavailable('collector-timeout')
                        chunk = os.read(p.stdout.fileno(), limit + 1 - len(data))
                        if not chunk:
                            break
                        data.extend(chunk)
                        require(len(data) <= limit, 'reply-size')
                if p.wait(timeout=max(0, deadline-time.monotonic())):
                    raise Unavailable('collector-unavailable')
                return bytes(data)
            finally:
                if p.poll() is None:
                    p.kill()
                p.wait()
    except (OSError, subprocess.TimeoutExpired):
        raise Unavailable('collector-unavailable') from None


def collect(d):
    pin, record = enrollment()
    require(pin == d['host_key'], 'host-policy')
    cred = os.environ.get('CREDENTIALS_DIRECTORY')
    require(cred and Path(cred).is_absolute(), 'identity')
    key = Path(cred) / 'ops-ssh.key'
    info = key.lstat()
    require(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o077 and info.st_uid in (0, os.getuid()), 'identity')
    remaining = min(d['seconds'], d['expires'] - time.time())
    require(remaining > 0, 'expiry')
    # Bind this connection to the verified bytes even if an administrator rotates the enrollment.
    with tempfile.TemporaryDirectory(prefix='samwise-host-') as temp:
        hosts = Path(temp) / 'known_hosts'
        hosts.write_bytes(record)
        return exchange(ssh_argv(key, hosts), json.dumps({'observations': d['observations']}).encode(),
                        remaining, d['bytes'])


def report(n, t):
    rows = '\n'.join(f'- {k}: {v}' for k, v in t['result'].items())
    return (f'Samwise read-only report for #{n} ({TARGET})\n\n{rows}\n\n'
            f'Collected at Unix time {t["observed"]}. Approval body SHA-256: {t["proof"][0]}.')


def advance(n, api, store, observe=collect):
    t = store.get(n)
    if t and t['phase'] in ('published', 'escalated', 'cancelled'):
        return

    def authorized():
        d, proof = api.authorization(n, challenge=t is None)
        require(t is None or (d == t['spec'] and proof == t['proof']), 'authorization-changed')
        require(api.base() == d['base'], 'base-moved')
        require(time.time() < d['expires'], 'expiry')
        return d, proof

    def save(phase, reason):
        t.update(phase=phase, last=reason)
        store.save(n, t, reason)

    try:
        d, proof = authorized()
        if t is None:
            t = dict(spec=d, proof=proof, attempt=0, outages=0)
            save('collect', 'claimed')
        if t['phase'] == 'collect':
            require(t['attempt'] < d['attempts'], 'attempt-budget')
            t['attempt'] += 1
            save('collect', 'read-started')
            raw = observe(d)
            require(len(raw) <= d['bytes'], 'reply-size')
            try:
                t['result'] = reply(raw, d['observations'])
            except ValueError:
                raise Denied('reply-invalid') from None
            t['observed'] = int(time.time())
            require(t['observed'] < d['expires'], 'expiry')
            save('report', 'validated-observations')

        body = report(n, t)
        authorized()
        found = api.reports(n, body)
        if not found and t['phase'] == 'report':
            authorized()
            save('posting', 'report-intent')
            api.get(f'issues/{n}/comments', 'POST', {'body': body})
            found = api.reports(n, body)
        if not found:
            raise Unavailable('report-uncertain')
        require(len(found) == 1, 'report-conflict')
        t['comment'] = found[0]
        save('published', 'report-verified')
    except Denied as e:
        if t:
            save('cancelled' if str(e) in CANCEL else 'escalated', str(e))
    except (Unavailable, OSError):
        if t:
            t['outages'] += 1
            terminal = (time.time() >= t['spec']['expires'] or t['outages'] >= 6 or
                        (t['phase'] == 'collect' and t['attempt'] >= t['spec']['attempts']))
            save('escalated' if terminal else t['phase'], 'dependency-unavailable')


def poll(directory, store_factory):
    try:
        pin, _ = enrollment()
    except (OSError, Denied):
        raise Denied('operations-enrollment') from None
    api = OperationsGithub(pin)
    store = store_factory(directory / VERSION)
    try:
        for n in store.pending():
            advance(n, api, store)
        for n in api.candidates():
            if store.get(n) is None:
                advance(n, api, store)
    finally:
        store.db.close()
