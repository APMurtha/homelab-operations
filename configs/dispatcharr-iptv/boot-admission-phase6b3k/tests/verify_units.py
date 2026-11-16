"""Native *offline* unit syntax/graph check. Never contacts a service manager.

Uses the exact existing stack/guard units and candidate drop-in, plus a small
Docker readiness fixture. It does not prove real Docker or kernel behavior.
"""
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parents[1]
BASE = HERE.parent / "minimal-phase6b3d/units"


def main():
    with tempfile.TemporaryDirectory(prefix="dispatcharr-admission-units-") as directory:
        root = Path(directory)
        for name in ["dispatcharr-stack.service", "dispatcharr-egress-guard.service"]:
            (root / name).write_bytes((BASE / name).read_bytes())
        dropins = root / "dispatcharr-stack.service.d"
        dropins.mkdir()
        (dropins / "20-resource-admission.conf").write_bytes(
            (HERE / "20-resource-admission.conf").read_bytes())
        # Readiness graph only; ExecStart is never executed by `verify`.
        (root / "docker.service").write_text(
            "[Unit]\nDescription=OFFLINE Docker readiness fixture\n"
            "[Service]\nType=oneshot\nExecStart=/usr/bin/true\nRemainAfterExit=yes\n"
        )
        docker_dropins = root / "docker.service.d"
        docker_dropins.mkdir()
        (docker_dropins / "50-dispatcharr-order.conf").write_bytes(
            (BASE / "docker.service.50-dispatcharr-order.conf").read_bytes())
        env = os.environ.copy()
        env["SYSTEMD_UNIT_PATH"] = str(root) + ":/usr/lib/systemd/system"
        result = subprocess.run(
            ["systemd-analyze", "verify", "--man=no",
             str(root / "dispatcharr-stack.service"),
             str(root / "dispatcharr-egress-guard.service"),
             str(root / "docker.service")],
            env=env, capture_output=True, text=True, timeout=30,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")
        if result.returncode:
            raise SystemExit(result.returncode)
        print("PASS: offline unit syntax/dependency fixture; no services executed")


if __name__ == "__main__":
    main()
