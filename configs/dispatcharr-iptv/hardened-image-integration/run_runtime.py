"""Run only an explicitly owned network-none test container, never production.
Payload contains the test harness and approved client source, no credentials.
"""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import time

DOCKER=['docker','-H','unix:///var/run/docker.sock']
NAME='dispatcharr-native-runtime-1124d96'
IMAGE='sha256:26c93e71dd431127ef72c651bfe0ad3f7431cef7c135749002833f1fc1524c78'
OWNER='1124d96'

def docker(args,timeout=60):
    result=subprocess.run(DOCKER+args,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError('test_docker_operation_failed:'+args[0]+':'+result.stderr[:200])
    return result.stdout.strip()

def production():
    rows={}
    for name in ['dispatcharr','rivendell-iptv-vpn','rivendell-iptv-relay','rivendell-iptv-gateway','jellyfin']:
        rows[name]=docker(['inspect','--format','{{.Id}} {{.Image}} {{.State.StartedAt}} {{.RestartCount}} {{.State.Health.Status}}',name])
        if not rows[name].endswith('healthy'):raise RuntimeError('production_health_drift')
    return rows

def main(payload,work):
    work=Path(work)
    receipt=json.loads((work/'build-receipt.json').read_text())
    if receipt.get('image_id')!=IMAGE or receipt.get('state')!='verified':raise RuntimeError('built_image_not_verified')
    if docker(['image','inspect',IMAGE,'--format','{{.Id}}'])!=IMAGE:raise RuntimeError('image_drift')
    memory=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    if memory<2*1024**3 or __import__('os').getloadavg()[0]>2:raise RuntimeError('test_capacity_gate_failed')
    before=production();networks=docker(['network','ls','--no-trunc','--format','{{.ID}} {{.Name}}'])
    if subprocess.run(DOCKER+['inspect',NAME],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:raise RuntimeError('test_name_conflict')
    fixture=work/'fixture';fixture.mkdir(mode=0o700)
    for name,data in payload.items():
        if name.startswith('/') or '..' in Path(name).parts:raise RuntimeError('unsafe_fixture_path')
        path=fixture/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(data,validate=True));path.chmod(0o644)
    pk=docker(['create','--pull=never','--name',NAME,'--label','dispatcharr.integration.owner='+OWNER,'--network=none','--read-only','--restart=no','--cap-drop=ALL','--cap-add=CHOWN','--cap-add=DAC_OVERRIDE','--cap-add=FOWNER','--cap-add=SETUID','--cap-add=SETGID','--cap-add=KILL','--security-opt','no-new-privileges:true','--memory=1536m','--memory-swap=1536m','--cpus=1','--pids-limit=256','--sysctl','net.ipv4.ip_unprivileged_port_start=0','--tmpfs','/data:rw,nosuid,nodev,size=512m','--tmpfs','/test-state:rw,nosuid,nodev,mode=0700,size=256m','--tmpfs','/run:rw,nosuid,nodev,size=32m','--tmpfs','/tmp:rw,nosuid,nodev,mode=1777,size=128m','--tmpfs','/guard-status:rw,nosuid,nodev,mode=0755,size=1m','--mount','type=bind,src='+str(fixture/'passwd')+',dst=/etc/passwd,readonly','--mount','type=bind,src='+str(fixture/'group')+',dst=/etc/group,readonly','--mount','type=bind,src='+str(fixture)+',dst=/fixture,readonly','--entrypoint','/dispatcharrpy/bin/python',IMAGE,'-B','/fixture/runtime_test.py'])
    result={'image_id':IMAGE,'container_id':pk,'owner':OWNER}
    try:
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
        logs=docker(['logs','--tail','100',pk]);(work/'runtime.log').write_text(logs)
        # tmpfs disappears when the test container exits. Recover the JSON
        # printed before exit rather than copying vanished temporary data.
        parsed=None
        for line in reversed(logs.splitlines()):
            try: value=json.loads(line)
            except ValueError: continue
            if isinstance(value,dict) and 'bootstrap' in value and 'boundary' in value:
                parsed=value;break
        if parsed is None:raise RuntimeError('runtime_result_missing_log_retained')
        result['runtime']=parsed
        (work/'runtime-result.json').write_text(json.dumps(parsed))
    finally:
        # Only the exact container created above is stopped/removed.
        if docker(['inspect','--format','{{.State.Running}}',pk])=='true':docker(['stop','--time','10',pk])
        docker(['rm',pk])
        result['cleaned']=True
        result['production_unchanged']=production()==before
        result['networks_unchanged']=docker(['network','ls','--no-trunc','--format','{{.ID}} {{.Name}}'])==networks
        (work/'runtime-receipt.json').write_text(json.dumps(result))
    print(json.dumps(result))
