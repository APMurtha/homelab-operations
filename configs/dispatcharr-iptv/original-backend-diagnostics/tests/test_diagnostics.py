import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location('diagnostic_'+name,HERE/'candidate'/f'{name}.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
B=load('backend');L=load('lifecycle');L.HERE=HERE/'candidate'
SECRET='SYNTHETIC_PRIVATE_PASSWORD_DO_NOT_RETAIN'

def command_fields():
    return {'command_start_s':100.0,'command_end_s':101.0,'command_elapsed_s':1.0,
            'stdout_bytes':128,'stderr_bytes':0,'output_complete':True,'reply_output_valid':True,**B.compare_brokers()}

def records(fail=None):
    result=[]
    for i,stage in enumerate(B.STAGES):
        result.append({'stage':stage,'event':'start','classification':'checking','elapsed_s':i*2.0})
        fields={'api_sources':{'count':14},'postgres':{'returncode':0},'redis':{},'uwsgi':{'count':2},'celery':{'count':2,'returncode':0,'default_present':True,'dvr_present':True}}[stage]
        if stage=='celery':fields.update(command_fields())
        if fail==stage:
            fields={'api_sources':{'count':14},'postgres':{'returncode':0},'redis':{},'uwsgi':{'count':0},'celery':{'count':1,'returncode':0,'default_present':True,'dvr_present':False}}[stage]
            if stage=='celery':fields.update(command_fields());fields['reply_output_valid']=False
            code={'api_sources':'source_hash_mismatch','postgres':'migration_mismatch','redis':'redis_ping_failed','uwsgi':'fresh_workers_missing','celery':'celery_unclassified_failure'}[stage]
            result.append({'stage':stage,'event':'fail','classification':code,'elapsed_s':i*2.0+1,**fields});break
        result.append({'stage':stage,'event':'pass','classification':'ready','elapsed_s':i*2.0+1,**fields})
    return result

def output(items, generic=False, padded=False):
    text=''.join(B.DIAG_PREFIX+json.dumps(r)+(' '*400 if padded else '')+'\n' for r in items)
    return text+('Backend readiness refused; values withheld.\n' if generic else '')

def capture(text, code=0, stdout='', timeout=2):
    script='import sys;sys.stderr.write('+repr(text)+');sys.stderr.flush();sys.stdout.write('+repr(stdout)+');sys.stdout.flush();sys.exit('+str(code)+')'
    return L._capture_backend([sys.executable,'-c',script],timeout)

class BackendFixture:
    def __init__(self):
        self.files={str(Path('/app')/f'f{i}.py'):b'code' for i in range(14)}
        self.keys=[f'live:worker:{i}:heartbeat' for i in [21,22]]
        self.now=1000;self.redis_error=None;self.ping=True;self.value='999';self.ttl=10;self.commands=[]
        self.pg_code=0;self.pg_stdout='184:b00f51e91c5b882cd84d3b2579d074ca\n';self.pg_error=None
        self.celery_code=0;self.celery_stdout=json.dumps({'default@fixture':{'ok':'pong'},'dvr@fixture':{'ok':'pong'}});self.celery_error=None;self.celery_stderr=''
        self.pins={'files':{f'f{i}.py':hashlib.sha256(b'code').hexdigest() for i in range(14)}}
        self.file_error=None
    def Path(self,value):
        fixture=self
        class FakePath:
            def __init__(self,value):self.value=str(value)
            def __truediv__(self,value):return FakePath(self.value+'/'+str(value))
            def read_text(self):
                if self.value=='/opt/permanent/api-source-pins.json':return json.dumps(fixture.pins)
                if self.value.startswith('/proc/'):return 'uwsgi\n'
                raise FileNotFoundError(SECRET)
            def read_bytes(self):
                if fixture.file_error:raise fixture.file_error
                return fixture.files[self.value]
        return FakePath(value)
    def run(self,args,**kwargs):
        self.commands.append((args,kwargs))
        if args[0]=='psql':
            if self.pg_error:raise self.pg_error
            return types.SimpleNamespace(returncode=self.pg_code,stdout=self.pg_stdout,stderr=SECRET)
        if self.celery_error:raise self.celery_error
        return types.SimpleNamespace(returncode=self.celery_code,stdout=self.celery_stdout,stderr=self.celery_stderr,complete=max(len(self.celery_stdout.encode()),len(self.celery_stderr.encode()))<=B.OUTPUT_LIMIT,stdout_bytes=min(B.OUTPUT_LIMIT+1,len(self.celery_stdout.encode())),stderr_bytes=min(B.OUTPUT_LIMIT+1,len(self.celery_stderr.encode())))
    def Redis(self,**kwargs):
        fixture=self
        class R:
            def ping(self):
                if fixture.redis_error:raise fixture.redis_error
                return fixture.ping
            def scan_iter(self,**kw):return iter(fixture.keys)
            def get(self,key):return fixture.value
            def ttl(self,key):return fixture.ttl
        return R()
    def execute(self):
        stream=io.StringIO();error=None;clock=itertools.count(0,.001)
        with patch.object(B,'Path',self.Path),patch.object(B.subprocess,'run',self.run),patch.object(B,'celery_capture',side_effect=self.run),patch.object(B.time,'time',return_value=self.now),patch.object(B.time,'monotonic',side_effect=lambda:next(clock)),patch.dict(sys.modules,{'redis':types.SimpleNamespace(Redis=self.Redis)}),patch.dict(os.environ,{'POSTGRES_PASSWORD':SECRET,'REDIS_PASSWORD':SECRET}),contextlib.redirect_stderr(stream):
            try:B.check()
            except Exception as e:error=e
        value=stream.getvalue();parsed=B.RecordStream()
        for line in value.splitlines():
            assert line.startswith(B.DIAG_PREFIX)
            parsed.append(line[len(B.DIAG_PREFIX):].encode())
        assert SECRET not in value
        return parsed.records,error,value

class BackendTests(unittest.TestCase):
    def assertFailure(self,f,stage,code):
        result,error,text=f.execute();self.assertIsNotNone(error);self.assertEqual(result[-1]['stage'],stage);self.assertEqual(result[-1]['event'],'fail');self.assertEqual(result[-1]['classification'],code);self.assertNotIn(SECRET,text)
    def test_all_five_successful_stages(self):
        f=BackendFixture();r,e,_=f.execute();self.assertIsNone(e);self.assertEqual([(x['stage'],x['event']) for x in r],[(s,event) for s in B.STAGES for event in ['start','pass']]);self.assertEqual(len(f.commands),2)
    def test_source_mismatch(self):
        f=BackendFixture();f.files['/app/f0.py']=b'wrong';self.assertFailure(f,'api_sources','source_hash_mismatch')
    def test_source_permission(self):
        f=BackendFixture();f.file_error=PermissionError(SECRET);self.assertFailure(f,'api_sources','file_permission')
    def test_source_missing(self):
        f=BackendFixture();f.file_error=FileNotFoundError(SECRET);self.assertFailure(f,'api_sources','file_missing')
    def test_postgres_command_error(self):
        f=BackendFixture();f.pg_code=2;self.assertFailure(f,'postgres','postgres_command_failed')
    def test_migration_mismatch(self):
        f=BackendFixture();f.pg_stdout=SECRET;self.assertFailure(f,'postgres','migration_mismatch')
    def test_postgres_timeout(self):
        f=BackendFixture();f.pg_error=subprocess.TimeoutExpired(SECRET,15);self.assertFailure(f,'postgres','subprocess_timeout')
    def test_Redis_ping_failure(self):
        f=BackendFixture();f.ping=False;self.assertFailure(f,'redis','redis_ping_failed')
    def test_Redis_authentication_failure(self):
        f=BackendFixture();T=type('AuthenticationError',(Exception,),{'__module__':'redis.exceptions'});f.redis_error=T(SECRET);self.assertFailure(f,'redis','redis_authentication_failed')
    def test_Redis_connection_failure(self):
        f=BackendFixture();T=type('ConnectionError',(Exception,),{'__module__':'redis.exceptions'});f.redis_error=T(SECRET);self.assertFailure(f,'redis','redis_connection_failed')
    def test_Redis_timeout(self):
        f=BackendFixture();T=type('TimeoutError',(Exception,),{'__module__':'redis.exceptions'});f.redis_error=T(SECRET);self.assertFailure(f,'redis','redis_timeout')
    def test_missing_uWSGI_heartbeat(self):
        f=BackendFixture();f.keys=f.keys[:1];self.assertFailure(f,'uwsgi','fresh_workers_missing')
    def test_stale_uWSGI_heartbeat(self):
        f=BackendFixture();f.value='960';self.assertFailure(f,'uwsgi','fresh_workers_missing')
    def test_expired_heartbeat(self):
        f=BackendFixture();f.ttl=-1;self.assertFailure(f,'uwsgi','fresh_workers_missing')
    def test_future_heartbeat(self):
        f=BackendFixture();f.value='1001';self.assertFailure(f,'uwsgi','fresh_workers_missing')
    def test_malformed_heartbeat(self):
        f=BackendFixture();f.value=SECRET;self.assertFailure(f,'uwsgi','fresh_workers_missing')
    def test_worker_count_exceeded(self):
        f=BackendFixture();f.keys=[f'live:worker:{i}:heartbeat' for i in range(18)];self.assertFailure(f,'uwsgi','worker_count_exceeded')
    def test_missing_default(self):
        f=BackendFixture();f.celery_stdout=json.dumps({'dvr@fixture':{'ok':'pong'}});self.assertFailure(f,'celery','celery_default_missing')
    def test_missing_DVR(self):
        f=BackendFixture();f.celery_stdout=json.dumps({'default@fixture':{'ok':'pong'}});self.assertFailure(f,'celery','celery_dvr_missing')
    def test_no_Celery_roles(self):
        f=BackendFixture();f.celery_stdout=SECRET;self.assertFailure(f,'celery','celery_unclassified_failure')
    def test_Celery_extra_reply(self):
        f=BackendFixture();f.celery_stdout=json.dumps({'default@fixture':{'ok':'pong'},'default@duplicate':{'ok':'pong'},'dvr@fixture':{'ok':'pong'}});self.assertFailure(f,'celery','celery_unclassified_failure')
    def test_Celery_command_failure(self):
        f=BackendFixture();f.celery_code=1;self.assertFailure(f,'celery','celery_unclassified_failure')
    def test_Celery_timeout(self):
        f=BackendFixture();f.celery_error=subprocess.TimeoutExpired(SECRET,40);self.assertFailure(f,'celery','subprocess_timeout')
    def test_unexpected_exception_redacted(self):
        f=BackendFixture();f.redis_error=RuntimeError(SECRET);self.assertFailure(f,'redis','unexpected_exception')
    def test_original_generic_main_failure(self):
        tree=ast.parse((HERE/'candidate/backend.py').read_text());main=next(n for n in tree.body if isinstance(n,ast.If))
        def failed():raise RuntimeError(SECRET)
        with self.assertRaises(SystemExit) as error:exec(compile(ast.Module(body=[main],type_ignores=[]),'main','exec'),{'__name__':'__main__','check':failed})
        self.assertEqual(str(error.exception),'Backend readiness refused; values withheld.')

class ProtocolTests(unittest.TestCase):
    def test_success_capture(self):self.assertEqual(capture(output(records()))['reason'],'accepted')
    def test_each_stage_failure_same_invocation(self):
        for stage in B.STAGES:
            with self.subTest(stage=stage):
                r=capture(output(records(stage),True),1);self.assertEqual(r['reason'],'backend_stage_failed');self.assertEqual(r['records'][-1]['stage'],stage)
    def test_failed_stage_cannot_be_success_exit(self):self.assertNotEqual(capture(output(records('redis')),0)['reason'],'accepted')
    def test_complete_records_cannot_hide_failed_process(self):self.assertNotEqual(capture(output(records()),1)['reason'],'accepted')
    def test_launch_error_no_records(self):
        with patch.object(L.subprocess,'Popen',side_effect=FileNotFoundError(SECRET)):
            r=L._capture_backend(['not-a-real-command']);self.assertEqual(r['reason'],'launch_failed');self.assertEqual(r['boundary'],'before_first_diagnostic');self.assertNotIn(SECRET,json.dumps(r))
    def test_process_exit_before_first_record(self):
        r=capture('',1);self.assertEqual(r['reason'],'launch_failed_before_first_diagnostic');self.assertFalse(r['producer_entered'])
    def test_stdout_credentials_rejected(self):
        r=capture('',1,stdout=SECRET);self.assertEqual(r['reason'],'unexpected_output');self.assertNotIn(SECRET,json.dumps(r))
    def test_stderr_credentials_rejected(self):
        r=capture(SECRET+'\n',1);self.assertEqual(r['reason'],'unexpected_output');self.assertNotIn(SECRET,json.dumps(r))
    def test_unexpected_fields_rejected_without_leaking(self):
        r=records();r[0]['password']=SECRET;out=capture(output(r),1);self.assertEqual(out['reason'],'invalid_diagnostics');self.assertNotIn(SECRET,json.dumps(out))
    def test_truncated_record(self):self.assertEqual(capture(output(records()).rstrip('\n'))['reason'],'truncated_diagnostics')
    def test_record_size_limit(self):self.assertEqual(capture(B.DIAG_PREFIX+'x'*1000+'\n',1)['reason'],'record_limit')
    def test_total_output_limit(self):
        r=capture(output(records(),padded=True));self.assertEqual(r['reason'],'output_limit');self.assertLessEqual(r['captured_bytes'],L.MAX_CAPTURE+4096)
    def test_duplicate_records_refused(self):self.assertEqual(capture(output(records()+records()))['reason'],'invalid_diagnostics')
    def test_incomplete_records_refused(self):self.assertEqual(capture(output(records()[:2]))['reason'],'incomplete_or_inconsistent_diagnostics')
    def test_success_with_generic_error_refused(self):self.assertNotEqual(capture(output(records(),True))['reason'],'accepted')
    def test_deadline_preserved(self):
        r=L._capture_backend([sys.executable,'-c','while True: pass'],timeout=.05);self.assertEqual(r['reason'],'deadline_exceeded')
    def test_out_of_order_refused(self):
        r=records();r[0]['stage']='redis';self.assertEqual(capture(output(r))['reason'],'invalid_diagnostics')
    def test_invalid_schema_values(self):
        cases=[{'elapsed_s':float('nan')},{'elapsed_s':float('inf')},{'elapsed_s':-1},{'elapsed_s':True},{'stage':SECRET},{'classification':SECRET},{'event':SECRET},{'count':SECRET}]
        for change in cases:
            with self.subTest(change=list(change)):
                r=records();r[0].update(change);self.assertEqual(capture(output(r))['reason'],'invalid_diagnostics')
    def test_huge_elapsed_integer_is_invalid_not_capture_error(self):
        r=records();r[0]['elapsed_s']=10**400;self.assertEqual(capture(output(r),1)['reason'],'invalid_diagnostics')
    def test_duplicate_JSON_key_refused(self):
        text=B.DIAG_PREFIX+'{"stage":"api_sources","stage":"redis","event":"start","elapsed_s":0,"classification":"checking"}\n';self.assertEqual(capture(text,1)['reason'],'invalid_diagnostics')
    def test_invalid_role_and_count_types(self):
        for key,value in [('count',True),('returncode','0'),('default_present',1),('dvr_present',SECRET)]:
            r=records();r[-1][key]=value;self.assertEqual(capture(output(r))['reason'],'invalid_diagnostics')
    def test_elapsed_must_increase(self):
        r=records();r[-1]['elapsed_s']=0;self.assertEqual(capture(output(r))['reason'],'invalid_diagnostics')

class LifecycleTests(unittest.TestCase):
    def run_execute(self,actual,writer_error=False):
        writes=[]
        with tempfile.TemporaryDirectory() as temp:
            fd=os.open(temp,os.O_RDONLY|os.O_DIRECTORY)
            def write(path,directory,name,value):
                if writer_error and name.endswith('.result.json'):raise OSError(SECRET)
                writes.append((name,copy.deepcopy(value)))
            stderr=io.StringIO()
            with patch.object(L,'_private_dir',return_value=(Path(temp),fd)),patch.object(L,'_receipt',side_effect=write),patch.object(L,'_capture_backend',return_value=actual),contextlib.redirect_stderr(stderr):
                try:L.execute_backend(['synthetic']);error=None
                except Exception as error:err=type(error)
                else:err=None
        return writes,stderr.getvalue(),err
    def test_validated_private_result_before_acceptance(self):
        actual=capture(output(records()));writes,text,error=self.run_execute(actual);self.assertIsNone(error);self.assertEqual(len(writes),2);self.assertEqual(writes[0][1]['invocation'],writes[1][1]['invocation']);self.assertEqual(writes[1][1]['reason'],'accepted');self.assertNotIn(SECRET,text)
    def test_precise_stage_is_retained(self):
        actual=capture(output(records('redis'),True),1);writes,text,error=self.run_execute(actual);self.assertIs(error,ValueError);self.assertEqual(writes[-1][1]['records'][-1]['classification'],'redis_ping_failed')
    def test_result_persistence_failure_cannot_accept(self):
        writes,text,error=self.run_execute(capture(output(records())),True);self.assertIs(error,ValueError);self.assertIn('evidence gap',text);self.assertNotIn(SECRET,text)
    def test_private_directory_failure_prevents_backend_launch(self):
        with patch.object(L,'_private_dir',side_effect=PermissionError(SECRET)),patch.object(L,'_capture_backend') as run,contextlib.redirect_stderr(io.StringIO()) as text,self.assertRaises(ValueError):L.execute_backend(['synthetic'])
        run.assert_not_called();self.assertNotIn(SECRET,text.getvalue())
    def test_historical_receipts_never_read_or_reused(self):
        failed=capture('',1);writes,_,error=self.run_execute(failed);self.assertIs(error,ValueError);self.assertEqual(writes[1][1]['records'],[]);self.assertEqual(writes[1][1]['boundary'],'before_first_diagnostic')
    def test_only_environment_backend_routes_to_diagnostics(self):
        with patch.object(L,'execute') as normal,patch.object(L,'execute_backend') as backend:
            L.inside('backend.py',environment=True);backend.assert_called_once();self.assertEqual(backend.call_args.args[1],90);normal.assert_not_called()
            L.inside('register.py','--config','/run/credentials/registration.json');normal.assert_called_once();self.assertEqual(normal.call_args.args[1],90)

class IntegrityTests(unittest.TestCase):
    def test_exact_original_hashes(self):
        pins=json.loads((HERE/'original-hashes.json').read_text())['files']
        for name,h in pins.items():self.assertEqual(hashlib.sha256((HERE/'original'/name).read_bytes()).hexdigest(),h)
    def test_untouched_lifecycle_functions_identical(self):
        def funcs(p):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
        a=funcs(HERE/'original/lifecycle.py');b=funcs(HERE/'candidate/lifecycle.py')
        for name in ['trusted','execute','prepare','start','rollback_integration','stop']:self.assertEqual(a[name],b[name],name)
    def test_non_Celery_backend_AST_preserved(self):
        def first_stages(path):
            node=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='check')
            return [ast.dump(n,include_attributes=False) for n in node.body[:-1]]
        self.assertEqual(first_stages(HERE/'structured-baseline/backend.py'),first_stages(HERE/'candidate/backend.py'))
    def test_bounded_capture_and_broker_comparison_AST_unchanged(self):
        def functions(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)}
        a=functions(HERE/'structured-baseline/backend.py');b=functions(HERE/'candidate/backend.py')
        for name in ['celery_capture','compare_brokers','classify_celery','decode_record']:self.assertEqual(a[name],b[name])

class AdditionalIntegrityTests(unittest.TestCase):
    def test_complete_candidate_manifest_and_install_closure(self):
        spec=importlib.util.spec_from_file_location('offline_candidate_verifier',HERE/'verify_candidate.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertTrue(module.verify()['manifest_paths_closed'])
    def test_only_original_two_manifest_entries_change(self):
        a=json.loads((HERE/'original/manifest.json').read_text());b=json.loads((HERE/'candidate/manifest.json').read_text());self.assertEqual(set(a['files']),set(b['files']));self.assertEqual({k for k in a['files'] if a['files'][k]!=b['files'][k]},{'backend.py','lifecycle.py'})
    def test_main_lifecycle_failure_response_unchanged(self):
        def main(path):return ast.dump(next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.If)),include_attributes=False)
        self.assertEqual(main(HERE/'original/lifecycle.py'),main(HERE/'candidate/lifecycle.py'))
    def test_no_added_readiness_delay_or_retry(self):
        source=(HERE/'candidate/backend.py').read_text();self.assertNotIn('time.sleep',source)
        self.assertEqual((HERE/'candidate/lifecycle.py').read_text().count('time.sleep(1)'),1)
    def test_migration_failure_requires_matching_evidence(self):
        r=records('postgres');r[-1]['returncode']=2;self.assertEqual(capture(output(r),1)['reason'],'invalid_diagnostics')
    def test_worker_failure_cannot_claim_two_fresh_workers(self):
        r=records('uwsgi');r[-1]['count']=2;self.assertEqual(capture(output(r),1)['reason'],'invalid_diagnostics')
    def test_Celery_missing_role_cannot_claim_role_present(self):
        r=records('celery');r[-1]['dvr_present']=True;self.assertEqual(capture(output(r),1)['reason'],'invalid_diagnostics')

class FinalFailureTests(unittest.TestCase):
    def test_malformed_JSON_is_refused(self):
        self.assertEqual(capture(B.DIAG_PREFIX+'{not JSON}\n',1)['reason'],'invalid_diagnostics')
    def test_invalid_UTF8_is_refused(self):
        code='import sys;sys.stderr.buffer.write('+repr(B.DIAG_PREFIX.encode()+b'\xff\n')+')'
        self.assertEqual(L._capture_backend([sys.executable,'-c',code],2)['reason'],'invalid_diagnostics')
    def test_main_success_exit_is_unchanged(self):
        main=next(n for n in ast.parse((HERE/'candidate/backend.py').read_text()).body if isinstance(n,ast.If))
        exec(compile(ast.Module(body=[main],type_ignores=[]),'main','exec'),{'__name__':'__main__','check':lambda:None})
    def test_intent_receipt_failure_prevents_launch(self):
        with tempfile.TemporaryDirectory() as d:
            fd=os.open(d,os.O_RDONLY|os.O_DIRECTORY)
            with patch.object(L,'_private_dir',return_value=(Path(d),fd)),patch.object(L,'_receipt',side_effect=FileExistsError(SECRET)),patch.object(L,'_capture_backend') as run,contextlib.redirect_stderr(io.StringIO()) as text,self.assertRaises(ValueError):L.execute_backend(['synthetic'])
            run.assert_not_called();self.assertNotIn(SECRET,text.getvalue())
    def test_capture_exception_remains_private_evidence_gap(self):
        with tempfile.TemporaryDirectory() as d:
            fd=os.open(d,os.O_RDONLY|os.O_DIRECTORY);writes=[]
            with patch.object(L,'_private_dir',return_value=(Path(d),fd)),patch.object(L,'_receipt',side_effect=lambda *a:writes.append(a[-1])),patch.object(L,'_capture_backend',side_effect=RuntimeError(SECRET)),contextlib.redirect_stderr(io.StringIO()) as text,self.assertRaises(ValueError):L.execute_backend(['synthetic'])
            self.assertEqual(len(writes),1);self.assertEqual(writes[0]['state'],'intent');self.assertNotIn(SECRET,text.getvalue())
    def test_mutated_original_pin_inventory_is_refused(self):
        spec=importlib.util.spec_from_file_location('offline_candidate_integrity',HERE/'verify_candidate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);original=m.load
        def fake(path):
            value=original(path)
            if path.name=='original-hashes.json':value['files']['backend.py']='0'*64
            return value
        with patch.object(m,'load',side_effect=fake),self.assertRaisesRegex(ValueError,'authorized_baseline_changed'):m.verify()

if __name__=='__main__':unittest.main()
