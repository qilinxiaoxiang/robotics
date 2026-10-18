"""V1.6 native readback: actual first layer (release pipeline parser), ETA, grams, and support extrusion inside
named 3D review boxes (tray PCB slot under the front lips, cap notch/hood edit box) per sliced archive."""
import sys, json, re, math, zipfile
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009')
import release_pipeline as r
R = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.6')
def boxes(prep, color):
    tr = {p['key']: p['translation'] for p in prep['rows'][0]['placements']} if False else None
    row = next(x for x in prep['rows'] if x['color'] == color)
    t = {p['key']: p['translation'] for p in row['placements']}
    out = {}
    if 'openrb_tray' in t:
        tx, ty, _ = t['openrb_tray']
        # print-frame slot under each lip: x 70.0..72.75 (lip to post), y 21.8..27.1 / 7.3..12.6, z 5.0..6.9 (pad top to lip underside)
        for nm, (y0, y1) in (('trayLipSlotLeft', (21.8, 27.1)), ('trayLipSlotRight', (7.3, 12.6))):
            out[nm] = [[70.0 + tx, y0 + ty, 5.0], [72.75 + tx, y1 + ty, 6.95]]
        out['trayWholeFootprint'] = [[tx, ty, 0.0], [74.55 + tx, 34.4 + ty, 12.0]]
    if 'head_cap' in t:
        tx, ty, _ = t['head_cap']; part = next(p for p in prep['parts'] if p['key'] == 'head_cap'); dz = part['dropToBedMm']
        lo, hi = [48.167, -32.109, 42.969], [67.771, -13.811, 68.244]   # cap notch/hood edit box, print frame (cap-notch-report)
        out['capNotchHoodEditBox'] = [[lo[0] + tx, lo[1] + ty, lo[2] + dz], [hi[0] + tx, hi[1] + ty, hi[2] + dz]]
    return out
def support_in_boxes(g, machine, cfg, B):
    off = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0., 0.]
    xyz = [0., 0., 0.]; kind = ''; relative = True; e = 0.; cnt = {k: 0 for k in B}; length = {k: 0.0 for k in B}; zs = {k: set() for k in B}
    for line in g.decode().splitlines():
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
                        cnt[k] += 1; length[k] += math.hypot(end[0] - xyz[0], end[1] - xyz[1]); zs[k].add(round(z, 2)); break
        xyz = end
    return {k: dict(supportSegments=cnt[k], supportLengthMm=round(length[k], 2), layers=len(zs[k]), box=B[k]) for k in B}
def grams(g, machine):
    pat = r'total filament weight \[g\]\s*:\s*([\d.]+)' if machine == 'Bambu' else r'total filament used \[g\]\s*=\s*([\d.]+)'
    return float(re.search(pat, g.decode())[1])
def review(color, machine):
    prep = r.read(R / 'run/preparation.json'); row = next(x for x in prep['rows'] if x['color'] == color and x['machine'] == machine)
    res = r.read(R / f'run/native/{color}_{machine}/result.json'); arch = r.bound(res['archive']); g, cfg, imgs = r.native_payload(arch)
    assert r.digest(g) == res['gcodeSha256']; r.check_profile(cfg, machine)
    first, foot = r.first_layer(g, r.bound(row['project']), machine)
    secs = r.time_seconds(g, machine); minutes = math.ceil(secs / 60); label = (f'{minutes // 60}h' if minutes >= 60 else '') + f'{minutes % 60}m'
    sup = support_in_boxes(g, machine, cfg, boxes(prep, color))
    nobj = sum(p['quantity'] for p in prep['parts'] if p['color'] == color)
    ok = len(first) == nobj and all(x['model_area_mm2'] > 0 for x in first) and foot['insideBed']
    for k in ('trayLipSlotLeft', 'trayLipSlotRight'):
        if k in sup: ok = ok and sup[k]['supportSegments'] == 0
    if 'capNotchHoodEditBox' in sup:
        import cap_support_contacts as C
        sup['capNotchHoodEditBox']['notchCheck'] = C.check(machine, sup['capNotchHoodEditBox']['box'], color); ok = ok and sup['capNotchHoodEditBox']['notchCheck']['passed']
    out = dict(color=color, machine=machine, archive=r.ref(arch), gcodeSha256=res['gcodeSha256'], estimatedSeconds=secs, filenameTime=label, filamentGrams=grams(g, machine),
               objects=nobj, nativeFirstLayer=first, footprint=foot, supportInReviewBoxes=sup, passed=bool(ok))
    r.write(R / f'review/{color}_{machine}-review.json', out); return out
if __name__ == '__main__':
    o = review(sys.argv[1], sys.argv[2])
    print(json.dumps({k: o[k] for k in ('color', 'machine', 'estimatedSeconds', 'filenameTime', 'filamentGrams', 'passed')}))
    for x in o['nativeFirstLayer']: print('  ', x['name'], round(x['model_area_mm2'], 1), 'islands', x['modelIslands'], 'support', round(x['support_area_mm2'], 1))
    for k, v in o['supportInReviewBoxes'].items(): print('  ', k, v['supportSegments'], v['supportLengthMm'], v['layers'], v.get('notchCheck', ''))
    print('   min pair gap', round(min([p['conservativeGapMm'] for p in o['footprint']['pairs']] or [99]), 2))
