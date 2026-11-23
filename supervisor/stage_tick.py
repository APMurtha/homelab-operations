"""Staging-only ExecStart override. Durable GitHub double and scripted model transport.

Uses the production tick, locking, SQLite, CLI, relay and test runner. Never reads real
GitHub or OpenAI credentials. Install only under a dedicated staging account.
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

from runner import Runner
from test_isolation import scripted_response
from test_worker import Hub
from worker import tick


class StageHub(Hub):
    def __init__(self, directory):
        super().__init__()
        self.path = directory / 'remote.json'
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.branch, self.pr, self.fail = data
        else:
            self.fail = 'pulls'

    def candidates(self):
        return [8]

    def get(self, *args):
        try:
            return super().get(*args)
        finally:
            tmp = self.path.with_suffix('.new')
            tmp.write_text(json.dumps([self.branch, self.pr, self.fail]))
            tmp.replace(self.path)


if __name__ == '__main__':
    os.umask(0o077)
    root = Path.home() / 'accept' / 'timer-state'
    root.mkdir(exist_ok=True)
    def upstream(body):
        counter = root / 'model-calls'
        attempt = int(counter.read_text()) + 1 if counter.exists() else 1
        counter.write_text(str(attempt))
        return scripted_response(body, attempt)

    with patch('worker.Github', lambda: StageHub(root)), patch('worker.Runner', lambda p: Runner(p, upstream)):
        tick(root)
