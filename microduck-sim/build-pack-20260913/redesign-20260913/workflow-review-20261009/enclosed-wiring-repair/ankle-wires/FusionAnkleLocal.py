"""Fusion Python.Run: new standalone editable ankle review, never active-model edits.
Six analytic 3D line/arc sketches + native circular sweeps, four native receiving
boxes, source motor BReps and limited unchanged mesh context. No mesh conversion.
Run only in Fusion; serialization/readback is not whole-harness acceptance.
"""
import adsk.core, adsk.fusion
from pathlib import Path
import datetime, hashlib, json, math, traceback, uuid
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/ankle-wires')
EXPECTED_MANIFEST_SHA='b9e7bbea531366162f16e47e59a87b115997b0d6cd84481bc03f0c8d1b026710'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def point(v):return adsk.core.Point3D.create(*[float(x)/10 for x in v])
def matrix(T):
 a=[float(v)for row in T for v in row]
 for i in (3,7,11):a[i]/=10
 m=adsk.core.Matrix3D.create();assert m.setWithArray(a);return m
def endpoint(curve,xyz):
 pts=[curve.startSketchPoint,curve.endSketchPoint];p=min(pts,key=lambda q:q.worldGeometry.distanceTo(point(xyz)))
 assert p.worldGeometry.distanceTo(point(xyz))*10<1e-5
 return p
def mm_bounds(body):
 bb=body.preciseBoundingBox
 return [[bb.minPoint.x*10,bb.minPoint.y*10,bb.minPoint.z*10],[bb.maxPoint.x*10,bb.maxPoint.y*10,bb.maxPoint.z*10]]
def run(context):
 tag=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
 out=D/('native-'+tag);out.mkdir(exist_ok=False)
 report={'status':'RUNNING','wholeHarnessAccepted':False,'scriptSha256':sha(D/'FusionAnkleLocal.py'),'sourceManifestSha256':sha(D/'ankle-fusion-manifest.json'),'curves':[],'sweeps':[],'housings':[],'meshReferences':[],'constraints':[]}
 try:
  assert report['sourceManifestSha256']==EXPECTED_MANIFEST_SHA,'Frozen ankle manifest changed'
  cfg=json.loads((D/'ankle-fusion-manifest.json').read_text())
  for path,h in cfg['sourceHashes'].items():assert sha(path)==h,path
  for row in cfg['parts']:assert sha(row['file'])==row['sha256'],row['key']
  route=json.loads((D/'ankle-route-check.json').read_text());assert route['complete'] and route['passedStatic'];assert len(route['strands'])==6
  native=json.loads((D/'native-motors/manifest.json').read_text());assert sha(native['sourceFile'])==native['sourceSha256']
  app=adsk.core.Application.get();resume_file=D/'fusion-ankle-last-run.json';prior=None
  if resume_file.exists():
   last=json.loads(resume_file.read_text());pr=Path(last['report'])
   if pr.exists():
    candidate=json.loads(pr.read_text())
    if candidate.get('status')=='FAILED_NOT_ACCEPTED' and candidate.get('sourceManifestSha256')==EXPECTED_MANIFEST_SHA and candidate.get('documentName'):prior=candidate
  if prior:
   matches=[app.documents.item(i) for i in range(app.documents.count) if app.documents.item(i).name==prior['documentName']]
   assert len(matches)==1,'Exact failed ankle document must be open; refusing a new dangling document'
   doc=matches[0];doc.activate();report['resumedDocument']=True
  else:
   doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='MicroDuck two ankle routes - local native review '+tag
  design=adsk.fusion.Design.cast(app.activeProduct);assert design
  if not prior:design.designType=adsk.fusion.DesignTypes.ParametricDesignType
  design.activateRootComponent();root=design.rootComponent;report['documentName']=doc.name
  def component(name,T=None,preserve=False):
   existing=[root.occurrences.item(i)for i in range(root.occurrences.count)if root.occurrences.item(i).component.name==name]
   assert len(existing)<=1,('Duplicate local component',name)
   if existing and preserve:return existing[0],False
   if existing:assert existing[0].deleteMe(),'Could not rebuild this script-owned partial component'
   occ=root.occurrences.addNewComponent(matrix(T)if T else adsk.core.Matrix3D.create());occ.component.name=name
   return (occ,True) if preserve else occ
  def native_bodies(top_occ):
   # Traverse each occurrence once. Bodies remain in their original STEP components.
   found=[]
   def visit(occ):
    comp=occ.component
    for i in range(comp.bRepBodies.count):
     native_body=comp.bRepBodies.item(i);proxy=native_body.createForAssemblyContext(occ)
     assert native_body.isSolid and native_body.volume>0
     found.append({'occurrence':occ.fullPathName,'name':native_body.name,'nativeVolumeMm3':native_body.volume*1000,'worldBoundsMm':mm_bounds(proxy)})
    for i in range(comp.occurrences.count):
     child=comp.occurrences.item(i);visit(child.createForAssemblyContext(occ))
   visit(top_occ);return found
  ports={}
  for w in route['strands']:
   for label in ('source','target'):
    p=w[label];ports[(p['motor'],p['sourceSocket'])]=p
  assert len(ports)==4
  for (motor,socket),p in ports.items():
   occ,created=component('SOURCE XL330 ID '+str(motor),p['transform'],preserve=True)
   if created:
    opts=app.importManager.createSTEPImportOptions(native['sourceFile']);assert app.importManager.importToTarget(opts,occ.component)
   bodies=native_bodies(occ)
   report.setdefault('manufacturerMotors',[]).append({'motor':motor,'sourceFile':native['sourceFile'],'sourceSha256':native['sourceSha256'],'sourceToWorld':p['transform'],'reusedExistingImport':not created,'bodies':bodies})
   assert len(bodies)==12,('Expected 12 nested manufacturer native bodies',motor,len(bodies))
   hp=component('ID '+str(motor)+' EHR3 catalogue envelope',p['transform']);comp=hp.component;lo,hi=p['housingLocalBounds']
   pi=comp.constructionPlanes.createInput();assert pi.setByOffset(comp.xYConstructionPlane,adsk.core.ValueInput.createByReal(lo[2]/10));pl=comp.constructionPlanes.add(pi)
   sk=comp.sketches.add(pl);sk.name='Catalogue rectangular profile; not detailed latch plastic'
   sk.sketchCurves.sketchLines.addTwoPointRectangle(point([lo[0],lo[1],0]),point([hi[0],hi[1],0]))
   ext=comp.features.extrudeFeatures.addSimple(sk.profiles.item(0),adsk.core.ValueInput.createByReal((hi[2]-lo[2])/10),adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
   body=ext.bodies.item(0);assert body.isSolid;body.name='EHR3 full receiving box';sk.isVisible=False;pl.isLightBulbOn=False
   proxy=body.createForAssemblyContext(hp)
   report['housings'].append({'motor':motor,'socket':socket,'nativeVolumeMm3':body.volume*1000,'worldBoundsMm':mm_bounds(proxy),'ownCaseBoxContactRecordedInSource':True,'detailedMatingAccepted':False})
  for row in route['strands']:
   occ=component(row['key']+' native 180 mm');comp=occ.component;sk=comp.sketches.add(comp.xYConstructionPlane);sk.name='EDITABLE 3D tangent lines and arcs; R2 / R4 receiving assumptions';curves=[];prev=None
   for p in row['primitives']:
    start=prev if prev else point(p['start'])
    c=sk.sketchCurves.sketchLines.addByTwoPoints(start,point(p['end']))if p['kind']=='line'else sk.sketchCurves.sketchArcs.addByThreePoints(start,point(p['mid']),point(p['end']))
    assert c;c.attributes.add('MicroDuck','analyticPrimitive',json.dumps(p));curves.append(c);prev=endpoint(c,p['end'])
   for i,(a,b)in enumerate(zip(curves,curves[1:])):
    x=endpoint(a,row['primitives'][i]['end']);y=endpoint(b,row['primitives'][i+1]['start'])
    if x!=y:assert x.merge(y),('Point merge failed',row['key'],i)
    assert endpoint(a,row['primitives'][i]['end'])==endpoint(b,row['primitives'][i+1]['start'])
    try:sk.geometricConstraints.addTangent(a,b);report['constraints'].append({'wire':row['key'],'join':i,'tangent':True})
    except Exception as e:report['constraints'].append({'wire':row['key'],'join':i,'tangent':False,'reason':str(e),'analyticSourceRetained':True})
   total=0
   for p,c in zip(row['primitives'],curves):
    g=c.worldGeometry;a=g.startPoint;b=g.endPoint;err=10*min(max(a.distanceTo(point(p['start'])),b.distanceTo(point(p['end']))),max(a.distanceTo(point(p['end'])),b.distanceTo(point(p['start']))))
    assert err<1e-5,('Native solver moved checked curve',row['key'],err)
    assert abs(c.length*10-p['lengthMm'])<1e-5
    if p['kind']=='arc':assert abs(g.radius*10-p['radiusMm'])<1e-5
    total+=c.length*10;report['curves'].append({'wire':row['key'],'kind':p['kind'],'nativeLengthMm':c.length*10,'endpointErrorMm':err,'radiusMm':g.radius*10 if p['kind']=='arc'else None})
   assert abs(total-180)<1e-4
   coll=adsk.core.ObjectCollection.create()
   for c in curves:coll.add(c)
   path=comp.features.createPath(coll,False);assert path and path.count==len(curves)
   path_length=sum(path.item(i).entity.length*10 for i in range(path.count));assert abs(path_length-180)<1e-4
   chain=comp.features.createPath(curves[0],True);assert chain and chain.count==len(curves),'Native connected chain incomplete'
   pi=comp.constructionPlanes.createInput();assert pi.setByDistanceOnPath(path,adsk.core.ValueInput.createByReal(0));plane=comp.constructionPlanes.add(pi)
   profile=comp.sketches.add(plane);profile.name='Diameter 1.5 mm wire receiving assumption';center=profile.modelToSketchSpace(point(row['primitives'][0]['start']));profile.sketchCurves.sketchCircles.addByCenterRadius(center,.075)
   inp=comp.features.sweepFeatures.createInput(profile.profiles.item(0),path,adsk.fusion.FeatureOperations.NewBodyFeatureOperation);inp.orientation=adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
   feat=comp.features.sweepFeatures.add(inp);assert feat and feat.bodies.count==1;body=feat.bodies.item(0);assert body.isSolid and body.volume>0;body.name=row['key']+' native circular sweep'
   nominal=math.pi*.75**2*180;assert abs(body.volume*1000-nominal)<.01,('Sweep volume differs',row['key'],body.volume*1000,nominal)
   report['sweeps'].append({'wire':row['key'],'solid':True,'nativeLengthMm':total,'nativeVolumeMm3':body.volume*1000,'expectedCircleVolumeMm3':nominal,'worldBoundsMm':mm_bounds(body),'sourceReceivingMeshBoundsMm':row['boundsMm'],'receivingMeshIsConservative':True})
   profile.isVisible=False;sk.isVisible=False;plane.isLightBulbOn=False
  O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
  for key in ['right_thigh','thigh','right_lower','lower','right_ankle','ankle','right_smallring','smallring','right_foot','foot','right_plate','plate']:
   meta=json.loads((O/(key+'.json')).read_text());assert sha(meta['file'])==meta['sha256'];delta=meta.get('importTranslationMm',[0,0,0]);T=[[1,0,0,delta[0]],[0,1,0,delta[1]],[0,0,1,delta[2]],[0,0,0,1]]
   occ=component('UNCHANGED MESH '+key,T);base=occ.component.features.baseFeatures.add();base.startEdit()
   try:bodies=occ.component.meshBodies.add(meta['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base)
   finally:base.finishEdit()
   assert bodies.count>0;occ.component.opacity=.3
   report['meshReferences'].append({'key':key,'sourceFile':meta['file'],'sourceSha256':meta['sha256'],'translationMm':delta,'nativeSolid':False})
  assert len(report['sweeps'])==6 and len(report['housings'])==4
  design.computeAll();archive=out/'MicroDuck-two-ankle-routes-native.f3d';opts=design.exportManager.createFusionArchiveExportOptions(str(archive));assert design.exportManager.execute(opts)
  report.update(status='NATIVE_CREATED_REVIEW_REQUIRED',archive=str(archive),archiveSha256=sha(archive),nativeWireCount=6,nativeHousingCount=4,nativeMotorBodyCount=48,remaining=cfg['remainingScope'],assemblyInstructions=cfg['assembly'],acceptanceScope='Native readback of the frozen local neutral geometry only; source static/self/preconnection receipts remain separate. Whole harness and flexible articulation not accepted.')
  app.activeViewport.fit()
 except Exception:report.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
 finally:
  (out/'native-readback.json').write_text(json.dumps(report,indent=2)+'\n')
  (D/'fusion-ankle-last-run.json').write_text(json.dumps({'report':str(out/'native-readback.json'),'status':report['status']},indent=2)+'\n')
run(None)
