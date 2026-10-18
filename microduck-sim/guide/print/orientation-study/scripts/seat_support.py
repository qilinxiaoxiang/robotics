#!/usr/bin/env python3
"""Where does native support touch the functional holes? For every planar circular hole end found in the CAD
(orientation_check.detect_holes), measure support / support-interface toolpath length
  - under each down-facing end: within (hole radius + 2 mm) of the hole axis and up to 1.5 mm below the end face;
  - inside each hole core: within (hole radius - 0.15 mm) of the axis, over the hole's own height range;
  - under each down-facing round boss face (PCB pad, pin tip, post end) at least 0.6 mm above the bed: within
    (boss radius + 1 mm) of the axis and up to 1.5 mm below the face.

    run_bounded_cad.py ... -- /tmp/microduck-cad-venv/bin/python scripts/seat_support.py RUN_DIR COLOR MACHINE OUT.json

RUN_DIR is a release-pipeline preparation directory holding exactly one part. Coordinates follow the pipeline:
bed = (sourceToPrint with dropToBed) * source + placement translation; Bambu commanded XY + extruder offset.
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
from orientation_check import detect_holes, load_mesh  # noqa: E402

PIPE = HERE.parents[2] / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'
sys.path.insert(0, str(PIPE))
import release_pipeline as rp  # noqa: E402


def support_segments(g, offset):
    kind, xyz, segs = '', [0.0, 0.0, 0.0], []
    relative, e = True, 0.0
    for line in g.decode(errors='replace').splitlines():
        if line.startswith(('; FEATURE:', ';TYPE:')):
            kind = line.split(':', 1)[1].strip().lower()
            continue
        if line.startswith('M82'):
            relative = False
        elif line.startswith('M83'):
            relative = True
        if not re.match(r'^G[0123] ', line):
            continue
        body = line.split(';')[0]
        v = {k: float(t) for k, t in re.findall(r'([XYZE])([-+]?\d*\.?\d+)', body)}
        end = [v.get(k, xyz[i]) for i, k in enumerate('XYZ')]
        de = v.get('E', 0.0) if relative else v.get('E', e) - e
        if 'E' in v:
            e = e + v['E'] if relative else v['E']
        if 'support' in kind and de > 0 and end[:2] != xyz[:2]:
            segs.append(((xyz[0] + end[0]) / 2 + offset[0], (xyz[1] + end[1]) / 2 + offset[1], end[2],
                         math.hypot(end[0] - xyz[0], end[1] - xyz[1]), 'interface' in kind))
        xyz = end
    return np.array([s[:4] for s in segs]) if segs else np.zeros((0, 4)), np.array([s[4] for s in segs], bool)


def main():
    run, color, machine, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    prep = json.loads((run / 'preparation.json').read_text())
    part = prep['parts'][0]
    row = next(r for r in prep['rows'] if r['color'] == color and r['machine'] == machine)
    T = np.array(part['sourceToPrint'], float)
    T[2, 3] += part['dropToBedMm']
    T[:3, 3] += np.array(row['placements'][0]['translation'], float)
    g, cfg, _ = rp.native_payload(run / 'native' / f'{color}_{machine}' / 'sliced.3mf')
    offset = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0.0, 0.0]
    segs, iface = support_segments(g, offset)
    mesh = load_mesh(part['source']['path'])
    R, t = T[:3, :3], T[:3, 3]
    rows, under_total, core_total = [], 0.0, 0.0
    boss_rows, boss_total, seen = [], 0.0, set()
    features = detect_holes(mesh)
    for h in features:
        if h['kind'] != 'boss':
            continue
        ax = R @ h['axis']
        for e in h['ends']:
            c, n = R @ e['centre'] + t, R @ e['normal']
            if n[2] >= -0.7 or c[2] < 0.6 or e['facet'] in seen or not len(segs):
                continue
            seen.add(e['facet'])          # one face can carry two loops (pad outline and pin root)
            d = segs[:, :3] - c
            radial = np.linalg.norm(d - np.outer(d @ ax, ax), axis=1)
            sel = (radial <= h['r'] + 1.0) & (segs[:, 2] <= c[2] + 0.01) & (segs[:, 2] >= c[2] - 1.5)
            mm = float(segs[sel, 3].sum())
            boss_total += mm
            boss_rows.append(dict(diameterMm=round(2 * h['r'], 2), zMm=round(float(c[2]), 2), supportUnderFaceMm=round(mm, 1)))
    for h in features:
        if h['kind'] != 'hole':
            continue
        ax = R @ h['axis']
        ends = [(R @ e['centre'] + t, R @ e['normal']) for e in h['ends']]
        zs = [c[2] for c, _ in ends]
        rec = dict(diameterMm=round(2 * h['r'], 2), tiltDeg=round(math.degrees(math.acos(min(1, abs(ax[2])))), 1), ends=[])
        for c, n in ends:
            state = 'down' if n[2] < -0.7 else 'up' if n[2] > 0.7 else 'side'
            mm = 0.0
            if state == 'down' and c[2] > 0.05 and len(segs):
                d = segs[:, :3] - c
                radial = np.linalg.norm(d - np.outer(d @ ax, ax), axis=1)
                sel = (radial <= h['r'] + 2.0) & (segs[:, 2] <= c[2] + 0.01) & (segs[:, 2] >= c[2] - 1.5)
                mm = float(segs[sel, 3].sum())
                under_total += mm
            rec['ends'].append(dict(state=state, zMm=round(float(c[2]), 2), supportUnderEndMm=round(mm, 1)))
        core = 0.0
        if len(segs):
            d = segs[:, :3] - ends[0][0]
            along = d @ ax
            radial = np.linalg.norm(d - np.outer(along, ax), axis=1)
            lo, hi = (min(0.0, *[(c - ends[0][0]) @ ax for c, _ in ends]), max(0.0, *[(c - ends[0][0]) @ ax for c, _ in ends]))
            if hi - lo < 0.2:          # blind hole: one detected end; probe 3 mm into the part
                lo, hi = (-3.0, 0.0) if ends[0][1] @ ax > 0 else (0.0, 3.0)
            sel = (radial <= max(h['r'] - 0.15, 0.2)) & (along >= lo) & (along <= hi)
            core = float(segs[sel, 3].sum())
        core_total += core
        rec['supportInCoreMm'] = round(core, 1)
        rows.append(rec)
    res = dict(run=str(run), machine=machine, holes=rows, supportUnderDownEndsMm=round(under_total, 1),
               downFacingBossFaces=boss_rows, supportUnderDownBossFacesMm=round(boss_total, 1),
               supportInHoleCoresMm=round(core_total, 1), supportToolpathMm=round(float(segs[:, 3].sum()) if len(segs) else 0.0, 1),
               supportInterfaceToolpathMm=round(float(segs[iface, 3].sum()) if len(segs) else 0.0, 1),
               method='Support toolpath midpoints from the native G-code; zones described in the module docstring.')
    out.write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: res[k] for k in ('supportUnderDownEndsMm', 'supportUnderDownBossFacesMm', 'supportInHoleCoresMm', 'supportToolpathMm')}))


if __name__ == '__main__':
    main()
