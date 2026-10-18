"""One registered motor / two source-defined sockets; print surrounds only.
A conservative whole housing can prove clearance, not certify a collided subset.
"""
from pathlib import Path
import json,base64,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parents[1];G=R/'leg-guide-20261006'
x=json.loads((G/'full-build-data.json').read_text());parts={p['key']:p for p in x['parts']}
S=np.array([[0,0,-1,-8],[-1,0,0,0],[0,1,0,0],[0,0,0,1.]])
T=np.array(parts['motor7']['sourceTransformWorld'])@S

def decode(p):
 v=np.frombuffer(base64.b64decode(p['positionB64']),dtype='<f4').reshape(-1,3).astype(float)
 f=np.frombuffer(base64.b64decode(p['indexB64']),dtype='<u4').reshape(-1,3)
 m=trimesh.Trimesh(v,f,process=True);assert m.is_watertight and m.is_winding_consistent and m.volume>0,p['key']
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert str(a.status())=='Error.NoError' and a.volume()>0,p['key'];return a

def world_box(lo,hi):
 a=mf.Manifold.cube(np.array(hi)-lo).translate(lo);return a.transform(T[:3])

def bbox(a):
 return list(a.bounding_box())

rows=[]
# Port housing envelope spans x=header outer thickness, y=JST EHR-3 width9.5.
# Board plane at stepz=-10.4; combined mated height8.1 -> outer shoulder -18.5.
# Entire7.1 high rectangle includes0.6 top lip, even if body dimension6.5 excludes it.
for sign in [1,-1]:
 cx=sign*8.0
 housing=world_box([cx-1.9,-13.75,-18.5],[cx+1.9,-4.25,-11.4])
 direction=(T[:3,:3]@np.array([0,0,-1.])).tolist()
 # Generic handling clearance allowance, not a claim about a particular person's fingertips.
 handling=world_box([cx-3.9,-15.75,-30.5],[cx+3.9,-2.25,-16.4])
 port={'side':sign,'mouthStepMm':[sign*7.7,-9,-16.4],'mouthWorldMm':(T@np.array([sign*7.7,-9,-16.4,1]))[:3].tolist(),'outwardWorld':direction,'housingBoundsWorld':bbox(housing),'pairs':[]}
 for key in ['thigh','plate','motor8','ring7']:
  obstacle=(mf.Manifold.cube(np.array(parts[key]['bounds'][1])-parts[key]['bounds'][0]).translate(parts[key]['bounds'][0]) if key=='motor8' else decode(parts[key]));tests={}
  for name,moving in [('fullHousing',housing),('handlingAllowance',handling)]:
   samples=[]
   for i in range(81):
    travel=20-i*.25;a=moving.translate(np.array(direction)*travel);cut=a^obstacle;vol=cut.volume();assert str(cut.status())=='Error.NoError'
    samples.append({'travelMm':travel,'intersectionMm3':vol,'bounds':bbox(cut) if vol>1e-8 else None})
   tests[name]={'count':len(samples),'maximumIntersectionMm3':max(r['intersectionMm3'] for r in samples),'finalIntersectionMm3':samples[-1]['intersectionMm3'],'firstCollision':next((s for s in samples if s['intersectionMm3']>1e-6),None),'samples':samples}
  port['pairs'].append({'obstacle':key,'geometryKind':'conservative-bounds-pending-native-check' if key=='motor8' else 'source-mesh','tests':tests})
 rows.append(port)
output={'candidateOnly':True,'motor':'motor7','station':'Left thigh after source step04, with ring7; case/rear screws not included in this initial local screen.','sampleStepMm':.25,'sourceSha256':hashlib.sha256((G/'full-build-data.json').read_bytes()).hexdigest(),'stepToWorld':T.tolist(),'ports':rows,'scope':'Conservative housing bounding solid against actual surrounding meshes; own socket mating not part of this collision screen. Handling is stated receiving allowance, not human validation.'}
(D/'knee-station-initial.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps([{'side':p['side'],'mouth':p['mouthWorldMm'],'pairs':[{'part':a['obstacle'],**{k:v['maximumIntersectionMm3'] for k,v in a['tests'].items()}} for a in p['pairs']]}for p in rows],indent=2))
