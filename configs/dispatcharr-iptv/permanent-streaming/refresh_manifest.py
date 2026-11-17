"""Local source packaging only. Does not connect, install, build or execute services."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
           and p.name not in ['manifest.json','validation-results.json']}
    (ROOT/'manifest.json').write_text(json.dumps({'schema':1,'files':files},indent=2)+'\n')
