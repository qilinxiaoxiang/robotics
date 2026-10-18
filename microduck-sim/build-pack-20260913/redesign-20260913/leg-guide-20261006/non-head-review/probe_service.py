from pathlib import Path
import json,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;p=D.parent.parent/'head-redesign-20261008/head-fit-investigation.py';n={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],n);data=n['data'];solid=n['solid'];test=n['samples'];out=[]
def cyl(a,b,r):
 a=np.array(a);b=np.array(b);T=trimesh.geometry.align_vectors([0,0,1],b-a);T[:3,3]=(a+b)/2;m=trimesh.creation.cylinder(radius=r,height=np.linalg.norm(b-a),sections=48).apply_transform(T);return n['man'](m)
for mod,roll,yaw,link in [(data['modules'][0],9,10,'yaw'),(data['modules'][1],4,5,'right_yaw')]:
 keys=mod['ownedPartKeys'];allparts={k:solid(k) for k in keys};tools=[]
 for screw in data['screws']:
  if screw['id'].startswith((f'S{roll:02}-case-',f'S{roll:02}-rear_center-',f'S{yaw:02}-horn-')):
   a=np.array(screw['world_center_mm']);v=np.array(screw['world_axis']);shaft=cyl(a+v*.5,a+v*40,1.5);hits={k:float((shaft^s).volume()) for k,s in allparts.items() if (shaft^s).volume()>.0001};tools.append({'screw':screw['id'],'hits':hits});print('TOOL',screw['id'],hits,flush=True)
 moving={k:s for k,s in allparts.items() if k not in [link,f'motor{yaw}']};fixed={k:allparts[k] for k in [link,f'motor{yaw}']};paths=[]
 for v in [[45,0,0],[-45,0,0],[0,0,-45]]:
  r=test(moving,fixed,[0,0,0],v,step=.5);paths.append(r);print('FOURJOINT',mod['id'],v,r['peakContactsMm3'],flush=True)
 out.append({'module':mod['id'],'tools':tools,'moving':list(moving),'fixed':list(fixed),'withdrawalPaths':paths})
(D/'service-probe.json').write_text(json.dumps(out,indent=2)+'\n')
