"""Measure a stopped lower-shell approach against every installed body part."""
from pathlib import Path
import base64,hashlib,json
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;data=json.loads((D/'full-build-data.json').read_text());by={p['key']:p for p in data['parts']};ss={};bounds={};bindings={}
def solid(k):
 if k not in ss:
  p=by[k];v=base64.b64decode(p['positionB64']);f=base64.b64decode(p['indexB64']);mesh=trimesh.Trimesh(np.frombuffer(v,'<f4').reshape(-1,3),np.frombuffer(f,'<u4').reshape(-1,3),process=True);s=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)));assert s.status()==mf.Error.NoError,(k,s.status());ss[k]=s;bounds[k]=mesh.bounds
  bindings[k]={'positionsSha256':hashlib.sha256(v).hexdigest(),'indicesSha256':hashlib.sha256(f).hexdigest(),'sourceTransformWorld':p['sourceTransformWorld']}
 return ss[k]
fixed=[];shell_operation=None
for mod in data['modules']:
 for op in mod['operations']:
  if 'head_bottom' in op['add']:
   shell_operation=op;break
  fixed+=op['add']
 if shell_operation:break
assert shell_operation is not None
fixed=sorted(set(k for k in fixed if by[k]['partKind']!='fastener'))
assert {'jaw_support','motor15','jaw_frame','lower_pad'}<=set(fixed), 'Current shell audit must include the already fitted jaw and lower pad'
for k in ['head_bottom']+fixed:solid(k)
def overlaps(z):
 translated=solid('head_bottom').translate([0,0,z]);out={};bb=bounds['head_bottom']+[0,0,z]
 for k in fixed:
  if np.any(bb[1]<bounds[k][0]) or np.any(bounds[k][1]<bb[0]):continue
  out[k]=max(0.,float((translated^solid(k)).volume()))
 return out
# The old -60 mm start intersects the already installed torso; use the open
# gap above it. The entire -40 mm route is checked, not only its endpoint.
old=overlaps(-60);assert max(old.values())>500
prev=-40;hit=None
for z in np.arange(-40,.0001,.25):
 vals=overlaps(float(z))
 if max(vals.values(),default=0)>.02:hit=float(z);break
 prev=float(z)
assert hit is not None
for _ in range(12):
 mid=(prev+hit)/2
 if max(overlaps(mid).values(),default=0)>.02:hit=mid
 else:prev=mid
stop=prev-.5
rows=[]
for z in np.linspace(-40,stop,int(np.ceil((40+stop)/.25))+1):
 vals=overlaps(float(z));assert max(vals.values(),default=0)<1e-8,(z,vals);rows.append({'offsetZMm':float(z),'maxOverlapMm3':max(vals.values(),default=0)})
moving=solid('head_bottom').translate([0,0,stop]);gaps={k:float(moving.min_gap(solid(k),2)) for k in fixed};assert min(gaps.values())>0
end=overlaps(0);contacts={}
for k,v in end.items():
 if v>.02:
  mesh=(solid('head_bottom')^solid(k)).to_mesh();vs=np.asarray(mesh.vert_properties)[:,:3];contacts[k]={'volumeMm3':v,'boundsMm':[vs.min(0).tolist(),vs.max(0).tolist()]}
path={'movingKeys':['head_bottom'],'fixedKeys':fixed,'start':[0,0,-40],'stop':[0,0,stop],'contactPair':'head_bottom--'+max(overlaps(hit),key=overlaps(hit).get),'firstThresholdCrossing':[0,0,hit],'thresholdMm3':.02,'retreatMm':.5,'minimumEndpointGapMm':min(gaps.values()),'samples':rows,'reason':'The original source lower-shell seats overlap the motor bottoms and roll rings. This preview stops clear; only an actual dry fit can establish whether this printed shell seats. Do not pull it closed with screws.'}
result={'problemIds':['P5','P6'],'checked':'2026-10-08','sourceBindings':bindings,'oldStartCollisions':{k:v for k,v in old.items() if v>.02},'path':path,'nominalFinalContacts':contacts,'physicalFitVerified':False,'scope':'Quarter-millimetre sampled clearance of a stopped approach; original geometry and final seat interference retained. Bounding-box spans are not penetration depths.'}
(D/'head-shell-fit-check.json').write_text(json.dumps(result,indent=2)+'\n');print('HEAD_SHELL_STOP_PASS',json.dumps({k:v for k,v in path.items() if k not in ['fixedKeys','samples']}))
