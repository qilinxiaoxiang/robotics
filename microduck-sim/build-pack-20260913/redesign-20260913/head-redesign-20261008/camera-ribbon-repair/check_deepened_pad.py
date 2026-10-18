from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n)
np=n['np'];mf=n['mf'];read=n['read'];load=n['loadfile'];mesh=n['mesh'];vol=n['volume'];read(Path(__file__))
pad=n['source']('upper_pad');pm=mesh(pad);records=[]
x0,x1,y0,y1,z0,z1,r=57.9,71.4,-37.8,-7,108,110,.6
cut=mf.Manifold.cube([x1-x0-2*r,y1-y0,z1-z0]).translate([x0+r,y0,z0])+mf.Manifold.cube([x1-x0,y1-y0-2*r,z1-z0]).translate([x0,y0+r,z0])
for x in [x0+r,x1-r]:
 for y in [y0+r,y1-r]:cut+=mf.Manifold.cylinder(z1-z0,r,circular_segments=48).translate([x,y,z0])
new=pad-cut;removed=pad^cut
for key in ['pi','zero_w_components','zero_w_gpio_solder_tails','gpio_discrete12_receiving','csi_free_straight_receiving']:
 f=D/(key+'-lowered-pose-world.stl');read(f);s=load(f).translate([0,-2,-2]);v,bb=vol(s,pad);vnew,bbnew=vol(s,new)
 records.append({'part':key,'sourceIntersectionMm3':v,'sourceIntersectionBoundsMm':bb,'pocketIntersectionMm3':vnew,'boundsMm':list(s.bounding_box())});del s;gc.collect()
samples=[];uncovered=[]
for x in np.arange(x0+.1,x1,.25):
 for y in np.arange(y0+.1,y1,.25):
  ray=np.array([[x,y,100.]]);hits,_,_=pm.ray.intersects_location(ray,[[0,0,1]],multiple_hits=True);zs=sorted(hits[:,2].tolist())
  if len(zs)>=2 and zs[-1]>z0:
   rem=z0-zs[0];samples.append(rem)
   if rem<1.2:uncovered.append({'x':float(x),'y':float(y),'remainingMm':rem,'sourceZ':zs})
out=D/'upper-pad-deepened-pocket-diagnostic-world.stl';mesh(new).export(out);read(out)
report={'accepted':False,'diagnosticOnly':True,'pocketBoundsMm':[x0,y0,z0,x1,y1,z1],'partChecks':records,'removedVolumeMm3':removed.volume(),'remainingBodies':len(new.decompose()),'watertight':bool(mesh(new).is_watertight),'sampleSpacingMm':.25,'thicknessSampleCount':len(samples),'minimumRemainingVerticalThicknessMm':min(samples) if samples else None,'under1p2mmSamples':uncovered,'exteriorRule':'Hidden upper-surface pocket only. At least 1.2mm sampled underside material required; sampling is not a global analytic wall-thickness proof. Full exterior comparison and strength not accepted.','sourceHashes':n['hashes']}
(D/'deepened-upper-pad-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['sourceHashes','under1p2mmSamples']},indent=2));print('thin samples',len(uncovered))
