from pathlib import Path
import json,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent
nm=json.loads((M.parent/'ankle-wires/native-motors/manifest.json').read_text());ns=[r for r in nm['parts']if r['motor']==2];top=json.loads((M/'active-topology.json').read_text());data=json.loads((D/'joint-right.json').read_text());rows=[]
def solid(m):return mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)))
for w in data['strands']:
 if w['routeId']!='ttl-03-02':continue
 a=solid(trimesh.load_mesh(w['file']))
 for mid in [2,3]:
  T=np.array(top['ports'][f'motor-{mid}-socket-13']['transform'])
  for r in ns:
   m=trimesh.load_mesh(r['file']);m.apply_transform(T@np.linalg.inv(r['worldTransform']));assert m.is_volume;c=a^solid(m);v=c.volume()
   if v>1e-7:rows.append({'wire':w['key'],'motor':mid,'solid':r['solid'],'volumeMm3':v,'bounds':list(c.bounding_box())})
print(rows);(D/'inner-native-diagnostic.json').write_text(json.dumps(rows,indent=2))
