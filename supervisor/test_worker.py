import fcntl
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from github import Denied, Github, LABEL, OWNER, PREFIX, REPO_ID, Unavailable, sha, spec
from worker import Store, advance, check_proposal, tick

BASE = 'a' * 40
COMMIT = 'b' * 40
CODE = 'engineering/measure.py'
TEST = 'engineering/test_measure.py'
SPEC = dict(version='engineering-v1', base=BASE, goal='Implement a measurement conversion.',
            paths=[CODE, TEST], suite='python-unittest')
BODY = json.dumps(SPEC)
CHANGES = {CODE: 'def triple(n): return n*3', TEST: 'import unittest\nfrom measure import triple\n'
           'class TestMeasure(unittest.TestCase):\n def test_triple(self): self.assertEqual(triple(4),12)'}


class Hub(Github):
    """GitHub transport double. Exercise production identity, claim, commit and PR logic."""
    def __init__(self):
        self.body = BODY
        self.owner = OWNER
        self.edit = None
        self.events = [dict(event='labeled', label=dict(name=LABEL), actor=dict(id=OWNER), id=17, created_at='1')]
        self.comments = [dict(user=dict(id=OWNER), body=f'approve engineering-v1 #8 17 {sha(BODY)} {BASE}',
                              created_at='2', updated_at='2', id=18)]
        self.branch = self.pr = None
        self.fail = None
        self.head = BASE
        self.entries = []

    def api(self, path, method='GET', data=None):
        if path == 'user':
            return dict(id=OWNER)
        if path == 'graphql':
            return {'data': {'repository': {'issue': {'body': self.body, 'lastEditedAt': self.edit}}}}
        return dict(id=REPO_ID, owner=dict(id=OWNER), full_name='APMurtha/homelab-operations', default_branch='main')

    def get(self, path, method='GET', data=None):
        if path == 'issues/8':
            return dict(number=8, state='open', user=dict(id=self.owner), labels=[dict(name=LABEL)], body=self.body)
        if path.startswith('issues/8/events?'):
            return self.events
        if path.startswith('issues/8/comments?'):
            return self.comments
        if path == 'issues/8/comments' and method == 'POST':
            comment = dict(data, user=dict(id=OWNER), id=20, created_at='2', updated_at='2')
            self.comments.append(comment)
            return comment
        if path == 'git/ref/heads/main':
            return {'object': {'sha': self.head}}
        if path.startswith('git/trees/') and '?' in path:
            return {'tree': self.entries, 'truncated': False}
        if path.startswith('git/commits/'):
            return {'tree': {'sha': BASE}}
        if path == 'git/trees':
            self.tree = data
            return {'sha': COMMIT}
        if path == 'git/commits':
            return {'sha': COMMIT}
        if path.startswith('git/matching-refs/'):
            return [self.branch] if self.branch else []
        if path == 'git/refs':
            assert self.branch is None
            self.branch = {'ref': data['ref'], 'object': {'sha': data['sha']}}
        elif path.startswith('pulls?'):
            return [self.pr] if self.pr else []
        elif path == 'pulls':
            assert self.pr is None and data['draft']
            self.pr = dict(number=19, head=dict(repo=dict(id=REPO_ID), ref=PREFIX + '8', sha=COMMIT),
                           base=dict(repo=dict(id=REPO_ID), ref='main'), draft=True, state='open')
        elif path != 'pulls/19':
            raise AssertionError(path)
        if path == self.fail:
            self.fail = None
            raise Unavailable()
        return self.pr


class Stub:
    def __init__(self):
        self.results = ['passed']
        self.calls = 0

    def propose(self, *args):
        self.calls += 1
        return CHANGES

    def test(self, *args):
        return self.results.pop(0)


class Workflow(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name)
        self.store = Store(self.path)
        self.addCleanup(lambda: self.store.db.close())
        self.api, self.runner = Hub(), Stub()

    def run_task(self):
        advance(8, self.api, self.runner, self.store)
        return self.store.get(8)

    def test_success_and_replay(self):
        self.assertEqual(self.run_task()['pr'], 19)
        self.assertEqual(self.run_task()['phase'], 'published')
        self.assertEqual(self.runner.calls, 1)

    def test_ambiguous_publication_survives_restart(self):
        for endpoint in ['git/refs', 'pulls']:
            with self.subTest(endpoint=endpoint):
                self.store.db.execute('DELETE FROM tasks')
                self.api = Hub()
                self.api.fail = endpoint
                self.runner = Stub()
                self.assertEqual(self.run_task()['phase'], 'publish')
                self.store.db.close()
                self.store = Store(self.path)
                self.assertEqual(self.run_task()['phase'], 'published')
                self.assertEqual(self.runner.calls, 1)

    def test_repeat_failures_escalate(self):
        self.runner.results = ['offline-test-failure'] * 3
        for phase in ['generate', 'generate', 'escalated', 'escalated']:
            self.assertEqual(self.run_task()['phase'], phase)
        self.assertIsNone(self.api.branch)

    def test_loss_of_approval_after_test(self):
        def test(*args):
            self.api.comments.clear()
            return 'passed'
        self.runner.test = test
        self.assertEqual(self.run_task()['phase'], 'cancelled')
        self.assertIsNone(self.api.branch)

    def test_base_moves_after_first_attempt(self):
        self.runner.results = ['offline-test-failure']
        self.run_task()
        self.api.head = COMMIT
        self.assertEqual(self.run_task()['last'], 'base-moved')

    def test_collision(self):
        self.api.branch = {'ref': 'refs/heads/' + PREFIX + '8', 'object': {'sha': BASE}}
        self.assertEqual(self.run_task()['last'], 'branch-conflict')
        self.assertIsNone(self.api.pr)

    def test_wrong_identity_edit_event_and_cancel(self):
        mutations = [lambda h: setattr(h, 'owner', 1), lambda h: setattr(h, 'edit', '3'),
                     lambda h: h.events[-1]['actor'].update(id=1),
                     lambda h: h.events[-1].update(id=4), lambda h: h.comments[-1].update(updated_at='3'),
                     lambda h: h.comments[-1].update(body='cancel engineering-v1 #8')]
        for modify in mutations:
            h = Hub()
            modify(h)
            with self.assertRaises(Denied):
                h.authorization(8)

    def test_scope_and_suite(self):
        for name in ['../secret.py', 'engineering/../x.py', '.github/workflows/edit.py',
                     'engineering/x.sh', 'supervisor/github.py', 'engineering/a;sh.py']:
            with self.assertRaises(Denied):
                spec(json.dumps(SPEC | {'paths': [TEST, name]}))
        with self.assertRaises(Denied):
            spec(json.dumps(SPEC | {'suite': 'sh -c foo'}))
        for proposed in [{TEST: 'x'}, {CODE: 'x'}, CHANGES | {'outside': 'x'}, CHANGES | {CODE: 'a'*32001}]:
            with self.assertRaises(Denied):
                check_proposal(SPEC, {}, proposed)

    def test_connector_approval_challenge_is_idempotent(self):
        self.api.comments.clear()
        for _ in range(2):
            self.assertIsNone(self.run_task())
        self.assertEqual(len(self.api.comments), 1)
        prompt = self.api.comments[0]
        self.api.comments.append(dict(prompt, id=21, body=prompt['body'].splitlines()[-1]))
        self.assertEqual(self.run_task()['proof'][2], 21)

    def test_concurrent_tick_never_starts_a_second_runner(self):
        with (self.path / 'lock').open('a') as lock, patch('worker.Runner') as runner:
            fcntl.flock(lock, fcntl.LOCK_EX)
            tick(self.path)
            runner.assert_not_called()

    def test_preexisting_closed_pr_never_reopens(self):
        self.api.fail = 'pulls'
        self.assertEqual(self.run_task()['phase'], 'publish')
        self.api.pr['state'] = 'closed'
        self.assertEqual(self.run_task()['last'], 'pr-conflict')

    def test_existing_tests_also_run_with_original_bytes(self):
        prior = {CODE: 'previous implementation', TEST: 'original test'}
        observed = []
        def test(n, files):
            observed.append(files[TEST])
            return 'passed' if len(observed) == 1 else 'offline-test-failure'
        with patch.object(self.api, 'files', return_value=prior):
            self.runner.test = test
            self.assertEqual(self.run_task()['phase'], 'generate')
        self.assertEqual(observed, [CHANGES[TEST], prior[TEST]])
        self.assertIsNone(self.api.branch)

    def test_expiration_is_terminal(self):
        self.runner.results = ['offline-test-failure']
        original = self.run_task()
        advance(8, self.api, self.runner, self.store, lambda: original['expires'])
        self.assertEqual(self.store.get(8)['last'], 'expired')
        self.assertEqual(self.runner.calls, 1)

    def test_outage_budget_survives_restarts(self):
        self.api.fail = 'git/refs'
        self.assertEqual(self.run_task()['outages'], 1)
        with patch.object(self.api, 'authorization', side_effect=Unavailable):
            for _ in range(11):
                self.run_task()
        self.assertEqual(self.store.get(8)['phase'], 'escalated')
        self.assertIsNone(self.api.pr)

    def test_untrusted_actor_cannot_approve(self):
        self.api.comments[0]['user']['id'] = 9
        with self.assertRaises(Denied):
            self.api.authorization(8)

    def test_symlink_and_submodule(self):
        for path, mode, kind in [(CODE, '120000', 'blob'), ('engineering', '160000', 'commit')]:
            self.api.entries = [dict(path=path, type=kind, mode=mode, size=10)]
            with self.assertRaises(Denied):
                self.api.files(SPEC)


if __name__ == '__main__':
    unittest.main()
