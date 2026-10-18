from pathlib import Path
import json,hashlib,base64
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parent.parent;H=R/'head-redesign-20261008';C=H/'usb-access/usb-repair/robot-source-cache';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def box(lo,hi):return mf.Manifold.cube(np.subtract(hi,lo).tolist()).translate(lo)
def tri(s):
 m=s.to_mesh();return trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=True)
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
def source(key):
 d=json.loads((C/(key+'.json')).read_text());p=np.frombuffer(base64.b64decode(d['positionB64']),dtype='<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(d['indexB64']),dtype='<u4').reshape(-1,3);return trimesh.Trimesh(p,f,process=True)
# Open-top tray: 1 mm free space each side of the published maximum box.
# Bank vertical: X thickness26,Y width65.9,Z length80.9.
bank=box([-95,-32.95,-55.45],[-69,32.95,25.45])
# 3mm robot-facing spine,3mm floor,2mm side cheeks; open front/back band windows.
s=box([-99,-35.95,-59.45],[-63,35.95,-56.45])
s+=box([-66,-35.95,-59.45],[-63,35.95,29])
# Shallow lips prevent side and rear translation without covering buttons/ports.
for y0,y1 in [(-35.95,-33.95),(33.95,35.95)]:
 s+=box([-99,y0,-59.45],[-63,y1,-46.45])
s+=box([-99,-35.95,-59.45],[-97,35.95,-48.45])
# Two positive load-bearing tongues rest on the original floor top Z=-36.
# Their source floor strips Y12.3..17.3 have no ventilation cutout.
for yc in [-14.8,14.8]:
 s+=box([-64.5,yc-2.5,-36],[-45,yc+2.5,-33])
 # Structural rear gusset stops0.8mm before the existing shelf rear edge.
 pts=np.array([[-63,-53],[-50.2,-36],[-63,-36]],float)
 wedge=mf.CrossSection([pts.tolist()]).extrude(5)
 # cross-section coords X,Z; extrusion localZ mapped to -worldY
 mat=np.array([[1,0,0,0],[0,0,-1,yc+2.5],[0,1,0,0]],float)
 s+=wedge.transform(mat)
# Belt passages through spine aligned to the actual source slots. Slots stay
# outside the bank receiving box; a long belt goes around the whole bank.
for zc in [-30.821742128,5.877257872]:
 for yc in [-18.365,18.365]:
  s-=box([-66.2,yc-1.05,zc-3.1],[-62.8,yc+1.05,zc+3.1])
# Single5991 vertical receiving bay belowIMU, all component face/ISET open.
# Official29.1x20.3x10.1 maximum envelope, not a barePCB proxy.
s+=box([-63,-11.15,-53.5],[-60,11.15,-21.9])
s+=box([-63,-11.15,-53.5],[-49.5,11.15,-52.5])
for yc in [-11.65,11.65]:
 s+=box([-63,yc-.5,-53.5],[-49.5,yc+.5,-39])
# Two broad strap slots on unoccupied spine beside board: adjustable retention,
# no tight proprietary connector cutout, no second receiver.
for yc in [-26,26]:
 s-=box([-66.2,yc-2,-49],[-62.8,yc+2,-43])
pd=box([-60,-10.15,-52],[-49.9,10.15,-22.9])
# Rounded external edges are not assumed; model uses straight printable edges.
m=tri(s);m.export(D/'pb1033mi-backpack-world.stl');read=trimesh.load(D/'pb1033mi-backpack-world.stl',force='mesh');assert read.is_watertight and len(read.split())==1 and read.volume>0
printm=read.copy();printm.apply_translation(-read.bounds[0]);printm.export(D/'pb1033mi-backpack-print.stl');tri(bank).export(D/'pb1033mi-reference-world.stl');tri(pd).export(D/'adafruit5991-receiving-world.stl')
report={'status':'candidate-checking','sourceGeneratorSha256':sha(Path(__file__)),'worldMeshSha256':sha(D/'pb1033mi-backpack-world.stl'),'printMeshSha256':sha(D/'pb1033mi-backpack-print.stl'),'sourceIndexSha256':sha(C/'index.json'),'bankPublishedBoxMm':[80.9,65.9,26],'bankBoundsMm':tri(bank).bounds.tolist(),'clearanceEachSideMm':1,'bodyCount':len(read.split()),'watertight':read.is_watertight,'volumeMm3':read.volume,'boundsMm':read.bounds.tolist(),'printRotationMatrix':np.eye(3).tolist(),'printTranslation':(-read.bounds[0]).tolist(),'bedPlaneWorldZ':-59.45,'support':'Tongue undersides extend5.2mm past the gussets; only these accessible bearing ledges may require local support. Main base/spine/cheeks grow directly from a flat floor.','receiver5991BoundsMm':tri(pd).bounds.tolist(),'collisionChecks':[],'receivingChecks':[]}
# Each part loaded independently; broad bounds reject separated geometry first.
for key in ['power_support','regulator','regulator_insert','imu_board','imu_clamp','shell_left','shell_right','fuse_carrier','motor10','motor5','torso_base','hip','right_hip','yaw','right_yaw','motor9','motor4','thigh','right_thigh']:
 mesh=source(key);bb=mesh.bounds
 for label,receiving in [('bank',bank),('5991',pd)]:
  rb=np.array(receiving.bounding_box()).reshape(2,3)
  if np.any(rb[1]<bb[0]) or np.any(bb[1]<rb[0]):report['receivingChecks'].append({'key':key,'receiving':label,'status':'AABB separated'});continue
  obstacle=man(mesh);assert obstacle.status()==mf.Error.NoError
  report['receivingChecks'].append({'key':key,'receiving':label,'intersectionMm3':(receiving^obstacle).volume()})
 if np.any(read.bounds[1]<bb[0]) or np.any(bb[1]<read.bounds[0]):report['collisionChecks'].append({'key':key,'status':'AABB separated'});continue
 o=man(mesh);assert o.status()==mf.Error.NoError
 hit=s^o;report['collisionChecks'].append({'key':key,'intersectionMm3':hit.volume(),'bounds':list(hit.bounding_box()) if not hit.is_empty() else None})
 if hit.volume()>.0001:tri(hit).export(D/(key+'-intersection.stl'))
(D/'candidate-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
