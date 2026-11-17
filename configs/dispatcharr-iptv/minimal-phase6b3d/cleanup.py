"""One-shot original-three cleanup; always attempt revocation AND scoped stop.
Invoked only by the reviewed managed unit. No retries or firewall removal.
"""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path('/docker/dispatcharr-iptv')


def managed():
    if os.geteuid()!=0 or '0::/system.slice/dispatcharr-stack.service' not in Path('/proc/self/cgroup').read_text().splitlines():
        raise ValueError('managed_stack_required')


def cleanup():
    managed()
    errors=[]
    commands=[['/usr/bin/python3','-B',str(ROOT/'guard.py'),'revoke-public'],
              ['/usr/bin/docker','compose','--project-name','rivendell-iptv','--project-directory',str(ROOT),
               '-f',str(ROOT/'compose.proposed.yaml'),'-f',str(ROOT/'minimal-phase6b3d/compose.persistence.proposed.yaml'),
               'stop','--timeout','60','gateway','dispatcharr','iptv-vpn'],
              ['/usr/bin/python3','-B',str(ROOT/'guard.py'),'assert-revoked']]
    for command in commands:
        try:
            result=subprocess.run(command,capture_output=True,timeout=200 if 'compose' in command else 10)
            if result.returncode:errors.append('cleanup_command_failed')
        except (OSError,subprocess.TimeoutExpired):errors.append('cleanup_command_incomplete')
    if errors:raise ValueError('scoped_cleanup_incomplete')

if __name__=='__main__':
    try:cleanup()
    except Exception:sys.exit('Original IPTV cleanup incomplete; no automatic restart.')
