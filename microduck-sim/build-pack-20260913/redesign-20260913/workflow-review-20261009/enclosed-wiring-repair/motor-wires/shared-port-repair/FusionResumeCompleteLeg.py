"""Run through Fusion Python.Run. New complete RIGHT leg review document.
No active-document mutation. Native line/arc and explicitly checked analytic-fit
sweeps; source printed meshes remain references, never faceted BRep substitutes.
"""
import adsk.core,adsk.fusion,json,hashlib,traceback,math,datetime
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires/shared-port-repair');M=D.parent
SIDE='right'
report={'resumeMode':'preserve nine successful wires; analytic C1 hip only','status':'RUNNING','side':SIDE,'nativeWires':[],'nativeMotors':[],'meshReferences':[],'wholeHarnessAccepted':False}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def point(v):return adsk.core.Point3D.create(*[x/10 for x in v])
def xyz(p):return[p.x*10,p.y*10,p.z*10]
def norm(v):return math.sqrt(sum(x*x for x in v))
def dist(a,b):return norm([x-y for x,y in zip(a,b)])
def collection(items):
 c=adsk.core.ObjectCollection.create()
 for x in items:c.add(x)
 return c
def matrix(T):
 a=[x for r in T for x in r]
 for i in[3,7,11]:a[i]/=10
 m=adsk.core.Matrix3D.create();assert m.setWithArray(a);return m
def endpoint(c,p):
 x=min([c.startSketchPoint,c.endSketchPoint],key=lambda s:s.worldGeometry.distanceTo(point(p)));assert x.worldGeometry.distanceTo(point(p))*10<1e-5;return x
def poly_distance(p,pts):
 best=1e99
 for a,b in zip(pts,pts[1:]):
  v=[y-x for x,y in zip(a,b)];s=sum(x*x for x in v);t=max(0,min(1,sum((x-y)*z for x,y,z in zip(p,a,v))/s))if s else 0;best=min(best,dist(p,[a[i]+t*v[i]for i in range(3)]))
 return best
def transform_point(v,T):return[sum(T[i][j]*v[j]for j in range(3))+T[i][3]for i in range(3)]
def helix(p,a):
 L=p['sweepRadians'];d=p['pitchRampRadians'];u=a-(L-d)
 I=a/2-d/(2*math.pi)*math.sin(math.pi*a/d)if a<d else a-d/2 if a<=L-d else L-1.5*d+u/2+d/(2*math.pi)*math.sin(math.pi*u/d)
 return[p['centerXY'][0]+p['radiusMm']*math.cos(a),p['centerXY'][1]-p['radiusMm']*math.sin(a),p['startZMm']-p['pitchMm']/(2*math.pi)*I]
def bezier(p,t):return[sum([((1-t)**3)*p[0][i],3*(1-t)**2*t*p[1][i],3*(1-t)*t*t*p[2][i],t**3*p[3][i]])for i in range(3)]
def stroke(c):
 ev=c.worldGeometry.evaluator;ok,a,b=ev.getParameterExtents();assert ok;ok,points=ev.getStrokes(a,b,.00005);assert ok;return[xyz(p)for p in points]
def native_body_count(comp):
 total=sum(1 for i in range(comp.bRepBodies.count)if comp.bRepBodies.item(i).isSolid)
 for i in range(comp.occurrences.count):total+=native_body_count(comp.occurrences.item(i).component)
 return total

def helix_derivative(p,a):
 L=p['sweepRadians'];d=p['pitchRampRadians']
 f=.5-.5*math.cos(math.pi*a/d) if a<d else 1 if a<=L-d else .5+.5*math.cos(math.pi*(a-(L-d))/d)
 return[-p['radiusMm']*math.sin(a),-p['radiusMm']*math.cos(a),-p['pitchMm']/(2*math.pi)*f]
def cubic_chunks(p):
 if p['kind']=='cubic-bezier':return [(p['controlPoints'],None)]
 L=p['sweepRadians'];d=p['pitchRampRadians'];nodes=sorted(set([L*i/math.ceil(L/.2) for i in range(math.ceil(L/.2)+1)]+[d,L-d]));out=[]
 for a,b in zip(nodes,nodes[1:]):
  u=helix(p,a);v=helix(p,b);du=helix_derivative(p,a);dv=helix_derivative(p,b);h=(b-a)/3
  cp=[u,[u[i]+h*du[i] for i in range(3)],[v[i]-h*dv[i] for i in range(3)],v]
  error=max(dist(bezier(cp,j/20),helix(p,a+(b-a)*j/20)) for j in range(21));assert error<.002
  out.append((cp,{'angleInterval':[a,b],'analyticParameterSampleErrorMm':error}))
 return out
def native_tangent(q,p,startPoint):
 ev=q.worldGeometry.evaluator;ok,a,b=ev.getParameterExtents();assert ok
 ok,pa=ev.getPointAtParameter(a);ok,pb=ev.getPointAtParameter(b);t=a if dist(xyz(pa),p)<dist(xyz(pb),p) else b
 ok,v=ev.getFirstDerivative(t);assert ok
 x=[v.x,v.y,v.z]
 if dist(xyz(pa),startPoint)>dist(xyz(pb),startPoint):x=[-z for z in x]
 return [z/norm(x) for z in x]
def joins(curves,spec):
 rows=[]
 for i in range(len(curves)-1):
  a,b=spec[i][:2];u,v=spec[i+1][:2];x=native_tangent(curves[i],b,a);y=native_tangent(curves[i+1],u,u)
  angle=math.degrees(math.acos(max(-1,min(1,sum(x[k]*y[k]for k in range(3))))));rows.append({'join':i,'angleDegrees':angle})
 return rows
def run(context):
 manifest=json.loads((D/'eight-leg-manifest.json').read_text());report['manifestSha256']=sha(D/'eight-leg-manifest.json')
 for f,h in manifest['sourceHashes'].items():assert sha(f)==h,('stale input',f)
 assert sha(manifest['centerlineInput'])==manifest['centerlineSha256'];paths=json.loads(Path(manifest['centerlineInput']).read_text())['paths'];ids={r['id']for r in manifest['routes']if (int(r['id'].split('-')[1])<=5)==(SIDE=='right')};paths=[p for p in paths if p['routeId']in ids];assert len(paths)==12
 app=adsk.core.Application.get();matches=[d for d in app.documents if 'COMPLETE RIGHT LEG' in d.name];assert len(matches)==1, 'Expected one exact existing right-leg document';doc=matches[0];doc.activate();design=adsk.fusion.Design.cast(app.activeProduct);assert design;root=design.rootComponent;design.activateRootComponent()
 previous=json.loads((D/'fusion-complete-leg-readback.json').read_text());assert len(previous['nativeWires'])==9
 report['nativeWires']=previous['nativeWires'];report['previousReceiptSha256']=sha(D/'fusion-complete-leg-readback.json');report['preservedNativeWires']=[]
 for r in previous['nativeWires']:
  matches=[o for o in root.occurrences if o.component.name==r['key']];assert len(matches)==1;assert matches[0].component.bRepBodies.count==1;v=matches[0].component.bRepBodies.item(0).volume*1000;assert abs(v-r['volumeMm3'])<1e-7;report['preservedNativeWires'].append({'key':r['key'],'volumeMm3':v})
 paths=[p for p in paths if p['routeId']=='ttl-05-04'];assert len(paths)==3
 for o in list(root.occurrences):
  if o.component.name in {p['key'] for p in paths}:
   assert o.component.bRepBodies.count==0
   sk=o.component.sketches.item(0);qs=[];sp=[]
   for p in next(r for r in paths if r['key']==o.component.name)['orderedPrimitives']:
    matches=[q for q in sk.sketchCurves if q.attributes.itemByName('MicroDuck','sourcePrimitive') and json.loads(q.attributes.itemByName('MicroDuck','sourcePrimitive').value)==p];assert len(matches)==1;q=matches[0];a=p.get('start');b=p.get('end')
    if p['kind']=='smooth-pitch-helix':a=helix(p,0);b=helix(p,p['sweepRadians'])
    if p['kind']=='cubic-bezier':a=p['controlPoints'][0];b=p['controlPoints'][-1]
    qs.append(q);sp.append((a,b))
   report['failedFittedCurveJoinReadback']=joins(qs,sp);(D/'fusion-complete-leg-resume-readback.json').write_text(json.dumps(report,indent=2));assert o.deleteMe()
 def comp(name,T=None):
  o=root.occurrences.addNewComponent(matrix(T)if T else adsk.core.Matrix3D.create());o.component.name=name;return o
 # Build wires first: failures never silently replace a native sweep by a mesh.
 for row in paths:
  o=comp(row['key']);c=o.component;sk=c.sketches.add(c.xYConstructionPlane);sk.name='EDITABLE 3D 180mm cable';curves=[];spec=[];prev=None;fitReports=[];T=row.get('canonicalToWorld',[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
  for primitiveIndex,p in enumerate(row['orderedPrimitives']):
   kind=p['kind']
   if kind in ['line','arc']:
    a=transform_point(p['start'],T);b=transform_point(p['end'],T);start=prev if prev else point(a)
    q=sk.sketchCurves.sketchLines.addByTwoPoints(start,point(b)) if kind=='line' else sk.sketchCurves.sketchArcs.addByThreePoints(start,point(transform_point(p['mid'],T)),point(b))
    assert q;q.attributes.add('MicroDuck','sourcePrimitive',json.dumps(p));curves.append(q);spec.append((a,b,p.get('lengthMm',dist(a,b)),kind));prev=endpoint(q,b)
   else:
    for cp,fit in cubic_chunks(p):
     world=[transform_point(x,T) for x in cp];items=[point(x) for x in world]
     if prev:items[0]=prev
     q=sk.sketchCurves.sketchControlPointSplines.add(items,adsk.fusion.SplineDegrees.SplineDegreeThree);assert q
     q.attributes.add('MicroDuck','sourcePrimitive',json.dumps({'originalIndex':primitiveIndex,'cubicControlsWorldMm':world,'analyticSource':p}))
     native=stroke(q);ref=[bezier(world,i/200) for i in range(201)];err=max(poly_distance(x,ref) for x in native);assert err+.0005<.003
     fitReports.append({'kind':kind,'controlPoints':4,'maximumNativeDeviationMm':err,'sourceApproximation':fit,'strokeSagittaMm':.0005})
     curves.append(q);spec.append((world[0],world[-1],None,kind));prev=endpoint(q,world[-1])
  for i,(a,b)in enumerate(zip(curves,curves[1:])):
   x=endpoint(a,spec[i][1]);y=endpoint(b,spec[i+1][0]);
   if x!=y:assert x.merge(y)
  design.computeAll();length=0
  for q,(a,b,expected,kind)in zip(curves,spec):
   endpoint(q,a);endpoint(q,b);length+=q.length*10
   if expected is not None:assert abs(q.length*10-expected)<1e-4
  assert abs(length-180)<.01,(row['key'],length)
  tangentRows=joins(curves,spec);assert max(x['angleDegrees']for x in tangentRows)<.001,('not C1',tangentRows)
  path=c.features.createPath(collection(curves),False);assert path and path.count==len(curves);assert c.features.createPath(curves[0],True).count==len(curves)
  pi=c.constructionPlanes.createInput();assert pi.setByDistanceOnPath(path,adsk.core.ValueInput.createByReal(0));pl=c.constructionPlanes.add(pi);profile=c.sketches.add(pl);profile.sketchCurves.sketchCircles.addByCenterRadius(profile.modelToSketchSpace(point(spec[0][0])),.075)
  inp=c.features.sweepFeatures.createInput(profile.profiles.item(0),path,adsk.fusion.FeatureOperations.NewBodyFeatureOperation);inp.orientation=adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType;f=c.features.sweepFeatures.add(inp);assert f and f.bodies.count==1 and f.bodies.item(0).isSolid
  profile.isVisible=False;pl.isLightBulbOn=False;sk.isVisible=False;report['nativeWires'].append({'key':row['key'],'pathEntities':path.count,'lengthMm':length,'volumeMm3':f.bodies.item(0).volume*1000,'fittedAnalyticReadback':fitReports,'maximumJoinAngleDegrees':max(x['angleDegrees']for x in tangentRows)});(D/'fusion-complete-leg-resume-readback.json').write_text(json.dumps(report,indent=2))
 top=json.loads((M/'active-topology.json').read_text());manufacturer=M.parents[1]/'leg-ports/xl330-registered-motor-local.step';motors=range(1,6)if SIDE=='right'else range(6,11)
 for mid in motors:
  p=top['ports'][f'motor-{mid}-socket-13'];o=comp(f'XL330 native ID{mid}',p['transform']);assert app.importManager.importToTarget(app.importManager.createSTEPImportOptions(str(manufacturer)),o.component);n=native_body_count(o.component);assert n==12,(mid,n);report['nativeMotors'].append({'id':mid,'recursiveSolidCount':n,'sourceSha256':sha(manufacturer)})
 for r in manifest['routes']:
  if r['id']not in ids:continue
  for pk in[r['fromPort'],r['toPort']]:
   p=top['ports'][pk];o=comp(pk+' complete receiving housing',p['transform']);c=o.component;lo,hi=p['housingLocalBounds'];ci=c.constructionPlanes.createInput();assert ci.setByOffset(c.xYConstructionPlane,adsk.core.ValueInput.createByReal(lo[2]/10));plane=c.constructionPlanes.add(ci);s=c.sketches.add(plane);s.sketchCurves.sketchLines.addTwoPointRectangle(point([lo[0],lo[1],0]),point([hi[0],hi[1],0]));ext=c.features.extrudeFeatures.addSimple(s.profiles.item(0),adsk.core.ValueInput.createByReal((hi[2]-lo[2])/10),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);assert ext.bodies.count==1;s.isVisible=False;plane.isLightBulbOn=False
   axis=root.sketches.add(root.xYConstructionPlane);axis.name=pk+' registered insertion axis';line=axis.sketchCurves.sketchLines.addByTwoPoints(point(p['mouth']),point([p['mouth'][i]+8*p['outward'][i]for i in range(3)]));line.isConstruction=True;axis.isVisible=False
 # Complete original leg plus neighbouring fixed objects that were near any route.
 G=M.parents[2]/'leg-guide-20261006/full-build-data.json';data=json.loads(G.read_text());module=next(m for m in data['modules']if m['id']==SIDE+'-leg');keys=set(module['partKeys']);del data
 inv=json.loads((D/'complete-interface-inventory.json').read_text());fixed={x['key']:x for x in inv['fixedOriginalObstacleInventory']};v=json.loads((D/f'valid-{SIDE}.json').read_text());keys|={x['obstacle'].split('-solid')[0]for x in v['checks']};hip=json.loads((M/'hip-valid-source-static.json').read_text());keys|={x['obstacle'].split('-solid')[0]for rr in hip['routes']if rr['side']==SIDE for x in rr['checked']}
 refs=[fixed[k]for k in sorted(keys)if k in fixed and not(k.startswith('motor')and k[5:].isdigit())]
 refs+=[dict(p,importTranslationMm=[0,0,0])for p in inv['existingAdjustableTieReceivingBodies']if p['key'].startswith(SIDE)]
 for p in refs:
  assert sha(p['file'])==p['sha256'];t=p.get('importTranslationMm',[0,0,0]);T=[[1,0,0,t[0]],[0,1,0,t[1]],[0,0,1,t[2]],[0,0,0,1]];o=comp('SOURCE REFERENCE '+p['key'],T);base=o.component.features.baseFeatures.add();base.startEdit()
  try:bs=o.component.meshBodies.add(p['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base)
  finally:base.finishEdit()
  vertices=[]
  for i in range(bs.count):
   b=bs.item(i);b.name=p['key'];mesh=b.displayMesh;assert mesh
   for q in mesh.nodeCoordinates:
    q=q.copy();q.transformBy(matrix(T));vertices.append(xyz(q))
  assert vertices;bounds=[[min(v[i]for v in vertices)for i in range(3)],[max(v[i]for v in vertices)for i in range(3)]];expected=p.get('expectedFinalBoundsMm');err=max(abs(bounds[i][j]-expected[i][j])for i in range(2)for j in range(3))if expected else None
  if err is not None:assert err<1e-4,(p['key'],err)
  o.component.opacity=.35;report['meshReferences'].append({'key':p['key'],'sourceSha256':p['sha256'],'nodeBoundsMm':bounds,'boundsErrorMm':err,'nativeBRepCertified':False,'sourceBoundMeshStaticCovered':True})
 design.computeAll();out=D/f'Fusion-complete-{SIDE}-leg-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(out)));report.update(status='NATIVE_FULL_LEG_CREATED_REVIEW_REQUIRED',output=str(out),outputSha256=sha(out),wholeHarnessAccepted=False,remaining=['Native UI/readback and local assembly review','Physical stock fit, soft slack and powered operation are not certified']);app.activeViewport.fit()
try:run(None)
except Exception:report.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
finally:(D/'fusion-complete-leg-resume-readback.json').write_text(json.dumps(report,indent=2))
