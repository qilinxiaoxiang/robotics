"""Bind a captured Fusion reference without rerunning unchanged solid checks."""
from pathlib import Path
import json,hashlib,copy
O=Path(__file__).resolve().parent;N=O/'positive-y13-native';S=next(p for p in O.parents if p.name=='microduck-sim');Q=O.parent/'current-ffc-native'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def save(p,r):Path(p).write_text(json.dumps(r,indent=2)+'\n')
oldpath=N/'native-readback-before-reference-capture.json';newpath=N/'native-readback.json';rp=N/'amp-reference-readback.json';a=read(oldpath);b=read(newpath);c=read(rp)
assert c['passed'] and c['captured'] and c['nodeCount']==7507 and c['maxBoundErrorMm']<1e-4
assert c['scriptSha256']==sha(O/'FusionCaptureAmpPose.py')
assert b['ampReferenceReadback']==c
assert set(b)-set(a)=={'ampReferenceReadback'}
assert all(a[k]==b[k] for k in a if k!='exports')
oldfiles={r['file']:r['sha256']for r in a['exports']};newfiles={r['file']:r['sha256']for r in b['exports']};assert oldfiles.keys()==newfiles.keys()
changes=[];geometry=[]
for p,h in newfiles.items():
 assert sha(p)==h
 if Path(p).suffix=='.f3d':assert h==c['archiveSha256'];changes.append({'file':p,'beforeSha256':oldfiles[p],'afterSha256':h})
 else:assert oldfiles[p]==h;geometry.append({'file':p,'sha256':h,'unchanged':True})
assert len(changes)==1
ac=N/'local-acceptance.json';backup=N/'local-acceptance-before-reference-capture.json'
if not backup.exists():backup.write_bytes(ac.read_bytes())
old=read(backup);assert old['passed'] and old['nativeReceiptSha256']==sha(oldpath)
for p,h in old['sourceHashes'].items():
 assert h==(sha(oldpath) if Path(p)==newpath else sha(p)),p
lineage={'status':'REFERENCE_CAPTURE_ONLY_GEOMETRY_UNCHANGED','passed':True,'noGeometryRerun':True,'geometryReceiptsReusedExactly':True,'previousAcceptance':{'file':str(backup),'sha256':sha(backup)},'nativeBefore':{'file':str(oldpath),'sha256':sha(oldpath)},'nativeAfter':{'file':str(newpath),'sha256':sha(newpath)},'referenceReadback':{'file':str(rp),'sha256':sha(rp)},'onlyChangedNativeReceiptFields':['exports[F3D].sha256','ampReferenceReadback'],'archiveChange':changes[0],'unchangedGeometryExports':geometry,'actualReferenceNodeCount':c['nodeCount'],'maximumWorldBoundErrorMm':c['maxBoundErrorMm'],'scriptSha256':sha(__file__),'limitations':'Local amplifier and its two support/pilot interfaces only. OpenRB head placement, complete FFC/wired closure, physical fit and commissioning remain unresolved.'}
lp=N/'reference-capture-lineage.json';save(lp,lineage)
r=copy.deepcopy(old);r['nativeReceiptSha256']=sha(newpath);r['sourceHashes'][str(newpath)]=sha(newpath);r['sourceHashes'][str(lp)]=sha(lp);r['sourceHashes'][str(rp)]=sha(rp);r['referenceCapture']={'passed':True,'lineageFile':str(lp),'lineageSha256':sha(lp),'actualNodeCount':c['nodeCount'],'maximumWorldBoundErrorMm':c['maxBoundErrorMm'],'archiveSha256':c['archiveSha256'],'geometryChecksRerun':False};r['wholeHeadPending']=['Actual OpenRB head placement and adjacent rigid connectors','Complete 200 mm FFC and other flexible wiring','Populated head closure and physical fit'];save(ac,r)
ip=N/'current-rigid-inventory.json';inv=read(ip);inv['sourceBindings'][str(ac)]=sha(ac);inv['sourceBindings'][str(lp)]=sha(lp);save(ip,inv)
sp=Q/'current-state.json';state=read(sp);state['nativeAmpReferenceCapturePending']=False;state['nativeAmpReferenceCapture']={'file':str(rp),'sha256':sha(rp),'passed':True};save(sp,state)
context=S/'PROJECT-CONTEXT.json';ct=read(context);before=copy.deepcopy(ct);head=ct['current_build']['staged_review_20261009']['activeRepair']['headAudioLocal'];rootrel=str(O.relative_to(S));head.update(status='PASSED_LOCAL_AMP_Y13_INTERFACE_AND_NATIVE_REFERENCE_READBACK',currentRepair='Amplifier +Y13 and its two native support/pilot interfaces passed 178 affected pairs against the exact 89-neighbor local inventory, including the separately registered MicroB receiving model. Native reference snapshot captured and 7,507 actual mesh nodes read back within 2.18e-6 mm of the checked amplifier pose. No geometry rerun after reference capture.',currentLocalAcceptance=rootrel+'/positive-y13-native/local-acceptance.json',currentLocalAcceptanceSha256=sha(ac),currentRigidInventory=rootrel+'/positive-y13-native/current-rigid-inventory.json',currentRigidInventorySha256=sha(ip),referenceCaptureLineage=rootrel+'/positive-y13-native/reference-capture-lineage.json',referenceCaptureLineageSha256=sha(lp),nativeArchive=rootrel+'/positive-y13-native/MicroDuck-closed-head-Pi-audio-positive-y13.f3d',nativeArchiveSha256=c['archiveSha256'],priorFailureRetained=rootrel+'/positive-y0-check.json',wholeHeadAccepted=False,wholeHeadPending=['OpenRB remains required in the head; its placement and full rigid plugs are not accepted by this local receipt.','Complete camera ribbon and other flexible wiring, populated closure, physical fit and commissioning remain pending.'],physicalFitVerified=False,printReleaseChanged=False)
after=copy.deepcopy(ct);after['current_build']['staged_review_20261009']['activeRepair']['headAudioLocal']=before['current_build']['staged_review_20261009']['activeRepair']['headAudioLocal'];assert after==before;save(context,ct)
for p,h in r['sourceHashes'].items():assert sha(p)==h,p
for p,h in inv['sourceBindings'].items():assert sha(p)==h,p
print(json.dumps({'localAcceptanceSha256':sha(ac),'lineageSha256':sha(lp),'inventorySha256':sha(ip),'nativeArchiveSha256':c['archiveSha256'],'geometryRerun':False,'contextScope':'current_build.staged_review_20261009.activeRepair.headAudioLocal'},indent=2))
