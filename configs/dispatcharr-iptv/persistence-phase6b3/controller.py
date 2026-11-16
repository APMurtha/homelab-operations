#!/usr/bin/env python3
"""UNINSTALLED candidate. Default check only; host mutations require --execute.
An observation loop is NOT an atomic fence against an out-of-band ruleset flush.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path('/docker/dispatcharr-iptv')
HERE = Path(__file__).resolve().parent
NAMES = {'iptv-vpn': 'rivendell-iptv-vpn', 'dispatcharr': 'dispatcharr',
         'gateway': 'rivendell-iptv-gateway'}
SOURCE_PINS = {'security.py': 'e7a92e7753e666a6f8cafd1b0292cec5e65f1431b09fc92ba10678c26e5ef8e2',
               'guard.py': 'df53629a537e66fcbdf664076b9fa58de47d590e4a0f0d0128fd15f46f3088bd',
 'Caddyfile': 'bf5e40d2ccba8799f4b38f15336399fea7068f676150c2f7b18a1e07dc081a98',
 'vpn-owner-gate.sh': 'e343e41632ece47165ecc6f2ae1f00779e92d77dd552329ef628807bab7ba523',
 'vpn-startup-gate.py': '766879e875aa801c376adc44a65f02301dfd2c225acd29909c34da823b847ee7',
 'resolv.vpn.conf': '847d06f745d54e604791fa452b44a992026df81ba0dbdf58d81a8d02dd9d7ce2',
 'vpn-post-rules.txt': 'd48815495401014e7fcd43848af20259a13f1a59c3ac7882795c9fecace6ade4'}

class Refusal(RuntimeError):
    """Only fixed diagnostic codes may be emitted; never command stderr/env."""


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


class Controller:
    """Same admission/quarantine paths are used by fake-backend regression tests."""
    def __init__(self, backend): self.b = backend; self.admitted = None

    def bootstrap(self):
        self.b.revoke()
        try:
            self.b.install_guard()
            self.b.verify_guard()
        except Exception:
            self.b.revoke()
            raise Refusal('guard_install_or_verify_failed') from None

    def start(self):
        if self.b.latched(): raise Refusal('quarantine_latched')
        self.b.verify_guard()
        topology(self.b.snapshot())  # refuses current unless-stopped deployment
        try:
            self.b.prepare_enrollment()
            for service, deadline in [('iptv-vpn', 180), ('dispatcharr', 360), ('gateway', 60)]:
                self.b.verify_guard()
                self.b.start(service)
                self.b.bind_enrollment(service)
                self.b.wait_healthy(service, deadline)  # checks guard each poll
            self.b.verify_enrollment()
            self.admitted = topology(self.b.snapshot(), True)
            self.b.publish()
        except Exception:
            self.quarantine()
            raise Refusal('admission_failed') from None

    def check(self):
        try:
            self.b.verify_guard()
            now = topology(self.b.snapshot(), True)
            self.b.verify_enrollment()
            if self.admitted is not None and now != self.admitted:
                raise Refusal('runtime_identity_changed')
        except Exception:
            self.quarantine()
            raise Refusal('runtime_fault_latched') from None

    def quarantine(self):
        self.b.revoke(); self.b.latch()
        # Restore the exact narrow baseline first if possible, then stop only IPTV.
        # A failure here cannot prove containment; it must be reported, not hidden.
        guard_ok = False
        try:
            self.b.install_guard(); self.b.verify_guard(); guard_ok = True
        except Exception: pass
        stopped = self.b.stop_project()
        self.b.revoke()
        if not guard_ok or not stopped:
            raise Refusal('containment_uncertain_manual_action_required')


def private_regular(path, maximum=0o077):
    st = path.lstat()
    import stat
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & maximum:
        raise Refusal('unsafe_private_input')


def trusted_directory(path):
    import stat
    for p in [path, *path.parents]:
        st = p.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise Refusal('unsafe_code_directory')


class Host:
    def __init__(self, execute=False):
        self.execute = execute
        self.enrollment = None
        trusted_directory(ROOT); trusted_directory(HERE)
        sys.dont_write_bytecode = True
        for name, digest in SOURCE_PINS.items():
            p = ROOT / name; st = p.lstat()
            if p.is_symlink() or st.st_uid != 0 or st.st_mode & 0o022 or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                raise Refusal('authoritative_source_changed')
        sys.path.insert(0, str(ROOT))
        import security
        private_regular(ROOT / 'private/egress-policy.json')
        private_regular(ROOT / 'private/wg0.conf')
        self.policy, self.digest = security.load_policy(ROOT / 'private/egress-policy.json')
        if security.read_peer(ROOT / 'private/wg0.conf') != (self.policy['wg_endpoint_ipv4'], self.policy['wg_endpoint_port']):
            raise Refusal('wireguard_peer_policy_mismatch')
        self.runtime = Path('/run/dispatcharr-persistence')
        self.ready = Path('/run/dispatcharr-guard/ready')
        self.fault = self.runtime / 'quarantine'
        self.admission = self.runtime / 'admitted.json'

    def command(self, args, *, mutate=False, timeout=20):
        if mutate and not self.execute: raise Refusal('execution_not_authorized')
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired): raise Refusal('backend_unavailable') from None
        if r.returncode: raise Refusal('backend_command_failed')
        return r.stdout

    def authorize(self):
        if not self.execute or os.geteuid() != 0: raise Refusal('execute_requires_root')
        token = ROOT / 'private/persistence-install-approved'
        private_regular(token)
        trusted_directory(ROOT / 'private')
        manifest_path = HERE / 'artifact-hashes.json'
        st = manifest_path.lstat()
        import stat
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise Refusal('unsafe_manifest')
        manifest = json.loads(manifest_path.read_text())
        for name, digest in manifest.items():
            p = HERE / name; st = p.lstat()
            if p.is_symlink() or st.st_uid != 0 or st.st_mode & 0o022 or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                raise Refusal('candidate_artifact_changed')
        if token.read_text().strip() != hashlib.sha256((HERE / 'artifact-hashes.json').read_bytes()).hexdigest():
            raise Refusal('installation_approval_mismatch')
        self.runtime.mkdir(mode=0o700, exist_ok=True)
        st = self.runtime.lstat()
        if self.runtime.is_symlink() or st.st_uid != 0 or st.st_mode & 0o077:
            raise Refusal('unsafe_runtime_directory')

    def verify_guard(self):
        live = json.loads(self.command(['nft', '-j', 'list', 'table', 'inet', 'rivendell_iptv']))
        verify_table(live, self.policy)
        if self.ready.read_text().strip() != self.digest: raise Refusal('ready_marker_mismatch')

    def install_guard(self):
        self.command(['/usr/bin/python3', str(ROOT / 'guard.py'), 'apply', '--policy', str(ROOT / 'private/egress-policy.json')], mutate=True)

    def revoke(self):
        if not self.execute: raise Refusal('execution_not_authorized')
        self.admission.unlink(missing_ok=True)
        self.ready.unlink(missing_ok=True)

    def latch(self): self.fault.touch(mode=0o600)
    def latched(self): return self.fault.exists()
    def publish(self):
        p = self.runtime / 'admitted.tmp'
        p.write_text(json.dumps({'guard_digest': self.digest, 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
        os.chmod(p, 0o600); os.replace(p, self.admission)

    def snapshot(self):
        items = json.loads(self.command(['docker', 'inspect', *NAMES.values()]))
        containers = {c['Config']['Labels']['com.docker.compose.service']: c for c in items}
        net = json.loads(self.command(['docker', 'network', 'inspect', 'rivendell-iptv-egress']))[0]
        ns = {}
        for k, c in containers.items():
            if c['State']['Running']: ns[k] = os.readlink('/proc/' + str(c['State']['Pid']) + '/ns/net')
        return {'containers': containers, 'network': net, 'netns': ns, 'host_netns': os.readlink('/proc/1/ns/net')}

    def prepare_enrollment(self):
        if not self.execute: raise Refusal('execution_not_authorized')
        sys.path.insert(0, str(HERE))
        from enrollment import Enrollment
        self.enrollment = Enrollment(self.runtime / 'enrolled.json')
        self.enrollment.prepare(self.snapshot())

    def bind_enrollment(self, service):
        if self.enrollment is None: raise Refusal('missing_enrollment')
        self.enrollment.bind(service, self.snapshot())

    def verify_enrollment(self):
        if self.enrollment is None: raise Refusal('missing_enrollment')
        self.enrollment.verify(self.snapshot())

    def start(self, service):
        state = self.snapshot(); topology(state)
        self.verify_guard()
        if self.enrollment is None: raise Refusal('missing_enrollment')
        self.enrollment.verify(state)
        self.command(['docker', 'start', self.enrollment.payload['ids'][service]], mutate=True)

    def wait_healthy(self, service, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.verify_guard(); s = self.snapshot(); topology(s)
            self.enrollment.verify(s)
            c = s['containers'][service]
            if c['State'].get('Health', {}).get('Status') == 'healthy': return
            if not c['State']['Running']: raise Refusal('component_start_failed')
            time.sleep(1)
        raise Refusal('component_health_deadline')

    def stop_project(self):
        # No record/name discovery: a fresh controller has no termination custody.
        if not self.execute or self.enrollment is None or self.enrollment.scope is None:
            return False
        try:
            for service in ['gateway', 'dispatcharr', 'iptv-vpn']:
                cid = self.enrollment.payload['ids'][service]
                c = json.loads(self.command(['docker', 'inspect', cid]))[0]
                if c['Id'] != cid: raise Refusal('stop_identity_changed')
                if c['State']['Running']:
                    self.enrollment.scope.audit()
                    pin = self.enrollment.scope.pins.get(service)
                    if pin is None or c['State']['Pid'] != pin.identity['pid']:
                        raise Refusal('stop_lifecycle_replaced')
                    pin.verify()
                    grace = {'dispatcharr': 60, 'gateway': 10, 'iptv-vpn': 15}[service]
                    self.command(['docker', 'stop', '-t', str(grace), cid], mutate=True, timeout=grace + 10)
        except Exception:
            pass  # Docker failure/timeout never grants authority to any new PID.
        try:
            # Verify subtree empty even after graceful stop; API is not required.
            self.enrollment.emergency()
            return True
        except Exception:
            return False


def take_lock(path):
    lock = path.open('a')
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close(); raise Refusal('duplicate_controller') from None
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'bootstrap', 'run', 'stop'], nargs='?', default='check')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.action != 'check' and not args.execute: raise Refusal('explicit_execute_required')
    b = Host(args.execute); c = Controller(b)
    if args.action == 'check':
        b.verify_guard(); topology(b.snapshot(), True)
        print(json.dumps({'check': 'pass', 'mutations': 0})); return
    b.authorize()
    lock = take_lock(b.runtime / 'controller.lock')
    if args.action == 'bootstrap': c.bootstrap(); return
    if args.action == 'stop':
        b.revoke()
        if not b.stop_project(): raise Refusal('scoped_stop_incomplete')
        return
    stopped = False
    def stop(*_):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    try:
        c.start()
        print(json.dumps({'state': 'admitted', 'poll_seconds': 1}), flush=True)
        while not stopped:
            c.check(); time.sleep(1)
    finally:
        b.revoke()
        try:
            if not b.stop_project(): raise Refusal('scoped_stop_incomplete')
        finally:
            if b.enrollment is not None: b.enrollment.close()

if __name__ == '__main__':
    try: main()
    except Exception as error:
        code = str(error) if isinstance(error, Refusal) else 'unexpected_error_values_withheld'
        print(json.dumps({'state': 'refused', 'reason': code}), file=sys.stderr)
        raise SystemExit(1)
