"""Import the frozen local IMU assembly into a new Fusion document."""
import adsk.core, adsk.fusion, json, hashlib, traceback
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair')
M=D/'power-sensor/imu-local-manifest.json'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
out={'status':'RUNNING','manifestSha256':sha(M),'parts':[],'physicalFitVerified':False,'wholeHarnessAccepted':False}
try:
 cfg=json.loads(M.read_text()); a=cfg['acceptance']; assert sha(a['report'])==a['sha256']
 check=json.loads(Path(a['report']).read_text()); assert check['passed'] and check['complete'] and not check['failures']
 for p,h in check['sourceHashes'].items(): assert sha(p)==h, p
 for p in cfg['parts']: assert sha(p['file'])==p['sha256'],p['key']
 app=adsk.core.Application.get()
 if app.activeDocument and app.activeDocument.name=='MicroDuck IMU local assembly':
  doc=app.activeDocument
 else:
  doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='MicroDuck IMU local assembly'
 design=adsk.fusion.Design.cast(app.activeProduct); root=design.rootComponent
 for p in cfg['parts']:
  T=p['sourceToWorld']; arr=[x for row in T for x in row]
  for k in (3,7,11):arr[k]/=10
  matrix=adsk.core.Matrix3D.create(); assert matrix.setWithArray(arr)
  matches=[]
  for i in range(root.occurrences.count):
   q=root.occurrences.item(i); attr=q.component.attributes.itemByName('MicroDuck','source')
   if attr and json.loads(attr.value)['key']==p['key']:
    assert json.loads(attr.value)['sha256']==p['sha256'];matches.append(q)
  assert len(matches)<=1
  if matches:occ=matches[0]
  else:
   occ=root.occurrences.addNewComponent(matrix);occ.component.name=p['name']
   occ.component.attributes.add('MicroDuck','source',json.dumps({'key':p['key'],'file':p['file'],'sha256':p['sha256']}))
   opts=app.importManager.createSTEPImportOptions(p['file']); assert app.importManager.importToTarget(opts,occ.component)
  box=occ.preciseBoundingBox; actual=[list(v*10 for v in box.minPoint.asArray()),list(v*10 for v in box.maxPoint.asArray())]
  err=max(abs(actual[i][j]-p['expectedFinalBoundsMm'][i][j]) for i in range(2) for j in range(3))
  assert err<.02,(p['key'],'placement/scale mismatch',err)
  if p['key']=='imu_cover':occ.component.opacity=.35
  out['parts'].append({'key':p['key'],'boundsMm':actual,'boundsErrorMm':err,'sourceSha256':p['sha256']})
 design.computeAll()
 inventory=[]
 for i in range(root.allOccurrences.count):
  occ=root.allOccurrences.item(i)
  for j in range(occ.bRepBodies.count):
   body=occ.bRepBodies.item(j);assert body.isSolid and body.volume>0
   inventory.append({'occurrence':occ.fullPathName,'body':body.name,'volumeMm3':body.volume*1000})
 assert len(inventory)==62,('Unexpected imported solid inventory',len(inventory))
 archive=D/'power-sensor/MicroDuck-IMU-local-assembly.f3d'
 assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
 camera=app.activeViewport.camera;camera.eye=adsk.core.Point3D.create(-18,-12,10);camera.target=adsk.core.Point3D.create(-3,-1,3);camera.upVector=adsk.core.Vector3D.create(0,0,1);camera.isFitView=True;app.activeViewport.camera=camera
 app.activeViewport.refresh()
 png=D/'power-sensor/imu-native-assembly.png';assert app.activeViewport.saveAsImageFile(str(png),1440,1000)
 out.update(status='NATIVE_LOCAL_ASSEMBLY_IMPORTED',inventory=inventory,nativeSolidCount=len(inventory),archive=str(archive),archiveSha256=sha(archive),image=str(png),acceptanceReportSha256=a['sha256'],scope=cfg['acceptance']['scope'])
except Exception:out.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
finally:(D/'power-sensor/fusion-imu-readback.json').write_text(json.dumps(out,indent=2))
