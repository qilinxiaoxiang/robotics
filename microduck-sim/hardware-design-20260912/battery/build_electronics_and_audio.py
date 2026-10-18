"""Run after build_battery_backpack.py. All lengths mm.
Adds removable electronics deck and audio enclosure. Overrides battery_lid STEP/STL.
Large regulator footprint supplied in task: 43.2 x 31.8 x 11; holes 38.862 x 25.4.
Audio: amplifier 22 x 21 x 12; speaker 21 x 31 x 6. Full robot fit unverified.
"""
from pathlib import Path
import json,numpy as np,cadquery as cq,trimesh
O=Path(__file__).resolve().parent
PARAM={'deck':[64,86,2],'deck_base_w':35,'lid_top_w':29,'mount_uv':[[-27,-37],[27,-37],[-27,37],[27,37]],'large_regulator_center_uv':[0,-18.5],'large_regulator_holes':[38.862,25.4],'small_regulator_center_uv':[-15.5,18],'audio_center_uv':[14,18],'audio_outer':[32,41,23.6],'hardware':'M2x6: deck-to-lid and audio-base-to-deck; M2x8: large board and audio lid. M2 nuts. Verify actual PCB hole diameters before insertion.'}
def box(x,y,z,u=0,v=0,w=0):return cq.Workplane('XY').box(x,y,z,centered=(True,True,False)).translate((u,v,w))
def cyl(r,h,u,v,w):return cq.Workplane('XY').circle(r).extrude(h).translate((u,v,w))
def nut_recess(s,u,v,w,side):
 # Standard M2 nut allowance: 4.3 mm across flats, 1.9 mm high; opening faces outward.
 s=s.cut(cq.Workplane('XY').polygon(6,4.3/np.cos(np.pi/6)).extrude(1.9).translate((u,v,w)))
 s=s.cut(box(4.5,4.3,1.9,u=u+side*2.0,v=v,w=w))
 return s
# Preserve tray/riser. Replace lid underside alignment tabs with flat printable underside.
lid=cq.importers.importStep(str(O/'battery_lid.step'))
lid=lid.cut(box(200,200,100,w=-73.5)) # remove W<26.5 only
for u,v in PARAM['mount_uv']:
 side=1 if u>0 else -1
 lid=lid.union(box(11.5,11,2.5,u=side*24.25,v=np.sign(v)*34,w=26.5))
 lid=lid.union(cyl(3.5,6,u,v,29))
 lid=nut_recess(lid,u,v,31.1,side)
 lid=lid.cut(cyl(1.15,5,u,v,30.8))
# Deck local coordinates have underside W=0, assembled at W=35.
deck=box(64,86,2)
for u,v in PARAM['mount_uv']:deck=deck.cut(cyl(1.15,4,u,v,-1))
# Large regulator: 2 mm board standoffs above a ventilated deck.
for u in [-38.862/2,38.862/2]:
 for v in [-18.5-12.7,-18.5+12.7]:
  deck=deck.union(cyl(2.8,2,u,v,2));deck=deck.cut(cyl(1.15,6,u,v,-1))
for u in [-12,-6,0,6,12]:deck=deck.cut(box(3,20,4,u=u,v=-18.5,w=-1))
# Small regulator: 24 mm clear edge pocket, two transverse retaining ties.
su,sv=PARAM['small_regulator_center_uv']
pocket=box(26,26,4,u=su,v=sv,w=2).cut(box(24,24,5,u=su,v=sv,w=2))
deck=deck.union(pocket)
for du in [-8.5,8.5]:
 for dv in [-8.5,8.5]:deck=deck.union(cyl(1.5,2,su+du,sv+dv,2))
for du in [-8,0,8]:deck=deck.cut(box(2,13,3,u=su+du,v=sv,w=-.5))
for du in [-13,13]:
 for dv in [-7,7]:deck=deck.cut(box(2,3.4,8,u=su+du,v=sv+dv,w=-1))
# Audio box bolts through deck outside amplifier/speaker footprint.
for u in [-13,13]:
 for v in [-17.5,17.5]:deck=deck.cut(cyl(1.15,4,u=u+14,v=v+18,w=-1))
# Audio box: bottom board area + 1 mm gap + separate speaker ledges + screwed grille.
audio=box(32,41,21.6).cut(box(28,37,22,u=0,v=0,w=1.6))
for u in [-13,13]:
 for v in [-17.5,17.5]:
  audio=audio.union(cyl(3,20,u,v,1.6))
  # Floor bolts pass up from deck; M2 nut remains accessible inside corner.
  audio=nut_recess(audio,u,v,1.8,1 if u>0 else -1)
  audio=audio.cut(cyl(1.15,6,u,v,-1))
  # Separate captive nuts for lid, kept clear of all component envelopes.
  audio=nut_recess(audio,u,v,17.4,1 if u>0 else -1)
  audio=audio.cut(cyl(1.15,9,u,v,15.0))
# Amplifier rests 1 mm above floor; ties through base avoid invented screw holes.
for u in [-8,8]:
 for v in [-10,2]:audio=audio.union(box(2.0,2.0,1.0,u=u,v=v,w=1.6))
for u in [-11.8,11.8]:
 for v in [-9,1]:audio=audio.cut(box(1.8,3.4,3,u=u,v=v,w=-.5))
# Speaker ledges at W=15.6: above 12 mm amplifier (base W=2.6).
for u in [-12.05,12.05]:audio=audio.union(box(4.0,25,1,u=u,v=0,w=14.6))
# Wire exit near bottom at -V, 8 x 5 mm; no holes toward battery.
audio=audio.cut(box(8,4,5,u=0,v=-20,w=3))
grille=box(32,41,2,w=21.6).cut(box(22.4,32.4,.61,w=21.59))
for u in [-13,13]:
 for v in [-17.5,17.5]:grille=grille.cut(cyl(1.15,4,u,v,20.6))
for u in [-7.5,-2.5,2.5,7.5]:
 for v in [-10,-5,0,5,10]:grille=grille.cut(cyl(1.2,4,u,v,20.6))
parts={'battery_lid':lid,'electronics_deck':deck,'audio_enclosure':audio,'audio_grille':grille}
prints={'battery_lid':lid.translate((0,0,-26.5)),'electronics_deck':deck,'audio_enclosure':audio,'audio_grille':grille.rotate((0,0,0),(1,0,0),180).translate((0,0,23.6))}
assembly={'battery_lid':lid,'electronics_deck':deck.translate((0,0,35)),'audio_enclosure':audio.translate((14,18,37)),'audio_grille':grille.translate((14,18,37))}
metrics={}
for n,s in parts.items():
 cq.exporters.export(s,str(O/(n+'.step')));cq.exporters.export(prints[n],str(O/(n+'.stl')),tolerance=.025,angularTolerance=.08)
 m=trimesh.load(O/(n+'.stl'),force='mesh');metrics[n]={'cad_valid':s.val().isValid(),'solids':len(s.solids().vals()),'volume_mm3':float(s.val().Volume()),'print_extents':m.extents.tolist(),'watertight':bool(m.is_watertight),'components':len(m.split(only_watertight=False))}
 v,f=assembly[n].val().tessellate(.025,.08);trimesh.Trimesh(np.array([[p.x,p.y,p.z] for p in v]),np.array(f),process=True).export(O/(n+'_assembly_position.ply'))
a=cq.Assembly(name='backpack_electronics_audio')
for n,s in assembly.items():a.add(s,name=n)
for n in ['battery_tray','frame_riser']:a.add(cq.importers.importStep(str(O/(n+'.step'))),name=n)
a.save(str(O/'battery_power_audio_assembly.step'))
# Rectangular component envelopes for collision review and reproducible placement.
envelopes={
 'large_regulator':box(43.2,31.8,11,u=0,v=-18.5,w=39),
 'small_regulator':box(22.9,22.9,9.7,u=-15.5,v=18,w=39),
 'amplifier':box(22,21,12,u=14,v=14,w=39.6),
 'speaker':box(21,31,6,u=14,v=18,w=52.6),
}
for n,s in envelopes.items():
 cq.exporters.export(s,str(O/(n+'_envelope.step')));v,f=s.val().tessellate(.025,.08);trimesh.Trimesh(np.array([[p.x,p.y,p.z] for p in v]),np.array(f),process=True).export(O/(n+'_envelope.ply'))
report={'parameters':PARAM,'metrics':metrics,'assembly_bounds_local_uvw':[[-32,-43,-8],[32,43,60.6]],'assembly_depth_from_original_contact_plane_mm':68.6,'full_robot_fit':'UNVERIFIED: new width 64 mm, height 86 mm, contact-to-outermost depth 68.6 mm.'}
(O/'electronics-audio-metrics.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
