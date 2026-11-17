"""Bounded metadata, strict transports and durable private local ownership.

No application mutation transport exists in this release. A future adapter needs
separate security review; saving a draft does not register/activate a provider.
"""
import datetime as dt
import fcntl
import hashlib
import http.client
import ipaddress
import json
import multiprocessing
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

OWNER = 'dispatcharr-provider/v1'
MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 100000
MAX_IMPORT = 200
COLLECTIONS = ('/api/m3u/accounts/', '/api/channels/channels/',
               '/api/channels/streams/', '/api/channels/groups/',
               '/api/epg/sources/', '/api/epg/epgdata/')

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


def atomic(path, value):
    data = (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()
    if len(data) > MAX_BYTES: raise Refused('private_state_size_limit')
    temp = path.with_name('.' + uuid.uuid4().hex)
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
        fd = os.open(path.parent, os.O_DIRECTORY | os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        temp.unlink(missing_ok=True)


class Redactor:
    def __init__(self, *secrets):
        self.secrets = {x for x in secrets if isinstance(x, str) and x}
    def collect(self, value):
        if isinstance(value, dict):
            for key, v in value.items():
                if key.lower() in ('password', 'username', 'token', 'access', 'access_token') and isinstance(v, str):
                    self.secrets.add(v)
                self.collect(v)
        elif isinstance(value, list):
            for v in value: self.collect(v)
    def text(self, value):
        s = str(value)
        # Do not echo any provider-returned URL or ANSI/control sequence.
        s = re.sub(r'https?://\S+', '[URL withheld]', s, flags=re.I)
        for secret in sorted(self.secrets, key=len, reverse=True):
            for form in {secret, quote(secret, safe='')}:
                s = s.replace(form, '[redacted]')
        return ''.join(c if c.isprintable() else '?' for c in s)[:160]


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


def provider(name, server, username, password, epg, max_streams):
    if not re.fullmatch(r'[\w .-]{1,80}', name, flags=re.UNICODE): raise Refused('invalid_provider_name')
    if any(not isinstance(x, str) or not x or len(x) > 512 or any(ord(c) < 32 for c in x)
           for x in (username, password)):
        raise Refused('invalid_credentials')
    if type(max_streams) is not int or not 1 <= max_streams <= 100:
        raise Refused('positive_known_connection_allowance_required')
    server = url(server, base=True)
    value = {'name': name, 'server': server, 'username': username, 'password': password,
             'epg_url': url(epg) if epg else None, 'max_streams': max_streams}
    if epg and not (urlsplit(value['epg_url']).path.endswith(('.xml', '.xmltv')) or urlsplit(value['epg_url']).path.endswith('/xmltv.php')):
        raise Refused('XMLTV_metadata_path_required')
    value['key'] = digest([server, username])
    return value


class Unavailable(Refused): pass


def _dns_child(pipe, host):
    try:
        answers = {r[4][0] for r in socket.getaddrinfo(host, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)}
        pipe.send(sorted(answers) if len(answers) <= 32 else [])
    except BaseException: pipe.send([])
    finally: pipe.close()


def resolve(host):
    # Ephemeral bounded DNS worker; no persistent service and no provider URL in argv.
    context = multiprocessing.get_context('fork')
    parent, child = context.Pipe(duplex=False)
    worker = context.Process(target=_dns_child, args=(child, host))
    worker.start(); child.close()
    try:
        if not parent.poll(5): raise Refused('metadata_DNS_deadline')
        answers = set(parent.recv())
        if not answers: raise Refused('metadata_DNS_failed')
        return answers
    finally:
        parent.close()
        if worker.is_alive(): worker.terminate()
        worker.join(2)
        if worker.is_alive(): worker.kill(); worker.join(2)


class MetadataHTTPS:
    """Trusted root approval + actual namespace + DNS/IP/TLS pinning. No proxy/retry.

    Approval is an administrative assertion, not continuous firewall attestation.
    This class does not enter/create a namespace or alter a network/security rule.
    """
    def __init__(self, approval):
        self.approval_path = approval
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
        a = private_read(self.approval_path, root=True)
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
                if e.get('host') == u.hostname and e.get('path') == u.path]
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
    def get(self, target):
        u, ip = self.authorize(target)
        if self.context.verify_mode != ssl.CERT_REQUIRED or not self.context.check_hostname:
            raise Refused('verified_TLS_required')
        connection = http.client.HTTPSConnection(u.hostname, 443, timeout=10, context=self.context)
        try:
            # Connect once to the checked IP, while authenticating the original DNS name.
            raw = socket.create_connection((ip, 443), timeout=10)
            try: connection.sock = self.context.wrap_socket(raw, server_hostname=u.hostname); secure = connection.sock; connection.auto_open = 0
            except BaseException: raw.close(); raise
            path = u.path + (('?' + u.query) if u.query else '')
            connection.request('GET', path, headers={'Accept-Encoding': 'identity', 'Connection': 'close'})
            response = connection.getresponse()
            if response.status == 404: raise Unavailable('metadata_not_available')
            if response.status != 200: raise Refused('metadata_HTTP_error_or_redirect_refused')
            if response.getheader('Content-Encoding', 'identity') != 'identity':
                raise Refused('compressed_metadata_not_supported')
            start = time.monotonic(); chunks = []; size = 0
            while True:
                if time.monotonic() - start > 15: raise Refused('metadata_deadline')
                secure.settimeout(max(0.001, min(10, 15 - (time.monotonic() - start))))
                chunk = response.read1(65536)
                if not chunk: break
                size += len(chunk)
                if size > MAX_BYTES: raise Refused('metadata_size_limit')
                chunks.append(chunk)
            return b''.join(chunks)
        except Refused: raise
        except (OSError, ssl.SSLError, http.client.HTTPException):
            raise Refused('metadata_transport_failed_no_retry') from None
        finally: connection.close()


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


def catalogue(raw):
    if not isinstance(raw, dict) or set(raw) != {'groups', 'channels', 'epg_ids'}:
        raise Refused('catalogue_schema')
    groups, channels = raw['groups'], raw['channels']
    if not isinstance(groups, list) or not isinstance(channels, list) or max(len(groups), len(channels)) > MAX_ROWS:
        raise Refused('catalogue_size_or_schema')
    def positive(value):
        text = str(value)
        if not re.fullmatch('[1-9][0-9]{0,11}', text): raise Refused('invalid_provider_numeric_ID')
        return text
    gs = {}; cs = {}
    for r in groups:
        if not isinstance(r, dict): raise Refused('group_schema')
        ident = positive(r.get('category_id'))
        if ident in gs: raise Refused('duplicate_group_ID')
        gs[ident] = {'id': ident, 'name': str(r.get('category_name', ident))[:256]}
    for r in channels:
        if not isinstance(r, dict): raise Refused('channel_schema')
        ident = positive(r.get('stream_id')); group = positive(r.get('category_id'))
        if ident in cs or group not in gs: raise Refused('duplicate_channel_or_unknown_group')
        epg = r.get('epg_channel_id') or None
        if epg is not None and (not isinstance(epg, str) or len(epg) > 256 or any(ord(c) < 33 for c in epg)):
            raise Refused('invalid_EPG_ID')
        cs[ident] = {'id': ident, 'group': group, 'name': str(r.get('name', ident))[:256],
                     'epg_id': epg, 'format_hint': str(r.get('container_extension') or 'unknown')[:32]}
    ids = raw['epg_ids']
    if not isinstance(ids, list) or len(ids) > MAX_ROWS or any(not isinstance(x, str) for x in ids) or len(ids) != len(set(ids)):
        raise Refused('invalid_or_duplicate_EPG_IDs')
    return {'groups': gs, 'channels': cs, 'epg_ids': sorted(ids)}


def discover(p, transport):
    # Fixed metadata actions only. Never use provider-returned stream/logo URLs.
    def action(name):
        target = p['server'] + '/player_api.php?' + urlencode(
            {'username': p['username'], 'password': p['password'], 'action': name})
        return decode(transport.get(target))
    groups = action('get_live_categories'); channels = action('get_live_streams')
    epg = p['epg_url'] or p['server'] + '/xmltv.php?' + urlencode(
        {'username': p['username'], 'password': p['password']})
    try: ids = xmltv_ids(transport.get(epg)); status = 'available'
    except Unavailable:
        if p['epg_url']: raise
        ids = set(); status = 'provider_EPG_unavailable'
    result = catalogue({'groups': groups, 'channels': channels, 'epg_ids': sorted(ids)})
    result['epg_status'] = status
    return result


def select(text, available, cap=MAX_IMPORT):
    if text.strip() == 'all': chosen = set(available)
    else:
        chosen = {x.strip() for x in text.split(',') if x.strip()}
    if not chosen or not chosen <= set(available) or len(chosen) > cap:
        raise Refused('selection_unknown_empty_or_over_limit')
    return sorted(chosen, key=int)


def plan(p, cat, groups, channels, existing):
    if (not isinstance(existing, dict) or set(existing) - {'accounts', 'channels', 'groups', 'epg_sources', 'epgdata'}
            or any(not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows) for rows in existing.values())):
        raise Refused('snapshot_schema')
    for r in existing.get('accounts', []):
        if r.get('name') == p['name'] or (r.get('server_url') and r['server_url'].rstrip('/') == p['server'] and r.get('username') == p['username']):
            raise Refused('duplicate_existing_provider')
    if any(c not in cat['channels'] or cat['channels'][c]['group'] not in groups for c in channels):
        raise Refused('channel_outside_selected_groups')
    if not groups or not set(groups) <= set(cat['groups']) or not 1 <= len(channels) <= MAX_IMPORT or len(channels) != len(set(channels)):
        raise Refused('selection_invalid_or_over_limit')
    if any(row.get('name') == cat['groups'][g]['name'] for row in existing.get('groups',[]) for g in groups):
        raise Refused('existing_group_name_conflict_no_implicit_adoption')
    if p['epg_url'] and any(r.get('url') == p['epg_url'] for r in existing.get('epg_sources', [])):
        raise Refused('duplicate_EPG_source_no_implicit_adoption')
    selected = [cat['channels'][c] for c in channels]
    ids = [r['epg_id'] for r in selected if r['epg_id']]
    if len(ids) != len(set(ids)): raise Refused('ambiguous_selected_EPG_ID')
    for row in selected:
        if any(r.get('tvg_id') == row['epg_id'] and row['epg_id'] for r in existing.get('channels', [])):
            raise Refused('existing_channel_EPG_conflict')
        if any(r.get('name') == row['name'] for r in existing.get('channels', [])):
            raise Refused('existing_channel_name_conflict')
        if sum(r.get('tvg_id') == row['epg_id'] for r in existing.get('epgdata', [])) > 1:
            raise Refused('ambiguous_existing_EPG_mapping')
    matched = {r['id']: r['epg_id'] for r in selected if r['epg_id'] in cat['epg_ids']}
    return {'provider_key': p['key'], 'provider_name': p['name'], 'groups': groups,
            'selected': selected, 'epg_matches': matched, 'epg_status': cat.get('epg_status', 'fixture'),
            'unmatched_channel_ids': [r['id'] for r in selected if r['id'] not in matched],
            'existing_resources_affected': [], 'native_resources_created': [],
            'existing_EPG_ID_collisions_for_review': sorted({r['tvg_id'] for r in existing.get('epgdata',[]) if r.get('tvg_id') in ids}),
            'network_prerequisites': ['separately approved metadata path',
                'native account-create side effects and logging review',
                'reviewed stream-format-specific enforcement before activation'],
            'streaming_activation': 'BLOCKED',
            'native_import': 'PLAN ONLY: no Dispatcharr mutations in this release',
            'native_account_request_recipe': {
                'method': 'POST', 'path': '/api/m3u/accounts/',
                'body': {'name': p['name'], 'account_type': 'XC', 'server_url': '<private server>',
                         'username': '<private username>', 'password': '<private password>',
                         'is_active': False, 'max_streams': p['max_streams'], 'refresh_interval': 24,
                         'enable_vod': False, 'auto_enable_new_groups_live': False,
                         'auto_enable_new_groups_vod': False, 'auto_enable_new_groups_series': False},
                'blocked': 'Native create calls refresh_m3u_groups even when inactive'},
            'native_EPG_request_recipe': {
                'method': 'POST', 'path': '/api/epg/sources/',
                'body': {'name': p['name'] + ' EPG', 'source_type': 'xmltv',
                         'url': '<private optional/provider XMLTV URL>', 'is_active': False}},
            'channel_import_plan': [{'provider_stream_id': r['id'], 'group_id': r['group'],
                                     'stable_epg_id': matched.get(r['id']),
                                     'Dispatcharr_stream_ID': None, 'epg_data_ID': None,
                                     'activation': 'BLOCKED; resolve native IDs and owned EPG source after review'}
                                    for r in selected],
            'native_XC_URL_shape': '/live/<username>/<password>/<stream_id>.ts (pinned native importer)',
            'HLS_relay_compatibility': 'NOT established; TS hints are not HLS manifests'}


class Dispatcharr:
    """Read-only release-specific API. Credentials supplied from a private file."""
    def __init__(self, origin, credentials):
        from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler
        u = urlsplit(origin)
        if origin != 'http://127.0.0.1:9191':
            # Other origins require a separately reviewed adapter, rather than LAN credential guessing.
            raise Refused('supported_API_origin_is_loopback_9191_only')
        self.origin = origin; self.token = None
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *args): return None
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        result = self.request('POST', '/api/accounts/token/', credentials)
        if not isinstance(result, dict) or not isinstance(result.get('access'), str) or not 1 <= len(result['access']) <= 8192:
            raise Refused('invalid_API_auth_response')
        self.token = result['access']
    def request(self, method, path, body=None):
        from urllib.request import Request
        from urllib.error import HTTPError, URLError
        if method == 'POST' and path == '/api/accounts/token/': pass
        elif method == 'GET' and any(re.fullmatch(re.escape(p) + r'\?(?:visibility_filter=all&)?page=[1-9][0-9]*', path) for p in COLLECTIONS): pass
        else: raise Refused('Dispatcharr_write_or_scope_refused')
        headers = {'Content-Type': 'application/json'}
        if self.token: headers['Authorization'] = 'Bearer ' + self.token
        try:
            req = Request(self.origin + path, headers=headers, method=method,
                          data=json.dumps(body).encode() if body is not None else None)
            with self.opener.open(req, timeout=10) as response:
                return decode(response.read(MAX_BYTES + 1))
        except HTTPError as error:
            error.close(); raise Refused('Dispatcharr_API_error_no_retry') from None
        except (URLError, OSError, ValueError):
            raise Refused('Dispatcharr_API_error_no_retry') from None
    def rows(self, collection):
        if collection not in COLLECTIONS: raise Refused('collection_refused')
        rows = []; seen = set()
        for page in range(1, 65):
            query = '?visibility_filter=all&page=' if collection == '/api/channels/channels/' else '?page='
            value = self.request('GET', collection + query + str(page))
            batch = value if isinstance(value, list) else value.get('results') if isinstance(value, dict) else None
            if not isinstance(batch, list): raise Refused('API_pagination_schema')
            for row in batch:
                ident = row.get('id') if isinstance(row, dict) else None
                if type(ident) is not int or ident <= 0 or ident in seen: raise Refused('API_inventory_ID_conflict')
                seen.add(ident)
            rows.extend(batch)
            if len(rows) > MAX_ROWS: raise Refused('API_inventory_limit')
            if isinstance(value, list) or not value.get('next'): return rows
        raise Refused('API_page_limit')
    def inventory(self):
        return {key: self.rows(path) for key, path in [
            ('accounts', '/api/m3u/accounts/'), ('channels', '/api/channels/channels/'), ('groups','/api/channels/groups/'),
            ('epg_sources', '/api/epg/sources/'), ('epgdata', '/api/epg/epgdata/')]}


class Store:
    """Local drafts only; exact before-image checks, durable intents, no automatic retry."""
    def __init__(self, root):
        self.root = Path(root).absolute(); self.fd = None
    def __enter__(self):
        # Refuse symlink ancestors; never chmod/adopt an unsafe existing directory.
        for p in [self.root, *self.root.parents]:
            if p.is_symlink(): raise Refused('symlink_state_path')
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        st = self.root.stat()
        if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o700:
            raise Refused('private_state_directory_0700_required')
        self.fd = os.open(self.root/'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        st = os.fstat(self.fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o600:
            os.close(self.fd); self.fd = None; raise Refused('unsafe_state_lock')
        try: fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError: os.close(self.fd); self.fd = None; raise Refused('state_locked') from None
        return self
    def __exit__(self, *args):
        if self.fd is not None: os.close(self.fd)
    def path(self, key):
        if not re.fullmatch('[a-f0-9]{64}', key): raise Refused('invalid_provider_key')
        return self.root/(key+'.json')
    def get(self, key):
        value = private_read(self.path(key))
        if (value.get('owner') != OWNER or value.get('provider', {}).get('key') != key
                or value.get('plan', {}).get('native_resources_created') != []
                or value.get('plan', {}).get('provider_key') != key
                or digest([value['provider'].get('server'),value['provider'].get('username')]) != key):
            raise Refused('ownership_or_remote_resource_conflict')
        return value
    def all(self):
        paths = [p for p in self.root.glob('*.json') if re.fullmatch('[a-f0-9]{64}', p.stem)]
        if len(paths) > 1000: raise Refused('draft_inventory_limit')
        return [self.get(p.stem) for p in sorted(paths)]
    def pending(self):
        p = self.root/'operation.json'
        if not p.exists(): return None
        op = private_read(p)
        if (set(op) != {'schema','owner','id','key','kind','before','after','state'}
                or op['schema'] != 1 or op['owner'] != OWNER
                or not re.fullmatch('[a-f0-9]{32}', str(op['id']))
                or not re.fullmatch('[a-f0-9]{64}', str(op['key']))
                or op['kind'] not in ('add','refresh','remove')
                or op['state'] not in ('pending','complete','aborted_without_retry')
                or any(not re.fullmatch('[a-f0-9]{64}', str(op[k])) for k in ['before','after'])):
            raise Refused('operation_journal_conflict')
        return op
    def transact(self, key, before, after, kind):
        pending = self.pending()
        if pending and pending['state'] == 'pending': raise Refused('pending_operation_reconcile_first')
        path = self.path(key)
        actual = self.get(key) if path.exists() else None
        if actual != before: raise Refused('local_before_image_conflict')
        if after and (after.get('owner') != OWNER or after.get('provider', {}).get('key') != key
                      or after.get('plan', {}).get('native_resources_created') != []
                      or after.get('plan', {}).get('provider_key') != key
                      or digest([after['provider'].get('server'),after['provider'].get('username')]) != key):
            raise Refused('ownership_or_remote_resource_conflict')
        if kind not in ('add', 'refresh', 'remove'): raise Refused('operation_scope')
        operation = {'schema': 1, 'owner': OWNER, 'id': uuid.uuid4().hex,
                     'key': key, 'kind': kind, 'before': digest(before), 'after': digest(after),
                     'state': 'pending'}
        # Preserve every prior journal instead of overwriting its evidence.
        if pending:
            archive = self.root/('journal-'+pending['id']+'.json')
            if archive.exists(): raise Refused('journal_archive_conflict')
            os.rename(self.root/'operation.json', archive)
        atomic(self.root/'operation.json', operation)
        if after is None:
            archive = self.root/('retired-'+operation['id']+'.json')
            if archive.exists(): raise Refused('retirement_archive_conflict')
            os.rename(path, archive)
        else: atomic(path, after)
        operation['state'] = 'complete'; atomic(self.root/'operation.json', operation)
        return operation
    def reconcile(self):
        op = self.pending()
        if not op or op.get('owner') != OWNER or op.get('state') != 'pending': raise Refused('no_owned_pending_operation')
        path = self.path(op['key']); current = self.get(op['key']) if path.exists() else None
        if digest(current) == op['after']:
            if op['kind'] == 'remove':
                archived = private_read(self.root/('retired-'+op['id']+'.json'))
                if digest(archived) != op['before']: raise Refused('retired_ownership_conflict')
            op['state'] = 'complete'
        elif digest(current) == op['before']: op['state'] = 'aborted_without_retry'
        else: raise Refused('uncertain_local_outcome_conflict')
        atomic(self.root/'operation.json', op)
        return op
