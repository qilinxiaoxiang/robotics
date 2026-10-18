"""Lightweight orchestration only; every CAD pair owns a bounded worker."""
from pathlib import Path
import subprocess,concurrent.futures,itertools,json,argparse
D=Path(__file__).resolve().parent;H=D.parent;A=D/'gpio-fanout/x225/actual4397';p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args();jobs=[]
for pin,key in itertools.product([12,20,35,40],['head_cap','head_bottom','jaw_support','motor15','zero_w_components','amplifier']):jobs.append((f'{a.tag}-{pin}-{key}',[str(D/'check_i2s_x225.py'),'--pin',str(pin),'--mode','pair','--key',key,'--actual']))
for x,y in itertools.combinations([12,20,35,40],2):jobs.append((f'{a.tag}-wirepair-{x}-{y}',[str(D/'check_audio_pair.py'),'--a',str(A/f'i2s-pin{x}-world.stl'),'--b',str(A/f'i2s-pin{y}-world.stl'),'--out',str(A/f'wirepair-{x}-{y}.json')]))
def run(job):
 name,cmd=job;p=subprocess.run(['python3',str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(A/f'{name}-resource.json'),'--','/tmp/microduck-cad-venv/bin/python']+cmd,capture_output=True,text=True);return name,p.returncode,p.stdout.splitlines()[0] if p.stdout else p.stderr[-500:]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 results=[]
 for result in ex.map(run,jobs):results.append(result);print(result,flush=True)
(A/f'{a.tag}-batch.json').write_text(json.dumps({'integrationReady':False,'results':results},indent=2)+'\n')
