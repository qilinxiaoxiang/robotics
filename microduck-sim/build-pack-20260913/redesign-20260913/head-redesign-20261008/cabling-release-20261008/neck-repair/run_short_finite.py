"""Serial supervisor only; child CAD jobs acquire the global guarded lock."""
from pathlib import Path
import json,subprocess,sys,hashlib,argparse
D=Path(__file__).resolve().parent;H=D.parent.parent;out=D/'short-isolated';plan=json.loads((out/'plan.json').read_text());last=None
ap=argparse.ArgumentParser();ap.add_argument('--poses');ap.add_argument('--continue-native-blocked',action='store_true');opt=ap.parse_args();selected=None if not opt.poses else set(map(int,opt.poses.split(',')))
for pair in plan['expectedPairs']:
 if selected is not None and pair['pose'] not in selected:continue
 i=pair['pose'];key=pair['obstacle'];mesh=out/'meshes'/f'{i}.json'
 commands=[]
 if not mesh.exists():commands.append(('mesh',f'mesh-{i}',['mesh','--pose',str(i)]))
 receipt=out/'pairs'/f'{i}__{key}.json'
 if receipt.exists():
  prior=json.loads(receipt.read_text());assert prior['planHash']==hashlib.sha256((out/'plan.json').read_bytes()).hexdigest()
  if not prior['passed'] and opt.continue_native_blocked and prior.get('nativeBaselineBlocked'):
   print(json.dumps({'preservedNativeBlockedFailure':str(receipt),'notAccepted':True}),flush=True);continue
  if not prior['passed']:
   print(json.dumps({'existingFailure':str(receipt),'action':'Stop; diagnose before continuing'}),flush=True);sys.exit(2)
  continue
 commands.append(('obstacle',f'pair-{i}-{key}',['obstacle','--pose',str(i),'--key',key]))
 for stage,label,args in commands:
  rp=out/'resources'/f'{label}.json';rp.parent.mkdir(exist_ok=True)
  cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--wait-lock-seconds','30','--max-mib','512','--seconds','120','--report',str(rp),'--','/tmp/microduck-cad-venv/bin/python',str(D/'short_path_worker.py'),*args]
  r=subprocess.run(cmd,capture_output=True,text=True)
  if r.returncode==2 and stage=='obstacle' and opt.continue_native_blocked and receipt.exists():
   failed=json.loads(receipt.read_text())
   if failed.get('nativeBaselineBlocked'):
    print(json.dumps({'preservedNativeBlockedFailure':label,'intersectionMm3':failed['intersectionMm3'],'notAccepted':True}),flush=True);continue
  if r.returncode:
   print(json.dumps({'stoppedAt':label,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}),flush=True);sys.exit(r.returncode)
  print(label+' passed',flush=True)
print('Declared finite pair inventory completed; review current receipts before acceptance.',flush=True)
