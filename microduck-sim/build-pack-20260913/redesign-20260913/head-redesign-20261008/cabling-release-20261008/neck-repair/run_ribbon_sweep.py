"""Stdlib checkpoint launcher; at most one guarded short CAD subprocess."""
import argparse,json,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-ribbon-sweep';O.mkdir(exist_ok=True);a=argparse.ArgumentParser();a.add_argument('--part',required=True);o=a.parse_args();meta=O/f'{o.part}.json'
while True:
 r=json.loads(meta.read_text()) if meta.exists() else {'completed':[]};n=len(r['completed'])
 if r.get('coverageComplete'):break
 receipt=O/f'{o.part}-batch-{n}.runtime.json';log=O/f'{o.part}-batch-{n}.log'
 cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(receipt),'--','/tmp/microduck-cad-venv/bin/python',str(D/'build_ribbon_sweep_batch.py'),'--part',o.part,'--count','3']
 with log.open('w') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 after=json.loads(meta.read_text());print(json.dumps({'part':o.part,'completed':len(after['completed']),'expected':len(after['expectedUniqueHeadRelativePoses']),'exitCode':result.returncode,'receipt':str(receipt)}),flush=True)
 if result.returncode or len(after['completed'])<=n:sys.exit(result.returncode or 2)
 if o.part=='head_bottom':
  compact=[sys.executable,str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(O/f'head-compact-{n}.runtime.json'),'--','/tmp/microduck-cad-venv/bin/python',str(D/'compact_ribbon_checkpoint.py'),'--part',o.part]
  with (O/f'head-compact-{n}.log').open('w') as f:cr=subprocess.run(compact,stdout=f,stderr=subprocess.STDOUT)
  if cr.returncode:sys.exit(cr.returncode)

