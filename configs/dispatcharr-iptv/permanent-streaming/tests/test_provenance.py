import ast
import hashlib
import json
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parents[1]

class Provenance(unittest.TestCase):
    def test_trial_reference_and_unchanged_security_methods(self):
        old=(HERE/'reference/trial_hls_relay.py').read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(),'15c7ab3d87cbeb6e23419ce08536d6882d2721a3c9339b6bb24673387de6fb75')
        def methods(data):
            cls=next(n for n in ast.parse(data).body if isinstance(n,ast.ClassDef) and n.name=='Relay')
            return {n.name:ast.dump(n,include_attributes=False) for n in cls.body if isinstance(n,ast.FunctionDef)}
        before,after=methods(old),methods((HERE/'hls_relay.py').read_bytes())
        for method in ['scope','rewrite','resource','validate_segment','check','close']:
            with self.subTest(method=method):self.assertEqual(before[method],after[method])
    def test_unchanged_finite_fetch_and_DNS_dependencies(self):
        for name,expected in {'fetch_runtime.py':'8b3595556c3061da17e5a018e07871238d786601e973625cde13f88ca91a3d27',
                              'dns_worker.py':'df7e483eaad95749fe5cc0ae97dd0d259c6e86b7896edca3cac9d62728870596',
                              'manifest_telemetry.py':'179a364baaf3a7fbde6c09082db0fc9df65639812a86e7139bc0c1ec32df5784'}.items():
            self.assertEqual(hashlib.sha256((HERE/name).read_bytes()).hexdigest(),expected)
    def test_manifest_complete_and_exact(self):
        manifest=json.loads((HERE/'manifest.json').read_text())['files']
        files={str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ['manifest.json','validation-results.json']}
        self.assertEqual(set(manifest),files)
        for name,h in manifest.items():self.assertEqual(hashlib.sha256((HERE/name).read_bytes()).hexdigest(),h,name)

if __name__=='__main__':unittest.main()
