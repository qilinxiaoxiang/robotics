from pathlib import Path
import base64,json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parents[1];G=R/'leg-guide-20261006';raw=(G/'full-build-data.json').read_bytes();data=json.loads(raw);parts={p['key']:p for p in data['parts']};P=parts['motor7'];T=np.array(P['sourceTransformWorld'])@np.array([[0,0,-1,-8],[-1,0,0,0],[0,1,0,0],[0,0,0,1]])
def box(lo,hi):return mf.Manifold.cube(np.array(hi)-lo).translate(lo)
def solid(p):
 v=np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3);t=trimesh.Trimesh(v,f,process=True);assert t.is_watertight and t.is_winding_consistent and t.volume>0
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(t.vertices,dtype=np.float64),np.ascontiguousarray(t.faces,dtype=np.uint64)));assert str(a.status())=='Error.NoError';return a
obstacles={'thigh':solid(parts['thigh']),'motor8_conservative':box(*parts['motor8']['bounds'])}
rows=[]
for sign in [1,-1]:
 cx=sign*8;h=box([cx-1.9,-13.75,-18.5],[cx+1.9,-4.25,-11.4]).transform(T[:3]);bb=np.array(h.bounding_box()).reshape(2,3)
 # Existing step01 motor approach = [0,-45,0], plate absent. Rectangular translations admit exact continuous swept box.
 lo=bb[0].copy();lo[1]-=45;swept=box(lo,bb[1]);tests=[]
 for key,a in obstacles.items():
  cut=swept^a;assert str(cut.status())=='Error.NoError'
  samples=[]
  for i in range(181):
   travel=-45+i*.25;q=h.translate([0,travel,0])^a;assert str(q.status())=='Error.NoError'
   if q.volume()>1e-6:samples.append({'travelY':travel,'intersectionMm3':q.volume(),'bounds':list(q.bounding_box())})
  tests.append({'obstacle':key,'continuousSweepIntersectionMm3':cut.volume(),'sampleCount':181,'collisions':samples})
 rows.append({'portSide':sign,'tests':tests})
o={'scope':'Only the newly added full housing envelope carried with motor7 along the existing step01 approach. Neither wire departure nor complete prewired assembly is certified.','sourceDataSha256':hashlib.sha256(raw).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'ports':rows,'plateAbsentPerOperationOrder':True,'physicalAssemblyVerified':False};(D/'preconnected-delta.json').write_text(json.dumps(o,indent=2)+'\n');print(json.dumps([{'port':r['portSide'],'tests':[{'obstacle':t['obstacle'],'sweptIntersection':t['continuousSweepIntersectionMm3'],'collidingSamples':len(t['collisions'])}for t in r['tests']]}for r in rows],indent=2))
