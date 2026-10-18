"""Bounded feasibility screen only; does not modify accepted cap or Pi mounting."""
from pathlib import Path
import sys,json,trimesh
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/electrical/head-layout');F=D/'final';O=Path(__file__).resolve().parent;sys.path.insert(0,str(D))
from geometry import box,man,obstacles,hits,PI_KEEP
allobs=obstacles(True);pi=next(x[1] for x in allobs if x[0]=='pcb__raspberry_pi_zero_2_w');obs=[x for x in allobs if x[0]!='pcb__raspberry_pi_zero_2_w']
for n in ['audio_carrier_assembly','head_fastener_reference_assembly','camera_pitch_foot_assembly','camera_cradle_assembly','openrb_actual_box_proxy_assembly','amp_reservation_assembly','speaker_reservation_assembly']:
 m=trimesh.load(F/(n+'.stl'),force='mesh');obs.append((n,m,man(m)))
records=[]
for dz in [0,-1,-2]:
 moved=pi.copy().apply_translation([0,0,dz]);plug=box([42.935,8.9,-56.1+dz],[25,18,10]);keep=[(n,box([c[0],c[1],c[2]+dz],d)) for n,c,d in PI_KEEP]
 records.append({'pi_shift_z_mm':dz,'pi_mesh_collisions':hits(man(moved),obs),'10mm_plug_internal_collisions':hits(man(plug),obs),'pi_component_and_gpio_collisions':{n:hits(man(m),obs) for n,m in keep}})
result={'mode':'feasibility screen, no accepted design changed','candidates':records,'existing_mount':'Face panel community ID76; four blind pilot bosses; M2.5 x 6 screw through 1.6mm board engages about4.4mm into approx5.5mm pilots','decision':'Retain unshifted accepted 8mm plug envelope for current queue. Lowering Pi requires a local face-panel boss revision, screw-length recheck and lower cap-window revision; it is not achieved by adding spacers. No published SC0727 moulding size currently establishes a need for that second print revision.'}
(O/'pi-shift-option-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
