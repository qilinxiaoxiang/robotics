#!/usr/bin/env python3
"""Jaw support: how much of the mouth-ring sliding seat (inner half-bore D16.8, plus its D14.9 retaining lip) and of
the four M2.5 screw-head seats rests on native support, per candidate slice.

    run_bounded_cad.py ... -- /tmp/microduck-cad-venv/bin/python scripts/jaw_bearing_seat.py OUT.json SLUG [SLUG ...]

Seat geometry is fitted in the current print frame (bed coordinates of slices/jaw_support_original/current):
inner cylinders about the axis x = 128.9, z = 11.7 along Y, radii 8.40 and 7.44 mm (mouth ring OD 16.4 mm).
A face rests on support when a support toolpath midpoint lies within 1.0 mm in XY and 0 to 0.6 mm below it.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'scripts'))
sys.dont_write_bytecode = True
from orientation_check import load_mesh  # noqa: E402
from seat_support import support_segments, rp  # noqa: E402

BASE = HERE / 'slices/jaw_support_original'


def bed_transform(run, machine='Bambu'):
    prep = json.loads((run / 'preparation.json').read_text())
    part = prep['parts'][0]
    row = next(r for r in prep['rows'] if r['machine'] == machine)
    T = np.array(part['sourceToPrint'], float)
    T[2, 3] += part['dropToBedMm']
    T[:3, 3] += np.array(row['placements'][0]['translation'], float)
    return part, row, T


def main():
    out, slugs = Path(sys.argv[1]), sys.argv[2:]
    part, _, Tc = bed_transform(BASE / 'current/run')
    src = load_mesh(part['source']['path'])
    # Seat faces selected once in the current bed frame, then carried to each candidate through source coordinates.
    cur = src.copy()
    cur.apply_transform(Tc)
    c, n = cur.triangles_center, cur.face_normals
    rad = np.c_[c[:, 0] - 128.9, c[:, 2] - 11.7]
    dist = np.hypot(*rad.T)
    inward = (n[:, [0, 2]] * rad).sum(1) < 0
    along = (abs(n[:, 1]) < 0.05) & (c[:, 1] > 150)
    bearing = along & inward & ((abs(dist - 8.40) < 0.15) | (abs(dist - 7.44) < 0.15))
    seats = (n[:, 2] < -0.9) & (abs(c[:, 2] - 17.1) < 0.05)           # flange underside around the four M2.5 holes
    rows = []
    for slug in slugs:
        run = BASE / slug / 'run'
        _, row, T = bed_transform(run)
        m = src.copy()
        m.apply_transform(T)
        g, cfg, _ = rp.native_payload(run / 'native' / 'Black_Bambu' / 'sliced.3mf')
        offset = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x')))
        segs, _ = support_segments(g, offset)
        touched = np.zeros(len(m.faces), bool)
        if len(segs):
            tree = cKDTree(segs[:, :2])
            cc = m.triangles_center
            for i, near in enumerate(tree.query_ball_point(cc[:, :2], r=1.0)):
                if near:
                    dz = cc[i, 2] - segs[near, 2]
                    touched[i] = np.any((dz >= -0.05) & (dz <= 0.6))
        a = m.area_faces
        nz = m.face_normals[:, 2]
        rows.append(dict(slug=slug, bearingSeatAreaMm2=round(float(a[bearing].sum()), 1),
                         bearingSeatOnSupportMm2=round(float(a[bearing & touched].sum()), 1),
                         bearingSeatFacingDownMm2=round(float(a[bearing & (nz < -0.5)].sum()), 1),
                         screwHeadSeatAreaMm2=round(float(a[seats].sum()), 1),
                         screwHeadSeatOnSupportMm2=round(float(a[seats & touched].sum()), 1)))
        print(json.dumps(rows[-1]))
    out.write_text(json.dumps(dict(method=__doc__.strip(), rows=rows), indent=1) + '\n')


if __name__ == '__main__':
    main()
