from pathlib import Path
import sys,ast,itertools
N=Path(__file__).resolve().parent;sys.path.insert(0,str(N.parent))
from check_routes import *
SIM=H.parent.parents[1];sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'));from assembly_fk import fk,TREE
B,_=fk();inv={k:np.linalg.inv(v) for k,v in B.items()};body={p['key']:p.get('body','jaw_soft') for p in data['parts']}
for k in obs:body.setdefault(k,'jaw_soft')
body={k:b if b in B else 'trunk_base' for k,b in body.items()}
rigid=json.loads((H/'usb-access/usb-repair/rigid-domain.json').read_text());cases=[r['jointDegrees'] for r in rigid['samples']]
obs['head_cap']=man(load(N.parent/'cap-neck-slot-closure-candidate-world.stl'))
head=np.array([-31.,23.2,125]);out=np.array([-1.,0,0]);rows=[]
for i,q in enumerate(cases):
 poses,_=fk({k:np.deg2rad(v) for k,v in q.items()});Ts={k:poses[k]@inv[k] for k in poses};T=Ts['jaw_soft'];p=(T@np.r_[head,1])[:3];axis=T[:3,:3]@out
 s=tube([p,p+axis*35],3.5);hh={}
 for k,o in obs.items():
  v=hits(s,o.transform(Ts[body[k]][:3]))
  if v>1e-4:hh[k]=v
 rows.append({'jointDegrees':q,'point':p.tolist(),'out':axis.tolist(),'hits':hh,'rigidBlocked':bool(rigid['samples'][i]['rigidIntersectionsMm3'])})
print([(r['jointDegrees'],r['hits'],r['rigidBlocked']) for r in rows if r['hits']],flush=True)
(N/'exit-probe.json').write_text(json.dumps({'rows':rows,'sourceHashes':hashes},indent=2)+'\n')
