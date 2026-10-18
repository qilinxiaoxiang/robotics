import subprocess,concurrent.futures,json
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent;O=D/'gpio-fanout/x225/actual4397';plan=json.loads((O/'complete-scene-plan.json').read_text());jobs=[p for p in plan['pairs'] if p['exactNeeded']];R=O/'complete-pairs';R.mkdir(exist_ok=True)
def run(j):
 pin,key=j['pin'],j['key'];p=subprocess.run(['python3',str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(R/f'{pin}-{key}-resource.json'),'--','/tmp/microduck-cad-venv/bin/python',str(D/'check_i2s_complete_pair.py'),'--pin',str(pin),'--key',key],capture_output=True,text=True);return pin,key,p.returncode,p.stdout.splitlines()[0] if p.returncode in [0,2] else p.stderr[-500:]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 results=[]
 for r in ex.map(run,jobs):results.append(r);print(r,flush=True)
(O/'complete-scene-batch.json').write_text(json.dumps({'integrationReady':False,'results':results,'allNoPenetration':all(r[2]==0 for r in results),'aabbSeparatedPairs':sum(not x['exactNeeded'] for x in plan['pairs'])},indent=2)+'\n')
