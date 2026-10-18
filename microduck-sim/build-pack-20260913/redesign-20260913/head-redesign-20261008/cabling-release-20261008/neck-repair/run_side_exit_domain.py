"""Two independent light workers at most; guard owns global scheduling."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,subprocess,sys,hashlib
D=Path(__file__).resolve().parent;H=D.parent.parent;OUT=D/'side-exit-domain';need=json.loads((OUT/'cad-needed.json').read_text());planHash=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest();assert need['planHash']==planHash

def run(label,args):
 rp=OUT/'resources'/f'{label}.json';rp.parent.mkdir(exist_ok=True)
 cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(rp),'--','/tmp/microduck-cad-venv/bin/python',str(D/'side_exit_worker.py'),*args]
 r=subprocess.run(cmd,capture_output=True,text=True)
 print(json.dumps({'job':label,'exitCode':r.returncode,**({'stdout':r.stdout,'stderr':r.stderr} if r.returncode else {})}),flush=True)
 return r.returncode

for i in sorted({r['pose'] for r in need['needsCAD']}):
 if not (OUT/'meshes'/f'{i}.json').exists():
  rc=run(f'mesh-{i}',['mesh','--pose',str(i)])
  if rc:sys.exit(rc)
 keys=[]
 for x in need['needsCAD']:
  if x['pose']!=i:continue
  path=OUT/'pairs'/f'{i}__{x["obstacle"]}.json'
  if path.exists():
   prev=json.loads(path.read_text());assert prev['planHash']==planHash
   if not prev['passed']:print('Existing native-clear failure: '+str(path));sys.exit(2)
   continue
  keys.append(x['obstacle'])
 # Each batch has unique obstacle keys, so normalized-input files cannot race.
 for offset in range(0,len(keys),2):
  with ThreadPoolExecutor(max_workers=2) as pool:
   futures=[pool.submit(run,f'pair-{i}-{k}',['obstacle','--pose',str(i),'--key',k]) for k in keys[offset:offset+2]]
   codes=[f.result() for f in as_completed(futures)]
  if any(codes):sys.exit(next(c for c in codes if c))
print('All pending source-domain CAD pairs executed. Reconcile before accepting subset.',flush=True)
