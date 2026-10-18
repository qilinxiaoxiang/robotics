"""Integrated compact replacement power_support, exact source mesh + parametric tray.
All design coordinates are trunk_base mm. Original functional mating faces unchanged;
only the four existing cable-tie openings extended through obstructing rear ribs.
"""
from pathlib import Path
import json,shutil
import cadquery as cq
import trimesh,numpy as np
from assembly_fk import *
OUT=Path(__file__).parent/'compact-battery';OUT.mkdir(exist_ok=True)
SRC=OUT/'source-frame-12.npz'
if not SRC.exists():shutil.copy(Path(__file__).resolve().parents[2]/'battery/source-frame-12.npz',SRC)
MATCH=json.loads(Path(__file__).with_name('body-transforms.json').read_text())['community_to_named_body']['12'];T=np.array(MATCH['matrix_mm'])
src=np.load(SRC);frame=trimesh.Trimesh(src['vertices'],src['faces'],process=True).apply_transform(T)
def box(x0,x1,y0,y1,z0,z1):return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0).translate(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))
def mesh(shape):
 v,f=shape.val().tessellate(.05,.1);return trimesh.Trimesh([[p.x,p.y,p.z] for p in v],f,process=True)
tray=box(-49.4,-21.8,-18.6,18.6,-37.5,-36.)
tray=tray.union(box(-49.4,-21.8,-18.6,18.6,28.,29.5))
for y in [-14,14]:tray=tray.union(box(-26.,-24.4,y-2,y+2,-37.5,29.5))
for y0,y1 in [(-18.6,-17.4),(17.4,18.6)]:
 for z0,z1 in [(-37.5,-34),(24.5,29.5)]:tray=tray.union(box(-49.4,-31.6,y0,y1,z0,z1))
# Vented lower shelf for motor regulator, exact screw pitch 25.4 X x 38.862 Y.
for y in [-19.2,19.2]:
 tray=tray.union(box(-37.5,-33.5,y-1.2,y+1.2,-57.5,-35.5))
tray=tray.union(box(-37.5,-33.5,-20.4,20.4,-37.5,-35.5))
deck=box(-59.1,-11.9,-17.9,17.9,-57.5,-55.5)
for y0,y1 in [(-8.5,-2),(2,8.5)]:deck=deck.cut(box(-49,-22,y0,y1,-58,-55))
for x in [-54.931,-16.069]:
 for y in [-12.7,12.7]:
  deck=deck.union(cq.Workplane('XY').center(x,y).circle(2.5).extrude(2).translate((0,0,-55.5)))
  deck=deck.cut(cq.Workplane('XY').center(x,y).circle(1.1).extrude(5).translate((0,0,-58)))
deck=deck.union(box(-37.5,-33.5,-20.4,20.4,-57.5,-55.5))
tray=tray.union(deck)
# Small regulator supported vertically in the 15mm gap between the hip servos.
small=box(-12.45,12.45,-6.6,-5.4,6.5,33.5)
small=small.union(box(-19,12.45,-6.6,-5.4,12.5,14.5))
small=small.union(box(-12.45,12.45,-6.6,5.8,6.5,8.0))
small=small.union(box(-12.45,12.45,-6.6,5.8,32,33.5))
for x0,x1 in [(-13.45,-12), (12,13.45)]:small=small.union(box(x0,x1,-6.6,5.8,6.5,33.5))
# Four corner mounting bosses outside the board max envelope, M2 through-cover screws.
for x in [-12.8,12.8]:
 for z in [6.8,33.2]:
  small=small.union(box(x-1.45,x+1.45,-6.6,5.8,z-1.45,z+1.45))
  small=small.cut(cq.Workplane('XZ').center(x,z).circle(.8).extrude(14,both=True))
small=small.cut(box(-8.5,8.5,-7,-5.2,11,29))
tray=tray.union(small.translate((-4,0,-2.5)))
# Rear battery-retention belt path; prolong the original slot through rear ribs.
slot_z=[-30.821742128,5.877257872];holes=[]
for z in slot_z:
 for y in [-18.365,18.365]:holes.append(box(-50.1,-20.5,y-1.05,y+1.05,z-3.1,z+3.1))
# Central ventilation/lightening in floor/top, maintaining connected perimeter and 6mm edge beams.
for z0,z1 in [(-37.6,-35.9),(27.9,29.6)]:
 for y0,y1 in [(-11,-2),(2,11)]:tray=tray.cut(box(-44.4,-29.6,y0,y1,z0,z1))
# Rounded wire exit, top center, leaves top corners as positive stops.
tray=tray.cut(box(-49.5,-38,-4,4,27.9,29.6))
for h in holes:tray=tray.cut(h)
tm=mesh(tray)
frame_cut=trimesh.boolean.difference([frame,mesh(box(-100,100,-100,100,-100,-38))],engine='manifold')
mod=trimesh.boolean.union([frame_cut,tm],engine='manifold')
for h in holes:mod=trimesh.boolean.difference([mod,mesh(h)],engine='manifold')
print('VALIDITY',mod.is_watertight,[(round(x.volume,3),x.bounds.tolist()) for x in mod.split()]); assert mod.is_watertight and len(mod.split())==1
cq.exporters.export(tray,str(OUT/'compact-tray.step'));cq.exporters.export(tray,str(OUT/'compact-tray-body.stl'))
mod.export(OUT/'power-support-integrated-body.stl')
mod.copy().apply_transform(np.linalg.inv(T)).export(OUT/'power-support-integrated-print.stl')
frame.export(OUT/'original-power-support-body.stl')
battery=trimesh.creation.box([22,34,63]).apply_translation([-37.6,0,-4]);battery.export(OUT/'battery-max-envelope-body.stl')
# Small regulator front cover: flat vented plate, four M2 screw holes.
cover=box(-14.25,14.25,5.8,7.,5.35,34.65)
cover=cover.cut(box(-8.5,8.5,5,8,11,29))
for x in [-12.8,12.8]:
 for z in [6.8,33.2]:cover=cover.cut(cq.Workplane('XZ').center(x,z).circle(1.1).extrude(14,both=True))
cover=cover.translate((-4,0,-2.5)).cut(box(-18.35,-14.0,5.7,7.1,5.2,29.8))
cq.exporters.export(cover,str(OUT/'small-regulator-cover.step'));cq.exporters.export(cover,str(OUT/'small-regulator-cover-body.stl'))
# Tie ribbon volumes: 1.2mm thickness, 4.8mm band width. Belt extents around whole frame and pack.
ties=[]
for z in slot_z:
 belt=box(-50.6,-49.4,-18.965,18.965,z-2.4,z+2.4)
 belt=belt.union(box(-20.6,-19.4,-18.965,18.965,z-2.4,z+2.4))
 for y in [-18.365,18.365]:belt=belt.union(box(-50.6,-19.4,y-.6,y+.6,z-2.4,z+2.4))
 ties.append(mesh(belt));cq.exporters.export(belt,str(OUT/f'tie-{z:.3f}-envelope.step'))
 trimesh.util.concatenate(ties).export(OUT/'two-retention-ties-envelope.stl')
result={'body':'trunk_base','units':'mm','battery':{'center':[-37.6,0,-4],'dimensions':[22,34,63],'mass_g_nominal':57,'mass_g_range':[37,77]},'source_transform':T.tolist(),'integrated_support_bounds':mod.bounds.tolist(),'original_frame_volume_mm3':frame.volume,'integrated_volume_mm3':mod.volume,'net_added_volume_mm3':mod.volume-frame.volume,'added_solid_PLA_1p24_g_cm3_g':(mod.volume-frame.volume)*.00124,'watertight':mod.is_watertight,'solid_count':len(mod.split()),'tie_spec':'2x 4.8mm nylon cable ties, >=200mm nominal length; modeled 1.2mm thickness; buckle kept outside rear','tie_center_z_mm':slot_z,'modified_existing_features':'The four existing slot passages at Y=+-18.365 extended through rear rib with 2.1x6.2mm openings. Motor mating surfaces and original screw holes untouched.'}
(OUT/'design.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
