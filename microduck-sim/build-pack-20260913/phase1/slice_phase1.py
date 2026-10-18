"""Slice the exact Phase 1 manifest using the existing checked Bambu profiles."""
from pathlib import Path
import hashlib
import json
import subprocess

P = Path(__file__).resolve().parent
O = P / 'printing'
O.mkdir(exist_ok=True)
profiles = P.parents[1] / 'hardware-design-20260912/slicing'
manifest = json.loads((P / 'print-manifest.json').read_text())
parts = [Path(r['file']) for r in manifest['instances']]
assert len(parts) == 85
for p, r in zip(parts,manifest['instances']):
    assert hashlib.sha256(p.read_bytes()).hexdigest() == r['sha256']
cmd = ['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--load-settings',f'{profiles}/machine.json;{profiles}/head-process.json',
    '--load-filaments',str(profiles / 'filament.json'),'--arrange','1','--orient','0','--slice','0',
    '--export-3mf','phase1-85-raw.3mf','--outputdir',str(O)] + list(map(str,parts))
with (O / 'slice.log').open('w') as f:
    result = subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
result.check_returncode()
data = json.loads((O / 'result.json').read_text())
assert data['return_code'] == 0 and data['sliced_plates']
output = O / 'MicroDuck-Phase1-85-instances-X1C-CoolPlate.3mf'
subprocess.run(['python3',str(profiles / 'embed_presets.py'),str(O / 'phase1-85-raw.3mf'),str(output)],check=True)
report = {'queue_count':len(parts),'parts':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in parts],
    'project':str(output),'project_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'result':data,
    'predicted_grams':sum(sum(f['total_used_g'] for f in plate['filaments']) for plate in data['sliced_plates']),
    'predicted_seconds':sum(plate['total_predication'] for plate in data['sliced_plates']),
    'plate_count':len(data['sliced_plates']),
    'machine':'X1 Carbon','nozzle_mm':.4,'bed':'Cool Plate','material':'PLA','layer_height_mm':.2,'walls':4,'infill':'30% gyroid','support':'tree(auto)',
    'physical_print_completed':False}
(O / 'slice-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['parts','result']}))
