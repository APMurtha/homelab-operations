"""Offline only. No Docker, netlink, subprocess, network, secrets or live data."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('candidate', HERE / 'controller.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
POLICY = {'wg_endpoint_ipv4': '192.0.2.1', 'wg_endpoint_port': 1637}

def state():
    net = {'Id': 'net-A', 'Name': 'rivendell-iptv-egress', 'Driver': 'bridge',
           'EnableIPv6': False, 'IPAM': {'Config': [{'Subnet': '172.16.70.0/24', 'Gateway': '172.16.70.1'}]},
           'Options': {'com.docker.network.bridge.name': 'br-iptv-eg'}, 'Containers': {}}
    cs = {}
    for service, name in c.NAMES.items():
        owner = service == 'iptv-vpn'
        cs[service] = {'Name': '/' + name, 'Id': service + '-A',
          'Config': {'Labels': {'com.docker.compose.project': 'rivendell-iptv', 'com.docker.compose.service': service}},
          'HostConfig': {'RestartPolicy': {'Name': 'no'}, 'NetworkMode': 'rivendell-iptv-egress' if owner else 'container:iptv-vpn-A',
                        'PortBindings': {'9192/tcp': [{'HostIp': '10.10.20.30', 'HostPort': '9191'}]} if owner else {}},
          'NetworkSettings': {'Networks': {'rivendell-iptv-egress': {'IPAddress': '', 'NetworkID': 'net-A', 'IPAMConfig': {'IPv4Address': '172.16.70.2'}}} if owner else {}},
          'State': {'Running': False, 'StartedAt': 'never', 'Health': {'Status': 'healthy'}}}
    cs['iptv-vpn']['Config']['Env'] = ['FIREWALL=on', 'VPN_SERVICE_PROVIDER=custom', 'VPN_TYPE=wireguard', 'DNS_KEEP_NAMESERVER=off', 'DNS_UPSTREAM_RESOLVER_TYPE=dot']
    for service, mounts in {'dispatcharr': {'/etc/resolv.conf': 'resolv.vpn.conf'}, 'iptv-vpn': {'/gluetun/wireguard/wg0.conf': 'private/wg0.conf', '/iptables/post-rules.txt': 'vpn-post-rules.txt'}, 'gateway': {'/etc/caddy/Caddyfile': 'Caddyfile'}}.items():
        cs[service]['Mounts'] = [{'Type': 'bind', 'Destination': d, 'Source': str(c.ROOT/p), 'RW': False} for d, p in mounts.items()]
    return {'network': net, 'containers': cs, 'netns': {}, 'host_netns': 'host'}

class Fake:
    def __init__(self):
        self.s = state(); self.live = None; self.ready = False; self.fault = False
        self.published = False; self.starts = []; self.install_fault = None
        self.stop_ok = True; self.docker = True; self.other_media = ('unchanged',)
    def revoke(self): self.ready = False; self.published = False
    def install_guard(self):
        if self.install_fault == 'fail': raise c.Refusal('fixture_install_failed')
        self.live = c.expected_table(POLICY)
        if self.install_fault == 'partial': self.live['nftables'].pop()
        self.ready = True
    def verify_guard(self):
        if self.live is None or not self.ready: raise c.Refusal('fixture_missing_guard')
        c.verify_table(self.live, POLICY)
    def snapshot(self):
        if not self.docker: raise c.Refusal('fixture_daemon_unavailable')
        return copy.deepcopy(self.s)
    def latched(self): return self.fault
    def latch(self): self.fault = True
    def publish(self): self.published = True
    def start(self, name):
        self.verify_guard(); self.starts.append(name)
        self.s['containers'][name]['State'].update(Running=True, StartedAt='started-' + str(len(self.starts)))
        self.s['netns'][name] = 'VPN-netns'
        if name == 'iptv-vpn': self.s['containers'][name]['NetworkSettings']['Networks']['rivendell-iptv-egress']['IPAddress'] = '172.16.70.2'
    def wait_healthy(self, name, seconds):
        self.verify_guard()
        if self.s['containers'][name]['State']['Health']['Status'] != 'healthy': raise c.Refusal('fixture_unhealthy')
    # Legacy fake backend remains a model; real enrollment has separate tests.
    def prepare_enrollment(self): pass
    def bind_enrollment(self, service): pass
    def verify_enrollment(self): pass
    def stop_project(self):
        if not self.docker or not self.stop_ok: return False
        for v in self.s['containers'].values(): v['State']['Running'] = False
        return True

class Tests(unittest.TestCase):
    def running(self):
        b = Fake(); x = c.Controller(b); x.bootstrap(); x.start(); return b, x
    def assert_closed(self, b):
        self.assertFalse(b.published)
        self.assertFalse(any(v['State']['Running'] for v in b.s['containers'].values()))
        self.assertEqual(b.other_media, ('unchanged',))
    def test_cold_boot_guard_precedes_docker_and_ordered_admission(self):
        b = Fake(); b.docker = False; x = c.Controller(b); x.bootstrap()
        self.assertEqual(b.starts, []); b.docker = True; x.start()
        self.assertEqual(b.starts, ['iptv-vpn', 'dispatcharr', 'gateway']); self.assertTrue(b.published)
    def test_stopped_owner_requires_static_IPAM_request(self):
        b = Fake(); x = c.Controller(b); x.bootstrap(); b.s['containers']['iptv-vpn']['NetworkSettings']['Networks']['rivendell-iptv-egress']['IPAMConfig'] = {}
        with self.assertRaises(c.Refusal): x.start()
        self.assert_closed(b)
    def test_missing_network(self):
        b = Fake(); x = c.Controller(b); x.bootstrap(); b.s['network'] = {}
        with self.assertRaises(c.Refusal): x.start()
        self.assert_closed(b)
    def test_changed_container_ip(self):
        b, x = self.running(); b.s['containers']['iptv-vpn']['NetworkSettings']['Networks']['rivendell-iptv-egress']['IPAddress'] = '172.16.70.3'
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)
    def test_missing_gluetun(self):
        b = Fake(); x = c.Controller(b); x.bootstrap(); del b.s['containers']['iptv-vpn']
        with self.assertRaises((c.Refusal, KeyError)): x.start()
        self.assert_closed(b)
    def test_nft_reload_missing_table_reconciles_and_latches(self):
        b, x = self.running(); b.live = None
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b); c.verify_table(b.live, POLICY)
    def test_controlled_daemon_restart_requires_fresh_admission(self):
        b, x = self.running(); b.revoke(); b.stop_project(); b.docker = False
        self.assert_closed(b); b.docker = True; y = c.Controller(b); y.bootstrap(); y.start()
        self.assertTrue(b.published)
    def test_daemon_unavailable_does_not_claim_containment(self):
        b, x = self.running(); b.docker = False
        with self.assertRaisesRegex(c.Refusal, 'containment_uncertain'): x.check()
        self.assertFalse(b.published); self.assertTrue(b.fault)
    def test_install_failure(self):
        b = Fake(); b.install_fault = 'fail'; x = c.Controller(b)
        with self.assertRaises(c.Refusal): x.bootstrap()
        self.assert_closed(b); self.assertFalse(b.ready)
    def test_partial_rule_install(self):
        b = Fake(); b.install_fault = 'partial'; x = c.Controller(b)
        with self.assertRaises(c.Refusal): x.bootstrap()
        self.assert_closed(b); self.assertFalse(b.ready)
    def test_wrong_namespace(self):
        b, x = self.running(); b.s['netns']['dispatcharr'] = 'host'
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)
    def test_duplicate_execution_uses_actual_flock(self):
        with tempfile.TemporaryDirectory() as d:
            a = c.take_lock(Path(d)/'lock')
            try:
                with self.assertRaisesRegex(c.Refusal, 'duplicate'): c.take_lock(Path(d)/'lock')
            finally: a.close()
    def test_failed_install_rollback_preserves_prior_guard_and_neighbors(self):
        b = Fake(); b.install_guard(); before = copy.deepcopy(b.live); b.install_fault = 'fail'
        with self.assertRaises(c.Refusal): c.Controller(b).bootstrap()
        self.assertEqual(b.live, before); self.assert_closed(b)
    def test_semantic_rule_tamper_not_hidden_by_rule_count(self):
        b, x = self.running()
        rule = next(v['rule'] for v in b.live['nftables'] if 'rule' in v)
        rule['expr'][-1] = {'accept': None}
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)
    def test_backend_metadata_counters_ignored_but_expressions_retained(self):
        live = c.expected_table(POLICY)
        for v in live['nftables']:
            for obj in v.values():
                if isinstance(obj, dict): obj['handle'] = 999
        c.verify_table(live, POLICY)
    def test_network_recreated_under_same_contract_still_latches(self):
        b, x = self.running(); b.s['network']['Id'] = 'net-B'
        b.s['containers']['iptv-vpn']['NetworkSettings']['Networks']['rivendell-iptv-egress']['NetworkID'] = 'net-B'
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)
    def test_bridge_name_drift(self):
        b, x = self.running(); b.s['network']['Options']['com.docker.network.bridge.name'] = 'br-other'
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)
    def test_vpn_restarts_identity_fingerprint_changes(self):
        b, x = self.running(); b.s['containers']['iptv-vpn']['State']['StartedAt'] = 'restarted'
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)
    def test_vpn_unhealthy(self):
        b, x = self.running(); b.s['containers']['iptv-vpn']['State']['Health']['Status'] = 'unhealthy'
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)
    def test_engine_autostart_must_be_removed_before_candidate(self):
        b = Fake(); x = c.Controller(b); x.bootstrap(); b.s['containers']['dispatcharr']['HostConfig']['RestartPolicy']['Name'] = 'unless-stopped'
        with self.assertRaisesRegex(c.Refusal, 'autostart'): x.start()
        self.assert_closed(b)
    def test_wrong_peer_or_lan_permission_rejected(self):
        b = Fake(); b.install_guard()
        next(v['set'] for v in b.live['nftables'] if v.get('set',{}).get('name')=='local_reply4')['elem'].append('0.0.0.0/0')
        with self.assertRaises(c.Refusal): b.verify_guard()
    def test_docker_DNS_mount_replacement_is_rejected(self):
        b, x = self.running(); b.s['containers']['dispatcharr']['Mounts'] = []
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)
    def test_vpn_killswitch_disable_is_rejected(self):
        b, x = self.running(); b.s['containers']['iptv-vpn']['Config']['Env'][0] = 'FIREWALL=off'
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)
    def test_unexpected_gateway_exposure_is_rejected(self):
        b, x = self.running(); b.s['containers']['iptv-vpn']['HostConfig']['PortBindings']['9192/tcp'][0]['HostIp'] = '0.0.0.0'
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)
    def test_no_automatic_retry_after_latched_fault(self):
        b, x = self.running(); b.live = None
        with self.assertRaises(c.Refusal): x.check()
        with self.assertRaisesRegex(c.Refusal, 'latched'): x.start()
        self.assert_closed(b)
    def test_polling_cannot_prove_zero_gap_after_out_of_band_flush(self):
        b, x = self.running(); b.live = None
        # Explicit counterexample BEFORE check runs: workloads are still running.
        self.assertTrue(b.published)
        self.assertTrue(b.s['containers']['dispatcharr']['State']['Running'])
        # This is a documented hard-guarantee gap, not a claimed fail-closed proof.
        with self.assertRaises(c.Refusal): x.check()
        self.assert_closed(b)

if __name__ == '__main__': unittest.main()
