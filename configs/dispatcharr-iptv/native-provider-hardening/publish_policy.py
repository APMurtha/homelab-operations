"""Candidate root-only explicit publication/revocation; never installs itself.

No credentials/URLs in arguments. No networking, namespace entry or service
operations. Future lifecycle hooks must revoke before private-policy/guard changes.
"""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import secrets
import stat
import time
from runtime.provider_policy import (directory,read,project,guard_snapshot,hex64,
                                     MAX_PROVIDERS,LEASE,LIMIT,refused)


class Publisher:
    def __init__(self,private='/run/dispatcharr-provider',public='/run/dispatcharr-provider-status',guard='/run/dispatcharr-guard-status'):
        self.private=Path(private);self.public=Path(public);self.guard=Path(guard)

    @contextlib.contextmanager
    def lock(self):
        if os.geteuid()!=0 or os.getegid()!=0: raise refused()
        fd=directory(self.private,0o700)
        try:
            lock=os.open('.status-writer.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=fd)
            try:
                s=os.fstat(lock)
                if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_gid!=0 or stat.S_IMODE(s.st_mode)!=0o600 or s.st_nlink!=1: raise refused()
                # Nonblocking: an interrupted competing operation is not retried.
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                yield fd
            finally: os.close(lock)
        finally: os.close(fd)

    @staticmethod
    def write(fd,name,obj,mode):
        raw=json.dumps(obj,sort_keys=True,allow_nan=False,separators=(',',':')).encode()
        if len(raw)>LIMIT: raise refused()
        temporary='.partial-'+secrets.token_hex(16)
        file=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode,dir_fd=fd)
        try:
            with os.fdopen(file,'wb') as f:
                os.fchmod(f.fileno(),mode);os.fchown(f.fileno(),0,0)
                f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(temporary,name,src_dir_fd=fd,dst_dir_fd=fd);os.fsync(fd)
        finally:
            try:os.unlink(temporary,dir_fd=fd)
            except FileNotFoundError:pass

    def initialize(self):
        with self.lock() as private:
            # Never adopt an existing/unexplained or replaced public anchor.
            try:os.stat('.status-anchor.json',dir_fd=private,follow_symlinks=False)
            except FileNotFoundError:pass
            else:raise refused()
            self.public.mkdir(mode=0o755);self.public.chmod(0o755)
            fd=directory(self.public,0o755)
            try:
                st=os.fstat(fd)
                self.write(private,'.status-anchor.json',{'schema':1,'dev':st.st_dev,'ino':st.st_ino},0o600)
            finally:os.close(fd)

    @contextlib.contextmanager
    def anchor(self,private):
        expected=read(private,'.status-anchor.json',0o600)
        fd=directory(self.public,0o755)
        try:
            st=os.fstat(fd)
            if expected!={'schema':1,'dev':st.st_dev,'ino':st.st_ino}: raise refused()
            count=0
            with os.scandir(fd) as entries:
                for e in entries:
                    count+=1
                    if count>MAX_PROVIDERS or not e.name.endswith('.json') or not hex64(e.name[:-5]): raise refused()
                    s=e.stat(follow_symlinks=False)
                    if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_gid!=0 or s.st_nlink!=1 or stat.S_IMODE(s.st_mode)!=0o644: raise refused()
            yield fd
        finally:os.close(fd)

    @staticmethod
    def withdraw(fd,key):
        try:os.unlink(key+'.json',dir_fd=fd)
        except FileNotFoundError:pass
        os.fsync(fd)

    def revoke(self,key=None):
        if key is not None and not hex64(key): raise refused()
        with self.lock() as private,self.anchor(private) as fd:
            names=[key] if key else [name[:-5] for name in os.listdir(fd)]
            error=None
            for name in names:
                try:self.withdraw(fd,name)
                except Exception as exc:error=exc
            if error is not None:raise refused() from None

    def publish(self,key):
        if not hex64(key): raise refused()
        with self.lock() as private,self.anchor(private) as fd:
            # Withdraw BEFORE reading/validating the private policy or grant.
            self.withdraw(fd,key)
            try:
                p=project(read(private,key+'.json',0o600),key)
                generation=guard_snapshot(self.guard,p)
                count=len(os.listdir(fd))
                if count>=MAX_PROVIDERS: raise refused()
                issued=time.time()
                anchor=os.fstat(fd)
                record={'schema':1,'generation':secrets.token_hex(32),'guard_generation':generation,'issued_epoch':issued,'anchor_dev':anchor.st_dev,'anchor_ino':anchor.st_ino,'policy':p}
                # Expiry is never extended beyond the root-private approval.
                p['expires_epoch']=min(p['expires_epoch'],issued+LEASE)
                self.write(fd,key+'.json',record,0o644)
                if guard_snapshot(self.guard,p)!=generation: raise refused()
                return record['generation']
            except BaseException:
                self.withdraw(fd,key)
                raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['init','publish','revoke','revoke-all'])
    parser.add_argument('key',nargs='?')
    args=parser.parse_args()
    try:
        p=Publisher()
        if args.action=='init' and args.key is None:p.initialize()
        elif args.action=='revoke-all' and args.key is None:p.revoke()
        elif args.action=='publish' and args.key:p.publish(args.key)
        elif args.action=='revoke' and args.key:p.revoke(args.key)
        else:raise refused()
    except Exception:raise SystemExit('provider_authorization_operation_failed_no_retry') from None
    print('provider_authorization_operation_complete')

if __name__=='__main__':main()
