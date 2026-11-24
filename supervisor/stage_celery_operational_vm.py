"""Disposable isolated staging fixture. No account changes or AppArmor load."""
from contextlib import suppress
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import time
import zipfile

SRC = Path('/run/samwise-celery-stage-fixture')
STATE = Path('/run/samwise-celery-shadow')
PROJECTIONS = Path('/run/samwise-observations')
DROP = PROJECTIONS/'celery-v1'
INSTALL = Path('/opt/samwise-celery-shadow')
ATT = 'samwise-celery-shadow-once.service'
BACK = hashlib.sha256(b'celery-disposable-operational-stage-v1').hexdigest()
SCOPE = 'docker-'+BACK+'.scope'
CGROOT = Path('/sys/fs/cgroup/system.slice')
APP_UID = 65530
UIDS = {'default@fixture':APP_UID,'dvr@fixture':APP_UID}
NAMES = sorted(UIDS)
ENV = {'PATH':'/usr/sbin:/usr/bin:/bin','HOME':'/nonexistent','LC_ALL':'C'}

def put(path, data, mode=0o644):
    if type(data) is not bytes:
        data=json.dumps(data,separators=(',',':')).encode()
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as out:
        out.write(data)
        os.fchmod(out.fileno(),mode)

def get(path):
    return json.loads(path.read_bytes())

def waitfor(fn, seconds=8):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        try:
            answer=fn()
            if answer:
                return answer
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(.025)
    raise RuntimeError('timed out waiting for stage fixture')

def run(argv, timeout=5):
    r=subprocess.run(argv,check=False,capture_output=True,text=True,timeout=timeout,env=ENV)
    if r.returncode!=0:
        raise ValueError('stage helper failed '+str(argv[0])+' '+r.stderr[:500])
    return r.stdout

def start(argv, **kw):
    return subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,env=ENV,**kw)

def uid(user):
    return {'user':user,'group':user,'extra_groups':[]}

def guest():
    import redis
    assert os.getpid()==1 and os.uname().nodename=='staging'
    run(['/usr/sbin/ip','link','set','lo','up'])
    assert not run(['/usr/sbin/ip','-4','route','show','default']).strip()
    assert not run(['/usr/sbin/ip','-6','route','show','default']).strip()
    assert [x.split(':')[0].strip() for x in
            Path('/proc/net/dev').read_text().splitlines()[2:]]==['lo']
    if (SRC/'playback').exists():
        start([sys.executable,'-IB','-m','http.server','18081','--bind','127.0.0.1',
               '--directory',str(SRC/'playback')],**uid(APP_UID))
    broker_args=[str(SRC/'redis-server'),'--bind','127.0.0.1','--port','6379',
                 '--save','','--appendonly','no','--daemonize','no','--dir',str(SRC/'redis')]
    p=start(broker_args,**uid(APP_UID))
    with redis.Redis(host='127.0.0.1',port=6379,socket_timeout=.25) as c:
        def ready():
            try: return c.ping()
            except redis.RedisError: return False
        waitfor(ready)
        for name,user in UIDS.items():
            role=name.split('@')[0]
            flags=[sys.executable,'-B',str(SRC/'worker.py'),'-A','dispatcharr','worker',
                   '-n',name,'-Q','celery' if role=='default' else 'dvr']
            start(['/bin/dash','-c',shlex.join(flags)+' & wait'],**uid(user))
        def subscribed():
            return sum(int(x.get('psub',0))>0 for x in c.client_list())==2
        waitfor(subscribed)
        put(SRC/'ready.json',{'broker':p.pid})
    if (SRC/'fault').read_text().strip()=='broker-restart':
        waitfor(lambda:(SRC/'start-replacement').exists(),5)
        p.terminate()
        p.wait(timeout=3)
        successor=start(broker_args,**uid(APP_UID))
        assert successor.pid!=p.pid
        with redis.Redis(host='127.0.0.1',port=6379,socket_timeout=.25) as client:
            def replacement_running():
                try: return client.ping()
                except redis.RedisError: return False
            waitfor(replacement_running,3)
        put(SRC/'replacement-ready',{'broker':successor.pid})
    # Keep the nested PID1 and broker scope bounded by the disposable outer
    # harness's cleanup and by this independent idle ceiling.
    time.sleep(90)

WORKER = b"""
import os,sys,time
from pathlib import Path
sys.path.insert(0,'/run/samwise-celery-stage-fixture/pidbox-runtime.zip')
from celery import Celery
from celery.worker.control import inspect_command
name=sys.argv[sys.argv.index('-n')+1]
role=name.split('@')[0]
base=Path('/run/samwise-celery-stage-fixture')
(base/role/'pid').write_text(str(os.getpid()))
fault=(base/'fault').read_text().strip()
app=Celery('fixture',broker='redis://127.0.0.1:6379/0')
app.conf.update(accept_content=['json'],task_serializer='json',
                control_exchange='different' if fault=='wrong-scope' else 'celery',
                broker_transport_options={'fanout_prefix':True,'fanout_patterns':True,'global_keyprefix':''})
@inspect_command(name='ping',default_timeout=.2)
def fixture_ping(state):
    assert state.hostname==name
    (base/role/'probe-seen').touch()
    if fault in ('stall','stall-'+role):
        time.sleep(35)
    return {'ok':'malformed' if fault=='malformed' and role=='default' else 'pong'}
app.Worker(hostname=name,pool='solo',concurrency=1,without_mingle=True,
           without_gossip=True,without_heartbeat=True,loglevel='ERROR').start()
"""


PLAYBACK = b'''
import http.client,os,subprocess,time
from pathlib import Path
base=Path('/run/samwise-celery-stage-fixture')
connection=http.client.HTTPConnection('127.0.0.1',18081,timeout=3)
connection.request('GET','/fixture.ts')
response=connection.getresponse()
assert response.status==200
length=int(response.getheader('Content-Length'))
assert 4096<length<8*1024*1024
tool=base/'media-root/usr/bin/ffmpeg'
lib=base/'media-root/usr/lib/x86_64-linux-gnu'
decoder=subprocess.Popen([str(tool),'-nostdin','-hide_banner','-v','error','-xerror',
    '-f','mpegts','-probesize','65536','-analyzeduration','500000','-i','pipe:0',
    '-map','0:v:0','-map','0:a:0','-progress','pipe:1','-f','null','-'],stdin=subprocess.PIPE,
    env=dict(os.environ,LD_LIBRARY_PATH=str(lib)+':'+str(lib/'pulseaudio')))
try:
    start=time.monotonic()
    sent=0
    while sent<length:
        block=response.read(min(8192,length-sent))
        assert block
        decoder.stdin.write(block)
        decoder.stdin.flush()
        sent+=len(block)
        wait=(18*sent/length)-(time.monotonic()-start)
        if wait>0: time.sleep(wait)
    decoder.stdin.close()
    assert decoder.wait(timeout=4)==0
finally:
    connection.close()
    if decoder.poll() is None:
        decoder.kill()
        decoder.wait(timeout=2)
'''


def host(bundle, fault=None):
    import celery_operational_witness as witness
    import render_celery_operational_enrollment as renderer

    assert os.geteuid()==0 and os.uname().nodename=='staging'
    assert run(['/usr/bin/systemd-detect-virt']).strip()=='kvm'
    paths=(SRC,STATE,PROJECTIONS,INSTALL,CGROOT/SCOPE,CGROOT/ATT)
    assert not any(os.path.lexists(path) for path in paths)
    foreign_types={'nfs','nfs4','cifs','9p','virtiofs','fuse.sshfs'}
    assert not set(run(['/usr/bin/findmnt','-rn','-o','FSTYPE']).split())&foreign_types
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    fixture_process=None
    launch=None
    shared=None
    playback=None
    foreign=None
    owned=[]
    def mkdir(path, mode, gid=0, owner=0):
        path.mkdir(mode=mode)
        owned.append(path)
        os.chown(path,owner,gid)
        path.chmod(mode)
    def hashfile(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def kernel_pids():
        mapping={}
        for h in (CGROOT/SCOPE/'cgroup.procs').read_text().splitlines():
            status=Path('/proc')/h/'status'
            v=next(line.split()[1:] for line in status.read_text().splitlines()
                   if line.startswith('NSpid:'))
            if len(v)==2:
                h,g=map(int,v)
                mapping[g]=h
        return mapping
    def ticks(h):
        return int((Path('/proc')/str(h)/'stat').read_text().rsplit(')',1)[1].split()[19])
    def pair(h):
        return [h,ticks(h)]
    def inode(pid, what):
        return (Path('/proc')/str(pid)/'ns'/what).stat().st_ino
    def pstatus(proc):
        raw=(Path('/proc')/str(proc)/'status').read_text().splitlines()
        return {x.partition(':')[0]:x.partition(':')[2].strip() for x in raw
                if x.startswith(('CapEff:','Seccomp:','VmHWM:'))}
    try:
        mkdir(SRC,0o755)
        mkdir(STATE,0o700)
        mkdir(PROJECTIONS,0o750,985)
        mkdir(DROP,0o2750,985)
        put(DROP/'.celery-acquisition.lock',b'',0o640)
        legacy = ('relay', 'backend', 'gateway', 'vpn-container', 'jellyfin')
        fake_sample=time.time_ns()
        for name in legacy:
            path=PROJECTIONS/name
            data=(b'running\n' if name=='relay' else
                  dict(schema='samwise-projection-v2',source='engine-health-v1',name=name,
                       sample_ns=fake_sample,until_ns=fake_sample+60*10**9,value='running'))
            put(path,data,0o640)
            os.chown(path,0,985)
            os.utime(path,ns=(fake_sample,fake_sample))
        old_files={name:hashfile(PROJECTIONS/name) for name in legacy}
        os.chown(DROP/'.celery-acquisition.lock',0,985)
        mkdir(SRC/'redis',0o700,APP_UID,APP_UID)
        for name,user in UIDS.items():
            mkdir(SRC/name.split('@')[0],0o700,user,user)

        modules=('celery_shadow_launcher.py','celery_operational_witness.py','celery_site_pidbox.py',
                 'celery_broker_guard.py','celery_handoff.py','celery_readiness.py',
                 'dispatcharr_project.py','ops_protocol.py','redis-server')
        for f in modules:
            put(SRC/f,(bundle/f).read_bytes(),0o755 if f=='redis-server' else 0o644)
        put(SRC/'witness',(bundle/'celery_operational_witness.py').read_bytes(),0o755)
        put(SRC/'pidbox-ping',(bundle/'celery_site_pidbox.py').read_bytes(),0o755)
        put(SRC/'fixture.py',Path(__file__).read_bytes(),0o644)
        put(SRC/'worker.py',WORKER,0o644)
        put(SRC/'fault',((fault or 'none')+'\n').encode())
        mkdir(SRC/'observer',0o755)
        for name in ('ops_collector.py','ops_protocol.py','celery_handoff.py','launch.py'):
            put(SRC/'observer'/name,(bundle/name).read_bytes(),0o644)
        put(SRC/'stage-fixture.passwd',b'root:x:0:0:root:/root:/bin/sh\nsamwise-observe:x:999:985::/nonexistent:/opt/samwise-observe/login\n')
        put(SRC/'stage-fixture.group',b'root:x:0:\nsamwise-observe:x:985:\n')
        media=(bundle/'media-root').exists() and fault is None
        if media:
            tool=bundle/'media-root/usr/bin/ffmpeg'
            assert hashfile(tool)=='bdf6aabffdba7411edff8d36c389d695257fcdf823d196020176e117612862f6'
            (SRC/'media-root').symlink_to((bundle/'media-root').resolve(),target_is_directory=True)
            lib=SRC/'media-root/usr/lib/x86_64-linux-gnu'
            media_env=ENV|{'LD_LIBRARY_PATH':str(lib)+':'+str(lib/'pulseaudio')}
            put(SRC/'playback.py',PLAYBACK,0o644)
            mkdir(SRC/'playback',0o750,APP_UID,APP_UID); os.chmod(SRC/'playback',0o770)
            # Codec test only; synthetic colour + sine, no source or provider.
            subprocess.run([str(tool),'-nostdin','-hide_banner','-v','error',
                '-f','lavfi','-i','testsrc=size=160x90:rate=15',
                '-f','lavfi','-i','sine=frequency=800:sample_rate=48000',
                '-t','21','-c:v','mpeg2video','-c:a','mp2','-f','mpegts',str(SRC/'playback'/'fixture.ts')],
                check=True,env=media_env,timeout=8,**uid(APP_UID))
        with zipfile.ZipFile(SRC/'pidbox-runtime.zip','x',zipfile.ZIP_DEFLATED) as output:
            for file in sorted((bundle/'pkg').rglob('*')):
                if file.is_file() and not file.is_symlink() and '__pycache__' not in file.parts:
                    output.write(file,file.relative_to(bundle/'pkg'))
        (SRC/'pidbox-runtime.zip').chmod(0o644)

        guest_code="import sys; sys.path[:0]=sys.argv[1:3]; import fixture; fixture.guest()"
        with (SRC/'guest.log').open('xb') as log:
            fixture_process=subprocess.Popen(['/usr/bin/systemd-run','--scope','--quiet','--collect',
              '--unit='+SCOPE,'-pTimeoutStopSec=1s','-pKillSignal=SIGKILL','/usr/bin/unshare','--pid','--fork','--net','--mount','--uts','--mount-proc',
              '--kill-child=KILL','/usr/bin/python3','-IB','-c',guest_code,str(SRC),
              str(SRC/'pidbox-runtime.zip')],env=ENV,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        try:
            ready=waitfor(lambda:get(SRC/'ready.json'))
        except RuntimeError:
            print('guest fixture diagnostic',(SRC/'guest.log').read_text()[:1000],flush=True)
            raise
        workers={n:int((SRC/n.split('@')[0]/'pid').read_text()) for n in NAMES}
        mapping=kernel_pids()
        init=mapping[1]
        broker=mapping[ready['broker']]
        physical={n:mapping[workers[n]] for n in NAMES}
        backend_net=inode(init,'net')
        assert backend_net!=inode('self','net')
        assert inode(init,'pid')!=inode(1,'pid')
        # A separate peer with host-visible PIDs shares this no-egress network.
        shared=start(['/usr/bin/nsenter',f'--net=/proc/{init}/ns/net','/usr/bin/sleep','40'])
        waitfor(lambda:inode(shared.pid,'net')==backend_net,2)
        assert inode(shared.pid,'pid')==inode(1,'pid')
        now=time.time_ns()
        worker_ids={n:pair(physical[n]) for n in NAMES}
        w=dict(version='celery-operational-witness-v1',boot=boot,backend_id=BACK,
               backend_pid=init,backend_ticks=ticks(init),backend_start_ns=now-5*10**9,
               net_inode=backend_net,worker_uid=APP_UID,worker_command='/usr/bin/python3',
               hostname='fixture',scope=witness.SCOPE,workers=worker_ids,
               broker=pair(broker),broker_uid=APP_UID)
        ok=dict(Name='/dispatcharr',Id=BACK,Status='running',Running=True,Pid=init,
                StartedNs=w['backend_start_ns'],Health='healthy',HealthEndNs=now,HealthExitCode=0)
        mkdir(STATE/'renderer-input',0o700)
        inputs=STATE/'renderer-input'
        put(inputs/'witness.json',w,0o600)
        put(inputs/'health.json',dict(boot=boot,sampled_ns=now,backend=ok),0o600)
        put(inputs/'boundary',b'Approved disposable fixture processes only. No external route.\n',0o600)
        output=STATE/'rendered'
        assert renderer.main(['--witness',str(inputs/'witness.json'),'--health',str(inputs/'health.json'),
              '--boundary',str(inputs/'boundary'),'--payload',str(SRC),'--output',str(output),
              '--node','staging','--now-ns',str(now)])==0
        for name in ('witness-enrollment.json','pidbox-enrollment.json','one-shot.json'):
            (output/name).rename(SRC/name)
        (output/'backend-witness.json').rename(STATE/'backend-witness.json')
        output.rmdir()
        if fault=='broker-restart':
            put(SRC/'start-replacement',b'disposable restart\n')
            new=waitfor(lambda:get(SRC/'replacement-ready'),5)
            assert new['broker']!=ready['broker']
        if fault=='foreign-peer':
            # An unreviewed effective UID joins the synthetic broker TCP
            # path without publishing or mutating anything. Must refuse.
            marker=SRC/'foreign-connected'
            with marker.open('xb') as out:
                foreign=subprocess.Popen(['/usr/bin/nsenter',f'--net=/proc/{init}/ns/net',
                    '/usr/bin/setpriv',f'--reuid={APP_UID+1}',f'--regid={APP_UID+1}','--clear-groups',
                    '/usr/bin/python3','-IB','-c',
                    'import socket,time; s=socket.create_connection(("127.0.0.1",6379),2); print("connected",flush=True); time.sleep(20)'],
                    env=ENV,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.DEVNULL)
            waitfor(lambda:marker.read_bytes()==b'connected\n',3)
        # The operational witness intentionally reads only the service's
        # own network namespace; it is exercised in the generated unit.
        if fault in ('dead-default','dead-dvr','broker-stop'):
            target=broker if fault=='broker-stop' else physical[fault[5:]+'@fixture']
            os.kill(target,signal.SIGKILL)
            waitfor(lambda:not (Path('/proc')/str(target)).exists()
                    or (Path('/proc')/str(target)/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z',2)
        def read_lease():
            which='pr51-stage-reader.service'
            args=['/usr/bin/systemd-run','--unit='+which,'--wait','--pipe','--quiet','--collect',
                  '-pRuntimeMaxSec=2s','-pKillMode=control-group','-pPrivateNetwork=yes',
                  '-pNoNewPrivileges=yes','-pCapabilityBoundingSet=CAP_SETUID CAP_SETGID',
                  '-pTemporaryFileSystem=/opt:mode=0755',
                  f'-pBindReadOnlyPaths={SRC/"observer"}:/opt/samwise-observe',
                  '-pProtectSystem=strict','--setenv=SSH_ORIGINAL_COMMAND=samwise-observe-v1',
                  '/usr/bin/setpriv','--reuid=999','--regid=985','--clear-groups',
                  '--inh-caps=-all','--ambient-caps=-all',
                  '/usr/bin/python3','-IB','/opt/samwise-observe/launch.py']
            request=json.dumps({'observations':list(legacy)+['celery']}).encode()
            obs=subprocess.run(args,input=request,capture_output=True,timeout=4,env=ENV)
            if obs.returncode:
                raise ValueError('native observer failed: '+obs.stderr.decode('ascii','replace')[:400])
            data=json.loads(obs.stdout)
            assert all(data[k]=='running' for k in legacy)
            return data['celery']

        media_progress=SRC/'decoder.progress'
        def frames():
            if not media_progress.exists():
                return 0
            matches=[int(line.partition('=')[2]) for line in media_progress.read_text().splitlines()
                     if line.startswith('frame=') and line.partition('=')[2].strip().isdigit()]
            return max(matches,default=0)

        if media:
            with media_progress.open('xb') as output:
                playback=subprocess.Popen(['/usr/bin/nsenter',f'--net=/proc/{init}/ns/net',
                    '/usr/bin/setpriv',f'--reuid={APP_UID}',f'--regid={APP_UID}','--clear-groups',
                    '/usr/bin/python3','-IB',str(SRC/'playback.py')],stdin=subprocess.DEVNULL,
                    stdout=output,stderr=subprocess.PIPE,env=ENV)
            def frames_or_error():
                if playback.poll() is not None and playback.returncode!=0:
                    raise RuntimeError(f'synthetic decoder exited {playback.returncode}: '+
                                       playback.stderr.read().decode('ascii','replace')[:350])
                return frames()
            before_frames=waitfor(frames_or_error,8)
            during_frames=0
        assert read_lease()=='unavailable'
        begin=time.monotonic()
        launch=subprocess.Popen(['/usr/bin/systemd-run','--unit=pr51-stage-bootstrap.service',
                '--wait','--pipe','--quiet','--collect','-pRuntimeMaxSec=20s',
                '-pTemporaryFileSystem=/opt:mode=0755',f'-pBindReadOnlyPaths={SRC}:{INSTALL}',
                '/usr/bin/python3','-IB',str(INSTALL/'celery_shadow_launcher.py'),'--launch'],
                env=ENV,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        seen={}
        resources={}
        receipt=False
        cancelled=False
        while launch.poll() is None and time.monotonic()-begin<19:
            for unit in (ATT,):
                with suppress(OSError,KeyError,ValueError):
                    cgroup=CGROOT/unit
                    for proc in (cgroup/'cgroup.procs').read_text().splitlines():
                        st=pstatus(proc)
                        # Ignore PID1's short-lived setup executor before the
                        # unit's actual Python has entered seccomp and dropped caps.
                        expected='0'*16
                        if st.get('CapEff')==expected and st.get('Seccomp')=='2' and (
                           int(st.get('VmHWM','0').split()[0]) >
                           int(seen.get(unit,{}).get('VmHWM','0').split()[0])):
                            seen[unit]=st
                    cpu=dict(line.split() for line in (cgroup/'cpu.stat').read_text().splitlines())
                    resources[unit]=dict(cpu_microseconds=int(cpu['usage_usec']),
                                         peak_bytes=int((cgroup/'memory.peak').read_text()))
            workers_received=all((SRC/name.split('@')[0]/'probe-seen').exists() for name in NAMES)
            if fault=='cancel' and ATT in seen and workers_received and not cancelled:
                run(['/usr/bin/systemctl','stop','--no-block',ATT])
                cancelled=True
            if (DROP/'.celery-publication.json').exists() and not receipt:
                receipt=True
                live=read_lease()
                print('live unprivileged native seccomp reader',live,flush=True)
                assert live=='both-ready'
                if media:
                    during_frames=frames()
                    assert during_frames>before_frames and playback.poll() is None
            time.sleep(.05)
        out,err=launch.communicate(timeout=2)
        print('unit launch',launch.returncode,out.strip(),err[:300],flush=True)
        expired=read_lease()
        print('after lease closed',expired,flush=True)
        assert expired=='unavailable'
        assert old_files=={name:hashfile(PROJECTIONS/name) for name in legacy}
        print('legacy synthetic relay/four containers unchanged',flush=True)
        print('zero-capability publisher and child sampled',seen,resources,flush=True)
        print('process/cgroup cleanup wall seconds',round(time.monotonic()-begin,3),
              {u:not (CGROOT/u).exists() for u in (ATT,)},flush=True)
        if media:
            after_frames=frames()
            # The same decoder and HTTP request lived through the lease;
            # both streams had to decode successfully for an exit-zero result.
            _out,err=playback.communicate(timeout=9)
            final_frames=frames()
            assert playback.returncode==0,err.decode('ascii','replace')[:300]
            assert final_frames>=240 and final_frames>during_frames>before_frames
            print('synthetic HTTP MPEG-TS video+audio decode frames',before_frames,
                  during_frames,after_frames,final_frames,flush=True)
        for u in (ATT,):
            if u not in seen:
                logs=run(['/usr/bin/journalctl','-n','5','--no-pager','-o','cat','-u',u])
                print(u,'recent unit output:',logs[-3500:],flush=True)
        if fault:
            assert not receipt and launch.returncode!=0
            assert fault!='cancel' or cancelled
            if fault in ('dead-default','dead-dvr','broker-stop','broker-restart','foreign-peer'):
                assert not any((SRC/n.split('@')[0]/'probe-seen').exists() for n in NAMES), 'ping reached a worker after refusal'
            assert all(not (CGROOT/u).exists() for u in (ATT,))
            assert time.monotonic()-begin < 18
            print(f'{fault} produced unavailable and no receipt',flush=True)
        elif not receipt:
            logs=run(['/usr/bin/journalctl','-n','35','--no-pager','-o','cat','-u',ATT])
            print('no receipt',logs[-3500:],flush=True)
            raise RuntimeError('exact stage launcher did not publish')
    finally:
        for unit in (ATT,SCOPE,'pr51-stage-bootstrap.service','pr51-stage-reader.service'):
            if (CGROOT/unit).exists():
                with suppress(subprocess.TimeoutExpired):
                    subprocess.run(['/usr/bin/systemctl','kill','--kill-whom=all','--signal=KILL',unit],
                                   env=ENV,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2)
        if shared is not None and shared.poll() is None:
            shared.terminate()
        if playback is not None and playback.poll() is None:
            playback.terminate()
        if foreign is not None and foreign.poll() is None:
            foreign.terminate()
        for proc in (launch,fixture_process,shared,playback,foreign):
            if proc is not None:
                with suppress(subprocess.TimeoutExpired): proc.wait(timeout=1)
        # Delete only individually owned synthetic trees opened by this run.
        for path in (PROJECTIONS,STATE,SRC):
            if path in owned:
                shutil.rmtree(path)
        waitfor(lambda:not any((CGROOT/u).exists() for u in (ATT,SCOPE)),4)

if __name__=='__main__':
    assert len(sys.argv) in (2,3) and (len(sys.argv)==2 or sys.argv[2] in ('cancel','stall-default','stall-dvr','dead-default','dead-dvr','broker-stop','broker-restart','foreign-peer','wrong-scope','malformed'))
    signals=lambda *_: (_ for _ in ()).throw(TimeoutError('stage fixture interrupted'))
    signal.signal(signal.SIGTERM, signals)
    signal.signal(signal.SIGINT, signals)
    sys.path.insert(0,sys.argv[1])
    host(Path(sys.argv[1]),sys.argv[2] if len(sys.argv)==3 else None)
