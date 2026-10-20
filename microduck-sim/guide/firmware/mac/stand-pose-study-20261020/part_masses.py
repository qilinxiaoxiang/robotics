"""Slicer part masses of the head and box parts printed after the as-built manifest (2026-10-15), from the released
Elegoo G-code, with the existing parser (dynamics/v19-20261014/gcode_part_masses.parse)."""
import json, sys
from pathlib import Path
SIM = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(SIM / 'hardware-design-20260912/whole-robot-20260912/dynamics/v19-20261014'))
import gcode_part_masses as g
P = SIM / 'guide/print'
FILES = {
    'V1.17-White': P / 'release-V1.17/run/delivery/zhengxia_V1.17_White_Elegoo-Centauri-Carbon_4h26m.gcode',
    'V1.17-Orange': P / 'release-V1.17/run/delivery/zhengxia_V1.17_Orange_Elegoo-Centauri-Carbon_1h49m.gcode',
}
FILES.update({f'V1.20-{p.name}': p for p in sorted((P / 'release-V1.20/run/delivery').glob('*Elegoo*.gcode'))})
FILES.update({'V1.9-Orange': P / 'release-V1.9/run-r2/delivery/zhengxia_V1.9_Orange_Elegoo-Centauri-Carbon_3h55m.gcode'})
out = {}
for k, f in FILES.items():
    r = g.parse(f)
    out[k] = {'file': str(f), 'objects': {o: round(v['model_g'], 2) for o, v in r['objects'].items()}}
    print(k, out[k]['objects'])
json.dump(out, open(Path(__file__).with_name('part_masses.json'), 'w'), indent=1)
