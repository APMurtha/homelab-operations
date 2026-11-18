"""Offline binding and fixture contracts; no Docker or application initialization."""
import ast,base64,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
import run_runtime as runner,runtime_admission as admission,runtime_transport as transport,runtime_test as fixture
BINDING=json.loads((HERE/'corrected-runtime-binding.json').read_text())
OLD=json.loads((HERE/'retained-image-contract.json').read_text())
PRESERVED=json.loads((HERE/'runtime-binding-preservation.json').read_text())
def digest(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return digest(json.dumps(value,sort_keys=True,separators=(',',':')).encode())

class CorrectedBinding(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name);self.work.chmod(0o700)
    def journal(self,name='synthetic-binding-01'):return admission.Journal(self.work,name)
    def verified(self,result,image=None):
        return admission.verified(Mock(return_value=result),image or BINDING['image_id'],'synthetic-binding-01',self.journal(),clock=lambda:10)
    def result(self,hashes=None):return {'base':{'id':BINDING['image_id']},'hashes':hashes or dict(BINDING['source_hashes']),'process_exited':True,'exit_code':0}
    def test_exact_corrected_image_and_contract_are_accepted(self):
        v=self.verified(self.result());self.assertEqual(v['image_id'],BINDING['image_id']);self.assertEqual(v['source_hashes'],BINDING['source_hashes'])
    def test_old_image_rejected_before_inspection_or_runner_work(self):
        inspect=Mock()
        with self.assertRaisesRegex(admission.Refused,'unapproved_test_image'):
            admission.verified(inspect,OLD['image'],'synthetic-binding-01',self.journal())
        inspect.assert_not_called()
        with patch.object(runner,'load_host_helpers') as load,self.assertRaisesRegex(RuntimeError,'new_accepted_test_image_required'):
            runner.main({},self.work,OLD['image'],attempt_id='synthetic-old-01')
        load.assert_not_called();self.assertEqual(transport.IMAGE,BINDING['image_id'])
    def test_wrong_source_hash_refused(self):
        hashes=dict(BINDING['source_hashes']);hashes['core/provider_security.py']='0'*64
        with self.assertRaisesRegex(admission.Refused,'verification_incomplete'):self.verified(self.result(hashes))
    def test_mixed_old_new_source_contract_refused(self):
        mixed=dict(BINDING['source_hashes']);mixed['apps/m3u/tasks.py']=OLD['source_hashes']['apps/m3u/tasks.py']
        with self.assertRaisesRegex(admission.Refused,'verification_incomplete'):self.verified(self.result(mixed))
    def test_old_contract_receipt_cannot_authorize_corrected_image(self):
        journal=self.journal();receipt={'image_id':BINDING['image_id'],'attempt_id':journal.attempt_id,'source_hashes':{**OLD['source_hashes'],**OLD['readiness_hashes']},'completed_monotonic':10,'exit_code':0,'process_exited':True}
        self.assertFalse(admission.receipt_valid(receipt,BINDING['image_id'],journal.attempt_id,10))
    def test_binding_exactly_matches_published_build_and_unbound_release(self):
        build=json.loads((HERE/'corrected-image-build-results.json').read_text());release=json.loads((ROOT/'configs/dispatcharr-iptv/native-provider-hardening/release-contract.json').read_text())
        self.assertEqual(BINDING['image_id'],build['new_image_id']);self.assertEqual(BINDING['source_hashes'],build['verification']['hashes'])
        self.assertEqual(BINDING['source_hashes'],{**release['source_hashes'],**release['readiness_hashes']});self.assertIsNone(release['aio_image'])
        self.assertEqual(digest((HERE/'corrected-image-build-results.json').read_bytes()),BINDING['build_results_sha256'])
        self.assertEqual({k for k in release['source_hashes'] if release['source_hashes'][k]!=OLD['source_hashes'][k]}, {'apps/m3u/api_views.py','apps/m3u/tasks.py','core/provider_security.py'})
        self.assertEqual(release['readiness_hashes'],OLD['readiness_hashes'])
    def test_detached_runner_and_helper_pins_agree(self):
        self.assertEqual(transport.IMAGE,admission.RETAINED_IMAGE)
        self.assertEqual(transport.APPROVED_RUNNER_SHA256,digest((HERE/'run_runtime.py').read_bytes()))
        for name,h in runner.HOST_HELPERS.items():self.assertEqual(digest((HERE/name).read_bytes()),h)
        for name,h in transport.PAYLOAD_CORE_PINS.items():self.assertEqual(digest((HERE/name).read_bytes()),h)
    def test_duplicate_identity_preserves_existing_attempt_and_history(self):
        journal=self.journal();journal.record('historical_fixture',{'unchanged':True});before=(journal.path/'admission.jsonl').read_bytes()
        with self.assertRaises(admission.Refused):self.journal()
        self.assertEqual((journal.path/'admission.jsonl').read_bytes(),before)
    def test_published_historical_evidence_remains_byte_identical(self):
        for name,h in PRESERVED['historical_files_sha256'].items():self.assertEqual(digest((ROOT/name).read_bytes()),h,name)
    def test_production_files_and_installed_target_mapping_unchanged(self):
        for name,h in PRESERVED['production_files_sha256'].items():self.assertEqual(digest((ROOT/name).read_bytes()),h,name)
        manifest=json.loads((ROOT/'configs/dispatcharr-iptv/trusted-guard-tests/transition-manifest.json').read_text())
        self.assertEqual(canonical(manifest['installed_files']),PRESERVED['installed_manifest_sha256'])
    def test_resource_limits_isolation_audit_and_transport_behavior_unchanged(self):
        for name,entry in PRESERVED['security_code'].items():
            source=(HERE/name).read_text()
            if 'whole_file_sha256' in entry:self.assertEqual(digest(source.encode()),entry['whole_file_sha256']);continue
            functions={n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
            for function,h in entry['functions'].items():self.assertEqual(digest(functions[function].encode()),h,name+':'+function)
        self.assertEqual((admission.STABILIZE_SECONDS,admission.MAX_SECONDS,admission.LOAD_MAX,admission.MEMORY_MIN,admission.DISK_MIN),(120,180,2,2*1024**3,1024**3))
        self.assertEqual(transport.JOB_SECONDS,1200)

class LifecycleReadbacks(unittest.TestCase):
    def detail(self):return {'id':10,'is_active':False,'channel_groups':[{'channel_group':25,'custom_properties':{'xc_id':'1'},'enabled':False,'auto_channel_sync':False}]}
    def failure(self):return {'detail':'native_discovery_failed_no_retry','account_id':10,'account_created':True,'discovery':{'state':'failed','code':'authorization_refused'}}
    def test_creation_readback_retains_exact_native_group_id_without_secrets(self):
        value=self.detail();value['password']='DO_NOT_RETAIN';row=fixture.creation_snapshot(value)
        self.assertEqual(row,{'account_id':10,'is_active':False,'groups':[{'channel_group':25,'xc_id':'1'}]});self.assertNotIn('DO_NOT_RETAIN',json.dumps(row))
    def test_active_enabled_duplicate_or_malformed_relations_refused(self):
        for mutate in [lambda v:v.update(is_active=True),lambda v:v['channel_groups'][0].update(enabled=True),lambda v:v['channel_groups'].append(v['channel_groups'][0].copy()),lambda v:v['channel_groups'][0].update(custom_properties=None)]:
            row=self.detail();mutate(row)
            with self.assertRaises(RuntimeError):fixture.creation_snapshot(row)
    def test_partial_failure_contract_has_exact_status_and_known_identity(self):
        self.assertEqual(fixture.discovery_failure_snapshot(403,self.failure()),{'HTTP_status':403,'account_id':10,'account_created':True,'code':'authorization_refused'})
        for status,changes in [(201,{}),(502,{}),(403,{'account_created':False}),(403,{'account_id':True}),(403,{'discovery':{'state':'failed','code':'https://secret.invalid/token'}})]:
            row=self.failure();row.update(changes)
            with self.assertRaisesRegex(RuntimeError,'native_failure_contract_refused'):fixture.discovery_failure_snapshot(status,row)
    def test_runtime_fixture_requires_real_association_and_safe_failure_assertions(self):
        source=(HERE/'runtime_test.py').read_text();tree=ast.parse(source)
        methods={n.name:ast.get_source_segment(source,n) for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)}
        positive=methods['test_06_actual_native_discovery_import_and_XMLTV_mapping'];negative=methods['test_05_explicit_discovery_failure_has_known_commit_and_no_blind_retry']
        self.assertIn('ChannelGroupM3UAccount.objects.get',positive);self.assertIn('native.channel_group_id',positive);self.assertNotIn('ChannelGroupM3UAccount.objects.create',positive)
        self.assertIn("self.assertFalse(created['is_active'])",positive);self.assertIn("self.assertEqual(len(selected),1)",positive)
        self.assertIn("'HTTP_status':403",negative);self.assertIn('ledger.clean()',negative);self.assertIn('M3UAccount.Status.ERROR',negative)
        self.assertIn('operator_requested=True',methods['test_03_real_Celery_default_and_profile_tasks_make_no_provider_requests'])
        exchange=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='exchange')
        calls=[n for n in ast.walk(exchange) if isinstance(n,ast.Call)]
        status_line=next(n.lineno for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='record')
        capture_line=next(n.lineno for n in calls if isinstance(n.func,ast.Name) and n.func.id=='creation_snapshot')
        self.assertLess(status_line,capture_line)

if __name__=='__main__':unittest.main()
