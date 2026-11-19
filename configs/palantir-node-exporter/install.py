#!/usr/bin/env python3
"""REVIEW ONLY: narrowly scoped Debian 12 / Palantir CT 110 node-exporter installer.

Run through Orthanc's pct exec only after separate deployment authorization.
Modes: install | verify BACKUP_DIRECTORY | rollback BACKUP_DIRECTORY.
No SSH, DNS, DHCP, network, firewall, Prometheus, or Grafana writes.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.request

PACKAGE = 'prometheus-node-exporter'
VERSION = '1.5.0-1+b6'
ADDRESS = '10.10.20.10'
UNIT = PACKAGE + '.service'
DROPIN = Path('/etc/systemd/system/' + UNIT + '.d')
OVERRIDE = DROPIN / 'palantir.conf'
DEFAULT = Path('/etc/default/' + PACKAGE)
BACKUPS = Path('/var/backups/palantir-node-exporter')
PROTECTED_UNITS = ['pihole-FTL.service', 'unbound.service', 'ssh.service']
CONFIG_PATHS = [Path(p) for p in (
    '/etc/pihole/pihole.toml', '/etc/pihole/setupVars.conf', '/etc/dnsmasq.d',
    '/etc/unbound', '/etc/network', '/etc/systemd/network', '/etc/resolv.conf',
    '/etc/ssh/sshd_config', '/etc/ssh/sshd_config.d', '/etc/ufw')]
OVERRIDE_TEXT = '''[Service]
ExecStart=
ExecStart=/usr/bin/prometheus-node-exporter --web.listen-address=10.10.20.10:9100 --collector.disable-defaults --collector.cpu --collector.meminfo --collector.filesystem --collector.filesystem.mount-points-exclude=^/.+ --log.level=warn
NoNewPrivileges=true
MemoryAccounting=true
MemoryMax=64M
CPUQuota=20%
TasksMax=32
'''


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def run(argv, *, check=True, timeout=45):
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=timeout,
                            env=dict(os.environ, LC_ALL='C', DEBIAN_FRONTEND='noninteractive',
                                     NEEDRESTART_MODE='l'))
    require(not check or result.returncode == 0,
            'Command failed (output withheld): ' + ' '.join(argv[:3]))
    return result


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(directory, name, value):
    target = directory / name
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    target.chmod(0o600)


def identity():
    require(os.geteuid() == 0, 'Must run as CT root through pct exec 110; do not change sudo.')
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines()
                   if '=' in line)
    require(release.get('ID', '').strip('"') == 'debian'
            and release.get('VERSION_ID', '').strip('"') == '12', 'Expected Debian 12; re-review package pin.')
    require(socket.gethostname().split('.')[0].lower() == 'palantir', 'Wrong hostname; refusing installation.')
    require(run(['systemd-detect-virt', '--container']).stdout.strip() == 'lxc', 'Expected LXC guest.')
    addresses = json.loads(run(['ip', '-j', '-4', 'address', 'show']).stdout)
    require(any(a.get('local') == ADDRESS for link in addresses for a in link['addr_info']), 'Wrong IP address.')
    for tool in ['apt-get', 'dpkg-query', 'systemctl', 'ss', 'dig']:
        require(shutil.which(tool), 'Missing required tool: ' + tool)


def installed():
    result = run(['dpkg-query', '-W', '-f=${db:Status-Abbrev} ${Version}', PACKAGE], check=False)
    return result.stdout.strip() if result.returncode == 0 else ''


def protected_files():
    out = {}
    for root in CONFIG_PATHS:
        paths = [root, *sorted(root.rglob('*'))] if root.is_dir() else [root]
        for p in paths:
            if p.is_symlink():
                out[str(p)] = {'symlink': os.readlink(p)}
                if p.is_file():
                    out[str(p)]['target_sha256'] = sha(p.read_bytes())
            elif p.is_file():
                out[str(p)] = {'sha256': sha(p.read_bytes()), 'mode': p.stat().st_mode & 0o7777}
    return out


def dns_checks():
    # Ordinary queries through existing local resolvers; no resolver/config changes.
    for port in ['53', '5335']:
        for transport in ['+notcp', '+tcp']:
            answer = run(['dig', '@127.0.0.1', '-p', port, 'example.com.', 'A', transport,
                          '+time=3', '+tries=1', '+noall', '+comments', '+answer'], timeout=10)
            require('status: NOERROR' in answer.stdout and re.search(r'\sIN\s+A\s+', answer.stdout),
                    'Existing DNS check failed on port ' + port + ' ' + transport)


def baseline():
    states = {}
    for unit in PROTECTED_UNITS:
        fields = dict(line.split('=', 1) for line in run([
            'systemctl', 'show', unit, '-p', 'MainPID', '-p', 'ActiveState', '-p', 'NRestarts']).stdout.splitlines())
        require(fields['ActiveState'] == 'active' and int(fields['MainPID']) > 0, 'Protected service inactive: ' + unit)
        states[unit] = fields
    links = json.loads(run(['ip', '-j', 'address', 'show']).stdout)
    addresses = sorted([link['ifname'], a['family'], a['local'], a['prefixlen']]
                       for link in links for a in link.get('addr_info', []))
    routes = json.loads(run(['ip', '-j', 'route', 'show', 'table', 'all']).stdout)
    routes = sorted(json.dumps({k: v for k, v in x.items() if k not in ['expires', 'cache']}, sort_keys=True) for x in routes)
    firewall = {}
    for tool in ['iptables-save', 'ip6tables-save']:
        if shutil.which(tool):
            r = run([tool], check=False)
            require(r.returncode == 0, 'Cannot read existing firewall state: ' + tool)
            # Export timestamps and policy-chain packet counters are dynamic, not rules.
            text = '\n'.join(re.sub(r'\[\d+:\d+\]', '[COUNTERS]', line)
                             for line in r.stdout.splitlines() if not line.startswith('#'))
            firewall[tool] = sha(text.encode())
    dns_checks()
    return {'services': states, 'configuration': protected_files(), 'addresses': addresses,
            'routes': routes, 'firewall': firewall,
            'firewall_limit': 'Only installed iptables-save frontends are fingerprinted; no firewall tools/rules are added.'}


def package_plan(action):
    args = ['apt-get', '-s', '--no-install-recommends', '--no-auto-remove', '--no-remove']
    if action == 'install':
        args += ['--no-upgrade', 'install', PACKAGE + '=' + VERSION]
    else:
        args.remove('--no-remove')
        args += ['purge', PACKAGE]
    text = run(args).stdout
    transactions = [line for line in text.splitlines() if re.match(r'^(Inst|Conf|Remv|Purg) ', line)]
    require(all(line.split()[1].split(':')[0] == PACKAGE for line in transactions),
            'Package transaction affects unrelated packages; stop and review.')
    require(any(line.startswith('Inst ' + PACKAGE + ' (' + VERSION + ' ') for line in transactions)
            if action == 'install' else any(line.startswith(('Remv ', 'Purg ')) for line in transactions),
            'Expected package operation absent; stop and review.')
    return text


def read_backup(value):
    p = Path(value)
    require(not BACKUPS.is_symlink() and BACKUPS.stat().st_uid == 0
            and not BACKUPS.stat().st_mode & 0o077, 'Unsafe backup parent.')
    require(not p.is_symlink() and p.parent == BACKUPS and p.is_dir(), 'Use the exact backup path printed by install.')
    require(p.stat().st_uid == 0 and not p.stat().st_mode & 0o077, 'Unsafe backup ownership/permissions.')
    manifest = json.loads((p / 'manifest.json').read_text())
    require(manifest['target'] == ADDRESS and manifest['version'] == VERSION, 'Wrong recovery set.')
    for name, checksum in manifest['files'].items():
        require(sha((p / name).read_bytes()) == checksum, 'Backup integrity failure: ' + name)
    return p


def verify(p):
    require(installed() == 'ii  ' + VERSION, 'Unexpected installed package state/version.')
    require(OVERRIDE.read_text() == OVERRIDE_TEXT, 'Agent override changed.')
    require(run(['systemctl', 'is-active', UNIT]).stdout.strip() == 'active', 'Exporter is not active.')
    require(run(['systemctl', 'show', UNIT, '-p', 'User', '--value']).stdout.strip() == 'prometheus', 'Exporter must be unprivileged.')
    listeners = run(['ss', '-H', '-lnt', 'sport = :9100']).stdout.splitlines()
    require(len(listeners) == 1 and listeners[0].split()[3] == ADDRESS + ':9100', 'Unexpected exporter listener/exposure.')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://' + ADDRESS + ':9100/metrics', timeout=10) as response:
        text = response.read(2_000_000).decode()
    samples = [line for line in text.splitlines() if line and not line.startswith('#')]
    def metric(name):
        return [float(line.rsplit(' ', 1)[1]) for line in samples if line.startswith(name + ' ') or line.startswith(name + '{')]
    require(metric('node_cpu_seconds_total'), 'No CPU counters.')
    successes = [line for line in samples if line.startswith('node_scrape_collector_success{')]
    require(len(successes) == 3 and all(float(x.rsplit(' ', 1)[1]) == 1 for x in successes), 'Collector failure/unexpected collector.')
    require(not any(line.startswith('node_zfs_') for line in samples), 'Unexpected ZFS collector.')
    roots = [line for line in samples if line.startswith('node_filesystem_size_bytes{')]
    require(len(roots) == 1 and 'mountpoint="/"' in roots[0] and 'fstype="ext4"' in roots[0], 'Expected only ext4 root filesystem.')
    memory = {line.split(':')[0]: int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines()}
    stat = os.statvfs('/')
    require(metric('node_memory_MemTotal_bytes') == [float(memory['MemTotal'])], 'Exporter RAM total differs from CT view.')
    require(metric('node_filesystem_size_bytes') == [float(stat.f_blocks * stat.f_frsize)], 'Root size differs from statvfs.')
    memory_percent = 100 * (1 - metric('node_memory_MemAvailable_bytes')[0] / memory['MemTotal'])
    host_memory_percent = 100 * (1 - memory['MemAvailable'] / memory['MemTotal'])
    fs_percent = 100 * (1 - metric('node_filesystem_free_bytes')[0] / metric('node_filesystem_size_bytes')[0])
    require(abs(memory_percent - host_memory_percent) <= 3, 'Memory reading mismatch beyond scrape timing tolerance.')
    require(abs(fs_percent - 100 * (1 - stat.f_bfree / stat.f_blocks)) <= .1, 'Root filesystem reading mismatch.')
    require(baseline() == json.loads((p / 'baseline.json').read_text()), 'Protected service/configuration/network state changed; stop for review.')
    return {'memory_percent': memory_percent, 'root_used_total_percent': fs_percent,
            'cpu_counters_present': True, 'cpu_rate_validation': 'Deferred to monitoring integration; CT accounting must be checked independently.',
            'protected_checks': 'passed', 'listener': ADDRESS + ':9100',
            'resource_state': run(['systemctl', 'show', UNIT, '-p', 'MemoryCurrent', '-p', 'CPUUsageNSec']).stdout}


def install():
    require(not installed(), 'Package already known to dpkg; reuse/repair requires a separate review.')
    require(not any(p.exists() or p.is_symlink() for p in [DROPIN, DEFAULT,
            Path('/usr/lib/systemd/system/' + UNIT), Path('/lib/systemd/system/' + UNIT)]), 'Existing exporter files; stop.')
    require(not run(['dpkg', '--audit']).stdout.strip(), 'Pending package repairs; stop.')
    require(not run(['ss', '-H', '-lnt', 'sport = :9100']).stdout.strip(), 'Port 9100 is occupied.')
    mem = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    require(mem >= 128 * 1024**2 and shutil.disk_usage('/').free >= 256 * 1024**2, 'Insufficient headroom.')
    plan = package_plan('install')
    before = baseline()
    require(not BACKUPS.is_symlink(), 'Backup parent may not be a symlink.')
    BACKUPS.mkdir(mode=0o700, exist_ok=True)
    require(BACKUPS.stat().st_uid == 0 and not BACKUPS.stat().st_mode & 0o077, 'Unsafe backup parent.')
    p = BACKUPS / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + str(os.getpid()))
    p.mkdir(mode=0o700)
    save(p, 'baseline.json', before)
    (p / 'package-plan.txt').write_text(plan)
    (p / 'reviewed-override.conf').write_text(OVERRIDE_TEXT)
    with tarfile.open(p / 'protected-config.tar.gz', 'w:gz', dereference=False) as archive:
        for item in CONFIG_PATHS:
            if item.exists() or item.is_symlink():
                archive.add(item, arcname=str(item).lstrip('/'))
    # Read every archive member to detect damage before any installation writes.
    with tarfile.open(p / 'protected-config.tar.gz', 'r:gz') as archive:
        for member in archive:
            if member.isfile():
                require(len(archive.extractfile(member).read()) == member.size, 'Archive integrity failure.')
    save(p, 'manifest.json', {'target': ADDRESS, 'version': VERSION, 'new_agent_files_previously_absent': True,
                            'files': {x.name: sha(x.read_bytes()) for x in p.iterdir() if x.is_file()}})
    read_backup(str(p))
    print('Verified private backup: ' + str(p), flush=True)
    try:
        DROPIN.mkdir(mode=0o755)
        with OVERRIDE.open('x') as file:
            file.write(OVERRIDE_TEXT)
        OVERRIDE.chmod(0o644)
        run(['systemctl', 'daemon-reload'])
        # Override exists before the package's first automatic service start.
        result = run(['apt-get', '--yes', '--no-install-recommends', '--no-auto-remove',
                      '--no-remove', '--no-upgrade', 'install', PACKAGE + '=' + VERSION],
                     check=False, timeout=240)
        (p / 'install.log').write_text(result.stdout + result.stderr)
        require(result.returncode == 0, 'Package install failed; inspect the private install log.')
        run(['systemctl', 'enable', '--now', UNIT])
        save(p, 'installed-files.json', {str(x): sha(x.read_bytes()) for x in [OVERRIDE, DEFAULT]})
        time.sleep(2)
        result = verify(p)
        save(p, 'verification.json', result)
        print(json.dumps({'installed': VERSION, 'backup': str(p), **result}, indent=2))
    except Exception:
        # Never restart or restore protected services automatically.
        run(['systemctl', 'disable', '--now', UNIT], check=False)
        print('Installation stopped; exporter disabled. Private recovery set: ' + str(p), file=sys.stderr)
        print('Review the failure before invoking rollback with this recovery set.', file=sys.stderr)
        raise


def rollback(p):
    expected = json.loads((p / 'installed-files.json').read_text()) if (p / 'installed-files.json').exists() else {str(OVERRIDE): sha(OVERRIDE_TEXT.encode())}
    for name, checksum in expected.items():
        file = Path(name)
        require(not file.is_symlink() and file.is_file() and sha(file.read_bytes()) == checksum,
                'Agent configuration drift; refusing automatic rollback: ' + name)
    state = installed()
    require(not state or state == 'ii  ' + VERSION, 'Partial/changed package state; manual package review required.')
    require(not state or (p / 'installed-files.json').exists(),
            'Installed file hashes unavailable; manual package review required.')
    if state:
        package_plan('purge')
        run(['systemctl', 'disable', '--now', UNIT])
        run(['apt-get', '--yes', '--no-auto-remove', 'purge', PACKAGE], timeout=240)
    OVERRIDE.unlink()
    DROPIN.rmdir()  # Refuses to remove any unexpected files.
    run(['systemctl', 'daemon-reload'])
    require(not installed() and not OVERRIDE.exists(), 'Agent removal not complete.')
    require(baseline() == json.loads((p / 'baseline.json').read_text()), 'Protected state differs; do not auto-restore it.')
    save(p, 'rollback.json', {'agent_removed': True, 'protected_checks': 'passed'})
    print('Only the new exporter was removed; recovery set retained: ' + str(p))


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'verify', 'rollback'])
    parser.add_argument('backup', nargs='?')
    args = parser.parse_args()
    require((args.action == 'install') == (args.backup is None), 'verify/rollback require the exact backup directory.')
    identity()
    if args.action == 'install':
        install()
    elif args.action == 'verify':
        print(json.dumps(verify(read_backup(args.backup)), indent=2))
    else:
        rollback(read_backup(args.backup))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, tarfile.TarError, subprocess.SubprocessError) as error:
        print('STOP: ' + str(error), file=sys.stderr)
        sys.exit(1)
