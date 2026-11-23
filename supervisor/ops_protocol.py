"""Shared, closed wire contract. This module has no transport or host privileges."""
import json

TAG = 'samwise-observe-v1'
TARGET = 'rivendell-dispatcharr'
STATES = {
    'backend': ('running', 'stopped', 'unhealthy'),
    'relay': ('running', 'stopped', 'unhealthy'),
    'vpn-container': ('running', 'stopped', 'unhealthy'),
    'jellyfin': ('running', 'stopped', 'unhealthy'),
    'gateway': ('running', 'stopped', 'unhealthy'),
    'vpn': ('verified', 'withdrawn', 'failed'),
    'guard': ('verified', 'withdrawn', 'failed'),
    'celery': ('both-ready', 'readiness-failed'),
    'logs': ('warning-or-error', 'no-warning-in-sample'),
    'playlist': ('present', 'absent'),
    'jellyfin-channel': ('present', 'absent'),
    'jellyfin-guide': ('current', 'empty'),
}
UNKNOWN = ('unavailable', 'stale')
MAX_REPLY = 4096


def check(condition):
    if not condition:
        raise ValueError('invalid operations protocol')


def decode(data):
    def unique(pairs):
        obj = dict(pairs)
        check(len(obj) == len(pairs))
        return obj
    try:
        return json.loads(data, object_pairs_hook=unique)
    except (TypeError, UnicodeError, RecursionError):
        raise ValueError('invalid operations protocol') from None


def observations(names):
    check(type(names) is list and 1 <= len(names) <= len(STATES))
    check(all(type(n) is str and n in STATES for n in names) and len(set(names)) == len(names))
    return names


def reply(data, names):
    obj = decode(data)
    check(type(obj) is dict and set(obj) == set(names))
    for n in names:
        check(type(obj[n]) is str and obj[n] in STATES[n] + UNKNOWN)
    return {n: obj[n] for n in names}

# Receipts for the previously unenrolled sources. Legacy relay/playlist/logs retain their format.
NS = 1_000_000_000
PROJECTIONS = {
    'backend': ('engine-health-v1', 60), 'gateway': ('engine-health-v1', 60),
    'vpn-container': ('engine-health-v1', 60), 'jellyfin': ('engine-health-v1', 60),
    'celery': ('dispatcharr-pong-v1', 60),
    'guard': ('kernel-policy-v1', 30), 'vpn': ('kernel-policy-v1', 30),
    'jellyfin-channel': ('jellyfin-livetv-v1', 120), 'jellyfin-guide': ('jellyfin-livetv-v1', 120),
}


def projected_value(data, name, mtime_ns, now_ns):
    obj = decode(data)
    source, ttl = PROJECTIONS[name]
    check(type(obj) is dict and set(obj) == {'schema','source','name','sample_ns','until_ns','value'})
    check(obj['schema'] == 'samwise-projection-v2' and obj['name'] == name and obj['source'] == source)
    start, end, value = obj['sample_ns'], obj['until_ns'], obj['value']
    check(type(start) is int and type(end) is int and 0 < start == mtime_ns <= now_ns)
    check(start < end <= start + ttl * NS and type(value) is str and value in STATES[name])
    return value if now_ns < end else 'stale'
