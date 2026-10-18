"""Check real jaw articulation exposes the cap drivers without removing parts."""
from pathlib import Path
import json,base64,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;raw=(D/'full-build-data.json').read_bytes();data=json.loads(raw);by={p['key']:p for p in data['parts']};solids={};bounds={}
def solid(k):
 if k not in solids:
  p=by[k];m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True);solids[k]=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)));bounds[k]=m.bounds
 return solids[k]
def intersect(s,q):
 b=solid(q);bb=np.array(s.bounding_box()).reshape(2,3)
 if np.any(bb[1]<bounds[q][0]) or np.any(bounds[q][1]<bb[0]):return None
 return s^b
keys=['jaw_frame','lower_pad'];fixed=sorted(set(by)-set(keys));pivot=[26.1,0,118.6146];rows=[];errors=[]
for angle in np.linspace(0,30,121):
 tr=trimesh.transformations.rotation_matrix(np.deg2rad(angle),[0,1,0],pivot);contacts=[]
 for k in keys:
  s=solid(k).transform(tr[:3,:])
  for q in fixed:
   inter=intersect(s,q)
   if inter is None:continue
   v=max(0.,float(inter.volume()))
   if v<=1e-7:continue
   bb=inter.bounding_box();allowed=k=='jaw_frame' and q=='motor15' and v<=.148 and bb[1]>=39.99899 and bb[4]<=40.00001 and bb[4]-bb[1]<=.00102
   contacts.append({'moving':k,'fixed':q,'volumeMm3':v,'boundsMm':list(bb),'boundedSourceFaceContact':allowed})
   if not allowed:errors.append({'angle':float(angle),'moving':k,'fixed':q,'volume':v})
 rows.append({'angleDegrees':float(angle),'contacts':contacts})
print('rotation scanned errors',errors[:5],flush=True)
cs=[c for c in data['screws'] if c.get('groupId')=='head_cap_closure'];tool=[]
closureids={c['id'] for c in cs};introduced=set()
for mod in data['modules']:
 for op in mod['operations']:
  introduced.update(op['add'])
  if closureids.intersection(op['screwIds']):assert 'upper_pad' not in introduced,'Upper pad must be installed after cap screws'
for angle in [0,30]:
 tr=trimesh.transformations.rotation_matrix(np.deg2rad(angle),[0,1,0],pivot)
 for c in cs:
  axis=np.array(c['world_axis']);head=np.array(c['world_center_mm']);m=trimesh.creation.cylinder(radius=1.5,height=45,sections=48);tt=trimesh.geometry.align_vectors([0,0,1],axis);tt[:3,3]=head+axis*23;m.apply_transform(tt);ss=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)));vs={}
  for q in by:
   if q=='upper_pad':continue # Installed only after cap screws; verified below.
   if q in keys:inter=ss^solid(q).transform(tr[:3,:])
   else:inter=intersect(ss,q)
   if inter is None:continue
   v=max(0.,float(inter.volume()))
   if v>1e-7:vs[q]=v
  tool.append({'angleDegrees':angle,'screwId':c['id'],'overlapsMm3':vs})
  if angle==30 and max(vs.values(),default=0)>.02:errors.append({'tool':c['id'],'angle':angle,'overlaps':vs})
report={'passed':not errors,'sourceDataSha256':hashlib.sha256(raw).hexdigest(),'pivotWorldMm':pivot,'rotationAxisWorld':[0,1,0],'openAngleDegrees':30,'stepDegrees':.25,'movingKeys':keys,'fixedKeys':fixed,'poses':rows,'driverDiameterMm':3,'driverLengthMm':45,'driverHeadOffsetMm':.5,'toolChecks':tool,'toolStateExcludesFutureParts':['upper_pad'],'errors':errors,'scope':'Source-mesh sampled articulation and complete model shaft corridors. Nominal jaw/motor face contact retained within named fixed slab. Does not establish finger/handle clearance, real joint calibration, or separate installation path.'}
(D/'audit-20261008/head-articulation-access.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':not errors,'errors':errors,'tools':tool}));assert not errors
