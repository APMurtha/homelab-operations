"""Validate the private batch and publish only the four enrolled topics."""
import grp
import os
from pathlib import Path
import pwd
import stat
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dispatcharr_project import CONTAINERS, OUTPUT, container, fields, publish, read_json
from ops_protocol import NS, check


def load(fd, uid, now):
    st = os.fstat(fd)
    check(st.st_uid == uid and stat.S_IMODE(st.st_mode) == 0o700)
    data, stamp = read_json(fd, 'batch', uid)
    fields(data, 'began ended records')
    began, ended = data['began'], data['ended']
    check(type(began) is int and type(ended) is int and 0 < began <= ended <= now)
    # Filesystem mtime can round down to the kernel tick. Freshness is anchored
    # to captured timestamps. A touched old batch never gets a new lease.
    check(ended-began <= 4*NS and now-began <= 5*NS and abs(stamp-ended) <= NS)
    records = data['records']
    check(type(records) is dict and set(records) <= set(CONTAINERS))
    return began, ended, records


def release(out, data):
    began, ended, records = data
    for name in CONTAINERS:
        try:
            sample, row = records[name]
            check(type(sample) is int and began <= sample <= ended)
            stamp, value = container(name, sample, row)
            publish(out, name, (stamp, value, None))
        except (OSError, KeyError, TypeError, ValueError):
            try:
                os.unlink(name, dir_fd=out)
            except FileNotFoundError:
                pass


def main():
    flags = os.O_DIRECTORY | os.O_NOFOLLOW | os.O_RDONLY
    out = os.open(OUTPUT, flags)
    try:
        st = os.fstat(out)
        check(st.st_uid == 0 and st.st_gid == grp.getgrnam('samwise-observe').gr_gid
              and stat.S_IMODE(st.st_mode) == 0o750)
        data = (0, 0, {})
        try:
            cache = os.open('/run/samwise-engine-health', flags)
            try:
                data = load(cache, pwd.getpwnam('samwise-engine-health').pw_uid, time.time_ns())
            finally:
                os.close(cache)
        except (OSError, KeyError, TypeError, ValueError):
            pass
        release(out, data)
    finally:
        os.close(out)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.exit(1)
