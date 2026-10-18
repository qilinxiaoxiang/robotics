from pathlib import Path
import subprocess,sys,concurrent.futures,json
D=Path(__file__).resolve().parent;H=D.parent;O=D/'speaker-rewire'
def run(t):
 k,start=t;cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(O/f'saddle-{k}-{start}-resource.json'),'--','/tmp/microduck-cad-venv/bin/python',str(D/'check_saddle.py'),'--key',k,'--start',str(start)];x=subprocess.run(cmd,capture_output=True,text=True);return {'key':k,'start':start,'exitCode':x.returncode,'output':x.stdout[-600:],'error':x.stderr[-400:]}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:r=list(pool.map(run,[(k,st) for k in ['motor13','head_yaw_link'] for st in [0,80,160]]))
(O/'saddle-domain-batch.json').write_text(json.dumps({'rows':r,'passed':all(x['exitCode']==0 for x in r),'integrationReady':False},indent=2));print(json.dumps(r))
