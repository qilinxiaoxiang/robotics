"""Write the V1.22 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.22 is the ankle rework, everything unprinted on 2026-10-19 (the V1.21 hot-glue molds were printed in black that day
and are not in it), on three plates:
  Orange  left and right ankle base and ankle side (print/ankle-split-20261019/, the 2026-10-07 split-ankle design in
          build-pack-20260913/redesign-20260913/ankle-redesign-20261007/): the one-piece bracket is a closed fork that had
          to be spread over the lower link and its servo; the base takes the package from above with the side off, the
          side closes along the shaft and two M2 x 8 TAP from above hold it,
  Black   left and right ankle sleeve, bore 10.4 mm (the stock 9.65 mm sleeve is a 0.17 mm press fit on the 10 mm link boss),
  Yellow  left and right slip-fit foot (print/foot-slipfit-20261019/foot_slipfit.py): the printed community feet with the
          ankle socket opened 0.2 mm sideways, the two snap tongues deleted and the heel well filled, held by the toe M2 x 6 TAP.
All eight rows are replacements of printed stock objects (copy-manifest.json ids: brackets 20/22, sleeves 148/150, feet
32/30). Ankle print poses come from print/ankle-split-20261019/poses/poses.json (per key: sourceToPrint from the
STL/*-local.stl frame, chosen by native slicing on both machines); the feet print in the stock pose (identity).

Each plate is one row centred on the bed (128, 128), 12 mm gap. Profiles, baseline stock and the deferred V2.0 head
parts come from the released manifest-V1.20.json (pinned by sha256).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.22.json]
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
V120_PATH = PRINT / 'release-V1.20/manifest-V1.20.json'
V120_SHA = 'b912b3c7eea53f81b96ccf861f4f04cee46eeffe8bf42259f75b0a839b8ce171'
SLIP = PRINT / 'foot-slipfit-20261019'
SPLIT = PRINT / 'ankle-split-20261019'
AR = PRINT.parents[1] / 'build-pack-20260913/redesign-20260913/ankle-redesign-20261007'
STOCK_DIR = PRINT.parents[1] / 'build-pack-20260913/assembly/print-parts'
PLATES = {'Orange': ['ankle_base_left', 'ankle_base_right', 'ankle_cheek_left', 'ankle_cheek_right'],
          'Black': ['ankle_sleeve_left', 'ankle_sleeve_right'],
          'Yellow': ['foot_left_slipfit', 'foot_right_slipfit']}
GAP_MM = 12.0
# Shawn 2026-10-19: three pairs of feet, one to fit and two spare for sole experiments (tape, hot-glue sheet, CA);
# the foot is the replaceable unit (slides off, one toe screw), so a ruined sole costs one foot, not a redesign.
FOOT_PAIRS = 3
IDENTITY = np.eye(4).tolist()
# wall-check regions that are stock geometry, with evidence (thin_wall_allowances.py; it refuses any thin wall V1.22 made)
ALLOWANCES = HERE / 'thin-wall-allowances.json'
# stock object: (community file, copy-manifest object id, the stock part it is)
STOCK = {'foot_left': ('community-44.stl', '32', 'left foot'), 'foot_right': ('community-46.stl', '30', 'right foot'),
         'ankle_left': ('community-66.stl', '20', 'left one-piece ankle bracket'), 'ankle_right': ('community-64.stl', '22', 'right one-piece ankle bracket'),
         'sleeve_left': ('community-62.stl', '148', 'left 9.65 mm ankle sleeve'), 'sleeve_right': ('community-68.stl', '150', 'right 9.65 mm ankle sleeve')}
ANKLE = {'base': ('Orange', 'ankle', 'ankle base'), 'cheek': ('Orange', 'ankle', 'ankle side'), 'sleeve': ('Black', 'sleeve', 'ankle sleeve')}


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


def foot_row(side):
    stock, sid, what = STOCK[f'foot_{side}']
    stl = SLIP / f'foot-{side}-slipfit.stl'
    area, size, _ = printed(stl)
    src = ref(stl)
    return dict(
        key=f'foot_{side}_slipfit', color='Yellow', quantity=FOOT_PAIRS, decision='replacement', replacesStockIds=[sid],
        path=src['path'], sha256=src['sha256'],
        sourceFrame=f'{stock} print frame (mm; flat sole at z = 0)',
        sourceToPrint=IDENTITY, flatContact={'minimumAreaMm2': round(0.95 * area, 1)},
        poseOrigin=f'The stock {stock} pose: flat sole on the bed, as the printed feet were made.',
        poseCheck=dict(printStl=src, bedContactMm2=round(area, 2), printSizeMm=size, note='print pose = stock print frame (identity)'),
        changeReason=(f'Replaces the printed {stock} (stock object {sid}, the {what}). Shawn 2026-10-19: the orange ankle bracket and the '
                      'yellow foot press together so tightly that they cannot be taken apart, and each fitting loads the ankle '
                      'servo. The socket that holds the bracket\'s lower block is opened 0.2 mm sideways along the straight '
                      'insertion path, the two snap tongues are deleted (the cut had left them 0.6-0.7 mm thin flakes with no hook) and the '
                      'heel well they stood in is filled to the wall tops; the faces the bracket rests on stay, '
                      'so it seats where it seats now, with 0.14-0.20 mm play each way and free lift-off. The toe M2 x 6 TAP '
                      'holds the foot. The same socket fits the V1.22 ankle base and side (ankle-split-check.json footSeat). '
                      'Sole unchanged below 4 mm (the hot-glue molds fit). foot-slipfit-20261019/slipfit-check.json.'),
        supersedes=f'printed {stock}',
        incrementalEvidence=ref(SLIP / 'slipfit-check.json'),
        evidenceAlso=[ref(SLIP / 'foot_slipfit.py')],
    )


def ankle_row(part, side, poses):
    colour, stock_key, what = ANKLE[part]
    stock, sid, stock_what = STOCK[f'{stock_key}_{side}']
    stl = AR / 'STL' / f'{side}-{part}-local.stl'
    entry = poses['parts'][f'{side}_{part}']
    assert entry['localStl']['sha256'] == sha(stl), f'{stl} changed since the pose study'
    pose = entry['chosen']
    pose = dict(pose, why=pose.get('why') or pose.get('reason') or 'chosen by native slicing on both machines, see poses.md',
                objectSettingsReason=pose.get('objectSettingsReason') or pose.get('objectSettingsSource') or 'pose study')
    T = pose['sourceToPrint']
    area, size, _ = printed(stl, T)
    src = ref(stl)
    key = f'ankle_{part if part != "cheek" else "cheek"}_{side}'
    reason = {
        'base': (f'Replaces the printed {stock} (stock object {sid}, the {stock_what}) together with ankle_cheek_{side}. Shawn 2026-10-19: '
                 'the one-piece bracket is a closed fork; the lower link with its servo and sleeve cannot come in from above '
                 '(assembly-path-investigation.md), so it was spread and pressed on, loading the ankle servo at every fitting. The '
                 'base keeps the motor-output holes and the foot block of the stock bracket; with the side off, the link-servo-'
                 'sleeve package lifts straight out (ankle-split-check.json packageLiftSideOff 0 mm3 left, the 0.137 mm3 source '
                 'mating-face slab right). The V1.22 slip-fit foot seats on it as on the stock bracket (footSeat).'),
        'cheek': (f'New part, with ankle_base_{side} replacing the printed {stock} (stock object {sid}). The removable side of the '
                  'split ankle: it closes along the shaft onto the sleeve until its two tabs meet the solid base posts, and two '
                  'M2 x 8 TAP from above (1.6 mm pilots in the base, 2.3 mm clearance in the side) hold and locate it. With the foot off '
                  'it slides outward clear of the base and the package (ankle-split-check.json sidePath); with the foot on it is '
                  'captured. DESIGN-NOTES.md in ankle-redesign-20261007/.'),
        'sleeve': (f'Replaces the printed {stock} (stock object {sid}, the {stock_what}): bore 10.4 mm instead of 9.65 mm on the 10 mm '
                   'link boss (the stock sleeve is a 14.96 mm3 press fit, ankle-split-check.json sleeveOnLinkBoss), OD 14.6 mm, '
                   '2.8 mm wide with 0.2 mm entry chamfers, so it slides on by hand and runs free. Black like the stock sleeve.'),
    }[part]
    # the base is the replacement row of the stock bracket; the side is an addition (one replacement row per stock instance)
    return dict(
        key=key, color=colour, quantity=1, decision='addition' if part == 'cheek' else 'replacement', replacesStockIds=[] if part == 'cheek' else [sid],
        path=src['path'], sha256=src['sha256'],
        sourceFrame=f'ankle-redesign-20261007 local frame of the {side} {what} (mm; motor shaft = local z through the origin)',
        sourceToPrint=T, flatContact={'minimumAreaMm2': round(0.95 * area, 1)},
        poseOrigin=f'{pose["poseName"]}: {pose["why"]}',
        poseCheck=dict(printStl=src, bedContactMm2=round(area, 2), printSizeMm=size,
                       note=f'print pose from ankle-split-20261019/poses/poses.json ({pose["poseName"]}), dropped to the bed'),
        changeReason=reason, supersedes=f'printed {stock}' if part != 'cheek' else 'nothing (new part of the split ankle)',
        incrementalEvidence=ref(SPLIT / 'ankle-split-check.json'),
        evidenceAlso=[ref(SPLIT / 'ankle_split_check.py'), ref(SPLIT / 'poses' / 'poses.json')],
        **({'objectSettings': dict(pose['objectSettings']), 'objectSettingsReason': pose['objectSettingsReason']} if pose.get('objectSettings') else {}),
        **({'brimInsideHullAllowanceMm2': 20.0,
            'brimInsideHullAllowanceReason': ('The gusset end face on the bed carries the real 12 x 1.1 mm recess of the stock bracket '
                                              '(community-66/64 notch beside the gusset hole). Bambu Studio loops the 4 mm outer brim into '
                                              'it: 13.3 mm2 inside the convex outline on both bases (poses.md), a strip bonded on three '
                                              'sides that is cut out with a blade. Orca puts support feet there instead. Not an opening '
                                              'filled with brim.')} if part == 'base' else {}),
    )


def build_parts(allowances=None):
    poses = json.loads((SPLIT / 'poses' / 'poses.json').read_text())
    parts = [ankle_row('base', 'left', poses), ankle_row('base', 'right', poses), ankle_row('cheek', 'left', poses), ankle_row('cheek', 'right', poses),
             ankle_row('sleeve', 'left', poses), ankle_row('sleeve', 'right', poses), foot_row('left'), foot_row('right')]
    for p in parts:
        allow = (allowances or {}).get(p['key'])
        if allow:
            p['thinWallAllowances'] = [{k: e[k] for k in ('bbox', 'minMm', 'reason')} for e in allow]
            p['evidenceAlso'] = p['evidenceAlso'] + [ref(ALLOWANCES), ref(HERE / 'thin_wall_allowances.py')]
    return parts


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.22.json'); a = ap.parse_args()
    assert sha(V120_PATH) == V120_SHA, 'manifest-V1.20.json changed since V1.22 was set up'
    m = json.loads(V120_PATH.read_text())
    parts = build_parts(json.loads(ALLOWANCES.read_text()))
    by = {p['key']: p for p in parts}
    placements = {}
    for colour, keys in PLATES.items():
        sizes = {k: printed(by[k]['path'], by[k]['sourceToPrint']) for k in keys}
        if colour == 'Yellow':  # FOOT_PAIRS rows of (left, right), the block centred on the bed
            width = sum(sizes[k][1][0] for k in keys) + GAP_MM * (len(keys) - 1)
            row_h = max(sizes[k][1][1] for k in keys)
            height = FOOT_PAIRS * row_h + GAP_MM * (FOOT_PAIRS - 1)
            pl = []
            for r in range(FOOT_PAIRS):
                x0 = 128.0 - width / 2; yrow = 128.0 - height / 2 + r * (row_h + GAP_MM)
                for key in keys:
                    _, size, lo = sizes[key]; y0 = yrow + (row_h - size[1]) / 2
                    assert 18.0 <= x0 and x0 + size[0] <= 238.0 and 28.0 <= y0 and y0 + size[1] <= 238.0, (key, x0, y0, size)
                    pl.append(dict(key=key, copy=r + 1, translation=[round(x0 - float(lo[0]), 4), round(y0 - float(lo[1]), 4), 0.0]))
                    x0 += size[0] + GAP_MM
            placements[colour] = pl
            continue
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
    m['processOverrideReason'] = 'Stock profiles on every plate (brims per object by the pipeline R1 rule or the manifest objectSettings).'
    m['retiredParts'] = [dict(key=f'{k}_stock', stockId=sid, path=str((STOCK_DIR / f).resolve()), reason=reason)
                         for k, (f, sid, _), reason in zip(STOCK, STOCK.values(),
                                                           ['press fit too tight to take apart; replaced by foot_left_slipfit',
                                                            'press fit too tight to take apart; replaced by foot_right_slipfit',
                                                            'closed fork, spread over the link and servo at every fitting; replaced by ankle_base_left + ankle_cheek_left',
                                                            'closed fork, spread over the link and servo at every fitting; replaced by ankle_base_right + ankle_cheek_right',
                                                            '9.65 mm bore press fit on the 10 mm link boss; replaced by ankle_sleeve_left (10.4 mm)',
                                                            '9.65 mm bore press fit on the 10 mm link boss; replaced by ankle_sleeve_right (10.4 mm)'])]
    m['version'] = 'V1.22'
    m['prototypeScope'] = ('V1.22 delta package, the ankle rework: Orange plate with the two ankle bases and two ankle sides, Black '
                           'plate with the two 10.4 mm ankle sleeves, Yellow plate with three pairs of slip-fit feet (one to fit, two spare for sole experiments). V1.20 is printed and the '
                           'V1.21 molds were printed in black on 2026-10-19 (Shawn).')
    m['knownFitBoundary'] = ('Ankle: the side screws are self-tapping in 1.6 mm printed pilots, hand snug only; the sleeve has about 0.4 mm '
                             'of diametral running clearance in CAD, so a little side play is by design; printed hole sizes are '
                             'not measured yet. Feet: 0.2 mm CAD clearance per side to the base and side; if a printed pair is tight, '
                             'sand the socket walls of the foot, never force it. Not fitted on the robot yet.')
    dc = m['deliveryContract']
    dc.update(colors=['Orange', 'Black', 'Yellow'], fileCount=6,
              baseline='printed V1.8 set, the V1.9 Orange plate, V1.17, V1.18, V1.20 (printed by 2026-10-19) and the V1.21 molds (printed black, 2026-10-19); V1.19 never printed',
              supersedes=['the printed stock ankle brackets community-66 and community-64, sleeves community-62 and community-68, feet community-44 and community-46'],
              status='INCREMENTAL_REPRINT')
    a.out.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(out=str(a.out), parts=[(p['key'], p['color'], p['poseCheck']['bedContactMm2'], p['poseCheck']['printSizeMm']) for p in parts],
                          placements=placements), indent=1))


if __name__ == '__main__':
    main()
