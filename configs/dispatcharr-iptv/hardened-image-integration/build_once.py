"""Explicitly authorized COPY-only build; never touches production containers.

Caller streams this source with an appended public-context PAYLOAD via NEST.
No provider settings, credentials, database or Docker socket enter containers.
"""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time

BASE='sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21'
TAG='local/dispatcharr-native-hardening:policy-lifecycle-review-v2'
DOCKER=['docker','-H','unix:///var/run/docker.sock']
LABEL='dispatcharr.integration.owner=1124d96'

def docker(args,timeout=60,raw=False):
    result=subprocess.run(DOCKER+args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if result.returncode:raise RuntimeError('docker_command_failed:'+args[0]+':'+result.stderr.decode(errors='replace')[:300])
    return result.stdout if raw else result.stdout.decode().strip()

def snapshot():
    result={}
    for pk in docker(['ps','-aq','--no-trunc']).splitlines():
        fmt='{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"status":{{json .State.Status}},"started":{{json .State.StartedAt}},"restarts":{{json .RestartCount}},"health":{{with index .State "Health"}}{{json .Status}}{{else}}null{{end}}}'
        row=json.loads(docker(['inspect','--format',fmt,pk]));result[row['name'].lstrip('/')]=row
    return result

def source_hashes(image,expected,name):
    pk=docker(['create','--pull=never','--name',name,'--label',LABEL,'--network=none','--read-only','--cap-drop=ALL','--security-opt','no-new-privileges:true','--restart=no','--memory=128m','--cpus=0.25','--entrypoint','/bin/true',image])
    try:
        state=json.loads(docker(['inspect','--format','{"running":{{json .State.Running}},"network":{{json .HostConfig.NetworkMode}},"mounts":{{json .Mounts}}}',pk]))
        if state!={'running':False,'network':'none','mounts':[]}:raise RuntimeError('probe_isolation_mismatch')
        found={}
        for path,wanted in expected.items():
            data=docker(['cp',pk+':/app/'+path,'-'],raw=True)
            with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                members=tar.getmembers()
                if len(members)!=1 or not members[0].isfile():raise RuntimeError('source_type_mismatch')
                found[path]=hashlib.sha256(tar.extractfile(members[0]).read()).hexdigest()
            if found[path]!=wanted:raise RuntimeError('source_drift:'+path)
        return found
    finally:
        docker(['rm',pk])


PUBLIC_CONTEXT_FILES = {'Dockerfile','app/core/provider_contract_hashes.json'} | {
    'app/'+name for name in (
        'apps/epg/api_views.py','apps/epg/signals.py','apps/epg/tasks.py',
        'apps/m3u/api_views.py','apps/m3u/signals.py','apps/m3u/tasks.py',
        'core/api_urls.py','core/xtream_codes.py','core/provider_dns.py',
        'core/provider_readiness.py','core/provider_security.py',
        'core/provider_security_view.py','core/provider_transport.py','core/provider_policy.py')
}


def write_context(context,files):
    """Future-rebuild correction: private transport root, public source dirs.

    The authorized build already produced a failed candidate; this correction
    must not be used for another build without separate authorization.
    """
    context.mkdir(mode=0o700)
    for name,obj in files.items():
        if name not in PUBLIC_CONTEXT_FILES or name.startswith('/') or '..' in Path(name).parts:raise RuntimeError('unsafe_context_path')
        data=base64.b64decode(obj['data'],validate=True)
        if hashlib.sha256(data).hexdigest()!=obj['sha256']:raise RuntimeError('context_hash_mismatch')
        path=context/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data);path.chmod(0o644)
    # COPY preserves directory modes. umask 077 must not leak into /app/apps
    # or /app/core after Docker chowns them to root. Workspace stays 0700.
    app=context/'app'
    if not app.is_dir():raise RuntimeError('app_overlay_missing')
    for directory in [app,*[p for p in app.rglob('*') if p.is_dir()]]:
        directory.chmod(0o755)
    return {str(p.relative_to(context)):oct(p.stat().st_mode&0o777) for p in context.rglob('*')}


def main(payload):
    os.umask(0o077)
    before=snapshot()
    if any(before.get(n,{}).get('health')!='healthy' for n in ['dispatcharr','rivendell-iptv-vpn','rivendell-iptv-relay','rivendell-iptv-gateway']):raise RuntimeError('production_health_gate_failed')
    memory=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    resources={'disk_free':shutil.disk_usage('/tmp').free,'memory_available':memory,'load':list(os.getloadavg())}
    if resources['disk_free']<3*1024**3 or memory<2*1024**3 or resources['load'][0]>2:raise RuntimeError('capacity_gate_failed')
    meta=json.loads(docker(['image','inspect',BASE,'--format','{"id":{{json .Id}},"onbuild":{{json (index .Config "OnBuild")}},"volumes":{{json (index .Config "Volumes")}}}']))
    if meta!={'id':BASE,'onbuild':None,'volumes':None}:raise RuntimeError('base_image_drift')
    exists=subprocess.run(DOCKER+['image','inspect',TAG],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if exists:raise RuntimeError('candidate_tag_already_exists_no_rebuild')
    work=Path('/tmp')/('dispatcharr-native-image-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));work.mkdir(mode=0o700)
    (work/'before.json').write_text(json.dumps(before));(work/'resources.json').write_text(json.dumps(resources))
    observed=source_hashes(BASE,payload['base_hashes'],'dispatcharr-native-base-probe-1124d96')
    context=work/'context';write_context(context,payload['files'])
    # Durable one-shot intent; never retry this command after uncertain outcome.
    receipt={'state':'intent','base':BASE,'tag':TAG,'source_hashes':observed,'resources':resources,'work':str(work)}
    (work/'build-receipt.json').write_text(json.dumps(receipt))
    command=DOCKER+['build','--pull=false','--network=none','--no-cache','--memory=512m','--memory-swap=512m','--cpu-period=100000','--cpu-quota=50000','--iidfile',str(work/'image.id'),'-t',TAG,str(context)]
    with (work/'build.log').open('wb') as log:
        process=subprocess.run(command,env={**os.environ,'DOCKER_BUILDKIT':'0'},stdout=log,stderr=subprocess.STDOUT,timeout=180)
    receipt['state']='failed' if process.returncode else 'built';receipt['exit_code']=process.returncode
    (work/'build-receipt.json').write_text(json.dumps(receipt))
    if process.returncode:raise RuntimeError('single_build_failed_log_retained:'+str(work))
    image=(work/'image.id').read_text().strip()
    if not re.fullmatch('sha256:[a-f0-9]{64}',image):raise RuntimeError('invalid_built_image_identity')
    if docker(['image','inspect',TAG,'--format','{{.Id}}'])!=image:raise RuntimeError('tag_identity_mismatch')
    installed=source_hashes(image,{**payload['output_hashes'],**payload['readiness_hashes']},'dispatcharr-native-built-probe-1124d96')
    if snapshot()!=before:raise RuntimeError('unrelated_container_identity_or_health_drift')
    receipt.update(state='verified',image_id=image,installed_hashes=installed,production_unchanged=True)
    (work/'build-receipt.json').write_text(json.dumps(receipt))
    print(json.dumps(receipt))
