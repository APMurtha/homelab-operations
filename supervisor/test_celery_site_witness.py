"""Synthetic kernel metadata fixtures: no services, sockets, or production access."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import celery_site_witness as w

BOOT = '8f20484f-6b92-4ff6-a3d9-a76a86525838'
CID = 'a'*64
CGROUP = '/system.slice/docker-'+CID+'.scope'
PYTHON = '/usr/local/bin/python3.13'
TCP = '  0: 0100007F:C001 0100007F:18EB 01 00000000:00000000 00:00000000 00000000 1000 0 400\n'


class SiteWitness(unittest.TestCase):
    now = 100_000_000_000

    def setUp(self):
        td = tempfile.TemporaryDirectory(prefix='sew-')
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.proc = self.root/'proc'
        self.cg = self.root/'cg'
        self.procs = self.cg/CGROUP.lstrip('/')/'cgroup.procs'
        self.procs.parent.mkdir(parents=True)
        self.procs.write_text('11\n12\n13\n14\n15\n16\n')
        self.enroll = self.root/'enroll'
        self.health = self.root/'health'
        self.boot = self.proc/'sys/kernel/random/boot_id'
        self.boot.parent.mkdir(parents=True)
        self.boot.write_text(BOOT+'\n')
        self.ns={}
        for n in ('net','uts','mnt','pid'):
            path=self.root/n
            path.touch()
            self.ns[n]=path
        self.enrollment = {
            'version':'celery-site-witness-v1', 'boot':BOOT, 'backend_id':CID,
            'backend_pid':11, 'backend_ticks':10001, 'backend_start_ns':self.now-20_000_000_000,
            'worker_uid':1000, 'worker_executable':PYTHON,'hostname':'fixture',
            'scope':dict(w.SCOPE),
        } | {name+'_inode':x.stat().st_ino for name,x in self.ns.items()}
        self.row = {'boot':BOOT,'sampled_ns':self.now-1,'backend':{
            'Name':'/dispatcharr','Id':CID,'Status':'running','Running':True,'Pid':11,
            'StartedNs':self.enrollment['backend_start_ns'],'Health':'healthy',
            'HealthEndNs':self.now-2,'HealthExitCode':0}}
        self.write(self.enroll,self.enrollment)
        self.write(self.health,self.row)
        self.make_process(11,1)
        self.make_process(12,11,exe='/usr/bin/dash')
        self.make_process(13,11,exe='/usr/bin/dash')
        self.make_process(14,12,'default')
        self.make_process(15,13,'dvr')
        self.make_process(16,14,'default')  # prefork child, not a distinct master

    def write(self,p,obj):
        p.write_text(json.dumps(obj))
        p.chmod(0o600)

    def make_process(self,pid,parent,role=None,exe=None):
        p=self.proc/str(pid)
        (p/'ns').mkdir(parents=True,exist_ok=True)
        (p/'fd').mkdir(exist_ok=True)
        (p/'net').mkdir(exist_ok=True)
        for name,target in self.ns.items():
            if not (p/'ns'/name).exists():
                os.link(target,p/'ns'/name)
        argv=[b'process']
        if role:
            argv=[b'celery',b'-A',b'dispatcharr',b'worker',b'-Q',w.WORKERS[role].encode(),
                  b'-n',(role+'@%h').encode()]
            (p/'fd'/'4').symlink_to('socket:[400]')
        (p/'exe').symlink_to(exe or PYTHON)
        (p/'cmdline').write_bytes(b'\0'.join(argv)+b'\0')
        (p/'cgroup').write_text('0::'+CGROUP+'\n')
        (p/'stat').write_text(f'{pid} (pytest fixture) S {parent} '+'0 '*17+f'{10001 if pid==11 else 20000+pid}\n')
        (p/'status').write_text('Uid:\t1000\t1000\t1000\t1000\n')
        (p/'net'/'tcp').write_text('header\n'+TCP)
        return p

    def start(self):
        return w.inspect(self.enroll,self.health,self.proc,self.cg,os.getuid(),lambda:self.now)

    def test_exact_frame_and_prefork_not_second_master(self):
        frame=self.start()
        self.assertEqual(frame['workers'],{'default@fixture':[14,20014],'dvr@fixture':[15,20015]})
        self.assertEqual(frame['scope_sha256'],hashlib.sha256(
                         json.dumps(w.SCOPE,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        self.assertEqual(frame['backend'],self.row['backend'])
        self.assertNotIn('socket',json.dumps(frame))

    def test_signed_witness_requires_distinct_exact_worker_uids(self):
        default_uid = self.enrollment.pop('worker_uid')
        dvr_uid = default_uid+1
        self.enrollment.update(version='celery-site-witness-signed-v2',
                               worker_uids={'default':default_uid,'dvr':dvr_uid})
        # DVR launch shell and actual worker must both match the enrolled UID.
        for pid in (13, 15):
            status = self.proc/str(pid)/'status'
            status.write_text('Uid:\t'+'\t'.join([str(dvr_uid)]*4)+'\n')
        self.write(self.enroll,self.enrollment)
        self.assertEqual(set(self.start()['workers']), {'default@fixture','dvr@fixture'})
        self.enrollment['worker_uids']['dvr']=default_uid
        self.write(self.enroll,self.enrollment)
        with self.assertRaises(ValueError):
            self.start()

    def test_rejects_second_master_and_wrong_worker_uid(self):
        self.make_process(17,12,'default')
        with self.procs.open('a') as out: out.write('17\n')
        with self.assertRaises(ValueError): self.start()
        self.procs.write_text('11\n12\n13\n14\n15\n16\n')
        (self.proc/'14/status').write_text('Uid:\t0\t0\t0\t0\n')
        with self.assertRaises(ValueError): self.start()

    def test_rejects_wrong_destination_port_state_or_unowned_socket(self):
        file=self.proc/'15/net/tcp'
        for raw in [TCP.replace('0100007F:18EB','0100007F:18EC'),
                    TCP.replace('0100007F:18EB','01000001:18EB'),
                    TCP.replace('18EB 01','18EB 0A'),TCP.replace('0 400','0 401')]:
            with self.subTest(raw=raw):
                file.write_text('header\n'+raw)
                with self.assertRaises(ValueError): self.start()

    def test_rejects_backend_restart_and_namespace_drift(self):
        file=self.proc/'11/stat'
        s=file.read_text()
        file.write_text(s.replace('10001','10002'))
        with self.assertRaises(ValueError): self.start()
        file.write_text(s)
        target=self.proc/'15/ns/net'
        target.unlink()
        target.touch()
        with self.assertRaises(ValueError): self.start()

    def test_rejects_role_queue_and_name_drift(self):
        file=self.proc/'15/cmdline'
        original=file.read_bytes()
        for changed in (original.replace(b'dvr@%h',b'dvr@foreign'),
                        original.replace(b'-Q\0dvr',b'-Q\0celery'),
                        original+b'-n\x00dvr@%h\x00'):
            file.write_bytes(changed)
            with self.assertRaises(ValueError): self.start()

    def test_stale_health_provenance_and_file_metadata(self):
        self.row['backend']['HealthEndNs']=self.now-45*10**9
        self.row['backend']['StartedNs']=1
        self.enrollment['backend_start_ns']=1
        self.write(self.enroll,self.enrollment)
        self.write(self.health,self.row)
        with self.assertRaises(ValueError): self.start()
        self.health.unlink()
        self.health.symlink_to(self.enroll)
        with self.assertRaises(OSError): self.start()
        self.enroll.chmod(0o640)
        with self.assertRaises(ValueError): self.start()

    def test_rejects_role_changes_before_frame_commit(self):
        actual=w.sockets
        def race(path):
            ok=actual(path)
            if path.name=='15':
                file=path/'cmdline'
                file.write_bytes(file.read_bytes().replace(b'dvr@%h',b'dvr@foreign'))
            return ok
        with patch.object(w,'sockets',race), self.assertRaises(ValueError):
            self.start()


if __name__=='__main__':
    unittest.main()
