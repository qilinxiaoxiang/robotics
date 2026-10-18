"""One local constant-length yaw service loop, isolated source-obstacle checks.
No full-scene import, no head integration or print release.
"""
import argparse,json,math,base64,hashlib
from pathlib import Path
from rolling_loop_math import rolling_loop
from prepare_single_candidate import moved
import short_path_worker as core
D=Path(__file__).resolve().parent;H=D.parent.parent;OUT=D/'segmented-yaw-below';BASE=H/'usb-access/usb-repair/rigid-domain.json';OLD=D/'short-isolated/plan.json'
R=31.;SEPARATION=18.;CENTER=[26.,0.,94.5];HALF=math.radians(87);SAGITTA=9-math.sqrt(81-.125**2)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,r):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2)+'\n')
def route(i):
 row={'jointDegrees':{},'nativeShellOriginalBottomIntersectionsMm3':{}} if i==-1 else json.loads(BASE.read_text())['samples'][i];q=row['jointDegrees'];g=rolling_loop(CENTER,[0,0,1],[math.cos(math.radians(135)),math.sin(math.radians(135)),0],R,SEPARATION,HALF,math.radians(q.get('head_yaw',0)),.25);g['points']=[[v[0],v[1],2*CENTER[2]-v[2]] for v in g['points']];parent={k:q.get(k,0) for k in ['neck_pitch','head_pitch']};g['points']=[moved(p,parent) for p in g['points']];return row,g

def plan():
 old=json.loads(OLD.read_text());base=json.loads(BASE.read_text());obs=old['obstacles'];clear=[i for i,r in enumerate(base['samples']) if not r['nativeShellOriginalBottomIntersectionsMm3']]
 sources=[Path(__file__),BASE,OLD,D/'rolling_loop_math.py',D/'prepare_single_candidate.py',D/'short_path_worker.py',D/'segment_capsule_clearance.py']
 for x in obs:
  p=D/'short-isolated/pairs'/f'-1__{x["key"]}.json';x['intrinsicReceipt']=str(p);x['intrinsicReceiptHash']=sha(p);sources.append(p);sources.append(Path(x['path']))
 r={'accepted':False,'scope':'Only local yaw service loop, not full11-low-voltage-net path or motor/data branches. No cap, portal, fanout, guide retention or print acceptance.','joint':'head_yaw','parentBody':'neck_pitch','childBody':'yaw_roll_motion','centerNeutral':CENTER,'radiusMm':R,'radialAnchorPhaseDeg':135,'childPlaneNeutralZ':76.5,'bendTowardNegativeZ':True,'priorFailure':'Both anchors relocated belowheadbottom andjawsupport, Udownward; no structuralcut. Rear-side135phase avoidsneckmotorfront atpitch90. At yaw-170 the semicircle bulge enters motor14 near childY12 atphase-30; phase-45 moves entire bulge towardpositiveY by~7mm atsame R andlength. Low planeZ83.5 becomesworldX27.08 atpitch90 and sweepsneckmotor/link; raise lowerplaneZ97 so X40.58, fixedradius/length. Rear anchors let rolling motor14 sweep into upper loop at head_roll -10deg; route moved to front/positiveY side without added length.','planeSeparationMm':SEPARATION,'neutralHalfAngleDeg':87,'receivingODMm':7,'minimumCenterlineBendRadiusMm':9,'analyticLengthMm':2*R*HALF+math.pi*SEPARATION/2,'lengthFormula':'thetaJoin=C+q/2; R*(C+q/2)+R*(C-q/2)+pi*d/2=2RC+pi*d/2. Equal radii, parallel planes.','connectorTangents':'Parent +e_theta; child -rot(q)e_theta, fixed in respective rigid bodies. Bridge endpoints on each plane have no translation relative to their owner.','outerNeutralRadialReceivingBoundMm':math.hypot(R,SEPARATION/2)+3.5,'neutralZReceivingBoundMm':[73.0,98.0],'sourceHashes':{str(p):sha(p) for p in sources},'obstacles':obs,'nativeClearIndices':clear,'nativeBlockedIndices':[i for i in range(229) if i not in clear],'expectedSelfIndices':list(range(229)),'expectedPairs':[{'pose':i,'key':o['key']} for i in clear for o in obs]};save(OUT/'plan.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['obstacles','sourceHashes','expectedPairs','nativeClearIndices','nativeBlockedIndices','expectedSelfIndices']}))
def current():
 p=json.loads((OUT/'plan.json').read_text());assert all(sha(f)==h for f,h in p['sourceHashes'].items());return p

def self_all():
 p=current();rs=[]
 for i in p['expectedSelfIndices']:
  row,g=route(i);r=core.self_one(g['points']);r.update(pose=i,nativeBlocked=bool(row['nativeShellOriginalBottomIntersectionsMm3']),analyticLengthMm=g['analyticLengthMm'],chordLengthDeficitMm=g['analyticLengthMm']-g['polylineLengthMm']);save(OUT/'self'/f'{i}.json',r);rs.append(r)
  if not r['passed']:break
 r={'passed':len(rs)==229 and all(x['passed'] for x in rs),'expected':229,'completed':len(rs),'coverageComplete':len(rs)==229,'planHash':sha(OUT/'plan.json'),'maximumChordLengthDeficitMm':max(x['chordLengthDeficitMm'] for x in rs),'failures':[x for x in rs if not x['passed']],'receiptHashes':{str(x['pose']):sha(OUT/'self'/f'{x["pose"]}.json') for x in rs}};save(OUT/'self-summary.json',r);print(json.dumps({k:v for k,v in r.items() if k!='receiptHashes'}));return 0 if r['passed'] else 2

def obstacle(i,key):
 import numpy as np,manifold3d as mf
 from segment_capsule_clearance import check
 p=current();sr=json.loads((OUT/'self-summary.json').read_text());assert sr['passed'] and sr['coverageComplete'] and sr['planHash']==sha(OUT/'plan.json');item=next(x for x in p['obstacles'] if x['key']==key);proof=json.loads(Path(item['intrinsicReceipt']).read_text());assert proof['inputObstacleWatertight'] and proof['inputObstacleVolumePositive'];d=json.loads(Path(item['path']).read_text());v=np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3);solid=mf.Manifold(mf.Mesh(v.copy(),f.copy()));normal=None
 if solid.status()!=mf.Error.NoError or solid.volume()<=0:
  import trimesh
  normal=D/'short-isolated/normalized-inputs'/f'{key}.ply';assert sha(normal)==proof['sourceValidation']['normalizedInputSha256'];t=trimesh.load(normal,force='mesh',process=False);assert t.is_watertight and t.is_volume;solid=mf.Manifold(mf.Mesh(np.array(t.vertices,np.float32),np.array(t.faces,np.uint32)))
 assert solid.status()==mf.Error.NoError and solid.volume()>0
 row,g=route(i);q={k:row['jointDegrees'].get(k,0) for k in core.ORDER[:core.BODIES[d['body']]]};origin=np.array(moved([0,0,0],q));rot=np.array([moved(e,q,True) for e in [[1,0,0],[0,1,0],[0,0,1]]]).T;solid=solid.transform(np.column_stack([rot,origin]));r=check(g['points'],3.5,SAGITTA,solid,source_evidence={'watertight':True,'positiveVolume':True,'sourceSha256':item['sha256'],'intrinsicReceiptHash':item['intrinsicReceiptHash']});r.update(pose=i,key=key,planHash=sha(OUT/'plan.json'),selfSummaryHash=sha(OUT/'self-summary.json'),nativeBlocked=bool(row['nativeShellOriginalBottomIntersectionsMm3']),normalizedInputHash=sha(normal) if normal else None);save(OUT/'pairs'/f'{i}__{key}.json',r);print(json.dumps({k:v for k,v in r.items() if k!='segments'}));return 0 if r['passed'] else 2
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('stage',choices=['plan','self','obstacle']);a.add_argument('--pose',type=int);a.add_argument('--key');o=a.parse_args();core.guard();raise SystemExit(plan() if o.stage=='plan' else self_all() if o.stage=='self' else obstacle(o.pose,o.key))
