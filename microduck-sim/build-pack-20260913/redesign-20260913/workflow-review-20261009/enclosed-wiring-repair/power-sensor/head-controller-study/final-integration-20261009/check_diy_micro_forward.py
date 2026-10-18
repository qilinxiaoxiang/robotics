"""Finite manufacturer's PCB-envelope check, not a claim of unknown plug seating depth."""
from pathlib import Path
import json,hashlib,gc,numpy as np,trimesh,manifold3d as mf
F=Path(__file__).resolve().parent
src=F/'original-inset-pi4-package.json';r=json.loads(src.read_text());T=np.array(r['piCurrentWorldDelta']);n=T[:3,:3]@np.array([-1.,0,0]);w=T[:3,:3]@np.array([0.,1,0]);v=T[:3,:3]@np.array([0.,0,1]);mouth=(T@np.array([44.,-9.9113773,133.6,1]))[:3]
def solid(m):
 assert m.is_volume;s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
# Socket-front to PCB near face is a receiving variable: vendor only publishes PCB 17x13.3x3.6, plug 11.
# Test one rearward-downwards PCB footprint with 5.5 mm seating allowance (NOT manufacturer datum).
M=np.eye(4);M[:3,:3]=np.column_stack([w,v,n]);M[:3,3]=mouth+v*6.65+n*(5.5+1.8)
m=trimesh.creation.box([17,13.3,3.6]);m.apply_transform(M);m.export(F/'diy-micro-forward-pcb-conditional-world.stl');a=solid(m);A=np.array(a.bounding_box()).reshape(2,3);checks=[]
for q in r['parts']:
 if q['group']=='pi_interface_conditional':continue
 p=Path(q['file']);assert hashlib.sha256(p.read_bytes()).hexdigest()==q['sha256'];b=trimesh.load_mesh(p);b.apply_transform(q['worldTransform']);repair=None
 if not b.is_volume:b=b.convex_hull;repair='source convex cover'
 B=b.bounds;sep=np.any(A[1]<B[0])or np.any(B[1]<A[0]);s=None if sep else a^solid(b)
 if s is not None:assert s.status()==mf.Error.NoError
 volume=0 if sep else max(0,s.volume());checks.append({'obstacle':q['key'],'volumeMm3':volume,'method':'bounds-separated'if sep else'valid-solid-intersection','sourceRepair':repair,'bounds':list(s.bounding_box())if volume>1e-6 else None})
 del b,s;gc.collect()
o={'sourceManifest':str(src),'sourceSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'pcbSource':'https://www.adafruit.com/product/4104','publishedDimensionsMm':{'pcb':[17,13.3,3.6],'plugLength':11},'positionAssumption':'Socket front to PCB near-face 5.5 mm; footprint extends toward Pi component side. Vendor does not publish seated datum, so this is conditional only. Up/down SKU roll must be matched to actual Micro shell key.','assumedPcbNearFaceOffsetMm':5.5,'meshBoundsMm':m.bounds.tolist(),'checks':checks,'hits':[q for q in checks if q['volumeMm3']>1e-6],'wholeHeadAccepted':False,'physicalConnectorAccepted':False};(F/'diy-micro-forward-pcb-conditional-check.json').write_text(json.dumps(o,indent=2)+'\n');print(json.dumps({'pairs':len(checks),'hits':o['hits'],'bounds':m.bounds.tolist()},indent=2))
