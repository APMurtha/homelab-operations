"""Synthetic pinned-API simulator. No sockets, HTTP clients, or media access.

This is a testing aid, not evidence that the real server is isolated. State is
private and durable so separate CLI invocations can inspect the same simulation.
"""
import copy
import re
import uuid
from .core import atomic, private_read, Refused
from .native import ACCOUNTS, CHANNELS, STREAMS, GROUPS, SOURCES, EPG, PROFILES


class Synthetic:
    simulation = True
    def __init__(self, catalogue, path=None, snapshot=None):
        self.catalogue, self.path = catalogue, path
        self.calls = []; self.fail = None; self.ticks = 0
        self.data = {p:[] for p in (ACCOUNTS,CHANNELS,STREAMS,GROUPS,SOURCES,EPG,PROFILES)}
        if path and path.exists():
            state = private_read(path)
            if state.get('simulation') is not True: raise Refused('synthetic_state_schema')
            self.data = state['data']; self.ticks = state['ticks']
        elif snapshot:
            for key,path_ in [('accounts',ACCOUNTS),('channels',CHANNELS),('groups',GROUPS),('epg_sources',SOURCES),('epgdata',EPG)]:
                self.data[path_] = copy.deepcopy(snapshot.get(key,[]))
        if not self.data[PROFILES]: self.data[PROFILES] = [{'id':1,'locked':True,'is_active':True,'command':'ffmpeg','parameters':'-i {streamUrl} -c copy -f mpegts pipe:1'}]
        self.jobs = {}; self.signal_jobs = []

    def save(self):
        if self.path: atomic(self.path,{'simulation':True,'data':self.data,'ticks':self.ticks})

    def allocate(self, path, body):
        row = copy.deepcopy(body)
        row['id'] = max([9]+[r['id'] for r in self.data[path]])+1
        self.data[path].append(row)
        return row

    def find(self, path, pk):
        return next((r for r in self.data[path] if r['id'] == pk),None)

    def finish(self, path, row):
        job = self.jobs.get((path,row['id']))
        if not job: return
        job['remaining'] -= 1
        if job['remaining'] > 0: row['status'] = 'fetching'; return
        self.ticks += 1; row['status'] = 'success'; row['updated_at'] = 'synthetic-'+str(self.ticks)
        if path == ACCOUNTS:
            enabled = {r['channel_group'] for r in row['channel_groups'] if r['enabled']}
            groups = {str(r['custom_properties']['xc_id']):r['channel_group'] for r in row['channel_groups']}
            for s in self.catalogue['channels'].values():
                if groups[s['group']] not in enabled: continue
                fields = {'m3u_account':row['id'],'stream_id':s['id'],'name':s['name'],
                    'channel_group':groups[s['group']],'tvg_id':s['epg_id'] or '', 'is_stale':False}
                existing = next((r for r in self.data[STREAMS] if r['m3u_account']==row['id'] and r['stream_id']==s['id']),None)
                if existing: existing.update(fields)
                else: self.allocate(STREAMS,fields)
        else:
            for tvg in self.catalogue['epg_ids']:
                if not any(r['epg_source']==row['id'] and r['tvg_id']==tvg for r in self.data[EPG]):
                    self.allocate(EPG,{'epg_source':row['id'],'tvg_id':tvg,'name':'Synthetic guide'})
        del self.jobs[(path,row['id'])]
        self.save()

    def exchange(self, method, path, body=None):
        self.calls.append((method,path,copy.deepcopy(body)))
        if self.fail: self.fail(method,path,body)
        if method == 'GET':
            for collection in self.data:
                if path.startswith(collection+'?'):
                    rows = self.data[collection]
                    if collection == STREAMS:
                        rows = [r for r in rows if self.find(ACCOUNTS,r['m3u_account']).get('is_active')]
                    return 200, copy.deepcopy(rows)
                match = re.fullmatch(re.escape(collection)+r'([1-9][0-9]*)/',path)
                if match:
                    row = self.find(collection,int(match[1]))
                    if row is None: return 404,{}
                    if collection in (ACCOUNTS,SOURCES): self.finish(collection,row)
                    return 200,copy.deepcopy(row)
        if method == 'POST' and path == ACCOUNTS:
            row = self.allocate(ACCOUNTS,body)
            row['custom_properties'] = {**body['custom_properties'], **{k:body[k] for k in ('enable_vod','auto_enable_new_groups_live','auto_enable_new_groups_vod','auto_enable_new_groups_series')}}
            row['status'] = 'pending_setup'; row['updated_at'] = None
            row['profiles'] = [{'id':row['id']+100,'is_default':True}]
            row['channel_groups'] = []
            # Synchronous group discovery happens EVEN for inactive accounts.
            for g in self.catalogue['groups'].values():
                group = self.allocate(GROUPS,{'name':g['name']})
                row['channel_groups'].append({'channel_group':group['id'],'enabled':False,
                    'auto_channel_sync':False,'auto_sync_channel_start':None,'auto_sync_channel_end':None,
                    'custom_properties':{'xc_id':g['id']}})
            self.save(); return 201,copy.deepcopy(row)
        if method == 'POST' and path == SOURCES:
            row = self.allocate(SOURCES,body); row.update(status='idle',updated_at=None)
            self.save(); return 201,copy.deepcopy(row)
        if method == 'POST' and path == CHANNELS:
            row = self.allocate(CHANNELS,body); row.update(uuid=str(uuid.uuid4()),channel_number=10000+row['id'])
            if row.get('epg_data_id'): self.signal_jobs.append(('parse_programs_for_tvg_id',row['epg_data_id']))
            for account in self.data[ACCOUNTS]:
                if account.get('locked') and account.get('name') == 'Custom':
                    relations = account.setdefault('channel_groups',[])
                    if not any(r['channel_group']==row['channel_group_id'] for r in relations):
                        relations.append({'channel_group':row['channel_group_id'],'enabled':True,'auto_channel_sync':False})
            self.save(); return 201,copy.deepcopy(row)
        if method == 'PATCH':
            m = re.fullmatch(re.escape(ACCOUNTS)+r'([1-9][0-9]*)/group-settings/',path)
            if m:
                self.find(ACCOUNTS,int(m[1]))['channel_groups'] = copy.deepcopy(body['group_settings'])
                self.save(); return 200,{'message':'updated'}
            for collection in (ACCOUNTS,SOURCES):
                m = re.fullmatch(re.escape(collection)+r'([1-9][0-9]*)/',path)
                if m:
                    row = self.find(collection,int(m[1])); row.update(body)
                    if 'is_active' in body: row['status'] = 'idle' if body['is_active'] else 'disabled'
                    self.save(); return 200,copy.deepcopy(row)
        m = re.fullmatch(r'/api/m3u/refresh/([1-9][0-9]*)/',path)
        if method == 'POST' and (m or path == '/api/epg/import/'):
            collection, pk = (ACCOUNTS,int(m[1])) if m else (SOURCES,body['id'])
            row = self.find(collection,pk)
            if not row or not row.get('is_active'): return 400,{}
            row['status'] = 'fetching'; self.jobs[(collection,pk)] = {'remaining':2}
            self.save(); return 202,{'success':True}
        return 405,{}
