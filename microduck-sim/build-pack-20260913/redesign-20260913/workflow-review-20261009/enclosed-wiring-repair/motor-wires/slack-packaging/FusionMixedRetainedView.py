import adsk.core,adsk.fusion,json,traceback,hashlib
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires/slack-packaging');r={}
try:
 app=adsk.core.Application.get();doc=next(d for d in app.documents if 'COMPLETE RIGHT LEG' in d.name);doc.activate();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
 a=design.appearances.itemByName('Leg harness amber') or design.appearances.add('Leg harness amber');a.color=adsk.core.Color.create(197,148,44,255)
 for occ in root.occurrences:
  if occ.component.name.startswith('joint_') or occ.component.name.startswith('hip_') or 'wire' in occ.component.name.lower():
   for b in occ.component.bRepBodies:b.appearance=a
 cam=app.activeViewport.camera;cam.eye=adsk.core.Point3D.create(25,-40,17);cam.target=adsk.core.Point3D.create(0,-4,-3.5);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.isFitView=False;cam.isSmoothTransition=False;cam.viewExtents=25;app.activeViewport.camera=cam;app.activeViewport.refresh();p=D/'complete-right-leg-mixed-retained.png';assert app.activeViewport.saveAsImageFile(str(p),1440,1000);r={'image':str(p),'scope':'Four original-length editable native cable routes, five native motor assemblies and source printed references; physical motion and whole-robot harness separate.'}
except Exception:r['error']=traceback.format_exc()
(D/'native-mixed-view.json').write_text(json.dumps(r,indent=2))
