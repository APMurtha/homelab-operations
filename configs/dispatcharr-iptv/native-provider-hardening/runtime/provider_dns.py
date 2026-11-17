"""Bounded A-only DNS via the existing VPN namespace's loopback resolver.

No fork/thread child (Celery prefork workers are daemonic), no fallback resolver,
no DNS search suffixes, and no external route. TLS still authenticates the host.
"""
import ipaddress
import secrets
import socket
import struct


def resolve(host):
    try:
        labels=host.encode('idna').split(b'.')
        if any(not 1<=len(x)<=63 for x in labels) or len(host)>253: raise ValueError()
        question=b''.join(bytes([len(x)])+x for x in labels)+b'\0\0\1\0\1'
        token=secrets.token_bytes(2);packet=token+struct.pack('!HHHHH',0x100,1,0,0,0)+question
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.settimeout(5);sock.connect(('127.0.0.1',53));sock.send(packet);data=sock.recv(16385)
        if len(data)>16384 or len(data)<12 or data[:2]!=token: raise ValueError()
        flags,questions,answers,ns,ar=struct.unpack('!HHHHH',data[2:12])
        if flags & 0x8000==0 or flags & 0x020f or questions!=1 or not 1<=answers<=32 or ns+ar>64: raise ValueError()
        def name(offset):
            out=[];seen=set();end=None
            while True:
                if offset>=len(data) or offset in seen or len(seen)>64: raise ValueError()
                seen.add(offset);n=data[offset];offset+=1
                if n==0: return b'.'.join(out).lower(),end or offset
                if n & 0xc0==0xc0:
                    if offset>=len(data): raise ValueError()
                    if end is None:end=offset+1
                    offset=((n&63)<<8)|data[offset];continue
                if n>63 or offset+n>len(data): raise ValueError()
                out.append(data[offset:offset+n]);offset+=n
        query,offset=name(12)
        if query!=host.lower().encode('idna') or data[offset:offset+4]!=b'\0\1\0\1': raise ValueError()
        offset+=4;ips=set()
        for _ in range(answers):
            _,offset=name(offset)
            if offset+10>len(data): raise ValueError()
            kind,cls,ttl,length=struct.unpack('!HHIH',data[offset:offset+10]);offset+=10
            if offset+length>len(data): raise ValueError()
            if kind==1 and cls==1 and length==4: ips.add(str(ipaddress.IPv4Address(data[offset:offset+4])))
            elif kind not in (5,46): raise ValueError()
            offset+=length
        if not ips: raise ValueError()
        return ips
    except Exception: raise ValueError('VPN_DNS_refused') from None
