"""Real synthetic TLS/HTTP in a loopback-only user network namespace, no containers."""
import json
import os
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.request import build_opener, ProxyHandler
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import hls_relay as relay
from telemetry import Telemetry
from fetch_runtime import Budget, DNS, FetchTimeout
from files import read_json, write_json
import health

SOURCE='https://'+relay.HOST+'/synthetic/live.m3u8'
PLAY=b'#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXT-X-MEDIA-SEQUENCE:1\n#EXTINF:6,\npart.ts\n'
TS=(bytes([0x47,0,0x10,0x10])+bytes(184))*3

class Upstream(BaseHTTPRequestHandler):
    status=200;body=PLAY;typ='application/vnd.apple.mpegurl';extra=[];hits=0;delay=0
    def log_message(self,*args):pass
    def do_GET(self):
        type(self).hits+=1
        if type(self).delay:time.sleep(type(self).delay)
        self.send_response(type(self).status);self.send_header('Content-Type',type(self).typ)
        for k,v in type(self).extra:self.send_header(k,v)
        self.send_header('Content-Length',str(len(type(self).body)));self.end_headers()
        try:self.wfile.write(type(self).body)
        except OSError:pass

@unittest.skipUnless(os.environ.get('PERMANENT_TEST_NS')=='1','requires isolated synthetic namespace')
class NetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names={x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','link']))}
        assert names=={'lo'}
        assert not any(r.get('dst')=='default' for r in json.loads(subprocess.check_output(['ip','-j','route'])))
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
            '-keyout',str(cls.root/'key'),'-out',str(cls.root/'cert'),'-subj','/CN='+relay.HOST,
            '-addext','subjectAltName=DNS:'+relay.HOST],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        # HTTPServer otherwise attempts reverse DNS for the synthetic public IP.
        socket.getfqdn=lambda name='':name or 'localhost'
        cls.up=ThreadingHTTPServer(('93.184.216.34',443),Upstream);cls.up.daemon_threads=True
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cls.root/'cert',cls.root/'key')
        cls.up.socket=ctx.wrap_socket(cls.up.socket,server_side=True)
        threading.Thread(target=cls.up.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):cls.up.shutdown();cls.up.server_close();cls.tmp.cleanup()
    def setUp(self):
        self.tmpcase=tempfile.TemporaryDirectory();self.ready=Path(self.tmpcase.name)/'ready';self.ready.write_text('ok')
        self.context=ssl.create_default_context(cafile=str(self.root/'cert'))
        self.r=self.make()
        Upstream.status=200;Upstream.body=PLAY;Upstream.typ='application/vnd.apple.mpegurl';Upstream.extra=[];Upstream.delay=0
    def make(self,context=None,resolver=None):
        return relay.Relay({'source':SOURCE,'ready_file':str(self.ready),'ready_hash':'ok'},
          context=context or self.context,resolver=resolver or (lambda *a:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))]))
    def tearDown(self):self.r.close();self.tmpcase.cleanup()
    def test_native_TLS_manifest_and_segment(self):
        output=self.r.fetch(SOURCE,True,validator=self.r.rewrite)
        path=next(x for x in output.decode().splitlines() if x.startswith('/'))
        Upstream.typ='video/mp2t';Upstream.body=TS
        typ,data=self.r.resource(path);self.assertEqual(data,TS);self.assertEqual(typ,'video/mp2t')
    def test_redirects_are_never_followed(self):
        for status in [301,302,303,307,308]:
            Upstream.status=status;Upstream.extra=[('Location','https://127.0.0.1/forbidden')]
            with self.subTest(status=status),self.assertRaises(relay.SecurityRejected):self.r.fetch(SOURCE,True)
    def test_DNS_rebinding_and_mixed_answers_rejected_before_connect(self):
        for ips in [['127.0.0.1'],['169.254.169.254'],['10.0.0.1'],['::1'],['93.184.216.34','192.168.1.1'],['224.0.0.1'],[]]:
            self.r.resolver=lambda *a,ips=ips:[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in ips]
            before=Upstream.hits
            with self.subTest(ips=ips),self.assertRaises(relay.FetchFailure):self.r.fetch(SOURCE,True)
            self.assertEqual(Upstream.hits,before)
    def test_certificate_validation_is_real(self):
        r=self.make(context=ssl.create_default_context())
        try:
            with self.assertRaises(ssl.SSLCertVerificationError):r.fetch(SOURCE,True)
        finally:r.close()
    def test_hostname_verification_is_real(self):
        wrong=ssl.create_default_context(cafile=str(self.root/'cert'))
        original=wrong.wrap_socket
        def wrap(*args,**kwargs):kwargs['server_hostname']='wrong.invalid';return original(*args,**kwargs)
        wrong.wrap_socket=wrap;r=self.make(context=wrong)
        try:
            with self.assertRaises(ssl.SSLCertVerificationError):r.fetch(SOURCE,True)
        finally:r.close()
    def test_encoding_size_and_framing_rejected(self):
        for extra in [[('Content-Encoding','gzip')],[('Content-Type','text/html')],[('Content-Length','1048577')],[('Transfer-Encoding','gzip')]]:
            Upstream.extra=extra
            with self.subTest(extra=extra),self.assertRaises(relay.SecurityRejected):self.r.fetch(SOURCE,True)
    def test_total_deadline_and_DNS_children_reaped(self):
        def slow(*args):time.sleep(2);return []
        r=self.make(resolver=slow);r.fetch_timeouts={'manifest':.1,'segment':.1}
        try:
            start=time.monotonic()
            with self.assertRaises(FetchTimeout):r.fetch(SOURCE,True)
            self.assertLess(time.monotonic()-start,1);self.assertFalse(r.dns.active)
        finally:r.close()
    def test_health_is_nonmedia_and_thread_limit(self):
        srv=relay.server(self.r,0);threading.Thread(target=srv.serve_forever,daemon=True).start()
        clients=[]
        try:
            url='http://127.0.0.1:'+str(srv.server_address[1])+'/healthz';before=Upstream.hits
            with build_opener(ProxyHandler({})).open(url) as response:self.assertTrue(json.load(response)['ok'])
            self.assertEqual(Upstream.hits,before)
            # Eight deliberately idle clients occupy bounded parser threads.
            for _ in range(8):clients.append(socket.create_connection(srv.server_address))
            end=time.monotonic()+1
            while srv.connections._value and time.monotonic()<end:time.sleep(.01)
            self.assertEqual(srv.connections._value,0)
            extra=socket.create_connection(srv.server_address);extra.settimeout(1)
            try:self.assertEqual(extra.recv(1),b'')
            finally:extra.close()
        finally:
            for client in clients:client.close()
            srv.shutdown();srv.server_close()
    def test_rotating_telemetry_bounded_over_many_writes(self):
        path=Path(self.tmpcase.name)/'events';t=Telemetry(str(path),max_bytes=1024)
        for i in range(100):
            t.emit('fetch','start',request_id=format(i,'x'));t.q.join()
        self.assertTrue(t.close());self.assertEqual(t.snapshot()['dropped'],0)
        self.assertLessEqual(path.stat().st_size,1024);self.assertLessEqual(Path(str(path)+'.1').stat().st_size,1024)
    def test_shutdown_cancels_active_exec_DNS(self):
        worker=Path(self.tmpcase.name)/'dns-worker.py';worker.write_text('import time;time.sleep(20)')
        r=self.make();r.resolver=None;r.dns=DNS(worker);errors=[]
        def fetch():
            try:r.fetch(SOURCE,True)
            except Exception as e:errors.append(e)
        thread=threading.Thread(target=fetch);thread.start()
        end=time.monotonic()+2
        while not r.dns.active and time.monotonic()<end:time.sleep(.01)
        self.assertTrue(r.dns.active);self.assertTrue(r.close());thread.join(2)
        self.assertFalse(thread.is_alive());self.assertFalse(r.dns.active)
        self.assertEqual(errors[0].category,'cancelled')

    def test_managed_process_startup_SIGTERM_and_stale_health(self):
        # Wrapper imports are real; config paths are injected by a private fixture runner.
        runtime=Path(self.tmpcase.name)/'runtime';runtime.mkdir();exports=Path(self.tmpcase.name)/'exports';exports.mkdir()
        runner=Path(self.tmpcase.name)/'runner.py'
        config={'source':SOURCE,'ready_file':str(self.ready),'ready_hash':'ok','manifest_deadline_seconds':12,'segment_deadline_seconds':12}
        runner.write_text('import sys\nsys.path.insert(0,'+repr(str(HERE))+')\nfrom relay_main import run\nfrom pathlib import Path\nraise SystemExit(run('+repr(config)+',Path('+repr(str(runtime))+'),Path('+repr(str(exports))+')))\n')
        proc=subprocess.Popen([sys.executable,'-B',str(runner)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            end=time.monotonic()+5
            while not (runtime/'stats.json').exists() and proc.poll() is None and time.monotonic()<end:time.sleep(.02)
            record=health.current(runtime);self.assertEqual(len(record['instance']),32)
            write_json(runtime/'binding.json',{'instance':record['instance'],'channel_uuid':str(__import__('uuid').uuid4())})
            end=time.monotonic()+4
            while not (runtime/'export-state.json').exists() and time.monotonic()<end:time.sleep(.02)
            self.assertTrue((exports/'current/guide.xml').exists())
            proc.send_signal(signal.SIGTERM);proc.wait(timeout=5);self.assertEqual(proc.returncode,0)
            self.assertTrue(read_json(runtime/'stats.json')['clean_shutdown'])
            with self.assertRaises((ValueError,FileNotFoundError)):health.current(runtime)
        finally:
            if proc.poll() is None:proc.kill();proc.wait()

if __name__=='__main__':unittest.main()
