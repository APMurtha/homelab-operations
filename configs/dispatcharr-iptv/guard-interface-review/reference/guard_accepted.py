#!/usr/bin/env python3
"""Default is syntax check. Only explicit 'apply' changes the NEW IPTV table."""
import argparse
import configparser
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from security import TABLE, load_policy, read_peer, render_rules


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['check', 'apply'])
    p.add_argument('--policy', required=True)
    p.add_argument('--wireguard', default='/docker/dispatcharr-iptv/private/wg0.conf')
    a = p.parse_args()
    policy, digest = load_policy(a.policy)
    if a.action == 'apply':
        if os.geteuid() != 0:
            raise ValueError('Applying the guard requires root.')
        for name in (a.policy, a.wireguard):
            st = Path(name).stat()
            if Path(name).is_symlink() or not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
                raise ValueError('Policy and WireGuard inputs must be root-owned private regular files.')
        if read_peer(a.wireguard) != (policy['wg_endpoint_ipv4'], policy['wg_endpoint_port']):
            raise ValueError('Policy and WireGuard peer mismatch.')
    if a.action == 'apply':
        directory = Path('/run/dispatcharr-guard')
        directory.mkdir(mode=0o755, exist_ok=True)
        if directory.is_symlink() or directory.stat().st_uid != 0 or directory.stat().st_mode & 0o022:
            raise ValueError('Unsafe ready-marker directory.')
        # Failed reapplication must never leave stale readiness for future starts.
        (directory / 'ready').unlink(missing_ok=True)
    exists = subprocess.run(['nft', 'list', 'table', 'inet', TABLE], capture_output=True).returncode == 0
    rules = ('delete table inet ' + TABLE + '\n' if exists else '') + render_rules(policy)
    # nft --check does not apply the transaction. No global flush/replace is used.
    subprocess.run(['nft', '--check', '--file', '-'], input=rules, text=True, check=True)
    if a.action == 'check':
        print('Scoped nftables transaction syntax accepted; no rules applied.')
        return
    subprocess.run(['nft', '--file', '-'], input=rules, text=True, check=True)
    # Atomic ruleset replacement first; readiness marker only after success.
    fd, name = tempfile.mkstemp(prefix='.ready-', dir=directory)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, 'w') as f:
            f.write(digest + '\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, directory / 'ready')
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print('Only the rivendell_iptv table updated; startup readiness recorded.')


if __name__ == '__main__':
    try:
        main()
    except (configparser.Error, ValueError, OSError, KeyError, subprocess.CalledProcessError):
        raise SystemExit('Guard operation failed; input values withheld. Do not start IPTV until the guard validates.')
