"""Synthetic tar metadata fixtures only; never invokes Docker or an application."""
import hashlib,io,json,tarfile,unittest
import corrected_build_control as control

class ImageInspection(unittest.TestCase):
    def layer(self,*,body=b'abc',mode=0o644,uid=0,dir_mode=0o755,kind=None,private=False,whiteout=None):
        raw=io.BytesIO()
        with tarfile.open(fileobj=raw,mode='w') as t:
            for name in ['app','app/core']:
                item=tarfile.TarInfo(name);item.type=tarfile.DIRTYPE;item.mode=dir_mode;t.addfile(item)
            if whiteout:
                item=tarfile.TarInfo('app/core/'+whiteout);item.size=0;t.addfile(item,io.BytesIO())
            else:
                item=tarfile.TarInfo('app/core/example.py');item.mode=mode;item.uid=uid
                if kind:item.type=kind;item.linkname='unapproved';t.addfile(item)
                else:item.size=len(body);t.addfile(item,io.BytesIO(body))
            if private:
                item=tarfile.TarInfo('run/dispatcharr-provider');item.type=tarfile.DIRTYPE;item.mode=0o700;t.addfile(item)
        return raw.getvalue()
    def scan(self,*layers,expected=b'abc'):
        raw=io.BytesIO();names=[str(i)+'/layer.tar' for i in range(len(layers))]
        with tarfile.open(fileobj=raw,mode='w') as t:
            for name,body in [*zip(names,layers),('manifest.json',json.dumps([{'Layers':names}]).encode())]:
                item=tarfile.TarInfo(name);item.size=len(body);t.addfile(item,io.BytesIO(body))
        raw.seek(0);return control.scan_stream(raw,{'core/example.py':hashlib.sha256(expected).hexdigest()})
    def test_valid_root_owned_readable_sources(self):
        v=self.scan(self.layer());self.assertEqual(v['source_metadata']['core/example.py']['mode'],'0o644');self.assertTrue(v['provider_runtime_state_absent'])
    def test_wrong_source_owner_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'source_permission'):self.scan(self.layer(uid=1000))
    def test_root_private_application_directory_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'directory_permission'):self.scan(self.layer(dir_mode=0o700))
    def test_source_permission_drift_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'source_permission'):self.scan(self.layer(mode=0o600))
    def test_private_policy_state_rejected_without_extracting_contents(self):
        with self.assertRaisesRegex(RuntimeError,'provider_runtime_state'):self.scan(self.layer(private=True))
    def test_wrong_source_hash_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'source_hash'):self.scan(self.layer(body=b'changed'))
    def test_source_symlink_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'source_type'):self.scan(self.layer(kind=tarfile.SYMTYPE))
    def test_whiteout_and_opaque_removal_are_respected(self):
        for marker in ['.wh.example.py','.wh..wh..opq']:
            with self.subTest(marker=marker),self.assertRaisesRegex(RuntimeError,'source_hash'):self.scan(self.layer(),self.layer(whiteout=marker))
    def test_manifest_layer_order_selects_latest_source(self):
        result=self.scan(self.layer(),self.layer(body=b'new'),expected=b'new');self.assertEqual(result['hashes']['core/example.py'],hashlib.sha256(b'new').hexdigest())

if __name__=='__main__':unittest.main()
