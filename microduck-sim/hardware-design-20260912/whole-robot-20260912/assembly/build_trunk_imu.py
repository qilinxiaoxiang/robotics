from pathlib import Path
import cadquery as cq,trimesh,numpy as np,json
O=Path(__file__).parent/'trunk-imu';O.mkdir(exist_ok=True)
def b(x0,x1,y0,y1,z0,z1):return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0).translate(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))
def cyl_x(x0,x1,y,z,r):return cq.Workplane('YZ').center(y,z).circle(r).extrude(x1-x0).translate((x0,0,0))
# Sensor holder front plate, side/floor/top retention. The board is inserted from -X.
h=b(-52.6,-51.4,-15.7,15.7,.8,31)
for y0,y1 in [(-15.7,-14.5),(14.5,15.7)]:h=h.union(b(-61.4,-51.4,y0,y1,.8,29.5))
for z0,z1 in [(.8,2),(28,29.5)]:h=h.union(b(-61.4,-51.4,-15.7,15.7,z0,z1))
h=h.cut(b(-53,-51,-10.5,10.5,6,24))
# Rigid clamp to the two outer upper battery-guide corners. Tongues remain outside battery Y+-17.
h=h.union(b(-52.6,-46.9,-21,21,29.7,33.7))
for sign in [-1,1]:
 y0,y1=sorted([sign*19.6,sign*21]);h=h.union(b(-50.6,-46.9,y0,y1,23.2,33.7))
 y0,y1=sorted([sign*17.5,sign*21]);h=h.union(b(-50.6,-46.9,y0,y1,23.2,24.4))
 # M2 pressure screw: pilot is 1.6mm. Tip bears on the original top corner at Z29.5.
 h=h.cut(cq.Workplane('XY').center(-48.0,sign*18).circle(.8).extrude(5).translate((0,0,29.5)))
# Vented rear cover, fastened through bosses that stay outside the complete reserved board box.
c=b(-62.6,-61.4,-19.5,19.5,.8,29.5).cut(b(-63,-61,-10.5,10.5,6,24))
for y in [-17.5,17.5]:
 for z in [4,26]:
  h=h.union(b(-61.4,-56.4,y-2,y+2,z-2,z+2))
  h=h.cut(cyl_x(-61.5,-55.9,y,z,.8))
  c=c.cut(cyl_x(-63,-61,y,z,1.1))
# Keep side cover only around its screws, lighten excess over the middle.
for y0,y1 in [(-19.6,-15.7),(15.7,19.6)]:c=c.cut(b(-63,-61,y0,y1,6.5,23.5))
parts={}
for name,s in [('imu_clamp_holder',h),('imu_rear_cover',c)]:
 cq.exporters.export(s,str(O/f'{name}.step'));cq.exporters.export(s,str(O/f'{name}_body.stl'))
 m=trimesh.load(O/f'{name}_body.stl',force='mesh');assert m.is_watertight and len(m.split())==1,(name,m.is_watertight,len(m.split()))
 parts[name]={'mass_PETG_1p27_g_cm3_g':m.volume*.00127,'body_com_mm':m.center_mass.tolist(),'bounds_mm':m.bounds.tolist()}
proxy=trimesh.creation.box([8,28,25]).apply_translation([-57,0,15]);proxy.export(O/'imu_28x25x8_envelope_body.stl')
result={'body':'trunk_base','sensor_center_m':[-.057,0,.015],'envelope_dims_m':[.008,.028,.025],'sensor_mass_kg':.0025,'printed_parts':parts,'mount':'Two M2x5 pressure screws; jaws capture existing upper battery-guide corners outside Y+-17mm battery. No changes to frozen frame. Four M2x6 rear-cover screws into 1.6mm pilots. Body axes in mm.','cavity_mm':[8.4,29,26],'evidence_status':'Static and trajectory check pending; clamp fit and sensor-axis calibration require physical assembly.'}
(O/'design.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
