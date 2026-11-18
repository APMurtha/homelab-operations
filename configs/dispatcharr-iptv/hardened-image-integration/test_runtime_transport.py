"""Actual detached POSIX fixture processes, never Docker or the application.

A temporary test copy pins a synthetic runner instead of the release runner.
There is no synthetic-runner option in the shipped production CLI.
"""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('transport',HERE/'runtime_transport.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
FAKE='''import base64,json,os,time,signal
from pathlib import Path
HOST_HELPERS={}
def production(deadline=None):return {'fixture':'healthy'}
def docker(args,timeout=5):
 if args[0]=='ps':
  p=Path(WORK)/'retained-container.json'
  return 'c'*64 if p.exists() else ''
 return 'unchanged'
def main(payload,work,image,attempt_id=None):
 global WORK
 WORK=str(work)
 control=json.loads(base64.b64decode(payload['fixture-control.json']))
 target=Path(work)/('runtime-attempt-'+attempt_id);target.mkdir(mode=0o700)
 def save(name,value):
  p=target/name;p.write_text(json.dumps(value));p.chmod(0o600)
 save('admission.jsonl',{'event':'verification_completed','details':{}})
 print('SECRET_PASSWORD https://user:secret@private.invalid/token');__import__('sys').stderr.write('SECRET_TOKEN')
 (Path(work)/'fixture-ready').write_text('ready')
 while control['mode']=='hold' and not (Path(work)/'release').exists():time.sleep(.01)
 if control['mode']=='ignore-term':
  signal.signal(signal.SIGTERM,signal.SIG_IGN)
  while True:time.sleep(.01)
 if control['mode']=='die':os._exit(7)
 if control['mode']=='uncertain-create':
  (Path(work)/'retained-container.json').write_text('{}');os._exit(8)
 if control['mode']=='fail':raise RuntimeError('SECRET_PASSWORD')
 (target/'admission.jsonl').write_text(json.dumps({'event':'container_created','details':{'container_id':'c'*64}})+'\\n')
 value={'image_id':image,'attempt_id':attempt_id,'container_id':'c'*64,'runtime':{'success':True},'cleaned':True,'production_unchanged':True,'networks_unchanged':True,'volumes_unchanged':True}
 save('runtime-receipt.json',value);return value
'''
# Freshly imported fixture modules need a fixed work path for read-only reconciliation.

def until(fn,seconds=4):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  value=fn()
  if value:return value
  time.sleep(.01)
 raise AssertionError('synthetic_fixture_deadline')

class Transport(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.root.chmod(0o700)
  self.work=self.root/'work';self.work.mkdir(mode=0o700);self.attempt='synthetic-transport-01'
  self.fake_source=FAKE.replace("HOST_HELPERS={}\n",'HOST_HELPERS={}\nWORK='+repr(str(self.work))+'\n')
  self.runner=self.root/'runner.py';self.runner.write_text(self.fake_source);self.runner.chmod(0o600)
  self.fake_hash=t.digest(self.runner.read_bytes())
  self.script=self.root/'transport.py'
  source=(HERE/'runtime_transport.py').read_text().replace(t.APPROVED_RUNNER_SHA256,self.fake_hash)
  source=source.replace('HEARTBEAT_SECONDS=5','HEARTBEAT_SECONDS=0.02').replace('TERM_GRACE_SECONDS=10','TERM_GRACE_SECONDS=0.05')
  self.script.write_text(source);self.script.chmod(0o600)
  spec=importlib.util.spec_from_file_location('fixture_transport',self.script);self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
  self.job=self.work/('transport-attempt-'+self.attempt)
  self.addCleanup(self.clean_processes)
 def clean_processes(self):
  (self.work/'release').touch()
  if not self.job.exists():return
  for filename in ['runner.claim','supervisor.claim']:
   try:
    claim=self.module.read(self.job/filename)
    if self.module.same_process(claim):os.kill(claim['pid'],signal.SIGKILL)
   except (OSError,ValueError):pass
 def payload(self,mode='complete'):
  p={'fixture-control.json':base64.b64encode(json.dumps({'mode':mode}).encode()).decode()}
  for name in t.PAYLOAD_CORE_PINS:p[name]=base64.b64encode((HERE/name).read_bytes()).decode()
  raw=json.dumps(p).encode();path=self.root/'payload.json';path.write_bytes(raw);path.chmod(0o600);return path,t.digest(raw)
 def launch(self,mode='complete'):
  payload,h=self.payload(mode)
  return self.module.launch(self.work,self.attempt,payload,h,self.runner)
 def status(self):return self.module.status(self.work,self.attempt)
 def finished(self):
  return until(lambda:(v if v['state'] in ['completed','failed'] else None) if (v:=self.status()) else None)
 def wait_ready(self):until(lambda:(self.work/'fixture-ready').exists())
 def test_normal_completion_is_reconciled_and_private(self):
  self.launch();self.assertEqual(self.finished()['state'],'completed')
  for p in self.job.iterdir():
   if p.is_file():self.assertEqual(p.stat().st_mode&0o777,0o600)
  text=''.join(p.read_text() for p in self.job.iterdir() if p.name in ['transport.log','runner-exit.json','state.json','completion.json'])
  self.assertNotIn('SECRET',text);self.assertNotIn('private.invalid',text)
 def test_duplicate_launch_refuses_without_overwriting_or_second_process(self):
  self.launch('hold');self.wait_ready();before=(self.job/'launch.json').read_bytes()
  payload,h=self.payload('hold')
  with patch.object(self.module.subprocess,'Popen') as spawn,self.assertRaisesRegex(self.module.Refused,'duplicate_transport_identity'):
   self.module.launch(self.work,self.attempt,payload,h,self.runner)
  spawn.assert_not_called();self.assertEqual(before,(self.job/'launch.json').read_bytes())
 def test_concurrent_launchers_only_reserve_one_attempt(self):
  payload,h=self.payload('hold')
  command=[sys.executable,'-B',str(self.script),'launch','--work',str(self.work),'--attempt-id',self.attempt,'--payload',str(payload),'--payload-sha256',h,'--runner',str(self.runner)]
  children=[subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) for _ in range(2)]
  returns=[]
  for child in children:child.communicate(timeout=3);returns.append(child.returncode)
  self.assertEqual(sorted(returns),[0,1]);self.wait_ready()
  self.assertEqual(len(list(self.work.glob('transport-attempt-*'))),1)
 def test_partial_reservation_never_becomes_implicit_permission_to_resume(self):
  self.job.mkdir(mode=0o700);self.assertEqual(self.status()['state'],'uncertain')
  payload,h=self.payload()
  with self.assertRaisesRegex(self.module.Refused,'duplicate_transport_identity'):self.module.launch(self.work,self.attempt,payload,h,self.runner)
 def test_missing_runner_identity_is_uncertain(self):
  self.launch();self.finished();(self.job/'runner.claim').unlink()
  self.assertEqual(self.status()['reason'],'runner_identity_missing')
 def test_production_conflict_never_reports_clean_completion(self):
  self.launch();self.finished();value=self.module.read(self.job/'baseline.json');value['production']={'fixture':'changed'};self.module.replace(self.job/'baseline.json',value)
  result=self.status();self.assertEqual(result['state'],'uncertain');self.assertFalse(result['cleanup_complete'])
 def test_runtime_receipt_conflict_is_uncertain(self):
  self.launch();self.finished();path=self.work/('runtime-attempt-'+self.attempt)/'runtime-receipt.json';value=self.module.read(path);value['cleaned']=False;self.module.replace(path,value)
  self.assertEqual(self.status()['reason'],'runtime_receipt_conflict')
 def test_core_payload_source_drift_refuses_before_reservation(self):
  path,h=self.payload();value=json.loads(path.read_text());value['runtime_test.py']=base64.b64encode(b'unreviewed').decode();raw=json.dumps(value).encode();path.write_bytes(raw)
  with self.assertRaisesRegex(self.module.Refused,'payload_source_drift'):self.module.launch(self.work,self.attempt,path,self.module.digest(raw),self.runner)
  self.assertFalse(self.job.exists())
 def test_consumed_runtime_identity_refuses_before_launch(self):
  (self.work/('runtime-attempt-'+self.attempt)).mkdir(mode=0o700);payload,h=self.payload()
  with self.assertRaisesRegex(self.module.Refused,'runtime_identity_already_consumed'):self.module.launch(self.work,self.attempt,payload,h,self.runner)
  self.assertFalse(self.job.exists())
 def test_launching_ssh_parent_hangup_does_not_stop_detached_job(self):
  payload,h=self.payload('hold')
  code="import importlib.util,time; s=importlib.util.spec_from_file_location('fixture',"+repr(str(self.script))+"); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.launch("+repr(str(self.work))+","+repr(self.attempt)+","+repr(str(payload))+","+repr(h)+","+repr(str(self.runner))+"); print('launched',flush=True); time.sleep(10)"
  parent=subprocess.Popen([sys.executable,'-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
  self.addCleanup(lambda:parent.kill() if parent.poll() is None else None)
  self.assertEqual(parent.stdout.readline(),b'launched\n');self.wait_ready()
  parent.send_signal(signal.SIGHUP);parent.wait(timeout=2)
  self.assertEqual(self.status()['state'],'running')
  (self.work/'release').touch();self.assertEqual(self.finished()['state'],'completed');parent.stdout.close()
 def test_unexpected_runner_exit_is_failed_only_after_reconciliation(self):
  self.launch('die');value=self.finished();self.assertEqual(value['state'],'failed');self.assertTrue(value['cleanup_complete'])
  self.assertFalse((self.job/'runner-exit.json').exists())
 def test_exception_does_not_log_exception_body(self):
  self.launch('fail');self.assertEqual(self.finished()['state'],'failed')
  self.assertNotIn('SECRET',(self.job/'runner-exit.json').read_text())
 def test_uncertain_creation_never_claims_cleanup_complete(self):
  self.launch('uncertain-create');until(lambda:(self.job/'completion.json').exists());until(lambda:not self.module.same_process(self.module.read(self.job/'supervisor.claim')))
  value=self.status();self.assertEqual(value['state'],'uncertain');self.assertFalse(value['cleanup_complete']);self.assertEqual(value['reason'],'owned_or_conflicting_container_retained')
 def test_supervisor_crash_does_not_kill_runner_or_trigger_restart(self):
  self.launch('hold');self.wait_ready();claim=self.module.read(self.job/'supervisor.claim');os.kill(claim['pid'],signal.SIGKILL)
  until(lambda:not self.module.same_process(claim))
  self.assertEqual(self.status()['reason'],'supervisor_missing_runner_still_alive')
  (self.work/'release').touch();self.assertEqual(self.finished()['state'],'completed')
 def test_unknown_attempt_status_has_no_launch_or_filesystem_writes(self):
  before=set(self.work.iterdir())
  with patch.object(self.module.subprocess,'Popen') as spawn:self.assertEqual(self.status()['state'],'uncertain')
  spawn.assert_not_called();self.assertEqual(before,set(self.work.iterdir()))
 def test_terminal_status_polling_is_read_only(self):
  self.launch();self.finished()
  before={str(p): (p.read_bytes(),p.stat().st_mtime_ns) for p in self.work.rglob('*') if p.is_file()}
  with patch.object(self.module.subprocess,'Popen') as spawn:
   for _ in range(3):self.assertEqual(self.status()['state'],'completed')
  spawn.assert_not_called();self.assertEqual(before,{str(p):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.work.rglob('*') if p.is_file()})
 def test_stale_status_is_uncertain_not_a_retry(self):
  self.launch('hold');self.wait_ready();state=self.module.read(self.job/'state.json');state['heartbeat_monotonic']-=100
  # Pause only this synthetic supervisor so it cannot refresh the fixture state.
  claim=self.module.read(self.job/'supervisor.claim');os.kill(claim['pid'],signal.SIGSTOP)
  try:
   self.module.replace(self.job/'state.json',state);self.assertEqual(self.status()['reason'],'stale_or_inconsistent_heartbeat')
  finally:os.kill(claim['pid'],signal.SIGCONT)
 def test_missing_completion_proof_cannot_pass(self):
  self.launch();self.finished();(self.job/'runner-exit.json').unlink()
  self.assertEqual(self.status()['state'],'failed')
 def test_missing_application_receipt_is_uncertain(self):
  self.launch();self.finished();(self.work/('runtime-attempt-'+self.attempt)/'runtime-receipt.json').unlink()
  self.assertEqual(self.status()['state'],'uncertain')
 def test_wrong_boot_or_mutated_snapshot_is_uncertain(self):
  self.launch();self.finished();x=self.module.read(self.job/'launch.json');x['boot_id']='wrong';self.module.replace(self.job/'launch.json',x)
  self.assertEqual(self.status()['state'],'uncertain')
 def test_runner_and_payload_drift_refuse_before_reservation(self):
  payload,h=self.payload()
  with self.assertRaisesRegex(self.module.Refused,'payload_digest_mismatch'):self.module.launch(self.work,self.attempt,payload,'f'*64,self.runner)
  self.assertFalse(self.job.exists())
  self.runner.write_text('unreviewed')
  with self.assertRaisesRegex(self.module.Refused,'runner_source_drift'):self.module.launch(self.work,self.attempt,payload,h,self.runner)
 def test_status_unavailable_docker_is_uncertain(self):
  self.launch();self.finished()
  with patch.object(self.module,'reconcile',side_effect=RuntimeError('SECRET')):
   value=self.status();self.assertEqual(value['state'],'uncertain');self.assertNotIn('SECRET',json.dumps(value))
 def test_bounded_outer_deadline_retains_uncertain_candidate(self):
  self.script.write_text(self.script.read_text().replace('JOB_SECONDS=1200','JOB_SECONDS=0.3'));self.script.chmod(0o600)
  # Module launch snapshots this test-only transport version; status verifies it.
  self.launch('ignore-term');until(lambda:(self.job/'completion.json').exists())
  until(lambda:not self.module.same_process(self.module.read(self.job/'supervisor.claim')))
  self.assertEqual(self.module.read(self.job/'completion.json')['reason'],'outer_deadline')
  self.assertEqual(self.finished()['state'],'failed')
 def test_pid_reuse_never_signals_unrelated_process(self):
  with patch.object(self.module,'same_process',return_value=False),patch.object(self.module.os,'killpg') as kill:
   self.assertFalse(self.module.signal_owned_group({'pid':123},signal.SIGTERM));kill.assert_not_called()
 def test_invalid_identity_is_not_reflected_in_status(self):
  value=self.module.status(self.work,'https://user:SECRET@private.invalid')
  self.assertEqual(value['state'],'uncertain');self.assertNotIn('SECRET',json.dumps(value));self.assertIsNone(value['attempt_id'])
 def test_symlink_private_input_is_rejected(self):
  payload,h=self.payload();link=self.root/'link.json';link.symlink_to(payload)
  with self.assertRaises(OSError):self.module.launch(self.work,self.attempt,link,h,self.runner)
 def test_previous_receipts_remain_intact(self):
  p=self.work/'previous-exclusive.intent';p.write_text('retained');p.chmod(0o600)
  self.launch();self.finished();self.assertEqual(p.read_text(),'retained')

class ReleasePins(unittest.TestCase):
 def test_release_runner_and_core_sources_are_unchanged(self):
  self.assertEqual(t.APPROVED_RUNNER_SHA256,t.digest((HERE/'run_runtime.py').read_bytes()))
  for name,h in t.PAYLOAD_CORE_PINS.items():self.assertEqual(h,t.digest((HERE/name).read_bytes()))
 def test_cli_parse_errors_do_not_echo_secret_arguments(self):
  result=subprocess.run([sys.executable,'-B',str(HERE/'runtime_transport.py'),'status','--password','SECRET_TOKEN'],capture_output=True,text=True,timeout=3)
  self.assertEqual(result.returncode,2);self.assertNotIn('SECRET_TOKEN',result.stdout+result.stderr)
 def test_no_lifecycle_or_status_launch_surface(self):
  import ast
  tree=ast.parse((HERE/'runtime_transport.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='status')
  text=ast.unparse(fn)
  for forbidden in ['Popen(', 'launch(', '.main(', '.mkdir(', 'killpg(']:self.assertNotIn(forbidden,text)

if __name__=='__main__':unittest.main()
