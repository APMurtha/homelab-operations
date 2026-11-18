"""Vendored bounded metadata primitives from provider CLI 04e8295; server scope wraps these. No live credentials included."""
import datetime as dt

import fcntl

import hashlib

import http.client

import ipaddress

import json


import os

from pathlib import Path

import re

import socket

import ssl

import stat

import subprocess

import time

from urllib.parse import urlsplit, urlencode, quote

import uuid

import xml.etree.ElementTree as ET

MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 100000

class Refused(Exception):
    """Messages are fixed safe codes, never upstream text."""

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()

def decode(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise Refused('duplicate_JSON_field')
            out[key] = value
        return out
    if len(raw) > MAX_BYTES: raise Refused('response_size_limit')
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Refused('invalid_JSON_number')))
    except (ValueError, UnicodeError, RecursionError):
        raise Refused('invalid_JSON') from None

def private_read(path, root=False):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as file:
            s = os.fstat(file.fileno())
            if (not stat.S_ISREG(s.st_mode) or s.st_nlink != 1
                    or stat.S_IMODE(s.st_mode) != 0o600
                    or s.st_uid != (0 if root else os.geteuid())):
                raise Refused('private_regular_single_link_0600_required')
            return decode(file.read(MAX_BYTES + 1))
    except OSError:
        raise Refused('private_file_unavailable') from None

def url(value, base=False):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value):
        raise Refused('invalid_URL')
    try:
        u = urlsplit(value)
        if (u.scheme != 'https' or not u.hostname or u.username or u.password or u.fragment
                or u.port not in (None, 443) or '%' in u.netloc or '\\' in value):
            raise Refused('HTTPS_no_userinfo_fragment_or_nonstandard_port_required')
        host = u.hostname.encode('idna').decode('ascii').lower()
        try: ipaddress.ip_address(host)
        except ValueError: pass
        else: raise Refused('DNS_hostname_required')
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', host) or '..' in host:
            raise Refused('invalid_hostname')
        if '%' in u.path or any(p in ('.', '..') for p in u.path.split('/')) or '//' in u.path:
            raise Refused('ambiguous_URL_path')
        if base and u.query: raise Refused('Xtream_base_URL_must_not_contain_query')
        return 'https://' + host + u.path.rstrip('/') + (('?' + u.query) if u.query else '')
    except (ValueError, UnicodeError): raise Refused('invalid_URL') from None

class Unavailable(Refused): pass



class MetadataHTTPS:
    """Trusted root approval + actual namespace + DNS/IP/TLS pinning. No proxy/retry.

    Approval is an administrative assertion, not continuous firewall attestation.
    This class does not enter/create a namespace or alter a network/security rule.
    """
    def __init__(self, approval, *, approval_reader=None):
        self.approval_path = approval
        self.approval_reader = approval_reader
        self.context = ssl.create_default_context()
    @staticmethod
    def context_checks(a):
        if (a.get('vpn_interface') != 'tun0' or a.get('host_netns') == a.get('netns')
                or not isinstance(a.get('host_netns'), list) or len(a['host_netns']) != 2
                or any(type(n) is not int or n <= 0 for n in a['host_netns'])
                or not re.fullmatch('[a-f0-9]{64}', str(a.get('policy_review_sha256','')))):
            raise Refused('separately_reviewed_VPN_namespace_required')
        try:
            names = [l.split()[1] for l in Path('/etc/resolv.conf').read_text().splitlines() if l.startswith('nameserver ')]
            if names != ['127.0.0.1']: raise Refused('approved_loopback_DNS_required')
            for name in ['all','default']:
                if Path('/proc/sys/net/ipv6/conf/'+name+'/disable_ipv6').read_text().strip() != '1':
                    raise Refused('IPv6_must_remain_disabled')
        except OSError: raise Refused('VPN_context_unavailable') from None
    @staticmethod
    def vpn_route(ip):
        binary = next((p for p in [Path('/usr/sbin/ip'),Path('/usr/bin/ip')] if p.exists()), None)
        if binary is None: raise Refused('read_only_route_verifier_unavailable')
        st = binary.stat()
        if st.st_uid != 0 or st.st_mode & 0o022: raise Refused('unsafe_route_verifier')
        try:
            result = subprocess.run([str(binary),'-j','route','get',ip],capture_output=True,timeout=3)
            rows = decode(result.stdout)
            if result.returncode or not isinstance(rows,list) or len(rows)!=1 or rows[0].get('dev')!='tun0':
                raise Refused('metadata_route_must_use_existing_tun0')
        except (OSError,subprocess.TimeoutExpired): raise Refused('route_verification_failed') from None
    def authorize(self, target):
        a = self.approval_reader() if self.approval_reader is not None else private_read(self.approval_path, root=True)
        ns = Path('/proc/self/ns/net').stat()
        if (a.get('schema') != 1 or a.get('purpose') != 'IPTV_METADATA_ONLY'
                or not a.get('review_reference')
                or a.get('boot_id') != Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                or a.get('netns') != [ns.st_dev, ns.st_ino]
                or type(a.get('expires_epoch')) not in (float, int)
                or not time.time() < a['expires_epoch'] <= time.time() + 86400):
            raise Refused('metadata_path_approval_missing_stale_or_wrong_namespace')
        self.context_checks(a)
        u = urlsplit(url(target)); matches = [e for e in a.get('endpoints', [])
                if e.get('host') == u.hostname and (
                    (self.approval_reader is None and e.get('path') == u.path) or
                    (self.approval_reader is not None and e.get('path_sha256') == digest(u.path)))]
        if len(matches) != 1: raise Refused('metadata_destination_not_approved')
        ips = matches[0].get('ipv4', [])
        if not 1 <= len(ips) <= 16: raise Refused('approved_IP_set_invalid')
        try:
            if any(not ipaddress.IPv4Address(x).is_global for x in ips): raise ValueError()
            answers = resolve(u.hostname)
        except (ValueError, OSError): raise Refused('metadata_DNS_or_IP_invalid') from None
        if not answers or not answers <= set(ips): raise Refused('metadata_DNS_outside_approved_IP_set')
        chosen = sorted(answers)[0]; self.vpn_route(chosen)
        return u, chosen

def xmltv_ids(raw):
    if len(raw) > MAX_BYTES: raise Refused('unsafe_or_oversized_XMLTV')
    try: text = raw.decode('utf-8-sig')
    except UnicodeError: raise Refused('XMLTV_UTF8_required') from None
    if '<!doctype' in text.lower() or '<!entity' in text.lower():
        raise Refused('unsafe_or_oversized_XMLTV')
    try:
        root = ET.fromstring(text)
        if root.tag != 'tv': raise Refused('XMLTV_root_required')
        ids = [c.attrib['id'] for c in root.findall('channel')]
    except (ET.ParseError, KeyError, ValueError): raise Refused('invalid_XMLTV') from None
    if len(ids) > MAX_ROWS or len(ids) != len(set(ids)): raise Refused('duplicate_or_large_XMLTV_IDs')
    for ident in ids:
        if not isinstance(ident, str) or not 1 <= len(ident) <= 256 or any(ord(c) < 33 for c in ident):
            raise Refused('invalid_EPG_ID')
    return set(ids)

from .provider_dns import resolve
