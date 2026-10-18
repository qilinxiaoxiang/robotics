"""Reproduce native Bambu slicing and SD exports from the current reviewed source."""
from pathlib import Path
import json, hashlib, shutil, subprocess, time
P=Path(__file__).resolve().parent
source=P.parent/'current-print-queue.3mf'
bambu='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
archive=P/'superseded-before-fastener-review'
archive.mkdir(exist_ok=True)
for name in ['MicroDuck-current-89-six-plates-sliced.3mf','handoff-verification.json','native-export-results.json','result.json','run-command.json','slice.log']:
 p=P/name
 if p.exists() and not (archive/name).exists():shutil.copy2(p,archive/name)
command=[bambu,'--arrange','0','--orient','0','--slice','0','--export-3mf','MicroDuck-current-89-six-plates-sliced.3mf','--outputdir',str(P),str(source)]
(P/'run-command.json').write_text(json.dumps({'command':command,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()},indent=2))
with (P/'slice.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
assert r.returncode==0, 'Native full slicing failed; inspect slice.log'
print('Native full six-plate slicing passed',flush=True)
results=[]
for n in range(1,7):
 d=P/'native-exports'/f'plate-{n}';d.mkdir(parents=True,exist_ok=True)
 name=f'zhengxia_microduck_plate_{n}.gcode.3mf'
 target=P/'SD-CARD'/name
 if target.exists() and not (archive/name).exists():shutil.copy2(target,archive/name)
 command=[bambu,'--arrange','0','--orient','0','--slice',str(n),'--min-save','--export-3mf',name,'--outputdir',str(d),str(source)]
 (d/'command.json').write_text(json.dumps(command,indent=2))
 start=time.monotonic()
 with (d/'export.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
 result=json.loads((d/'result.json').read_text())
 assert r.returncode==result['return_code']==0,(n,r.returncode,result)
 shutil.copy2(d/name,target)
 results.append({'plate':n,'exit_code':r.returncode,'return_code':result['return_code'],'elapsed_seconds':round(time.monotonic()-start,1),'name':name})
 print(f'Native SD export plate {n} passed',flush=True)
(P/'native-export-results.json').write_text(json.dumps(results,indent=2))
