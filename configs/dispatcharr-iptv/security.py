"""Shared strict policy parsing; no network requests and no credential logging."""
import base64
import configparser
import hashlib
import ipaddress
import json
from pathlib import Path

TABLE = 'rivendell_iptv'
BRIDGE = 'br-iptv-eg'
VPN_IP = '172.16.70.2'
SUBNET = '172.16.70.0/24'
LOCAL_REPLIES = ['10.10.20.30/32', '10.10.30.0/24', '172.20.0.0/16']


def read_peer(path):
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.read_string(Path(path).read_text())
    if set(parser.sections()) != {'Interface', 'Peer'}:
        raise ValueError('One Interface and one Peer section are required.')
    interface, peer = parser['Interface'], parser['Peer']
    if not interface.get('PrivateKey') or not peer.get('PresharedKey'):
        raise ValueError('A separate complete AirVPN device configuration is required.')
    for value in (interface.get('PrivateKey'), peer.get('PublicKey'), peer.get('PresharedKey')):
        if not value or len(base64.b64decode(value, validate=True)) != 32:
            raise ValueError('WireGuard keys must be complete 32-byte base64 values.')
    addresses = [ipaddress.ip_interface(x.strip()) for x in interface.get('Address', '').split(',')]
    if not addresses or any(x.version != 4 for x in addresses):
        raise ValueError('Only IPv4 WireGuard addresses are allowed for this pilot.')
    if peer.get('AllowedIPs', '').replace(' ', '') != '0.0.0.0/0':
        raise ValueError('AllowedIPs must be exactly 0.0.0.0/0 for this pilot.')
    host, port = peer.get('Endpoint', '').rsplit(':', 1)
    address = ipaddress.IPv4Address(host)
    if not address.is_global or not 1 <= int(port) <= 65535:
        raise ValueError('Endpoint must be a public literal IPv4 address and valid UDP port.')
    if any(x.network.overlaps(ipaddress.ip_network(SUBNET)) for x in addresses):
        raise ValueError('WireGuard and Docker networks overlap.')
    return str(address), int(port)


def load_policy(path):
    raw = Path(path).read_bytes()
    d = json.loads(raw)
    if not isinstance(d, dict) or set(d) != {'schema', 'bridge', 'subnet', 'vpn_ip', 'wg_endpoint_ipv4', 'wg_endpoint_port', 'local_reply_cidrs'}:
        raise ValueError('Unexpected policy fields.')
    if (d['schema'], d['bridge'], d['subnet'], d['vpn_ip']) != (1, BRIDGE, SUBNET, VPN_IP):
        raise ValueError('Policy differs from the reviewed bridge/address contract.')
    ipaddress.IPv4Address(d['wg_endpoint_ipv4'])
    if isinstance(d['wg_endpoint_port'], bool) or not isinstance(d['wg_endpoint_port'], int) or not 1 <= d['wg_endpoint_port'] <= 65535:
        raise ValueError('Invalid peer port.')
    if d['local_reply_cidrs'] != LOCAL_REPLIES:
        raise ValueError('LAN return scope changed; review it before generating a new contract.')
    return d, hashlib.sha256(raw).hexdigest()


def render_rules(d):
    peer = str(ipaddress.IPv4Address(d['wg_endpoint_ipv4']))
    port = d['wg_endpoint_port']
    local = ', '.join(LOCAL_REPLIES)
    return f'''table inet {TABLE} {{
  set wg_peer4 {{ type ipv4_addr . inet_service; elements = {{ {peer} . {port} }}; }}
  set local_reply4 {{ type ipv4_addr; flags interval; elements = {{ {local} }}; }}
  chain forward {{
    type filter hook forward priority -10; policy accept;
    ip saddr {SUBNET} iifname != "{BRIDGE}" counter drop
    iifname "{BRIDGE}" meta nfproto ipv6 counter drop
    iifname "{BRIDGE}" ip saddr != {VPN_IP} counter drop
    iifname "{BRIDGE}" ip daddr . udp dport @wg_peer4 counter accept
    iifname "{BRIDGE}" ip daddr @local_reply4 ct state established,related counter accept
    iifname "{BRIDGE}" counter drop
    oifname "{BRIDGE}" meta nfproto ipv6 counter drop
    oifname "{BRIDGE}" ip daddr {VPN_IP} ip saddr @local_reply4 tcp dport 9192 counter accept
    oifname "{BRIDGE}" ct state established,related counter accept
    oifname "{BRIDGE}" counter drop
  }}
  chain input {{
    type filter hook input priority -10; policy accept;
    ip saddr {SUBNET} iifname != "{BRIDGE}" counter drop
    iifname "{BRIDGE}" meta nfproto ipv6 counter drop
    iifname "{BRIDGE}" ct state established,related counter accept
    iifname "{BRIDGE}" counter drop
  }}
  chain output {{
    type filter hook output priority -10; policy accept;
    ip daddr {VPN_IP} tcp dport 9192 counter accept
    ip daddr {VPN_IP} ct state established,related counter accept
    ip daddr {VPN_IP} counter drop
  }}
}}
'''
