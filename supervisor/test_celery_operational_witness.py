"""Synthetic witness checks; no namespace changes, privileges, or network."""
import json
import os
from pathlib import Path
import tempfile
import unittest

import celery_operational_witness as w


BOOT='969b9316-6f6d-4b74-8bfa-a69f5dfdf9dc'
BACKEND='b'*64
CG='/system.slice/docker-'+BACKEND+'.scope'
ADDR='0100007F:18EB'
OTHER='0100007F:BB00'
UID=12345
NOW=10**12


class OperationalWitness(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.proc = self.root/'proc'
        self.cg = self.root/'cgroups'
        self.cgroup_procs = self.cg/CG.lstrip('/')/'cgroup.procs'
        self.net = self.proc/'self/net'
        self.file(self.proc/'sys/kernel/random/boot_id',BOOT+'\n')
        self.file(self.proc/'self/ns/net','unused inode')
        self.file(self.proc/'1/status','NSpid:\t1\n')
        self.process(21,7,721,['/sbin/init'])
        self.process(22,21,722,['redis-server 127.0.0.1:6379'])
        self.process(23,21,723,['/usr/bin/dash'])
        self.process(24,23,724,self.worker('default'))
        self.process(25,23,725,self.worker('dvr'))
        self.process(26,24,726,self.worker('default'))
        self.file(self.cgroup_procs,'21\n22\n23\n24\n25\n26\n')
        self.rows = [
            self.tcp(ADDR,'00000000:0000','0A',UID,501),
            self.tcp(ADDR,OTHER,'01',UID,601), self.tcp(OTHER,ADDR,'01',UID,602),
            self.tcp(ADDR,'0100007F:BB01','01',UID,603),
            self.tcp('0100007F:BB01',ADDR,'01',UID,604),
        ]
        self.endpoint()
        self.enroll = self.root/'enroll.json'
        self.healthy = self.root/'health.json'
        self.p = dict(version=w.VERSION,boot=BOOT,backend_id=BACKEND,backend_pid=21,
                      backend_ticks=721,backend_start_ns=NOW-1000,
                      net_inode=(self.proc/'self/ns/net').stat().st_ino,hostname='fixture',
                      worker_uid=UID,worker_command='/usr/bin/python3',
                      workers={'default@fixture':[24,724],'dvr@fixture':[25,725]},
                      broker=[22,722],broker_uid=UID,scope=w.SCOPE.copy())
        self.snapshot = dict(boot=BOOT,sampled_ns=NOW-10,
            backend=dict(Name='/dispatcharr',Id=BACKEND,Status='running',Running=True,
                Pid=21,StartedNs=NOW-1000,Health='healthy',HealthEndNs=NOW-20,
                HealthExitCode=0))

    @staticmethod
    def file(path, text):
        path.parent.mkdir(parents=True,exist_ok=True)
        if isinstance(text,bytes):
            path.write_bytes(text)
        else:
            path.write_text(text)
        return path

    @staticmethod
    def worker(role):
        q = {'default':'celery','dvr':'dvr'}[role]
        return ['/usr/bin/python3','worker.py','-A','dispatcharr','worker',
                '-n',role+'@%h','--queues='+q]

    def process(self,pid,ppid,ticks,args):
        p = self.proc/str(pid)
        self.file(p/'stat', f'{pid} (proc (fixture)) S {ppid} '+'0 '*17+str(ticks)+'\n')
        self.file(p/'cgroup','0::'+CG+'\n')
        self.file(p/'status','Uid:\t'+'\t'.join([str(UID)]*4)+f'\nNSpid:\t{pid}\t{pid-20}\n')
        self.file(p/'cmdline',('\0'.join(args)+'\0').encode())

    @staticmethod
    def tcp(local,remote,state,uid,ino):
        return f'  0: {local} {remote} {state} 0 0 0 {uid} 0 {ino}\n'

    def endpoint(self,v4=None,v6=None):
        head = '  sl  local_address rem_address   st\n'
        self.file(self.net/'tcp',head+''.join(self.rows if v4 is None else v4))
        self.file(self.net/'tcp6',head+''.join([] if v6 is None else v6))

    def snapshot_files(self):
        for path, value in ((self.enroll,self.p),(self.healthy,self.snapshot)):
            self.file(path,json.dumps(value))
            path.chmod(0o600)

    def inspect(self, now=NOW):
        self.snapshot_files()
        return w.inspect(self.enroll,self.healthy,self.proc,self.cg,os.getuid(),lambda: now)

    def test_same_uid_split_process_tree_without_foreign_proc_links(self):
        found=self.inspect()
        self.assertEqual(found['workers'], self.p['workers'])
        self.assertEqual(found['endpoint'],w.ENDPOINT)
        self.assertEqual(found['net_inode'],self.p['net_inode'])
        self.assertEqual(found['backend'],self.snapshot['backend'])
        self.assertFalse((self.proc/'24/ns').exists())
        self.assertFalse((self.proc/'22/fd').exists())

    def test_host_proc_view_and_unique_container_pids_are_mandatory(self):
        path=self.proc/'25/status'
        original=path.read_text()
        path.write_text(original.replace('25\t5','25\t4'))
        with self.assertRaises(ValueError):
            self.inspect()
        path.write_text(original.replace('25\t5','25'))
        with self.assertRaises(ValueError):
            self.inspect()

    def test_duplicate_master_and_exact_start_are_mandatory(self):
        self.process(27,23,727,self.worker('default'))
        self.cgroup_procs.write_text(self.cgroup_procs.read_text()+'27\n')
        with self.assertRaises(ValueError):
            self.inspect()
        self.cgroup_procs.write_text('21\n22\n23\n24\n25\n26\n')
        self.process(24,23,999,self.worker('default'))
        with self.assertRaises(ValueError):
            self.inspect()

    def test_stale_health_wrong_boot_or_port_is_unavailable(self):
        with self.assertRaises(ValueError):
            self.inspect(now=NOW+w.SOURCE_AGE_NS)
        self.p['boot']='969b9316-6f6d-4b74-8bfa-a69f5dfdf9dd'
        with self.assertRaises(ValueError):
            self.inspect()
        self.p['boot']=BOOT
        self.process(22,21,722,['redis-server 127.0.0.1:6380'])
        with self.assertRaises(ValueError):
            self.inspect()

    def test_namespace_listener_and_live_peer_changes_are_unavailable(self):
        self.p['net_inode']+=1
        with self.assertRaises(ValueError):
            self.inspect()
        self.p['net_inode']-=1
        for wrong in (self.rows[1:], self.rows[:-1],
                      self.rows+[self.tcp('00000000:18EB','00000000:0000','0A',UID,9914)],
                      self.rows[:2]+[self.tcp(OTHER,ADDR,'01',UID+1,602)]+self.rows[3:]):
            with self.subTest(wrong=wrong):
                self.endpoint(v4=wrong)
                with self.assertRaises(ValueError):
                    self.inspect()
        self.endpoint(v6=[self.tcp('0'*32+':18EB','0'*32+':0000','0A',UID,169)])
        with self.assertRaises(ValueError):
            self.inspect()

    def test_role_queue_and_broker_incarnation_must_not_drift(self):
        self.process(25,23,725,self.worker('dvr')[:-1]+['--queues=celery'])
        with self.assertRaises(ValueError):
            self.inspect()
        self.process(25,23,725,self.worker('dvr'))
        self.process(22,21,999,['redis-server 127.0.0.1:6379'])
        with self.assertRaises(ValueError):
            self.inspect()

    def test_enrollment_disallows_ambiguous_scope_and_duplicate_pid(self):
        self.p['scope']['database']=1
        with self.assertRaises(ValueError):
            self.inspect()
        self.p['scope']['database']=0
        self.p['workers']['dvr@fixture']=[24,725]
        with self.assertRaises(ValueError):
            self.inspect()


if __name__=='__main__':
    unittest.main()
