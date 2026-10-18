"""Fusion Python.Run. Add only the missing native OpenRB to the exact open head study.
A diagnostic configuration, not a release or a geometry acceptance.
"""
import adsk.core,adsk.fusion
from pathlib import Path
import json,hashlib,traceback,datetime,uuid
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study')
SPEC_SHA='e0befada3285ce49fcb2f656062d1b71b3a43cfce4d37b89fc73f26c269683bf'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mat(T):
 a=[float(x)for row in T for x in row]
 for i in (3,7,11):a[i]/=10
 m=adsk.core.Matrix3D.create();assert m.setWithArray(a);return m
def bbox(entity):
 b=entity.preciseBoundingBox;assert b is not None
 return [[b.minPoint.x*10,b.minPoint.y*10,b.minPoint.z*10],[b.maxPoint.x*10,b.maxPoint.y*10,b.maxPoint.z*10]]
def bodies(top):
 rows=[]
 def visit(occ):
  c=occ.component
  for i in range(c.bRepBodies.count):
   b=c.bRepBodies.item(i);assert b.isSolid and b.volume>0
   proxy=b.createForAssemblyContext(occ);rows.append({'name':b.name,'path':occ.fullPathName,'volumeMm3':b.volume*1000,'boundsMm':bbox(proxy)})
  for i in range(c.occurrences.count):visit(c.occurrences.item(i).createForAssemblyContext(occ))
 visit(top);return rows
def local_count(comp,seen=None):
 # Count assembly instances, not only root bRepBodies. No geometry copying.
 count=comp.bRepBodies.count
 for i in range(comp.occurrences.count):count+=local_count(comp.occurrences.item(i).component)
 return count
def run(context):
 tag=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:5];out=D/('diagnostic-native-'+tag);out.mkdir()
 r={'status':'RUNNING','accepted':False,'wholeHeadAccepted':False,'scriptSha256':sha(D/'FusionAddOriginalHeadOpenRB.py')}
 try:
  p=D/'original-head-diagnostic-spec.json';assert sha(p)==SPEC_SHA;cfg=json.loads(p.read_text());assert sha(cfg['sourceStep'])==cfg['sourceStepSha256']
  for f,h in cfg['sourceBindings'].items():assert sha(f)==h,f
  app=adsk.core.Application.get();docs=[app.documents.item(i)for i in range(app.documents.count)if app.documents.item(i).name==cfg['targetDocumentName']];assert len(docs)==1,'Exact existing head study must be open; no new document will be created'
  doc=docs[0];doc.activate();design=adsk.fusion.Design.cast(app.activeProduct);assert design;design.activateRootComponent();root=design.rootComponent;r['documentName']=doc.name
  matches=[]
  for i in range(root.occurrences.count):
   o=root.occurrences.item(i);a=o.component.attributes.itemByName('MicroDuck','originalHeadOpenRBDiagnostic')
   if a:
    old=json.loads(a.value);assert old['sourceSha256']==cfg['sourceStepSha256'];matches.append(o)
  assert len(matches)<=1,'Duplicate diagnostic controller occurrences'
  if matches:
   occ=matches[0];occ.transform2=mat(cfg['sourceToWorld']);r['reusedDiagnosticOccurrence']=True
  else:
   occ=root.occurrences.addNewComponent(mat(cfg['sourceToWorld']));occ.component.name=cfg['diagnosticName'];occ.component.attributes.add('MicroDuck','originalHeadOpenRBDiagnostic',json.dumps({'sourceSha256':cfg['sourceStepSha256'],'specSha256':SPEC_SHA}))
   available=[]
   candidate=globals().get('manufacturerComponent')
   if candidate and candidate.isValid and candidate.parentDesign==design and local_count(candidate)==136:available.append(candidate)
   for i in range(root.occurrences.count):
    q=root.occurrences.item(i);c=q.component
    if c==occ.component:continue
    if ('openrb' in c.name.lower() or 'manufacturer' in c.name.lower()) and local_count(c)==136 and c not in available:available.append(c)
   if len(available)==1:
    occ.component.occurrences.addExistingComponent(available[0],adsk.core.Matrix3D.create());r['reusedManufacturerComponent']=available[0].name
   else:
    assert not available,'Ambiguous existing manufacturer assemblies; refusing duplicate import'
    assert app.importManager.importToTarget(app.importManager.createSTEPImportOptions(cfg['sourceStep']),occ.component);r['importedOnlyManufacturerStep']=True
  occ.isLightBulbOn=True
  for o in occ.component.allOccurrences:o.isLightBulbOn=True
  for o in [occ]+[occ.component.allOccurrences.item(i)for i in range(occ.component.allOccurrences.count)]:
   for j in range(o.component.bRepBodies.count):o.component.bRepBodies.item(j).isLightBulbOn=True
  native=bodies(occ);assert len(native)==136,('Expected nested136manufacturer solids',len(native))
  actual=bbox(occ);err=max(abs(actual[i][j]-cfg['expectedWorldBoundsMm'][i][j])for i in range(2)for j in range(3));assert err<cfg['worldBoundsToleranceMm'],('Original source pose/mm mismatch',actual,err)
  volume=sum(x['volumeMm3']for x in native);assert abs(volume-cfg['expectedSourceTotalVolumeMm3'])<.02,('Source volume differs',volume,cfg['expectedSourceTotalVolumeMm3'])
  design.computeAll();archive=out/'diagnostic-original-openrb-coupled-head.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
  r.update(status='DIAGNOSTIC_CONTROLLER_ADDED_NOT_ACCEPTED',nativeSolidCount=len(native),nativeBodies=native,worldBoundsMm=actual,boundsErrorMm=err,sourceToWorld=cfg['sourceToWorld'],specSha256=SPEC_SHA,sourceStep=cfg['sourceStep'],sourceStepSha256=cfg['sourceStepSha256'],archive=str(archive),archiveSha256=sha(archive),knownConflicts='Original rearUSB-C vs closed native shell; current Pi/header, MicroB and amplifier/mounts require coupled repair. Visible model is diagnostic only.')
 except Exception:r.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
 finally:
  p=out/'native-readback.json';p.write_text(json.dumps(r,indent=2)+'\n');(D/'fusion-original-openrb-last-run.json').write_text(json.dumps({'report':str(p),'status':r['status']},indent=2)+'\n')
run(None)
