from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent/'motor-wires';O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
def solid(m):
 assert m.is_volume
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert a.status()==mf.Error.NoError and a.volume()>0;return a
top=json.loads((M/'active-topology.json').read_text());rows=[]
for rid in ['ttl-02-01','ttl-07-06']:
 r=next(r for r in top['routes']if r['id']==rid)
 for end in ['fromPort','toPort']:
  p=top['ports'][r[end]];lo,hi=np.array(p['housingLocalBounds']);m=trimesh.creation.box(hi-lo);m.apply_translation((hi+lo)/2);m.apply_transform(np.array(p['transform']));a=solid(m);f=D/(r[end]+'-housing.stl');m.export(f);hits=[]
  for qf in O.glob('*.json'):
   q=json.loads(qf.read_text());b=np.array(q['expectedFinalBoundsMm'])
   if q['key']=='motor'+str(p['motor']):continue
   if np.any(m.bounds[1]<b[0])or np.any(b[1]<m.bounds[0]):continue
   b=trimesh.load_mesh(q['file']);b.apply_translation(q.get('importTranslationMm',[0,0,0]));c=a^solid(b)
   if c.volume()>1e-7:hits.append({'key':q['key'],'volumeMm3':c.volume(),'bounds':list(c.bounding_box())})
  rows.append({'port':r[end],'file':str(f),'hits':hits});print(rows[-1],flush=True)
(D/'housing-static-check.json').write_text(json.dumps(rows,indent=2))
