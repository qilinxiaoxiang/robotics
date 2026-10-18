import adsk.core,adsk.fusion,json,hashlib
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/ankle-wires')
q=json.loads((D/'fusion-ankle-last-run.json').read_text());rp=Path(q['report']);r=json.loads(rp.read_text());assert r['status']=='NATIVE_CREATED_REVIEW_REQUIRED'
app=adsk.core.Application.get();assert app.activeDocument.name==r['documentName'];design=adsk.fusion.Design.cast(app.activeProduct)
a=design.appearances.itemByName('MicroDuck cable amber')
if not a:a=design.appearances.add('MicroDuck cable amber');a.color=adsk.core.Color.create(210,135,30,255);a.roughness=.65
for i in range(design.rootComponent.occurrences.count):
 o=design.rootComponent.occurrences.item(i)
 if 'native 180 mm' in o.component.name:
  for j in range(o.component.bRepBodies.count):o.component.bRepBodies.item(j).appearance=a
cam=app.activeViewport.camera;cam.eye=adsk.core.Point3D.create(-30,-30,18);cam.target=adsk.core.Point3D.create(-4,0,-5);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.cameraType=adsk.core.CameraTypes.OrthographicCameraType;cam.isFitView=True;app.activeViewport.camera=cam;app.activeViewport.visualStyle=adsk.core.VisualStyles.ShadedVisualStyle;app.activeViewport.refresh()
p=rp.parent/'ankle-native-assembly.png';assert app.activeViewport.saveAsImageFile(str(p),1440,1000);assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(r['archive']));r.update(image=str(p),archiveSha256=hashlib.sha256(Path(r['archive']).read_bytes()).hexdigest());rp.write_text(json.dumps(r,indent=2))
