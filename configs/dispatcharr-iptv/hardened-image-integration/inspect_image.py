"""Read-only immutable-image hash verification. No source is exported.
No container/build/lifecycle operation; stream through the selected NEST profile.
"""
import hashlib, io, json, pathlib, subprocess, tarfile
IMAGE='sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21'
DOCKER=['docker','-H','unix:///var/run/docker.sock']
PINS={'core/xtream_codes.py': '702aa9eae38cc3fce733a2f42e66f5b2b68458a22fd95d57ed0dc14a9231c76d', 'apps/m3u/api_views.py': '1299f6d86af5bd86ca04087f3ca70120ee1b04686c182ea0682560f0b7165d63', 'apps/m3u/tasks.py': '921e0fea7273c0ce7d1b1380a4f675718fbc5cdb3bb0d38005cdae2b73cce981', 'apps/m3u/signals.py': '854c44f190e57a262e474e0d24a237c004a557a036a7dc527f05b1381ecd4bd3', 'apps/epg/api_views.py': 'df6ebcd84afe9237cb8ca2989d572170a2c8a325b85f8781d1d8becb217e2e4f', 'apps/epg/tasks.py': 'deb4792a39ed93c57da435ecc2a4fcdf5b4dad8f4e087d3afdb5d4f2b7932ff9', 'apps/epg/signals.py': '541c1157f01b794d05cf74b58eeaab521fa161273ce3430bb705955b94153e7a', 'core/api_urls.py': 'aa780f16f02f7bcffe5fdf26aa3f658a0e91190e84377540c75ec73b1dbce81e'}
READINESS={'apps/proxy/live_proxy/input/buffer.py': '17d77baba54923ef3414a7051eebed9c27a891eb1479dd9c68a299e0d5f89810', 'apps/proxy/live_proxy/input/manager.py': 'ce2400eb4bcdaec43ee571b7982f85ca2cd719eec9acb0282976edb3684245cf', 'apps/proxy/live_proxy/output/ts/generator.py': 'db9200e53419a9ca3acb19ad05df49d3a4c9c06567d3e659c26214cecf5e312b', 'apps/proxy/live_proxy/readiness.py': 'fb4882ba579b14b0a2f7aec7306c8f31e1c7bb5f6c3acacce1a40dc62de1143b'}
SELECTED=set(PINS)|set(READINESS)

class Prefix:
    def __init__(self,first,rest):self.first=first;self.rest=rest
    def read(self,n=-1):
        if n<0:raise RuntimeError('unbounded_read_refused')
        out=self.first[:n];self.first=self.first[n:]
        return out+self.rest.read(n-len(out)) if len(out)<n else out


def verify(image_id=None,expected=None):
    image_id=IMAGE if image_id is None else image_id
    expected={**PINS,**READINESS} if expected is None else expected
    selected_names=SELECTED if set(expected)==set(PINS)|set(READINESS) else set(expected)
    image=json.loads(subprocess.check_output(DOCKER+['image','inspect',image_id,'--format','{"id":{{json .Id}},"size":{{json .Size}}}']))
    if image['id']!=image_id:raise RuntimeError('image_identity_mismatch')
    process=subprocess.Popen(DOCKER+['image','save',image_id],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    layers={};manifest=None
    try:
        with tarfile.open(fileobj=process.stdout,mode='r|') as outer:
            for member in outer:
                if not member.isfile():continue
                stream=outer.extractfile(member)
                if member.name=='manifest.json':manifest=json.load(stream);continue
                first=stream.read(min(512,member.size))
                if first.lstrip().startswith((b'{',b'[')):continue
                found={};deleted=[];opaque=[]
                try:
                    with tarfile.open(fileobj=Prefix(first,stream),mode='r|*') as layer:
                        for item in layer:
                            name=item.name.removeprefix('./').removeprefix('app/')
                            if item.name.removeprefix('./').startswith('app/'):
                                if pathlib.PurePosixPath(name).name=='.wh..wh..opq':opaque.append(str(pathlib.PurePosixPath(name).parent))
                                elif pathlib.PurePosixPath(name).name.startswith('.wh.'):
                                    deleted.append(str(pathlib.PurePosixPath(name).with_name(pathlib.PurePosixPath(name).name[4:])))
                                elif name in selected_names:
                                    if not item.isfile() or item.size>2*1024*1024:raise RuntimeError('unexpected_source_type_or_size')
                                    found[name]=hashlib.sha256(layer.extractfile(item).read()).hexdigest()
                            if len(layer.members)>1000:layer.members.clear()
                except tarfile.ReadError:continue
                layers[member.name]=(found,deleted,opaque)
                if len(outer.members)>1000:outer.members.clear()
        if process.wait(timeout=30):raise RuntimeError('image_save_failed')
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=10)
    if not isinstance(manifest,list) or len(manifest)!=1:raise RuntimeError('image_manifest_mismatch')
    selected={}
    for name in manifest[0]['Layers']:
        if name not in layers:raise RuntimeError('missing_image_layer')
        found,deleted,opaque=layers[name]
        for key in list(selected):
            if key in deleted or any(d in ('.','') or key.startswith(d.rstrip('/')+'/') for d in opaque):del selected[key]
        selected.update(found)
    for name,wanted in expected.items():
        if name not in selected:raise RuntimeError('missing_source:'+name)
        if selected[name]!=wanted:raise RuntimeError('source_drift_stop:'+name+':'+selected[name])
    return {'base':image,'hashes':selected,'process_exited':True,'exit_code':0,'mode':'read_only_image_save_hashes_only_no_containers'}


def main():
    print(json.dumps(verify()))

if __name__=='__main__':main()
