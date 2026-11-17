"""Pinned native API algorithm. No live mutation transport is enabled.

Injected transports implement exchange(method, path, body)->(HTTP status, JSON).
Only the synthetic transport shipped here can execute the write workflow. Never
substitute an HTTP client without the separate server-side network/logging review.
"""
import copy
import re
import shlex
import time
import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from .core import (Refused, Store, atomic, private_read, digest, MAX_ROWS,
                   MAX_IMPORT, provider, OWNER)

ACCOUNTS = '/api/m3u/accounts/'
CHANNELS = '/api/channels/channels/'
STREAMS = '/api/channels/streams/'
GROUPS = '/api/channels/groups/'
SOURCES = '/api/epg/sources/'
EPG = '/api/epg/epgdata/'
PROFILES = '/api/core/streamprofiles/'
COLLECTIONS = (ACCOUNTS, CHANNELS, STREAMS, GROUPS, SOURCES, EPG, PROFILES)
NATIVE_OWNER = OWNER + '/native-v1'


def ident(value):
    if type(value) is not int or value <= 0:
        raise Refused('native_positive_ID_required')
    return value


def exact(row, expected):
    return isinstance(row, dict) and all(row.get(k) == v for k, v in expected.items())


class LiveBlocked:
    """No credentials, authentication or network request occurs in native mode."""
    simulation = False
    def exchange(self, *args):
        raise Refused('native_live_execution_blocked_server_network_and_logging_review_required')


class API:
    def __init__(self, transport):
        self.transport = transport

    def call(self, method, path, body=None, statuses=(200,)):
        # Restrict this adapter independently of the injected transport.
        read = method == 'GET' and any(re.fullmatch(re.escape(p) + r'(?:[1-9][0-9]*/|\?(?:visibility_filter=all&)?page=[1-9][0-9]*)', path) for p in COLLECTIONS)
        write = ((method == 'POST' and path in (ACCOUNTS, CHANNELS, SOURCES, '/api/epg/import/'))
                 or (method == 'PATCH' and any(re.fullmatch(re.escape(p) + r'[1-9][0-9]*/', path) for p in (ACCOUNTS, SOURCES)))
                 or (method == 'PATCH' and re.fullmatch(re.escape(ACCOUNTS) + r'[1-9][0-9]*/group-settings/', path))
                 or (method == 'POST' and re.fullmatch(r'/api/m3u/refresh/[1-9][0-9]*/', path)))
        if not (read or write): raise Refused('native_API_scope_refused')
        if method == 'POST' and path == '/api/epg/import/':
            if not isinstance(body,dict) or set(body) != {'id','force'} or body['force'] is not False:
                raise Refused('native_explicit_scoped_EPG_import_required')
            ident(body['id'])
        if write and getattr(self.transport, 'simulation', False) is not True:
            raise Refused('native_live_execution_blocked_server_network_and_logging_review_required')
        try: status, result = self.transport.exchange(method, path, copy.deepcopy(body))
        except Exception:
            # Raw server/HTTP exceptions may contain credentials. Outcome UNKNOWN.
            raise Refused('native_API_outcome_uncertain_no_retry') from None
        if status not in statuses: raise Refused('native_API_status_refused_no_retry')
        return result

    def detail(self, path, pk):
        row = self.call('GET', path + str(ident(pk)) + '/')
        if not isinstance(row, dict) or row.get('id') != pk:
            raise Refused('native_detail_identity_conflict')
        return row

    def rows(self, path):
        if path not in COLLECTIONS: raise Refused('native_collection_scope')
        rows, seen = [], set()
        for page in range(1, 65):
            query = '?visibility_filter=all&page=' if path == CHANNELS else '?page='
            data = self.call('GET', path + query + str(page))
            batch = data if isinstance(data, list) else data.get('results') if isinstance(data, dict) else None
            if not isinstance(batch, list): raise Refused('native_pagination_schema')
            for row in batch:
                pk = ident(row.get('id') if isinstance(row, dict) else None)
                if pk in seen: raise Refused('native_duplicate_ID')
                seen.add(pk)
            rows.extend(batch)
            if len(rows) > MAX_ROWS: raise Refused('native_inventory_limit')
            # Never follow a server-supplied next URL, including credential URLs.
            if isinstance(data, list) or not data.get('next'): return rows
        raise Refused('native_page_limit')


class Ledger:
    """Use inside Store's private directory lock. Every remote intent is durable.

    A pending receipt blocks *all* new writes. Reconciliation only reads; it never
    retries an uncertain mutation, including queue requests or unknown POST IDs.
    """
    def __init__(self, store, key):
        self.store = store
        store.path(key)  # validate key before constructing filenames
        self.path = store.root / ('native-' + key + '.json')
        self.key = key
        self.value = private_read(self.path) if self.path.exists() else None
        if self.value:
            v = self.value
            if (v.get('owner') != NATIVE_OWNER or v.get('key') != key or v.get('schema') != 1
                    or not isinstance(v.get('operations'), list)
                    or digest([v.get('provider', {}).get('server'), v.get('provider', {}).get('username')]) != key):
                raise Refused('native_ownership_conflict')
            if (v.get('simulation') is not True or v.get('phase') not in ('registering','refreshing','registered_inactive')
                    or not isinstance(v.get('resources'),dict) or len(v['operations']) > 2000):
                raise Refused('native_ledger_schema_conflict')
            seen = set()
            fields = {'id','method','path','body','before','expected','collection','state','returned_id'}
            for op in v['operations']:
                if (not isinstance(op,dict) or set(op) != fields or op['id'] in seen
                        or not re.fullmatch('[a-f0-9]{32}',str(op['id']))
                        or op['method'] not in ('POST','PATCH')
                        or op['state'] not in ('intent','acknowledged','verified')
                        or op['collection'] not in (None,ACCOUNTS,SOURCES,CHANNELS)):
                    raise Refused('native_journal_schema_conflict')
                seen.add(op['id'])
                if op['returned_id'] is not None: ident(op['returned_id'])
            for name in ('account','epg_source'):
                if name not in v['resources']: continue
                tag = v['resources'][name].get('tag',{})
                if (tag.get('owner') != NATIVE_OWNER or tag.get('key') != key
                        or not re.fullmatch('[a-f0-9]{32}',str(tag.get('registration','')))):
                    raise Refused('native_ownership_tag_conflict')

    def save(self):
        atomic(self.path, self.value)

    def begin(self, p, selected):
        if self.value: raise Refused('native_provider_already_managed_or_interrupted')
        self.value = {'schema':1, 'owner':NATIVE_OWNER, 'key':self.key,
                      'provider':copy.deepcopy(p), 'selected':copy.deepcopy(selected), 'operations':[], 'resources':{},
                      'phase':'registering', 'activation':'BLOCKED', 'simulation':True}
        self.save()

    def clean(self):
        if any(op['state'] != 'verified' for op in self.value['operations']):
            raise Refused('native_pending_intent_read_only_reconciliation_required')

    def mutate(self, api, method, path, body, expected=None, collection=None, before=None, statuses=(200,)):
        self.clean()
        if len(self.value['operations']) >= 2000: raise Refused('native_journal_limit')
        op = {'id':uuid.uuid4().hex, 'method':method, 'path':path, 'body':body,
              'before':before, 'expected':expected, 'collection':collection,
              'state':'intent', 'returned_id':None}
        self.value['operations'].append(op); self.save()  # before any API mutation
        result = api.call(method, path, body, statuses)
        # Queue acknowledgement is not completion; preserve durable pending state.
        op['state'] = 'acknowledged'
        if collection and isinstance(result, dict): op['returned_id'] = ident(result.get('id'))
        self.save()
        if expected is not None:
            pk = op['returned_id'] if collection else ident(int(path.rstrip('/').split('/')[-1]))
            row = api.detail(collection or path.rsplit(str(pk) + '/', 1)[0], pk)
            if not exact(row, expected): raise Refused('native_write_readback_conflict')
            op['state'] = 'verified'; self.save()
            return row
        return result

    def verify_last(self):
        self.value['operations'][-1]['state'] = 'verified'; self.save()

    def reconcile(self, api):
        """Known-ID creates/PATCH only. Unknown IDs and asynchronous intents stop."""
        pending = [o for o in self.value['operations'] if o['state'] != 'verified']
        if len(pending) != 1: raise Refused('native_no_single_reconcilable_intent')
        op = pending[0]
        if op['expected'] is None or (op['collection'] and not op['returned_id']):
            raise Refused('native_uncertain_create_or_task_requires_review_no_retry')
        pk = op['returned_id'] if op['collection'] else int(op['path'].rstrip('/').split('/')[-1])
        path = op['collection'] or op['path'].rsplit(str(pk) + '/', 1)[0]
        if not exact(api.detail(path, pk), op['expected']): raise Refused('native_reconcile_conflict')
        op['state'] = 'verified'; self.save()
        # Completion of a write does NOT resume an interrupted registration.
        return {'reconciled_intent':op['id'], 'phase':self.value['phase'], 'automatic_resume':False}


def epg_url(p):
    return p['epg_url'] or p['server'] + '/xmltv.php?' + urlencode({'username':p['username'], 'password':p['password']})


class Adapter:
    def __init__(self, api, ledger, pause=time.sleep, polls=30, progress=lambda _:None):
        if type(polls) is not int or not 1 <= polls <= 60: raise Refused('native_poll_bound')
        self.api, self.ledger, self.pause, self.polls, self.progress = api, ledger, pause, polls, progress

    def wait(self, collection, pk, prior):
        for _ in range(self.polls):
            row = self.api.detail(collection, pk)
            if row.get('status') == 'error': raise Refused('native_background_import_failed')
            if row.get('status') == 'success' and row.get('updated_at') and row['updated_at'] != prior:
                self.ledger.verify_last(); return row
            self.pause(1)
        raise Refused('native_import_deadline_no_requeue')

    def patch(self, collection, row, changes):
        # Explicitly changed values only; retain private before-image for review.
        return self.ledger.mutate(self.api, 'PATCH', collection+str(ident(row['id']))+'/', changes,
                                  changes, before={k:row.get(k) for k in changes})

    def register(self, p, selected, profile_id):
        # Profile ID comes from separately reviewed configuration; never infer a
        # native ID from a display label. Caller must supply the locked profile.
        checked = provider(p['name'],p['server'],p['username'],p['password'],p['epg_url'],p['max_streams'])
        if checked != p: raise Refused('native_provider_identity_conflict')
        ident(profile_id)
        profiles = []
        for row in self.api.rows(PROFILES):
            try: args = shlex.split(row.get('parameters',''))
            except ValueError: raise Refused('native_profile_parameters_invalid') from None
            codecs = [args[i+1] for i,x in enumerate(args[:-1]) if x in ('-c','-codec','-c:v','-c:a','-codec:v','-codec:a')]
            if (row.get('command') == 'ffmpeg' and row.get('locked') is True and row.get('is_active') is True
                    and any(args[i:i+2] == ['-c','copy'] for i in range(len(args)))
                    and any(args[i:i+2] == ['-f','mpegts'] for i in range(len(args)))
                    and all(c == 'copy' for c in codecs)):
                profiles.append(row['id'])
        if profiles != [profile_id]: raise Refused('native_unique_locked_streamcopy_profile_required')
        if not selected or len(selected) > MAX_IMPORT or len({r['id'] for r in selected}) != len(selected):
            raise Refused('native_explicit_bounded_selection_required')
        if any(not re.fullmatch('[1-9][0-9]*', str(r['id'])) or not re.fullmatch('[1-9][0-9]*', str(r['group'])) for r in selected):
            raise Refused('native_stable_provider_ID_required')
        names, tvgs = [r['name'] for r in selected], [r['epg_id'] for r in selected if r['epg_id']]
        if len(set(names)) != len(names) or len(set(tvgs)) != len(tvgs): raise Refused('native_selection_ambiguity')
        accounts, baseline = self.api.rows(ACCOUNTS), self.api.rows(CHANNELS)
        if any(r.get('name') == p['name'] or (r.get('server_url') == p['server'] and r.get('username') == p['username']) for r in accounts):
            raise Refused('native_duplicate_provider')
        self.channel_conflicts(selected, baseline)
        if any(r.get('name') == p['name']+' EPG' or r.get('url') == epg_url(p) for r in self.api.rows(SOURCES)):
            raise Refused('native_duplicate_EPG_source')
        baseline_groups = self.api.rows(GROUPS)
        self.ledger.begin(p, selected)
        self.ledger.value['baseline_channels'] = baseline
        self.ledger.value['baseline_accounts'] = accounts
        self.ledger.value['indirect_account_effects'] = []
        self.ledger.value['profile_id'] = profile_id; self.ledger.save()
        tag = {'provider_cli': {'owner':NATIVE_OWNER, 'key':p['key'], 'registration':uuid.uuid4().hex}}
        body = {'name':p['name'], 'account_type':'XC', 'server_url':p['server'], 'username':p['username'],
                'password':p['password'], 'max_streams':p['max_streams'], 'is_active':False,
                'refresh_interval':24, 'cron_expression':'', 'custom_properties':tag,
                'enable_vod':False, 'auto_enable_new_groups_live':False,
                'auto_enable_new_groups_vod':False, 'auto_enable_new_groups_series':False}
        # Write-only creation flags are stored under custom_properties by native
        # serializer; compare persisted fields, never assume response echoes flags.
        expected = {k:v for k,v in body.items() if k not in ('enable_vod','auto_enable_new_groups_live','auto_enable_new_groups_vod','auto_enable_new_groups_series','custom_properties')}
        account = self.ledger.mutate(self.api,'POST',ACCOUNTS,body,expected,ACCOUNTS,before={'existing_ids':[r['id'] for r in accounts]},statuses=(201,))
        aid = account['id']; resources = self.ledger.value['resources']
        resources['account'] = {'id':aid,'tag':tag['provider_cli'],'profiles':account.get('profiles',[])}
        self.ledger.save()
        self.assert_owner(account, resources['account'])
        self.verify_account_flags(account)
        self.progress('Account created; checking native groups (metadata side effects recorded).')
        settings, groups = [], {}
        for rel in account.get('channel_groups', []):
            gid = ident(rel.get('channel_group')); xc = str(rel.get('custom_properties',{}).get('xc_id',''))
            if gid in [r['channel_group'] for r in settings] or xc in groups: raise Refused('native_group_identity_ambiguous')
            groups[xc] = gid
            settings.append({'channel_group':gid, 'enabled':xc in {r['group'] for r in selected}, 'auto_channel_sync':False,
                             'auto_sync_channel_start':None, 'auto_sync_channel_end':None,
                             'custom_properties':rel.get('custom_properties',{})})
        if not {r['group'] for r in selected} <= set(groups): raise Refused('native_selected_group_missing')
        # Settings endpoint is account-scoped. Verify *every* association, so a
        # surprise enabled group/auto-sync cannot be hidden behind selected rows.
        self.ledger.mutate(self.api,'PATCH',ACCOUNTS+str(aid)+'/group-settings/',{'group_settings':settings},before=account.get('channel_groups'))
        self.verify_groups(self.api.detail(ACCOUNTS,aid),settings)
        self.ledger.verify_last()
        resources['groups'] = {'associations':settings, 'global_groups_owned':False,
            'new_global_group_ids':[g['id'] for g in self.api.rows(GROUPS) if g['id'] not in {b['id'] for b in baseline_groups}]}; self.ledger.save()
        account = self.patch(ACCOUNTS,self.api.detail(ACCOUNTS,aid),{'is_active':True})
        self.ledger.mutate(self.api,'POST','/api/m3u/refresh/'+str(aid)+'/',{},before={'updated_at':account.get('updated_at')},statuses=(202,))
        account = self.wait(ACCOUNTS,aid,account.get('updated_at'))
        self.verify_groups(account,settings)
        self.verify_account_flags(account)
        streams = [r for r in self.api.rows(STREAMS) if r.get('m3u_account') == aid]
        resources['discovered_stream_ids'] = [r['id'] for r in streams]; self.ledger.save()
        native = self.resolve_streams(selected,streams,groups)
        self.progress('Selected native stream IDs resolved; importing owned XMLTV source.')
        source_body = {'name':p['name']+' EPG','source_type':'xmltv','url':epg_url(p),
                       'is_active':False,'refresh_interval':24,'cron_expression':'','priority':0,'custom_properties':tag}
        source = self.ledger.mutate(self.api,'POST',SOURCES,source_body,source_body,SOURCES,before={'existing_ids':[r['id'] for r in self.api.rows(SOURCES)]},statuses=(201,))
        resources['epg_source'] = {'id':source['id'],'tag':tag['provider_cli']}; self.ledger.save()
        source = self.patch(SOURCES,source,{'is_active':True})
        self.ledger.mutate(self.api,'POST','/api/epg/import/',{'id':source['id'],'force':False},before={'updated_at':source.get('updated_at')},statuses=(202,))
        self.wait(SOURCES,source['id'],source.get('updated_at'))
        entries = [r for r in self.api.rows(EPG) if r.get('epg_source') == source['id']]
        resources['epg_data_ids'] = [r['id'] for r in entries]; resources['channels'] = []; self.ledger.save()
        mappings = self.resolve_epg(selected,entries)
        self.channel_conflicts(selected,self.api.rows(CHANNELS))
        for row in selected:
            current = self.api.rows(CHANNELS)
            self.channel_conflicts([row],current)
            stream = native[row['id']]
            body = {'name':row['name'],'streams':[stream['id']], 'channel_group_id':groups[row['group']],
                    'tvg_id':row['epg_id'] or '', 'epg_data_id':mappings[row['id']],
                    'stream_profile_id':profile_id,'hidden_from_output':True,'channel_profile_ids':[]}
            expected = {k:v for k,v in body.items() if k != 'channel_profile_ids'}
            channel = self.ledger.mutate(self.api,'POST',CHANNELS,body,expected,CHANNELS,before={'existing_ids':[r['id'] for r in current]},statuses=(201,))
            try: uuid.UUID(channel.get('uuid',''))
            except (ValueError,TypeError,AttributeError): raise Refused('native_channel_UUID_missing_or_invalid') from None
            try: protected_number = Decimal(str(channel.get('channel_number'))) == Decimal(9001)
            except InvalidOperation: protected_number = False
            if channel['id'] == 3 or protected_number:
                raise Refused('native_protected_DW_identity_collision')
            resources['channels'].append({'id':channel['id'],'uuid':channel.get('uuid'),
                'provider_stream_id':row['id'],'stream_id':stream['id'],'expected':expected})
            self.ledger.save()
            # Manual-channel signals may attach the group to the existing
            # locked Custom account and queue programme parsing. These are
            # observed side effects, never ownership of that shared account.
            now = {a['id']:a for a in self.api.rows(ACCOUNTS)}
            effects = [{'account_id':a['id'],'before':a,'after':now.get(a['id']),'owned':False}
                       for a in accounts if a != now.get(a['id'])]
            self.ledger.value['indirect_account_effects'] = effects
            self.ledger.save()
        # Keep metadata draft channels hidden and account/source inactive. The
        # temporary active window above is NOT a safe network isolation boundary.
        self.patch(SOURCES,self.api.detail(SOURCES,source['id']),{'is_active':False})
        self.patch(ACCOUNTS,self.api.detail(ACCOUNTS,aid),{'is_active':False})
        self.verify()
        self.ledger.value['phase'] = 'registered_inactive'; self.ledger.save()
        return self.summary()

    @staticmethod
    def channel_conflicts(selected, current):
        for r in selected:
            if any(c.get('name') == r['name'] or (r['epg_id'] and c.get('tvg_id') == r['epg_id']) for c in current):
                raise Refused('native_existing_channel_conflict_no_overwrite')

    @staticmethod
    def assert_owner(row, owned):
        if row.get('id') != owned['id'] or row.get('custom_properties',{}).get('provider_cli') != owned['tag']:
            raise Refused('native_ownership_tag_conflict')

    @staticmethod
    def verify_account_flags(account):
        props = account.get('custom_properties',{})
        if any(props.get(k) is not False for k in ('enable_vod','auto_enable_new_groups_live','auto_enable_new_groups_vod','auto_enable_new_groups_series')):
            raise Refused('native_automatic_discovery_flags_unsafe')

    @staticmethod
    def verify_groups(account, expected):
        actual = account.get('channel_groups',[])
        fields = ('channel_group','enabled','auto_channel_sync','auto_sync_channel_start','auto_sync_channel_end','custom_properties')
        normalize = lambda rows: sorted([{k:r.get(k) for k in fields} for r in rows],key=lambda r:r['channel_group'])
        if normalize(actual) != normalize(expected): raise Refused('native_group_selection_or_autosync_conflict')

    @staticmethod
    def resolve_streams(selected, streams, groups):
        out = {}
        for row in selected:
            matches = [s for s in streams if str(s.get('stream_id')) == row['id']]
            if len(matches) != 1: raise Refused('native_stream_ID_missing_or_ambiguous')
            s = matches[0]
            if s.get('channel_group') != groups[row['group']] or (s.get('tvg_id') or '') != (row['epg_id'] or '') or s.get('is_stale'):
                raise Refused('native_selected_stream_metadata_drift')
            out[row['id']] = s
        return out

    @staticmethod
    def resolve_epg(selected, entries):
        out = {}
        for row in selected:
            matches = [e for e in entries if row['epg_id'] and e.get('tvg_id') == row['epg_id']]
            if len(matches) > 1: raise Refused('native_EPG_identifier_ambiguous')
            out[row['id']] = matches[0]['id'] if matches else None
        return out

    def verify(self):
        v = self.ledger.value; self.ledger.clean(); r = v['resources']
        account = self.api.detail(ACCOUNTS,r['account']['id']); self.assert_owner(account,r['account'])
        self.verify_groups(account,r['groups']['associations'])
        self.verify_account_flags(account)
        source = self.api.detail(SOURCES,r['epg_source']['id']); self.assert_owner(source,r['epg_source'])
        p = v['provider']
        if (not exact(account,{'name':p['name'],'account_type':'XC','server_url':p['server'],'username':p['username'],
                               'max_streams':p['max_streams'],'refresh_interval':24,'cron_expression':''})
                or not exact(source,{'name':p['name']+' EPG','source_type':'xmltv','url':epg_url(p),
                                    'refresh_interval':24,'cron_expression':'','priority':0})):
            raise Refused('native_owned_account_or_source_configuration_drift')
        if account.get('is_active') is not False or source.get('is_active') is not False:
            raise Refused('native_final_inactive_state_required')
        for c in r['channels']:
            row = self.api.detail(CHANNELS,c['id'])
            if not exact(row,c['expected']) or row.get('uuid') != c['uuid']: raise Refused('native_owned_channel_drift')
        current = self.api.rows(CHANNELS); owned = {c['id'] for c in r['channels']}
        for other in current:
            if other['id'] not in owned and (set(other.get('streams',[])) & set(r['discovered_stream_ids'])
                    or other.get('epg_data_id') in r['epg_data_ids']):
                raise Refused('native_shared_stream_or_EPG_resource_conflict')
        order = lambda rows: sorted(rows,key=lambda row:row['id'])
        if order([r for r in current if r['id'] not in owned]) != order(v['baseline_channels']):
            raise Refused('native_unrelated_or_automatic_channel_change')
        return self.summary()

    def refresh(self):
        """Refresh only previously owned metadata; changed IDs/mappings stop.

        No new channels and no remapping on refresh. Queued work is never retried.
        """
        self.verify()
        v = self.ledger.value; r = v['resources']
        if v['phase'] != 'registered_inactive': raise Refused('native_incomplete_registration_requires_review')
        v['phase'] = 'refreshing'; self.ledger.save()
        account = self.patch(ACCOUNTS,self.api.detail(ACCOUNTS,r['account']['id']),{'is_active':True})
        self.ledger.mutate(self.api,'POST','/api/m3u/refresh/'+str(account['id'])+'/',{},before={'updated_at':account.get('updated_at')},statuses=(202,))
        account = self.wait(ACCOUNTS,account['id'],account.get('updated_at'))
        self.verify_groups(account,r['groups']['associations'])
        self.verify_account_flags(account)
        groups = {str(g['custom_properties']['xc_id']):g['channel_group'] for g in account['channel_groups']}
        streams = [s for s in self.api.rows(STREAMS) if s.get('m3u_account') == account['id']]
        resolved = self.resolve_streams(v['selected'],streams,groups)
        for channel in r['channels']:
            if resolved[channel['provider_stream_id']]['id'] != channel['stream_id']:
                raise Refused('native_refresh_stream_identity_changed_no_rebind')
        source = self.patch(SOURCES,self.api.detail(SOURCES,r['epg_source']['id']),{'is_active':True})
        self.ledger.mutate(self.api,'POST','/api/epg/import/',{'id':source['id'],'force':False},before={'updated_at':source.get('updated_at')},statuses=(202,))
        self.wait(SOURCES,source['id'],source.get('updated_at'))
        entries = [e for e in self.api.rows(EPG) if e.get('epg_source') == source['id']]
        mapping = self.resolve_epg(v['selected'],entries)
        if any(mapping[c['provider_stream_id']] != c['expected']['epg_data_id'] for c in r['channels']):
            raise Refused('native_refresh_EPG_mapping_changed_no_overwrite')
        r['discovered_stream_ids'] = [s['id'] for s in streams]
        r['epg_data_ids'] = [e['id'] for e in entries]; self.ledger.save()
        self.patch(SOURCES,self.api.detail(SOURCES,source['id']),{'is_active':False})
        self.patch(ACCOUNTS,self.api.detail(ACCOUNTS,account['id']),{'is_active':False})
        self.verify(); v['phase'] = 'registered_inactive'; self.ledger.save()
        return self.summary()

    def summary(self):
        v = self.ledger.value; r = v['resources']
        return {'key':v['key'],'simulation':v['simulation'],'phase':v['phase'],
                'account_id':r.get('account',{}).get('id'),
                'channel_ids':[r['id'] for r in r.get('channels',[])],
                'epg_source_id':r.get('epg_source',{}).get('id'),
                'unmatched_channel_ids':[r['id'] for r in r.get('channels',[]) if r['expected']['epg_data_id'] is None],
                'activation':'BLOCKED; no relay, Jellyfin or media activation',
                'removal':'DISABLED; native account cascade/shared relationships require further review'}

    def remove(self):
        raise Refused('native_removal_disabled_cascade_and_shared_resource_safety_unproven')
