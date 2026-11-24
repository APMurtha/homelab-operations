"""No production keys. Real one-ping fixture is explicitly selected on staging."""
from contextlib import ExitStack
import ctypes
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import tempfile
import time
import unittest

import celery_signed_origin as origin
import celery_site_pidbox as site

NAMES = ['default@fixture','dvr@fixture']
SEEDS = [bytes([n])*32 for n in (73, 183)]
SCOPE = site.digest(site.canonical(site.SCOPE))
BACKEND = 'a'*64


def signer(seed, message=None):
    """OpenSSL test implementation only. Fixture seeds must never be enrolled."""
    lib=ctypes.CDLL(origin._CRYPTO)
    ptr,string,size,integer=ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t,ctypes.c_int
    def f(name, result, *args):
        fn=getattr(lib,name)
        fn.restype,fn.argtypes=result,list(args)
        return fn
    key=f('EVP_PKEY_new_raw_private_key_ex',ptr,ptr,string,string,string,size)(
        None,b'ED25519',None,seed,len(seed))
    assert key
    try:
        if message is None:
            out=ctypes.create_string_buffer(32)
            count=size(32)
            assert f('EVP_PKEY_get_raw_public_key',integer,ptr,ptr,ptr)(
                key,out,ctypes.byref(count))==1 and count.value==32
            return out.raw.hex()
        ctx=f('EVP_MD_CTX_new',ptr)()
        assert ctx
        try:
            assert f('EVP_DigestSignInit',integer,ptr,ptr,ptr,ptr,ptr)(ctx,None,None,None,key)==1
            out=ctypes.create_string_buffer(64)
            count=size(64)
            assert f('EVP_DigestSign',integer,ptr,ptr,ptr,string,size)(
                ctx,out,ctypes.byref(count),message,len(message))==1 and count.value==64
            return out.raw.hex()
        finally:
            f('EVP_MD_CTX_free',None,ptr)(ctx)
    finally:
        f('EVP_PKEY_free',None,ptr)(key)


def frame(name, incarnation, nonce, seed):
    return {name:{'ok':'pong','origin':{'version':1,'incarnation':incarnation,
            'signature':signer(seed,origin.statement(nonce,SCOPE,name,incarnation))}}}


class SignedOrigin(unittest.TestCase):
    def setUp(self):
        self.nonce='b'*64
        self.keys=dict(zip(NAMES,(signer(s) for s in SEEDS)))
        self.ids=dict(zip(NAMES,('c'*64,'d'*64)))
        self.first,self.last=[frame(n,self.ids[n],self.nonce,s) for n,s in zip(NAMES,SEEDS)]

    def verify(self, raw, nonce=None, ids=None):
        return origin.qualify(raw,NAMES,self.keys,self.ids if ids is None else ids,
                              self.nonce if nonce is None else nonce,SCOPE)

    def test_two_distinct_keys_and_one_authenticated_incomplete(self):
        self.assertEqual(self.verify([self.first,self.last]),{n:{'ok':'pong'} for n in NAMES})
        self.assertEqual(self.verify([self.last]),{NAMES[1]:{'ok':'pong'}})

    def test_duplicate_legacy_foreign_swapped_wrong_key_and_wrong_incarnation(self):
        invalid=[
            [self.first,self.first],
            [{NAMES[0]:{'ok':'pong'}}],
            [{'default@foreign':self.first[NAMES[0]]}],
            [{NAMES[1]:self.first[NAMES[0]]}],
            [frame(NAMES[0],self.ids[NAMES[0]],self.nonce,SEEDS[1])],
            [frame(NAMES[1],'e'*64,self.nonce,SEEDS[1])],
            [self.first,self.last,self.first],
            [],
        ]
        for raw in invalid:
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                self.verify(raw)

    def test_replay_scope_collision_and_wrong_incarnation(self):
        self.assertNotEqual(origin.challenge(),origin.challenge())
        with self.assertRaises(ValueError):
            self.verify([self.first,self.last],nonce='f'*64)
        with self.assertRaises(ValueError):
            self.verify([self.first,self.last],ids=self.ids|{NAMES[0]:'1'*64})
        with self.assertRaises(ValueError):
            origin.qualify([self.first,self.last],NAMES,self.keys,self.ids,self.nonce,'1'*64)
        with self.assertRaises(ValueError):
            origin.qualify([self.first,self.last],NAMES,{n:self.keys[NAMES[0]] for n in NAMES},
                           self.ids,self.nonce,SCOPE)


def local_incarnation(pid):
    parent=Path('/proc')/str(pid)
    start=int((parent/'stat').read_text().rsplit(')',1)[1].split()[19])
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    return origin.incarnation(site='staging',boot=boot,backend=BACKEND,
                              host_pid=pid,guest_pid=pid,ticks=start)


def stage_driver():
    """Runs entirely inside a verified disposable fixture, no inputs from host."""
    from celery import Celery
    import redis
    assert os.environ.get('SAMWISE_SIGNED_STAGE')=='staging-private-loopback'
    with open('/proc/net/dev') as devices:
        assert re.findall(r'^\s*([^:\s]+):',devices.read(),re.M)==['lo']
    assert Path('/proc/1/ns/pid').stat().st_ino==Path('/proc/self/ns/pid').stat().st_ino
    with tempfile.TemporaryDirectory(prefix='signed-fixture-') as tmp,ExitStack() as cleanup:
        fixture=Path(tmp)/'signed_worker_fixture.py'
        fixture.write_text("""
import os,secrets,sys
from celery import Celery
from celery.worker.control import inspect_command
from test_celery_signed_origin import NAMES,frame,local_incarnation,signer
app=Celery('fixture',broker='redis://127.0.0.1:6379/0')
app.conf.update(accept_content=['json'],task_serializer='json',control_exchange='celery',
    broker_transport_options={'fanout_prefix':True,'fanout_patterns':True,'global_keyprefix':''})
name=sys.argv[1]
seed=secrets.token_bytes(32)
pub_fd=int(sys.argv[2])
assert os.write(pub_fd,signer(seed).encode('ascii'))==64
os.close(pub_fd)
@inspect_command(name='ping',default_timeout=.2)
def fixture_ping(state,samwise_readiness_nonce=None):
    if samwise_readiness_nonce is None:
        return {'ok':'pong'}
    assert state.hostname==name and os.getuid() in (65530,65531,65532)
    assert os.getgid()==os.getuid() and not os.getgroups()
    return frame(name,local_incarnation(os.getpid()),samwise_readiness_nonce,seed)[name]
app.Worker(hostname=name, pool='solo', concurrency=1, without_mingle=True,
           without_gossip=True,without_heartbeat=True,loglevel='ERROR').start()
""")
        assert os.geteuid()==0
        uid_map=[tuple(map(int,line.split())) for line in Path('/proc/self/uid_map').read_text().splitlines()]
        assert any(first==0 and outer>0 and count>0 for first,outer,count in uid_map)
        Path(tmp).chmod(0o755)
        base={'PATH':'/usr/bin:/bin','HOME':'/tmp',
              'PYTHONPATH':os.environ['PYTHONPATH']+':'+tmp,'PYTHONDONTWRITEBYTECODE':'1'}
        def stop(p):
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=2)
        def run(argv, uid=None, pass_fds=()):
            creds={} if uid is None else {'user':uid,'group':uid,'extra_groups':[]}
            p=subprocess.Popen(argv,cwd=tmp,env=base,**creds,pass_fds=pass_fds,
                               close_fds=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            cleanup.callback(stop,p)
            return p
        def worker(name,uid):
            read,write=os.pipe2(os.O_CLOEXEC)
            try:
                try:
                    p=run([sys.executable,'-B',str(fixture),name,str(write)],uid,(write,))
                finally:
                    os.close(write)
                assert select.select([read],[],[],4)[0]
                raw=os.read(read,65)
                assert len(raw)==64 and p.poll() is None
                return p,raw.decode('ascii')
            finally:
                os.close(read)
        def cross_proc_refused(uid,pid):
            # Same private kernel only; no attempted access outside this pair.
            source="""import errno,sys
try:
    fd=open('/proc/'+sys.argv[1]+'/mem','rb')
except OSError as err:
    assert err.errno in (errno.EACCES,errno.EPERM)
else:
    fd.close()
    raise AssertionError('cross_role_memory_read_allowed')
"""
            with subprocess.Popen([sys.executable,'-I','-c',source,str(pid)],env=base,
                    user=uid,group=uid,extra_groups=[],close_fds=True,stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) as probe:
                assert probe.wait(timeout=2)==0
        def ready(admin, count):
            for _ in range(100):
                if sum(int(x.get('psub',0))>0 for x in admin.client_list())>=count:
                    return
                time.sleep(.05)
            raise AssertionError('fixture_workers_not_ready')
        broker_dir=Path(tmp)/'broker'
        broker_dir.mkdir(mode=0o777)
        broker_dir.chmod(0o777)
        broker=run([os.environ['SAMWISE_STAGE_REDIS'],'--bind','127.0.0.1','--port','6379',
                    '--save','','--appendonly','no','--daemonize','no','--dir',str(broker_dir)],65532)
        with redis.Redis(host='127.0.0.1',port=6379,socket_timeout=.3) as admin:
            for _ in range(100):
                try:
                    if admin.ping():
                        break
                except redis.RedisError:
                    assert broker.poll() is None
                    time.sleep(.05)
            else:
                raise AssertionError('fixture_broker_not_ready')
            started={n:worker(n,uid) for n,uid in zip(NAMES,(65530,65531))}
            workers={n:w for n,(w,key) in started.items()}
            keys={n:key for n,(w,key) in started.items()}
            ready(admin,2)
            cross_proc_refused(65530,workers[NAMES[1]].pid)
            cross_proc_refused(65531,workers[NAMES[0]].pid)
            baseline={n:local_incarnation(w.pid) for n,w in workers.items()}
            nonce=origin.challenge()
            def qualified(raw):
                assert len(raw)==2
                for n,w in workers.items():
                    assert local_incarnation(w.pid)==baseline[n]
                return origin.qualify(raw,NAMES,keys,baseline,nonce,SCOPE)
            began=time.monotonic()
            assert site.capture(Celery,NAMES,qualified,nonce=nonce)=={n:{'ok':'pong'} for n in NAMES}
            good=time.monotonic()-began
            rogue,_=worker(NAMES[0],65532)
            ready(admin,3)
            hostile=origin.challenge()
            frames=lambda raw: origin.qualify(raw,NAMES,keys,baseline,hostile,SCOPE)
            try:
                site.capture(Celery,NAMES,frames,nonce=hostile)
            except ValueError:
                pass
            else:
                raise AssertionError('duplicate_or_foreign_publication_accepted')
            stop(rogue)
            stop(workers[NAMES[0]])
            rogue,_=worker(NAMES[0],65532)
            ready(admin,2)
            restart=origin.challenge()
            # Even if expected PID/start data reflected the new process, wrong
            # per-role key must still reject it independently.
            changed=baseline|{NAMES[0]:local_incarnation(rogue.pid)}
            assert changed[NAMES[0]]!=baseline[NAMES[0]]
            try:
                site.capture(Celery,NAMES,lambda raw:origin.qualify(
                    raw,NAMES,keys,changed,restart,SCOPE),nonce=restart)
            except ValueError:
                pass
            else:
                raise AssertionError('wrong_key_after_restart_accepted')
        print(f'signed_origin_fixture_ready_seconds={good:.3f} duplicate_denied=1 wrong_key_after_restart_denied=1 cross_role_key_memory_denied=2')


if __name__=='__main__':
    if sys.argv[1:]==['--staging-private-fixture']:
        stage_driver()
    else:
        unittest.main()
