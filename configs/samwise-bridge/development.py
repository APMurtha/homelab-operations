"""Host-side policy and isolated runner for v3's first development template."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import uuid

import development_job as job
import runner
from task_schema import GIT_SHA, InvalidTask, Task, unique_fields
from worker import BridgeError, REPO, gh

IMAGE = "sha256:db79c76fc71f354b20aa165d852eb70b9a0a6fbea568f2fa91f760a7b1302053"
PREFIX = "samwise-task-v3:"


def parse(body):
    if not isinstance(body, str) or len(body) > 2048 or not body.startswith(PREFIX):
        raise InvalidTask("invalid v3 envelope")
    try:
        raw = body.encode()
        value = json.loads(body[len(PREFIX):], object_pairs_hook=unique_fields)
    except (ValueError, RecursionError) as exc:
        raise InvalidTask("invalid v3 JSON") from exc
    if len(raw) > 2048 or not isinstance(value, dict):
        raise InvalidTask("invalid v3 task")
    commit = value.pop("commit", None)
    if (not isinstance(commit, str) or not GIT_SHA.fullmatch(commit)
            or type(value.get("revision")) is not int or value != {
                "revision": 1, "template": job.TEMPLATE, "paths": [job.TARGET]}):
        raise InvalidTask("unsupported development task")
    return Task(job.TEMPLATE, 1, commit, hashlib.sha256(raw).hexdigest())


def verify_base(task):
    ref = gh(f"{REPO}/git/ref/heads/main")["object"]
    if ref["type"] != "commit" or ref["sha"] != task.commit:
        raise BridgeError("development requires the current main commit")
    try:
        entry = subprocess.check_output(runner.git("ls-tree", task.commit, "--", job.TARGET),
                                        stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        env=runner.ENV, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise BridgeError("pinned tree unavailable") from exc
    if entry:
        raise BridgeError("development path already exists")


def develop(image):
    if image != IMAGE or os.geteuid() == 0:
        raise BridgeError("development requires the reviewed rootless runtime")
    name = f"samwise-dev-{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory() as hooks:
        podman = runner.podman_command(hooks)
        command = runner.container_command(podman, image, name) + ["-I", "-S", "-"]
        try:
            with Path(job.__file__).with_suffix(".py").open("rb") as program, tempfile.TemporaryFile() as output:
                with subprocess.Popen(command, env=runner.PODMAN_ENV, stdin=program,
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                      start_new_session=True) as process:
                    try:
                        if not runner.bounded_output(process, output, 1024, 180) or process.wait(timeout=5):
                            raise BridgeError("development job failed")
                    finally:
                        if process.poll() is None:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                output.seek(0)
                return job.validate(json.loads(output.read(), object_pairs_hook=unique_fields))
        except (OSError, ValueError, RecursionError, subprocess.SubprocessError) as exc:
            raise BridgeError("development timed out or returned invalid output") from exc
        finally:
            runner.cleanup(podman, name)
