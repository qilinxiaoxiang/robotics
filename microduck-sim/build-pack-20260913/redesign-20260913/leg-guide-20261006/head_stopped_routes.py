"""Measured stop evidence for native head routes that remain physically unresolved."""
from pathlib import Path
import json,base64,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;source=D/'full-build-data.json';raw=source.read_bytes();source_hash=hashlib.sha256(raw).hexdigest();source_stat=source.stat();data=json.loads(raw);by={p['key']:p for p in data['parts']};solids={}
def solid(k):
 if k not in solids:
  p=by[k];m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True);solids[k]=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
 return solids[k]
capkeys=['head_cap','openrb','audio_carrier','amplifier','speaker','camera_pitch_foot','camera_cradle','camera_board']+[k for k,p in by.items() if p.get('fastenerId','').startswith(('E-openrb','E-audio_carrier','E-camera'))]
facekeys=['face_panel','pi','eye_trim'];jawkeys=['jaw_frame','motor15','lower_pad'];jawrot=trimesh.transformations.rotation_matrix(np.deg2rad(30),[0,1,0],[26.1,0,118.6146])
configs=[('shell-around-closed-jaw',['head_bottom'],['jaw_support','motor14','motor15','head_yaw_link','head_roll_ring_a','head_roll_ring_b','jaw_frame','lower_pad'],[0,0,-40],[]),('jaw-group-to-loose-support',jawkeys,['jaw_support'],[0,0,-32],[]),('face-into-open-bottom',facekeys,['head_bottom','jaw_support','motor14','motor15','head_yaw_link','jaw_frame','lower_pad','head_roll_ring_a','head_roll_ring_b'],[0,0,40],['jaw_frame','lower_pad']),('cap-over-installed-face',capkeys,['head_bottom','jaw_support','motor14','motor15','head_yaw_link','face_panel','pi','eye_trim','jaw_frame','lower_pad','head_roll_ring_a','head_roll_ring_b'],[0,0,48],['jaw_frame','lower_pad'])]
out={}
for name,moving,fixed,vector,posed in configs:
 fs={q:(solid(q).transform(jawrot[:3,:]) if q in posed else solid(q)) for q in fixed};v=np.array(vector,dtype=float)
 def contacts(t):
  hits={}
  for k in moving:
   s=solid(k).translate(v*t);bb=np.array(s.bounding_box()).reshape(2,3)
   for q,b in fs.items():
    qb=np.array(b.bounding_box()).reshape(2,3)
    if np.any(bb[1]<qb[0]) or np.any(qb[1]<bb[0]):continue
    value=max(0.,float((s^b).volume()))
    if value>1e-8:hits[k+'--'+q]=value
  return hits
 previous=1.;bracket=None
 for t in np.linspace(1,0,129):
  hits=contacts(float(t))
  if max(hits.values(),default=0)>.02:bracket=[previous,float(t)];break
  previous=float(t)
 assert bracket,(name,'no obstruction')
 safe,blocked=bracket
 for _ in range(16):
  mid=(safe+blocked)/2
  if max(contacts(mid).values(),default=0)>.02:blocked=mid
  else:safe=mid
 stop=min(1.,safe+.5/np.linalg.norm(v))
 while stop<1 and min(float(solid(k).translate(v*stop).min_gap(b,5)) for k in moving for b in fs.values())<=.1:stop=min(1.,stop+.25/np.linalg.norm(v))
 samples=[]
 for t in np.linspace(1,stop,int(np.ceil(np.linalg.norm(v)*(1-stop)/.25))+1):
  hits=contacts(float(t));assert not hits,(name,t,hits);samples.append({'t':float(t),'offset':(v*t).tolist(),'overlaps':hits})
 gaprows={k+'--'+q:float(solid(k).translate(v*stop).min_gap(b,5)) for k in moving for q,b in fs.items()};gap=min(gaprows.values());assert gap>.05
 r={'movingKeys':moving,'fixedKeys':fixed,'start':vector,'stop':(v*stop).tolist(),'contactOffset':(v*blocked).tolist(),'contactPairs':contacts(blocked),'stopGapMm':gap,'samples':samples,'posedFixedKeys':posed,'fixedPose':{'axis':[0,1,0],'pivot':[26.1,0,118.6146],'angleDegrees':30} if posed else None,'physicalFitAccepted':False,'status':'stopped-before-known-obstruction'};out[name]=r;print(name,{k:r[k] for k in ['stop','contactOffset','contactPairs','stopGapMm']},flush=True)
operation_ids={'shell-around-closed-jaw':'head-07','jaw-group-to-loose-support':'head-05','face-into-open-bottom':'head-close-01','cap-over-installed-face':'head-close-03'}
operations={op['id']:(mod,op) for mod in data['modules'] for op in mod['operations']}
errors=[];bindings=[]
def check(ok,message):
 if not ok:errors.append(message)
def vector_matches(actual,want):
 return isinstance(actual,list) and len(actual)==3 and np.allclose(actual,want,atol=1e-7,rtol=0)
for name,result in out.items():
 oid=operation_ids[name]
 if oid not in operations:
  errors.append(name+': canonical operation missing '+oid);continue
 mod,op=operations[oid];stop=op.get('motionStop',{})
 before=len(errors)
 check(vector_matches(stop.get('start'),result['start']),oid+': motionStop start differs from checked route')
 check(vector_matches(stop.get('stop'),result['stop']),oid+': motionStop endpoint differs from checked route')
 check(set(stop.get('movingKeys',[]))==set(result['movingKeys']),oid+': motionStop moving group differs from checked route')
 check(len(stop.get('movingKeys',[]))==len(result['movingKeys']),oid+': duplicate or omitted moving member')
 check(set(op.get('add',[])+op.get('moveKeys',[]))==set(result['movingKeys']),oid+': operation moving group differs from stop group')
 expected_pairs={tuple(p.split('--')) for p in result['contactPairs']}
 check(tuple(stop.get('contactPair',[])) in expected_pairs,oid+': named contact pair is not a measured obstruction')
 poses=op.get('fixedPoses',[])
 if result['posedFixedKeys']:
  check(len(poses)==1,oid+': must retain exactly the checked jaw pose')
  if len(poses)==1:
   pose=poses[0]
   check(set(pose.get('keys',[]))==set(result['posedFixedKeys']) and len(pose.get('keys',[]))==len(result['posedFixedKeys']),oid+': fixed pose attached group differs')
   check(vector_matches(pose.get('axis'),[0,1,0]) and vector_matches(pose.get('pivot'),[26.1,0,118.6146]) and pose.get('degrees')==30,oid+': fixed pose axis/pivot/angle differs')
 else:check(not poses,oid+': checked route requires closed jaw, no fixed pose override')
 present=set(mod['partKeys'])-set(mod.get('ownedPartKeys',[]))
 for prior in mod['operations']:
  present.update(prior['add'])
  if prior['id']==oid:break
 if 'isolatedPartKeys' in op:present.intersection_update(op['isolatedPartKeys'])
 check(set(result['movingKeys']+result['fixedKeys'])<=present,oid+': rendered state omits checked moving parts or obstacles '+str(sorted(set(result['movingKeys']+result['fixedKeys'])-present)))
 bindings.append({'operationId':oid,'route':name,'operationSha256':hashlib.sha256(json.dumps(op,sort_keys=True).encode()).hexdigest(),'passed':len(errors)==before,'motionStop':stop,'fixedPoses':poses,'visibleParts':sorted(present)})
current_hash=hashlib.sha256(source.read_bytes()).hexdigest()
check(current_hash==source_hash,'Source data changed during verification; rerun against rebuilt data')
report={'passed':not errors,'errors':errors,'sourceFile':str(source),'sourceSha256':source_hash,'sourceSha256AtCompletion':current_hash,'sourceMtimeNs':source_stat.st_mtime_ns,'sourceSizeBytes':len(raw),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'operationBindings':bindings,'scope':'Clear sampled partial routes only; full insertion remains unresolved.0.25mm maximum translation sampling.0.5mm initial margin beyond .02mm3 boundary, increased if needed for gap; independently zero-intersection and >.05mm gap at stop. Generated operation IDs, moving groups, stop endpoints, visible obstacles and jaw poses are bound to current data.','routes':out}
(D/'audit-20261008/head-stopped-routes.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':not errors,'errors':errors,'sourceSha256':source_hash}))
assert not errors,'\n'.join(errors)
