"""Single local retainer candidate: keep lens recessed, clear moved GPIO tails."""
from pathlib import Path
import os,json,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;hashes={}
def load(p):
 hashes[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest();m=trimesh.load(p,force='mesh');return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def mesh(s):
 q=s.to_mesh();return trimesh.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True)
def export(s,name):
 m=mesh(s);assert m.is_watertight;assert name!='retainer-roll90-rearseat4-world.stl' or len(s.decompose())==1;file=D/name;m.export(file);return {'mesh':name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'boundsMm':m.bounds.tolist()}
def bx(lo,hi):return mf.Manifold.cube(np.array(hi)-lo).translate(lo)
def cyl(x0,x1,y,z,r):return mf.Manifold.cylinder(x1-x0,r,circular_segments=48).rotate([0,90,0]).translate([x0,y,z])
r=json.loads((H/'camera-retainer/cabling/rotated-camera-candidate/camera-retainer-report.json').read_text());shift=.1;holes=np.array(r['cameraMountHolesWorldMm']);holes[:,0]+=shift;back=float(holes[0,0]);front=back+1.12;cy=-.09137821197509766;zs=sorted(set(holes[:,2]));framefront=back-.5;frameback=back-2.4;bossback=back-3.5;mountfront=back+1.2;wingback=mountfront-1.7;ret=mf.Manifold();rails=[cy-14.5,cy+14.5];bottom=zs[0]-4.1
for y in rails[:1]:ret+=bx([frameback,y-1.6,bottom-1],[framefront,y+1.6,zs[1]+2.4])
ret+=bx([frameback,rails[0]-1.6,bottom-1],[framefront,rails[1]+1.6,bottom+1])
for x,y,z in holes:
 ret+=cyl(bossback,framefront,y,z,2.4)+cyl(framefront,back,y,z,1.9);ry=rails[0];zlo,zhi=(z-2.4,z-.6) if z==zs[0] else (z+.6,z+2.4);ret+=bx([frameback,min(y,ry)-.8,zlo],[framefront,max(y,ry)+.8,zhi]);ret-=cyl(bossback+.4,back+.05,y,z,.8)
anchors=mf.Manifold();screws=[]
for i,(_,y,z) in enumerate(holes,1):
 s=cyl(front-4,front,y,z,1)+cyl(front,front+1.5,y,z,2);f='camera-'+str(i)+'-roll90-rearseat4-screw-world.stl';mesh(s).export(D/f);screws.append({'id':'camera-'+str(i),'spec':'M2 x 4 TAP','headSeatMm':[front,y,z],'outwardAxis':[1,0,0],'lengthMm':4,'pcbThroughMm':1.12,'plasticEngagementMm':2.88,'blindPilotMm':3.1,'tipMarginMm':.22,'mesh':f})
for i,y in enumerate([cy-18,cy+18],1):
 z=119.;ret+=cyl(wingback,mountfront,y,z,2.8);ry=rails[0];ret+=bx([frameback+1.2,min(y,ry)-.7,z-1.5],[framefront+1.2,max(y,ry)+.7,z+1.5]);ret-=cyl(wingback-.1,mountfront+.1,y,z,1.1);anchors+=cyl(mountfront,81.15,y,z,2.8)-cyl(mountfront-.01,80.75,y,z,.8);s=cyl(wingback,wingback+4,y,z,1)+cyl(wingback-1.5,wingback,y,z,2);f='face-wing-'+str(i)+'-roll90-rearseat4-screw-world.stl';mesh(s).export(D/f);screws.append({'id':'face-wing-'+str(i),'spec':'M2 x 4 TAP','headSeatMm':[wingback,y,z],'outwardAxis':[-1,0,0],'lengthMm':4,'retainerThroughMm':mountfront-wingback,'plasticEngagementMm':wingback+4-mountfront,'pilotDepthMm':80.75-mountfront,'tipMarginMm':80.75-(wingback+4),'mesh':f})
cam=load(H/'camera-retainer/cabling/rotated-camera-candidate/camera-shifted-reference-world.stl').translate([shift,0,0]);exports={'camera_board':export(cam,'camera-roll90-rearseat4-world.stl'),'camera_retainer':export(ret,'retainer-roll90-rearseat4-world.stl'),'camera_anchors':None};mesh(anchors).export(D/'camera-anchors-roll90-rearseat4-world.stl')
lens=np.array(r['lensFrontWorldMm'])+[shift,0,0];fov=load(H/'camera-retainer/cabling/rotated-camera-candidate/camera-shifted-fov-world.stl').translate([shift,0,0]);mesh(fov).export(D/'camera-fov-roll90-rearseat4-world.stl');af=cyl(lens[0],lens[0]+.5,lens[1],lens[2],4.5);mesh(af).export(D/'camera-rearseat4-af-additional-receiving-world.stl')
checks=[]
for name,s in [('retainer',ret),('camera',cam)]+[(q['id'],load(D/q['mesh'])) for q in screws]:
 for k,f in [(k,D/(k+'-lowered-pose-world.stl')) for k in ['pi','zero_w_components','zero_w_gpio_solder_tails']]+[(q['key'],H/q['mesh']) for q in json.loads((D/'gpio-individual-receiving-manifest.json').read_text())['additionalParts']]:
  b=load(f);v=max(0,float((s^b).volume()));checks.append({'part':name,'obstacle':k,'overlapMm3':v})
negative=[]
for i,(_,y,z) in enumerate(holes,1):
 old6=cyl(front-6,front,y,z,1)+cyl(front,front+1.5,y,z,2);tails=load(D/'zero_w_gpio_solder_tails-lowered-pose-world.stl');negative.append({'id':'camera-'+str(i),'old6mmAgainstNewTailsMm3':max(0,float((old6^tails).volume()))})
report={'status':'LOCAL_CAMERA_GEOMETRY_ONLY','integrationReady':False,'shiftFromPublishedMm':[shift,0,0],'cameraLensFrontMm':lens.tolist(),'frontEyePlaneMm':89.4,'nominalLensRecessMm':89.4-lens[0],'autofocusAdditionalReceivingMm':.5,'remainingAfterAfReceivingMm':89.4-lens[0]-.5,'autofocusBoundary':'0.5mm additional axial receiving allowance; actual moving lens envelope not manufacturer-verified. Diameter9mm receiving; no lens contact/clamp.','exports':exports,'screws':screws,'piPairChecks':checks,'old6mmNegative':negative,'passedLocalPiChecks':not any(c['overlapMm3']>1e-5 for c in checks),'sourceHashes':hashes,'physicalVerified':False,'strengthVerified':False};(D/'local-camera-roll90-rearseat4-pi-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passedLocalPiChecks'],'remaining':[q for q in checks if q['overlapMm3']>1e-5],'recessMm':report['nominalLensRecessMm'],'afterAF':report['remainingAfterAfReceivingMm']}))
