"""Restore only native curved material removed by two historical Pi USB cuts."""
import os,json,hashlib,sys,types
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1','Use bounded resource guard'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parents[2];H=R/'head-redesign-20261008';U=H/'usb-access/usb-repair'
sys.path.insert(0,str(H/'gpio-audio-repair'));import precision_mesh as pm
c=types.SimpleNamespace(np=np,tm=tm,mf=mf)
paths={'native':H/'curved-head/community-curved-head-world.stl','current':H/'gpio-audio-repair/speaker-final-export/speaker-pilot-fix/cap-speaker-pilot-fixed-world.stl','oldReceiving':H/'curved-head/zero_w_usb_moulding-world.stl','spec':U/'positive-x225-service-opening-spec.json','spacer':H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json','basePose':H/'camera-ribbon-repair/positive-x225-pose.json','initialCutGenerator':H/'curved-head/build_mounts_and_paths.py','laterCutGenerator':U/'apply_usb_service_opening.py','exporter':H/'gpio-audio-repair/precision_mesh.py'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=pm.load(c,paths['native']);current=pm.load(c,paths['current']);oldmesh=tm.load(paths['oldReceiving'],force='mesh');lo,hi=oldmesh.bounds
join_margin=.02
oldcut=mf.Manifold.cube(hi-lo+1+2*join_margin).translate(lo-.5-join_margin)
spec=json.loads(paths['spec'].read_text());rot=np.column_stack([spec['widthAxis'],spec['heightAxis'],spec['axis']]);T=np.column_stack([rot,np.array(spec['cutStartMm'])+rot[:,2]*spec['cutLengthMm']/2]);newcut=mf.Manifold.cube([spec['cutWidthMm']+2*join_margin,spec['cutHeightMm']+2*join_margin,spec['cutLengthMm']+2*join_margin],True).transform(T)
selectors=(oldcut+newcut).as_original();sourcepatch=native^selectors;candidate=(current+sourcepatch).as_original();fill=candidate-current
print('join diagnostic',candidate.status(),[x.volume()for x in candidate.decompose()],flush=True)
assert candidate.status()==mf.Error.NoError and len(candidate.decompose())==1
out=D/'head-cap-roof-restored-candidate-world.stl';io=pm.export(c,candidate,out);rb=pm.load(c,out)
checks={'currentMaterialRemovedMm3':max(0,(current-rb).volume()),'newMaterialOutsideNativeMm3':max(0,((rb-current)-native).volume()),'newMaterialOutsideHistoricalCutsPlusNativeOverlapRimMm3':max(0,((rb-current)-selectors).volume()),'missingRequiredNativePatchMm3':max(0,(sourcepatch-rb).volume())}
assert all(v<1e-5 for v in checks.values()),checks
patchout=D/'native-roof-reconstruction-patch-world.stl';patchio=pm.export(c,sourcepatch,patchout)
sp=json.loads(paths['spacer'].read_text());po=json.loads(paths['basePose'].read_text());shoulder=np.array(po['usbShoulderWorldMm'])+sp['translationFromPositiveX225Mm'];axis=rot[:,2]
plug=mf.Manifold.cube([8,18,25],True).transform(np.column_stack([rot,shoulder+axis*12.5]));conflict=rb^plug
report={'status':'GEOMETRIC_RESTORATION_CANDIDATE_NOT_WIRED_ASSEMBLY_ACCEPTANCE','sourceHashes':{str(p):sha(p)for p in paths.values()},'scriptSha256':sha(Path(__file__)),'output':str(out),'outputSha256':sha(out),'coordinates':'unchanged head/guide world mm; no scale or transform','restoredPatch':{'path':str(patchout),'sha256':sha(patchout),'solidIsNativeReconstructionPatchNotSeparatePrint':True,'addedDeltaVolumeMm3':fill.volume(),'patchVolumeMm3':sourcepatch.volume(),'boundsMm':list(fill.bounding_box()),'bodies':len(fill.decompose()),'export':patchio},'cap':{'volumeMm3':rb.volume(),'closedBodies':len(rb.decompose()),'export':io},'checks':checks,'kept':['all original current cap material including internal posts and speaker pilots','rear OpenRB service aperture','all geometry outside the two recorded Pi USB cutter volumes'],'removedOpenings':['historical axis-aligned Pi USB receiving+0.5 cut','later positive-X2.25 pose-bound9x19 Pi USB sweep'], 'cutDefinitions':{'nativeOverlapRimMm':join_margin,'oldBoundsMm':[list(lo-.5),list(hi+.5)],'laterSpec':str(paths['spec'])},'piUSB':{'outwardAxisWorld':axis.tolist(),'receivingShoulderWorldMm':shoulder.tolist(),'shoulderIsOfficialSocketDatum':False,'receivingDimensionsMm':[25,18,8],'vendorDimensionsVerified':False,'seatedReceivingOverlapWithRestoredCapMm3':max(0,conflict.volume()),'meaning':'negative model case retained; not a verified physical connector collision'},'physicalFitVerified':False,'wiringAccepted':False,'printRelease':False,'remaining':'Check actual Pi USB connector boundary and routing before accepting roof for connected assembly; moving only the flexible tail does not change the upward-facing seated body.'}
(D/'roof-restoration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'output':str(out),'addedMm3':fill.volume(),'checks':checks,'cap':report['cap'],'plugReceivingOverlapMm3':report['piUSB']['seatedReceivingOverlapWithRestoredCapMm3']}))
