#!/usr/bin/env python3
"""Does the board as drawn (pcb/build/footprints.json) fit in the head? Parts only; wires are not in the meshes.

Every footprint becomes a box (its courtyard x its height behind the rear face); every connector also gets a plug box
(mated housing plus the first bend of its wires). The boxes sit on the camera back where space_check.py found room.
1. HOME: each box against the voxel grid of the head parts (guide meshes), at 0 and 1 mm clearance.
2. Head poses: the parts that move relative to the head (yaw bracket, neck pitch group, neck) are swept over the
   MJCF joint ranges of head_pitch, head_yaw and head_roll and tested against the same boxes.

Run on the Mac mini: ~/.venvs/microduck-dyn/bin/python fit_check.py   -> prints, writes fit-check.json
"""
import itertools
import json
from pathlib import Path

import numpy as np

import space_check as S

HERE = Path(__file__).resolve().parent
FP = json.loads((HERE / 'pcb' / 'build' / 'footprints.json').read_text())
XML = HERE.parent / 'microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml'

# Board frame -> robot frame (mm). Board seen from the rear: x right (= robot -y), y down (= robot -z), parts toward -x.
Y_AT_X0, Z_AT_Y0 = 1.0, 145.5          # outline y -29..1, z 115.5..145.5 (space-check.json, 1 mm clearance result)
X_LIMIT = 62.9                         # front limit of the slab space_check.py found free
TAIL, PCB = 1.5, 1.6                   # through-hole solder tails on the front face, board thickness
X_REAR = X_LIMIT - TAIL - PCB          # rear (component) face
BAND = 13.8                            # board y above which the through-hole parts stand

# footprint name prefix -> (body height, plug top) in mm behind the rear face; plug top None = nothing plugs in
SHAPES = [
    ('PinSocket', 8.5, 8.5 + 16.0),            # 8.5 mm socket, Dupont housing 14 + wire exit 2 (as the breadboard tail)
    ('PinHeader', 8.5, 2.5 + 14.0 + 2.0),      # 2.5 plastic + 6 pin; the housing sits on the plastic
    ('Molex_PicoBlade', 4.2, 14.0),            # mated 51021 housing about 6, wires bend within 8 more
    ('TerminalBlock', 9.0, 9.0 + 16.0),        # screwdriver comes straight from behind
]
LOW = 1.5                                      # everything else (SOT-23-5 is the tallest, 1.45 max)
PLUG_CELLS = {'J_TOUCH_3V3': 1}                # 1x2 socket (no 1x1 in stock), the single lead plugs into pin 1 at the left
CLEARANCES = (0.0, 1.0)
MOVING = {                                     # MJCF body -> guide parts it carries (neck-route/nr_lib.py)
    'yaw_roll_motion': ['motor13', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b'],
    'neck_pitch': ['neck_pitch', 'neck_pitch_ring', 'idler11', 'idler_cap11'],
    'neck': ['motor12', 'motor11', 'neck_link_a', 'neck_link_b'],
}
HEAD_BODY = 'jaw_soft'
STEPS = {'head_pitch': 13, 'head_yaw': 18, 'head_roll': 11}


def boxes():
    out = [('pcb', 'body', [X_REAR, Y_AT_X0 - 30.0, Z_AT_Y0 - 30.0], [X_REAR + PCB, Y_AT_X0, Z_AT_Y0]),
           ('solder tails', 'body', [X_REAR + PCB, Y_AT_X0 - 30.0, Z_AT_Y0 - BAND], [X_LIMIT, Y_AT_X0, Z_AT_Y0])]
    for p in FP['parts']:
        x0, y0, x1, y1 = p['box']
        x0, y0, x1, y1 = max(x0, 0.0), max(y0, 0.0), min(x1, 30.0), min(y1, 30.0)
        body, plug = LOW, None
        for prefix, b, pl in SHAPES:
            if p['footprint'].startswith(prefix):
                body, plug = b, pl
        lo_yz, hi_yz = [Y_AT_X0 - x1, Z_AT_Y0 - y1], [Y_AT_X0 - x0, Z_AT_Y0 - y0]
        out.append((p['ref'], 'body', [X_REAR - body] + lo_yz, [X_REAR] + hi_yz))
        if plug:
            px0, px1 = x0, x1
            if p['ref'] in PLUG_CELLS:             # a socket longer than its plug: the plug stands on its first cells only
                px1 = min(x1, x0 + 2.54 * PLUG_CELLS[p['ref']] + 0.5)
            out.append((p['ref'], 'plug', [X_REAR - plug, Y_AT_X0 - px1, Z_AT_Y0 - y1],
                        [X_REAR - body, Y_AT_X0 - px0, Z_AT_Y0 - y0]))
    return [(r, k, np.array(lo), np.array(hi)) for r, k, lo, hi in out]


def home(bx):
    g, owner = S.grid(S.REMOVED | S.SOFT)
    centres = {k: S.REGION[0] + (ijk + 0.5) * S.VOX for k, ijk in owner.items()}
    res = {}
    for cl in CLEARANCES:
        hits = []
        for ref, kind, lo, hi in bx:
            for key, c in centres.items():
                n = int(((c > lo - cl) & (c < hi + cl)).all(1).sum())
                if n:
                    hits.append({'board_part': ref, 'kind': kind, 'head_part': key, 'voxels': n})
        res[f'clearance_{cl:g}_mm'] = hits
    return res


def body_T(mj, M, D, adr, q):
    D.qpos[:] = M.qpos0
    for j, v in q.items():
        D.qpos[adr[j]] = v
    mj.mj_kinematics(M, D)
    tb = M.body('trunk_base').id
    R0, p0 = D.xmat[tb].reshape(3, 3), D.xpos[tb]
    out = {}
    for b in list(MOVING) + [HEAD_BODY]:
        i = M.body(b).id
        T = np.eye(4)
        T[:3, :3] = R0.T @ D.xmat[i].reshape(3, 3)
        T[:3, 3] = R0.T @ (D.xpos[i] - p0) * 1000.0
        out[b] = T
    return out


def poses(bx):
    import mujoco as mj
    M = mj.MjModel.from_xml_path(str(XML))
    D = mj.MjData(M)
    adr = {M.joint(i).name: int(M.jnt_qposadr[i]) for i in range(M.njnt)}
    rng = {j: M.jnt_range[M.joint(j).id].copy() for j in STEPS}
    T0 = body_T(mj, M, D, adr, {})
    region = S.REGION
    S.REGION = np.array([[-1e4] * 3, [1e4] * 3])          # the moving parts start outside the head region
    pts = {}
    for body, keys in MOVING.items():
        for p in S.GUIDE['parts']:
            if p['key'] in keys:
                pts[(body, p['key'])] = S.surface_points(*S.mesh(p), step=1.0)
    S.REGION = region
    corners = {k: np.array(list(itertools.product(*zip(P.min(0), P.max(0))))) for k, P in pts.items()}
    seen = set()
    bb = S.BREADBOARD                       # on the robot today: the reference the new board is compared with
    sets = {'new_board': bx,
            'breadboard_today': [('breadboard', 'body', np.array(bb[0]), np.array(bb[1])),
                                 ('breadboard', 'plug', np.array([bb[0][0] - S.PLUG, bb[0][1], bb[0][2]]),
                                  np.array([bb[0][0], bb[1][1], bb[1][2]]))]}
    near_lo = np.min([b[2] for s in sets.values() for b in s], 0) - 6.0
    near_hi = np.max([b[3] for s in sets.values() for b in s], 0) + 6.0
    # gap field on a 0.5 mm grid around the board: distance (largest-axis measure, as in the voxel check) from each
    # cell centre to the nearest box and which box that is; a pose then costs one lookup per surface point
    shape = np.ceil((near_hi - near_lo) / S.VOX).astype(int)
    cx, cy, cz = [near_lo[a] + (np.arange(shape[a]) + 0.5) * S.VOX for a in range(3)]
    field = {}
    for name, boxset in sets.items():
        gap = np.full(shape, 99.0)
        which = np.zeros(shape, dtype=int)
        for b, (_, _, lo, hi) in enumerate(boxset):
            dx = np.maximum(lo[0] - cx, cx - hi[0])[:, None, None]
            dy = np.maximum(lo[1] - cy, cy - hi[1])[None, :, None]
            dz = np.maximum(lo[2] - cz, cz - hi[2])[None, None, :]
            d = np.maximum(np.maximum(dx, dy), dz).clip(min=0.0)
            closer = d < gap
            gap[closer] = d[closer]
            which[closer] = b
        field[name] = (gap, which)
    by_roll = {name: {} for name in sets}   # roll deg -> smallest gap over pitch and yaw, with what and where
    touched = {name: {} for name in sets}   # roll deg -> every "board part kind / head part" pair that touches
    n = 0
    axes = [np.linspace(rng[j][0], rng[j][1], k) for j, k in STEPS.items()]
    for vals in itertools.product(*axes):
        q = dict(zip(STEPS, vals))
        Tq = body_T(mj, M, D, adr, q)
        n += 1
        to_head = np.linalg.inv(Tq[HEAD_BODY] @ np.linalg.inv(T0[HEAD_BODY]))
        for (body, key), P in pts.items():
            T = to_head @ Tq[body] @ np.linalg.inv(T0[body])
            sig = (key, tuple(np.round(T[:3].ravel(), 3)))
            if sig in seen:                                   # this part already stood here relative to the head
                continue
            seen.add(sig)
            C = corners[(body, key)] @ T[:3, :3].T + T[:3, 3]
            if (C.max(0) < near_lo).any() or (C.min(0) > near_hi).any():
                continue                                      # its whole bounding box is away from the board
            Q = P @ T[:3, :3].T + T[:3, 3]
            Q = Q[((Q > near_lo) & (Q < near_hi)).all(1)]
            if not len(Q):
                continue
            ijk = np.minimum(((Q - near_lo) / S.VOX).astype(int), shape - 1)
            roll = round(float(np.degrees(q['head_roll'])), 1)
            for name, (gap, which) in field.items():
                d = gap[ijk[:, 0], ijk[:, 1], ijk[:, 2]]
                for b in np.unique(which[ijk[:, 0], ijk[:, 1], ijk[:, 2]][d == 0]):
                    touched[name].setdefault(roll, set()).add(f'{sets[name][b][0]} {sets[name][b][1]} / {key}')
                i = int(d.argmin())
                if d[i] < by_roll[name].get(roll, {'gap_mm': 6.0})['gap_mm']:
                    b = sets[name][int(which[ijk[i, 0], ijk[i, 1], ijk[i, 2]])]
                    by_roll[name][roll] = {
                        'gap_mm': round(float(d[i]), 2), 'head_part': key, 'board_part': b[0], 'kind': b[1],
                        'touching_points': int((d == 0).sum()),
                        'pose_deg': {j: round(float(np.degrees(v)), 1) for j, v in q.items()}}
    return {'poses': n, 'joint_range_deg': {j: [round(float(np.degrees(v)), 1) for v in rng[j]] for j in rng},
            'note': 'smallest gap per head_roll over all head_pitch and head_yaw; a roll that is not listed stays over 6 mm',
            'smallest_gap_by_roll': {name: dict(sorted(v.items())) for name, v in by_roll.items()},
            'touching_by_roll': {name: {r: sorted(s) for r, s in sorted(v.items())} for name, v in touched.items()}}


def main():
    bx = boxes()
    out = {'guide_revision': S.GUIDE['revision'], 'not_modelled': 'wires',
           'board': {'robot_y': [Y_AT_X0 - 30.0, Y_AT_X0], 'robot_z': [Z_AT_Y0 - 30.0, Z_AT_Y0],
                     'rear_face_x': round(X_REAR, 2), 'deepest_plug_x': round(min(b[2][0] for b in bx), 2)},
           'home': home(bx)}
    print(json.dumps(out, indent=1), flush=True)
    out['head_poses'] = poses(bx)
    print(json.dumps(out['head_poses'], indent=1))
    (HERE / 'fit-check.json').write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
