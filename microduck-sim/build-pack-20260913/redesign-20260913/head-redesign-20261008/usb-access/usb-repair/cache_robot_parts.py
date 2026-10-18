"""Split source JSON once, allowing later checks to load a single obstacle.

Includes low trunk components that can approach an external cable as the neck
turns. A head-height cutoff must not remove them from articulation checks.
"""
from pathlib import Path
import hashlib,json,os
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1','Run through resource guard'
D=Path(__file__).resolve().parent;H=D.parent.parent
source=H.parent/'leg-guide-20261006/full-build-data.json'
raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest();data=json.loads(raw);del raw
dest=D/'robot-source-cache';dest.mkdir(exist_ok=True);parts={}
for part in data['parts']:
    key=part['key'];assert '/' not in key and '..' not in key
    name=key+'.json';(dest/name).write_text(json.dumps(part,separators=(',',':'))+'\n');parts[key]=name
index={'sourceFile':str(source.resolve()),'sourceDataSha256':digest,'parts':parts,'scope':'All source parts; no vertical cutoff or body exclusions'}
temp=dest/'index.tmp';temp.write_text(json.dumps(index,indent=2)+'\n');temp.replace(dest/'index.json')
print(json.dumps({'cachedParts':len(parts),'sourceSha256':digest}))
