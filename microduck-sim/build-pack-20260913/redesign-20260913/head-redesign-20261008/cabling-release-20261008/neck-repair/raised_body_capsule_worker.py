"""Strict round receiving proof, one source obstacle and one pose per worker."""
import argparse,base64,json,math
from pathlib import Path
import raised_body_worker as w
from segment_capsule_clearance import check
w.core.guard()
import numpy as np,manifold3d as mf
D=Path(__file__).resolve().parent;OUT=D/'raised-body-capsule';ap=argparse.ArgumentParser();ap.add_argument('--pose',type=int,required=True);ap.add_argument('--key',required=True);o=ap.parse_args();plan=w.core.current();w.passed_self();item=next(x for x in plan['obstacles'] if x['key']==o.key)
rp=Path(item['intrinsicSolidValidationReceipt']);assert w.core.sha(rp)==item['intrinsicSolidValidationReceiptHash'];proof=json.loads(rp.read_text());assert proof['inputObstacleWatertight'] and proof['inputObstacleVolumePositive'] and proof['obstacleSha256']==item['sha256'];assert w.core.sha(item['path'])==item['sha256']
d=json.loads(Path(item['path']).read_text());v=np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3);solid=mf.Manifold(mf.Mesh(v.copy(),f.copy()))
if solid.status()!=mf.Error.NoError or solid.volume()<=0:
 import trimesh
 npth=rp.parent.parent/'normalized-inputs'/f'{o.key}.ply';sv=proof['sourceValidation'];assert sv['topologyNormalization'] and w.core.sha(npth)==sv['normalizedInputSha256']
 normalized=trimesh.load(npth,force='mesh',process=False);assert normalized.is_watertight and normalized.is_volume
 solid=mf.Manifold(mf.Mesh(np.asarray(normalized.vertices,np.float32),np.asarray(normalized.faces,np.uint32)))
assert solid.status()==mf.Error.NoError and solid.volume()>0
row,g=w.geom(o.pose);assert g and g['minimumCenterRadiusMm']>=9
q={k:row['jointDegrees'].get(k,0) for k in w.core.ORDER[:w.core.BODIES[d['body']]]};origin=np.array(w.moved([0,0,0],q));R=np.array([w.moved(a,q,True) for a in [[1,0,0],[0,1,0],[0,0,1]]]).T;T=np.column_stack([R,origin]);solid=solid.transform(T)
A=math.radians(abs(135+row['jointDegrees'].get('head_yaw',0)/2)+sum(abs(x) for x in row['jointDegrees'].values()));B=math.radians(20);pi=math.pi
M=[1,B*pi,(B+B*B)*pi**2,(B+3*B*B+B**3)*pi**3,(B+7*B*B+6*B**3+B**4)*pi**4]
fourth=sum(math.comb(4,k)*A**(4-k)*M[k] for k in range(5));integration_bound=60*fourth/(180*240**4);assert integration_bound<.0001
sagitta=9-math.sqrt(81-.25**2)+.0001
r=check(g['points'],3.5,sagitta,solid,source_evidence={'watertight':True,'positiveVolume':True,'sourceSha256':item['sha256'],'intrinsicValidityReceiptSha256':item['intrinsicSolidValidationReceiptHash']})
r.update(pose=o.pose,key=o.key,planHash=w.core.sha(w.OUT/'plan.json'),jointDegrees=row['jointDegrees'],nativeBaselineBlocked=bool(row['nativeShellOriginalBottomIntersectionsMm3']),body=d['body'],bodyTransform=T.tolist(),analyticLengthMm=g['analyticLengthMm'],simpsonEndpointErrorBoundMm=integration_bound,unitTangentFourthDerivativeNormBound=fourth,centerlineErrorBound='Max arclength step0.5mm and minimum analytic center radius9mm give9−sqrt(81−0.25²). Added0.0001mm exceeds the per-pose composite-Simpson bound L*M4/(180*n^4), n240. M4 follows Leibniz on constant-rate rotation matrices and chain-rule bounds M_k for the20deg*sin(pi*u) tilt; all rotation matrices have operator norm1.',sourceHashes={str(p):w.core.sha(p) for p in [Path(__file__),D/'segment_capsule_clearance.py',D/'raised_body_worker.py',D/'raised_body_family.py',w.OUT/'plan.json',rp,Path(item['path'])]})
w.core.save(OUT/f'{o.pose}__{o.key}.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['segments','sourceHashes']}));raise SystemExit(0 if r['passed'] else 2)
