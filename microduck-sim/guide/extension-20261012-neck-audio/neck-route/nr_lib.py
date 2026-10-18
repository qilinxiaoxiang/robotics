"""Shared helpers for the neck-route feasibility study (read-only on every V1.8 / guide source).

Frame: robot frame, mm, x forward, y left, z up (MJCF trunk_base at q = 0), the same frame as guide/print/world and the
interference-audit solid cache. Joint kinematics come from the MJCF; each guide part is assigned to the MJCF body whose
visual meshes occupy the same place (checked in kin_check.py).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[2]                                   # .../microduck-sim
GUIDE = SIM / 'guide'
IA = GUIDE / 'content' / 'interference-audit'
sys.path.insert(0, str(IA))
import ia_lib  # noqa: E402  (read-only helpers; CACHE holds the closed audit solids)

ROUTES = GUIDE / 'content' / 'routes.json'
WORLD = GUIDE / 'print' / 'world'
XML = SIM / 'microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml'
SCRATCH = Path(os.environ.get('NR_SCRATCH', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/'
                                            'feb8343a-52e2-499e-88f6-f1b3a6b98491/scratchpad/neck-route'))
SCRATCH.mkdir(parents=True, exist_ok=True)
NOTCHLESS_CAP = HERE / 'study-solids' / 'head_cap-no-notch.stl'

# Guide part key -> MJCF body that carries it (kin_check.py verifies the assignment with the MJCF visual-mesh bounds
# and with sweeps that must not create new overlaps between neighbouring bodies).
TORSO = ['torso_base', 'shell_left', 'shell_right', 'ring10_torso', 'ring5_torso', 'imu_board', 'imu_sh4_receiving',
         'openrb_board', 'rear_pack', 'rear_pack_cover', 'idler12', 'idler_cap12']
NECK = ['motor12', 'motor11', 'neck_link_a', 'neck_link_b']
PITCH = ['neck_pitch', 'neck_pitch_ring', 'idler11', 'idler_cap11']
YAW = ['motor13', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b']
HEAD_FIXED = ['motor14', 'motor15', 'jaw_support', 'head_bottom', 'head_cap', 'face_panel', 'eye_trim', 'camera_board',
              'mouth_sliding_ring', 'pi']
JAW = ['jaw_frame']
BODY_OF = {}
for _b, _ks in (('trunk_base', TORSO), ('neck', NECK), ('neck_pitch', PITCH), ('yaw_roll_motion', YAW),
                ('jaw_soft', HEAD_FIXED), ('jaw', JAW)):
    for _k in _ks:
        BODY_OF[_k] = _b
BODY_ORDER = ['trunk_base', 'neck', 'neck_pitch', 'yaw_roll_motion', 'jaw_soft', 'jaw']
JOINTS = ['neck_pitch', 'head_pitch', 'head_yaw', 'head_roll']
JAW_PIVOT = np.array([26.1, 0.0, 118.6146])
JAW_AXIS = np.array([0.0, 1.0, 0.0])
JAW_OPEN_MAX_DEG = 40.0


def pi_keys(guide_parts):
    """Every Pi-group key (board, header, pins, receiving housings, components) rides on the head."""
    return [p['key'] for p in guide_parts if p['key'].startswith('head_pi_')]


def body_of(key):
    if key in BODY_OF:
        return BODY_OF[key]
    if key.startswith('head_pi_') or key == 'pi':
        return 'jaw_soft'
    return None


def load_solid(key):
    """Closed audit solid for a guide key; head_cap may be replaced by the notch-less study cap."""
    if key == 'head_cap_nonotch':
        import trimesh
        m = trimesh.load(NOTCHLESS_CAP, force='mesh')
        return np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
    return ia_lib.load_solid(key)


def routes():
    return json.loads(ROUTES.read_text())['routes']


def rot(axis, ang):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def T_about(point, axis, ang):
    T = np.eye(4)
    R = rot(axis, ang)
    T[:3, :3] = R
    T[:3, 3] = np.asarray(point) - R @ np.asarray(point)
    return T


class FK:
    """MuJoCo kinematics. part_T(q) gives, per body, the 4x4 transform taking a q = 0 guide part to pose q (mm)."""

    def __init__(self):
        import mujoco
        self.mj = mujoco
        self.M = mujoco.MjModel.from_xml_path(str(XML))
        self.D = mujoco.MjData(self.M)
        self.qadr = {self.M.joint(i).name: int(self.M.jnt_qposadr[i]) for i in range(self.M.njnt)}
        self.range = {j: self.M.jnt_range[self.M.joint(j).id].copy() for j in JOINTS}
        self.T0 = self._body_T({})

    def _body_T(self, q):
        mj, M, D = self.mj, self.M, self.D
        D.qpos[:] = M.qpos0
        for j, v in q.items():
            if j in self.qadr:
                D.qpos[self.qadr[j]] = v
        mj.mj_kinematics(M, D)
        tb = M.body('trunk_base').id
        R0 = D.xmat[tb].reshape(3, 3)
        p0 = D.xpos[tb]
        out = {}
        for b in BODY_ORDER[:-1]:
            i = M.body(b).id
            T = np.eye(4)
            T[:3, :3] = R0.T @ D.xmat[i].reshape(3, 3)
            T[:3, 3] = R0.T @ (D.xpos[i] - p0) * 1000.0
            out[b] = T
        return out

    def part_T(self, q):
        """q: dict joint -> rad; optional 'jaw' in degrees of opening (0..40)."""
        Tq = self._body_T(q)
        out = {b: Tq[b] @ np.linalg.inv(self.T0[b]) for b in Tq}
        out['jaw'] = out['jaw_soft'] @ T_about(JAW_PIVOT, JAW_AXIS, np.radians(q.get('jaw', 0.0)))
        return out

    def anchors(self, q=None):
        mj, M, D = self.mj, self.M, self.D
        self._body_T(q or {})
        tb = M.body('trunk_base').id
        R0 = D.xmat[tb].reshape(3, 3)
        out = {}
        for j in JOINTS:
            k = M.joint(j).id
            out[j] = (R0.T @ (D.xanchor[k] - D.xpos[tb]) * 1000.0, R0.T @ D.xaxis[k])
        return out


def apply(T, p):
    p = np.asarray(p, float)
    return p @ T[:3, :3].T + T[:3, 3]


def polyline_length(p):
    p = np.asarray(p, float)
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())


def resample(p, step=0.5):
    p = np.asarray(p, float)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(np.ceil(s[-1] / step)) + 1)
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, p[:, i]) for i in range(3)], 1)


def jdump(obj, path):
    def conv(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, Path):
            return str(o)
        raise TypeError(type(o))
    Path(path).write_text(json.dumps(obj, indent=1, default=conv))


# Existing cables that already run through the neck and head (guide-data.json, radius as the guide draws them).
OTHER_CABLES = ['dxl-n12', 'dxl-12-11', 'dxl-11-13', 'dxl-13-14', 'dxl-14-15', 'csi']


def cable_tubes(step=0.25):
    """(id, densely sampled centreline, radius) for OTHER_CABLES; the centreline is the guide path polyline."""
    g = ia_lib.load_guide()
    out = []
    for c in g['cables']:
        if c['id'] in OTHER_CABLES:
            out.append((c['id'], resample(np.array(c['path'], float), step), float(c.get('radius') or 0.9)))
    return out


def rnd(x, n=2):
    return ia_lib.rnd(x, n)
