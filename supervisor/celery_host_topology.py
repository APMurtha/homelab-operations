"""Passive Linux host-to-container PID mapping with loopback-only broker authority.

Expects an independently authenticated enrollment. Never joins a namespace,
opens a socket, contacts a service, or turns an unsupported topology into a pass.
"""
import hashlib
import os
from pathlib import Path
import re
import stat

ADDR = ('0100007F', 6379)
MAX_ROWS = 512
MAX_MEMBERS = 128
CGROUP = re.compile(r'/system\.slice/docker-[a-f0-9]{64}\.scope')
SHA = re.compile('[a-f0-9]{64}')


def need(ok):
    if not ok:
        raise ValueError('host topology refused')


def number(x, cap=2**63-1):
    need(type(x) is int and 0 < x <= cap)
    return x


def bounded(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        need(stat.S_ISREG(os.fstat(stream.fileno()).st_mode))
        raw = stream.read(limit + 1)
    need(len(raw) <= limit)
    return raw.decode('ascii', 'strict')


def statuses(folder, pid):
    raw = bounded(folder/'status', 16384)
    fields = re.findall(r'^NSpid:[ \t]+([0-9]+(?:[ \t]+[0-9]+)*)$', raw, re.M)
    need(len(fields) == 1)
    values = [number(int(v), 2**31-1) for v in fields[0].split()]
    need(values and values[0] == pid)
    return tuple(values)


def process(proc, pair, layout, *, host=False):
    need(type(pair) in (tuple, list) and len(pair) == 2)
    pid, ticks = number(pair[0], 2**31-1), number(pair[1])
    folder = proc/str(pid)
    line = bounded(folder/'stat', 4096)
    prefix, tail = line.rsplit(')', 1)
    fields = tail.split()
    need(int(prefix.split(' ',1)[0]) == pid and fields[0] not in ('Z','X','x')
         and int(fields[19]) == ticks)
    need((folder/'ns/pid').stat().st_ino ==
         layout['host_pid_inode' if host else 'pid_inode'])
    pids = statuses(folder, pid)
    need(len(pids) == (1 if host else 2))
    if not host:
        need((folder/'ns/net').stat().st_ino == layout['net_inode'])
        need(bounded(folder/'cgroup', 8192).splitlines() == ['0::'+layout['guest_cgroup']])
    return folder, pids


def fds(folder):
    owned = set()
    with os.scandir(folder/'fd') as entries:
        for i, entry in enumerate(entries):
            need(i < 128)
            try:
                link = os.readlink(entry.path)
            except FileNotFoundError:
                continue
            match = re.fullmatch(r'socket:\[([0-9]+)\]', link)
            if match:
                owned.add(number(int(match[1])))
    return owned


def table(path):
    def address(text):
        host, port = text.split(':')
        need(re.fullmatch(r'[0-9A-Fa-f]{8}|[0-9A-Fa-f]{32}', host))
        return host.upper(), int(port,16)
    rows = []
    for line in bounded(path, 128*1024).splitlines()[1:]:
        need(len(rows) < MAX_ROWS)
        c = line.split()
        need(len(c) >= 10 and re.fullmatch(r'[0-9A-F]{2}', c[3]))
        rows.append((address(c[1]),address(c[2]),c[3],int(c[9])))
    return rows


def _mapping(proc, layout, cgroups, *, target_net=True):
    # Require a known host procfs view and exactly one guest level.
    for name in ('host_pid_inode','pid_inode','net_inode'):
        number(layout[name])
    need(layout['host_pid_inode'] != layout['pid_inode'])
    need(type(layout['guest_cgroup']) is str and CGROUP.fullmatch(layout['guest_cgroup']))
    need(bounded(proc/'sys/kernel/random/boot_id',100).strip() == layout['boot'])
    self_name = os.readlink(proc/'self')
    need(re.fullmatch(r'[1-9][0-9]{0,9}', self_name))
    self_pid = number(int(self_name), 2**31-1)
    self_folder = proc/str(self_pid)
    init_folder = proc/'1'
    for folder,pid in ((self_folder,self_pid),(init_folder,1)):
        need((folder/'ns/pid').stat().st_ino == layout['host_pid_inode'])
        need(statuses(folder,pid) == (pid,))
    original_net = (self_folder/'ns/net').stat().st_ino
    need(not target_net or original_net == layout['net_inode'])

    names = sorted(layout['workers'])
    need(len(names)==2 and re.fullmatch(r'default@[A-Za-z0-9_.-]{1,253}',names[0])
         and re.fullmatch(r'dvr@[A-Za-z0-9_.-]{1,253}',names[1]))
    pairs = [layout['guest_init'],layout['broker'],*(layout['workers'][k] for k in names)]
    vetted = [process(proc, pair, layout) for pair in pairs]
    ids = [values for _,values in vetted]
    need(ids[0][1] == 1 and all(len({v[i] for v in ids}) == len(ids) for i in (0,1)))
    membership_file = cgroups/layout['guest_cgroup'].lstrip('/')/'cgroup.procs'
    def membership():
        before = membership_file.lstat()
        need(stat.S_ISREG(before.st_mode))
        values = bounded(membership_file,4096).split()
        after = membership_file.lstat()
        need(os.path.samestat(before,after) and before.st_ctime_ns == after.st_ctime_ns)
        need(4 <= len(values) <= MAX_MEMBERS and len(set(values)) == len(values))
        return (before.st_dev, before.st_ino, before.st_ctime_ns,
                {number(int(v),2**31-1) for v in values})
    members = membership()
    need({v[0] for v in ids} <= members[-1])

    def verify():
        need([process(proc,pair,layout) for pair in pairs] == vetted and membership() == members)
        need(os.readlink(proc/'self') == self_name and
             (self_folder/'ns/pid').stat().st_ino == layout['host_pid_inode'] and
             (self_folder/'ns/net').stat().st_ino == original_net and
             statuses(self_folder,self_pid) == (self_pid,) and
             (init_folder/'ns/pid').stat().st_ino == layout['host_pid_inode'] and
             statuses(init_folder,1) == (1,) and
             bounded(proc/'sys/kernel/random/boot_id',100).strip() == layout['boot'])
    return (dict(zip(('guest_init','broker',*names),ids)), self_folder,
            vetted[1][0], [p[0] for p in vetted[2:]], verify)


def host_mapping(proc, layout, *, cgroups=Path('/sys/fs/cgroup')):
    """Return structural identity only, never broker or peer authority."""
    mapping, _, _, _, verify = _mapping(proc, layout, cgroups)
    verify()
    return mapping


def signed_endpoint(proc, layout, *, cgroups=Path('/sys/fs/cgroup')):
    """Verify the specific broker and worker sockets, not reply origin.

    Shared-network path: permit unrelated local clients but never use their
    absence/presence as evidence for a reply. Caller must authenticate each
    enrolled worker independently and re-run this bracket after capture.
    """
    return _endpoint(proc,layout,cgroups,False,False, target_net=False)


def topology(proc, layout, *, allow_self=False, cgroups=Path('/sys/fs/cgroup')):
    """Verify structural identity and closed loopback-only broker authority."""
    need(type(allow_self) is bool)
    return _endpoint(proc,layout,cgroups,True,allow_self)


def _endpoint(proc,layout,cgroups,closed,allow_self, *, target_net=True):
    mapping, self_folder, broker, workers, verify = _mapping(proc, layout, cgroups,
                                                           target_net=target_net)
    net = broker/'net'
    interfaces = [line.split(':',1)[0].strip()
                  for line in bounded(net/'dev',16384).splitlines()[2:]]
    need(interfaces == ['lo'] if closed else interfaces.count('lo')==1)
    need(Path(os.readlink(broker/'exe')).name == 'redis-server')
    pinned = layout['broker_sha256']
    need(type(pinned) is str and SHA.fullmatch(pinned))
    # The executable reference is a kernel-owned proc magic link.
    with (broker/'exe').open('rb') as exe:
        code = exe.read(32*1024*1024+1)
    need(0 < len(code) <= 32*1024*1024 and hashlib.sha256(code).hexdigest()==pinned)
    ipv6 = table(net/'tcp6')
    need(not any(a[1]==ADDR[1] or b[1]==ADDR[1] for a,b,_,_ in ipv6))
    rows = table(net/'tcp')
    listeners = [(a,ino) for a,_,s,ino in rows if a[1]==ADDR[1] and s=='0A']
    broker_fds = fds(broker)
    need(len(listeners)==1 and listeners[0][0]==ADDR and listeners[0][1] in broker_fds)
    clients = {ino for _,b,s,ino in rows if b==ADDR and s=='01' and ino}
    accepted = {ino for a,_,s,ino in rows if a==ADDR and s in ('01','0A') and ino}
    need(broker_fds == accepted and bool(clients))
    # Every accepted connection must have a matching in-kernel loopback
    # client tuple; neither remote inbound clients nor duplicate tuples pass.
    left = [(a,b) for a,b,s,ino in rows if b==ADDR and s=='01' and ino]
    right = [(b,a) for a,b,s,ino in rows if a==ADDR and s=='01' and ino]
    need(len(set(left)) == len(left) and len(set(right)) == len(right) and
         set(left) == set(right) and len(clients) == len(left))
    owned = [fds(folder)&clients for folder in workers]
    extra = clients - (owned[0]|owned[1])
    self_owned = fds(self_folder) if allow_self else set()
    need(all(owned) and not(owned[0]&owned[1]) and
         not(self_owned&(owned[0]|owned[1])) and (not closed or extra <= self_owned))
    # Recheck the actual socket join, not just process IDs, after mapping
    # validation so a moving peer set never becomes an authority witness.
    need(set(table(net/'tcp')) == set(rows) and set(table(net/'tcp6')) == set(ipv6))
    need(fds(broker) == broker_fds and [fds(folder)&clients for folder in workers] == owned)
    if allow_self:
        need(fds(self_folder)&clients == self_owned&clients)
    verify()
    return mapping
