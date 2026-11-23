"""Local reader-side eligibility. No service, socket, secret or process inspection."""
from contextlib import contextmanager, suppress
import fcntl
import os
import stat
import struct

from ops_protocol import check, decode

DROP = 'celery-v1'
ANCHOR = '.celery-acquisition.lock'
LEASE = '.celery-publisher.lease'
COMMIT = '.celery-publication.json'


def vacuum(fd, name):
    with suppress(FileNotFoundError):
        os.unlink(name, dir_fd=fd)


def eligible(st, owner, group=None):
    check(stat.S_ISREG(st.st_mode) and st.st_uid == owner and
          stat.S_IMODE(st.st_mode) == 0o640 and st.st_nlink == 1 and
          (group is None or st.st_gid == group))
    return signature(st)


def signature(st):
    return [st.st_dev, st.st_ino, st.st_uid, st.st_gid, st.st_mode, st.st_nlink,
            st.st_size, st.st_ctime_ns, st.st_mtime_ns]


def current(fd, name, owner, group=None):
    return eligible(os.stat(name, dir_fd=fd, follow_symlinks=False), owner, group)


@contextmanager
def open_control(fd, name, owner, group=None):
    control = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        check(eligible(os.fstat(control), owner, group) == current(fd, name, owner, group))
        yield control
    finally:
        os.close(control)


# Linux 64-bit struct flock; production launcher must qualify its platform.
# Unlike BSD flock, an OFD write lock requires a writable descriptor: a
# group-read-only collector cannot forge a positive publisher liveness flag.
OFD_LOCK = struct.Struct('@hhqqi4x')


def lease_write(fd):
    check(hasattr(fcntl, 'F_OFD_SETLK'))
    fcntl.fcntl(fd, fcntl.F_OFD_SETLK,
                OFD_LOCK.pack(fcntl.F_WRLCK, os.SEEK_SET, 0, 0, 0))


def writer_alive(fd):
    check(hasattr(fcntl, 'F_OFD_GETLK'))
    answer = fcntl.fcntl(fd, fcntl.F_OFD_GETLK,
                         OFD_LOCK.pack(fcntl.F_RDLCK, os.SEEK_SET, 0, 0, 0))
    lock, origin, start, length, pid = OFD_LOCK.unpack(answer)
    return (lock, origin, start, length, pid) == (fcntl.F_WRLCK, os.SEEK_SET, 0, 0, -1)


@contextmanager
def open_drop(fd, owner):
    child = os.open(DROP, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
    try:
        stamp = signature(os.fstat(child))
        check(stamp[2] == owner and stat.S_IMODE(stamp[4]) in (0o700, 0o750, 0o2750) and
              stamp == signature(os.stat(DROP, dir_fd=fd, follow_symlinks=False)))
        yield child, stamp
        check(stamp == signature(os.fstat(child)) ==
              signature(os.stat(DROP, dir_fd=fd, follow_symlinks=False)))
    finally:
        os.close(child)


def guarded_observe(fd, owner, observe):
    with open_drop(fd, owner) as (child, stamp):
        return guarded_receipt(child, owner, stamp, observe)


def guarded_receipt(fd, owner, folder, observe):
    group = folder[3]
    with open_control(fd, ANCHOR, owner, group) as anchor:
        fcntl.flock(anchor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        anchor_sig = eligible(os.fstat(anchor), owner, group)
        check(anchor_sig == current(fd, ANCHOR, owner, group))
        with open_control(fd, LEASE, owner, group) as lease:
            lease_sig = eligible(os.fstat(lease), owner, group)
            check(writer_alive(lease))
            with open_control(fd, COMMIT, owner, group) as commit:
                commit_sig = eligible(os.fstat(commit), owner, group)
                receipt_sig = current(fd, 'celery', owner, group)
                check(commit_sig[6] <= 4096)
                payload = os.read(commit, 4097)
                check(len(payload) == commit_sig[6] and
                      decode(payload) == [folder, anchor_sig, lease_sig, receipt_sig])
                value = observe(fd)
                check(current(fd, ANCHOR, owner, group) == anchor_sig and
                      current(fd, LEASE, owner, group) == lease_sig and
                      current(fd, COMMIT, owner, group) == commit_sig and
                      current(fd, 'celery', owner, group) == receipt_sig and writer_alive(lease))
                return value
