"""One polling cycle per invocation. The systemd timer drives this after logout/reboot."""
import argparse
import fcntl
import json
import os
import sqlite3
import time
from pathlib import Path

from github import Denied, Github, MAX_FILE, Unavailable, require
from runner import Runner

MAX_ATTEMPTS = 3
MAX_OUTAGES = 12
DEADLINE = 3600
TERMINAL = {'published', 'escalated', 'cancelled'}


class Store:
    def __init__(self, directory):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.db = sqlite3.connect(directory / 'state.sqlite3')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS tasks (issue INTEGER PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS receipts (issue INTEGER, stamp INTEGER, event TEXT, attempt INTEGER);
        ''')

    def get(self, n):
        row = self.db.execute('SELECT data FROM tasks WHERE issue=?', (n,)).fetchone()
        return json.loads(row[0]) if row else None

    def pending(self):
        return [n for n, in self.db.execute('SELECT issue FROM tasks ORDER BY issue')
                if self.get(n)['phase'] not in TERMINAL]

    def save(self, n, t, event):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO tasks VALUES (?, ?)', (n, json.dumps(t)))
            self.db.execute('INSERT INTO receipts VALUES (?, ?, ?, ?)',
                            (n, int(time.time()), event, t['attempt']))
        print(f'issue={n} event={event} attempt={t["attempt"]}', flush=True)


def check_proposal(d, old, proposed):
    require(isinstance(proposed, dict) and proposed and set(proposed) <= set(d['paths']), 'scope')
    for data in proposed.values():
        require(isinstance(data, str) and len(data.encode()) <= MAX_FILE and '\0' not in data, 'content')
    files = old | proposed
    require(files != old, 'empty-change')
    require(any(p.startswith('engineering/test_') and files.get(p) != old.get(p) for p in files), 'test-change')
    require(any(not p.startswith('engineering/test_') and files.get(p) != old.get(p) for p in files), 'code-change')
    return files


def advance(n, api, runner, store, now=time.time):
    t = store.get(n)
    if t and t['phase'] in TERMINAL:
        return

    def authorized():
        d, proof = api.authorization(n, challenge=t is None)
        require(t is None or (proof == t['proof'] and d == t['spec']), 'authorization-changed')
        require(api.base() == d['base'], 'base-moved')
        if t:
            require(now() < t['expires'], 'expired')
        return d, proof

    def save(phase, event):
        t['phase'] = phase
        t['last'] = event
        store.save(n, t, event)

    try:
        d, proof = authorized()
        if t is None:
            t = dict(spec=d, proof=proof, attempt=0, outages=0, expires=int(now()) + DEADLINE)
            save('generate', 'claimed')
        if t['phase'] == 'generate':
            if t['attempt'] >= MAX_ATTEMPTS:
                save('escalated', 'attempt-budget')
                return
            old = api.files(d)
            t['attempt'] += 1
            store.save(n, t, 'attempt-start')
            proposed = runner.propose(n, d, t.get('candidate', old), t.get('feedback', 'initial'))
            t['candidate'] = check_proposal(d, old, proposed)
            save('test', 'proposal-checkpoint')
        if t['phase'] == 'test':
            authorized()
            result = runner.test(n, t['candidate'])
            if result == 'passed':
                original = api.files(d)
                locked = {p: v for p, v in original.items() if p.startswith('engineering/test_')}
                if locked:
                    result = runner.test(n, t['candidate'] | locked)
            if result != 'passed':
                t['feedback'] = result
                save('generate' if t['attempt'] < MAX_ATTEMPTS else 'escalated', 'offline-test-failure')
                return
            save('commit', 'offline-tests-passed')
        if t['phase'] == 'commit':
            authorized()
            t['commit'] = api.commit(n, d, t['candidate'])
            save('publish', 'commit-checkpoint')
        if t['phase'] == 'publish':
            t['pr'] = api.publish(n, t['commit'], authorized)
            save('published', 'draft-verified')
    except Denied as e:
        if t:
            save('cancelled' if str(e) in ('inactive', 'cancelled', 'authorization-changed',
                 'awaiting-approval', 'ready') else 'escalated', str(e))
    except Unavailable:
        if t:
            t['outages'] += 1
            save('escalated' if t['outages'] >= MAX_OUTAGES or now() >= t['expires']
                 else t['phase'], 'dependency-unavailable')


def tick(directory):
    if os.getuid() == 0:
        raise Denied('requires-unprivileged-user')
    os.umask(0o077)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / 'lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        api, runner, store = Github(), Runner(directory), Store(directory)
        try:
            runner.cleanup()
            for n in store.pending():
                advance(n, api, runner, store)
            for n in api.candidates():
                if store.get(n) is None:
                    advance(n, api, runner, store)
        finally:
            store.db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    try:
        tick(args.state.resolve())
    except (Unavailable, Denied):
        raise SystemExit('supervisor dependency or identity check failed') from None
