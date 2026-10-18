"""V1.6 final native review for one colour/machine: per-object first layer (release pipeline parser), ETA, grams, and
support extrusion inside every support-blocker region (plus the OpenRB tray lip slots), for the final slice and for the
file already being printed. Read-only on all inputs; writes review/<Color>_<Machine>-review.json."""
import sys, json, re, math
from pathlib import Path
import numpy as np
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009')
import release_pipeline as r
F = Path(__file__).resolve().parents[1]
D = Path.home() / 'Downloads/zhengxia_MicroDuck_V1.6_now'
V15 = Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/15-COMPLETE-INCREMENTAL-20261009/run/delivery')
PRINTING = {
    ('Yellow', 'Bambu'): D / 'yellow-flat/zhengxia_V1.6_Yellow_Bambu-X1C_1h56m.gcode.3mf',
    ('Yellow', 'Elegoo'): D / 'yellow-flat/zhengxia_V1.6_Yellow_Elegoo-Centauri-Carbon_1h41m.gcode',
    ('White', 'Bambu'): D / 'zhengxia_V1.5_White_Bambu-X1C_19m.gcode.3mf',
    ('White', 'Elegoo'): V15 / 'zhengxia_V1.5_White_Elegoo-Centauri-Carbon_15m.gcode',
    ('Orange', 'Bambu'): D / 'orange-flat/zhengxia_V1.6_Orange_Bambu-X1C_2h40m.gcode.3mf',
    ('Orange', 'Elegoo'): D / 'orange-flat/zhengxia_V1.6_Orange_Elegoo-Centauri-Carbon_2h57m.gcode',
    ('Black', 'Bambu'): Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.6/run/native/Black_Bambu/sliced.3mf'),
    ('Black', 'Elegoo'): D / 'zhengxia_V1.6_Black_Elegoo-Centauri-Carbon_2h34m.gcode'}

def gcode(p):
    p = Path(p)
    if p.suffix == '.3mf':
        g, _, _ = r.native_payload(p); return g
    return p.read_bytes()

def grams(g, machine):
    pat = r'total filament weight \[g\]\s*:\s*([\d.]+)' if machine == 'Bambu' else r'total filament used \[g\]\s*=\s*([\d.]+)'
    return float(re.search(pat, g.decode(errors='replace'))[1])

def review_boxes(prep, row):
    """Axis-aligned print-frame regions: each support blocker transformed with its owner, plus the tray lip slots."""
    parts = {p['key']: p for p in prep['parts']}; out = {}
    manifest = r.read(prep['manifest']['path']); src = {p['key']: p for p in manifest['parts']}
    for pl in row['placements']:
        key = pl['key']; T = np.array(parts[key]['sourceToPrint']); T[2, 3] += parts[key]['dropToBedMm']
        for i, b in enumerate(x for x in src[key].get('supportBlockers', []) if row['machine'] in x.get('machines', list(r.MACHINES))):
            m = r.load_mesh(r.bound(b), T); lo, hi = m.bounds + np.array(pl['translation'])
            out[f'{key}:blocker{i + 1}:{Path(b["path"]).stem}'] = [lo.tolist(), hi.tolist()]
        if key == 'openrb_tray':
            tx, ty, _ = pl['translation']
            for nm, (y0, y1) in (('trayLipSlotLeft', (21.8, 27.1)), ('trayLipSlotRight', (7.3, 12.6))):
                out[nm] = [[70.0 + tx, y0 + ty, 5.0], [72.75 + tx, y1 + ty, 6.95]]
    return out

def support_in_boxes(g, machine, cfg, B):
    off = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0., 0.]
    xyz = [0., 0., 0.]; kind = ''; relative = True; e = 0.; cnt = {k: 0 for k in B}; length = {k: 0.0 for k in B}
    for line in g.decode(errors='replace').splitlines():
        if line.startswith(('; FEATURE:', ';TYPE:')): kind = line.split(':', 1)[1].strip().lower()
        if line.startswith('M82'): relative = False
        if line.startswith('M83'): relative = True
        if line.startswith('G92 '):
            m = re.search(r'E([-+\d.]+)', line)
            if m: e = float(m[1])
        if not re.match(r'^G[0123] ', line): continue
        v = {k: float(t) for k, t in re.findall(r'([XYZE])([-+]?\d*\.?\d+)', line.split(';')[0])}
        end = [v.get(k, xyz[i]) for i, k in enumerate('XYZ')]; de = v.get('E', 0) if relative else v.get('E', e) - e
        if 'E' in v: e = v['E'] if not relative else e + v['E']
        if de > 0 and 'support' in kind and end[:2] != xyz[:2]:
            for k, (lo, hi) in B.items():
                for f in (0.0, 0.5, 1.0):
                    x = xyz[0] + f * (end[0] - xyz[0]) + off[0]; y = xyz[1] + f * (end[1] - xyz[1]) + off[1]; z = end[2]
                    if lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1] and lo[2] <= z <= hi[2]:
                        cnt[k] += 1; length[k] += math.hypot(end[0] - xyz[0], end[1] - xyz[1]); break
        xyz = end
    return {k: dict(supportSegments=cnt[k], supportLengthMm=round(length[k], 2)) for k in B}

def readback(g, project, machine, cfg, B):
    first, foot = r.first_layer(g, project, machine); secs = r.time_seconds(g, machine)
    return dict(estimatedSeconds=secs, filamentGrams=grams(g, machine), objects=len(first),
                firstLayer={x['name']: dict(modelAreaMm2=round(x['model_area_mm2'], 2), islands=x['modelIslands'], supportAreaMm2=round(x['support_area_mm2'], 2)) for x in first},
                insideBed=foot['insideBed'], minConservativeGapMm=round(min([p['conservativeGapMm'] for p in foot['pairs']] or [99]), 2),
                supportInReviewBoxes=support_in_boxes(g, machine, cfg, B))

def review(color, machine):
    prepp = F / 'run/preparation.json'; prep = r.read(prepp); row = next(x for x in prep['rows'] if x['color'] == color and x['machine'] == machine)
    project = r.bound(row['project']); res = r.read(F / f'run/native/{color}_{machine}/result.json'); arch = r.bound(res['archive'])
    g, cfg, _ = r.native_payload(arch); assert r.digest(g) == res['gcodeSha256']; r.check_profile(cfg, machine)
    B = review_boxes(prep, row); new = readback(g, project, machine, cfg, B)
    ref = PRINTING[(color, machine)]; old = readback(gcode(ref), project, machine, cfg, B)
    nobj = sum(p['quantity'] for p in prep['parts'] if p['color'] == color)
    area = {k: dict(final=new['firstLayer'][k]['modelAreaMm2'], printing=old['firstLayer'].get(k, {}).get('modelAreaMm2'),
                    relDiff=round(abs(new['firstLayer'][k]['modelAreaMm2'] - old['firstLayer'].get(k, {}).get('modelAreaMm2', 0)) / new['firstLayer'][k]['modelAreaMm2'], 4)) for k in new['firstLayer']}
    blockers_clear = all(v['supportSegments'] <= old['supportInReviewBoxes'][k]['supportSegments'] or v['supportSegments'] == 0 for k, v in new['supportInReviewBoxes'].items())
    tray_clear = all(new['supportInReviewBoxes'][k]['supportSegments'] == 0 for k in ('trayLipSlotLeft', 'trayLipSlotRight') if k in new['supportInReviewBoxes'])
    ok = new['objects'] == nobj == old['objects'] and set(new['firstLayer']) == set(old['firstLayer']) and all(a['relDiff'] < 0.05 for a in area.values()) and new['insideBed'] and blockers_clear and tray_clear
    out = dict(color=color, machine=machine, archive=r.ref(arch), gcodeSha256=res['gcodeSha256'], printingReference=r.ref(ref),
               final=new, printing=old, firstLayerComparison=area, reviewBoxes=B, blockerRegionsNoWorseThanPrinting=blockers_clear, trayLipSlotsSupportFree=tray_clear, passed=bool(ok))
    r.write(F / f'review/{color}_{machine}-review.json', out); return out

if __name__ == '__main__':
    o = review(sys.argv[1], sys.argv[2])
    print(json.dumps(dict(color=o['color'], machine=o['machine'], passed=o['passed'], secs=[o['final']['estimatedSeconds'], o['printing']['estimatedSeconds']], grams=[o['final']['filamentGrams'], o['printing']['filamentGrams']], objects=[o['final']['objects'], o['printing']['objects']], minGap=o['final']['minConservativeGapMm'])))
    for k, a in o['firstLayerComparison'].items(): print('   first layer', k, a)
    for k, v in o['final']['supportInReviewBoxes'].items(): print('   support', k, 'final', v['supportSegments'], 'printing', o['printing']['supportInReviewBoxes'][k]['supportSegments'])
