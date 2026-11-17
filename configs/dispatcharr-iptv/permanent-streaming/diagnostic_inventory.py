"""Compare private deployment snapshots offline; never contact Docker or services.

Input schema matches the failed deployment's sanitized baseline() records. Full
records stay private: CLI output contains only pass/refusal, never their values.
"""
import argparse
import json
from pathlib import Path
from contracts import NAMES, Refusal

DEDICATED = frozenset(NAMES.values())
FIELDS = ('id', 'image', 'started', 'running', 'health', 'restart',
          'restart_count', 'host_config_sha256')


def unrelated(snapshot):
    result = {}
    seen = set()
    for record in snapshot['containers']:
        name = record['name'].removeprefix('/')
        if not name or '/' in name or name in seen:
            raise Refusal('invalid_or_duplicate_inventory_name')
        seen.add(name)
        if name in DEDICATED:
            continue
        # Index all required fields so an incomplete snapshot cannot pass.
        result[name] = tuple(record[field] for field in FIELDS)
    return result


def compare(before, after):
    if unrelated(before) != unrelated(after):
        raise Refusal('unrelated_container_identity_or_configuration_changed')
    for key in ('network_ids', 'docker_process', 'dedicated_network'):
        if before[key] != after[key]:
            raise Refusal('Docker_or_network_identity_changed')
    return {'unrelated_containers': 'unchanged', 'Docker_and_networks': 'unchanged'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args()
    try:
        result = compare(json.loads(args.before.read_text()), json.loads(args.after.read_text()))
    except Exception:
        raise SystemExit('Deployment inventory comparison refused; values withheld.')
    print(json.dumps(result, sort_keys=True))
