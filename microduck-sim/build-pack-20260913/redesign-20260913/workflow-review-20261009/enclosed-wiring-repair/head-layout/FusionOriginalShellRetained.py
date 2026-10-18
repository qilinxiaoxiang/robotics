"""Use native BRep for original closed shell retention; avoid independent STL re-tessellation slivers."""
import adsk.core,adsk.fusion,json,traceback,hashlib
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout')
r={'passed':False,'scope':'Original crown and rear material retained in current native cap; whole populated closure is separate.'}
try:
 app=adsk.core.Application.get();doc=next(d for d in app.documents if d.name=='MicroDuck Pi roof mounts native study');doc.activate();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
 original=next(o for o in root.occurrences if o.component.name=='Exact original roof stop - preserve exterior').component.bRepBodies.item(0)
 current=next(o for o in root.occurrences if o.component.name=='Closed cap with integral Pi mounting bosses').component.bRepBodies.item(0)
 mgr=adsk.fusion.TemporaryBRepManager.get();copy=mgr.copy(original);r['originalVolumeMm3']=original.volume*1000;r['currentVolumeMm3']=current.volume*1000
 ok=mgr.booleanOperation(copy,current,adsk.fusion.BooleanTypes.DifferenceBooleanType);r['booleanSucceeded']=ok
 if ok:
  r['missingOriginalMaterialMm3']=copy.volume*1000 if copy.isValid else 0
  box=copy.preciseBoundingBox if copy.isValid else None
  r['removedMaterialBoundsMm']=[[v*10 for v in box.minPoint.asArray()],[v*10 for v in box.maxPoint.asArray()]] if box else None
  r['remainingFaces']=copy.faces.count if copy.isValid else 0
  r['passed']=r['missingOriginalMaterialMm3']<1e-6
 else:r['error']='Native Boolean did not establish subtraction result.'
except Exception:r['error']=traceback.format_exc()
r['scriptSha256']=hashlib.sha256((D/'FusionOriginalShellRetained.py').read_bytes()).hexdigest();(D/'native-shell-retained.json').write_text(json.dumps(r,indent=2)+'\n')
