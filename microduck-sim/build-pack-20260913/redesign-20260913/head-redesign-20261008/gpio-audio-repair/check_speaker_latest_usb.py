"""Only new audio receiving pieces vs each distinct current USB endcase."""
import subprocess,concurrent.futures,json
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent;O=D/'speaker-rewire';U=H/'usb-access/usb-repair/positive-x225-exports';R=O/'usb-x225';R.mkdir(exist_ok=True)
parts={'speaker0':O/'speaker-wire-0-world.stl','speaker1':O/'speaker-wire-1-world.stl','saddle':O/'speaker-pair-roof-saddle-tie-clearance-world.stl','tie':O/'speaker-tie-receiving-world.stl'};jobs=[(name,span,f) for name in parts for span in [25,80] for f in sorted((U/f'span-{span}-diagnostic').glob('*.stl'))];assert len(jobs)==48
def run(job):
 name,span,f=job;tag=f'{name}-{span}-{f.stem}';out=R/f'{tag}.json';p=subprocess.run(['python3',str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(R/f'{tag}-resource.json'),'--','/tmp/microduck-cad-venv/bin/python',str(D/'check_audio_pair.py'),'--a',str(parts[name]),'--b',str(f),'--out',str(out)],capture_output=True,text=True);return {'tag':tag,'exitCode':p.returncode,'result':json.loads(out.read_text()) if out.exists() else {'error':p.stderr[-500:]}}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 results=[]
 for r in ex.map(run,jobs):results.append(r);print(r['tag'],r['exitCode'],r['result'].get('overlapMm3'),r['result'].get('minimumGapMm'),flush=True)
(R/'batch.json').write_text(json.dumps({'passed':all(r['exitCode']==0 for r in results),'rows':results,'scope':'USB cases independently; never union both length variants as a single assembly.'},indent=2)+'\n')
