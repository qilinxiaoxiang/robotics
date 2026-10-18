"""V1.9 native review (adapted from release-V1.8/scripts/review_v18.py) for one colour/machine: per-object first layer (release pipeline parser), ETA, grams, brim
extrusion, and support extrusion inside every support-blocker review box. A part that was also in the V1.8 (or V1.7 / V1.6 final)
slice is compared with that accepted slice of the same part (head_cap_v19 is compared with the V1.8 head_cap); a new part (no earlier slice) must show a first-layer
model area of at least 80 % of its manifest flat contact. Read-only on all inputs; writes review/<Color>_<Machine>-review.json.

    /tmp/microduck-cad-venv/bin/python scripts/review_v19.py <run-dir> Orange Bambu
"""
import sys, json, re
from pathlib import Path
sys.dont_write_bytecode = True
V16 = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.6-final')
V17 = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.7')
V18 = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.8')
EARLIER_KEY = {'head_cap_v19': 'head_cap'}
sys.path.insert(0, str(V16 / 'scripts'))
import review_final as rf  # noqa: E402  (parsers shared with the V1.6 review)
r = rf.r


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


def earlier_first_layer(key, color, machine):
    """Accepted earlier slice of the same part (V1.8, else V1.7, else V1.6 final): first-layer model area and
    the support counts inside that release's review boxes for this part."""
    key = EARLIER_KEY.get(key, key)
    for base in (V18, V17, V16):
        prep = base / 'run/preparation.json'
        if not prep.exists():
            continue
        p = r.read(prep)
        if not any(x['key'] == key and x['color'] == color for x in p['parts']):
            continue
        res = r.read(base / f'run/native/{color}_{machine}/result.json'); g, _, _ = r.native_payload(Path(res['archive']['path']))
        row = next(x for x in p['rows'] if x['color'] == color and x['machine'] == machine)
        first, _ = r.first_layer(g, r.bound(row['project']), machine)
        area = {x['name']: round(x['model_area_mm2'], 2) for x in first}
        rev = base / f'review/{color}_{machine}-review.json'
        boxes = r.read(rev)['final']['supportInReviewBoxes'] if rev.exists() else {}
        return dict(release=base.name, area=area.get(f'{key}_1'), supportBoxes={k: v for k, v in boxes.items() if k.startswith(key + ':')})
    return None


def blocker_meshes(prep, row):
    """Each support blocker as a print-frame mesh (owner pose + plate translation), keyed like rf.review_boxes."""
    import numpy as np
    parts = {p['key']: p for p in prep['parts']}; manifest = r.read(prep['manifest']['path']); src = {p['key']: p for p in manifest['parts']}; out = {}
    for pl in row['placements']:
        key = pl['key']; T = np.array(parts[key]['sourceToPrint']); T[2, 3] += parts[key]['dropToBedMm']
        for i, b in enumerate(x for x in src[key].get('supportBlockers', []) if row['machine'] in x.get('machines', list(r.MACHINES))):
            m = r.load_mesh(r.bound(b), T); m.apply_translation(pl['translation']); out[f'{key}:blocker{i + 1}:{Path(b["path"]).stem}'] = m
    return out


def support_points_in_boxes(g, machine, cfg, B):
    """Like rf.support_in_boxes but returns the sampled support points per box, for a containment test."""
    import math
    off = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0., 0.]
    xyz = [0., 0., 0.]; kind = ''; relative = True; e = 0.; pts = {k: [] for k in B}
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
                hit = False
                for f in (0.0, 0.5, 1.0):
                    x = xyz[0] + f * (end[0] - xyz[0]) + off[0]; y = xyz[1] + f * (end[1] - xyz[1]) + off[1]; z = end[2]
                    if lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1] and lo[2] <= z <= hi[2]:
                        pts[k].append((x, y, z)); hit = True
                if hit: break
        xyz = end
    return pts


def review(run, color, machine):
    F = Path(run).resolve()
    prep = r.read(F / 'preparation.json'); row = next(x for x in prep['rows'] if x['color'] == color and x['machine'] == machine)
    manifest = r.read(prep['manifest']['path']); src = {p['key']: p for p in manifest['parts']}
    project = r.bound(row['project']); res = r.read(F / f'native/{color}_{machine}/result.json'); arch = r.bound(res['archive'])
    g, cfg, _ = r.native_payload(arch); assert r.digest(g) == res['gcodeSha256']; r.check_profile(cfg, machine)
    B = rf.review_boxes(prep, row); new = rf.readback(g, project, machine, cfg, B); new['brimExtrusionMm'] = brim_mm(g)
    parts = [p for p in prep['parts'] if p['color'] == color]
    comparison = {}; ok_parts = True
    for p in parts:
        name = f'{p["key"]}_1'; fl = new['firstLayer'].get(name)
        earlier = earlier_first_layer(p['key'], color, machine)
        entry = dict(v19=fl['modelAreaMm2'] if fl else None, islands=fl['islands'] if fl else None, manifestFlatContactMm2=round(p['flatContactAreaMm2'], 2))
        if earlier and earlier['area']:
            entry.update(earlierRelease=earlier['release'], earlier=earlier['area'], relDiff=round(abs(fl['modelAreaMm2'] - earlier['area']) / max(earlier['area'], 1e-9), 4))
            good = fl is not None and entry['relDiff'] < 0.05
        else:
            entry.update(earlierRelease=None, rule='new part: first-layer model area >= 0.8 x manifest flat contact')
            good = fl is not None and fl['modelAreaMm2'] >= 0.8 * p['flatContactAreaMm2']
        entry['passed'] = bool(good); ok_parts &= bool(good); comparison[name] = entry
    # Support inside a blocker box: zero, or no more than the accepted earlier slice of the same part in the same box.
    support = {}
    support_free = True
    meshes = blocker_meshes(prep, row); samples = support_points_in_boxes(g, machine, cfg, B)
    for k, v in new['supportInReviewBoxes'].items():
        # The review box is the blocker's bounding box and may hold legitimate support beside the blocked feature; the
        # blocker itself (its mesh volume) must hold none.
        import numpy as _np
        inside = int(meshes[k].contains(_np.array(samples[k])).sum()) if samples[k] else 0
        v = dict(v, supportSamplesInsideBlockerMesh=inside)
        key = k.split(':')[0]; earlier = earlier_first_layer(key, color, machine) if v['supportSegments'] else None
        allowed = 0
        if earlier:
            # match by blocker stem (the box naming is key:blockerN:stem in both releases)
            stem = k.split(':')[-1]
            for ek, ev in earlier['supportBoxes'].items():
                if ek.split(':')[-1].replace('-shifted', '').replace('-v18-world', '').replace('-print', '').replace('-world', '') == stem.replace('-shifted', '').replace('-v18-world', '').replace('-print', '').replace('-world', ''):
                    allowed = max(allowed, ev['supportSegments'])
        # Pass: no support in the box, none inside the blocker volume, or no more than the accepted earlier slice of the
        # same part allowing 10 % + 2 segments of tree-support noise (the V1.6 review accepted support beside the
        # cap-through holes; a changed mesh elsewhere on the part re-routes a branch or two).
        tolerance = int(allowed * 1.10 + 2) if allowed else 0
        passed = v['supportSegments'] == 0 or inside == 0 or v['supportSegments'] <= tolerance
        support[k] = dict(v, allowedFromEarlierSlice=allowed, allowedWithTolerance=tolerance, passed=bool(passed)); support_free &= bool(passed)
    brim_needed = color in {k.split('_')[0] for k in manifest.get('processOverrides', {})}
    brim_ok = (new['brimExtrusionMm'] > 0) if brim_needed else True
    nobj = sum(p['quantity'] for p in parts)
    ok = new['objects'] == nobj and new['insideBed'] and support_free and brim_ok and ok_parts
    out = dict(color=color, machine=machine, archive=r.ref(arch), gcodeSha256=res['gcodeSha256'], final=new, firstLayerComparison=comparison,
               reviewBoxes=B, supportInReviewBoxes=support, reviewRegionsSupportFree=support_free, brimRequired=brim_needed, brimPresent=brim_ok,
               objectsExpected=nobj, passed=bool(ok))
    (F.parent / 'review').mkdir(exist_ok=True)
    r.write(F.parent / f'review/{color}_{machine}-review.json', out); return out


if __name__ == '__main__':
    o = review(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(dict(color=o['color'], machine=o['machine'], passed=o['passed'], secs=o['final']['estimatedSeconds'],
                          grams=o['final']['filamentGrams'], brimMm=o['final']['brimExtrusionMm'], objects=o['final']['objects'])))
    for k, a in o['firstLayerComparison'].items(): print('   first layer', k, a)
    for k, v in o['supportInReviewBoxes'].items(): print('   support', k, {a: b for a, b in v.items() if a != 'supportLengthMm'})
