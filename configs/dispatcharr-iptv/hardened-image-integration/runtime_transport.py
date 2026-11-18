"""Receipt-safe temporary host process, never a service or a status-triggered job.

Only launch can spawn work. Status uses bounded read-only Docker queries when
terminal reconciliation is necessary. No raw child output or exception bodies
are logged. Separate authorization is required before launching the real runner.
"""
import argparse
import base64
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

APPROVED_RUNNER_SHA256='8ae09016286ca99f82d42b3ea915235a12b5e754701499287495bca02039afbd'
PAYLOAD_CORE_PINS= {'runtime_test.py': '3641f48248a43a3182ff10f2f7121d2a0a4c11110f51427216dc5941e5381bfd', 'runtime_diagnostics.py': 'de5ed39ff92da1002e2f90507511d9dd3cfc878b8e5de55126fb30d467bae432'}
IMAGE='sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439'
JOB_SECONDS=1200
HEARTBEAT_SECONDS=5
STALE_SECONDS=20
TERM_GRACE_SECONDS=10
MAX_JSON=8*1024*1024

class Refused(RuntimeError):pass

class SafeParser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'runtime transport: invalid arguments; values withheld\n')

def digest(data):return hashlib.sha256(data).hexdigest()
def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def monotonic():return time.monotonic()
def process(pid):
    try:
        text=Path('/proc')/str(pid)/'stat';value=text.read_text();fields=value[value.rfind(')')+2:].split()
        return {'pid':pid,'boot_id':boot(),'start_ticks':int(fields[19]),'live':fields[0]!='Z'}
    except (OSError,ValueError,IndexError):return None

def same_process(identity):
    if not isinstance(identity,dict) or type(identity.get('pid')) is not int:return False
    current=process(identity['pid'])
    return current is not None and current['live'] and all(current[k]==identity.get(k) for k in ['pid','boot_id','start_ticks'])

def private_dir(path):
    s=Path(path).lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.geteuid() or stat.S_IMODE(s.st_mode)!=0o700:raise Refused('unsafe_private_directory')

def read_bytes(path,limit=MAX_JSON):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        s=os.fstat(stream.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.geteuid() or s.st_nlink!=1 or stat.S_IMODE(s.st_mode)!=0o600:raise Refused('unsafe_private_file')
        value=stream.read(limit+1)
    if len(value)>limit:raise Refused('private_file_size_limit')
    return value

def read(path):return json.loads(read_bytes(path))
def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)

def write_new(path,value):
    data=value if isinstance(value,bytes) else json.dumps(value,sort_keys=True,allow_nan=False).encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    sync_dir(Path(path).parent)

def replace(path,value):
    temporary=Path(path).with_name('.'+Path(path).name+'-'+str(os.getpid()))
    write_new(temporary,value);os.replace(temporary,path);sync_dir(Path(path).parent)

def log(job,event):
    allowed={'supervisor_started','runner_started','runner_returned','runner_abnormal_exit','outer_deadline','supervisor_failed'}
    if event not in allowed:raise Refused('invalid_log_event')
    path=job/'transport.log';fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'ab') as stream:
        data=(json.dumps({'epoch_seconds':time.time(),'event':event})+'\n').encode()
        if os.fstat(stream.fileno()).st_size+len(data)>8192:raise Refused('transport_log_limit')
        stream.write(data);stream.flush();os.fsync(stream.fileno())

def identity(work,attempt_id):
    work=Path(work).resolve();private_dir(work)
    if not isinstance(attempt_id,str) or not re.fullmatch('[a-z0-9][a-z0-9-]{7,63}',attempt_id):raise Refused('invalid_attempt_identity')
    return work,work/('transport-attempt-'+attempt_id)

def validate_payload(raw,runner_source):
    payload=json.loads(raw)
    if not isinstance(payload,dict) or len(payload)>128:raise Refused('invalid_payload')
    for key,value in payload.items():
        if not isinstance(key,str) or not re.fullmatch('[A-Za-z0-9_./-]{1,180}',key) or key.startswith('/') or '..' in Path(key).parts or not isinstance(value,str):raise Refused('unsafe_payload')
        try:base64.b64decode(value,validate=True)
        except (ValueError,TypeError):raise Refused('invalid_payload_encoding') from None
    import ast
    tree=ast.parse(runner_source)
    helpers=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='HOST_HELPERS' for t in n.targets)))
    for name,wanted in {**PAYLOAD_CORE_PINS,**{'host/'+k:v for k,v in helpers.items()}}.items():
        try:value=base64.b64decode(payload[name],validate=True)
        except (KeyError,ValueError,TypeError):raise Refused('reviewed_payload_required') from None
        if digest(value)!=wanted:raise Refused('payload_source_drift')
    return payload

def load_job(job):
    job=Path(job);private_dir(job);manifest=read(job/'launch.json')
    work,expected=identity(manifest['work'],manifest['attempt_id'])
    if job.resolve()!=expected or manifest.get('schema')!=1 or manifest.get('boot_id')!=boot():raise Refused('job_identity_or_boot_mismatch')
    for filename,key in [('runner.py','runner_sha256'),('payload.json','payload_sha256'),('transport.py','transport_sha256')]:
        if digest(read_bytes(job/filename))!=manifest.get(key):raise Refused('job_source_drift')
    if manifest['runner_sha256']!=APPROVED_RUNNER_SHA256:raise Refused('runner_source_drift')
    return manifest

def runner_module(job):
    source=read_bytes(job/'runner.py')
    if digest(source)!=APPROVED_RUNNER_SHA256:raise Refused('runner_source_drift')
    import types
    module=types.ModuleType('_reviewed_transport_runner');module.__file__=str(job/'runner.py')
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    return module

def launch(work,attempt_id,payload_path,payload_sha256,runner_path):
    work,job=identity(work,attempt_id)
    source=read_bytes(runner_path)
    if digest(source)!=APPROVED_RUNNER_SHA256:raise Refused('runner_source_drift')
    raw=read_bytes(payload_path)
    if not re.fullmatch('[a-f0-9]{64}',payload_sha256) or digest(raw)!=payload_sha256:raise Refused('payload_digest_mismatch')
    validate_payload(raw,source)
    if job.exists():raise Refused('duplicate_transport_identity')
    if (work/('runtime-attempt-'+attempt_id)).exists():raise Refused('runtime_identity_already_consumed')
    try:job.mkdir(mode=0o700)
    except FileExistsError:raise Refused('duplicate_transport_identity') from None
    sync_dir(work)
    # A partial reservation is deliberately never automatically reusable.
    transport=Path(__file__).read_bytes()
    write_new(job/'runner.py',source);write_new(job/'payload.json',raw);write_new(job/'transport.py',transport)
    write_new(job/'launch.json',{'schema':1,'attempt_id':attempt_id,'work':str(work),'boot_id':boot(),'reserved_epoch':time.time(),
        'runner_sha256':digest(source),'payload_sha256':digest(raw),'transport_sha256':digest(transport),'job_seconds':JOB_SECONDS})
    # Double fork: the short-lived intermediate is reaped, while the bounded
    # supervisor is adopted independently of SSH. Every inherited stream/FD closes.
    intermediate=os.fork()
    if intermediate==0:
        try:
            os.setsid()
            if os.fork()!=0:os._exit(0)
            fd=os.open(os.devnull,os.O_RDWR)
            for target in [0,1,2]:os.dup2(fd,target)
            os.closerange(3,os.sysconf('SC_OPEN_MAX'))
            env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','HOME':str(job)}
            os.execve(sys.executable,[sys.executable,'-I','-B',str(job/'transport.py'),'_supervise','--job',str(job)],env)
        except BaseException:os._exit(1)
    _,result=os.waitpid(intermediate,0)
    # A successful fork handshake is not a completed or even accepted application
    # test. Missing later claims remain uncertain; never repeat this launch.
    return {'attempt_id':attempt_id,'state':'reserved' if result==0 else 'uncertain','next_action':'status_same_attempt_only'}


def baseline(module):
    return {'production':module.production(deadline=monotonic()+10),
        'networks':module.docker(['network','ls','--no-trunc','--format','{{.ID}} {{.Name}}'],timeout=5),
        'volumes':module.docker(['volume','ls','--format','{{json .}}'],timeout=5)}


def execute(job):
    os.umask(0o077)
    job=Path(job);manifest=load_job(job);parent=read(job/'supervisor.claim')
    if parent['pid']!=os.getppid() or not same_process(parent):raise Refused('supervisor_identity_missing')
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    write_new(job/'runner.claim',process(os.getpid()))
    invoked=False
    try:
        module=runner_module(job)
        payload=validate_payload(read_bytes(job/'payload.json'),read_bytes(job/'runner.py'))
        write_new(job/'baseline.json',baseline(module))
        invoked=True
        # Raw runner stdout/stderr are discarded, never copied into transport logs.
        with open(os.devnull,'w') as discard,contextlib.redirect_stdout(discard),contextlib.redirect_stderr(discard):
            result=module.main(payload,manifest['work'],IMAGE,attempt_id=manifest['attempt_id'])
        good=isinstance(result,dict) and result.get('runtime',{}).get('success') is True and all(result.get(k) is True for k in ['cleaned','production_unchanged','networks_unchanged','volumes_unchanged'])
        write_new(job/'runner-exit.json',{'schema':1,'runner_invoked':True,'normal_return':True,'candidate':'completed' if good else 'failed','epoch_seconds':time.time()})
        return 0 if good else 1
    except BaseException:
        write_new(job/'runner-exit.json',{'schema':1,'runner_invoked':invoked,'normal_return':False,'candidate':'failed','epoch_seconds':time.time()})
        return 1

def signal_owned_group(claim,signum):
    if not same_process(claim) or os.getpgid(claim['pid'])!=claim['pid']:return False
    os.killpg(claim['pid'],signum);return True


def supervise(job):
    os.umask(0o077)
    job=Path(job);manifest=load_job(job)
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    if not 0<=time.time()-manifest['reserved_epoch']<=60:raise Refused('stale_launch_reservation')
    self_id=process(os.getpid());write_new(job/'supervisor.claim',self_id)
    started=monotonic();deadline=started+JOB_SECONDS
    runner=None;runner_id=None
    try:
        log(job,'supervisor_started')
        runner=subprocess.Popen([sys.executable,'-I','-B',str(job/'transport.py'),'_execute','--job',str(job)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,close_fds=True)
        runner_id=process(runner.pid)
        log(job,'runner_started')
        while runner.poll() is None:
            now=monotonic()
            replace(job/'state.json',{'schema':1,'phase':'running','heartbeat_monotonic':now,'supervisor':self_id,'runner':runner_id,'deadline_monotonic':deadline})
            if now>=deadline:
                log(job,'outer_deadline')
                if runner_id:signal_owned_group(runner_id,signal.SIGTERM)
                try:runner.wait(timeout=TERM_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    if runner_id:signal_owned_group(runner_id,signal.SIGKILL)
                    try:runner.wait(timeout=5)
                    except subprocess.TimeoutExpired:pass
                write_new(job/'completion.json',{'schema':1,'candidate':'uncertain','reason':'outer_deadline','epoch_seconds':time.time()})
                return 1
            time.sleep(min(HEARTBEAT_SECONDS,max(0,deadline-now)))
        log(job,'runner_returned' if runner.returncode==0 else 'runner_abnormal_exit')
        write_new(job/'completion.json',{'schema':1,'candidate':'await_reconciliation','runner_exit_code':runner.returncode,'epoch_seconds':time.time()})
        return 0 if runner.returncode==0 else 1
    except BaseException:
        # Do not relaunch, force Docker cleanup, or claim the runner is stopped.
        try:log(job,'supervisor_failed')
        except BaseException:pass
        try:write_new(job/'completion.json',{'schema':1,'candidate':'uncertain','reason':'supervisor_failure','epoch_seconds':time.time()})
        except BaseException:pass
        return 1


def last_admission(job,manifest):
    path=Path(manifest['work'])/('runtime-attempt-'+manifest['attempt_id'])/'admission.jsonl'
    if not path.exists():return {'last_event':None,'container_id':None}
    raw=read_bytes(path,1024*1024);rows=[json.loads(l) for l in raw.splitlines()]
    known={'attempt_reserved','verification_started','verification_completed','stabilization_started','capacity_observation','stabilization_ended','admission_decision','admission_invalidated','container_creation_intent','container_created','runtime_finished','attempt_failed'}
    last=None;container_id=None
    for row in rows:
        if row.get('event') in known:last=row['event']
        value=row.get('details',{}).get('container_id')
        if isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value):container_id=value
    return {'last_event':last,'container_id':container_id}


def reconcile(job,manifest,evidence):
    module=runner_module(job);deadline=monotonic()+30
    def query(args):
        left=deadline-monotonic()
        if left<=0:raise Refused('reconcile_deadline')
        return module.docker(args,timeout=min(5,left))
    name='dispatcharr-native-runtime-'+manifest['attempt_id'];found=set()
    filters=['name=^/'+name+'$','label=dispatcharr.integration.attempt='+manifest['attempt_id']]
    if evidence['container_id']:filters.append('id='+evidence['container_id'])
    for value in filters:found.update(query(['ps','-aq','--no-trunc','--filter',value]).split())
    if found:
        # Presence is never cleanup success. Do not mutate or dump inspect data.
        return {'clean':False,'reason':'owned_or_conflicting_container_retained'}
    original=read(job/'baseline.json')
    current={'production':module.production(deadline=min(deadline,monotonic()+10)),
        'networks':query(['network','ls','--no-trunc','--format','{{.ID}} {{.Name}}']),
        'volumes':query(['volume','ls','--format','{{json .}}'])}
    return {'clean':current==original,'reason':'scoped_absence_and_production_match' if current==original else 'production_fingerprint_conflict'}


def status(work,attempt_id):
    # No mkdir, writes, claims, Popen, main call, cleanup or launch occurs here.
    safe_id=attempt_id if isinstance(attempt_id,str) and re.fullmatch('[a-z0-9][a-z0-9-]{7,63}',attempt_id) else None
    result={'attempt_id':safe_id,'state':'uncertain','cleanup_complete':False}
    try:
        work,job=identity(work,attempt_id);manifest=load_job(job)
        evidence=last_admission(job,manifest);result.update(last_event=evidence['last_event'])
        supervisor=read(job/'supervisor.claim') if (job/'supervisor.claim').exists() else None
        runner=read(job/'runner.claim') if (job/'runner.claim').exists() else None
        supervisor_live=same_process(supervisor);runner_live=same_process(runner)
        if supervisor_live:
            state=read(job/'state.json');age=monotonic()-state['heartbeat_monotonic']
            if state.get('supervisor')!=supervisor or not 0<=age<=STALE_SECONDS:return {**result,'reason':'stale_or_inconsistent_heartbeat'}
            return {**result,'state':'running','reason':'matching_supervisor_and_fresh_heartbeat','heartbeat_age_seconds':age}
        if runner_live:return {**result,'reason':'supervisor_missing_runner_still_alive'}
        if supervisor is None:return {**result,'reason':'launch_not_confirmed'}
        if runner is None:return {**result,'reason':'runner_identity_missing'}
        outcome=reconcile(job,manifest,evidence)
        if not outcome['clean']:return {**result,'reason':outcome['reason']}
        child=read(job/'runner-exit.json') if (job/'runner-exit.json').exists() else None
        completion=read(job/'completion.json') if (job/'completion.json').exists() else None
        success=(isinstance(child,dict) and child.get('normal_return') is True and child.get('candidate')=='completed'
            and not (isinstance(completion,dict) and completion.get('candidate')=='uncertain'))
        if success:
            receipt=read(work/('runtime-attempt-'+attempt_id)/'runtime-receipt.json')
            if (receipt.get('attempt_id')!=attempt_id or receipt.get('image_id')!=IMAGE
                    or receipt.get('container_id')!=evidence['container_id']
                    or receipt.get('runtime',{}).get('success') is not True
                    or any(receipt.get(k) is not True for k in ['cleaned','production_unchanged','networks_unchanged','volumes_unchanged'])):
                return {**result,'reason':'runtime_receipt_conflict'}
        return {**result,'state':'completed' if success else 'failed','cleanup_complete':True,
            'reason':'normal_return_reconciled' if success else 'failure_or_abnormal_exit_reconciled'}
    except BaseException:
        return {**result,'reason':'missing_invalid_or_unavailable_evidence'}


def main():
    parser=SafeParser(description='Detached private one-attempt transport; no status-triggered launch')
    sub=parser.add_subparsers(dest='command',required=True)
    launch_parser=sub.add_parser('launch');status_parser=sub.add_parser('status')
    for command in [launch_parser,status_parser]:
        command.add_argument('--work',required=True);command.add_argument('--attempt-id',required=True)
    launch_parser.add_argument('--payload',required=True);launch_parser.add_argument('--payload-sha256',required=True);launch_parser.add_argument('--runner',required=True)
    for command in ['_supervise','_execute']:sub.add_parser(command,help=argparse.SUPPRESS).add_argument('--job',required=True)
    args=parser.parse_args()
    try:
        if args.command=='launch':print(json.dumps(launch(args.work,args.attempt_id,args.payload,args.payload_sha256,args.runner)));return 0
        if args.command=='status':print(json.dumps(status(args.work,args.attempt_id)));return 0
        return supervise(args.job) if args.command=='_supervise' else execute(args.job)
    except BaseException:
        value=getattr(args,'attempt_id',None)
        safe_id=value if isinstance(value,str) and re.fullmatch('[a-z0-9][a-z0-9-]{7,63}',value) else None
        if args.command in ['launch','status']:print(json.dumps({'attempt_id':safe_id,'state':'uncertain','reason':'transport_refused_no_automatic_retry'}))
        return 1

if __name__=='__main__':raise SystemExit(main())
