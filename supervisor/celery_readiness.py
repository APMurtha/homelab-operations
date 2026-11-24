"""Staging-only Celery readiness acquisition core; no production launcher."""
from contextlib import contextmanager, suppress
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import re
import selectors
import secrets
import signal
import stat
import subprocess
import time
import uuid

from celery_handoff import ANCHOR, COMMIT, LEASE, current, eligible, lease_write, signature, vacuum
from dispatcharr_project import celery, container, directory, publish
from ops_protocol import NS, PROJECTIONS, check

LIMIT = 16_384
PING_SECONDS = 8
DEADLINE_SECONDS = 12
TTL_NS = PROJECTIONS['celery'][1] * NS
MAX_CLOCK_SKEW_NS = 250_000_000
NAME = re.compile(r'(default|dvr)@[A-Za-z0-9_.-]{1,253}')


@dataclass(frozen=True)
class Witness:
    boot_id: str
    backend: dict
    # Exact node name -> (PID, process start ticks), from owner-reviewed source.
    workers: dict


def destinations(names):
    check(type(names) is tuple and len(names) == 2 and all(
        type(name) is str and NAME.fullmatch(name) for name in names))
    check(tuple(name.split('@', 1)[0] for name in names) == ('default', 'dvr'))
    return names


def argv(python, app, names):
    check(Path(python).is_absolute() and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', app))
    return [python, '-B', '-m', 'celery', '-A', app, 'inspect', 'ping',
            '--destination=' + ','.join(destinations(names)), '--timeout=8', '--json']


def capture(command, cwd, env, timeout=DEADLINE_SECONDS):
    """One bounded subprocess, no shell, no terminal and no saved pipe contents."""
    check(0 < timeout <= DEADLINE_SECONDS)
    end = time.monotonic() + timeout
    buffers = [bytearray(), bytearray()]
    with subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True,
                          close_fds=True,
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as child:
        try:
            with selectors.DefaultSelector() as sel:
                for i, pipe in enumerate((child.stdout, child.stderr)):
                    sel.register(pipe, selectors.EVENT_READ, i)
                while sel.get_map():
                    left = end - time.monotonic()
                    if left <= 0:
                        raise TimeoutError('capture_deadline')
                    for key, _ in sel.select(left):
                        chunk = os.read(key.fd, 4096)
                        if not chunk:
                            sel.unregister(key.fileobj)
                            continue
                        b = buffers[key.data]
                        check(len(b) + len(chunk) <= LIMIT)
                        b.extend(chunk)
                # Observe leader exit without reaping it. Keeping its PID reserved
                # anchors the PGID until our cleanup signal has been sent.
                while True:
                    left = end - time.monotonic()
                    if left <= 0:
                        raise TimeoutError('capture_deadline')
                    exited = os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                    if exited is not None:
                        break
                    time.sleep(min(0.01, left))
        finally:
            # Even a clean leader may leave a descendant that closed both pipes.
            # Signal before any Popen wait/poll can release the original PGID.
            with suppress(ProcessLookupError):
                os.killpg(child.pid, signal.SIGKILL)
        return child.wait(), bytes(buffers[0]), bytes(buffers[1])


def pongs(result, names):
    """Preserve the managed parser's strict JSON contract; additionally pin full names."""
    names = destinations(names)
    code, stdout, stderr = result
    check(type(code) is int and code == 0 and type(stdout) is bytes and
          type(stderr) is bytes and 0 < len(stdout) <= LIMIT and not stderr)

    def unique(pairs):
        value = {}
        for key, item in pairs:
            check(key not in value)
            value[key] = item
        return value

    def nonfinite(_):
        raise ValueError('nonfinite_json')

    value = json.loads(stdout.decode('utf-8', 'strict'), object_pairs_hook=unique,
                       parse_constant=nonfinite)
    # An empty capture has no positive transport witness, even with rc=0.
    check(type(value) is dict and 0 < len(value) <= 2 and
          all(key in names and reply == {'ok': 'pong'} for key, reply in value.items()))
    return tuple(name in value for name in names)


def remove_projection(fd):
    with suppress(FileNotFoundError):
        os.unlink('celery', dir_fd=fd)


def identity(witness, names, observed_ns, boot):
    check(isinstance(witness, Witness) and witness.boot_id == boot)
    probe_ns, health = container('backend', observed_ns, witness.backend)
    check(health == 'running' and observed_ns - probe_ns < TTL_NS)
    check(type(witness.workers) is dict and witness.workers.keys() == set(names))
    workers = [witness.workers[name] for name in names]
    check(all(type(w) is tuple and len(w) == 2 and
              all(type(x) is int and x > 0 for x in w) for w in workers))
    check(len({w[0] for w in workers}) == 2)
    return tuple(witness.backend[k] for k in ('Id', 'Pid', 'StartedNs')), workers, probe_ns


def atomic_control(fd, name, body=b''):
    temp = '.celery-' + secrets.token_hex(16)
    handle = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=fd)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(body)
            stream.flush()
            os.fchmod(stream.fileno(), 0o640)
        os.replace(temp, name, src_dir_fd=fd, dst_dir_fd=fd)
    finally:
        vacuum(fd, temp)


@contextmanager
def leased_acquisition(output, owner, boot, names, inspect, ping, *,
                       now=time.time_ns, monotonic=time.monotonic_ns, deadline_ns=None):
    """Offer a committed result only while this particular publisher lease lives.

    No production provisioning/entry point. Trusted adapters must be bounded
    by the reviewed launcher; the reader never invokes them.
    """
    from celery_handoff import open_control
    from contextlib import ExitStack

    with ExitStack() as resources:
        status = 'unavailable'
        try:
            fd = resources.enter_context(directory(output, owner))
            info = os.fstat(fd)
            check(stat.S_IMODE(info.st_mode) in (0o700, 0o750, 0o2750))
            group = info.st_gid
            anchor = os.open(ANCHOR, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                             dir_fd=fd)
            resources.callback(os.close, anchor)
            anchor_sig = eligible(os.fstat(anchor), owner, group)
            check(anchor_sig == current(fd, ANCHOR, owner, group))
            try:
                fcntl.flock(anchor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                status = 'busy'
            else:
                check(anchor_sig == current(fd, ANCHOR, owner, group))
                # Preserve an already committed publisher if its lease is live.
                # Only the anchored writer may create a new generation.
                from celery_handoff import writer_alive
                try:
                    with open_control(fd, LEASE, owner, group) as previous:
                        busy = writer_alive(previous)
                except (OSError, ValueError):
                    busy = False
                if busy:
                    status = 'busy'
                else:
                    # Invalidate first, then create a fresh lease inode. Never
                    # reacquire the old inode, so a dead writer cannot be revived.
                    vacuum(fd, COMMIT)
                    remove_projection(fd)
                    atomic_control(fd, LEASE)
                    lease = os.open(LEASE, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                                    dir_fd=fd)
                    resources.callback(os.close, lease)
                    lease_sig = eligible(os.fstat(lease), owner, group)
                    check(lease_sig == current(fd, LEASE, owner, group))
                    lease_write(lease)
                    status = acquire_value(fd, boot, names, inspect, ping, now, monotonic, deadline_ns)
                    if status != 'unavailable':
                        check(anchor_sig == current(fd, ANCHOR, owner, group) and
                              lease_sig == current(fd, LEASE, owner, group))
                        receipt_sig = current(fd, 'celery', owner, group)
                        check(deadline_ns is None or monotonic() < deadline_ns)
                        # Reserve the final name under EX. Writing the gate in
                        # this inode does not update the evidence directory's
                        # ctime; it can be bound and checked by every reader.
                        atomic_control(fd, COMMIT)
                        folder = signature(os.fstat(fd))
                        control = os.open(COMMIT, os.O_WRONLY | os.O_NOFOLLOW |
                                          os.O_NONBLOCK, dir_fd=fd)
                        try:
                            check(eligible(os.fstat(control), owner, group) ==
                                  current(fd, COMMIT, owner, group))
                            data = json.dumps([folder, anchor_sig, lease_sig, receipt_sig]).encode()
                            check(os.write(control, data) == len(data))
                            if deadline_ns is not None and monotonic() >= deadline_ns:
                                vacuum(fd, COMMIT)
                                remove_projection(fd)
                                check(False)
                        finally:
                            os.close(control)
                # The reader can now take a shared lock, but it must also see
                # this exact lease still locked by this publisher.
                fcntl.flock(anchor, fcntl.LOCK_UN)
        except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError,
                subprocess.SubprocessError):
            status = 'unavailable'
            resources.close()
        yield status


def acquire_value(fd, boot, names, inspect, ping, now, monotonic, deadline_ns=None):
    names = destinations(names)
    check(str(uuid.UUID(boot)) == boot)
    t0, m0 = now(), monotonic()
    check(deadline_ns is None or m0 < deadline_ns)
    before = inspect()
    t1 = now()
    bid, workerids, health0 = identity(before, names, t1, boot)
    check(deadline_ns is None or monotonic() < deadline_ns)
    default, dvr = pongs(ping(names), names)
    check(deadline_ns is None or monotonic() < deadline_ns)
    after = inspect()
    t2, m2 = now(), monotonic()
    check(deadline_ns is None or m2 < deadline_ns)
    aid, workers_after, health1 = identity(after, names, t2, boot)
    check(bid == aid and workerids == workers_after and bid[2] <= t0 <= t1 <= t2)
    elapsed = m2 - m0
    check(0 <= elapsed <= (DEADLINE_SECONDS + 2) * NS and
          abs(t2 - t0 - elapsed) <= MAX_CLOCK_SKEW_NS)
    sample = min(t0, health0, health1)
    check(0 < sample <= t2 < sample + TTL_NS)
    row = dict(container_id=bid[0], event='pass' if default and dvr else 'fail',
               returncode=0, count=int(default)+int(dvr), output_complete=True,
               reply_output_valid=True, default_present=default, dvr_present=dvr)
    _, value = celery(t0, row, (t2, after.backend))
    publish(fd, 'celery', (sample, value, None))
    return value
