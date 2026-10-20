#!/usr/bin/env python3
"""Project a native slice's support onto the named functional faces of one two-half ankle part (faces.py beside this file;
adapted from ankle-split-20261019/poses/scripts/face_support.py).

    run_bounded_cad.py ... -- /tmp/microduck-cad-venv/bin/python face_support.py RUN_DIR COLOR MACHINE OUT.json

RUN_DIR is a release-pipeline-v2 preparation directory holding exactly one part (the local STL). Bed coordinates follow the
pipeline: bed = (sourceToPrint with dropToBed) * local + placement translation; Bambu commanded XY + extruder offset.
Per face set: area, area facing down (nz < -0.5) / up / side, area resting on support (face centre within 1.0 mm XY of a
support toolpath midpoint and 0 to 0.6 mm above it: the rule of support_map.py / jaw_bearing_seat.py), the lowest and
highest print z of the set, and for cavities the support toolpath length inside the cavity volume (midpoints mapped back to
the local frame). Also: total support XY extrusion length (review_v122.py's supportExtrusionTotalMm), interface length,
first-layer rows (model/support/brim area, release_pipeline_v2.first_layer) and the per-object brim review, and the
extrusion length per feature type on the first three layers (how a near-bed step was printed). Read-only on the slice.
"""
import json, math, re, sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
SIM = Path('/Users/xiangzheng/code/robotics/microduck-sim')
STUDY = SIM / 'guide/print/orientation-study'
sys.path.insert(0, str(STUDY)); sys.path.insert(0, str(STUDY / 'scripts')); sys.path.insert(0, str(HERE)); sys.dont_write_bytecode = True
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
from orientation_check import load_mesh  # noqa: E402
from seat_support import support_segments  # noqa: E402
import release_pipeline_v2 as r2  # noqa: E402
from faces import face_sets, MEANING  # noqa: E402

# Cavities in the local frame: name -> function(local xyz array) -> bool mask
def cavities(kind):
    toe = lambda p: (np.hypot(abs(p[:, 0]) - 17.5, p[:, 2] + 16) < 1.1) & (p[:, 1] > -9.7) & (p[:, 1] < -6.3)
    if kind == 'outer':
        return {
            'output_holes': lambda p: (np.min([np.hypot(p[:, 0] - cx, p[:, 1] - cy) for cx, cy in [(6, 0), (-6, 0), (0, 6), (0, -6)]], axis=0) < 2.2) & (p[:, 2] > -33) & (p[:, 2] < -30.7),
            'centre_aperture': lambda p: (np.hypot(p[:, 0], p[:, 1]) < 2.5) & (p[:, 2] > -33) & (p[:, 2] < -30.7),
            'toe_hole': toe,
        }
    return {
        'pocket': lambda p: (np.hypot(p[:, 0], p[:, 1]) < 7.5) & (p[:, 2] > -1.3) & (p[:, 2] < 1.5),
        'lip_bore': lambda p: (np.hypot(p[:, 0], p[:, 1]) < 7.0) & (p[:, 2] > 1.5) & (p[:, 2] < 2.7),
        'toe_hole': toe,
    }


def model_segments(g, offset):
    """Non-support extrusion midpoints (x, y, z, length) and the feature type per segment."""
    kind, xyz, segs, kinds = '', [0.0, 0.0, 0.0], [], []
    relative, e = True, 0.0
    for line in g.decode(errors='replace').splitlines():
        if line.startswith(('; FEATURE:', ';TYPE:')):
            kind = line.split(':', 1)[1].strip(); continue
        if line.startswith('M82'): relative = False
        elif line.startswith('M83'): relative = True
        elif line.startswith('G92 '):
            mm = re.search(r'E([-+\d.]+)', line)
            if mm: e = float(mm[1])
        if not re.match(r'^G[0123] ', line): continue
        body = line.split(';')[0]
        v = {k: float(t) for k, t in re.findall(r'([XYZE])([-+]?\d*\.?\d+)', body)}
        end = [v.get(k, xyz[i]) for i, k in enumerate('XYZ')]
        de = v.get('E', 0.0) if relative else v.get('E', e) - e
        if 'E' in v: e = e + v['E'] if relative else v['E']
        if de > 0 and end[:2] != xyz[:2] and 'support' not in kind.lower():
            segs.append(((xyz[0] + end[0]) / 2 + offset[0], (xyz[1] + end[1]) / 2 + offset[1], end[2], math.hypot(end[0] - xyz[0], end[1] - xyz[1])))
            kinds.append(kind)
        xyz = end
    return (np.array(segs) if segs else np.zeros((0, 4))), np.array(kinds)


def main():
    run, color, machine, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    prep = json.loads((run / 'preparation.json').read_text())
    part = prep['parts'][0]; key = part['key']; kind = key.split('_')[1]
    row = next(r for r in prep['rows'] if r['color'] == color and r['machine'] == machine)
    T = np.array(part['sourceToPrint'], float); T[2, 3] += part['dropToBedMm']; T[:3, 3] += np.array(row['placements'][0]['translation'], float)
    Ti = np.linalg.inv(T)
    archive = run / 'native' / f'{color}_{machine}' / 'sliced.3mf'; project = run / f'{color}_{machine}_editable.3mf'
    g, cfg, _ = r2.native_payload(archive)
    offset = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0.0, 0.0]
    segs, iface = support_segments(g, offset)
    msegs, mkinds = model_segments(g, offset)
    m = load_mesh(part['source']['path'])
    sets, rule = face_sets(key, m)
    m.apply_transform(T)
    c, n, a = m.triangles_center, m.face_normals, m.area_faces
    touched = np.zeros(len(m.faces), bool)
    if len(segs):
        tree = cKDTree(segs[:, :2])
        for i, near in enumerate(tree.query_ball_point(c[:, :2], r=1.0)):
            if near:
                dz = c[i, 2] - segs[near, 2]
                touched[i] = np.any((dz >= -0.05) & (dz <= 0.6))
    nz = n[:, 2]
    local_sup = (segs[:, :3] @ Ti[:3, :3].T + Ti[:3, 3]) if len(segs) else np.zeros((0, 3))
    cav = cavities(kind)
    inside = {name: round(float(segs[f(local_sup), 3].sum()), 1) if len(segs) else 0.0 for name, f in cav.items()}
    face_rows = {}
    for name, mask in sets.items():
        zc = c[mask, 2]
        face_rows[name] = dict(must=name in rule['must'], meaning=MEANING[name], areaMm2=round(float(a[mask].sum()), 1),
                               downMm2=round(float(a[mask & (nz < -0.5)].sum()), 1), upMm2=round(float(a[mask & (nz > 0.5)].sum()), 1),
                               sideMm2=round(float(a[mask & (abs(nz) <= 0.5)].sum()), 1),
                               onBedMm2=round(float(a[mask & (c[:, 2] < 0.05) & (nz < -0.9)].sum()), 1),
                               touchedMm2=round(float(a[mask & touched].sum()), 1), touchedDownMm2=round(float(a[mask & touched & (nz < -0.5)].sum()), 1),
                               printZMm=[round(float(zc.min()), 2), round(float(zc.max()), 2)] if len(zc) else None)
    for cname, mm in inside.items():
        tgt = {'pocket': 'pocket_wall', 'lip_bore': 'lip_bore', 'toe_hole': 'toe_seat'}.get(cname)
        if tgt in face_rows:
            face_rows[tgt]['supportInsideMm'] = mm
    # First three layers by feature (how a near-bed step is printed) and the tongue toolpath presence.
    zs = sorted(set(np.round(msegs[:, 2], 3))) if len(msegs) else []
    layers = {}
    for z in zs[:3]:
        sel = abs(msegs[:, 2] - z) < 1e-6
        d = {}
        for k in set(mkinds[sel]):
            d[k] = round(float(msegs[sel & (mkinds == k), 3].sum()), 1)
        layers[f'z={z}'] = d
    local_model = (msegs[:, :3] @ Ti[:3, :3].T + Ti[:3, 3]) if len(msegs) else np.zeros((0, 3))
    first, _ = r2.first_layer(g, project, machine)
    brim = r2.brim_review(first, prep['parts'], machine)
    res = dict(run=str(run), key=key, machine=machine, color=color, poseName=part.get('poseName'),
               supportExtrusionTotalMm=round(float(segs[:, 3].sum()) if len(segs) else 0.0, 1),
               supportInterfaceMm=round(float(segs[iface, 3].sum()) if len(segs) else 0.0, 1),
               supportInsideCavitiesMm=inside, faceSets=face_rows,
               firstLayer=[dict(name=x['name'], modelAreaMm2=round(x['model_area_mm2'], 1), islands=x['modelIslands'], supportAreaMm2=round(x['support_area_mm2'], 1), brimAreaMm2=round(x['brim_area_mm2'], 1)) for x in first],
               brim=dict(passed=brim['passed'], objects={k: dict(brimType=v['brimType'], brimAreaMm2=v['brimAreaMm2'], reachMm=v['brimReachMm'], failures=v['failures']) for k, v in brim['objects'].items()}),
               tipAngleDeg=part['tipAngleDeg'], objectSettings=part['objectSettings'], objectSettingsSource=part['objectSettingsSource'],
               firstThreeLayersByFeatureMm=layers,
               method='support toolpath midpoints from the native G-code; a face rests on support when its centre is within 1.0 mm XY and 0..0.6 mm above a support midpoint; cavity figures are support midpoints inside the local-frame cavity volume')
    out.write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: res[k] for k in ('supportExtrusionTotalMm', 'supportInsideCavitiesMm', 'tipAngleDeg', 'objectSettings')}))


if __name__ == '__main__':
    main()
