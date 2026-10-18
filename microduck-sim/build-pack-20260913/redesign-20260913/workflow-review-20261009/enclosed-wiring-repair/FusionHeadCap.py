import adsk.core,adsk.fusion,json,traceback
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout')
r={'status':'RUNNING','accepted':False}
try:
 app=adsk.core.Application.get();design=adsk.fusion.Design.cast(app.activeProduct);assert design.parentDocument.name=='MicroDuck head native packaging repair';root=design.rootComponent
 match=[root.occurrences.item(i)for i in range(root.occurrences.count)if root.occurrences.item(i).component.name=='Original closed cap native faceted solid'];assert len(match)<=1
 if match:occ=match[0]
 else:
  m=adsk.core.Matrix3D.create();m.setWithArray([0,-1,0,2.61,1,0,0,0,0,0,1,11.11146,0,0,0,1]);occ=root.occurrences.addNewComponent(m);occ.component.name='Original closed cap native faceted solid'
  assert app.importManager.importToTarget(app.importManager.createSTEPImportOptions(str(D/'sources/top-head-native.step')),occ.component)
 occ.component.opacity=.15
 archive=D/'MicroDuck-head-native-packaging.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
 r['status']='CLOSED_CAP_ADDED_FOR_FIT_CHECK';r['scope']='Original cap shell as packaging reference; mounting posts must be redesigned for adopted board positions.'
except Exception:r.update(status='FAILED',error=traceback.format_exc())
finally:(D/'fusion-cap-readback.json').write_text(json.dumps(r,indent=2))
