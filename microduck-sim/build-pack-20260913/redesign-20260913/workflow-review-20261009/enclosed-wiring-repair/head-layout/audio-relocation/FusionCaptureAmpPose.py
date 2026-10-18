"""Capture the already-authorized reference transform, then inspect real mesh nodes.
No geometry or sketch edits. Run only after the existing Y13 update completes.
"""
import adsk.core,adsk.fusion,json,hashlib,traceback
from pathlib import Path
O=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout/audio-relocation');N=O/'positive-y13-native';p=N/'native-readback.json';r=json.loads(p.read_text());report={'passed':False,'scriptSha256':hashlib.sha256((O/'FusionCaptureAmpPose.py').read_bytes()).hexdigest()}
try:
 assert r['status']=='NATIVE_AMP_Y13_SKETCHES_UPDATED_PENDING_DIFFERENCE_CHECK'
 app=adsk.core.Application.get();docs=[d for d in app.documents if d.name=='MicroDuck Pi roof mounts native study'];assert len(docs)==1;docs[0].activate();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent;a=next(o for o in root.occurrences if o.component.name=='REFERENCE current relocated amplifier and X1 terminal');T=a.transform2;report['initialOccurrenceTranslationCm']=T.translation.asArray();assert min(abs(T.translation.y),abs(T.translation.y-1.3))<1e-6
 if abs(T.translation.y-1.3)>1e-6:T.translation=adsk.core.Vector3D.create(T.translation.x,1.3,T.translation.z);a.transform2=T
 report['hadPendingSnapshot']=design.snapshots.hasPendingSnapshot
 if design.snapshots.hasPendingSnapshot:assert design.snapshots.add()
 assert design.computeAll();lo=[float('inf')]*3;hi=[-float('inf')]*3;count=0
 for mesh in a.component.meshBodies:
  for q in mesh.mesh.nodeCoordinates:
   z=q.copy();z.transformBy(a.transform2);v=[t*10 for t in z.asArray()];count+=1
   for i in range(3):lo[i]=min(lo[i],v[i]);hi[i]=max(hi[i],v[i])
 expected=json.loads((O/'positive-y13-check.json').read_text())['ampBoundsMm'];err=max(abs(v-w)for v,w in zip(lo+hi,expected));assert count>0 and err<1e-4,(lo,hi,expected,err)
 arc=next(x for x in r['exports']if x['file'].endswith('.f3d'));assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(arc['file']));arc['sha256']=hashlib.sha256(Path(arc['file']).read_bytes()).hexdigest();report.update(passed=True,nodeCount=count,actualWorldBoundsMm=[lo,hi],expectedWorldBoundsMm=expected,maxBoundErrorMm=err,captured=not design.snapshots.hasPendingSnapshot,archiveSha256=arc['sha256']);r['ampReferenceReadback']=report;p.write_text(json.dumps(r,indent=2)+'\n')
except Exception:report['error']=traceback.format_exc()
finally:(N/'amp-reference-readback.json').write_text(json.dumps(report,indent=2)+'\n')
