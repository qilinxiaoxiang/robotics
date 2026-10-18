import base64,hashlib,json,sys
from pathlib import Path
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;G=D.parents[2]/'leg-guide-20261006';opid=sys.argv[1]
packet=json.loads((D/'station-inputs'/f'{opid}.json').read_text());row=packet['station'];op=row['operation'];parts={p['key']:p for p in packet['parts']};cache={}
old=json.loads((D/'original-neck-part.json').read_text())
def build(p):
 m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True);s=mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
added=build(parts['neck_pitch'])-build(old);assert added.status()==mf.Error.NoError and added.volume()>0
bounds={k:np.array(p['bounds']) for k,p in parts.items()}
def solid(k):
 if k not in cache:cache[k]=build(parts[k])
 return cache[k]
def vol(a,b):
 ba=np.array(a.bounding_box()).reshape(2,3);bb=np.array(b.bounding_box()).reshape(2,3)
 if np.any(ba[1]<bb[0]) or np.any(bb[1]<ba[0]):return 0.
 return max(0,float((a^b).volume()))
rows=[]
if opid in ['neck-09','neck-11']:
 v=np.array(op['approachVector']);n=int(np.ceil(np.linalg.norm(v)/.25))+1
 for k in row['fixedParts']:
  # swept AABB is a complete continuous separation check where disjoint.
  box=np.array(added.bounding_box()).reshape(2,3);sweep=np.array([np.minimum(box[0],box[0]+v),np.maximum(box[1],box[1]+v)])
  if np.any(sweep[1]<bounds[k][0]) or np.any(bounds[k][1]<sweep[0]):rows.append({'moving':'neck_pitch_added_seats','fixed':k,'samples':n,'maxMm3':0,'aabbSeparated':True});continue
  b=solid(k);vv=[vol(added.translate(v*t),b) for t in np.linspace(1,0,n)];rows.append({'moving':'neck_pitch_added_seats','fixed':k,'samples':n,'maxMm3':max(vv)})
else:
 moving=op.get('moveKeys') or op['add']
 for k in moving:
  if k=='neck_pitch':continue
  v=np.array(op.get('partApproachVectors',{}).get(k,op.get('approachVector',parts[k].get('approachVector',[0,35,20]))));n=int(np.ceil(np.linalg.norm(v)/.25))+1;b=solid(k);vv=[vol(b.translate(v*t),added) for t in np.linspace(1,0,n)];rows.append({'moving':k,'fixed':'neck_pitch_added_seats','samples':n,'maxMm3':max(vv)})
out={'passed':all(r['maxMm3']<1e-5 for r in rows),'operationId':opid,'rows':rows,'addedSeatVolumeMm3':added.volume(),'inputSha256':hashlib.sha256((D/'station-inputs'/f'{opid}.json').read_bytes()).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'Integral neck-seat added material only; unchanged source material inherits prior operation-specific receipts.'}
(D/f'{opid}-seat-delta.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));sys.exit(0 if out['passed'] else 1)
