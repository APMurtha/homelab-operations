#!/usr/bin/python3 -IB
"""Fixed-path, passive site witness for isolated Celery shadow qualification.

No service APIs, signal, subprocess, sockets, or environment reads. Enrollment
attests startup broker scope; it cannot prove live DB or control subscriptions.
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
EXE = re.compile('/[A-Za-z0-9_./-]{1,200}')


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


def enrollment(obj, boot):
    require(type(obj) is dict and obj.get('version') in
            ('celery-site-witness-v1', 'celery-site-witness-signed-v2'))
    signed = obj['version'] == 'celery-site-witness-signed-v2'
    p = keys(obj, 'version boot backend_id backend_pid backend_ticks backend_start_ns '
             'net_inode pid_inode uts_inode mnt_inode worker_executable hostname scope '
             + ('worker_uids' if signed else 'worker_uid'))
    require(p['boot'] == boot)
    require(str(uuid.UUID(boot)) == boot)
    require(type(p['backend_id']) is str and HEX.fullmatch(p['backend_id']))
    require(type(p['hostname']) is str and NAME.fullmatch(p['hostname']))
    require(type(p['worker_executable']) is str and EXE.fullmatch(p['worker_executable'])
            and '..' not in Path(p['worker_executable']).parts)
    for k in ('backend_ticks', 'backend_start_ns', 'net_inode', 'pid_inode', 'mnt_inode', 'uts_inode'):
        integer(p[k])
    integer(p['backend_pid'], 2**31-1)
    if signed:
        uids = keys(p['worker_uids'], 'default dvr')
        require(len({integer(u, 2**31-1) for u in uids.values()}) == 2)
    else:
        integer(p['worker_uid'], 2**31-1)
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


def process(proc, pid, p, cgroup, role=None):
    directory = proc/str(integer(pid, 2**31-1))
    fields = bounded(directory/'stat', 4096).decode('ascii').rsplit(')', 1)[1].split()
    require(fields[0] not in ('Z','X','x'))
    require(bounded(directory/'cgroup', 8192).decode('ascii').splitlines() == ['0::'+cgroup])
    for name in ('net', 'pid', 'mnt', 'uts'):
        # These are kernel nsfs magic links, never paths supplied by enrollment.
        require(os.stat(directory/'ns'/name).st_ino == p[name+'_inode'])
    if role is not None:
        required_uid = p['worker_uids'][role] if 'worker_uids' in p else p['worker_uid']
        status = bounded(directory/'status', 16384)
        found = re.findall(rb'^Uid:\s+([0-9]+)[ \t]+([0-9]+)[ \t]+([0-9]+)[ \t]+([0-9]+)$',status,re.M)
        require(len(found)==1 and all(int(v)==required_uid for v in found[0]))
    return integer(int(fields[1]), 2**31-1), integer(int(fields[19]))


def role_from_argv(exe, args, p):
    if exe != p['worker_executable'] or b'worker' not in args or b'dispatcharr' not in args:
        return None
    require(args.count(b'worker') == 1)
    def option(short,long):
        positions = [i for i,v in enumerate(args) if v in (short,long)]
        values = [args[i+1] for i in positions if i+1<len(args)]
        values.extend(v[len(long)+1:] for v in args if v.startswith(long+b'='))
        require(len(values)==1 and len(positions)<=1)
        return values[0]
    require(option(b'-A',b'--app')==b'dispatcharr')
    name=option(b'-n',b'--hostname').decode('ascii')
    queue=option(b'-Q',b'--queues').decode('ascii')
    role, sep, host=name.partition('@')
    require(sep and role in WORKERS and host in ('%h',p['hostname']) and queue==WORKERS[role])
    return role


def sockets(dirpath):
    fdentries = []
    with os.scandir(dirpath/'fd') as it:
        for ent in it:
            require(len(fdentries) < 512)
            fdentries.append(ent.name)
    owned=set()
    for name in fdentries:
        try:
            dst=os.readlink(dirpath/'fd'/name)
        except FileNotFoundError:
            continue
        match=re.fullmatch(r'socket:\[([0-9]+)\]',dst)
        if match:
            owned.add(match[1])
    tcp=bounded(dirpath/'net'/'tcp', 256*1024).decode('ascii').splitlines()[1:]
    return any(len(row)>9 and row[3]=='01' and row[2]==TCP_LOOPBACK and row[9] in owned
               for row in map(str.split,tcp))


def gather(proc, cgroot, p):
    # Container cgroup is derived from the exact enrolled Docker identity;
    # never accept an arbitrary cgroup passed by the invoking caller.
    cg='system.slice/docker-'+p['backend_id']+'.scope'
    proc_file=cgroot/'system.slice'/('docker-'+p['backend_id']+'.scope')/'cgroup.procs'
    list_ = bounded(proc_file, 4096).split()
    require(1 <= len(list_) <= 128 and len(set(list_)) == len(list_) and
            all(b.isdigit() for b in list_))
    members={integer(int(b),2**31-1) for b in list_}
    require(p['backend_pid'] in members)
    backend=process(proc,p['backend_pid'],p,'/'+cg)
    require(backend[1]==p['backend_ticks'])
    candidates={}
    for pid in members:
        path=proc/str(pid)
        try:
            exe=os.readlink(path/'exe')
            if exe != p['worker_executable']:
                continue
            raw=bounded(path/'cmdline',8192)
            require(raw.endswith(b'\0'))
            role=role_from_argv(exe, raw[:-1].split(b'\0'),p)
            if role is None:
                continue
            ppid,ticks=process(proc,pid,p,'/'+cg,role=role)
        except FileNotFoundError:
            continue  # transient child cannot satisfy required two masters
        candidates[pid]=(role,ppid,ticks)
    result={}
    for pid,(role,ppid,ticks) in candidates.items():
        if ppid in candidates:
            require(candidates[ppid][0]==role)
            continue  # prefork child carries parent's same command line
        require(role+'@'+p['hostname'] not in result and ppid in members)
        require(os.readlink(proc/str(ppid)/'exe') in ('/usr/bin/dash','/bin/dash'))
        process(proc,ppid,p,'/'+cg,role=role)
        require(sockets(proc/str(pid)))
        result[role+'@'+p['hostname']]=[pid,ticks]
    require(set(result)=={role+'@'+p['hostname'] for role in WORKERS})
    require(process(proc,p['backend_pid'],p,'/'+cg)==backend)
    for full,(pid,ticks) in result.items():
        path = proc/str(pid)
        role, ppid, _ = candidates[pid]
        require(process(proc,pid,p,'/'+cg,role=role)==(ppid,ticks))
        raw=bounded(path/'cmdline',8192)
        require(raw.endswith(b'\0') and role_from_argv(os.readlink(path/'exe'),
                    raw[:-1].split(b'\0'),p)==role and full==role+'@'+p['hostname'])
        require(sockets(path))
    require(set(bounded(proc_file, 4096).split()) == set(list_))
    return result


def inspect(enrollment_path, health_path, proc=PROC, cgroup=CGROUPS, owner=0, clock=time.time_ns):
    boot=bounded(proc/'sys/kernel/random/boot_id',64).decode('ascii').strip()
    p=enrollment(trusted_read(enrollment_path,owner),boot)
    start=clock()
    b=health(trusted_read(health_path,owner),p,start)
    w=gather(proc,cgroup,p)
    require(enrollment(trusted_read(enrollment_path,owner),boot)==p)
    require(health(trusted_read(health_path,owner),p,clock())==b)
    require(bounded(proc/'sys/kernel/random/boot_id',64).decode('ascii').strip()==boot)
    return {'boot':boot, 'backend':b, 'workers':w, 'net_inode':p['net_inode'],
            'endpoint':ENDPOINT, 'scope_sha256':hashlib.sha256(
                json.dumps(SCOPE, sort_keys=True, separators=(',',':')).encode()).hexdigest()}


def main():
    try:
        require(len(sys.argv)==1 and os.geteuid()==0 and sys.flags.isolated and
                Path(__file__)==ENROLLMENT.parent/'witness')
        frame=inspect(ENROLLMENT,HEALTH)
    except (OSError, ValueError, TypeError, IndexError, KeyError, OverflowError, RecursionError):
        return 1
    print(json.dumps(frame,sort_keys=True,separators=(',',':')))
    return 0


if __name__=='__main__':
    sys.exit(main())
