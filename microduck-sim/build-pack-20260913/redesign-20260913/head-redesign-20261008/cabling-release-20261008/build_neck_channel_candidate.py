from check_routes import *
import ast
for node in ast.parse((H/'usb-access/full-harness/build_harness.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['arc','rounded']:exec(compile(ast.Module(body=[node],type_ignores=[]),'<arc>','exec'))
for k,f in [('head_cap','cap-audio-rotation-candidate-world.stl'),('amplifier','amplifier-audio-rotation-candidate-world.stl'),('curved_cap_hardware','hardware-audio-rotation-candidate-world.stl'),('speaker_keeper','speaker-keeper-wire-relief-candidate-world.stl')]:obs[k]=man(load(D/f))
wp=np.array([[54.5,23.2,134],[10,23.2,134],[10,23.2,125],[-31,23.2,125.]])
pts,L=rounded(wp,4);tang=np.gradient(pts,axis=0);tang/=np.linalg.norm(tang,axis=1)[:,None];width=np.tile([0,1,0],(len(pts),1));normal=np.cross(tang,width);vertices=[]
for p,w,n in zip(pts,width,normal):vertices.extend([p-w*5.1-n*1.6,p+w*5.1-n*1.6,p+w*5.1+n*1.6,p-w*5.1+n*1.6])
faces=[[0,2,1],[0,3,2]]
for i in range(len(pts)-1):
 for j in range(4):a=4*i+j;b=4*i+(j+1)%4;faces.extend([[a,b,b+4],[a,b+4,a+4]])
n=len(vertices);faces.extend([[n-4,n-3,n-2],[n-4,n-2,n-1]]);m=trimesh.Trimesh(vertices,faces,process=True);trimesh.repair.fix_normals(m);s=man(m)
hh=check(s);bb=np.array((s^obs['head_cap']).bounding_box()).reshape(2,3)
# Local cable portal only: exact strip/cap overlap plus0.5mm clearance. Do not
# hollow arbitrary shell or resize its silhouette. Closed portal does not prove cap closure.
cut=s.minkowski_sum(mf.Manifold.cube([1,1,1],True));cap=(obs['head_cap']-cut).simplify(.00003)
tri(cap).export(D/'cap-neck-portal-candidate-world.stl');m.export(D/'neck-flat-bundle-head-receiving-world.stl')
report={'candidate':True,'bundleCapacity':'Two rows of6 Ø1.5mm conductors with1.7mm lateral pitch,10.2x3.2 receiving rectangle; route does not yet include pin fanouts or individual wire bendstrain.','centerlineLengthMm':L,'centerlineMm':pts.tolist(),'centerlineRmm':4,'innerMostLayerRadiusMm':2.4,'intersectionsBeforePortalMm3':hh,'portalRemovedMm3':float((obs['head_cap']-cap).volume()),'portalCollisionBoundsMm':bb.tolist(),'capAfterWatertight':tri(cap).is_watertight,'capAfterComponents':len(cap.decompose()),'postPortalOtherIntersectionsMm3':{k:v for k,v in hh.items() if k!='head_cap'},'remaining':['Thread loose free wire ends through closedportal whilecapdetached; rigid cap closure withalreadyinstalledloop untested.','Pin fanouts to this trunk and dynamic neck service loop stillrequired.'],'sourceHashes':hashes,'assemblyAcceptance':False};(D/'neck-channel-candidate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['sourceHashes','centerlineMm']},indent=2))
