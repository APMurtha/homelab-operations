"""Synthetic pinned-API visibility, detail-404 and durable DELETE regressions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock, MagicMock
from urllib.error import HTTPError
from urllib.parse import urlsplit, parse_qs
from test_candidate import FakeAPI
import api as transport
import register as reg
from files import read_json, write_json


class HiddenAPI(FakeAPI):
    rows = transport.API.rows
    def __init__(self):
        super().__init__(); self.events=[]; self.delete_fault=None; self.detail_fault=None
    def request(self, method, path, body=None):
        self.events.append((method,path))
        parts=urlsplit(path)
        if method=='GET' and parts.path in self.tables:
            rows=copy.deepcopy(self.tables[parts.path])
            if parts.path==reg.CHANNELS and parse_qs(parts.query).get('visibility_filter')!=['all']:
                rows=[r for r in rows if not r.get('hidden_from_output')]
            return rows
        if method=='GET' and path==self.detail_fault:raise transport.Uncertain('synthetic_read_timeout')
        if method=='DELETE' and self.delete_fault:
            fault=self.delete_fault;self.delete_fault=None
            if fault=='before':raise transport.Uncertain('synthetic_before_DELETE')
            if fault=='no_effect':return None
            if fault=='after':
                super().request(method,path,body);raise transport.Uncertain('synthetic_after_DELETE')
        return super().request(method,path,body)


class RollbackTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.state=Path(self.temp.name)/'state';self.runtime=Path(self.temp.name)/'runtime';self.runtime.mkdir()
        self.api=HiddenAPI()
        record={'instance':'a'*32,'endpoint':'http://127.0.0.1:19193/s/'+'a'*32+'/live.m3u8'}
        cfg={'expected_network_access_sha256':reg.digest(self.api.tables['/api/core/settings/'][0]['value']),'jellyfin_peer_ipv4':['172.20.0.4']}
        with patch.object(reg,'current',return_value=record):self.owned=reg.reconcile(self.api,self.runtime,self.state,cfg)
        self.api.events=[];self.api.writes=[]
        self.channel=reg.CHANNELS+str(self.owned['channel']['id'])+'/'
        self.stream=reg.STREAMS+str(self.owned['stream']['id'])+'/'
    def rollback(self):reg.rollback_owned(self.api,self.runtime,self.state)
    def test_hidden_detail_present_collection_absent_and_reference(self):
        self.assertEqual(self.api.request('GET',reg.CHANNELS+'?page=1'),[])
        self.assertEqual(self.api.request('GET',self.channel)['streams'],[self.owned['stream']['id']])
        self.assertEqual(len(self.api.rows(reg.CHANNELS)),1)
        self.rollback();self.assertEqual([x[:2] for x in self.api.writes],[('DELETE',self.channel),('DELETE',self.stream)])
        events=self.api.events;i=events.index(('DELETE',self.channel));j=events.index(('DELETE',self.stream))
        self.assertIn(('GET',self.channel),events[i+1:j]);self.assertEqual(read_json(self.state/'rollback-owned.json')['state'],'complete')
        self.assertFalse((self.state/'owned.json').exists())
    def test_hidden_shared_stream_refused_before_delete(self):
        foreign=copy.deepcopy(self.api.tables[reg.CHANNELS][0]);foreign['id']=77
        self.api.tables[reg.CHANNELS].append(foreign)
        with self.assertRaises(transport.Rejected):self.rollback()
        self.assertFalse(self.api.writes)
    def test_all_channels_query_is_mandatory(self):
        self.api.rows(reg.CHANNELS)
        self.assertIn(('GET',reg.CHANNELS+'?visibility_filter=all&page=1'),self.api.events)
    def test_modified_record_either_kind_refused_before_any_write(self):
        for collection in (reg.CHANNELS,reg.STREAMS):
            old=copy.deepcopy(self.api.tables[collection]);self.api.tables[collection][0]['name']='foreign'
            with self.assertRaises(transport.Rejected):self.rollback()
            self.assertFalse(self.api.writes);self.api.tables[collection]=old
    def test_unknown_record_is_not_adopted(self):
        self.api.tables[reg.CHANNELS][0]['id']=77
        with self.assertRaises(transport.Rejected):self.rollback()
        self.assertFalse(self.api.writes)
    def test_authoritative_missing_channel_permits_stream_cleanup(self):
        self.api.tables[reg.CHANNELS]=[];self.rollback()
        self.assertEqual([x[1] for x in self.api.writes],[self.stream])
    def test_missing_both_is_verified_without_mutation(self):
        self.api.tables[reg.CHANNELS]=[];self.api.tables[reg.STREAMS]=[];self.rollback()
        self.assertFalse(self.api.writes)
    def test_existing_channel_missing_stream_refuses(self):
        self.api.tables[reg.STREAMS]=[]
        with self.assertRaises(transport.Rejected):self.rollback()
        self.assertFalse(self.api.writes)
    def test_uncertain_detail_never_means_absent(self):
        self.api.detail_fault=self.channel
        with self.assertRaises(transport.Uncertain):self.rollback()
        self.assertFalse(self.api.writes)
    def test_delete_timeout_before_effect_never_retries(self):
        self.api.delete_fault='before'
        with self.assertRaises(transport.Uncertain):self.rollback()
        before=list(self.api.events)
        with self.assertRaises(transport.Uncertain):self.rollback()
        self.assertEqual(sum(m=='DELETE' for m,p in before),sum(m=='DELETE' for m,p in self.api.events))
        self.assertTrue((self.state/'owned.json').exists())
    def test_delete_effect_then_timeout_recovers_by_GET_only(self):
        self.api.delete_fault='after'
        with self.assertRaises(transport.Uncertain):self.rollback()
        self.assertEqual(read_json(self.state/'rollback-owned.json')['deletes'],{'channel':'pending'})
        self.rollback()
        self.assertEqual([x[:2] for x in self.api.writes],[('DELETE',self.channel),('DELETE',self.stream)])
    def test_unverified_delete_does_not_delete_stream(self):
        self.api.delete_fault='no_effect'
        with self.assertRaises(transport.Uncertain):self.rollback()
        self.assertTrue(self.api.tables[reg.STREAMS]);self.assertTrue(self.api.tables[reg.CHANNELS])
        with self.assertRaises(transport.Uncertain):self.rollback()
        self.assertEqual(sum(m=='DELETE' for m,p in self.api.events),1)
    def test_pending_registration_and_commit_preserved(self):
        for name in ('journal.json','commit.json'):
            write_json(self.state/name,{'uncertain':True})
            with self.assertRaises(transport.Rejected):self.rollback()
            self.assertFalse(self.api.writes);(self.state/name).unlink()
    def test_receipt_ownership_conflict_refused(self):
        write_json(self.state/'rollback-owned.json',{'owned':{},'state':'intent','deletes':{}})
        with self.assertRaises(transport.Rejected):self.rollback()
        self.assertFalse(self.api.writes)
    def test_completed_receipt_crash_before_ledger_retirement(self):
        self.api.tables[reg.CHANNELS]=[];self.api.tables[reg.STREAMS]=[]
        write_json(self.state/'rollback-owned.json',{'owned':self.owned,'state':'complete','deletes':{'channel':'absent','stream':'absent'}})
        self.rollback();self.assertFalse(self.api.writes);self.assertFalse((self.state/'owned.json').exists())
    def test_truncated_ledger_does_not_authorize_deletion(self):
        write_json(self.state/'owned.json',{'stream':{'id':1},'channel':{'id':1}})
        with self.assertRaises(transport.Rejected):self.rollback()
        self.assertFalse(self.api.writes)
    def test_journal_delete_timeout_before_effect_blocks_retry(self):
        write_json(self.state/'journal.json',{'ops':[{'collection':reg.CHANNELS,'id':self.owned['channel']['id'],'before':None,'after':self.owned['channel']}],'uncertain':False})
        self.api.delete_fault='before'
        with self.assertRaises(transport.Uncertain):reg.Transaction(self.api,self.state/'journal.json').rollback()
        with self.assertRaises(transport.Uncertain):reg.Transaction(self.api,self.state/'journal.json').rollback()
        self.assertEqual(sum(m=='DELETE' for m,p in self.api.events),1)

    def test_invalid_receipt_order_refused(self):
        for state,deletes in [('intent',{'stream':'pending'}),('complete',{})]:
            write_json(self.state/'rollback-owned.json',{'owned':self.owned,'state':state,'deletes':deletes})
            with self.assertRaises(transport.Rejected):self.rollback()
            self.assertFalse(self.api.writes)
    def test_channel_reappearing_blocks_stream_delete(self):
        original=self.api.request
        deleted=[False]
        def request(method,path,body=None):
            if method=='DELETE' and path==self.channel:deleted[0]=True
            if method=='GET' and path==self.channel and deleted[0]:
                return copy.deepcopy(self.owned['channel'])
            return original(method,path,body)
        self.api.request=request
        with self.assertRaises(transport.Uncertain):self.rollback()
        self.assertTrue(self.api.tables[reg.STREAMS])
        self.assertEqual([w[1] for w in self.api.writes],[self.channel])
    def test_malformed_detail_not_treated_as_absent(self):
        original=self.api.request
        self.api.request=lambda method,path,body=None: None if method=='GET' and path==self.channel else original(method,path,body)
        with self.assertRaises(transport.Rejected):self.rollback()
        self.assertFalse(self.api.writes)

    def test_known_journal_id_hidden_rollback_uses_detail(self):
        (self.state/'owned.json').unlink()
        write_json(self.state/'journal.json',{'ops':[{'collection':reg.CHANNELS,'id':self.owned['channel']['id'],'before':None,'after':self.owned['channel']}],'uncertain':False})
        reg.Transaction(self.api,self.state/'journal.json').rollback()
        self.assertEqual(self.api.writes[0][:2],('DELETE',self.channel))
    def test_restart_rebind_uses_hidden_detail_and_all_reference_scan(self):
        cfg={'expected_network_access_sha256':reg.digest(self.api.tables['/api/core/settings/'][0]['value']),'jellyfin_peer_ipv4':['172.20.0.4']}
        with patch.object(reg,'current',return_value={'instance':'b'*32,'endpoint':'http://127.0.0.1:19193/s/'+'b'*32+'/live.m3u8'}):reg.reconcile(self.api,self.runtime,self.state,cfg)
        self.assertEqual(len(self.api.tables[reg.CHANNELS]),1)


class TransportTests(unittest.TestCase):
    def fake(self, code):
        api=object.__new__(transport.API);api.token='synthetic';api.opener=Mock()
        api.opener.open.side_effect=HTTPError('http://localhost',code,'fixture',{},None);return api
    def test_only_detail_GET_404_is_authoritative_absence(self):
        with self.assertRaises(transport.NotFound):self.fake(404).request('GET',reg.CHANNELS+'2/')
        for method,path,code in [('DELETE',reg.CHANNELS+'2/',404),('GET',reg.CHANNELS,404),('GET',reg.CHANNELS+'2/',403),('GET',reg.CHANNELS+'2/',401)]:
            with self.assertRaises(transport.Rejected) as got:self.fake(code).request(method,path)
            self.assertNotIsInstance(got.exception,transport.NotFound)
    def test_server_and_transport_failures_uncertain(self):
        with self.assertRaises(transport.Uncertain):self.fake(503).request('GET',reg.CHANNELS+'2/')
    def test_DELETE_requires_204_and_no_retry(self):
        api=object.__new__(transport.API);api.token='synthetic';api.opener=MagicMock()
        response=api.opener.open.return_value.__enter__.return_value
        response.status=200;response.read.return_value=b''
        with self.assertRaises(transport.Uncertain):api.request('DELETE',reg.CHANNELS+'2/')
        self.assertEqual(api.opener.open.call_count,1)
        response.status=204;self.assertIsNone(api.request('DELETE',reg.CHANNELS+'2/'))

    def test_query_scope_stays_narrow(self):
        for path in [reg.STREAMS+'?visibility_filter=all&page=1',reg.CHANNELS+'?visibility_filter=all&page=1&other=x']:
            with self.assertRaises(transport.Rejected):self.fake(200).request('GET',path)

if __name__=='__main__':unittest.main()
