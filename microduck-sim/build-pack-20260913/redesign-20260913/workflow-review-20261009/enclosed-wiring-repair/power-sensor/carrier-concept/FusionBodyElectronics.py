"""Fusion Python.Run: frozen local body-electronics assembly, no active-model edits.
Import native additions, manufacturer STEP hierarchy and local receiving sweeps.
Retained community material stays an explicitly labelled mesh reference.
Native readback is not electrical commissioning or whole-harness acceptance.
"""
import adsk.core, adsk.fusion
from pathlib import Path
import datetime, hashlib, json, traceback, uuid
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/power-sensor/carrier-concept')
EXPECTED_MANIFEST_SHA='82e21a8b81db3461493a3d9478055ff96c977dcfcb79e05599beecafac7d4387'
PRIOR_BOUNDS_MANIFEST_SHA='f3b4e52d8dcfe71327b6295af90b3a211ce275a788a9bf028d61a81666f218fd'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def matrix(T):
 a=[float(v)for row in T for v in row]
 for i in (3,7,11):a[i]/=10
 m=adsk.core.Matrix3D.create();assert m.setWithArray(a);return m

def bounds(entity):
 b=entity.preciseBoundingBox
 if b is None:
  coordinates=[]
  for mesh in entity.component.meshBodies:
   for v in mesh.displayMesh.nodeCoordinates:
    q=v.copy();q.transformBy(entity.transform2);coordinates.append([q.x*10,q.y*10,q.z*10])
  assert coordinates, 'Mesh-only occurrence has no nodes'
  return [[min(q[i]for q in coordinates)for i in range(3)],[max(q[i]for q in coordinates)for i in range(3)]]
 assert b is not None, 'No geometric bounds for imported occurrence'
 return [[b.minPoint.x*10,b.minPoint.y*10,b.minPoint.z*10],[b.maxPoint.x*10,b.maxPoint.y*10,b.maxPoint.z*10]]

def nested_bodies(top):
 out=[]
 def visit(occ):
  comp=occ.component
  for i in range(comp.bRepBodies.count):
   native=comp.bRepBodies.item(i);assert native.isSolid and native.volume>0
   proxy=native.createForAssemblyContext(occ)
   out.append({'occurrence':occ.fullPathName,'name':native.name,'volumeMm3':native.volume*1000,'boundsMm':bounds(proxy)})
  for i in range(comp.occurrences.count):visit(comp.occurrences.item(i).createForAssemblyContext(occ))
 visit(top);return out

def run(context):
 tag=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
 folder=D/('native-'+tag);folder.mkdir(exist_ok=False)
 report={'status':'RUNNING','manifestSha256':sha(D/'carrier-manifest.json'),'scriptSha256':sha(D/'FusionBodyElectronics.py'),'parts':[],'wholeHarnessAccepted':False,'physicalFitVerified':False}
 try:
  assert report['manifestSha256']==EXPECTED_MANIFEST_SHA,'Frozen local manifest changed'
  cfg=json.loads((D/'carrier-manifest.json').read_text());assert len(cfg['parts'])==9
  for f,h in cfg['sourceHashes'].items():assert sha(f)==h,f
  a=cfg['localAssemblyAcceptance'];assert a['passed'] and a['complete'] and sha(a['report'])==a['sha256']
  check=json.loads(Path(a['report']).read_text());assert check['passed'] and check['complete'] and check['coverage']['complete']
  for f,h in check['sourceHashes'].items():assert sha(f)==h,f
  for p in cfg['parts']:assert sha(p['file'])==p['sha256'],p['key']
  # Resume only the same model after the one documented asymmetric-bounds correction.
  # The old snapshot is not an alternative accepted source; current hashes above are mandatory.
  previous=D/'carrier-manifest-before-bound-correction.json'
  assert sha(previous)==PRIOR_BOUNDS_MANIFEST_SHA
  before=json.loads(previous.read_text())
  target=next(q for q in before['parts']if q['key']=='OpenRB150_native')
  assert target['expectedFinalBoundsMm'][1][1]==12.71
  target['expectedFinalBoundsMm'][1][1]=12.69
  assert before==cfg,'Only the exact expected upper Y bound may differ for document resume'
  resume_hashes={EXPECTED_MANIFEST_SHA,PRIOR_BOUNDS_MANIFEST_SHA}
  app=adsk.core.Application.get();lastfile=D/'fusion-carrier-last-run.json';prior=None
  if lastfile.exists():
   last=json.loads(lastfile.read_text());p=Path(last['report'])
   if p.exists():
    old=json.loads(p.read_text())
    if old.get('status')=='FAILED_NOT_ACCEPTED' and old.get('manifestSha256')in resume_hashes and old.get('documentName'):prior=old
  if prior:
   matches=[app.documents.item(i)for i in range(app.documents.count)if app.documents.item(i).name==prior['documentName']]
   assert len(matches)==1,'Open exact failed document to resume; refusing another dangling document'
   doc=matches[0];doc.activate();report['resumedDocument']=True
  else:
   doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='MicroDuck body electronics - local assembly '+tag
  report['documentName']=doc.name
  design=adsk.fusion.Design.cast(app.activeProduct);assert design
  if not prior:design.designType=adsk.fusion.DesignTypes.ParametricDesignType
  design.activateRootComponent();root=design.rootComponent
  for p in cfg['parts']:
   found=[]
   for i in range(root.occurrences.count):
    q=root.occurrences.item(i);attr=q.component.attributes.itemByName('MicroDuck','carrierSource')
    if attr:
     data=json.loads(attr.value)
     if data['key']==p['key']:
      assert data['sha256']==p['sha256'];found.append(q)
   assert len(found)<=1,('Duplicate part',p['key'])
   if found:
    occ=found[0];state=occ.component.attributes.itemByName('MicroDuck','carrierImported')
    if not state:
     assert occ.deleteMe();found=[]
   if not found:
    occ=root.occurrences.addNewComponent(matrix(p['sourceToWorld']));occ.component.name=p['name']
    occ.component.attributes.add('MicroDuck','carrierSource',json.dumps({'key':p['key'],'file':p['file'],'sha256':p['sha256'],'sourceToWorld':p['sourceToWorld']}))
    if p['geometryKind']=='source mesh':
     base=occ.component.features.baseFeatures.add();base.startEdit()
     try:meshes=occ.component.meshBodies.add(p['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base)
     finally:base.finishEdit()
     assert meshes.count>0;occ.component.opacity=.55
    else:
     options=app.importManager.createSTEPImportOptions(p['file']);assert app.importManager.importToTarget(options,occ.component)
    occ.component.attributes.add('MicroDuck','carrierImported','true')
   native=nested_bodies(occ);assert len(native)==p['expectedNativeSolidCount'],('Unexpected nested native count',p['key'],len(native),p['expectedNativeSolidCount'])
   actual=bounds(occ);expected=p['expectedFinalBoundsMm']
   err=max(abs(actual[i][j]-expected[i][j])for i in range(2)for j in range(3))
   # Only the published manufacturer envelope is rounded to two decimal mm.
   tolerance=.006 if p['expectedBoundsPrecisionMm']==.01 else .002
   assert err<tolerance,('Source/world placement or mm scale mismatch',p['key'],err,actual,expected)
   row={'key':p['key'],'file':p['file'],'sourceSha256':p['sha256'],'sourceToWorld':p['sourceToWorld'],'worldBoundsMm':actual,'expectedBoundsMm':expected,'boundsErrorMm':err,'boundsToleranceMm':tolerance,'nativeBodies':native,'nativeSolidCount':len(native),'meshReference':p['geometryKind']=='source mesh'}
   report['parts'].append(row)
  count=sum(x['nativeSolidCount']for x in report['parts']);assert count==143
  assert sum(x['meshReference']for x in report['parts'])==1
  design.computeAll();archive=folder/'MicroDuck-body-electronics-local.f3d'
  assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
  app.activeViewport.fit()
  image=folder/'body-electronics-native.png';assert app.activeViewport.saveAsImageFile(str(image),1440,1000)
  report.update(status='NATIVE_LOCAL_ASSEMBLY_IMPORTED_REVIEW_REQUIRED',nativeSolidCount=count,manufacturerNativeSolidCount=136,meshReferenceParts=1,archive=str(archive),archiveSha256=sha(archive),image=str(image),acceptanceReportSha256=a['sha256'],acceptanceScope=a['scope'],assemblySequence=cfg['assemblyPlanning'],remaining=cfg['remaining'])
 except Exception:report.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
 finally:
  output=folder/'native-readback.json';output.write_text(json.dumps(report,indent=2)+'\n')
  lastfile=D/'fusion-carrier-last-run.json';lastfile.write_text(json.dumps({'report':str(output),'status':report['status']},indent=2)+'\n')
run(None)
