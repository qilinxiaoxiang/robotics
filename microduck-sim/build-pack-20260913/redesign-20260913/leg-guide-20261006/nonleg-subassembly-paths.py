"""Native-solid bench paths for the non-leg assembly repair, P5/P6."""
from pathlib import Path
import base64,hashlib,json
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent
data=json.loads((D/'full-build-data.json').read_text());parts={p['key']:p for p in data['parts']};solids={};bindings={}
def solid(k):
 if k not in solids:
  p=parts[k];vertices=base64.b64decode(p['positionB64']);faces=base64.b64decode(p['indexB64']);m=trimesh.Trimesh(np.frombuffer(vertices,'<f4').reshape(-1,3),np.frombuffer(faces,'<u4').reshape(-1,3),process=True)
  s=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)));assert s.status()==mf.Error.NoError,(k,str(s.status()));solids[k]=s
  bindings[k]={'positionsSha256':hashlib.sha256(vertices).hexdigest(),'indicesSha256':hashlib.sha256(faces).hexdigest(),'sourceTransformWorld':p['sourceTransformWorld']}
 return solids[k]
paths=[
 ('roll-ring-before-motor',['head_roll_ring_a'],['head_yaw_link','head_roll_ring_b'],[-60,0,0]),
 ('roll-motor-after-rings',['motor14'],['head_yaw_link','head_roll_ring_a','head_roll_ring_b'],[-60,0,0]),
 ('jaw-motor-in-detached-support',['motor15'],['jaw_support'],[0,60,0]),
 ('amplifier-on-detached-carrier',['amplifier'],['audio_carrier'],[0,0,60]),
 ('speaker-on-detached-carrier',['speaker'],['audio_carrier','amplifier'],[0,0,60]),
 ('populated-carrier-into-cap',['audio_carrier','amplifier','speaker'],['head_cap','openrb'],[0,0,-60]),
 ('jaw-support-group-to-shell',['jaw_support','motor15'],['head_bottom','motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b'],[0,0,60])]
results=[]
for name,moving,fixed,vector in paths:
 rows=[]
 for a in moving:
  for b in fixed:
   end=max(0.,float((solid(a)^solid(b)).volume()));samples=[max(0.,float((solid(a).translate(np.array(vector)*t)^solid(b)).volume())) for t in np.linspace(1,0,121)];peak=max(samples)
   if peak>.00001:rows.append({'moving':a,'fixed':b,'peakMm3':peak,'finalMm3':end,'excessOverFinalMm3':max(0.,peak-end)})
 result={'id':name,'moving':moving,'fixed':fixed,'startTranslationMm':vector,'samples':121,'stepMm':.5,'pairs':rows,'sourceFinalContact':any(r['finalMm3']>.02 for r in rows),'transitExcess':any(r['excessOverFinalMm3']>.02 for r in rows)}
 results.append(result);print(name,json.dumps(result),flush=True)
assert not any(r['transitExcess'] for r in results)
assert all(not r['sourceFinalContact'] for r in results[:-1])
assert results[-1]['sourceFinalContact'], 'Do not erase the nominal head-shell conflict'
(D/'nonleg-subassembly-paths.json').write_text(json.dumps({'problemIds':['P5','P6'],'checked':'2026-10-08','sourceBindings':bindings,'paths':results,'scope':'Finite .5 mm translation samples. First six paths have zero measured solid crossing; final support-to-shell path retains source final interference and is NOT fit acceptance. No physical assembly or actual cabling verified.','physicalFitVerified':False},indent=2)+'\n')
print('NONLEG_SUBASSEMBLY_PATHS_PASS')
