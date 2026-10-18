"""P5/P6: classify sampled rigid-head collisions, without waiving cable failures.
This is a design test; no physical joint range or runtime calibration is changed.
"""
from pathlib import Path
import json,hashlib,itertools,numpy as np,base64,trimesh
D=Path(__file__).resolve().parent;H=D.parent.parent;OLD=D.parent/'full-harness'
ns={'__file__':str(OLD/'build_harness.py')}
exec((OLD/'build_harness.py').read_text().split('# PUBLISHED_CONNECTOR_FROM_SOURCE_SHOULDER')[0],ns)
obs,data,man,hits= (ns[k] for k in ['obs','data','man','hits'])
import sys
SIM=H.parent.parents[1];FK=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py'
sys.path.insert(0,str(FK.parent));from assembly_fk import fk,TREE
B,_=fk(); inv={k:np.linalg.inv(v) for k,v in B.items()};bodymap={p['key']:p.get('body','jaw_soft') for p in data['parts']}
for k in obs:bodymap.setdefault(k,'jaw_soft')
unknown={k:b for k,b in bodymap.items() if b not in B};bodymap={k:b if b in B else 'trunk_base' for k,b in bodymap.items()}
js=['neck_pitch','head_pitch','head_yaw','head_roll'];limits={j:np.rad2deg(np.fromstring(next(x for x in TREE.iter('joint') if x.get('name')==j).get('range'),sep=' ')).tolist() for j in js}
cases=[]
for j,(lo,hi) in limits.items():
 for a in np.linspace(lo,hi,int(np.ceil((hi-lo)/5))+1):cases.append({j:float(a)})
for a in itertools.product([-20,0,20],[-30,0,30],[-90,0,90],[-20,0,20]):cases.append(dict(zip(js,a)))
basepart=next(p for p in data['parts'] if p['key']=='head_bottom')
original_bottom=man(trimesh.Trimesh(np.frombuffer(base64.b64decode(basepart['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(basepart['indexB64']),'<u4').reshape(-1,3),process=True))
native={'head_cap':man(ns['load'](H/'curved-head/community-curved-head-world.stl')),'head_bottom':original_bottom}
# Use rigid shell/bottom only. Electronics-layout changes must not silently alter this baseline.
baseline_contacts={}
for part,obj in native.items():
 for k,o in obs.items():
  if bodymap[k]=='jaw_soft':continue
  v=hits(obj,o)
  if v>1e-4:baseline_contacts[part+'--'+k]=v
rows=[]
for index,q in enumerate(cases):
 poses,_=fk({k:np.deg2rad(v) for k,v in q.items()});T=poses['jaw_soft']@inv['jaw_soft'];intersections={};original_intersections={};baseline_contact_rows={}
 for part in ['head_cap','head_bottom']:
  moved=obs[part].transform(T[:3])
  for k,o in obs.items():
   b=bodymap[k]
   if b=='jaw_soft':continue
   Tb=poses[b]@inv[b];v=hits(moved,o.transform(Tb[:3]))
   if v>1e-4:intersections[part+'--'+k]=v
   v0=hits(native[part].transform(T[:3]),o.transform(Tb[:3]))
   if v0>1e-4:
    pair=part+'--'+k
    if pair in baseline_contacts and v0<=baseline_contacts[pair]+.001:baseline_contact_rows[pair]=v0
    else:original_intersections[pair]=v0
 rows.append({'jointDegrees':q,'rigidIntersectionsMm3':intersections,'nativeShellOriginalBottomIntersectionsMm3':original_intersections,'sourceZeroPoseContactMm3':baseline_contact_rows})
 if index%25==0:print(index,len(cases),flush=True)
fail=[r for r in rows if r['rigidIntersectionsMm3']]
cal=SIM/'build-pack-20260913/phase1/runtime/calibration.template.json'
report={'problemIds':['P5','P6'],'scope':'Sampled rigid shell/bottom domain only; not a new mechanical range and not a cable-collision waiver','sourceJointLimitsDegrees':limits,'totalSamples':len(rows),'rigidBlockedSamples':len(fail),'nativeBlockedSamples':sum(bool(r['nativeShellOriginalBottomIntersectionsMm3']) for r in rows),'samples':rows,'unmatchedBodies':unknown,'runtimeSource':{'path':str(cal.relative_to(SIM)),'sha256':hashlib.sha256(cal.read_bytes()).hexdigest(),'physicalCalibrationConfirmed':json.loads(cal.read_text())['physical_calibration_confirmed'],'meaning':json.loads(cal.read_text())['joint_limits_source']['meaning']},'sourceHashes':ns['sourceHashes']|{'viewer-candidate.json':hashlib.sha256((H/'viewer-candidate.json').read_bytes()).hexdigest(),'assembly_fk.py':hashlib.sha256(FK.read_bytes()).hexdigest()},'sourceZeroPoseContactCeilingsMm3':baseline_contacts,'contactScope':'Only explicitly named existing zero-pose interface pairs, bounded by original zero-pose volume+0.001mm3; no intermediate/new pair waivers','runtimeLimitsChanged':False,'physicalFitVerified':False}
(D/'rigid-domain.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'samples':len(rows),'rigidBlocked':len(fail),'failedDegrees':[r['jointDegrees'] for r in fail]}),flush=True)
