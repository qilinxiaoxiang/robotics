"""MicroDuck battery backpack, referenced to CURRENT community 3MF object 12.
Local axes: U=-original Z, V=original Y+10.1495, W=original X-9.5.
No complete-robot assembly claim. Units: mm.
"""
from pathlib import Path
import json
import cadquery as cq
import numpy as np
import trimesh
OUT=Path(__file__).resolve().parent
P={"battery_max": [34.0,63.0,22.0],"cavity":[36.0,65.0,24.0],"wall":2.0,"floor":2.5,"lid":2.5,"riser_height":8.0,"frame_contact_x":1.5,"tray_base_x":9.5,"origin_y":-10.1495,"tie_rows_v":[-18.3495,18.3495],"frame_slot_z":[-18.365,18.365],"strap_width":4.8,"strap_thickness_max":1.0}
W,L,H=P['cavity'];wall=P['wall'];base=P['floor'];OW,OL=W+2*wall,L+2*wall

def box(dx,dy,dz,u=0,v=0,w=0):
 return cq.Workplane('XY').box(dx,dy,dz,centered=(True,True,False)).translate((u,v,w))
# Tray: full floor; structural side and end walls; no fastener inside battery cavity.
tray=box(OW,OL,H+base).cut(box(W,L,H+1,w=base))
# Cable egress: one 12 mm wide, 6 mm deep top notch in +V end wall.
tray=tray.cut(box(12,wall+2,6.2,v=OL/2-wall/2,w=base+H-6))
# Guiding ears straddle each structural strap outside the side wall.
for v in P['tie_rows_v']:
 for u in [-OW/2,OW/2]:
  for dv in [-4.15,4.15]:
   tray=tray.union(box(1.4,1.8,7,u=u,v=v+dv,w=base+H-7))
# Riser: ring 3 mm thick at tray underside; 8 separated feet avoid original four slots.
riser=box(OW,OL,3,w=-3).cut(box(W,L,5,w=-4))
for v in P['tie_rows_v']:
 for u in P['frame_slot_z']:
  for dv in [-5.5,5.5]:
   riser=riser.union(box(3.2,3.0,5,u=u,v=v+dv,w=-8))
# Lid: hard load path from ties to rim, not directly onto battery pouch.
lid_z=base+H
lid=box(OW+3.0,OL+.6,P['lid'],w=lid_z)
# Four corner guide tabs outside tray. Clearance .3 mm per wall face.
for u in [-OW/2-.8,OW/2+.8]:
 for v in [-OL/2+5,OL/2-5]:
  lid=lid.union(box(1.0,6.0,3.2,u=u,v=v,w=lid_z-3))
# Side notches locate the two ties in V while keeping top face flat for printing upside down.
for v in P['tie_rows_v']:
 for u in [-OW/2-1.5,OW/2+1.5]:
  lid=lid.cut(box(1.5,6.5,P['lid']+1,u=u,v=v,w=lid_z-.1))
# Separate flat power-board shelf; boards strap on 2 mm standoffs, not on battery.
# The shelf is independent of assembled backplate; its final attachment remains separate work.
# Only main battery structural parts are emitted in this revision.
parts={'battery_tray':tray,'frame_riser':riser,'battery_lid':lid}
printparts={'battery_tray':tray,'frame_riser':riser.rotate((0,0,0),(1,0,0),180),'battery_lid':lid.rotate((0,0,0),(1,0,0),180).translate((0,0,lid_z+P['lid']))}
metrics={}
for name,shape in parts.items():
 cq.exporters.export(shape,str(OUT/(name+'.step')))
 cq.exporters.export(printparts[name],str(OUT/(name+'.stl')),tolerance=.025,angularTolerance=.08)
 m=trimesh.load(OUT/(name+'.stl'),force='mesh');metrics[name]={'cad_valid':shape.val().isValid(),'solid_count':len(shape.solids().vals()),'volume_mm3':float(shape.val().Volume()),'print_bounds_mm':m.bounds.tolist(),'print_extents_mm':m.extents.tolist(),'watertight':bool(m.is_watertight),'mesh_components':len(m.split(only_watertight=False))}
# Assembly preserves local U,V,W.
assy=cq.Assembly(name='MicroDuck_battery_backpack_local')
for name,shape in parts.items():assy.add(shape,name=name)
assy.save(str(OUT/'battery_backpack_assembly.step'))
# Reference envelope is separate from printable parts.
env=box(*P['battery_max'],w=base+1.0)
cq.exporters.export(env,str(OUT/'battery_envelope_reference.step'))
# Original frame mesh transformed to backpack-local coordinates.
d=np.load(OUT/'source-frame-12.npz');old=d['vertices'];verts=np.column_stack([-old[:,2],old[:,1]-P['origin_y'],old[:,0]-P['tray_base_x']]);frame=trimesh.Trimesh(verts,d['faces'],process=True);frame.export(OUT/'a_obj_reference_local.stl')
# Collision volumes compare each PRINTABLE assembly part with current a.obj, not full robot.
collisions={}
for name,shape in parts.items():
 v,f=shape.val().tessellate(.025,.08);mesh=trimesh.Trimesh(np.array([[a.x,a.y,a.z] for a in v]),np.array(f),process=True)
 try:
  inter=trimesh.boolean.intersection([frame,mesh],engine='manifold');collisions[name]={'intersection_volume_mm3':float(inter.volume),'intersection_empty':bool(inter.is_empty)}
 except Exception as e:collisions[name]={'error':str(e)}
 mesh.export(OUT/(name+'_assembly_position.ply'))
meta={'parameters':P,'local_axes':'U=-original Z; V=original Y+10.1495; W=original X-9.5','local_to_a_obj_4x4':[[0,0,1,9.5],[0,1,0,-10.1495],[-1,0,0,0],[0,0,0,1]],'coordinate_handedness':'Right-handed rigid rotation and translation.','metrics':metrics,'a_obj_collisions':collisions,'assembly_unverified':'Only current a.obj checked. Other robot parts, wiring, dynamic motion and print fit are unverified.'}
(OUT/'design-metrics.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
