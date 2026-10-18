from pathlib import Path
import subprocess,json,time,re,hashlib
D=Path(__file__).resolve().parent;R=D.parents[2];out=D/'native-V1-Orange-nut-window-final';out.mkdir(exist_ok=True)
project=R/'printing/12-REPAIR-V1-20261008/staging-projects/MicroDuck_Elegoo_Orange_ASSEMBLY_editable.3mf';assert hashlib.sha256(project.read_bytes()).hexdigest()=='6b16b32b49bf7ae2ece617927cd8ee6505f1f30c478d9502d3c9f566d50e00a6'
def pressure():
 raw=subprocess.check_output(['memory_pressure'],text=True);level=int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True));return {'time':time.time(),'freePercentage':int(re.search(r'free percentage: (\d+)%',raw)[1]),'pressureLevel':level,'raw':raw}
initial=pressure();records=[initial]
assert initial['pressureLevel']<4,'Preexisting critical pressure; do not start native process'
cmd=['python3',str(R/'head-redesign-20261008/run_bounded_cad.py'),'--wait-lock-seconds','30','--max-mib','1024','--seconds','120','--report',str(out/'resource.json'),'--','/tmp/microduck-cad-venv/bin/python',str(R/'printing/10-SURFACE-QUALITY-20261006/slicing/guarded_orca_slice.py'),'--project',str(project),'--outputdir',str(out),'--export','Orange_V1_fixed_native.3mf']
p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);reason=None;warning_streak=0
while p.poll()is None:
 time.sleep(1)
 r=pressure();records.append(r)
 warning_streak=warning_streak+1 if initial['pressureLevel']==1 and r['pressureLevel']>=2 else 0
 if r['pressureLevel']>=4 or warning_streak>=3:
  reason='system-memory-pressure-deteriorated';p.terminate();break
text,_=p.communicate(timeout=15);records.append(pressure());report={'initial':initial,'samples':records,'stopReason':reason,'guardExitCode':p.returncode,'mode':'exclusive native slicer; 1024MiB/120s; original support/geometry/collision checks preserved','pressurePolicy':'Stop immediately at critical4, or three consecutive1-second samples of new warning2 from normal1. Baseline warning2 only stops at4. Free-percent is recorded but normal allocation is not failure.','policyCorrectionReason':'Old5-percentage-point free-memory threshold misclassified normal~800MiB allocation on16GiB as pressure even with kernel pressureLevel1. Per root authorization corrected to actual sustained kernel pressure, retaining1GiB hard cap.','projectSha256':hashlib.sha256(project.read_bytes()).hexdigest()};(out/'system-pressure-monitor.json').write_text(json.dumps(report,indent=2)+'\n');(out/'guard-output.log').write_text(text);print(text);print(json.dumps({k:v for k,v in report.items()if k not in('initial','samples')}))
raise SystemExit(p.returncode)
