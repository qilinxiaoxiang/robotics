"""Body2 guide: existing motor11 passive output four-hole face, uniform2mm flange."""
import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;O=D/'guide-clips';O.mkdir(exist_ok=True);box=lambda size,pos:mf.Manifold.cube(size).translate(pos)
base=box([5,17,5.2],[-2.5,-8.5,-5.2]);lid=box([5,17,5.2],[-2.5,-8.5,0]);channel=mf.Manifold.cylinder(5.4,3.7,3.7,64).rotate([0,90,0]).translate([-2.7,0,0]);base-=channel;lid-=channel
for y in [-6,6]:
 base-=mf.Manifold.cylinder(4.7,.8,.8,32).translate([0,y,-4.6]);lid-=mf.Manifold.cylinder(5.4,1.1,1.1,32).translate([0,y,-.1]);lid-=mf.Manifold.cylinder(3.4,2.05,2.05,40).translate([0,y,2])
C=[44,-25,76];base=base.rotate([0,90,0]).translate(C);lid=lid.rotate([0,90,0]).translate(C)
flange=mf.Manifold.cylinder(2,9.2,9.2,96)-mf.Manifold.cylinder(2.2,4,4,64).translate([0,0,-.1])
for x,y in [(6,0),(-6,0),(0,6),(0,-6)]:flange-=mf.Manifold.cylinder(2.2,1.1,1.1,32).translate([x,y,-.1])
flange=flange.rotate([90,0,0]).translate([26,-17.5,82.4215]);arm=box([9,7.5,3],[31,-25,76]);base=base+flange+arm
r={'integrationReady':False,'body':'neck_pitch','bodyIndex':2,'anchorCenterWorldMm':C,'wireAxisWorld':[0,0,1],'receivingODMm':7,'holeDiameterMm':7.4,'sourceMounts':['S11-horn-037','S11-horn-038','S11-horn-039','S11-horn-040'],'sourceMountLengthMm':6,'newMountLengthMm':8,'uniformAddedStackMm':2,'mountHoleClearanceDiameterMm':2.2,'lidFasteners':{'spec':'M2 x 6 TAP','quantity':2,'pilotDiameterMm':1.6,'engagementMm':4,'bottomMarginMm':1.2,'headDiameterReceivingMm':4.1,'headHeightReceivingMm':1.5},'parts':[]}
for name,s in [('lower-yaw-guide-base',base),('lower-yaw-guide-lid',lid)]:
 assert s.status()==mf.Error.NoError and len(s.decompose())==1;m=s.to_mesh64();tm=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert tm.is_watertight and tm.is_volume;p=O/(name+'-world.stl');p.write_text(trimesh.exchange.stl.export_stl_ascii(tm));rd=trimesh.load(p,force='mesh');assert rd.is_watertight and rd.is_volume and len(rd.split())==1;r['parts'].append({'key':name,'mesh':str(p),'sha256':c.sha(p),'bounds':rd.bounds.tolist(),'singleConnectedClosedBody':True})
r['sourceHashes']={str(Path(__file__)):c.sha(Path(__file__))};c.save(O/'lower-yaw-guide-candidate.json',r);print(json.dumps(r))
