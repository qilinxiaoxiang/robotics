import concurrent.futures,json,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parents[2]/'head-redesign-20261008';rows=json.loads((D/'station-inventory.json').read_text())
tasks=[(r['operation']['id'],'tool') for r in rows if r['operation']['screwIds']]+[(r['operation']['id'],'carry') for r in rows if r['movingScrewIds'] and r['operation'].get('approachVector') and not r['operation'].get('motionWaypoints')]
def run(t):
 op,kind=t;cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--max-mib','512','--seconds','120','--parallel-light','--wait-lock-seconds','30','--report',str(D/f'{op}-{kind}-resource.json'),'--','/tmp/microduck-cad-venv/bin/python',str(D/'check_delta.py'),'--operation',op,'--kind',kind]
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(D/f'{op}-{kind}.log').write_text(p.stdout);return {'operation':op,'kind':kind,'exitCode':p.returncode}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 result=[]
 for r in pool.map(run,tasks):result.append(r);print(json.dumps(r),flush=True)
(D/'delta-jobs.json').write_text(json.dumps(result,indent=2)+'\n')
