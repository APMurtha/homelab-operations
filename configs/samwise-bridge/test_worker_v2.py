"""Offline authorization, receipt and recovery tests against a simulated GitHub."""
from copy import deepcopy
import hashlib
import json
import sqlite3
import unittest
from unittest.mock import patch

import worker as fixture
import worker_v2 as bridge

NUMBER = 25
SHA = "a" * 40
STAMP = "2026-11-18T12:00:00Z"
IMAGE = "sha256:" + "1" * 64
PATH = f"{fixture.REPO}/issues/{NUMBER}"
BODY = "samwise-task-v2:" + json.dumps({"kind": "repo-inventory", "revision": 1, "commit": SHA})


class GitHub:
    def __init__(self):
        self.owner = fixture.OWNER
        self.repo = bridge.REPO_ID
        self.issue = {"number": NUMBER, "state": "open", "user": {"id": self.owner},
                      "updated_at": STAMP, "body": BODY, "labels": [{"name": fixture.READY}]}
        self.events = [{"id": 10, "event": "labeled", "actor": {"id": self.owner},
                        "created_at": STAMP, "label": {"name": fixture.READY}}]
        self.comments = [{"id": 11, "user": {"id": self.owner}, "created_at": STAMP,
                          "updated_at": STAMP, "body": f"samwise-approve-v2: 10 "
                          + hashlib.sha256(BODY.encode()).hexdigest()}]
        self.after_claim = lambda: None

    def get(self, path):
        if path == PATH:
            return deepcopy(self.issue)
        if path == "user":
            return {"id": self.owner}
        if path == fixture.REPO:
            return {"id": self.repo}
        if path.startswith(f"{PATH}/events?"):
            return deepcopy(self.events)
        if path.startswith(f"{PATH}/comments?"):
            return deepcopy(self.comments)
        raise AssertionError(path)

    def label(self, number, name, **kwargs):
        self.issue["labels"].append({"name": name})
        if name == fixture.RUNNING:
            self.after_claim()


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.github = GitHub()
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE receipts (issue INTEGER PRIMARY KEY, "
                        "result TEXT, updated TEXT, published INTEGER)")
        self.mock(fixture, "gh", self.github.get)
        self.mock(bridge.publisher, "gh", self.github.get)
        self.mock(fixture, "label", self.github.label)
        self.mock(fixture, "cycle", return_value=False)
        self.source = self.mock(bridge, "verify_source")
        self.job = self.mock(bridge.runner, "inventory", return_value={"files": 5, "focus": "code"})
        self.publication = self.mock(bridge.publisher, "publish", side_effect=self.publish)

    def mock(self, module, name, *args, **kwargs):
        patcher = patch.object(module, name, *args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def publish(self, db, number, result, updated, report):
        with db:
            db.execute("UPDATE receipts SET published=1 WHERE issue=?", (number,))

    def run_cycle(self):
        return bridge.cycle(self.db, NUMBER, image=IMAGE)

    def result(self):
        return self.db.execute("SELECT result FROM receipts").fetchone()

    def test_success_and_replay_after_label_removal(self):
        self.assertTrue(self.run_cycle())
        self.assertEqual(self.result(), ("passed",))
        self.assertEqual(self.job.call_args.args[0].commit, SHA)
        report = json.loads(self.publication.call_args.args[-1])
        self.assertEqual(report["approval_comment"], 11)
        self.assertEqual(report["runner_image"], IMAGE)
        self.github.issue["labels"] = [{"name": fixture.READY}]
        self.assertFalse(self.run_cycle())
        self.job.assert_called_once()
        self.publication.assert_called_once()

    def test_wrong_authenticated_identity_or_repository(self):
        with self.subTest("account"):
            self.github.owner = 123
            with self.assertRaises(fixture.BridgeError):
                self.run_cycle()
        with self.subTest("repository"):
            self.github.owner = fixture.OWNER
            self.github.repo = 123
            with self.assertRaises(fixture.BridgeError):
                self.run_cycle()
        self.job.assert_not_called()

    def test_owner_login_spoofs_with_wrong_ids(self):
        for identity in (self.github.issue, self.github.events[0], self.github.comments[0]):
            field = "actor" if "actor" in identity else "user"
            with self.subTest(identity=identity):
                identity[field] = {"login": "APMurtha", "id": 123}
                self.assertFalse(self.run_cycle())
                identity[field]["id"] = fixture.OWNER
        self.job.assert_not_called()

    def test_label_without_approval(self):
        self.github.comments = []
        self.assertFalse(self.run_cycle())
        self.assertIsNone(self.result())

    def test_relabel_needs_approval_for_new_event_even_in_same_second(self):
        self.github.events.append({**self.github.events[0], "id": 12})
        self.assertFalse(self.run_cycle())
        self.job.assert_not_called()

    def test_exact_body_change_after_claim(self):
        self.github.after_claim = lambda: self.github.issue.update(body=BODY + " ")
        self.assertFalse(self.run_cycle())
        self.assertEqual(self.result(), ("cancelled",))
        self.job.assert_not_called()

    def test_withdrawal_during_source_checks(self):
        self.source.side_effect = lambda *_: self.github.comments.clear()
        self.assertFalse(self.run_cycle())
        self.assertEqual(self.result(), ("cancelled",))
        self.job.assert_not_called()

    def test_edited_approval_is_ineligible(self):
        self.github.comments[0]["updated_at"] = "2026-11-18T12:00:01Z"
        self.assertFalse(self.run_cycle())
        self.job.assert_not_called()

    def test_terminal_label_and_fixture_dispatch(self):
        self.github.issue["labels"].append({"name": fixture.DONE})
        self.assertFalse(self.run_cycle())
        self.github.issue["body"] = fixture.TASK
        self.assertFalse(self.run_cycle())
        fixture.cycle.assert_called_with(self.db, NUMBER)
        self.job.assert_not_called()

    def test_interrupted_claim_never_reexecutes(self):
        self.job.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.run_cycle()
        self.assertEqual(self.result(), ("claimed",))
        self.assertFalse(self.run_cycle())
        self.assertEqual(self.result(), ("interrupted",))
        self.job.assert_called_once()

    def test_publication_retry_never_reexecutes(self):
        self.publication.side_effect = [fixture.BridgeError("disconnected"), None]
        with self.assertRaises(fixture.BridgeError):
            self.run_cycle()
        self.assertEqual(self.result(), ("passed",))
        self.assertFalse(self.run_cycle())
        first, second = self.publication.call_args_list
        self.assertEqual(first, second)
        self.job.assert_called_once()

    def test_runner_timeout_is_terminal(self):
        self.job.side_effect = fixture.BridgeError("offline job timed out")
        self.assertFalse(self.run_cycle())
        self.assertEqual(self.result(), ("runner-failed",))
        self.assertFalse(self.run_cycle())
        self.job.assert_called_once()

    def test_denied_source_does_not_start_runner(self):
        self.source.side_effect = fixture.BridgeError("pinned commit is outside GitHub main")
        self.assertFalse(self.run_cycle())
        self.job.assert_not_called()


if __name__ == "__main__":
    unittest.main()
