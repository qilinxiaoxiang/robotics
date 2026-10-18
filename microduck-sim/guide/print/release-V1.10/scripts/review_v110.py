"""V1.10 native review (adapted from release-V1.9/scripts/review_v19.py) for one colour/machine: per-object first layer
(release pipeline parser), ETA, grams, brim extrusion, and support extrusion in three print-frame regions:

  rear_frame:topWallUnderside  inside the box under the 61.7 x 18.9 mm top-wall bridge (world x -65.9..-47,
                               |y| <= 30.85, z -42.8..45.3); support must be present and reach the bridge
  rear_frame:lipUnderside      under the 7.5 mm lip (world x -45..-37.5, |y| <= 13.2, z -44..27.3); support must be
                               present and reach the lip
  rear_lid:footprint           the lid's whole footprint, any height; must hold no support

Both parts are new (no earlier slice), so each first-layer model area must be at least 0.8 x its manifest flat
contact. Read-only on all inputs; writes review/<Color>_<Machine>-review.json.

    /tmp/microduck-cad-venv/bin/python scripts/review_v110.py <run-dir> Orange Bambu
"""
import sys, json, re, math
from pathlib import Path
import numpy as np
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.6-final/scripts')
import review_final as rf  # noqa: E402  (parsers shared with the V1.6/V1.9 reviews)
r = rf.r

# world-frame regions (robot frame, mm): [lo, hi]
WORLD_REGIONS = {
    'rear_frame:topWallUnderside': ('rear_frame', [[-65.9, -30.85, -42.8], [-47.0, 30.85, 45.3]], 'present', 45.3),
    'rear_frame:lipUnderside': ('rear_frame', [[-45.0, -13.2, -44.0], [-37.5, 13.2, 27.3]], 'present', 27.3),
}
REACH_TOLERANCE_MM = 0.8   # top Z gap 0.2 plus up to three 0.2 mm interface layers under the overhang


def brim_mm(g):
    kind = ''; xy = None; total = 0.0
    for line in g.decode(errors='replace').splitlines():
        if line.startswith(('; FEATURE:', ';TYPE:')):
            kind = line.split(':', 1)[1].strip().lower()
        if not re.match(r'^G[0123] ', line):
            continue
        v = {k: float(t) for k, t in re.findall(r'([XYE])([-+]?\d*\.?\d+)', line.split(';')[0])}
        end = (v.get('X', xy[0] if xy else 0.0), v.get('Y', xy[1] if xy else 0.0))
        if xy and 'brim' in kind and v.get('E', 0) > 0:
            total += ((end[0] - xy[0]) ** 2 + (end[1] - xy[1]) ** 2) ** 0.5
        xy = end
    return round(total, 1)


def regions(prep, row):
    """Print-plate boxes: each world region through its owner's sourceToPrint, drop and plate translation; plus the lid footprint."""
    parts = {p['key']: p for p in prep['parts']}; out = {}
    place = {pl['key']: pl for pl in row['placements']}
    for name, (key, (lo, hi), _, _) in WORLD_REGIONS.items():
        T = np.array(parts[key]['sourceToPrint']); T[2, 3] += parts[key]['dropToBedMm']
        c = np.array([[x, y, z, 1.0] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]) @ T.T
        c = c[:, :3] + np.array(place[key]['translation'])
        out[name] = [c.min(0).tolist(), c.max(0).tolist()]
    b = np.array(parts['rear_lid']['bounds']) + np.array(place['rear_lid']['translation'])
    out['rear_lid:footprint'] = [[b[0, 0] - 0.5, b[0, 1] - 0.5, 0.0], [b[1, 0] + 0.5, b[1, 1] + 0.5, 300.0]]
    return out


def support_in(g, machine, cfg, B):
    """Support extrusion per box: segments, XY length and the highest support layer z."""
    off = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0., 0.]
    xyz = [0., 0., 0.]; kind = ''; relative = True; e = 0.
    res = {k: dict(supportSegments=0, supportLengthMm=0.0, supportTopZMm=None) for k in B}; total = 0.0
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
            seg = math.hypot(end[0] - xyz[0], end[1] - xyz[1]); total += seg
            for k, (lo, hi) in B.items():
                for f in (0.0, 0.5, 1.0):
                    x = xyz[0] + f * (end[0] - xyz[0]) + off[0]; y = xyz[1] + f * (end[1] - xyz[1]) + off[1]; z = end[2]
                    if lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1] and lo[2] <= z <= hi[2]:
                        s = res[k]; s['supportSegments'] += 1; s['supportLengthMm'] += seg
                        s['supportTopZMm'] = z if s['supportTopZMm'] is None else max(s['supportTopZMm'], z); break
        xyz = end
    for s in res.values(): s['supportLengthMm'] = round(s['supportLengthMm'], 1)
    return res, round(total, 1)


def review(run, color, machine):
    F = Path(run).resolve()
    prep = r.read(F / 'preparation.json'); row = next(x for x in prep['rows'] if x['color'] == color and x['machine'] == machine)
    project = r.bound(row['project']); res = r.read(F / f'native/{color}_{machine}/result.json'); arch = r.bound(res['archive'])
    manifest = r.read(prep['manifest']['path'])
    g, cfg, _ = r.native_payload(arch); assert r.digest(g) == res['gcodeSha256']; r.check_profile(cfg, machine)
    new = rf.readback(g, project, machine, cfg, {}); new.pop('supportInReviewBoxes', None); new['brimExtrusionMm'] = brim_mm(g)
    parts = [p for p in prep['parts'] if p['color'] == color]
    comparison = {}; ok_parts = True
    for p in parts:
        name = f'{p["key"]}_1'; fl = new['firstLayer'].get(name)
        good = fl is not None and fl['modelAreaMm2'] >= 0.8 * p['flatContactAreaMm2']
        comparison[name] = dict(v110=fl['modelAreaMm2'] if fl else None, islands=fl['islands'] if fl else None,
                                manifestFlatContactMm2=round(p['flatContactAreaMm2'], 2),
                                rule='new part: first-layer model area >= 0.8 x manifest flat contact', passed=bool(good))
        ok_parts &= bool(good)
    B = regions(prep, row); sup, total = support_in(g, machine, cfg, B)
    support_ok = True
    for name, s in sup.items():
        if name in WORLD_REGIONS:
            key, (lo, hi), _, underside_z = WORLD_REGIONS[name]
            T = np.array(next(p for p in parts if p['key'] == key)['sourceToPrint'])
            target = float((T @ np.array([lo[0], lo[1], underside_z, 1.0]))[2])
            s.update(rule=f'support present and its top layer within {REACH_TOLERANCE_MM} mm under the overhang (print z {target:.2f})',
                     overhangPrintZMm=round(target, 2))
            s['passed'] = bool(s['supportSegments'] > 0 and s['supportTopZMm'] is not None and s['supportTopZMm'] >= target - REACH_TOLERANCE_MM)
        else:
            s.update(rule='no support anywhere over the lid', passed=s['supportSegments'] == 0)
        support_ok &= s['passed']
    brim_needed = color in {k.split('_')[0] for k in manifest.get('processOverrides', {})}
    brim_ok = (new['brimExtrusionMm'] > 0) if brim_needed else True
    nobj = sum(p['quantity'] for p in parts)
    ok = new['objects'] == nobj and new['insideBed'] and support_ok and brim_ok and ok_parts
    out = dict(color=color, machine=machine, archive=r.ref(arch), gcodeSha256=res['gcodeSha256'], final=new, firstLayerComparison=comparison,
               supportRegions=B, supportByRegion=sup, supportExtrusionTotalMm=total, supportAsIntended=bool(support_ok),
               brimRequired=brim_needed, brimPresent=brim_ok, objectsExpected=nobj,
               slicerLog=(F / f'native/{color}_{machine}/cli.log').read_text(errors='replace').strip(), passed=bool(ok))
    (F.parent / 'review').mkdir(exist_ok=True)
    r.write(F.parent / f'review/{color}_{machine}-review.json', out); return out


if __name__ == '__main__':
    o = review(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(dict(color=o['color'], machine=o['machine'], passed=o['passed'], secs=o['final']['estimatedSeconds'],
                          grams=o['final']['filamentGrams'], brimMm=o['final']['brimExtrusionMm'], objects=o['final']['objects'],
                          supportTotalMm=o['supportExtrusionTotalMm'])))
    for k, a in o['firstLayerComparison'].items(): print('   first layer', k, a)
    for k, v in o['supportByRegion'].items(): print('   support', k, v)
    if o['slicerLog']: print('   slicer log:', o['slicerLog'][-200:])
