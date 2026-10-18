"""Low-memory dispatch of independent proven-light continuous wire checks."""
from pathlib import Path
import json,subprocess,sys,concurrent.futures
from amp16_aabb_precheck import bounds,compare
D=Path(__file__).resolve().parent;H=D.parent;O=D/'speaker-rewire';script=D/'check_speaker_motion.py'
def run(phase,wire,direction,key='head_cap'):
 name=f'{phase}-{direction}-{wire}-{key}';cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(O/(name+'-resource.json')),'--','/tmp/microduck-cad-venv/bin/python',str(script),'--phase',phase,'--wire',str(wire),'--direction',direction,'--key',key];x=subprocess.run(cmd,capture_output=True,text=True);return {'name':name,'exitCode':x.returncode,'output':x.stdout[-450:],'error':x.stderr[-500:]}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 results=list(pool.map(lambda t:run(*t),[(p,i,d) for p in ['build'] for i in [0,1] for d in ['insertion','closure']]))
print(json.dumps(results),flush=True)
if any(x['exitCode'] for x in results):raise SystemExit(1)
scene=json.loads((O/'scene-plan.json').read_text())['rows'];carried={'head_cap','openrb','speaker','amplifier','speaker_keeper','speaker_cradle','curved_cap_hardware','openrb_usb_receiving','usb25_acUsbCReceiving','usb80_acUsbCReceiving'};jobs=[('pair',i,'insertion','head_cap') for i in [0,1]];readback=[]
for i in [0,1]:
 bb=bounds(O/f'wire-{i}-closure-continuous-receiving-world.stl')
 for k,r in scene.items():
  if k in carried:continue
  intersect=compare(bb,r['boundsMm'])['aabbOverlap'];readback.append({'wire':i,'key':k,'aabbDisjoint':not intersect})
  if intersect:jobs.append(('pair',i,'closure',k))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda t:run(*t),jobs))
report={'jobs':results,'aabbReadback':readback,'allJobsExitZero':all(x['exitCode']==0 for x in results),'integrationReady':False,'carriedRigidKeys':sorted(carried),'scope':'Continuous conservative wire sweep vs fixed head; diagnosticUSB25/80 treated independently as static cases, not actual simultaneous USB motion.'};(O/'continuous-motion-batch.json').write_text(json.dumps(report,indent=2));print(json.dumps({'jobs':len(jobs),'failed':[x for x in results if x['exitCode']]}))
