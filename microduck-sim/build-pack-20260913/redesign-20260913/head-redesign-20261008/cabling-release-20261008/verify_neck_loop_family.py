"""Finite constant-length external service-loop family; explicit connector boundary."""
from check_routes import *
import sys,itertools,ast
from scipy.optimize import brentq
for node in ast.parse((H/'usb-access/full-harness/build_harness.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name=='tube':exec(compile(ast.Module(body=[node],type_ignores=[]),'<parallel tube>','exec'))
ptail=np.array([1e9,1e9,1e9]);SIM=H.parent.parents[1];sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'));from assembly_fk import fk,TREE
B,_=fk();inv={k:np.linalg.inv(v) for k,v in B.items()};body={p['key']:p.get('body','jaw_soft') for p in data['parts']}
for k in obs:
 if k not in body:body[k]='jaw_soft'
body={k:b if b in B else 'trunk_base' for k,b in body.items()};limits={j:np.rad2deg(np.fromstring(next(x for x in TREE.iter('joint') if x.get('name')==j).get('range'),sep=' ')).tolist() for j in ['neck_pitch','head_pitch','head_yaw','head_roll']};cases=[]
for j,(lo,hi) in limits.items():
 for a in np.linspace(lo,hi,int(np.ceil((hi-lo)/5))+1):cases.append({j:float(a)})
for a in itertools.product([-20,0,20],[-30,0,30],[-90,0,90],[-20,0,20]):cases.append(dict(zip(limits,a)))
head=np.array([-31.,23.2,125]);torso=np.array([-66.,23.2,35.]);rows=[]
def curve(a,b,ta,c):
 p=np.array([a,a+ta*c,b+[-c,0,0],b]);t=np.linspace(0,1,181)[:,None];q=(1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t**2*p[2]+t**3*p[3];return q,float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum())
for deg in cases:
 poses,_=fk({k:np.deg2rad(v) for k,v in deg.items()});Ts={k:poses[k]@inv[k] for k in poses};T=Ts['jaw_soft'];p=(T@np.r_[head,1])[:3];axis=T[:3,:3]@[-1.,0,0]
 if curve(p,torso,axis,0)[1]>180:rows.append({'jointDegrees':deg,'lengthUnavailable':True});continue
 try:c=brentq(lambda c:curve(p,torso,axis,c)[1]-180,0,350)
 except ValueError:rows.append({'jointDegrees':deg,'lengthUnavailable':True});continue
 q,L=curve(p,torso,axis,c);mesh=tube(q,7);s=man(mesh);hh={}
 for k,o in obs.items():
  v=hits(s,o.transform(Ts[body[k]][:3,:]))
  if v>1e-4:hh[k]=v
 # Finite differences give a sampled radius diagnostic, not a continuous curvature proof.
 d=np.gradient(q,axis=0);dd=np.gradient(d,axis=0);curv=np.linalg.norm(np.cross(d,dd),axis=1)/np.maximum(np.linalg.norm(d,axis=1)**3,1e-12);rad=float(1/max(curv))
 rows.append({'jointDegrees':deg,'lengthMm':L,'minimumSampledCenterlineRadiusMm':rad,'intersectionsMm3':hh})
 if all(abs(x)<1e-8 for x in deg.values()) and not (D/'neck-loop-neutral-receiving-world.stl').exists():mesh.export(D/'neck-loop-neutral-receiving-world.stl')
out={'family':'180mm constant arclength cubic behindneck; round7mm receiving bundle','headPortalMm':head.tolist(),'torsoHoldingPointMm':torso.tolist(),'torsoPointBoundary':'Intermediate point outside IMU guard; NOT a measured sensor socket or final electrical endpoint. Thus this is a loop-section test, not a complete harness acceptance.','samples':len(rows),'rows':rows,'collisionSamples':sum(bool(x.get('intersectionsMm3')) for x in rows),'lengthUnavailableSamples':sum(x.get('lengthUnavailable',False) for x in rows),'minimumSampledRadiusMm':min(x.get('minimumSampledCenterlineRadiusMm',1e9) for x in rows),'headInteriorTrunkLengthMm':91.06637061435917,'knownSectionLengthBeforeFanoutsMm':271.0663706143592,'existing250mmAdequateForThisFamily':False,'remaining':'Both pin/socket fanouts and continuous supported deformation/strain restraint are absent; this family cannot release a cable or print.','sourceHashes':hashes,'accepted':False};(D/'neck-loop-family.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ['sourceHashes','rows']})
