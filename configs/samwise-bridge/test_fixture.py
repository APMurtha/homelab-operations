"""Regression coverage for the original fixture-only entry point."""
import sqlite3
import unittest
from unittest.mock import patch

import worker


class FixtureTests(unittest.TestCase):
    def test_fixture_runs_once_and_v2_body_remains_ineligible(self):
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.execute("CREATE TABLE receipts (issue INTEGER PRIMARY KEY, "
                   "result TEXT, updated TEXT, published INTEGER)")
        issue = {"body": "samwise-task-v2: {}", "state": "open", "updated_at": "stamp",
                 "labels": [{"name": worker.READY}], "user": {"id": worker.OWNER}}

        def get(path):
            if path == "user":
                return {"id": worker.OWNER}
            if path == worker.REPO:
                return {"id": 1126036330}
            if "/events?" in path:
                return [{"label": {"name": worker.READY}, "event": "labeled",
                         "actor": {"id": worker.OWNER}}]
            return {**issue, "labels": list(issue["labels"])}

        def label(_number, name, *, remove=False):
            if remove:
                issue["labels"].remove({"name": name})
            else:
                issue["labels"].append({"name": name})

        with (patch.object(worker, "gh", side_effect=get),
              patch.object(worker, "label", side_effect=label),
              patch.object(worker, "codex_task", return_value="passed") as job):
            self.assertFalse(worker.cycle(db, 25))
            issue["body"] = worker.TASK
            self.assertTrue(worker.cycle(db, 25))
            self.assertFalse(worker.cycle(db, 25))
        job.assert_called_once()
        self.assertEqual(db.execute("SELECT result, published FROM receipts").fetchone(),
                         ("passed", 1))
