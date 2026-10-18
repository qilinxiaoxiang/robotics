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
def path_readback(path,curves):
 if not path:return {'count':0,'sourceIndices':[],'lengthMm':0,'complete':False}
 ids=[];length=0;entities=[]
 for i in range(path.count):
  pe=path.item(i);e=pe.entity;native=getattr(e,'nativeObject',None)or e;index=next((j for j,q in enumerate(curves)if q==native or q==e),None);ids.append(index)
  ev=pe.curve.evaluator;ok,a,b=ev.getParameterExtents();assert ok;ok,l=ev.getLengthAtParameter(a,b);assert ok;length+=l*10
  entities.append({'index':i,'sourceIndex':index,'type':e.objectType,'lengthMm':l*10})
 complete=len(ids)==len(curves)and sorted(x for x in ids if x is not None)==list(range(len(curves)))and abs(length-180)<.01
 return {'count':path.count,'sourceIndices':ids,'lengthMm':length,'complete':complete,'entities':entities}
def run(context):
 app=adsk.core.Application.get();docs=[d for d in app.documents if 'COMPLETE RIGHT LEG' in d.name];assert len(docs)==1;doc=docs[0];doc.activate();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent;design.activateRootComponent()
 row=next(r for r in json.loads((D/'eight-leg-centerlines.json').read_text())['paths']if r['key']=='ttl-05-04-conductor-1');occ=next(o for o in root.occurrences if o.component.name==row['key']);c=occ.component;assert c.bRepBodies.count==0;sk=c.sketches.item(0);curves=[];spec=[];T=row['canonicalToWorld']
 candidates=[q for q in sk.sketchCurves if q.attributes.itemByName('MicroDuck','sourcePrimitive')]
 for i,p in enumerate(row['orderedPrimitives']):
  if p['kind']in ['line','arc']:
   found=[q for q in candidates if json.loads(q.attributes.itemByName('MicroDuck','sourcePrimitive').value)==p];assert len(found)==1;curves+=found;spec.append((transform_point(p['start'],T),transform_point(p['end'],T)))
  else:
   for cp,fit in cubic_chunks(p):
    world=[transform_point(x,T)for x in cp];found=[q for q in candidates if json.loads(q.attributes.itemByName('MicroDuck','sourcePrimitive').value).get('cubicControlsWorldMm')==world];assert len(found)==1;curves+=found;spec.append((world[0],world[-1]))
 assert len(curves)==len(candidates);report['expectedEntities']=len(curves);report['sketchLengthMm']=sum(q.length*10 for q in curves);report['maximumJoinAngleDegrees']=max(x['angleDegrees']for x in joins(curves,spec));assert abs(report['sketchLengthMm']-180)<.01;assert report['maximumJoinAngleDegrees']<.001
 path=c.features.createPath(collection(curves),False);report['explicit']=path_readback(path,curves)
 try:report['auto']=path_readback(c.features.createPath(curves[0],True),curves)
 except Exception:report['auto']={'error':traceback.format_exc()}
 (D/'fusion-hip-path-readback.json').write_text(json.dumps(report,indent=2));assert report['explicit']['complete'],'Explicit source curve coverage incomplete'
 pi=c.constructionPlanes.createInput();assert pi.setByDistanceOnPath(path,adsk.core.ValueInput.createByReal(0));pl=c.constructionPlanes.add(pi);profile=c.sketches.add(pl);profile.sketchCurves.sketchCircles.addByCenterRadius(profile.modelToSketchSpace(point(spec[0][0])),.075)
 inp=c.features.sweepFeatures.createInput(profile.profiles.item(0),path,adsk.fusion.FeatureOperations.NewBodyFeatureOperation);inp.orientation=adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType;f=c.features.sweepFeatures.add(inp);assert f and f.bodies.count==1 and f.bodies.item(0).isSolid
 report['nativeWire']={'key':row['key'],'volumeMm3':f.bodies.item(0).volume*1000,'pathLengthMm':report['explicit']['lengthMm'],'pathEntities':path.count,'nativeSolid':True};sk.isVisible=False;profile.isVisible=False;pl.isLightBulbOn=False;report['status']='FIRST_HIP_NATIVE_SWEEP_CREATED';design.computeAll()
 report['preservedNine']={}
 old=json.loads((D/'fusion-complete-leg-readback.json').read_text())
 for r in old['nativeWires']:
  co=next(o.component for o in root.occurrences if o.component.name==r['key']);v=co.bRepBodies.item(0).volume*1000;assert abs(v-r['volumeMm3'])<1e-7;report['preservedNine'][r['key']]=v
try:run(None)
except Exception:report.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
finally:(D/'fusion-hip-path-readback.json').write_text(json.dumps(report,indent=2))
