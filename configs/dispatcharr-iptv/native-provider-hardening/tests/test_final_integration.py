"""Offline matched transition fixtures. No Docker/systemd commands are executed."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
import yaml

BASE=Path(__file__).resolve().parents[2]
PERMANENT=BASE/'permanent-streaming'
sys.path[:0]=[str(PERMANENT),str(PERMANENT/'tests'),str(BASE)]
import verify,lifecycle,native_contract,provider_control
from test_contract import state
spec=importlib.util.spec_from_file_location('native_transition_guard',BASE/'guard.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
FAKE='sha256:'+'c'*64  # Synthetic inspection identity, never an image/build.


def native_state():
    s=state();aio=s['containers']['dispatcharr'];aio['Config']['Image']=FAKE;aio['Image']=FAKE
    aio['HostConfig'].update(Memory=3221225472,NanoCpus=2000000000,PidsLimit=512)
    overlay=yaml.safe_load((PERMANENT/'compose.native.yaml').read_text())
    for m in overlay['services']['dispatcharr']['volumes']:
        aio['Mounts'].append({'Type':'bind','Source':m['source'],'Destination':m['target'],'RW':False})
    return s


def steps(*names):
    result={}
    for name in names:
        for line in name.read_text().splitlines():
            if line and not line.startswith('#') and '=' in line:
                key,value=line.split('=',1)
                if value:result.setdefault(key,[]).append(value)
                else:result[key]=[]
    return result


class FinalIntegration(unittest.TestCase):
    def test_future_build_uses_fresh_tag_and_approved_application_revision(self):
        import importlib.util
        folder=BASE/'hardened-image-integration';spec=importlib.util.spec_from_file_location('future_recipe',folder/'build_once.py');recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)
        self.assertNotEqual(recipe.TAG,'local/dispatcharr-native-hardening:1124d96-review')
        self.assertIn('0b8ac7d326a89c9607654d426eb0270f65e41136',(folder/'Dockerfile').read_text())
        self.assertEqual(recipe.BASE,native_contract.BASE)
    def test_runtime_fixture_preparation_is_public_code_under_private_transport(self):
        import base64
        spec=importlib.util.spec_from_file_location('future_runtime',BASE/'hardened-image-integration/run_runtime.py');runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
        with patch.object(runtime,'docker') as docker:
            with self.assertRaises(RuntimeError):runtime.main({},'/unused')
            with self.assertRaises(RuntimeError):runtime.main({},'/unused',native_contract.FAILED)
            docker.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp:
            old=os.umask(0o077)
            try:root=runtime.prepare_fixture(Path(tmp),{'client/dispatcharr_provider/core.py':base64.b64encode(b'synthetic').decode()})
            finally:os.umask(old)
            self.assertEqual(Path(tmp).stat().st_mode&0o777,0o700)
            self.assertEqual(root.stat().st_mode&0o777,0o755);self.assertEqual((root/'client/dispatcharr_provider').stat().st_mode&0o777,0o755)
    def test_unbound_image_refuses_before_any_Docker_operation(self):
        with patch.object(lifecycle,'execute') as execute:
            with self.assertRaises(ValueError):lifecycle.configure_native()
            execute.assert_not_called()
    def test_failed_and_legacy_image_ids_refused(self):
        record=native_contract.source_contract()
        for value in [None,'latest',native_contract.BASE,native_contract.FAILED]:
            with patch.object(native_contract,'source_contract',return_value={**record,'aio_image':value}),self.assertRaises(ValueError):native_contract.image()
    def test_explicit_synthetic_image_binding_and_fourteen_sources(self):
        r=native_contract.source_contract();self.assertEqual(len(r['source_hashes']),14);self.assertEqual(len(r['readiness_hashes']),4)
        with patch.object(native_contract,'source_contract',return_value={**r,'aio_image':FAKE}):self.assertEqual(native_contract.image(),FAKE)
    def test_AIO_and_relay_image_contracts_are_separate(self):
        self.assertEqual(verify.IMAGES['relay'],verify.RELAY_IMAGE)
        with patch.object(native_contract,'image',return_value=FAKE):verify.workload(native_state(),True,True)
        s=native_state();s['containers']['relay']['Config']['Image']=FAKE
        with patch.object(native_contract,'image',return_value=FAKE),self.assertRaises(Exception):verify.workload(s,True,True)
    def test_native_immutable_inspect_identity_is_required(self):
        s=native_state();s['containers']['dispatcharr']['Image']=native_contract.FAILED
        with patch.object(native_contract,'image',return_value=FAKE),self.assertRaises(Exception):verify.workload(s,True,True)
    def test_baseline_four_service_contract_still_passes(self):verify.workload(state(),True)
    def test_native_overlay_changes_only_AIO(self):
        overlay=yaml.safe_load((PERMANENT/'compose.native.yaml').read_text());self.assertEqual(set(overlay['services']),{'dispatcharr'})
        self.assertEqual(set(overlay['services']['dispatcharr']),{'image','volumes'})
        self.assertIn(':?',overlay['services']['dispatcharr']['image'])
    def test_native_mounts_are_required_and_readonly(self):
        for target in ['/guard-status','/run/dispatcharr-provider-status','/opt/native-provider-hardening']:
            for missing in [False,True]:
                s=native_state();mounts=s['containers']['dispatcharr']['Mounts']
                m=next(m for m in mounts if m['Destination']==target)
                if missing:mounts.remove(m)
                else:m['RW']=True
                with patch.object(native_contract,'image',return_value=FAKE),self.assertRaises(Exception):verify.workload(s,True,True)
    def test_extra_private_or_duplicate_AIO_mount_refused(self):
        for m in [{'Destination':'/private','Source':'/run/dispatcharr-provider','Type':'bind','RW':False},copy.deepcopy(native_state()['containers']['dispatcharr']['Mounts'][-1])]:
            s=native_state();s['containers']['dispatcharr']['Mounts'].append(m)
            with patch.object(native_contract,'image',return_value=FAKE),self.assertRaises(Exception):verify.workload(s,True,True)
    def test_native_resource_or_privilege_drift_refused(self):
        for field,value in [('Memory',1),('NanoCpus',1),('PidsLimit',1),('CapAdd',['SYS_ADMIN'])]:
            s=native_state();s['containers']['dispatcharr']['HostConfig'][field]=value
            with patch.object(native_contract,'image',return_value=FAKE),self.assertRaises(Exception):verify.workload(s,True,True)
    def test_relay_has_no_new_mounts_or_policy_authority(self):
        spec=yaml.safe_load((PERMANENT/'compose.yaml').read_text())['services']['relay']
        self.assertEqual(len(spec['volumes']),6)
        self.assertNotIn('/run/dispatcharr-provider-status',str(spec));self.assertNotIn('/run/dispatcharr-provider',str(spec))
    def test_native_effective_systemd_order(self):
        values=steps(BASE/'minimal-phase6b3d/units/dispatcharr-stack.service',BASE/'boot-admission-phase6b3k/20-resource-admission.conf',PERMANENT/'30-permanent-streaming.conf',PERMANENT/'40-native-hardening.conf')
        pre=values['ExecStartPre'];self.assertTrue(pre[0].endswith('provider_control.py revoke'))
        self.assertIn('rm -f',pre[1]);self.assertIn('inputs --native',pre[2]);self.assertIn('admit.py',pre[3]);self.assertIn('guard.py apply',pre[4]);self.assertIn('prepare --native',pre[5]);self.assertIn('prestart --native',pre[6])
        self.assertEqual(values['TimeoutStartSec'],['540']);self.assertEqual(values['TimeoutStopSec'],['240']);self.assertEqual(values['Restart'],['no'])
        self.assertTrue(values['ExecStopPost'][0].endswith('provider_control.py revoke'))
    def test_guard_drop_withdraws_before_validation(self):
        p=BASE/'minimal-phase6b3d/units/dispatcharr-egress-guard.service.d/20-trusted-readiness.conf'
        v=steps(p);self.assertTrue(v['ExecStartPre'][0].endswith('provider_control.py revoke'));self.assertIn('RuntimeDirectoryPreserve=yes',p.read_text())
    def test_native_start_never_publishes_or_renews(self):
        events=[];g=Mock();g.grant.side_effect=lambda *a:events.append('grant')
        with patch.object(lifecycle,'NATIVE',True),patch.object(lifecycle,'trusted',return_value=g),patch.object(lifecycle,'execute',side_effect=lambda c,*a:events.append(c[-1])),patch.object(lifecycle,'inside',side_effect=lambda n,*a,**k:events.append(n)):
            lifecycle.start()
        self.assertLess(events.index('grant'),events.index('relay'));self.assertLess(events.index('native_contract.py'),events.index('backend.py'));self.assertLess(events.index('register.py'),events.index('gateway'))
        self.assertNotIn('publish',str(events));self.assertNotIn('renew',str(events))
    def test_cleanup_attempts_all_actions_when_provider_fails(self):
        events=[]
        def execute(c,*a):
            events.append(c)
            if 'provider_control.py' in ' '.join(c):raise ValueError('synthetic')
        g=Mock()
        with patch.object(lifecycle,'execute',side_effect=execute),patch.object(lifecycle,'trusted',return_value=g),self.assertRaises(ValueError):lifecycle.stop()
        g.revoke.assert_called_once_with(False);self.assertTrue(any('compose' in c for c in events));self.assertEqual(len(events),4)
    def test_stop_does_not_require_native_image_binding(self):
        with patch.object(lifecycle,'execute'),patch.object(lifecycle,'trusted'),patch.object(native_contract,'image',side_effect=AssertionError('binding must not be used')):lifecycle.stop()
    def test_rollback_withdrawal_failure_prevents_API_deletion(self):
        with patch.object(lifecycle,'execute',side_effect=ValueError('synthetic')),patch.object(lifecycle,'inside') as inside,self.assertRaises(ValueError):lifecycle.rollback_integration()
        inside.assert_not_called()
    def test_guard_withdrawal_attempts_guard_cleanup_after_provider_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=guard.Publisher(Path(tmp)/'private',Path(tmp)/'public');p.private.mkdir();p.public.mkdir()
            for f in [p.private/'ready',p.public/'guard.json',p.public/'grant.json']:f.write_text('synthetic')
            p.transaction=Mock(return_value={'phase':'applied','blocked':False});p.write=Mock()
            with patch.object(provider_control,'revoke',side_effect=ValueError('synthetic')),self.assertRaises(ValueError):p.withdraw()
            self.assertFalse((p.private/'ready').exists());self.assertFalse(list(p.public.iterdir()))
    def test_provider_withdrawal_precedes_guard_lock_or_directory_failure(self):
        for action in ['apply','revoke']:
            instance=guard.Publisher();events=[]
            def fail_lock():events.append('guard_validation');raise ValueError('synthetic')
            with patch.object(provider_control,'revoke',side_effect=lambda:events.append('provider')),patch.object(instance,'locked',side_effect=fail_lock),self.assertRaises(ValueError):
                instance.apply('/unused','/unused') if action=='apply' else instance.revoke()
            self.assertEqual(events,['provider','guard_validation'])
    def test_three_service_no_provider_state_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(provider_control,'PRIVATE',Path(tmp)/'private'),patch.object(provider_control,'PUBLIC',Path(tmp)/'public'),patch.object(provider_control.os,'geteuid',return_value=0),patch.object(provider_control,'publisher') as p:
            provider_control.revoke();provider_control.assert_revoked();p.assert_not_called()
    def test_partial_provider_state_never_silently_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'public').mkdir();p=Mock();p.revoke.side_effect=ValueError('unexplained')
            with patch.object(provider_control,'PRIVATE',root/'private'),patch.object(provider_control,'PUBLIC',root/'public'),patch.object(provider_control.os,'geteuid',return_value=0),patch.object(provider_control,'publisher',return_value=p),self.assertRaises(ValueError):provider_control.revoke()
    def test_no_new_network_or_published_port_in_overlay(self):
        text=(PERMANENT/'compose.native.yaml').read_text();self.assertNotIn('ports:',text);self.assertNotIn('networks:',text)
    def test_contract_pins_unchanged_guard_reader_and_native_outputs(self):
        r=native_contract.source_contract();original=json.loads((BASE/'native-provider-hardening/output-hashes.json').read_text());self.assertEqual(r['source_hashes'],original)
        self.assertIn('apps/proxy/live_proxy/readiness.py',r['readiness_hashes'])

if __name__=='__main__':unittest.main()
