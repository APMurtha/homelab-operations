"""Regression for the observed COPY directory-mode defect; no Docker calls."""
import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('build_recipe',Path(__file__).with_name('build_once.py'))
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class Modes(unittest.TestCase):
    def test_private_umask_does_not_make_image_packages_root_private(self):
        data=b'public synthetic source';item={'data':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'context';old=os.umask(0o077)
            try:build.write_context(root,{'Dockerfile':item,'app/apps/m3u/tasks.py':item,'app/core/provider_security.py':item})
            finally:os.umask(old)
            self.assertEqual(root.stat().st_mode&0o777,0o700)
            for name in ['app','app/apps','app/apps/m3u','app/core']:
                self.assertEqual((root/name).stat().st_mode&0o777,0o755)
            self.assertEqual((root/'app/apps/m3u/tasks.py').stat().st_mode&0o777,0o644)
            self.assertEqual((root/'app/apps/m3u/tasks.py').read_bytes(),data)
    def test_unsafe_paths_and_content_drift_are_refused(self):
        for name,item in [('../escape',{'data':'','sha256':hashlib.sha256(b'').hexdigest()}),('app/core/a.py',{'data':'','sha256':'0'*64})]:
            with tempfile.TemporaryDirectory() as tmp,self.assertRaises(RuntimeError):
                build.write_context(Path(tmp)/'context',{name:item})

if __name__=='__main__':unittest.main()
