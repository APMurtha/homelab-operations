import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import ssl
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid
import xml.etree.ElementTree as ET
import datetime as dt

HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import hls_relay as relay
import health
import register as reg
from api import Rejected, Uncertain, API, NotFound
from files import read_json, write_json
from rate_budget import RollingBudget
from exports import documents, publish
import jellyfin
import verify
import lifecycle

SOURCE='https://'+relay.HOST+'/synthetic/live.m3u8'
PLAY=b'#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXT-X-MEDIA-SEQUENCE:1\n#EXTINF:6,\npart.ts\n'

class BudgetTests(unittest.TestCase):
    def test_boundary_exhaustion_and_recovery(self):
        now=[0];b=RollingBudget(lambda:now[0])
        for _ in range(120):b.take()
        with self.assertRaises(ValueError):b.take()
        now[0]=59.999
        with self.assertRaises(ValueError):b.take()
        now[0]=60;b.take();self.assertEqual(len(b.events),1)
    def test_no_lifetime_exhaustion_and_bounded_storage(self):
        now=[0];b=RollingBudget(lambda:now[0])
        for _ in range(10000):
            b.take();now[0]+=.6;self.assertLessEqual(len(b.events),120)
    def test_concurrent_budget(self):
        import concurrent.futures
        b=RollingBudget(lambda:0)
        def take(_):
            try:b.take();return 1
            except ValueError:return 0
        with concurrent.futures.ThreadPoolExecutor(16) as pool:self.assertEqual(sum(pool.map(take,range(200))),120)

class RelayTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.ready=self.root/'ready';self.ready.write_text('approved')
        self.guard_patch=patch.object(relay,'Readiness',return_value=__import__('unittest.mock',fromlist=['Mock']).Mock(expected={'generation':'a'*64}));self.guard_patch.start();self.addCleanup(self.guard_patch.stop)
        def checked():
            if self.ready.read_text()!='approved':raise ValueError('fixture_guard_invalid')
        relay.Readiness.return_value.check.side_effect=checked
        self.r=relay.Relay({'source':SOURCE,'guard_status_dir':str(self.ready.parent),'ready_hash':'approved'})
    def tearDown(self):self.r.close();self.temp.cleanup()
    def test_destination_matrix(self):
        for url in ['http://'+relay.HOST+'/synthetic/a.ts','https://127.0.0.1/a.ts','https://other.invalid/a.ts',
                    'https://u:p@'+relay.HOST+'/synthetic/a.ts','https://'+relay.HOST+':443/synthetic/a.ts',
                    SOURCE+'?token=x','https://'+relay.HOST+'/synthetic/../a.ts',
                    'https://'+relay.HOST+'/synthetic/%2e/a.ts','https://'+relay.HOST+'/other/a.ts',
                    'file:///etc/passwd','https://'+relay.HOST+'/synthetic/a.mp4']:
            with self.subTest(url=url),self.assertRaises(relay.SecurityRejected):self.r.scope(url)
    def test_forbidden_HLS_tags(self):
        for tag in [b'#EXT-X-KEY:METHOD=AES-128,URI="key"',b'#EXT-X-MAP:URI="map"',b'#EXT-X-STREAM-INF:BANDWIDTH=1',
                    b'#EXT-X-MEDIA:URI="other"',b'#EXT-X-PART:URI="part"',b'#EXT-X-UNKNOWN:VALUE=1']:
            with self.subTest(tag=tag),self.assertRaises(relay.SecurityRejected):self.r.rewrite(PLAY+tag+b'\n')
    def test_opaque_resources_and_bounded_map(self):
        out=self.r.rewrite(PLAY)
        self.assertNotIn(relay.HOST.encode(),out);self.assertIn(self.r.session.encode(),out)
        for i in range(4200):self.r.rewrite(PLAY.replace(b'part.ts',str(i).encode()+b'.ts'))
        self.assertEqual(len(self.r.resources),4096);self.assertLessEqual(len(self.r.manifest_telemetry.links),4096)
    def test_fresh_identity_and_stale_path(self):
        other=relay.Relay({'source':SOURCE,'guard_status_dir':str(self.ready.parent),'ready_hash':'approved'})
        try:
            self.assertNotEqual(other.session,self.r.session)
            with self.assertRaises(relay.SecurityRejected):other.resource('/s/'+self.r.session+'/live.m3u8')
        finally:other.close()
    def test_guard_loss_and_latch(self):
        self.ready.unlink()
        with self.assertRaises(relay.SecurityRejected):self.r.check()
        self.ready.write_text('approved');self.r.fatal='security_rejection'
        with self.assertRaises(relay.SecurityRejected):self.r.check()
    def test_insecure_TLS_context_refused(self):
        with self.assertRaises(relay.SecurityRejected):
            relay.Relay({'source':SOURCE,'guard_status_dir':str(self.ready.parent),'ready_hash':'approved'},context=ssl._create_unverified_context())
    def test_bad_segments_and_sizes(self):
        for data in [b'',b'bad'*188,b'G'+bytes(187)]:
            with self.assertRaises(relay.SecurityRejected):self.r.validate_segment(data)
        with self.assertRaises(relay.SecurityRejected):self.r.rewrite(b'x'*(relay.MAX_MANIFEST+1))
    def test_no_internal_retry_and_defaults(self):
        class DNS:
            active=set()
            def __init__(self):self.calls=0
            def resolve(self,*args):self.calls+=1;raise relay.DNSFailure('fixture')
        dns=DNS();self.r.dns=dns
        with self.assertRaises(relay.DNSFailure):self.r.fetch(SOURCE,True)
        self.assertEqual(dns.calls,1);self.assertEqual(self.r.fetch_timeouts,{'manifest':12,'segment':12})
    def test_rate_refusal_precedes_DNS(self):
        self.r.rate=RollingBudget(lambda:0)
        for _ in range(120):self.r.rate.take()
        with patch.object(self.r.dns,'resolve') as dns,self.assertRaises(relay.SecurityRejected):self.r.fetch(SOURCE,True)
        dns.assert_not_called()

class HealthTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.instance='a'*32
        write_json(self.root/'endpoint.json',{'instance':self.instance,'endpoint':'http://127.0.0.1:19193/s/'+self.instance+'/live.m3u8'})
        write_json(self.root/'stats.json',{'instance':self.instance,'monotonic':100,'fatal':None,'stopped':False})
    def tearDown(self):self.t.cleanup()
    def opener(self,body):
        from unittest.mock import MagicMock
        op=MagicMock();response=op.open.return_value.__enter__.return_value
        response.status=200;response.read.return_value=json.dumps(body).encode();return op
    def test_health_does_not_fetch_manifest(self):
        op=self.opener({'instance':self.instance,'ok':True})
        health.current(self.root,op,lambda:101);self.assertEqual(op.open.call_args.args[0],'http://127.0.0.1:19193/healthz')
    def test_stale_file_rejected(self):
        with self.assertRaises(ValueError):health.current(self.root,self.opener({}),lambda:107)
    def test_new_process_rejects_old_record(self):
        with self.assertRaises(ValueError):health.current(self.root,self.opener({'instance':'b'*32,'ok':True}),lambda:101)

class FakeAPI:
    def __init__(self):
        self.tables={reg.STREAMS:[],reg.CHANNELS:[], '/api/channels/groups/':[{'id':1,'name':'Default Group'}],
            '/api/core/streamprofiles/':[{'id':7,'command':'ffmpeg','locked':True,'is_active':True,'parameters':'-i {streamUrl} -c copy -f mpegts pipe:1'}],
            '/api/core/settings/':[{'id':2,'key':'network_access','value':{'STREAMS':'127.0.0.1/32,10.10.20.30/32,172.16.70.1/32,172.20.0.4/32','M3U_EPG':'127.0.0.1/32','XC_API':'127.0.0.1/32'}}]}
        self.writes=[];self.fail=None;self.uncertain=False
    def rows(self,path):return copy.deepcopy(self.tables[path])
    def request(self,method,path,body=None):
        collection=next(k for k in self.tables if path.startswith(k));suffix=path[len(collection):]
        row=next((r for r in self.tables[collection] if str(r['id'])+'/'==suffix),None)
        if method=='GET':
            if row is None:raise NotFound('fixture_404')
            return copy.deepcopy(row)
        if self.fail==(method,collection):raise Rejected('fixture')
        self.writes.append((method,path,copy.deepcopy(body)))
        if method=='POST':
            row=dict(body);row.pop('channel_profile_ids',None);row['id']=max([r['id'] for r in self.tables[collection]]+[0])+1
            if collection==reg.STREAMS:row.update(is_custom=True,m3u_account=1)
            else:row['uuid']=str(uuid.uuid4())
            self.tables[collection].append(row)
        elif method=='PATCH':row.update(body)
        elif method=='DELETE':self.tables[collection].remove(row)
        if self.uncertain:self.uncertain=False;raise Uncertain('fixture_after_write')
        return copy.deepcopy(row)

class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.state=Path(self.t.name)/'state';self.runtime=Path(self.t.name)/'runtime';self.runtime.mkdir()
        self.api=FakeAPI();self.record={'instance':'a'*32,'endpoint':'http://127.0.0.1:19193/s/'+'a'*32+'/live.m3u8'}
        self.cfg={'expected_network_access_sha256':reg.digest(self.api.tables['/api/core/settings/'][0]['value']),'jellyfin_peer_ipv4':['172.20.0.4']}
        self.mock=patch.object(reg,'current',side_effect=lambda _:copy.deepcopy(self.record));self.mock.start()
    def tearDown(self):self.mock.stop();self.t.cleanup()
    def run_registration(self):return reg.reconcile(self.api,self.runtime,self.state,self.cfg)
    def test_new_registration_and_fresh_rebind(self):
        first=self.run_registration();self.record={'instance':'b'*32,'endpoint':'http://127.0.0.1:19193/s/'+'b'*32+'/live.m3u8'}
        second=self.run_registration();self.assertEqual(first['channel']['uuid'],second['channel']['uuid'])
        self.assertEqual(len(self.api.tables[reg.CHANNELS]),1);self.assertEqual(len(self.api.tables[reg.STREAMS]),1)
        self.assertEqual(second['stream']['url'],self.record['endpoint']);self.assertNotIn(relay.HOST,str(second))
        self.assertFalse((self.state/'journal.json').exists())
    def test_collision_never_adopted(self):
        self.api.tables[reg.CHANNELS].append({'id':8,'channel_number':9001})
        with self.assertRaises(Rejected):self.run_registration()
        self.assertFalse(self.api.writes)
    def test_foreign_edit_refused(self):
        self.run_registration();self.api.tables[reg.STREAMS][0]['name']='operator edit'
        count=len(self.api.writes)
        with self.assertRaises(Rejected):self.run_registration()
        self.assertEqual(len(self.api.writes),count)
    def test_channel_failure_rolls_back_created_stream(self):
        self.api.fail=('POST',reg.CHANNELS)
        with self.assertRaises(Rejected):self.run_registration()
        self.assertEqual(self.api.tables[reg.STREAMS],[]);self.assertFalse((self.runtime/'binding.json').exists())
    def test_unknown_create_outcome_reconciled_without_duplicate(self):
        self.api.uncertain=True
        with self.assertRaises(Uncertain):self.run_registration()
        self.assertEqual(len(self.api.tables[reg.STREAMS]),1)
        with self.assertRaises(Rejected):self.run_registration()
        reg.Transaction(self.api,self.state/'journal.json').rollback()
        self.run_registration();self.assertEqual(len(self.api.tables[reg.STREAMS]),1)
    def test_changed_relay_during_registration_rolls_back(self):
        with patch.object(reg,'current',side_effect=[self.record,dict(self.record,instance='b'*32)]):
            with self.assertRaises(Rejected):self.run_registration()
        self.assertEqual(self.api.tables[reg.STREAMS],[]);self.assertEqual(self.api.tables[reg.CHANNELS],[])
    def test_unknown_patch_rollback_preserves_old_endpoint(self):
        first=self.run_registration();self.record=dict(self.record,instance='b'*32,endpoint='http://127.0.0.1:19193/s/'+'b'*32+'/live.m3u8')
        self.api.uncertain=True
        with self.assertRaises(Uncertain):self.run_registration()
        with self.assertRaises(Rejected):self.run_registration()
        reg.Transaction(self.api,self.state/'journal.json').rollback()
        self.assertEqual(self.api.tables[reg.STREAMS][0]['url'],first['stream']['url'])
    def test_unresolved_rollback_blocks_next_start(self):
        self.api.fail=('POST',reg.CHANNELS)
        original=self.api.request
        def failing(method,path,body=None):
            if method=='DELETE':raise Uncertain('unreachable')
            return original(method,path,body)
        self.api.request=failing
        with self.assertRaises(Uncertain):self.run_registration()
        self.assertTrue((self.state/'journal.json').exists())
        with self.assertRaises(Rejected):self.run_registration()
        self.assertEqual(len(self.api.tables[reg.STREAMS]),1)
    def test_no_profile_or_settings_write(self):
        self.run_registration()
        self.assertTrue(all(p.startswith('/api/channels/') for _,p,_ in self.api.writes))
    def test_ACL_or_profile_drift_blocks_before_write(self):
        self.api.tables['/api/core/streamprofiles/'][0]['parameters']='-c:v libx264 -f mpegts'
        with self.assertRaises(Rejected):self.run_registration()
        self.assertFalse(self.api.writes)
    def test_explicit_pending_rollback_cannot_reverse_committed_transaction(self):
        owned=self.run_registration();write_json(self.state/'commit.json',owned)
        write_json(self.state/'journal.json',{'ops':[],'uncertain':False})
        count=len(self.api.writes)
        with self.assertRaises(Rejected):reg.Transaction(self.api,self.state/'journal.json').rollback()
        self.assertEqual(len(self.api.writes),count)

    def test_interrupted_commit_finishes_before_new_rebind(self):
        owned=self.run_registration();write_json(self.state/'commit.json',owned)
        (self.state/'owned.json').unlink();write_json(self.state/'journal.json',{'ops':[],'uncertain':False})
        self.run_registration();self.assertFalse((self.state/'commit.json').exists())
    def test_explicit_rollback_deletes_only_owned_records(self):
        self.run_registration();self.api.tables[reg.CHANNELS].append({'id':99,'name':'unrelated','streams':[]})
        reg.rollback_owned(self.api,self.runtime,self.state)
        self.assertEqual(self.api.tables[reg.STREAMS],[])
        self.assertEqual([r['id'] for r in self.api.tables[reg.CHANNELS]],[99])
        with self.assertRaises(Rejected):self.run_registration()
    def test_owned_rollback_conflict_preserves_data(self):
        owned=self.run_registration();self.api.tables[reg.CHANNELS].append({'id':99,'streams':[owned['stream']['id']]})
        with self.assertRaises(Rejected):reg.rollback_owned(self.api,self.runtime,self.state)
        self.assertEqual(len(self.api.tables[reg.STREAMS]),1)


class ExportTests(unittest.TestCase):
    def test_placeholder_no_fabricated_schedule_and_local_only(self):
        m,x=documents(str(uuid.uuid4()),dt.datetime(2026,1,1,tzinfo=dt.timezone.utc))
        self.assertIn(b'9001',m);self.assertNotIn(b'https://',m);root=ET.fromstring(x)
        self.assertEqual(len(root.findall('programme')),1);self.assertIn('placeholder',root.find('programme/title').text)
        self.assertEqual(root.find('programme').attrib['channel'],'dw-english-permanent')
    def test_renewal_atomic_pair_and_bounded_generations(self):
        with tempfile.TemporaryDirectory() as t:
            ident=str(uuid.uuid4());now=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
            for h in range(8):publish(t,ident,now+dt.timedelta(hours=h))
            self.assertLessEqual(len(list(Path(t).glob('g-*'))),2)
            self.assertTrue((Path(t)/'current/guide.xml').exists());self.assertTrue((Path(t)/'current/dispatcharr.m3u').exists())
    def test_untrusted_UUID_and_symlink_refused(self):
        with self.assertRaises(ValueError):documents('bad\nhttp://evil.invalid',dt.datetime.now(dt.timezone.utc))
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/'current').mkdir()
            with self.assertRaises(ValueError):publish(t,str(uuid.uuid4()))

class JellyfinTests(unittest.TestCase):
    def test_only_owned_tuner_provider_added_and_idempotent(self):
        before={'TunerHosts':[{'Id':'other','Url':'private-existing'}],'ListingProviders':[], 'DVR':'unchanged','libraries':'untouched'}
        result=jellyfin.plan(before);self.assertEqual(before['TunerHosts'][0],result['TunerHosts'][0])
        self.assertEqual(result,jellyfin.plan(result));self.assertEqual(before['DVR'],result['DVR'])
        t=result['TunerHosts'][-1];self.assertEqual(t['TunerCount'],1);self.assertTrue(t['AllowStreamSharing']);self.assertFalse(t['EnableStreamLooping'])
    def test_rollback_conflict_is_not_overwritten(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'receipt';write_json(p,{'before':{},'after':{'TunerHosts':[]}})
            api=MagicMock();api.config.return_value={'operator':'change'}
            with self.assertRaises(ValueError):jellyfin.rollback(api,p)
            self.assertEqual(api.config.call_count,1)
    def test_server_defaults_do_not_hide_unrelated_configuration_changes(self):
        planned=jellyfin.plan({'TunerHosts':[],'ListingProviders':[],'DVR':'preserve'})
        actual=copy.deepcopy(planned);actual['TunerHosts'][0]['ServerGeneratedDefault']=False
        self.assertTrue(jellyfin.scoped_result(planned,actual))
        actual['DVR']='changed';self.assertFalse(jellyfin.scoped_result(planned,actual))

    def test_rollback_exact_transaction(self):
        class Fake:
            def __init__(self):self.value={'TunerHosts':[],'ListingProviders':[],'unchanged':True}
            def config(self,value=None):
                if value is not None:self.value=copy.deepcopy(value)
                return copy.deepcopy(self.value)
        f=Fake();before=f.config()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'receipt';jellyfin.apply(f,p);jellyfin.rollback(f,p)
        self.assertEqual(f.config(),before)

class LifecycleTests(unittest.TestCase):
    def test_registration_and_exports_precede_gateway(self):
        events=[]
        with patch.object(lifecycle,'execute',side_effect=lambda a,*_:events.append(a)),patch.object(lifecycle,'inside',side_effect=lambda *a,**k:events.append(list(a))),patch.object(lifecycle,'trusted'):lifecycle.start()
        registration=next(i for i,e in enumerate(events) if e[0]=='register.py')
        gateway=next(i for i,e in enumerate(events) if e[-1]=='gateway')
        self.assertLess(registration,gateway);self.assertIn('--no-deps',events[gateway])
    def test_registration_failure_never_starts_gateway(self):
        calls=[]
        def inside(script,*args,**kw):
            if script=='register.py':raise ValueError('fixture')
        with patch.object(lifecycle,'execute',side_effect=lambda a,*_:calls.append(a)),patch.object(lifecycle,'inside',side_effect=inside),patch.object(lifecycle,'trusted'):
            with self.assertRaises(ValueError):lifecycle.start()
        self.assertFalse(any(c[-1]=='gateway' for c in calls))
    def test_scoped_cleanup_only_four_services(self):
        with patch.object(lifecycle,'execute') as execute,patch.object(lifecycle,'trusted'):lifecycle.stop()
        a=next(c.args[0] for c in execute.call_args_list if 'compose' in c.args[0]);self.assertEqual(a[-4:],['gateway','relay','dispatcharr','iptv-vpn']);self.assertNotIn('down',a)

if __name__=='__main__':unittest.main()
