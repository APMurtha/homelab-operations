#!/usr/bin/python3 -IBS
"""Fixed candidate pidbox adapter. Requires a reviewed isolated broker topology.

No caller-supplied hosts, DBs, queues, credentials or arbitrary commands. The
launcher supervises the independent, bounded execution of this single adapter.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import signal
import time
from types import ModuleType

INSTALL = Path('/opt/samwise-celery-shadow')
ENROLLMENT = INSTALL / 'pidbox-enrollment.json'
RUNTIME = INSTALL / 'pidbox-runtime.zip'
SANDBOX = INSTALL / 'celery_broker_guard.py'
SIGNED = 'celery-site-signed-origin-v2'
PROC = Path('/proc')
HOST = '127.0.0.1'
PORT = 6379
ADDR = ('0100007F', PORT)
SCOPE = {'endpoint':'127.0.0.1:6379','database':0,'exchange':'celery.pidbox',
         'reply_exchange':'reply.celery.pidbox','fanout_prefix':'/0.',
         'fanout_patterns':True,'keyprefix':'','serializer':'json'}
URL = 'redis://127.0.0.1:6379/0'
PROOF = 'closed-kernel-pid-netns-v1'
MAX_RUNTIME = 32*1024*1024
MAX_ROWS = 512
MAX_FDS = 128
SHA = re.compile('[0-9a-f]{64}')
WORKER = re.compile('(?:default|dvr)@[A-Za-z0-9_.-]{1,253}')


def need(ok):
    if not ok:
        raise ValueError('pidbox_scope_refused')


def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(',',':')).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def enrolled_names(value):
    need(type(value) is list and len(value) == 2 and
         all(type(name) is str and WORKER.fullmatch(name) for name in value) and
         [name.split('@',1)[0] for name in value] == ['default','dvr'])
    return value


def pid_pair(value):
    need(type(value) is list and len(value) == 2 and
         all(type(x) is int and 0 < x < 2**63 for x in value) and value[0] <= 2**31-1)
    return value


def no_dupes(pairs):
    obj = dict(pairs)
    need(len(obj) == len(pairs))
    return obj


def enrollment(data):
    need(type(data) is bytes and 0 < len(data) <= 8192)
    p = json.loads(data.decode('utf-8','strict'),object_pairs_hook=no_dupes)
    need(type(p) is dict)
    signed=p.get('version')==SIGNED
    base=set(('version','boot','net_inode','pid_inode','scope_sha256','topology',
              'broker','workers','broker_sha256','runtime_sha256'))
    ext={'host_pid_inode','guest_init','guest_cgroup','public_keys','worker_uids',
         'launcher_origin_sha256','launcher_topology_sha256','broker_guard_sha256'}
    need(set(p)==base|(ext if signed else set()))
    need((signed and p['topology']=='signed-worker-host-provenance-v2' or
          p['version']=='celery-site-pidbox-v1' and p['topology']==PROOF) and
         p['scope_sha256']==digest(canonical(SCOPE)))
    if signed:
        need(type(p['host_pid_inode']) is int and p['host_pid_inode']>0 and
             p['host_pid_inode']!=p['pid_inode'])
        pid_pair(p['guest_init'])
        need(type(p['guest_cgroup']) is str and
             re.fullmatch(r'/system\.slice/docker-[a-f0-9]{64}\.scope',p['guest_cgroup']))
        need(all(type(p[k]) is str and SHA.fullmatch(p[k])
                 for k in ('launcher_origin_sha256','launcher_topology_sha256','broker_guard_sha256')))
        ids=p['worker_uids']
        keys=p['public_keys']
        need(type(keys) is dict and type(ids) is dict and set(keys)==set(ids)==set(p['workers']))
        need(all(type(i) is int and 0<i<=2**31-1 for i in ids.values()) and len(set(ids.values()))==2)
        need(all(type(k) is str and SHA.fullmatch(k) for k in keys.values()) and len(set(keys.values()))==2)
    need(type(p['boot']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',p['boot']))
    need(type(p['net_inode']) is int and p['net_inode'] > 0 and
         type(p['pid_inode']) is int and p['pid_inode'] > 0 and
         all(type(p[key]) is str and SHA.fullmatch(p[key])
             for key in ('broker_sha256','runtime_sha256')))
    need(type(p['workers']) is dict)
    pairs = [pid_pair(p['workers'][name]) for name in enrolled_names(sorted(p['workers']))]
    pairs.append(pid_pair(p['broker']))
    need(len({pair[0] for pair in pairs}) == 3)
    return p


def trusted_bytes(path, maximum, owner=0, mode=0o600):
    need(path.is_absolute() and all(p not in ('.','..') for p in path.parts))
    fd = os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        for part in path.parent.parts[1:]:
            new = os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
            os.close(fd)
            fd = new
            st = os.fstat(fd)
            need(st.st_uid in (0,owner) and
                 (not st.st_mode & 0o022 or part=='tmp' and st.st_uid==0 and st.st_mode & stat.S_ISVTX))
        leaf = os.open(path.name,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
        with os.fdopen(leaf,'rb') as stream:
            st = os.fstat(stream.fileno())
            need(stat.S_ISREG(st.st_mode) and st.st_uid==owner and st.st_nlink==1 and
                 stat.S_IMODE(st.st_mode)==mode and 0 < st.st_size <= maximum)
            data = stream.read(maximum+1)
            end = os.stat(path.name,dir_fd=fd,follow_symlinks=False)
            need(os.path.samestat(st,end) and st.st_ctime_ns==end.st_ctime_ns and
                 len(data)==st.st_size)
            return data
    finally:
        os.close(fd)


def small(path, limit):
    with path.open('rb') as f:
        raw = f.read(limit+1)
    need(len(raw)<=limit)
    return raw.decode('ascii','strict')


def process(proc, pair, p):
    pid,ticks = pair
    folder = proc/str(pid)
    line = small(folder/'stat',4096)
    tail = line.rsplit(')',1)[1].split()
    need(int(line.split(' ',1)[0])==pid and tail[0] not in ('Z','X') and int(tail[19])==ticks)
    for key in ('pid','net'):
        need((folder/'ns'/key).stat().st_ino == p[key+'_inode'])
    return folder


def fds(folder):
    seen = set()
    with os.scandir(folder/'fd') as entries:
        for number, entry in enumerate(entries,1):
            need(number <= MAX_FDS)
            try:
                target = os.readlink(entry.path)
            except FileNotFoundError:
                continue
            sock = re.fullmatch(r'socket:\[(\d+)\]',target)
            if sock:
                seen.add(int(sock[1]))
    return seen


def table(path):
    def address(value):
        host,port = value.split(':')
        return host.upper(),int(port,16)
    rows = []
    for line in small(path,128*1024).splitlines()[1:]:
        need(len(rows) < MAX_ROWS)
        col = line.split()
        need(len(col) >= 10)
        rows.append((address(col[1]),address(col[2]),col[3],int(col[9])))
    return rows


def topology(proc,p,allow_self=False):
    need(small(proc/'sys/kernel/random/boot_id',100).strip()==p['boot'])
    for key in ('pid','net'):
        need((proc/'self/ns'/key).stat().st_ino==p[key+'_inode'])
    broker = process(proc,p['broker'],p)
    interfaces = [row.split(':',1)[0].strip()
                  for row in small(broker/'net/dev',16384).splitlines()[2:]]
    # This adapter admits a controlled loopback-only topology. It does not
    # treat a normal shared production network namespace as equivalent.
    need(interfaces==['lo'])
    workers = [process(proc,p['workers'][name],p) for name in sorted(p['workers'])]
    need(Path(os.readlink(broker/'exe')).name == 'redis-server')
    with (broker/'exe').open('rb') as executable:  # pinned kernel proc link
        code = executable.read(MAX_RUNTIME+1)
    need(0 < len(code) <= MAX_RUNTIME and digest(code)==p['broker_sha256'])
    rows = table(broker/'net/tcp')
    six = table(broker/'net/tcp6')
    need(not any(a[1]==PORT or b[1]==PORT for a,b,state,ino in six))
    listeners = [(a,ino) for a,b,state,ino in rows if a[1]==PORT and state=='0A']
    broker_ino = fds(broker)
    need(len(listeners)==1 and listeners[0][0]==ADDR and listeners[0][1] in broker_ino)
    clients = {ino for a,b,state,ino in rows if b==ADDR and state=='01'}
    server = {ino for a,b,state,ino in rows if a==ADDR and ino}
    # Require only this TCP listener/accepted clients; this detects an
    # unapproved extra listener including a Unix-domain socket owned by Redis.
    need(broker_ino == server and bool(clients))
    owned = [fds(folder)&clients for folder in workers]
    extra = clients - (owned[0]|owned[1])
    # The caller may still own its bounded Redis pool descriptors after
    # capture. No other-process connection is eligible in either bracket.
    need(all(owned) and not (owned[0]&owned[1]) and
         (not extra or allow_self and extra <= fds(proc/'self')))
    # Cross-check stable original process identities after the fd join.
    process(proc,p['broker'],p)
    for pair in p['workers'].values():
        process(proc,pair,p)


def network_event(event,args):
    # This is an app-layer guard for this reviewed, pinned Python dependency
    # set, NOT a general kernel confinement claim. Exact deployed egress
    # and read-policy enforcement are independent gates.
    if event=='socket.__new__':
        need(args[1]==socket.AF_INET and (args[2]&0xf)==socket.SOCK_STREAM)
    elif event=='socket.connect':
        endpoint = args[1]
        need(type(endpoint) is tuple and endpoint==(HOST,PORT))
    elif event=='socket.getaddrinfo':
        need(args[0]==HOST and args[1] in (PORT,str(PORT)))
    elif event in ('socket.bind','socket.sendto','socket.sendmsg','socket.gethostbyname',
                   'socket.gethostbyaddr','subprocess.Popen','os.system','os.posix_spawn','os.fork','os.exec'):
        raise ValueError('pidbox_scope_refused')


def replies(raw,names, validate):
    need(type(raw) is list and 0 < len(raw) < 3)
    result = {}
    for frame in raw:
        need(type(frame) is dict and len(frame)==1)
        worker,pong = next(iter(frame.items()))
        need(worker in names and worker not in result and pong=={'ok':'pong'})
        result[worker] = pong
    validate()
    return result


def capture(Celery,names,validate, *, nonce=None):
    need(nonce is None or type(nonce) is str and SHA.fullmatch(nonce))
    app = Celery('samwise_fixed_pidbox', broker=URL)
    app.conf.update(broker_url=URL,broker_read_url=URL,broker_write_url=URL,
        broker_connection_retry=False,broker_connection_retry_on_startup=False,
        broker_connection_max_retries=0,broker_connection_timeout=1,
        broker_failover_strategy='round-robin',task_serializer='json',accept_content=['json'],
        control_exchange='celery',broker_transport_options={
            'fanout_prefix':True,'fanout_patterns':True,'global_keyprefix':'',
            'socket_connect_timeout':1,'socket_timeout':2,'retry_on_timeout':False})
    try:
        with app.connection_for_write() as connection:
            # No fallback list, credentials, SSL substitution or URL parameters.
            need(connection.hostname==HOST and connection.port==PORT and
                 connection.virtual_host in ('/0','0',0) and not connection.alt and
                 not connection.ssl and not connection.userid and not connection.password)
            connection.connect()
            channel = connection.default_channel
            box = app.control.mailbox
            need(box.exchange.name==SCOPE['exchange'] and
                 box.reply_exchange.name==SCOPE['reply_exchange'] and
                 box.serializer==SCOPE['serializer'] and
                 channel.keyprefix_fanout==SCOPE['fanout_prefix'] and
                 channel.fanout_patterns is True and
                 channel.global_keyprefix==SCOPE['keyprefix'] and
                 channel._get_publish_topic(box.exchange.name,'')==
                 SCOPE['fanout_prefix']+SCOPE['exchange'])
            # Do not flatten upstream replies or stop at the expected count:
            # collect one extra frame so duplicate/foreign replies can refuse.
            raw = app.control.broadcast('ping',arguments={} if nonce is None else
                {'samwise_readiness_nonce':nonce},destination=names,
                connection=connection,channel=channel,reply=True,timeout=8,limit=3)
    finally:
        app.close()
    if nonce is not None:
        return validate(raw)
    return replies(raw,names,validate)


def signed_invocation(p, args, enrollment_hash, proc=PROC, now_ns=None):
    need(len(args)==3 and all(arg.startswith(prefix) for arg,prefix in zip(
         args, ('--challenge=', '--deadline-ns=', '--enrollment-sha='))))
    challenge=args[0].removeprefix('--challenge=')
    cutoff_text=args[1].removeprefix('--deadline-ns=')
    requested_hash=args[2].removeprefix('--enrollment-sha=')
    need(SHA.fullmatch(challenge) and SHA.fullmatch(requested_hash)
         and requested_hash==enrollment_hash and re.fullmatch('[1-9][0-9]{0,18}',cutoff_text))
    cutoff=int(cutoff_text)
    now_ns=time.monotonic_ns() if now_ns is None else now_ns
    need(0 < cutoff-now_ns <= 12*10**9)
    # Manager resolves /proc/<pid>/ns/net separately from the attestor.
    # Independently reject a rebound PID/net namespace before any socket.
    need(small(proc/'sys/kernel/random/boot_id',64).strip()==p['boot'])
    need((proc/'self/ns/net').stat().st_ino==p['net_inode'])
    need(small(proc/'self/cgroup',8192)=='0::/system.slice/samwise-celery-shadow-broker.service\n')
    return challenge,cutoff


def preload_native_stdlib():
    # Open just the trusted stdlib's native dependency closure before the
    # Landlock file rule. -IBS excludes all ambient site or local packages.
    # Do not preload any Celery/Redis/plugin code before confinement.
    import _multiprocessing
    import _posixsubprocess
    import bz2
    import lzma
    import ssl
    import uuid


def discard_loader_handles():
    # Some hardened native loaders leave verified regular library FDs open.
    # Close them before untrusted runtime code; never swallow a passed socket,
    # pipe, directory, or unknown descriptor. Guard independently rechecks.
    for entry in os.listdir('/proc/self/fd'):
        fd = int(entry)
        if fd < 3:
            continue
        try:
            info = os.fstat(fd)
        except OSError as exc:
            if exc.errno != errno.EBADF:
                raise
            continue  # readdir's own ephemeral descriptor
        need(stat.S_ISREG(info.st_mode))
        os.close(fd)


def main(args):
    need(sys.flags.isolated and sys.flags.no_site and os.geteuid()==0 and Path(__file__)==INSTALL/'pidbox-ping')
    raw=trusted_bytes(ENROLLMENT,8192)
    p = enrollment(raw)
    names = enrolled_names(sorted(p['workers']))
    fixed=['--destination='+','.join(names),'--timeout=8','--json']
    signed=p['version']==SIGNED
    challenge=None
    if signed:
        need(args[:3]==fixed)
        challenge,cutoff=signed_invocation(p,args[3:],digest(raw))
        # Process-level monotonic relative timer complements both transient
        # unit lifetimes. Expiration terminates the in-flight capture.
        remaining=(cutoff-time.monotonic_ns())/10**9
        need(remaining>0)
        signal.setitimer(signal.ITIMER_REAL, remaining)
    else:
        need(args==fixed)
    need(digest(trusted_bytes(RUNTIME,MAX_RUNTIME,mode=0o644))==p['runtime_sha256'])
    # New adapter never reads host /proc. The trusted publisher witnesses on
    # both sides. Fail before importing broker code if native confinement
    # (the required no-host-proc/no-extra-port path) can't be established.
    if signed:
        source=trusted_bytes(SANDBOX,128*1024,mode=0o644)
        need(digest(source)==p['broker_guard_sha256'])
        guard=ModuleType('celery_broker_guard')
        guard.__file__=str(SANDBOX)
        exec(compile(source,str(SANDBOX),'exec',dont_inherit=True),guard.__dict__)
        preload_native_stdlib()
        discard_loader_handles()
        need(guard.apply(RUNTIME) is True)
        def verify(raw):
            need(type(raw) is list and 0<len(raw)<=2)
            return raw
    else:
        topology(PROC,p)
        verify = lambda: topology(PROC,p,allow_self=True)
    sys.addaudithook(network_event)
    sys.path.insert(0,str(RUNTIME))
    # The reviewed archive must match the individually pinned site source.
    import celery
    import kombu
    import redis
    need((celery.__version__,kombu.__version__,redis.__version__)==('5.6.3','5.6.2','6.4.0') and
         all(str(module.__file__).startswith(str(RUNTIME)+'/') for module in (celery,kombu,redis)))
    if signed:
        need(cutoff-time.monotonic_ns() >= 8*10**9)
    result=capture(celery.Celery,names,verify,nonce=challenge)
    if signed:
        need(time.monotonic_ns() < cutoff)
    print(json.dumps(result,separators=(',',':')))


if __name__=='__main__':
    try:
        main(sys.argv[1:])
    except Exception:
        # Keep broker/client exceptions and their payloads inside the helper.
        sys.exit(1)
