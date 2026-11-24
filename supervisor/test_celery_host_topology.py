"""Offline synthetic host procfs tests. No namespace or network operations."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import celery_host_topology as top

BOOT='8f20484f-6b92-4ff6-a3d9-a76a86525838'
CG='/system.slice/docker-'+'a'*64+'.scope'


class HostTopology(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory(prefix='sctopo-')
        self.addCleanup(td.cleanup)
        r=self.root=Path(td.name)
        self.proc=r/'proc'
        self.cgroups=r/'cgroups'
        self.members=self.cgroups/CG.lstrip('/')/'cgroup.procs'
        self.members.parent.mkdir(parents=True)
        self.members.write_text('101\n102\n103\n104\n')
        boot=self.proc/'sys/kernel/random/boot_id'
        boot.parent.mkdir(parents=True)
        boot.write_text(BOOT+'\n')
        self.host=r/'host'
        self.pidns=r/'guest'
        self.net=r/'net'
        for p in (self.host,self.pidns,self.net):
            p.touch()
        for pid, nspid in ((1,None),(88,None),(101,1),(102,2),(103,3),(104,4)):
            self.proc_fixture(pid,nspid)
        (self.proc/'self').symlink_to('88')
        broker=self.proc/'102'
        exe=r/'redis-server'
        code=b'fixture broker immutable bytes'
        exe.write_bytes(code)
        (broker/'exe').symlink_to(exe)
        self.tcp=broker/'net/tcp'
        self.tcp.write_text('header\n'+self.row(6379,0,'0A',201)+self.row(6379,30001,'01',202)
            +self.row(6379,30002,'01',203)+self.row(30001,6379,'01',301)
            +self.row(30002,6379,'01',302))
        (broker/'net/tcp6').write_text('header\n')
        (broker/'net/dev').write_text('header\nheader\n lo: 0\n')
        for p, fds in ((102,(201,202,203)),(103,(301,)),(104,(302,))):
            for n, sock in enumerate(fds):
                (self.proc/str(p)/'fd'/str(n)).symlink_to(f'socket:[{sock}]')
        self.layout={'boot':BOOT,'host_pid_inode':self.host.stat().st_ino,
            'pid_inode':self.pidns.stat().st_ino,'net_inode':self.net.stat().st_ino,
            'guest_init':[101,1010],'broker':[102,1020],
            'workers':{'default@fixture':[103,1030],'dvr@fixture':[104,1040]},
            'guest_cgroup':CG,'broker_sha256':hashlib.sha256(code).hexdigest()}

    @staticmethod
    def row(a,b,s,i):
        return f'  0: 0100007F:{a:04X} 0100007F:{b:04X} {s} 0 0 0 1000 0 {i}\n'

    def proc_fixture(self,pid,nspid):
        p=self.proc/str(pid)
        (p/'ns').mkdir(parents=True)
        (p/'fd').mkdir()
        (p/'net').mkdir()
        (p/'status').write_text('NSpid:\t'+str(pid)+('' if nspid is None else '\t'+str(nspid))+'\n')
        (p/'stat').write_text(f'{pid} (fixture) S 1 '+'0 '*17+str(pid*10)+'\n')
        (p/'cgroup').write_text('0::'+CG+'\n')
        os.link(self.host if nspid is None else self.pidns,p/'ns/pid')
        os.link(self.net,p/'ns/net')

    def witness(self,allow=False):
        return top.topology(self.proc,self.layout,allow_self=allow,cgroups=self.cgroups)

    def test_two_levels_and_exact_kernel_peers(self):
        self.assertEqual(self.witness(), {'guest_init':(101,1),'broker':(102,2),
                         'default@fixture':(103,3),'dvr@fixture':(104,4)})

    def test_host_view_and_multiple_nested_levels_refusal(self):
        q=self.proc/'88/status'
        q.write_text('NSpid:\t88\t2\n')
        with self.assertRaises(ValueError): self.witness()
        q.write_text('NSpid:\t88\n')
        q=self.proc/'104/status'
        q.write_text('NSpid:\t104\t4\t1\n')
        with self.assertRaises(ValueError): self.witness()
        q.write_text('NSpid:\t104\t3\n')
        with self.assertRaises(ValueError): self.witness()

    def test_share_network_refused_but_identity_does_not_claim_authority(self):
        (self.proc/'102/net/dev').write_text('header\nheader\n lo: 0\n eth0: 0\n')
        self.assertIn('broker',top.host_mapping(self.proc,self.layout,cgroups=self.cgroups))
        with self.assertRaises(ValueError): self.witness()

    def test_signed_attestor_keeps_private_network_and_still_pins_target_namespace(self):
        self_net = self.proc/'88/ns/net'
        self_net.unlink()
        self_net.touch()
        (self.proc/'102/net/dev').write_text('header\nheader\n lo: 0\n eth0: 0\n')
        self.assertEqual(top.signed_endpoint(self.proc, self.layout, cgroups=self.cgroups)
                         ['default@fixture'], (103, 3))
        with self.assertRaises(ValueError):
            self.witness()
        member_net = self.proc/'104/ns/net'
        member_net.unlink()
        os.link(self_net, member_net)
        with self.assertRaises(ValueError):
            top.signed_endpoint(self.proc, self.layout, cgroups=self.cgroups)

    def test_foreign_peer_and_self_ownership(self):
        with self.tcp.open('a') as stream:
            stream.write(self.row(6379,30003,'01',204)+self.row(30003,6379,'01',303))
        (self.proc/'102/fd/3').symlink_to('socket:[204]')
        with self.assertRaises(ValueError): self.witness(True)
        (self.proc/'88/fd/1').symlink_to('socket:[303]')
        with self.assertRaises(ValueError): self.witness()
        self.assertIn('broker',self.witness(True))

    def test_unmatched_authenticated_connection_and_listener_refusal(self):
        previous=self.tcp.read_text()
        with self.tcp.open('a') as stream: stream.write(self.row(6379,30100,'01',210))
        (self.proc/'102/fd/4').symlink_to('socket:[210]')
        with self.assertRaises(ValueError): self.witness(True)
        (self.proc/'102/fd/4').unlink()
        self.tcp.write_text(previous.replace('0100007F:18EB 0100007F:0000 0A','00000000:18EB 0100007F:0000 0A'))
        with self.assertRaises(ValueError): self.witness()

    def test_restart_and_role_namespace_drift(self):
        p=self.proc/'103/stat'
        p.write_text(p.read_text().replace('1030','1031'))
        with self.assertRaises(ValueError): self.witness()
        p.write_text(p.read_text().replace('1031','1030'))
        (self.proc/'104/ns/net').unlink()
        (self.proc/'104/ns/net').touch()
        with self.assertRaises(ValueError): self.witness()

    def test_cgroup_replacement_mid_join(self):
        original=top.fds
        def race(folder):
            if folder.name=='104':
                self.members.write_text('101\n102\n103\n104\n123\n')
            return original(folder)
        with patch.object(top,'fds',race), self.assertRaises(ValueError):
            self.witness()

    def test_same_members_different_inode_refused(self):
        original=top.fds
        def race(folder):
            if folder.name=='104':
                temporary=self.members.with_name('replacement')
                temporary.write_bytes(self.members.read_bytes())
                temporary.replace(self.members)
            return original(folder)
        with patch.object(top,'fds',race), self.assertRaises(ValueError):
            self.witness()

    def test_peer_changes_mid_join(self):
        original=top.fds
        def race(folder):
            if folder.name=='104':
                self.tcp.write_text(self.tcp.read_text().replace('00:00000000', '01:00000000')
                                    .replace(' 0 302\n',' 0 409\n'))
            return original(folder)
        with patch.object(top,'fds',race), self.assertRaises(ValueError):
            self.witness()


if __name__=='__main__':
    unittest.main()
