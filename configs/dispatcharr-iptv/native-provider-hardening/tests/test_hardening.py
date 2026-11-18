"""Synthetic-only security fixtures; never import Django or contact a provider."""
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
import socket
import ssl
import struct
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch,MagicMock

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[2]
package=types.ModuleType('fixture_core');package.__path__=[str(BASE/'runtime')];sys.modules['fixture_core']=package
from fixture_core import provider_security as s,provider_transport as t,provider_dns as dns,provider_policy as policy_interface
spec=importlib.util.spec_from_file_location('prepare_native',BASE/'prepare.py');prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)


def resource(kind='XC'):
    p=types.SimpleNamespace(account_type=kind,server_url='https://provider.example.invalid',username='synthetic-user',custom_properties={},is_active=True)
    key=s.digest([p.server_url,p.username]);p.custom_properties={'provider_cli':{'key':key,'owner':'dispatcharr-provider/v1/native-v1'}}
    return p,key


class Security(unittest.TestCase):
    def setUp(self):
        self.r,self.key=resource()
        self.policy={'operations':['discover','refresh','epg'],'policy_review_sha256':'a'*64}
        self.p=patch.object(s,'policy',return_value=self.policy);self.p.start();self.addCleanup(self.p.stop)
        self.reader=patch.object(s,'Readiness');self.reader.start();self.addCleanup(self.reader.stop)
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
    def enter(self,kind='refresh'): self.stack.enter_context(s.job(kind,self.r,True))
    def deny(self,fn):
        with self.assertRaises((s.Denied,t.Refused,ValueError)):fn()

    def test_no_ambient_permission(self): self.deny(lambda:s.fetch('https://provider.example.invalid/player_api.php'))
    def test_scheduled_task_has_no_explicit_authority(self):
        self.deny(lambda:s.job('refresh',self.r,False).__enter__())
    def test_unapproved_action_refused(self):
        self.policy['operations']=['discover'];self.deny(lambda:s.job('refresh',self.r,True).__enter__())
    def test_resource_key_cannot_be_rebound_to_different_provider(self):
        self.r.server_url='https://other.example.invalid';self.deny(lambda:s.resource_key(self.r))
    def test_unowned_resource_refused(self):
        self.r.custom_properties['provider_cli']['owner']='foreign';self.deny(lambda:s.resource_key(self.r))
    def test_guard_grant_failure_refuses_job(self):
        with patch.object(s,'Readiness',side_effect=ValueError('synthetic-secret')):self.deny(lambda:s.job('refresh',self.r,True).__enter__())
    def test_revocation_is_observed_before_next_io(self):
        self.enter();self.policy['operations']=[]
        self.deny(s.check)
    def test_replaced_approval_refused(self):
        self.enter()
        with patch.object(s,'policy',return_value={**self.policy,'new':'generation'}):self.deny(s.check)
    def test_generation_revocation_checked_during_job(self):
        self.enter();s.CURRENT.get()['reader'].check.side_effect=ValueError('revoked')
        self.deny(s.check)
    def test_scope_does_not_leak_to_later_tasks(self):
        with s.job('refresh',self.r,True):self.assertEqual(s.check()['key'],self.key)
        self.deny(s.check)
    def test_deactivated_provider_cannot_start_a_new_refresh(self):
        self.r.is_active=False
        self.deny(lambda:s.job('refresh',self.r,True).__enter__())
        with s.job('discover',self.r,True):self.assertEqual(s.check()['kind'],'discover')

    def test_local_custom_DW_does_not_require_provider_policy(self):
        self.r.account_type='STD'
        with s.job('refresh',self.r,False):self.assertIsNone(s.CURRENT.get())
    def test_profile_and_VOD_network_actions_not_allowed(self):
        self.enter()
        for action in ('get_vod_info','get_series','get_short_epg'):
            self.deny(lambda:s.xc_get(self.r.server_url,'player_api.php',{'action':action}))
    def test_unapproved_endpoint_refused(self):
        self.enter();self.deny(lambda:s.xc_get(self.r.server_url,'other.php',{}))
    def test_credential_query_encoding_never_becomes_argv(self):
        self.enter()
        with patch.object(s,'fetch',return_value=b'[]') as fetch:
            self.assertEqual(s.xc_get(self.r.server_url,'player_api.php',{'username':'name &','password':'secret/?','action':'get_live_streams'}),[])
            target=fetch.call_args.args[0];self.assertIn('password=secret%2F%3F',target)
    def test_unknown_provider_URL_fields_cannot_bypass_artwork_suppression(self):
        self.enter()
        raw=[{'stream_id':101,'category_id':'1','name':'Fixture','epg_channel_id':'one','stream_icon':'http://private.invalid/token','tvg-logo':'http://127.0.0.1','direct_source':'http://169.254.169.254','custom-secret-url':'https://unapproved.invalid'}]
        with patch.object(s,'fetch',return_value=json.dumps(raw).encode()):
            rows=s.xc_get(self.r.server_url,'player_api.php',{'action':'get_live_streams'})
        self.assertEqual(rows,[{'stream_id':101,'category_id':'1','name':'Fixture','epg_channel_id':'one'}])

    def test_request_budget_bounded(self):
        self.enter();s.CURRENT.get()['requests']=32
        with patch.object(s.socket,'socket') as connect:
            self.deny(lambda:s.fetch(self.r.server_url));connect.assert_not_called()
    def test_concurrency_fail_closed(self):
        self.enter();s.SLOTS.acquire();s.SLOTS.acquire()
        try:self.deny(lambda:s.fetch(self.r.server_url))
        finally:s.SLOTS.release();s.SLOTS.release()
    def test_raw_logger_message_and_traceback_are_discarded(self):
        out=io.StringIO();logger=logging.getLogger('fixture-security');handler=logging.StreamHandler(out);logger.addHandler(handler);logger.setLevel(logging.DEBUG)
        try:s.SafeLogger('fixture-security').exception('password=synthetic-secret %s','https://private.invalid/?token=x',exc_info=True)
        finally:logger.removeHandler(handler)
        self.assertNotIn('secret',out.getvalue());self.assertNotIn('private',out.getvalue());self.assertNotIn('Traceback',out.getvalue())
    def test_safe_exception_does_not_preserve_remote_body(self):
        with self.assertRaises(s.Denied) as caught:
            with s.safe_errors():raise RuntimeError('synthetic-secret provider reply')
        self.assertEqual(str(caught.exception),'provider_security_refused_no_retry');self.assertTrue(caught.exception.__suppress_context__)
    def test_private_media_metadata_URL_encodes_credentials_and_validates_ID(self):
        value=s.media_url(self.r.server_url,'user/name','secret/?',101)
        self.assertIn('/user%2Fname/secret%2F%3F/101.ts',value)
        self.deny(lambda:s.media_url(self.r.server_url,'u','p','../escape'))

    def test_remote_artwork_is_removed_without_inventing_guide_content(self):
        raw=b'<tv><channel id="one"><display-name>Fixture</display-name><icon src="http://127.0.0.1/private"/></channel><programme channel="one"><title>Original title</title><icon src="https://artwork.invalid/token"/></programme></tv>'
        result=s.clean_xmltv(raw)
        self.assertNotIn(b'127.0.0.1',result);self.assertNotIn(b'artwork.invalid',result)
        self.assertIn(b'Original title',result);self.assertEqual(s.validate_xmltv(result),{'one'})

    def test_XMLTV_well_formed_ids(self):self.assertEqual(s.validate_xmltv(b'<tv><channel id="one"/><programme channel="one"><title>Fixture</title></programme></tv>'),{'one'})
    def test_XMLTV_external_and_internal_entities_refused(self):
        for raw in (b'<!DOCTYPE tv SYSTEM "file:///private"><tv/>',b'<!DOCTYPE tv [<!ENTITY x "secret">]><tv>&x;</tv>',b'<tv>&notdefined;</tv>'):
            self.deny(lambda:s.validate_xmltv(raw))
    def test_XMLTV_malformed_root_duplicate_or_encoding_refused(self):
        for raw in (b'<tv>',b'<html/>',b'<tv><channel id="x"/><channel id="x"/></tv>',b'\xff\xfe<tv/>'):
            self.deny(lambda:s.validate_xmltv(raw))
    def test_XMLTV_depth_resource_limit(self):self.deny(lambda:s.validate_xmltv(b'<tv>'+b'<a>'*65+b'</a>'*65+b'</tv>'))
    def test_XMLTV_archive_and_size_refused(self):
        self.deny(lambda:s.validate_xmltv(b'\x1f\x8bcompressed'))
        with patch.object(s,'MAX_BYTES',16):self.deny(lambda:s.validate_xmltv(b'<tv>'+b' '*40+b'</tv>'))
    def test_XMLTV_source_identity_binding(self):
        source=types.SimpleNamespace(source_type='xmltv',url='https://guide.example.invalid/guide.xml?token=synthetic',custom_properties=self.r.custom_properties)
        self.policy['epg_url_sha256']=s.digest(source.url)
        self.assertEqual(s.resource_key(source),self.key)
        source.url='https://foreign.invalid/guide.xml';self.deny(lambda:s.resource_key(source))
    def test_valid_XMLTV_cache_is_private_atomic_and_native_source_is_updated(self):
        self.enter('epg')
        source=types.SimpleNamespace(id=7,url='https://guide.example.invalid/guide.xml',source_type='xmltv',custom_properties=self.r.custom_properties,save=MagicMock(),is_active=True)
        self.policy['epg_url_sha256']=s.digest(source.url)
        with tempfile.TemporaryDirectory() as tmp:
            conf=types.ModuleType('django.conf');conf.settings=types.SimpleNamespace(MEDIA_ROOT=tmp)
            with patch.dict(sys.modules,{'django':types.ModuleType('django'),'django.conf':conf}),patch.object(s,'fetch',return_value=b'<tv><channel id="one"/></tv>'):
                self.assertTrue(s.xmltv_download(source))
            path=Path(tmp)/'cached_epg/7.xml'
            self.assertEqual(s.validate_xmltv(path.read_bytes()),{'one'})
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(source.file_path,str(path));source.save.assert_called_once_with(update_fields=['file_path','extracted_file_path'])
            self.assertIsNone(source.extracted_file_path)
            self.assertEqual(len(list(path.parent.iterdir())),1)

    def test_crash_retained_partial_is_not_overwritten_or_deleted(self):
        self.enter('epg')
        source=types.SimpleNamespace(id=7,url='https://guide.example.invalid/guide.xml',source_type='xmltv',custom_properties=self.r.custom_properties,save=MagicMock(),is_active=True)
        self.policy['epg_url_sha256']=s.digest(source.url)
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'cached_epg';directory.mkdir();partial=directory/'7.native.partial';partial.write_bytes(b'prior retained evidence')
            conf=types.ModuleType('django.conf');conf.settings=types.SimpleNamespace(MEDIA_ROOT=tmp)
            with patch.dict(sys.modules,{'django':types.ModuleType('django'),'django.conf':conf}),patch.object(s,'fetch',return_value=b'<tv/>'):
                self.deny(lambda:s.xmltv_download(source))
            self.assertEqual(partial.read_bytes(),b'prior retained evidence');source.save.assert_not_called()

    def test_atomic_XMLTV_cache_preserves_old_on_invalid_input(self):
        self.enter('epg')
        source=types.SimpleNamespace(id=7,url='https://guide.example.invalid/guide.xml',source_type='xmltv',custom_properties=self.r.custom_properties,is_active=True)
        self.policy['epg_url_sha256']=s.digest(source.url)
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'cached_epg';directory.mkdir();path=directory/'7.xml';path.write_bytes(b'<tv/>')
            with patch.object(s,'fetch',return_value=b'<tv>'):
                self.deny(lambda:s.xmltv_download(source))
            self.assertEqual(path.read_bytes(),b'<tv/>')


class Policy(unittest.TestCase):
    def setUp(self):
        self.example=json.loads((BASE/'policy.example.json').read_text())
        ns=Path('/proc/self/ns/net').stat();self.key='a'*64
        self.example.update(provider_key=self.key,netns=[ns.st_dev,ns.st_ino],
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),host_netns=[1,1],expires_epoch=time.time()+300)
        for endpoint in self.example['endpoints']:endpoint['ipv4']=['93.184.216.34']
    def call(self):
        try:return policy_interface.validate(self.example,self.key)
        except Exception:raise s.Denied() from None
    def test_trusted_policy_shape_and_current_namespace(self):self.assertEqual(self.call(),self.example)
    def test_untrusted_owner_or_writable_anchor_refused(self):
        # Actual UID1000/ownership/mode access is exercised in run-permissions.sh.
        for owner,mode in [(1000,0o40755),(0,0o40777),(0,0o40700)]:
            st=types.SimpleNamespace(st_uid=owner,st_gid=0,st_mode=mode,st_nlink=2)
            with patch.object(policy_interface.os,'open',return_value=123),patch.object(policy_interface.os,'close'),patch.object(policy_interface.os,'fstat',return_value=st):
                with self.assertRaises(Exception):policy_interface.directory('/synthetic',0o755)
    def test_policy_expiration_wrong_provider_owner_and_boot_refused(self):
        for field,value in [('expires_epoch',0),('provider_key','f'*64),('network_owner','WAN'),('boot_id','old')]:
            original=self.example[field];self.example[field]=value
            with self.assertRaises(s.Denied):self.call()
            self.example[field]=original
    def test_policy_extra_fields_or_duplicate_permissions_refused(self):
        self.example['unexpected']=True
        with self.assertRaises(s.Denied):self.call()
        del self.example['unexpected'];self.example['operations']=['discover','discover']
        with self.assertRaises(s.Denied):self.call()
    def test_policy_cannot_hide_ports_queries_or_private_addresses(self):
        old=copy.deepcopy(self.example['endpoints'])
        for change in [{'port':8443},{'ipv4':['127.0.0.1']},{'path':'/player_api.php?override=true'}]:
            self.example['endpoints']=copy.deepcopy(old);self.example['endpoints'][0].update(change)
            with self.assertRaises(s.Denied):self.call()

    def test_policy_directory_symlink_or_large_file_refused(self):
        # No-follow/open errors and size limits remain fail-closed at the reader.
        with patch.object(policy_interface,'directory',side_effect=OSError('synthetic symlink')):
            with self.assertRaises(t.Refused):policy_interface.Reader('/synthetic').read(self.key)
        st=types.SimpleNamespace(st_mode=0o100644,st_uid=0,st_gid=0,st_nlink=1,st_size=65537)
        stream=MagicMock();stream.__enter__.return_value=stream;stream.fileno.return_value=123
        with patch.object(policy_interface.os,'open',return_value=123),patch.object(policy_interface.os,'fdopen',return_value=stream),patch.object(policy_interface.os,'fstat',return_value=st):
            with self.assertRaises(t.Refused):policy_interface.read(123,'synthetic')


class Destination(unittest.TestCase):
    def approval(self):
        ns=Path('/proc/self/ns/net').stat()
        return {'schema':1,'purpose':'IPTV_METADATA_ONLY','review_reference':'synthetic-only',
                'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'netns':[ns.st_dev,ns.st_ino],
                'expires_epoch':time.time()+300,'endpoints':[{'host':'provider.example.invalid','path':'/player_api.php','ipv4':['93.184.216.34']} ]}
    def authorize(self,approval=None,answers=None,target='https://provider.example.invalid/player_api.php'):
        with patch.object(t,'private_read',return_value=approval or self.approval()),patch.object(t.MetadataHTTPS,'context_checks'),patch.object(t,'resolve',return_value=answers or {'93.184.216.34'}),patch.object(t.MetadataHTTPS,'vpn_route'):
            return t.MetadataHTTPS('synthetic').authorize(target)
    def test_approved_public_destination(self):self.assertEqual(self.authorize()[1],'93.184.216.34')
    def test_DNS_rebinding_and_private_answers_rejected(self):
        for ips in ({'127.0.0.1'},{'10.0.0.1'},{'169.254.169.254'},{'::1'},{'93.184.216.34','8.8.8.8'}):
            with self.assertRaises(t.Refused):self.authorize(answers=ips)
    def test_wrong_actual_namespace_rejected(self):
        a=self.approval();a['netns'][1]+=1
        with self.assertRaises(t.Refused):self.authorize(approval=a)
    def test_expired_approval_rejected(self):
        a=self.approval();a['expires_epoch']=0
        with self.assertRaises(t.Refused):self.authorize(approval=a)
    def test_changed_destination_path_host_port_or_tls_refused(self):
        for target in ('http://provider.example.invalid/player_api.php','https://provider.example.invalid:8443/player_api.php','https://foreign.invalid/player_api.php','https://provider.example.invalid/private'):
            with self.assertRaises(t.Refused):self.authorize(target=target)
    def test_host_wan_route_rejected(self):
        with patch.object(Path,'exists',return_value=True),patch.object(Path,'stat',return_value=types.SimpleNamespace(st_uid=0,st_mode=0o100755)),patch.object(t.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout=b'[{"dev":"eth0"}]')):
            with self.assertRaises(t.Refused):t.MetadataHTTPS.vpn_route('93.184.216.34')
    def test_DNS_does_not_fork_a_Celery_worker(self):
        self.assertNotIn('multiprocessing',(BASE/'runtime/provider_transport.py').read_text())
        self.assertNotIn('getaddrinfo',(BASE/'runtime/provider_dns.py').read_text())
    def test_DNS_query_accepts_pinned_A_records(self):
        def reply(query):
            return query[:2]+struct.pack('!HHHHH',0x8180,1,1,0,0)+query[12:]+b'\xc0\x0c'+struct.pack('!HHIH',1,1,60,4)+socket.inet_aton('93.184.216.34')
        sock=MagicMock();sock.__enter__.return_value=sock;sock.send.side_effect=lambda q:setattr(sock,'packet',q);sock.recv.side_effect=lambda _:reply(sock.packet)
        with patch.object(dns.socket,'socket',return_value=sock):self.assertEqual(dns.resolve('provider.example.invalid'),{'93.184.216.34'})
        self.assertEqual(sock.connect.call_args.args[0],('127.0.0.1',53));self.assertEqual(sock.send.call_count,1)
    def test_DNS_truncated_or_wrong_transaction_refused(self):
        sock=MagicMock();sock.__enter__.return_value=sock;sock.recv.return_value=b'\0'*12
        with patch.object(dns.socket,'socket',return_value=sock),self.assertRaises(ValueError):dns.resolve('provider.example.invalid')


class Patches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Source inputs are retained official files; source pins fail on drift.
        cls.source=Path(os.environ.get('DISPATCHARR_PINNED_SOURCE','/tmp/dispatcharr-native-hardening-input'))
        cls.originals={n:(cls.source/n).read_text() for n in prepare.PINS}
        cls.patched={n:prepare.change(n,v) for n,v in cls.originals.items()}
    def test_exact_source_and_deterministic_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'new';hashes=prepare.prepare(self.source,output)
            self.assertEqual(hashes,json.loads((BASE/'output-hashes.json').read_text()))
            self.assertEqual((output/'server.patch').read_bytes(),(BASE/'server.patch').read_bytes())
    def test_unified_patch_applies_to_exact_sources_and_matches_all_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree=Path(tmp)/'source';shutil.copytree(self.source,tree)
            with (BASE/'server.patch').open('rb') as patchfile:
                result=subprocess.run(['patch','--batch','--forward','-p1','-d',str(tree)],stdin=patchfile,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            for name,wanted in json.loads((BASE/'output-hashes.json').read_text()).items():
                self.assertEqual(hashlib.sha256((tree/name).read_bytes()).hexdigest(),wanted)

    def test_drift_refused_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'src';source.mkdir();output=Path(tmp)/'out'
            name=next(iter(prepare.PINS));p=source/name;p.parent.mkdir(parents=True);p.write_text('unreviewed')
            with self.assertRaises(ValueError):prepare.prepare(source,output)
            self.assertFalse(output.exists())
    def test_every_output_parses(self):
        for text in self.patched.values():ast.parse(text)
    def test_all_XC_client_requests_use_pinned_transport(self):
        tree=ast.parse(self.patched['core/xtream_codes.py'])
        n=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_make_request')
        self.assertIn('xc_get',ast.unparse(n));self.assertNotIn('requests.Session',self.patched['core/xtream_codes.py'])
        self.assertNotIn('max_retries=3',self.patched['core/xtream_codes.py'])
    def test_patched_XC_client_authenticates_and_discovers_without_requests_session(self):
        code=self.patched['core/xtream_codes.py'];r,key=resource()
        with patch.dict(sys.modules,{'core':types.ModuleType('core'),'core.provider_security':s,'requests':types.ModuleType('requests')}):
            env={'__name__':'synthetic_native_client'};exec(compile(code,'prepared-XC','exec'),env)
        with patch.dict(sys.modules,{'core':types.ModuleType('core'),'core.provider_security':s}):
            client=env['Client'](r.server_url,r.username,'synthetic-secret')
        approval={'operations':['discover','refresh'],'policy_review_sha256':'a'*64}
        def data(target):
            return b'[{"stream_id":101,"name":"Fixture","stream_icon":"http://127.0.0.1"}]' if 'action=' in target else b'{"user_info":{"auth":1}}'
        with patch.object(s,'policy',return_value=approval),patch.object(s,'Readiness'),s.job('refresh',r,True),patch.object(s,'fetch',side_effect=data) as fetch:
            result=client.get_all_live_streams()
        self.assertEqual(result,[{'stream_id':101,'name':'Fixture'}]);self.assertEqual(fetch.call_count,2)
        self.assertEqual(client.get_stream_url(101),'https://provider.example.invalid/live/synthetic-user/synthetic-secret/101.ts')
        client.close()

    def test_creation_requires_explicit_discovery(self):
        text=self.patched['apps/m3u/api_views.py']
        self.assertIn('request.data.get("metadata_discovery") is True',text)
        self.assertIn('with job("discover", M3UAccount.objects.get(id=account_id), True):',text)
    def test_worker_defaults_deny_ambient_or_periodic_requests(self):
        self.assertIn('operator_requested=False',self.patched['apps/m3u/tasks.py'])
        self.assertIn('with job("refresh",',self.patched['apps/m3u/tasks.py'])
        self.assertIn('with job("epg",',self.patched['apps/epg/tasks.py'])
        self.assertIn('operator_requested=True',self.patched['apps/m3u/api_views.py'])
        self.assertIn('operator_requested=True',self.patched['apps/epg/api_views.py'])
    def test_manual_tasks_keep_time_limits_and_disable_delivery_retries(self):
        for file,name,seconds in [('apps/m3u/tasks.py','refresh_single_m3u_account',3600),('apps/epg/tasks.py','refresh_epg_data',14400)]:
            fn=next(n for n in ast.walk(ast.parse(self.patched[file])) if isinstance(n,ast.FunctionDef) and n.name==name)
            options={k.arg:ast.literal_eval(k.value) for k in fn.decorator_list[0].keywords}
            self.assertEqual(options['time_limit'],seconds);self.assertIs(options['acks_late'],False)
            self.assertIs(options['reject_on_worker_lost'],False);self.assertEqual(options['autoretry_for'],())

    def test_no_raw_print_diagnostic_or_profile_job_queue(self):
        text=self.patched['apps/m3u/tasks.py']
        self.assertNotIn('refresh_account_profiles.delay(account.id)',text)
        fn=next(n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.FunctionDef) and n.name=='check_field_lengths')
        self.assertEqual(ast.unparse(fn.body[0]),'return None')

    def test_periodic_remote_sources_and_XC_disabled(self):
        self.assertIn('instance.account_type != "XC"',self.patched['apps/m3u/signals.py'])
        self.assertIn('instance.is_active and not remote(instance)',self.patched['apps/epg/signals.py'])
        self.assertIn('and not remote(instance)',self.patched['apps/epg/signals.py'])
    def test_automatic_profile_tasks_have_no_network_or_model_calls(self):
        for name in ('refresh_account_profiles','refresh_account_info'):
            fn=next(n for n in ast.walk(ast.parse(self.patched['apps/m3u/tasks.py'])) if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(len(fn.body),1);self.assertIsInstance(fn.body[0],ast.Return)
    def test_remote_XMLTV_download_is_intercepted_before_legacy_requests(self):
        fn=next(n for n in ast.walk(ast.parse(self.patched['apps/epg/tasks.py'])) if isinstance(n,ast.FunctionDef) and n.name=='fetch_xmltv')
        self.assertEqual(ast.unparse(fn.body[0]),'if source.url:\n    return xmltv_download(source)')
    def test_native_XML_parsers_have_no_external_entity_or_recovery(self):
        tree=ast.parse(self.patched['apps/epg/tasks.py'])
        parsers=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='etree' and n.func.attr in ('iterparse','XMLParser')]
        self.assertGreaterEqual(len(parsers),4)
        for parser in parsers:
            flags={k.arg:ast.literal_eval(k.value) for k in parser.keywords if k.arg in ('resolve_entities','load_dtd','recover','huge_tree','no_network')}
            self.assertEqual(flags,{'resolve_entities':False,'load_dtd':False,'recover':False,'huge_tree':False,'no_network':True})
    def test_actual_worker_entry_refuses_periodic_call_before_lock_or_network(self):
        fn=copy.deepcopy(next(n for n in ast.walk(ast.parse(self.patched['apps/m3u/tasks.py'])) if isinstance(n,ast.FunctionDef) and n.name=='refresh_single_m3u_account'))
        fn.decorator_list=[];r,key=resource();lock=MagicMock()
        env={'job':s.job,'M3UAccount':types.SimpleNamespace(objects=types.SimpleNamespace(get=lambda **kw:r)), 'acquire_task_lock':lock}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'prepared-task','exec'),env)
        with self.assertRaises(s.Denied):env[fn.name](7)
        lock.assert_not_called()

    def test_actual_profile_tasks_do_not_authenticate_or_query_database(self):
        for name in ('refresh_account_profiles','refresh_account_info'):
            fn=copy.deepcopy(next(n for n in ast.walk(ast.parse(self.patched['apps/m3u/tasks.py'])) if isinstance(n,ast.FunctionDef) and n.name==name));fn.decorator_list=[]
            env={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'prepared-profile','exec'),env)
            self.assertEqual(env[name](999),'automatic_native_profile_refresh_disabled')

    def test_actual_account_creation_default_is_network_silent(self):
        tree=ast.parse(self.patched['apps/m3u/api_views.py'])
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='M3UAccountViewSet')
        fn=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='create'));fn.decorator_list=[]
        # The native code's super().create returns an already committed account.
        class Parent:
            def create(self,*args,**kwargs):return types.SimpleNamespace(data={'account_type':'XC','id':7})
        fake=ast.ClassDef(name='Candidate',bases=[ast.Name(id='Parent',ctx=ast.Load())],keywords=[],body=[fn],decorator_list=[])
        env={'Parent':Parent,'M3UAccount':types.SimpleNamespace(Types=types.SimpleNamespace(XC='XC')),
             'send_websocket_update':lambda *a,**k:None,'refresh_m3u_groups':MagicMock(),'job':MagicMock()}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fake],type_ignores=[])),'prepared-create','exec'),env)
        utils=types.ModuleType('core.utils');utils.send_websocket_update=lambda *a,**k:None
        with patch.dict(sys.modules,{'core':types.ModuleType('core'),'core.utils':utils}):
            env['Candidate']().create(types.SimpleNamespace(FILES={},data={}))
        env['job'].assert_not_called();env['refresh_m3u_groups'].assert_not_called()

    def test_channel_signal_programme_task_is_cache_only_for_remote_source(self):
        fn=next(n for n in ast.walk(ast.parse(self.patched['apps/epg/tasks.py'])) if isinstance(n,ast.FunctionDef) and n.name=='parse_programs_for_tvg_id')
        self.assertIn('automatic_remote_programme_parse_disabled',ast.unparse(fn.body[:2]))
    def test_remote_import_does_not_schedule_DVR_or_auto_apply_artwork(self):
        text=self.patched['apps/epg/tasks.py']
        self.assertIn('if not remote(source): evaluate_series_rules.delay()',text)
        self.assertIn('if not remote(source): maybe_auto_apply_epg_logos(source)',text)
        self.assertIn('"tvg-logo": ""',self.patched['apps/m3u/tasks.py'])

    def test_no_guard_relay_Docker_or_systemd_file_is_patched(self):
        self.assertEqual(set(self.patched),set(prepare.PINS))
        self.assertFalse(any('guard' in name or 'relay' in name or name.endswith(('.service','.yaml')) for name in self.patched))

if __name__=='__main__':unittest.main()
