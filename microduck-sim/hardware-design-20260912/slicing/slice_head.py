"""Slice the replacement head with the same machine/filament and tree supports."""
from pathlib import Path
import subprocess, json

P = Path(__file__).resolve().parent
out = P / 'head'
out.mkdir(exist_ok=True)
process = json.loads((P / 'process.json').read_text())
process.update({'enable_support': '1', 'support_type': 'tree(auto)',
                'support_on_build_plate_only': '0'})
(P / 'head-process.json').write_text(json.dumps(process, indent=2))
cmd = ['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio',
       '--load-settings', f'{P}/machine.json;{P}/head-process.json',
       '--load-filaments', str(P / 'filament.json'), '--arrange', '1',
       '--orient', '0', '--slice', '0', '--export-3mf', 'head-with-camera-mount.3mf',
       '--outputdir', str(out), str(P.parent / 'head/head-camera-holes.stl')]
with (out / 'slice.log').open('w') as log:
    result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
result.check_returncode()
data = json.loads((out / 'result.json').read_text())
assert data['return_code'] == 0 and data.get('sliced_plates'), data
(out / 'slice-result.json').write_text(json.dumps(data, indent=2))
print([(p['total_predication'], p['filaments'], p['warning_message']) for p in data['sliced_plates']])
