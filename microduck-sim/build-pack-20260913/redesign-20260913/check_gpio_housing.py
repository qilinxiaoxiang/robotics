from pathlib import Path
import sys,json,trimesh
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/electrical/head-layout');F=D/'final';O=Path(__file__).resolve().parent;sys.path.insert(0,str(D))
from geometry import box,man,obstacles,hits
obs=[x for x in obstacles(True) if x[0] != "motor_support"]
m=trimesh.load(O.parent/"assembly/mouth-support/motor-support-coaxial-assembly.stl",force="mesh");obs.append(("current_coaxial_motor_support",m,man(m)))
for n in ['audio_carrier_assembly','head_fastener_reference_assembly','camera_pitch_foot_assembly','camera_cradle_assembly','openrb_actual_box_proxy_assembly','amp_reservation_assembly','speaker_reservation_assembly']:
 m=trimesh.load(F/(n+'.stl'),force='mesh');obs.append((n,m,man(m)))
m=trimesh.load(O/'head-cap-usb-service-body.stl',force='mesh');obs.append(('new_cap',m,man(m)))
# The previous check omitted Pi screw heads. Include the selected physical envelope.
for x in [3.935,26.935]:
 for y in [-29.011,28.989]:
  m=trimesh.creation.cylinder(radius=2,height=1.5,sections=64).apply_translation([x,y,-58.46])
  obs.append((f'pi_screw_head_{x}_{y}',m,man(m)))
rows=[]
for width,length,height in [(7,52,15),(7,54,15),(8,54,18),(9,56,18)]:
 m=box([3.935,-.011,-59.21+height/2],[width,length,height]);r={'envelope_xyz_mm':[width,length,height],'lower_plane_z_mm':-59.21,'hits':hits(man(m),obs)};rows.append(r)
result={'purpose':'Allowance for a 2x20 female housing with 12 populated contacts plus wire exit; supplier-specific housing remains stock check','candidates':rows,'selected_housing_and_exit_envelope_xyz_mm':[7,52,15],'selected_envelope_passed':not rows[0]['hits'],'pi_screw_head_envelope_diameter_height_mm':[4,1.5],'pi_screw_head_nominal_clearance_mm':1.0,'old_54mm_envelope_clearance_mm':0.0,'negative_18mm_housing_rejected':bool(rows[2]['hits']),'physical_tests':0,'scope':'Rigid envelope against retained head, revised cap and Pi screw heads; not a vendor drawing or electrical contact rating'}
(O/'gpio-housing-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

sys.exit(0 if result['selected_envelope_passed'] and result['negative_18mm_housing_rejected'] else 1)
