from pathlib import Path
import json,base64,hashlib,numpy as np,trimesh,manifold3d as mf
from scipy.spatial.transform import Rotation
R=Path(__file__).resolve().parent;G=R.parent/'leg-guide-20261006';data=json.loads((G/'full-build-data.json').read_text());rows={p['key']:p for p in data['parts']};M=json.loads((R/'candidate-manifest.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def from_mesh(m):
 a=mf.Manifold(mf.Mesh(np.array(m.vertices,dtype=np.float32),np.array(m.faces,dtype=np.uint32)));assert a.status()==mf.Error.NoError;return a

def source(k,T):
 p=rows[k];m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),dtype='<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),dtype='<u4').reshape(-1,3),process=True).apply_transform(np.linalg.inv(T));return from_mesh(m)
def stl(side,name):return from_mesh(trimesh.load(R/'STL'/f'{side}-{name}-local.stl',force='mesh',process=True))
def overlaps(moving,fixed,d):return {m+'--'+f:max(0.,float((a.translate(d)^b).volume())) for m,a in moving.items() for f,b in fixed.items()}
report={'scope':'Own finite actual-solid discrimination; independent acceptance is separate. No physical fit or strength validation.','sourceHashes':M['sourceHashes'],'manifestSha256':sha(R/'candidate-manifest.json'),'scriptSha256':sha(__file__),'sides':{}}
for side in ['left','right']:
 s=M['sides'][side];T=np.array(s['frameWorld']);left=side=='left';lower=source('lower' if left else 'right_lower',T);motor=source('motor6' if left else 'motor1',T);old=source('ankle' if left else 'right_ankle',T);oldring=source('smallring' if left else 'right_smallring',T);foot=source('foot' if left else 'right_foot',T);washer=source('washer6' if left else 'washer1',T);base=stl(side,'base');cap=stl(side,'cheek');ring=stl(side,'sleeve');candidate=base+cap;extra=candidate-old
 packet={};baseline={};caproute={};slip={};footroute={}
 for d in np.linspace(30,0,121):
  packet[str(float(d))]=overlaps({'lower':lower,'motor':motor,'newSleeve':ring,'washer':washer},{'newBase':base},[0,float(d),0]);baseline[str(float(d))]=overlaps({'lower':lower,'motor':motor,'oldSleeve':oldring},{'oldAnkle':old},[0,float(d),0])
 for d in np.linspace(12,0,49):
  caproute[str(float(d))]=overlaps({'removableSide':cap},{'newBase':base,'lower':lower,'motor':motor,'newSleeve':ring},[0,0,float(d)])
  slip[str(float(d))]=overlaps({'newSleeve':ring},{'lower':lower},[0,0,float(d)])
 for d in np.linspace(32,0,129):footroute[str(float(d))]=overlaps({'foot':foot},{'addedCandidate':extra},[0,-float(d),0])
 maxval=lambda q:max(v for p in q.values() for v in p.values())
 assert maxval(baseline)>.02
 assert maxval(caproute)<1e-5 and maxval(slip)<1e-5 and maxval(footroute)<1e-5
 # Isolate unchanged right nominal mating-face contact instead of claiming clear.
 allowedpacket=.00001 if left else .138;assert maxval(packet)<allowedpacket
 screws=[];fastener_checks=[];Ry=Rotation.from_euler('x',-90,degrees=True).as_matrix()
 for x in [-12.,12.]:
  axis=lambda rad,start,end:mf.Manifold.cylinder(end-start,rad,rad,96).transform(np.c_[Ry,[x,start,4.5]])
  shaft=axis(1,-2,6);head=axis(2,6,7.72);tool=axis(1.75,7.72,22.72);screws.append(shaft+head)
  host=axis(1.4,-2,1.5)-axis(.8,-2,1.5);seat=axis(2.,5.9,6)-axis(1.15,5.9,6)
  tests={'headVsFootMm3':max(0.,(head^foot).volume()),'headVsCapMm3':max(0.,(head^cap).volume()),'headVsBaseMm3':max(0.,(head^base).volume()),'driverVsAllMm3':sum(max(0.,(tool^a).volume()) for a in [base,cap,foot,lower,motor]),'missingContinuousPilotHostMm3':max(0.,(host-base).volume()),'missingHeadSeatAnnulusMm3':max(0.,(seat-cap).volume())}
  assert max(tests.values())<1e-5,(side,x,tests);fastener_checks.append({'xLocal':x,**tests})
 sweep=[]
 for degree in range(-90,91):
  rt=np.c_[Rotation.from_euler('z',degree,degrees=True).as_matrix(),[0,0,0]];moving=extra.transform(rt);sv=(screws[0]+screws[1]).transform(rt);p={'degree':degree,'addedVsLowerMm3':max(0.,(moving^lower).volume()),'addedVsFullMotorMm3':max(0.,(moving^motor).volume()),'newScrewsVsLowerMm3':max(0.,(sv^lower).volume()),'newScrewsVsFullMotorMm3':max(0.,(sv^motor).volume())};assert max(v for k,v in p.items() if k!='degree')<1e-5,(side,p);sweep.append(p)
 stats={'baselineBlockedPackageMaximumOverlapMm3':maxval(baseline),'candidatePackageMaximumOverlapMm3':maxval(packet),'candidateCapMaximumOverlapMm3':maxval(caproute),'newSleeveSlipMaximumOverlapMm3':maxval(slip),'footApproachAgainstAddedMaterialMaximumOverlapMm3':maxval(footroute),'oldSleeveFinalLowerOverlapMm3':(oldring^lower).volume(),'newSleeveFinalLowerOverlapMm3':(ring^lower).volume(),'candidateAddedFootOverlapMm3':max(0.,(extra^foot).volume()),'oldAnkleFootOverlapMm3':(old^foot).volume(),'candidateAnkleFootOverlapMm3':(candidate^foot).volume()}
 report['sides'][side]={'stats':stats,'packageSamples':packet,'baselineSamples':baseline,'capSamples':caproute,'sleeveSamples':slip,'footApproachAddedObstacleSamples':footroute,'fastenerChecks':fastener_checks,'addedAndScrewRotationSamples':sweep,'rotationScope':'Only new material/new hardware checked here. Original foot/body collision limits require independent proper case-versus-horn separation; no ±90° full-joint clearance claim.','sourceNominalCaseContactRetained':not left}
 print(side,'CANDIDATE_FINITE_CHECK_PASS',stats,flush=True)
report['passed']=True;(R/'geometry-evidence.json').write_text(json.dumps(report,indent=2)+'\n');print('CANDIDATE_FINITE_GEOMETRY_CHECK_PASS')
