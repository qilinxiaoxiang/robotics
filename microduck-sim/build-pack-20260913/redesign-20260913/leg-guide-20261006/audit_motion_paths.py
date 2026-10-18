"""Sample the displayed translations against all prior visible assembly meshes.

This detects crossings; final-pose interference is reported separately and is
never proof of a valid rigid fit. No hardware or geometry is changed.
"""
from pathlib import Path
import argparse,base64,hashlib,json
import numpy as np
import trimesh
import manifold3d as mf
D=Path(__file__).resolve().parent
PARSER=argparse.ArgumentParser()
PARSER.add_argument('--data',type=Path,default=D/'full-build-data.json')
PARSER.add_argument('--output',type=Path,default=D/'motion-path-audit.json')
PARSER.add_argument('--module')
PARSER.add_argument('--suggest',action='store_true')
PARSER.add_argument('--nonleg',action='store_true')
PARSER.add_argument('--samples',type=int,default=17)
PARSER.add_argument('--step',type=float)
args=PARSER.parse_args()
data=json.loads(args.data.read_text());parts={p['key']:p for p in data['parts']};solids={};bounds={};rows=[];suggestions=[];poseTransforms={}
legacy=dict(thigh=[0,0,0],plate=[0,90,0],motor7=[0,40,0],motor8=[0,60,0],lower=[0,-40,0],motor6=[0,-38,0],smallring=[0,32,0],ankle=[0,40,0],foot=[0,0,-32],hip=[0,40,0],yaw=[40,0,0],passive=[0,0,38],motor9=[0,0,42],motor10=[0,0,45],ring7=[0,26,0],ring8=[0,26,0],ring9=[28,0,0])
def solid(k):
 if k not in solids:
  p=parts[k];m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
  s=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
  if s.status()!=mf.Error.NoError: raise ValueError((k,str(s.status())))
  solids[k]=s;bounds[k]=m.bounds
 return solids[k]
def vector(op,k):
 p=parts[k]
 if k in op.get('partApproachVectors',{}):return op['partApproachVectors'][k]
 if k in op.get('moveKeys',[]) and 'approachVector' in op:return op['approachVector']
 if k.startswith(('washer','nut_')):
  c=next(c for c in data['screws'] if c['id']==p['fastenerId']);return np.array(c['world_axis'])*(-12 if k.startswith('nut_') or 'nut side' in p['name'] else 12)
 return op.get('partApproachVectors',{}).get(k,op.get('approachVector',legacy.get(k,p.get('approachVector',[0,35,20]))))
def overlap(a,b,offset):
 sa=solid(a);sb=solid(b);ba=bounds[a];bb=bounds[b]
 if a in poseTransforms:
  sa=sa.transform(poseTransforms[a]);ba=np.array(sa.bounding_box()).reshape(2,3)
 if b in poseTransforms:
  sb=sb.transform(poseTransforms[b]);bb=np.array(sb.bounding_box()).reshape(2,3)
 bo=ba+offset
 if np.any(bo[1]<bb[0]) or np.any(bb[1]<bo[0]):return 0.
 return max(0.,float((sa.translate(offset)^sb).volume()))
for mod in data['modules']:
 if args.module and args.module!=mod['id']:continue
 if args.nonleg and 'leg' in mod['id']:continue
 seen=set(mod['partKeys'])-set(mod.get('ownedPartKeys',[]))
 for op in mod['operations']:
  poseTransforms.clear()
  for pose in op.get('fixedPoses',[]):
   axis=np.array(pose['axis'],float);axis/=np.linalg.norm(axis);a=axis;K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]]);t=np.deg2rad(pose['degrees']);R=np.eye(3)+np.sin(t)*K+(1-np.cos(t))*(K@K);p=np.array(pose['pivot']);T=np.column_stack([R,p-R@p])
   for k in pose['keys']:poseTransforms[k]=T
  seen.update(op['add']); moving=list(dict.fromkeys(op['add']+op.get('moveKeys',[])))
  if op.get('requiresPhysicalFit') or (op.get('animationBlockedReason') and not op.get('motionStop')):
   rows.append(dict(module=mod['id'],operation=op['id'],title=op['title'],status='explicit-fit-checkpoint'));continue
  visible=seen & set(op.get('isolatedPartKeys',seen));moving=[k for k in moving if k in visible];grouped=bool(op.get('moveKeys'));fixed=visible-set(moving)
  for n,k in enumerate(moving):
   v=np.array(vector(op,k),dtype=float)
   stop=op.get('motionStop')
   start=np.array(stop['start']) if stop and k in stop['movingKeys'] else v
   finish=np.array(stop['stop']) if stop and k in stop['movingKeys'] else np.zeros(3)
   if not np.linalg.norm(v):continue
   if op.get('motionWaypoints') and k in op['motionWaypoints']['movingKeys']:
    way=np.array(op['motionWaypoints']['points']);offsets=[]
    for aa,bb in zip(way[:-1],way[1:]):offsets.extend([aa+(bb-aa)*t for t in np.linspace(0,1,int(np.ceil(np.linalg.norm(bb-aa)/(args.step or 1)))+1)])
   else:offsets=[finish+(start-finish)*t for t in np.linspace(1,0,int(np.ceil(np.linalg.norm(start-finish)/args.step))+1 if args.step else args.samples)]
   obstacles=fixed if grouped else fixed|set(moving[:n])
   targets=[]
   for q in sorted(obstacles):
    if q==k:continue
    end=overlap(k,q,np.zeros(3)); values=[overlap(k,q,offset) for offset in offsets]
    mx=max(values)
    if mx>end+.02:targets.append(q)
    if mx>.02:rows.append(dict(module=mod['id'],operation=op['id'],title=op['title'],moving=k,fixed=q,vector=v.tolist(),maxOverlapMm3=mx,finalOverlapMm3=end,preterminalMaxMm3=max(values[:-1],default=0),positiveSampleFractions=[float(t) for t,vv in zip(np.linspace(1,0,len(values)),values) if vv>.02],excessOverFinalMm3=max(0,mx-end),status='crossing' if mx>end+.02 else 'source-final-contact',samples=len(values)))
   if args.suggest and targets and not grouped:
    distance=max(28,float(np.linalg.norm(v)));candidates=[-v]+[np.array(axis)*distance for axis in [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]]]
    rotation=np.array(parts[k].get('sourceTransformWorld',np.eye(4)))[:3,:3]
    candidates += [rotation[:,i]*sign*distance for i in range(3) for sign in [1,-1]]
    related=[c for c in data['screws'] if c.get('partKey')==k or k=='motor'+str((c.get('servo_ids') or [''])[0])]
    candidates += [np.array(c['world_axis'])*sign*distance for c in related for sign in [1,-1]]
    best=None
    for alt in candidates:
     excess=0.;worst=None
     for q in sorted(obstacles):
      end=overlap(k,q,np.zeros(3));peak=max(overlap(k,q,alt*t) for t in np.linspace(1,0,args.samples))
      if peak-end>excess:excess=peak-end;worst=q
      if best and excess>best['excessOverFinalMm3']:break
     if best is None or excess<best['excessOverFinalMm3']:best=dict(module=mod['id'],operation=op['id'],moving=k,vector=alt.tolist(),excessOverFinalMm3=excess,worst=worst)
     if excess<=.02:break
    suggestions.append(best);print('SUGGEST',json.dumps(best),flush=True)
  print(mod['id'],op['id'],'done',flush=True)
out=dict(problemIds=['P5','P6'],dataSha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),sampling=args.samples,maxStepMm=args.step,scope='Finite translation samples against visible installed parts. Screwdriver access uses separate verifier. Does not certify continuous clearance, flexible cables, or printed fit.',rows=rows,suggestions=suggestions,crossings=sum(r['status']=='crossing' for r in rows))
args.output.write_text(json.dumps(out,indent=2)+'\n');print('CROSSINGS',out['crossings'])

if out["crossings"] and not args.suggest: raise SystemExit(1)
