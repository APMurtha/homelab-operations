"""Verify publication retry behavior and the fixed GitHub write scope."""
import json
import sqlite3
import unittest
from unittest.mock import patch

import publisher
from worker import BridgeError, OWNER, READY, REPO, RUNNING

GIT = f"{REPO}/git"
BRANCH = "samwise/results/issue-25"
SHA = "a" * 40
COMMIT = "b" * 40
STAMP = "2026-11-18T12:00:00+00:00"
PR = {"number": 50, "head": {"sha": COMMIT, "ref": BRANCH},
      "base": {"ref": "main", "repo": {"id": 1126036330}}}
REF = {"ref": f"refs/heads/{BRANCH}", "object": {"sha": COMMIT}}


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE receipts (issue INTEGER PRIMARY KEY, published INTEGER)")
        self.db.execute("INSERT INTO receipts VALUES (25, 0)")
        self.matches = []
        self.comments = []
        self.issue = {"labels": [{"name": READY}, {"name": RUNNING}]}
        self.ref = REF
        self.fail_comment_once = False
        self.fail_ref_once = False
        self.get = self.replace("gh", self.gh)
        self.write = self.replace("post", self.post)
        self.labels = self.replace("label", lambda *_args, **_kwargs: None)

    def replace(self, name, effect):
        patcher = patch.object(publisher, name, side_effect=effect)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def gh(self, path):
        if path == f"{GIT}/commits/{SHA}":
            return {"tree": {"sha": "c" * 40}}
        if path.startswith(f"{REPO}/pulls?"):
            return self.matches
        if path == f"{GIT}/ref/heads/{BRANCH}":
            return self.ref
        if path.startswith(f"{REPO}/issues/25/comments?"):
            return self.comments
        if path == f"{REPO}/issues/25":
            return self.issue
        raise AssertionError(path)

    def post(self, path, data):
        if path == f"{GIT}/trees":
            self.assertEqual(data["tree"][0]["path"], "samwise-results/issue-25.json")
            self.assertEqual(len(data["tree"]), 1)
            return {"sha": "d" * 40}
        if path == f"{GIT}/commits":
            self.assertEqual(data["parents"], [SHA])
            self.assertEqual(data["committer"]["date"], STAMP)
            return {"sha": COMMIT}
        if path == f"{GIT}/refs":
            if self.fail_ref_once:
                self.fail_ref_once = False
                raise BridgeError("lost ref response")
            return self.ref
        if path == f"{REPO}/pulls":
            self.assertEqual(data["head"], BRANCH)
            self.assertEqual(data["base"], "main")
            self.assertTrue(data["draft"])
            self.matches.append(PR)
            return PR
        if path == f"{REPO}/issues/25/comments":
            self.comments.append({"user": {"id": OWNER}, "body": data["body"]})
            if self.fail_comment_once:
                self.fail_comment_once = False
                raise BridgeError("lost comment response")
            return self.comments[-1]
        raise AssertionError(path)

    def publish(self, result="passed"):
        publisher.publish(self.db, 25, result, STAMP, json.dumps({"commit": SHA}))

    def test_reconciles_lost_ref_and_comment_responses(self):
        self.fail_ref_once = True
        self.fail_comment_once = True
        with self.assertRaisesRegex(BridgeError, "lost comment"):
            self.publish()
        self.assertEqual(self.db.execute("SELECT published FROM receipts").fetchone(), (0,))
        self.publish()
        self.assertEqual(len(self.comments), 1)
        self.assertEqual(len(self.matches), 1)
        self.assertEqual([call.args[0] for call in self.write.call_args_list].count(f"{GIT}/refs"), 1)
        self.assertEqual(self.db.execute("SELECT published FROM receipts").fetchone(), (1,))

    def test_spoofed_comment_does_not_count_as_result(self):
        self.comments = [{"user": {"id": 123}, "body":
                          "Samwise v2 result for #25: `cancelled`.\n\n<!-- samwise-v2-receipt:25 -->"}]
        self.publish("cancelled")
        self.assertEqual(len(self.comments), 2)
        self.assertEqual(self.write.call_count, 1)

    def test_branch_collision_never_overwrites_or_creates_pr(self):
        self.ref = {**REF, "object": {"sha": SHA}}
        with self.assertRaisesRegex(BridgeError, "unexpected commit"):
            self.publish()
        self.assertEqual(self.matches, [])
        self.assertEqual(self.comments, [])
        self.labels.assert_not_called()


if __name__ == "__main__":
    unittest.main()
