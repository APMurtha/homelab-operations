"""Fixed input projection and credential-free Dispatcharr fingerprint job."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import uuid

from development import IMAGE
import runner
from worker import BridgeError

INPUTS = (
    "docs/dispatcharr-permanent-streaming-artifact-review.md",
    "docs/dispatcharr-jellyfin-integration.md",
    "docs/dispatcharr-structured-celery-restoration-results.md",
    "configs/dispatcharr-iptv/structured-celery-restoration-results.json",
)
TARGET = "samwise-dispatcharr-evidence.md"
LIMIT = 128 * 1024
REVIEWED_RECEIPT = "fcdb2c7923f2b74787a7b40ceb8222420884e40e86feab9bce472973c07836d0"
PROGRAM = """import base64, hashlib, json, sys
blobs = json.load(sys.stdin)
print(json.dumps([hashlib.sha256(base64.b64decode(b, validate=True)).hexdigest() for b in blobs]))
"""


def git(*args):
    return subprocess.check_output(runner.git(*args), env=runner.ENV,
                                   stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)


def snapshot(commit):
    if not re.fullmatch("[0-9a-f]{40}", commit) or git("cat-file", "-t", commit) != b"commit\n":
        raise BridgeError("expected pinned commit")
    if git("ls-tree", commit, "--", TARGET):
        raise BridgeError("output already exists")
    blobs = []
    for path in INPUTS:
        entry = git("ls-tree", commit, "--", path)
        match = re.fullmatch(rb"100644 blob ([0-9a-f]{40})\t" + re.escape(path.encode()) + rb"\n", entry)
        if not match:
            raise BridgeError("missing or non-regular evidence")
        oid = match[1].decode()
        if int(git("cat-file", "-s", oid)) > LIMIT:
            raise BridgeError("oversized evidence")
        blobs.append(git("cat-file", "blob", oid))
    return blobs


def isolated(blobs):
    if os.geteuid() == 0:
        raise BridgeError("rootless staging runtime required")
    name = "samwise-v4-" + uuid.uuid4().hex
    with tempfile.TemporaryDirectory() as hooks, tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as output:
        source.write(json.dumps([base64.b64encode(b).decode() for b in blobs]).encode())
        source.seek(0)
        podman = runner.podman_command(hooks)
        command = runner.container_command(podman, IMAGE, name, timeout=20)
        try:
            with subprocess.Popen(command + ["-I", "-S", "-c", PROGRAM], stdin=source,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  env=runner.PODMAN_ENV, start_new_session=True) as proc:
                try:
                    if not runner.bounded_output(proc, output, 512, 25) or proc.wait(timeout=5):
                        raise BridgeError("fingerprint job failed")
                finally:
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
            output.seek(0)
            return json.load(output)
        finally:
            runner.cleanup(podman, name)


def report(commit, blobs, hashes):
    if len(blobs) != len(INPUTS) or hashes != [hashlib.sha256(b).hexdigest() for b in blobs]:
        raise BridgeError("runner fingerprint mismatch")
    rows = [f"| `{path}` | {len(blob)} | `{digest}` |"
            for path, blob, digest in zip(INPUTS, blobs, hashes)]
    finding = ("The reviewed November 19 receipt records failed structured Celery readiness. "
               "Registration and export rebinding were never reached."
               if hashes[-1] == REVIEWED_RECEIPT else
               "The restoration receipt differs from the reviewed November 19 evidence. Review its provenance.")
    return "\n".join(["# DW English repository evidence", "", f"Source commit `{commit}`.", "",
                      "| File | Bytes | SHA-256 |", "|---|---:|---|", *rows, "", finding,
                      "Current service and playback state are unknown.", ""])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Offline staging probe with no GitHub adapter")
    parser.add_argument("commit")
    base = parser.parse_args().commit
    inputs = snapshot(base)
    print(report(base, inputs, isolated(inputs)), end="")
