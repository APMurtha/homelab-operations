"""Consume two fixed engine inspection rounds from a half-closed descriptor."""
import json
import os
from pathlib import Path
import secrets
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dispatcharr_monitor_fields import engine_fields, engine_time
from dispatcharr_project import CONTAINERS, container
from ops_protocol import NS, check, decode

CACHE = Path('/run/samwise-engine-health/batch')
MAX_BODY = 512 * 1024


def line(stream):
    raw = stream.readline(1025)
    check(len(raw) <= 1024 and raw.endswith(b'\r\n'))
    return raw[:-2]


def exact(stream, size):
    check(0 <= size <= MAX_BODY)
    data = stream.read(size)
    check(len(data) == size)
    return data


def response(stream):
    status = line(stream).split(b' ', 2)
    check(len(status) == 3 and status[0] == b'HTTP/1.1' and status[1].isdigit())
    headers = {}
    for _ in range(48):
        raw = line(stream)
        if not raw:
            break
        key, sep, value = raw.partition(b':')
        check(sep and key.lower() not in headers)
        headers[key.lower()] = value.strip()
    else:
        raise ValueError('headers')
    if headers.get(b'transfer-encoding') == b'chunked':
        check(b'content-length' not in headers)
        data = bytearray()
        for _ in range(2048):
            raw = line(stream)
            check(1 <= len(raw) <= 8 and all(c in b'0123456789abcdefABCDEF' for c in raw))
            length = int(raw, 16)
            check(len(data) + length <= MAX_BODY)
            if not length:
                check(line(stream) == b'')
                break
            data.extend(exact(stream, length))
            check(exact(stream, 2) == b'\r\n')
        else:
            raise ValueError('chunks')
    else:
        length = headers.get(b'content-length', b'')
        check(b'transfer-encoding' not in headers and length.isdigit())
        data = exact(stream, int(length))
    return decode(data) if status[1] == b'200' else None


def select(name, obj, observed):
    state = obj['State']
    for key in ('Paused', 'Restarting', 'Dead', 'Running'):
        check(type(state[key]) is bool)
    check(not state['Paused'] and not state['Restarting'] and state['Dead'] == (state['Status'] == 'dead'))
    row = engine_fields(obj)
    if row['Status'] == 'running':
        logs = state['Health']['Log']
        check(type(logs) is list and 0 < len(logs) <= 5)
        start = engine_time(logs[-1]['Start'])
        check(row['StartedNs'] <= start <= row['HealthEndNs'])
    else:
        row['StartedNs'] = engine_time(state['StartedAt'])
    container(name, observed, row)
    return row


def capture(stream, began, clock=time.time_ns):
    rounds = []
    for _ in range(2):
        rows = {}
        for name in CONTAINERS:
            obj = response(stream)
            observed = clock()
            check(began <= observed <= began + 4 * NS)
            try:
                rows[name] = (observed, select(name, obj, observed))
            except (KeyError, IndexError, ValueError, TypeError, OverflowError):
                rows[name] = None
        rounds.append(rows)
    check(stream.read(1) == b'')
    records = {}
    for name in CONTAINERS:
        first, second = (r[name] for r in rounds)
        if not first or not second:
            continue
        a, b = first[1], second[1]
        keys = ('Id','Name','StartedNs','Running','Pid','Status','Health','HealthExitCode')
        if any(a[k] != b[k] for k in keys):
            continue
        if a['Running'] and b['HealthEndNs'] < a['HealthEndNs']:
            continue
        # Conservative first sample, including its original probe time. Stopped
        # state can only be asserted as early as the request for this batch.
        if not a['Running'] and a['StartedNs'] > began:
            continue
        records[name] = [first[0] if a['Running'] else began, a]
    return dict(began=began, ended=clock(), records=records)


def main():
    temp = CACHE.with_name('.batch-' + secrets.token_hex(12))
    CACHE.unlink(missing_ok=True)
    try:
        data = capture(sys.stdin.buffer, int(sys.argv[1]))
        with temp.open('x') as stream:
            json.dump(data, stream, separators=(',', ':'))
        temp.replace(CACHE)
    finally:
        temp.unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.exit(1)
