"""Staging-only Celery readiness acquisition core; no production launcher."""
from contextlib import suppress
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time
import uuid

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
    clean = False
    with subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True,
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
                left = end - time.monotonic()
                if left <= 0:
                    raise TimeoutError('capture_deadline')
                result = child.wait(timeout=left), bytes(buffers[0]), bytes(buffers[1])
                clean = True
                return result
        finally:
            if not clean:
                with suppress(ProcessLookupError):
                    os.killpg(child.pid, signal.SIGKILL)


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


def acquire(output, owner, boot, names, inspect, ping, *,
            now=time.time_ns, monotonic=time.monotonic_ns):
    """Staging entry point. Inspect callbacks are trusted, bounded, passive adapters.

    Publish only the existing sanitized projection. Keep its source contract,
    using the oldest actual observation time from the bracket and backend health.
    Never run beside another writer of the celery projection.
    """
    with directory(output, owner, private=True) as fd:
        lock = os.open('.celery-acquisition.lock', os.O_RDWR | os.O_CREAT |
                       os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd)
        try:
            lock_stat = os.fstat(lock)
            check(stat.S_ISREG(lock_stat.st_mode) and lock_stat.st_uid == owner and
                  stat.S_IMODE(lock_stat.st_mode) == 0o600 and lock_stat.st_nlink == 1)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return 'busy'
            remove_projection(fd)
            try:
                names = destinations(names)
                check(str(uuid.UUID(boot)) == boot)
                t0, m0 = now(), monotonic()
                before = inspect()
                t1 = now()
                bid, workerids, health0 = identity(before, names, t1, boot)
                default, dvr = pongs(ping(names), names)
                after = inspect()
                t2, m2 = now(), monotonic()
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
                # Reuse the installed projector's pure Celery validation before publication.
                _, value = celery(t0, row, (t2, after.backend))
                publish(fd, 'celery', (sample, value, None))
                return value
            except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError,
                    subprocess.SubprocessError):
                remove_projection(fd)
                return 'unavailable'
        finally:
            os.close(lock)
