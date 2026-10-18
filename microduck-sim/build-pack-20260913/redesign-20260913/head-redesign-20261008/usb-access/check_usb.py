from pathlib import Path
import sys,json,base64,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;R=H.parent;SIM=R.parents[1]
sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'))
from assembly_fk import fk
B,G=fk();pose=np.array(B['jaw_soft']);layout=json.loads((H/'curved-head/curved-layout.json').read_text());config=json.loads((H/'viewer-candidate.json').read_text());data=json.loads((R/'leg-guide-20261006/full-build-data.json').read_text())
def man(m):
 m=m.copy();m.process();return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def box(c,s):
 m=trimesh.creation.box(s);m.apply_translation(c);return m
T=np.array(layout['transformsFromGuideWorld']['openrb']);plug=trimesh.load(D/'full-harness/openrb-usb-c-published-envelope-world.stl',force='mesh');axis=(T@pose)[:3,:3]@np.array([0,0,1.])
obs={}
for p in data['parts']:
 k=p['key']
 if k in config['removedParts'] or p.get('partKind')=='fastener':continue
 if k in config['replacementMeshes']:m=trimesh.load(H/config['replacementMeshes'][k],force='mesh')
 else:m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
 obs[k]=m
for p in config['additionalParts']:
 if 'screw' not in p['key'] and not p.get('plugEnvelope'):obs[p['key']]=trimesh.load(H/p['mesh'],force='mesh')
# Optional integrated cap export includes actual local service openings.
cap=H/'curved-head/curved-cap-final-candidate-world.stl'
if cap.exists():obs['head_cap']=trimesh.load(cap,force='mesh')
solid=man(plug);hits={}
for k,m in obs.items():
 lo,hi=m.bounds;a,b=plug.bounds
 if np.any(lo>b) or np.any(a>hi):continue
 v=max(0.,float((solid^man(m)).volume()))
 if v>1e-4:hits[k]=v
path=[];solids={k:man(m) for k,m in obs.items()}
for distance in np.arange(30,-.001,-.25):
 moved=plug.copy().apply_translation(axis*distance);a,b=moved.bounds;collisions={}
 for k,m in obs.items():
  lo,hi=m.bounds
  if np.any(lo>b) or np.any(a>hi):continue
  v=max(0.,float((man(moved)^solids[k]).volume()))
  if v>1e-4:collisions[k]=v
 path.append({'offsetMm':round(float(distance),3),'intersectionsMm3':collisions})
pi_plug=trimesh.load(H/'curved-head/zero_w_usb_moulding-world.stl',force='mesh');pi_path=[]
for distance in np.arange(30,-.001,-.25):
 moved=pi_plug.copy().apply_translation([0,0,distance]);a,b=moved.bounds;collisions={};ms=man(moved)
 for k,m in obs.items():
  lo,hi=m.bounds
  if np.any(lo>b) or np.any(a>hi):continue
  v=max(0.,float((ms^solids[k]).volume()))
  if v>1e-4:collisions[k]=v
 pi_path.append({'offsetMm':round(float(distance),3),'intersectionsMm3':collisions})
pi_check={'outwardAxis':[0,0,1],'stepMm':.25,'samples':pi_path,'passed':not any(p['intersectionsMm3'] for p in pi_path),'topProtrusionBeyondNativeCapMm':float(pi_plug.bounds[1,2]-trimesh.load(H/'curved-head/community-curved-head-world.stl',force='mesh').bounds[1,2]),'receivingBoundary':'25x18x8 mm declared receiving envelope; this protrusion is connector space, not a restored smooth exterior for the complete connected robot.'}
r={'status':'receiving-envelope-investigation','source':'Adafruit 4472 published 27 mm moulding plus strain-relief length with seated shoulder unchanged; transverse 7x12 mm receiving boundary remains declared','sourceHashes':{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [H/'curved-head/curved-layout.json',H/'viewer-candidate.json']+([cap] if cap.exists() else [])},'worldFrame':pose.tolist(),'openrbRelocation':T.tolist(),'boundsMm':plug.bounds.tolist(),'outwardAxis':axis.tolist(),'intersectionsMm3':hits,'piUsbConnectorInsertion':pi_check,'connectorInsertion':{'stepMm':.25,'samples':path,'passed':not any(p['intersectionsMm3'] for p in path)},'completeCableRouteVerified':False,'physicalFitVerified':False};(D/'usb-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['connectorInsertion','piUsbConnectorInsertion']}));print('USB_CONNECTOR_INSERTION',r['connectorInsertion']['passed'])

print('PI_USB_CONNECTOR_INSERTION',pi_check['passed'],[p for p in pi_path if p['intersectionsMm3']][-3:])
