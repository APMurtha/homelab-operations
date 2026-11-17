"""Actual pinned-Caddy response tests. Run only in a loopback-only network NS.

unshare --user --map-root-user --net sh -c 'ip link set lo up; exec ...'
Normal unittest discovery skips these network tests; no host listeners are opened.
"""
import argparse
import gzip
import hashlib
import http.client
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse

ROOT=Path(__file__).resolve().parents[1]
BINARY=Path(os.environ.get('CADDY_TEST_BINARY','/tmp/dispatcharr-caddy-validation/caddy'))
CONFIG=Path(os.environ.get('CADDY_TEST_CONFIG',str(ROOT/'Caddyfile')))
BINARY_SHA='a563843e11cbce39c557bd429ebb787d56f49d51d9bbb3292cd9b36b37a60cdf'
SENTINEL='fixture-sensitive-token'
URL='https://provider.invalid/live?token='+SENTINEL
TS=b'G'+bytes(187)
CASES={};HITS=[];REQUEST_HEADERS={}
DANGEROUS=('Location','Refresh','Content-Location','Link','Alt-Svc','Report-To','Reporting-Endpoints','NEL','WWW-Authenticate','Proxy-Authenticate','Authorization','Proxy-Authorization','X-Provider-URL','X-Access-Token','X-Unknown-Debug','Content-Disposition','X-Accel-Redirect','X-Sendfile','X-Stream-URL','X-Auth-Token','Authentication-Info','Server','Via')

class Upstream(http.server.BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def do_HEAD(self):self.respond(True)
    def do_GET(self):self.respond(False)
    def respond(self,head):
        HITS.append(self.path)
        try:key=int(self.path.rsplit('/',1)[-1].rsplit('-',1)[-1],16)
        except ValueError:key=-1
        REQUEST_HEADERS[key]=dict(self.headers)
        c=CASES[key]
        if c.get('raw'):
            self.wfile.write(c['raw']);self.wfile.flush();self.close_connection=True;return
        self.send_response_only(c.get('status',200))
        for key,value in c.get('headers',[]):self.send_header(key,value)
        if c.get('chunked'):self.send_header('Transfer-Encoding','chunked')
        elif 'body' in c or head:self.send_header('Content-Length',str(len(c.get('body',TS))))
        if c.get('trailers') and c.get('announced'):self.send_header('Trailer',', '.join(k for k,v in c['trailers']))
        self.end_headers()
        if head:return
        if c.get('stream'):
            for _ in range(4):
                self.wfile.write(b'%X\r\n'%len(TS)+TS+b'\r\n');self.wfile.flush();time.sleep(0.35)
            self.wfile.write(b'0\r\n\r\n');self.wfile.flush();return
        body=c.get('body',TS)
        if c.get('chunked'):
            self.wfile.write(b'%X\r\n'%len(body)+body+b'\r\n0\r\n')
            for key,value in c.get('trailers',[]):self.wfile.write((key+': '+value+'\r\n').encode())
            self.wfile.write(b'\r\n')
        else:self.wfile.write(body)
        self.wfile.flush()

@unittest.skipUnless(os.environ.get('DISPATCHARR_GATEWAY_TEST_NS')=='1','requires isolated loopback-only namespace')
class GatewayResponses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if {i['ifname'] for i in json.loads(subprocess.check_output(['ip','-j','link'],text=True))}!={'lo'}:raise RuntimeError('Not an isolated loopback-only namespace')
        routes=json.loads(subprocess.check_output(['ip','-j','route','show','table','all'],text=True))
        if any(r.get('dst')=='default' or r.get('dev')!='lo' for r in routes):raise RuntimeError('External route present')
        if hashlib.sha256(BINARY.read_bytes()).hexdigest()!=BINARY_SHA:raise RuntimeError('Unreviewed Caddy binary')
        cls.tmp=tempfile.TemporaryDirectory(prefix='dispatcharr-gateway-regression-')
        cls.directory=Path(cls.tmp.name)
        cls.addClassCleanup(cls.cleanup)
        cls.upstream=http.server.ThreadingHTTPServer(('127.0.0.1',19191),Upstream)
        cls.upstream.daemon_threads=True
        cls.thread=threading.Thread(target=cls.upstream.serve_forever,daemon=True);cls.thread.start()
        text=CONFIG.read_text().replace('http://:9192','http://127.0.0.1:19192').replace('127.0.0.1:9191','127.0.0.1:19191')
        cls.cfg=cls.directory/'Caddyfile';cls.cfg.write_text(text)
        env={'PATH':'/usr/bin:/bin','HOME':str(cls.directory),'XDG_CONFIG_HOME':str(cls.directory),'XDG_DATA_HOME':str(cls.directory),'LANG':'C'}
        validation=subprocess.run([str(BINARY),'validate','--config',str(cls.cfg),'--adapter','caddyfile'],capture_output=True,text=True,env=env,timeout=15)
        if validation.returncode:raise RuntimeError(validation.stderr)
        cls.log=(cls.directory/'caddy.log').open('w')
        cls.process=subprocess.Popen([str(BINARY),'run','--config',str(cls.cfg),'--adapter','caddyfile'],stdout=cls.log,stderr=subprocess.STDOUT,env=env)
        for _ in range(100):
            try:
                s=socket.create_connection(('127.0.0.1',19192),timeout=.1);s.close();break
            except OSError:
                if cls.process.poll() is not None:raise RuntimeError('Caddy startup failed')
                time.sleep(.02)
        else:raise RuntimeError('Caddy listener not ready')
    @classmethod
    def cleanup(cls):
        process=getattr(cls,'process',None)
        if process is not None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        upstream=getattr(cls,'upstream',None)
        if upstream is not None:
            upstream.shutdown();upstream.server_close();cls.thread.join(timeout=2)
        log=getattr(cls,'log',None)
        if log is not None:log.close()
        cls.tmp.cleanup()
    def request(self,case,*,admin=False,method='GET',headers=None):
        key=len(CASES)+1;CASES[key]=case
        path=('/api/fixture/' if admin else '/proxy/ts/stream/00000000-0000-0000-0000-')+format(key,'012x')
        conn=http.client.HTTPConnection('127.0.0.1',19192,timeout=4)
        conn.request(method,path,headers=headers or {})
        response=conn.getresponse();body=response.read();pairs=response.getheaders();status=response.status;conn.close()
        return status,pairs,body
    def clean(self,pairs,*,media=True):
        lower=[(k.lower(),v) for k,v in pairs]
        for k,v in lower:
            self.assertNotIn(SENTINEL,v)
            self.assertNotIn('provider.invalid',urllib.parse.unquote(v).lower())
            self.assertNotIn(k,{n.lower() for n in DANGEROUS if n not in ('Server','Via')})
            if media:self.assertNotEqual(k,'set-cookie')
        self.assertIn('content-security-policy',dict(lower))
    def test_01_valid_mpegts_and_required_headers(self):
        status,headers,body=self.request({'headers':[('Content-Type','video/mp2t'),('Cache-Control','public,max-age=100')],'body':TS*3})
        self.assertEqual(status,200);self.assertEqual(body,TS*3);self.clean(headers)
        d=dict((k.lower(),v) for k,v in headers)
        self.assertEqual(d['content-type'],'video/mp2t');self.assertEqual(d['cache-control'],'no-store')
        self.assertEqual(d['content-length'],str(len(body)))
    def test_02_header_names_values_duplicates_and_encoding(self):
        for key in DANGEROUS+('Set-Cookie',):
            for value in (URL,urllib.parse.quote(URL,safe='')):
                with self.subTest(header=key,encoded=value!=URL):
                    status,headers,body=self.request({'headers':[('Content-Type','video/mp2t'),(key.swapcase(),value),(key.lower(),value+'duplicate')],'body':TS})
                    self.assertEqual(status,200);self.assertEqual(body,TS);self.clean(headers)
    def test_03_location_refresh_together_and_original_failure(self):
        for fields in ([('Location',URL)],[('Refresh','0;url='+URL)],[('Location',URL),('Refresh','0;url='+URL)]):
            status,headers,body=self.request({'headers':[('Content-Type','video/mp2t')]+fields,'body':TS})
            self.assertEqual(status,200);self.assertEqual(body,TS);self.clean(headers)
    def test_04_normalized_media_header_values(self):
        status,headers,body=self.request({'headers':[('Content-Type','video/mp2t; provider="'+URL+'"'),('Cache-Control','extension="'+URL+'"')],'body':TS})
        self.assertEqual(status,200);self.assertEqual(body,TS);self.clean(headers)
        self.assertEqual(dict((k.lower(),v) for k,v in headers)['content-type'],'video/mp2t')
    def test_05_redirects_rejected_on_stream_and_app_routes(self):
        for code in (301,302,303,307,308):
            for admin in (False,True):
                with self.subTest(code=code,admin=admin):
                    status,headers,body=self.request({'status':code,'headers':[('Content-Type','video/mp2t'),('Location',URL),('Refresh','0;url='+URL)],'body':b''},admin=admin)
                    self.assertEqual(status,502);self.clean(headers,media=not admin)
                    self.assertNotIn(SENTINEL.encode(),body)
    def test_06_unsupported_types_and_status(self):
        for ctype in ('text/html','application/vnd.apple.mpegurl','application/json','application/octet-stream'):
            status,headers,_=self.request({'headers':[('Content-Type',ctype),('Location',URL)],'body':b'fixture'})
            self.assertEqual(status,502);self.clean(headers)
        for code in (204,206,400,500):
            status,headers,_=self.request({'status':code,'headers':[('Content-Type','video/mp2t'),('Location',URL)],'body':TS if code!=204 else b''})
            self.assertEqual(status,502);self.clean(headers)
    def test_07_malformed_upstream(self):
        for raw in (b'HTTP/1.1 broken\r\n\r\n',b'HTTP/1.1 200 OK\r\nContent-Length: nope\r\n\r\n',b'HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\nx'):
            status,headers,_=self.request({'raw':raw})
            self.assertEqual(status,502)
            self.assertNotIn(SENTINEL,str(headers))
    def test_08_chunked_and_incremental_live_stream(self):
        key=len(CASES)+1;CASES[key]={'headers':[('Content-Type','video/mp2t'),('Refresh',URL)],'chunked':True,'stream':True}
        conn=http.client.HTTPConnection('127.0.0.1',19192,timeout=4)
        start=time.monotonic();conn.request('GET','/proxy/ts/stream/00000000-0000-0000-0000-'+format(key,'012x'))
        response=conn.getresponse();first=response.read(len(TS));first_time=time.monotonic()-start
        rest=response.read();elapsed=time.monotonic()-start
        self.assertEqual(response.status,200);self.assertEqual(first,TS);self.assertEqual(first+rest,TS*4)
        self.assertLess(first_time,.8);self.assertGreater(elapsed,1.1);self.clean(response.getheaders())
        self.assertFalse(response.chunked);self.assertTrue(response.will_close);conn.close()
    def test_09_head_and_connection_reuse(self):
        status,headers,body=self.request({'headers':[('Content-Type','video/mp2t')],'body':TS*2},method='HEAD')
        self.assertEqual(status,200);self.assertEqual(body,b'');self.clean(headers)
        self.assertEqual(dict((k.lower(),v) for k,v in headers)['content-length'],str(len(TS)*2))
        conn=http.client.HTTPConnection('127.0.0.1',19192,timeout=4)
        for _ in range(2):
            key=len(CASES)+1;CASES[key]={'headers':[('Content-Type','video/mp2t')],'body':TS}
            conn.request('GET','/proxy/ts/stream/00000000-0000-0000-0000-'+format(key,'012x'))
            response=conn.getresponse();self.assertEqual(response.read(),TS);self.assertFalse(response.will_close)
        conn.close()
    def test_10_identity_and_encoded_upstream(self):
        key=len(CASES)+1
        status,headers,_=self.request({'headers':[('Content-Type','video/mp2t'),('Content-Encoding','gzip')],'body':gzip.compress(TS)},headers={'Accept-Encoding':'gzip'})
        self.assertEqual(REQUEST_HEADERS[key].get('Accept-Encoding'),'identity')
        self.assertEqual(status,502);self.clean(headers)
        status,headers,body=self.request({'headers':[('Content-Type','video/mp2t'),('Content-Encoding','identity')],'body':TS})
        self.assertEqual(status,200);self.assertEqual(body,TS);self.clean(headers)
    def test_11_other_successful_application_paths(self):
        for ctype in ('application/json','text/css','application/javascript','application/xml'):
            dangerous=[(h,URL) for h in DANGEROUS if h not in ('Server','Via')]
            status,headers,body=self.request({'headers':[('Content-Type',ctype),('Cache-Control','no-cache'),('ETag','"local-asset"'),('Vary','Accept-Encoding'),('Set-Cookie','sessionid=local-application-cookie; HttpOnly; SameSite=Lax')]+dangerous,'body':b'local response'},admin=True)
            self.assertEqual(status,200);self.assertEqual(body,b'local response');self.clean(headers,media=False)
            d=dict((k.lower(),v) for k,v in headers);self.assertEqual(d['content-type'],ctype)
            self.assertIn('sessionid=local-application-cookie',d['set-cookie']);self.assertEqual(d['etag'],'"local-asset"')
    def test_12_encoded_application_assets(self):
        body=gzip.compress(b'local CSS body')
        status,headers,result=self.request({'headers':[('Content-Type','text/css'),('Content-Encoding','gzip'),('Location',URL)],'body':body},admin=True,headers={'Accept-Encoding':'gzip'})
        self.assertEqual(status,200);self.assertEqual(result,body);self.clean(headers,media=False)
        self.assertEqual(dict((k.lower(),v) for k,v in headers)['content-encoding'],'gzip')
    def test_13a_provider_trailers_never_reach_client(self):
        for announced in (False,True):
            for admin in (False,True):
                key=len(CASES)+1
                CASES[key]={'headers':[('Content-Type','application/json' if admin else 'video/mp2t')],'body':TS,'chunked':True,'trailers': [('Location',URL),('Refresh',URL),('X-Provider-URL',URL)],'announced':announced}
                path=('/api/fixture/' if admin else '/proxy/ts/stream/00000000-0000-0000-0000-')+format(key,'012x')
                wire=socket.create_connection(('127.0.0.1',19192),timeout=4)
                wire.sendall(('GET '+path+' HTTP/1.1\r\nHost: 127.0.0.1:19192\r\nConnection: close\r\n\r\n').encode())
                data=b''
                while True:
                    part=wire.recv(4096)
                    if not part:break
                    data+=part
                wire.close()
                self.assertNotIn(SENTINEL.encode(),data)
                head,body=data.split(b'\r\n\r\n',1)
                self.assertIn(b'200 OK',head);self.assertEqual(body,TS,msg='announced='+str(announced)+' admin='+str(admin)+' headers='+repr(head))
                self.assertNotIn(b'\r\ntrailer:',head.lower())
    def test_13_forbidden_routes_never_reach_upstream(self):
        for path in ('/proxy/hls/stream/id/index.m3u8','/output/m3u?direct=true','/proxy/ts/stream/00000000-0000-0000-0000-000000000001?direct=true','/proxy/ts/stream/00000000-0000-0000-0000-000000000001?other=value'):
            before=len(HITS);conn=http.client.HTTPConnection('127.0.0.1',19192,timeout=3);conn.request('GET',path)
            response=conn.getresponse();self.assertEqual(response.status,403);response.read();conn.close();self.assertEqual(len(HITS),before)

    def test_14_identity_headers_removed_on_media_and_admin(self):
        for admin in [False,True]:
            key=len(CASES)+1
            status,headers,body=self.request({'headers':[('Content-Type','text/plain' if admin else 'video/mp2t')],'body':TS},admin=admin,headers={'X-Real-IP':'203.0.113.8','X-Forwarded-For':'203.0.113.8'})
            self.assertEqual(status,200)
            seen={k.lower():v for k,v in REQUEST_HEADERS[key].items()}
            self.assertNotIn('x-real-ip',seen);self.assertEqual(seen['x-forwarded-for'],'127.0.0.1')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--binary',type=Path,default=BINARY);parser.add_argument('--config',type=Path,default=CONFIG);parser.add_argument('--report',type=Path);parser.add_argument('--case',action='append')
    args=parser.parse_args();BINARY=args.binary.resolve();CONFIG=args.config.resolve()
    suite=unittest.TestSuite(GatewayResponses(name) for name in args.case) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(GatewayResponses)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary={'pinned_binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'config_sha256':hashlib.sha256(CONFIG.read_bytes()).hexdigest(),'groups_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'fixture_requests':len(HITS),'external_network_available':False,'success':result.wasSuccessful() and not result.skipped}
    print(json.dumps(summary))
    if args.report:args.report.write_text(json.dumps(summary,indent=2)+'\n')
    raise SystemExit(0 if summary['success'] else 1)
