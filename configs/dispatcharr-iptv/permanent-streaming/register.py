"""Single-channel API saga. Durable intents reconcile unknown outcomes before reuse."""
import argparse
import copy
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import uuid
from api import API, Rejected, Uncertain, NotFound
from files import private_json, read_json, write_json, private_directory
from health import current

STREAMS = '/api/channels/streams/'
CHANNELS = '/api/channels/channels/'
TVG = 'dw-english-permanent'
SNAME = 'DW English — managed relay'
CNAME = 'DW English'


def matches(row, values):
    return all(row.get(k) == v for k, v in values.items())


def owned_detail(api, collection, fields):
    """Only authenticated detail GET 404 means absence; list omission never does."""
    try:
        row = api.request('GET', collection + str(identifier(fields)) + '/')
    except NotFound:
        return None
    if not isinstance(row, dict) or identifier(row) != fields['id']:
        raise Rejected('owned_detail_invalid')
    return row


def unshared(api, stream_id, except_channel=None):
    # API.rows requests visibility_filter=all on the pinned admin channel API.
    for channel in api.rows(CHANNELS):
        identifier(channel)
        refs = channel.get('streams')
        if not isinstance(refs, list) or any(type(x) is not int for x in refs):
            raise Rejected('channel_reference_inventory_invalid')
        if stream_id in refs and channel['id'] != except_channel:
            raise Rejected('owned_stream_shared')


def identifier(row):
    if type(row.get('id')) is not int or row['id'] <= 0: raise Rejected('invalid_ID')
    return row['id']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate_profile(rows):
    profiles = []
    for row in rows:
        args = shlex.split(row.get('parameters', ''))
        copy_codec = any(args[i:i+2] == ['-c', 'copy'] for i in range(len(args)))
        mpegts = any(args[i:i+2] == ['-f', 'mpegts'] for i in range(len(args)))
        codec_args = [args[i+1] for i,x in enumerate(args[:-1]) if x in ['-c','-codec','-c:v','-c:a','-codec:v','-codec:a']]
        if any(v != 'copy' for v in codec_args): continue
        if row.get('command') == 'ffmpeg' and row.get('locked') and row.get('is_active') and copy_codec and mpegts:
            profiles.append(row)
    if len(profiles) != 1: raise Rejected('streamcopy_profile_ambiguous')
    return identifier(profiles[0])


def network_check(settings, expected_hash, clients):
    rows = [r for r in settings if r.get('key') == 'network_access']
    if len(rows) != 1 or digest(rows[0]['value']) != expected_hash:
        raise Rejected('network_access_review_required')
    value = rows[0]['value']
    for key in ['M3U_EPG', 'XC_API']:
        if value.get(key) != '127.0.0.1/32': raise Rejected('non_stream_ACL_changed')
    networks = [ipaddress.ip_network(x.strip(), strict=True) for x in value['STREAMS'].split(',')]
    if any(n.version != 4 or n.prefixlen != 32 for n in networks):
        raise Rejected('exact_stream_peers_required')
    required = {'127.0.0.1', '10.10.20.30', '172.16.70.1', *clients}
    if {str(n.network_address) for n in networks} != required:
        raise Rejected('stream_peers_changed')


class Transaction:
    def __init__(self, api, path):
        self.api, self.path = api, Path(path)
        saved = read_json(path) if self.path.exists() else {'ops': [], 'uncertain': False}
        self.ops = saved['ops']
        self.uncertain = saved['uncertain']

    def save(self): write_json(self.path, {'ops': self.ops, 'uncertain': self.uncertain})

    def mutate(self, collection, before, after, extras=None):
        if before:
            current_row = self.api.request('GET', collection + str(identifier(before)) + '/')
            if not matches(current_row, before): raise Rejected('concurrent_record_change')
        op = {'collection': collection, 'id': identifier(before) if before else None,
              'before': before, 'after': after}
        self.ops.append(op); self.save()  # write ahead, including an unknown create
        path = collection + (str(op['id']) + '/' if before else '')
        try:
            result = self.api.request('PATCH' if before else 'POST', path, dict(after, **(extras or {})))
        except Uncertain:
            self.uncertain = True; self.save(); raise
        op['id'] = identifier(result); self.save()
        actual = self.api.request('GET', collection + str(op['id']) + '/')
        if not matches(actual, after): raise Rejected('write_verification_failed')
        return actual

    def rollback(self):
        """Reconcile each intent by GET. Conflicts refuse instead of overwriting an operator."""
        if (self.path.parent/'commit.json').exists():
            raise Rejected('committed_transaction_requires_commit_reconciliation')
        for op in reversed(self.ops):
            collection = op['collection']
            if collection not in [STREAMS, CHANNELS]: raise Rejected('journal_scope_invalid')
            if op['id']:
                row = owned_detail(self.api, collection, {'id': op['id']})
                candidates = [row] if row is not None else []
            else:
                candidates = [r for r in self.api.rows(collection)
                              if r.get('name') == op['after']['name'] and r.get('tvg_id') == TVG]
            if not candidates:
                if op['before']: raise Rejected('rollback_record_missing')
                continue
            if len(candidates) != 1: raise Rejected('rollback_ambiguous')
            row = candidates[0]
            if op.get('rollback_delete_pending'): raise Uncertain('unresolved_delete_requires_operator_reconciliation')
            if op['before'] and matches(row, {k: v for k, v in op['before'].items() if k != 'id'}):
                continue  # previous interrupted rollback already restored this row
            if not matches(row, op['after']): raise Rejected('rollback_conflict')
            path = collection + str(identifier(row)) + '/'
            if op['before']:
                body = {k: v for k, v in op['before'].items() if k != 'id'}
                self.api.request('PATCH', path, body)
                if not matches(self.api.request('GET', path), body): raise Rejected('rollback_not_verified')
            else:
                # A created stream may not be deleted if another channel adopted it.
                if collection == STREAMS: unshared(self.api, row['id'])
                op['id'] = identifier(row); op['rollback_delete_pending'] = True; self.save()
                self.api.request('DELETE', path)
                if owned_detail(self.api, collection, {'id': row['id']}) is not None:
                    raise Rejected('rollback_not_verified')
        self.ops = []; self.path.unlink(missing_ok=True)

    def commit(self): self.path.unlink(missing_ok=True); self.ops = []


def reconcile(api, runtime, state, config):
    """Requires current relay health; API/backend readiness is a preceding unit gate."""
    record = current(runtime)
    state = private_directory(state)
    if (state/'rollback-owned.json').exists():
        raise Rejected('rollback_state_requires_operator_reconciliation')
    transaction = Transaction(api, state / 'journal.json')
    commit = state / 'commit.json'
    if commit.exists():
        saved = read_json(commit)
        for collection, fields in [(STREAMS, saved['stream']), (CHANNELS, saved['channel'])]:
            actual = api.request('GET', collection + str(identifier(fields)) + '/')
            if not matches(actual, fields): raise Rejected('committed_record_conflict')
        write_json(state / 'owned.json', saved)
        transaction.commit(); commit.unlink()
    elif transaction.ops:
        raise Rejected('pending_transaction_requires_explicit_reconciliation')
    profile = validate_profile(api.rows('/api/core/streamprofiles/'))
    network_check(api.rows('/api/core/settings/'), config['expected_network_access_sha256'], config['jellyfin_peer_ipv4'])
    groups = [r for r in api.rows('/api/channels/groups/') if r.get('name') == 'Default Group']
    if len(groups) != 1: raise Rejected('existing_default_group_required')
    ledger_file = state / 'owned.json'
    owned = read_json(ledger_file) if ledger_file.exists() else None
    streams, channels = api.rows(STREAMS), api.rows(CHANNELS)
    if owned:
        found = []
        for collection, saved in [(STREAMS, owned['stream']), (CHANNELS, owned['channel'])]:
            row = owned_detail(api, collection, saved)
            if row is None or not matches(row, saved): raise Rejected('owned_record_conflict')
            found.append(row)
        stream, channel = found
        unshared(api, stream['id'], channel['id'])
    else:
        if any(r.get('tvg_id') == TVG or r.get('name') == SNAME for r in streams) or any(
            r.get('tvg_id') == TVG or r.get('name') == CNAME or r.get('channel_number') == 9001 for r in channels):
            raise Rejected('channel_or_stream_collision')
        stream = channel = None
    stream_body = {'name': SNAME, 'url': record['endpoint'], 'tvg_id': TVG, 'stream_profile_id': profile,
                   'logo_url': '', 'is_adult': False, 'is_catchup': False, 'is_radio': False}
    try:
        before = dict(id=stream['id'], **{k: stream.get(k) for k in stream_body}) if stream else None
        stream = transaction.mutate(STREAMS, before, stream_body)
        if not stream.get('is_custom'): raise Rejected('custom_stream_required')
        channel_body = {'name': CNAME, 'channel_number': 9001.0, 'tvg_id': TVG, 'streams': [stream['id']],
                        'stream_profile_id': profile, 'channel_group_id': identifier(groups[0]),
                        'hidden_from_output': True, 'is_adult': False, 'is_catchup': False, 'is_radio': False}
        before = dict(id=channel['id'], **{k: channel.get(k) for k in channel_body}) if channel else None
        # Empty profile membership avoids the pinned API's default add-to-all-profiles side effect.
        channel = transaction.mutate(CHANNELS, before, channel_body,
                     {'channel_profile_ids': []} if channel is None else None)
        channel_uuid = str(uuid.UUID(channel['uuid']))
        # Verify health/instance again immediately before committing/publishing the binding.
        if current(runtime) != record: raise Rejected('relay_restarted_during_registration')
        new_owned = {'stream': dict(id=stream['id'], is_custom=True, m3u_account=stream['m3u_account'], **stream_body),
                     'channel': dict(id=channel['id'], uuid=channel_uuid, **channel_body)}
        write_json(state / 'commit.json', new_owned)
        write_json(ledger_file, new_owned)
        transaction.commit()
        (state / 'commit.json').unlink()
        write_json(Path(runtime) / 'binding.json', {'instance': record['instance'], 'channel_uuid': channel_uuid})
        return new_owned
    except Exception:
        if not (state / 'commit.json').exists() and not transaction.uncertain:
            try: transaction.rollback()
            except Uncertain:
                transaction.uncertain = True; transaction.save(); raise
        raise


def rollback_owned(api, runtime, state):
    """Explicit operator action, under exclusive administration and idle clearance.

    Write-ahead DELETE intents survive crashes. A missing detail reconciles an
    interrupted deletion; a still-present row after an unresolved intent blocks
    any repeat DELETE. There is no server CAS: external concurrency remains a
    documented check-to-use limitation.
    """
    state = Path(state); ledger = state/'owned.json'; receipt = state/'rollback-owned.json'
    if (state/'journal.json').exists() or (state/'commit.json').exists():
        raise Rejected('reconcile_pending_registration_first')
    if not ledger.exists(): return
    owned = read_json(ledger)
    stream_fields = {'id','is_custom','m3u_account','name','url','tvg_id','stream_profile_id',
                     'logo_url','is_adult','is_catchup','is_radio'}
    channel_fields = {'id','uuid','name','channel_number','tvg_id','streams','stream_profile_id',
                      'channel_group_id','hidden_from_output','is_adult','is_catchup','is_radio'}
    if (set(owned) != {'channel','stream'} or set(owned['stream']) != stream_fields
            or set(owned['channel']) != channel_fields):
        raise Rejected('owned_ledger_schema_invalid')
    stream, channel = owned['stream'], owned['channel']
    if (stream['name'] != SNAME or channel['name'] != CNAME
            or stream['tvg_id'] != TVG or channel['tvg_id'] != TVG
            or stream['is_custom'] is not True or channel['hidden_from_output'] is not True
            or channel['channel_number'] != 9001 or channel['streams'] != [identifier(stream)]
            or channel['stream_profile_id'] != stream['stream_profile_id']):
        raise Rejected('owned_ledger_scope_invalid')
    identifier(channel)
    progress = {'owned': owned, 'state': 'intent', 'deletes': {}}
    if receipt.exists():
        progress = read_json(receipt)
        if progress.get('owned') != owned: raise Rejected('rollback_ledger_conflict')
        if set(progress) != {'owned', 'state', 'deletes'} or progress['state'] not in ('intent', 'complete'):
            raise Rejected('rollback_receipt_review_required')
        if not isinstance(progress['deletes'], dict) or set(progress['deletes']) - {'channel', 'stream'}:
            raise Rejected('rollback_receipt_invalid')
        if any(v not in ('pending', 'absent') for v in progress['deletes'].values()):
            raise Rejected('rollback_receipt_invalid')
        if ('stream' in progress['deletes'] and progress['deletes'].get('channel') != 'absent'
                or progress['state'] == 'complete' and progress['deletes'] != {'channel':'absent','stream':'absent'}):
            raise Rejected('rollback_receipt_order_invalid')
    # Validate both records before *any* destructive change.
    rows = {}
    for key, collection in [('channel', CHANNELS), ('stream', STREAMS)]:
        row = owned_detail(api, collection, owned[key]); rows[key] = row
        if row is not None and not matches(row, owned[key]):
            raise Rejected('rollback_record_conflict')
        if row is not None and key in progress['deletes']:
            raise Uncertain('unresolved_delete_requires_operator_reconciliation')
    if rows['channel'] is not None and rows['stream'] is None:
        raise Rejected('owned_channel_references_missing_stream')
    unshared(api, owned['stream']['id'], owned['channel']['id'])
    write_json(receipt, progress)
    for key, collection in [('channel', CHANNELS), ('stream', STREAMS)]:
        fields = owned[key]
        if key == 'stream':
            if owned_detail(api, CHANNELS, owned['channel']) is not None:
                raise Rejected('channel_deletion_not_verified')
            unshared(api, fields['id'])
        row = owned_detail(api, collection, fields)
        if row is not None:
            if not matches(row, fields): raise Rejected('rollback_record_conflict')
            progress['deletes'][key] = 'pending'; write_json(receipt, progress)
            # No retry, including DELETE 404 or a transport error. Keep intent.
            api.request('DELETE', collection + str(fields['id']) + '/')
            if owned_detail(api, collection, fields) is not None:
                raise Uncertain('rollback_deletion_not_verified')
        progress['deletes'][key] = 'absent'; write_json(receipt, progress)
    # A final authoritative absence check precedes retiring ownership evidence.
    for key, collection in [('channel', CHANNELS), ('stream', STREAMS)]:
        if owned_detail(api, collection, owned[key]) is not None:
            raise Rejected('rollback_record_reappeared')
    progress['state'] = 'complete'; write_json(receipt, progress)
    ledger.unlink(); (Path(runtime)/'binding.json').unlink(missing_ok=True)
    (Path(runtime)/'export-state.json').unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--config', required=True)
    p.add_argument('--runtime', default='/runtime'); p.add_argument('--state', default='/data/permanent-streaming')
    p.add_argument('--reconcile-pending', action='store_true')
    p.add_argument('--rollback-owned', action='store_true')
    p.add_argument('--confirm-no-inflight-requests', action='store_true')
    a = p.parse_args(); config = private_json(a.config)
    if set(config) != {'username', 'password', 'expected_network_access_sha256', 'jellyfin_peer_ipv4'}:
        raise Rejected('registration_configuration_invalid')
    state = private_directory(a.state)
    with os.fdopen(os.open(state/'lock',os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600),'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        api = API({k: config[k] for k in ['username', 'password']})
        if a.reconcile_pending and a.rollback_owned:raise Rejected('choose_one_action')
        if a.rollback_owned:
            rollback_owned(api,a.runtime,state)
        elif a.reconcile_pending:
            if not a.confirm_no_inflight_requests: raise Rejected('operator_confirmation_required')
            Transaction(api, state/'journal.json').rollback()
        else:
            reconcile(api, a.runtime, state, config)


if __name__ == '__main__':
    try: main()
    except Exception: raise SystemExit('Registration refused; preserve private journal and inspect before retrying.')
