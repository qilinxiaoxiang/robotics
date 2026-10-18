from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;R=M.parents[2];G=R/'leg-guide-20261006';O=M.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 assert m.is_volume
 s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
base=json.loads((G/'full-build-data.json').read_text());obs={json.loads(p.read_text())['key']:json.loads(p.read_text())for p in O.glob('*.json')};rows=[];sources={str(G/'full-build-data.json'):sha(G/'full-build-data.json'),str(M/'active-topology.json'):sha(M/'active-topology.json'),str(D/'housing-static.json'):sha(D/'housing-static.json')}
for side,ids,thigh in [('right',[2,3],'right_thigh'),('left',[7,8],'thigh')]:
 op=next(m for m in base['modules']if m['id']==side+'-leg')['operations'][0];ob=obs[thigh];assert sha(ob['file'])==ob['sha256'];sources[ob['file']]=ob['sha256'];b=trimesh.load_mesh(ob['file']);b.apply_translation(ob.get('importTranslationMm',[0,0,0]));sb=solid(b)
 for mid in ids:
  vec=op['partApproachVectors'][f'motor{mid}'];assert vec==op['partApproachVectors'][f'motor{ids[0]}']
  for socket in [13,14]:
   pk=f'motor-{mid}-socket-{socket}';path=D/(pk+'-housing.stl');sources[str(path)]=sha(path);a=solid(trimesh.load_mesh(path));hits=[]
   for i in range(181):
    offset=np.array(vec)*(1-i/180);c=a.translate(offset)^sb;assert c.status()==mf.Error.NoError
    if c.volume()>1e-7:hits.append({'sample':i,'translationMm':offset.tolist(),'volumeMm3':c.volume(),'boundsMm':list(c.bounding_box())})
   rows.append({'port':pk,'guideOperation':op['id'],'vectorMm':vec,'fixedObstacle':thigh,'samples':181,'hits':hits});print(pk,len(hits),flush=True)
report={'passed':not any(r['hits']for r in rows),'sourceHashes':sources,'scriptSha256':sha(__file__),'rows':rows,'scope':'Both sockets on both thigh motors preplugged. All four housings travel with the two motors along their identical leg01 vectors against the fixed thigh. Relative housing/other motor and later reinforcing plate clearances inherit source-bound housing-static.json final arrangement because the common rigid translation does not change those pairs. Plate can be fitted after the motors. Flexible wires are fed loose, not swept as fixed shapes. This only checks the added connector bodies; bare-motor guide proof is independent.','sourceStaticExternalClear':json.loads((D/'housing-static.json').read_text())['externalClear']};assert report['sourceStaticExternalClear'];(D/'four-preplugged-delta.json').write_text(json.dumps(report,indent=2));print('passed',report['passed'])
