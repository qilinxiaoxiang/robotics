"""Reconcile ALL expected sampled source pairs; missing/stale never pass."""
import json,math
from pathlib import Path
import follow_yaw_worker as w
D=Path(__file__).resolve().parent;OUT=D/'follow-yaw-capsule';p=w.core.current();ph=w.core.sha(w.OUT/'plan.json');sr=w.passed_self();missing=[];stale=[];bad=[];receipts={};counts={'AABB':0,'capsule':0};minimum=None
for pair in p['expectedPairs']:
 i,k=pair['pose'],pair['obstacle'];item=next(x for x in p['obstacles'] if x['key']==k);a=w.OUT/'pairs'/f'{i}__{k}.json';c=OUT/f'{i}__{k}.json';file=None
 if a.exists():
  r=json.loads(a.read_text())
  if r.get('method','').startswith('All receiving-segment'):
   assert r['receivingRadiusMm']>=3.5+(9-math.sqrt(81-.25**2))+.0001+.001
   valid=r['planHash']==ph and r['obstacleSha256']==item['sha256'] and r['centerlineFileSha256']==w.core.sha(w.OUT/'centerlines'/f'{i}.json') and r['intrinsicSolidValidationReceiptHash']==item['intrinsicSolidValidationReceiptHash'];file=a;counts['AABB']+=1
 if file is None and c.exists():
  r=json.loads(c.read_text());valid=r['planHash']==ph and r['sourceEvidence']['sourceSha256']==item['sha256'] and r['coverageComplete'] and r['expectedSegments']==len(r['segments']) and r['nominalRadiusMm']==3.5
  for path,h in r['sourceHashes'].items():valid=valid and w.core.sha(path)==h
  proof=json.loads(Path(item['intrinsicSolidValidationReceipt']).read_text());sv=proof['sourceValidation']
  if sv.get('topologyNormalization'):
   normpath=Path(item['intrinsicSolidValidationReceipt']).parent.parent/'normalized-inputs'/f'{k}.ply';valid=valid and w.core.sha(normpath)==sv['normalizedInputSha256']
  file=c;counts['capsule']+=1;gap=r['minimumGapLowerBoundMm'];minimum=gap if minimum is None else min(minimum,gap)
 if file is None:missing.append(pair);continue
 if not valid:stale.append(pair);continue
 receipts[str(file)]=w.core.sha(file)
 if not r['passed']:bad.append({'pose':i,'key':k,'file':str(file),'inconclusiveSegmentIndices':r.get('inconclusiveSegmentIndices',[])})
complete=not missing and not stale
r={'wholeHarnessAccepted':False,'sampledSourceSubsetClear':complete and not bad,'coverageComplete':complete,'planHash':ph,'expectedPairs':len(p['expectedPairs']),'completedPairs':len(receipts),'counts':counts,'minimumPrismGapLowerBoundMm':minimum,'nativeClearPoses':186,'nativeBlocked43SelfDiagnostics':sr['nativeBlockedFailures'],'missing':missing,'stale':stale,'inconclusive':bad,'scope':'Only15 source neck/torso/motor obstacles across186 supplied native-clear sampled poses. Strict nominal round radius3.5 receiving clearance via conservative segment bounds or line-enclosing prisms plus curvature/integration/numerical allowance.','notAccepted':['All current head cap/electronics/FFC/audio/USB obstacles and all other robot parts','Full adjacent-pose angular paths, although neutral-other-joints yaw1degree self/material continuity was tested','Electrical terminal fanouts, route retention and closure/installation','Available stock length and actual wire bend/strain/electrical operating performance'],'sourceHashes':{str(Path(__file__)):w.core.sha(Path(__file__)),str(w.OUT/'plan.json'):ph,str(w.OUT/'self-summary.json'):w.core.sha(w.OUT/'self-summary.json')},'receiptHashes':receipts};w.core.save(OUT/'summary.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['missing','receiptHashes']},indent=2));raise SystemExit(0 if r['sampledSourceSubsetClear'] else 2)
