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


def inside(script, *args, environment=False):
    command = ['docker','exec','--user','1000:1000','dispatcharr']
    if environment:
        command += ['sh','-c','. /etc/profile.d/dispatcharr.sh; export PYTHONDONTWRITEBYTECODE=1; exec python -B /opt/permanent/backend.py']
    else: command += ['python','-B','/opt/permanent/'+script, *args]
    execute(command, 90)


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
