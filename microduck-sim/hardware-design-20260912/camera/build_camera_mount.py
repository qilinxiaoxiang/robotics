"""Camera Module 3 Wide mount, millimetres. Run with CadQuery >=2.8.
Part coordinates are manufacturing coordinates; assembly axes are documented in interface.json.
No original Microduck files are modified. Camera envelope is a clearance proxy, not a Raspberry Pi CAD model.
"""
from pathlib import Path
import json, math
import cadquery as cq
import trimesh
import numpy as np

OUT=Path(__file__).resolve().parent
PARAMS={
 'pcb_width':25.0,'pcb_height':23.862,'pcb_thickness':1.12,
 'pcb_holes':[(2,2),(23,2),(2,14.5),(23,14.5)],
 'pcb_hole_diameter':2.2,'m2_clearance':2.4,'standoff_diameter':4.6,
 'backplate_thickness':2.4,'rear_clearance':4.8,
 'nut_m2_af':4.1,'nut_m2_depth':1.65,
 'mount_foot':[30,16,3],'mount_holes':[[-11,0],[11,0]],'m3_clearance':3.4,
 'hinge_center':[0,0,11],'hinge_lug_width':8.0,'hinge_gap':8.5,
 'hinge_ear_outer_width':16.0,'hinge_lug_depth':9.0,'hinge_local_y':-9.5,
 'pitch_check_degrees':list(range(-45,46,5)),
}

def box(x,y,z,dx,dy,dz):
 return cq.Workplane('XY').box(dx,dy,dz,centered=False).translate((x,y,z))

def x_hole(x,y,z,length,diam=3.4,teardrop=False):
 h=cq.Workplane('YZ',origin=(x,0,0)).center(y,z).circle(diam/2).extrude(length)
 if teardrop:
  r=diam/2
  top=cq.Workplane('YZ',origin=(x,0,0)).polyline([(y-r*.707,z+r*.707),(y+r*.707,z+r*.707),(y,z+r*1.42)]).close().extrude(length)
  h=h.union(top)
 return h

def make_cradle():
 p=PARAMS
 s=box(-2.5,-2.5,0,p['pcb_width']+5,p['pcb_height']+5.138,p['backplate_thickness'])
 # Open rear access window: four corner hole supports remain connected by the frame.
 s=s.cut(box(4,4,-1,p['pcb_width']-8,p['pcb_height']-5.862,p['backplate_thickness']+2))
 for x,y in p['pcb_holes']:
  s=s.union(cq.Workplane('XY').center(x,y).circle(p['standoff_diameter']/2).extrude(p['rear_clearance']).translate((0,0,p['backplate_thickness'])))
 # Lower hinge lug, flat underside for support-free printing.
 s=s.union(box((p['pcb_width']-p['hinge_lug_width'])/2,p['hinge_local_y']-5,0,p['hinge_lug_width'],-.5-(p['hinge_local_y']-5),p['hinge_lug_depth']))
 s=s.cut(x_hole((p['pcb_width']-p['hinge_lug_width'])/2-1,p['hinge_local_y'],p['hinge_lug_depth']/2,p['hinge_lug_width']+2,p['m3_clearance'],teardrop=True))
 for x,y in p['pcb_holes']:
  s=s.cut(cq.Workplane('XY').center(x,y).circle(p['m2_clearance']/2).extrude(12).translate((0,0,-1)))
  # Hexagonal M2 nut recess, accessible from back. Flats clearance, not self-tapping plastic.
  diameter=p['nut_m2_af']/math.cos(math.pi/6)
  s=s.cut(cq.Workplane('XY').center(x,y).polygon(6,diameter).extrude(p['nut_m2_depth']))
 return s

def make_foot():
 p=PARAMS;fw,fd,ft=p['mount_foot'];outer=p['hinge_ear_outer_width'];gap=p['hinge_gap'];hz=p['hinge_center'][2]
 s=box(-fw/2,-fd/2,0,fw,fd,ft)
 for x in (-outer/2,gap/2):
  ear=(cq.Workplane('YZ',origin=(x,0,0)).moveTo(-5,ft-.2).lineTo(5,ft-.2).lineTo(5,hz)
       .threePointArc((0,hz+5),(-5,hz)).close().extrude((outer-gap)/2))
  s=s.union(ear)
 s=s.cut(x_hole(-outer/2-1,0,hz,outer+2,p['m3_clearance'],teardrop=True))
 for x,y in PARAMS['mount_holes']:
  s=s.cut(cq.Workplane('XY').center(x,y).circle(p['m3_clearance']/2).extrude(ft+2).translate((0,0,-1)))
  # Reserve space for a 7mm M3 washer and button head beside the hinge ears.
  s=s.cut(cq.Workplane('XY').center(x,y).circle(3.7).extrude(3.2).translate((0,0,ft)))
 return s

def to_assembly(s):
 # Source: PCB in XY, forward +Z. Assembly: X right, Z up, camera forward -Y.
 p=PARAMS
 return s.rotate((0,0,0),(1,0,0),90).translate((-p['pcb_width']/2,p['hinge_lug_depth']/2,p['hinge_center'][2]-p['hinge_local_y']))

def make_proxy():
 p=PARAMS;back=p['backplate_thickness']+p['rear_clearance']
 pcb=box(0,0,back,p['pcb_width'],p['pcb_height'],p['pcb_thickness'])
 for x,y in PARAMS['pcb_holes']:
  pcb=pcb.cut(cq.Workplane('XY').center(x,y).circle(p['pcb_hole_diameter']/2).extrude(p['pcb_thickness']+1).translate((0,0,back-.1)))
 # Camera carrier; conservative official body and protrusion envelope.
 lens_base=box(7.1,9.0,back+1.12,10.8,10.8,4.07)
 lens=cq.Workplane('XY').center(12.5,14.4).circle(3.475).extrude(4.23).translate((0,0,back+1.12+4.07))
 # Rear FFC connector proxy: full-width official 19.61mm, 5.71mm edge depth.
 connector=box((25-19.61)/2,23.862-5.71,back-2.75,19.61,5.71,2.75)
 # Cable keepout, not a real cable CAD. Exits top edge without a wall in its way.
 ribbon=box(2.5,23.862,back-2.5,20,12,0.5)
 return {'pcb':pcb,'lens_body':lens_base,'lens':lens,'rear_connector':connector,'ribbon_keepout':ribbon}

def exportpart(name,solid):
 assert solid.val().isValid(),name
 cq.exporters.export(solid,str(OUT/f'{name}.step'))
 cq.exporters.export(solid,str(OUT/f'{name}.stl'),tolerance=.04,angularTolerance=.08)
 mesh=trimesh.load(OUT/f'{name}.stl',force='mesh')
 assert mesh.is_watertight,(name,'not watertight')
 assert mesh.is_winding_consistent,(name,'winding')
 assert mesh.volume>0,(name,'volume')
 assert len(mesh.split())==1,(name,'disconnected')
 return {'extent_mm':mesh.extents.tolist(),'bounds_mm':mesh.bounds.tolist(),
         'volume_mm3':float(mesh.volume),'estimated_PETG_g_at_1.27_g_cm3':float(mesh.volume*.00127),
         'watertight':bool(mesh.is_watertight),'winding_consistent':bool(mesh.is_winding_consistent),
         'connected_bodies':len(mesh.split()),'triangles':len(mesh.faces)}

def intersection_mm3(a,b):
 v=a.intersect(b).val().Volume()
 return max(0,float(v))

cradle=make_cradle();foot=make_foot();proxy=make_proxy();mounted=to_assembly(cradle)
checks={'parts':{},'intersections_mm3':{},'pitch_collision_checks':[]}
for name,part in [('camera_cradle',cradle),('camera_pitch_foot',foot)]:
 checks['parts'][name]=exportpart(name,part)
for name,part in proxy.items():
 overlap=intersection_mm3(cradle,part)
 checks['intersections_mm3']['cradle_vs_'+name]=overlap
 assert overlap<1e-5,(name,overlap)
for angle in PARAMS['pitch_check_degrees']:
 rotated=mounted.rotate((0,0,11),(1,0,11),angle)
 vol=intersection_mm3(rotated,foot)
 checks['pitch_collision_checks'].append({'degrees':angle,'collision_mm3':vol})
 assert vol<1e-5,(angle,vol)
# Assembly includes separately named references; reference camera objects are never print pieces.
asm=cq.Assembly(name='CameraModule3Wide_Mount')
asm.add(foot,name='PRINT_camera_pitch_foot',color=cq.Color(.14,.27,.35))
asm.add(mounted,name='PRINT_camera_cradle',color=cq.Color(.96,.59,.18))
for name,part in proxy.items():
 color={'pcb':cq.Color(.05,.45,.21),'lens_body':cq.Color(.25,.25,.27),'lens':cq.Color(.06,.08,.10),
        'rear_connector':cq.Color(.65,.63,.57),'ribbon_keepout':cq.Color(.8,.82,.87,.5)}[name]
 asm.add(to_assembly(part),name='REFERENCE_'+name,color=color)
asm.export(str(OUT/'camera_mount_assembly.step'))
interface={
 'units':'mm','coordinate_system':'X right across camera PCB; +Z up from flat foot; camera optical axis -Y at zero pitch',
 'mounting_face':'foot underside Z=0; dimensions X=30 Y=16',
 'mount_hole_centers_mm':[[-11,0,0],[11,0,0]],'mount_hole_diameter_mm':3.4,
 'mount_foot_thickness_mm':3,'hinge_axis_point_mm':[0,0,11],'hinge_axis_direction':[1,0,0],
 'camera_front_normal_zero_pitch':[0,-1,0],
 'optical_lens_front_center_mm':[0,4.5-(7.2+1.12+8.3),20.5+14.4],
 'pcb_back_plane_zero_pitch':'Y = -2.7',
 'cradle_to_assembly':{'rotation_x_degrees':90,'translation_mm':[-12.5,4.5,20.5]},
 'source_drawing':'../reference/camera-wide.pdf',
 'note':'No robot-head orientation or mating-shell geometry is assumed. Camera proxy and pitch clearance are computational checks, not physical fit tests.'
}
(OUT/'parameters.json').write_text(json.dumps(PARAMS,indent=2)+'\n')
(OUT/'interface.json').write_text(json.dumps(interface,indent=2)+'\n')
(OUT/'verification.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
