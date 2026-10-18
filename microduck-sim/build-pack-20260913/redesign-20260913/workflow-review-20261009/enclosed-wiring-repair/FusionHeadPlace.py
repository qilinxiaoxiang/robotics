import adsk.core,adsk.fusion,json,traceback
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout')
def matrix(T):
 a=[v for row in T for v in row]
 for i in [3,7,11]:a[i]/=10
 m=adsk.core.Matrix3D.create();assert m.setWithArray(a);return m
r={'status':'RUNNING','accepted':False}
try:
 app=adsk.core.Application.get();design=adsk.fusion.Design.cast(app.activeProduct);assert design.parentDocument.name=='MicroDuck head native packaging repair';root=design.rootComponent
 p=json.loads((D/'native-lanes-pose.json').read_text());design.activateRootComponent()
 for name,k in [('Pi Zero W populated group','piCurrentWorldDelta'),('OpenRB manufacturer native solids','openrbNativeToWorld')]:
  q=[root.occurrences.item(i)for i in range(root.occurrences.count)if root.occurrences.item(i).component.name==name];assert len(q)==1
  q[0].isGrounded=False;q[0].isGroundToParent=False;q[0].transform2=matrix(p[k])
  if design.snapshots.hasPendingSnapshot:design.snapshots.add()
 if design.snapshots.hasPendingSnapshot:design.snapshots.add()
 design.computeAll()
 r['actualTransforms']={root.occurrences.item(i).component.name:root.occurrences.item(i).transform2.asArray()for i in range(root.occurrences.count)}
 for name,k in [('Pi Zero W populated group','piCurrentWorldDelta'),('OpenRB manufacturer native solids','openrbNativeToWorld')]:
  expected=matrix(p[k]).asArray();assert max(abs(a-b)for a,b in zip(expected,r['actualTransforms'][name]))<1e-6,('Pose did not persist',name)
 camera=app.activeViewport.camera;camera.eye=adsk.core.Point3D.create(15,-18,22);camera.target=adsk.core.Point3D.create(3,0,14);camera.upVector=adsk.core.Vector3D.create(0,0,1);camera.isFitView=True;app.activeViewport.camera=camera;app.activeViewport.refresh()
 app.activeViewport.saveAsImageFile(str(D/'native-lanes-view.png'),1440,1000)
 r['status']='POSE_APPLIED_FOR_CHECK'
except Exception:r.update(status='FAILED',error=traceback.format_exc())
finally:(D/'native-lanes-readback.json').write_text(json.dumps(r,indent=2))
