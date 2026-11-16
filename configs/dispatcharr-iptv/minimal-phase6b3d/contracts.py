"""Pure one-shot contracts extracted from historical validation; no controller.
No mutations, supervision, enrollment, cgroups, polling or process termination.
"""
import json
from pathlib import Path
ROOT = Path('/docker/dispatcharr-iptv')
HERE = Path(__file__).resolve().parent
NAMES = {'iptv-vpn': 'rivendell-iptv-vpn', 'dispatcharr': 'dispatcharr', 'gateway': 'rivendell-iptv-gateway'}
class Refusal(RuntimeError): pass

def canonical(value):
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()
                if k not in ('handle', 'packets', 'bytes', 'metainfo')}
    if isinstance(value, list):
        return [canonical(v) for v in value if not (isinstance(v, dict) and 'metainfo' in v)]
    return value

def expected_table(policy):
    def fill(x):
        if isinstance(x, dict): return {k: fill(v) for k, v in x.items()}
        if isinstance(x, list): return [fill(v) for v in x]
        if x == '__WG_ENDPOINT__': return policy['wg_endpoint_ipv4']
        if x == '__WG_PORT__': return policy['wg_endpoint_port']
        return x
    return fill(json.loads((HERE / 'accepted-table.template.json').read_text()))

def verify_table(live, policy):
    if canonical(live) != canonical(expected_table(policy)):
        raise Refusal('guard_semantic_mismatch')

def topology(state, require_running=False):
    n = state['network']
    if (n.get('Name'), n.get('Driver'), n.get('EnableIPv6')) != ('rivendell-iptv-egress', 'bridge', False):
        raise Refusal('network_contract_changed')
    if n.get('Options', {}).get('com.docker.network.bridge.name') != 'br-iptv-eg':
        raise Refusal('bridge_contract_changed')
    configs = n.get('IPAM', {}).get('Config', [])
    if configs != [{'Subnet': '172.16.70.0/24', 'Gateway': '172.16.70.1'}]:
        raise Refusal('subnet_contract_changed')
    containers = state['containers']; owner = containers['iptv-vpn']
    for service, c in containers.items():
        if service not in NAMES or c['Name'].lstrip('/') != NAMES[service]:
            raise Refusal('container_scope_mismatch')
        labels = c['Config'].get('Labels', {})
        if labels.get('com.docker.compose.project') != 'rivendell-iptv' or labels.get('com.docker.compose.service') != service:
            raise Refusal('container_label_mismatch')
        if c['HostConfig']['RestartPolicy']['Name'] != 'no':
            raise Refusal('engine_autostart_not_disabled')
        if c['HostConfig'].get('Privileged'):
            raise Refusal('privileged_component')
        if require_running and not c['State']['Running']:
            raise Refusal('component_stopped')
    if set(containers) != set(NAMES): raise Refusal('missing_component')
    expected_ports = {'9192/tcp': [{'HostIp': '10.10.20.30', 'HostPort': '9191'}]}
    if owner['HostConfig'].get('PortBindings') != expected_ports:
        raise Refusal('published_ports_changed')
    if any(containers[k]['HostConfig'].get('PortBindings') for k in ['dispatcharr', 'gateway']):
        raise Refusal('unexpected_published_ports')
    env = dict(v.split('=', 1) for v in owner['Config'].get('Env', []) if '=' in v)
    for key, value in {'FIREWALL': 'on', 'VPN_SERVICE_PROVIDER': 'custom', 'VPN_TYPE': 'wireguard', 'DNS_KEEP_NAMESERVER': 'off', 'DNS_UPSTREAM_RESOLVER_TYPE': 'dot'}.items():
        if env.get(key) != value: raise Refusal('vpn_environment_contract_changed')
    required_mounts = {'dispatcharr': {'/etc/resolv.conf': str(ROOT / 'resolv.vpn.conf')},
                       'iptv-vpn': {'/gluetun/wireguard/wg0.conf': str(ROOT / 'private/wg0.conf'), '/iptables/post-rules.txt': str(ROOT / 'vpn-post-rules.txt')},
                       'gateway': {'/etc/caddy/Caddyfile': str(ROOT / 'Caddyfile')}}
    for service, mounts in required_mounts.items():
        actual = {m['Destination']: m for m in containers[service].get('Mounts', [])}
        for target, source in mounts.items():
            m = actual.get(target, {})
            if m.get('Type') != 'bind' or m.get('Source') != source or m.get('RW') is not False:
                raise Refusal('protected_mount_changed')
    if owner['HostConfig']['NetworkMode'] != 'rivendell-iptv-egress':
        raise Refusal('owner_network_mode_changed')
    owner_ips = owner['NetworkSettings']['Networks']
    if set(owner_ips) != {'rivendell-iptv-egress'}:
        raise Refusal('owner_network_set_changed')
    attachment = owner_ips['rivendell-iptv-egress']
    if owner['State']['Running']:
        if attachment.get('IPAddress') != '172.16.70.2' or attachment.get('NetworkID') != n['Id']:
            raise Refusal('owner_address_changed')
    elif attachment.get('IPAMConfig', {}).get('IPv4Address') != '172.16.70.2' or attachment.get('NetworkID') not in ('', None, n['Id']):
        raise Refusal('stopped_owner_static_address_missing')
    if set(n.get('Containers', {})) - {owner['Id']}:
        raise Refusal('unexpected_network_member')
    for service in ['dispatcharr', 'gateway']:
        if containers[service]['HostConfig']['NetworkMode'] != 'container:' + owner['Id']:
            raise Refusal('wrong_namespace_reference')
    if require_running:
        ids = [state['netns'].get(k) for k in NAMES]
        if not ids[0] or len(set(ids)) != 1 or ids[0] == state['host_netns']:
            raise Refusal('wrong_live_namespace')
        if owner['State'].get('Health', {}).get('Status') != 'healthy':
            raise Refusal('vpn_unhealthy')
    return tuple((k, containers[k]['Id'], containers[k]['State']['StartedAt']) for k in sorted(NAMES)) + (('network', n['Id']),)
