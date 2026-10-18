"""Stdlib orchestration; each exact pair lives in a fresh guarded process."""
from pathlib import Path
import json,subprocess,sys
D=Path(__file__).resolve().parent;H=D.parent;O=D/'speaker-rewire'
from amp16_aabb_precheck import bounds,compare
scene=json.loads((O/'scene-plan.json').read_text());p={'pairs':[]}
for i in [0,1]:
 bb=bounds(O/f'speaker-wire-{i}-world.stl');p['pairs'].append({'wire':i,'keys':[k for k,r in scene['rows'].items() if compare(bb,r['boundsMm'])['aabbOverlap']],'aabbDisjoint':[k for k,r in scene['rows'].items() if not compare(bb,r['boundsMm'])['aabbOverlap']]})
(O/'static-plan.json').write_text(json.dumps(p,indent=2))
results=[]
for row in p['pairs']:
 for key in row['keys']:
  i=row['wire']
  component=O/f'openrb-components-wire{i}.json'
  if key=='openrb' and component.exists():
   import bounded_amp_check as c
   proof=json.loads(component.read_text())
   if proof.get('passed') and all(c.sha(k)==h for k,h in proof['inputHashes'].items()):
    results.append({'wire':i,'key':key,'exitCode':0,'componentProof':str(component),'wholeConvexFalsePositiveNotWaived':'Every source triangle belongs to one of142 tested conservative components'});continue
  r=O/f'pair-{i}-{key}-resource.json'
  cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(r),'--','/tmp/microduck-cad-venv/bin/python',str(D/'check_speaker_rewire.py'),'--mode','static','--wire',str(i),'--key',key]
  ret=subprocess.run(cmd,capture_output=True,text=True);print(ret.stdout[-1600:],flush=True)
  results.append({'wire':i,'key':key,'exitCode':ret.returncode,'resource':str(r)})
  (O/'static-batch.json').write_text(json.dumps({'results':results,'complete':False},indent=2))
  if ret.returncode:print(ret.stderr,flush=True);sys.exit(ret.returncode)
(O/'static-batch.json').write_text(json.dumps({'results':results,'complete':True},indent=2))
