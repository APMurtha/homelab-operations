from contextlib import redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

import celery_operational_witness as witness
import celery_shadow_launcher as launcher
import celery_site_pidbox as pidbox
import render_celery_operational_enrollment as renderer


BOOT = '969b9316-6f6d-4b74-8bfa-a69f5dfdf9dc'
NOW = 2_000_000_000_000


class RenderEnrollment(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.base = Path(d.name)
        self.out = self.base/'output'
        self.snapshot = self.base/'snapshot.json'
        self.health = self.base/'health.json'
        self.boundary = self.base/'reviewed.txt'
        self.payload = self.base/'payload'
        self.payload.mkdir()
        self.secret = b'only synthetic reviewed facts: do not copy'
        self.boundary.write_bytes(self.secret)
        self.boundary.chmod(0o600)
        for f in renderer.PATHS:
            (self.payload/f).write_bytes(('synthetic '+f).encode())
        self.source = dict(version=witness.VERSION,boot=BOOT,backend_id='a'*64,backend_pid=22,
                           backend_ticks=7,backend_start_ns=NOW-9000,net_inode=23,hostname='fixture',
                           worker_uid=1234,worker_command='/usr/bin/python3',
                           workers={'default@fixture':[24,8],'dvr@fixture':[25,9]},
                           broker=[26,10],broker_uid=1234,scope=witness.SCOPE)
        self.frame=dict(boot=BOOT,sampled_ns=NOW-6,backend=dict(Name='/dispatcharr',Id='a'*64,
             Status='running',Running=True,Pid=22,StartedNs=NOW-9000,Health='healthy',
             HealthEndNs=NOW-7,HealthExitCode=0))
        self.snapshot.write_text(json.dumps(self.source))
        self.health.write_text(json.dumps(self.frame))

    def call(self, node='staging', now=NOW):
        argv=['--witness',str(self.snapshot),'--health',str(self.health),'--boundary',str(self.boundary),
              '--payload',str(self.payload),'--output',str(self.out),'--node',node,'--now-ns',str(now)]
        with redirect_stderr(io.StringIO()) as stream:
            rc = renderer.main(argv)
        if rc:
            self.assertEqual(stream.getvalue(),'enrollment rendering refused\n')
        return rc

    def test_output_valid_with_exact_launcher_bindings_and_private_permissions(self):
        self.assertEqual(self.call(),0)
        self.assertEqual(self.out.stat().st_mode&0o777,0o700)
        contents={f.name:f.read_bytes() for f in self.out.iterdir()}
        self.assertEqual(set(contents),{'witness-enrollment.json','pidbox-enrollment.json',
                                        'backend-witness.json','one-shot.json'})
        self.assertTrue(all(self.secret not in data for data in contents.values()))
        self.assertTrue(all(f.stat().st_mode&0o777==0o600 for f in self.out.iterdir()))
        p=launcher.permit(contents['one-shot.json'],BOOT,NOW,node='staging')
        b=pidbox.enrollment(contents['pidbox-enrollment.json'])
        self.assertEqual(p['boundary_sha256'],b['boundary_sha256'])
        self.assertEqual(p['boundary_sha256'],hashlib.sha256(self.secret).hexdigest())
        self.assertEqual(p['witness_enrollment_sha256'],pidbox.digest(contents['witness-enrollment.json']))
        self.assertEqual(p['pidbox_enrollment_sha256'],pidbox.digest(contents['pidbox-enrollment.json']))
        self.assertEqual(p['witness_sha256'],pidbox.digest((self.payload/'witness').read_bytes()))
        self.assertEqual(b['runtime_sha256'],pidbox.digest((self.payload/'pidbox-runtime.zip').read_bytes()))
        with self.assertRaises(ValueError):
            launcher.permit(contents['one-shot.json'],BOOT,NOW,node=launcher.HOST)

    def test_refuses_to_overwrite_directory_with_prior_nonce(self):
        self.assertEqual(self.call(node=launcher.HOST),0)
        previous=(self.out/'one-shot.json').read_bytes()
        self.assertEqual(self.call(node=launcher.HOST),1)
        self.assertEqual((self.out/'one-shot.json').read_bytes(),previous)

    def test_stale_health_unreviewed_boundary_or_symlink_writes_nothing(self):
        self.assertEqual(self.call(now=NOW+witness.SOURCE_AGE_NS),1)
        self.assertFalse(self.out.exists())
        self.boundary.write_bytes(b' \n\t')
        self.assertEqual(self.call(),1)
        self.assertFalse(self.out.exists())
        self.boundary.write_bytes(self.secret)
        self.boundary.chmod(0o644)
        self.assertEqual(self.call(),1)
        self.assertFalse(self.out.exists())
        self.boundary.chmod(0o600)
        guard=self.payload/'celery_broker_guard.py'
        guard.unlink()
        guard.symlink_to(self.boundary)
        self.assertEqual(self.call(),1)
        self.assertFalse(self.out.exists())

    def test_duplicate_json_fields_fail_before_output(self):
        self.health.write_text('{"boot":"x","boot":"y"}')
        self.assertEqual(self.call(),1)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
