"""Private bounded JSON and atomic writes. No credential values in exceptions."""
import json
import os
from pathlib import Path
import stat


def read_json(path, limit=262144):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            raise ValueError('regular_file_required')
        raw = f.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('input_size_limit')
    return json.loads(raw)


def private_json(path):
    st = Path(path).lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
        raise ValueError('private_file_required')
    return read_json(path)


def atomic(path, data, mode=0o600):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, mode)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def write_json(path, value):
    atomic(path, (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode())


def private_directory(path):
    path = Path(path)
    path.mkdir(mode=0o700, exist_ok=True)
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise ValueError('private_directory_required')
    return path
