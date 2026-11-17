"""ISOLATED DESIGN MODEL ONLY. Not a guard, installer or production helper.

Caller supplies a temporary namespace fixture. Kernel/owner verification is a
synthetic input; this model never executes nft, Docker, systemd or network I/O.
"""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile

GUARD_FIELDS = {'schema', 'boot_id', 'generation', 'policy_sha256'}
GRANT_FIELDS = GUARD_FIELDS | {'netns_dev', 'netns_ino'}


def netns():
    st = Path('/proc/self/ns/net').stat()
    return st.st_dev, st.st_ino


class Publisher:
    def __init__(self, private, public, boot_id):
        if os.environ.get('TRUSTED_GUARD_DESIGN_NS') != '1' or os.geteuid() != 0:
            raise RuntimeError('isolated_namespace_fixture_required')
        self.private, self.public, self.boot_id = Path(private), Path(public), boot_id

    @contextlib.contextmanager
    def locked(self):
        fd = os.open(self.private/'writer.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def revoke(self):
        # Attempt every withdrawal even if one fails; failures never mean success.
        errors = []
        for path in (self.public/'guard.json', self.public/'grant.json', self.private/'ready'):
            try: path.unlink(missing_ok=True)
            except OSError as exc: errors.append(exc)
        if errors: raise OSError('revocation_failed')

    def atomic(self, name, value, hook=lambda _: None):
        fd, temporary = tempfile.mkstemp(dir=self.private, prefix='.uncommitted-')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream); stream.flush(); os.fchmod(stream.fileno(),0o644);os.fsync(stream.fileno())
            hook('status-temporary')
            os.replace(temporary,self.public/name)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def apply(self, digest, validate=lambda: None, kernel_verified=True, hook=lambda _: None):
        with self.locked():
            hook('before-revoke')
            self.revoke()
            hook('after-revoke')
            validate()
            if not kernel_verified: raise ValueError('kernel_verification_failed')
            record = {'schema':1,'boot_id':self.boot_id,'generation':secrets.token_hex(32),
                      'policy_sha256':digest}
            (self.private/'ready').write_text(digest+'\n')
            (self.private/'ready').chmod(0o644)
            hook('private-written')
            self.atomic('guard.json',record,hook)
            hook('guard-published')
            return record

    def grant(self, digest, namespace, owner_verified=True, hook=lambda _: None):
        with self.locked():
            guard = json.loads((self.public/'guard.json').read_text())
            if not owner_verified or guard['policy_sha256']!=digest or guard['boot_id']!=self.boot_id:
                raise ValueError('owner_or_policy_not_verified')
            record = dict(guard,netns_dev=namespace[0],netns_ino=namespace[1])
            self.atomic('grant.json',record,hook)
            hook('grant-published')
            return record


class Reader:
    def __init__(self, public, boot_id, digest):
        self.public, self.boot_id, self.digest = Path(public), boot_id, digest
        self.expected = self.read('grant.json', GRANT_FIELDS)
        self.check()

    def read(self, name, fields):
        # Current-path lookup for every check; no cached descriptor to a status file.
        directory = os.open(self.public,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            st=os.fstat(directory)
            if st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o755 or st.st_nlink==0:
                raise ValueError('unsafe_or_retired_anchor')
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
            with os.fdopen(fd,'rb') as stream:
                st=os.fstat(stream.fileno())
                if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o644 or st.st_nlink!=1:
                    raise ValueError('unsafe_assertion')
                raw=stream.read(2049)
            if len(raw)>2048: raise ValueError('oversized_assertion')
            value=json.loads(raw)
            if set(value)!=fields or value.get('schema')!=1: raise ValueError('invalid_fields')
            if len(value.get('generation',''))!=64 or any(c not in '0123456789abcdef' for c in value['generation']):
                raise ValueError('invalid_generation')
            return value
        finally: os.close(directory)

    def check(self):
        first=self.read('guard.json',GUARD_FIELDS)
        grant=self.read('grant.json',GRANT_FIELDS)
        second=self.read('guard.json',GUARD_FIELDS)
        if first!=second or grant!=self.expected: raise ValueError('generation_changed')
        if any(grant[k]!=first[k] for k in GUARD_FIELDS): raise ValueError('grant_generation_mismatch')
        if first['boot_id']!=self.boot_id or first['policy_sha256']!=self.digest: raise ValueError('wrong_boot_or_policy')
        if (grant['netns_dev'],grant['netns_ino'])!=netns(): raise ValueError('wrong_namespace')
        return first['generation']
