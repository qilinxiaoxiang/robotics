from pathlib import Path
O=Path(__file__).resolve().parent
exec((O/'check_one_pose.py').read_text().split('Tp=')[0])
N=O/'positive-y13-native';receipt=read(N/'native-readback.json');assert receipt['status']=='NATIVE_AMP_Y13_SKETCHES_UPDATED_PENDING_DIFFERENCE_CHECK'
for f in receipt['exports']:assert sha(f['file'])==f['sha256']
positive=read(O/'positive-y13-check.json');negative=read(O/'positive-y0-check.json');assert positive['passed'] and not negative['passed'];assert any(x['fixed']=='REFERENCE MicroB photo receiving' and x['intersectionMm3']>190 for x in negative['hits'])
amp=load(O/'amplifier-positive-y13-world.stl');cap=load(N/'closed-cap-Pi-audio-positive-y13-world.stl');oldcap=load(O/'native/closed-cap-Pi-audio-mounts-world.stl');added=cap-oldcap;removed=oldcap-cap;checks=[]
def test(target,s,obs,part,plane=False):
 q=s^obs;v=max(0,q.volume());checks.append({'target':target,'fixed':part,'volumeMm3':v,'intentionalFinalBoardSeatPlane':bool(plane and v<1e-4)})
for row in positive['inventory']:
 if row['id']=='current_cap':
  test('amp',amp,cap,'current_cap',True);continue
 assert sha(row['file'])==row['sha256'];obs=load(row['file']).transform(np.array(row['worldTransform'])[:3]);test('amp',amp,obs,row['id']);test('new_native_cap_material',added,obs,row['id']);del obs;gc.collect()
test('new_native_cap_material',added,amp,'amp',True)
fail=[x for x in checks if x['volumeMm3']>1e-7 and not x['intentionalFinalBoardSeatPlane']];out={'status':'PASSED_LOCAL_CURRENT_AMP_AND_INTERFACE'if not fail else'FAILED_LOCAL_CURRENT_AMP_AND_INTERFACE','passed':not fail,'currentLayoutAcceptedScope':'Relocated amplifier and modified two roof boss/pilot interfaces against one full explicit current rigid inventory; physical and whole head closure excluded.','wholeHeadAccepted':False,'physicalFitVerified':False,'checks':checks,'failures':fail,'ampPairsExpected':89,'ampPairsCompleted':sum(x['target']=='amp' for x in checks),'newMaterialPairsExpected':89,'newMaterialPairsCompleted':sum(x['target']=='new_native_cap_material' for x in checks),'ownerSelfPairExcluded':'Added cap material against its owning cap is self geometry; replaced with its mating amp interface. All other current rigid parts remain.','nativeNewMaterialMm3':added.volume(),'nativeRemovedMaterialMm3':removed.volume(),'negativeControl':{'file':str(O/'positive-y0-check.json'),'ampMicroBCollisionMm3':next(x['intersectionMm3']for x in negative['hits']if x['fixed']=='REFERENCE MicroB photo receiving')},'sourceHashes':hashes,'nativeReceiptSha256':sha(N/'native-readback.json')};(N/'local-acceptance.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['status','ampPairsCompleted','newMaterialPairsCompleted','failures','nativeNewMaterialMm3','nativeRemovedMaterialMm3']},indent=2))
