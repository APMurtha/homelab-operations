"""Unprivileged, bounded current-path authorization snapshot; never kernel attestation."""
import json
import os
from pathlib import Path
import re
import stat
import uuid

GUARD_FIELDS={'schema','boot_id','generation','policy_sha256'}
GRANT_FIELDS=GUARD_FIELDS|{'netns_dev','netns_ino'}


def boot_identity():
    value=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if str(uuid.UUID(value))!=value:raise ValueError('invalid_host_boot')
    return value


def namespace():
    st=Path('/proc/self/ns/net').stat()
    return st.st_dev,st.st_ino


def pairs(items):
    out={}
    for k,v in items:
        if k in out:raise ValueError('duplicate_field')
        out[k]=v
    return out


class Readiness:
    def __init__(self,directory,digest):
        if not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest):raise ValueError('policy_digest_invalid')
        self.directory=Path(directory);self.digest=digest;self.boot=boot_identity()
        self.anchor=None
        self.expected=self.read('grant.json',GRANT_FIELDS)
        self.check()

    def read(self,name,fields):
        d=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            st=os.fstat(d);identity=(st.st_dev,st.st_ino)
            if st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o755 or st.st_nlink==0:
                raise ValueError('unsafe_status_anchor')
            if self.anchor is not None and self.anchor!=identity:raise ValueError('status_anchor_replaced')
            self.anchor=identity
            with os.scandir(d) as entries:
                if any(entry.name not in {'guard.json','grant.json'} for entry in entries):raise ValueError('unexpected_status_file')
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=d)
            with os.fdopen(fd,'rb') as f:
                st=os.fstat(f.fileno())
                if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o644 or st.st_nlink!=1:
                    raise ValueError('unsafe_status_file')
                raw=f.read(2049)
            if len(raw)>2048:raise ValueError('status_size_limit')
            value=json.loads(raw,object_pairs_hook=pairs)
            if not isinstance(value,dict) or set(value)!=fields or type(value['schema']) is not int or value['schema']!=1:
                raise ValueError('status_schema')
            for key in ['generation','policy_sha256']:
                if not isinstance(value[key],str) or not re.fullmatch('[a-f0-9]{64}',value[key]):raise ValueError('status_digest')
            if not isinstance(value['boot_id'],str) or str(uuid.UUID(value['boot_id']))!=value['boot_id']:raise ValueError('status_boot')
            for key in fields-GUARD_FIELDS:
                if type(value[key]) is not int or value[key]<=0:raise ValueError('status_namespace')
            return value
        finally:os.close(d)

    def check(self):
        first=self.read('guard.json',GUARD_FIELDS)
        grant=self.read('grant.json',GRANT_FIELDS)
        second=self.read('guard.json',GUARD_FIELDS)
        if first!=second or grant!=self.expected or any(grant[k]!=first[k] for k in GUARD_FIELDS):raise ValueError('generation_changed')
        if boot_identity()!=self.boot or first['boot_id']!=self.boot or first['policy_sha256']!=self.digest:raise ValueError('boot_or_policy_changed')
        if (grant['netns_dev'],grant['netns_ino'])!=namespace():raise ValueError('wrong_relay_namespace')
        return first['generation']
