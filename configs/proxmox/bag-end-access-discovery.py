#!/usr/bin/env python3
"""Read-only discovery from Bag-End; no SSH login, configuration writes or sudo."""
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import shlex
import socket
import stat
import subprocess
import time

NODES = {"orthanc": "10.10.10.2", "cirith-ungol": "10.10.10.3", "dol-guldur": "10.10.10.4"}

def call(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=8)
        return p.returncode, p.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None, ""

def fingerprint(key):
    try:
        raw = base64.b64decode(key, validate=True)
        return "SHA256:" + base64.b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
    except (ValueError, TypeError):
        return None

def main():
    host = socket.gethostname().split(".")[0]
    if host != "bag-end" or getpass.getuser() != "murth":
        raise SystemExit("STOP: requires Bag-End's existing murth terminal; no probes performed.")
    rc, text = call(["ip", "-j", "address", "show", "dev", "ens18"])
    addresses = []
    if rc == 0:
        for interface in json.loads(text):
            addresses += [{k: a.get(k) for k in ("family", "local", "prefixlen", "dynamic")} for a in interface.get("addr_info", [])]
    out = {"hostname": host, "account": "murth", "UTC": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "inspection_only": True, "addresses": addresses}
    if not any(a.get("local") == "10.10.40.132" and a.get("prefixlen") == 24 for a in addresses):
        out["stop"] = "ens18 address differs or could not be verified; no network probes performed"
        print(json.dumps(out, indent=2)); return
    ssh = Path.home() / ".ssh"
    out["ssh_files"] = []
    out["public_key_fingerprints"] = []
    if ssh.is_dir():
        for p in sorted(ssh.iterdir()):
            st = p.lstat()
            if not stat.S_ISREG(st.st_mode):
                continue
            if p.name.startswith("id_") or p.name in ("config", "known_hosts"):
                out["ssh_files"].append({"name": p.name, "mode": oct(stat.S_IMODE(st.st_mode)), "uid": st.st_uid})
            if p.name.endswith(".pub") and st.st_size < 16384:
                parts = p.read_text().split()
                if len(parts) >= 2:
                    out["public_key_fingerprints"].append({"name": p.name, "type": parts[0], "fingerprint": fingerprint(parts[1])})
    # Read text only: ssh -G may execute Match exec, so it is deliberately not used.
    config = ssh / "config"
    out["ssh_configuration"] = []
    if config.is_file() and not config.is_symlink() and config.stat().st_size < 1048576:
        for line in config.read_text().splitlines():
            try:
                parts = shlex.split(line, comments=True)
            except ValueError:
                continue
            if not parts:
                continue
            directive = parts[0].lower()
            if directive in {"host", "hostname", "user", "identityfile", "userknownhostsfile", "proxyjump", "include", "identitiesonly", "forwardagent"}:
                out["ssh_configuration"].append({"directive": directive, "values": parts[1:]})
            elif directive in {"match", "proxycommand", "localcommand"}:
                out["ssh_configuration"].append({"directive": directive, "value_withheld": True, "not_executed": True})
    # Output fingerprint fields only, excluding key comments and key material.
    rc, text = call(["ssh-add", "-l"])
    out["agent"] = {"reachable_with_identities": rc == 0, "exit": rc, "fingerprints": [x.split()[1] for x in text.splitlines() if len(x.split()) > 1 and x.split()[1].startswith("SHA256:")]}
    out["node_probes"] = []
    for name, address in NODES.items():
        row = {"name": name, "address": address, "TCP": {}}
        for port in (22, 8006):
            try:
                with socket.create_connection((address, port), timeout=2):
                    row["TCP"][str(port)] = "connected"
            except OSError:
                row["TCP"][str(port)] = "unavailable_or_filtered"
        out["node_probes"].append(row)
    out["limitations"] = ["No authentication attempted", "TCP connection does not verify server identity or permissions", "Included SSH configuration not evaluated", "Private keys, authorized_keys and API credential contents not read", "No packages, accounts, agents, services or configuration installed/changed"]
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
