"""Local replacement: fixed eccentric sliding bushing; source files stay frozen."""
from pathlib import Path
import sys,json,numpy as np,trimesh,manifold3d as md
H=Path(__file__).resolve().parent;OLD=H.parents[1]/'hardware-design-20260912/whole-robot-20260912'
sys.path.insert(0,str(OLD/'assembly'));from assembly_fk import fk,raw
sys.path.insert(0,str(OLD/'electrical/head-layout'));from geometry import man,tri
O=H/'mouth-support';O.mkdir(exist_ok=True)
g=next(g for g in fk()[1] if g['body']=='jaw_soft' and g['mesh']=='motor_support')
base=raw(g['mesh']).apply_transform(g['local'])
def cylinder_y(radius,ylow,yhigh,x=3,z=-18):
 s=md.Manifold.cylinder(yhigh-ylow,radius,radius,circular_segments=160,center=True)
 return s.rotate([90,0,0]).translate([x,(ylow+yhigh)/2,z])
# Outer seat follows the source support; bore follows both measured jaw ends and motor output.
outer=cylinder_y(7.7,-39.7,-37,3.2)
shellg=next(x for x in fk()[1] if x['body']=='jaw_soft' and x['mesh']=='bottom_head_shell')
shell=man(raw(shellg['mesh']).apply_transform(shellg['local']))
# Keep an orthogonal 0.2 mm envelope clear of the retained lower shell.
shell_clear=shell
for axis in range(3):
 for sign in [-1,1]:
  v=[0,0,0];v[axis]=sign*.2;shell_clear=shell_clear+shell.translate(v)
outer=outer-shell_clear
bore=cylinder_y(5.2,-40.5,-36.5,3.0)
new=(man(base)+outer)-bore
m=tri(new);components=m.split();assert all(abs(x.volume)<1e-6 for x in components[1:]),[x.volume for x in components];m=max(components,key=lambda x:abs(x.volume));new=man(m);m.export(O/'motor-support-coaxial-assembly.stl')
r=next(r for r in json.loads((H/'community-print-inventory.json').read_text())['objects'] if r['id']==24)
T=np.eye(4);T[:3,:3]=r['source_to_reference_rotation'];T[:3,3]=r['source_to_reference_translation_mm']
p=m.copy().apply_transform(np.linalg.inv(g['local'])).apply_transform(np.linalg.inv(T));R=np.eye(4);R[:3,:3]=r['original_plate_rotation'];p.apply_transform(R);p.apply_translation([-p.bounds.mean(0)[0],-p.bounds.mean(0)[1],-p.bounds[0,2]])
p.export(O/'motor-support-coaxial-print.stl')
assert m.is_watertight and len(m.split())==1,(m.is_watertight,len(m.split()))
report={'source_replaced':'community h.obj / ID24; motor_support','frame':'jaw_soft, mm','jaw_output_and_passive_boss_axis':[3,0,-18],'source_support_seat_axis':[3.2,0,-18],'outer_diameter_mm':15.4,'bore_diameter_mm':10.4,'bore_axis':[3,0,-18],'axial_y_mm':[-39.7,-37],'nominal_radial_clearance_mm':.2,'nominal_flange_axial_clearance_mm':.3,'added_volume_mm3':new.volume()-man(base).volume(),'watertight':bool(m.is_watertight),'connected_solids':len(m.split()),'replaces_default_mouth_bearing':True,'separate_mouth_ring_required':False,'physical_fit_verified':False,'source_unchanged':True}
(O/'design.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
