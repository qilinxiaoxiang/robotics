"""Lightweight complete-coverage screen and guarded isolated source-pair run."""
import json,math,struct,base64,itertools,subprocess,sys,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import segmented_yaw_neck_worker as w
D=w.D;OUT=w.OUT;p=w.current();ph=w.sha(OUT/'plan.json');sr=json.loads((OUT/'self-summary.json').read_text());assert sr['passed'] and sr['planHash']==ph
radius=3.5+w.SAGITTA+.001;bs={}
for o in p['obstacles']:
 d=json.loads(Path(o['path']).read_text());v=list(struct.iter_unpack('<fff',base64.b64decode(d['positionB64'])));bs[o['key']]=[list(map(min,zip(*v))),list(map(max,zip(*v)))]
needs=[];aabbs=[]
for i in p['nativeClearIndices']:
 row,g=w.route(i);segbox=[[[min(a[k],b[k])-radius for k in range(3)],[max(a[k],b[k])+radius for k in range(3)]] for a,b in zip(g['points'],g['points'][1:])]
 for o in p['obstacles']:
  q={k:row['jointDegrees'].get(k,0) for k in w.core.ORDER[:w.core.BODIES[o['body']]]};corners=[w.moved(v,q) for v in itertools.product(*zip(*bs[o['key']]))];box=[list(map(min,zip(*corners))),list(map(max,zip(*corners)))];pair={'pose':i,'key':o['key']}
  if all(any(s[0][k]>box[1][k]+.0001 or box[0][k]-.0001>s[1][k] for k in range(3)) for s in segbox):aabbs.append(pair|{'method':'Every conservative segment receiving AABB disjoint from full posed source vertex AABB','radiusMm':radius,'obstaclePaddingMm':.0001})
  else:needs.append(pair)
w.save(OUT/'screen.json',{'planHash':ph,'sourceHashes':{str(Path(__file__)):w.sha(__file__)},'expected':p['expectedPairs'],'aabbDisjoint':aabbs,'needsCAD':needs,'wholeAccepted':False});print(json.dumps({'expected':len(p['expectedPairs']),'aabbDisjoint':len(aabbs),'needsCAD':len(needs)}),flush=True)
if '--run' not in sys.argv:raise SystemExit(0)
stop=threading.Event()
def job(x):
 if stop.is_set():return None
 i,k=x['pose'],x['key'];f=OUT/'pairs'/f'{i}__{k}.json'
 if f.exists():
  r=json.loads(f.read_text())
  if r.get('planHash')==ph and r.get('selfSummaryHash')==w.sha(OUT/'self-summary.json'):
   if not r['passed']:stop.set()
   return 0 if r['passed'] else 2
 cmd=[sys.executable,str(w.H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(OUT/'resources'/f'{i}__{k}.json'),'--','/tmp/microduck-cad-venv/bin/python',str(D/'segmented_yaw_neck_worker.py'),'obstacle','--pose',str(i),'--key',k];r=subprocess.run(cmd,capture_output=True,text=True)
 if r.returncode:stop.set()
 print(json.dumps({'pose':i,'key':k,'exitCode':r.returncode}),flush=True);return r.returncode
with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(job,needs))
completed=len(aabbs);failures=[];missing=[];receipts={}
for x in needs:
 f=OUT/'pairs'/f'{x["pose"]}__{x["key"]}.json'
 if not f.exists():missing.append(x);continue
 r=json.loads(f.read_text())
 if r.get('planHash')!=ph or r.get('selfSummaryHash')!=w.sha(OUT/'self-summary.json') or not r.get('coverageComplete'):missing.append(x);continue
 completed+=1;receipts[f.name]=w.sha(f)
 if not r['passed']:failures.append(x|{'minimumCenterlineDistanceLowerBoundMm':r['minimumGapLowerBoundMm'],'inconclusiveSegments':r['inconclusiveSegmentIndices']})
r={'wholeAccepted':False,'scope':p['scope'],'source15SubsetPassed':not failures and not missing,'coverageComplete':not missing,'planHash':ph,'screenHash':w.sha(OUT/'screen.json'),'expected':len(p['expectedPairs']),'completed':completed,'failures':failures,'missing':missing,'receiptHashes':receipts};w.save(OUT/'summary.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['missing','receiptHashes','failures']}));raise SystemExit(0 if r['source15SubsetPassed'] else 2)
