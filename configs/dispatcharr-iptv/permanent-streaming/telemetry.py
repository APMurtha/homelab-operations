"""Bounded, asynchronous, allowlisted telemetry. Never serialize arbitrary errors/URLs."""
import collections,datetime,json,os,queue,re,secrets,threading,time
STAGES={'fetch','guard','dns','connect','tls','request','headers','body','body_first_byte','manifest_validation','segment_validation','local_send','ffmpeg','application','redis','client_read','client_process','metrics_write','gateway'}
OUTCOMES={'start','ok','timeout','cancelled','dns_failure','http_failure','security_rejection','io_failure','internal_error','sample','eof','gap','disconnect'}
NUMERIC={'duration_ms','remaining_ms','status','bytes','answers','media_sequence','segments','target_duration','speed','fps','media_seconds','output_bytes','head','published_ms','progress_ms','pttl_ms','client_bytes','client_chunks','evicted_keys','rchar','wchar','cpu_ticks','gap_ms','processing_ms','read_ms','queue_bytes','metadata_valid','sequence_delta','sequence_age_ms','content_age_ms','repeat_count','stale_candidate','manifest_sequence','segment_sequence','discontinuity_sequence','discontinuities'}
IDS={'request_id','resource_id','content_id','generation_id','manifest_request_id'}
class Telemetry:
 def __init__(self,path=None,*,max_events=1024,max_bytes=8388608,run_id=None):
  if type(max_events) is not int or not 1<=max_events<=8192 or type(max_bytes) is not int or not 1<=max_bytes<=33554432:raise ValueError('telemetry_bounds')
  self.run_id=run_id or secrets.token_hex(8);
  if not re.fullmatch(r'[a-f0-9]{16}',self.run_id):raise ValueError('telemetry_run_id')
  self.source_id=secrets.token_hex(4);self.origin=time.monotonic_ns();self.wall=datetime.datetime.now(datetime.timezone.utc).isoformat();self.max_bytes=max_bytes;self.dropped=0;self.written=0;self.errors=0;self.seq=0;self.closed=False;self.lock=threading.Lock();self.q=queue.Queue(max_events);self.fd=None;self.worker=None
  if path is not None:
   self.path=path;self.file_bytes=0
   self.fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
   self.worker=threading.Thread(target=self._write,daemon=True,name='bounded-telemetry');self.worker.start()
   self.emit('fetch','sample',anchor=True)
 def emit(self,stage,outcome,**fields):
  if stage not in STAGES or outcome not in OUTCOMES:raise ValueError('telemetry_enum')
  for k,v in fields.items():
   if k in NUMERIC:
    if type(v) not in (int,float) or not __import__('math').isfinite(v):raise ValueError('telemetry_numeric')
   elif k in IDS:
    if not isinstance(v,str) or not re.fullmatch(r'[a-f0-9]{1,32}',v):raise ValueError('telemetry_identifier')
   elif k=='manifest_state':
    if v not in ['first','advanced','regressed','repeated','changed_same_sequence','metadata_invalid']:raise ValueError('telemetry_manifest_state')
   elif k=='kind':
    if v not in ['manifest','segment']:raise ValueError('telemetry_kind')
   elif k=='state':
    if v not in ['initializing','connecting','waiting_for_clients','active','buffering','stopping','stopped','error','unknown']:raise ValueError('telemetry_state')
   elif k=='anchor':
    if v is not True:raise ValueError('telemetry_anchor')
   else:raise ValueError('telemetry_field')
  if self.fd is None:return
  with self.lock:
   if self.closed:return
   self.seq+=1;record={'schema':1,'run':self.run_id,'source':self.source_id,'seq':self.seq,'t_ns':time.monotonic_ns(),'stage':stage,'outcome':outcome,**fields}
   if fields.get('anchor'):record['wall_UTC']=self.wall
   data=(json.dumps(record,separators=(',',':'),allow_nan=False)+'\n').encode()
   if len(data)>1024:self.dropped+=1;return
   try:self.q.put_nowait(data)
   except queue.Full:self.dropped+=1
 def _write(self):
  try:
   while True:
    item=self.q.get()
    try:
     if item is None:return
     if len(item)>self.max_bytes:self.dropped+=1;continue
     if self.file_bytes+len(item)>self.max_bytes:
      os.close(self.fd);self.fd=None
      os.replace(self.path,self.path+'.1')
      self.fd=os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);self.file_bytes=0
     view=memoryview(item)
     while view:
      n=os.write(self.fd,view)
      if n<=0:raise OSError('telemetry_no_progress')
      view=view[n:];self.written+=n;self.file_bytes+=n
    except OSError:self.errors+=1
    finally:self.q.task_done()
  finally:
   if self.fd is not None:os.close(self.fd);self.fd=None
 def close(self,timeout=.5):
  with self.lock:self.closed=True
  if self.worker:
   try:self.q.put_nowait(None)
   except queue.Full:
    try:self.q.get_nowait();self.q.task_done();self.dropped+=1
    except queue.Empty:pass
    try:self.q.put_nowait(None)
    except queue.Full:return False
   self.worker.join(timeout)
   return not self.worker.is_alive()
  return True
 def snapshot(self):return {'dropped':self.dropped,'errors':self.errors,'written_bytes':self.written,'queued':self.q.qsize()}
