"""Two independent short guarded jobs; complete explicit coverage before acceptance."""
import concurrent.futures,subprocess,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-ribbon-sweep'
def run(job):
 part,start=job;p=O/f'{part}-split-clearance-{start}.json'
 if p.exists():
  previous=json.loads(p.read_text())
  if previous.get('passed') and previous['expectedPoses']==json.loads((O/'head_bottom.json').read_text())['expectedUniqueHeadRelativePoses'][start:start+10] and all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in previous['sourceHashes'].items()):return job
 log=O/f'{part}-split-clearance-{start}.log';cmd=['python3',str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(p.with_suffix('.runtime.json')),'--','/tmp/microduck-cad-venv/bin/python',str(D/'verify_split_channel_clearance.py'),'--part',part,'--start',str(start),'--count','10']
 with log.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(job,r.returncode);data=json.loads(p.read_text());assert data['passed'],(job,'clearance failure');return job
jobs=[(part,start) for part in ['head_bottom','head_roll_bearing_carrier','jaw_support'] for start in range(0,79,10)]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for i,job in enumerate(pool.map(run,jobs),1):print(i,len(jobs),job,flush=True)
