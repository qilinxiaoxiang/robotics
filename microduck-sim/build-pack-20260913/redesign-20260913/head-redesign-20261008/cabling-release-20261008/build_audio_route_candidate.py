"""Bounded internal amp90deg+0.8Y proposal, new roof pillars, speaker pair.
No canonical updates. Receiver hypotheses explicitly retain manufacturing hold.
"""
from check_routes import *
import ast
src=(H/'usb-access/full-harness/build_harness.py').read_text();tree=ast.parse(src)
for node in tree.body:
 if isinstance(node,ast.FunctionDef) and node.name in ['arc','rounded']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<source rounded circular arc>','exec'))
cap=obs['head_cap'];native=man(load(H/'curved-head/community-curved-head-world.stl'));oldholes=np.array([[26.6500006104,-17.287000885,133.5849994],[39.3500006104,-17.287000885,133.5849994]])
oldcolumns=mf.Manifold.batch_boolean([mf.Manifold.cylinder(28,2.01,circular_segments=64).translate(p) for p in oldholes],mf.OpType.Add)
base=cap-(oldcolumns-native)
T=trimesh.transformations.rotation_matrix(np.pi/2,[0,0,1],[33,-24,138]);T[1,3]+=.8
amp=man(meshes['amplifier'].copy().apply_transform(T));newholes=trimesh.transform_points(oldholes,T);native_mesh=tri(native);posts=[]
for p in newholes:
 loc,_,_=native_mesh.ray.intersects_location([p],[[0,0,1]],multiple_hits=True);top=float(loc[:,2].min()+.5)
 raw=mf.Manifold.cylinder(top-p[2],2,circular_segments=64).translate(p)
 # Restrict new column to points vertically below the original cap's exact surface.
 near=native ^ mf.Manifold.cube([4.02,4.02,60],True).translate([p[0],p[1],140]);col=mf.Manifold.batch_boolean([near.translate([0,0,-z]) for z in np.arange(0,31,.5)],mf.OpType.Add)
 post=(raw^col)-mf.Manifold.cylinder(7.2,1.05,circular_segments=64).translate(p-[0,0,.1]);posts.append(post)
newcap=(base+mf.Manifold.batch_boolean(posts,mf.OpType.Add)).simplify(.00003)
# Remove only the two old amp screws by their documented small bounding boxes;
# regenerate at relocated mounting axes. Other six screws/four nuts untouched.
hardware=obs['curved_cap_hardware'];oldsc=mf.Manifold.batch_boolean([mf.Manifold.cube([5,5,12],True).translate(p+[0,0,1]) for p in oldholes],mf.OpType.Add)
newhardware=hardware-oldsc
for p in newholes:
 shaft=mf.Manifold.cylinder(8,1.25,circular_segments=48).translate(p-[0,0,1.57]);head=mf.Manifold.cylinder(1.7,2.5,circular_segments=48).translate(p-[0,0,3.27]);newhardware+=shaft+head
# Current amp mounting has no source-surface alteration beyond the roof pillars.
obs['head_cap']=newcap;obs['amplifier']=amp;obs['curved_cap_hardware']=newhardware
keeper=obs['speaker_keeper']
for x in [-7.77,1.77]:keeper-=mf.Manifold.cylinder(4,1.5,circular_segments=64).translate([x,.94,131.5])
obs['speaker_keeper']=keeper;tri(keeper).export(D/'speaker-keeper-wire-relief-candidate-world.stl')
paths=[];solids=[]
for i,x in enumerate([-7.77,1.77]):
 p=np.array([x,.94,132.35]);end=np.array([23.203,-21.5-i*3.5,138.5]);rear=-12.+i*2.5;y=-4.5-i*1.5
 wp=np.array([p,p+[0,0,2.5],[x,y,134.85],[rear,y,134.85],[rear,-18-i*1.5,135.5-i*1.8],[13+i*2.5,end[1],138.5],end])
 try:pts,L=rounded(wp,2.)
 except ValueError as e:raise
 s=tube(pts,.75);solids.append(s)
 # Intended pad + terminal mating volumes only, never discard whole endpoint parts.
 padbox=mf.Manifold.cube([2.4,2.4,1.6],True).translate(p)
 term=mf.Manifold.cube([1.8,1.8,1.8],True).translate(end)
 hh={}
 for k,o in obs.items():
  if k=='speaker':o-=padbox
  if k=='amplifier':o-=term
  v=hits(s,o)
  if v>1e-5:hh[k]=v
 paths.append({'id':f'speaker-{i}','waypointsMm':wp.tolist(),'analyticLengthMm':L,'tubeDiameterMm':1.5,'bendRadiusMm':2,'intersectionsMm3':hh,'centerlineMm':pts.tolist()})
 tri(s).export(D/f'speaker-wire-{i}-candidate-world.stl')
static=check(amp,['amplifier','curved_cap_hardware']);print('AMP',static)
# Check new mounting columns and hardware against every real body, allowing only
# its matched cap and amp pilot/clearance interface for fasteners.
posthits=check(mf.Manifold.batch_boolean(posts,mf.OpType.Add),['head_cap']);hardwarehits=check(newhardware,['head_cap','amplifier','curved_cap_hardware','openrb','speaker_cradle','speaker_keeper'])
for k,s in [('cap-audio-rotation-candidate',newcap),('amplifier-audio-rotation-candidate',amp),('hardware-audio-rotation-candidate',newhardware)]:tri(s).export(D/(k+'-world.stl'))
report={'status':'UNPUBLISHED_INTERNAL_AUDIO_CANDIDATE','ampTransformFromCurrentWorld':T.tolist(),'newAmpHoleBottomMm':newholes.tolist(),'ampStaticIntersectionsMm3':static,'newPostIntersectionsMm3':posthits,'hardwareExternalIntersectionsMm3':hardwarehits,'speakerWires':paths,'wirePairIntersectionMm3':hits(*solids),'keeperWatertight':tri(keeper).is_watertight,'keeperBodies':len(keeper.decompose()),'keeperRemovedVolumeMm3':float((man(meshes['speaker_keeper'])-keeper).volume()),'capWatertight':tri(newcap).is_watertight,'capComponents':len(newcap.decompose()),'sourceHashes':hashes,'assemblyAcceptance':False,'assumptions':['Cable OD1.5mm and static R2 are receiving parameters, not exact purchased wire specifications.','Speaker pad XY centers from dimension-scaled manufacturer diagram, not separately dimensioned; +/-0.5mm to be tested.','Terminal exit direction from official Eagle package; height138.5mm and1.8mm mating aperture are receiving assumptions.']}
(D/'audio-route-candidate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['speakerWires','sourceHashes']},indent=2));print([(a['id'],a['intersectionsMm3']) for a in paths])
