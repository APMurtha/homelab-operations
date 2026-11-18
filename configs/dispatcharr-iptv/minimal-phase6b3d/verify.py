#!/usr/bin/env python3
"""Read-only one-shot checks. No controller loop, restart or signal operations."""
import argparse,hashlib,json,os,stat,subprocess,sys
from pathlib import Path
from contracts import ROOT,NAMES,Refusal,topology,verify_table
PINS={'guard.py': '147cb62b0fa19e90d391b5583bde7e342f71bfca748e068f730ba3dd56e91f8a', 'security.py': 'e7a92e7753e666a6f8cafd1b0292cec5e65f1431b09fc92ba10678c26e5ef8e2', 'vpn-owner-gate.sh': 'e343e41632ece47165ecc6f2ae1f00779e92d77dd552329ef628807bab7ba523', 'vpn-startup-gate.py': '766879e875aa801c376adc44a65f02301dfd2c225acd29909c34da823b847ee7', 'Caddyfile': 'bf5e40d2ccba8799f4b38f15336399fea7068f676150c2f7b18a1e07dc081a98', 'resolv.vpn.conf': '847d06f745d54e604791fa452b44a992026df81ba0dbdf58d81a8d02dd9d7ce2', 'vpn-post-rules.txt': 'd48815495401014e7fcd43848af20259a13f1a59c3ac7882795c9fecace6ade4'}
EXTRA_PINS={'/etc/systemd/system/dispatcharr-egress-guard.service.d/20-trusted-readiness.conf': '37226a0e1d77a14d2f0c0e16254f0f6699e7e0c543afcebfd24630cde0249a34', '/etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf': 'e639eab69f150f9f9ab833def8353c38f33bdbf00e3cb23e5ad0dfc595edd964', '/docker/dispatcharr-iptv/minimal-phase6b3d/cleanup.py': '0007aafcc865746e2186e3d491a9c913958985453e8ea66f7523e690dc5406f2', '/docker/dispatcharr-iptv/provider_control.py': '33fd56fc7a461ad9e416ba10f0bbdea175b2382e461e192bcb213a77e5844d24', '/docker/dispatcharr-iptv/native-provider-hardening/publish_policy.py': '0e0a36dffeed12b092e97025ce0ec857dd1b470009321d677b3fd25796baa4e8', '/docker/dispatcharr-iptv/native-provider-hardening/output-hashes.json': 'dc861e4615419508a43c16613f36bad1eca549980814fbbc51efb726566a4dd4', '/docker/dispatcharr-iptv/native-provider-hardening/release-contract.json': '891b115e0ad7b6e154aab9f1967fca6009e60e8ae6ba6996b14a980ef9573af1', '/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_dns.py': '28c9564793e1285eb72bb9d91ab24a85ccc3ca2f3db80398445d380b53d9af3a', '/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_policy.py': '2691cc3eeed26f13869d7cdacc671f0e2eebcd46e54e944279ffe78dd0b82639', '/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_readiness.py': '5f137b756a1a988d4641ccd8a13b6bd4e13849bbdb2539c22026c88f4d8cf698', '/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_security.py': '8d3049e4dfb471f62a66c13a17e94da04e6cff3050e07121208327071c4ce004', '/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_security_view.py': 'b3e77ccd704251b85cccdc8df9966ecc8d748a4a1542780512746886be31374b', '/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_transport.py': '4032865e09c82b5a755af99ef2a8b62e88aca46e346321565dd0af783cec0d39'}
IMAGES={'iptv-vpn':'qmcgaw/gluetun@sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209',
'dispatcharr':'ghcr.io/dispatcharr/dispatcharr:0.33.0@sha256:96bc548978c68e684677da7895692eeeefb7f0b2edfa38311dac2b702c61d236',
'gateway':'caddy:2-alpine@sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9'}

def read_json(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=25)
    if p.returncode:raise Refusal('read_only_backend_failed')
    return json.loads(p.stdout)

def inputs():
    for name,digest in PINS.items():
        p=ROOT/name;st=p.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_mode&0o022 or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise Refusal('accepted_source_changed')
    for name,digest in EXTRA_PINS.items():
        p=__import__('pathlib').Path(name);st=p.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o644 or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise Refusal('trusted_lifecycle_source_changed')
    sys.path.insert(0,str(ROOT))
    from security import load_policy
    return load_policy(ROOT/'private/egress-policy.json')

def kernel(policy,digest):
    verify_table(read_json(['nft','-j','list','table','inet','rivendell_iptv']),policy)
    try:
        fd=os.open('/run/dispatcharr-guard/ready',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd) as f:
            st=os.fstat(f.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o644 or st.st_nlink!=1 or f.read(66)!=digest+'\n':raise Refusal('ready_marker_mismatch')
    except OSError:raise Refusal('ready_marker_unavailable') from None

def guard(policy,digest):
    kernel(policy,digest)
    sys.path.insert(0,str(ROOT))
    import guard as trusted_guard
    trusted_guard.Publisher().coherence(ROOT/'private/egress-policy.json')


def workload(state,running=False):
    topology(state,running)
    for s,c in state['containers'].items():
        if c['Config'].get('Image')!=IMAGES[s]:raise Refusal('accepted_image_changed')
        if c['HostConfig'].get('CgroupParent',''):raise Refusal('retired_cgroup_override_present')

def snapshot():
    cs=read_json(['docker','inspect',*NAMES.values()])
    containers={c['Config']['Labels']['com.docker.compose.service']:c for c in cs}
    net=read_json(['docker','network','inspect','rivendell-iptv-egress'])[0]
    ns={s:os.readlink('/proc/'+str(c['State']['Pid'])+'/ns/net') for s,c in containers.items() if c['State']['Running']}
    return {'containers':containers,'network':net,'netns':ns,'host_netns':os.readlink('/proc/1/ns/net')}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['inputs','kernel','guard','prestart','running']);a=p.parse_args()
    policy,digest=inputs()
    if a.mode=='kernel':kernel(policy,digest)
    elif a.mode!='inputs':guard(policy,digest)
    if a.mode in ['prestart','running']:workload(snapshot(),a.mode=='running')
    print(json.dumps({'check':a.mode,'result':'pass','mutations':0}))
if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('One-shot verification failed; values withheld. Inspect unit state before starting IPTV.')
