"""Offline JSON contract fixtures. Never execute Celery, Django or a broker."""
import ast,hashlib,json,copy,unittest
from pathlib import Path
from test_diagnostics import B,L,HERE,BackendFixture,SECRET,capture

GOOD={'default@synthetic-worker':{'ok':'pong'},'dvr@synthetic-worker':{'ok':'pong'}}

def run_response(value,code=0,stderr='',raw=False):
    f=BackendFixture();f.celery_stdout=value if raw else json.dumps(value);f.celery_code=code;f.celery_stderr=stderr
    return f.execute()

class StructuredTests(unittest.TestCase):
    def assertRefused(self,value,code=0,stderr='',raw=False):
        rows,error,text=run_response(value,code,stderr,raw);self.assertIsNotNone(error);self.assertEqual(rows[-1]['event'],'fail');self.assertNotIn(SECRET,text);self.assertNotIn('synthetic-worker',text);return rows[-1]
    def test_valid_both_positive(self):
        rows,error,text=run_response(GOOD);self.assertIsNone(error);self.assertEqual(rows[-1]['count'],2);self.assertTrue(rows[-1]['default_present'] and rows[-1]['dvr_present']);self.assertTrue(rows[-1]['reply_output_valid']);self.assertNotIn('synthetic-worker',text)
    def test_JSON_key_order_does_not_matter(self):
        rows,error,_=run_response(dict(reversed(list(GOOD.items()))));self.assertIsNone(error)
    def test_JSON_whitespace_and_complete_newline(self):
        rows,error,_=run_response(' \n'+json.dumps(GOOD,indent=2)+'\n',raw=True);self.assertIsNone(error)
    def test_missing_default(self):
        r=self.assertRefused({'dvr@synthetic-worker':{'ok':'pong'}});self.assertEqual(r['classification'],'celery_default_missing');self.assertTrue(r['dvr_present']);self.assertFalse(r['default_present'])
    def test_missing_DVR(self):
        r=self.assertRefused({'default@synthetic-worker':{'ok':'pong'}});self.assertEqual(r['classification'],'celery_dvr_missing')
    def test_empty_mapping_is_not_success(self):self.assertEqual(self.assertRefused({})['classification'],'celery_roles_missing')
    def test_duplicate_same_worker_JSON_key(self):
        raw='{"default@synthetic-worker":{"ok":"pong"},"default@synthetic-worker":{"ok":"pong"},"dvr@synthetic-worker":{"ok":"pong"}}';r=self.assertRefused(raw,raw=True);self.assertFalse(r['reply_output_valid'])
    def test_duplicate_role_different_identity(self):
        r=self.assertRefused({'default@synthetic-worker':{'ok':'pong'},'default@second-worker':{'ok':'pong'}});self.assertFalse(r['reply_output_valid'])
    def test_duplicate_nested_reply_key(self):
        r=self.assertRefused('{"default@synthetic-worker":{"ok":"pong","ok":"pong"},"dvr@synthetic-worker":{"ok":"pong"}}',raw=True);self.assertFalse(r['reply_output_valid'])
    def test_unexpected_third_worker(self):
        v=copy.deepcopy(GOOD);v['extra@synthetic-worker']={'ok':'pong'};self.assertFalse(self.assertRefused(v)['reply_output_valid'])
    def test_unexpected_worker_or_identity_shape(self):
        for name in ['other@synthetic-worker','Default@synthetic-worker','default','default@','default@https://private.invalid','default@x@other']:
            with self.subTest(shape=len(name)):self.assertRefused({name:{'ok':'pong'},'dvr@synthetic-worker':{'ok':'pong'}})
    def test_explicit_error_is_not_pong(self):
        v=copy.deepcopy(GOOD);v['default@synthetic-worker']={'error':SECRET};r=self.assertRefused(v);self.assertFalse(r['default_present']);self.assertEqual(r['classification'],'celery_unclassified_failure')
    def test_negative_wrong_type_extra_fields_or_wrong_case(self):
        for payload in [{'ok':'PONG'},{'ok':True},{'ok':'no'},'pong',None,{'ok':'pong','error':SECRET},{}]:
            v=copy.deepcopy(GOOD);v['default@synthetic-worker']=payload;self.assertRefused(v)
    def test_malformed_or_truncated_JSON(self):
        for raw in ['{','{"default@x":',json.dumps(GOOD)[:-1],json.dumps(GOOD)+' garbage', 'log prefix\n'+json.dumps(GOOD)]:self.assertRefused(raw,raw=True)
    def test_nonfinite_or_non_mapping_JSON(self):
        for raw in ['null','true','[]','[{}]','NaN','Infinity','{"default@x":{"ok":NaN}}']:self.assertRefused(raw,raw=True)
    def test_two_JSON_documents_refused(self):self.assertRefused(json.dumps(GOOD)+json.dumps(GOOD),raw=True)
    def test_oversize_JSON_and_whitespace_refused(self):self.assertRefused(json.dumps(GOOD)+' '*(B.OUTPUT_LIMIT+1),raw=True)
    def test_zero_exit_with_invalid_response_refused(self):self.assertRefused('not JSON',raw=True)
    def test_nonzero_with_valid_pongs_refused(self):
        r=self.assertRefused(GOOD,code=69);self.assertEqual(r['returncode'],69);self.assertEqual(r['classification'],'celery_unclassified_failure')
    def test_stderr_warning_or_error_not_ignored(self):
        self.assertEqual(B.structured_replies(json.dumps(GOOD),None),([],False));self.assertEqual(B.structured_replies(json.dumps(GOOD),'',1),([],False))
        self.assertRefused(GOOD,stderr='DuplicateNodenameWarning: synthetic-worker\n');self.assertRefused(GOOD,stderr=SECRET+'\n')
    def test_hostname_and_credentials_are_not_in_receipt(self):
        private='private-hostname-DO-NOT-LOG';v={'default@'+private:{'ok':'pong'},'dvr@'+private:{'ok':'pong'}}
        rows,error,text=run_response(v);self.assertIsNone(error);self.assertNotIn(private,text)
        v['default@'+private]={'error':'redis://user:'+SECRET+'@'+private+'/0'};rows,error,text=run_response(v);self.assertIsNotNone(error);self.assertNotIn(private,text);self.assertNotIn(SECRET,text);self.assertNotIn('redis://',text)
    def test_no_human_formatter_fallback(self):self.assertRefused('-> default@synthetic-worker: OK\n pong\n-> dvr@synthetic-worker: OK\n pong\n',raw=True)
    def test_private_receipt_capture_accepts_only_valid_stage_records(self):
        rows,error,text=run_response(GOOD);self.assertIsNone(error);receipt=capture(text);self.assertEqual(receipt['reason'],'accepted');self.assertEqual(receipt['records'],rows)
    def test_private_receipt_retains_missing_role_failure(self):
        rows,error,text=run_response({'dvr@synthetic-worker':{'ok':'pong'}});receipt=capture(text,1);self.assertEqual(receipt['reason'],'backend_stage_failed');self.assertEqual(receipt['records'][-1]['classification'],'celery_default_missing')
    def test_one_command_exact_syntax_and_existing_deadline(self):
        f=BackendFixture();f.execute();self.assertEqual(len(f.commands),2);args,kw=f.commands[-1];self.assertEqual(args,['celery','-A','dispatcharr','inspect','ping','--timeout=8','--json']);self.assertEqual(kw,dict(cwd='/app',capture_output=True,text=True,timeout=40))
    def test_broker_comparison_still_unknown(self):
        rows,error,_=run_response(GOOD);self.assertFalse(rows[-1]['broker_comparison_known']);self.assertFalse(any(rows[-1][k] for k in B.compare_brokers()))

class StructuredIntegrityTests(unittest.TestCase):
    def test_exact_current_rollback_bytes(self):
        expected={'backend.py':'5d37a1a53a8c4e05d3b699998cd3ae618cb4b79112c9c651ed9711d9175a5e4b','lifecycle.py':'0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac','manifest.json':'52f8c8e14ecc33fec0b362b1ef32f7d79111ba9d127ee759bc08b939a8f1620b'}
        for n,h in expected.items():self.assertEqual(hashlib.sha256((HERE/'structured-baseline'/n).read_bytes()).hexdigest(),h)
        self.assertEqual((HERE/'candidate/lifecycle.py').read_bytes(),(HERE/'structured-baseline/lifecycle.py').read_bytes())
    def test_manifest_delta_only_backend(self):
        a=json.loads((HERE/'structured-baseline/manifest.json').read_text())['files'];b=json.loads((HERE/'candidate/manifest.json').read_text())['files'];self.assertEqual(set(a),set(b));self.assertEqual({n for n in a if a[n]!=b[n]},{'backend.py'})
    def test_no_human_regex_in_readiness_function(self):
        node=next(n for n in ast.parse((HERE/'candidate/backend.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='check');text=ast.unparse(node);self.assertNotIn('re.findall',text);self.assertIn('structured_replies',text)
    def test_retained_CLI_contract(self):
        v=json.loads((HERE/'celery-json-cli-contract.json').read_text());self.assertEqual(v['version'],'5.6.3');self.assertEqual(v['source_sha256'],'c1267b714e2100b4c7f9817833a985f6f4cf704da08485ddaaa33279f54efbdd');self.assertFalse(v['new_application_execution']);self.assertEqual(v['syntax'][-2:],['--timeout=8','--json'])

if __name__=='__main__':unittest.main()
