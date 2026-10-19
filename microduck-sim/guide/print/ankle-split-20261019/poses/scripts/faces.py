#!/usr/bin/env python3
"""Named functional faces of the six split-ankle parts, selected on the LOCAL-frame STL (ankle-redesign-20261007/STL/
*-local.stl; the motor shaft is local Z, the two M2 x 8 TAP screws run along local Y at x = +-12, z = 4.5).
Each selector returns a boolean mask over the faces of orientation_check.load_mesh(local_stl). Geometry from
generate_candidate.py (slot 2.2 x 0.55 at y 1.5..2.05, tongue 2 x 0.4 at y 1.6..2.0, pilot d1.6 y -2.5..1.7, clearance d2.3
y 1.5..6.05, tabs y 2..6, pillar/tab tops z 7.1) and the hole list renders/holes-local.json (output seats: d4.4 counterbore
floors at z = -32.5 around (+-6, 0) and (0, +-6); motor face z = -30.7; pocket d15 / lip d14 at z 1.5).

    /tmp/microduck-cad-venv/bin/python faces.py      # prints the selected area of every set, for a sanity check
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/orientation-study')
sys.path.insert(0, str(STUDY)); sys.dont_write_bytecode = True
from orientation_check import load_mesh  # noqa: E402

# Which sets must print clean (the brief's functional-face rule), which are reported only.
RULE = {
    'base': dict(must=['motor_face', 'output_seats', 'slot_walls', 'post_register', 'pilot_bores'],
                 report=['slot_floor', 'split_face', 'wing_inner_walls', 'foot_shoulder', 'foot_block', 'plate_underside', 'arm_inner_face', 'arm_outer_face', 'gusset_hole', 'top_faces']),
    'cheek': dict(must=['pocket_wall', 'capture_lip', 'tongue_sides', 'tongue_tips', 'tab_register', 'clearance_bores'],
                  report=['lip_bore', 'head_seats', 'split_face', 'side_walls', 'inner_face', 'tab_undersides', 'exterior_top', 'tab_tops']),
    'sleeve': dict(must=['bore', 'outer_face', 'end_faces'], report=['chamfers']),
}
# Plain-words meaning of each set, for poses.md.
MEANING = {
    'motor_face': 'inner motor mating face (399 mm2 plane at local z = -30.7, faces +Z): the XL330 output horn/case face sits on it',
    'output_seats': 'four motor-output screw seats: d4.4 counterbore floors at local z = -32.5 under the M2 x 4 TAP heads',
    'slot_walls': 'open-top slot side walls (2.2 mm apart, x = +-12 +- 1.1, y 1.5..2.05): the register for the cheek tongues',
    'post_register': 'post faces at y = 2.0 beside each slot: the flat faces the cheek tab is pulled against',
    'pilot_bores': 'two d1.6 blind TAP pilots along Y (y -2.5..1.5 at x = +-12, z = 4.5)',
    'slot_floor': 'slot floor at y = 1.5 (0.1 mm nominal gap to the tongue tip)',
    'split_face': 'split plane z = -1.6 (base +Z face / cheek -Z face, 65 mm2 strip on the foot side)',
    'wing_inner_walls': 'wing inner walls at x = +-11 (z -1.6..3): the cheek body nests between them',
    'foot_shoulder': 'plate underside at z = -33 outside the seats: the shoulder the yellow foot socket rim bears on',
    'foot_block': 'lower block (z -35.85..-33) outer faces: the slip-fit foot socket (V1.22, 0.2 mm clearance) slides over them',
    'plate_underside': 'plate underside inside r < 8 at z = -33 (between the seats, horn-side clearance)',
    'arm_inner_face': 'arm inner face y = -7.12 (faces the motor package)',
    'arm_outer_face': 'arm outer face y = -9.62 (exterior)',
    'gusset_hole': 'original d2.2 / d4.4 counterbored hole through the gusset at x = 17.5, z = -16 (axis Y)',
    'top_faces': 'wing tops z = 3 and post tops z = 7.1 (exterior)',
    'pocket_wall': 'bearing pocket: d15 cylinder wall (local z -1.3..1.5) the black sleeve OD 14.6 runs in',
    'capture_lip': 'inside capture lip: annulus r 7..7.5 at z = 1.5 facing -Z, the sleeve end bears on it axially',
    'tongue_sides': 'tongue side walls (2 mm wide at x = +-12 +- 1, y 1.6..2.0): the register in the base slots',
    'tongue_tips': 'tongue tips at y = 1.6 (0.1 mm nominal gap to the slot floor)',
    'tab_register': 'tab faces at y = 2.0 (x 8..11 and 13..15): pulled against the base posts',
    'clearance_bores': 'two d2.3 clearance holes along Y (y 1.5..6.05 at x = +-12, z = 4.5) for the M2 x 8 TAP shanks',
    'lip_bore': 'd14 bore above the lip (z 1.5..3.0): the washer / rear screw window, nothing slides in it',
    'head_seats': 'cap screw head seats at y = 6 (x 8..15): the M2 x 8 TAP heads bear on them',
    'side_walls': 'cheek side walls at x = +-11 (z -1.6..3): nest between the base wings',
    'inner_face': 'inner face z = -1.3 (193 mm2) facing the lower link',
    'tab_undersides': 'tab undersides z = 1.65 outside the ring body (exterior)',
    'exterior_top': 'exterior top faces (z 1.0, 3.0 planes and the sloped ring top, facing +Z)',
    'tab_tops': 'tab tops z = 7.1 (exterior)',
    'bore': 'sleeve bore d10.4 (slides on the lower-link d10 boss)',
    'outer_face': 'sleeve outer face d14.6 (slides in the cheek pocket)',
    'end_faces': 'sleeve end faces z = +-1.4 (axial contact with the lip and the link flange)',
    'chamfers': '0.2 mm entry chamfers at both ends',
}


def _sets(kind, m):
    c, n, a = m.triangles_center, m.face_normals, m.area_faces
    x, y, z = c.T
    nx, ny, nz = n.T
    r = np.hypot(x, y)
    S = {}
    if kind == 'base':
        S['motor_face'] = (nz > 0.99) & (abs(z + 30.7) < 0.05)
        seat_r = np.min([np.hypot(x - cx, y - cy) for cx, cy in [(6, 0), (-6, 0), (0, 6), (0, -6)]], axis=0)
        S['output_seats'] = (nz < -0.99) & (abs(z + 32.5) < 0.05) & (seat_r < 2.3)
        S['plate_underside'] = (nz < -0.99) & (abs(z + 33) < 0.05) & (r < 8)
        S['foot_shoulder'] = (nz < -0.99) & (abs(z + 33) < 0.05) & (r >= 8)
        S['foot_block'] = (z < -33.05) & ~((nz < -0.99) & (abs(z + 33) < 0.05))
        px = np.minimum(abs(x - 12), abs(x + 12))
        inslot = (y > 1.45) & (y < 2.1) & (z > 1.6) & (z < 7.15)
        S['slot_walls'] = inslot & (abs(nx) > 0.99) & (abs(px - 1.1) < 0.05)
        S['slot_floor'] = inslot & (ny > 0.99) & (abs(y - 1.5) < 0.05) & (px < 1.15)
        S['post_register'] = (ny > 0.99) & (abs(y - 2.0) < 0.05) & (z > 1.6) & (z < 7.15) & (px >= 1.05) & (px < 2.05)
        S['pilot_bores'] = (abs(np.hypot(px, z - 4.5) - 0.8) < 0.1) & (y > -2.55) & (y < 1.55) & (abs(ny) < 0.3)
        S['split_face'] = (nz > 0.99) & (abs(z + 1.6) < 0.05)
        S['wing_inner_walls'] = (abs(nx) > 0.99) & (abs(abs(x) - 11) < 0.05) & (z > -1.65) & (z < 3.05) & (y < -0.6)
        S['arm_inner_face'] = (ny > 0.99) & (abs(y + 7.12) < 0.05)
        S['arm_outer_face'] = (ny < -0.99) & (abs(y + 9.62) < 0.05)
        S['gusset_hole'] = (np.hypot(abs(x) - 17.5, z + 16) < 2.3) & (y > -9.7) & (y < -7.1) & (abs(ny) < 0.3)
        S['top_faces'] = (nz > 0.99) & ((abs(z - 3.0) < 0.05) | (abs(z - 7.1) < 0.05))
    elif kind == 'cheek':
        inward = (nx * x + ny * y) < 0
        S['pocket_wall'] = (abs(r - 7.5) < 0.15) & (abs(nz) < 0.3) & inward & (z > -1.35) & (z < 1.55)
        S['lip_bore'] = (abs(r - 7.0) < 0.15) & (abs(nz) < 0.3) & inward & (z > 1.45) & (z < 3.05)
        S['capture_lip'] = (nz < -0.99) & (abs(z - 1.5) < 0.05) & (r > 6.9) & (r < 7.6)
        px = np.minimum(abs(x - 12), abs(x + 12))
        intongue = (y > 1.55) & (y < 2.05) & (z > 1.6) & (z < 7.15)
        S['tongue_sides'] = intongue & (abs(nx) > 0.99) & (abs(px - 1.0) < 0.05)
        S['tongue_tips'] = intongue & (ny < -0.99) & (abs(y - 1.6) < 0.05) & (px < 1.05)
        S['tab_register'] = (ny < -0.99) & (abs(y - 2.0) < 0.05) & (z > 1.6) & (z < 7.15) & (abs(x) >= 8) & (abs(x) <= 15)
        S['head_seats'] = (ny > 0.99) & (abs(y - 6.0) < 0.05) & (abs(x) >= 7.9) & (z > 1.6)
        S['clearance_bores'] = (abs(np.hypot(px, z - 4.5) - 1.15) < 0.1) & (y > 1.45) & (y < 6.1) & (abs(ny) < 0.3)
        S['split_face'] = (nz < -0.99) & (abs(z + 1.6) < 0.05)
        S['inner_face'] = (nz < -0.99) & (abs(z + 1.3) < 0.05)
        S['side_walls'] = (abs(nx) > 0.99) & (abs(abs(x) - 11) < 0.05) & (z > -1.65) & (z < 3.05) & (y < -4)
        S['tab_undersides'] = (nz < -0.99) & (abs(z - 1.65) < 0.05)
        S['tab_tops'] = (nz > 0.99) & (abs(z - 7.1) < 0.05)
        S['exterior_top'] = (nz > 0.7) & (z > 0.9) & (z < 7.0) & ~S['tab_tops']
    elif kind == 'sleeve':
        S['bore'] = (abs(r - 5.2) < 0.08) & (abs(nz) < 0.3)
        S['outer_face'] = (abs(r - 7.3) < 0.08) & (abs(nz) < 0.3)
        S['end_faces'] = (abs(nz) > 0.99) & (abs(abs(z) - 1.4) < 0.02)
        S['chamfers'] = (abs(nz) > 0.5) & (abs(nz) < 0.9)
    return S


def face_sets(key, mesh):
    kind = key.split('_')[1]
    return _sets(kind, mesh), RULE[kind]


if __name__ == '__main__':
    l2p = json.loads((HERE.parent / 'local-to-printstl.json').read_text())
    for key, row in l2p.items():
        m = load_mesh(row['localStl'])
        S, rule = face_sets(key, m)
        print(key)
        for name, mask in S.items():
            print(f"   {name:<18s} {'MUST' if name in rule['must'] else 'rep '} area {m.area_faces[mask].sum():8.1f} mm2  faces {int(mask.sum()):4d}")
