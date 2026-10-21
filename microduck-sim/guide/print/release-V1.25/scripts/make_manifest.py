"""Write the V1.25 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.25 is the V1.24 two-half ankle plate again (one Orange plate, print/ankle-halves-20261020/make_halves.py) with a round
sleeve bore. Shawn 2026-10-20 on the printed V1.24: the 45 deg teardrop roof of the inner half's sleeve pocket is not
wanted; keep the d15 pocket and the d14 lip bore round and let support stand in the hole. The inner halves now stand on
their toe end (local +x down on the left, -x on the right, the outer halves' pose), so the support inside the bore lands on
its heel side and the weight side prints as a vertical wall (poses/decisions.json).
  ankle_outer_{side}  unchanged from V1.24 (same STL): the plate on the servo horn and half the foot block
  ankle_inner_{side}  the plate on the V1.22 sleeve and the other half of the foot block, round bore, sleeve lip 1.2 mm
One V1.24 outer half came off the bed mid-print with the R1 4 mm brim (photo 2026-10-20 23:16); every half stands 36.5 mm
tall on 41 mm2, so every row carries an 8 mm outer brim (objectSettings) and the parts sit 20 mm apart.

Profiles and baseline stock come from the released manifest-V1.20.json (pinned by sha256), as for V1.22 and V1.24.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.25.json]
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
V120_PATH = PRINT / 'release-V1.20/manifest-V1.20.json'
V120_SHA = 'b912b3c7eea53f81b96ccf861f4f04cee46eeffe8bf42259f75b0a839b8ce171'
HALVES = PRINT / 'ankle-halves-20261020'
PLATES = {'Orange': ['ankle_outer_left', 'ankle_inner_left', 'ankle_outer_right', 'ankle_inner_right']}
GAP_MM = 20.0
BRIM = {'brim_type': 'outer_only', 'brim_width': '8', 'brim_object_gap': '0.1'}
BRIM_REASON = ('Every half stands 36.5 mm tall on a 41 mm2 end face; one V1.24 outer half in this pose came off the bed mid-print '
               'with the R1 4 mm brim (2026-10-20), and Bambu advises a wider brim for a taller part on a smaller footprint '
               '(orientation-study/PRINT-ORIENTATION-PRACTICE.md R1). 8 mm outer brim, 0.1 mm gap.')
STOCK = {'left': ('community-66.stl', '20', 'left one-piece ankle bracket'), 'right': ('community-64.stl', '22', 'right one-piece ankle bracket')}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p); assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def printed(path, T=None):
    m = trimesh.load(path, force='mesh', process=False)
    if T is not None:
        m.apply_transform(np.asarray(T, dtype=float))
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    area = float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
    return area, (m.bounds[1] - m.bounds[0]).round(2).tolist(), m.bounds[0]


def half_row(kind, side, poses, check):
    stock, sid, stock_what = STOCK[side]
    stl = HALVES / 'STL' / f'{side}-{kind}-local.stl'
    entry = poses['parts'][f'{side}_{kind}']
    assert entry['localStl']['sha256'] == sha(stl), f'{stl} changed since the pose study'
    pose = entry['chosen']; T = pose['sourceToPrint']
    area, size, _ = printed(stl, T)
    src = ref(stl); c = check['sides'][side]
    reason = {
        'outer': (f'Replaces the printed {stock} (stock object {sid}, the {stock_what}) together with ankle_inner_{side}; it also replaces the '
                  'V1.22 ankle base. Shawn 2026-10-20: the V1.22 base and side look fragile, need careful support removal, and their two pairs '
                  'of screw posts catch the servo wire. This is the stock bracket for local z < -16.1 (the cut at the toe screw axis, set back '
                  '0.1 mm): the plate on the servo horn with the four M2 x 4 seats as before and half of the foot block. The link-servo-sleeve '
                  'package sits straight down into it (halves-check.json packageLiftOutOfOuterClearMm 30). The V1.22 slip-fit foot seats on '
                  'both halves exactly as on the stock bracket (footSeat play, drop contact) and holds them together.'),
        'inner': (f'New part, with ankle_outer_{side} replacing the printed {stock} (stock object {sid}); it also replaces the V1.22 ankle side. '
                  'The stock bracket for local z > -15.9: the plate whose pocket runs on the 10.4 mm V1.22 sleeve, with its sleeve lip raised '
                  'from 0.25-0.5 mm to 1.2 mm, the d15 pocket and d14 lip bore round as on the stock bracket (V1.24 had a 45 deg teardrop roof; '
                  'Shawn 2026-10-20 wants the bore round with support in it), and the other half of the foot block. It prints on its toe end '
                  'with support inside the bore on its heel side. It slides along the shaft onto the sleeve '
                  f'(innerOffAlongShaftClearMm {c["innerOffAlongShaftClearMm"]}); the foot socket captures it (1 mm apart overlaps the foot by '
                  f'{c["footCapture"]["innerApart1mm"]} mm3) and the toe M2 x 6, on the cut, holds it down. No screw, post or tab of its own.'),
    }[kind]
    return dict(
        key=f'ankle_{kind}_{side}', color='Orange', quantity=1, decision='replacement' if kind == 'outer' else 'addition',
        replacesStockIds=[sid] if kind == 'outer' else [],
        path=src['path'], sha256=src['sha256'],
        sourceFrame=f'ankle-halves-20261020 local frame of the {side} ankle {kind} half (mm; motor shaft = local z, up = local y)',
        sourceToPrint=T, flatContact={'minimumAreaMm2': round(0.95 * area, 1)},
        poseOrigin=f'{pose["poseName"]}: {pose["why"]}',
        poseCheck=dict(printStl=src, bedContactMm2=round(area, 2), printSizeMm=size,
                       note=f'print pose from ankle-halves-20261020/poses/poses.json ({pose["poseName"]}), dropped to the bed'),
        changeReason=reason, supersedes=(f'the V1.24 ankle_outer_{side} print (same part)' if kind == 'outer' else f'the V1.24 ankle_inner_{side} print (teardrop pocket)'),
        incrementalEvidence=ref(HALVES / 'halves-check.json'),
        evidenceAlso=[ref(HALVES / 'make_halves.py'), ref(HALVES / 'poses' / 'poses.json')],
        objectSettings=dict(BRIM), objectSettingsReason=BRIM_REASON,
        **pose.get('brim', {}),   # brimInsideHullAllowance* (outer: stock notch) / brimAlongSupportReason (inner): poses/decisions.json
    )


def build_parts():
    poses = json.loads((HALVES / 'poses' / 'poses.json').read_text()); check = json.loads((HALVES / 'halves-check.json').read_text())
    assert check['passed'] is True
    return [half_row(k, s, poses, check) for s in ('left', 'right') for k in ('outer', 'inner')]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.25.json'); a = ap.parse_args()
    assert sha(V120_PATH) == V120_SHA, 'manifest-V1.20.json changed since V1.22 was set up'
    m = json.loads(V120_PATH.read_text())
    parts = build_parts(); by = {p['key']: p for p in parts}
    placements = {}
    for colour, keys in PLATES.items():
        sizes = {k: printed(by[k]['path'], by[k]['sourceToPrint']) for k in keys}
        width = sum(sizes[k][1][0] for k in keys) + GAP_MM * (len(keys) - 1)
        x0 = 128.0 - width / 2; pl = []
        for key in keys:
            _, size, lo = sizes[key]; y0 = 128.0 - size[1] / 2
            assert 18.0 <= x0 and x0 + size[0] <= 238.0 and 28.0 <= y0 and y0 + size[1] <= 238.0, (key, x0, y0, size)
            pl.append(dict(key=key, copy=1, translation=[round(x0 - float(lo[0]), 4), round(y0 - float(lo[1]), 4), 0.0]))
            x0 += size[0] + GAP_MM
        placements[colour] = pl
    m['parts'] = parts
    m['placements'] = placements
    m['processOverrides'] = {}
    m['processOverrideReason'] = 'Stock profile (brims per object by the pipeline R1 rule or the manifest objectSettings).'
    m['retiredParts'] = [dict(key=f'ankle_inner_{s}_V1.24', stockId=STOCK[s][1], path=str((REL / 'retired' / f'ankle_inner_{s}-V1.24.stl').resolve()),
                              reason=f'V1.24 inner half with the 45 deg teardrop sleeve pocket; replaced by the round-bore ankle_inner_{s}')
                         for s in ('left', 'right')]
    m['version'] = 'V1.25'
    m['prototypeScope'] = ('V1.25 delta package, the two-half ankle with a round sleeve bore: one Orange plate with the outer and inner '
                           'halves of both ankles. V1.22 and V1.24 are printed (Shawn 2026-10-20); the V1.22 black sleeves and yellow '
                           'slip-fit feet stay.')
    m['knownFitBoundary'] = ('The two halves meet 0.2 mm apart at the cut; the foot socket (0.15-0.19 mm play to the stock envelope) and the toe '
                             'M2 x 6 hold them. The sleeve keeps about 0.4 mm of diametral running clearance once the support is out of the bore and '
                             'the bore is scraped smooth. Printed sizes are not measured; '
                             'if the foot is tight on the two halves, sand the socket walls of the foot, never force it. Not fitted yet.')
    dc = m['deliveryContract']
    dc.update(colors=['Orange'], fileCount=2,
              baseline='printed V1.8 set, the V1.9 Orange plate, V1.17, V1.18, V1.20, the V1.21 molds, V1.22 and V1.24 (printed by 2026-10-20); V1.19 and V1.23 never printed',
              supersedes=['the printed V1.24 Orange plate: its teardrop-pocket inner halves, and the outer half that came off the bed'],
              status='INCREMENTAL_REPRINT')
    a.out.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(out=str(a.out), parts=[(p['key'], p['color'], p['poseCheck']['bedContactMm2'], p['poseCheck']['printSizeMm']) for p in parts],
                          placements=placements), indent=1))


if __name__ == '__main__':
    main()
