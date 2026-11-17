"""Real TLS sockets, DNS packets and guard records in an unrouted user/net namespace.

The only authorization bypass is a test-only authorize() stub for loopback TLS.
Destination authorization itself is exercised separately against public/private
DNS fixtures. Production contains no such bypass.
"""
import contextlib
import http.server
import json
import os
from pathlib import Path
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).parent))
from test_hardening import s,t,dns,resource


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.server.requests.append(self.path)
        try:
            if self.path=='/slow-headers':time.sleep(0.4)
            if self.path=='/redirect':
                self.send_response(302);self.send_header('Location','https://foreign.invalid/secret');self.send_header('Content-Length','0');self.end_headers();return
            if self.path=='/oversized':
                self.send_response(200);self.send_header('Content-Length',str(20*1024*1024));self.end_headers();return
            self.send_response(200)
            if self.path=='/chunked':self.send_header('Transfer-Encoding','chunked')
            else:self.send_header('Content-Length','4' if self.path=='/bad-length' else '2')
            self.end_headers()
            if self.path=='/slow-body':time.sleep(0.4)
            if self.path=='/revoke':self.server.guard.unlink()
            if self.path=='/chunked':self.wfile.write(b'2\r\n[]\r\n0\r\n\r\n')
            else:self.wfile.write(b'[]')
            self.wfile.flush()
        except (OSError,ssl.SSLError):pass


class Network(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Runner is required; this check prevents accidentally opening host ports.
        if os.environ.get('NATIVE_ISOLATED_TEST')!='1':raise RuntimeError('isolated_runner_required')
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.cert=cls.root/'cert.pem';cls.key=cls.root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(cls.key),'-out',str(cls.cert),'-days','1','-subj','/CN=provider.example.invalid','-addext','subjectAltName=DNS:provider.example.invalid'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',443),Handler)
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cls.cert,cls.key)
        cls.server.socket=ctx.wrap_socket(cls.server.socket,server_side=True);cls.server.requests=[]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()
    def setUp(self):
        self.r,self.key=resource();self.directory=self.root/'status';self.directory.mkdir(exist_ok=True);self.directory.chmod(0o755)
        ns=Path('/proc/self/ns/net').stat();boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        self.guard={'schema':1,'boot_id':boot,'generation':'b'*64,'policy_sha256':'a'*64}
        self.grant={**self.guard,'netns_dev':ns.st_dev,'netns_ino':ns.st_ino}
        for name,obj in [('guard.json',self.guard),('grant.json',self.grant)]:
            path=self.directory/name;path.write_text(json.dumps(obj));path.chmod(0o644)
        self.server.guard=self.directory/'guard.json'
        self.policy={'operations':['discover','refresh','epg'],'policy_review_sha256':'a'*64}
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(s,'policy',return_value=self.policy));self.stack.enter_context(patch.object(s,'GUARD',str(self.directory)))
        self.stack.enter_context(patch.object(t.MetadataHTTPS,'authorize',side_effect=lambda _,target:(urlsplit(target),'127.0.0.1'),autospec=True))
        factory=ssl.create_default_context
        self.stack.enter_context(patch.object(s.ssl,'create_default_context',side_effect=lambda:factory(cafile=str(self.cert))))
        self.before=len(self.server.requests)
    def fetch(self,path='/ok',host='provider.example.invalid'):
        with s.job('refresh',self.r,True):return s.fetch('https://'+host+path)
    def test_real_TLS_hostname_certificate_and_response(self):self.assertEqual(self.fetch(),b'[]')
    def test_real_TLS_hostname_mismatch_refused_without_HTTP(self):
        with self.assertRaises(s.Denied):self.fetch(host='foreign.invalid')
        self.assertEqual(len(self.server.requests),self.before)
    def test_untrusted_certificate_refused(self):
        factory=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with patch.object(s.ssl,'create_default_context',return_value=factory),self.assertRaises(s.Denied):self.fetch()
    def test_redirect_is_not_followed_or_retried(self):
        with self.assertRaises(s.Denied):self.fetch('/redirect')
        self.assertEqual(self.server.requests[self.before:],['/redirect'])
    def test_declared_oversized_body_refused(self):
        with self.assertRaises(s.Denied):self.fetch('/oversized')
    def test_body_truncation_refused(self):
        with self.assertRaises(s.Denied):self.fetch('/bad-length')
    def test_chunked_transfer_is_compatible(self):self.assertEqual(self.fetch('/chunked'),b'[]')
    def test_absolute_deadline_includes_HTTP_headers(self):
        start=time.monotonic()
        with patch.object(s,'TOTAL',0.15),self.assertRaises(s.Denied):self.fetch('/slow-headers')
        self.assertLess(time.monotonic()-start,1)
    def test_idle_deadline_includes_body(self):
        with patch.object(s,'IDLE',0.1),self.assertRaises(s.Denied):self.fetch('/slow-body')
    def test_revocation_during_fetch_is_observed(self):
        with self.assertRaises(s.Denied):self.fetch('/revoke')
        self.assertEqual(self.server.requests[self.before:],['/revoke'])
    def test_real_wrong_namespace_grant_refuses_before_connect(self):
        self.grant['netns_ino']+=1;(self.directory/'grant.json').write_text(json.dumps(self.grant))
        with self.assertRaises(s.Denied):self.fetch()
        self.assertEqual(len(self.server.requests),self.before)
    def test_real_changed_generation_refuses_startup(self):
        self.grant['generation']='c'*64;(self.directory/'grant.json').write_text(json.dumps(self.grant))
        with self.assertRaises(s.Denied):self.fetch()
    def test_network_has_no_external_default_route(self):
        rows=subprocess.check_output(['ip','route','show','default'],text=True);self.assertEqual(rows,'')
    def test_actual_DNS_loopback_wire_exchange(self):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as server:
            server.bind(('127.0.0.1',53));server.settimeout(2)
            def respond():
                query,peer=server.recvfrom(4096)
                response=query[:2]+struct.pack('!HHHHH',0x8180,1,1,0,0)+query[12:]+b'\xc0\x0c'+struct.pack('!HHIH',1,1,60,4)+socket.inet_aton('93.184.216.34')
                server.sendto(response,peer)
            thread=threading.Thread(target=respond);thread.start()
            self.assertEqual(dns.resolve('provider.example.invalid'),{'93.184.216.34'});thread.join()

if __name__=='__main__':unittest.main(verbosity=2)
