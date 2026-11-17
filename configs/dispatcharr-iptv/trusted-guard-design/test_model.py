"""Permission and crash feasibility, not production lifecycle acceptance."""
import ctypes
import errno
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import model

BASE=Path(__file__).resolve().parents[1]
# Reuse the prior real-UID probe, preserving the complete 171-test baseline.
sys.path.insert(0,str(BASE/'guard-interface-review'))
from test_feasibility import unprivileged
DIGEST='a'*64
BOOT='11111111-1111-4111-8111-111111111111'

class Design(unittest.TestCase):
    def setUp(self):
        self.assertEqual(os.environ.get('TRUSTED_GUARD_DESIGN_NS'),'1')
        self.temp=tempfile.TemporaryDirectory(prefix='trusted-guard-design-');self.root=Path(self.temp.name)
        subprocess.run(['mount','-t','tmpfs','-o','size=8m,nosuid,nodev','tmpfs',str(self.root)],check=True)
        self.root.chmod(0o755)
        self.private=self.root/'private';self.private.mkdir(mode=0o700)
        self.public=self.root/'public';self.public.mkdir(mode=0o755)
        self.bound=self.root/'bound';self.bound.mkdir(mode=0o755)
        subprocess.run(['mount','--bind',str(self.public),str(self.bound)],check=True)
        subprocess.run(['mount','-o','remount,bind,ro,nosuid,nodev,noexec',str(self.bound)],check=True)
        self.publisher=model.Publisher(self.private,self.public,BOOT)
        self.publisher.apply(DIGEST);self.publisher.grant(DIGEST,model.netns())
        self.reader=model.Reader(self.bound,BOOT,DIGEST)
    def tearDown(self):
        subprocess.run(['umount',str(self.bound)],check=True)
        subprocess.run(['umount',str(self.root)],check=True)
        self.temp.cleanup()
    def read(self,reader=None):return unprivileged(lambda:(reader or self.reader).check())
    def assertClosed(self):self.assertFalse(self.read()['ok'])
    def crash(self,phase,grant=False):
        read,write=os.pipe();pid=os.fork()
        if pid==0:
            os.close(read)
            def hook(value):
                if value==phase:
                    os.write(write,b'!')
                    signal.pause()
            if grant:self.publisher.grant(DIGEST,model.netns(),hook=hook)
            else:self.publisher.apply(DIGEST,hook=hook)
            os._exit(90)
        os.close(write)
        # Bounded read so a broken crash fixture cannot block indefinitely.
        import select
        self.assertTrue(select.select([read],[],[],3)[0],'crash phase not reached')
        self.assertEqual(os.read(read,1),b'!');os.close(read)
        os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
    def test_valid_UID1000_only_minimal_status_and_namespace(self):
        self.assertTrue(self.read()['ok'])
        self.assertEqual(unprivileged(lambda:(self.private/'ready').read_text())['error'],'PermissionError')
        self.assertEqual(set(p.name for p in self.bound.iterdir()),{'guard.json','grant.json'})
        self.assertEqual((self.private.stat().st_uid,self.private.stat().st_mode & 0o777),(0,0o700))
    def test_directory_bind_observes_unlink_immediately_on_next_check(self):
        self.publisher.revoke();self.assertClosed()
        self.assertFalse((self.bound/'guard.json').exists())
    def test_unchanged_policy_gets_fresh_generation_and_requires_new_reader(self):
        old=self.reader.expected['generation'];new=self.publisher.apply(DIGEST)
        self.publisher.grant(DIGEST,model.netns())
        self.assertNotEqual(old,new['generation']);self.assertClosed()
        self.assertTrue(self.read(model.Reader(self.bound,BOOT,DIGEST))['ok'])
    def test_changed_policy_requires_explicit_new_expected_digest(self):
        self.publisher.apply('b'*64);self.publisher.grant('b'*64,model.netns());self.assertClosed()
        with self.assertRaises(ValueError):model.Reader(self.bound,BOOT,DIGEST)
        self.assertTrue(self.read(model.Reader(self.bound,BOOT,'b'*64))['ok'])
    def test_early_policy_failure_after_revoke_is_closed(self):
        def bad():raise ValueError('synthetic_bad_policy')
        with self.assertRaises(ValueError):self.publisher.apply(DIGEST,validate=bad)
        self.assertClosed()
    def test_early_wireguard_failure_after_revoke_is_closed(self):
        def bad():raise ValueError('synthetic_bad_wireguard')
        with self.assertRaises(ValueError):self.publisher.apply(DIGEST,validate=bad)
        self.assertClosed()
    def test_late_kernel_verification_failure_is_closed(self):
        with self.assertRaises(ValueError):self.publisher.apply(DIGEST,kernel_verified=False)
        self.assertClosed()
    def test_crash_before_revoke_exposes_manager_cleanup_window(self):
        self.crash('before-revoke')
        self.assertTrue(self.read()['ok'])  # Explicit limit, NOT immediate crash detection.
        self.publisher.revoke()             # Model of required manager failure hook.
        self.assertClosed()
    def test_crash_after_revoke_is_closed_before_manager_cleanup(self):
        self.crash('after-revoke');self.assertClosed()
    def test_crash_after_private_legacy_publish_keeps_public_closed(self):
        self.crash('private-written');self.assertClosed()
        self.assertTrue((self.private/'ready').exists())
        self.publisher.revoke();self.assertFalse((self.private/'ready').exists())
    def test_crash_with_uncommitted_temp_is_closed_and_private(self):
        self.crash('status-temporary');self.assertClosed()
        self.assertFalse((self.bound/'guard.json').exists())
        self.assertEqual(unprivileged(lambda:list(self.private.iterdir()))['error'],'PermissionError')
    def test_crash_after_guard_publish_without_grant_is_closed(self):
        self.crash('guard-published');self.assertClosed()
        self.assertFalse((self.bound/'grant.json').exists())
    def test_crash_after_grant_publish_needs_manager_cleanup(self):
        self.crash('grant-published',grant=True)
        self.assertTrue(self.read()['ok'])
        self.publisher.revoke();self.assertClosed()
    def test_stop_then_restart_never_implicitly_adopts_new_generation(self):
        self.publisher.revoke();self.assertClosed()
        self.publisher.apply(DIGEST);self.publisher.grant(DIGEST,model.netns());self.assertClosed()
    def test_startup_during_guard_replacement_has_no_valid_grant(self):
        self.publisher.apply(DIGEST)
        with self.assertRaises(OSError):model.Reader(self.bound,BOOT,DIGEST)
    def test_completed_check_cannot_recall_already_issued_decision(self):
        decision=self.read()['value'];self.publisher.revoke()
        self.assertEqual(decision,self.reader.expected['generation']);self.assertClosed()
    def test_old_boot_replay_is_rejected(self):
        with self.assertRaises(ValueError):model.Reader(self.bound,'22222222-2222-4222-8222-222222222222',DIGEST)
    def test_publication_failure_leaves_public_closed(self):
        with mock.patch.object(self.publisher,'atomic',side_effect=OSError('synthetic_publish_failure')):
            with self.assertRaises(OSError):self.publisher.apply(DIGEST)
        self.assertClosed()
    def test_one_failed_unlink_still_withdraws_other_required_assertion(self):
        real=Path.unlink
        def fail(path,*a,**kw):
            if path==self.public/'guard.json':raise PermissionError('synthetic_revoke_failure')
            return real(path,*a,**kw)
        with mock.patch.object(Path,'unlink',fail):
            with self.assertRaises(OSError):self.publisher.revoke()
        self.assertClosed()
    def test_total_revoke_failure_is_not_falsely_reported_closed(self):
        with mock.patch.object(Path,'unlink',side_effect=PermissionError('synthetic_failure')):
            with self.assertRaises(OSError):self.publisher.revoke()
        self.assertTrue(self.read()['ok'])  # Must stop processes via manager; file-only guarantee impossible.
    def test_safe_anchor_replacement_revokes_old_bound_directory_first(self):
        self.publisher.revoke();self.public.rename(self.root/'retired');self.public.mkdir(mode=0o755)
        self.assertClosed()
    def test_unsafe_root_rename_is_outside_protocol_and_undetectable(self):
        self.public.rename(self.root/'retired');self.public.mkdir(mode=0o755)
        self.assertTrue(self.read()['ok'])  # Rejected maintenance sequence, not a claimed guarantee.
    def test_actual_read_only_mount_forbids_root_write(self):
        with self.assertRaises(OSError) as raised:(self.bound/'guard.json').write_text('tamper')
        self.assertEqual(raised.exception.errno,errno.EROFS)
    def test_invalid_symlink_writable_or_extra_fields_are_rejected(self):
        original=(self.public/'guard.json').read_text()
        for value in ('invalid',json.dumps(dict(json.loads(original),unexpected=True))):
            (self.public/'guard.json').write_text(value);self.assertClosed()
        (self.public/'guard.json').write_text(original);(self.public/'guard.json').chmod(0o666);self.assertClosed()
        (self.public/'guard.json').unlink();(self.public/'guard.json').symlink_to(self.private/'ready');self.assertClosed()
    def test_namespace_grant_does_not_allow_different_real_namespace(self):
        self.assertTrue(self.read()['ok'])
        pid=os.fork()
        if pid==0:
            if ctypes.CDLL(None,use_errno=True).unshare(0x40000000)!=0:os._exit(91)
            result=self.read();os._exit(0 if not result['ok'] else 92)
        _,status=os.waitpid(pid,0);self.assertEqual(status,0)
    def test_unverified_owner_cannot_receive_grant(self):
        self.publisher.apply(DIGEST)
        with self.assertRaises(ValueError):self.publisher.grant(DIGEST,model.netns(),owner_verified=False)
        self.assertClosed()
    def test_legacy_root_consumer_still_gets_policy_digest(self):
        self.assertEqual((self.private/'ready').read_text(),DIGEST+'\n')
    def test_writer_lock_serializes_reapplication(self):
        import fcntl
        with self.publisher.locked():
            def blocked():
                fd=os.open(self.private/'writer.lock',os.O_RDWR)
                try:
                    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    except BlockingIOError:return True
                    return False
                finally:os.close(fd)
            # Root child tests the private writer lock; no lock is exposed to relay.
            pid=os.fork()
            if pid==0:os._exit(0 if blocked() else 1)
            _,status=os.waitpid(pid,0);self.assertEqual(status,0)

if __name__=='__main__':unittest.main()
