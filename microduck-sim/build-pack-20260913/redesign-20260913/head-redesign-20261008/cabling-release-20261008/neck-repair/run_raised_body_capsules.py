"""Up to4 independent single-obstacle jobs; global launcher enforces budget."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,json,hashlib,threading,sys
D=Path(__file__).resolve().parent;H=D.parent.parent;P=D/'raised-body-domain';OUT=D/'raised-body-capsule';needs=json.loads((P/'cad-needed.json').read_text());ph=hashlib.sha256((P/'plan.json').read_bytes()).hexdigest();assert needs['planHash']==ph;stop=threading.Event()
def run(row):
 if stop.is_set():return None
 i,k=row['pose'],row['obstacle'];rp=OUT/'resources'/f'{i}__{k}.json';rp.parent.mkdir(exist_ok=True,parents=True)
 cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(rp),'--','/tmp/microduck-cad-venv/bin/python',str(D/'raised_body_capsule_worker.py'),'--pose',str(i),'--key',k]
 r=subprocess.run(cmd,capture_output=True,text=True);print(json.dumps({'pose':i,'key':k,'exitCode':r.returncode,**({'stdout':r.stdout,'stderr':r.stderr} if r.returncode else {})}),flush=True)
 if r.returncode:stop.set()
 return r.returncode
with ThreadPoolExecutor(max_workers=4) as pool:
 futures=[pool.submit(run,r) for r in needs['needsCAD']];codes=[f.result() for f in as_completed(futures)]
raise SystemExit(next((c for c in codes if c),0))
