#!/usr/bin/env python3
"""Offline renderer. Inputs express an existing, separately reviewed trust decision."""
import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import secrets
import stat
import sys

import celery_operational_witness as witness
import celery_shadow_launcher as launcher
import celery_site_pidbox as pidbox


NANOSECONDS = 10**9
INPUT_LIMIT = 8192
BOUNDARY_LIMIT = 1024 * 1024
PATHS = ('witness', 'pidbox-ping', 'celery_broker_guard.py', 'pidbox-runtime.zip')
LIMITS = (256*1024, 256*1024, 128*1024, pidbox.MAX_RUNTIME)


@contextmanager
def directory(path):
    """Walk actual directory entries, not symlinks, even for a local caller."""
    absolute = Path(os.path.abspath(path))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open('/', flags)
    try:
        for component in absolute.parts[1:]:
            child = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def read_file(fd, name, limit, private=False):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    with os.fdopen(os.open(name, flags, dir_fd=fd), 'rb') as stream:
        before = os.fstat(stream.fileno())
        witness.require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                        and 0 < before.st_size <= limit)
        if private:
            witness.require(before.st_uid in (0, os.geteuid()) and before.st_mode & 0o077 == 0)
        data = stream.read(limit + 1)
        after = os.stat(name, dir_fd=fd, follow_symlinks=False)
        witness.require(os.path.samestat(before, after) and before.st_ctime_ns == after.st_ctime_ns
                        and len(data) == before.st_size)
        return data


def read_local(path, limit, private=False):
    with directory(path.parent) as fd:
        return read_file(fd, path.name, limit, private=private)


def json_input(path):
    return witness.sanitized_json(read_local(path, INPUT_LIMIT))


def bundle(snapshot, backend, boundary_sha256, payload_pins, node, now_ns, ttl_seconds):
    """Validate and cross-bind every generated record before creating any files."""
    witness.require(type(snapshot) is dict and 'boot' in snapshot)
    boot = snapshot['boot']
    witness.enrollment(snapshot, boot)
    witness.health(backend, snapshot, now_ns)
    witness.require(node in (launcher.HOST, launcher.STAGE_HOST)
                    and type(ttl_seconds) is int
                    and launcher.HARD_SECONDS <= ttl_seconds <= 300)
    names = sorted(snapshot['workers'])
    scope = pidbox.digest(pidbox.canonical(snapshot['scope']))
    broker = pidbox.canonical(dict(version=pidbox.OPERATIONAL, boot=boot,
        net_inode=snapshot['net_inode'], scope_sha256=scope, names=names,
        runtime_sha256=payload_pins['pidbox-runtime.zip'],
        broker_guard_sha256=payload_pins['celery_broker_guard.py'], boundary_sha256=boundary_sha256))
    pidbox.enrollment(broker)
    w = pidbox.canonical(snapshot)
    version, target = ((launcher.PRODUCTION_PERMIT, launcher.TARGET) if node == launcher.HOST
                       else (launcher.STAGE_PERMIT, launcher.STAGE_TARGET))
    permit = pidbox.canonical(dict(version=version, host=node, target=target, boot=boot,
        nonce=secrets.token_hex(32), not_before_ns=now_ns,
        expires_ns=now_ns+ttl_seconds*NANOSECONDS, backend_id=snapshot['backend_id'],
        backend_pid=snapshot['backend_pid'], backend_start_ns=snapshot['backend_start_ns'],
        net_inode=snapshot['net_inode'], names=names, broker_endpoint=snapshot['scope']['endpoint'],
        broker_scope_sha256=scope, witness_sha256=payload_pins['witness'],
        ping_sha256=payload_pins['pidbox-ping'], witness_enrollment_sha256=pidbox.digest(w),
        pidbox_enrollment_sha256=pidbox.digest(broker),
        boundary_contract=launcher.TRUST, boundary_sha256=boundary_sha256))
    launcher.permit(permit, boot, now_ns, node=node)
    return dict(zip(('witness-enrollment.json','pidbox-enrollment.json','one-shot.json',
                    'backend-witness.json'), (w, broker, permit, pidbox.canonical(backend))))


def write_new(output, records):
    witness.require(output.name not in ('.', '..', ''))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    with directory(output.parent) as parent:
        os.mkdir(output.name, mode=0o700, dir_fd=parent)
        made = []
        fd = None
        try:
            fd = os.open(output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                         dir_fd=parent)
            info = os.fstat(fd)
            witness.require(info.st_uid == os.geteuid() and (info.st_mode & 0o077) == 0)
            os.fchmod(fd, 0o700)
            for name, raw in records.items():
                piece = os.open(name, flags, 0o600, dir_fd=fd)
                made.append(name)
                with os.fdopen(piece,'wb') as stream:
                    os.fchmod(stream.fileno(), 0o600)
                    stream.write(raw)
        except Exception:
            if fd is not None:
                for name in made:
                    os.unlink(name, dir_fd=fd)
            os.rmdir(output.name, dir_fd=parent)
            raise
        finally:
            if fd is not None:
                os.close(fd)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('witness','health','boundary','payload','output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--node', choices=(launcher.HOST,launcher.STAGE_HOST), required=True)
    p.add_argument('--now-ns', type=int, required=True)
    p.add_argument('--ttl-seconds', type=int, default=60)
    a = p.parse_args(argv)
    try:
        snapshot = json_input(a.witness)
        backend = json_input(a.health)
        boundary = read_local(a.boundary, BOUNDARY_LIMIT, private=True)
        witness.require(boundary.strip())
        with directory(a.payload) as fd:
            pins = {name:pidbox.digest(read_file(fd,name,limit))
                    for name, limit in zip(PATHS,LIMITS)}
        records = bundle(snapshot,backend,pidbox.digest(boundary),pins,a.node,a.now_ns,a.ttl_seconds)
        write_new(a.output,records)
    except (OSError, ValueError, TypeError, KeyError, RecursionError, OverflowError):
        print('enrollment rendering refused', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
