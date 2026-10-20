"""Write the V1.24 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.24 is the two-half ankle, one Orange plate (print/ankle-halves-20261020/make_halves.py). Shawn 2026-10-20 on the printed
V1.22 split ankle: the base and side look fragile, their supports have to be removed with care, and the two pairs of screw
posts catch the servo wire; he never fitted the two M2 x 8 and the ankle worked. Each ankle is now the stock one-piece
bracket cut in half at mid shaft:
  ankle_outer_{side}  the plate on the servo horn (four M2 x 4 as before) and half the foot block: replaces the bracket
  ankle_inner_{side}  the plate on the V1.22 sleeve and the other half of the foot block (sleeve lip raised to 1.2 mm; a
                      45 deg teardrop roof on the pocket so it prints on its heel chamfer without support in the pocket)
The foot holds both halves: its socket wraps them and the toe M2 x 6 TAP sits on the cut. The V1.22 black sleeves and yellow
slip-fit feet are printed and stay. The outer rows replace the printed stock objects 20/22 (copy-manifest.json, the
brackets); the inner rows are additions, as the V1.22 base and side rows were. Print poses come from
print/ankle-halves-20261020/poses/poses.json (sourceToPrint from STL/*-local.stl, chosen by native slicing on both machines).

The plate is one row centred on the bed (128, 128), 12 mm gap. Profiles and baseline stock come from the released
manifest-V1.20.json (pinned by sha256), as for V1.22.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.24.json]
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
GAP_MM = 12.0
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
                  'from 0.25-0.5 mm to 1.2 mm and a 45 deg teardrop roof on the pocket and lip bore (the sleeve keeps 270 deg of round bore, the '
                  'whole lower half included), and the other half of the foot block. It slides along the shaft onto the sleeve '
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
        changeReason=reason, supersedes=(f'printed {stock} and the V1.22 ankle base' if kind == 'outer' else 'the V1.22 ankle side'),
        incrementalEvidence=ref(HALVES / 'halves-check.json'),
        evidenceAlso=[ref(HALVES / 'make_halves.py'), ref(HALVES / 'poses' / 'poses.json')],
        **({'objectSettings': dict(pose['objectSettings']), 'objectSettingsReason': pose['objectSettingsReason']} if pose.get('objectSettings') else {}),
        **pose.get('brim', {}),   # brimInsideHullAllowance* (outer: stock notch) / brimAlongSupportReason (inner): poses/decisions.json
    )


def build_parts():
    poses = json.loads((HALVES / 'poses' / 'poses.json').read_text()); check = json.loads((HALVES / 'halves-check.json').read_text())
    assert check['passed'] is True
    return [half_row(k, s, poses, check) for s in ('left', 'right') for k in ('outer', 'inner')]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.24.json'); a = ap.parse_args()
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
    m['retiredParts'] = [dict(key=f'ankle_{p}_{s}_V1.22', stockId=STOCK[s][1], path=str((REL / 'retired' / f'ankle_{p}_{s}-V1.22.stl').resolve()),
                              reason=f'V1.22 split-ankle {"base" if p == "base" else "side"}: thin screw posts that catch the servo wire; replaced by ankle_{"outer" if p == "base" else "inner"}_{s}')
                         for s in ('left', 'right') for p in ('base', 'cheek')]
    m['version'] = 'V1.24'
    m['prototypeScope'] = ('V1.24 delta package, the two-half ankle: one Orange plate with the outer and inner halves of both ankles. '
                           'V1.22 is printed (Shawn 2026-10-20); its black sleeves and yellow slip-fit feet stay.')
    m['knownFitBoundary'] = ('The two halves meet 0.2 mm apart at the cut; the foot socket (0.15-0.19 mm play to the stock envelope) and the toe '
                             'M2 x 6 hold them. The sleeve keeps about 0.4 mm of diametral running clearance. Printed sizes are not measured; '
                             'if the foot is tight on the two halves, sand the socket walls of the foot, never force it. Not fitted yet.')
    dc = m['deliveryContract']
    dc.update(colors=['Orange'], fileCount=2,
              baseline='printed V1.8 set, the V1.9 Orange plate, V1.17, V1.18, V1.20, the V1.21 molds and V1.22 (printed by 2026-10-20); V1.19 and V1.23 never printed',
              supersedes=['the printed V1.22 ankle bases and ankle sides (and the stock ankle brackets community-66 and community-64 they replaced)'],
              status='INCREMENTAL_REPRINT')
    a.out.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(out=str(a.out), parts=[(p['key'], p['color'], p['poseCheck']['bedContactMm2'], p['poseCheck']['printSizeMm']) for p in parts],
                          placements=placements), indent=1))


if __name__ == '__main__':
    main()
