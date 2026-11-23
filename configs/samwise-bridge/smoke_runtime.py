"""Exercise the offline image as the current rootless user, without GitHub or receipts."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
import uuid

import runner

MIN_AVAILABLE_KIB = 4_718_592
MAX_COLD_SECONDS = 145

PROBE = """
import errno
import os
from pathlib import Path
import resource
import socket
import sys

host_namespaces, marker = sys.argv[1:-1], Path(sys.argv[-1])
namespaces = ("user", "net", "pid", "ipc", "uts", "mnt", "cgroup")
assert all(os.readlink(f"/proc/self/ns/{ns}") != host
           for ns, host in zip(namespaces, host_namespaces, strict=True))
assert os.getuid() == os.getgid() == 65532
assert os.getpid() == 1
status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
assert int(status["CapEff"], 16) == 0 and int(status["NoNewPrivs"]) == 1
assert {name for _, name in socket.if_nameindex()} == {"lo"}
with socket.socket() as listener:
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    with socket.create_connection(listener.getsockname(), timeout=1):
        pass
    try:
        socket.create_connection(("192.0.2.1", 443), timeout=1)
    except OSError as exc:
        assert exc.errno == errno.ENETUNREACH, exc
    else:
        raise AssertionError("outbound network reachable")

assert not marker.exists() and not Path("/run/secrets").exists()
assert not Path("/run/podman/podman.sock").exists()
assert not Path("/var/run/docker.sock").exists()
assert not (set(os.environ) & {"GH_TOKEN", "GITHUB_TOKEN", "OPENAI_API_KEY",
                              "SSH_AUTH_SOCK", "HTTP_PROXY", "HTTPS_PROXY"})
mounts = {}
for line in Path("/proc/self/mountinfo").read_text().splitlines():
    before, after = line.split(" - ", 1)
    fields = before.split()
    mounts[fields[4]] = (fields[5].split(","), after.split()[0])
    target = fields[4]
    assert target in {"/", "/tmp", "/etc/hostname", "/etc/resolv.conf", "/run/.containerenv"} or (
        target in {"/dev", "/proc", "/sys"} or target.startswith(("/dev/", "/proc/", "/sys/"))
    ), target
assert "ro" in mounts["/"][0]
assert mounts["/tmp"][1] == "tmpfs"
assert {"rw", "nodev", "nosuid", "noexec"} <= set(mounts["/tmp"][0])
assert os.statvfs("/tmp").f_frsize * os.statvfs("/tmp").f_blocks == 512 * 1024**2
Path("/tmp/isolated").write_text("ok")
print("Container mounts:", sorted(mounts))
cg = Path("/sys/fs/cgroup")
assert (cg / "memory.max").read_text().strip() == str(3584 * 1024**2)
assert (cg / "memory.high").read_text().strip() == str(3360 * 1024**2)
assert (cg / "memory.swap.max").read_text().strip() == "0"
assert (cg / "pids.max").read_text().strip() == "128"
quota, period = (cg / "cpu.max").read_text().split()
assert int(quota) == 4 * int(period)
assert resource.getrlimit(resource.RLIMIT_FSIZE) == (64 * 1024**2,) * 2
"""

INFERENCE = """
from pathlib import Path
import runpy
import sys

try:
    runpy.run_path("/opt/samwise/offline.py", run_name="__main__")
finally:
    cg = Path("/sys/fs/cgroup")
    print("Samwise peak bytes:", (cg / "memory.peak").read_text().strip(), file=sys.stderr)
    events = (cg / "memory.events").read_text().splitlines()
    assert {"oom 0", "oom_kill 0"} <= set(events), events
"""


def smoke(image):
    if os.geteuid() == 0 or not runner.IMAGE_ID.fullmatch(image):
        raise SystemExit("Use a rootless account and the full local sha256 image ID.")
    with tempfile.TemporaryDirectory(prefix="samwise-smoke-") as directory:
        root = Path(directory)
        marker = root / "host-only"
        marker.touch()
        hooks = root / "hooks"
        hooks.mkdir()
        podman = runner.podman_command(hooks)

        def invoke(args, **kwargs):
            return subprocess.run(podman + args, env=runner.PODMAN_ENV, **kwargs)

        def probe(program, *args, timeout=175, payload=b"", expect_timeout=False):
            name = f"samwise-smoke-{uuid.uuid4().hex}"
            command = runner.container_command(podman, image, name, timeout=timeout)
            env = {**runner.PODMAN_ENV, "GH_TOKEN": "synthetic", "GITHUB_TOKEN": "synthetic",
                   "OPENAI_API_KEY": "synthetic", "SSH_AUTH_SOCK": str(marker),
                   "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9"}
            try:
                started = time.monotonic()
                result = subprocess.run(command + ["-c", program, *args], input=payload,
                                        capture_output=True, timeout=timeout + 15, env=env)
                if expect_timeout:
                    assert result.stdout == b"started\n", result
                    # Podman can report an unknown exit status after conmon
                    # kills the process and automatically removes the container.
                    assert result.returncode in {137, 255}, result
                    assert timeout - 1 <= time.monotonic() - started < timeout + 15
                else:
                    if result.returncode:
                        raise RuntimeError(
                            f"{name} exited with status {result.returncode} "
                            f"after {time.monotonic() - started:.1f}s: "
                            f"{result.stderr.decode(errors='replace').strip()}"
                        )
                assert invoke(["container", "exists", name], timeout=10).returncode == 1
                return result
            finally:
                runner.cleanup(podman, name)

        actual = invoke(["image", "inspect", "--format", "{{.Id}}", image],
                        capture_output=True, text=True, check=True, timeout=15).stdout.strip()
        assert actual.removeprefix("sha256:") == image.removeprefix("sha256:"), actual
        namespaces = [os.readlink(f"/proc/self/ns/{ns}")
                      for ns in ("user", "net", "pid", "ipc", "uts", "mnt", "cgroup")]
        result = probe(PROBE, *namespaces, str(marker))
        print(result.stdout.decode().strip())
        probe('import time; print("started", flush=True); time.sleep(60)',
              timeout=5, expect_timeout=True)

        snapshot = io.BytesIO()
        with tarfile.open(fileobj=snapshot, mode="w") as archive:
            archive.addfile(tarfile.TarInfo("example.md"))
        with Path("/proc/meminfo").open() as meminfo:
            available = next(int(line.split()[1]) for line in meminfo
                             if line.startswith("MemAvailable:"))
        if available < MIN_AVAILABLE_KIB:
            raise RuntimeError(f"MemAvailable {available} KiB is below {MIN_AVAILABLE_KIB} KiB")
        start = time.monotonic()
        result = probe(INFERENCE, payload=snapshot.getvalue())
        elapsed = time.monotonic() - start
        assert json.loads(result.stdout) == {"files": 1, "focus": "documentation"}
        peak_line, = [line for line in result.stderr.splitlines()
                      if line.startswith(b"Samwise peak bytes: ")]
        peak = int(peak_line.split()[-1])
        print(f"MemAvailable {available} KiB, cold inference {elapsed:.1f}s, "
              f"cgroup peak {peak} bytes ({peak / 1024**2:.1f} MiB).")
        if peak >= runner.MEMORY_MIB * 1024**2 or elapsed >= MAX_COLD_SECONDS:
            raise RuntimeError("Cold inference exceeded the acceptance resource gate")
        print(f"{image} passed isolation, timeout and offline inference. "
              "No cgroup OOM events.")


if __name__ == "__main__":
    if not __debug__:
        raise SystemExit("Run this test with Python assertions enabled.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    smoke(parser.parse_args().image)
