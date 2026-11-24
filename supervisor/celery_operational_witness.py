#!/usr/bin/python3 -IB
"""Unprivileged-metadata witness for the trusted application boundary.

Read only selected host procfs metadata and the joined namespace TCP table.
This corroborates operational placement, not reply origin or FD ownership.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import uuid

ENROLLMENT = Path('/opt/samwise-celery-shadow/witness-enrollment.json')
HEALTH = Path('/run/samwise-celery-shadow/backend-witness.json')
PROC = Path('/proc')
CGROUPS = Path('/sys/fs/cgroup')
ENDPOINT = '127.0.0.1:6379'
TCP_LOOPBACK = '0100007F:18EB'
SOURCE_AGE_NS = 45 * 10**9
WORKERS = {'default': 'celery', 'dvr': 'dvr'}
SCOPE = {'endpoint': ENDPOINT, 'database': 0, 'exchange': 'celery.pidbox',
         'reply_exchange': 'reply.celery.pidbox', 'fanout_prefix': '/0.',
         'fanout_patterns': True, 'keyprefix': '', 'serializer': 'json'}
HEX = re.compile('[0-9a-f]{64}')
NAME = re.compile('[A-Za-z0-9_.-]{1,253}')
COMMAND = re.compile(r'(?:/[A-Za-z0-9_./-]{1,200}|celery)')
VERSION = 'celery-operational-witness-v1'


def require(condition):
    if not condition:
        raise ValueError('witness refused')


def keys(obj, names):
    require(type(obj) is dict and set(obj) == set(names.split()))
    return obj


def integer(x, limit=2**63-1):
    require(type(x) is int and 0 < x <= limit)
    return x


def sanitized_json(data):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result)
            result[k] = v
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False))


def trusted_read(path, owner):
    """Root-owned single-link state below non-writable, non-link ancestors."""
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                            os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
            st = os.fstat(fd)
            require(st.st_uid in (0, owner) and
                    (not st.st_mode & 0o022 or
                     (part == 'tmp' and st.st_uid == 0 and st.st_mode & stat.S_ISVTX)))
        original = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW |
                           os.O_CLOEXEC, dir_fd=fd)
        with os.fdopen(original, 'rb') as io:
            before = os.fstat(io.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_uid == owner and
                    stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1
                    and 0 < before.st_size <= 8192)
            data = io.read(8193)
            after = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            require(os.path.samestat(before, after) and
                    before.st_ctime_ns == after.st_ctime_ns and len(data) == before.st_size)
            return sanitized_json(data)
    finally:
        os.close(fd)


def bounded(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as io:
        require(stat.S_ISREG(os.fstat(io.fileno()).st_mode))
        data = io.read(limit+1)
    require(len(data) <= limit)
    return data


def pair(v):
    require(type(v) is list and len(v) == 2)
    return integer(v[0], 2**31-1), integer(v[1])


def enrollment(obj, boot):
    p = keys(obj, 'version boot backend_id backend_pid backend_ticks backend_start_ns '
             'net_inode hostname worker_uid worker_command workers broker broker_uid scope')
    require(p['version'] == VERSION and p['boot'] == boot and str(uuid.UUID(boot)) == boot)
    require(type(p['backend_id']) is str and HEX.fullmatch(p['backend_id']))
    require(type(p['hostname']) is str and NAME.fullmatch(p['hostname']))
    require(type(p['worker_command']) is str and COMMAND.fullmatch(p['worker_command'])
            and '..' not in Path(p['worker_command']).parts)
    for k in ('backend_ticks', 'backend_start_ns', 'net_inode'):
        integer(p[k])
    for k in ('backend_pid', 'worker_uid', 'broker_uid'):
        integer(p[k], 2**31-1)
    full = {role+'@'+p['hostname'] for role in WORKERS}
    require(type(p['workers']) is dict and set(p['workers']) == full)
    enrolled = [p['backend_pid'], pair(p['broker'])[0], *[pair(v)[0] for v in p['workers'].values()]]
    require(len(set(enrolled)) == len(enrolled))
    require(p['scope'] == SCOPE and type(p['scope']['database']) is int and
            type(p['scope']['fanout_patterns']) is bool)
    return p


def health(row, p, now):
    keys(row, 'boot sampled_ns backend')
    require(row['boot'] == p['boot'])
    b = keys(row['backend'], 'Name Id Status Running Pid StartedNs Health HealthEndNs HealthExitCode')
    require(b['Name'] == '/dispatcharr' and b['Id'] == p['backend_id'] and
            b['Status'] == 'running' and b['Running'] is True and
            integer(b['Pid']) == p['backend_pid'] and integer(b['StartedNs']) == p['backend_start_ns'] and
            b['Health'] == 'healthy' and type(b['HealthExitCode']) is int and b['HealthExitCode'] == 0)
    require(b['StartedNs'] <= integer(b['HealthEndNs']) <= integer(row['sampled_ns']) <= now and
            now - b['HealthEndNs'] < SOURCE_AGE_NS)
    return b


def namespace_ids(proc, pid):
    status = bounded(proc/str(pid)/'status', 16384)
    specs = re.findall(rb'^NSpid:[ \t]+([0-9]+(?:[ \t]+[0-9]+)*)$', status, re.M)
    require(len(specs) == 1)
    result = tuple(integer(int(n), 2**31-1) for n in specs[0].split())
    require(result[0] == pid)
    return result


def process(proc, pid, cgroup, uid=None):
    folder = proc/str(pid)
    prefix, tail = bounded(folder/'stat', 4096).rsplit(b')', 1)
    fields = tail.split()
    require(int(prefix.split(b' ', 1)[0]) == pid and fields[0] not in (b'Z', b'X', b'x'))
    require(bounded(folder/'cgroup', 8192).splitlines() == [b'0::'+cgroup.encode('ascii')])
    if uid is not None:
        status = bounded(folder/'status', 16384)
        rows = re.findall(rb'^Uid:[ \t]+([0-9]+)[ \t]+([0-9]+)[ \t]+([0-9]+)[ \t]+([0-9]+)$',
                          status, re.M)
        require(len(rows) == 1 and tuple(map(int, rows[0])) == (uid,)*4)
    return integer(int(fields[1]), 2**31-1), integer(int(fields[19]))


def argv(proc, pid):
    raw = bounded(proc/str(pid)/'cmdline', 8192)
    require(not raw or raw.endswith(b'\0'))
    return raw[:-1].split(b'\0') if raw else []


def worker_role(args, p):
    if not args or args[0] != p['worker_command'].encode('ascii') or b'worker' not in args:
        return None
    require(args.count(b'worker') == 1)

    def option(short, long):
        values = [args[i+1] for i, v in enumerate(args[:-1]) if v in (short, long)]
        values.extend(v[len(long)+1:] for v in args if v.startswith(long+b'='))
        require(len(values) == 1 and args[-1] not in (short, long))
        return values[0]

    require(option(b'-A', b'--app') == b'dispatcharr')
    role, sep, host = option(b'-n', b'--hostname').decode('ascii').partition('@')
    require(sep and role in WORKERS and host in ('%h', p['hostname'])
            and option(b'-Q', b'--queues') == WORKERS[role].encode('ascii'))
    return role


def broker_title(args):
    # Redis names its actual daemon process using its bound endpoint.
    if len(args) == 1:
        return args[0].rsplit(b'/', 1)[-1] == b'redis-server 127.0.0.1:6379'
    # Process titles may leave trailing NUL padding in procfs, but no other
    # arguments can stand in for the exact Redis bind and port.
    return bool(args) and all(not a for a in args[1:]) and broker_title(args[:1])


def members_from(path):
    raw = bounded(path, 4096).split()
    require(1 <= len(raw) <= 128 and all(v.isdigit() for v in raw))
    members = {integer(int(v), 2**31-1) for v in raw}
    require(len(members) == len(raw))
    return members


def gather(proc, cgroot, p):
    cg = '/system.slice/docker-'+p['backend_id']+'.scope'
    path = cgroot/cg.lstrip('/')/'cgroup.procs'
    members = members_from(path)
    require({p['backend_pid'], pair(p['broker'])[0], *[pair(v)[0] for v in p['workers'].values()]} <= members)
    backend = process(proc, p['backend_pid'], cg)
    require(backend[1] == p['backend_ticks'] and namespace_ids(proc, 1) == (1,))
    backend_ns = namespace_ids(proc, p['backend_pid'])
    require(len(backend_ns) == 2 and backend_ns[1] == 1)
    broker_pid, broker_ticks = pair(p['broker'])
    require(broker_title(argv(proc, broker_pid)))
    broker = process(proc, broker_pid, cg, p['broker_uid'])
    require(broker[1] == broker_ticks)
    broker_ns = namespace_ids(proc, broker_pid)
    require(len(broker_ns) == 2 and broker_ns[1] != 1)
    candidates = {}
    for pid in members:
        try:
            role = worker_role(argv(proc, pid), p)
            if role is not None:
                ppid, ticks = process(proc, pid, cg, p['worker_uid'])
                candidates[pid] = (role, ppid, ticks)
        except FileNotFoundError:
            # A transient task which disappears cannot confer readiness.
            require(pid not in {pair(v)[0] for v in p['workers'].values()})

    result = {}
    for pid, (role, ppid, ticks) in candidates.items():
        if ppid in candidates:
            require(candidates[ppid][0] == role)
            continue
        name = role+'@'+p['hostname']
        require(name not in result and ppid in members)
        result[name] = [pid, ticks]
    require(result == p['workers'])
    watched_ns = {pid: namespace_ids(proc,pid) for pid,_ in result.values()}
    require(all(len(ns) == 2 for ns in watched_ns.values()) and
            len({backend_ns[1], broker_ns[1], *[ns[1] for ns in watched_ns.values()]}) == 4)
    require(process(proc, p['backend_pid'], cg) == backend and
            broker_title(argv(proc, broker_pid)) and process(proc, broker_pid, cg, p['broker_uid']) == broker)
    for name, (pid, ticks) in result.items():
        role, ppid, _ = candidates[pid]
        require(process(proc,pid,cg,p['worker_uid']) == (ppid,ticks)
                and worker_role(argv(proc,pid),p) == role and name == role+'@'+p['hostname'])
    require(members_from(path) == members and namespace_ids(proc,1) == (1,) and
            namespace_ids(proc,p['backend_pid']) == backend_ns and namespace_ids(proc,broker_pid) == broker_ns and
            all(namespace_ids(proc,pid) == ns for pid,ns in watched_ns.items()))
    return result


def tcp_table(path, addr_len):
    lines = bounded(path, 128*1024).splitlines()
    require(lines and b'local_address' in lines[0] and 0 < len(lines) <= 513)
    shape = re.compile(rb'[0-9A-F]{'+str(addr_len).encode()+rb'}:[0-9A-F]{4}')
    rows = []
    for line in lines[1:]:
        c = line.split()
        require(len(c) >= 10 and shape.fullmatch(c[1]) and shape.fullmatch(c[2]) and
                re.fullmatch(rb'[0-9A-F]{2}', c[3]) and c[7].isdigit() and c[9].isdigit())
        rows.append((c[1], c[2], c[3], int(c[7]), int(c[9])))
    return rows


def endpoint(proc, p):
    # Only our own namespace link and TCP tables; foreign proc links need
    # privilege and would not authenticate a pidbox publisher in any event.
    require((proc/'self/ns/net').stat().st_ino == p['net_inode'])
    v4 = tcp_table(proc/'self/net/tcp', 8)
    v6 = tcp_table(proc/'self/net/tcp6', 32)
    port = b':18EB'
    address = TCP_LOOPBACK.encode()
    require(not any(a.endswith(port) or b.endswith(port) for a,b,_,_,_ in v6))
    listeners = [(a,uid,ino) for a,_,s,uid,ino in v4 if a.endswith(port) and s == b'0A']
    require(len(listeners) == 1 and listeners[0][:2] == (address,p['broker_uid']) and listeners[0][2] > 0)
    outgoing, incoming = set(), set()
    for a,b,s,uid,ino in v4:
        if not (a.endswith(port) or b.endswith(port)) or s != b'01':
            continue
        require(ino > 0)
        if b == address:
            require(a.startswith(b'0100007F:') and uid == p['worker_uid'] and (a,b) not in outgoing)
            outgoing.add((a,b))
        elif a == address:
            require(b.startswith(b'0100007F:') and uid == p['broker_uid'] and (b,a) not in incoming)
            incoming.add((b,a))
        else:
            require(False)
    require(len(outgoing) >= 2 and outgoing == incoming)


def inspect(enrollment_path, health_path, proc=PROC, cgroup=CGROUPS, owner=0, clock=time.time_ns):
    boot = bounded(proc/'sys/kernel/random/boot_id', 64).decode('ascii').strip()
    p = enrollment(trusted_read(enrollment_path, owner), boot)
    b = health(trusted_read(health_path, owner), p, clock())
    endpoint(proc,p)
    workers = gather(proc,cgroup,p)
    endpoint(proc,p)
    require(enrollment(trusted_read(enrollment_path,owner),boot) == p)
    require(health(trusted_read(health_path,owner),p,clock()) == b)
    require(bounded(proc/'sys/kernel/random/boot_id',64).decode('ascii').strip() == boot)
    return {'boot':boot, 'backend':b, 'workers':workers, 'net_inode':p['net_inode'],
            'endpoint':ENDPOINT, 'scope_sha256':hashlib.sha256(
                json.dumps(SCOPE,sort_keys=True,separators=(',',':')).encode()).hexdigest()}


def main():
    try:
        require(len(sys.argv) == 1 and os.geteuid() == 0 and sys.flags.isolated
                and Path(__file__) == ENROLLMENT.parent/'witness')
        status = bounded(PROC/'self/status',16384)
        require(all(re.search(rb'^'+cap+rb':[ \t]+0{16}$', status, re.M)
                    for cap in (b'CapEff',b'CapPrm')))
        frame = inspect(ENROLLMENT,HEALTH)
    except (OSError, ValueError, TypeError, IndexError, KeyError, OverflowError, RecursionError):
        return 1
    print(json.dumps(frame,sort_keys=True,separators=(',',':')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
