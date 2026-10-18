from pathlib import Path
import sys,json,numpy as np,trimesh
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parents[1]/'hardware-design-20260912/whole-robot-20260912/assembly'));from assembly_fk import fk,raw

def circles(m,ax,v):
 p=np.zeros(3);p[ax]=v;s=m.section(plane_origin=p,plane_normal=np.eye(3)[ax]);out=[]
 if s is None:return []
 for q in s.discrete:
  if len(q)<12 or np.linalg.norm(q[0]-q[-1])>1e-3:continue
  q=np.delete(q,ax,1);A=np.c_[2*q,np.ones(len(q))];cx,cy,c=np.linalg.lstsq(A,(q*q).sum(1),rcond=None)[0];r=np.sqrt(max(c+cx*cx+cy*cy,0));err=np.max(np.abs(np.linalg.norm(q-[cx,cy],axis=1)-r))
  if err<.008:out.append({'center_other_axes':[float(cx),float(cy)],'radius':float(r),'max_error':float(err),'points':len(q)})
 return out
rows=[]
for name in ['xl330']:
 m=raw(name)
 for v in [-14.4,-13.2,-12.5,-11.5,11.5,12.5,13.2,14.4]:rows.append({'part':name,'axis':0,'plane':v,'circles':circles(m,0,v)})
for name in ['jaw','motor_support']:
 g=next(g for g in fk()[1] if g['body']=='jaw_soft' and g['mesh']==name);m=raw(name).apply_transform(g['local'])
 for v in [-42,-41,-40.5,-39.5,-38,28,35,39,40,41]:rows.append({'part':name,'axis':1,'plane':v,'circles':circles(m,1,v)})
(H/'joint-interface-circles.json').write_text(json.dumps(rows,indent=2))
for r in rows:
 if r['circles']:print(r)
