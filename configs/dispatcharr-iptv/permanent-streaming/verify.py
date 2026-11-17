"""Candidate one-shot verifier: retain exact nftables contract and add relay checks."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from urllib.parse import urlsplit
from contracts import ROOT, NAMES, Refusal, topology, verify_table

HERE = Path(__file__).resolve().parent
PATCHED = 'local/dispatcharr-readiness@sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21'
IMAGES = {'dispatcharr': PATCHED, 'relay': PATCHED,
          'iptv-vpn':'qmcgaw/gluetun@sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209',
          'gateway':'caddy:2-alpine@sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9'}


def command(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if p.returncode: raise Refusal('read_only_backend_failed')
    return p.stdout


def file_pin(path, expected):
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
        raise Refusal('unsafe_source_permissions')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise Refusal('accepted_source_changed')


def inputs():
    for name, expected in json.loads((HERE/'base-input-pins.json').read_text()).items():
        file_pin(ROOT/name, expected)
    for name, expected in json.loads((HERE/'manifest.json').read_text())['files'].items():
        if '..' in Path(name).parts or Path(name).is_absolute(): raise Refusal('manifest_path')
        file_pin(HERE/name, expected)
    for f, expected in [('/etc/systemd/system/dispatcharr-stack.service','30e7f5e64b7a6ce3f8ec3cf80572d74bb2dd1ed67083929276cf55fbb65c357e'),
        ('/etc/systemd/system/dispatcharr-egress-guard.service','bde5207014fa24781d8cd1275a54dac056684299e498f4773fca2ed2e98cc174'),
        ('/etc/systemd/system/docker.service.d/50-dispatcharr-order.conf','c9beb54d2b2e6285013355f3a80dd6677ff7723d10e835f45c499f39fb9e581b'),
        ('/etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf','72643075862dfeb6ce968997edd19c9fbff30eea025d7ea74eb6691d372f8ceb')]:
        file_pin(Path(f), expected)
    file_pin(Path('/etc/systemd/system/dispatcharr-stack.service.d/30-permanent-streaming.conf'),
             json.loads((HERE/'manifest.json').read_text())['files']['30-permanent-streaming.conf'])
    # Existing base guard still verifies original files. The candidate lives beside
    # them, so guard-before-Docker behavior does not depend on a changed base pin.
    sys.path.insert(0,str(ROOT))
    from security import load_policy
    policy, digest = load_policy(ROOT/'private/egress-policy.json')
    from files import private_json
    for name in ['permanent-relay.json','permanent-registration.json']:
        path=ROOT/'private'/name
        if path.lstat().st_uid != 1000 or stat.S_IMODE(path.lstat().st_mode) != 0o400:
            raise Refusal('private_input_permissions')
    relay = private_json(ROOT/'private/permanent-relay.json')
    if set(relay) != {'source','ready_file','ready_hash','manifest_deadline_seconds','segment_deadline_seconds'}:
        raise Refusal('relay_configuration_fields')
    from hls_relay import HOST
    u=urlsplit(relay['source'])
    if u.scheme!='https' or u.netloc!=HOST or u.query or u.fragment or not u.path.endswith('.m3u8') or '%' in u.path or '\\' in u.path or '//' in u.path or any(p in ['.','..'] for p in u.path.split('/')):
        raise Refusal('relay_source_scope')
    if relay['ready_file']!='/guard/ready' or relay['ready_hash']!=digest or relay['manifest_deadline_seconds']!=12 or relay['segment_deadline_seconds']!=12:
        raise Refusal('relay_policy_changed')
    registration=private_json(ROOT/'private/permanent-registration.json')
    if set(registration) != {'username','password','expected_network_access_sha256','jellyfin_peer_ipv4'}:
        raise Refusal('registration_configuration_fields')
    if not registration['username'] or not registration['password'] or not re.fullmatch('[a-f0-9]{64}',registration['expected_network_access_sha256']):
        raise Refusal('registration_configuration_invalid')
    peers=registration['jellyfin_peer_ipv4']
    if not isinstance(peers,list) or not 1<=len(peers)<=8 or len(set(peers))!=len(peers):raise Refusal('Jellyfin_peers_invalid')
    for peer in peers:
        if ipaddress.ip_address(peer).version!=4:raise Refusal('Jellyfin_peers_invalid')
    return policy,digest


def guard(policy,digest):
    verify_table(json.loads(command(['nft','-j','list','table','inet','rivendell_iptv'])),policy)
    if Path('/run/dispatcharr-guard/ready').read_text().strip()!=digest:raise Refusal('ready_marker_mismatch')


def workload(state,running=False):
    topology(state,running)
    for service,c in state['containers'].items():
        if c['Config'].get('Image')!=IMAGES[service]:raise Refusal('accepted_image_changed')
        if c['HostConfig'].get('CgroupParent',''):raise Refusal('retired_cgroup_override_present')
        if running and c['State'].get('Health',{}).get('Status')!='healthy':raise Refusal('component_unhealthy')


def snapshot():
    cs=json.loads(command(['docker','inspect',*NAMES.values()]))
    project=command(['docker','ps','-aq','--filter','label=com.docker.compose.project=rivendell-iptv','--no-trunc']).split()
    if set(project)!={c['Id'] for c in cs}:raise Refusal('unexpected_project_container')
    containers={c['Config']['Labels']['com.docker.compose.service']:c for c in cs}
    net=json.loads(command(['docker','network','inspect','rivendell-iptv-egress']))[0]
    ns={s:os.readlink('/proc/'+str(c['State']['Pid'])+'/ns/net') for s,c in containers.items() if c['State']['Running']}
    return {'containers':containers,'network':net,'netns':ns,'host_netns':os.readlink('/proc/1/ns/net')}


def vpn_running():
    run=lambda args:command(['docker','exec','rivendell-iptv-vpn',*args])
    routes=run(['ip','route','show','table','all'])
    if not any('default' in r and 'tun0' in r for r in routes.splitlines()):raise Refusal('VPN_default_route_missing')
    output=run(['iptables','-S','OUTPUT'])
    if '-P OUTPUT DROP' not in output or '127.0.0.11/32' not in output or 'REJECT' not in output:raise Refusal('VPN_killswitch_changed')
    if run(['cat','/proc/sys/net/ipv6/conf/all/disable_ipv6']).strip()!='1':raise Refusal('IPv6_not_disabled')
    for name in ['dispatcharr','rivendell-iptv-relay']:
        lines=command(['docker','exec',name,'cat','/etc/resolv.conf']).splitlines()
        if [r.split()[1] for r in lines if r.startswith('nameserver ')]!=['127.0.0.1']:raise Refusal('resolver_changed')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['inputs','prestart','running']);a=p.parse_args()
    try:
        policy,digest=inputs()
        if a.mode!='inputs':guard(policy,digest);workload(snapshot(),a.mode=='running')
        if a.mode=='running':
            vpn_running()
            command(['docker','exec','--user','1000:1000','dispatcharr','python','-B','/opt/permanent/verify_binding.py'])
        print(json.dumps({'check':a.mode,'result':'pass','mutations':0}))
    except Exception:raise SystemExit('Permanent IPTV verification refused; values withheld.')
