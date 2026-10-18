from pathlib import Path
import subprocess,json,time,re,hashlib
D=Path(__file__).resolve().parent;R=D.parents[2];out=D/'native-V1-Orange-original-orientation-exclusive';out.mkdir(exist_ok=True)
project=R/'printing/12-REPAIR-V1-20261008/staging-projects/MicroDuck_Elegoo_Orange_ASSEMBLY_editable.3mf';assert hashlib.sha256(project.read_bytes()).hexdigest()=='729636ed6888c1ced9608c8920df49dcbadb8068492dfa4239b4a8ce70219202'
def pressure():
 raw=subprocess.check_output(['memory_pressure'],text=True);level=int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True));return {'time':time.time(),'freePercentage':int(re.search(r'free percentage: (\d+)%',raw)[1]),'pressureLevel':level,'raw':raw}
initial=pressure();records=[initial]
assert initial['pressureLevel']<4,'Preexisting critical pressure; do not start native process'
cmd=['python3',str(R/'head-redesign-20261008/run_bounded_cad.py'),'--wait-lock-seconds','30','--max-mib','1024','--seconds','120','--report',str(out/'resource.json'),'--','/tmp/microduck-cad-venv/bin/python',str(R/'printing/10-SURFACE-QUALITY-20261006/slicing/guarded_orca_slice.py'),'--project',str(project),'--outputdir',str(out),'--export','Orange_V1p1_native.3mf']
p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);reason=None
while p.poll()is None:
 time.sleep(1)
 r=pressure();records.append(r)
 if r['pressureLevel']>=4 or r['freePercentage']<=initial['freePercentage']-5:
  reason='system-memory-pressure-deteriorated';p.terminate();break
text,_=p.communicate(timeout=15);records.append(pressure());report={'initial':initial,'samples':records,'stopReason':reason,'guardExitCode':p.returncode,'mode':'exclusive native slicer; 1024MiB/120s; original support/geometry/collision checks preserved','projectSha256':hashlib.sha256(project.read_bytes()).hexdigest()};(out/'system-pressure-monitor.json').write_text(json.dumps(report,indent=2)+'\n');(out/'guard-output.log').write_text(text);print(text);print(json.dumps({k:v for k,v in report.items()if k not in('initial','samples')}))
raise SystemExit(p.returncode)
