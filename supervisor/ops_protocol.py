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
