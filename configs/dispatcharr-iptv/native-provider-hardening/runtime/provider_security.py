"""Offline candidate: trusted AirVPN-only native metadata contract, no media.

Installed as core.provider_security in a separately reviewed image. Root-published authorization
and guard-status read-only mounts are prerequisites, never created by workers.
"""
import contextlib
import contextvars
import errno
import hashlib
import http.client
import io
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import selectors
import socket
import ssl
import threading
import time
from urllib.parse import urlencode, urlsplit, quote
from .provider_transport import MetadataHTTPS, Refused, private_read, digest, decode, xmltv_ids, url
from .provider_readiness import Readiness
from .provider_policy import Reader

CONTRACT = 'dispatcharr-native-airvpn-v1'
AUTHORIZATION = Reader()
GUARD = '/guard-status'
MAX_BYTES = 16 * 1024 * 1024
TOTAL = 30.0
IDLE = 5.0
FEATURES = ['artwork_stripped','bounded_io','guard_grant','manual_jobs','no_auto_dvr','no_redirect','no_retry','public_ipv4_pinning','public_policy_lease','tls','xml_no_dtd']
CURRENT = contextvars.ContextVar('provider_job',default=None)
SLOTS = threading.BoundedSemaphore(2)


class Denied(Refused):
    def __init__(self): super().__init__('provider_security_refused_no_retry')


def policy(key):
    try: return AUTHORIZATION.read(key)
    except Exception: raise Denied() from None


def remote(resource):
    return getattr(resource,'account_type',None)=='XC' or (getattr(resource,'source_type',None)=='xmltv' and bool(getattr(resource,'url',None)))


def resource_key(resource):
    try:
        tag=(resource.custom_properties or {})['provider_cli']
        key=tag['key']
        if tag['owner']!='dispatcharr-provider/v1/native-v1': raise Denied()
        if getattr(resource,'account_type',None)=='XC':
            if digest([url(resource.server_url,base=True),resource.username])!=key: raise Denied()
        elif getattr(resource,'source_type',None)=='xmltv':
            if digest(resource.url)!=policy(key).get('epg_url_sha256'): raise Denied()
        else: raise Denied()
        return key
    except Exception: raise Denied() from None


@contextlib.contextmanager
def job(kind,resource,operator_requested=False):
    if not remote(resource):
        yield; return
    if operator_requested is not True: raise Denied()
    if kind in ('refresh','epg') and getattr(resource,'is_active',False) is not True: raise Denied()
    key=resource_key(resource); p=policy(key)
    if kind not in p['operations']: raise Denied()
    try: reader=Readiness(GUARD,p['policy_review_sha256'])
    except Exception: raise Denied() from None
    value={'key':key,'kind':kind,'policy':p,'reader':reader,'requests':0}
    token=CURRENT.set(value)
    try:
        check(); yield
    finally: CURRENT.reset(token)


def check():
    state=CURRENT.get()
    if state is None: raise Denied()
    p=policy(state['key'])
    if p!=state['policy'] or state['kind'] not in p['operations']: raise Denied()
    try: state['reader'].check()
    except Exception: raise Denied() from None
    return state


class SafeLogger:
    """Never send raw source/provider strings, params or traceback to handlers."""
    def __init__(self,name): self.logger=logging.getLogger(name)
    def getEffectiveLevel(self): return self.logger.getEffectiveLevel()
    def isEnabledFor(self,level): return self.logger.isEnabledFor(level)
    def __getattr__(self,name):
        level={'debug':10,'trace':10,'info':20,'warning':30,'warn':30,'error':40,'exception':40,'critical':50}.get(name)
        if level is None: raise AttributeError(name)
        return lambda *args,**kwargs:self.logger.log(level,'native_provider_event_details_withheld')


def progress(*args,**kwargs):
    # Status fields remain available through the supported API. Unstructured
    # websocket progress strings are suppressed in these credential-bearing paths.
    return None


class Wire(io.RawIOBase):
    """Absolute and idle deadlines also cover HTTP headers and TLS handshakes."""
    def __init__(self,sock,deadline): self.sock=sock;self.deadline=deadline;self.count=0;self.limit=65536
    def readable(self): return True
    def operation(self,fn,event=selectors.EVENT_READ):
        idle=time.monotonic()+IDLE
        while True:
            check()
            remaining=min(self.deadline,idle)-time.monotonic()
            if remaining<=0: raise Denied()
            try: return fn()
            except ssl.SSLWantReadError: event=selectors.EVENT_READ
            except BlockingIOError: pass
            except ssl.SSLWantWriteError: event=selectors.EVENT_WRITE
            with selectors.DefaultSelector() as sel:
                sel.register(self.sock,event);sel.select(min(remaining,0.25))
    def readinto(self,buf):
        data=self.operation(lambda:self.sock.recv(min(len(buf),65536)))
        self.count+=len(data)
        if self.count>self.limit: raise Denied()
        buf[:len(data)]=data;return len(data)
    def makefile(self,*args,**kwargs): return io.BufferedReader(self,buffer_size=8192)


def fetch(target):
    """One pinned HTTPS GET. No requests/urllib retries, redirects or proxies."""
    state=check()
    state['requests']+=1
    if state['requests']>32 or not SLOTS.acquire(blocking=False): raise Denied()
    sock=None;response=None;deadline=time.monotonic()+TOTAL
    try:
        transport=MetadataHTTPS(None, approval_reader=lambda: policy(state['key']))
        u,ip=transport.authorize(target)
        check()
        if time.monotonic()>=deadline: raise Denied()
        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM);sock.setblocking(False)
        result=sock.connect_ex((ip,443))
        if result not in (0,errno.EINPROGRESS,errno.EWOULDBLOCK): raise Denied()
        wire=Wire(sock,deadline)
        # Nonblocking connect must finish before wrapping TLS. Each wait observes
        # current authorization; no hostname is resolved again for the connection.
        with selectors.DefaultSelector() as sel:
            sel.register(sock,selectors.EVENT_WRITE)
            connect_deadline=min(deadline,time.monotonic()+IDLE)
            while not sel.select(min(0.25,max(0,connect_deadline-time.monotonic()))):
                check()
                if time.monotonic()>=connect_deadline: raise Denied()
        if sock.getsockopt(socket.SOL_SOCKET,socket.SO_ERROR): raise Denied()
        context=ssl.create_default_context()
        if context.verify_mode!=ssl.CERT_REQUIRED or not context.check_hostname: raise Denied()
        raw=sock;sock=context.wrap_socket(raw,server_hostname=u.hostname,do_handshake_on_connect=False)
        sock.setblocking(False);wire=Wire(sock,deadline)
        wire.operation(sock.do_handshake)
        request=('GET '+u.path+('?' + u.query if u.query else '')+' HTTP/1.1\r\nHost: '+u.hostname+'\r\nAccept-Encoding: identity\r\nConnection: close\r\nUser-Agent: Dispatcharr-native-metadata/1\r\n\r\n').encode('ascii')
        sent=0
        while sent<len(request): sent+=wire.operation(lambda:sock.send(request[sent:]),selectors.EVENT_WRITE)
        response=http.client.HTTPResponse(wire);response.begin();wire.limit=MAX_BYTES+65536
        if response.status!=200 or response.getheader('Content-Encoding','identity').lower()!='identity': raise Denied()
        length=response.getheader('Content-Length')
        if length is not None and (not length.isdigit() or int(length)>MAX_BYTES): raise Denied()
        chunks=[];size=0
        while True:
            check()
            if time.monotonic()>=deadline: raise Denied()
            chunk=response.read1(65536)
            if not chunk: break
            size+=len(chunk)
            if size>MAX_BYTES: raise Denied()
            chunks.append(chunk)
        if length is not None and size!=int(length): raise Denied()
        check();return b''.join(chunks)
    except Exception: raise Denied() from None
    finally:
        if response is not None: response.close()
        if sock is not None: sock.close()
        SLOTS.release()


def xc_get(server,endpoint,params):
    state=check()
    if state['kind'] not in ('discover','refresh') or endpoint!='player_api.php': raise Denied()
    allowed={'get_live_categories','get_live_streams'}
    if params.get('action') not in allowed and 'action' in params: raise Denied()
    if set(params)-{'username','password','action','category_id'}: raise Denied()
    try:
        data=decode(fetch(url(server,base=True)+'/player_api.php?'+urlencode(params)))
        if params.get('action')=='get_live_streams':
            if not isinstance(data,list) or len(data)>100000: raise Denied()
            fields={'name','stream_id','category_id','epg_channel_id','container_extension','num','stream_type','added','is_adult','custom_sid','tv_archive','tv_archive_duration'}
            if any(not isinstance(row,dict) for row in data): raise Denied()
            # No external artwork, direct_source or unknown URL-bearing extension
            # fields enter native metadata through the stream importer.
            data=[{k:v for k,v in row.items() if k in fields} for row in data]
        return data
    except Exception: raise Denied() from None


def xmltv_download(source):
    state=check()
    if state['kind']!='epg' or resource_key(source)!=state['key']: raise Denied()
    try:
        data=clean_xmltv(fetch(source.url))  # UTF-8, size, no DTD/entities, well-formed tv
        # Never decompress an attacker-supplied archive; remote input is plain XML.
        from django.conf import settings
        if type(source.id) is not int or source.id<=0: raise Denied()
        check()
        directory=Path(settings.MEDIA_ROOT)/'cached_epg';directory.mkdir(exist_ok=True)
        name=directory/(str(source.id)+'.native.partial')
        # One crash-retained partial per source, never adopt/overwrite a stale
        # file. Reconciliation is explicit; no unbounded temporary-file growth.
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'wb') as f: f.write(data);f.flush();os.fsync(f.fileno())
            check()
            destination=directory/(str(source.id)+'.xml');os.replace(name,destination)
            source.file_path=str(destination);source.extracted_file_path=None
            source.save(update_fields=['file_path','extracted_file_path'])
        finally:
            Path(name).unlink(missing_ok=True)
        return True
    except Exception: raise Denied() from None


def contract(key):
    p=policy(key)
    try:
        MetadataHTTPS.context_checks(p)
        reader=Readiness(GUARD,p['policy_review_sha256']);generation=reader.check()
    except Exception: raise Denied() from None
    return {'contract':CONTRACT,'network_owner':'AirVPN','features':FEATURES,
            'provider_key':key,'epg_url_sha256':p['epg_url_sha256'],'guard_generation':generation,'expires_epoch':p['expires_epoch'],
            'runtime_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'source_hashes':source_hashes(),
            'operations':p['operations'],'media_activation':False,'native_removal':False}

class NoSession:
    def close(self): pass


def denied_remote_playlist(*args,**kwargs):
    raise Denied()


@contextlib.contextmanager
def safe_errors():
    try: yield
    except Exception: raise Denied() from None


def validate_xmltv(data):
    import xml.etree.ElementTree as ET
    if len(data)>MAX_BYTES: raise Denied()
    try:
        text=data.decode('utf-8-sig')
        if '<!doctype' in text.lower() or '<!entity' in text.lower(): raise Denied()
        parser=ET.XMLPullParser(events=('start','end'));depth=count=0;ids=set();root_seen=False
        for offset in range(0,len(text),8192):
            parser.feed(text[offset:offset+8192])
            for event,elem in parser.read_events():
                if event=='start':
                    depth+=1;count+=1
                    if not root_seen:
                        if elem.tag!='tv': raise Denied()
                        root_seen=True
                    if depth>64 or count>100000 or len(elem.attrib)>32: raise Denied()
                    if any(len(k)>256 or len(v)>2048 for k,v in elem.attrib.items()): raise Denied()
                    if elem.tag=='channel':
                        key=elem.attrib.get('id','')
                        if not 1<=len(key)<=256 or key in ids or any(ord(c)<33 for c in key): raise Denied()
                        ids.add(key)
                else:
                    if len(elem.text or '')>1048576 or len(elem.tail or '')>1048576: raise Denied()
                    elem.clear();depth-=1
        parser.close()
        if not root_seen or depth: raise Denied()
        return ids
    except Exception: raise Denied() from None


def source_hashes():
    expected=json.loads(Path(__file__).with_name('provider_contract_hashes.json').read_text())
    base=Path(__file__).resolve().parent.parent
    actual={}
    for relative,wanted in expected.items():
        if relative.startswith('/') or '..' in Path(relative).parts: raise Denied()
        path=base/relative
        actual[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual[relative]!=wanted: raise Denied()
    return actual


def media_url(server,username,password,stream_id,kind='live',extension='ts'):
    """Private metadata value only; building a URL grants no playback authority."""
    if (kind not in ('live','series','movie') or not re.fullmatch('[1-9][0-9]{0,11}',str(stream_id))
            or not re.fullmatch('[a-z0-9]{1,8}',extension)):
        raise Denied()
    return url(server,base=True)+'/'+kind+'/'+quote(username,safe='')+'/'+quote(password,safe='')+'/'+str(stream_id)+'.'+extension


def clean_xmltv(data):
    """Keep real guide text/IDs; discard external artwork/link triggers."""
    validate_xmltv(data)
    import xml.etree.ElementTree as ET
    tree=ET.fromstring(data.decode('utf-8-sig'))
    for parent in tree.iter():
        for child in list(parent):
            if child.tag.rsplit('}',1)[-1] in ('icon','image','url'): parent.remove(child)
    result=ET.tostring(tree,encoding='utf-8',xml_declaration=True)
    if len(result)>MAX_BYTES: raise Denied()
    return result
