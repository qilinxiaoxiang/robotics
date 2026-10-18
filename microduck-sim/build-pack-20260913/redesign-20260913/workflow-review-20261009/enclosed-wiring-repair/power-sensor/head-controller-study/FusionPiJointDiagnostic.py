"""Move existing68 Pi parts and MicroB as one rigid diagnostic; no new imports/mounts.
Python.Run entrypoint. The owned straight plugs still fail; this is not accepted head CAD.
"""
import adsk.core,adsk.fusion
from pathlib import Path
import json,hashlib,traceback,datetime,uuid
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study')
SPEC_SHA='2401354cb2101fbb0b2b2a216ec621def0a053ea280b9b42ad168d9b65287ecb'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mat(T):
 a=[float(x)for row in T for x in row]
 for i in (3,7,11):a[i]/=10
 m=adsk.core.Matrix3D.create();assert m.setWithArray(a);return m
def mesh_bounds(occ):
 lo=[float('inf')]*3;hi=[-float('inf')]*3;nodes=0
 assert occ.component.occurrences.count==0,'Expected a direct mesh reference, not nested assembly'
 for body in occ.component.meshBodies:
  for q in body.displayMesh.nodeCoordinates:
   p=q.copy();p.transformBy(occ.transform2);v=[p.x*10,p.y*10,p.z*10];nodes+=1
   for i in range(3):lo[i]=min(lo[i],v[i]);hi[i]=max(hi[i],v[i])
 assert nodes>0,'No actual displayed source nodes';return [lo,hi],nodes

def run(context):
 out=D/('pi-joint-native-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:5]);out.mkdir()
 r={'status':'RUNNING','accepted':False,'wholeHeadAccepted':False,'printReady':False,'scriptSha256':sha(D/'FusionPiJointDiagnostic.py'),'records':[]}
 try:
  spec=D/'pi-joint-diagnostic-spec.json';assert sha(spec)==SPEC_SHA;cfg=json.loads(spec.read_text())
  for p,h in cfg['sourceBindings'].items():assert sha(p)==h,('Source binding changed',p)
  for q in cfg['parts']:assert sha(q['file'])==q['sha256'],q['file']
  app=adsk.core.Application.get();docs=[d for d in app.documents if d.name==cfg['targetDocumentName']];assert len(docs)==1,'Exact existing diagnostic document must be open'
  docs[0].activate();design=adsk.fusion.Design.cast(app.activeProduct);design.activateRootComponent();root=design.rootComponent
  controllers=[o for o in root.occurrences if o.component.attributes.itemByName('MicroDuck','originalHeadOpenRBDiagnostic')];assert len(controllers)==1,'Native original OpenRB diagnostic must already exist; no imports here'
  controllers[0].isLightBulbOn=True
  selected=[]
  for q in cfg['parts']:
   found=[o for o in root.occurrences if o.component.name==q['id']];assert len(found)==1,('Missing/duplicate source reference',q['id'],len(found))
   o=found[0];a=o.component.attributes.itemByName('MicroDuck','source');assert a,('Missing source attribute',q['id']);meta=json.loads(a.value);assert meta['file']==q['file'] and meta['sha256']==q['sha256'],('Mismatched source geometry',q['id']);selected.append((q,o))
  assert len(selected)==69 and sum(q['id'].startswith('REFERENCE Pi current')for q,o in selected)==68
  # All targets/source bindings preflight before modifying any occurrence. Exact target transforms are resumable.
  for q,o in selected:
   o.transform2=mat(q['worldTransform']);o.isLightBulbOn=True;o.component.attributes.add('MicroDuck','piJointDiagnostic',json.dumps({'specSha256':SPEC_SHA,'originalSourceToWorld':q['sourceWorldTransform'],'currentSourceToWorld':q['worldTransform'],'accepted':False}))
  design.computeAll();maximum=0
  for q,o in selected:
   b,n=mesh_bounds(o);err=max(abs(b[i][k]-q['expectedFinalBoundsMm'][i][k])for i in range(2)for k in range(3));maximum=max(maximum,err);assert err<.002,('World source bounds mismatch',q['id'],err,b,q['expectedFinalBoundsMm']);r['records'].append({'name':q['id'],'meshNodes':n,'worldBoundsMm':b,'maximumErrorMm':err,'sourceToWorld':q['worldTransform']})
  if design.designType==adsk.fusion.DesignTypes.ParametricDesignType and design.snapshots.hasPendingSnapshot:design.snapshots.add()
  archive=out/'diagnostic-Pi-front-inclined-original-OpenRB.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
  r.update(status='DIAGNOSTIC_PI_RIGID_GROUP_REPOSITIONED_USB_NOT_ACCEPTED',documentName=docs[0].name,piPartCount=68,microBReceiverCount=1,maximumWorldBoundErrorMm=maximum,specSha256=SPEC_SHA,archive=str(archive),archiveSha256=sha(archive),knownFailures=['MicroB25mm receiver still crosses original closed roof','Original OpenRB full USB-C straight body crosses rear wall','Historical SC0727+4472 hypothetical47.9x20x12 A coupler is unplaced; SC0727 availability unconfirmed','Existing old Pi/amp mounting features are not changed or accepted at new pose'],nativeMountsModified=False,controllerReimported=False)
 except Exception:r.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
 finally:
  p=out/'native-readback.json';p.write_text(json.dumps(r,indent=2)+'\n');(D/'fusion-pi-joint-last-run.json').write_text(json.dumps({'report':str(p),'status':r['status']},indent=2)+'\n')
run(None)
