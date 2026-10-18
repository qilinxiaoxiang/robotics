"""Rebase executable CAD/model input paths after extraction; preserve historical results."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
original='/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912'
inputs=['electrical/head-layout/final/head-mesh-mass-manifest.json',
        'dynamics/compact-prototype.config.json','dynamics/new-geometry.json']
def rebase(value):
    if isinstance(value,str) and value.startswith(original+'/'):
        return str(P.parent)+value[len(original):]
    if isinstance(value,list):return [rebase(x) for x in value]
    if isinstance(value,dict):return {k:rebase(v) for k,v in value.items()}
    return value
for name in inputs:
    path=P/name;old=json.loads(path.read_text());new=rebase(old)
    if old!=new:
        backup=path.with_name(path.name+'.before-relocation')
        if not backup.exists():backup.write_bytes(path.read_bytes())
        path.write_text(json.dumps(new,indent=2)+'\n')
        print('Updated',name)
    else:print('Already current',name)
