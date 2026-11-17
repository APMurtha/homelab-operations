import contextlib
import copy
import importlib
import io
import json
import os
from pathlib import Path
import socket
import ssl
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import urlsplit, parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dispatcharr_provider import core as c, cli


def raw():
    return {'groups':[{'category_id':'1','category_name':'News'},{'category_id':'2','category_name':'Arts'}],
            'channels':[{'stream_id':11,'category_id':'1','name':'Station One','epg_channel_id':'station.one','container_extension':'ts'},
                        {'stream_id':22,'category_id':'2','name':'Station Two','epg_channel_id':'station.two','container_extension':'m3u8'}],
            'epg_ids':['station.one','station.two']}

def provider():return c.provider('Fixture','https://provider.example.invalid','fixture-user','secret-phrase-987','',1)

def bundle():
    p=provider();cat=c.catalogue(raw());return {'schema':1,'owner':c.OWNER,'provider':p,
        'plan':c.plan(p,cat,['1'],['11'],{}),'catalogue_digest':c.digest(cat)}


class Validation(unittest.TestCase):
    def test_valid_and_normalized_URL(self):self.assertEqual(c.url('https://PROVIDER.example.invalid/'),'https://provider.example.invalid')
    def test_insecure_and_ambiguous_URLs(self):
        for target in ['http://host.test','https://u:p@host.test','https://127.0.0.1','https://host.test:8443',
                       'https://host.test/#fragment','https://host.test/a/../x','https://host.test/%2e','https://host.test//x',
                       'https://host.test/\nx','https://host.test\\x','https://bad..test/']:
            with self.subTest(target=target),self.assertRaises(c.Refused):c.url(target)
    def test_base_query_refused(self):
        with self.assertRaises(c.Refused):c.url('https://provider.test/?token=private',True)
    def test_media_EPG_URL_refused(self):
        with self.assertRaises(c.Refused):c.provider('X','https://provider.test','u','p','https://provider.test/live/1.ts',1)
    def test_unknown_or_unlimited_connection_allowance_refused(self):
        for value in [0,-1,True,101,'1',None]:
            with self.assertRaises(c.Refused):c.provider('X','https://provider.test','u','p','',value)
    def test_empty_control_or_large_credentials_refused(self):
        for password in ['', 'p\nx','x'*513]:
            with self.assertRaises(c.Refused):c.provider('X','https://provider.test','u',password,'',1)
    def test_provider_names_no_terminal_injection(self):
        for name in ['https://foo','bad\x1bname','']:
            with self.assertRaises(c.Refused):c.provider(name,'https://provider.test','u','p','',1)
    def test_redaction_plain_percent_URL_and_controls(self):
        r=c.Redactor('secret/word');r.collect({'password':'anothersecret'})
        for secret in ['secret/word','secret%2Fword','anothersecret']:
            self.assertNotIn(secret,r.text('label '+secret))
        self.assertNotIn('token=value',r.text('see https://x.test/a?token=value'))
        self.assertNotIn('\x1b',r.text('bad\x1b[31m'))
    def test_JSON_duplicate_nonfinite_and_size_rejected(self):
        for data in [b'{"a":1,"a":2}',b'{"a":NaN}',b'not-json',b'x'*(c.MAX_BYTES+1)]:
            with self.assertRaises(c.Refused):c.decode(data)
    def test_private_permissions_symlinks_hardlinks_and_FIFO(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'secret';p.write_text('{}');p.chmod(0o600);self.assertEqual(c.private_read(p),{})
            p.chmod(0o644)
            with self.assertRaises(c.Refused):c.private_read(p)
            p.chmod(0o600);alias=Path(t)/'alias';alias.symlink_to(p)
            with self.assertRaises(c.Refused):c.private_read(alias)
            alias.unlink();os.link(p,alias)
            with self.assertRaises(c.Refused):c.private_read(p)
            fifo=Path(t)/'fifo';os.mkfifo(fifo,0o600)
            with self.assertRaises(c.Refused):c.private_read(fifo)
    def test_root_approval_cannot_be_user_owned(self):
        if os.geteuid()==0:self.skipTest('this test is for an unprivileged operator')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'approval';p.write_text('{}');p.chmod(0o600)
            with self.assertRaises(c.Refused):c.private_read(p,root=True)


class Metadata(unittest.TestCase):
    def setUp(self):
        self.context=patch.object(c.MetadataHTTPS,'context_checks');self.context.start();self.addCleanup(self.context.stop)
        self.route=patch.object(c.MetadataHTTPS,'vpn_route');self.route.start();self.addCleanup(self.route.stop)
    def approval(self):
        ns=Path('/proc/self/ns/net').stat()
        return {'schema':1,'purpose':'IPTV_METADATA_ONLY','review_reference':'synthetic-review',
                'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'netns':[ns.st_dev,ns.st_ino],'expires_epoch':c.time.time()+600,
                'endpoints':[{'host':'provider.example.invalid','path':'/player_api.php','ipv4':['93.184.216.34']}]}
    def test_valid_approval_DNS_and_namespace(self):
        with patch.object(c,'private_read',return_value=self.approval()),patch.object(c,'resolve',return_value={'93.184.216.34'}):
            self.assertEqual(c.MetadataHTTPS('synthetic').authorize('https://provider.example.invalid/player_api.php')[1],'93.184.216.34')
    def test_stale_boot_namespace_expiry_and_purpose_refused(self):
        for key,value in [('boot_id','other'),('netns',[0,0]),('expires_epoch',0),('purpose','MEDIA'),('review_reference','')]:
            a=self.approval();a[key]=value
            with patch.object(c,'private_read',return_value=a),self.assertRaises(c.Refused):c.MetadataHTTPS('synthetic').authorize('https://provider.example.invalid/player_api.php')
    def test_private_multicast_rebinding_and_AAAA_refused(self):
        for answers in [{'127.0.0.1'},{'10.0.0.1'},{'93.184.216.34','127.0.0.1'},{'2001:4860:4860::8888'},set()]:
            with patch.object(c,'private_read',return_value=self.approval()),patch.object(c,'resolve',return_value=answers),self.assertRaises(c.Refused):c.MetadataHTTPS('synthetic').authorize('https://provider.example.invalid/player_api.php')
    def test_unapproved_endpoint_and_host_refused(self):
        for u in ['https://other.example.invalid/player_api.php','https://provider.example.invalid/live/1.ts']:
            with patch.object(c,'private_read',return_value=self.approval()),self.assertRaises(c.Refused):c.MetadataHTTPS('synthetic').authorize(u)
    def transport(self,status=200,content=b'[]',encoding='identity'):
        transport=c.MetadataHTTPS('synthetic');conn=MagicMock();response=conn.getresponse.return_value
        response.status=status;response.getheader.return_value=encoding;response.read1.side_effect=[content,b'']
        return transport,conn
    def test_TLS_hostname_and_checked_IP_pinning(self):
        t,conn=self.transport();context=MagicMock();context.verify_mode=ssl.CERT_REQUIRED;context.check_hostname=True;t.context=context
        with patch.object(t,'authorize',return_value=(urlsplit('https://provider.example.invalid/player_api.php'), '93.184.216.34')),patch.object(c.http.client,'HTTPSConnection',return_value=conn),patch.object(c.socket,'create_connection') as connect:
            self.assertEqual(t.get('synthetic'),b'[]');self.assertEqual(connect.call_args.args[0],('93.184.216.34',443));self.assertEqual(context.wrap_socket.call_args.kwargs['server_hostname'],'provider.example.invalid')
    def test_TLS_insecure_context_refused(self):
        t,conn=self.transport();t.context=ssl._create_unverified_context()
        with patch.object(t,'authorize',return_value=(urlsplit('https://provider.example.invalid/player_api.php'),'93.184.216.34')),self.assertRaises(c.Refused):t.get('synthetic')
    def test_redirects_HTTP_errors_and_compression_no_retry(self):
        for code,encoding in [(301,'identity'),(302,'identity'),(403,'identity'),(500,'identity'),(200,'gzip')]:
            t,conn=self.transport(code,encoding=encoding)
            t.context=MagicMock(verify_mode=ssl.CERT_REQUIRED,check_hostname=True)
            with patch.object(t,'authorize',return_value=(urlsplit('https://provider.example.invalid/player_api.php'),'93.184.216.34')),patch.object(c.http.client,'HTTPSConnection',return_value=conn),patch.object(c.socket,'create_connection'),self.assertRaises(c.Refused):t.get('synthetic')
            self.assertEqual(conn.request.call_count,1)
    def test_metadata_body_size_and_deadline_limits(self):
        for content,times in [(b'x'*(c.MAX_BYTES+1),None),(b'[]',[0,16])]:
            t,conn=self.transport(content=content);t.context=MagicMock(verify_mode=ssl.CERT_REQUIRED,check_hostname=True)
            clock=patch.object(c.time,'monotonic',side_effect=times) if times else contextlib.nullcontext()
            with patch.object(t,'authorize',return_value=(urlsplit('https://provider.example.invalid/player_api.php'),'93.184.216.34')),patch.object(c.http.client,'HTTPSConnection',return_value=conn),patch.object(c.socket,'create_connection'),clock,self.assertRaises(c.Refused):t.get('synthetic')
            self.assertEqual(conn.request.call_count,1)
    def test_TLS_certificate_failure_before_credentials_are_sent(self):
        t,conn=self.transport();t.context=MagicMock(verify_mode=ssl.CERT_REQUIRED,check_hostname=True);t.context.wrap_socket.side_effect=ssl.SSLCertVerificationError('synthetic_secret_URL')
        with patch.object(t,'authorize',return_value=(urlsplit('https://provider.example.invalid/player_api.php'),'93.184.216.34')),patch.object(c.http.client,'HTTPSConnection',return_value=conn),patch.object(c.socket,'create_connection'),self.assertRaises(c.Refused) as err:t.get('synthetic')
        conn.request.assert_not_called();self.assertNotIn('synthetic_secret',str(err.exception))

    def test_provider_errors_do_not_echo_credential_URL(self):
        t,conn=self.transport();t.context=MagicMock(verify_mode=ssl.CERT_REQUIRED,check_hostname=True)
        with patch.object(t,'authorize',return_value=(urlsplit('https://provider.example.invalid/player_api.php'),'93.184.216.34')),patch.object(c.socket,'create_connection',side_effect=OSError('https://secret:password@provider/')),self.assertRaises(c.Refused) as e:t.get('synthetic')
        self.assertNotIn('password',str(e.exception))
    def test_fixed_actions_no_media_and_optional_default_EPG(self):
        p=provider();mock=MagicMock();mock.get.side_effect=[json.dumps(raw()['groups']).encode(),json.dumps(raw()['channels']).encode(),b'<tv><channel id="station.one"/></tv>']
        cat=c.discover(p,mock);self.assertIn('station.one',cat['epg_ids'])
        urls=[call.args[0] for call in mock.get.call_args_list]
        self.assertEqual([parse_qs(urlsplit(u).query).get('action') for u in urls[:2]],[['get_live_categories'],['get_live_streams']])
        self.assertTrue(all('/live/' not in u for u in urls));self.assertEqual(urlsplit(urls[2]).path,'/xmltv.php')
    def test_optional_EPG_unavailable_is_explicit_but_TLS_errors_not_hidden(self):
        p=provider();m=MagicMock();m.get.side_effect=[json.dumps(raw()['groups']).encode(),json.dumps(raw()['channels']).encode(),c.Unavailable('metadata_not_available')]
        self.assertEqual(c.discover(p,m)['epg_status'],'provider_EPG_unavailable')
        m.get.side_effect=[json.dumps(raw()['groups']).encode(),json.dumps(raw()['channels']).encode(),c.Refused('TLS_error')]
        with self.assertRaises(c.Refused):c.discover(p,m)
    def test_DNS_worker_is_bounded_and_cleans_up(self):
        with patch.object(c.socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,0,'',('93.184.216.34',443))]):
            self.assertEqual(c.resolve('synthetic.invalid'),{'93.184.216.34'})


class Planning(unittest.TestCase):
    def test_stable_EPG_exact_match_and_unknown_format(self):
        plan=c.plan(provider(),c.catalogue(raw()),['1'],['11'],{})
        self.assertEqual(plan['epg_matches'],{'11':'station.one'});self.assertEqual(plan['streaming_activation'],'BLOCKED');self.assertEqual(plan['native_resources_created'],[])
    def test_missing_EPG_not_fuzzy_matched(self):
        r=raw();r['epg_ids']=['STATION.ONE'];plan=c.plan(provider(),c.catalogue(r),['1'],['11'],{})
        self.assertEqual(plan['epg_matches'],{});self.assertEqual(plan['unmatched_channel_ids'],['11'])
    def test_selection_subset_limits_and_unknown(self):
        self.assertEqual(c.select('11,11',{'11':{},'22':{}}),['11'])
        for value in ['', '55','all']:
            with self.assertRaises(c.Refused):c.select(value,{'11':{},'22':{}},cap=1)
    def test_channel_cannot_escape_selected_group(self):
        with self.assertRaises(c.Refused):c.plan(provider(),c.catalogue(raw()),['1'],['22'],{})
    def test_duplicates_provider_name_identity_channel_and_EPG(self):
        p=provider();cat=c.catalogue(raw())
        fixtures=[{'groups':[{'id':2,'name':'News'}]},{'accounts':[{'name':p['name']}]},{'accounts':[{'name':'Other','server_url':p['server'],'username':p['username']}]},
                  {'channels':[{'id':7,'name':'Station One'}]},{'channels':[{'id':7,'tvg_id':'station.one'}]},
                  {'epgdata':[{'id':1,'tvg_id':'station.one'},{'id':2,'tvg_id':'station.one'}]}]
        for existing in fixtures:
            with self.subTest(existing=existing),self.assertRaises(c.Refused):c.plan(p,cat,['1'],['11'],existing)
    def test_DW_English_existing_resources_preserved(self):
        existing={'channels':[{'id':3,'name':'DW English','tvg_id':'dw-english-permanent','streams':[3]}]};saved=copy.deepcopy(existing)
        c.plan(provider(),c.catalogue(raw()),['1'],['11'],existing);self.assertEqual(existing,saved)
    def test_direct_DW_collision_refused(self):
        r=raw();r['channels'][0]['epg_channel_id']='dw-english-permanent'
        with self.assertRaises(c.Refused):c.plan(provider(),c.catalogue(r),['1'],['11'],{'channels':[{'id':3,'tvg_id':'dw-english-permanent'}]})
    def test_duplicate_catalogue_and_EPG_IDs_refused(self):
        for key in ['groups','channels','epg_ids']:
            r=raw();r[key].append(copy.deepcopy(r[key][0]))
            with self.assertRaises(c.Refused):c.catalogue(r)
    def test_large_inventory_bounded(self):
        r=raw();r['channels']=[dict(r['channels'][0],stream_id=i+1) for i in range(10000)]
        self.assertEqual(len(c.catalogue(r)['channels']),10000)
        with patch.object(c,'MAX_ROWS',100),self.assertRaises(c.Refused):c.catalogue(r)
    def test_XMLTV_entities_duplicates_and_malformed_refused(self):
        for rawxml in [b'<!DOCTYPE tv><tv/>', '<!DOCTYPE tv><tv/>'.encode('utf-16'),b'<!ENTITY x "evil"><tv/>',b'<tv><channel id="a"/><channel id="a"/></tv>',b'<bad>',b'<root/>']:
            with self.assertRaises(c.Refused):c.xmltv_ids(rawxml)
    def test_XMLTV_valid(self):self.assertEqual(c.xmltv_ids(b'<tv><channel id="news.1"/></tv>'),{'news.1'})


class API(unittest.TestCase):
    def api(self):a=object.__new__(c.Dispatcharr);a.token='synthetic';a.origin='http://127.0.0.1:9191';a.opener=MagicMock();return a
    def test_all_production_mutations_refused_before_transport(self):
        a=self.api()
        for method in ['POST','PATCH','DELETE']:
            for path in c.COLLECTIONS:
                with self.assertRaises(c.Refused):a.request(method,path,{'password':'synthetic'})
        a.opener.open.assert_not_called()
    def test_unknown_or_broad_API_origins_refused(self):
        for origin in ['http://10.10.20.30:9191','https://unapproved.example.invalid']:
            with self.assertRaises(c.Refused):c.Dispatcharr(origin,{})
    def test_pagination_uses_local_number_not_remote_next_URL(self):
        a=self.api();a.request=MagicMock(side_effect=[{'results':[{'id':1}],'next':'https://evil.test/secret'},{'results':[{'id':2}],'next':None}])
        self.assertEqual(len(a.rows('/api/channels/channels/')),2)
        self.assertEqual(a.request.call_args.args[1],'/api/channels/channels/?visibility_filter=all&page=2')
    def test_duplicate_page_and_infinite_pages_fail(self):
        a=self.api();a.request=MagicMock(return_value={'results':[{'id':1}],'next':'more'})
        with self.assertRaises(c.Refused):a.rows('/api/m3u/accounts/')
        a.request=MagicMock(return_value={'results':[],'next':'more'})
        with self.assertRaises(c.Refused):a.rows('/api/m3u/accounts/')
        self.assertEqual(a.request.call_count,64)
    def test_hostile_error_is_generic(self):
        from urllib.error import URLError
        a=self.api();a.opener.open.side_effect=URLError('secret=must-not-print')
        with self.assertRaises(c.Refused) as e:a.request('GET','/api/m3u/accounts/?page=1')
        self.assertNotIn('must-not-print',str(e.exception))


class Ownership(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'state';self.b=bundle();self.key=self.b['provider']['key']
    def test_add_refresh_remove_and_private_recovery(self):
        with c.Store(self.root) as store:
            store.transact(self.key,None,self.b,'add');self.assertEqual(store.get(self.key),self.b)
            st=store.path(self.key).stat();self.assertEqual(st.st_mode&0o777,0o600)
            newer=dict(self.b,catalogue_digest='updated');store.transact(self.key,self.b,newer,'refresh')
            store.transact(self.key,newer,None,'remove');self.assertFalse(store.path(self.key).exists())
            archives=list(self.root.glob('retired-*.json'));self.assertEqual(len(archives),1);self.assertEqual(c.private_read(archives[0]),newer)
    def test_before_image_conflict(self):
        with c.Store(self.root) as store:
            store.transact(self.key,None,self.b,'add')
            with self.assertRaises(c.Refused):store.transact(self.key,None,self.b,'add')
    def test_remote_resource_ownership_never_deleted(self):
        with c.Store(self.root) as store:
            bad=copy.deepcopy(self.b);bad['plan']['native_resources_created']=[{'type':'channel','id':3}]
            with self.assertRaises(c.Refused):store.transact(self.key,None,bad,'add')
    def test_unowned_draft_and_wrong_provider_key_refused(self):
        with c.Store(self.root) as store:
            bad=copy.deepcopy(self.b);bad['owner']='unmanaged';c.atomic(store.path(self.key),bad)
            with self.assertRaises(c.Refused):store.get(self.key)
            bad=copy.deepcopy(self.b);bad['provider']['username']='changed';c.atomic(store.path(self.key),bad)
            with self.assertRaises(c.Refused):store.get(self.key)
    def test_crash_after_publication_reconciles_without_repeating(self):
        with c.Store(self.root) as store:
            original=c.atomic
            def crash(path,value):
                if path.name=='operation.json' and value['state']=='complete':raise OSError('synthetic_crash')
                original(path,value)
            with patch.object(c,'atomic',side_effect=crash),self.assertRaises(OSError):store.transact(self.key,None,self.b,'add')
            with self.assertRaises(c.Refused):store.transact(self.key,self.b,self.b,'refresh')
            self.assertEqual(store.reconcile()['state'],'complete');self.assertEqual(store.get(self.key),self.b)
    def test_crash_before_publication_aborts_no_retry(self):
        with c.Store(self.root) as store:
            original=c.atomic
            def crash(path,value):
                if path.name==self.key+'.json':raise OSError('synthetic_crash')
                original(path,value)
            with patch.object(c,'atomic',side_effect=crash),self.assertRaises(OSError):store.transact(self.key,None,self.b,'add')
            self.assertEqual(store.reconcile()['state'],'aborted_without_retry');self.assertFalse(store.path(self.key).exists())
    def test_interrupted_remove_known_archive_reconciles(self):
        with c.Store(self.root) as store:
            store.transact(self.key,None,self.b,'add');original=c.atomic
            def crash(path,value):
                if path.name=='operation.json' and value['state']=='complete':raise OSError('synthetic_crash')
                original(path,value)
            with patch.object(c,'atomic',side_effect=crash),self.assertRaises(OSError):store.transact(self.key,self.b,None,'remove')
            self.assertEqual(store.reconcile()['state'],'complete')
    def test_pending_unexpected_state_refuses(self):
        with c.Store(self.root) as store:
            store.transact(self.key,None,self.b,'add');op=store.pending();op['state']='pending';c.atomic(self.root/'operation.json',op)
            changed=copy.deepcopy(self.b);changed['catalogue_digest']='foreign';c.atomic(store.path(self.key),changed)
            with self.assertRaises(c.Refused):store.reconcile()
    def test_unsafe_directory_lock_symlink_and_journal(self):
        self.root.mkdir(mode=0o755)
        with self.assertRaises(c.Refused):
            with c.Store(self.root):pass
        self.root.chmod(0o700);(self.root/'lock').symlink_to('/etc/passwd')
        with self.assertRaises(OSError):
            with c.Store(self.root):pass
        (self.root/'lock').unlink()
        with c.Store(self.root) as store:
            c.atomic(self.root/'operation.json',{'id':'../../outside'})
            with self.assertRaises(c.Refused):store.pending()


class CLI(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.fixture=self.root/'fixture.json';self.fixture.write_text(json.dumps(raw()))
    def run_cli(self,extra,answers):
        out=io.StringIO();err=io.StringIO()
        with patch('builtins.input',side_effect=answers),patch.object(cli.getpass,'getpass',side_effect=['secret-phrase-987','']),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            rc=cli.main(['--state-dir',str(self.root/'state'),*extra])
        return rc,out.getvalue(),err.getvalue()
    def inputs(self):return ['Fixture','https://provider.example.invalid','fixture-user','1','1','11']
    def test_dry_run_no_state_or_network_and_no_secrets(self):
        with patch.object(c.MetadataHTTPS,'get',side_effect=AssertionError('no network')):
            rc,out,err=self.run_cli(['add','--fixture',str(self.fixture)],self.inputs())
        self.assertEqual(rc,0,err);self.assertNotIn('secret-phrase-987',out+err);self.assertNotIn('fixture-user',out+err);self.assertFalse((self.root/'state').exists());self.assertIn('BLOCKED',out)
    def test_apply_requires_exact_confirmation_and_saves_only_draft(self):
        p=provider();rc,out,err=self.run_cli(['add','--fixture',str(self.fixture),'--apply'],self.inputs()+['ADD '+p['key'][:12]])
        self.assertEqual(rc,0,err)
        with c.Store(self.root/'state') as store:self.assertEqual(store.get(p['key'])['plan']['native_resources_created'],[])
    def test_cancelled_confirmation_has_no_secret_installation(self):
        rc,out,err=self.run_cli(['add','--fixture',str(self.fixture),'--apply'],self.inputs()+['no'])
        self.assertEqual(rc,2);self.assertFalse((self.root/'state').exists())
    def test_accidental_secret_arguments_never_echoed(self):
        rc,out,err=self.run_cli(['add','--password','secret-phrase-987'],[])
        self.assertEqual(rc,2);self.assertNotIn('secret-phrase-987',out+err);self.assertNotIn('Traceback',err)
    def test_list_inspect_refresh_and_remove_local_draft_only(self):
        p=provider();key=p['key'];state=self.root/'state'
        with c.Store(state) as store:store.transact(key,None,bundle(),'add')
        for command in ['list','inspect']:
            rc,out,err=self.run_cli([command],[]);self.assertEqual(rc,0,err);self.assertIn(key,out);self.assertNotIn(p['password'],out)
        rc,out,err=self.run_cli(['refresh',key,'--fixture',str(self.fixture)],[]);self.assertEqual(rc,0,err)
        rc,out,err=self.run_cli(['remove',key,'--apply'],['REMOVE '+key[:12]]);self.assertEqual(rc,0,err)
        self.assertFalse((state/(key+'.json')).exists());self.assertEqual(len(list(state.glob('retired-*.json'))),1)
    def test_refresh_refuses_changed_owned_EPG_mapping(self):
        p=provider();key=p['key']
        with c.Store(self.root/'state') as store:store.transact(key,None,bundle(),'add')
        changed=raw();changed['channels'][0]['epg_channel_id']='different';self.fixture.write_text(json.dumps(changed))
        rc,out,err=self.run_cli(['refresh',key,'--fixture',str(self.fixture)],[]);self.assertEqual(rc,2);self.assertIn('no_overwrite',err)
    def test_hostile_provider_names_redacted_in_output(self):
        changed=raw();changed['channels'][0]['name']='secret-phrase-987 https://evil.invalid/?token=private';self.fixture.write_text(json.dumps(changed))
        rc,out,err=self.run_cli(['add','--fixture',str(self.fixture)],self.inputs());self.assertEqual(rc,0,err)
        self.assertNotIn('secret-phrase-987',out+err);self.assertNotIn('token=private',out+err)
    def test_remote_inspection_redacts_admin_account_passwords(self):
        inv={'accounts':[{'id':1,'name':'embedded-provider-password','password':'provider-password','username':'private-user'}],'channels':[{'id':3}], 'epg_sources':[],'epgdata':[]}
        with patch.object(cli,'inventory',return_value=inv):rc,out,err=self.run_cli(['inspect','--remote'],[])
        self.assertEqual(rc,0,err);self.assertNotIn('provider-password',out+err);self.assertNotIn('private-user',out+err)

    def test_secure_getpass_fallback_refused(self):
        with patch.object(cli.getpass,'getpass',side_effect=cli.getpass.GetPassWarning),self.assertRaises(c.Refused):cli.hidden('Password: ')
    def test_selection_display_pages_without_unbounded_output(self):
        rows={str(i):{'name':'Station'} for i in range(1,121)};out=io.StringIO()
        with patch('builtins.input',side_effect=['y','n']),contextlib.redirect_stdout(out):cli.show_rows(rows,c.Redactor(),'channels')
        self.assertIn('100:',out.getvalue());self.assertNotIn('101:',out.getvalue())

    def test_interruption_no_traceback(self):
        with patch('builtins.input',side_effect=KeyboardInterrupt),contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(cli.main(['add','--fixture',str(self.fixture)]),130)
        self.assertNotIn('Traceback',err.getvalue())

class Contract(unittest.TestCase):
    def test_original_source_and_image_pins_preserved(self):
        root=Path(__file__).resolve().parents[2]
        contract=json.loads((root/'tools/dispatcharr_provider/api-contract.json').read_text())
        original=json.loads((root/'configs/dispatcharr-iptv/permanent-streaming/api-source-pins.json').read_text())
        self.assertEqual(contract['upstream_commit'],original['commit']);self.assertEqual(contract['accepted_image'],original['image'])
        for path,digest in original['files'].items():self.assertEqual(contract['source_files'][path],digest)
    def test_existing_EPG_source_is_not_adopted(self):
        p=c.provider('Fixture','https://provider.example.invalid','fixture-user','synthetic','https://provider.example.invalid/guide.xml?token=placeholder',1)
        existing={'epg_sources':[{'id':17,'url':p['epg_url']}]};before=copy.deepcopy(existing)
        with self.assertRaises(c.Refused):c.plan(p,c.catalogue(raw()),['1'],['11'],existing)
        self.assertEqual(existing,before)


class Context(unittest.TestCase):
    def test_host_namespace_and_unreviewed_policy_refused(self):
        for value in [{}, {'vpn_interface':'tun0','netns':[1,2],'host_netns':[1,2],'policy_review_sha256':'a'*64}]:
            with self.assertRaises(c.Refused):c.MetadataHTTPS.context_checks(value)
    def test_dns_and_IPv6_still_required(self):
        value={'vpn_interface':'tun0','netns':[1,2],'host_netns':[1,3],'policy_review_sha256':'a'*64}
        for dns,ipv6 in [('nameserver 8.8.8.8','1'),('nameserver 127.0.0.1','0')]:
            with patch.object(Path,'read_text',autospec=True,side_effect=lambda path: dns if str(path)=='/etc/resolv.conf' else ipv6),self.assertRaises(c.Refused):c.MetadataHTTPS.context_checks(value)
        def read(path):return 'nameserver 127.0.0.1\n' if str(path)=='/etc/resolv.conf' else '1'
        with patch.object(Path,'read_text',autospec=True,side_effect=read):c.MetadataHTTPS.context_checks(value)
    def test_only_tun0_route_is_accepted(self):
        for dev in ['eth0','lo','tun0']:
            result=MagicMock(returncode=0,stdout=json.dumps([{'dev':dev}]).encode())
            with patch.object(c.subprocess,'run',return_value=result),patch.object(Path,'exists',return_value=True),patch.object(Path,'stat',return_value=MagicMock(st_uid=0,st_mode=0o100755)):
                if dev=='tun0':c.MetadataHTTPS.vpn_route('93.184.216.34')
                else:
                    with self.assertRaises(c.Refused):c.MetadataHTTPS.vpn_route('93.184.216.34')

if __name__=='__main__':unittest.main()
