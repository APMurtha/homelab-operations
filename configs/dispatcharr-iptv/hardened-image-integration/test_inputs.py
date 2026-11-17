"""Offline input-verifier tests; these do not execute Django/Celery or Docker."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent

def module(name):
    spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

inspect=module('inspect_image');prepare=module('prepare_context')

def archive(files):
    result=io.BytesIO()
    with tarfile.open(fileobj=result,mode='w') as tar:
        for name,data in files.items():
            member=tarfile.TarInfo(name);member.size=len(data);tar.addfile(member,io.BytesIO(data))
    return result.getvalue()


def inspect_layers(layers,expected):
    names=['layer-'+str(i)+'/layer.tar' for i in range(len(layers))]
    outer=archive({**{n:archive(v) for n,v in zip(names,layers)},'manifest.json':json.dumps([{'Layers':names}]).encode()})
    process=types.SimpleNamespace(stdout=io.BytesIO(outer),wait=lambda **kw:0,poll=lambda:0)
    with patch.object(inspect,'PINS',{'apps/example.py':hashlib.sha256(expected).hexdigest()}),patch.object(inspect,'READINESS',{}),patch.object(inspect,'SELECTED',{'apps/example.py'}),patch.object(inspect.subprocess,'check_output',return_value=json.dumps({'id':inspect.IMAGE,'size':123}).encode()),patch.object(inspect.subprocess,'Popen',return_value=process),contextlib.redirect_stdout(io.StringIO()) as output:
        inspect.main()
    return output.getvalue()


class Inputs(unittest.TestCase):
    def test_streaming_hashes_return_no_source_bytes(self):
        text=inspect_layers([{'app/apps/example.py':b'SOURCE_CONTENT_NOT_FOR_EXPORT'}],b'SOURCE_CONTENT_NOT_FOR_EXPORT')
        self.assertNotIn('SOURCE_CONTENT_NOT_FOR_EXPORT',text)
        self.assertEqual(json.loads(text)['hashes']['apps/example.py'],hashlib.sha256(b'SOURCE_CONTENT_NOT_FOR_EXPORT').hexdigest())
    def test_latest_layer_wins(self):
        self.assertIn(hashlib.sha256(b'new').hexdigest(),inspect_layers([{'app/apps/example.py':b'old'},{'app/apps/example.py':b'new'}],b'new'))
    def test_whiteout_does_not_adopt_stale_source(self):
        with self.assertRaisesRegex(RuntimeError,'missing_source'):
            inspect_layers([{'app/apps/example.py':b'old'},{'app/apps/.wh.example.py':b''}],b'old')
    def test_opaque_app_root_does_not_adopt_stale_source(self):
        with self.assertRaisesRegex(RuntimeError,'missing_source'):
            inspect_layers([{'app/apps/example.py':b'old'},{'app/.wh..wh..opq':b''}],b'old')
    def test_context_requires_actual_base_and_readiness_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'context'
            with self.assertRaisesRegex(ValueError,'evidence_required'):
                prepare.prepare(Path('/unused'),output,{'base':{'id':prepare.BASE},'hashes':json.loads((prepare.HARDENING/'source-pins.json').read_text())})
            self.assertFalse(output.exists())

if __name__=='__main__':unittest.main(verbosity=2)
