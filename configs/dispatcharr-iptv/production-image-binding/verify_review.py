"""Read-only offline proposal validation. No install, Docker or service commands."""
import copy,hashlib,importlib.util,json
from pathlib import Path
import yaml
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=ROOT/'configs/dispatcharr-iptv'
IMAGE='sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439'
def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def native_contract():
    spec=importlib.util.spec_from_file_location('proposed_native_binding',BASE/'permanent-streaming/native_contract.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.BUNDLE=HERE/'candidate/native-provider-hardening'
    return module

def verify():
    inputs=read(HERE/'review-input-pins.json')
    for name,h in inputs.items():
        if digest(ROOT/name)!=h:raise ValueError('review_input_drift:'+name)
    accepted=read(BASE/'hardened-image-integration/corrected-runtime-acceptance-results.json')
    build=read(BASE/'hardened-image-integration/corrected-image-build-results.json')
    proposed=read(HERE/'candidate/native-provider-hardening/release-contract.json')
    active=read(BASE/'native-provider-hardening/release-contract.json')
    if active['aio_image'] is not None or proposed!={**active,'aio_image':IMAGE}:raise ValueError('active_or_proposed_binding_changed')
    if native_contract().image()!=IMAGE or IMAGE!=accepted['image'] or IMAGE!=build['new_image_id']:raise ValueError('image_evidence_mismatch')
    if {**proposed['source_hashes'],**proposed['readiness_hashes']}!=build['verification']['hashes']:raise ValueError('source_evidence_mismatch')
    if not accepted['application']['success'] or accepted['application']['tests_run']!=11 or not accepted['final_transport_status']['cleanup_complete']:raise ValueError('acceptance_incomplete')
    original=yaml.safe_load((BASE/'permanent-streaming/compose.yaml').read_text())
    overlay=yaml.safe_load((HERE/'candidate/permanent-streaming/compose.native.yaml').read_text())
    if set(overlay)!= {'services'} or set(overlay['services'])!={'dispatcharr'}:raise ValueError('overlay_scope')
    aio=overlay['services']['dispatcharr']
    if set(aio)!={'image','volumes'} or aio['image']!=IMAGE:raise ValueError('overlay_binding')
    expected_mounts={
        '/guard-status':'/run/dispatcharr-guard-status',
        '/run/dispatcharr-provider-status':'/run/dispatcharr-provider-status',
        '/opt/native-provider-hardening':'/docker/dispatcharr-iptv/native-provider-hardening'}
    if len(aio['volumes'])!=3 or {m['target']:m['source'] for m in aio['volumes']}!=expected_mounts:raise ValueError('native_mount_scope')
    if any(m.get('read_only') is not True or m.get('bind')!={'create_host_path':False} for m in aio['volumes']):raise ValueError('native_mount_permission')
    merged=copy.deepcopy(original);merged['services']['dispatcharr']['image']=IMAGE
    merged['services']['dispatcharr']['volumes']+=copy.deepcopy(aio['volumes'])
    effective=yaml.safe_load((HERE/'compose.effective.review.yaml').read_text())
    if merged!=effective:raise ValueError('effective_compose_drift')
    for service in ['iptv-vpn','relay','gateway']:
        if effective['services'][service]!=original['services'][service]:raise ValueError('unrelated_service_proposal')
    if effective['networks']!=original['networks']:raise ValueError('network_proposal')
    current_api=read(BASE/'permanent-streaming/api-source-pins.json');api=read(HERE/'candidate/permanent-streaming/api-source-pins.json')
    expected_api=copy.deepcopy(current_api);expected_api['image']=IMAGE
    for name in ['core/api_urls.py','apps/m3u/api_views.py']:expected_api['files'][name]=proposed['source_hashes'][name]
    if api!=expected_api:raise ValueError('API_pin_scope')
    targets=read(HERE/'installed-targets.proposed.json')['installed_files']
    if set(targets)!=set(read(BASE/'trusted-guard-tests/transition-manifest.json')['installed_files']):raise ValueError('installed_target_scope')
    for target,item in targets.items():
        if digest(ROOT/item['source'])!=item['sha256'] or (item['uid'],item['gid'],item['mode'])!=(0,0,'0644'):raise ValueError('matched_source_drift:'+target)
    def pin(target,wanted):
        if targets[target]['sha256']!=wanted:raise ValueError('dependency_pin_drift:'+target)
    root='/docker/dispatcharr-iptv/'
    for rel,h in read(HERE/'candidate/permanent-streaming/base-input-pins.json').items():pin(root+rel,h)
    for rel,h in read(HERE/'candidate/permanent-streaming/manifest.json')['files'].items():
        pin('/etc/systemd/system/dispatcharr-stack.service.d/'+rel if rel=='40-native-hardening.conf' else root+'permanent-streaming/'+rel,h)
    import ast
    text=(HERE/'candidate/minimal-phase6b3d/verify.py').read_text()
    pins=ast.literal_eval(next(n.value for n in ast.parse(text).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXTRA_PINS' for t in n.targets)))
    for target,h in pins.items():pin(target,h)
    baseline=read(HERE/'installed-public-baseline.json');rollback=read(HERE/'rollback-targets.json')
    if not baseline['all_installed_public_files_match_227122d'] or len(rollback['installed_files'])!=67:raise ValueError('rollback_baseline_unknown')
    for target,item in rollback['installed_files'].items():
        if baseline['files'][target]['sha256']!=item['sha256']:raise ValueError('rollback_file_mismatch')
    return {'status':'PASS_OFFLINE_REVIEW_ONLY','image':IMAGE,'source_count':18,'matched_targets':len(targets),'unchanged_other_services':True,'active_release_unbound':True,'rollback_image':rollback['aio_image'],'authorization_required':True}

if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
