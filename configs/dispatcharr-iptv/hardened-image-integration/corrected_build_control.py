"""One authorized COPY-only build with read-only layer verification; no probes.
Private state supplies exact approved public source bytes. Never runs an image.
"""
import argparse,base64,hashlib,io,json,os,re,stat,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
D=['docker','-H','unix:///var/run/docker.sock']

def sha(v):return hashlib.sha256(v).hexdigest()
def canon(v):return sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def command(args,timeout=30):
 p=subprocess.run(D+args,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('docker_read_failed_'+args[0])
 return p.stdout.strip()
def atomic(path,value):
 tmp=path.with_suffix('.tmp');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f,sort_keys=True);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path);fd=os.open(path.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
def capacity(work):
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 fs=os.statvfs(work);v={'load':list(os.getloadavg()),'memory_available_bytes':mem,'disk_available_bytes':fs.f_bavail*fs.f_frsize,'epoch':time.time()}
 v['passed']=v['load'][0]<=2 and mem>=2*1024**3 and v['disk_available_bytes']>=3*1024**3
 return v

def snapshot():
 ids=command(['ps','-aq','--no-trunc']).split();rows={}
 for c in json.loads(command(['inspect',*ids])) if ids else []:
  rows[c['Name'].lstrip('/') ]={'id':c['Id'],'image':c['Image'],'started':c['State']['StartedAt'],'restarts':c['RestartCount'],'status':c['State']['Status'],'health':c['State'].get('Health',{}).get('Status'),'configuration_sha256':canon({k:c[k] for k in ['Config','HostConfig','Mounts']})}
 nets=command(['network','ls','-q']).split();vols=command(['volume','ls','-q']).split()
 return {'containers':rows,'networks_sha256':canon(json.loads(command(['network','inspect',*nets])) if nets else []),'volumes_sha256':canon(json.loads(command(['volume','inspect',*vols])) if vols else [])}
def healthy(before):
 if len(before['containers'])!=33 or any(before['containers'].get(n,{}).get('health')!='healthy' for n in ['dispatcharr','rivendell-iptv-vpn','rivendell-iptv-relay','rivendell-iptv-gateway','jellyfin']):raise RuntimeError('production_health_or_inventory_gate')
def image_meta(image):
 v=json.loads(command(['image','inspect',image]))[0]
 return {'id':v['Id'],'tags':v.get('RepoTags') or [],'layers':v['RootFS']['Layers'],'size':v['Size'],'created':v['Created'],'config_sha256':canon(v['Config']),'revision':v['Config'].get('Labels',{}).get('org.opencontainers.image.revision'),'onbuild':v['Config'].get('OnBuild'),'volumes':v['Config'].get('Volumes')}

class Prefix:
 def __init__(self,first,rest):self.first=first;self.rest=rest
 def read(self,n=-1):
  if n<0:raise RuntimeError('unbounded_stream_read')
  first=self.first[:n];self.first=self.first[n:]
  return first+self.rest.read(n-len(first)) if len(first)<n else first

def scan_stream(stream,expected):
 wanted={'app/'+n for n in expected};dirs={'app'}
 for f in wanted:dirs.update(str(p) for p in PurePosixPath(f).parents if str(p)!='.')
 layers={};manifest=None;private='run/dispatcharr-provider';public='run/dispatcharr-provider-status'
 with tarfile.open(fileobj=stream,mode='r|') as outer:
  for member in outer:
   if not member.isfile():continue
   body=outer.extractfile(member)
   if member.name=='manifest.json':manifest=json.load(body);continue
   first=body.read(min(512,member.size))
   if first.lstrip().startswith((b'{',b'[')):continue
   found={};deletes=[];opaque=[]
   try:
    with tarfile.open(fileobj=Prefix(first,body),mode='r|*') as layer:
     for item in layer:
      name=item.name.removeprefix('./').rstrip('/');p=PurePosixPath(name)
      if p.name=='.wh..wh..opq':opaque.append(str(p.parent));continue
      if p.name.startswith('.wh.'):deletes.append(str(p.with_name(p.name[4:])));continue
      selected=name in wanted or name in dirs or name==private or name.startswith(private+'/') or name==public or name.startswith(public+'/')
      if selected:
       entry={'uid':item.uid,'gid':item.gid,'mode':oct(item.mode&0o7777),'type':'file' if item.isfile() else 'directory' if item.isdir() else 'other','acl_present':any('acl' in k.lower() for k in item.pax_headers)}
       if name in wanted:
        if not item.isfile() or item.size>2*1024**2:raise RuntimeError('source_type_or_size_refused')
        entry['sha256']=sha(layer.extractfile(item).read())
       found[name]=entry
      if len(layer.members)>1000:layer.members.clear()
   except tarfile.ReadError:continue
   layers[member.name]=(found,deletes,opaque)
   if len(outer.members)>1000:outer.members.clear()
 if not isinstance(manifest,list) or len(manifest)!=1:raise RuntimeError('image_manifest_refused')
 selected={}
 for name in manifest[0]['Layers']:
  if name not in layers:raise RuntimeError('missing_layer')
  found,deletes,opaque=layers[name]
  for k in list(selected):
   if any(k==d or k.startswith(d+'/') for d in deletes) or any(d in ('.','') or k.startswith(d+'/') for d in opaque):del selected[k]
  selected.update(found)
 for path,h in expected.items():
  v=selected.get('app/'+path)
  if v is None or v.get('sha256')!=h:raise RuntimeError('image_source_hash_refused_'+path)
  if (v['uid'],v['gid'],v['mode'],v['type'],v['acl_present'])!=(0,0,'0o644','file',False):raise RuntimeError('source_permission_refused_'+path)
 for path in dirs:
  v=selected.get(path)
  if v is None or (v['uid'],v['gid'],v['mode'],v['type'],v['acl_present'])!=(0,0,'0o755','directory',False):raise RuntimeError('directory_permission_refused_'+path)
 if any(k==private or k.startswith(private+'/') or k==public or k.startswith(public+'/') for k in selected):raise RuntimeError('unexpected_provider_runtime_state_in_image')
 return {'hashes':{n:selected['app/'+n]['sha256'] for n in expected},'source_metadata':{n:selected['app/'+n] for n in expected},'directory_metadata':{n:selected[n] for n in sorted(dirs)},'provider_runtime_state_absent':True,'verification':'streamed image layers; no containers or application execution'}

def scan(image,expected):
 meta=image_meta(image)
 if meta['id']!=image:raise RuntimeError('immutable_image_drift')
 start=time.monotonic();p=subprocess.Popen(D+['image','save',image],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
 try:
  result=scan_stream(p.stdout,expected)
  if p.wait(timeout=30):raise RuntimeError('image_export_failed')
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=10)
 result.update(image=image,export_exit_code=0,elapsed_seconds=time.monotonic()-start,verified_epoch=time.time());return result

def transport_probe(work):
 st=work.stat()
 if (st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode))!=(0,0,0o700):raise RuntimeError('private_transport_metadata_refused')
 r,w=os.pipe();pid=os.fork()
 if pid==0:
  os.close(r);os.setgroups([]);os.setgid(1000);os.setuid(1000)
  try:list(work.iterdir());denied=False
  except PermissionError:denied=True
  os.write(w,b'yes' if denied else b'no');os._exit(0)
 os.close(w);value=os.read(r,4);os.close(r);os.waitpid(pid,0)
 if value!=b'yes':raise RuntimeError('UID1000_transport_access_not_denied')
 return {'uid':0,'gid':0,'mode':'0700','actual_UID1000_traversal_denied':True}

def phase(work,action):
 if os.geteuid()!=0:raise RuntimeError('root_private_build_transport_required')
 os.umask(0o077);state=json.loads((work/'state.json').read_text());recipe=(work/'build_once.py').read_bytes()
 if sha(recipe)!=state['recipe_sha256']:raise RuntimeError('reviewed_recipe_drift')
 module={'__name__':'reviewed_build_recipe'};exec(compile(recipe,str(work/'build_once.py'),'exec'),module)
 if action=='preflight':
  if (work/'preflight.json').exists():raise RuntimeError('preflight_receipt_already_exists')
  pre={'snapshot':snapshot(),'capacity':capacity(work),'base':image_meta(state['base']),'old_image':image_meta(state['old_image']),'transport':transport_probe(work)}
  atomic(work/'preflight.json',pre);healthy(pre['snapshot'])
  if pre['snapshot']!=state['expected_production']:raise RuntimeError('accepted_production_fingerprint_drift')
  if not pre['capacity']['passed']:raise RuntimeError('initial_capacity_refused')
  if pre['base']['id']!=state['base'] or pre['base']['onbuild'] is not None or pre['base']['volumes'] is not None:raise RuntimeError('base_metadata_refused')
  check=subprocess.run(D+['image','inspect',state['tag']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  if check.returncode!=1:raise RuntimeError('tag_not_proven_unused')
  verified=scan(state['base'],state['base_hashes']);atomic(work/'base-verification.json',verified)
  module['write_context'](work/'context',state['files'])
  for p in (work/'context').rglob('*'):
   st=p.lstat()
   if st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=(0o755 if p.is_dir() else 0o644):raise RuntimeError('build_context_permissions_refused')
  atomic(work/'preflight-complete.json',{'passed':True,'base_verified_epoch':verified['verified_epoch'],'context_files':len(state['files'])});print(json.dumps({'preflight_passed':True,'capacity':pre['capacity'],'base_hashes':len(verified['hashes']),'transport':pre['transport'],'work':str(work)}))
 elif action=='build':
  pre=json.loads((work/'preflight.json').read_text());verified=json.loads((work/'base-verification.json').read_text())
  if not (work/'preflight-complete.json').exists() or time.time()-verified['verified_epoch']<120:raise RuntimeError('verification_or_stabilization_incomplete')
  now=capacity(work);atomic(work/'build-capacity.json',now)
  if not now['passed']:raise RuntimeError('final_build_capacity_refused')
  if snapshot()!=pre['snapshot'] or image_meta(state['old_image'])!=pre['old_image']:raise RuntimeError('production_or_old_image_drift')
  for name,item in state['files'].items():
   if sha((work/'context'/name).read_bytes())!=item['sha256']:raise RuntimeError('context_drift')
  if subprocess.run(D+['image','inspect',state['tag']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=1:raise RuntimeError('tag_not_unused')
  command_line=D+['build','--pull=false','--network=none','--no-cache','--memory=512m','--memory-swap=512m','--cpu-period=100000','--cpu-quota=50000','--label','org.opencontainers.image.revision='+state['commit'],'--iidfile',str(work/'image.id'),'-t',state['tag'],str(work/'context')]
  fd=os.open(work/'build-intent.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:json.dump({'state':'intent','command':command_line,'epoch':time.time()},f);f.flush();os.fsync(f.fileno())
  start=time.monotonic()
  try:
   with (work/'build.log').open('wb') as log:p=subprocess.run(command_line,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'DOCKER_BUILDKIT':'0'},timeout=180)
  except BaseException:
   atomic(work/'build-result.json',{'state':'uncertain','reason':'build_process_interrupted_or_timeout'});raise
  receipt={'state':'built' if p.returncode==0 else 'failed','exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start,'command':command_line,'capacity':now}
  if p.returncode==0:
   receipt['image_id']=(work/'image.id').read_text().strip()
   if not re.fullmatch('sha256:[a-f0-9]{64}',receipt['image_id']):raise RuntimeError('invalid_image_identity')
  atomic(work/'build-result.json',receipt);print(json.dumps(receipt))
  if p.returncode:raise RuntimeError('single_build_failed_no_retry')
 elif action=='verify':
  result=json.loads((work/'build-result.json').read_text());pre=json.loads((work/'preflight.json').read_text())
  if result['state']!='built':raise RuntimeError('build_not_successful')
  image=result['image_id'];meta=image_meta(image)
  if meta['revision']!=state['commit'] or meta['layers'][:len(pre['base']['layers'])]!=pre['base']['layers'] or image_meta(state['tag'])['id']!=image:raise RuntimeError('image_provenance_refused')
  verified=scan(image,state['expected']);atomic(work/'image-verification.json',verified)
  post=snapshot();preserved=post==pre['snapshot'];old=image_meta(state['old_image'])==pre['old_image'];healthy(post)
  report={'state':'verified' if preserved and old else 'failed','image':meta,'old_image_preserved':old,'production_unchanged':preserved,'postflight':post,'source_hashes':verified['hashes'],'transport':transport_probe(work),'build_log_sha256':sha((work/'build.log').read_bytes())}
  atomic(work/'acceptance.json',report);print(json.dumps({'state':report['state'],'image_id':image,'verified_sources':len(verified['hashes']),'production_unchanged':preserved,'old_image_preserved':old}))
  if not preserved or not old:raise RuntimeError('production_preservation_refused')
 elif action=='collect':
  names=['preflight.json','preflight-complete.json','base-verification.json','build-capacity.json','build-intent.json','build-result.json','image-verification.json','acceptance.json','failure.json']
  out={n:json.loads((work/n).read_text()) for n in names if (work/n).exists()};out['private_receipts_sha256']={n:sha((work/n).read_bytes()) for n in names if (work/n).exists()};print(json.dumps(out))
 else:raise RuntimeError('unknown_phase')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('work',type=Path);parser.add_argument('action',choices=['preflight','build','verify','collect']);args=parser.parse_args()
 try:phase(args.work,args.action)
 except BaseException as error:
  if args.work.exists():atomic(args.work/'failure.json',{'phase':args.action,'classification':type(error).__name__,'reason':str(error) if isinstance(error,RuntimeError) and re.fullmatch('[A-Za-z0-9_/.:-]{1,200}',str(error)) else 'details_withheld','epoch':time.time()})
  raise SystemExit('build control refused; private receipt retained')
