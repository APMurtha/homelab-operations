"""Bounded diagnostic only: UID-1000 reads, no Django app or provider traffic."""
import json
import os
from pathlib import Path

root=Path('/test-state')
private=root/'private-policy';private.mkdir(mode=0o700)
(private/'policy.json').write_text('{}');(private/'policy.json').chmod(0o600)
public=root/'public-status';public.mkdir(mode=0o755)
(public/'marker').write_text('SYNTHETIC_POSIX_FIXTURE_NOT_A_GRANT');(public/'marker').chmod(0o644)
r,w=os.pipe();pid=os.fork()
if pid==0:
    os.close(r);os.setgroups([]);os.setgid(1000);os.setuid(1000)
    def readable(path):
        try:
            with open(path,'rb') as stream:stream.read(1)
            return True
        except PermissionError:return False
    import django,celery,ssl
    result={'uid':os.geteuid(),'gid':os.getegid(),'app_api_readable':readable('/app/apps/api/__init__.py'),'core_policy_module_readable':readable('/app/core/provider_security.py'),'root_private_policy_readable':readable(private/'policy.json'),'root_public_marker_readable':readable(public/'marker'),'python':__import__('sys').version.split()[0],'django':django.get_version(),'celery':celery.__version__,'openssl':ssl.OPENSSL_VERSION}
    os.write(w,json.dumps(result).encode());os.close(w);os._exit(0)
os.close(w);data=os.read(r,8192);os.close(r);_,status=os.waitpid(pid,0)
if status:raise SystemExit('diagnostic_child_failed')
print(data.decode())
