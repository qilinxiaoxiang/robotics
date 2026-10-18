from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[2];M=D.parents[1]/'motor-wires'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert a.status()==mf.Error.NoError and a.volume()>0;return a
routes=json.loads((D/'data-boundary-v2.json').read_text())['parts'];top=json.loads((M/'active-topology.json').read_text());source=W/'leg-ports/manufacturer-motor-components.json';j=json.loads(source.read_text());S=np.array([[0,0,-1,-8],[-1,0,0,0],[0,1,0,0],[0,0,0,1.]])
rows=[]
expanded=[dict(r,motorNumber=n)for r in routes for n in ([5,12]if r['key']=='data_12_05'else[10])]
for r in expanded:
 num=r['motorNumber'];T=np.array(top['ports'][f'motor-{num}-socket-'+('14' if num==12 else '13')]['transform'])@S
 a=solid(trimesh.load(r['file'],force='mesh'))
 for comp in j['solids']:
  if comp['index'] in j['excludesUninstalledRearIdlerSolids']:continue
  mesh=trimesh.Trimesh(comp['vertices'],comp['faces'],process=True);mesh.apply_transform(T);b=solid(mesh);c=a^b
  rows.append({'route':r['key'],'motor':num,'sourceSolid':comp['index'],'volumeMm3':c.volume(),'boundsMm':list(c.bounding_box()) if c.volume()>1e-7 else None})
 print(r['key'],[(x['sourceSolid'],x['volumeMm3'])for x in rows if x['route']==r['key'] and x['volumeMm3']>1e-7],flush=True)
(D/'data-boundary-v2-own-motors.json').write_text(json.dumps({'complete':True,'expectedPairs':len(expanded)*(len(j['solids'])-len(j['excludesUninstalledRearIdlerSolids'])),'pairs':rows,'passed':all(x['volumeMm3']<1e-7 for x in rows),'sourceHashes':{str(f):sha(f)for f in [source,M/'active-topology.json',D/'data-boundary-v2.json',Path(__file__)]}},indent=2)+'\n')
