"""Real local socket audit fixtures; requires an isolated user/network namespace."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
import runtime_diagnostics as d

HERE=Path(__file__).resolve().parent

class LocalFixtures(unittest.TestCase):
    def setUp(self):
        if os.environ.get('DISPATCHARR_AUDIT_FIXTURE')!='1':raise RuntimeError('isolated_network_runner_required')
        self.assertEqual({name for _,name in socket.if_nameindex()},{'lo'})
        self.assertFalse(any(l.split()[1]=='00000000' for l in Path('/proc/net/route').read_text().splitlines()[1:]))
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    def child(self,body):
        prefix="import sys,socket\nsys.path.insert(0,sys.argv[1])\nimport runtime_diagnostics as d\nv=d.Diagnostics(sys.argv[2],'application',emit_fd=1,tests=d.TEST_IDS)\nv.complete('redis',{'redis_ping':True})\nv.begin('native_api',next(iter(d.TEST_IDS)))\nsys.addaudithook(v.audit)\n"
        return subprocess.run([sys.executable,'-B','-c',prefix+body,str(HERE),str(Path(self.tmp.name)/'evidence')],capture_output=True,text=True,timeout=10)
    def test_real_unix_path_connection_is_allowed(self):
        path=str(Path(self.tmp.name)/'synthetic.sock')
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
            server.bind(path);server.listen(1)
            result=self.child('s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\ns.connect('+repr(path)+')\ns.sendall(b"synthetic")\ns.close()\n')
            self.assertEqual(result.returncode,0)
            with server.accept()[0] as client:self.assertEqual(client.recv(32),b'synthetic')
        self.assertIsNone(d.recover_records(result.stdout)['last_refusal'])
    def test_real_IPv4_loopback_client_is_allowed(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1',0));server.listen(1);port=server.getsockname()[1]
            result=self.child('s=socket.create_connection(("127.0.0.1",'+str(port)+'),timeout=2)\ns.sendall(b"synthetic")\ns.close()\n')
            self.assertEqual(result.returncode,0)
            with server.accept()[0] as client:self.assertEqual(client.recv(32),b'synthetic')
        self.assertIsNone(d.recover_records(result.stdout)['last_refusal'])
    def test_genuine_public_connect_is_refused_before_OS_network_use(self):
        result=self.child('s=socket.socket()\ns.connect(("8.8.8.8",443))\nraise SystemExit("must never reach")\n')
        self.assertEqual(result.returncode,86);event=d.recover_records(result.stdout)['last_refusal']
        self.assertEqual(event['network']['destination_class'],'public');self.assertEqual(event['network']['family'],'AF_INET')
        self.assertEqual(event['reason'],'public_network_destination_denied')
        self.assertNotIn('8.8.8.8',result.stdout)
        snapshot=d.load_snapshot(Path(self.tmp.name)/'evidence',os.geteuid())
        self.assertEqual(snapshot['last_checkpoint']['phase'],'redis');self.assertEqual(snapshot['last_refusal']['kind'],'refusal')

if __name__=='__main__':unittest.main(verbosity=2)
