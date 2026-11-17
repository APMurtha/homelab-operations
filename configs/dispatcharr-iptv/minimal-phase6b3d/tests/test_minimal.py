"""Offline policy/unit fixtures only. No Docker, nft, services, packets or signals."""
import copy,importlib.util,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import contracts as c
import verify as v
# Reuse the historical topology fixtures without importing any enrollment helper.
spec=importlib.util.spec_from_file_location('oldfixtures',HERE.parent/'persistence-phase6b3/tests/test_controller.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
POLICY={'wg_endpoint_ipv4':'192.0.2.1','wg_endpoint_port':1637}

def state(running=False):
    s=f.state()
    for name,item in s['containers'].items():
        item['Config']['Image']=v.IMAGES[name];item['HostConfig']['CgroupParent']=''
        if running:item['State']['Running']=True;s['netns'][name]='vpn'
    if running:s['containers']['iptv-vpn']['NetworkSettings']['Networks']['rivendell-iptv-egress']['IPAddress']='172.16.70.2'
    return s

def startup(guard_ok=True,network=True,vpn=True,partial=False):
    # Explicit job/Compose model, NOT a running systemd or Docker test.
    events=['guard-before-docker'];other_docker=True
    if not guard_ok:return events+['guard-failed','workload-blocked'],other_docker
    events+=['docker-active','guard-reapplied','guard-verified']
    if not network or not vpn:return events+['preflight-failed','scoped-stop'],other_docker
    events+=['vpn-start','vpn-health','app-start','app-health','gateway-start']
    return events+(['health-failed','scoped-stop'] if partial else ['postcheck','active']),other_docker

class Tests(unittest.TestCase):
    def test_startup_order_and_no_background_supervisor(self):
        e,other=startup();self.assertLess(e.index('guard-verified'),e.index('app-start'));self.assertTrue(other)
        unit=(HERE/'units/dispatcharr-stack.service').read_text();self.assertIn('Type=oneshot',unit);self.assertIn('Restart=no',unit);self.assertNotIn('controller.py',unit)
    def test_guard_failure_blocks_only_IPTV(self):
        e,other=startup(guard_ok=False);self.assertNotIn('app-start',e);self.assertTrue(other)
        drop=(HERE/'units/docker.service.50-dispatcharr-order.conf').read_text();self.assertIn('Wants=',drop);self.assertNotIn('Requires=',drop)
    def test_missing_network_refuses(self):
        s=state();s['network']={}
        with self.assertRaises(c.Refusal):v.workload(s)
        self.assertNotIn('app-start',startup(network=False)[0])
    def test_missing_Gluetun_refuses(self):
        s=state();del s['containers']['iptv-vpn']
        with self.assertRaises((c.Refusal,KeyError)):v.workload(s)
        self.assertNotIn('app-start',startup(vpn=False)[0])
    def test_container_restart_preserves_namespace_contract(self):
        s=state(True);v.workload(s,True);s['containers']['dispatcharr']['State']['StartedAt']='restart';v.workload(s,True)
        s['netns']['dispatcharr']='wrong'
        with self.assertRaises(c.Refusal):v.workload(s,True)
    def test_Docker_restart_reapplies_before_admission(self):
        unit=(HERE/'units/dispatcharr-stack.service').read_text();self.assertIn('PartOf=docker.service',unit);self.assertIn('BindsTo=docker.service',unit)
        self.assertLess(unit.index('guard.py apply'),unit.index(' up --detach'))
        s=state()
        for c0 in s['containers'].values():c0['HostConfig']['RestartPolicy']['Name']='unless-stopped'
        with self.assertRaises(c.Refusal):v.workload(s)
    def test_duplicate_guard_semantic_validation(self):
        expected=c.expected_table(POLICY)
        for _ in range(2):c.verify_table(copy.deepcopy(expected),POLICY)
        damaged=copy.deepcopy(expected);damaged['nftables'].pop()
        with self.assertRaises(c.Refusal):c.verify_table(damaged,POLICY)
    def test_rollback_and_partial_failure_never_delete_rules_or_data(self):
        e,_=startup(partial=True);self.assertEqual(e[-1],'scoped-stop')
        unit=(HERE/'units/dispatcharr-stack.service').read_text();self.assertIn('ExecStopPost=',unit);self.assertIn('stop --timeout 60 gateway dispatcharr iptv-vpn',unit)
        guard=(HERE/'units/dispatcharr-egress-guard.service').read_text();self.assertNotIn('ExecStop=',guard)
        self.assertNotIn('down ',unit);self.assertNotIn('flush ruleset',unit)
    def test_retired_cgroup_and_wrong_image_rejected(self):
        s=state();s['containers']['dispatcharr']['HostConfig']['CgroupParent']='rivendelliptv.slice'
        with self.assertRaises(c.Refusal):v.workload(s)
        s=state();s['containers']['dispatcharr']['Config']['Image']='changed'
        with self.assertRaises(c.Refusal):v.workload(s)
    def test_unexpected_ports_or_namespace_or_network_recreation_contract(self):
        s=state();s['network']['Id']='new';s['containers']['iptv-vpn']['NetworkSettings']['Networks']['rivendell-iptv-egress']['NetworkID']='new';v.workload(s)
        s['network']['Options']['com.docker.network.bridge.name']='different'
        with self.assertRaises(c.Refusal):v.workload(s)
    def test_guard_marker_failure_blocks_preflight(self):
        expected=c.expected_table(POLICY)
        with patch.object(v,'read_json',return_value=expected),patch.object(c,'expected_table',return_value=expected),patch('pathlib.Path.read_text',return_value='stale'):
            with self.assertRaises(c.Refusal):v.guard(POLICY,'expected')
    def test_no_active_security_policy_changes(self):
        self.assertEqual((HERE/'accepted-table.template.json').read_bytes(),(HERE.parent/'persistence-phase6b3/accepted-table.template.json').read_bytes())
        self.assertEqual(v.PINS['guard.py'],'d25808d50ff14dd1f195397d34b1ead33c3ed8fa5b6aebc5a6c4bf2c120e91b0')

if __name__=='__main__':unittest.main()
