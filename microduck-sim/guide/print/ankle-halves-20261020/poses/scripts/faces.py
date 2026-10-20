#!/usr/bin/env python3
"""Named functional faces of the two-half ankle (make_halves.py), on the LOCAL-frame STL (STL/{side}-{outer,inner}-local.stl:
local z is the motor shaft, local y up, the foot below; the cut at z = -16 +- 0.1; the right frame mirrors local x).
MUST sets slide, bear or mate and must print without support under them; REPORT sets are counted only.

    /tmp/microduck-cad-venv/bin/python faces.py      # prints the selected area of every set
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; HALVES = HERE.parents[1]
STUDY = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/orientation-study')
sys.path.insert(0, str(STUDY)); sys.dont_write_bytecode = True
CUT, GAP = -16.0, 0.1

RULE = {
    'outer': dict(must=['motor_face', 'output_seats', 'cut_face'], report=['foot_block', 'toe_seat', 'outer_plate_face']),
    'inner': dict(must=['pocket_wall', 'capture_lip', 'cut_face'], report=['foot_block', 'toe_seat', 'lip_bore', 'outer_plate_face']),
}
MEANING = {
    'motor_face': 'inner motor mating face (plane local z = -30.7, faces +Z): the XL330 output horn/case face sits on it',
    'output_seats': 'four motor-output screw seats: d4.4 counterbore floors at local z = -32.5 under the M2 x 4 TAP heads',
    'cut_face': 'the cut face (local z = -16.1 on the outer half, -15.9 on the inner): the two halves meet here, 0.2 mm apart',
    'foot_block': 'the half foot block below local y = -9.4: the slip-fit foot socket (0.15-0.19 mm play) slides over it',
    'toe_seat': 'the half countersink of the toe M2 x 6 TAP at local x = +-17.5, z = -16',
    'outer_plate_face': 'the exterior face of the plate (outer: z < -33, inner: z > 3)',
    'pocket_wall': 'bearing pocket: d15 cylinder wall (local z -1.3..1.5) the black sleeve OD 14.6 runs in',
    'capture_lip': 'capture lip underside: annulus r 7..7.5 at z = 1.5 facing -Z, the sleeve end bears on it axially',
    'lip_bore': 'd14 bore above the lip (z 1.5..2.7): nothing slides in it',
}


def _sets(kind, m):
    c, n = m.triangles_center, m.face_normals
    x, y, z = c.T; nx, ny, nz = n.T; r = np.hypot(x, y); S = {}
    S['foot_block'] = y < -9.4
    S['toe_seat'] = (np.hypot(abs(x) - 17.5, z - CUT) < 1.9) & (ny > 0.3)
    if kind == 'outer':
        S['motor_face'] = (nz > 0.99) & (abs(z + 30.7) < 0.05)
        seat_r = np.min([np.hypot(x - cx, y - cy) for cx, cy in [(6, 0), (-6, 0), (0, 6), (0, -6)]], axis=0)
        S['output_seats'] = (nz < -0.99) & (abs(z + 32.5) < 0.05) & (seat_r < 2.3)
        S['cut_face'] = (nz > 0.99) & (abs(z - (CUT - GAP)) < 0.03)
        S['outer_plate_face'] = (nz < -0.7) & (z < -33.0)
    else:
        inward = (nx * x + ny * y) < 0
        S['pocket_wall'] = (abs(r - 7.5) < 0.15) & (abs(nz) < 0.3) & inward & (z > -1.35) & (z < 1.55)
        S['capture_lip'] = (nz < -0.99) & (abs(z - 1.5) < 0.05) & (r > 6.9) & (r < 7.6)
        S['lip_bore'] = (abs(r - 7.05) < 0.15) & (abs(nz) < 0.3) & inward & (z > 1.45) & (z < 2.75)
        S['cut_face'] = (nz < -0.99) & (abs(z - (CUT + GAP)) < 0.03)
        S['outer_plate_face'] = (nz > 0.7) & (z > 3.0)
    return S


def face_sets(key, mesh):
    kind = key.split('_')[1]
    return _sets(kind, mesh), RULE[kind]


if __name__ == '__main__':
    from orientation_check import load_mesh
    for side in ('left', 'right'):
        for kind in ('outer', 'inner'):
            m = load_mesh(HALVES / 'STL' / f'{side}-{kind}-local.stl'); S, rule = face_sets(f'{side}_{kind}', m)
            print(side, kind)
            for name, mask in S.items():
                print(f"   {name:<18s} {'MUST' if name in rule['must'] else 'rep '} area {m.area_faces[mask].sum():8.1f} mm2  faces {int(mask.sum()):4d}")
