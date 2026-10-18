from pathlib import Path
import sys,json,time,itertools
import numpy as np,trimesh,manifold3d
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scipy.optimize import differential_evolution
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'assembly'))
from assembly_fk import fk,raw
REMOVE={'elec_rpi_robot_hat_pcb','speaker','lens','m12_lens_holder'}
def man(m):return manifold3d.Manifold(manifold3d.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
obs=[];shell=[]
for g in fk()[1]:
 if g['body']=='jaw_soft' and g['mesh'] not in REMOVE:
  m=raw(g['mesh']).apply_transform(g['local']);obs.append((g['mesh'],m,man(m)))
  if g['mesh'] in ['top_head_shell','bottom_head_shell']:shell.append(m)
# Expanded Pi chip/connector reserve on inside face. Full-port placement remains separately unverified.
for n,c,d in [('pi_inside_component_allowance',[15.435,-.011,-57.31],[28,63,3.8]),('pi_header_connection_allowance',[2.935,-.011,-53.21],[5,52,12])]:
 m=trimesh.creation.box(d).apply_translation(c);obs.append((n,m,man(m)))
hull=ConvexHull(np.concatenate([x.vertices for x in shell]));eq=hull.equations
corners=trimesh.creation.box([21,27,68]).vertices
best={'value':1e20};start=time.time();count=0

def obj(v,detail=False):
 global count
 count+=1;c=np.array(v[:3]);R=Rotation.from_euler('xyz',v[3:],degrees=True).as_matrix();verts=corners@R.T+c
 # Conservative enclosing convex shell hull; actual shell material collision below.
 outside=np.maximum(0,verts@eq[:,:3].T+eq[:,3]).max(axis=1)
 score=float((outside*outside).sum()*10)
 bm=manifold3d.Manifold.cube([21,27,68],center=True).transform(np.c_[R,c]);lo=verts.min(0);hi=verts.max(0);hits=[]
 for n,m,mm in obs:
  if np.any(lo>m.bounds[1]) or np.any(hi<m.bounds[0]):continue
  vol=float((bm^mm).volume());score+=vol
  if vol>.001:hits.append([n,vol])
 if score<best['value']:
  best.update(value=score,x=list(v),collisions=hits,outside_corner_distances_mm=outside.tolist(),rotation=R.tolist(),evaluations=count)
 if detail:return score,hits
 return score

def callback(x,convergence):
 if best['value']<1e-5:return True
 return False
for seed in [4,29,44]:
 result=differential_evolution(obj,[(-4,31),(-26,26),(-37,3),(-45,45),(-45,45),(-45,45)],popsize=12,maxiter=90,tol=.001,atol=.001,seed=seed,callback=callback,polish=False)
 print(seed,best,round(time.time()-start,2),flush=True)
 (HERE/'openrb-rotated-optimization.json').write_text(json.dumps(best,indent=2)+'\n')
 if best['value']<1e-5:break
