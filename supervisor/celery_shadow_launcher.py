"""Fixed one-shot host supervisor for a separately provisioned shadow check.

No installation or listener. No issue-supplied values, shell execution, service
discovery, Docker socket or credentials. Required site adapters are deliberately
not enrolled by this draft; without their reviewed hashes it cannot emit ready.
"""
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

from celery_readiness import Witness, capture, destinations, leased_acquisition
from dispatcharr_project import directory
from ops_protocol import NS, check, decode

HOST = 'rivendell'
TARGET = 'rivendell-dispatcharr'
UNIT = 'samwise-celery-shadow-once.service'
INSTALL = Path('/opt/samwise-celery-shadow')
STATE = Path('/run/samwise-celery-shadow')
DROP = Path('/run/samwise-observations/celery-v1')
WITNESS = INSTALL / 'witness'
PING = INSTALL / 'pidbox-ping'
PERMIT = INSTALL / 'one-shot.json'
ENDPOINT = '127.0.0.1:6379'
OBSERVER_UID = 999
OBSERVER_GID = 985
WITNESS_SECONDS = 1
BROKER_SECONDS = 12
LEASE_SECONDS = 3
UNIT_SECONDS = 17
HARD_SECONDS = 18
CAPTURE_ENV = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'HOME': '/nonexistent'}
SHA = re.compile('[0-9a-f]{64}')
UUID = re.compile('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}')


def digest(text):
    check(type(text) is str and SHA.fullmatch(text) is not None)
    return text


def uint(value):
    check(type(value) is int and 0 < value < 2**63)
    return value


def keys(value, expected):
    check(type(value) is dict and set(value) == set(expected.split()))
    return value


def trusted_bytes(path, owner, mode, maximum):
    with directory(path.parent, owner) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                     os.O_CLOEXEC, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            st = os.fstat(stream.fileno())
            check(stat.S_ISREG(st.st_mode) and st.st_uid == owner and st.st_nlink == 1 and
                  stat.S_IMODE(st.st_mode) == mode and st.st_size <= maximum)
            data = stream.read(maximum + 1)
            after = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            check(os.path.samestat(st, after) and st.st_ctime_ns == after.st_ctime_ns and
                  len(data) == st.st_size)
        return data


def permit(raw, boot, now):
    p = keys(decode(raw), 'version host target boot nonce not_before_ns expires_ns backend_id '
             'backend_pid backend_start_ns net_inode names broker_endpoint broker_scope_sha256 '
             'witness_sha256 ping_sha256')
    check(p['version'] == 'celery-shadow-once-v1' and p['host'] == HOST and p['target'] == TARGET)
    check(p['boot'] == boot and UUID.fullmatch(boot) is not None)
    digest(p['nonce'])
    start, end = uint(p['not_before_ns']), uint(p['expires_ns'])
    check(start <= now and now + HARD_SECONDS * NS <= end and end - start <= 300 * NS)
    digest(p['backend_id'])
    check(uint(p['backend_pid']) <= 2**31-1)
    check(uint(p['backend_start_ns']) <= now)
    uint(p['net_inode'])
    check(type(p['names']) is list)
    destinations(tuple(p['names']))
    check(p['broker_endpoint'] == ENDPOINT)
    for field in ('broker_scope_sha256', 'witness_sha256', 'ping_sha256'):
        digest(p[field])
    return p


def claim(path, p, owner):
    # Private /run state retained until reboot. A consumed permit is not retried
    # on any later refusal, including immediate exit or crash.
    with directory(path, owner, private=True) as fd:
        name = 'consumed-' + digest(p['nonce'])
        token = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                        os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=fd)
        os.close(token)


def unit_command(p, permit_sha, began_ns):
    digest(permit_sha)
    uint(began_ns)
    pid = uint(p['backend_pid'])
    check(pid <= 2**31-1)
    # A separate launcher policy audit must qualify the actual site adapters.
    # The network namespace and IPv4 address filter are independent of argv;
    # the immutable pidbox adapter must additionally enforce the exact port.
    props = (
        'Type=exec', f'RuntimeMaxSec={UNIT_SECONDS}s', 'KillMode=control-group', 'KillSignal=SIGKILL',
        'TimeoutStopSec=1s', 'Restart=no', 'UMask=0077', 'NoNewPrivileges=yes',
        'CapabilityBoundingSet=', 'RestrictAddressFamilies=AF_UNIX AF_INET',
        'ProtectHome=yes', 'ProtectSystem=strict', 'PrivateTmp=yes', 'PrivateDevices=yes',
        'ProtectKernelTunables=yes', 'ProtectKernelModules=yes', 'ProtectControlGroups=yes',
        'RestrictSUIDSGID=yes', 'RestrictNamespaces=yes', 'IPAddressDeny=any',
        'IPAddressAllow=127.0.0.1/32', 'SocketBindDeny=any',
        'InaccessiblePaths=-/root -/home -/run/credentials -/run/docker.sock -/var/lib/docker',
        f'ReadWritePaths={DROP} {STATE}', f'NetworkNamespacePath=/proc/{pid}/ns/net',
    )
    return ['/usr/bin/systemd-run', '--unit='+UNIT, '--wait', '--collect', '--quiet'] + [
        '-p'+v for v in props] + ['/usr/bin/python3', '-IB', str(INSTALL/'celery_shadow_launcher.py'),
                                '--worker', permit_sha, str(began_ns)]


def pinned_worker(p, owner, readonly):
    # Adapters are site-local fixed executables reviewed separately, not
    # general shell runners; re-check pinned executable bodies before using.
    for key, path in (('witness_sha256', WITNESS), ('ping_sha256', PING)):
        raw = trusted_bytes(path, owner, 0o755, 256*1024)
        check(hashlib.sha256(raw).hexdigest() == p[key])
    names = destinations(tuple(p['names']))
    boot = p['boot']

    def inspect():
        code, out, err = capture([str(WITNESS)], '/', CAPTURE_ENV, WITNESS_SECONDS)
        check(code == 0 and not err)
        frame = keys(decode(out), 'boot backend workers net_inode endpoint scope_sha256')
        check(frame['boot'] == boot and frame['net_inode'] == p['net_inode'] and
              frame['endpoint'] == ENDPOINT and frame['scope_sha256'] == p['broker_scope_sha256'])
        check(tuple(frame['backend'][k] for k in ('Id','Pid','StartedNs')) ==
              tuple(p[k] for k in ('backend_id','backend_pid','backend_start_ns')))
        check(type(frame['workers']) is dict and frame['workers'].keys() == set(names))
        check(all(type(v) is list for v in frame['workers'].values()))
        return Witness(boot, frame['backend'], {k: tuple(v) for k,v in frame['workers'].items()})

    def ping(exact):
        check(exact == names)
        return capture([str(PING), '--destination='+','.join(names), '--timeout=8', '--json'],
                       '/', CAPTURE_ENV, BROKER_SECONDS)

    launched = time.monotonic()
    with leased_acquisition(DROP, owner, boot, names, inspect, ping) as result:
        if result not in ('both-ready','readiness-failed'):
            return 'unavailable'
        end = min(launched+UNIT_SECONDS, time.monotonic()+LEASE_SECONDS)
        # The staged reader observes the separate protected path. Hold the lease
        # only for the reviewed bounded collection window, with no child/fork.
        return readonly(result, end)


def entry(mode, expected_sha=None, start_text=None):
    started = time.monotonic_ns()
    wall_end = None
    if mode == '--worker':
        check(type(start_text) is str and re.fullmatch(r'[0-9]{1,19}', start_text))
        launched = uint(int(start_text))
        # A detached/late orchestrator execution cannot open a new window.
        # Accept at most the dedicated one-second unit startup margin.
        check(0 <= started-launched < (HARD_SECONDS-UNIT_SECONDS)*NS)
        wall_end = (launched+HARD_SECONDS*NS)/NS
    else:
        check(start_text is None)
    check(os.geteuid() == 0 and os.uname().nodename == HOST)
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    raw = trusted_bytes(PERMIT, 0, 0o600, 4096)
    permit_sha = hashlib.sha256(raw).hexdigest()
    if mode == '--worker':
        check(digest(expected_sha) == permit_sha)
    else:
        check(expected_sha is None)
    p = permit(raw, boot, time.time_ns())
    if mode == '--plan-only':
        # No side effects, no nonce revealed and no active site access.
        check(unit_command(p, permit_sha, started)[0] == '/usr/bin/systemd-run')
        return 'plan-valid'
    if mode == '--launch':
        # systemd, not this invocation, enforces the independent whole-cgroup
        # limit even if this parent exits. No failed unit is restarted.
        run = subprocess.run(unit_command(p, permit_sha, started), cwd='/', env=CAPTURE_ENV,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, timeout=HARD_SECONDS, check=False)
        return 'shadow-finished' if run.returncode == 0 else 'unavailable'
    check(mode == '--worker')
    cgroup = Path('/proc/self/cgroup').read_text().strip().partition('::')[2]
    check(cgroup == '/system.slice/'+UNIT)
    ns = Path('/proc/self/ns/net').stat()
    check(ns.st_ino == p['net_inode'])
    claim(STATE, p, 0)

    def lease_window(_value, end):
        # Actual readers must use the read-only leased collector. The producer
        # does not pass the lease descriptor, run SSH or publish raw evidence.
        delay = min(end, wall_end) - time.monotonic()
        check(delay > 0)
        time.sleep(delay)
        return 'shadow-window-closed'

    return pinned_worker(p, 0, lease_window)


if __name__ == '__main__':
    try:
        check((len(sys.argv) == 2 and sys.argv[1] in ('--plan-only','--launch')) or
              (len(sys.argv) == 4 and sys.argv[1] == '--worker'))
        result = entry(*sys.argv[1:])
    except (OSError, ValueError, TypeError, KeyError, OverflowError, subprocess.SubprocessError):
        result = 'unavailable'
    print(result)
    sys.exit(int(result == 'unavailable'))
