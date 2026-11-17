"""Bounded DW English trial relay. No requests on import; private config on stdin.

External HTTPS resources use fresh all-public DNS validation, IP pinning and TLS
hostname verification. FFmpeg receives only opaque loopback MPEG-TS resources.
Permanent candidate; destination and finite-fetch enforcement retained from Phase 4M.
"""
import collections
import hashlib
import hmac
import http.client
import ipaddress
import json
import math
from pathlib import Path
import re
import secrets
import socket
import ssl
import threading
import time
import sys
import select
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_runtime import Budget, DNS, FetchFailure, FetchTimeout, Cancelled, DNSFailure, HTTPFailure
from telemetry import Telemetry
from rate_budget import RollingBudget
from guard_readiness import Readiness
from manifest_telemetry import ManifestTelemetry
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, urljoin, unquote

Denied = FetchFailure  # Legacy catch-all; typed categories remain distinct.
class SecurityRejected(FetchFailure):
    category = 'security_rejection'

HOST = 'dwamdstream102.akamaized.net'
PORT = 19193
MAX_MANIFEST = 1048576
MAX_SEGMENT = 8388608

class Relay:
    def __init__(self, config, *, resolver=None, context=None, dns=None, telemetry=None):
        self.source = config['source']
        self.parent = urlsplit(self.source).path.rsplit('/', 1)[0] + '/'
        self.guard = Readiness(config['guard_status_dir'], config['ready_hash'])
        self.expires = float('inf')
        self.rate = RollingBudget()
        self.resolver = resolver
        self.dns = dns or DNS()
        self.telemetry_key = secrets.token_bytes(32)
        self.fetch_timeouts = {}
        for kind in ('manifest', 'segment'):
            value = float(config.get(kind + '_deadline_seconds', 12))
            if not math.isfinite(value) or not .05 <= value <= 60:
                raise ValueError('invalid_fetch_deadline')
            self.fetch_timeouts[kind] = value
        self.cancelled = threading.Event()
        self.active_budgets = set()
        self.local = threading.local()
        self.request_sequence = 0
        self.manifest_telemetry = ManifestTelemetry()
        self.context = context or ssl.create_default_context()
        if self.context.verify_mode != ssl.CERT_REQUIRED or not self.context.check_hostname:
            raise SecurityRejected('TLS_verification_required')
        self.secret = secrets.token_bytes(32)
        self.session = secrets.token_hex(16)
        self.resources = collections.OrderedDict()
        self.lock = threading.RLock()
        self.slots = threading.BoundedSemaphore(4)
        self.stats = collections.Counter()
        self.peers = collections.OrderedDict()
        self.fatal = None
        self.scope(self.source, manifest=True)
        self.telemetry = telemetry or Telemetry(config.get('telemetry_path'),run_id=config.get('telemetry_run_id'))

    def check(self):
        if self.fatal:
            raise SecurityRejected('relay_latched_closed')
        if time.monotonic() >= self.expires:
            raise SecurityRejected('expired')
        try:
            self.guard.check()
        except (OSError, ValueError, TypeError, KeyError):
            raise SecurityRejected('guard_not_ready') from None

    def scope(self, url, manifest=False):
        if not isinstance(url, str) or len(url) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in url) or '\\' in url:
            raise SecurityRejected('invalid_URI')
        try:
            u = urlsplit(url)
            valid = u.scheme == 'https' and u.netloc == HOST and u.port is None
        except ValueError:
            raise SecurityRejected('invalid_authority') from None
        # No percent escapes, queries or traversal: this trial's reviewed media
        # path needs none. Reject ambiguous normalization rather than guessing.
        if not valid or u.query or u.fragment or '%' in u.path or '//' in u.path or any(p in ('.','..') for p in u.path.split('/')):
            raise SecurityRejected('unapproved_destination')
        if manifest:
            if url != self.source or not u.path.endswith('.m3u8'):
                raise SecurityRejected('unapproved_manifest')
        elif not u.path.startswith(self.parent) or not u.path.endswith('.ts'):
            raise SecurityRejected('unapproved_segment')
        return u

    def fetch(self, url, manifest=False, *, cancel=None, validator=None):
        kind = 'manifest' if manifest else 'segment'
        with self.lock:
            self.request_sequence += 1
            self.stats['requests'] += 1  # Includes DNS and failed attempts.
            sequence = self.request_sequence
            attempts = self.stats['requests']
        ids = {'request_id': format(sequence, 'x'),
               'resource_id': hmac.new(self.telemetry_key, str(url).encode(), hashlib.sha256).hexdigest()[:16],
               'kind': kind}
        self.local.ids = ids
        budget = Budget(self.fetch_timeouts[kind], self.telemetry, ids, (self.cancelled, cancel))
        with self.lock: self.active_budgets.add(budget)
        raw = tls = response = None
        outcome = 'ok'
        self.telemetry.emit('fetch', 'start', **ids)
        try:
            with budget.stage('guard'):
                self.check()
                u = self.scope(url, manifest)
                try: self.rate.take()
                except ValueError: raise SecurityRejected('rolling_request_budget') from None
            with budget.stage('dns'):
                answers = self.dns.resolve(HOST, 443, budget, self.resolver)
                try: addresses = {a[4][0] for a in answers}
                except Exception: raise DNSFailure('dns_answer_format', 'dns') from None
                if not addresses or any(not ipaddress.ip_address(a).is_global or ipaddress.ip_address(a).is_multicast or ipaddress.ip_address(a).is_reserved for a in addresses):
                    raise SecurityRejected('nonpublic_DNS', 'dns')
                ipv4 = sorted(a for a in addresses if ipaddress.ip_address(a).version == 4)
                if not ipv4: raise SecurityRejected('no_approved_IPv4', 'dns')
                self.check()
            with budget.stage('connect'):
                raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                budget.socket(raw)
                raw.connect((ipv4[0], 443))
            with budget.stage('tls'):
                tls = self.context.wrap_socket(raw, server_hostname=HOST, do_handshake_on_connect=False)
                budget.socket(tls)
                tls.do_handshake()
            with budget.stage('request'):
                budget.socket(tls)
                tls.sendall(('GET '+u.path+' HTTP/1.1\r\nHost: '+HOST+'\r\nUser-Agent: Dispatcharr-DW-trial/1\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n').encode('ascii'))
            with budget.stage('headers'):
                budget.socket(tls)
                response = http.client.HTTPResponse(tls)
                response.begin()
                status = response.status
                self.telemetry.emit('headers','sample',**ids,status=status)
                if 300 <= status <= 399: raise SecurityRejected('upstream_redirect_rejected', 'headers')
                if status != 200: raise HTTPFailure('upstream_status_failure', 'headers')
                headers = response.getheaders()
                def values(name): return [v for k,v in headers if k.lower() == name]
                encoding = values('content-encoding')
                if len(encoding) > 1 or encoding and encoding[0].lower() != 'identity':
                    raise SecurityRejected('encoded_response', 'headers')
                types = values('content-type')
                if len(types) != 1: raise SecurityRejected('ambiguous_content_type', 'headers')
                media = [v.split(';',1)[0].strip().lower() for v in types[0].split(',')]
                allowed = {'application/vnd.apple.mpegurl','application/x-mpegurl','audio/mpegurl','audio/x-mpegurl'} if manifest else {'video/mp2t','application/octet-stream'}
                if not media or len(media)>4 or any(t not in allowed for t in media):
                    raise SecurityRejected('unsupported_content_type', 'headers')
                lengths = values('content-length'); transfer = values('transfer-encoding')
                if len(lengths)>1 or len(transfer)>1 or lengths and transfer:
                    raise SecurityRejected('ambiguous_response_framing', 'headers')
                if transfer and transfer[0].lower() != 'chunked': raise SecurityRejected('unsupported_transfer_encoding', 'headers')
                limit = MAX_MANIFEST if manifest else MAX_SEGMENT
                length = lengths[0] if lengths else None
                if length and (not length.isdigit() or int(length)>limit): raise SecurityRejected('response_size_limit', 'headers')
            with budget.stage('body'):
                data = bytearray()
                try:
                    while True:
                        budget.socket(tls)
                        block = response.read1(min(65536, limit+1-len(data)))
                        budget.check()
                        if not block: break
                        if not data: self.telemetry.emit('body_first_byte','ok',**ids,bytes=len(block),duration_ms=round((time.monotonic()-budget.started)*1000,3))
                        data.extend(block)
                        if len(data)>limit: raise SecurityRejected('response_size_limit', 'body')
                        if length is not None and len(data)==int(length): break
                    if length is not None and len(data)!=int(length): raise HTTPFailure('truncated_response_body', 'body')
                finally: self.telemetry.emit('body','sample',**ids,bytes=len(data))
                data = bytes(data)
            with budget.stage('manifest_validation' if manifest else 'segment_validation'):
                output = validator(data) if validator is not None else data
                self.check()
                if manifest:
                    content_id=hmac.new(self.telemetry_key, data, hashlib.sha256).hexdigest()[:16]
                    def segment_id(uri):
                        value=urljoin(self.source,uri)
                        return hmac.new(self.telemetry_key,value.encode(),hashlib.sha256).hexdigest()[:16]
                    metadata=self.manifest_telemetry.observe(data,content_id,ids['request_id'],segment_id)
                    self.telemetry.emit('manifest_validation','sample',**ids,content_id=content_id,**metadata)
                else:
                    self.telemetry.emit('segment_validation','sample',**ids,**self.manifest_telemetry.segment(ids['resource_id']))
            budget.check()
            with self.lock:
                self.peers[ipv4[0]] = None
                self.peers.move_to_end(ipv4[0])
                while len(self.peers) > 64: self.peers.popitem(last=False)
                self.stats['bytes'] += len(data)
                self.stats['manifests' if manifest else 'segments'] += 1
            self.telemetry.emit('fetch', 'ok', **ids, status=status, bytes=len(data), duration_ms=round((time.monotonic()-budget.started)*1000,3))
            return output
        except ssl.SSLCertVerificationError:
            budget.check()
            outcome = 'security_rejection'
            raise
        except FetchFailure as exc:
            outcome = exc.category
            raise
        except Exception:
            try: budget.check()
            except FetchFailure as exc:
                outcome = exc.category
                raise
            outcome = 'http_failure'
            raise HTTPFailure('upstream_io_failure', budget.stage_name) from None
        finally:
            if outcome != 'ok': self.telemetry.emit('fetch', outcome, **ids, duration_ms=round((time.monotonic()-budget.started)*1000,3))
            if response is not None: response.close()
            budget.close()
            if raw is not None: raw.close()
            with self.lock: self.active_budgets.discard(budget)

    def close(self):
        self.cancelled.set()
        with self.lock: budgets = list(self.active_budgets)
        for budget in budgets: budget.abort('cancelled')
        end = time.monotonic() + 1
        while self.active_budgets and time.monotonic() < end: time.sleep(.01)
        return self.telemetry.close() and not self.active_budgets and not self.dns.active

    def rewrite(self, data):
        if len(data) > MAX_MANIFEST:
            raise SecurityRejected('manifest_size_limit')
        try: text = data.decode('utf-8-sig')
        except UnicodeError: raise SecurityRejected('manifest_encoding') from None
        if any(ord(c) < 32 and c not in '\r\n' for c in text):
            raise SecurityRejected('manifest_control')
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines or lines.pop(0) != '#EXTM3U':
            raise SecurityRejected('invalid_manifest')
        output = ['#EXTM3U']; pending=False; count=0; seen=set()
        for line in lines:
            if not line.startswith('#'):
                if not pending: raise SecurityRejected('unexpected_URI')
                url = urljoin(self.source, line)
                self.scope(url)
                token = hmac.new(self.secret, url.encode(), hashlib.sha256).hexdigest()
                with self.lock:
                    self.resources[token] = url
                    self.resources.move_to_end(token)
                    while len(self.resources) > 4096: self.resources.popitem(last=False)
                output.append('/s/'+self.session+'/r/'+token+'.ts')
                pending=False; count+=1
            elif line.startswith('#EXTINF:'):
                if pending: raise SecurityRejected('missing_segment')
                try: duration=float(line.split(':',1)[1].split(',',1)[0])
                except ValueError: raise SecurityRejected('invalid_duration') from None
                if not math.isfinite(duration) or not 0 < duration <= 10:
                    raise SecurityRejected('invalid_duration')
                output.append('#EXTINF:'+str(duration)+','); pending=True
            elif re.fullmatch(r'#EXT-X-(VERSION|TARGETDURATION|MEDIA-SEQUENCE|DISCONTINUITY-SEQUENCE):[0-9]{1,16}',line):
                key=line.split(':',1)[0]
                if key in seen: raise SecurityRejected('duplicate_HLS_tag')
                seen.add(key); output.append(line)
            elif line in ('#EXT-X-ENDLIST','#EXT-X-DISCONTINUITY','#EXT-X-INDEPENDENT-SEGMENTS'):
                output.append(line)
            elif line == '#EXT-X-KEY:METHOD=NONE':
                output.append(line)
            elif line.startswith('#EXT-X-PROGRAM-DATE-TIME:'):
                if not re.fullmatch(r'#EXT-X-PROGRAM-DATE-TIME:[0-9T:.+Z-]{10,40}',line):
                    raise SecurityRejected('unexpected_date_metadata')
            elif line.startswith('#EXT-X-SPLICEPOINT-SCTE35:'):
                if not re.fullmatch(r'#EXT-X-SPLICEPOINT-SCTE35:[A-Za-z0-9+/=]{1,4096}',line):
                    raise SecurityRejected('unexpected_splice_metadata')
                # Drop only opaque playlist metadata, never media segments.
            else:
                raise SecurityRejected('unsupported_HLS_tag')
        if pending or not count or '#EXT-X-TARGETDURATION' not in seen or '#EXT-X-MEDIA-SEQUENCE' not in seen:
            raise SecurityRejected('incomplete_media_playlist')
        return ('\n'.join(output)+'\n').encode('ascii')

    def resource(self, path, *, cancel=None):
        self.check()
        if path == '/s/'+self.session+'/live.m3u8':
            return 'application/vnd.apple.mpegurl', self.fetch(self.source, True, cancel=cancel, validator=self.rewrite)
        match = re.fullmatch('/s/'+self.session+r'/r/([a-f0-9]{64})\.ts',path)
        if not match: raise SecurityRejected('unknown_resource')
        with self.lock: url = self.resources.get(match[1])
        if not url: raise SecurityRejected('unknown_resource')
        return 'video/mp2t', self.fetch(url, cancel=cancel, validator=self.validate_segment)

    def validate_segment(self, data):
        if len(data) < 188*3 or len(data)%188 or any(
            data[i] != 0x47 or data[i+1] & 0x80 or data[i+3] & 0xc0
            or not (data[i+3] & 0x30)
            or ((data[i+3] & 0x20) and data[i+4] > 183)
            for i in range(0,len(data),188)):
            raise SecurityRejected('not_MPEG_TS')
        return data

    def snapshot(self):
        with self.lock:
            return {'guard_generation':self.guard.expected['generation'],'counts':dict(self.stats),'peer_IPs':sorted(self.peers),'fatal':self.fatal,'remaining_seconds':None, 'telemetry':self.telemetry.snapshot(), 'active_DNS_workers':len(self.dns.active)}


def server(relay, port=PORT):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'LocalMediaRelay'
        def log_message(self,*args): pass
        def do_GET(self):
            if self.path == '/healthz':
                import json
                try: relay.check(); ok = not relay.cancelled.is_set()
                except Exception: ok = False
                body = json.dumps({'instance': relay.session, 'ok': ok}).encode()
                self.send_response(200 if ok else 503)
                self.send_header('Content-Length', str(len(body))); self.end_headers()
                self.wfile.write(body); return
            if not relay.slots.acquire(blocking=False):
                self.send_response(503); self.send_header('Content-Length','0'); self.end_headers(); return
            cancel = threading.Event(); finished = threading.Event()
            def peer_watch():
                while not finished.wait(.025):
                    try:
                        readable,_,_ = select.select([self.connection],[],[],0)
                        if readable and self.connection.recv(1,socket.MSG_PEEK|socket.MSG_DONTWAIT)==b'':
                            cancel.set(); return
                    except (OSError,ValueError): cancel.set(); return
            watcher = threading.Thread(target=peer_watch,daemon=True); watcher.start()
            try:
                try:
                    typ,body = relay.resource(self.path,cancel=cancel)
                    if cancel.is_set(): return
                    self.send_response(200); self.send_header('Content-Type',typ)
                    self.send_header('Content-Length',str(len(body)))
                    self.send_header('Cache-Control','no-store'); self.end_headers()
                    begin = time.monotonic()
                    self.wfile.write(body)
                    relay.telemetry.emit('local_send','ok',**getattr(relay.local,'ids',{}),bytes=len(body),duration_ms=round((time.monotonic()-begin)*1000,3))
                except (BrokenPipeError,ConnectionResetError):
                    cancel.set(); relay.telemetry.emit('local_send','disconnect')
                except Exception as exc:
                    category = exc.category if isinstance(exc,FetchFailure) else 'security_rejection' if isinstance(exc,ssl.SSLCertVerificationError) else 'internal_error'
                    code = exc.code if isinstance(exc,FetchFailure) else 'internal_error'
                    if category!='cancelled' and code!='unknown_resource' and relay.fatal is None: relay.fatal=category
                    relay.stats['rejections']+=1
                    if not cancel.is_set():
                        self.send_response(502); self.send_header('Content-Length','0'); self.end_headers()
            finally:
                finished.set(); watcher.join(.1); relay.slots.release()
    from bounded_server import BoundedServer
    srv=BoundedServer(('127.0.0.1',port),Handler)
    srv.daemon_threads=True; srv.block_on_close=False
    return srv
