"""Native repaired cap third-boss and structural fastening acceptance; no source edits."""
from pathlib import Path
import sys,json,hashlib
import numpy as np,trimesh
from scipy.spatial.transform import Rotation
O=Path(__file__).resolve().parent;R=O.parent;P=R.parent;S=P.parent
H=S/'hardware-design-20260912/whole-robot-20260912/electrical/head-layout';sys.path.insert(0,str(H))
from geometry import man,tri,box,hits,obstacles,fk,raw
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--cap',type=Path,default=R/'head-cap-usb-service-body.stl');ap.add_argument('--output',type=Path,default=O/'electronics-head-closure-verification.json');args=ap.parse_args()
from evidence_sources import hashes, assembly_sources
source_paths=assembly_sources()+[H/'geometry.py',P/'assembly/mouth-support/motor-support-coaxial-assembly.stl']
cap_path=args.cap.resolve();before_path=O/'before-third-boss-repair-head-cap-usb-service-body.stl'
cap=trimesh.load(cap_path);before=trimesh.load(before_path);added=man(cap)-man(before)
def cyl(x,y,z,r,h):
 t=np.eye(4);t[:3,:3]=[[0,0,1],[0,1,0],[-1,0,0]];t[:3,3]=[x,y,z];return man(trimesh.creation.cylinder(radius=r,height=h,sections=96,transform=t))
probe=cyl(4,0,31.5,1.6,8)-cyl(4,0,31.5,1.2,8)
bore=cyl(3.35,0,31.5,1.,9.3)
ob=[o for o in obstacles(True) if o[0] not in ['motor_support','jaw','jaw_soft']]
for n in ['audio_carrier_assembly','openrb_actual_box_proxy_assembly','amp_reservation_assembly','speaker_reservation_assembly','camera_pitch_foot_assembly','camera_cradle_assembly','camera_module3_wide_assembly','head_fastener_reference_assembly']:
 source_paths.append(H/'final'/(n+'.stl'))
 m=trimesh.load(H/'final'/(n+'.stl'));ob.append((n,m,man(m)))
m=trimesh.load(P/'assembly/mouth-support/motor-support-coaxial-assembly.stl');ob.append(('current_motor_support',m,man(m)))
addedhits=hits(added,ob) if added.volume()>.000001 else [];motion=[];pivot=np.array([3.,0,-18]);moving=[]
for g in fk()[1]:
 if g['body']=='jaw_soft' and g['mesh'] in ['jaw','jaw_soft']:
  m=raw(g['mesh']).apply_transform(g['local']);moving.append((g['mesh'],man(m)))
for deg in np.arange(0,30.01,.5):
 rot=Rotation.from_euler('y',deg,degrees=True).as_matrix();T=np.c_[rot,pivot-rot@pivot]
 motion.append({'degrees':float(deg),'collisions':[(name,float((solid.transform(T)^man(cap)).volume())) for name,solid in moving if float((solid.transform(T)^man(cap)).volume())>.001]})
# Exact axial material readback around structural hole rims.
def intersections(m,y,z,r):
 loc,_,_=m.ray.intersects_location([[-100,y+r,z]],[[1,0,0]]);return np.unique(np.round(loc[:,0],5)).tolist() if len(loc) else []
g=next(g for g in fk()[1] if g['mesh']=='bottom_head_shell' and g['body']=='jaw_soft');bottom=raw(g['mesh']).apply_transform(g['local']);support=trimesh.load(P/'assembly/mouth-support/motor-support-coaxial-assembly.stl')
rays=[]
for y,z in [(39,-67.5),(-39,-67.5),(0,31.5),(19,1.5),(9.35,-41),(-30,-34),(-30,5)]:
 rays.append({'axis':'X','hole_yz':[y,z],'radial_offset_y_mm':1.5,'bottom_shell_material_endpoints_x':intersections(bottom,y,z,1.5),'support_material_endpoints_x':intersections(support,y,z,1.5),'current_cap_material_endpoints_x':intersections(cap,y,z,1.5)})
report={'problem_ids':['P5','P6'],'frame':'jaw_soft_mm','scope':'Restored third cap closure plus four motor-support/head-shell screws. Does not cover other robot structural interfaces','source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths+[Path(__file__),O/'restore_head_closure.py',cap_path,before_path]},'current_cap_watertight':bool(cap.is_watertight),'current_cap_solids':len(cap.split()),'restored_boss_outer_diameter_mm':4.6,'pilot_diameter_mm':2.1,'radial_wall_mm':1.25,'nearest_neck_servo_top_z_mm':29.0,'boss_bottom_z_mm':29.2,'nominal_neck_servo_vertical_gap_mm':.2,'added_volume_mm3':float(added.volume()),'probe_ring_volume_mm3':float(probe.volume()),'before_ring_supported_mm3':float((probe^man(before)).volume()),'after_ring_supported_mm3':float((probe^man(cap)).volume()),'bore_intersection_mm3':float((bore^man(cap)).volume()),'added_geometry_vs_current_head_collisions':addedhits,'jaw_motion_samples':motion,'structural_hole_rays':rays,'print_affected':'current head-cap-usb-service-print.stl only; original current3MFplate1 object4 must be updated/resliced by owner','passed':cap.is_watertight and len(cap.split())==1 and not addedhits and all(not r['collisions'] for r in motion) and abs((probe^man(cap)).volume()-probe.volume())<.001 and (bore^man(cap)).volume()<.001 and (probe^man(before)).volume()<probe.volume()*.9}
args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['jaw_motion_samples','structural_hole_rays','source_hashes']},indent=2));sys.exit(0 if report['passed'] else 1)
