"""Offline validation tests for the proposed v2 task envelope."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "task_schema", Path(__file__).resolve().parent / "task_schema.py"
)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def body(**changes):
    data = {"kind": "repo-inventory", "revision": 1, "commit": "a" * 40}
    data.update(changes)
    return module.PREFIX + json.dumps(data)


class TaskSchemaTests(unittest.TestCase):
    def test_valid(self):
        task = module.parse(body())
        self.assertEqual(task.kind, "repo-inventory")
        self.assertTrue(module.same_authorized_content(body(), task.digest))

    def test_mutated_after_approval(self):
        task = module.parse(body())
        self.assertFalse(module.same_authorized_content(body(commit="b" * 40), task.digest))

    def test_denied_kinds(self):
        for kind in ("shell", "deploy", "ssh", "freeform"):
            with self.subTest(kind=kind), self.assertRaises(module.InvalidTask):
                module.parse(body(kind=kind))

    def test_denied_fields(self):
        for field in ("prompt", "command", "host", "path", "secret"):
            with self.subTest(field=field), self.assertRaises(module.InvalidTask):
                module.parse(body(**{field: "anything"}))

    def test_invalid_revision(self):
        for revision in (True, "1", 2):
            with self.subTest(revision=revision), self.assertRaises(module.InvalidTask):
                module.parse(body(revision=revision))

    def test_invalid_commit(self):
        for commit in ("../etc/passwd", "A" * 40, "f" * 64, "main"):
            with self.subTest(commit=commit), self.assertRaises(module.InvalidTask):
                module.parse(body(commit=commit))

    def test_oversized(self):
        with self.assertRaises(module.InvalidTask):
            module.parse(body() + " " * 3000)

    def test_duplicate_or_nonobject(self):
        with self.assertRaises(module.InvalidTask):
            module.parse(module.PREFIX + "[]")


if __name__ == "__main__":
    unittest.main()
