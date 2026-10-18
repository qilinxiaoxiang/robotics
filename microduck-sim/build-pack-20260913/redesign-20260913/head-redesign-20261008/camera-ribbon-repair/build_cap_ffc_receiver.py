"""Local internal FFC receiver groove; retain exact exterior and bound remaining skin."""
from pathlib import Path
import os,json,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n);read=n['read'];load=n['loadfile'];mesh=n['mesh'];read(Path(__file__))
cf=H/'usb-access/usb-repair/head-cap-usb-service-world.stl';read(cf);old=load(cf);rf=D/'sc1892-developable-U-receiving-world.stl';read(rf);ribbon=load(rf)
local=ribbon^mf.Manifold.cube([9,10,7]).translate([51,-40,129]);cut=local.minkowski_sum(mf.Manifold.cube([.6,.6,.6],True));new=old-cut
out=D/'head-cap-usb-ffc-receiver-world.stl';mesh(new).export(out);read(out)
# The contact region is the negative-Y wall. Select all negative-Y outer-facing
# triangles across the whole native cap, not just the most favorable local patch.
cm=mesh(old);mask=(cm.face_normals[:,1]<-.05)&(cm.triangles_center[:,1]<-20);outer=cm.submesh([np.where(mask)[0]],append=True)
km=mesh(cut);v,f=trimesh.remesh.subdivide_to_size(km.vertices,km.faces,max_edge=.25,max_iter=8);closest,dist,tri=trimesh.proximity.closest_point(outer,v);imin=int(np.argmin(dist));bound=float(dist.min())-.25
raw,bb=n['volume'](ribbon,old);now,nbb=n['volume'](ribbon,new)
r={'accepted':False,'status':'LOCAL_INTERNAL_FFC_GROOVE_ONLY','ribbonBeforeMm3':raw,'ribbonAfterMm3':now,'receivingClearanceCubeHalfSideMm':.3,'removedVolumeMm3':max(0,(old-new).volume()),'removedBoundsMm':list((old-new).bounding_box()),'candidateBodies':len(new.decompose()),'watertight':mesh(new).is_watertight,'sampledDistanceToNegativeYOuterFacesMm':float(dist.min()),'surfaceSamplingMaxEdgeMm':.25,'remainingSkinLowerBoundMm':bound,'minimumSkinCriterionMm':1.2,'skinBoundPass':bound>=1.2,'sampleCount':len(v),'worstCutPointMm':v[imin].tolist(),'worstOuterPointMm':closest[imin].tolist(),'outerClassification':'Native negative-Y wall external triangles have outward negative-Y normals. Includes all old-cap triangles Y<-20 and normalY<-.05, including internal features if similarly oriented (conservative). Bound subtracts maximum sampled cutter triangle edge length; no strength certification.','sourceHashes':n['hashes'],'remaining':['Wholecap closure with fullFFC','Revised audio posts merged by owner','Ribbon retention, physicalbend/stiffener/latch bounds','Source-pair and robot articulation gates']}
(D/'cap-ffc-receiver-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='sourceHashes'},indent=2))
