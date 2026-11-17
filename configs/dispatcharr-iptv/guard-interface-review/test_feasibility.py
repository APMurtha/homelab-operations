"""Offline counterexamples, NOT a deployment interface or replacement guard.

Run only in a fresh mapped user/mount/network namespace. All paths are on a
private temporary tmpfs; nft is mocked, filesystem permissions/mounts are real.
"""
import errno
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

BASE = Path(__file__).resolve().parents[1]
CANDIDATE = BASE / 'permanent-streaming'
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location('accepted_guard', BASE / 'guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
sys.path.insert(0, str(CANDIDATE))
import hls_relay
import relay_main
# This module is imported lazily by server(). Preload before dropping UID:
# the private checkout ancestor is not the production read-only /opt mount.
import bounded_server
from health import current


def unprivileged(action):
    """Fork a real UID/GID 1000 reader, no supplementary groups/capabilities."""
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        try:
            os.setgroups([]); os.setgid(1000); os.setuid(1000)
            assert os.getuid() == os.getgid() == 1000 and os.getgroups() == []
            status = Path('/proc/self/status').read_text()
            assert 'CapEff:\t0000000000000000' in status
            value = {'ok': True, 'value': action()}
        except Exception as exc:
            value = {'ok': False, 'error': type(exc).__name__, 'reason': str(exc),
                     'errno': getattr(exc, 'errno', None)}
        os.write(write_fd, json.dumps(value).encode())
        os.close(write_fd); os._exit(0)
    os.close(write_fd)
    data = os.read(read_fd, 16384); os.close(read_fd)
    _, status = os.waitpid(pid, 0)
    assert status == 0
    return json.loads(data)


def candidate_check(path, digest):
    relay = hls_relay.Relay.__new__(hls_relay.Relay)
    relay.ready = Path(path); relay.ready_hash = digest
    relay.fatal = None; relay.expires = float('inf')
    relay.check()
    return True


def inode_aware_proposal(path, digest):
    """Evaluated and rejected idea; deliberately not integrated into candidate."""
    with Path(path).open() as stream:
        st = os.fstat(stream.fileno())
        if st.st_nlink != 1 or st.st_uid != 0 or st.st_mode & 0o022:
            raise ValueError('revoked_or_unsafe')
        if stream.read(66) != digest + '\n':
            raise ValueError('invalid')
    return True


class Feasibility(unittest.TestCase):
    def setUp(self):
        self.assertEqual(os.environ.get('DISPATCHARR_GUARD_FIXTURE_NS'), '1')
        self.assertEqual(os.getuid(), 0)
        self.temp = tempfile.TemporaryDirectory(prefix='guard-interface-offline-')
        self.root = Path(self.temp.name)
        subprocess.run(['mount', '-t', 'tmpfs', '-o', 'size=8m,nosuid,nodev',
                        'tmpfs', str(self.root)], check=True)
        self.root.chmod(0o755); self.mounts = []
        self.private = self.root/'guard'; self.private.mkdir(mode=0o700)
        self.marker = self.private/'ready'
        self.public = self.root/'interface'; self.public.mkdir(mode=0o755)
        self.policy = self.root/'policy.json'
        value = {'schema':1, 'bridge':'br-iptv-eg', 'subnet':'172.16.70.0/24',
                 'vpn_ip':'172.16.70.2', 'wg_endpoint_ipv4':'93.184.216.34',
                 'wg_endpoint_port':443, 'local_reply_cidrs':guard.load_policy.__globals__['LOCAL_REPLIES']}
        self.policy.write_text(json.dumps(value)); self.policy.chmod(0o600)
        self.digest = guard.load_policy(self.policy)[1]
        # Fixed all-zero synthetic keys, never used for network access.
        key = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
        self.wireguard = self.root/'wg0.conf'
        self.wireguard.write_text('[Interface]\nPrivateKey='+key+'\nAddress=10.7.0.2/32\n'
                                 '[Peer]\nPublicKey='+key+'\nPresharedKey='+key+
                                 '\nAllowedIPs=0.0.0.0/0\nEndpoint=93.184.216.34:443\n')
        self.wireguard.chmod(0o600)
        self.marker.write_text(self.digest+'\n'); self.marker.chmod(0o644)
        (self.private/'protected-policy').write_text('synthetic protected data')
        (self.private/'protected-policy').chmod(0o600)

    def tearDown(self):
        for path in reversed(self.mounts):
            subprocess.run(['umount', str(path)], check=True)
        subprocess.run(['umount', str(self.root)], check=True)
        self.temp.cleanup()

    def bind(self, source=None, name='ready'):
        target = self.public/name; target.touch()
        subprocess.run(['mount', '--bind', str(source or self.marker), str(target)], check=True)
        self.mounts.append(target)
        subprocess.run(['mount', '-o', 'remount,bind,ro,nosuid,nodev,noexec', str(target)], check=True)
        return target

    def apply(self, fail=None):
        real_path = Path
        def mapped(value):
            return self.private if str(value)=='/run/dispatcharr-guard' else real_path(value)
        def nft(args, **kwargs):
            self.assertEqual(args[0], 'nft')
            if fail and (('--check' in args) == (fail == 'check')) and args[1]!='list':
                raise subprocess.CalledProcessError(1, args)
            return subprocess.CompletedProcess(args, 1 if args[1]=='list' else 0)
        argv = ['guard.py','apply','--policy',str(self.policy),'--wireguard',str(self.wireguard)]
        with mock.patch.object(guard, 'Path', side_effect=mapped), mock.patch.object(sys, 'argv', argv), \
             mock.patch.object(guard.subprocess, 'run', side_effect=nft), mock.patch('builtins.print'):
            guard.main()

    def test_original_directory_permission_failure_is_reproduced(self):
        result = unprivileged(lambda: candidate_check(self.marker, self.digest))
        self.assertEqual(result['error'], 'SecurityRejected')
        self.assertEqual(result['reason'], 'guard_not_ready')
        st = self.private.stat(); self.assertEqual((st.st_uid, st.st_gid, st.st_mode & 0o777), (0,0,0o700))

    def test_single_file_bind_access_exposes_no_siblings(self):
        target = self.bind()
        self.assertTrue(unprivileged(lambda: candidate_check(target, self.digest))['ok'])
        self.assertEqual(unprivileged(lambda: (self.private/'protected-policy').read_text())['error'], 'PermissionError')
        self.assertEqual(unprivileged(lambda: (self.public/'protected-policy').read_text())['error'], 'FileNotFoundError')
        self.assertEqual(set(p.name for p in self.public.iterdir()), {'ready'})

    def test_actual_read_only_bind_refuses_even_file_owner_write(self):
        source = self.root/'writable-fixture'; source.write_text('synthetic')
        os.chown(source,1000,1000); source.chmod(0o600)
        target = self.bind(source)
        result = unprivileged(lambda: target.write_text('changed'))
        self.assertEqual(result['errno'], errno.EROFS)
        self.assertEqual(source.read_text(), 'synthetic')

    def test_missing_marker_fails_candidate_check(self):
        self.marker.unlink()
        self.assertEqual(unprivileged(lambda: candidate_check(self.marker,self.digest))['reason'], 'guard_not_ready')

    def test_invalid_contents_fail_on_accessible_interface(self):
        target = self.bind(); self.marker.write_text('invalid\n')
        self.assertEqual(unprivileged(lambda: candidate_check(target,self.digest))['reason'], 'guard_hash_mismatch')

    def test_plain_file_bind_survives_unlink_and_is_unsafe(self):
        target = self.bind(); self.marker.unlink()
        self.assertFalse(self.marker.exists())
        self.assertTrue(unprivileged(lambda: candidate_check(target,self.digest))['ok'])
        self.assertEqual(target.stat().st_nlink, 0)

    def test_inode_check_detects_unlinked_bound_generation(self):
        target = self.bind(); self.marker.unlink()
        self.assertEqual(unprivileged(lambda: inode_aware_proposal(target,self.digest))['error'], 'ValueError')

    def test_successful_reapply_changes_inode_but_not_policy_digest(self):
        target = self.bind(); old_inode = target.stat().st_ino
        self.apply()
        self.assertNotEqual(self.marker.stat().st_ino, old_inode)
        self.assertEqual(self.marker.read_text(), target.read_text())
        self.assertEqual(target.stat().st_nlink, 0)
        self.assertEqual(unprivileged(lambda: inode_aware_proposal(target,self.digest))['error'], 'ValueError')

    def test_late_guard_failure_revokes_original_not_copied_status(self):
        copied = self.public/'copied-ready'; shutil.copyfile(self.marker,copied); copied.chmod(0o644)
        with self.assertRaises(subprocess.CalledProcessError): self.apply(fail='check')
        self.assertFalse(self.marker.exists())
        self.assertTrue(unprivileged(lambda: inode_aware_proposal(copied,self.digest))['ok'])

    def test_early_policy_failure_is_unobservable_to_bound_inode(self):
        target = self.bind(); before = (target.stat().st_ino, target.stat().st_nlink, target.read_bytes())
        self.policy.write_text('{}')
        with self.assertRaises(ValueError): self.apply()
        self.assertEqual(before, (target.stat().st_ino, target.stat().st_nlink, target.read_bytes()))
        self.assertTrue(unprivileged(lambda: inode_aware_proposal(target,self.digest))['ok'])

    def test_early_WireGuard_mismatch_also_preserves_old_authorization(self):
        target = self.bind()
        self.wireguard.write_text(self.wireguard.read_text().replace('93.184.216.34:443','93.184.216.35:443'))
        with self.assertRaises(ValueError): self.apply()
        self.assertEqual(target.stat().st_nlink, 1)
        self.assertTrue(unprivileged(lambda: inode_aware_proposal(target,self.digest))['ok'])

    def test_copied_status_cannot_track_new_generation(self):
        copied = self.public/'copied-ready'; shutil.copyfile(self.marker,copied); copied.chmod(0o644)
        self.apply()
        self.assertTrue(unprivileged(lambda: inode_aware_proposal(copied,self.digest))['ok'])
        self.assertNotEqual(copied.stat().st_ino,self.marker.stat().st_ino)

    def test_relay_refuses_private_guard_before_endpoint_publication(self):
        runtime = self.root/'runtime'; runtime.mkdir(mode=0o700); os.chown(runtime,1000,1000)
        exports = self.root/'exports'; exports.mkdir(mode=0o750); os.chown(exports,1000,1000)
        config = {'source':'https://'+hls_relay.HOST+'/synthetic/live.m3u8',
                  'ready_file':str(self.marker),'ready_hash':self.digest,
                  'manifest_deadline_seconds':12,'segment_deadline_seconds':12}
        result = unprivileged(lambda: relay_main.run(config,runtime,exports))
        self.assertEqual((result['error'],result['reason']), ('SecurityRejected','guard_not_ready'))
        self.assertFalse((runtime/'endpoint.json').exists())

    def test_accessible_file_bind_allows_nonmedia_start_and_clean_stop_only(self):
        target = self.bind()
        runtime = self.root/'runtime'; runtime.mkdir(mode=0o700); os.chown(runtime,1000,1000)
        exports = self.root/'exports'; exports.mkdir(mode=0o750); os.chown(exports,1000,1000)
        config = {'source':'https://'+hls_relay.HOST+'/synthetic/live.m3u8',
                  'ready_file':str(target),'ready_hash':self.digest,
                  'manifest_deadline_seconds':12,'segment_deadline_seconds':12}
        pid = os.fork()
        if pid == 0:
            os.setgroups([]);os.setgid(1000);os.setuid(1000)
            try: result=relay_main.run(config,runtime,exports)
            except Exception:
                __import__("traceback").print_exc();result=99
            os._exit(result)
        try:
            deadline=time.monotonic()+5
            while True:
                try: current(runtime); break
                except (OSError,ValueError,KeyError):
                    if time.monotonic()>deadline: self.fail('synthetic relay unready')
                    time.sleep(.02)
            stats=json.loads((runtime/'stats.json').read_text())
            self.assertFalse(stats['fatal'])
            self.assertEqual(stats['counts'].get('requests',0),0)
        finally:
            os.kill(pid,signal.SIGTERM)
            deadline=time.monotonic()+6
            while True:
                ended,status=os.waitpid(pid,os.WNOHANG)
                if ended: break
                if time.monotonic()>deadline:
                    os.kill(pid,signal.SIGKILL);os.waitpid(pid,0);self.fail('fixture shutdown timeout')
                time.sleep(.02)
        self.assertEqual(status,0)
        self.assertFalse((runtime/'endpoint.json').exists())
        stats=json.loads((runtime/'stats.json').read_text())
        self.assertTrue(stats['stopped'] and stats['clean_shutdown'])

if __name__=='__main__':unittest.main()
