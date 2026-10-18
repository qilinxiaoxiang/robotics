from pathlib import Path
import sys,json,itertools,time
import numpy as np,trimesh,manifold3d
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'assembly'))
from assembly_fk import fk,raw
REMOVE={'elec_rpi_robot_hat_pcb','speaker','lens','m12_lens_holder'}
def manifold(m):return manifold3d.Manifold(manifold3d.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
OBS=[]
for g in fk()[1]:
 if g['body']=='jaw_soft' and g['mesh'] not in REMOVE:
  m=raw(g['mesh']).apply_transform(g['local']);OBS.append((g['mesh'],m,manifold(m)))
print(json.dumps({n:np.round(m.bounds,2).tolist() for n,m,_ in OBS},indent=2),flush=True)
def hits(c,d,details=False,obs=OBS):
 lo=np.array(c)-np.array(d)/2;hi=np.array(c)+np.array(d)/2;b=None;hs=[]
 for n,m,mm in obs:
  if np.any(hi<m.bounds[0]) or np.any(lo>m.bounds[1]):continue
  if b is None:b=manifold3d.Manifold.cube(d,center=True).translate(c)
  v=(b^mm).volume()
  if v>.001:
   if not details:return True
   hs.append([n,float(v)])
 return hs if details else False
# Search wholly within existing shell bounding range. Exact shell intersections checked as occupied geometry.
results={};start=time.time()
for d in [(21,27,68),(27,21,68),(21,68,27),(27,68,21),(68,21,27),(68,27,21)]:
 out=[];tested=0
 for x,y,z in itertools.product(np.arange(-23,31,3),np.arange(-30,31,3),np.arange(-45,14,3)):
  c=[float(x),float(y),float(z)];lo=np.array(c)-np.array(d)/2;hi=np.array(c)+np.array(d)/2
  if lo[0]<-30 or hi[0]>37 or lo[1]<-43 or hi[1]>43 or lo[2]<-76 or hi[2]>30:continue
  tested+=1
  if not hits(c,d):out.append(c)
 results[str(d)]={'dims_mm':d,'tested':tested,'candidates':out};print(d,tested,len(out),out[:10],round(time.time()-start,2),flush=True)
(HERE/'openrb-box-candidates.json').write_text(json.dumps(results,indent=2)+'\n')
