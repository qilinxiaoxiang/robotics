"""Lightweight source split; no CAD imports or resident full scene."""
from pathlib import Path
import json,hashlib,os
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;p=H.parent/'leg-guide-20261006/full-build-data.json';C=D/'head-source-cache';C.mkdir(exist_ok=True)
with p.open() as f:x=json.load(f)
(C/'head-screws.json').write_text(json.dumps([q for q in x['screws'] if q.get('partKey')=='pi' or 'pi' in q.get('id','').lower()],indent=2)+'\n')
cfg=json.loads((H/'viewer-candidate.json').read_text());files=cfg['replacementMeshes']|{q['key']:q['mesh'] for q in cfg['additionalParts']};index={}
for q in x['parts']:
 if q['bounds'][1][2]>90:
  dest=C/(q['key']+'.json');dest.write_text(json.dumps(q,separators=(',',':')));index[q['key']]=dest.name
h=hashlib.sha256()
with p.open('rb') as f:
 for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
(C/'index.json').write_text(json.dumps({'sourceDataSha256':h.hexdigest(),'sourceFile':str(p.resolve()),'parts':index},indent=2)+'\n');print('cached',len(index))
