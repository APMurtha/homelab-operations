"""Opt-in owner-signed operations grants received on one enrolled GitHub issue."""
import argparse
import base64
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from github import Denied, OWNER, REPO, REPO_ID, Unavailable, require, sha
from operations import OperationsGithub, advance, collect, enrollment
from ops_protocol import decode
from worker import Store

DOMAIN = 'samwise-operations-single-v1'
PREFIX = DOMAIN + '\n'
MARKER = 'Samwise operations single-submission inbox v1'
LABEL = 'samwise:operations-v1-ready'
POLICY = Path('/etc/samwise/operations-v1/single-submission.json')
GRAPH = ('query($id:ID!){node(id:$id){__typename ... on IssueComment{'
         'id fullDatabaseId body lastEditedAt createdAt author{... on User{databaseId}} '
         'issue{fullDatabaseId number repository{databaseId}}}}}')


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def positive(value):
    return type(value) is int and 0 < value < 2**63


def policy(obj):
    require(type(obj) is dict and set(obj) == {'issue','issue_id','label_id','event','key'}, 'inbox-policy')
    require(all(positive(obj[k]) for k in ('issue','issue_id','label_id','event')), 'inbox-policy')
    require(type(obj['key']) is str and re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/]{68}', obj['key']), 'signer')
    blob = base64.b64decode(obj['key'].split()[1], validate=True)
    require(len(blob)==51 and blob[:19]==b'\0\0\0\x0bssh-ed25519\0\0\0 ', 'signer')
    return obj


def enrolled():
    for path in (POLICY, *POLICY.parents):
        info = path.lstat()
        kind = stat.S_ISREG if path == POLICY else stat.S_ISDIR
        require(kind(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022, 'inbox-policy')
    require(POLICY.stat().st_nlink == 1 and POLICY.stat().st_size <= 2048, 'inbox-policy')
    p = policy(decode(POLICY.read_bytes()))
    require(p['key'] != 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINdamAGCsQq31Uv+08lkBzoO4XLz2qYjJa8CGmj3B1Ea',
            'public-test-vector')
    return p


def context(p):
    return dict(protocol=DOMAIN, repository=REPO, repository_id=REPO_ID, owner_id=OWNER,
                issue=p['issue'], issue_id=p['issue_id'], label_id=p['label_id'], label_event=p['event'])


def verify(key, message, signature):
    require(type(signature) is str and len(signature)<=1024 and signature.isascii(), 'signature')
    with tempfile.TemporaryDirectory() as t:
        signers, sig = Path(t)/'allowed', Path(t)/'signature'
        signers.write_text('owner '+key+'\n')
        sig.write_text(signature)
        try:
            r = subprocess.run(['/usr/bin/ssh-keygen','-Y','verify','-f',str(signers),'-I','owner',
                                '-n',DOMAIN,'-s',str(sig)], input=message.encode(), stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=3, env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
        except (OSError, subprocess.TimeoutExpired):
            raise Unavailable('verifier') from None
        require(r.returncode==0, 'signature')


def timestamp(value):
    try:
        return int(datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp())
    except (TypeError, ValueError, OverflowError):
        raise Denied('event-time') from None


class Inbox(OperationsGithub):
    hostname = 'github.com'

    def __init__(self, pin, p, read_policy=None, read_pin=None):
        super().__init__(pin)
        self.p = policy(p)
        self.read_pin = read_pin
        self.read_policy = read_policy
        self.remaining = 64

    def api(self, path, method='GET', data=None):
        if self.remaining <= 0:
            raise Unavailable('github-budget')
        self.remaining -= 1
        return super().api(path, method, data)

    def recent(self):
        # Five-minute maximum grant, two seconds of timestamp granularity margin.
        since = datetime.fromtimestamp(time.time()-302,timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        return self.pages(f'issues/{self.p["issue"]}/comments?since={since}')

    def submissions(self):
        rows = list(self.recent())
        for c in rows:
            if c['user']['id']==OWNER and isinstance(c['body'],str):
                match = re.fullmatch('cancel '+DOMAIN+' ([0-9a-f]{64})', c['body'].strip())
                if match:
                    self.store.revoke(match[1])
        return rows

    def payload(self, body):
        require(type(body) is str and len(body)<=4096 and body.startswith(PREFIX),'envelope')
        try:
            env = decode(body[len(PREFIX):])
            require(type(env) is dict and set(env)=={'grant','signature'},'envelope')
            grant = env['grant']
            ctx = context(self.p)
            require(type(grant) is dict and set(grant)==set(ctx)|{'issued','nonce','task','digest'}
                    and all(type(grant[k]) is type(v) and grant[k]==v for k,v in ctx.items()), 'context')
            require(type(grant['nonce']) is str and re.fullmatch('[0-9a-f]{64}',grant['nonce']), 'nonce')
            task = self.parse_spec(canonical(grant['task']))
            require(sha(canonical(task))==grant['digest'],'task-digest')
            require(positive(grant['issued']) and grant['issued']<=time.time()<task['expires']
                    and task['expires']-grant['issued']<=300,'expiry')
            verify(self.p['key'],canonical(grant),env['signature'])
        except (TypeError, ValueError, KeyError, RecursionError):
            raise Denied('envelope') from None
        return grant, task

    def candidates(self):
        self.anchor()
        found = []
        for c in self.submissions():
            if (c['user']['id'] != OWNER or not positive(c['id']) or not isinstance(c['body'],str)
                    or not c['body'].startswith(PREFIX) or self.store.get(c['id']) is not None):
                continue
            try:
                grant, _ = self.payload(c['body'])
            except Denied:
                continue
            if not self.store.consumed(grant['nonce']):
                found.append(c['id'])
        return found

    def anchor(self):
        if self.read_pin is not None:
            require(self.read_pin() == self.pin, 'host-policy')
        if self.read_policy is not None:
            require(self.read_policy() == self.p, 'authorization-changed')
        self.identity()
        n = self.p['issue']
        i = self.get(f'issues/{n}')
        require(i['number']==n and i['id']==self.p['issue_id'] and i['state']=='open'
                and 'pull_request' not in i and i['user']['id']==OWNER and i['body']==MARKER
                and any(l['name']==LABEL and l['id']==self.p['label_id'] for l in i['labels']), 'inactive')
        response = self.api('graphql','POST',{'query':
            'query($id:ID!){node(id:$id){... on Issue{fullDatabaseId body lastEditedAt repository{databaseId}}}}',
            'variables':{'id':i['node_id']}})
        graph = (response.get('data') or {}).get('node')
        require(not response.get('errors') and graph and graph['fullDatabaseId']==str(self.p['issue_id']) and graph['body']==MARKER and
                graph['lastEditedAt'] is None and graph['repository']['databaseId']==REPO_ID, 'edited')
        events = list(self.pages(f'issues/{n}/events'))
        require(not any(e['event'] in ('closed','reopened','transferred') for e in events), 'inactive')
        epochs = [e for e in events if e['event'] in ('labeled','unlabeled') and e['label']['name']==LABEL]
        require(len(epochs)==1 and epochs[0]['id']==self.p['event'] and epochs[0]['event']=='labeled'
                and epochs[0]['actor']['id']==OWNER, 'ready')
        return timestamp(epochs[0]['created_at'])

    def authorization(self, n, challenge=False):
        epoch = self.anchor()
        c = self.get(f'issues/comments/{n}')
        require(c['id']==n and c['user']['id']==OWNER and c['created_at']==c['updated_at']
                and c['issue_url']==f'https://api.github.com/repos/{REPO}/issues/{self.p["issue"]}', 'inactive')
        g = self.api('graphql','POST',{'query':GRAPH,'variables':{'id':c['node_id']}})
        node = (g.get('data') or {}).get('node')
        require(not g.get('errors') and node and node['__typename']=='IssueComment' and
                node['id']==c['node_id'] and node['fullDatabaseId']==str(n) and node['author']['databaseId']==OWNER
                and node['issue']==dict(fullDatabaseId=str(self.p['issue_id']),number=self.p['issue'],
                                        repository=dict(databaseId=REPO_ID)) and node['lastEditedAt'] is None
                and node['createdAt']==c['created_at'] and node['body']==c['body'], 'authorization-changed')
        body = c['body']
        grant, task = self.payload(body)
        created = timestamp(c['created_at'])
        require(epoch<=grant['issued']<=created<=time.time()<task['expires'],'expiry')
        self.submissions()
        require(not self.store.revoked(grant['nonce']), 'cancelled')
        return task, [sha(body),self.p['event'],n,grant['nonce'],sha(self.p['key'])]

    def reports(self, n, body):
        return [c['id'] for c in self.recent() if c['user']['id']==OWNER and c['body']==body
                and c['created_at']==c['updated_at']]


class InboxStore(Store):
    def __init__(self, directory):
        super().__init__(directory)
        self.db.execute('CREATE TABLE IF NOT EXISTS grants(nonce TEXT PRIMARY KEY, submission INTEGER UNIQUE NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS revoked(nonce TEXT PRIMARY KEY)')

    def revoke(self, nonce):
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO revoked VALUES(?)',(nonce,))

    def revoked(self, nonce):
        return self.db.execute('SELECT 1 FROM revoked WHERE nonce=?',(nonce,)).fetchone() is not None

    def consumed(self, nonce):
        return self.revoked(nonce) or self.db.execute('SELECT 1 FROM grants WHERE nonce=?',(nonce,)).fetchone() is not None

    def claim(self, n, t):
        try:
            with self.db:
                inserted = self.db.execute('INSERT INTO grants SELECT ?,? WHERE NOT EXISTS '
                                           '(SELECT 1 FROM revoked WHERE nonce=?)',(t['proof'][3],n,t['proof'][3]))
                if inserted.rowcount != 1:
                    return False
                self.db.execute('INSERT INTO tasks VALUES(?,?)',(n,json.dumps(t)))
                self.db.execute('INSERT INTO receipts VALUES(?,?,?,0)',(n,int(time.time()),'claimed'))
        except sqlite3.IntegrityError:
            return False
        return True


def poll(directory, api=None, observe=collect):
    directory = directory / DOMAIN
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (directory/'lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if api is None:
            api = Inbox(enrollment()[0],enrolled(),read_policy=enrolled,read_pin=lambda: enrollment()[0])
        store = InboxStore(directory)
        api.store = store
        try:
            def run(n):
                try:
                    advance(n,api,store,observe,claim=store.claim,issue=api.p['issue'])
                except (KeyError,TypeError,ValueError):
                    raise Unavailable('provider-response') from None
            for n in store.pending():
                run(n)
            for n in api.candidates():
                if store.get(n) is None:
                    run(n)
        finally:
            store.db.close()


def enabled_tick(directory):
    if (os.environ.get('SAMWISE_OPERATIONS_V1') == 'enabled' and
            os.environ.get('SAMWISE_OPERATIONS_SINGLE') == 'enabled'):
        require(os.getuid() != 0, 'requires-unprivileged-user')
        os.umask(0o077)
        poll(directory)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    try:
        enabled_tick(args.state.resolve())
    except (Denied, Unavailable, OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        sys.exit('single-submission dependency or policy check failed')
