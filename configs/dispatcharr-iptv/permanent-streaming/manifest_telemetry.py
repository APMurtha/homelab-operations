"""Metadata only: normalize as enforcement does; never decide media delivery."""
import collections,threading,time,re
class ManifestTelemetry:
 def __init__(self,clock=time.monotonic):
  self.clock=clock;self.lock=threading.Lock();self.last=None;self.links=collections.OrderedDict()
 @staticmethod
 def parse(data):
  try:
   lines=[line.strip() for line in data.decode('utf-8-sig').splitlines() if line.strip()]
   if not lines or lines[0]!='#EXTM3U':return None
   fields={};uris=[];pending=False;discontinuities=0
   for line in lines[1:]:
    match=re.fullmatch(r'#EXT-X-(MEDIA-SEQUENCE|TARGETDURATION|DISCONTINUITY-SEQUENCE):([0-9]{1,16})',line)
    if match:
     if match[1] in fields:return None
     fields[match[1]]=int(match[2])
    elif line.startswith(('#EXT-X-MEDIA-SEQUENCE:','#EXT-X-TARGETDURATION:','#EXT-X-DISCONTINUITY-SEQUENCE:')):return None
    elif line.startswith('#EXTINF:'):
     if pending:return None
     pending=True
    elif not line.startswith('#'):
     if not pending:return None
     uris.append(line);pending=False
    elif line=='#EXT-X-DISCONTINUITY':discontinuities+=1
   if pending or not uris or 'MEDIA-SEQUENCE' not in fields or fields.get('TARGETDURATION',0)<=0:return None
   return {'media_sequence':fields['MEDIA-SEQUENCE'],'target_duration':fields['TARGETDURATION'],'discontinuity_sequence':fields.get('DISCONTINUITY-SEQUENCE',0),'discontinuities':discontinuities,'uris':uris}
  except (UnicodeError,ValueError):return None
 def observe(self,data,content_id,request_id,resource_id):
  parsed=self.parse(data)
  if parsed is None:return {'metadata_valid':0,'manifest_state':'metadata_invalid'}
  now=self.clock();seq=parsed['media_sequence']
  with self.lock:
   old=self.last
   state='first' if old is None else 'advanced' if seq>old['seq'] else 'regressed' if seq<old['seq'] else 'repeated' if content_id==old['content'] else 'changed_same_sequence'
   seq_since=now if old is None or seq!=old['seq'] else old['seq_since']
   content_since=now if old is None or content_id!=old['content'] else old['content_since']
   repeat=old['repeat']+1 if old is not None and content_id==old['content'] else 0
   delta=0 if old is None else seq-old['seq']
   self.last={'seq':seq,'seq_since':seq_since,'content':content_id,'content_since':content_since,'repeat':repeat}
   for index,uri in enumerate(parsed['uris']):
    key=resource_id(uri);self.links[key]={'manifest_request_id':request_id,'manifest_sequence':seq,'segment_sequence':seq+index};self.links.move_to_end(key)
    while len(self.links)>4096:self.links.popitem(last=False)
   return {**{k:v for k,v in parsed.items() if k!='uris'},'segments':len(parsed['uris']),'metadata_valid':1,'manifest_state':state,'sequence_delta':delta,'sequence_age_ms':round((now-seq_since)*1000,3),'content_age_ms':round((now-content_since)*1000,3),'repeat_count':repeat,'stale_candidate':int(now-seq_since>=parsed['target_duration']*2)}
 def segment(self,resource_id):
  with self.lock:return dict(self.links.get(resource_id,{}))
