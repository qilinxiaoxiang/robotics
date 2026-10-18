"""V1.7 native review for one colour/machine: per-object first layer (release pipeline parser) against the V1.6 final
slice of the same part, ETA, grams, brim extrusion, and support extrusion inside every support-blocker region (plus the
OpenRB tray lip slots), which must be zero or no more than in the accepted V1.6 slice. Read-only on all inputs; writes review/<Color>_<Machine>-review.json.

    /tmp/microduck-cad-venv/bin/python scripts/review_v17.py Orange Bambu
"""
import sys, json, re
from pathlib import Path
sys.dont_write_bytecode = True
V16 = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.6-final')
sys.path.insert(0, str(V16 / 'scripts'))
import review_final as rf  # noqa: E402  (parsers shared with the V1.6 review)
r = rf.r
F = Path(__file__).resolve().parents[1]


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


def review(color, machine):
    prep = r.read(F / 'run/preparation.json'); row = next(x for x in prep['rows'] if x['color'] == color and x['machine'] == machine)
    project = r.bound(row['project']); res = r.read(F / f'run/native/{color}_{machine}/result.json'); arch = r.bound(res['archive'])
    g, cfg, _ = r.native_payload(arch); assert r.digest(g) == res['gcodeSha256']; r.check_profile(cfg, machine)
    B = rf.review_boxes(prep, row); new = rf.readback(g, project, machine, cfg, B); new['brimExtrusionMm'] = brim_mm(g)
    old_res = r.read(V16 / f'run/native/{color}_{machine}/result.json'); old_arch = Path(old_res['archive']['path'])
    old_g, _, _ = r.native_payload(old_arch)
    old_prep = r.read(V16 / 'run/preparation.json'); old_row = next(x for x in old_prep['rows'] if x['color'] == color and x['machine'] == machine)
    old_first, _ = r.first_layer(old_g, r.bound(old_row['project']), machine)
    old_area = {x['name']: round(x['model_area_mm2'], 2) for x in old_first}
    area = {k: dict(v17=v['modelAreaMm2'], v16=old_area.get(k), islands=v['islands']) for k, v in new['firstLayer'].items()}
    # A blocker's review box is its axis-aligned bounding box, so it can also hold legitimate support next to the blocked
    # feature (the tie-slot box spans the support under the hood). Pass: zero, or no more than the accepted V1.6 slice.
    v16_boxes = r.read(V16 / f'review/{color}_{machine}-review.json')['final']['supportInReviewBoxes']
    support_free = all(v['supportSegments'] == 0 or v['supportSegments'] <= v16_boxes.get(k, {}).get('supportSegments', -1)
                       for k, v in new['supportInReviewBoxes'].items())
    brim_ok = (new['brimExtrusionMm'] > 0) if color == 'Orange' else True
    nobj = sum(p['quantity'] for p in prep['parts'] if p['color'] == color)
    ok = new['objects'] == nobj and new['insideBed'] and support_free and brim_ok and all(
        a['v16'] and a['v17'] >= 100 for a in area.values())
    out = dict(color=color, machine=machine, archive=r.ref(arch), gcodeSha256=res['gcodeSha256'], v16Reference=r.ref(old_arch),
               final=new, firstLayerComparison=area, reviewBoxes=B, reviewRegionsSupportFree=support_free, brimPresent=brim_ok, passed=bool(ok))
    r.write(F / f'review/{color}_{machine}-review.json', out); return out


if __name__ == '__main__':
    o = review(sys.argv[1], sys.argv[2])
    print(json.dumps(dict(color=o['color'], machine=o['machine'], passed=o['passed'], secs=o['final']['estimatedSeconds'],
                          grams=o['final']['filamentGrams'], brimMm=o['final']['brimExtrusionMm'], objects=o['final']['objects'])))
    for k, a in o['firstLayerComparison'].items(): print('   first layer', k, a)
    for k, v in o['final']['supportInReviewBoxes'].items(): print('   support', k, v)
