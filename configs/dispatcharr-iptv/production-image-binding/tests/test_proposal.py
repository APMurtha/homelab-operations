"""Offline source/Compose/lifecycle review only. No subprocess or Docker calls."""
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import verify_review as review

class ProposedBinding(unittest.TestCase):
    def test_complete_review_passes_without_installing(self):
        result=review.verify();self.assertEqual(result['matched_targets'],80);self.assertTrue(result['active_release_unbound']);self.assertTrue(result['authorization_required'])
    def modified(self,path,mutate):
        original=review.read
        def read(p):
            v=original(p)
            if p==path:mutate(v)
            return v
        return patch.object(review,'read',side_effect=read)
    def test_wrong_image_is_refused(self):
        with self.modified(HERE/'candidate/native-provider-hardening/release-contract.json',lambda v:v.update(aio_image='sha256:'+'f'*64)),self.assertRaises(ValueError):review.verify()
    def test_old_or_mixed_source_hashes_are_refused(self):
        def change(v):v['source_hashes']['apps/m3u/tasks.py']='0'*64
        with self.modified(HERE/'candidate/native-provider-hardening/release-contract.json',change),self.assertRaises(ValueError):review.verify()
    def test_all_eighteen_hashes_match_real_acceptance(self):
        p=review.native_contract().source_contract();a=review.read(review.BASE/'hardened-image-integration/corrected-runtime-acceptance-results.json');h=a['admission_records'];verified=next(r['details'] for r in h if r['event']=='verification_completed')
        self.assertEqual({**p['source_hashes'],**p['readiness_hashes']},verified['source_hashes']);self.assertEqual(len(verified['source_hashes']),18)
    def test_bound_image_resolves_through_existing_native_verifier(self):self.assertEqual(review.native_contract().image(),review.IMAGE)
    def test_stale_backend_registrar_API_pins_are_rejected(self):
        def change(v):v['files']['core/api_urls.py']=review.read(review.BASE/'permanent-streaming/api-source-pins.json')['files']['core/api_urls.py']
        with self.modified(HERE/'candidate/permanent-streaming/api-source-pins.json',change),self.assertRaisesRegex(ValueError,'API_pin_scope'):review.verify()
    def test_only_two_API_hashes_change_and_no_file_check_is_removed(self):
        a=review.read(review.BASE/'permanent-streaming/api-source-pins.json');b=review.read(HERE/'candidate/permanent-streaming/api-source-pins.json');self.assertEqual(set(a['files']),set(b['files']));self.assertEqual(len(b['files']),14)
        self.assertEqual({k for k in b['files'] if a['files'][k]!=b['files'][k]},{'core/api_urls.py','apps/m3u/api_views.py'})
    def test_other_three_services_networks_and_no_ports_remain_identical(self):
        a=review.yaml.safe_load((review.BASE/'permanent-streaming/compose.yaml').read_text());b=review.yaml.safe_load((HERE/'compose.effective.review.yaml').read_text())
        self.assertEqual(set(a['services']),set(b['services']))
        for name in ['iptv-vpn','relay','gateway']:self.assertEqual(a['services'][name],b['services'][name])
        self.assertEqual(a['networks'],b['networks']);self.assertNotIn('ports',b['services']['dispatcharr'])
        self.assertEqual(set(k for k in a['services']['dispatcharr'] if a['services']['dispatcharr'][k]!=b['services']['dispatcharr'][k]),{'image','volumes'})
    def test_native_mounts_are_readonly_and_never_include_private_policy(self):
        p=review.yaml.safe_load((HERE/'candidate/permanent-streaming/compose.native.yaml').read_text())['services']['dispatcharr']['volumes']
        self.assertEqual(len(p),3);self.assertTrue(all(m['read_only'] for m in p));self.assertFalse(any(m['source']=='/run/dispatcharr-provider' for m in p))
    def test_writable_public_projection_is_refused(self):
        original=review.yaml.safe_load
        def load(text):
            v=original(text)
            if isinstance(v,dict) and set(v.get('services',{}))=={'dispatcharr'}:v['services']['dispatcharr']['volumes'][1]['read_only']=False
            return v
        with patch.object(review.yaml,'safe_load',side_effect=load),self.assertRaisesRegex(ValueError,'native_mount_permission'):review.verify()
    def test_target_addition_or_permission_weakening_is_refused(self):
        for mutate in [lambda v:v['installed_files'].update({'/unexpected':next(iter(v['installed_files'].values()))}),lambda v:next(iter(v['installed_files'].values())).update(mode='0666')]:
            with self.modified(HERE/'installed-targets.proposed.json',mutate),self.assertRaises(ValueError):review.verify()
    def test_complete_real_old_public_baseline_and_rollback_identity(self):
        a=review.read(HERE/'installed-public-baseline.json');p=review.read(HERE/'rollback-targets.json');self.assertTrue(a['all_installed_public_files_match_227122d']);self.assertFalse(a['native_40_installed']);self.assertEqual(len(p['installed_files']),67)
        self.assertEqual(p['aio_image'],'sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21');self.assertFalse(p['persistent_data_delete_or_restore'])
    def test_revocation_precedes_admission_and_guard_reapplication(self):
        for name in ['40-native-hardening.conf','30-permanent-streaming.conf']:
            source=(review.BASE/'permanent-streaming'/name).read_text();lines=[l for l in source.splitlines() if l.startswith('ExecStartPre=') and l!='ExecStartPre=']
            self.assertIn('provider_control.py revoke',lines[0]);self.assertLess(next(i for i,l in enumerate(lines) if 'admit.py' in l),next(i for i,l in enumerate(lines) if 'guard.py apply' in l))
        stop=(review.BASE/'permanent-streaming/lifecycle.py').read_text();self.assertIn("errors.append('provider_withdrawal_failed')",stop);self.assertIn("errors.append('scoped_stop_failed')",stop)
    def test_no_automatic_policy_publication_in_native_startup(self):
        source=(review.BASE/'permanent-streaming/lifecycle.py').read_text();self.assertIn("provider_control.py'),'prepare'",source);self.assertNotIn('publish_policy.py',source)
        helper=(review.BASE/'provider_control.py').read_text();self.assertIn('assert_revoked()',helper);self.assertNotIn('.publish(',helper)
    def test_source_variant_changes_only_release_pin_in_minimal_verifier(self):
        import ast
        old=(review.BASE/'minimal-phase6b3d/verify.py').read_text();new=(HERE/'candidate/minimal-phase6b3d/verify.py').read_text()
        def pins(source):return next(n for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXTRA_PINS' for t in n.targets))
        a=ast.literal_eval(pins(old).value);b=ast.literal_eval(pins(new).value)
        self.assertEqual({k for k in a if a[k]!=b[k]},{'/docker/dispatcharr-iptv/native-provider-hardening/release-contract.json'})
        self.assertEqual(old.splitlines()[7:],new.splitlines()[7:])

if __name__=='__main__':unittest.main()
