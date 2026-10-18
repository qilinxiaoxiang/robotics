from pathlib import Path
import subprocess,json,concurrent.futures
H=Path(__file__).resolve().parent.parent;D=H/'current-closure'
keys=[['openrb','jaw_support'],['speaker','jaw_support'],['speaker_cradle','jaw_support'],['curved_cap_hardware','head_yaw_link'],['curved_cap_hardware','motor13'],['curved_cap_hardware','jaw_frame'],['curved_cap_hardware','jaw_support'],['curved_cap_hardware','motor15']]
def run(k):
 cmd=['python3',str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','60','--report',str(D/('--'.join(k)+'-resource.json')),'--','/tmp/microduck-cad-venv/bin/python',str(D/'attached_pair.py'),*k]
 p=subprocess.run(cmd,capture_output=True,text=True);print(k,p.returncode,p.stdout[-500:],p.stderr[-500:],flush=True);return k,p.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as e:rows=list(e.map(run,keys))
(D/'attached-run-summary.json').write_text(json.dumps(rows,indent=2))
