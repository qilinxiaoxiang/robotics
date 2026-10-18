from pathlib import Path
import json,numpy as np,hashlib
F=Path(__file__).resolve().parent;D=F.parent;HD=D.parents[1]/'head-layout';r=json.loads((F/'joint-known-pi-package.json').read_text());T0=np.array(r['boardNativeToWorld']);T=np.array(json.loads((HD/'native-fusion-repair-inputs.json').read_text())['openrb']['nativeToCurrentWorld']);T[0,3]+=4.5
base=json.loads((HD/'audio-relocation/positive-y13-native/current-rigid-inventory.json').read_text());byid={q['id']:q for q in base['parts']}
for q in r['parts']:
 if q['group']=='controller':q['worldTransform']=(T@np.linalg.inv(T0)@q['worldTransform']).tolist()
 elif q['group'] in ['pi','pi_interface_conditional']:q['worldTransform'][0][3]+=7
 elif q['group']=='speaker':q['worldTransform']=byid[q['key']]['worldTransform']
 elif q['group']=='amp':
  q['file']=str(HD/'audio-relocation/original-controller-side/amplifier-quarter-turn-inset05-world.stl');q['sha256']=hashlib.sha256(Path(q['file']).read_bytes()).hexdigest();q['worldTransform']=np.eye(4).tolist()
r['boardNativeToWorld']=T.tolist();r['piCurrentWorldDelta'][0][3]+=7;r['stage']='Original OpenRB shifted +X4.5, populated Pi shifted +X7 from prior vertical datum. Full straight C and Micro receiving retained as explicit negative references; no purchases or trimming.';(F/'original-inset-package.json').write_text(json.dumps(r,indent=2)+'\n');s=(F/'check_package.py').read_text().replace("src=F/'joint-package.json'","src=F/'original-inset-package.json'").replace("'joint-check-'","'original-inset-check-'");(F/'check_original_inset.py').write_text(s)
