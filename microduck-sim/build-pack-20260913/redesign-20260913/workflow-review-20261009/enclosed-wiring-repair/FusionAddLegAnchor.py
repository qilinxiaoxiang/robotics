import adsk.core,adsk.fusion,json,hashlib,traceback
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
out={'status':'RUNNING','wholeHarnessAccepted':False,'physicalFitVerified':False}
try:
 manifest=D/'retention-fusion-manifest.json';cfg=json.loads(manifest.read_text())
 for p,h in cfg['sourceHashes'].items():assert sha(p)==h,p
 part=next(p for p in cfg['parts']if p['key']=='right-case-anchor');assert sha(part['file'])==part['sha256']
 app=adsk.core.Application.get();docs=[app.documents.item(i)for i in range(app.documents.count)if app.documents.item(i).name.startswith('LOCAL ttl-04-03')];assert len(docs)==1,'Expected one existing local leg document'
 doc=docs[0];doc.activate();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent;design.activateRootComponent()
 matches=[root.occurrences.item(i)for i in range(root.occurrences.count)if root.occurrences.item(i).component.name=='Case anchor receiving envelope']
 assert len(matches)<=1
 if matches:
  occ=matches[0];assert occ.component.attributes.itemByName('MicroDuck','sourceSha256').value==part['sha256']
 else:
  occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());comp=occ.component;comp.name='Case anchor receiving envelope'
  base=comp.features.baseFeatures.add();base.name='Source-bound bought tie envelope';base.startEdit()
  try:bodies=comp.meshBodies.add(part['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base);assert bodies.count==1
  finally:base.finishEdit()
  comp.attributes.add('MicroDuck','sourceSha256',part['sha256'])
  comp.attributes.add('MicroDuck','scope','Nylon tie receiving mesh; static and rigid anchor motion checks external; not printed stock or an exact flexible simulation.')
  bodies.item(0).name='Case strap and 5x5x3 mm lock envelope'
 coords=[]
 for point in occ.component.meshBodies.item(0).mesh.nodeCoordinates:
  point.transformBy(occ.transform2);coords.append([x*10 for x in point.asArray()])
 actual=[[min(p[j]for p in coords)for j in range(3)],[max(p[j]for p in coords)for j in range(3)]]
 err=max(abs(actual[i][j]-part['expectedFinalBoundsMm'][i][j])for i in range(2)for j in range(3));assert err<1e-4,(actual,err)
 wires=[]
 for i in range(root.occurrences.count):
  c=root.occurrences.item(i).component
  if c.name.startswith('Conductor '):
   assert c.features.sweepFeatures.count==1
   b=c.features.sweepFeatures.item(0).bodies.item(0);assert b.isSolid
   wires.append({'name':c.name,'volumeMm3':b.volume*1000})
 assert len(wires)==3
 archive=D/'Fusion-ttl-04-03-retained-local.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
 out.update(status='ANCHOR_ADDED_TO_NATIVE_LOCAL_ASSEMBLY',manifestSha256=sha(manifest),anchorSha256=part['sha256'],anchorBoundsMm=actual,boundsErrorMm=err,nativeConductors=wires,archive=str(archive),archiveSha256=sha(archive),scope='Rigid receiving strap only; flexible keeper is adjusted during physical assembly. Existing wire sweeps retained. Whole leg not accepted by this import.')
 app.activeViewport.fit()
except Exception:out.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
finally:(D/'fusion-retention-readback.json').write_text(json.dumps(out,indent=2))
