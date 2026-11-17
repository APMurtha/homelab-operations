"""Non-media loopback challenge against the current instance; no manifest fetch."""
import argparse
import json
import re
import time
import urllib.request
from pathlib import Path
from files import read_json
from api import NoRedirect


def current(runtime, opener=None, clock=time.monotonic):
    runtime = Path(runtime)
    record = read_json(runtime / 'endpoint.json')
    stats = read_json(runtime / 'stats.json')
    instance = record['instance']
    if not re.fullmatch('[a-f0-9]{32}', instance):
        raise ValueError('instance_invalid')
    expected = 'http://127.0.0.1:19193/s/' + instance + '/live.m3u8'
    if record['endpoint'] != expected or stats['instance'] != instance:
        raise ValueError('endpoint_mismatch')
    age = clock() - stats['monotonic']
    if not 0 <= age < 6 or stats['fatal'] or stats['stopped']:
        raise ValueError('relay_not_ready')
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open('http://127.0.0.1:19193/healthz', timeout=3) as response:
        body = response.read(1025)
        if response.status != 200 or len(body) > 1024:
            raise ValueError('health_failed')
    if json.loads(body) != {'instance': instance, 'ok': True}:
        raise ValueError('stale_instance')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', default='/runtime')
    a = p.parse_args()
    try: current(a.runtime)
    except Exception: raise SystemExit('Relay health failed; details withheld.')
