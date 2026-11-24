from contextlib import ExitStack
import json
import os
from pathlib import Path
from shutil import copyfile
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from unittest.mock import patch

import celery_site_pidbox as site


class PidboxRules(unittest.TestCase):
    def test_expect_exact_worker_roles_and_raw_reply_uniqueness(self):
        names = ['default@fixture','dvr@fixture']
        one = {names[0]:{'ok':'pong'}}
        two = {names[1]:{'ok':'pong'}}
        self.assertEqual(site.replies([one,two],names,lambda:None),one|two)
        self.assertEqual(site.replies([one],names,lambda:None),one)
        for frames in ([one,one], [one,two,one], [{**one, **two}], [],
                       [{'default@wrong':{'ok':'pong'}}], [{names[0]:{'ok':'pong','noise':1}}]):
            with self.subTest(frames=frames),self.assertRaises(ValueError):
                site.replies(frames,names,lambda:None)

    def test_decoy_port_foreign_address_and_socket_families_refused(self):
        site.network_event('socket.connect',(None,('127.0.0.1',6379)))
        for name,args in [('socket.connect',(None,('127.0.0.1',6380))),
                          ('socket.connect',(None,('10.10.20.30',6379))),
                          ('socket.connect',(None,'/run/redis.sock')),
                          ('socket.getaddrinfo',('fake',6379)),
                          ('socket.__new__',(None,socket.AF_INET6,socket.SOCK_STREAM)),
                          ('socket.__new__',(None,socket.AF_INET,socket.SOCK_DGRAM)),
                          ('subprocess.Popen',())]:
            with self.subTest(name=name,args=args),self.assertRaises(ValueError):
                site.network_event(name,args)

    def test_db_control_scope_and_namespace_proof_are_fixed(self):
        scope = site.digest(site.canonical(site.SCOPE))
        p=dict(version='celery-site-pidbox-v1',boot='1ee950ea-57f1-4c0e-b127-dbf0b23dc841',
            net_inode=42,pid_inode=7,scope_sha256=scope,topology=site.PROOF,broker=[1,11],
            workers={'default@fixture':[2,22],'dvr@fixture':[3,33]},
            runtime_sha256='a'*64,broker_sha256='b'*64)
        self.assertEqual(site.enrollment(site.canonical(p)),p)
        for change in (dict(topology='unknown'),dict(runtime_sha256='bad'),
                       dict(scope_sha256=site.digest(site.canonical(site.SCOPE|{'database':1}))),
                       dict(scope_sha256=site.digest(site.canonical(site.SCOPE|{'fanout_prefix':''}))),
                       dict(scope_sha256=site.digest(site.canonical(site.SCOPE|{'reply_exchange':'foreign'})))):
            with self.subTest(change=change),self.assertRaises(ValueError):
                site.enrollment(site.canonical(p|change))


def stage_driver():
    # This whole driver runs only in a private network/PID namespace with
    # synthetic data and no visible host service or deployment credentials.
    import redis
    fixed = Path('/opt/samwise-celery-shadow')
    root = Path('/tmp')
    names = ['default@fixture','dvr@fixture']
    def pair(process):
        statfile = Path('/proc')/str(process.pid)/'stat'
        return [process.pid,int(statfile.read_text().rsplit(')',1)[1].split()[19])]
    def stop(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
    (root/'site_celery_fixture.py').write_text(
        "from celery import Celery\n"
        "app=Celery('fixture',broker='redis://127.0.0.1:6379/0')\n"
        "app.conf.update(accept_content=['json'],task_serializer='json', control_exchange='celery',"
        "broker_transport_options={'fanout_prefix':True,'fanout_patterns':True,'global_keyprefix':''})\n")
    with ExitStack() as resources:
        def launch(command,extra=None):
            env={'PATH':'/usr/bin:/bin','HOME':'/tmp','PYTHONPATH':'/libs:/tmp',
                 'PYTHONDONTWRITEBYTECODE':'1'} | (extra or {})
            process = subprocess.Popen(command,cwd=root,env=env,stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            resources.callback(stop,process)
            return process
        broker = launch(['/broker/redis-server','--bind','127.0.0.1','--port','6379',
                         '--save','','--appendonly','no','--daemonize','no','--dir','/tmp'])
        with redis.Redis(host='127.0.0.1',port=6379,socket_timeout=.3) as admin:
            for _ in range(100):
                try:
                    if admin.ping():
                        break
                except redis.RedisError:
                    assert broker.poll() is None
                    time.sleep(.05)
            else:
                raise AssertionError('fixture_redis_not_ready')
            workers = {name:launch([sys.executable,'-B','-m','celery','-A','site_celery_fixture',
                'worker','--hostname='+name,'--pool=solo','--concurrency=1','--without-mingle',
                '--without-gossip','--without-heartbeat']) for name in names}
            for _ in range(100):
                if sum(int(x.get('psub',0))>0 for x in admin.client_list())>=2:
                    break
                assert all(w.poll() is None for w in workers.values())
                time.sleep(.05)
            else:
                raise AssertionError('fixture_workers_not_ready')
        p=dict(version='celery-site-pidbox-v1',boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
               net_inode=Path('/proc/self/ns/net').stat().st_ino,
               pid_inode=Path('/proc/self/ns/pid').stat().st_ino,
               scope_sha256=site.digest(site.canonical(site.SCOPE)),topology=site.PROOF,
               broker=pair(broker),workers={n:pair(w) for n,w in workers.items()},
               broker_sha256=site.digest(Path('/broker/redis-server').read_bytes()),
               runtime_sha256=site.digest((fixed/'pidbox-runtime.zip').read_bytes()))
        enroll=fixed/'pidbox-enrollment.json'
        def write(config):
            enroll.write_bytes(site.canonical(config))
            enroll.chmod(0o600)
        def execute(dest='--destination='+','.join(names)):
            began=time.monotonic()
            r=subprocess.run([str(fixed/'pidbox-ping'),dest,'--timeout=8','--json'],
                              env={'PATH':'/usr/bin:/bin','LC_ALL':'C','HOME':'/tmp'},timeout=12,
                              stdin=subprocess.DEVNULL,capture_output=True)
            return r,time.monotonic()-began
        write(p)
        site.topology(Path('/proc'),p)
        # Compose the exact broker executable with the real lease/reader
        # and launcher pins; the stored backend health fixture stays synthetic.
        import celery_shadow_launcher as shadow
        from celery_handoff import ANCHOR,DROP
        from ops_collector import collect
        read_path=fixed/'fixture-observations'
        read_path.mkdir(mode=0o700)
        drop=read_path/DROP
        drop.mkdir(mode=0o700)
        (drop/ANCHOR).touch()
        (drop/ANCHOR).chmod(0o640)
        tick=time.time_ns()-10**9
        backend=dict(Name='/dispatcharr', Id='a'*64, Status='running', Running=True,
                     Pid=broker.pid, StartedNs=tick, Health='healthy',
                     HealthEndNs=tick, HealthExitCode=0)
        frame=dict(boot=p['boot'],backend=backend,workers=p['workers'],
                   net_inode=p['net_inode'],endpoint=site.SCOPE['endpoint'],scope_sha256=p['scope_sha256'])
        witness=fixed/'witness'
        witness.write_text('#!/usr/bin/python3 -IB\nprint('+repr(site.canonical(frame).decode())+')\n')
        witness.chmod(0o755)
        witness_enroll=fixed/'witness-enrollment.json'
        witness_enroll.write_bytes(b'{}')
        witness_enroll.chmod(0o600)
        plan=dict(boot=p['boot'],names=names,net_inode=p['net_inode'],broker_scope_sha256=shadow.BROKER_SCOPE,
               backend_id=backend['Id'],backend_pid=backend['Pid'],backend_start_ns=tick,
               witness_sha256=site.digest(witness.read_bytes()),
               ping_sha256=site.digest((fixed/'pidbox-ping').read_bytes()),
               witness_enrollment_sha256=site.digest(witness_enroll.read_bytes()),
               pidbox_enrollment_sha256=site.digest(enroll.read_bytes()))
        req='{"observations":["celery"]}'
        def observe(expected,_deadline):
            assert collect(req,read_path,0)=={'celery':expected}
            return expected
        with patch.object(shadow,'DROP',drop):
            started=time.monotonic()
            assert shadow.pinned_worker(plan,0,observe)=='both-ready'
            good=time.monotonic()-started
        assert collect(req,read_path,0)=={'celery':'unavailable'}
        # A real foreign subscriber in this same Redis network namespace is
        # ruled out by the independent established-client inode ownership join.
        with redis.Redis(host='127.0.0.1',port=6379,socket_timeout=1).pubsub() as foreign:
            foreign.psubscribe('/0.celery.pidbox*')
            assert foreign.get_message(timeout=1)['type']=='psubscribe'
            r,_=execute()
            assert r.returncode==1 and not r.stdout and not r.stderr
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as decoy:
            decoy.bind(('127.0.0.1',6380))
            decoy.listen(1)
            decoy.settimeout(.05)
            r=subprocess.run([sys.executable,'-IB','-c',
                "import sys,socket;sys.path.insert(0,'/stage');from celery_site_pidbox import network_event;sys.addaudithook(network_event);"
                "socket.create_connection(('127.0.0.1',6380),.2)"],
                timeout=2,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            assert r.returncode!=0
            try:
                conn,_=decoy.accept()
            except TimeoutError:
                pass
            else:
                conn.close()
                raise AssertionError('decoy_port_received_connection')
        # A duplicate-role real worker is not treated as the already enrolled
        # PID. Its extra connections must prevent a broker capture.
        dup=launch([sys.executable,'-B','-m','celery','-A','site_celery_fixture',
                    'worker','--hostname='+names[0],'--pool=solo','--concurrency=1',
                    '--without-mingle','--without-gossip','--without-heartbeat'])
        with redis.Redis(host='127.0.0.1',port=6379,socket_timeout=1) as admin:
            for _ in range(90):
                if sum(int(x.get('psub',0))>0 for x in admin.client_list())>=3:
                    break
                assert dup.poll() is None
                time.sleep(.05)
            else:
                raise AssertionError('fixture_duplicate_not_ready')
        r,_=execute()
        assert r.returncode==1 and not r.stdout and not r.stderr
        stop(dup)
        r,_=execute('--destination=default@fixture,dvr@unexpected')
        assert r.returncode==1 and not r.stdout and not r.stderr
        write(p|{'runtime_sha256':'0'*64})
        r,_=execute()
        assert r.returncode==1 and not r.stdout and not r.stderr
        write(p)
        stop(broker)
        r, bad=execute()
        assert r.returncode==1 and not r.stdout and not r.stderr
        print(f'site_pidbox_ready_seconds={good:.3f} lost_broker_refusal_seconds={bad:.3f}')


@unittest.skipUnless(os.environ.get('SAMWISE_CELERY_SITE_STAGE')=='1',
                     'requires disposable bubblewrap, Redis and pinned local staging libraries')
class IsolatedSite(unittest.TestCase):
    def test_real_fixed_tcp_scope_fresh_workers_and_foreign_subscriber(self):
        stage = Path(__file__).resolve().parent
        redis=Path(os.environ['SAMWISE_STAGE_REDIS']).resolve(strict=True)
        libs=Path(os.environ['SAMWISE_STAGE_LIBRARIES']).resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix='celery-site-stage-') as tmp:
            root=Path(tmp)
            copyfile(stage/'celery_site_pidbox.py',root/'pidbox-ping')
            (root/'pidbox-ping').chmod(0o755)
            with zipfile.ZipFile(root/'pidbox-runtime.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
                for item in sorted(libs.rglob('*')):
                    if item.is_file() and not item.is_symlink() and '__pycache__' not in item.parts:
                        name=item.relative_to(libs).as_posix()
                        archive.writestr(zipfile.ZipInfo(name),item.read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
            (root/'pidbox-runtime.zip').chmod(0o644)
            cmd=['/usr/bin/bwrap','--unshare-user','--uid','0','--gid','0','--unshare-net','--unshare-pid',
                 '--die-with-parent','--clearenv','--setenv','PATH','/usr/bin','--setenv','PYTHONPATH','/libs:/stage',
                 '--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64',
                 '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(stage),'/stage',
                 '--ro-bind',str(libs),'/libs','--ro-bind',str(redis),'/broker/redis-server',
                 '--dir','/opt','--bind',str(root),'/opt/samwise-celery-shadow',
                 '--chdir','/tmp','/usr/bin/python3','-B','/stage/test_celery_site_pidbox.py','--fixture']
            runner=subprocess.run(cmd,timeout=27,stdin=subprocess.DEVNULL,capture_output=True,text=True)
            self.assertEqual(runner.returncode,0,runner.stderr)
            self.assertRegex(runner.stdout,r'^site_pidbox_ready_seconds=[\d.]+ lost_broker_refusal_seconds=[\d.]+\n$')
            print(runner.stdout.strip())


if __name__=='__main__':
    if sys.argv[1:]==['--fixture']:
        stage_driver()
    else:
        unittest.main()
