"""Finite rigid tie/lock checks, deliberately not a flexible-wire simulator."""
import json,sys,itertools,hashlib
from pathlib import Path
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).parent;O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles';SIM=D.parents[4];FK=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py';G=D.parents[2]/'leg-guide-20261006/full-build-data.json'
sys.path.insert(0,str(FK.parent));from assembly_fk import fk
B,_=fk();data=json.loads(G.read_text());body={p['key']:p.get('body','trunk_base') for p in data['parts']};source=json.loads((D/'retention-plan.json').read_text());obs=[json.loads(p.read_text())for p in O.glob('*.json')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def solid(m):
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert str(a.status())=='Error.NoError' and a.volume()>0;return a
rows=[]
for side in ['right','left']:
 poses=[(r,p,0)for r,p in itertools.product([-22,0,22],[-90,0,90])]+[(0,0,-90),(0,0,90)]
 for ri,pi,ki in poses:
  P,_=fk({side+'_hip_roll':np.deg2rad(ri),side+'_hip_pitch':np.deg2rad(pi),side+'_knee':np.deg2rad(ki)})
  for part in [p for p in source['parts'] if p['key']==side+'-case-anchor']:
   owner=part['worldBody'];T=P[owner]@np.linalg.inv(B[owner]);tie=trimesh.load_mesh(part['file']);tie.apply_transform(T);a=solid(tie);exact=[];culled=[];same=[]
   for o in obs:
    obody=body.get(o['key'],'trunk_base')
    if obody==owner:same.append(o['key']);continue
    U=P[obody]@np.linalg.inv(B[obody]);bb=np.array(o['expectedFinalBoundsMm']);v=np.array(list(itertools.product(*zip(bb[0],bb[1]))));v=v@U[:3,:3].T+U[:3,3];lo=v.min(axis=0);hi=v.max(axis=0)
    if np.any(tie.bounds[1]<lo)or np.any(hi<tie.bounds[0]):culled.append(o['key']);continue
    m=trimesh.load_mesh(o['file']);m.apply_translation(o.get('importTranslationMm',[0,0,0]));m.apply_transform(U);cut=a^solid(m);vol=cut.volume();exact.append({'key':o['key'],'sourceSha256':o['sha256'],'overlapMm3':vol,'bounds':list(cut.bounding_box())if vol>1e-7 else None})
   rows.append({'side':side,'rollPitchKneeDegrees':[ri,pi,ki],'part':part['key'],'exact':exact,'aabbCulled':culled,'sameBodyInherited':same});print(side,ri,pi,ki,part['key'],[(r['key'],round(r['overlapMm3'],4))for r in exact if r['overlapMm3']>1e-7],flush=True)
   (D/'retention-motion.json').write_text(json.dumps({'completed':False,'sourceHashes':{str(D/'retention-plan.json'):sha(D/'retention-plan.json'),str(FK):sha(FK),str(G):sha(G)},'rows':rows},indent=2))
r=json.loads((D/'retention-motion.json').read_text());r['completed']=True;r['sampledRigidPassed']=all(x['overlapMm3']<1e-7 for a in rows for x in a['exact']);r['scope']='11 distinct neutral/extreme source hip/knee configurations per side. Case anchor/lock only. Flexible loose keeper is not treated as a fixed rigid shape. Not continuous-domain acceptance.';(D/'retention-motion.json').write_text(json.dumps(r,indent=2))
