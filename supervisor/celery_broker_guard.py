"""One-way kernel confinement for the fixed, single-threaded broker child.

Call after trusted setup/imports, before Celery can open a socket. Requires an
independently attested loopback-only IP rule; Landlock limits TCP ports, not
addresses. A failing apply must terminate the child, never fall back.
"""
import ctypes as C
import os
from pathlib import Path
import platform
import socket
import stat
import sys

PORT = 6379
MIN_ABI = 4
RUNTIME = Path('/opt/samwise-celery-shadow/pidbox-runtime.zip')
STDLIB = Path(f'/usr/lib/python{sys.version_info.major}.{sys.version_info.minor}')
READ_FILE, READ_DIR = 1 << 2, 1 << 3
TCP_BIND, TCP_CONNECT = 1, 2
EPERM = 0x00050001
ALLOW = 0x7FFF0000
NE, EQ, GT, MASKED_EQ = 1, 4, 6, 7


class Ruleset(C.Structure):
    _fields_ = [('fs', C.c_uint64), ('net', C.c_uint64)]


class PathRule(C.Structure):
    _pack_ = 1
    _fields_ = [('access', C.c_uint64), ('parent', C.c_int32)]


class NetRule(C.Structure):
    _fields_ = [('access', C.c_uint64), ('port', C.c_uint64)]


class Compare(C.Structure):
    _fields_ = [('arg', C.c_uint), ('op', C.c_int),
                ('a', C.c_uint64), ('b', C.c_uint64)]


def reject_rules():
    for name in ('socketpair', 'bind', 'listen', 'accept', 'accept4',
                 'sendmsg', 'sendmmsg', 'recvmsg', 'recvmmsg', 'clone', 'clone3',
                 'fork', 'vfork', 'execve', 'execveat', 'unshare', 'setns',
                 'bpf', 'ptrace', 'process_vm_readv', 'process_vm_writev',
                 'kill', 'tkill', 'tgkill', 'pidfd_send_signal', 'rt_sigqueueinfo', 'rt_tgsigqueueinfo',
                 'pidfd_getfd', 'io_uring_setup', 'io_uring_enter', 'io_uring_register'):
        yield name, ()
    yield 'socket', (Compare(0, NE, socket.AF_INET, 0),)
    # Lower four bits are the Linux socket type; the kernel rejects unknown flags.
    for kind in range(16):
        if kind != socket.SOCK_STREAM:
            yield 'socket', (Compare(1, MASKED_EQ, 15, kind),)
    # Linux protocol=0 selects the default TCP protocol for AF_INET/SOCK_STREAM.
    for protocol in range(1, socket.IPPROTO_TCP):
        yield 'socket', (Compare(2, EQ, protocol, 0),)
    yield 'socket', (Compare(2, GT, socket.IPPROTO_TCP, 0),)
    # send()/sendall() may be implemented as sendto() with no destination.
    yield 'sendto', (Compare(4, NE, 0, 0),)


def fixed_file(path, is_dir=False):
    fd = os.open('/', os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for index, part in enumerate(path.parts[1:], 1):
            directory = is_dir or index < len(path.parts) - 1
            extra = os.O_DIRECTORY if directory else 0
            peer = os.open(part, os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC | extra, dir_fd=fd)
            os.close(fd)
            fd = peer
            s = os.fstat(fd)
            if (s.st_uid != 0 or s.st_mode & 0o022 or
                (directory and not stat.S_ISDIR(s.st_mode)) or
                (not directory and (not stat.S_ISREG(s.st_mode) or s.st_nlink != 1))):
                raise ValueError('broker_guard_untrusted_path')
        ret, fd = fd, -1
        return ret
    finally:
        if fd >= 0:
            os.close(fd)


def activate_fs_and_port(libc, runtime):
    if platform.machine() != 'x86_64' or C.sizeof(C.c_void_p) != 8:
        raise ValueError('broker_guard_unsupported_abi')
    c_sys = libc.syscall
    c_sys.restype = C.c_long

    def syscall(number, *args):
        result = c_sys(C.c_long(number), *args)
        if result < 0:
            raise OSError(C.get_errno(), 'broker_guard_landlock')
        return result

    if syscall(444, C.c_void_p(), C.c_size_t(), C.c_uint(1)) < MIN_ABI:
        raise ValueError('broker_guard_unsupported_abi')
    # ABI 4 already has TCP port restrictions and all filesystem rights
    # through TRUNCATE. No device FD is inherited and no device can be opened;
    # native seccomp independently rejects AF_UNIX and all signal sends.
    policy = Ruleset(0x7fff, TCP_BIND | TCP_CONNECT)
    rules = syscall(444, C.byref(policy), C.c_size_t(C.sizeof(policy)), C.c_uint(0))
    try:
        for path, is_dir, rights in ((STDLIB, True, READ_FILE | READ_DIR),
                                     (runtime, False, READ_FILE)):
            pfd = fixed_file(path, is_dir)
            try:
                entry = PathRule(rights, pfd)
                syscall(445, C.c_int(rules), C.c_int(1), C.byref(entry), C.c_uint(0))
            finally:
                os.close(pfd)
        conn = NetRule(TCP_CONNECT, PORT)
        syscall(445, C.c_int(rules), C.c_int(2), C.byref(conn), C.c_uint(0))
        if libc.prctl(38, C.c_ulong(1), C.c_ulong(0), C.c_ulong(0), C.c_ulong(0)):
            raise OSError(C.get_errno(), 'broker_guard_no_new_privileges')
        syscall(446, C.c_int(rules), C.c_uint(0))
    finally:
        os.close(rules)


def activate_syscalls(seccomp):
    seccomp.seccomp_init.argtypes = [C.c_uint32]
    seccomp.seccomp_init.restype = C.c_void_p
    seccomp.seccomp_release.argtypes = [C.c_void_p]
    seccomp.seccomp_load.argtypes = [C.c_void_p]
    seccomp.seccomp_syscall_resolve_name.argtypes = [C.c_char_p]
    seccomp.seccomp_rule_add_array.argtypes = [C.c_void_p, C.c_uint32, C.c_int, C.c_uint,
                                              C.POINTER(Compare)]
    ctx = seccomp.seccomp_init(ALLOW)
    if not ctx:
        raise ValueError('broker_guard_seccomp_init')
    try:
        for name, compares in reject_rules():
            number = seccomp.seccomp_syscall_resolve_name(name.encode('ascii'))
            if number < 0 or seccomp.seccomp_rule_add_array(
                    ctx, EPERM, number, len(compares), (Compare * len(compares))(*compares)) != 0:
                raise ValueError('broker_guard_seccomp_rule')
        if seccomp.seccomp_load(ctx) != 0:
            raise ValueError('broker_guard_seccomp_load')
    finally:
        seccomp.seccomp_release(ctx)


def apply(runtime_path):
    """Fixed installation path; no credentials, enrollment, /proc or IP config."""
    if Path(runtime_path) != RUNTIME or not sys.flags.isolated or not sys.flags.no_site:
        raise ValueError('broker_guard_untrusted_entry')
    # No worker thread bypass and no pre-opened file/socket or passed-in fd.
    if len(os.listdir('/proc/self/task')) != 1:
        raise ValueError('broker_guard_multithreaded')
    if any(int(entry) > 2 and os.path.lexists('/proc/self/fd/'+entry)
           for entry in os.listdir('/proc/self/fd')):
        raise ValueError('broker_guard_inherited_fd')
    if any(stat.S_ISSOCK(os.fstat(fd).st_mode) for fd in (0, 1, 2)):
        raise ValueError('broker_guard_inherited_fd')
    libc = C.CDLL(None, use_errno=True)
    seccomp = C.CDLL('libseccomp.so.2', use_errno=True)
    activate_fs_and_port(libc, RUNTIME)
    activate_syscalls(seccomp)
    return True
