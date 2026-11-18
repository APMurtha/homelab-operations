"""Synthetic processes/configuration only; never import Dispatcharr or contact a broker."""
import copy,json,math,os,subprocess,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
from test_diagnostics import B,L,BackendFixture,SECRET,records,output,capture,command_fields,HERE

BROKER='Error: Could not connect to the message broker. Please make sure your broker (e.g., RabbitMQ or Redis) is running and the connection settings are correct. Reason: '
REMOTE='Error: Unable to run the `inspect ping` command. Reason: '
IMPORT='Error: \nUnable to load celery application.\nThe module dispatcharr was not found.\n'

def broker():
    return dict(transport='redis',host='LOCALHOST.',port=6379,database=0,username='',password=SECRET,
                control_exchange='celery',global_keyprefix='',fanout_prefix=True,fanout_patterns=True,tls=None)
def snapshots():return {k:broker() for k in ['inspection','default','dvr']}

class ClassificationTests(unittest.TestCase):
    def test_no_replies(self):self.assertEqual(B.classify_celery(69,'','Error: No nodes replied within time constraint\n'),'celery_no_replies')
    def test_broker_connection_error(self):self.assertEqual(B.classify_celery(69,'',BROKER+'redis://user:'+SECRET+'@synthetic.invalid/0\n'),'celery_broker_connection_failed')
    def test_remote_command_exception(self):self.assertEqual(B.classify_celery(69,'',REMOTE+SECRET+'\n'),'celery_remote_command_failed')
    def test_import_failure(self):self.assertEqual(B.classify_celery(2,'',IMPORT),'celery_usage_or_import_failed')
    def test_click_usage_envelope(self):self.assertEqual(B.classify_celery(2,'',"Usage: celery [OPTIONS] COMMAND [ARGS]...\nTry 'celery --help' for help.\n\n"+IMPORT),'celery_usage_or_import_failed')
    def test_ambiguous_code69_not_assumed_no_replies(self):self.assertEqual(B.classify_celery(69,'',''),'celery_unclassified_failure')
    def test_malformed_ambiguous_or_truncated(self):
        bad=['Error: No nodes replied within time constraint', BROKER+'x\n'+REMOTE+'x\n',BROKER+'[truncated]\n',BROKER+'…\n',BROKER+'x Error: another error\n',BROKER+'x\x00\n',BROKER+'x\t\n',BROKER+'x\x7f\n',BROKER+'   \n','\x1b[31m'+IMPORT,SECRET+'\n',BROKER+'\n']
        for text in bad:
            with self.subTest(text_type=len(text)):self.assertEqual(B.classify_celery(69,'',text),'celery_unclassified_failure')
    def test_oversize_or_incomplete(self):
        for args in [(69,'',BROKER+'x'*B.OUTPUT_LIMIT+'\n',True),(69,'','Error: No nodes replied within time constraint\n',False),(2,'x',IMPORT,True)]:self.assertEqual(B.classify_celery(*args),'celery_unclassified_failure')
    def test_exit_code_must_match_signature(self):self.assertEqual(B.classify_celery(1,'','Error: No nodes replied within time constraint\n'),'celery_unclassified_failure')
    def test_broker_secret_never_emitted(self):
        f=BackendFixture();f.celery_code=69;f.celery_stdout='';f.celery_stderr=BROKER+'redis://user:'+SECRET+'@synthetic.invalid/0\n'
        rows,error,text=f.execute();self.assertIsNotNone(error);self.assertEqual(rows[-1]['classification'],'celery_broker_connection_failed');self.assertNotIn(SECRET,text);self.assertNotIn('redis://',text);self.assertNotIn('synthetic.invalid',text)
    def test_success_retains_exact_roles_and_footer(self):
        f=BackendFixture();f.celery_stdout+='\n2 nodes online.\n';rows,error,text=f.execute();self.assertIsNone(error);self.assertTrue(rows[-1]['reply_output_valid']);self.assertEqual(rows[-1]['classification'],'ready')
    def test_success_with_unknown_log_output_refused(self):
        for mode in ['stderr','terminal_control']:
            f=BackendFixture()
            if mode=='stderr':f.celery_stderr=SECRET+'\n'
            else:f.celery_stdout=f.celery_stdout.replace('@fixture','@fixture\x1b[31m')
            rows,error,text=f.execute();self.assertIsNotNone(error);self.assertEqual(rows[-1]['classification'],'celery_unclassified_failure');self.assertFalse(rows[-1]['reply_output_valid'])
    def test_internal_classification_not_a_schema_field(self):
        row=records()[-1];row['celery_failure']='ready'
        with self.assertRaises(B.InvalidDiagnostics):B.decode_record(json.dumps(row).encode())

class ComparisonTests(unittest.TestCase):
    def test_matching(self):self.assertTrue(all(B.compare_brokers(snapshots()).values()))
    def test_each_worker_and_category(self):
        for role in ['default','dvr']:
            for field,value,category in [('host','different.invalid','endpoint'),('port',6380,'endpoint'),('password','different','auth'),('username','other','auth'),('database',1,'namespace'),('control_exchange','other','namespace'),('fanout_prefix',False,'namespace')]:
                v=snapshots();v[role][field]=value;r=B.compare_brokers(v);self.assertTrue(r['broker_comparison_known']);self.assertFalse(r['broker_'+category+'_equal'])
    def test_missing_or_environment_only_unknown(self):
        for v in [None,{}, {'inspection':broker()},dict(REDIS_HOST='localhost'),{'inspection':{},'default':{},'dvr':{}}]:self.assertFalse(any(B.compare_brokers(v).values()))
    def test_unknown_never_means_proven_mismatch(self):
        v=snapshots();del v['default']['password'];self.assertFalse(B.compare_brokers(v)['broker_comparison_known'])
    def test_transport_and_tls_identity(self):
        v=snapshots()
        for row in v.values():row.update(transport='rediss',tls=dict(verify=True,ca_identity='synthetic CA',client_identity='synthetic client'))
        self.assertTrue(all(B.compare_brokers(v).values()));v['dvr']['tls']['ca_identity']='other';self.assertFalse(B.compare_brokers(v)['broker_transport_equal'])
    def test_unverified_tls_unknown(self):
        v=snapshots();v['dvr'].update(transport='rediss',tls=dict(verify=False,ca_identity='',client_identity=''));self.assertFalse(any(B.compare_brokers(v).values()))
    def test_malformed_effective_configuration_unknown(self):
        for field,value in [('port',True),('database',-1),('host','https://private.invalid'),('host','bad:port'),('password',None),('fanout_patterns','yes'),('transport','sentinel')]:
            v=snapshots();v['inspection'][field]=value;self.assertFalse(any(B.compare_brokers(v).values()))
    def test_only_fixed_booleans_returned(self):
        r=B.compare_brokers(snapshots());self.assertTrue(all(type(x) is bool for x in r.values()));self.assertNotIn(SECRET,json.dumps(r))
    def test_runtime_comparison_explicitly_unknown(self):
        rows,e,_=BackendFixture().execute();self.assertFalse(rows[-1]['broker_comparison_known']);self.assertFalse(any(rows[-1][k] for k in B.compare_brokers()))

class CaptureTests(unittest.TestCase):
    def run_child(self,code,timeout=2):return B.celery_capture([sys.executable,'-c',code],cwd=str(HERE),capture_output=True,text=True,timeout=timeout)
    def test_bounded_real_synthetic_child(self):
        p=self.run_child("import sys;sys.stdout.write('safe');sys.stderr.write('error');sys.exit(69)");self.assertEqual((p.stdout,p.stderr,p.returncode,p.stdout_bytes,p.stderr_bytes,p.complete),('safe','error',69,4,5,True))
    def test_stdout_and_stderr_overflow(self):
        for pipe in ['stdout','stderr']:
            p=self.run_child("import sys;sys."+pipe+".write('x'*100000)");self.assertFalse(p.complete);self.assertLessEqual(len(p.stdout.encode()),B.OUTPUT_LIMIT);self.assertLessEqual(len(p.stderr.encode()),B.OUTPUT_LIMIT);self.assertEqual(max(p.stdout_bytes,p.stderr_bytes),B.OUTPUT_LIMIT+1)
    def test_invalid_utf8(self):
        p=self.run_child("import os;os.write(2,b'\\xff')");self.assertFalse(p.complete)
    def test_interrupted_deadline_still_fails(self):
        with self.assertRaises(subprocess.TimeoutExpired):self.run_child('import time;time.sleep(2)',timeout=.03)
    def test_exact_original_invocation_and_no_retry(self):
        f=BackendFixture();rows,e,_=f.execute();args,kw=f.commands[-1];self.assertEqual(args,['celery','-A','dispatcharr','inspect','ping','--timeout=8']);self.assertEqual(kw,dict(cwd='/app',capture_output=True,text=True,timeout=40));self.assertEqual(len(f.commands),2)
    def test_precise_command_timing_schema(self):
        rows,e,_=BackendFixture().execute();r=rows[-1];self.assertGreaterEqual(r['command_end_s'],r['command_start_s']);self.assertAlmostEqual(r['command_end_s']-r['command_start_s'],r['command_elapsed_s']);self.assertIs(type(r['stdout_bytes']),int)
    def test_invalid_timing_and_byte_counts_refused(self):
        for field,value in [('command_start_s',float('nan')),('command_elapsed_s',2),('command_end_s',99),('stdout_bytes',B.OUTPUT_LIMIT+2),('stderr_bytes',True)]:
            r=records()[-1];r[field]=value
            with self.assertRaises(B.InvalidDiagnostics):B.decode_record(json.dumps(r).encode())
    def test_unknown_comparison_cannot_carry_true_equality(self):
        r=records()[-1];r['broker_auth_equal']=True
        with self.assertRaises(B.InvalidDiagnostics):B.decode_record(json.dumps(r).encode())
    def test_false_success_or_failure_evidence_refused(self):
        for field in ['reply_output_valid','output_complete']:
            r=records()[-1];r[field]=False
            with self.assertRaises(B.InvalidDiagnostics):B.decode_record(json.dumps(r).encode())
    def test_failing_command_cannot_become_success(self):
        f=BackendFixture();f.celery_code=69;rows,e,_=f.execute();self.assertIsNotNone(e);self.assertEqual(rows[-1]['event'],'fail')
    def test_private_receipt_capture_same_invocation(self):
        f=BackendFixture();rows,e,text=f.execute();r=capture(text);self.assertEqual(r['reason'],'accepted');self.assertEqual(r['records'][-1]['command_elapsed_s'],rows[-1]['command_elapsed_s'])

class BaselineTests(unittest.TestCase):
    def test_exact_installed_baseline_rollback_copies(self):
        import hashlib
        pins=json.loads((HERE/'installed-baseline-hashes.json').read_text())['files']
        for n,h in pins.items():self.assertEqual(hashlib.sha256((HERE/'installed-baseline'/n).read_bytes()).hexdigest(),h)
        self.assertEqual((HERE/'candidate/lifecycle.py').read_bytes(),(HERE/'installed-baseline/lifecycle.py').read_bytes())
    def test_only_backend_manifest_entry_changes_from_installed(self):
        a=json.loads((HERE/'installed-baseline/manifest.json').read_text())['files'];b=json.loads((HERE/'candidate/manifest.json').read_text())['files']
        self.assertEqual(set(a),set(b));self.assertEqual({n for n in a if a[n]!=b[n]},{'backend.py'})
    def test_only_two_deployment_targets(self):
        v=json.loads((HERE/'candidate-inventory.json').read_text());self.assertEqual(len(v['replacement_targets']),2);self.assertEqual(len(v['unchanged_installed_targets']),65)
        self.assertEqual({Path(t).name for t in v['replacement_targets']},{'backend.py','manifest.json'})
    def test_rollback_inventory_cannot_substitute_old_original(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('strict_candidate_verifier',HERE/'verify_candidate.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);original=v.load
        def wrong(path):
            data=original(path)
            if path.name=='candidate-inventory.json':
                row=data['rollback_targets']['/docker/dispatcharr-iptv/permanent-streaming/backend.py'];row['source']='configs/dispatcharr-iptv/original-backend-diagnostics/original/backend.py';row['sha256']=v.ORIGINAL['backend.py']
            return data
        with patch.object(v,'load',side_effect=wrong),self.assertRaisesRegex(ValueError,'installed_rollback_inventory_drift'):v.verify()
    def test_record_size_and_capture_limits_unchanged(self):
        self.assertEqual(B.MAX_RECORD,768);self.assertEqual(L.MAX_CAPTURE,4096);self.assertEqual(L.MAX_RECEIPT,16384)
        r=records()[-1];r.update(command_start_s=1000000000000.0,command_end_s=1000000000001.0)
        self.assertLessEqual(len(B.DIAG_PREFIX+json.dumps(r)),B.MAX_RECORD)

if __name__=='__main__':unittest.main()
