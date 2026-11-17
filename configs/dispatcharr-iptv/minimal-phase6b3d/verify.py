#!/usr/bin/env python3
"""Read-only one-shot checks. No controller loop, restart or signal operations."""
import argparse,hashlib,json,os,stat,subprocess,sys
from pathlib import Path
from contracts import ROOT,NAMES,Refusal,topology,verify_table
PINS={'guard.py':'d25808d50ff14dd1f195397d34b1ead33c3ed8fa5b6aebc5a6c4bf2c120e91b0',
'security.py':'e7a92e7753e666a6f8cafd1b0292cec5e65f1431b09fc92ba10678c26e5ef8e2',
'vpn-owner-gate.sh':'e343e41632ece47165ecc6f2ae1f00779e92d77dd552329ef628807bab7ba523',
'vpn-startup-gate.py':'766879e875aa801c376adc44a65f02301dfd2c225acd29909c34da823b847ee7',
'Caddyfile':'bf5e40d2ccba8799f4b38f15336399fea7068f676150c2f7b18a1e07dc081a98',
'resolv.vpn.conf':'847d06f745d54e604791fa452b44a992026df81ba0dbdf58d81a8d02dd9d7ce2',
'vpn-post-rules.txt':'d48815495401014e7fcd43848af20259a13f1a59c3ac7882795c9fecace6ade4'}
EXTRA_PINS={'/etc/systemd/system/dispatcharr-egress-guard.service.d/20-trusted-readiness.conf': '392994ee3a0eec4b87127b13aa1efb51ce058fd135fbbed52f17d30fde2dbefc', '/etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf': '578e03101e64c14da217e3d77f5bed9e0dbfbab9dad24b3f077c6b3891aed023', '/docker/dispatcharr-iptv/minimal-phase6b3d/cleanup.py': 'bb1f7166cb6adeec352abdd2eccb21365c8ae61ff7892a0da028e4c1fee71432'}
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
