"""Repair shared sketch endpoints and continue native sweeps in the EXISTING local document.
No STEP imports, mesh replacement or robot-model changes.
"""
import adsk.core,adsk.fusion,json,traceback,hashlib
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires')
report={'status':'RUNNING','wholeHarnessAccepted':False,'wires':[]}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def point(v):return adsk.core.Point3D.create(*[x/10 for x in v])
def collection(curves):
 out=adsk.core.ObjectCollection.create()
 for c in curves:out.add(c)
 return out
def endpoint(curve,xyz):
 pts=[curve.startSketchPoint,curve.endSketchPoint];p=min(pts,key=lambda q:q.worldGeometry.distanceTo(point(xyz)))
 assert p.worldGeometry.distanceTo(point(xyz))*10<1e-5
 return p

def path_info(path):
 out=[]
 if not path:return {'count':0,'entities':[],'lengthMm':0}
 for i in range(path.count):
  pe=path.item(i);curve=pe.entity
  out.append({'type':curve.objectType,'construction':getattr(curve,'isConstruction',None),'lengthMm':curve.length*10,'sourcePrimitive':json.loads(curve.attributes.itemByName('MicroDuck','primitive').value) if curve.attributes.itemByName('MicroDuck','primitive')else None})
 return {'count':path.count,'entities':out,'lengthMm':sum(x['lengthMm']for x in out)}

def run():
 app=adsk.core.Application.get();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
 assert design.parentDocument.name.startswith('LOCAL ttl-04-03'), 'Wrong active document; no changes made.'
 cfg=json.loads((D/'local-route.json').read_text());report['routeSha256']=sha(D/'local-route.json');report['document']=design.parentDocument.name
 design.activateRootComponent()
 for row in cfg['strands']:
  rec={'wire':row['id'],'joins':[],'tangentConstraints':[]};report['wires'].append(rec)
  occs=[root.occurrences.item(i)for i in range(root.occurrences.count)if root.occurrences.item(i).component.name==f"Conductor {row['id']} 180mm"]
  assert len(occs)<=1
  occ=occs[0]if occs else root.occurrences.addNewComponent(adsk.core.Matrix3D.create());comp=occ.component
  if not occs:comp.name=f"Conductor {row['id']} 180mm"
  sketches=[comp.sketches.item(i)for i in range(comp.sketches.count)if comp.sketches.item(i).name.startswith('EDITABLE 3D')]
  if sketches:
   assert len(sketches)==1;sk=sketches[0];allcurves=[sk.sketchCurves.item(i)for i in range(sk.sketchCurves.count)]
   curves=[]
   for p in row['primitives']:
    matches=[c for c in allcurves if c.attributes.itemByName('MicroDuck','primitive') and json.loads(c.attributes.itemByName('MicroDuck','primitive').value)==p]
    assert len(matches)==1;curves.append(matches[0])
   # Discriminating baseline: report actual entity TYPES, not only count.
   rec['beforePath']=path_info(comp.features.createPath(collection(curves),False))
  else:
   sk=comp.sketches.add(comp.xYConstructionPlane);sk.name='EDITABLE 3D route; local R2 and storage R4';curves=[];prev=None
   for p in row['primitives']:
    start=prev if prev else point(p['start'])
    c=sk.sketchCurves.sketchLines.addByTwoPoints(start,point(p['end'])) if p['kind']=='line' else sk.sketchCurves.sketchArcs.addByThreePoints(start,point(p['mid']),point(p['end']))
    assert c;c.attributes.add('MicroDuck','primitive',json.dumps(p));curves.append(c);prev=endpoint(c,p['end'])
  rec['curvesBefore']=[{'type':c.objectType,'isConstruction':c.isConstruction,'isReference':c.isReference,'startConnectedCount':c.startSketchPoint.connectedEntities.count,'endConnectedCount':c.endSketchPoint.connectedEntities.count}for c in curves]
  for c in curves:
   assert not c.isReference
   if c.isConstruction:c.isConstruction=False
  for i,(a,b)in enumerate(zip(curves,curves[1:])):
   x=endpoint(a,row['primitives'][i]['end']);y=endpoint(b,row['primitives'][i+1]['start']);same=x==y
   rec['joins'].append({'index':i,'alreadyShared':same,'positionErrorMm':x.worldGeometry.distanceTo(y.worldGeometry)*10,'connectedBefore':[x.connectedEntities.count,y.connectedEntities.count]})
   if not same:assert x.merge(y),('Point merge failed',i)
   assert endpoint(a,row['primitives'][i]['end'])==endpoint(b,row['primitives'][i+1]['start']),('Still disconnected',i)
   if not sketches:
    try:sk.geometricConstraints.addTangent(a,b);rec['tangentConstraints'].append(True)
    except Exception as e:rec['tangentConstraints'].append(str(e))
  design.computeAll()
  # Every original curve must survive with its checked endpoint/radius/length.
  lengths=[]
  for p,c in zip(row['primitives'],curves):
   assert c.isValid;endpoint(c,p['start']);endpoint(c,p['end']);assert abs(c.length*10-p['lengthMm'])<1e-5
   if p['kind']=='arc':assert abs(c.worldGeometry.radius*10-p['radiusMm'])<1e-5
   lengths.append(c.length*10)
  assert abs(sum(lengths)-180)<1e-4
  path=comp.features.createPath(collection(curves),False);rec['afterPath']=path_info(path)
  assert path.count==len(curves)==17 and abs(rec['afterPath']['lengthMm']-180)<1e-4,'Incomplete native path: no sweep created'
  rec['firstCurveChain']=path_info(comp.features.createPath(curves[0],True))
  assert rec['firstCurveChain']['count']==17,'Shared endpoint chain incomplete'
  # Skip an already-completed native wire; never duplicate it on a resumed run.
  if comp.features.sweepFeatures.count:
   assert comp.features.sweepFeatures.count==1;feature=comp.features.sweepFeatures.item(0)
  else:
   pi=comp.constructionPlanes.createInput();assert pi.setByDistanceOnPath(path,adsk.core.ValueInput.createByReal(0))
   plane=comp.constructionPlanes.add(pi);profile=comp.sketches.add(plane);profile.name='Ø1.5 mm receiving wire profile'
   center=profile.modelToSketchSpace(point(row['primitives'][0]['start']));circle=profile.sketchCurves.sketchCircles.addByCenterRadius(center,.075)
   inp=comp.features.sweepFeatures.createInput(profile.profiles.item(0),path,adsk.fusion.FeatureOperations.NewBodyFeatureOperation);inp.orientation=adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
   feature=comp.features.sweepFeatures.add(inp);profile.isVisible=False;plane.isLightBulbOn=False
  assert feature and feature.bodies.count==1;body=feature.bodies.item(0);assert body.isSolid and body.volume>0
  body.name=f"Native circular conductor {row['id']} 180mm";rec['nativeBody']={'solid':body.isSolid,'volumeMm3':body.volume*1000,'name':body.name};sk.isVisible=False
 design.computeAll();out=D/'Fusion-ttl-04-03-local-review.f3d';opts=design.exportManager.createFusionArchiveExportOptions(str(out));assert design.exportManager.execute(opts)
 report.update(status='NATIVE_CREATED_REVIEW_REQUIRED',output=str(out),outputSha256=sha(out),wholeHarnessAccepted=False,remaining=['Retention/installation/motion still unverified','Wire OD and R2 are receiving assumptions','Native body interference remains a separate readback; bound mesh-static receipts are available'])
 app.activeViewport.fit()
try:run()
except Exception:report.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
finally:(D/'fusion-resume-readback.json').write_text(json.dumps(report,indent=2))
