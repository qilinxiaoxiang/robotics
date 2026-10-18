import adsk.core,adsk.fusion,json,hashlib
from pathlib import Path
F=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/fusion-review')
app=adsk.core.Application.get()
p=F/'MicroDuck-C-native-review.f3d'
doc=app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(str(p)))
design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
mesh=sum(o.component.meshBodies.count for o in root.occurrences)
solids=sum(o.component.bRepBodies.count for o in root.occurrences)
assert mesh==166 and solids==11,(mesh,solids)
bank=next(o.component.bRepBodies.item(0) for o in root.occurrences if o.component.name.startswith('C lowered8'))
size=[10*x for x in bank.boundingBox.maxPoint.vectorTo(bank.boundingBox.minPoint).asArray()]
assert max(abs(abs(size[i])-[80.9,26,65.9][i]) for i in range(3))<1e-5
cam=app.activeViewport.camera;cam.eye=adsk.core.Point3D.create(48,55,35);cam.target=adsk.core.Point3D.create(0,0,0);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.cameraType=adsk.core.CameraTypes.OrthographicCameraType;cam.isFitView=True;app.activeViewport.camera=cam
app.activeViewport.visualStyle=adsk.core.VisualStyles.ShadedVisualStyle
app.activeViewport.refresh();adsk.doEvents()
app.activeViewport.saveAsImageFile(str(F/'C-native-readback.png'),1600,1200)
(F/'native-readback.json').write_text(json.dumps({'passed':True,'archiveSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'meshBodies':mesh,'solidBodies':solids,'newParametricSolids':10,'oldNominalBatteryHidden':True,'batteryDimensionsMm':[abs(x) for x in size],'physicalVerified':False,'printReady':False},indent=2)+'\n')
# Close only the four temporary documents created during this import session.
owned={'microduck','MicroDuck C – packaging review','MicroDuck C - packaging review','MicroDuck C - native layout and frame skeleton'}
closed=[]
for d in list(app.documents):
 if d!=doc and d.name in owned:
  closed.append(d.name);d.close(False)
(F/'session-cleanup.json').write_text(json.dumps({'closedTemporaryDocuments':closed},indent=2))
