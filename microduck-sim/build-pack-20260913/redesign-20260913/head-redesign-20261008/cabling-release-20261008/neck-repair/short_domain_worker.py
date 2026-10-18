"""Source-bound 186-pose domain, exact per-segment AABB screening, isolated CAD."""
import argparse,base64,itertools,json,math,struct,sys
from pathlib import Path
import short_path_worker as core
from prepare_single_candidate import moved
D=Path(__file__).resolve().parent;H=D.parent.parent;OLD=D/'short-isolated';OUT=D/'short-domain';core.OUT=OUT
RADIUS=(3.5+(9-math.sqrt(81-.25**2)))/math.cos(math.pi/24)+.0001

def source_bounds(item):
 d=json.loads(Path(item['path']).read_text());lo=[float('inf')]*3;hi=[-float('inf')]*3
 for v in struct.iter_unpack('<fff',base64.b64decode(d['positionB64'])):
  for k in range(3):lo[k]=min(lo[k],v[k]);hi[k]=max(hi[k],v[k])
 return lo,hi

def moved_bounds(box,body,q):
 qq={k:q.get(k,0) for k in core.ORDER[:core.BODIES[body]]};corners=[moved(p,qq) for p in itertools.product(*zip(*box))]
 return [list(map(min,zip(*corners))),list(map(max,zip(*corners)))]

def plan():
 old=json.loads((OLD/'plan.json').read_text());base=json.loads((H/'usb-access/usb-repair/rigid-domain.json').read_text());indices=[i for i,r in enumerate(base['samples']) if not r['nativeShellOriginalBottomIntersectionsMm3']];assert len(indices)==186
 old['expectedPairs']=[{'pose':i,'obstacle':o['key']} for i in indices for o in old['obstacles']];old['stageScope']='All186 native-rigid-clear sampled poses against15 source neck/torso/motor parts. Current cap/electronics, fixed head exit, endpoint fanouts and continuous angular paths excluded and still unvalidated.'
 old['inputHashes'][str(Path(__file__).resolve())]=core.sha(Path(__file__));old['inputHashes'][str((OLD/'plan.json').resolve())]=core.sha(OLD/'plan.json');old['inputHashes'][str((OLD/'summary.json').resolve())]=core.sha(OLD/'summary.json');old['nativeClearPoseIndices']=indices;old['blocked43PreservedIn']=str(H/'usb-access/usb-repair/rigid-domain.json');old['priorFiniteBlockedFailureReceipt']=str(OLD/'pairs/148__motor14.json');old['inputHashes'][old['priorFiniteBlockedFailureReceipt']]=core.sha(Path(old['priorFiniteBlockedFailureReceipt']))
 for o in old['obstacles']:
  rp=OLD/'pairs'/f'-1__{o["key"]}.json';r=json.loads(rp.read_text());assert r['passed'] and r['obstacleSha256']==o['sha256'] and r['inputObstacleWatertight'] and r['inputObstacleVolumePositive'];o['intrinsicSolidValidationReceipt']=str(rp.resolve());o['intrinsicSolidValidationReceiptHash']=core.sha(rp);old['inputHashes'][str(rp.resolve())]=core.sha(rp);o['neutralActualVertexBounds']=source_bounds(o)
 old['AABBReceivingRadiusMm']=RADIUS;core.save(OUT/'plan.json',old);print(json.dumps({'expectedPairs':len(old['expectedPairs']),'nativeClearPoses':186,'sourceObstacles':15,'planHash':core.sha(OUT/'plan.json')}))

def screen():
 p=core.current();core.passed_self();ph=core.sha(OUT/'plan.json');needs=[];done=0
 for i in p['nativeClearPoseIndices']:
  row,g=core.geom(i);pts=g['points'];ch=__import__('hashlib').sha256(json.dumps(pts,separators=(',',':')).encode()).hexdigest();boxes=[[[min(a[k],b[k])-RADIUS for k in range(3)],[max(a[k],b[k])+RADIUS for k in range(3)]] for a,b in zip(pts,pts[1:])]
  curve={'pose':i,'planHash':ph,'centerlineSha256':ch,'points':pts,'jointDegrees':row['jointDegrees'],'AABBReceivingRadiusMm':RADIUS};core.save(OUT/'centerlines'/f'{i}.json',curve)
  for o in p['obstacles']:
   box=moved_bounds(o['neutralActualVertexBounds'],o['body'],row['jointDegrees']);overlaps=[]
   for j,seg in enumerate(boxes):
    if not any(seg[0][k]>box[1][k]+.0001 or box[0][k]-.0001>seg[1][k] for k in range(3)):overlaps.append(j)
   if overlaps:needs.append({'pose':i,'obstacle':o['key'],'candidateSegmentIndices':overlaps});continue
   r={'pose':i,'key':o['key'],'planHash':ph,'centerlineSha256':ch,'centerlineFileSha256':core.sha(OUT/'centerlines'/f'{i}.json'),'obstacleSha256':o['sha256'],'nativeBaselineBlocked':False,'intersectionMm3':0.,'passed':True,'method':'All receiving-segment conservative AABBs disjoint from posed actual-vertex obstacle bounds','intrinsicSolidValidationReceiptHash':o['intrinsicSolidValidationReceiptHash'],'poseObstacleBounds':box,'receivingRadiusMm':RADIUS,'obstacleBoundsPaddingMm':.0001};core.save(OUT/'pairs'/f'{i}__{o["key"]}.json',r);done+=1
 core.save(OUT/'cad-needed.json',{'planHash':ph,'expectedPairs':len(p['expectedPairs']),'aabbDisjointPairs':done,'needsCAD':needs,'coverageComplete':not needs});print(json.dumps({'expectedPairs':len(p['expectedPairs']),'aabbDisjointPairs':done,'needsCAD':len(needs),'posesNeedingMesh':len({r['pose'] for r in needs})}))

def summary():
 p=core.current();ph=core.sha(OUT/'plan.json');missing=[];bad=[];stale=[];done=[];receipts={}
 for pair in p['expectedPairs']:
  f=OUT/'pairs'/f'{pair["pose"]}__{pair["obstacle"]}.json'
  if not f.exists():missing.append(pair);continue
  r=json.loads(f.read_text());o=next(o for o in p['obstacles'] if o['key']==pair['obstacle']);ok=r.get('planHash')==ph and r.get('obstacleSha256')==o['sha256']
  if r['method'].startswith('All receiving-segment'):ok=ok and core.sha(OUT/'centerlines'/f'{pair["pose"]}.json')==r['centerlineFileSha256'] and r['intrinsicSolidValidationReceiptHash']==o['intrinsicSolidValidationReceiptHash']
  else:ok=ok and (OUT/'meshes'/f'{pair["pose"]}.stl').exists() and core.sha(OUT/'meshes'/f'{pair["pose"]}.stl')==r['receivingSha256']
  if not ok:stale.append(pair);continue
  done.append(pair);receipts[f.name]=core.sha(f)
  if not r['passed']:bad.append(r)
 s=core.passed_self();complete=not missing and not stale
 r={'wholeHarnessAccepted':False,'planHash':ph,'self229Passed':True,'expectedPairCount':len(p['expectedPairs']),'completedPairCount':len(done),'coverageComplete':complete,'nativeClear15PartSubsetClear':complete and not bad,'missingPairs':missing,'stalePairs':stale,'failedPairs':bad,'scope':p['stageScope'],'priorNativeBlockedFailure':p['priorFiniteBlockedFailureReceipt'],'receiptHashes':receipts};core.save(OUT/'summary.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['missingPairs','receiptHashes']},indent=2));return 0 if complete and not bad else 2
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['plan','self','screen','mesh','obstacle','summary']);ap.add_argument('--pose',type=int);ap.add_argument('--key');o=ap.parse_args();core.guard();sys.exit(plan() if o.stage=='plan' else core.self_all() if o.stage=='self' else screen() if o.stage=='screen' else core.mesh(o.pose) if o.stage=='mesh' else core.obstacle(o.pose,o.key) if o.stage=='obstacle' else summary())
