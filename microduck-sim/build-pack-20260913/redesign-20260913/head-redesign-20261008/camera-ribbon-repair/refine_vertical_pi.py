from pathlib import Path
import json,numpy as np
from scipy.optimize import differential_evolution
from scipy.spatial.transform import Rotation
D=Path(__file__).resolve().parent;p=D/'search_pi_discrete_pose.py';n={'__file__':str(p)};exec(p.read_text().split('rows=[]')[0],n);c=n['c'];mf=n['mf'];core=n['core'];fixed=n['fixed'];hard={k:v for k,v in fixed.items() if k not in ['face_panel','camera_retainer','camera_mount_screws']};u=mf.Manifold.batch_boolean(list(hard.values()),mf.OpType.Add);history=[];best=1e20;count=0

def shape(x):
 T=np.eye(4);T[:3,:3]=Rotation.from_euler('xyz',x[3:],degrees=True).as_matrix();T[:3,3]=n['center']+x[:3]-T[:3,:3]@n['center'];return core.transform(T[:3]),T

def obj(x):
 global best,count
 count+=1;m,T=shape(x);v=c.hits(m,u)
 if v<best:best=v;history.append({'n':count,'v':v,'x':x.tolist()});print(history[-1],flush=True)
 return v
r=differential_evolution(obj,[(1.2,2.7),(-2,2),(-3,1),(-5,5),(-5,5),(-5,5)],popsize=5,maxiter=35,tol=.001,seed=24,polish=False);m,T=shape(r.x);hh={k:c.hits(m,o) for k,o in fixed.items() if c.hits(m,o)>1e-5};report={'parameters':r.x.tolist(),'transform':T.tolist(),'hitsMm3':hh,'history':history,'count':count,'mouth':(T[:3,:3]@n['mouth']+T[:3,3]).tolist(),'accepted':False,'sourceHashes':c.hashes};(D/'refined-vertical-pi.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
