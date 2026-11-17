"""Offline native contract tests. All remote IDs and credentials are synthetic."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dispatcharr_provider import core as c, cli
from dispatcharr_provider.native import *
from dispatcharr_provider.synthetic import Synthetic

RAW = {'groups':[{'category_id':'1','category_name':'Synthetic News'}, {'category_id':'2','category_name':'Synthetic Arts'}],
       'channels':[{'stream_id':101,'category_id':'1','name':'Synthetic One','epg_channel_id':'one'},
                   {'stream_id':102,'category_id':'1','name':'Unselected','epg_channel_id':'two'},
                   {'stream_id':203,'category_id':'2','name':'Other group','epg_channel_id':'three'}],
       'epg_ids':['one','two']}
DW = {'id':3,'name':'DW English','streams':[3],'channel_number':9001,'tvg_id':'dw','uuid':'synthetic-dw'}


class Native(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name)/'state').__enter__(); self.addCleanup(self.store.__exit__)
        self.p = c.provider('Synthetic','https://provider.example.invalid','synthetic-user','synthetic-secret',None,1)
        self.cat = c.catalogue(copy.deepcopy(RAW)); self.selected = [self.cat['channels']['101']]
        self.transport = Synthetic(self.cat,snapshot={'channels':[DW]})
        self.api = API(self.transport); self.ledger = Ledger(self.store,self.p['key'])
        self.adapter = Adapter(self.api,self.ledger,pause=lambda _:None,polls=3)

    def register(self): return self.adapter.register(self.p,self.selected,1)
    def assertRefused(self, func, code=None):
        with self.assertRaises(c.Refused) as caught: func()
        if code: self.assertIn(code,str(caught.exception))

    def test_full_native_registration_uses_actual_IDs_and_readbacks(self):
        result = self.register(); self.assertEqual(result['phase'],'registered_inactive')
        r = self.ledger.value['resources']; channel = self.api.detail(CHANNELS,r['channels'][0]['id'])
        self.assertNotEqual(channel['streams'],[101]); self.assertNotEqual(channel['epg_data_id'],'one')
        self.assertEqual(channel['streams'],[r['channels'][0]['stream_id']])
        self.assertEqual(channel['epg_data_id'],r['epg_data_ids'][0]); self.assertTrue(channel['hidden_from_output'])
        self.assertEqual(channel['channel_profile_ids'],[])
        self.assertEqual(self.api.detail(ACCOUNTS,r['account']['id'])['is_active'],False)
        self.assertEqual(self.api.detail(SOURCES,r['epg_source']['id'])['is_active'],False)
        self.assertTrue(all(o['state']=='verified' for o in self.ledger.value['operations']))

    def test_account_creation_inactive_still_discovers_groups(self):
        self.register(); op = self.ledger.value['operations'][0]
        self.assertFalse(op['body']['is_active'])
        self.assertEqual(len(self.transport.data[GROUPS]),2)
        self.assertEqual(len(self.ledger.value['resources']['account']['profiles']),1)

    def test_only_selected_channels_imported_but_category_metadata_is_broader(self):
        self.register(); resources = self.ledger.value['resources']
        self.assertEqual(len(resources['channels']),1)
        self.assertEqual(len(resources['discovered_stream_ids']),2)
        self.assertEqual(len(self.transport.data[CHANNELS]),2) # preserved DW plus one
        settings = resources['groups']['associations']
        self.assertEqual([r['enabled'] for r in settings],[True,False])
        self.assertTrue(all(not r['auto_channel_sync'] for r in settings))
        self.assertFalse(resources['groups']['global_groups_owned'])

    def test_DW_and_unrelated_records_preserved_exactly(self):
        self.register(); self.adapter.refresh()
        self.assertEqual(self.api.detail(CHANNELS,3),DW)
        writes = [(method,path) for method,path,_ in self.transport.calls if method!='GET']
        self.assertFalse(any(path==CHANNELS+'3/' for _,path in writes))
        self.assertFalse(any('jellyfin' in path or 'settings' in path and 'group-settings' not in path for _,path in writes))

    def test_refresh_does_not_create_or_remap_channels(self):
        self.register(); before = copy.deepcopy(self.transport.data[CHANNELS])
        self.adapter.refresh(); self.assertEqual(self.transport.data[CHANNELS],before)
        self.assertEqual(sum(m=='POST' and p==CHANNELS for m,p,_ in self.transport.calls),1)

    def test_separate_XMLTV_source_not_provider_default(self):
        self.p['epg_url']='https://guide.example.invalid/list.xml?token=synthetic'
        self.register(); self.assertEqual(self.transport.data[SOURCES][0]['url'],self.p['epg_url'])

    def test_provider_XMLTV_is_private_URL_not_media(self):
        self.register(); source = self.transport.data[SOURCES][0]
        self.assertIn('/xmltv.php?',source['url']); self.assertNotIn('/live/',source['url'])

    def test_missing_EPG_is_explicitly_unmapped(self):
        self.cat['epg_ids']=[]; result=self.register()
        self.assertEqual(len(result['unmatched_channel_ids']),1)
        self.assertIsNone(self.transport.data[CHANNELS][-1]['epg_data_id'])

    def test_duplicate_EPG_ID_in_owned_source_refused(self):
        def duplicate(path,row):
            original(path,row)
            if path==SOURCES and row['status']=='success' and len(self.transport.data[EPG])==2:
                self.transport.allocate(EPG,{'epg_source':row['id'],'tvg_id':'one'})
        original=self.transport.finish; self.transport.finish=duplicate
        self.assertRefused(self.register,'EPG_identifier_ambiguous')
        self.assertEqual(self.transport.data[CHANNELS],[DW])

    def test_EPG_foreign_source_never_used(self):
        self.cat['epg_ids']=[]
        self.transport.data[EPG]=[{'id':7,'epg_source':999,'tvg_id':'one'}]
        self.register(); self.assertIsNone(self.transport.data[CHANNELS][-1]['epg_data_id'])

    def test_existing_provider_identity_conflict_before_writes(self):
        self.transport.data[ACCOUNTS]=[{'id':4,'server_url':self.p['server'],'username':self.p['username']}]
        self.assertRefused(self.register,'duplicate_provider'); self.assertFalse(self.ledger.path.exists())

    def test_existing_provider_name_conflict_before_writes(self):
        self.transport.data[ACCOUNTS]=[{'id':4,'name':self.p['name']}]
        self.assertRefused(self.register,'duplicate_provider')

    def test_existing_channel_name_conflict(self):
        self.selected[0]['name']='DW English'; self.assertRefused(self.register,'existing_channel_conflict')
        self.assertFalse(self.ledger.path.exists())

    def test_existing_channel_tvg_conflict(self):
        self.selected[0]['epg_id']='dw'; self.assertRefused(self.register,'existing_channel_conflict')

    def test_duplicate_EPG_source_no_adoption(self):
        self.transport.data[SOURCES]=[{'id':5,'url':epg_url(self.p)}]
        self.assertRefused(self.register,'duplicate_EPG_source')

    def test_empty_selection_refused(self):
        self.selected=[]; self.assertRefused(self.register,'bounded_selection')

    def test_oversized_selection_refused(self):
        self.selected=self.selected*201; self.assertRefused(self.register,'bounded_selection')

    def test_duplicate_provider_stream_selection_refused(self):
        self.selected=self.selected*2; self.assertRefused(self.register,'bounded_selection')

    def test_non_numeric_stable_ID_refused(self):
        self.selected[0]['id']='not-an-ID'; self.assertRefused(self.register,'stable_provider_ID')

    def test_noncopy_or_unlocked_profile_refused_before_mutation(self):
        for field,value in [('locked',False),('parameters','-c libx264 -f mpegts'),('is_active',False)]:
            old=self.transport.data[PROFILES][0][field]; self.transport.data[PROFILES][0][field]=value
            self.assertRefused(self.register,'streamcopy_profile'); self.transport.data[PROFILES][0][field]=old
        self.assertFalse(self.ledger.path.exists())

    def test_no_profile_ID_guess_or_duplicate_profile(self):
        self.transport.data[PROFILES].append({**self.transport.data[PROFILES][0],'id':2})
        self.assertRefused(self.register,'streamcopy_profile')

    def test_missing_selected_native_stream_refused(self):
        self.cat['channels'].pop('101'); self.assertRefused(self.register,'stream_ID_missing')

    def test_duplicate_native_stream_ID_refused(self):
        original=self.transport.finish
        def duplicate(path,row):
            original(path,row)
            if path==ACCOUNTS and row['status']=='success' and len(self.transport.data[STREAMS])==2:
                self.transport.allocate(STREAMS,{**self.transport.data[STREAMS][0]})
        self.transport.finish=duplicate
        # allocate must use a distinct native primary key but same provider ID.
        def allocate(path,body):
            body={k:v for k,v in body.items() if k!='id'}
            return original_allocate(path,body)
        original_allocate=self.transport.allocate; self.transport.allocate=allocate
        self.assertRefused(self.register,'stream_ID_missing_or_ambiguous')

    def test_wrong_native_group_refused(self):
        original=self.transport.finish
        def wrong(path,row):
            original(path,row)
            if path==ACCOUNTS and row['status']=='success':
                self.transport.data[STREAMS][0]['channel_group']=999
        self.transport.finish=wrong; self.assertRefused(self.register,'metadata_drift')

    def test_new_automatic_channel_side_effect_is_detected(self):
        original=self.transport.finish
        def extra(path,row):
            original(path,row)
            if path==ACCOUNTS and row['status']=='success' and len(self.transport.data[CHANNELS])==1:
                self.transport.allocate(CHANNELS,{'name':'Unexpected auto channel'})
        self.transport.finish=extra; self.assertRefused(self.register,'automatic_channel_change')

    def test_refresh_changed_EPG_ID_refuses_overwrite(self):
        self.register(); original=copy.deepcopy(self.transport.data[CHANNELS]); self.transport.data[EPG][0]['id']+=100
        self.assertRefused(self.adapter.refresh,'mapping_changed_no_overwrite')
        self.assertEqual(self.transport.data[CHANNELS],original)

    def test_provider_refresh_changed_stable_guide_metadata_is_not_rebound(self):
        self.register(); before=copy.deepcopy(self.transport.data[CHANNELS])
        self.cat['channels']['101']['epg_id']='changed.stable.id'
        self.assertRefused(self.adapter.refresh,'metadata_drift')
        self.assertEqual(self.transport.data[CHANNELS],before)
        self.assertEqual(self.ledger.value['phase'],'refreshing')

    def test_owned_channel_modification_blocks_refresh(self):
        self.register(); self.transport.data[CHANNELS][-1]['name']='Modified'
        calls=len(self.transport.calls); self.assertRefused(self.adapter.refresh,'owned_channel_drift')
        self.assertTrue(all(m=='GET' for m,_,_ in self.transport.calls[calls:]))

    def test_ownership_tag_modification_blocks_refresh(self):
        self.register(); self.transport.data[ACCOUNTS][0]['custom_properties']['provider_cli']['key']='foreign'
        self.assertRefused(self.adapter.refresh,'ownership_tag_conflict')

    def test_WAL_exists_before_every_mutation(self):
        def check(method,path,body):
            if method!='GET':
                value=c.private_read(self.ledger.path); op=value['operations'][-1]
                self.assertEqual(op['state'],'intent'); self.assertEqual(op['body'],body)
                self.assertEqual(op['method'],method); self.assertEqual(op['path'],path)
        self.transport.fail=check; self.register()

    def test_timeout_leaves_pending_and_does_not_retry_POST(self):
        def fail(method,path,body):
            if method=='POST': raise TimeoutError('secret provider URL')
        self.transport.fail=fail
        self.assertRefused(self.register,'uncertain_no_retry')
        self.assertEqual(self.ledger.value['operations'][-1]['state'],'intent')
        self.assertRefused(self.register,'already_managed')
        self.assertEqual(sum(m=='POST' for m,_,_ in self.transport.calls),1)

    def test_POST_committed_response_lost_requires_review(self):
        exchange=self.transport.exchange
        def lost(method,path,body=None):
            status,data=exchange(method,path,body)
            if method=='POST' and path==ACCOUNTS: raise TimeoutError('synthetic-secret')
            return status,data
        self.transport.exchange=lost; self.assertRefused(self.register,'uncertain_no_retry')
        self.assertEqual(len(self.transport.data[ACCOUNTS]),1)
        self.assertRefused(lambda:self.ledger.reconcile(self.api),'requires_review_no_retry')

    def test_known_ID_reconciliation_reads_only_no_resume(self):
        exchange=self.transport.exchange; once=[False]
        def fail(method,path,body=None):
            if method=='GET' and path==ACCOUNTS+'10/' and not once[0]:
                once[0]=True; raise TimeoutError()
            return exchange(method,path,body)
        self.transport.exchange=fail; self.assertRefused(self.register)
        self.assertEqual(self.ledger.value['operations'][0]['returned_id'],10)
        before=len(self.transport.calls); result=self.ledger.reconcile(self.api)
        self.assertFalse(result['automatic_resume']); self.assertTrue(all(m=='GET' for m,_,_ in self.transport.calls[before:]))
        self.assertEqual(self.ledger.value['phase'],'registering')

    def test_pending_task_deadline_never_requeues(self):
        self.transport.finish=lambda path,row:None
        self.assertRefused(self.register,'deadline_no_requeue')
        self.assertEqual(sum(m=='POST' and '/refresh/' in p for m,p,_ in self.transport.calls),1)
        self.assertRefused(lambda:self.ledger.reconcile(self.api),'requires_review_no_retry')

    def test_background_error_stops_with_receipt(self):
        self.transport.finish=lambda path,row:row.update(status='error') if (path,row['id']) in self.transport.jobs else None
        self.assertRefused(self.register,'background_import_failed')
        self.assertEqual(self.ledger.value['operations'][-1]['state'],'acknowledged')

    def test_stale_success_does_not_satisfy_new_refresh(self):
        self.register(); self.transport.finish=lambda path,row:row.update(status='success')
        self.assertRefused(self.adapter.refresh,'deadline_no_requeue')

    def test_native_delete_always_disabled_even_owned(self):
        self.register(); before=copy.deepcopy(self.transport.data)
        self.assertRefused(self.adapter.remove,'removal_disabled'); self.assertEqual(before,self.transport.data)
        self.assertRefused(lambda:self.api.call('DELETE',ACCOUNTS+'10/'),'scope_refused')

    def test_native_live_transport_does_not_send_any_write(self):
        transport=LiveBlocked()
        with patch.object(transport,'exchange') as send:
            self.assertRefused(lambda:API(transport).call('POST',ACCOUNTS,{}),'live_execution_blocked')
            send.assert_not_called()

    def test_API_errors_are_fixed_safe_codes(self):
        for error in [TimeoutError('synthetic-secret'),PermissionError('https://secret.invalid/?token=secret')]:
            self.transport.fail=lambda *_,error=error:(_ for _ in ()).throw(error)
            with self.assertRaises(c.Refused) as caught:self.api.rows(ACCOUNTS)
            self.assertNotIn('secret',str(caught.exception))

    def test_auth_failure_does_not_echo_response_body(self):
        self.transport.exchange=lambda *args:(401,{'password':'synthetic-secret','error':'unsafe URL'})
        self.assertRefused(lambda:self.api.rows(ACCOUNTS),'status_refused')

    def test_page_next_external_URL_never_followed(self):
        paths=[]
        def pages(method,path,body):
            paths.append(path)
            return 200,{'results':[{'id':len(paths)}], 'next':'https://foreign.invalid/secret' if len(paths)<2 else None}
        self.transport.exchange=pages
        self.assertEqual(len(self.api.rows(ACCOUNTS)),2)
        self.assertEqual(paths,[ACCOUNTS+'?page=1',ACCOUNTS+'?page=2'])

    def test_hidden_inventory_and_duplicate_ID_detection(self):
        self.api.rows(CHANNELS)
        self.assertIn('visibility_filter=all',self.transport.calls[-1][1])
        self.transport.exchange=lambda *_:(200,{'results':[{'id':1}],'next':'anything'})
        self.assertRefused(lambda:self.api.rows(CHANNELS),'duplicate_ID')

    def test_pagination_bound_and_invalid_IDs(self):
        count=[0]
        def endless(*_):
            count[0]+=1; return 200,{'results':[{'id':count[0]}],'next':'anything'}
        self.transport.exchange=endless; self.assertRefused(lambda:self.api.rows(ACCOUNTS),'page_limit')
        for pk in (True,0,'7',-1):
            self.assertRefused(lambda pk=pk:self.api.detail(ACCOUNTS,pk),'positive_ID')

    def test_private_ledger_and_before_images(self):
        self.register(); self.assertEqual(self.ledger.path.stat().st_mode & 0o777,0o600)
        loaded=Ledger(self.store,self.p['key']); self.assertEqual(loaded.value,self.ledger.value)
        patches=[o for o in loaded.value['operations'] if o['method']=='PATCH' and o['path'].endswith('/10/')]
        self.assertTrue(all(o['before'] is not None for o in patches))

    def test_no_mutating_out_of_scope_endpoint_or_global_refresh(self):
        for method,path in [('POST','/api/m3u/refresh/'),('PATCH',CHANNELS+'3/'),('POST',STREAMS),('POST','/api/epg/sources/3/import/')]:
            self.assertRefused(lambda:self.api.call(method,path,{}),'scope_refused')

    def test_incomplete_registration_cannot_be_restarted(self):
        self.register(); self.ledger.value['phase']='registering'; self.ledger.save()
        self.assertRefused(self.adapter.refresh,'incomplete_registration')

    def test_poll_bound_is_not_unbounded_retry(self):
        for polls in (0,61,True): self.assertRefused(lambda:Adapter(self.api,self.ledger,polls=polls),'poll_bound')

    def test_hidden_channel_sharing_owned_stream_blocks_refresh(self):
        self.register(); stream=self.ledger.value['resources']['channels'][0]['stream_id']
        self.transport.allocate(CHANNELS,{'name':'Hidden foreign','streams':[stream],'hidden_from_output':True})
        self.assertRefused(self.adapter.refresh,'shared_stream_or_EPG')

    def test_shared_EPG_data_blocks_refresh(self):
        self.register(); entry=self.ledger.value['resources']['epg_data_ids'][0]
        self.transport.allocate(CHANNELS,{'name':'Foreign guide consumer','streams':[],'epg_data_id':entry})
        self.assertRefused(self.adapter.refresh,'shared_stream_or_EPG')

    def test_manual_channel_signal_effects_are_recorded_not_adopted(self):
        self.transport.data[ACCOUNTS]=[{'id':4,'name':'Custom','locked':True,'channel_groups':[]}]
        self.register(); effects=self.ledger.value['indirect_account_effects']
        self.assertEqual(effects[0]['account_id'],4); self.assertFalse(effects[0]['owned'])
        self.assertEqual(effects[0]['before']['channel_groups'],[])
        self.assertEqual(len(effects[0]['after']['channel_groups']),1)
        self.assertEqual(self.transport.signal_jobs[0][0],'parse_programs_for_tvg_id')

    def test_native_selection_flags_readback_must_be_false(self):
        original=self.transport.exchange
        def unsafe(method,path,body=None):
            status,row=original(method,path,body)
            if method=='GET' and path==ACCOUNTS+'10/':
                row['custom_properties']['auto_enable_new_groups_live']=True
            return status,row
        self.transport.exchange=unsafe; self.assertRefused(self.register,'discovery_flags_unsafe')
        self.assertFalse(any('/refresh/' in p for _,p,_ in self.transport.calls))

    def test_foreign_native_ID_response_refused(self):
        self.transport.exchange=lambda *_:(200,{'id':99})
        self.assertRefused(lambda:self.api.detail(ACCOUNTS,10),'detail_identity_conflict')

    def test_modified_source_URL_blocks_refresh(self):
        self.register(); self.transport.data[SOURCES][0]['url']='https://foreign.invalid/guide.xml'
        self.assertRefused(self.adapter.refresh,'configuration_drift')

    def test_ledger_owner_tampering_refused(self):
        self.register(); self.ledger.value['owner']='foreign'; self.ledger.save()
        self.assertRefused(lambda:Ledger(self.store,self.p['key']),'ownership_conflict')

    def test_second_registration_cannot_overwrite_ledger(self):
        self.register(); before=self.ledger.path.read_bytes()
        self.assertRefused(self.register)
        self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_failed_WAL_persistence_prevents_API_write(self):
        with patch('dispatcharr_provider.native.atomic',side_effect=OSError('synthetic disk full')):
            with self.assertRaises(OSError): self.register()
        self.assertFalse(any(m!='GET' for m,_,_ in self.transport.calls))

    def test_global_EPG_import_body_is_refused_before_transport(self):
        for body in ({}, {'id':1}, {'id':None,'force':False}, {'id':1,'force':True}):
            self.assertRefused(lambda:self.api.call('POST','/api/epg/import/',body,statuses=(202,)))
        self.assertEqual(self.transport.calls,[])

    def test_all_EPGLess_channels_not_mapped_by_name(self):
        self.selected[0]['epg_id']=None
        self.register(); self.assertIsNone(self.transport.data[CHANNELS][-1]['epg_data_id'])


class NativeCLI(unittest.TestCase):
    def test_live_mode_refuses_before_input_state_or_network(self):
        with tempfile.TemporaryDirectory() as tmp,patch('builtins.input') as prompt,contextlib.redirect_stderr(io.StringIO()) as err:
            state=Path(tmp)/'absent'
            code=cli.main(['--state-dir',str(state),'add','--native','--fixture','unused','--apply'])
            self.assertEqual(code,2); prompt.assert_not_called(); self.assertFalse(state.exists())
            self.assertIn('native_live_execution_blocked',err.getvalue())

    def test_simulation_requires_explicit_native_mode(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['list','--simulate-native']),2)

    def test_dry_run_does_not_save_or_claim_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture=Path(tmp)/'fixture.json';fixture.write_text(json.dumps(RAW)); out=io.StringIO()
            with patch('builtins.input',side_effect=['Synthetic','https://provider.example.invalid','synthetic-user','1','1','101']),patch('dispatcharr_provider.cli.hidden',side_effect=['synthetic-secret','']),contextlib.redirect_stdout(out):
                code=cli.main(['--state-dir',str(Path(tmp)/'state'),'add','--native','--simulate-native','--fixture',str(fixture)])
            self.assertEqual(code,0); self.assertFalse((Path(tmp)/'state').exists())
            self.assertNotIn('synthetic-secret',out.getvalue()); self.assertNotIn('synthetic-user',out.getvalue())
            self.assertIn('dry_run',out.getvalue())

    def test_confirmed_simulation_register_list_refresh_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture=Path(tmp)/'fixture.json';fixture.write_text(json.dumps(RAW)); state=Path(tmp)/'state'
            p=c.provider('Synthetic','https://provider.example.invalid','synthetic-user','synthetic-secret',None,1)
            base=['--state-dir',str(state)]; args=['--native','--simulate-native','--fixture',str(fixture),'--apply']
            with patch('builtins.input',side_effect=['Synthetic',p['server'],p['username'],'1','1','101','SIMULATE ADD '+p['key'][:12]]),patch('dispatcharr_provider.cli.hidden',side_effect=[p['password'],'']),contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(cli.main(base+['add']+args),0)
            self.assertIn('registered_inactive',out.getvalue()); self.assertNotIn(p['password'],out.getvalue())
            with patch('builtins.input',return_value='SIMULATE REFRESH '+p['key'][:12]),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(base+['refresh',p['key']]+args),0)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(cli.main(base+['list','--native']),0)
            self.assertIn('registered_inactive',out.getvalue()); self.assertNotIn('password',out.getvalue())

if __name__=='__main__':unittest.main()
