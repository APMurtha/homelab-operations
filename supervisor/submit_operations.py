"""Owner-side submission. No supervisor challenge, callback, or retry loop."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from github import Denied, REPO, Unavailable, require, sha
from operations import parse_enrollment
from ops_protocol import decode
from single_submission import DOMAIN, PREFIX, Inbox, canonical, context, policy, verify


def submit(api, task, signer, receipt, nonce=None):
    api.anchor()
    task = api.parse_spec(canonical(task))
    issued = int(time.time())
    require(issued < task['expires'] <= issued+300 and api.base()==task['base'], 'expiry-or-base')
    grant = context(api.p) | dict(issued=issued,nonce=nonce or secrets.token_hex(32),
                                  task=task,digest=sha(canonical(task)))
    message = canonical(grant)
    signature = signer(message)
    verify(api.p['key'],message,signature)
    body = PREFIX + canonical(dict(grant=grant,signature=signature))
    # Persist the exact submission before the only write. An uncertain POST must
    # be reconciled by nonce/body; reusing this intent path never resubmits.
    with os.fdopen(os.open(receipt,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    parent = os.open(Path(receipt).parent, os.O_DIRECTORY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    require(time.time()<task['expires'], 'expiry')
    c = api.get(f'issues/{api.p["issue"]}/comments','POST',{'body':body})
    require(c['user']['id']==grant['owner_id'] and c['body']==body and
            c['issue_url']==f'https://api.github.com/repos/{REPO}/issues/{api.p["issue"]}', 'uncertain-post')
    return c['id']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('policy','task','known-hosts','identity','receipt'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--ttl-seconds',type=int,help='set expiry on a template that omits expires (1 to 300)')
    a = p.parse_args()
    task = decode(a.task.read_bytes())
    if a.ttl_seconds is not None:
        require(type(task) is dict and 'expires' not in task and 1 <= a.ttl_seconds <= 300, 'expiry')
        task['expires'] = int(time.time()) + a.ttl_seconds
    api = Inbox(parse_enrollment(a.known_hosts.read_bytes())[0],policy(decode(a.policy.read_bytes())))
    def sign(message):
        proc = subprocess.run(['/usr/bin/ssh-keygen','-Y','sign','-f',str(a.identity.resolve()),'-n',DOMAIN],
                              input=message.encode(),stdout=subprocess.PIPE,check=True)
        return proc.stdout.decode('ascii')
    print(submit(api,task,sign,a.receipt))


if __name__=='__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, Denied, Unavailable, subprocess.SubprocessError):
        sys.exit('Submission unconfirmed. Reconcile any saved intent on the enrolled issue before retrying.')
