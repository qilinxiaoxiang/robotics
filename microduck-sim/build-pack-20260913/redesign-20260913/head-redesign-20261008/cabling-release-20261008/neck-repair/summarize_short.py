"""Reconcile every declared pair; a passing subset is never full coverage."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;OUT=D/'short-isolated'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((OUT/'plan.json').read_text());ph=sha(OUT/'plan.json');staleInputs=[name for name,h in p['inputHashes'].items() if sha(Path(name))!=h];completed=[];missing=[];stale=[];failed=[];receipts={}
for pair in p['expectedPairs']:
 f=OUT/'pairs'/f'{pair["pose"]}__{pair["obstacle"]}.json'
 if not f.exists():missing.append(pair);continue
 r=json.loads(f.read_text());obstacle=next(o for o in p['obstacles'] if o['key']==pair['obstacle']);mesh=OUT/'meshes'/f'{pair["pose"]}.stl'
 if r['planHash']!=ph or r['obstacleSha256']!=obstacle['sha256'] or not mesh.exists() or sha(mesh)!=r['receivingSha256']:stale.append(pair);continue
 completed.append(pair);receipts[f.name]=sha(f)
 if not r['passed']:failed.append({'pair':pair,'intersectionMm3':r['intersectionMm3'],'nativeBaselineBlocked':r['nativeBaselineBlocked'],'bounds':r['intersectionBounds']})
s=json.loads((OUT/'self-summary.json').read_text());selfCurrent=s['planHash']==ph and s['coverageComplete'] and s['passed'];coverage=not missing and not stale and not staleInputs
r={'accepted':False,'wholeHarnessAccepted':False,'planHash':ph,'expectedPairCount':len(p['expectedPairs']),'completedPairCount':len(completed),'coverageComplete':coverage,'self229Passed':selfCurrent,'finitePairSubsetClear':coverage and selfCurrent and not failed,'missingPairs':missing,'stalePairs':stale,'staleInputs':staleInputs,'failedPairs':failed,'scope':p['stageScope'],'currentHeadState':p['currentHeadState'],'receiptHashes':receipts}
(OUT/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['missingPairs','receiptHashes','currentHeadState']},indent=2))
