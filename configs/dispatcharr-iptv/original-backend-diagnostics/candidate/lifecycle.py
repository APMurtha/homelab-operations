"""Future systemd entrypoint; exact project only. Never call during offline tests."""
import argparse
import importlib.util
import sys
import os
from pathlib import Path
import stat
import subprocess
import time

ROOT = Path('/docker/dispatcharr-iptv')
HERE = ROOT / 'permanent-streaming'
COMPOSE = ['docker','compose','--project-name','rivendell-iptv','--project-directory',str(ROOT),'-f',str(HERE/'compose.yaml')]
UP = ['up','--detach','--no-build','--pull','never','--no-recreate','--wait','--wait-timeout','360']


def trusted():
    sys.path.insert(0,str(ROOT))
    spec=importlib.util.spec_from_file_location('trusted_lifecycle_guard',ROOT/'guard.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.Publisher()


def execute(args, timeout=380):
    result = subprocess.run(args, capture_output=True, timeout=timeout)
    if result.returncode: raise ValueError('scoped_command_failed')


# Only backend invocation output uses this path. Other execute()/cleanup is unchanged.
import json
import selectors
import secrets

MAX_CAPTURE = 4096
MAX_RECEIPT = 16384
GENERIC_BACKEND = b'Backend readiness refused; values withheld.'


def _protocol():
    spec=importlib.util.spec_from_file_location('original_backend_diagnostic_schema',HERE/'backend.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def _private_dir():
    target=ROOT/'private'/'backend-diagnostics'
    for path in [ROOT,*ROOT.parents]:
        st=path.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)&0o022:
            raise ValueError('diagnostic_ancestor_unsafe')
    if os.geteuid()!=0 or os.getegid()!=0:raise ValueError('diagnostic_writer_not_root')
    private=ROOT/'private';st=private.lstat()
    if not stat.S_ISDIR(st.st_mode) or (st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode))!=(0,0,0o700):raise ValueError('diagnostic_private_unsafe')
    parent=os.open(private,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        actual=os.fstat(parent)
        if (actual.st_dev,actual.st_ino)!=(st.st_dev,st.st_ino) or (actual.st_uid,actual.st_gid,stat.S_IMODE(actual.st_mode))!=(0,0,0o700):raise ValueError('diagnostic_parent_changed')
        try:os.mkdir('backend-diagnostics',0o700,dir_fd=parent)
        except FileExistsError:pass
        os.fsync(parent)  # Persist a newly created private-directory entry before launch.
        fd=os.open('backend-diagnostics',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
    finally:os.close(parent)
    try:
        st=os.fstat(fd)
        if (st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode))!=(0,0,0o700):raise ValueError('diagnostic_directory_unsafe')
        return target,fd
    except BaseException:os.close(fd);raise


def _receipt(target, directory, name, value):
    # Held dirfd plus current-path identity; never overwrite/adopt existing files.
    parts=name.split('.')
    if len(parts)!=3 or len(parts[0])!=32 or any(c not in '0123456789abcdef' for c in parts[0]) or parts[1] not in {'intent','result'} or parts[2]!='json':raise ValueError('diagnostic_filename')
    st=target.lstat();held=os.fstat(directory)
    if not stat.S_ISDIR(st.st_mode) or (st.st_dev,st.st_ino)!=(held.st_dev,held.st_ino) or (st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode))!=(0,0,0o700):raise ValueError('diagnostic_anchor_changed')
    data=(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
    if len(data)>MAX_RECEIPT:raise ValueError('diagnostic_receipt_limit')
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
    with os.fdopen(fd,'wb') as out:
        os.fchmod(out.fileno(),0o600);st=os.fstat(out.fileno())
        if not stat.S_ISREG(st.st_mode) or (st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode),st.st_nlink)!=(0,0,0o600,1):raise ValueError('diagnostic_file_unsafe')
        out.write(data);out.flush();os.fsync(out.fileno())
    os.fsync(directory)


def _capture_backend(args, timeout=90):
    protocol=_protocol();stream=protocol.RecordStream();started=time.monotonic()
    process=None;selector=selectors.DefaultSelector();buffer=b'';total=0;generic=False;reason=None;code=None
    try:
        try:process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        except OSError:reason='launch_failed'
        if process is not None:
            selector.register(process.stdout,selectors.EVENT_READ,'stdout');selector.register(process.stderr,selectors.EVENT_READ,'stderr')
            while selector.get_map() and reason is None:
                remaining=timeout-(time.monotonic()-started)
                if remaining<=0:reason='deadline_exceeded';break
                for key,_ in selector.select(remaining):
                    chunk=os.read(key.fileobj.fileno(),4096)
                    if not chunk:selector.unregister(key.fileobj);continue
                    total+=len(chunk)
                    if total>MAX_CAPTURE:reason='output_limit';break
                    if key.data=='stdout':reason='unexpected_output';break
                    buffer+=chunk
                    while b'\n' in buffer:
                        line,buffer=buffer.split(b'\n',1)
                        if len(line)>protocol.MAX_RECORD:reason='record_limit';break
                        if line==GENERIC_BACKEND and not generic:generic=True;continue
                        prefix=protocol.DIAG_PREFIX.encode()
                        if not line.startswith(prefix):reason='unexpected_output';break
                        try:stream.append(line[len(prefix):])
                        except protocol.InvalidDiagnostics:reason='invalid_diagnostics';break
                    if reason is not None:break
                    if len(buffer)>protocol.MAX_RECORD:reason='record_limit';break
            if reason is not None and process.poll() is None:process.kill()
            try:code=process.wait(timeout=max(0.001,timeout-(time.monotonic()-started)) if reason is None else 10)
            except subprocess.TimeoutExpired:
                reason='deadline_exceeded';process.kill();code=process.wait(timeout=10)
            if reason is None and buffer:reason='truncated_diagnostics'
            if reason is None:
                if code==0 and stream.passed and not generic:reason='accepted'
                elif not stream.records:reason='launch_failed_before_first_diagnostic'
                elif stream.records[-1]['event']=='fail' and code!=0:reason='backend_stage_failed'
                else:reason='incomplete_or_inconsistent_diagnostics'
    except Exception:
        reason='capture_failed'
    finally:
        if process is not None:
            if process.poll() is None:process.kill();process.wait(timeout=10)
            if process.stdout is not None:process.stdout.close()
            if process.stderr is not None:process.stderr.close()
        selector.close()
    return {'reason':reason,'returncode':code,'records':stream.records,'producer_entered':bool(stream.records),'boundary':'inside_readiness' if stream.records else 'before_first_diagnostic','captured_bytes':min(total,MAX_CAPTURE+4096)}


def execute_backend(args, timeout=90):
    target=None;directory=None
    try:
        target,directory=_private_dir();invocation=secrets.token_hex(16)
        _receipt(target,directory,invocation+'.intent.json',{'schema':1,'invocation':invocation,'state':'intent'})
        outcome=_capture_backend(args,timeout)
        _receipt(target,directory,invocation+'.result.json',{'schema':1,'invocation':invocation,'state':'complete',**outcome})
        # Only records already accepted by the strict decoder are forwarded.
        for record in outcome['records']:
            print('DISPATCHARR_BACKEND_DIAG '+json.dumps(record,sort_keys=True,allow_nan=False,separators=(',',':')),file=sys.stderr,flush=True)
        if outcome['reason']!='accepted':
            print('Backend diagnostic evidence: '+outcome['reason']+'; backend not accepted.',file=sys.stderr,flush=True)
            raise ValueError('scoped_command_failed')
    except Exception:
        print('Backend diagnostic evidence gap or failure; no automatic retry.',file=sys.stderr,flush=True)
        raise ValueError('scoped_command_failed') from None
    finally:
        if directory is not None:os.close(directory)


def inside(script, *args, environment=False):
    command = ['docker','exec','--user','1000:1000','dispatcharr']
    if environment:
        command += ['sh','-c','. /etc/profile.d/dispatcharr.sh; export PYTHONDONTWRITEBYTECODE=1; exec python -B /opt/permanent/backend.py']
    else: command += ['python','-B','/opt/permanent/'+script, *args]
    if environment: execute_backend(command, 90)
    else: execute(command, 90)


def prepare():
    # systemd created the root-private parent; never chown a symlink or arbitrary tree.
    parent = Path('/run/dispatcharr-permanent')
    if parent.is_symlink() or parent.stat().st_uid != 0: raise ValueError('unsafe_runtime_parent')
    child = parent / 'relay'
    if child.is_symlink(): raise ValueError('unsafe_runtime')
    child.mkdir(mode=0o700, exist_ok=True)
    os.chmod(child, 0o700); os.chown(child, 1000, 1000)
    import verify
    snapshot=verify.snapshot();verify.workload(snapshot,False)
    trusted().remember_owner(snapshot['containers']['iptv-vpn'],snapshot['network'],ROOT/'private/egress-policy.json')


def start():
    execute(COMPOSE + UP + ['iptv-vpn'])
    trusted().grant(ROOT/'private/egress-policy.json')
    execute(COMPOSE + UP + ['--no-deps','dispatcharr','relay'])
    inside('backend.py', environment=True)
    inside('register.py','--config','/run/credentials/registration.json')
    # The relay's existing state writer generates exports on binding, then hourly.
    for _ in range(8):
        try:
            inside('verify_binding.py')
            break
        except ValueError: time.sleep(1)
    else: raise ValueError('registration_or_exports_unready')
    execute(COMPOSE + UP + ['--no-deps','gateway'])


def rollback_integration():
    execute(COMPOSE + ['stop','--timeout','60','gateway','relay'],140)
    inside('register.py','--config','/run/credentials/registration.json','--rollback-owned')


def stop():
    errors=[]
    try:trusted().revoke(False)
    except Exception:errors.append('withdrawal_failed')
    try:execute(COMPOSE + ['stop','--timeout','60','gateway','relay','dispatcharr','iptv-vpn'], 210)
    except Exception:errors.append('scoped_stop_failed')
    try:
        execute(['/usr/bin/python3','-B',str(ROOT/'guard.py'),'assert-revoked'],10)
    except Exception:errors.append('withdrawal_not_verified')
    if errors:raise ValueError('scoped_cleanup_incomplete')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action',choices=['prepare','start','stop','rollback-integration']); a=p.parse_args()
    try: {'prepare':prepare,'start':start,'stop':stop,'rollback-integration':rollback_integration}[a.action]()
    except Exception: raise SystemExit('Managed IPTV action failed; details withheld. No automatic retry.')
