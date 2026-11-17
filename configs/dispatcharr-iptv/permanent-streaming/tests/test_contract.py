"""Compose-derived Docker fixtures; exact nftables semantics and privilege negatives."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
import yaml
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import contracts
import verify


def state():
    config=yaml.safe_load((HERE/'compose.yaml').read_text())
    cs={}
    for service,v in config['services'].items():
        is_owner=service=='iptv-vpn'
        mounts=[{'Destination':m['target'],'Source':m['source'],'Type':'bind','RW':not m.get('read_only',False)} for m in v['volumes']]
        for value in v.get('tmpfs',[]):mounts.append({'Destination':value.split(':')[0],'Type':'tmpfs','RW':True})
        cs[service]={'Id':service+'-ID','Name':'/'+v['container_name'],
          'Config':{'Image':v['image'],'User':v.get('user',''),'Entrypoint':v['entrypoint'],
                    'Labels':{'com.docker.compose.project':'rivendell-iptv','com.docker.compose.service':service},
                    'Env':[k+'='+str(value) for k,value in v.get('environment',{}).items()]},
          'HostConfig':{'NetworkMode':'rivendell-iptv-egress' if is_owner else 'container:iptv-vpn-ID',
             'PortBindings':{'9192/tcp':[{'HostIp':'10.10.20.30','HostPort':'9191'}]} if is_owner else {},
             'RestartPolicy':{'Name':v['restart']},'Privileged':v['privileged'], 'CgroupParent':'',
             'ReadonlyRootfs':v.get('read_only',False),'CapDrop':v.get('cap_drop',[]),'CapAdd':v.get('cap_add',[]),
             'SecurityOpt':v.get('security_opt',[]),'Memory':268435456,'MemorySwap':268435456,'NanoCpus':500000000,'PidsLimit':64},
          'State':{'Running':True,'StartedAt':'fixture','Health':{'Status':'healthy'}},'Mounts':mounts,
          'NetworkSettings':{'Networks':{'rivendell-iptv-egress':{'IPAddress':'172.16.70.2','NetworkID':'network'}} if is_owner else {}}}
    return {'containers':cs,'network':{'Name':'rivendell-iptv-egress','Id':'network','Driver':'bridge','EnableIPv6':False,
            'Options':{'com.docker.network.bridge.name':'br-iptv-eg'},'IPAM':{'Config':[{'Subnet':'172.16.70.0/24','Gateway':'172.16.70.1'}]},'Containers':{'iptv-vpn-ID':{}}},
            'netns':{k:'VPN' for k in cs},'host_netns':'HOST'}

class Contracts(unittest.TestCase):
    def test_full_four_service_contract(self):verify.workload(state(),True)
    def test_each_service_must_be_present(self):
        for key in contracts.NAMES:
            s=state();del s['containers'][key]
            with self.subTest(service=key),self.assertRaises((contracts.Refusal,KeyError)):verify.workload(s,True)
    def test_original_image_cannot_silently_replace_patched(self):
        s=state();s['containers']['dispatcharr']['Config']['Image']='ghcr.io/dispatcharr/dispatcharr:0.33.0'
        with self.assertRaises(contracts.Refusal):verify.workload(s)
    def test_privilege_port_network_and_resource_negatives(self):
        mutations=[lambda r:r['HostConfig'].update(Privileged=True),lambda r:r['HostConfig'].update(Memory=0),
                   lambda r:r['HostConfig'].update(ReadonlyRootfs=False),lambda r:r['HostConfig'].update(CapAdd=['NET_ADMIN']),
                   lambda r:r['HostConfig'].update(NetworkMode='host'),lambda r:r['HostConfig'].update(SecurityOpt=[]),
                   lambda r:r['HostConfig'].update(PortBindings={'19193/tcp':[]}),lambda r:r['Config'].update(User='0:0')]
        for mutate in mutations:
            s=state();mutate(s['containers']['relay'])
            with self.assertRaises(contracts.Refusal):verify.workload(s,True)
    def test_relay_readonly_sources_and_extra_mounts_rejected(self):
        for target in ['/opt/permanent','/etc/resolv.conf','/run/credentials/relay.json','/guard']:
            s=state();next(m for m in s['containers']['relay']['Mounts'] if m['Destination']==target)['RW']=True
            with self.assertRaises(contracts.Refusal):verify.workload(s)
        s=state();s['containers']['relay']['Mounts'].append({'Destination':'/host','Type':'bind','Source':'/','RW':True})
        with self.assertRaises(contracts.Refusal):verify.workload(s)
    def test_namespace_and_health_required(self):
        s=state();s['netns']['relay']='FOREIGN'
        with self.assertRaises(contracts.Refusal):verify.workload(s,True)
        s=state();s['containers']['relay']['State']['Health']['Status']='unhealthy'
        with self.assertRaises(contracts.Refusal):verify.workload(s,True)
    def test_exact_unchanged_firewall(self):
        self.assertEqual((HERE/'accepted-table.template.json').read_bytes(),(HERE.parent/'minimal-phase6b3d/accepted-table.template.json').read_bytes())
        p={'wg_endpoint_ipv4':'192.0.2.1','wg_endpoint_port':1637}
        table=contracts.expected_table(p);contracts.verify_table(table,p)
        table['nftables'].pop()
        with self.assertRaises(contracts.Refusal):contracts.verify_table(table,p)
    def test_gate_and_base_VPN_unchanged(self):
        base=yaml.safe_load((HERE.parent/'compose.proposed.yaml').read_text());candidate=yaml.safe_load((HERE/'compose.yaml').read_text())
        vpn=copy.deepcopy(candidate['services']['iptv-vpn']);vpn.pop('pull_policy');vpn['restart']='unless-stopped'
        self.assertEqual(vpn,base['services']['iptv-vpn'])
        self.assertEqual(candidate['networks'],base['networks'])
        self.assertEqual(candidate['services']['iptv-vpn']['ports'],base['services']['iptv-vpn']['ports'])
        unit=(HERE/'30-permanent-streaming.conf').read_text()
        self.assertIn('boot-admission-phase6b3k/admit.py',unit);self.assertNotIn('Timeout',unit)
        self.assertLess(unit.index('admit.py'),unit.index('guard.py apply'));self.assertLess(unit.index('guard.py apply'),unit.index('verify.py prestart'))
        self.assertEqual(hashlib.sha256((HERE.parent/'boot-admission-phase6b3k/admit.py').read_bytes()).hexdigest(),'649c5dcee6fff563bf7ee80d62d77d42e8c942e8a6a1205eeb4a2a570be2f917')
    def test_gateway_only_identity_header_adjustment(self):
        before=(HERE.parent/'Caddyfile').read_text();candidate=(HERE/'Caddyfile').read_text()
        restored='\n'.join(l for l in candidate.split('\n') if l.strip()!='header_up -X-Real-IP')
        self.assertEqual(restored,before);self.assertEqual(candidate.count('header_up -X-Real-IP'),2)
        self.assertNotIn('127.0.0.1:19191',candidate)

if __name__=='__main__':unittest.main()
