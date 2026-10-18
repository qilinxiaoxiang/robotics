from pathlib import Path
import json,numpy as np
from scipy.optimize import differential_evolution
from scipy.spatial.transform import Rotation
D=Path(__file__).resolve().parent;p=D/'search_horizontal_pi.py';n={'__file__':str(p)};exec(p.read_text().split('rows=[]')[0],n);c=n['c'];mf=n['mf'];core=n['core'];base=np.array([[0,-1,0],[0,0,1],[-1,0,0]])
fixed=n['fixed'];hard={k:v for k,v in fixed.items() if k not in ['face_panel','camera_retainer','camera_mount_screws','jaw_support']};union=mf.Manifold.batch_boolean(list(hard.values()),mf.OpType.Add);soft=fixed['jaw_support'];count=0;best=(1e20,None);history=[]
def shape(x):
 T=np.eye(4);T[:3,:3]=Rotation.from_euler('xyz',x[3:],degrees=True).as_matrix()@base;T[:3,3]=x[:3]-T[:3,:3]@n['center'];return core.transform(T[:3]),T
def objective(x):
 global count,best
 count+=1;m,T=shape(x);a=c.hits(m,union);b=c.hits(m,soft);value=a+.15*b
 if value<best[0]:best=(value,x.tolist());history.append({'i':count,'hard':a,'soft':b,'x':x.tolist()});print('best',history[-1],flush=True)
 return value
res=differential_evolution(objective,[(34,48),(-20,20),(129,135),(-10,10),(-10,10),(-25,25)],popsize=5,maxiter=30,tol=.001,seed=12,polish=False,workers=1)
m,T=shape(res.x);hits={k:c.hits(m,o) for k,o in fixed.items() if c.hits(m,o)>1e-5};report={'parameters':res.x.tolist(),'transform':T.tolist(),'allOriginalObstacleHitsMm3':hits,'searched':count,'history':history,'excludedForReprintOnly':['face_panel','camera_retainer','camera_mount_screws'],'jawSupportWeightedNotWaived':True,'accepted':False,'sourceHashes':c.hashes};(D/'optimized-pi-pose.json').write_text(json.dumps(report,indent=2)+'\n');c.tri(m).export(D/'optimized-pi-core-probe-world.stl');print(json.dumps(report,indent=2))
