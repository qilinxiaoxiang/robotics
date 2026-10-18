from check_routes import *
cap=man(load(D/'cap-neck-portal-candidate-world.stl'));cable=man(load(D/'neck-flat-bundle-head-receiving-world.stl'));collisions=[]
for z in np.arange(40,-.001,-.25):
 v=hits(cap.translate([0,0,z]),cable)
 if v>1e-5:collisions.append({'offsetZmm':float(z),'volumeMm3':v})
# One bounded correction to this exact portal: open its lower edge along the
# demonstrated closure interference. Preserve every other surface.
rearRegion=mf.Manifold.cube([32,13,55],True).translate([-24,23.2,105]);sweeps=[cable.translate([0,0,-z]) for z in np.arange(40,-.001,-.25)];cut=mf.Manifold.batch_boolean(sweeps,mf.OpType.Add).minkowski_sum(mf.Manifold.cube([1,1,1],True))^rearRegion
candidate=(cap-cut).simplify(.00003);tri(candidate).export(D/'cap-neck-slot-closure-candidate-world.stl');bad=[]
for z in np.arange(40,-.001,-.25):
 v=hits(candidate.translate([0,0,z]),cable)
 if v>1e-5:bad.append({'offsetZmm':float(z),'volumeMm3':v})
out={'closedPortalNegativeControl':{'collisionPoseCount':len(collisions),'peakMm3':max((p['volumeMm3'] for p in collisions),default=0)},'lowerEdgeSlotCorrection':{'extraRemovalMm3':float((cap^cut).volume()),'removedBoundsMm':np.array((cap^cut).bounding_box()).reshape(2,3).tolist(),'boundsMethod':'Exact finite rear-region cut before0.00003mm STL simplification; avoid mistaking numerical surface slivers elsewhere for the cut bounds.','remainingCollisionPoses':bad,'sampleCount':161,'stepMm':.25,'watertight':tri(candidate).is_watertight,'components':len(candidate.decompose())},'boundary':'Only cap-versus-fixednecktrunk crossing checked here; moving amp-to-Pi wire service loop, pin fanouts and lower-edge removable retention are still required. No external envelope enlarged.','sourceHashes':hashes,'assemblyAcceptance':False};(D/'neck-slot-closure.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='sourceHashes'},indent=2))
