"""Offline socket-event/checkpoint fixtures. No Docker, Django or provider calls."""
import ast
import io
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import runtime_diagnostics as d
import runtime_test as harness
import run_runtime

TEST='Integration.test_02_default_inactive_account_creation_has_no_provider_requests'


def connect(address,family=socket.AF_INET):return d.address_info('socket.connect',(types.SimpleNamespace(family=family),address))


class Classification(unittest.TestCase):
    def test_pathname_unix_is_classified_and_legacy_allowed(self):
        v=connect('/synthetic/private.sock',socket.AF_UNIX)
        self.assertEqual(v['destination_class'],'unix_ipc');self.assertTrue(v['legacy_allowed']);self.assertNotIn('private.sock',json.dumps(v))
    def test_abstract_unix_is_local_but_still_denied(self):
        for value in ['\0secret_socket',b'\0secret_socket']:
            v=connect(value,socket.AF_UNIX);self.assertEqual(v['destination_class'],'unix_ipc');self.assertFalse(v['legacy_allowed'])
    def test_bytes_unix_is_classified_without_broadening_permission(self):
        v=connect(b'/synthetic/private.sock',socket.AF_UNIX);self.assertEqual(v['destination_class'],'unix_ipc');self.assertFalse(v['legacy_allowed'])
    def test_IPv4_loopback_and_database_hint(self):
        v=connect(('127.0.0.1',5432));self.assertTrue(v['legacy_allowed']);self.assertEqual(v['local_service'],'postgresql_fixture')
        self.assertNotIn('127.0.0.1',json.dumps(v));self.assertNotIn('5432',json.dumps(v))
    def test_IPv6_loopback_and_Redis_hint(self):
        v=connect(('::1',6379,0,0),socket.AF_INET6);self.assertTrue(v['legacy_allowed']);self.assertEqual(v['local_service'],'redis_fixture')
    def test_local_HTTP_clients_keep_exact_old_literals(self):
        for port in [443,5656]:
            self.assertTrue(connect(('127.0.0.1',port))['legacy_allowed'])
        self.assertTrue(d.address_info('socket.getaddrinfo',('localhost',443,0,0,0))['legacy_allowed'])
    def test_bytes_loopback_classifies_local_but_remains_denied(self):
        v=connect((b'127.0.0.1',6379));self.assertEqual(v['destination_class'],'loopback');self.assertFalse(v['legacy_allowed'])
    def test_expanded_and_mapped_loopback_still_denied(self):
        for host in ['0:0:0:0:0:0:0:1','::ffff:127.0.0.1']:
            v=connect((host,6379),socket.AF_INET6);self.assertEqual(v['destination_class'],'loopback');self.assertFalse(v['legacy_allowed'])
        self.assertFalse(connect(('127.0.0.2',443))['legacy_allowed'])
    def test_private_and_link_local_never_escape(self):
        for host in ['10.10.20.30','192.168.1.1','169.254.169.254']:
            v=connect((host,443));self.assertEqual(v['destination_class'],'private');self.assertFalse(v['legacy_allowed']);self.assertNotIn(host,json.dumps(v))
    def test_public_destination_is_classified_and_denied(self):
        v=connect(('8.8.8.8',443));self.assertEqual(v['destination_class'],'public');self.assertFalse(v['legacy_allowed'])
    def test_unknown_hostname_is_never_resolved_or_logged(self):
        value='credentials.provider.invalid'
        with patch.object(socket,'getaddrinfo',side_effect=AssertionError('must not resolve')):
            v=d.address_info('socket.getaddrinfo',(value,443,0,0,0))
        self.assertEqual(v['destination_class'],'unknown');self.assertFalse(v['legacy_allowed']);self.assertNotIn(value,json.dumps(v))
    def test_malformed_shapes_fail_closed(self):
        for value in [None,(),('127.0.0.1',),('127.0.0.1','secret'),('/not-a-TCP-host',443),{'host':'secret'},b'\xff']:
            v=connect(value);self.assertFalse(v['legacy_allowed'])
        self.assertFalse(d.address_info('socket.connect',())['legacy_allowed'])
    def test_local_kernel_socket_classification_does_not_authorize_it(self):
        v=connect((0,0),getattr(socket,'AF_NETLINK',999));self.assertFalse(v['legacy_allowed']);self.assertEqual(v['destination_class'],'unknown');self.assertEqual(v['address_form'],'kernel_ipc')
    def test_ipv6_private_and_unspecified(self):
        self.assertEqual(connect(('fd00::1',443),socket.AF_INET6)['destination_class'],'private')
        for address,family in [('0.0.0.0',socket.AF_INET),('::',socket.AF_INET6)]:self.assertFalse(connect((address,443),family)['legacy_allowed'])


class Evidence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'evidence';self.diag=d.Diagnostics(self.root,'application',tests=d.TEST_IDS)
    def test_migration_checkpoint_is_atomic_restricted_and_loadable(self):
        self.diag.begin('migrations');self.diag.complete('migrations',{'migration_count':184,'migration_fingerprint':'a'*32})
        file=self.root/'snapshot.json';self.assertEqual(file.stat().st_mode&0o777,0o600)
        r=d.load_snapshot(self.root,os.geteuid());self.assertEqual(r['last_checkpoint']['details']['migration_count'],184)
    def test_begin_later_phase_cannot_infer_completion(self):
        self.diag.complete('django_setup',{'django_version':'6.0.9'});self.diag.begin('migrations')
        r=d.load_snapshot(self.root,os.geteuid());self.assertEqual(r['last_checkpoint']['phase'],'django_setup');self.assertNotIn('application:migrations',r['completed'])
    def test_actual_task_count_checkpoint_needs_explicit_completion(self):
        self.diag.begin('task_execution',TEST)
        self.assertIsNone(d.load_snapshot(self.root,os.geteuid())['last_checkpoint'])
        self.diag.complete('task_execution',{'actual_completed_tasks':1})
        self.assertEqual(d.load_snapshot(self.root,os.geteuid())['last_checkpoint']['details']['actual_completed_tasks'],1)
    def test_checkpoint_order_uses_sequence_not_dictionary_position(self):
        self.diag.complete('task_execution',{'actual_completed_tasks':1});self.diag.complete('native_api',{'completed_tests':1});self.diag.complete('task_execution',{'actual_completed_tasks':2})
        self.assertEqual(d.load_snapshot(self.root,os.geteuid())['last_checkpoint']['phase'],'task_execution')
    def test_refusal_contains_phase_test_role_UID_and_reason(self):
        self.diag.begin('native_api',TEST);exitcodes=[]
        self.diag.audit('socket.connect',(types.SimpleNamespace(family=socket.AF_INET),('8.8.8.8',443)),exitcodes.append)
        self.assertEqual(exitcodes,[86]);r=d.load_snapshot(self.root,os.geteuid())['last_refusal']
        self.assertEqual(r['phase'],'native_api');self.assertEqual(r['test_id'],TEST);self.assertEqual(r['uid'],os.geteuid());self.assertEqual(r['reason'],'public_network_destination_denied')
    def test_allowed_operation_has_no_refusal_or_termination(self):
        exits=[];self.diag.audit('socket.connect',(types.SimpleNamespace(family=socket.AF_INET),('127.0.0.1',6379)),exits.append)
        self.assertEqual(exits,[]);self.assertFalse((self.root/'snapshot.json').exists())
    def test_credentials_urls_bodies_environment_and_locals_are_not_captured(self):
        password='TOP_SECRET_PASSWORD';token='PRIVATE_TOKEN_VALUE';url='https://user:TOP_SECRET_PASSWORD@private.invalid/?token=PRIVATE_TOKEN_VALUE'
        try:raise ValueError(url)
        except ValueError as error:self.diag.exception(error,reason=url,tb=error.__traceback__)
        self.diag.context('secret_phase_'+password,'secret_test_'+token)
        self.diag.record('exception',details={'password':password,'token':token,'request_body':url,'environment':dict(os.environ),'django_version':password},reason=url)
        raw=(self.root/'snapshot.json').read_text()
        for secret in [password,token,url,'private.invalid','request_body']:self.assertNotIn(secret,raw)
    def test_generated_URL_filename_and_source_line_are_redacted(self):
        try:exec(compile("raise ValueError('PRIVATE_TOKEN_VALUE')",'https://user:secret@private.invalid/?token=private','exec'),{})
        except ValueError as error:self.diag.exception(error,tb=error.__traceback__)
        raw=(self.root/'snapshot.json').read_text();self.assertNotIn('PRIVATE_TOKEN_VALUE',raw);self.assertNotIn('private.invalid',raw);self.assertIn('redacted-file',raw)
    def test_unknown_detail_and_stack_keys_never_escape(self):
        self.diag.record('exception',network={'destination':'private.invalid','password':'secret','family':'AF_INET'},stack=[{'file':'api.py','function':'call','line':1,'locals':'TOP_SECRET'}],reason='test_error')
        raw=(self.root/'snapshot.json').read_text();self.assertNotIn('private.invalid',raw);self.assertNotIn('TOP_SECRET',raw);self.assertNotIn('password',raw)
    def test_diagnostics_failure_still_terminates_and_emits_classified_record(self):
        read,write=os.pipe();self.addCleanup(os.close,read);self.addCleanup(os.close,write);self.diag.emit_fd=write
        with patch.object(self.diag,'_persist',side_effect=OSError('SECRET')):
            exits=[];self.diag.audit('socket.connect',(types.SimpleNamespace(family=socket.AF_INET),('8.8.8.8',443)),exits.append)
        value=json.loads(os.read(read,8192));self.assertEqual(value['network']['destination_class'],'public');self.assertEqual(value['persistence'],'failed');self.assertEqual(exits,[86])
    def test_limit_still_emits_refusal_without_allowing_operation(self):
        read,write=os.pipe();self.addCleanup(os.close,read);self.addCleanup(os.close,write);self.diag.emit_fd=write;self.diag.state['sequence']=d.MAX_RECORDS
        exits=[];self.diag.audit('socket.connect',(types.SimpleNamespace(family=socket.AF_INET),('8.8.8.8',443)),exits.append)
        self.assertEqual(json.loads(os.read(read,8192))['kind'],'refusal');self.assertEqual(exits,[86])
    def test_snapshot_survives_abnormal_exit_with_last_checkpoint(self):
        code='''import sys,types,socket
sys.path.insert(0,sys.argv[1])
import runtime_diagnostics as d
v=d.Diagnostics(sys.argv[2],'application',emit_fd=1,tests=d.TEST_IDS)
v.complete('migrations',{'migration_count':184,'migration_fingerprint':'b'*32})
v.begin('native_api',next(iter(d.TEST_IDS)))
v.audit('socket.connect',(types.SimpleNamespace(family=socket.AF_INET),('8.8.8.8',443)))
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(HERE),str(Path(self.tmp.name)/'child')],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,86);r=d.load_snapshot(Path(self.tmp.name)/'child',os.geteuid());self.assertEqual(r['last_checkpoint']['phase'],'migrations');self.assertEqual(r['last_refusal']['network']['destination_class'],'public')
        self.assertEqual(d.recover_records(result.stdout)['last_checkpoint']['details']['migration_count'],184)
    def test_pid1_style_kill_still_leaves_emitted_checkpoint_without_final_result(self):
        code="import sys,os,signal;sys.path.insert(0,sys.argv[1]);import runtime_diagnostics as d;v=d.Diagnostics(sys.argv[2],'supervisor',emit_fd=1);v.complete('postgresql',{'postgres_major':17});os.kill(os.getpid(),signal.SIGKILL)"
        result=subprocess.run([sys.executable,'-B','-c',code,str(HERE),str(Path(self.tmp.name)/'killed')],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,-9);recovered=d.recover_records(result.stdout)
        self.assertEqual(recovered['last_checkpoint']['phase'],'postgresql');self.assertNotIn('supervisor:final_acceptance',recovered['completed'])
    def test_snapshot_rejects_symlink_and_wrong_permissions(self):
        self.diag.complete('redis',{'redis_ping':True});file=self.root/'snapshot.json';file.chmod(0o644)
        with self.assertRaises(ValueError):d.load_snapshot(self.root,os.geteuid())
        file.unlink();file.symlink_to('/dev/null')
        with self.assertRaises(OSError):d.load_snapshot(self.root,os.geteuid())
    def test_parent_incomplete_does_not_hide_specific_refusal(self):
        self.diag.complete('migrations',{'migration_count':184});self.diag.audit('socket.connect',(types.SimpleNamespace(family=socket.AF_INET),('8.8.8.8',443)),lambda _:None)
        state=json.loads((self.root/'snapshot.json').read_text());refusal=state['last_failure'];generic={**refusal,'kind':'incomplete','role':'supervisor','reason':'application_process_abnormal'}
        recovered=d.recover_records(json.dumps(refusal)+'\n'+json.dumps(generic));self.assertEqual(recovered['last_refusal']['kind'],'refusal');self.assertEqual(recovered['last_failure']['kind'],'incomplete')
    def test_no_app_result_can_still_recover_durable_checkpoints(self):
        self.diag.complete('migrations',{'migration_count':184});record=json.loads((self.root/'snapshot.json').read_text())['last_checkpoint']
        recovered=d.recover_records('ordinary log\n'+json.dumps(record));self.assertEqual(recovered['last_checkpoint']['phase'],'migrations')
    def test_malformed_log_json_and_unknown_fields_do_not_smuggle_secrets(self):
        lines=['{}','[]','{"dispatcharr_test_diagnostic":1,"role":{}}',json.dumps({d.TAG:1,'role':'application','kind':'checkpoint','phase':'redis','details':{'redis_ping':True,'token':'SECRET'}})]
        self.assertNotIn('SECRET',json.dumps(d.recover_records('\n'.join(lines))))
    def test_final_acceptance_requires_explicit_records_not_later_phase(self):
        value={'success':True,'tests_success':True,'application_exit_code':0,'application_diagnostics':{'completed':{}}}
        self.assertFalse(harness.final_acceptance_ready(value))
        phases=['django_setup','migrations','celery_startup','task_registration','task_execution','native_api','xtream_xmltv','uwsgi','application_suite']
        value['application_diagnostics']['completed']={'application:'+p:{'kind':'checkpoint'} for p in phases}
        self.assertTrue(harness.final_acceptance_ready(value));value['application_exit_code']=86;self.assertFalse(harness.final_acceptance_ready(value))
    def test_unittest_failure_text_is_sanitized(self):
        with patch.object(harness,'DIAG',self.diag):
            runner=unittest.TextTestRunner(stream=io.StringIO(),resultclass=harness.EvidenceResult)
            class Synthetic(unittest.TestCase):
                def runTest(self):raise ValueError('https://private.invalid/TOP_SECRET')
            result=runner.run(Synthetic())
        self.assertEqual(len(result.errors),1);self.assertNotIn('TOP_SECRET',result.errors[0][1]);self.assertNotIn('private.invalid',result.errors[0][1])
    def test_fixture_uses_inherited_descriptor_and_not_raw_child_log(self):
        source=(HERE/'runtime_test.py').read_text();self.assertIn("kwargs['pass_fds']",source);self.assertNotIn("(STATE/'application.log').read_text()",source)
        self.assertIn("DIAG.complete('migrations'",source);self.assertIn("DIAG.complete('celery_startup'",source)
    def test_runner_preserves_prior_attempt_and_has_bounded_log_recovery(self):
        source=(HERE/'run_runtime.py').read_text();self.assertIn('runtime-attempt-',(HERE/'runtime_admission.py').read_text());self.assertIn('admission.Journal(work,attempt_id)',source);self.assertIn('diagnostics.recover_records(logs)',source);self.assertIn("'--log-opt=max-size=1m'",source)
        self.assertIn("parsed['success']=False",source)

if __name__=='__main__':unittest.main()
