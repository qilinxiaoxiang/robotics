from pathlib import Path
import json,subprocess,hashlib
H=Path(__file__).resolve().parent;D=H.parents[1]/'hardware-design-20260912';O=H/'printing-full';O.mkdir(exist_ok=True);profiles=D/'slicing'
rows=json.loads((H/'community-print-inventory.json').read_text())['objects'];parts=[Path(r['print_file']) for r in rows if r['id'] not in [6,12,24]]+[Path(r['path']) for r in json.loads((H/'printing/slice-verification.json').read_text())['parts']]
# Source queue has 8 idlers and 6 caps. Stock 14 of each as an upper-bound allowance; installed quantities remain separate.
for name in ['idle_horn.stl','idle_cap.stl']:
 matched=[r for r in rows if r['source_name']==name];parts.extend([Path(matched[0]['print_file'])]*(14-len(matched)))
assert len(parts)==89
cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--load-settings',f'{profiles}/machine.json;{profiles}/head-process.json','--load-filaments',str(profiles/'filament.json'),'--arrange','1','--orient','0','--slice','0','--export-3mf','full-89-queue-raw.3mf','--outputdir',str(O)]+list(map(str,parts))
with (O/'slice.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
r.check_returncode();data=json.loads((O/'result.json').read_text());assert data['return_code']==0 and data.get('sliced_plates')
subprocess.run(['python3',str(profiles/'embed_presets.py'),str(O/'full-89-queue-raw.3mf'),str(O/'MicroDuck-complete-89-instances-X1C-CoolPlate.3mf')],check=True)
report={'queue_count':89,'queue_meaning':'64 retained source instances + 11 current parts + 14 extra idlers/caps = 89. Idler and cap stock totals 14 each, an upper-bound allowance, not an installed quantity.','original_source_profile':'P1S PLA2walls15%; this queue uses stronger4walls30% PLA process; mass/dynamics are not automatically revalidated','parts':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in parts],'result':data};(O/'slice-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps({'plates':len(data['sliced_plates']),'objects':sum(len(x['objects']) for x in data['sliced_plates']),'g':sum(sum(f['total_used_g'] for f in x['filaments']) for x in data['sliced_plates']),'seconds':sum(x['total_predication'] for x in data['sliced_plates']),'warnings':[x['warning_message'] for x in data['sliced_plates']]},indent=2))
