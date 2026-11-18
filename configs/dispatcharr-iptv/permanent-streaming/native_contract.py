"""Explicit native release binding. Null is intentionally NOT an image pin."""
import hashlib
import json
import os
import stat
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
BUNDLE=Path('/opt/native-provider-hardening') if str(HERE)=='/opt/permanent' else HERE.parent/'native-provider-hardening'
BASE='sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21'
FAILED='sha256:26c93e71dd431127ef72c651bfe0ad3f7431cef7c135749002833f1fc1524c78'


def source_contract():
    record=json.loads((BUNDLE/'release-contract.json').read_text())
    if set(record)!={'schema','aio_image','source_hashes','readiness_hashes'} or type(record['schema']) is not int or record['schema']!=1:raise ValueError('native_release_schema')
    expected=json.loads((BUNDLE/'output-hashes.json').read_text())
    if len(expected)!=14 or record['source_hashes']!=expected or len(record['readiness_hashes'])!=4:raise ValueError('native_source_contract')
    return record


def image():
    value=source_contract()['aio_image']
    if not isinstance(value,str) or not re.fullmatch('sha256:[a-f0-9]{64}',value) or value in {BASE,FAILED}:raise ValueError('hardened_image_unbound_or_rejected')
    return value


def verify_runtime():
    """Executed only by UID1000 inside a future accepted AIO, not in this task."""
    if os.geteuid()!=1000 or os.getegid()!=1000:raise ValueError('native_worker_identity')
    record=source_contract()
    for name,wanted in {**record['source_hashes'],**record['readiness_hashes']}.items():
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('source_path')
        path=Path('/app')/name
        if name in record['source_hashes']:
            st=path.lstat()
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o644 or st.st_nlink!=1:raise ValueError('native_code_permissions')
            for parent in [path.parent,*path.parent.parents]:
                if str(parent)=='/':break
                st=parent.lstat()
                if not stat.S_ISDIR(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o755:raise ValueError('native_code_directory')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=wanted:raise ValueError('native_image_source_changed')

if __name__=='__main__':verify_runtime()
