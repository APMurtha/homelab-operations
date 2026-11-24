"""Fixed one-shot host supervisor for a separately provisioned shadow check.

No installation or listener. No issue-supplied values, shell execution, service
discovery, Docker socket or credentials. Required site adapters are deliberately
not enrolled by this draft; without their reviewed hashes it cannot emit ready.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
from types import ModuleType

def trust_flat_entrypoint():
    """Python -I excludes the script directory; admit only the pinned package."""
    package = Path('/opt/samwise-celery-shadow')
    check_path = Path(__file__)
    if (os.geteuid() != 0 or not sys.flags.isolated or
            check_path != package/'celery_shadow_launcher.py'):
        raise ValueError('untrusted_entry')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in package.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                            os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
            meta = os.fstat(fd)
            if meta.st_uid != 0 or meta.st_mode & 0o022:
                raise ValueError('untrusted_entry')
        # Read the exact vetted .py files, then load from those bytes without
        # consulting importlib filesystem discovery (packages, .so or pycache).
        ordered = ('ops_protocol', 'celery_handoff', 'dispatcharr_project', 'celery_readiness')
        sources = {}
        for name in (*ordered, 'celery_shadow_launcher'):
            filename = name + '.py'
            source_fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                                os.O_CLOEXEC, dir_fd=fd)
            with os.fdopen(source_fd,'rb') as stream:
                before = os.fstat(stream.fileno())
                if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or
                        stat.S_IMODE(before.st_mode) != 0o644 or before.st_nlink != 1 or
                        before.st_size > 256*1024):
                    raise ValueError('untrusted_entry')
                data = stream.read(256*1024+1)
                after = os.stat(filename, dir_fd=fd, follow_symlinks=False)
                if (not os.path.samestat(before,after) or before.st_ctime_ns != after.st_ctime_ns or
                        len(data) != before.st_size):
                    raise ValueError('untrusted_entry')
                sources[name] = data
        for name in ordered:
            if name in sys.modules:
                raise ValueError('untrusted_entry')
            module = ModuleType(name)
            module.__file__ = str(package/(name+'.py'))
            sys.modules[name] = module
            exec(compile(sources[name], module.__file__, 'exec', dont_inherit=True),
                 module.__dict__)
    finally:
        os.close(fd)


try:
    if __name__ == '__main__':
        trust_flat_entrypoint()
    from celery_handoff import ANCHOR, current
    from celery_readiness import Witness, capture, destinations, leased_acquisition
    from dispatcharr_project import directory
    from ops_protocol import NS, check, decode
except (OSError, ValueError, ImportError, SyntaxError):
    if __name__ != '__main__':
        raise
    print('unavailable')
    sys.exit(1)

HOST = 'rivendell'
TARGET = 'rivendell-dispatcharr'
STAGE_HOST = 'staging'
STAGE_TARGET = 'samwise-staging-dispatcharr-fixture'
PRODUCTION_PERMIT = 'celery-shadow-once-v1'
STAGE_PERMIT = 'celery-shadow-signed-fixture-once-v1'
UNIT = 'samwise-celery-shadow-once.service'
BROKER_UNIT = 'samwise-celery-shadow-broker.service'
INSTALL = Path('/opt/samwise-celery-shadow')
STATE = Path('/run/samwise-celery-shadow')
DROP = Path('/run/samwise-observations/celery-v1')
WITNESS = INSTALL / 'witness'
PING = INSTALL / 'pidbox-ping'
WITNESS_ENROLL = INSTALL / 'witness-enrollment.json'
PIDBOX_ENROLL = INSTALL / 'pidbox-enrollment.json'
SIGNED_ORIGIN = 'celery-site-signed-origin-v2'
BROKER_SCOPE = '191dd4b1462369703511b422e36ee4c7bd4350f23ff963c77f7f1d9b8b3bc6d7'
PERMIT = INSTALL / 'one-shot.json'
STAGE_PASSWD = INSTALL / 'stage-fixture.passwd'
STAGE_GROUP = INSTALL / 'stage-fixture.group'
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


def permit(raw, boot, now, *, node=HOST):
    p = keys(decode(raw), 'version host target boot nonce not_before_ns expires_ns backend_id '
             'backend_pid backend_start_ns net_inode names broker_endpoint broker_scope_sha256 '
             'witness_sha256 ping_sha256 witness_enrollment_sha256 pidbox_enrollment_sha256')
    check(node in (HOST, STAGE_HOST) and p['host'] == node)
    expected = (PRODUCTION_PERMIT, TARGET) if node == HOST else (STAGE_PERMIT, STAGE_TARGET)
    check((p['version'], p['target']) == expected)
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
    check(p['broker_endpoint'] == ENDPOINT and p['broker_scope_sha256'] == BROKER_SCOPE)
    for field in ('broker_scope_sha256', 'witness_sha256', 'ping_sha256',
                  'witness_enrollment_sha256', 'pidbox_enrollment_sha256'):
        digest(p[field])
    return p


OBSERVER = 'samwise-observe'


def observer_ids(passwd, groups):
    users = [line.split(':') for line in passwd.decode('utf-8').splitlines()]
    owns = [row for row in users if len(row) == 7 and row[0] == OBSERVER]
    check(len(owns) == 1 and owns[0][2:4] == [str(OBSERVER_UID),str(OBSERVER_GID)] and
          owns[0][-1] == '/opt/samwise-observe/login')
    check(sum(len(row) == 7 and row[2] == str(OBSERVER_UID) for row in users) == 1)
    check(sum(len(row) == 7 and row[3] == str(OBSERVER_GID) for row in users) == 1)
    memberships = [line.split(':') for line in groups.decode('utf-8').splitlines()]
    named = [row for row in memberships if len(row) == 4 and row[0] == OBSERVER]
    check(len(named) == 1 and named[0][2] == str(OBSERVER_GID) and
          named[0][3] in ('',OBSERVER))
    check(sum(len(row) == 4 and row[2] == str(OBSERVER_GID) for row in memberships) == 1)
    check(all(len(row) != 4 or OBSERVER not in row[3].split(',') or
              row[2] == str(OBSERVER_GID) for row in memberships))


def evidence_ids(outer, drop):
    check((outer.st_uid,outer.st_gid,stat.S_IMODE(outer.st_mode)) ==
          (0,OBSERVER_GID,0o750))
    check((drop.st_uid,drop.st_gid,stat.S_IMODE(drop.st_mode)) ==
          (0,OBSERVER_GID,0o2750))


def preflight_observer(*, stage_launch=False):
    # Only local files, no NSS, DNS or call to the active SSH observer.
    passwd, group = ((STAGE_PASSWD, STAGE_GROUP) if stage_launch else
                     (Path('/etc/passwd'), Path('/etc/group')))
    observer_ids(trusted_bytes(passwd,0,0o644,128*1024),
                 trusted_bytes(group,0,0o644,128*1024))
    with directory(DROP.parent, 0) as outer, directory(DROP, 0) as drop:
        evidence_ids(os.fstat(outer),os.fstat(drop))
        current(drop, ANCHOR, 0, OBSERVER_GID)


def claim(path, p, owner):
    # Private /run state retained until reboot. A consumed permit is not retried
    # on any later refusal, including immediate exit or crash.
    with directory(path, owner, private=True) as fd:
        name = 'consumed-' + digest(p['nonce'])
        token = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                        os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=fd)
        os.close(token)


def unit_command(p, permit_sha, began_ns, *, attestor=False):
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
    if attestor:
        # No IP sockets and no target namespace in this service. Root uses
        # local systemd IPC only to start the separately bounded broker unit.
        replace = ('CapabilityBoundingSet=', 'RestrictAddressFamilies=',
                   'IPAddressAllow=', 'NetworkNamespacePath=')
        props = tuple(prop for prop in props if not prop.startswith(replace)) + (
            'PrivateNetwork=yes', 'CapabilityBoundingSet=CAP_SYS_PTRACE',
            'RestrictAddressFamilies=AF_UNIX', 'SystemCallFilter=~@debug',
        )
    if p.get('host') == STAGE_HOST:
        check(attestor and (p['version'],p['target']) == (STAGE_PERMIT,STAGE_TARGET))
        # Never edit or shadow another account on the actual stage host.
        # Only the transient VM180 fixture gets the synthetic principals.
        props += (f'BindReadOnlyPaths={STAGE_PASSWD}:/etc/passwd {STAGE_GROUP}:/etc/group',)
    return ['/usr/bin/systemd-run', '--unit='+UNIT, '--wait', '--collect', '--quiet'] + [
        '-p'+v for v in props] + ['/usr/bin/python3', '-IB', str(INSTALL/'celery_shadow_launcher.py'),
                                '--worker', permit_sha, str(began_ns)]


def broker_command(p, names, nonce, deadline_ns, now_ns=None):
    check(destinations(names) == tuple(p['names']))
    pid, cutoff = uint(p['backend_pid']), uint(deadline_ns)
    check(pid <= 2**31-1)
    check(now_ns is None or type(now_ns) is int)
    left = cutoff - (time.monotonic_ns() if now_ns is None else now_ns)
    check(0 < left <= BROKER_SECONDS*NS)
    # The fixed helper independently verifies the same absolute deadline.
    # Leave no reserve for a retry, and never place a permit/lease in this unit.
    props = (
        'Type=exec', f'RuntimeMaxSec={left//1000}us', 'KillMode=control-group',
        'KillSignal=SIGKILL', 'TimeoutStopSec=1s', 'Restart=no', 'UMask=0077',
        'NoNewPrivileges=yes', 'CapabilityBoundingSet=', 'RestrictAddressFamilies=AF_INET',
        'ProtectHome=yes', 'ProtectSystem=strict', 'PrivateTmp=yes', 'PrivateDevices=yes',
        'ProtectKernelTunables=yes', 'ProtectKernelModules=yes', 'ProtectControlGroups=yes',
        'RestrictSUIDSGID=yes', 'RestrictNamespaces=yes', 'IPAddressDeny=any',
        'IPAddressAllow=127.0.0.1/32', 'SocketBindDeny=any',
        'InaccessiblePaths=-/root -/home -/run/credentials -/run/docker.sock -/var/lib/docker '
        f'{DROP} {STATE} -/run/systemd -/run/dbus',
        f'NetworkNamespacePath=/proc/{pid}/ns/net',
    )
    return ['/usr/bin/systemd-run', '--unit='+BROKER_UNIT, '--wait', '--pipe', '--collect',
            '--quiet', *('-p'+v for v in props), '/usr/bin/python3', '-IBS',str(PING),
            '--destination='+','.join(names),'--timeout=8','--json','--challenge='+digest(nonce),
            '--deadline-ns='+str(cutoff)]


def approved_module(name, expected, owner):
    # Exact source bytes only (root metadata and permit-pinned enrollment), no
    # ambient package discovery or possibility of stale cached bytecode.
    src = INSTALL/(name+'.py')
    data=trusted_bytes(src,owner,0o644,128*1024)
    check(hashlib.sha256(data).hexdigest()==digest(expected))
    module=ModuleType(name)
    module.__file__=str(src)
    exec(compile(data,module.__file__,'exec',dont_inherit=True),module.__dict__)
    return module


def kernel_ids(proc, name, mapped, broker):
    host,guest=mapped[name]
    expected=broker['workers'][name]
    check(type(expected) is list and len(expected)==2 and host==expected[0])
    uid=uint(broker['worker_uids'][name])
    st=proc/str(host)/'status'
    with st.open('rb') as stream:
        raw=stream.read(16385)
    check(len(raw)<=16384)
    rows=re.findall(rb'^Uid:[ 	]+([0-9]+)[ 	]+([0-9]+)[ 	]+([0-9]+)[ 	]+([0-9]+)$',
                    raw,re.M)
    check(len(rows)==1 and all(int(value)==uid for value in rows[0]))
    return (host,guest,expected[1])


def signed_plan(mapping, origin, names, p, broker, proc=Path('/proc')):
    check(type(broker.get('worker_uids')) is dict and
          type(broker.get('public_keys')) is dict and
          broker['worker_uids'].keys()==broker['public_keys'].keys()==set(names))
    check(len({uint(i) for i in broker['worker_uids'].values()})==2)
    validate=getattr(mapping, 'signed_endpoint')
    mapped=validate(proc,broker)
    check(list(broker['guest_init'])[0]==p['backend_pid'] and
          broker['guest_cgroup']=='/system.slice/docker-'+p['backend_id']+'.scope')
    identities={n:kernel_ids(proc,n,mapped,broker) for n in names}
    check(validate(proc,broker)==mapped)
    return {n:origin.incarnation(site=p['host'],boot=p['boot'],backend=p['backend_id'],
                                  host_pid=v[0],guest_pid=v[1],ticks=v[2])
            for n,v in identities.items()}


def checked_enrollment(p, owner):
    for key,path in (('witness_enrollment_sha256', WITNESS_ENROLL),
                     ('pidbox_enrollment_sha256', PIDBOX_ENROLL)):
        raw = trusted_bytes(path, owner, 0o600, 8192)
        check(hashlib.sha256(raw).hexdigest() == p[key])
    broker = decode(raw)  # pidbox enrollment is last.
    check(type(broker) is dict)
    if p['host'] == STAGE_HOST:
        # The exact deployed bytes run in both places; staging cannot turn
        # an unsigned/no-origin fixture into a readiness claim.
        check(broker.get('version') == SIGNED_ORIGIN)
    return broker


def pinned_worker(p, owner, readonly, deadline_ns=None, *, broker_sender=None):
    # Adapters are site-local fixed executables reviewed separately, not
    # general shell runners; re-check pinned executable bodies before using.
    for key, path in (('witness_sha256', WITNESS), ('ping_sha256', PING)):
        raw = trusted_bytes(path, owner, 0o755, 256*1024)
        check(hashlib.sha256(raw).hexdigest() == p[key])
    names = destinations(tuple(p['names']))
    boot = p['boot']
    broker = checked_enrollment(p, owner)
    check(type(broker) is dict)
    signed = broker.get('version')==SIGNED_ORIGIN
    origin = mapping = None
    if signed:
        # Neither ordinary Redis replies nor matching pre/post socket samples are
        # a source-authentication fallback.
        check(deadline_ns is not None and callable(broker_sender))
        origin=approved_module('celery_signed_origin',broker['launcher_origin_sha256'],owner)
        mapping=approved_module('celery_host_topology',broker['launcher_topology_sha256'],owner)
    elif 'version' in broker:
        check(broker['version']=='celery-site-pidbox-v1')
    def budget(limit):
        if deadline_ns is None:
            return limit
        remaining=(deadline_ns-time.monotonic_ns())/NS
        check(remaining>0)
        return min(limit,remaining)
    incarnation=None
    check(type(broker) is dict and broker.get('boot')==boot and
          broker.get('net_inode')==p['net_inode'] and
          broker.get('scope_sha256')==BROKER_SCOPE and
          type(broker.get('workers')) is dict and broker['workers'].keys()==set(names))

    def inspect():
        nonlocal incarnation
        check(checked_enrollment(p, owner)==broker)
        code, out, err = capture([str(WITNESS)], '/', CAPTURE_ENV, budget(WITNESS_SECONDS))
        check(code == 0 and not err)
        frame = keys(decode(out), 'boot backend workers net_inode endpoint scope_sha256')
        check(frame['boot'] == boot and frame['net_inode'] == p['net_inode'] and
              frame['endpoint'] == ENDPOINT and frame['scope_sha256'] == p['broker_scope_sha256'])
        check(tuple(frame['backend'][k] for k in ('Id','Pid','StartedNs')) ==
              tuple(p[k] for k in ('backend_id','backend_pid','backend_start_ns')))
        check(type(frame['workers']) is dict and frame['workers']==broker['workers'])
        check(all(type(v) is list for v in frame['workers'].values()))
        if signed:
            current_ids=signed_plan(mapping,origin,names,p,broker)
            check(incarnation is None or current_ids==incarnation)
            incarnation=current_ids
            budget(WITNESS_SECONDS)
        return Witness(boot, frame['backend'], {k: tuple(v) for k,v in frame['workers'].items()})

    def ping(exact):
        check(exact == names and checked_enrollment(p, owner)==broker)
        argv=[str(PING), '--destination='+','.join(names), '--timeout=8', '--json']
        if not signed:
            return capture(argv,'/',CAPTURE_ENV,budget(BROKER_SECONDS))
        check(incarnation is not None)
        nonce=origin.challenge()
        code,out,err=broker_sender(exact, nonce, budget(BROKER_SECONDS))
        check(code==0 and not err and type(out) is bytes and 0<len(out)<=16384)
        proved=origin.qualify(decode(out),list(names),broker['public_keys'],
                              incarnation,nonce,BROKER_SCOPE)
        budget(WITNESS_SECONDS)
        return (0,json.dumps(proved,separators=(',',':')).encode('ascii'),b'')

    launched = time.monotonic()
    with leased_acquisition(DROP, owner, boot, names, inspect, ping, deadline_ns=deadline_ns) as result:
        if result not in ('both-ready','readiness-failed'):
            return 'unavailable'
        end = min(launched+UNIT_SECONDS, time.monotonic()+LEASE_SECONDS,
                  deadline_ns/NS if deadline_ns is not None else float('inf'))
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
    node = os.uname().nodename
    check(os.geteuid() == 0 and node in (HOST, STAGE_HOST))
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    raw = trusted_bytes(PERMIT, 0, 0o600, 4096)
    permit_sha = hashlib.sha256(raw).hexdigest()
    if mode == '--worker':
        check(digest(expected_sha) == permit_sha)
    else:
        check(expected_sha is None)
    p = permit(raw, boot, time.time_ns(), node=node)
    attestor = False
    if node == STAGE_HOST or mode != '--plan-only':
        # Legacy production plan-only performs no site access. All executions
        # pin the same reviewed enrollment before selecting a unit shape.
        attestor = checked_enrollment(p, 0).get('version') == SIGNED_ORIGIN
    if mode == '--plan-only':
        # No side effects, no nonce revealed and no active site access.
        check(unit_command(p, permit_sha, started, attestor=attestor)[0] == '/usr/bin/systemd-run')
        return 'plan-valid'
    if mode == '--launch':
        if node == STAGE_HOST:
            preflight_observer(stage_launch=True)
        else:
            preflight_observer()
        # systemd, not this invocation, enforces the independent whole-cgroup
        # limit even if this parent exits. No failed unit is restarted.
        left = HARD_SECONDS - (time.monotonic_ns()-started)/NS
        check(0 < left <= HARD_SECONDS)
        run = subprocess.run(unit_command(p, permit_sha, started, attestor=attestor), cwd='/', env=CAPTURE_ENV,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, timeout=left, check=False)
        return 'shadow-finished' if run.returncode == 0 else 'unavailable'
    check(mode == '--worker')
    cgroup = Path('/proc/self/cgroup').read_text().strip().partition('::')[2]
    check(cgroup == '/system.slice/'+UNIT)
    ns = Path('/proc/self/ns/net').stat()
    if attestor:
        check(ns.st_ino != p['net_inode'])
        # The manager confines this service before Python starts. Refuse an
        # accidentally shared host network even if the cgroup name matches.
        interfaces = [line.split(':',1)[0].strip() for line in
                      Path('/proc/self/net/dev').read_text().splitlines()[2:]]
        check(interfaces == ['lo'])
    else:
        check(ns.st_ino == p['net_inode'])
    preflight_observer()
    claim(STATE, p, 0)

    def lease_window(_value, end):
        # Actual readers must use the read-only leased collector. The producer
        # does not pass the lease descriptor, run SSH or publish raw evidence.
        delay = min(end, wall_end) - time.monotonic()
        check(delay > 0)
        time.sleep(delay)
        return 'shadow-window-closed'

    def send(names, nonce, timeout):
        began = time.monotonic_ns()
        cutoff = min(began + int(timeout*NS), int(wall_end*NS))
        args = broker_command(p, names, nonce, cutoff, began)
        return capture(args, '/', CAPTURE_ENV, (cutoff-began)/NS)

    return pinned_worker(p, 0, lease_window, int(wall_end*NS),
                         broker_sender=send if attestor else None)


if __name__ == '__main__':
    try:
        check((len(sys.argv) == 2 and sys.argv[1] in ('--plan-only','--launch')) or
              (len(sys.argv) == 4 and sys.argv[1] == '--worker'))
        result = entry(*sys.argv[1:])
    except (OSError, ValueError, TypeError, KeyError, OverflowError, subprocess.SubprocessError):
        result = 'unavailable'
    print(result)
    sys.exit(int(result == 'unavailable'))
