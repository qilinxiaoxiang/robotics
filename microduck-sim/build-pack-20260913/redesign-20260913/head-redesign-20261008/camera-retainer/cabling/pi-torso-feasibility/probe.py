"""Finite principal-planeZeroW torsofit search, no source edits or mountingclaims."""
from pathlib import Path
import sys,json,hashlib,itertools
import numpy as np,trimesh,manifold3d as mf
from scipy.spatial import ConvexHull
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D.parent))
import conditional_u_route as c
C=c.C;G=c.G;H=c.H
center=np.array([68.11,-.0113773,131.0496]);B=np.array([[0,0,1],[1,0,0],[0,1,0]],float)
files={k:C/(k+'-world.stl') for k in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails','zero_w_usb_moulding']}
parts={'pi':c.dec('pi')}|{k:c.man(trimesh.load_mesh(p)) for k,p in files.items()};corekeys=[k for k in parts if k!='zero_w_usb_moulding'];vertices=np.concatenate([c.tri(parts[k]).vertices for k in corekeys]);local=(vertices-center)@B
allLocal=np.concatenate([(c.tri(o).vertices-center)@B for o in parts.values()])
shell=trimesh.util.concatenate([c.tri(c.dec(k)) for k in ['shell_left','shell_right']]);hull=ConvexHull(shell.vertices);A=hull.equations[:,:3];bb=hull.equations[:,3];shellbounds=shell.bounds
# Envelopeistheconvexhull ofexistingtorsoexteriors. This isONLYa generous
# candidatecontainmentbound,neverproofeverypointinsideisrealinteriorspace.
obs={}
for k,p in c.P.items():
 b=np.array(p['bounds'])
 if b[0,2]<42.1 and b[1,2]>.2 and b[1,0]>-63 and b[0,0]<40:obs[k]=c.dec(k)
obsunion=mf.Manifold.batch_boolean(list(obs.values()),mf.OpType.Add)
rotations=[]
for perm in itertools.permutations(range(3)):
 for signs in itertools.product([-1,1],repeat=3):
  R=np.eye(3)[:,perm]*np.array(signs)
  if np.linalg.det(R)>.5:rotations.append(R)
centers=[np.array([x,y,z],float) for x in [-14,-10,-6,-2,2] for y in [-16,-12,-8,-4,0,4,8,12,16] for z in [8,12,16,20,24,28,32,36,40]]
results=[];summary={};outside=0;examined=0;best=[]
for ri,R in enumerate(rotations):
 normalaxis=int(np.argmax(abs(R[:,2])));family=['YZ','XZ','XY'][normalaxis];familycount=summary.setdefault(family,{'posesTested':0,'outsideConvexTorsoEnvelope':0,'insideCandidates':0,'collisionFreeCore':0,'collisionFreeIncludingUsb':0})
 support=np.max((local@R.T)@A.T,axis=0)
 for pos in centers:
  examined+=1;familycount['posesTested']+=1
  if np.any(support+A@pos+bb>.01):outside+=1;familycount['outsideConvexTorsoEnvelope']+=1;continue
  familycount['insideCandidates']+=1;T=np.eye(4);T[:3,:3]=R@B.T;T[:3,3]=pos-T[:3,:3]@center
  moved={k:o.transform(T[:3]) for k,o in parts.items()};core=mf.Manifold.batch_boolean([moved[k] for k in corekeys],mf.OpType.Add);v=max(0,(core^obsunion).volume())
  hits={}
  for k,o in obs.items():
   vol=max(0,(core^o).volume())
   if vol>1e-5:hits[k]=vol
  usbHit={k:max(0,(moved['zero_w_usb_moulding']^o).volume()) for k,o in obs.items()};usbHit={k:v for k,v in usbHit.items() if v>1e-5}
  if not hits:familycount['collisionFreeCore']+=1
  if not hits and not usbHit:familycount['collisionFreeIncludingUsb']+=1
  piMouth=np.array([65.8,32.4886208,131.0496]);mouth=T[:3,:3]@piMouth+T[:3,3];cameraMouth=np.array([74.73,-.0913783,140.5766]);lb=float(np.linalg.norm(cameraMouth-mouth))+9.4
  row={'rotationIndex':ri,'plane':family,'centerWorldMm':pos.tolist(),'worldTransform':T.tolist(),'wholeCoreIntersectionUnionMm3':v,'coreCollisionsMm3':hits,'usbCollisionsMm3':usbHit,'piMouthWorldMm':mouth.tolist(),'straightCableLowerBoundIncludingAssumedContactsMm':lb,'coreClear':not bool(hits),'coreAndUsbClear':not bool(hits or usbHit)};results.append(row)
  best.append((v,ri,pos,T,core));best.sort(key=lambda r:r[0]);best=best[:3]
 print('plane',ri,family,'checked',examined,'inside',len(results),flush=True)
for i,b in enumerate(best):c.tri(b[4]).export(D/f'closest-rejected-core-{i+1}-world.stl')
report={'date':'2026-10-08','status':'NO_CLEAR_POSE_IN_FINITE_PRINCIPAL_PLANE_SCAN' if not any(r['coreAndUsbClear'] for r in results) else 'CLEAR_PLACEMENT_ONLY_REQUIRES_MOUNTS_AND_ROUTING','problemIds':['P0','P5','P6'],'scope':'WholeownedZeroW65x30referencePCB+components+40pinmale/femalehousing15mmreceivingenvelope+soldertails2mm; USBmoulding checked separately. No originalpartmodified.','region':'Existingtorsoexteriorconvexhull plus realinterferenceagainstallpartswhoseboundsintersecttorso. Convexhull isgeneroussuperset,notactualfree-spacecertificate.','orientationCount':len(rotations),'threePlanes':summary,'centerGrid':{'X':[-14,-10,-6,-2,2],'Y':[-16,-12,-8,-4,0,4,8,12,16],'Z':[8,12,16,20,24,28,32,36,40]},'totalPoses':examined,'outsideEnvelopeCount':outside,'insideCandidateCount':len(results),'obstacleKeys':list(obs),'insideCandidates':sorted(results,key=lambda r:r['wholeCoreIntersectionUnionMm3']),'electricalTopology':{'camera':'ExistingSC1892 200mm15to22 remains required','power':'Currentcontractistether20VtoDFR1202inoriginalbatterycavity,notaninstalledbattery. Regulator/support/fuse/IMUremainobstacles.','piPower':'Existingfour250mm22AWGheaderleads','imu':'Existing250mmextendedI2Cleads','USB':'ExistingSC0727 80mm +Adafruit4472 152mm toheadOpenRB; rerouteandjointserviceunvalidated.'},'cableBoundary':'Euclideanmouthdistance+9.4mmassumedinsertionsisalowerboundONLY; doesnotincludeobstaclebypass,3Dendnormalchanges,wideFFCtorsion,neckheadpitch/yaw/rollserviceorretention. No route released from this number.','mountingAcceptance':False,'routingAcceptance':False,'physicalFitVerified':False,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*files.values(),G/'full-build-data.json',H.parent/'design-contract.json',D/'probe.py']}}
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['status','totalPoses','insideCandidateCount','threePlanes']},indent=2))
