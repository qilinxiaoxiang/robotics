"""One local receiver window; all dimensions are design bounds, not hardware measurements."""
from pathlib import Path
import os,json,hashlib,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n)
source=n['source'];mesh=n['mesh'];volume=n['volume'];load=n['loadfile'];read=n['read']
read(Path(__file__));pose=json.loads(read(D/'lowered-pose-pair-checks.json'))
old=source('head_bottom')
x0,x1,y0,y1,r,z0,z1=57.9,71.4,-35.8,-5.0,.6,108,114
cut=mf.Manifold.cube([x1-x0-2*r,y1-y0,z1-z0]).translate([x0+r,y0,z0])+mf.Manifold.cube([x1-x0,y1-y0-2*r,z1-z0]).translate([x0,y0+r,z0])
for x in [x0+r,x1-r]:
 for y in [y0+r,y1-r]:cut+=mf.Manifold.cylinder(z1-z0,r,circular_segments=48).translate([x,y,z0])
new=old-cut;removed=old^cut
out=D/'head-bottom-pi-receiver-world.stl';mesh(new).export(out);read(out)
checks=[]
for k in ['pi','zero_w_components','zero_w_gpio_solder_tails','gpio_discrete12_receiving','csi_free_straight_receiving']:
 f=D/(k+'-lowered-pose-world.stl');read(f);s=load(f)
 checks.append({'part':k,'originalIntersectionMm3':volume(s,old)[0],'newIntersectionMm3':volume(s,new)[0],'toUpperPadIntersectionMm3':volume(s,source('upper_pad'))[0]});del s;gc.collect()
# Removed floor projected down must be hidden within the fixed upper lip pad, not a new exposed outer contour.
pad=source('upper_pad');bounds=np.array(removed.bounding_box()).reshape(2,3)
# Sampling rays gives coverage and floor thickness independently of simplification of the source meshes.
om=mesh(old);pm=mesh(pad);samples=[]
for x in np.arange(x0+.15,x1,.5):
 for y in np.arange(y0+.15,y1,.5):
  orig=np.array([[x,y,100.]])
  hits,_,_=om.ray.intersects_location(orig,[[0,0,1]],multiple_hits=True);zs=sorted(hits[:,2].tolist()) if len(hits) else []
  rm=any(z0-1e-6<=z<=z1+1e-6 for z in zs)
  if not rm:continue
  hits,_,_=pm.ray.intersects_location(orig,[[0,0,1]],multiple_hits=True);pz=sorted(hits[:,2].tolist()) if len(hits) else []
  samples.append({'x':float(x),'y':float(y),'sourceFloorZ':zs,'upperPadZ':pz,'padCovers':len(pz)>=2})
rpt={'accepted':False,'status':'LOCAL_RECEIVER_ONLY_NO_ASSEMBLY_RELEASE','worldTransform':pose['worldTransform'],'windowBoundsMm':[x0,y0,z0,x1,y1,z1],'cornerRadiusMm':r,'sourceVolumeMm3':old.volume(),'candidateVolumeMm3':new.volume(),'removedVolumeMm3':removed.volume(),'removedBoundsMm':list(removed.bounding_box()),'sourceBodies':len(old.decompose()),'candidateBodies':len(new.decompose()),'watertight':mesh(new).is_watertight,'primarySupportMaxXBoundMm':52.3,'minimumXSeparationToPrimarySupportMm':x0-52.3,'partChecks':checks,'undersideCoverageSampleCount':len(samples),'uncoveredSamples':[s for s in samples if not s['padCovers']],'coverageCriterion':'0.5mm XY sampling of removed floor must project into upper_pad. This is a geometric visibility/coverage test, not structural certification.','remainingAcceptance':['Exact all-obstacle pair checks including new camera/Pi support','Load/print material physical validation','Full joint domain, insertion sequence and 200mm cable routing'],'sourceHashes':n['hashes']}
(D/'bottom-pi-receiver-report.json').write_text(json.dumps(rpt,indent=2)+'\n');print(json.dumps({k:v for k,v in rpt.items() if k not in ['sourceHashes','uncoveredSamples']},indent=2));print('uncovered',len(rpt['uncoveredSamples']))
