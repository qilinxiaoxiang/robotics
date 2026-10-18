from pathlib import Path
import sys,numpy as np,trimesh,manifold3d
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'assembly'))
from assembly_fk import fk,raw
REMOVE={'elec_rpi_robot_hat_pcb','speaker','lens','m12_lens_holder'}
def man(m):return manifold3d.Manifold(manifold3d.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def tri(mm):
 m=mm.to_mesh();return trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=True)
def box(c,d):return trimesh.creation.box(d).apply_translation(c)
def cub(c,d):return manifold3d.Manifold.cube(d,center=True).translate(c)
def obstacles(exclude_shell=False):
 r=[]
 for g in fk()[1]:
  if g['body']=='jaw_soft' and g['mesh'] not in REMOVE:
   if exclude_shell and g['mesh']=='top_head_shell':continue
   m=raw(g['mesh']).apply_transform(g['local']);r.append((g['mesh'],m,man(m)))
 return r
PI_KEEP=[('pi_inside_components',[15.435,-.011,-57.31],[28,63,3.8]),('pi_gpio_connection',[3.935,-.011,-53.21],[7,52,12])]
def add_pi(obs):return obs+[(n,box(c,d),cub(c,d)) for n,c,d in PI_KEEP]
def hits(mm,obs,detail=True):
 m=tri(mm);lo=m.bounds[0];hi=m.bounds[1];r=[]
 for n,o,om in obs:
  if np.any(lo>o.bounds[1]) or np.any(hi<o.bounds[0]):continue
  v=float((mm^om).volume())
  if v>.001:
   if not detail:return True
   r.append([n,v])
 return r if detail else False
