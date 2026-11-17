"""One absolute budget and kill/reap DNS isolation; no retry or timeout reset."""
import contextlib,json,multiprocessing,os,selectors,socket,subprocess,sys,threading,time
from pathlib import Path
class FetchFailure(ValueError):
 category='internal_error'
 def __init__(self,code,stage='fetch'):super().__init__(code);self.code=code;self.stage=stage
class FetchTimeout(FetchFailure):category='timeout'
class Cancelled(FetchFailure):category='cancelled'
class DNSFailure(FetchFailure):category='dns_failure'
class HTTPFailure(FetchFailure):category='http_failure'
class Budget:
 def __init__(self,seconds,telemetry,ids,events=()):
  self.started=time.monotonic();self.end=self.started+seconds;self.stage_name='guard';self.reason=None;self.sock=None;self.lock=threading.Lock();self.done=threading.Event();self.events=events;self.telemetry=telemetry;self.ids=ids
  self.watcher=threading.Thread(target=self._watch,daemon=True,name='fetch-watchdog');self.watcher.start()
 def _watch(self):
  while not self.done.wait(min(.025,max(.001,self.end-time.monotonic()))):
   if any(e is not None and e.is_set() for e in self.events):self.abort('cancelled');return
   if time.monotonic()>=self.end:self.abort('timeout');return
 def abort(self,reason):
  with self.lock:
   if self.reason is None:self.reason=reason
   s=self.sock
  if s is not None:self.close_socket(s)
 @staticmethod
 def close_socket(s):
  try:s.shutdown(socket.SHUT_RDWR)
  except (OSError,ValueError):pass
  try:s.close()
  except (OSError,ValueError):pass
 def check(self):
  if any(e is not None and e.is_set() for e in self.events):self.abort('cancelled')
  if time.monotonic()>=self.end:self.abort('timeout')
  if self.reason=='timeout':raise FetchTimeout('total_fetch_deadline',self.stage_name)
  if self.reason:raise Cancelled('fetch_cancelled',self.stage_name)
  return self.end-time.monotonic()
 def socket(self,s):
  with self.lock:self.sock=s;aborted=self.reason is not None
  if aborted:self.close_socket(s)
  self.check();s.settimeout(self.check())
 @contextlib.contextmanager
 def stage(self,name):
  self.stage_name=name;self.check();start=time.monotonic();self.telemetry.emit(name,'start',**self.ids,remaining_ms=round(self.check()*1000,3))
  outcome='ok'
  try:yield;self.check()
  except FetchFailure as e:outcome=e.category;raise
  except Exception:
   try:self.check()
   except FetchFailure as e:outcome=e.category;raise
   outcome='io_failure';raise
  finally:self.telemetry.emit(name,outcome,**self.ids,duration_ms=round((time.monotonic()-start)*1000,3),remaining_ms=max(0,round((self.end-time.monotonic())*1000,3)))
 def close(self):
  self.done.set();self.watcher.join(.1)
  if self.sock is not None:self.close_socket(self.sock)

def _callable_child(send,resolver,host,port):
 try:send.send({'ok':True,'answers':resolver(host,port,socket.AF_UNSPEC,socket.SOCK_STREAM)})
 except Exception:send.send({'ok':False})
 finally:send.close()

class DNS:
 """Production exec helper; callable fork adapter exists only for injected fixture APIs."""
 def __init__(self,worker=None):self.worker=Path(worker or Path(__file__).with_name('dns_worker.py'));self.active=set();self.lock=threading.Lock();self.slots=threading.BoundedSemaphore(4)
 def resolve(self,host,port,budget,resolver=None):
  budget.check()
  if not self.slots.acquire(blocking=False):raise DNSFailure('dns_capacity','dns')
  try:return self._resolve(host,port,budget,resolver)
  finally:self.slots.release()
 def _resolve(self,host,port,budget,resolver=None):
  if resolver is not None:return self._fixture_callable(host,port,budget,resolver)
  proc=subprocess.Popen([sys.executable,'-I','-S',str(self.worker),host,str(port)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env={'LANG':'C.UTF-8'})
  with self.lock:self.active.add(proc.pid)
  selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ);data=bytearray()
  try:
   while True:
    wait=min(.025,budget.check())
    if not selector.select(wait):continue
    b=os.read(proc.stdout.fileno(),4096)
    if not b:break
    data.extend(b)
    if len(data)>65536:raise DNSFailure('dns_response_size','dns')
   budget.check();value=json.loads(data)
   if not value.get('ok'):raise DNSFailure('dns_resolution_failed','dns')
   return self._answers(value)
  except FetchFailure:raise
  except Exception as e:
   budget.check();raise DNSFailure('dns_resolution_failed','dns') from None
  finally:
   selector.close();proc.stdout.close()
   if proc.poll() is None:proc.kill()
   proc.wait(timeout=.5)
   with self.lock:self.active.discard(proc.pid)
 def _fixture_callable(self,host,port,budget,resolver):
  # Never selected by JSON configuration or the production default. Child may
  # only resolve; unlike a background thread it is killed/reaped on cancellation.
  recv,send=multiprocessing.get_context('fork').Pipe(duplex=False)
  proc=multiprocessing.get_context('fork').Process(target=_callable_child,args=(send,resolver,host,port),daemon=True);proc.start();send.close()
  with self.lock:self.active.add(proc.pid)
  try:
   while not recv.poll(min(.025,budget.check())):pass
   budget.check();value=recv.recv()
   if not value.get('ok'):raise DNSFailure('dns_resolution_failed','dns')
   return self._answers(value)
  except FetchFailure:raise
  except Exception:
   budget.check();raise DNSFailure('dns_resolution_failed','dns') from None
  finally:
   recv.close()
   if proc.is_alive():proc.kill()
   proc.join(.5)
   if proc.is_alive():raise DNSFailure('dns_cleanup_failed','dns')
   with self.lock:self.active.discard(proc.pid)
   proc.close()
 @staticmethod
 def _answers(value):
  answers=value.get('answers')
  if not isinstance(answers,(list,tuple)) or not 0<len(answers)<=64:raise DNSFailure('dns_answer_format','dns')
  return answers
