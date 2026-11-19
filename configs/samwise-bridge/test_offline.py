"""Test extraction and host-side offline runner constraints with synthetic data."""
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import offline
import runner
import stage_runtime
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


    def test_runtime_command_uses_pinned_image_and_explicit_isolation(self):
        image = "sha256:" + "a" * 64
        args = runner.container_command(runner.podman_command("/tmp/empty"), image, "isolated")
        self.assertEqual(args[-2:], ["--entrypoint=/usr/local/bin/python3", image])
        for flag in (
            "--pull=never", "--network=none", "--read-only", "--read-only-tmpfs=false",
            "--http-proxy=false", "--unsetenv-all", "--image-volume=ignore", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--user=65532:65532", "--memory=3584m",
            "--memory-swap=3584m", "--cpus=4", "--pids-limit=128", "--pid=private",
            "--ipc=private", "--uts=private", "--cgroupns=private", "--rm",
        ):
            self.assertIn(flag, args)
        for mount_flag in ("--volume", "--mount", "--secret", "--env-host", "--privileged"):
            self.assertFalse(any(arg.split("=")[0] == mount_flag for arg in args))

    @patch.object(runner.subprocess, "run")
    def test_cleanup_refuses_to_silently_ignore_podman_failure(self, run):
        run.side_effect = subprocess.CalledProcessError(125, "podman rm")
        with self.assertRaisesRegex(BridgeError, "cleanup failed for samwise-test"):
            runner.cleanup(runner.podman_command("/tmp/empty"), "samwise-test")
        self.assertTrue(run.call_args.kwargs["check"])

    def test_git_archive_reaches_subprocess_and_result_is_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git = ["/usr/bin/git", "-C", directory]
            subprocess.run(git + ["init", "--quiet"], check=True)
            (root / "README.md").write_text("committed")
            subprocess.run(git + ["add", "README.md"], check=True)
            subprocess.run(git + ["-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                                  "commit", "--quiet", "-m", "fixture"], check=True)
            commit = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
            (root / "README.md").write_text("uncommitted")
            fake = (
                "import json, sys, tarfile; "
                "t = tarfile.open(fileobj=sys.stdin.buffer, mode='r|'); "
                "assert t.extractfile(t.next()).read() == b'committed'; "
                "print(json.dumps(dict(files=1, focus='documentation')))"
            )
            with (patch.object(runner, "ROOT", root),
                  patch.object(runner, "container_command", return_value=[sys.executable, "-c", fake]),
                  patch.object(runner, "cleanup") as cleanup):
                result = runner.run_container(SimpleNamespace(commit=commit), "sha256:" + "a" * 64,
                                              "samwise-test", "/tmp/empty")
            self.assertEqual(result, {"files": 1, "focus": "documentation"})
            cleanup.assert_called_once()

    @patch.object(stage_runtime.urllib.request, "urlopen", return_value=io.BytesIO(b"wrong"))
    def test_runtime_download_rejects_digest_mismatch(self, _):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Digest mismatch"):
                stage_runtime.fetch("https://example.invalid/blob", Path(directory) / "blob", "a" * 64)


if __name__ == "__main__":
    unittest.main()
