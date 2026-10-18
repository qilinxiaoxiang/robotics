"""Conditional kinematic scan inferred from source CAD, separate from XML actuators."""
from pathlib import Path
import json,sys,numpy as np,trimesh,manifold3d as md
from scipy.spatial.transform import Rotation
HERE=Path(__file__).resolve().parent;OLD=HERE.parents[1]/'hardware-design-20260912/whole-robot-20260912';sys.path.insert(0,str(OLD/'assembly'))
from assembly_fk import fk,raw
sys.path.insert(0,str(OLD/'electrical/head-layout'));from geometry import man,hits
mov=[];fixed=[]
for g in fk()[1]:
 if g['body']!='jaw_soft':continue
 if g['mesh'] in ['top_head_shell','elec_rpi_robot_hat_pcb','speaker','lens','m12_lens_holder']:continue
 m=raw(g['mesh']).apply_transform(g['local']);r=(g['mesh']+':'+str(g['index']),m,man(m))
 (mov if g['mesh'] in ['jaw','jaw_soft'] else fixed).append(r)
H=OLD/'electrical/head-layout/final'
for n in ['head_cap','audio_carrier','camera_pitch_foot','camera_cradle','camera_module3_wide','openrb_actual_box_proxy','amp_reservation','speaker_reservation','head_fastener_reference']:
 m=trimesh.load(H/(n+'_assembly.stl'),force='mesh');fixed.append((n,m,man(m)))
res=[];pivot=np.array([3.2,0,-18])
for deg in np.arange(0,30.01,.5):
 R=Rotation.from_euler('y',deg,degrees=True).as_matrix();T=np.c_[R,pivot-R@pivot];hh=[]
 for n,m,s in mov:
  for name,v in hits(s.transform(T),fixed):hh.append({'moving':n,'fixed':name,'volume_mm3':v})
 res.append({'degrees':float(deg),'hits':hh})
report={'conditional_only':True,'axis_frame':'jaw_soft mm','axis_point_mm':pivot.tolist(),'axis_direction':[0,1,0],'basis':'Opposite 15x15x3 bearing centre x3.2,z-18; source motor transform centre x3.0,z-18 differs by0.2mm. No mouth joint exists in source XML. Confirm shaft/hole axis and moving pad attachment physically before powering.', 'moving_parts':['jaw','jaw_soft'],'fixed_upper_pad':'soft_mouth_top','rows':res,'collision_free_sampled_degrees':[r['degrees'] for r in res if not r['hits']]}
(HERE/'mouth-motion-conditional.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2));print('firsthits',next((r for r in res if r['hits']),None))
