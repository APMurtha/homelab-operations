"""Synthetic clocks/Docker responses only; never runs Docker or sleeps in real time."""
import base64
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import runtime_admission as a
import run_runtime as runner

class Clock:
    def __init__(self):self.now=1000.;self.sleeps=[];self.overshoot=0;self.interrupt=False
    def __call__(self):return self.now
    def sleep(self,seconds):
        if self.interrupt:raise KeyboardInterrupt
        self.sleeps.append(seconds);self.now+=seconds+self.overshoot

class Admission(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name);self.work.chmod(0o700);self.clock=Clock()
        self.journal=a.Journal(self.work,'synthetic-attempt-01');self.baseline={'protected':'healthy'}
        self.receipt=a.verified(lambda *args:{'base':{'id':a.RETAINED_IMAGE},'hashes':dict(a.EXPECTED_SOURCES),'process_exited':True,'exit_code':0},a.RETAINED_IMAGE,self.journal.attempt_id,self.journal,clock=self.clock)
        self.values={'memory_available_bytes':3*1024**3,'disk_available_bytes':2*1024**3,'load':[.5,.5,.5]};self.probes=0
    def rows(self):return [json.loads(l) for l in (self.journal.path/'admission.jsonl').read_text().splitlines()]
    def probe(self,deadline):self.probes+=1;return {'image_id':a.RETAINED_IMAGE,'production':self.baseline}
    def measure(self):return {**self.values,'monotonic':self.clock()}
    def run_gate(self,**kw):
        return a.stabilize(kw.pop('receipt',self.receipt),a.RETAINED_IMAGE,self.journal.attempt_id,self.baseline,kw.pop('probe',self.probe),kw.pop('capacity',self.measure),self.journal,clock=self.clock,sleep=self.clock.sleep,**kw)
    def decisions(self):return [r for r in self.rows() if r['event']=='admission_decision']
    def test_success_waits_full_fixed_interval_then_one_decision(self):
        decision=self.run_gate();self.assertTrue(decision['admitted']);self.assertEqual(sum(self.clock.sleeps),120)
        self.assertEqual(len(self.decisions()),1);self.assertEqual(self.probes,9)
        self.assertEqual(self.rows()[1]['event'],'verification_started');self.assertEqual(self.rows()[2]['event'],'verification_completed')
    def test_high_load_observations_cannot_extend_or_shorten_fixed_interval(self):
        def capacity():
            v=self.measure();v['load']=[8 if self.clock.now<1120 else .5,1,1];return v
        self.assertTrue(self.run_gate(capacity=capacity)['admitted']);self.assertEqual(sum(self.clock.sleeps),120);self.assertEqual(len(self.decisions()),1)
    def test_persistent_load_refusal_is_one_final_decision(self):
        self.values['load']=[2.001,1,1]
        with self.assertRaisesRegex(a.Refused,'final_capacity_refused'):self.run_gate()
        self.assertEqual(sum(self.clock.sleeps),120);self.assertEqual(len(self.decisions()),1)
        self.assertEqual(self.decisions()[0]['details']['measurement']['load'][0],2.001)
    def test_exact_existing_thresholds_pass(self):
        self.values.update(memory_available_bytes=a.MEMORY_MIN,disk_available_bytes=a.DISK_MIN,load=[2,2,2]);self.assertTrue(self.run_gate()['admitted'])
    def test_memory_refusal_is_measured_and_durable(self):
        self.values['memory_available_bytes']=a.MEMORY_MIN-1
        with self.assertRaisesRegex(a.Refused,'final_capacity_refused'):self.run_gate()
        self.assertEqual(self.decisions()[0]['details']['measurement']['memory_available_bytes'],a.MEMORY_MIN-1)
    def test_disk_refusal_is_measured_and_durable(self):
        self.values['disk_available_bytes']=a.DISK_MIN-1
        with self.assertRaisesRegex(a.Refused,'final_capacity_refused'):self.run_gate()
        self.assertEqual(len(self.decisions()),1)
    def test_missing_verification_never_starts_stabilization(self):
        with self.assertRaisesRegex(a.Refused,'missing_or_stale_verification'):self.run_gate(receipt=None)
        self.assertEqual(self.probes,0);self.assertEqual(self.decisions(),[])
    def test_stale_and_future_and_other_attempt_receipts_fail(self):
        for field,value in [('completed_monotonic',self.clock()-31),('completed_monotonic',self.clock()+1),('attempt_id','historical-attempt')]:
            with self.subTest(field=field,value=value),self.assertRaisesRegex(a.Refused,'missing_or_stale_verification'):self.run_gate(receipt={**self.receipt,field:value})
        self.assertEqual(self.decisions(),[])
    def test_verifier_must_reap_process_and_match_all_18_hashes(self):
        good={'base':{'id':a.RETAINED_IMAGE},'hashes':a.EXPECTED_SOURCES,'process_exited':True,'exit_code':0}
        for change in [{'process_exited':False},{'exit_code':None},{'exit_code':1},{'hashes':{}},{'base':{'id':'changed'}}]:
            with self.subTest(change=change),self.assertRaisesRegex(a.Refused,'verification_incomplete'):
                a.verified(lambda *args:{**good,**change},a.RETAINED_IMAGE,self.journal.attempt_id,self.journal,clock=self.clock)
    def test_incomplete_receipt_cannot_authorize_stabilization(self):
        for change in [{'process_exited':False},{'exit_code':1},{'source_hashes':{}}]:
            with self.assertRaisesRegex(a.Refused,'missing_or_stale_verification'):self.run_gate(receipt={**self.receipt,**change})
    def test_image_change_during_stabilization_refuses_without_decision(self):
        def probe(deadline):return {**self.probe(deadline),'image_id':a.RETAINED_IMAGE if self.probes<3 else 'sha256:'+'f'*64}
        with self.assertRaisesRegex(a.Refused,'image_changed'):self.run_gate(probe=probe)
        self.assertEqual(self.decisions(),[])
    def test_production_change_during_stabilization_refuses(self):
        def probe(deadline):return {**self.probe(deadline),'production':self.baseline if self.probes<2 else {'protected':'unhealthy'}}
        with self.assertRaisesRegex(a.Refused,'production_changed'):self.run_gate(probe=probe)
        self.assertEqual(self.decisions(),[])
    def test_source_contract_change_refuses(self):
        saved=dict(a.EXPECTED_SOURCES)
        def probe(deadline):
            if self.probes==1:a.EXPECTED_SOURCES['core/provider_dns.py']='a'*64
            return self.probe(deadline)
        try:
            with self.assertRaisesRegex(a.Refused,'source_contract_changed'):self.run_gate(probe=probe)
        finally:a.EXPECTED_SOURCES.clear();a.EXPECTED_SOURCES.update(saved)
    def test_oversleep_timeout_has_actual_elapsed_no_decision(self):
        self.clock.overshoot=180
        with self.assertRaisesRegex(a.Refused,'stabilization_timeout'):self.run_gate()
        self.assertEqual(self.rows()[-1]['details']['elapsed_seconds'],195);self.assertFalse(self.rows()[-1]['details']['completed']);self.assertEqual(self.decisions(),[])
    def test_slow_probe_timeout_cannot_admit(self):
        def probe(deadline):self.clock.now=deadline+1;return self.probe(deadline)
        with self.assertRaisesRegex(a.Refused,'stabilization_timeout'):self.run_gate(probe=probe)
    def test_interruption_is_not_completion_or_permission_to_retry(self):
        self.clock.interrupt=True
        with self.assertRaises(KeyboardInterrupt):self.run_gate()
        self.assertFalse(self.rows()[-1]['details']['completed']);self.assertEqual(self.decisions(),[])
        with self.assertRaisesRegex(a.Refused,'duplicate_attempt_identity'):a.Journal(self.work,self.journal.attempt_id)
    def test_duplicate_identity_preserves_existing_receipts(self):
        before=(self.journal.path/'admission.jsonl').read_bytes()
        with self.assertRaisesRegex(a.Refused,'duplicate_attempt_identity'):a.Journal(self.work,self.journal.attempt_id)
        self.assertEqual(before,(self.journal.path/'admission.jsonl').read_bytes())
    def test_three_minute_ceiling_never_extends_or_admits_on_timeout(self):
        with self.assertRaisesRegex(a.Refused,'stabilization_timeout'):self.run_gate(seconds=180)
        self.assertEqual(sum(self.clock.sleeps),180);self.assertEqual(self.decisions(),[])
        self.assertFalse(self.rows()[-1]['details']['completed'])
    def test_slow_observation_persistence_cannot_admit_after_deadline(self):
        original=self.journal.record
        def record(event,details):
            value=original(event,details)
            if event=='capacity_observation' and self.clock.now>=1120:self.clock.now+=80
            return value
        with patch.object(self.journal,'record',side_effect=record),self.assertRaisesRegex(a.Refused,'stabilization_timeout'):self.run_gate()
        self.assertEqual(self.decisions(),[])
    def test_stale_measurement_after_slow_persistence_is_refused(self):
        original=self.journal.record
        def record(event,details):
            value=original(event,details)
            if event=='capacity_observation':self.clock.now+=6
            return value
        with patch.object(self.journal,'record',side_effect=record),self.assertRaisesRegex(a.Refused,'stale_capacity_measurement'):self.run_gate()
        self.assertEqual(self.decisions(),[])
    def test_late_decision_persistence_is_invalidated_without_second_decision(self):
        original=self.journal.record
        def record(event,details):
            value=original(event,details)
            if event=='admission_decision':self.clock.now+=80
            return value
        with patch.object(self.journal,'record',side_effect=record),self.assertRaisesRegex(a.Refused,'admission_evidence_timeout'):self.run_gate()
        self.assertEqual(len(self.decisions()),1);self.assertEqual(self.rows()[-1]['event'],'admission_invalidated')
    def test_failed_journal_write_cannot_authorize_admission(self):
        def stop(event,details):
            if event=='capacity_observation':raise OSError('synthetic_journal_failure')
        with patch.object(self.journal,'record',side_effect=stop),self.assertRaises(OSError):self.run_gate()
        self.assertEqual(self.decisions(),[])
    def test_invalid_interval_and_malformed_measurements_fail_closed(self):
        for seconds in [0,181,True,1.5]:
            with self.assertRaisesRegex(a.Refused,'invalid_stabilization_interval'):self.run_gate(seconds=seconds)
        with self.assertRaisesRegex(a.Refused,'invalid_capacity_measurement'):self.run_gate(capacity=lambda:{**self.measure(),'load':[float('nan'),1,1]})
        self.assertEqual(self.decisions(),[])
    def test_stale_measurement_and_backward_clock_fail(self):
        with self.assertRaisesRegex(a.Refused,'stale_capacity_measurement'):self.run_gate(capacity=lambda:{**self.measure(),'monotonic':self.clock()-6})
    def test_journal_is_private_and_pins_match_approved_release(self):
        self.assertEqual((self.journal.path/'admission.jsonl').stat().st_mode&0o777,0o600)
        contract=json.loads((HERE.parent/'native-provider-hardening/release-contract.json').read_text())
        self.assertEqual(len(a.EXPECTED_SOURCES),18);self.assertEqual(a.EXPECTED_SOURCES,{**contract['source_hashes'],**contract['readiness_hashes']})

class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.work=Path(self.tmp.name);self.work.chmod(0o700);self.clock=Clock()
        (self.work/'build-receipt.json').write_text(json.dumps({'state':'verified','image_id':a.RETAINED_IMAGE}))
        self.payload={'runtime_diagnostics.py':base64.b64encode((HERE/'runtime_diagnostics.py').read_bytes()).decode(),'expected-source-hashes.json':base64.b64encode(json.dumps(a.EXPECTED_SOURCES).encode()).decode()}
        self.baseline={'protected':'healthy'};self.calls=[];self.inspections=0
        self.inspector=types.SimpleNamespace(verify=self.verify)
    def verify(self,*args):
        self.inspections+=1
        return {'base':{'id':a.RETAINED_IMAGE},'hashes':dict(a.EXPECTED_SOURCES),'process_exited':True,'exit_code':0}
    def docker(self,args,**kwargs):
        self.calls.append(args)
        if args[0]=='network':return 'unchanged networks'
        if args[0]=='volume':return 'unchanged volumes'
        if args[0]=='ps':return ''
        if args[0]=='create':return 'c'*64
        if args[0]=='inspect':
            if args[2]=='{{.State.Running}}':return 'false'
            if args[2]=='{{.State.ExitCode}}':return '0'
            fixture=self.work/'runtime-attempt-synthetic-attempt-02/fixture'
            mounts=[{'Type':'bind','Source':str(src),'Destination':dst,'RW':False} for src,dst in [(fixture,'/fixture'),(fixture/'passwd','/etc/passwd'),(fixture/'group','/etc/group')]]
            return json.dumps({'network':'none','ports':{},'privileged':False,'readonly':True,'mounts':mounts,'memory':1536*1024**2,'pids':256})
        if args[0]=='logs':return json.dumps({'bootstrap':{},'boundary':'synthetic fixture','success':True})
        return ''
    def execute(self,load=.5,memory=3*1024**3,disk=2*1024**3):
        original_stabilize=a.stabilize;original_verified=a.verified
        def stabilize(*args,**kw):return original_stabilize(*args,**kw,clock=self.clock,sleep=self.clock.sleep)
        def verified(*args,**kw):return original_verified(*args,**kw,clock=self.clock)
        with patch.object(runner,'load_host_helpers',return_value=(a,self.inspector)),patch.object(runner,'production',return_value=self.baseline),patch.object(runner,'probe',return_value={'image_id':a.RETAINED_IMAGE,'production':self.baseline}),patch.object(runner,'docker',side_effect=self.docker),patch.object(a,'measure',side_effect=lambda *args:{'memory_available_bytes':memory,'disk_available_bytes':disk,'load':[load,1,1],'monotonic':self.clock()}),patch.object(a,'stabilize',side_effect=stabilize),patch.object(a,'verified',side_effect=verified),contextlib.redirect_stdout(io.StringIO()):
            return runner.main(self.payload,self.work,a.RETAINED_IMAGE,attempt_id='synthetic-attempt-02')
    def test_creation_only_after_one_scan_fixed_wait_and_one_admission(self):
        result=self.execute();self.assertTrue(result['cleaned']);self.assertEqual(self.inspections,1);self.assertEqual(sum(self.clock.sleeps),120)
        self.assertEqual(sum(c[0]=='create' for c in self.calls),1);self.assertEqual(sum(c[0]=='start' for c in self.calls),1)
        rows=[json.loads(l) for l in (self.work/'runtime-attempt-synthetic-attempt-02/admission.jsonl').read_text().splitlines()]
        events=[r['event'] for r in rows];self.assertEqual(events.count('admission_decision'),1);self.assertLess(events.index('admission_decision'),events.index('container_creation_intent'))
        create=next(c for c in self.calls if c[0]=='create')
        for flag in ['--network=none','--read-only','--memory=1536m','--memory-swap=1536m','--cpus=1','--pids-limit=256','--restart=no']:self.assertIn(flag,create)
    def test_failed_admission_never_creates_or_retries(self):
        with self.assertRaisesRegex(a.Refused,'final_capacity_refused'):self.execute(load=5)
        self.assertEqual(self.inspections,1);self.assertFalse(any(c[0] in ['create','start'] for c in self.calls))
    def test_memory_and_disk_refusals_never_create(self):
        with self.assertRaisesRegex(a.Refused,'final_capacity_refused'):self.execute(memory=a.MEMORY_MIN-1)
        self.assertFalse(any(c[0] in ['create','start'] for c in self.calls))
    def test_disk_refusal_never_creates(self):
        with self.assertRaisesRegex(a.Refused,'final_capacity_refused'):self.execute(disk=a.DISK_MIN-1)
        self.assertFalse(any(c[0] in ['create','start'] for c in self.calls))
    def test_interrupted_main_keeps_exclusive_identity_and_failure_receipt(self):
        self.clock.interrupt=True
        with self.assertRaises(KeyboardInterrupt):self.execute()
        self.assertFalse(any(c[0] in ['create','start'] for c in self.calls))
        journal=self.work/'runtime-attempt-synthetic-attempt-02/admission.jsonl'
        rows=[json.loads(l) for l in journal.read_text().splitlines()]
        self.assertEqual(rows[-1]['details']['reason'],'interrupted')
        before=journal.read_bytes()
        with self.assertRaisesRegex(a.Refused,'duplicate_attempt_identity'):self.execute()
        self.assertEqual(journal.read_bytes(),before);self.assertEqual(self.inspections,1)
    def test_known_created_container_is_cleaned_if_receipt_write_fails(self):
        original=a.Journal.record
        def record(journal,event,details):
            if event=='container_created':raise OSError('synthetic_receipt_failure')
            return original(journal,event,details)
        with patch.object(a.Journal,'record',autospec=True,side_effect=record),self.assertRaises(OSError):self.execute()
        self.assertEqual(sum(c[0]=='create' for c in self.calls),1)
        self.assertEqual(sum(c[0]=='rm' for c in self.calls),1)
        self.assertFalse(any(c[0]=='start' for c in self.calls))
    def test_incomplete_verification_never_creates(self):
        self.inspector.verify=lambda *args:{'process_exited':False}
        with self.assertRaisesRegex(a.Refused,'verification_incomplete'):self.execute()
        self.assertFalse(any(c[0]=='create' for c in self.calls));self.assertEqual(self.clock.sleeps,[])
    def test_host_helpers_require_exact_reviewed_bytes(self):
        payload={'host/'+name:base64.b64encode((HERE/name).read_bytes()).decode() for name in runner.HOST_HELPERS}
        modules=runner.load_host_helpers(payload);self.assertEqual(modules[0].EXPECTED_SOURCES,a.EXPECTED_SOURCES)
        payload['host/runtime_admission.py']=base64.b64encode(b'UNAPPROVED').decode()
        with self.assertRaisesRegex(RuntimeError,'host_helper_source_drift'):runner.load_host_helpers(payload)
    def test_post_admission_image_drift_never_creates(self):
        calls=0
        def check(*args):
            nonlocal calls
            calls+=1
            # stabilize probe is mocked at this boundary; final recheck differs.
            return {'image_id':'changed','production':self.baseline}
        with patch.object(runner,'probe',side_effect=check):
            # execute installs its own probe; exercise the managed last check via
            # an admission stub that already validated its synthetic interval.
            with patch.object(a,'stabilize',return_value={'admitted':True}),patch.object(runner,'load_host_helpers',return_value=(a,self.inspector)),patch.object(runner,'production',return_value=self.baseline),patch.object(runner,'docker',side_effect=self.docker):
                with self.assertRaisesRegex(a.Refused,'post_admission_drift'):runner.main(self.payload,self.work,a.RETAINED_IMAGE,attempt_id='synthetic-attempt-03')
        self.assertFalse(any(c[0]=='create' for c in self.calls))

class VerificationExit(unittest.TestCase):
    def exercise(self,exit_code):
        import hashlib,tarfile
        import inspect_image
        def archive(files):
            result=io.BytesIO()
            with tarfile.open(fileobj=result,mode='w') as tar:
                for name,data in files.items():
                    item=tarfile.TarInfo(name);item.size=len(data);tar.addfile(item,io.BytesIO(data))
            return result.getvalue()
        data=b'approved synthetic source';layer=archive({'app/core/fixture.py':data})
        outer=archive({'fixture/layer.tar':layer,'manifest.json':json.dumps([{'Layers':['fixture/layer.tar']}]).encode()})
        waited=[]
        def wait(**kwargs):waited.append(True);return exit_code
        process=types.SimpleNamespace(stdout=io.BytesIO(outer),wait=wait,poll=lambda:exit_code)
        with patch.object(inspect_image.subprocess,'check_output',return_value=json.dumps({'id':a.RETAINED_IMAGE,'size':123}).encode()),patch.object(inspect_image.subprocess,'Popen',return_value=process) as spawn:
            if exit_code:
                with self.assertRaisesRegex(RuntimeError,'image_save_failed'):inspect_image.verify(a.RETAINED_IMAGE,{'core/fixture.py':hashlib.sha256(data).hexdigest()})
                result=None
            else:result=inspect_image.verify(a.RETAINED_IMAGE,{'core/fixture.py':hashlib.sha256(data).hexdigest()})
        self.assertEqual(waited,[True]);spawn.assert_called_once();return result
    def test_verification_result_requires_reaped_successful_export(self):
        result=self.exercise(0);self.assertTrue(result['process_exited']);self.assertEqual(result['exit_code'],0)
    def test_export_failure_cannot_produce_completion_evidence(self):self.assertIsNone(self.exercise(1))

if __name__=='__main__':unittest.main()
