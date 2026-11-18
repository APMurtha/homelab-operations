"""Pure one-shot contracts extracted from historical validation; no controller.
No mutations, supervision, enrollment, cgroups, polling or process termination.
"""
import json
from pathlib import Path
ROOT = Path('/docker/dispatcharr-iptv')
HERE = Path(__file__).resolve().parent
NAMES = {'iptv-vpn': 'rivendell-iptv-vpn', 'dispatcharr': 'dispatcharr', 'gateway': 'rivendell-iptv-gateway', 'relay': 'rivendell-iptv-relay'}
class Refusal(RuntimeError): pass

RELAY_TMPFS = {'/tmp': 'rw,nosuid,nodev,noexec,size=16m,uid=1000,gid=1000,mode=0700'}

def mount_index(container):
    # Reject duplicates before indexing: a dict comprehension would hide them.
    result = {}
    for mount in container.get('Mounts', []):
        target = mount.get('Destination')
        if not isinstance(target, str) or not target.startswith('/') or target in result:
            raise Refusal('invalid_or_duplicate_mount')
        result[target] = mount
    return result


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

def topology(state, require_running=False, native=False):
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
    if any(containers[k]['HostConfig'].get('PortBindings') for k in ['dispatcharr', 'gateway', 'relay']):
        raise Refusal('unexpected_published_ports')
    env = dict(v.split('=', 1) for v in owner['Config'].get('Env', []) if '=' in v)
    for key, value in {'FIREWALL': 'on', 'VPN_SERVICE_PROVIDER': 'custom', 'VPN_TYPE': 'wireguard', 'DNS_KEEP_NAMESERVER': 'off', 'DNS_UPSTREAM_RESOLVER_TYPE': 'dot'}.items():
        if env.get(key) != value: raise Refusal('vpn_environment_contract_changed')
    required_mounts = {'dispatcharr': {'/etc/resolv.conf': str(ROOT / 'resolv.vpn.conf'), '/opt/permanent': str(ROOT / 'permanent-streaming'), '/run/credentials/registration.json': str(ROOT / 'private/permanent-registration.json'), '/opt/dispatcharr-vpn-startup-gate.py': str(ROOT / 'vpn-startup-gate.py'), '/opt/egress-policy.json': str(ROOT / 'private/egress-policy.json'), '/guard': '/run/dispatcharr-guard'},
                       'iptv-vpn': {'/guard': '/run/dispatcharr-guard', '/opt/egress-policy.json': str(ROOT / 'private/egress-policy.json'), '/opt/vpn-owner-gate.sh': str(ROOT / 'vpn-owner-gate.sh'), '/gluetun/wireguard/wg0.conf': str(ROOT / 'private/wg0.conf'), '/iptables/post-rules.txt': str(ROOT / 'vpn-post-rules.txt')},
                       'gateway': {'/etc/caddy/Caddyfile': str(ROOT / 'permanent-streaming/Caddyfile')},
                       'relay': {'/opt/permanent': str(ROOT / 'permanent-streaming'), '/etc/resolv.conf': str(ROOT / 'resolv.vpn.conf'), '/guard-status': '/run/dispatcharr-guard-status', '/run/credentials/relay.json': str(ROOT / 'private/permanent-relay.json')}}
    if native:
        required_mounts['dispatcharr'].update({'/guard-status':'/run/dispatcharr-guard-status',
            '/run/dispatcharr-provider-status':'/run/dispatcharr-provider-status',
            '/opt/native-provider-hardening':str(ROOT/'native-provider-hardening')})
        aio=containers['dispatcharr'];h=aio['HostConfig']
        if (aio['Config'].get('User','')!='' or set(h.get('CapDrop') or [])!={'ALL'}
                or set(h.get('CapAdd') or [])!={'CHOWN','DAC_OVERRIDE','FOWNER','SETUID','SETGID','KILL'}
                or 'no-new-privileges:true' not in (h.get('SecurityOpt') or [])
                or h.get('Memory')!=3221225472 or h.get('NanoCpus')!=2000000000 or h.get('PidsLimit')!=512):raise Refusal('native_AIO_security_changed')
        actual=mount_index(containers['dispatcharr'])
        writable={'/data':str(ROOT/'data'),'/runtime':'/run/dispatcharr-permanent/relay'}
        if set(actual)!=set(required_mounts['dispatcharr'])|set(writable):raise Refusal('unexpected_native_AIO_mount')
        for target,source in writable.items():
            m=actual[target]
            if m.get('Source')!=source or m.get('Type')!='bind' or m.get('RW') is not True:raise Refusal('AIO_data_mount_changed')
        if any(m.get('Propagation','rprivate')!='rprivate' for m in actual.values()):raise Refusal('AIO_mount_propagation')
    for service, mounts in required_mounts.items():
        actual = mount_index(containers[service])
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
    for service in ['dispatcharr', 'gateway', 'relay']:
        if containers[service]['HostConfig']['NetworkMode'] != 'container:' + owner['Id']:
            raise Refusal('wrong_namespace_reference')
    if require_running:
        ids = [state['netns'].get(k) for k in NAMES]
        if not ids[0] or len(set(ids)) != 1 or ids[0] == state['host_netns']:
            raise Refusal('wrong_live_namespace')
        if owner['State'].get('Health', {}).get('Status') != 'healthy':
            raise Refusal('vpn_unhealthy')
    if containers['dispatcharr']['Config'].get('Entrypoint') != ['python', '/opt/dispatcharr-vpn-startup-gate.py']:
        raise Refusal('AIO_gate_removed')
    r = containers['relay']
    h = r['HostConfig']
    if r['Config'].get('User') != '1000:1000' or not h.get('ReadonlyRootfs') or set(h.get('CapDrop') or []) != {'ALL'} or h.get('CapAdd'):
        raise Refusal('relay_privilege_changed')
    if h.get('Memory') != 268435456 or h.get('MemorySwap') != 268435456 or h.get('NanoCpus') != 500000000 or h.get('PidsLimit') != 64:
        raise Refusal('relay_resource_contract_changed')
    if 'no-new-privileges:true' not in (h.get('SecurityOpt') or []):
        raise Refusal('relay_security_option_changed')
    expected_mounts = {'/runtime': '/run/dispatcharr-permanent/relay', '/exports': '/docker/jellyfin/config/iptv/permanent-dw'}
    if h.get('Tmpfs') != RELAY_TMPFS:
        raise Refusal('relay_tmpfs_configuration_changed')
    actual = mount_index(r)
    for target, source in expected_mounts.items():
        if actual.get(target, {}).get('Source') != source or actual[target].get('Type') != 'bind' or actual[target].get('RW') is not True:
            raise Refusal('relay_runtime_mount_changed')
    binds = set(required_mounts['relay']) | set(expected_mounts)
    # HostConfig.Tmpfs is authoritative in both states. Docker may omit /tmp
    # from Mounts even while running; validate it strictly whenever represented.
    if set(actual) - {'/tmp'} != binds:
        raise Refusal('unexpected_relay_mount')
    if any(actual[target].get('Propagation', 'rprivate') != 'rprivate' for target in binds):
        raise Refusal('unsafe_relay_bind_propagation')
    tmp = actual.get('/tmp')
    if tmp is not None and (tmp.get('Type') != 'tmpfs' or tmp.get('RW') is not True
          or tmp.get('Source') not in ('', None)
          or tmp.get('Mode', '') != '' or tmp.get('Propagation', '') != ''):
        raise Refusal('unsafe_relay_tmpfs_mount')
    if r['Config'].get('Entrypoint') != ['python', '-B', '/opt/permanent/relay_main.py']:
        raise Refusal('relay_entrypoint_changed')
    return tuple((k, containers[k]['Id'], containers[k]['State']['StartedAt']) for k in sorted(NAMES)) + (('network', n['Id']),)
