"""Forced-command entry point. No shell, subprocess, service APIs or network clients."""
import json
import os
import re
import signal
import stat
import sys
import time
from pathlib import Path

if __name__ == '__main__':
    # The sshd ForceCommand uses Python isolated mode and this administrator-owned directory.
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from celery_handoff import guarded_observe, signature
from ops_protocol import PROJECTIONS, STATES, TAG, check, decode, observations, projected_value

EVIDENCE = Path('/run/samwise-observations')
LIMIT = 65536
AGE = 300
ATTRIBUTE = re.compile(r'[ \t]+([\w-]+)="([^"]*)"')
END_HEADER = re.compile(r'[ \t]*,')


def observe(dirfd, name, owner):
    # A single fixed component; never follow a symlink or block opening a FIFO.
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dirfd)
    with os.fdopen(fd, 'rb') as source:
        before = os.fstat(fd)
        check(stat.S_ISREG(before.st_mode) and before.st_uid == owner and not before.st_mode & 0o022)
        check(before.st_nlink == 1)
        if name in PROJECTIONS:
            check(stat.S_IMODE(before.st_mode) in (0o600, 0o640))
        if name not in PROJECTIONS and not 0 <= time.time() - before.st_mtime <= AGE:
            return 'stale'
        check(before.st_size <= LIMIT)
        data = source.read(LIMIT + 1)
        after = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
        check(len(data) == before.st_size and os.path.samestat(before, after)
              and before.st_ctime_ns == after.st_ctime_ns)
    if name in PROJECTIONS:
        return projected_value(data, name, before.st_mtime_ns, time.time_ns())
    if name == 'relay':
        value = data.decode('ascii').strip()
        check(value in STATES[name])
        return value
    if name == 'playlist':
        lines = data.decode('utf-8-sig').splitlines()
        check(lines and lines[0].strip() == '#EXTM3U')
        for line in lines:
            if not line.startswith('#EXTINF:'):
                continue
            # Match attributes from the start of the header. Never search the display name,
            # URL, or a different quoted attribute for something resembling a channel ID.
            header = re.match(r'^#EXTINF:[^ ,\t]+', line)
            check(header is not None)
            pos = header.end()
            channel_id = None
            while True:
                if END_HEADER.match(line, pos):
                    break
                attr = ATTRIBUTE.match(line, pos)
                check(attr is not None)
                if attr[1] == 'tvg-id':
                    check(channel_id is None)
                    channel_id = attr[2]
                pos = attr.end()
            if channel_id == 'dw-english-permanent':
                return 'present'
        return 'absent'
    if name == 'logs':
        # Input is a bounded projection of Dispatcharr severity records only.
        levels = data.decode('ascii').splitlines()
        check(levels and all(level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') for level in levels))
        return 'warning-or-error' if set(levels) & {'WARNING', 'ERROR', 'CRITICAL'} else 'no-warning-in-sample'
    raise ValueError('unsupported observation')


def collect(raw, directory=EVIDENCE, owner=0):
    req = decode(raw)
    check(type(req) is dict and set(req) == {'observations'})
    names = observations(req['observations'])
    result = dict.fromkeys(names, 'unavailable')
    try:
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        return result
    try:
        info = os.fstat(fd)
        if info.st_uid != owner or info.st_mode & 0o022:
            return result
        for n in names:
            try:
                if n == 'celery':
                    actor = signature(os.fstat(fd))[:5]
                    check(actor == signature(os.stat(directory, follow_symlinks=False))[:5])
                    value = guarded_observe(fd, owner, lambda child: observe(child, n, owner))
                    check(actor == signature(os.fstat(fd))[:5] ==
                          signature(os.stat(directory, follow_symlinks=False))[:5])
                    result[n] = value
                else:
                    result[n] = observe(fd, n, owner)
            except (OSError, ValueError, TypeError, KeyError):
                pass
    finally:
        os.close(fd)
    return result


if __name__ == '__main__':
    signal.alarm(10)
    try:
        check(os.getuid() != 0 and os.environ.get('SSH_ORIGINAL_COMMAND') == TAG and len(sys.argv) == 1)
        raw = sys.stdin.buffer.read(1025)
        check(len(raw) <= 1024)
        print(json.dumps(collect(raw), separators=(',', ':')))
    except (OSError, ValueError):
        sys.exit(64)
