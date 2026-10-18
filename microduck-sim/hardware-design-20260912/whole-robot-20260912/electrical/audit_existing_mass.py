"""Read existing MJCF/component meshes; never modifies the robot model.
Run: /tmp/microduck-cad-venv/bin/python audit_existing_mass.py
"""
from pathlib import Path
import json, xml.etree.ElementTree as ET
import numpy as np
import trimesh
OUT=Path(__file__).resolve().parent
SIM=OUT.parents[2]
models={
 'official_current':SIM/'microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml',
 'community_old':SIM/'Microduck-build-tutorial/microduck/src/model/mjcf/robot.xml',
}
names={'np_f970','pcb__raspberry_pi_zero_2_w','speaker','m12_lens_holder','elec_rpi_robot_hat_pcb','lens','battery'}
def vec(s,default):return np.array([float(x) for x in s.split()]) if s else np.array(default,dtype=float)
def rotation(q):return trimesh.transformations.quaternion_matrix(q)[:3,:3]
def inertia(it):
 if it.get('fullinertia'):
  xx,yy,zz,xy,xz,yz=vec(it.get('fullinertia'),[]);return np.array([[xx,xy,xz],[xy,yy,yz],[xz,yz,zz]])
 R=rotation(vec(it.get('quat'),[1,0,0,0]));return R@np.diag(vec(it.get('diaginertia'),[]))@R.T
out={'warning':'Part metadata files contain Onshape provenance only, not individual mass/inertia. Do not subtract supplier mass from an unknown already-lumped body as though exact. Bounds below assume an identified uniform mesh distribution and nonnegative remaining mass moments; they are upper bounds, not measured original masses. Individual upper bounds cannot all be applied together.', 'models':{}}
for label,mp in models.items():
 root=ET.parse(mp).getroot(); total=sum(float(it.attrib['mass']) for it in root.iter('inertial'))
 mres={'path':str(mp),'total_explicit_mass_g':total*1000,'parts':[],'imu_sites':[s.attrib for s in root.iter('site') if 'imu' in s.get('name','')], 'part_metadata_contains_mass':False}
 for body in root.iter('body'):
  it=body.find('inertial')
  if it is None:continue
  m=float(it.get('mass'));c=vec(it.get('pos'),[0,0,0]);I=inertia(it)
  S=np.trace(I)/2*np.eye(3)-I
  H=np.block([[S+m*np.outer(c,c),m*c[:,None]],[m*c[None,:],np.array([[m]])]])
  d,U=np.linalg.eigh(H);Hm=U@np.diag(1/np.sqrt(d))@U.T
  seen=set()
  for g in body.findall('geom'):
   n=g.get('mesh');
   if n not in names or n in seen:continue
   seen.add(n); mesh=trimesh.load_mesh(mp.parent/'assets'/f'{n}.stl');R=rotation(vec(g.get('quat'),[1,0,0,0]));pos=vec(g.get('pos'),[0,0,0])
   # STL units in this source are metres (no mesh scale set in XML).
   cm=R@mesh.center_mass+pos;I1=R@(mesh.moment_inertia/mesh.volume)@R.T
   S1=np.trace(I1)/2*np.eye(3)-I1
   H1=np.block([[S1+np.outer(cm,cm),cm[:,None]],[cm[None,:],np.array([[1.]])]])
   cap=1/max(np.linalg.eigvalsh(Hm@H1@Hm))
   meta=mp.parent/'assets'/f'{n}.part'
   rec={'id':n,'parent_body':body.get('name'),'parent_lumped_mass_g':m*1000,'parent_com_m':c.tolist(),'parent_inertia_com_kg_m2':I.tolist(),'geom_pos_m':pos.tolist(),'geom_quat_wxyz':vec(g.get('quat'),[1,0,0,0]).tolist(),'mesh_extents_mm':(mesh.extents*1000).tolist(),'mesh_watertight':mesh.is_watertight,'mesh_positive_volume':bool(mesh.volume>0),'uniform_mesh_com_in_body_m':cm.tolist(),'uniform_mesh_inertia_per_kg_m2':I1.tolist(),'assumption_dependent_removal_upper_bound_g':cap*1000,'original_component_mass_g':None,'individual_inertia_available':False}
   if meta.exists():rec['onshape_metadata']=json.loads(meta.read_text())
   mres['parts'].append(rec)
 out['models'][label]=mres
(OUT/'existing-model-mass-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:{'total_g':v['total_explicit_mass_g'],'parts':[{p:x[p] for p in ['id','parent_body','mesh_extents_mm','assumption_dependent_removal_upper_bound_g']} for x in v['parts']]} for k,v in out['models'].items()},indent=2))
