"""Root-published metadata authorization, not a secret or kernel attestation.

Directory inode is pinned per worker; each read reopens current paths. Leases
bound stale bind mounts/crashed publishers to 300 seconds; revocation is observed
at existing I/O checks, not atomically with network use. No network operations.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
import uuid
import ipaddress
from urllib.parse import urlsplit
from .provider_transport import Refused, digest, url
from .provider_readiness import Readiness, GUARD_FIELDS, GRANT_FIELDS

LEASE = 300
LIMIT = 65536
MAX_PROVIDERS = 64
PUBLIC = Path('/run/dispatcharr-provider-status')
PRIVATE_FIELDS = {'server_contract','provider_key','network_owner','purpose','schema','review_reference','boot_id','netns','host_netns','expires_epoch','vpn_interface','policy_review_sha256','endpoints','operations','epg_url_sha256'}
PUBLIC_FIELDS = PRIVATE_FIELDS - {'review_reference'}
RECORD_FIELDS = {'schema','generation','guard_generation','issued_epoch','anchor_dev','anchor_ino','policy'}


def refused():
    return Refused('provider_authorization_unavailable')


def hex64(value):
    return isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value) is not None


def boot():
    value=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if str(uuid.UUID(value))!=value: raise refused()
    return value


def number(value):
    return type(value) in (int,float) and math.isfinite(value)


def validate(p,key,public=False):
    if not isinstance(p,dict) or set(p)!=(PUBLIC_FIELDS if public else PRIVATE_FIELDS): raise refused()
    if (not hex64(key) or p['provider_key']!=key or p['server_contract']!='dispatcharr-native-airvpn-v1'
            or type(p['schema']) is not int or p['schema']!=1 or p['network_owner']!='AirVPN'
            or p['purpose']!='IPTV_METADATA_ONLY' or p['vpn_interface']!='tun0'
            or p['boot_id']!=boot() or not hex64(p['policy_review_sha256']) or not hex64(p['epg_url_sha256'])
            or not number(p['expires_epoch']) or not time.time()<p['expires_epoch']<=time.time()+86400): raise refused()
    if not public and (not isinstance(p['review_reference'],str) or not p['review_reference'].strip()): raise refused()
    for field in ('netns','host_netns'):
        if not isinstance(p[field],list) or len(p[field])!=2 or any(type(n) is not int or n<=0 for n in p[field]): raise refused()
    if p['netns']==p['host_netns']: raise refused()
    operations=p['operations']
    if not isinstance(operations,list) or not 1<=len(operations)<=3 or any(type(v) is not str for v in operations) or len(set(operations))!=len(operations) or not set(operations)<={'discover','refresh','epg'}: raise refused()
    endpoints=p['endpoints']
    if not isinstance(endpoints,list) or not 1<=len(endpoints)<=16: raise refused()
    seen=set()
    for e in endpoints:
        if not isinstance(e,dict) or set(e)!={'host','path_sha256' if public else 'path','ipv4'}: raise refused()
        if not isinstance(e['host'],str): raise refused()
        u=urlsplit(url('https://'+e['host']))
        if u.hostname!=e['host'] or u.netloc!=e['host'] or u.path or u.query: raise refused()
        path=e['path_sha256' if public else 'path']
        if public:
            if not hex64(path): raise refused()
        else:
            if not isinstance(path,str) or not path.startswith('/'): raise refused()
            target=urlsplit(url('https://'+e['host']+path))
            if target.path!=path or target.query: raise refused()
        pair=(e['host'],path)
        if pair in seen: raise refused()
        seen.add(pair);ips=e['ipv4']
        if not isinstance(ips,list) or not 1<=len(ips)<=16 or len(set(ips))!=len(ips): raise refused()
        if any(not isinstance(ip,str) or not ipaddress.IPv4Address(ip).is_global or str(ipaddress.IPv4Address(ip))!=ip for ip in ips): raise refused()
    return p


def project(p,key):
    validate(p,key)
    result=json.loads(json.dumps({k:v for k,v in p.items() if k!='review_reference'}))
    result['endpoints']=[{'host':e['host'],'path_sha256':digest(e['path']),'ipv4':e['ipv4']} for e in p['endpoints']]
    result['expires_epoch']=min(result['expires_epoch'],time.time()+LEASE)
    return result


def directory(path,mode):
    """Open trusted ancestry without following any symlink, including parents."""
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts: raise refused()
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd);fd=child
            st=os.fstat(fd)
            # Sticky root /tmp is allowed for isolated fixtures; final anchors
            # must have the exact required mode and can never be writable.
            sticky=st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o1777
            if st.st_uid!=0 or st.st_gid!=0 or (st.st_mode&0o022 and not sticky): raise refused()
        st=os.fstat(fd)
        if stat.S_IMODE(st.st_mode)!=mode or st.st_nlink==0: raise refused()
        return fd
    except BaseException:
        os.close(fd);raise


def read(fd,name,mode=0o644):
    file=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    with os.fdopen(file,'rb') as stream:
        st=os.fstat(stream.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=mode or st.st_size>LIMIT: raise refused()
        raw=stream.read(LIMIT+1)
    if len(raw)>LIMIT: raise refused()
    def pairs(items):
        result={}
        for k,v in items:
            if k in result: raise refused()
            result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(refused()))


def guard_snapshot(path,p):
    """Publisher validates an existing trusted grant; never creates a grant."""
    fd=directory(path,0o755)
    try:
        first=read(fd,'guard.json');grant=read(fd,'grant.json');second=read(fd,'guard.json')
        if (not isinstance(first,dict) or not isinstance(grant,dict) or set(first)!=GUARD_FIELDS or set(grant)!=GRANT_FIELDS
                or first!=second or any(grant[k]!=first[k] for k in GUARD_FIELDS)
                or type(first['schema']) is not int or first['schema']!=1
                or not hex64(first['generation']) or first['boot_id']!=p['boot_id']
                or first['policy_sha256']!=p['policy_review_sha256']
                or any(type(grant[k]) is not int or grant[k]<=0 for k in ('netns_dev','netns_ino'))
                or [grant['netns_dev'],grant['netns_ino']]!=p['netns']): raise refused()
        return first['generation']
    finally: os.close(fd)


class Reader:
    def __init__(self,directory=PUBLIC,guard='/guard-status'):
        self.directory=Path(directory);self.guard=guard;self.anchor=None

    def read(self,key):
        try:
            if not hex64(key): raise refused()
            fd=directory(self.directory,0o755)
            try:
                st=os.fstat(fd);identity=(st.st_dev,st.st_ino)
                if self.anchor is not None and identity!=self.anchor: raise refused()
                self.anchor=identity
                value=read(fd,key+'.json')
                # Detect host current-path replacement during this read.
                current=directory(self.directory,0o755)
                try:
                    st=os.fstat(current)
                    if (st.st_dev,st.st_ino)!=identity: raise refused()
                finally: os.close(current)
            finally: os.close(fd)
            if not isinstance(value,dict) or set(value)!=RECORD_FIELDS or type(value['schema']) is not int or value['schema']!=1: raise refused()
            if not hex64(value['generation']) or not hex64(value['guard_generation']): raise refused()
            if any(type(value[k]) is not int or value[k]<=0 for k in ('anchor_dev','anchor_ino')) or (value['anchor_dev'],value['anchor_ino'])!=identity: raise refused()
            p=validate(value['policy'],key,True);now=time.time()
            if not number(value['issued_epoch']) or not value['issued_epoch']<=now<p['expires_epoch']<=value['issued_epoch']+LEASE: raise refused()
            ns=Path('/proc/self/ns/net').stat()
            if p['netns']!=[ns.st_dev,ns.st_ino]: raise refused()
            r=Readiness(self.guard,p['policy_review_sha256'])
            if r.check()!=value['guard_generation']: raise refused()
            # Generations participate in each job's existing equality check.
            return {**p,'review_reference':'trusted_public_projection','authorization_generation':value['generation'],'guard_generation':value['guard_generation']}
        except Exception: raise refused() from None
