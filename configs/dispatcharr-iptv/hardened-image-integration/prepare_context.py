"""Prepare a verified COPY-only build context. Does not invoke Docker or install.

Use only after the actual local base's eight input and four readiness hashes pass.
All outputs must match the approved release; existing output dirs are refused.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

HERE=Path(__file__).resolve().parent
HARDENING=HERE.parent/'native-provider-hardening'
BASE='sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21'


def prepare(source,output,evidence):
    expected=json.loads((HARDENING/'source-pins.json').read_text())
    inspector_spec=importlib.util.spec_from_file_location('image_inspector',HERE/'inspect_image.py')
    inspector=importlib.util.module_from_spec(inspector_spec);inspector_spec.loader.exec_module(inspector)
    if inspector.PINS!=expected:raise ValueError('inspector_source_pin_drift')
    expected.update(inspector.READINESS)
    if (evidence.get('base',{}).get('id')!=BASE
            or any(evidence.get('hashes',{}).get(k)!=v for k,v in expected.items())):
        raise ValueError('verified_actual_base_source_evidence_required')
    if output.exists():raise ValueError('new_context_directory_required')
    spec=importlib.util.spec_from_file_location('approved_prepare',HARDENING/'prepare.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as temporary:
        overlay=Path(temporary)/'overlay';actual=module.prepare(source,overlay)
        if actual!=json.loads((HARDENING/'output-hashes.json').read_text()):raise ValueError('approved_output_hash_mismatch')
        if (overlay/'server.patch').read_bytes()!=(HARDENING/'server.patch').read_bytes():raise ValueError('reviewed_patch_mismatch')
        output.mkdir(mode=0o700)
        for name,sha in actual.items():
            target=output/'app'/name;target.parent.mkdir(parents=True,exist_ok=True)
            if hashlib.sha256((overlay/name).read_bytes()).hexdigest()!=sha:raise ValueError('overlay_drift')
            shutil.copyfile(overlay/name,target)
        shutil.copyfile(overlay/'core/provider_contract_hashes.json',output/'app/core/provider_contract_hashes.json')
        shutil.copyfile(HERE/'Dockerfile',output/'Dockerfile')
        # Public code modes must not inherit private transport umask. Docker's
        # reviewed COPY --chown=0:0 supplies image ownership; no chmod of secrets.
        for directory in [output/'app',*[p for p in (output/'app').rglob('*') if p.is_dir()]]:
            directory.chmod(0o755)
        for file in output.rglob('*'):
            if file.is_file(): file.chmod(0o644)
    files={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'context-hashes.json').write_text(json.dumps(files,indent=2,sort_keys=True)+'\n')
    return files


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path);parser.add_argument('evidence',type=Path)
    args=parser.parse_args();print(json.dumps(prepare(args.source,args.output,json.loads(args.evidence.read_text())),indent=2))
