"""Extend only existing speaker pilot through native inner roof after cap union."""
from pathlib import Path
import os,json,hashlib,math,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
from shapely.geometry import Polygon
D=Path(__file__).resolve().parent;G=D.parent;H=G.parent;O=D/'speaker-pilot-fix';O.mkdir(exist_ok=True)
sys.path.insert(0,str(G));import precision_mesh as pm
class C:pass
c=C();c.tm=tm;c.np=np;c.mf=mf
src=G/'speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl';native=H/'curved-head/community-curved-head-world.stl';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=pm.load(c,src);origin=np.array([-16,17,133.45]);radius=1.05;depth=3.29
# Reuse original 48-sided diameter/orientation: extends same pilot, no lateral redesign.
source_mesh=tm.load(src,force='mesh');vv=np.asarray(source_mesh.vertices);rad=np.linalg.norm(vv[:,:2]-origin[:2],axis=1)
ring=vv[(abs(vv[:,2]-origin[2])<1e-4)&(rad>1.04)&(rad<1.06),:2]
ring=np.unique(ring,axis=0);ring=ring[np.argsort(np.arctan2(ring[:,1]-origin[1],ring[:,0]-origin[0]))]
assert len(ring)==48,len(ring)
section=mf.CrossSection([ring]);cut=section.extrude(depth+.01).translate([0,0,origin[2]-.01]);removed=a^cut;b=a-cut
assert a.status()==mf.Error.NoError and b.status()==mf.Error.NoError
assert removed.volume()>0;assert len(b.decompose())==1
new=O/'cap-speaker-pilot-fixed-world.stl'
q=b.to_mesh64()
for proc in (False,True):
 mm=tm.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=proc)
 print('topology',proc,len(mm.vertices),len(mm.faces),mm.is_watertight,mm.is_winding_consistent,float(mm.area_faces.min()),flush=True)
io=pm.export(c,b,new);reread=pm.load(c,new)
added=max(0,(reread-a).volume());missing=max(0,(cut^reread).volume());assert added<1e-7 and missing<1e-7
# Exact source outer-roof triangles clipped against a circumscribed disk footprint.
# Piecewise-linear roof z extrema occur on clipped polygon vertices. Wider patch
# also supplies a conservative gradient bound for an oblique thickness estimate.
m=tm.load(native,force='mesh');n=128
roof=[]
for patchr in (radius, radius+2):
 rr=patchr/math.cos(math.pi/n);disk=Polygon([(-16+rr*math.cos(2*math.pi*i/n),17+rr*math.sin(2*math.pi*i/n))for i in range(n)])
 vals=[];slopes=[]
 for tri,normal in zip(m.triangles,m.face_normals):
  if normal[2]<=.05 or tri[:,2].max()<135:continue
  if tri[:,0].max() < -16-rr or tri[:,0].min()>-16+rr or tri[:,1].max()<17-rr or tri[:,1].min()>17+rr:continue
  p=Polygon(tri[:,:2]);q=p.intersection(disk)
  if q.is_empty or not hasattr(q,'exterior'):continue
  plane=np.linalg.solve(np.column_stack([tri[:,:2],np.ones(3)]),tri[:,2]);coords=list(q.exterior.coords);vals += [float(plane@[x,y,1])for x,y in coords];slopes.append(float(np.linalg.norm(plane[:2])))
 assert vals
 roof.append({'footprintRadiusMm':patchr,'minOuterRoofZMm':min(vals),'maxGradient':max(slopes),'verticalRemainingMm':min(vals)-(origin[2]+depth)})
assert roof[0]['verticalRemainingMm']>.6
# Physical Euclidean clearance to outer surface lower-bounded via wider domain:
# vertical gap/(sqrt(1+L^2)), provided closest boundary cannot lie outside patch.
thickness=roof[0]['verticalRemainingMm']/math.sqrt(1+roof[1]['maxGradient']**2)
# Independent required full bore portion, excludes shared closed blind end.
req=section.extrude(2.99-.02).translate([0,0,origin[2]+.01]);oldv=max(0,(req^a).volume());newv=max(0,(req^reread).volume());assert oldv>1e-4 and newv<1e-7
report={'passed':True,'source':str(src),'sourceSha256':sha(src),'nativeRoofSha256':sha(native),'output':str(new),'outputSha256':sha(new),'originWorldMm':origin.tolist(),'axisWorld':[0,0,1],'diameterMm':radius*2,'facets':48,'depthMm':depth,'requiredEngagementMm':2.99,'tipAllowanceMm':.3,'closedBlindEndZMm':136.74,'removedVolumeMm3':float(removed.volume()),'addedVolumeMm3':added,'requiredFullCrossSectionOldIntersectionMm3':oldv,'requiredFullCrossSectionNewIntersectionMm3':newv,'fullCutNewIntersectionMm3':missing,'sourceSubsetProof':added<1e-7,'closedBodies':len(reread.decompose()),'stlRoundTrip':io,'outerRoof':roof,'localRemainingEuclideanLowerBoundMm':thickness,'thicknessMethod':'Exact original outer-roof triangles intersected in XY with circumscribed128gon. Affine roof min over footprint; bound converted with max roof gradient over2mm wider neighborhood. No outer surface is cut; cut is strictly below its footprint minimum.','inheritedRigidCollisionScope':'Strict subset of previous cap: no new interference for the same rigid trajectory/obstacles. This does not assert strength, physical tolerance, or full-head FFC fit.'}
(O/'pilot-fix-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
