"""Authenticated control plane. Never run Git hooks or check out issue-controlled paths."""
import base64
import hashlib
import json
import re
import subprocess
from urllib.parse import urlencode

REPO = 'APMurtha/homelab-operations'
OWNER = 57697374
REPO_ID = 1126036330
LABEL = 'samwise:engineering-v1-ready'
PREFIX = 'samwise/engineering-v1-'
MAX_FILE = 32000
PATH = re.compile(r'engineering/(?:[a-z][a-z0-9_]{0,47}/){0,2}[a-z][a-z0-9_]{0,47}\.py')
SHA = re.compile('[0-9a-f]{40}')


class Denied(Exception):
    """Permanent policy failure or withdrawn authorization."""


class Unavailable(Exception):
    """Control-plane failure, safe to reconcile later."""


def require(ok, reason):
    if not ok:
        raise Denied(reason)


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def spec(body):
    try:
        d = json.loads(body)
        require(set(d) == {'version', 'base', 'goal', 'paths', 'suite'}, 'fields')
        require(d['version'] == 'engineering-v1' and d['suite'] == 'python-unittest', 'version')
        require(SHA.fullmatch(d['base']) and 1 <= len(d['goal'].strip()) <= 4000, 'goal-or-base')
        paths = d['paths']
        require(isinstance(paths, list) and 2 <= len(paths) <= 12, 'scope')
        require(all(PATH.fullmatch(p) for p in paths) and len(set(paths)) == len(paths), 'paths')
        require(any(p.startswith('engineering/test_') and p.count('/') == 1 for p in paths), 'tests')
        return d
    except (TypeError, KeyError, ValueError, AttributeError):
        raise Denied('format') from None


class Github:
    def api(self, path, method='GET', data=None):
        cmd = ['gh', 'api', '--method', method, path]
        if data is not None:
            cmd += ['--input', '-']
        try:
            res = subprocess.run(cmd, input=json.dumps(data).encode() if data is not None else None,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30)
            if res.returncode:
                raise Unavailable('github')
            return json.loads(res.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            raise Unavailable('github') from None

    def get(self, path, *args):
        return self.api(f'repos/{REPO}/{path}', *args)

    def pages(self, path):
        sep = '&' if '?' in path else '?'
        for page in range(1, 12):
            rows = self.get(f'{path}{sep}per_page=100&page={page}')
            yield from rows
            if len(rows) < 100:
                return
        raise Unavailable('pagination-limit')

    def identity(self):
        require(self.api('user')['id'] == OWNER, 'control-identity')
        r = self.api('repos/' + REPO)
        require((r['id'], r['owner']['id'], r['full_name'], r['default_branch']) ==
                (REPO_ID, OWNER, REPO, 'main'), 'repository')

    def candidates(self):
        self.identity()
        return [i['number'] for i in self.pages('issues?' + urlencode({'labels': LABEL, 'state': 'open'}))
                if 'pull_request' not in i and i['user']['id'] == OWNER]

    def authorization(self, n, challenge=False):
        self.identity()
        i = self.get(f'issues/{n}')
        require(i['number'] == n and 'pull_request' not in i and i['state'] == 'open'
                and i['user']['id'] == OWNER and LABEL in [l['name'] for l in i['labels']], 'inactive')
        query = ('query($n:Int!){repository(owner:"APMurtha",name:"homelab-operations")'
                 '{issue(number:$n){body lastEditedAt}}}')
        graph = self.api('graphql', 'POST', {'query': query, 'variables': {'n': n}})
        snapshot = graph['data']['repository']['issue']
        require(snapshot and snapshot['lastEditedAt'] is None and snapshot['body'] == i['body'], 'edited')
        d = spec(i['body'])
        events = [e for e in self.pages(f'issues/{n}/events')
                  if e['event'] in ('labeled', 'unlabeled') and e['label']['name'] == LABEL]
        require(events and events[-1]['event'] == 'labeled' and events[-1]['actor']['id'] == OWNER, 'ready')
        event = events[-1]
        digest = sha(i['body'])
        approval = f'approve engineering-v1 #{n} {event["id"]} {digest} {d["base"]}'
        comments = [c for c in self.pages(f'issues/{n}/comments') if c['user']['id'] == OWNER]
        require(all(c['body'].strip() != f'cancel engineering-v1 #{n}' for c in comments), 'cancelled')
        valid = [c for c in comments if c['body'] == approval and c['updated_at'] == c['created_at']
                 and c['created_at'] >= event['created_at']]
        if not valid and challenge:
            message = ('Samwise engineering approval requested for this immutable issue. '
                       'Reply with the following exact line to authorize up to three attempts.\n\n'
                       + approval)
            if not any(c['body'] == message for c in comments):
                require(self.base() == d['base'], 'base-moved')
                self.get(f'issues/{n}/comments', 'POST', {'body': message})
        require(valid, 'awaiting-approval')
        return d, [digest, event['id'], valid[0]['id']]

    def base(self):
        return self.get('git/ref/heads/main')['object']['sha']

    def files(self, d):
        tree = self.get('git/trees/' + d['base'] + '?recursive=1')
        require(not tree['truncated'], 'truncated-tree')
        entries = {e['path']: e for e in tree['tree']}
        files = {}
        for p in d['paths']:
            parts = p.split('/')
            for k in range(1, len(parts)):
                ancestor = entries.get('/'.join(parts[:k]))
                require(not ancestor or ancestor['type'] == 'tree', 'ancestor')
            if p in entries:
                e = entries[p]
                require(e['mode'] == '100644' and e['type'] == 'blob' and e['size'] <= MAX_FILE, 'blob')
                try:
                    files[p] = base64.b64decode(self.get('git/blobs/' + e['sha'])['content']).decode()
                except (ValueError, UnicodeError):
                    raise Denied('encoding') from None
        return files

    def commit(self, n, d, files):
        tree = self.get('git/trees', 'POST', {'base_tree': self.get('git/commits/' + d['base'])['tree']['sha'],
                        'tree': [{'path': p, 'mode': '100644', 'type': 'blob', 'content': content}
                                 for p, content in sorted(files.items())]})
        return self.get('git/commits', 'POST', {'message': f'Implement approved engineering task #{n}',
                        'tree': tree['sha'], 'parents': [d['base']]})['sha']

    def publish(self, n, commit, authorize):
        branch = PREFIX + str(n)
        refs = self.get('git/matching-refs/heads/' + branch)
        exact = [r for r in refs if r['ref'] == 'refs/heads/' + branch]
        if not exact:
            authorize()
            self.get('git/refs', 'POST', {'ref': 'refs/heads/' + branch, 'sha': commit})
        else:
            require(exact[0]['object']['sha'] == commit, 'branch-conflict')
        prs = list(self.pages('pulls?' + urlencode({'state': 'all', 'head': 'APMurtha:' + branch})))
        if not prs:
            authorize()
            pr = self.get('pulls', 'POST', {'head': branch, 'base': 'main', 'draft': True,
                        'title': f'Implement engineering task #{n}',
                        'body': f'Refs #{n}. The supervisor ran the approved offline Python suite. Review the diff and tests.'})
            prs = [self.get(f'pulls/{pr["number"]}')]
        require(len(prs) == 1, 'pr-conflict')
        p = prs[0]
        require(p['head']['repo']['id'] == REPO_ID and p['head']['ref'] == branch and
                p['head']['sha'] == commit and p['base']['repo']['id'] == REPO_ID and
                p['base']['ref'] == 'main' and p['draft'] and p['state'] == 'open', 'pr-conflict')
        return p['number']
