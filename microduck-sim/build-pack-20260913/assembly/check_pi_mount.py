from pathlib import Path
import sys,json,numpy as np,trimesh,manifold3d as md
H=Path(__file__).resolve().parent;D=H.parents[1]/'hardware-design-20260912/whole-robot-20260912/electrical/head-layout';sys.path.insert(0,str(D));from geometry import man,tri,box,obstacles,hits,cub,PI_KEEP
obs=[x for x in obstacles(True) if x[0]!='face_part'];obs +=[(n,box(c,d),cub(c,d)) for n,c,d in PI_KEEP if n=='pi_gpio_connection']
for name in ['audio_carrier_assembly','openrb_actual_box_proxy_assembly','amp_reservation_assembly','speaker_reservation_assembly','pi_usb_data_plug_reservation_assembly','pi_usb_power_plug_reservation_assembly']:
 m=trimesh.load(D/'final'/(name+'.stl'));obs.append((name,m,man(m)))
m=trimesh.load(H/'mouth-clearance/head-cap-mouth-clearance-assembly.stl');obs.append(('new_head_cap',m,man(m)))
allheads=[];rows=[]
for x in [3.935,26.935]:
 for y in [-29.011,28.989]:
  sh=trimesh.creation.cylinder(radius=1.25,height=6,sections=64).apply_translation([x,y,-62.21]);head=trimesh.creation.cylinder(radius=2.25,height=1.8,sections=64).apply_translation([x,y,-58.31]);s=man(sh)+man(head);allheads.append(s);rows.append({'xy':[x,y],'hits_except_intended_plastic_thread':hits(s,obs)})
assembly_solid=md.Manifold.batch_boolean(allheads,md.OpType.Add);tri(assembly_solid).export(H/'pi-mount-screw-reference.stl');result={'spec':'M2.5x6 tapping screw, head <=4.5dia x1.8high mm','quantity':4,'nuts':0,'PCB_hole_diameter_mm':2.7,'PCB_thickness_mm':1.6,'pilot_diameter_mm_approx':2,'pilot_depth_mm_approx':5.5,'engagement_mm':4.4,'tip_to_blind_end_mm_approx':1.1,'screw_steel_solid_upper_g':float(assembly_solid.volume()*.00785),'checks':rows,'passed':all(not r['hits_except_intended_plastic_thread'] for r in rows),'scope':'Geometric envelope and pilot-depth inference; actual tapping thread and tightening not physically tested.'}
(H/'pi-mount-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
