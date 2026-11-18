"""Run only an explicitly owned network-none test container, never production.
Payload contains the test harness and approved client source, no credentials.
"""
import base64
import hashlib
import importlib.util
import types
import json
import re
from pathlib import Path
import subprocess
import time

DOCKER=['docker','-H','unix:///var/run/docker.sock']
IMAGE=None  # Requires the separately reviewed successful build receipt, never the failed image.
OWNER='1124d96'
HOST_HELPERS={'runtime_admission.py': '7e029a8fb42ec2b813a0d58fd1a0e399e2b6a9a116741b570e275a9d674bee44', 'inspect_image.py': '67549e04e19b0239229c878984f61a6b44f5e944dc1c4a5950f678e2b1872822'}

def docker(args,timeout=60):
    result=subprocess.run(DOCKER+args,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError('test_docker_operation_failed:'+args[0])
    return result.stdout.strip()

def production(deadline=None):
    def budget():
        if deadline is None:return 60
        left=deadline-time.monotonic()
        if left<=0:raise RuntimeError('stabilization_timeout')
        return min(5,left)
    ids=docker(['ps','-aq'],timeout=budget()).split()
    data=json.loads(docker(['inspect',*ids],timeout=budget())) if ids else []
    rows={}
    for c in data:
        name=c['Name'].lstrip('/')
        rows[name]={'id':c['Id'],'image':c['Image'],'started':c['State']['StartedAt'],
            'restarts':c['RestartCount'],'health':c['State'].get('Health',{}).get('Status'),
            'status':c['State']['Status'],'configuration_sha256':hashlib.sha256(json.dumps(
                {k:c[k] for k in ['Config','HostConfig','Mounts']},sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    for name in ['dispatcharr','rivendell-iptv-vpn','rivendell-iptv-relay','rivendell-iptv-gateway','jellyfin']:
        if rows.get(name,{}).get('health')!='healthy':raise RuntimeError('production_health_drift')
    return rows


def probe(deadline):
    left=deadline-time.monotonic()
    if left<=0:raise RuntimeError('stabilization_timeout')
    image=docker(['image','inspect',IMAGE,'--format','{{.Id}}'],timeout=min(5,left))
    return {'image_id':image,'production':production(deadline)}


def load_host_helpers(payload):
    modules=[]
    for name,wanted in HOST_HELPERS.items():
        try:source=base64.b64decode(payload['host/'+name],validate=True)
        except (KeyError,ValueError,TypeError):raise RuntimeError('reviewed_host_helper_required') from None
        if hashlib.sha256(source).hexdigest()!=wanted:raise RuntimeError('host_helper_source_drift')
        module=types.ModuleType('_reviewed_'+name.removesuffix('.py'));module.__file__='<reviewed_host_helper>'
        exec(compile(source,module.__file__,'exec'),module.__dict__);modules.append(module)
    return modules


def prepare_fixture(work,payload):
    # Only synthetic/public test source enters this bind; transport parent stays private.
    fixture=work/'fixture';fixture.mkdir(mode=0o755)
    for name,data in payload.items():
        if name.startswith('/') or '..' in Path(name).parts:raise RuntimeError('unsafe_fixture_path')
        path=fixture/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(data,validate=True));path.chmod(0o644)
    for directory in [fixture,*[p for p in fixture.rglob('*') if p.is_dir()]]:directory.chmod(0o755)
    return fixture

def main(payload,work,image=None,*,attempt_id=None):
    global IMAGE
    if not isinstance(image,str) or image!='sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439':raise RuntimeError('new_accepted_test_image_required')
    if 'runtime_diagnostics.py' not in payload:raise RuntimeError('diagnostic_fixture_module_required')
    admission,inspector=load_host_helpers(payload)
    IMAGE=image;work=Path(work)
    journal=admission.Journal(work,attempt_id)
    try:return managed(payload,work,image,admission,inspector,journal)
    except BaseException as error:
        reason=str(error) if isinstance(error,admission.Refused) else 'interrupted' if isinstance(error,(KeyboardInterrupt,SystemExit)) else 'runner_failure'
        journal.record('attempt_failed',{'reason':reason,'container_state':'inspect_creation_records_before_any_recovery'})
        raise


def managed(payload,work,image,admission,inspector,journal):
    receipt=json.loads((work/'build-receipt.json').read_text())
    if receipt.get('image_id')!=image or receipt.get('state')!='verified':raise admission.Refused('built_image_not_verified')
    try:expected=json.loads(base64.b64decode(payload['expected-source-hashes.json'],validate=True))
    except (KeyError,ValueError,TypeError):raise admission.Refused('expected_source_fixture_required') from None
    if expected!=admission.EXPECTED_SOURCES:raise admission.Refused('expected_source_fixture_drift')
    before=production();networks=docker(['network','ls','--no-trunc','--format','{{.ID}} {{.Name}}'])
    volumes=docker(['volume','ls','--format','{{json .}}'])
    name='dispatcharr-native-runtime-'+journal.attempt_id
    if docker(['ps','-aq','--filter','name=^/'+name+'$']):raise admission.Refused('test_name_conflict')
    attempt=journal.path
    # Review helpers stay on the host; the synthetic container payload is unchanged.
    fixture=prepare_fixture(attempt,{k:v for k,v in payload.items() if not k.startswith('host/')})
    verification=admission.verified(inspector.verify,image,journal.attempt_id,journal)
    decision=admission.stabilize(verification,image,journal.attempt_id,before,probe,
        lambda:admission.measure(work),journal)
    # Cheap current identity/health/fixture checks, no new capacity decision or scan.
    current=probe(time.monotonic()+10)
    if current!={'image_id':image,'production':before}:raise admission.Refused('post_admission_drift')
    if json.loads(base64.b64decode(payload['expected-source-hashes.json'],validate=True))!=admission.EXPECTED_SOURCES:raise admission.Refused('source_contract_changed')
    for relative,data in payload.items():
        if relative.startswith('host/'):continue
        if (fixture/relative).read_bytes()!=base64.b64decode(data,validate=True):raise admission.Refused('fixture_drift')
    spec=importlib.util.spec_from_file_location('_owned_runtime_diagnostics',fixture/'runtime_diagnostics.py')
    diagnostics=importlib.util.module_from_spec(spec);spec.loader.exec_module(diagnostics)
    journal.record('container_creation_intent',{'name':name,'image_id':image})
    pk=docker(['create','--pull=never','--name',name,'--label','dispatcharr.integration.owner='+OWNER,'--label','dispatcharr.integration.attempt='+journal.attempt_id,'--network=none','--read-only','--restart=no','--log-driver=json-file','--log-opt=max-size=1m','--log-opt=max-file=2','--cap-drop=ALL','--cap-add=CHOWN','--cap-add=DAC_OVERRIDE','--cap-add=FOWNER','--cap-add=SETUID','--cap-add=SETGID','--cap-add=KILL','--security-opt','no-new-privileges:true','--memory=1536m','--memory-swap=1536m','--cpus=1','--pids-limit=256','--sysctl','net.ipv4.ip_unprivileged_port_start=0','--tmpfs','/data:rw,nosuid,nodev,size=512m','--tmpfs','/test-state:rw,nosuid,nodev,mode=0700,size=256m','--tmpfs','/run:rw,nosuid,nodev,size=32m','--tmpfs','/tmp:rw,nosuid,nodev,mode=1777,size=128m','--tmpfs','/guard-status:rw,nosuid,nodev,mode=0755,size=1m','--mount','type=bind,src='+str(fixture/'passwd')+',dst=/etc/passwd,readonly','--mount','type=bind,src='+str(fixture/'group')+',dst=/etc/group,readonly','--mount','type=bind,src='+str(fixture)+',dst=/fixture,readonly','--entrypoint','/dispatcharrpy/bin/python',IMAGE,'-B','/fixture/runtime_test.py'])
    result={'admission':decision,'attempt_id':journal.attempt_id,'image_id':IMAGE,'container_id':pk,'owner':OWNER,'attempt_directory':str(attempt)}
    try:
        journal.record('container_created',{'container_id':pk})
        config=json.loads(docker(['inspect','--format','{"network":{{json .HostConfig.NetworkMode}},"ports":{{json .HostConfig.PortBindings}},"privileged":{{json .HostConfig.Privileged}},"readonly":{{json .HostConfig.ReadonlyRootfs}},"mounts":{{json .Mounts}},"memory":{{json .HostConfig.Memory}},"pids":{{json .HostConfig.PidsLimit}}}',pk]))
        binds=[m for m in config['mounts'] if m['Type']=='bind']
        expected={str(fixture):'/fixture',str(fixture/'passwd'):'/etc/passwd',str(fixture/'group'):'/etc/group'}
        if (config['network']!='none' or config['ports'] not in ({},None) or config['privileged'] or not config['readonly'] or len(binds)!=3 or {m['Source']:m['Destination'] for m in binds}!=expected or any(m['RW'] for m in binds) or any(m['Type']=='volume' for m in config['mounts'])):raise RuntimeError('uncertain_test_isolation_stop')
        result['isolation']=config
        docker(['start',pk]);deadline=time.monotonic()+240
        while docker(['inspect','--format','{{.State.Running}}',pk])=='true':
            if time.monotonic()>deadline:
                result['timeout']=True;docker(['stop','--time','10',pk]);break
            time.sleep(2)
        result['exit_code']=int(docker(['inspect','--format','{{.State.ExitCode}}',pk]))
        # Only synthetic test logs/data are read. No production exec or data access.
        logs=docker(['logs','--tail','1000',pk])[-2*1024*1024:];(attempt/'runtime.log').write_text(logs)
        # tmpfs disappears when the test container exits. Recover the JSON
        # printed before exit rather than copying vanished temporary data.
        parsed=None
        for line in reversed(logs.splitlines()):
            try: value=json.loads(line)
            except ValueError: continue
            if isinstance(value,dict) and 'bootstrap' in value and 'boundary' in value:
                parsed=value;break
        recovered=diagnostics.recover_records(logs)
        result['diagnostics']=recovered
        if parsed is None:
            parsed={'bootstrap':{},'boundary':'network-none; incomplete execution','success':False,'bootstrap_error':'runtime_result_missing','diagnostics':recovered}
        if recovered['last_refusal'] is not None:
            parsed['success']=False;parsed['failure_classification']='socket_audit_refusal'
        if result['exit_code']!=0:
            parsed['success']=False;parsed.setdefault('failure_classification','container_abnormal_exit')
        (attempt/'diagnostics.json').write_text(json.dumps(recovered))
        result['runtime']=parsed
        (attempt/'runtime-result.json').write_text(json.dumps(parsed))
    finally:
        # Only the exact container created above is stopped/removed.
        if docker(['inspect','--format','{{.State.Running}}',pk])=='true':docker(['stop','--time','10',pk])
        docker(['rm',pk])
        result['cleaned']=True
        result['production_unchanged']=production()==before
        result['volumes_unchanged']=docker(['volume','ls','--format','{{json .}}'])==volumes
        result['networks_unchanged']=docker(['network','ls','--no-trunc','--format','{{.ID}} {{.Name}}'])==networks
        (attempt/'runtime-receipt.json').write_text(json.dumps(result))
    journal.record('runtime_finished',{'success':result.get('runtime',{}).get('success',False),'cleaned':result.get('cleaned',False),'production_unchanged':result.get('production_unchanged',False)})
    print(json.dumps(result))
    return result
