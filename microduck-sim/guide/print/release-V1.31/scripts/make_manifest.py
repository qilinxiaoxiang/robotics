"""Write the V1.31 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.31 is one Orange plate with one part: the battery backpack frame with a wider DFR1202 slot. Shawn 2026-10-23: the board
does not go into the printed V1.20 frame. The V1.20 clip arms stood 0.2 mm from the 26.0 mm board edge and 0.2 mm from the
standoff rib behind them, which prints shut, so the arm cannot bend for its lip. Now the arms are 27.0 apart (0.5 per
side), the ribs end 0.9 inside the arms, and the lips reach 0.3 over the board edge with a 42 deg lead-in
(back-plate/battery-backpack-20261015/build_bp.py ARM_Y, RIB_Y, LIP_DEPTH). Nothing else in the frame changes; the cap is
unchanged and not reprinted.

The row is the V1.20 frame row with the rebuilt STL and the same sourceToPrint. Thin regions found by the wall check are
accepted only where the V1.20 print had the same region (bbox within 1 mm) or on the clip arms and lips, which are 0.8 mm
flexures by design.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.31.json]
"""
import argparse, copy, hashlib, json, sys
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
V120_PATH = PRINT / 'release-V1.20/manifest-V1.20.json'
V120_SHA = 'b912b3c7eea53f81b96ccf861f4f04cee46eeffe8bf42259f75b0a839b8ce171'
BP = PRINT / 'back-plate/battery-backpack-20261015'
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
FLEX_REASON = ('DFR1202 clip arm or lip: a 0.8 mm flexure by design, it bends 0.3 mm to let the board pass '
               '(build_bp.py ARM_Y/LIP_DEPTH, 2026-10-23)')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p); assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def printed(path, T):
    m = trimesh.load(path, force='mesh', process=False)
    v, inv = np.unique(m.vertices, axis=0, return_inverse=True)
    m = trimesh.Trimesh(v, inv.reshape(-1)[m.faces], process=False); m.apply_transform(np.array(T, float))
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    return m


def thin(m, key):
    return [g for g in wall_check.check(m.copy(), (), key)['regions'] if g['status'] == 'FAIL']


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.31.json'); a = ap.parse_args()
    assert sha(V120_PATH) == V120_SHA, 'manifest-V1.20.json changed since V1.31 was set up'
    m = json.loads(V120_PATH.read_text())
    row = copy.deepcopy(next(p for p in m['parts'] if p['key'] == 'battery_backpack_frame'))
    world = BP / 'battery_backpack_frame-world.stl'; src = ref(world)
    assert src['sha256'] != row['sha256'], 'frame STL did not change'
    T = np.array(row['sourceToPrint'], float)
    k = printed(world, T); old = printed(row['path'] if sha(row['path']) == row['sha256'] else PRINT / 'world/battery_backpack_frame.stl', T)
    assert sha(PRINT / 'world/battery_backpack_frame.stl') == row['sha256'], 'guide world frame is not the printed V1.20 frame'
    area = float(k.area_faces[np.max(np.abs(k.triangles[:, :, 2]), axis=1) <= .01].sum()); size = (k.bounds[1] - k.bounds[0]).round(2).tolist()
    assert area >= row['flatContact']['minimumAreaMm2'], area
    # clip arms and lips in print coordinates: world x -52.4..-46.4, |y| 12.6..14.4, z 12.5..22.0 and 30.0..39.5
    flex = []
    for s in (1, -1):
        for z0, z1 in ((12.4, 22.1), (29.9, 39.6)):
            c = np.array([[x, y, z, 1.0] for x in (-52.4, -46.4) for y in (s * 12.6, s * 14.4) for z in (z0, z1)]) @ T.T
            flex.append((c[:, :3].min(0) - [0, 0, 0], c[:, :3].max(0)))
    drop = -float(trimesh.load(world, force='mesh').copy().apply_transform(T).bounds[0, 2])
    flex = [(lo + [0, 0, drop], hi + [0, 0, drop]) for lo, hi in flex]
    olds = thin(old, 'battery_backpack_frame')
    allow = []
    for g in thin(k, 'battery_backpack_frame'):
        lo, hi = np.array(g['bbox'])
        was = [o for o in olds if (lo > np.array(o['bbox'][0]) - 1.0).all() and (hi < np.array(o['bbox'][1]) + 1.0).all()]
        on_arm = any((lo > f[0] - 0.2).all() and (hi < f[1] + 0.2).all() for f in flex)
        assert was or on_arm, ('new thin region', g['minMm'], g['areaMm2'], g['bbox'])
        allow.append(dict(bbox=[[c - .05 for c in g['bbox'][0]], [c + .05 for c in g['bbox'][1]]], minMm=round(max(g['minMm'] - .005, 0.01), 3),
                          reason=FLEX_REASON if on_arm else 'present in the printed V1.20 frame, which printed and fitted'))
    row.update(path=src['path'], sha256=src['sha256'], thinWallAllowances=allow,
               changeReason=('V1.31: the V1.20 frame with a wider DFR1202 slot. Shawn 2026-10-23: the board does not go in. The V1.20 clip '
                             'arms stood 0.2 mm from the 26.0 mm board edge and 0.2 mm from the rib behind them (prints shut, the arm '
                             'cannot bend); the arms are now 27.0 apart, the ribs end 0.9 inside them, the lips reach 0.3 over the board '
                             'edge with a 42 deg lead-in. Evidence: back-plate/battery-backpack-20261015/build/build.json, bp_checks.json.'),
               supersedes='battery_backpack_frame of release V1.20 (printed; the DFR1202 does not fit its slot)')
    pstl = BP / 'battery_backpack_frame-print.stl'
    row['poseCheck'] = dict(printStl=ref(pstl), bedContactMm2=round(area, 2), printSizeMm=size,
                            note='V1.31: contact from the rebuilt world STL with the unchanged V1.20 sourceToPrint')
    row['incrementalEvidence'] = ref(BP / 'bp_checks.json'); row['evidenceAlso'] = [ref(BP / 'build/build.json')]
    lo = k.bounds[0]
    m['parts'] = [row]
    m['placements'] = {'Orange': [dict(key='battery_backpack_frame', copy=1,
                                       translation=[round(128.0 - size[0] / 2 - float(lo[0]), 4), round(128.0 - size[1] / 2 - float(lo[1]), 4), 0.0])]}
    m['processOverrides'] = {}
    m['processOverrideReason'] = 'No process overrides: V1.31 carries only the Orange frame (as V1.20).'
    m['retiredParts'] = [{'part': 'battery_backpack_frame (V1.20)', 'printed': 'V1.20 (Orange)',
                          'reason': 'the DFR1202 does not go between its clip arms; replaced by the V1.31 frame with the wider slot'}]
    m['version'] = 'V1.31'
    m['prototypeScope'] = 'V1.31 delta package on one Orange plate: the battery backpack frame with the wider DFR1202 slot.'
    m['knownFitBoundary'] = ('Board size from the DFRobot DFR1202 page (30 x 26 x 8 mm), not measured. The lips snap over the board '
                             'edge with 0.3 mm of bend, untested on a print. The rest of the frame is the V1.20 frame that fitted.')
    m.pop('deferred', None)
    m['deliveryContract'].update(colors=['Orange'], fileCount=2, status='INCREMENTAL_REPRINT',
                                 baseline='printed releases through V1.28 (V1.30 printing)',
                                 supersedes=['battery_backpack_frame of V1.20'])
    a.out.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(out=str(a.out), contact=round(area, 1), size=size, allowances=[(x['minMm'], x['reason'][:20]) for x in allow],
                          placements=m['placements'])))


if __name__ == '__main__':
    main()
