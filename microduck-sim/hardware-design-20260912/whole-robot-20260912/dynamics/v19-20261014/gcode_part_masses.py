"""Per-object filament mass from the released Elegoo Centauri Carbon G-code (relative extrusion, M83).

Extrusion is attributed to the object open between EXCLUDE_OBJECT_START/END and split by ;TYPE: into
model (walls, infill, skin, bridges, ironing) and support. Brim/skirt/custom moves are excluded.
Mass = filament length x pi/4 x d^2 x filament_density, both read from the G-code header.
"""
from pathlib import Path
import json, math, re, collections, sys
GUIDE = Path(__file__).resolve().parents[4] / 'guide' / 'print'
FILES = {
    'V1.9': GUIDE / 'release-V1.9/run-r2/delivery/zhengxia_V1.9_Orange_Elegoo-Centauri-Carbon_3h55m.gcode',
    'V1.8-Orange': GUIDE / 'release-V1.8/run/delivery/zhengxia_V1.8_Orange_Elegoo-Centauri-Carbon_3h28m.gcode',
    'V1.8-White': GUIDE / 'release-V1.8/run/delivery/zhengxia_V1.8_White_Elegoo-Centauri-Carbon_10m.gcode',
    'V1.8-Yellow': GUIDE / 'release-V1.8/run/delivery/zhengxia_V1.8_Yellow_Elegoo-Centauri-Carbon_2h56m.gcode',
    'V1.8-Black': GUIDE / 'release-V1.8/run/delivery/zhengxia_V1.8_Black_Elegoo-Centauri-Carbon_44m.gcode',
}
EXCLUDE = {'Brim', 'Skirt', 'Custom', 'Prime tower', 'Wipe tower'}

def parse(path):
    text = path.read_text(errors='replace').splitlines()
    dens = diam = None; total_g = None; relative = None
    for line in text:
        if line.startswith('; filament_density'): dens = float(re.split('[:=]', line)[1].split(',')[0])
        if line.startswith('; filament_diameter'): diam = float(re.split('[:=]', line)[1].split(',')[0])
        if line.startswith('; total filament used [g]'): total_g = float(line.split('=')[1])
        if relative is None and line.strip() == 'M83': relative = True
        if relative is None and line.strip() == 'M82': relative = False
    assert relative, 'expected relative extrusion'
    g_per_mm = math.pi / 4 * diam ** 2 * dens / 1000.0
    obj = None; typ = None; acc = collections.defaultdict(lambda: collections.defaultdict(float))
    for line in text:
        if line.startswith('EXCLUDE_OBJECT_START'):
            obj = line.split('NAME=')[1].split()[0]; continue
        if line.startswith('EXCLUDE_OBJECT_END'):
            obj = None; continue
        if line.startswith(';TYPE:'):
            typ = line[6:].strip(); continue
        if line[:3] in ('G1 ', 'G0 ', 'G2 ', 'G3 ') and ' E' in line:
            m = re.search(r' E(-?[0-9.]+)', line)
            if m:
                acc[obj or '<none>'][typ or '<none>'] += float(m.group(1))
    out = {}
    for o, types in acc.items():
        model = sum(v for t, v in types.items() if t not in EXCLUDE and 'upport' not in t)
        support = sum(v for t, v in types.items() if 'upport' in t)
        other = sum(v for t, v in types.items() if t in EXCLUDE)
        out[o] = dict(model_g=round(model * g_per_mm, 3), support_g=round(support * g_per_mm, 3),
                      excluded_g=round(other * g_per_mm, 3), types={t: round(v * g_per_mm, 3) for t, v in types.items()})
    s = sum(v['model_g'] + v['support_g'] + v['excluded_g'] for v in out.values())
    return dict(file=str(path), filament_density_g_cm3=dens, filament_diameter_mm=diam,
                header_total_g=total_g, parsed_total_g=round(s, 2), objects=out)

if __name__ == '__main__':
    res = {k: parse(p) for k, p in FILES.items()}
    Path(__file__).with_name('slicer-part-masses.json').write_text(json.dumps(res, indent=1) + '\n')
    for k, r in res.items():
        print(k, 'header', r['header_total_g'], 'parsed', r['parsed_total_g'])
        for o, v in r['objects'].items(): print('   ', o, v['model_g'], 'support', v['support_g'])
