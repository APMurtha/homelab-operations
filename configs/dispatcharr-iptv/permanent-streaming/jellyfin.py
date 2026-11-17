"""Future authorized tuner/provider-only transaction. No deployment on import."""
import argparse
import copy
import json
from pathlib import Path
import urllib.request
import uuid
from api import NoRedirect
from files import private_json, read_json, write_json

TUNER = str(uuid.uuid5(uuid.NAMESPACE_URL, 'homelab-operations:permanent-dw:9001:tuner'))
GUIDE = str(uuid.uuid5(uuid.NAMESPACE_URL, 'homelab-operations:permanent-dw:9001:guide'))
BASE = '/config/iptv/permanent-dw/current/'


def plan(current):
    result = copy.deepcopy(current)
    tuner = {'Id': TUNER, 'Type': 'm3u', 'Url': BASE+'dispatcharr.m3u',
             'FriendlyName': 'DW English — managed', 'TunerCount': 1,
             'AllowStreamSharing': True, 'EnableStreamLooping': False,
             'AllowHWTranscoding': False, 'ImportFavoritesOnly': False}
    guide = {'Id': GUIDE, 'Type': 'xmltv', 'Path': BASE+'guide.xml',
             'EnabledTuners': [TUNER], 'EnableAllTuners': False, 'ChannelMappings': []}
    for key, desired in [('TunerHosts', tuner), ('ListingProviders', guide)]:
        rows = result.get(key, [])
        if not isinstance(rows, list): raise ValueError('Jellyfin_schema_changed')
        existing = [x for x in rows if x.get('Id') == desired['Id']]
        if len(existing) > 1: raise ValueError('owned_configuration_ambiguous')
        if existing and any(existing[0].get(k) != v for k,v in desired.items()):
            raise ValueError('owned_configuration_conflict')
        if not existing: rows.append(desired)
        result[key] = rows
    return result


class Jellyfin:
    def __init__(self, token):
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.headers = {'Authorization': 'MediaBrowser Client="NEST Permanent DW", Device="Rivendell", '
                        'DeviceId="nest-permanent-dw", Version="1", Token="'+token+'"',
                        'Content-Type': 'application/json'}

    def request(self, path, value=None):
        import re
        if path not in ['/System/Configuration/livetv','/ScheduledTasks'] and not re.fullmatch(r'/ScheduledTasks/Running/[a-fA-F0-9-]{1,64}',path):
            raise ValueError('Jellyfin_scope_refused')
        data = json.dumps(value).encode() if value is not None else None
        req = urllib.request.Request('http://127.0.0.1:8096'+path,
                data=data, headers=self.headers, method='POST' if data is not None else 'GET')
        with self.opener.open(req, timeout=15) as response:
            raw = response.read(1048577)
            if len(raw) > 1048576: raise ValueError('configuration_limit')
        return json.loads(raw) if raw else None

    def config(self, value=None): return self.request('/System/Configuration/livetv',value)

    def refresh_guide(self):
        tasks=[t for t in self.request('/ScheduledTasks') if t.get('Key')=='RefreshGuide']
        if len(tasks)!=1: raise ValueError('guide_task_ambiguous')
        self.request('/ScheduledTasks/Running/'+tasks[0]['Id'],{})


def scoped_result(expected, actual):
    for key in set(expected)|set(actual):
        if key not in ['TunerHosts','ListingProviders'] and expected.get(key)!=actual.get(key): return False
    for key, ident in [('TunerHosts',TUNER),('ListingProviders',GUIDE)]:
        wanted=expected.get(key,[]); found=actual.get(key,[])
        old=[x for x in wanted if x.get('Id')!=ident]; other=[x for x in found if x.get('Id')!=ident]
        owned=[x for x in found if x.get('Id')==ident]; target=[x for x in wanted if x.get('Id')==ident]
        if old!=other or len(owned)!=1 or len(target)!=1 or not all(owned[0].get(k)==v for k,v in target[0].items()):return False
    return True


def apply(api, receipt):
    receipt = Path(receipt)
    if receipt.exists(): raise ValueError('reconcile_existing_Jellyfin_receipt')
    before = api.config(); after = plan(before)
    write_json(receipt, {'before': before, 'after': after, 'state': 'intent'})
    if api.config() != before: raise ValueError('concurrent_Jellyfin_change')
    api.config(after)
    actual = api.config()
    # Jellyfin may populate extra defaults: accept only if the arrays contain our
    # intended fields and all unrelated top-level values and original rows remain.
    if not scoped_result(after,actual): raise ValueError('Jellyfin_verification_requires_reconciliation')
    write_json(receipt, {'before': before, 'after': actual, 'state': 'verified'})


def rollback(api, receipt):
    saved = read_json(receipt); actual = api.config()
    if actual == saved['before']: return
    if actual != saved['after'] and not (saved.get('state')=='intent' and scoped_result(saved['after'],actual)):
        raise ValueError('Jellyfin_rollback_conflict')
    api.config(saved['before'])
    if api.config() != saved['before']: raise ValueError('Jellyfin_rollback_unverified')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['apply','rollback'])
    p.add_argument('--credentials', required=True); p.add_argument('--receipt', required=True)
    a = p.parse_args()
    try:
        credential = private_json(a.credentials)
        api = Jellyfin(credential['AccessToken'])
        (apply if a.action == 'apply' else rollback)(api, a.receipt)
        api.refresh_guide()
    except Exception: raise SystemExit('Jellyfin transaction refused; reconcile the private receipt.')
