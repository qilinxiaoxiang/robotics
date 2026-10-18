"""Reversible accessory mounts using existing holes; frozen robot parts unchanged."""
from pathlib import Path
import cadquery as cq,trimesh,numpy as np,json
O=Path(__file__).resolve().parent/'service-mounts';O.mkdir(exist_ok=True)
def box(x0,x1,y0,y1,z0,z1):return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0).translate(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))
def cylz(x,y,z0,z1,r):return cq.Workplane('XY').center(x,y).circle(r).extrude(z1-z0).translate((0,0,z0))
def cylx(x0,x1,y,z,r):return cq.Workplane('YZ').center(y,z).circle(r).extrude(x1-x0).translate((x0,0,0))
parts=[]
def emit(name,shape,orientation=None):
 cq.exporters.export(shape,str(O/(name+'.step')));cq.exporters.export(shape,str(O/(name+'-body.stl')))
 m=trimesh.load(O/(name+'-body.stl'),force='mesh');assert m.is_watertight and len(m.split())==1
 p=m.copy()
 if orientation is not None:p.apply_transform(orientation)
 p.apply_translation(np.r_[-p.bounds.mean(0)[:2],-p.bounds[0,2]]);p.export(O/(name+'-print.stl'))
 parts.append({'name':name,'body':'trunk_base','mesh':str(O/(name+'-body.stl')),'print_file':str(O/(name+'-print.stl')),'bounds_mm':m.bounds.tolist(),'solid_PLA_mass_g':m.volume*.00124,'water_tight':m.is_watertight})
 return m
# Eleven insulated fuses in two narrower levels: six upper, five lower.
# Existing screw heads remain accessible at z=-69; lower tray avoids their axes.
h=box(-49.8,-21.2,-21.3,21.3,-69,-67.4)
for x in [-54.931,-16.069]:
 for y in [-12.7,12.7]:
  h=h.union(cylz(x,y,-69,-57.5,2.6))
  xa,xb=sorted([x,-35.5]);h=h.union(box(xa,xb,y-2.6,y+2.6,-69,-67.4))
  h=h.cut(cylz(x,y,-70,-57,1.2))
h=h.union(box(-49.8,-21.2,-21.3,21.3,-77.1,-75.5))
for y0,y1 in [(-21.3,-20.1),(20.1,21.3)]:
 h=h.union(box(-49.8,-21.2,y0,y1,-77.1,-61))
levels=[(np.linspace(-15.5,15.5,6),-64.9,-67.4),(np.linspace(-12.4,12.4,5),-73.0,-75.5)]
for centers,cz,floor in levels:
 for y in (centers[:-1]+centers[1:])/2:h=h.union(box(-47.5,-23.5,y-.4,y+.4,floor,floor+1.8))
 for x in ([-46.5,-24.5] if floor>-70 else [-44,-27]):
  for y in [-19.3,19.3]:h=h.cut(box(x-1.4,x+1.4,y-.8,y+.8,floor-2,floor+.2))
emit('fuse-bank',h)
fuses=[]
for i,(y,cz) in enumerate([(y,cz) for centers,cz,floor in levels for y in centers]):
 m=trimesh.creation.box([24,5,5]).apply_translation([-35.5,y,cz]);m.export(O/f'fuse-{i+1:02d}-envelope.stl');fuses.append({'id':i+1,'center_mm':[-35.5,float(y),float(cz)],'envelope_mm':[24,5,5]})
# Four 2.5 mm-wide, 1.1 mm-thick purchased-tie envelopes; printed slots unchanged.
ties=[]
for i,(x,zlo,zhi) in enumerate([(-46.5,-69.75,-61.8),(-24.5,-69.75,-61.8),(-44,-77.75,-69.75),(-27,-77.75,-69.75)],1):
 t=box(x-1.25,x+1.25,-19.3,19.3,zlo-.55,zlo+.55).union(box(x-1.25,x+1.25,-19.3,19.3,zhi-.55,zhi+.55))
 for y in [-19.3,19.3]:t=t.union(box(x-1.25,x+1.25,y-.55,y+.55,zlo,zhi))
 cq.exporters.export(t,str(O/f'fuse-tie-{i}-envelope.stl'));ties.append({'id':i,'width_mm':2.5,'thickness_mm':1.1,'loop_x_mm':x,'loop_y_mm':[-19.3,19.3],'loop_z_mm':[zlo,zhi]})
# Low-voltage alarm carrier bolts to four existing IMU rear-cover holes.
# The alarm's complete supplier maximum box has 0.6 mm total side clearance.
a=box(-64.6,-62.6,-21.3,21.3,.8,29.5)
a=a.cut(box(-65,-62,-10.5,10.5,6,24))
for y in [-17.5,17.5]:
 for z in [4,26]:a=a.cut(cylx(-65,-62,y,z,1.15))
for y0,y1 in [(-21.3,-19.3),(19.3,21.3)]:a=a.union(box(-78,-62.6,y0,y1,.8,29.5))
a=a.union(box(-78,-62.6,-21.3,21.3,.8,2.2))
# The removable alarm is retained by two narrow straps through sidewall slots.
for y0,y1 in [(-22,-19),(19,22)]:
 for z in [7,23]:a=a.cut(box(-76.7,-73.7,y0,y1,z-1.1,z+1.1))
# Positive Y is the alarm pin end. Central slot exposes the 5-pin header.
a=a.cut(box(-79,-64.6,19,22,8,22))
# Pololu1408 body8.5Y x3.7X x3.5Z, actuator3mm above; a single edge strap leaves it clear.
# A low side saddle extends beyond the alarm, and terminal opening stays clear of the alarm box.
a=a.union(box(-85.1,-62.6,-8,8,28,29.5)).union(box(-85.1,-77.5,-8,8,29.5,31.5))
for x0,x1 in [(-84.0,-83.35),(-79.25,-78.6)]:a=a.union(box(x0,x1,-4.7,4.7,31.5,32.6))
for y0,y1 in [(-5.3,-4.45),(4.45,5.3)]:a=a.union(box(-84,-78.6,y0,y1,31.5,32.6))
a=a.cut(box(-82.65,-79.95,-3.6,3.6,27.9,32))
for y in [-6.8,6.8]:a=a.cut(box(-84.85,-82.45,y-.7,y+.7,27.9,31.7))
T=np.eye(4);T[:3,:3]=[[0,1,0],[0,0,1],[1,0,0]]
emit('voltage-alarm-carrier',a,T)
alarm=trimesh.creation.box([11,38,25]).apply_translation([-70.7,0,15]);alarm.export(O/'voltage-alarm-envelope.stl')
plug=trimesh.creation.box([12,22,13]).apply_translation([-70.7,30,15]);plug.export(O/'alarm-connector-envelope.stl')
# Switch metal body and full actuator travel, not a nominal point pose.
sw=trimesh.creation.box([3.7,8.5,3.5]).apply_translation([-81.3,0,33.25]);sw.export(O/'en-switch-body-envelope.stl')
trimesh.creation.box([1.6,3.6,3]).apply_translation([-81.3,0,36.5]).export(O/'en-switch-actuator-envelope.stl')
# Manufacturer does not dimension pin length. This is a fabrication limit for insulated pin tails.
trimesh.creation.box([2.4,6.8,11.5]).apply_translation([-81.3,0,25.75]).export(O/'en-switch-terminal-envelope.stl')
st=box(-84.65,-82.65,-6.8,6.8,27.1,27.9).union(box(-84.65,-82.65,-6.8,6.8,35.0,35.8))
for y in [-6.8,6.8]:st=st.union(box(-84.65,-82.65,y-.4,y+.4,27.5,35.4))
cq.exporters.export(st,str(O/'en-switch-tie-envelope.stl'))
result={'en_switch_mount':{'model':'Pololu1408','body_mm':[3.7,8.5,3.5],'center_mm':[-81.3,0,33.25],'actuator_travel_envelope_mm':[1.6,3.6,3],'fastening':'one2mm wide,0.8mm thick tie over the rearward body edge; not over actuator','terminal_reservation_mm':[2.4,6.8,11.5],'terminal_basis':'manufacturer drawing omits pin length; insulated tails must fit this fabrication envelope, first-article required','source':'https://a.pololu-files.com/picture/0J4359.560.jpg'},'tie_reservations':ties,'alarm_connector_reservation':{'axis':'+Y along 38mm alarm long edge','center_mm':[-70.7,30,15],'size_mm':[12,22,13],'basis':'12mm plug +10mm bend; nominal pin row at height15, supplier has no dimensioned connector drawing. Align pin row with side window during first article.'},'body':'trunk_base','frozen_parts_modified':False,'parts':parts,'fuses':fuses,'alarm_envelope_mm':[11,38,25],'alarm_center_mm':[-70.7,0,15],'fasteners':[
 {'use':'Fuse carrier + existing D42V110F5 shelf/board stack','spec':'M2 x 20 machine screw','quantity':4,'replaces':'4 x M2 x 8; retain existing four nuts'},
 {'use':'Alarm carrier + existing IMU rear cover','spec':'M2 x 8 machine screw','quantity':4,'replaces':'4 x M2 x 6 into original 1.6mm pilots'}],
 'status':'Generated engineering accessory mounts; mesh/fit checks are separate. No print or physical load acceptance.',
 'additional_mass_warning':'New carrier volume, alarm 7g, eleven fuses, wires and replacement fasteners were not in the old 45-case dynamics suite.'}
(O/'design.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
