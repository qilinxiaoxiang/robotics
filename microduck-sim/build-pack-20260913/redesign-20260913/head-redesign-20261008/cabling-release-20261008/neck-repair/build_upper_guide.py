"""Two-case-screw upper guide candidate; body3, unchanged receivingOD7mm."""
import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;O=D/'guide-clips';O.mkdir(exist_ok=True)
C=np.array([56.,0.,123.5]);box=lambda size,pos:mf.Manifold.cube(size).translate(pos)
body=box([5,17,5.2],[-2.5,-8.5,-5.2]);lid=box([5,17,5.2],[-2.5,-8.5,0]);channel=mf.Manifold.cylinder(5.4,3.7,3.7,64).rotate([0,90,0]).translate([-2.7,0,0]);body=body-channel;lid=lid-channel
for y in [-6,6]:
 body=body-mf.Manifold.cylinder(4.7,.8,.8,32).translate([0,y,-4.6]);lid=lid-mf.Manifold.cylinder(5.4,1.1,1.1,32).translate([0,y,-.1]);lid=lid-mf.Manifold.cylinder(3.4,2.05,2.05,40).translate([0,y,2])
body=body.translate(C.tolist());lid=lid.translate(C.tolist())
flange=mf.Manifold.cylinder(2,2.4,2.4,48).translate([18,-22.5,129.1145997])+mf.Manifold.cylinder(2,2.4,2.4,48).translate([34,-22.5,129.1145997])+box([16,2.4,2],[18,-23.7,129.1145997])
for x in [18,34]:flange=flange-mf.Manifold.cylinder(2.2,1.1,1.1,32).translate([x,-22.5,129.0145997])
arm=box([2.4,8,2],[32.8,-30.5,129.1145997])+box([24.4,2.4,2],[32.8,-30.5,129.1145997])+box([2.4,10,4.7],[54.8,-30.5,126.5])+box([2.4,14.5,2],[54.8,-22.5,126.5])+box([2.4,2,11.2],[54.8,-10,117.3])+box([2.4,10,2],[54.8,-9,117.3])
base=body+flange+arm
report={'integrationReady':False,'guideBody':'yaw_roll_motion','center':C.tolist(),'roundReceivingODMm':7,'printedHoleDiameterMm':7.4,'caseMount':{'ids':['S13-case-097','S13-case-098'],'sourceLengthMm':10,'newLengthMm':12,'addedStackMm':2,'preservedNominalThreadEngagementMm':3.5},'lidFasteners':{'quantity':2,'spec':'M2 x 6 TAP','headDatumAboveSplitMm':2,'capClearanceDiameterMm':2.2,'pilotDiameterMm':1.6,'pilotDepthMm':4.6,'nominalEngagementMm':4,'screwTipToOuterBottomMm':1.2,'counterboreDiameterMm':4.1,'headHeightReceivingMm':1.5},'parts':[]}
for name,s in [('upper-guide-base',base),('upper-guide-lid',lid)]:
 assert s.status()==mf.Error.NoError;pieces=s.decompose();report['parts'].append({'name':name,'connectedBodies':len(pieces),'volumeMm3':s.volume()});assert len(pieces)==1,(name,[p.volume() for p in pieces]);m=s.to_mesh64();tm=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert tm.is_watertight and tm.is_volume;p=O/(name+'-world.stl');p.write_text(trimesh.exchange.stl.export_stl_ascii(tm));r=trimesh.load(p,force='mesh');assert r.is_watertight and r.is_volume;report['parts'][-1].update(mesh=str(p),sha256=c.sha(p),bounds=r.bounds.tolist())
report['sourceHashes']={str(Path(__file__)):c.sha(Path(__file__))};c.save(O/'upper-guide-candidate.json',report);print(json.dumps(report))
