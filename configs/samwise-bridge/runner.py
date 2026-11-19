"""Send a bounded source snapshot to the offline rootless Podman runner."""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import uuid

from worker import BridgeError

ROOT = Path(__file__).resolve().parents[2]
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
MAX_ARCHIVE = 32 * 1024 * 1024
OUTCOMES = frozenset({"documentation", "configuration", "code"})
ENV = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
       "GIT_NO_LAZY_FETCH": "1", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
if os.environ.get("XDG_RUNTIME_DIR") == f"/run/user/{os.getuid()}":
    ENV["XDG_RUNTIME_DIR"] = os.environ["XDG_RUNTIME_DIR"]


def git(*args):
    return ["/usr/bin/git", "--no-replace-objects", "-C", str(ROOT), *args]


def bounded_output(process, output, limit, timeout):
    subprocess.run(["/usr/bin/head", "-c", str(limit + 1)], stdin=process.stdout,
                   stdout=output, timeout=timeout, check=True, env=ENV)
    process.stdout.close()
    return output.tell() <= limit


def inventory(task, image):
    if not IMAGE_ID.fullmatch(image) or os.geteuid() == 0:
        raise BridgeError("offline runner requires rootless Podman and a pinned local image ID")
    name = f"samwise-{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix="samwise-no-hooks-") as hooks:
        return run_container(task, image, name, hooks)


def podman_command(hooks):
    return ["/usr/bin/podman", "--remote=false", "--default-mounts-file=/dev/null",
              f"--hooks-dir={hooks}"]


PODMAN_ENV = {**ENV, "CONTAINERS_CONF": "/dev/null", "CONTAINERS_CONF_OVERRIDE": "/dev/null"}
MEMORY_MIB = 3584


def container_command(podman, image, name, *, timeout=175):
    return podman + [
        "run", "--name", name, "--rm", "--interactive", "--pull=never",
        "--network=none", "--http-proxy=false", "--read-only", "--read-only-tmpfs=false",
        "--image-volume=ignore", "--no-healthcheck", "--log-driver=none", f"--timeout={timeout}",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--pids-limit=128", f"--memory={MEMORY_MIB}m", f"--memory-swap={MEMORY_MIB}m",
        "--cpus=4", "--ulimit=fsize=67108864:67108864",
        "--unsetenv-all", "--cgroupns=private", "--ipc=private", "--pid=private",
        "--uts=private", "--no-hosts", "--passwd=false",
        "--systemd=false", "--init=false", "--restart=no",
        "--tmpfs=/tmp:rw,nodev,nosuid,noexec,size=512m",
        "--user=65532:65532", "--entrypoint=/usr/local/bin/python3", image,
    ]


def cleanup(podman, name):
    try:
        subprocess.run(podman + ["rm", "--force", "--ignore", name], env=PODMAN_ENV,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       stdin=subprocess.DEVNULL, timeout=15, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise BridgeError(f"offline container cleanup failed for {name}") from exc


def run_container(task, image, name, hooks):
    podman = podman_command(hooks)
    command = container_command(podman, image, name) + ["/opt/samwise/offline.py"]
    try:
        with tempfile.TemporaryFile() as snapshot, tempfile.TemporaryFile() as output:
            # An archive from the exact Git object excludes checkout state, config and hooks.
            archive = git("archive", "--format=tar", task.commit)
            with subprocess.Popen(archive, env=ENV, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL) as process:
                # head enforces the size cap while subprocess.run supplies the read deadline.
                try:
                    if not bounded_output(process, snapshot, MAX_ARCHIVE, 20) or process.wait(timeout=5):
                        raise BridgeError("source snapshot unavailable or too large")
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
            snapshot.seek(0)
            with subprocess.Popen(command, env=PODMAN_ENV, stdin=snapshot, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, start_new_session=True) as process:
                try:
                    if not bounded_output(process, output, 4096, 180) or process.wait(timeout=5):
                        raise BridgeError("offline Codex runner failed")
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
            output.seek(0)
            data = json.load(output)
            if not isinstance(data, dict) or set(data) != {
                "files", "focus",
            }:
                raise BridgeError("invalid offline result")
            if (type(data["files"]) is not int or not 0 < data["files"] <= 10000
                    or not isinstance(data["focus"], str) or data["focus"] not in OUTCOMES):
                raise BridgeError("invalid offline result")
            return data
    except subprocess.TimeoutExpired as exc:
        raise BridgeError("offline job timed out") from exc
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise BridgeError("offline runner unavailable or returned invalid data") from exc
    finally:
        cleanup(podman, name)
