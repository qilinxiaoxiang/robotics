from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent/'motor-wires';O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 assert m.is_volume
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert a.status()==mf.Error.NoError;return a
top=json.loads((M/'active-topology.json').read_text());rows=[]
for rid in ['ttl-02-01','ttl-07-06']:
 rr=next(r for r in top['routes']if r['id']==rid)
 for label in ['fromPort','toPort']:
  key=rr[label];port=top['ports'][key];m=trimesh.load_mesh(D/(key+'-housing.stl'));a=solid(m);v=np.array(port['outward']);end=m.bounds+v*15;bb=np.array([np.minimum(m.bounds[0],end[0]),np.maximum(m.bounds[1],end[1])]);checks=[]
  for f in O.glob('*.json'):
   ob=json.loads(f.read_text());obb=np.array(ob['expectedFinalBoundsMm'])
   if ob['key'].startswith('motor'):continue
   if np.any(bb[1]<obb[0])or np.any(obb[1]<bb[0]):continue
   assert sha(ob['file'])==ob['sha256'];om=trimesh.load_mesh(ob['file']);om.apply_translation(ob.get('importTranslationMm',[0,0,0]));b=solid(om);samples=[]
   for t in np.linspace(0,15,61):
    cut=a.translate(v*t)^b;assert cut.status()==mf.Error.NoError;vol=cut.volume()
    if vol>1e-7:samples.append({'withdrawalMm':float(t),'overlapMm3':vol,'bounds':list(cut.bounding_box())})
   checks.append({'key':ob['key'],'sourceSha256':ob['sha256'],'collisionSamples':samples})
  out={'route':rid,'port':key,'axis':v.tolist(),'housingFile':str(D/(key+'-housing.stl')),'checks':checks,'blockedBy':[x['key']for x in checks if x['collisionSamples']]};rows.append(out);print(key,out['blockedBy'],flush=True)
(D/'plug-access.json').write_text(json.dumps({'scope':'0..15mm axial full-housing approach/withdrawal at0.25mm samples, unchanged original printed/structural objects. Own standard mating separately documented; grip/hand access not certified.','topologySha256':sha(M/'active-topology.json'),'ports':rows},indent=2))
