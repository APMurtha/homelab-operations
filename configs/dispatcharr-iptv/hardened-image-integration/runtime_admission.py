"""Offline-reviewable host admission state machine; never creates a container.

Measurements during the fixed interval are observations, not admission retries.
Only the caller can create a container, after the single final admitted result.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time

MEMORY_MIN=2*1024**3
DISK_MIN=1024**3
LOAD_MAX=2
STABILIZE_SECONDS=120
MAX_SECONDS=180
OBSERVATION_SECONDS=15
RECEIPT_MAX_AGE=30
RETAINED_IMAGE='sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439'

EXPECTED_SOURCES = {'apps/epg/api_views.py': '6fafed61eb78ebfdd669ab60745001948a63f708dd549175e8d4950a68ce0051', 'apps/epg/signals.py': 'a55f451c8af899edb79f201802e3533cf2139199c37abdb95fa4978a8dac2d8c', 'apps/epg/tasks.py': '3d94f0c6aa4eed6520d584d97ad85b62760a9ae80efeac640a690eabacc427c6', 'apps/m3u/api_views.py': '6c48c35abc821efbb428a74c832e7c8c018eef472d6f987505169cd83d902936', 'apps/m3u/signals.py': '7b7b35c2931f401ef179b132648496749c49c07fabf0dd85d6c019e10dbacd92', 'apps/m3u/tasks.py': '75a6eb9276ec96b0e5de2ae2b1274a63ffe47ef89cc8d6c1620a89e049467fb1', 'apps/proxy/live_proxy/input/buffer.py': '17d77baba54923ef3414a7051eebed9c27a891eb1479dd9c68a299e0d5f89810', 'apps/proxy/live_proxy/input/manager.py': 'ce2400eb4bcdaec43ee571b7982f85ca2cd719eec9acb0282976edb3684245cf', 'apps/proxy/live_proxy/output/ts/generator.py': 'db9200e53419a9ca3acb19ad05df49d3a4c9c06567d3e659c26214cecf5e312b', 'apps/proxy/live_proxy/readiness.py': 'fb4882ba579b14b0a2f7aec7306c8f31e1c7bb5f6c3acacce1a40dc62de1143b', 'core/api_urls.py': '8ba3069abff1d26ff9d0070fd83194097c8b6f565b0b0391f46f0709155de324', 'core/provider_dns.py': '28c9564793e1285eb72bb9d91ab24a85ccc3ca2f3db80398445d380b53d9af3a', 'core/provider_policy.py': '2691cc3eeed26f13869d7cdacc671f0e2eebcd46e54e944279ffe78dd0b82639', 'core/provider_readiness.py': '5f137b756a1a988d4641ccd8a13b6bd4e13849bbdb2539c22026c88f4d8cf698', 'core/provider_security.py': '8d3049e4dfb471f62a66c13a17e94da04e6cff3050e07121208327071c4ce004', 'core/provider_security_view.py': 'b3e77ccd704251b85cccdc8df9966ecc8d748a4a1542780512746886be31374b', 'core/provider_transport.py': '4032865e09c82b5a755af99ef2a8b62e88aca46e346321565dd0af783cec0d39', 'core/xtream_codes.py': 'ed31daaf05ee812cfa7750b423c8b8840ab19bca48cc3ee560202857848133fa'}

class Refused(RuntimeError):pass

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Journal:
    def __init__(self,work,attempt_id):
        if not isinstance(attempt_id,str) or not re.fullmatch('[a-z0-9][a-z0-9-]{7,63}',attempt_id):raise Refused('attempt_identity_required')
        work=Path(work);s=work.lstat()
        if not stat.S_ISDIR(s.st_mode) or stat.S_IMODE(s.st_mode)!=0o700 or s.st_uid!=os.geteuid():raise Refused('private_work_required')
        self.attempt_id=attempt_id;self.path=work/('runtime-attempt-'+attempt_id)
        try:self.path.mkdir(mode=0o700)
        except FileExistsError:raise Refused('duplicate_attempt_identity') from None
        fd=os.open(self.path/'admission.jsonl',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        os.close(fd);self.sequence=0
        self.record('attempt_reserved',{'attempt_id':attempt_id})
        fd=os.open(work,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)
    def record(self,event,details):
        self.sequence+=1
        if self.sequence>64:raise Refused('journal_limit')
        row={'schema':1,'sequence':self.sequence,'epoch_seconds':time.time(),'event':event,'details':details}
        data=json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
        if len(data)>16384:raise Refused('journal_record_limit')
        fd=os.open(self.path/'admission.jsonl',os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW)
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        fd=os.open(self.path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)
        return row


def measure(work,clock=time.monotonic):
    memory=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    load=list(os.getloadavg());disk=os.statvfs(work)
    return {'monotonic':clock(),'memory_available_bytes':memory,'disk_available_bytes':disk.f_bavail*disk.f_frsize,'load':load}


def capacity_valid(row):
    if not isinstance(row,dict):return False
    if any(type(row.get(k)) is not int or row[k]<0 for k in ['memory_available_bytes','disk_available_bytes']):return False
    load=row.get('load')
    return (isinstance(load,list) and len(load)==3 and all(type(v) in [int,float] and math.isfinite(v) and v>=0 for v in load)
        and type(row.get('monotonic')) in [int,float] and math.isfinite(row['monotonic']))


def verified(inspect,image,attempt_id,journal,clock=time.monotonic):
    if image!=RETAINED_IMAGE:raise Refused('unapproved_test_image')
    journal.record('verification_started',{'image_id':image})
    result=inspect(image,EXPECTED_SOURCES)
    if (not isinstance(result,dict) or result.get('base',{}).get('id')!=image
            or result.get('hashes')!=EXPECTED_SOURCES or result.get('process_exited') is not True
            or type(result.get('exit_code')) is not int or result['exit_code']!=0):raise Refused('verification_incomplete')
    receipt={'image_id':image,'attempt_id':attempt_id,'source_hashes':dict(EXPECTED_SOURCES),
        'completed_monotonic':clock(),'exit_code':0,'process_exited':True,'source_contract_sha256':digest(EXPECTED_SOURCES)}
    journal.record('verification_completed',receipt)
    return receipt


def receipt_valid(receipt,image,attempt_id,now):
    if not isinstance(receipt,dict):return False
    timestamp=receipt.get('completed_monotonic')
    return (image==RETAINED_IMAGE and receipt.get('image_id')==image and receipt.get('attempt_id')==attempt_id
        and receipt.get('source_hashes')==EXPECTED_SOURCES and receipt.get('source_contract_sha256')==digest(EXPECTED_SOURCES)
        and receipt.get('process_exited') is True and type(receipt.get('exit_code')) is int and receipt['exit_code']==0
        and type(timestamp) in [int,float] and math.isfinite(timestamp) and 0<=now-timestamp<=RECEIPT_MAX_AGE)


def stabilize(receipt,image,attempt_id,baseline,probe,capacity,journal,*,clock=time.monotonic,sleep=time.sleep,seconds=STABILIZE_SECONDS):
    if type(seconds) is not int or not 1<=seconds<=MAX_SECONDS:raise Refused('invalid_stabilization_interval')
    started=clock()
    if not receipt_valid(receipt,image,attempt_id,started):raise Refused('missing_or_stale_verification')
    contract=digest(EXPECTED_SOURCES);deadline=started+MAX_SECONDS
    journal.record('stabilization_started',{'monotonic':started,'fixed_seconds':seconds,'maximum_seconds':MAX_SECONDS,'observation_seconds':OBSERVATION_SECONDS})
    completed=False
    try:
        while True:
            now=clock()
            if now<started or now>=deadline:raise Refused('stabilization_timeout')
            # Probe must bound each cheap identity/health command by deadline.
            current=probe(deadline)
            now=clock()
            if now<started or now>deadline:raise Refused('stabilization_timeout')
            if current.get('image_id')!=image:raise Refused('image_changed')
            if current.get('production')!=baseline:raise Refused('production_changed')
            if digest(EXPECTED_SOURCES)!=contract or receipt['source_hashes']!=EXPECTED_SOURCES:raise Refused('source_contract_changed')
            row=capacity()
            if not capacity_valid(row):raise Refused('invalid_capacity_measurement')
            now=clock()
            if now<started or now>deadline:raise Refused('stabilization_timeout')
            if not started<=row['monotonic']<=now or now-row['monotonic']>5:raise Refused('stale_capacity_measurement')
            journal.record('capacity_observation',row)
            now=clock()
            if now>deadline:raise Refused('stabilization_timeout')
            if now-row['monotonic']>5:raise Refused('stale_capacity_measurement')
            elapsed=now-started
            if elapsed>=seconds:
                journal.record('stabilization_ended',{'monotonic':now,'elapsed_seconds':elapsed,'completed':True})
                completed=True
                now=clock()
                if now>deadline:raise Refused('stabilization_timeout')
                if now-row['monotonic']>5:raise Refused('stale_capacity_measurement')
                decision={'admitted':row['memory_available_bytes']>=MEMORY_MIN and row['disk_available_bytes']>=DISK_MIN and row['load'][0]<=LOAD_MAX,
                    'measurement':row,'memory_min_bytes':MEMORY_MIN,'disk_min_bytes':DISK_MIN,'load1_max':LOAD_MAX,'elapsed_seconds':elapsed}
                journal.record('admission_decision',decision)
                if clock()>deadline:
                    journal.record('admission_invalidated',{'reason':'evidence_write_exceeded_deadline'})
                    raise Refused('admission_evidence_timeout')
                if not decision['admitted']:raise Refused('final_capacity_refused')
                return decision
            sleep(min(OBSERVATION_SECONDS,seconds-elapsed))
    finally:
        if not completed:journal.record('stabilization_ended',{'monotonic':clock(),'elapsed_seconds':clock()-started,'completed':False})
