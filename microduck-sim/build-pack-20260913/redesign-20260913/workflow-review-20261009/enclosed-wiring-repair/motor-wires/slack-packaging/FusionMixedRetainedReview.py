import adsk.core,adsk.fusion,json,hashlib,traceback,math,datetime
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires/slack-packaging')
report={'status':'RUNNING','nativeWires':[],'wholeHarnessAccepted':False}
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

def run(context):
 data=json.loads((D/'mixed-right.json').read_text());assert data['currentStaticClear'];report['sourceSha256']=sha(D/'mixed-right.json')
 delta=json.loads((D/'mixed-delta.json').read_text());assert delta['passed'];report['deltaSha256']=sha(D/'mixed-delta.json')
 paths=[dict(r,orderedPrimitives=r['primitives'])for r in data['rows']]
 app=adsk.core.Application.get();doc=None
 for i in range(app.documents.count):
  d=app.documents.item(i)
  if 'COMPLETE RIGHT LEG' in d.name.upper():doc=d;break
 assert doc,'Open the existing complete right leg native document';doc.activate();design=adsk.fusion.Design.cast(app.activeProduct);design.activateRootComponent();root=design.rootComponent
 keys={p['key']for p in paths};hidden=[]
 for i in range(root.occurrences.count):
  o=root.occurrences.item(i)
  if o.component.name in keys or o.component.name in {'SURFACE FOLD '+k for k in keys}:o.isLightBulbOn=False;hidden.append(o.component.name)
 report['hiddenBaselineWireComponents']=hidden
 def comp(name,T=None):
  o=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());o.component.name='MIXED NOMINAL '+name;return o
 for row in paths:
  o=comp(row['key']);c=o.component;sk=c.sketches.add(c.xYConstructionPlane);sk.name='EDITABLE nominal cable receiving path';curves=[];spec=[];prev=None;fitReports=[];T=row.get('canonicalToWorld',[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
  for p in row['orderedPrimitives']:
   kind=p['kind']
   if kind in['line','arc']:
    a=transform_point(p['start'],T);b=transform_point(p['end'],T);start=prev if prev else point(a)
    q=sk.sketchCurves.sketchLines.addByTwoPoints(start,point(b))if kind=='line'else sk.sketchCurves.sketchArcs.addByThreePoints(start,point(transform_point(p['mid'],T)),point(b));expected=p.get('lengthMm',dist(a,b));fit=None
   else:
    if kind=='smooth-pitch-helix':
     N=math.ceil(p['sweepRadians']/.04);angles=sorted(set([p['sweepRadians']*i/N for i in range(N+1)]+[p['pitchRampRadians'],p['sweepRadians']-p['pitchRampRadians']]));pts=[transform_point(helix(p,t),T)for t in angles]
    elif kind=='cubic-bezier':pts=[transform_point(bezier(p['controlPoints'],i/80),T)for i in range(81)]
    else:raise ValueError(kind)
    a,b=pts[0],pts[-1];items=[point(x)for x in pts]
    if prev:items[0]=prev
    q=sk.sketchCurves.sketchFittedSplines.add(collection(items));assert q;fit={'kind':kind,'fitPointCount':len(pts)};native=stroke(q);errors=[]
    if kind=='smooth-pitch-helix':
     # canonical reflection is its own inverse, so evaluate actual fitted points against the analytic helix.
     for x in native:
      v=transform_point(x,T);angle=math.atan2(-(v[1]-p['centerXY'][1]),v[0]-p['centerXY'][0]);candidates=[max(0,min(p['sweepRadians'],angle+2*math.pi*j))for j in range(-1,5)];errors.append(min(dist(v,helix(p,t))for t in candidates))
    else:
     ref=[transform_point(bezier(p['controlPoints'],i/2000),T)for i in range(2001)];errors=[poly_distance(x,ref)for x in native]
    fit['maximumStrokePointDeviationMm']=max(errors);fit['strokeSagittaMm']=.0005;assert max(errors)+.0005<.003,('native analytic approximation outside receiving allowance',row['key'],fit);fitReports.append(fit);expected=None
   assert q;q.attributes.add('MicroDuck','sourcePrimitive',json.dumps(p));curves.append(q);spec.append((a,b,expected,kind));prev=endpoint(q,b)
  for i,(a,b)in enumerate(zip(curves,curves[1:])):
   x=endpoint(a,spec[i][1]);y=endpoint(b,spec[i+1][0]);
   if x!=y:assert x.merge(y)
  design.computeAll();length=0
  for q,(a,b,expected,kind)in zip(curves,spec):
   endpoint(q,a);endpoint(q,b);length+=q.length*10
   if expected is not None:assert abs(q.length*10-expected)<1e-4
  assert abs(length-row['lengthMm'])<.01,(row['key'],length)
  path=c.features.createPath(collection(curves),False);assert path and path.count==len(curves);assert abs(sum(path.item(i).entity.length*10 for i in range(path.count))-row['lengthMm'])<.01
  pi=c.constructionPlanes.createInput();assert pi.setByDistanceOnPath(path,adsk.core.ValueInput.createByReal(0));pl=c.constructionPlanes.add(pi);profile=c.sketches.add(pl);profile.sketchCurves.sketchCircles.addByCenterRadius(profile.modelToSketchSpace(point(spec[0][0])),.075)
  inp=c.features.sweepFeatures.createInput(profile.profiles.item(0),path,adsk.fusion.FeatureOperations.NewBodyFeatureOperation);inp.orientation=adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType;f=c.features.sweepFeatures.add(inp);assert f and f.bodies.count==1 and f.bodies.item(0).isSolid
  profile.isVisible=False;pl.isLightBulbOn=False;sk.isVisible=False;report['nativeWires'].append({'key':row['key'],'pathEntities':path.count,'lengthMm':length,'volumeMm3':f.bodies.item(0).volume*1000,'fittedAnalyticReadback':fitReports});(D/'native-mixed-readback.json').write_text(json.dumps(report,indent=2))


 for i in range(root.occurrences.count):
  o=root.occurrences.item(i)
  if o.component.name=='SOURCE REFERENCE right-case-anchor':o.isLightBulbOn=False
 for row in json.loads((D/'keeper-candidates.json').read_text())['parts']:
  if not row['key'].startswith('right-'):continue
  assert sha(row['file'])==row['sha256'];o=comp('ADJUSTABLE TIE '+row['key']);bf=o.component.features.baseFeatures.add();bf.startEdit()
  try:meshes=o.component.meshBodies.add(row['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,bf)
  finally:bf.finishEdit()
  assert meshes.count>0;o.component.opacity=.8
 design.computeAll();out=D/('Fusion-mixed-retained-review-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.f3d');assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(out)));report.update(status='NATIVE_MIXED_RETAINED_REVIEW',output=str(out),outputSha256=sha(out),remaining=['Side-view packaging review','100 mm nominal stock availability and actual flexible span','Manual soft loop adjustment; not rigid walking proof']);app.activeViewport.fit()
try:run(None)
except Exception:report.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
finally:(D/'native-mixed-readback.json').write_text(json.dumps(report,indent=2))
