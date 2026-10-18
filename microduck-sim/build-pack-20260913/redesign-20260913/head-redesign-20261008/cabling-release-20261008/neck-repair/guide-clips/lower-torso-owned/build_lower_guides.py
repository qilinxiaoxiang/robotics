from pathlib import Path
import sys,json,hashlib,os,base64
D=Path(__file__).resolve().parent;N=D.parent.parent;H=N.parent.parent;sys.path.insert(0,str(N))
from short_path_worker import guard,save,sha
guard()
import manifold3d as mf,numpy as np,trimesh
box=lambda size,pos:mf.Manifold.cube(size).translate(pos)
def cy(r,h,p):return mf.Manifold.cylinder(h,r,r,64).rotate([90,0,0]).translate(p)
def clamp(C):
 b=box([17,5.2,5],[-8.5,0,-2.5]);l=box([17,5.2,5],[-8.5,-5.2,-2.5]);ch=mf.Manifold.cylinder(5.4,3.7,3.7,64).translate([0,0,-2.7]);b=b-ch;l=l-ch
 for x in [-6,6]:
  b=b-cy(.8,4.7,[x,4.6,0]);l=l-cy(1.1,5.4,[x,.1,0]);l=l-cy(2.05,3.4,[x,-2,0])
 return b.translate(C),l.translate(C)
def write(name,s):
 assert s.status()==mf.Error.NoError and len(s.decompose())==1,(name,s.status(),len(s.decompose()))
 m=s.to_mesh64();t=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert t.is_watertight and t.is_volume;p=D/(name+'-world.stl');lines=['solid exact_cad']
 for norm,tri in zip(t.face_normals,t.triangles):
  lines += ['facet normal '+' '.join(repr(float(x)) for x in norm),'outer loop']
  lines += ['vertex '+' '.join(repr(float(x)) for x in v) for v in tri]
  lines += ['endloop','endfacet']
 lines += ['endsolid exact_cad'];p.write_text('\n'.join(lines)+'\n');r=trimesh.load(p,force='mesh',process=False);uv,ui=np.unique(np.asarray(r.vertices),axis=0,return_inverse=True);r=trimesh.Trimesh(uv,ui[np.asarray(r.faces)],process=False);assert r.is_watertight and r.is_volume
 return {'key':name,'mesh':str(p),'sha256':sha(p),'bounds':r.bounds.tolist(),'volumeMm3':r.volume}
C=[42,-24,56];base,lid=clamp(C)
f=cy(2.4,2,[18,-13.5,54.9215])+cy(2.4,2,[34,-13.5,54.9215])+box([16,2,2.4],[18,-15.5,53.7215])
for x in [18,34]:f=f-cy(1.1,2.2,[x,-13.4,54.9215])
arm=box([2.8,9.5,2.4],[32.6,-23,54.9215]);base=base+f+arm
rows=[{'body':'neck','centerMm':C,'channelAxis':[0,0,1],'mountIds':['S12-case-089','S12-case-090'],'oldLengthMm':10,'newLengthMm':12,'addedStackMm':2,'preservedEngagementMm':3.5,'parts':[write('neck-body1-guide-base',base),write('neck-body1-guide-lid',lid)]}]
C=[8,-25,47];base,lid=clamp(C)
f=cy(8.5,2,[26,-18.40119,32.5215])-cy(4.6,2.2,[26,-18.30119,32.5215])
for x,z in [(20,32.5215),(32,32.5215),(26,26.5215),(26,38.5215)]:f=f-cy(1.1,2.2,[x,-18.30119,z])
# Short initial candidate arm; any source-shell intersection is a failing test.
arm=box([3,2,15],[17.5,-20.40119,32.5])+box([12.5,2.4,3],[5,-22,44.5])+box([3,4,3],[17.5,-23,44.5])
base=base+f+arm
cache=H/'usb-access/usb-repair/robot-source-cache';index=json.loads((cache/'index.json').read_text());source=cache/index['parts']['shell_right'];d=json.loads(source.read_text());v=np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3);ix=np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3);shell=mf.Manifold(mf.Mesh64(np.asarray(v,np.float64),np.array(ix,dtype=np.uint64,order="C")));assert shell.status()==mf.Error.NoError
relief=shell+shell.translate([0,-.10,0]);removed=base^relief
protected=None
for x,z in [(20,32.5215),(32,32.5215),(26,26.5215),(26,38.5215)]:
 s=cy(2,1.2,[x,-19.20119,z])-cy(1.1,2.2,[x,-18.30119,z]);protected=s if protected is None else protected+s
lost=(removed^protected).volume();save(D/'torso-relief-receipt.json',{'removedMm3':removed.volume(),'lostOuterHeadSeatSupportMm3':lost,'minimumTestedHeadSeatBackingMm':1.2,'sourceSha256':sha(source),'nativeSourceChanged':False})
assert lost<1e-5,('headseat',lost)
base=(base-relief).simplify(1e-5)
rows.append({'body':'trunk_base','centerMm':C,'channelAxis':[0,0,1],'mountIds':['S12-horn-025','S12-horn-026','S12-horn-027','S12-horn-028'],'oldLengthMm':6,'newLengthMm':8,'addedStackMm':2,'preservedEngagementMm':2.09881,'parts':[write('torso-body0-guide-base',base),write('torso-body0-guide-lid',lid)]})
r={'integrationReady':False,'guides':rows,'lidFasteners':{'spec':'M2 x6 TAP','quantityPerGuide':2,'pilotDiameterMm':1.6,'pilotDepthMm':4.6,'headSeatMm':2,'engagementMm':4,'tipMarginMm':1.2,'clearanceDiameterMm':2.2,'headEnvelopeDiameterMm':4,'headEnvelopeHeightMm':1.5},'channelDiameterMm':7.4,'receivingBundleDiameterMm':7,'function':'Removable routing guide; no quantified axial strain-relief grip is inferred from the clearance channel.','sourceHashes':{str(Path(__file__)):sha(Path(__file__))},'pending':['Actual source/static and relative-joint domain','Screw and guide insertion/tool paths','Wire service spans connecting these new fixed anchors','Native slice and physical support removal']};save(D/'candidate.json',r);print(json.dumps(r))
