"""Offline file/manifest closure check. No operational commands or runtime reads."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ORIGINAL = {'backend.py':'651c7f5952667ac0bda3e21e1e1edb73963aea16b38c9ceca8501182ae774dbf','lifecycle.py':'9dbe2ec2cfb41b847cffc5cff487e558c16f56d5d992474670989c387d286779','manifest.json':'9014af51977ae95a33ea5a380480196da8352af6043bde6126c9b39a4c8f781c'}
BASELINE='227122dcbe9ebc76be46b8a91231350d6c93bdb4'
def load(path):return json.loads(path.read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify():
    inv=load(HERE/'candidate-inventory.json');pins=load(HERE/'original-hashes.json')
    if pins['files']!=ORIGINAL or pins['source_commit']!=BASELINE or inv['baseline_commit']!=BASELINE:raise ValueError('authorized_baseline_changed')
    for name,h in pins['files'].items():
        if digest(HERE/'original'/name)!=h:raise ValueError('original_baseline_drift')
    for name,h in inv['existing_tracked_inputs_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('unrelated_tracked_input_drift')
    if inv['unchanged_image']!='sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21' or inv['Docker_systemd_network_changes'] is not False:raise ValueError('runtime_scope_changed')
    if inv['receipt_directory']!={'path':'/docker/dispatcharr-iptv/private/backend-diagnostics','uid':0,'gid':0,'mode':'0700','files_mode':'0600','kind':'diagnostic evidence only; never a readiness/authorization latch'}:raise ValueError('receipt_permissions_changed')
    expected={'/docker/dispatcharr-iptv/permanent-streaming/'+n for n in ['backend.py','lifecycle.py','manifest.json']}
    if set(inv['replacement_targets'])!=expected or set(inv['rollback_targets'])!=expected:raise ValueError('replacement_scope')
    for key in ['replacement_targets','rollback_targets']:
        for row in inv[key].values():
            if digest(ROOT/row['source'])!=row['sha256'] or (row['uid'],row['gid'],row['mode'])!=(0,0,'0644'):raise ValueError('candidate_hash_or_permissions')
    original=load(HERE/'original/manifest.json');candidate=load(HERE/'candidate/manifest.json')
    changed={n for n in original['files'] if original['files'][n]!=candidate['files'].get(n)}
    if set(original['files'])!=set(candidate['files']) or changed!={'backend.py','lifecycle.py'}:raise ValueError('manifest_scope')
    all_targets={**inv['unchanged_installed_targets'],**{t:r['sha256'] for t,r in inv['replacement_targets'].items()}}
    if len(all_targets)!=67:raise ValueError('baseline_target_count')
    for name,h in candidate['files'].items():
        target='/docker/dispatcharr-iptv/permanent-streaming/'+name
        if all_targets.get(target)!=h:raise ValueError('installed_manifest_closure')
    if 'provider_control.py' in (HERE/'candidate/lifecycle.py').read_text() or '--native' in (HERE/'candidate/lifecycle.py').read_text():raise ValueError('wrong_lifecycle_baseline')
    return {'result':'PASS_OFFLINE_CANDIDATE_ONLY','original_hashes_verified':3,'replacement_files':3,'unchanged_installed_files':64,'manifest_paths_closed':True,'production_authorization_required':True}
if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
