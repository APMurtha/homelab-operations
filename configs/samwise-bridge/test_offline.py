"""Test extraction and host-side offline runner constraints with synthetic data."""
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import offline
import runner
from worker import BridgeError


def snapshot(name, kind=tarfile.REGTYPE):
    stream = io.BytesIO()
    entry = tarfile.TarInfo(name)
    entry.type = kind
    content = b"example"
    if kind == tarfile.REGTYPE:
        entry.size = len(content)
    else:
        entry.linkname = "/etc/passwd"
    with tarfile.open(fileobj=stream, mode="w") as archive:
        archive.addfile(entry, io.BytesIO(content))
    stream.seek(0)
    return stream


class OfflineTests(unittest.TestCase):
    def test_counts_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(offline.unpack(snapshot("docs/example.md"), root),
                             {"documentation": 1})
            self.assertEqual((root / "docs/example.md").read_bytes(), b"example")

    def test_denies_traversal_absolute_links_and_devices(self):
        for name, kind in [("../outside.txt", tarfile.REGTYPE), ("/etc/passwd", tarfile.REGTYPE),
                           ("link", tarfile.SYMTYPE), ("link", tarfile.LNKTYPE),
                           ("device", tarfile.CHRTYPE)]:
            with self.subTest(name=name, kind=kind), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    offline.unpack(snapshot(name, kind), Path(directory))
                self.assertEqual(list(Path(directory).iterdir()), [])

    @patch.object(runner.os, "geteuid", return_value=0)
    def test_requires_rootless_and_pinned_image(self, _):
        with self.assertRaises(BridgeError):
            runner.inventory(SimpleNamespace(commit="a" * 40), "sha256:" + "a" * 64)
        with self.assertRaises(BridgeError):
            runner.inventory(SimpleNamespace(commit="a" * 40), "latest")

    @patch.object(runner.subprocess, "run")
    @patch.object(runner.subprocess, "Popen")
    @patch.object(runner, "bounded_output")
    @patch.object(runner.os, "killpg")
    def test_timeout_kills_client_and_requests_container_cleanup(self, killpg, bound, popen, run):
        job = popen.return_value.__enter__.return_value
        job.wait.return_value = 0
        job.poll.return_value = None
        bound.side_effect = [True, subprocess.TimeoutExpired("container", 180)]
        with self.assertRaisesRegex(BridgeError, "timed out"):
            runner.run_container(SimpleNamespace(commit="a" * 40),
                                 "sha256:" + "a" * 64, "samwise-test", "/tmp/empty")
        killpg.assert_called_once()
        cleanup = run.call_args.args[0]
        self.assertEqual(cleanup[-4:], ["rm", "--force", "--ignore", "samwise-test"])
        args = popen.call_args.args[0]
        self.assertIn("--network=none", args)
        self.assertIn("--timeout=175", args)
        self.assertIn("--default-mounts-file=/dev/null", args)
        self.assertIn("--read-only", args)
        self.assertNotIn("GH_TOKEN", popen.call_args.kwargs["env"])


if __name__ == "__main__":
    unittest.main()
