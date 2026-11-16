#!/usr/bin/env python3
"""Read-only one-shot checks. No controller loop, restart or signal operations."""
import argparse,hashlib,json,os,stat,subprocess,sys
from pathlib import Path
from contracts import ROOT,NAMES,Refusal,topology,verify_table
PINS={'guard.py':'df53629a537e66fcbdf664076b9fa58de47d590e4a0f0d0128fd15f46f3088bd',
'security.py':'e7a92e7753e666a6f8cafd1b0292cec5e65f1431b09fc92ba10678c26e5ef8e2',
'vpn-owner-gate.sh':'e343e41632ece47165ecc6f2ae1f00779e92d77dd552329ef628807bab7ba523',
'vpn-startup-gate.py':'766879e875aa801c376adc44a65f02301dfd2c225acd29909c34da823b847ee7',
'Caddyfile':'bf5e40d2ccba8799f4b38f15336399fea7068f676150c2f7b18a1e07dc081a98',
'resolv.vpn.conf':'847d06f745d54e604791fa452b44a992026df81ba0dbdf58d81a8d02dd9d7ce2',
'vpn-post-rules.txt':'d48815495401014e7fcd43848af20259a13f1a59c3ac7882795c9fecace6ade4'}
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
    sys.path.insert(0,str(ROOT))
    from security import load_policy
    return load_policy(ROOT/'private/egress-policy.json')

def guard(policy,digest):
    verify_table(read_json(['nft','-j','list','table','inet','rivendell_iptv']),policy)
    if Path('/run/dispatcharr-guard/ready').read_text().strip()!=digest:raise Refusal('ready_marker_mismatch')

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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['inputs','guard','prestart','running']);a=p.parse_args()
    policy,digest=inputs()
    if a.mode!='inputs':guard(policy,digest)
    if a.mode in ['prestart','running']:workload(snapshot(),a.mode=='running')
    print(json.dumps({'check':a.mode,'result':'pass','mutations':0}))
if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('One-shot verification failed; values withheld. Inspect unit state before starting IPTV.')
