"""Shared helpers for the power-support origin study (read-only on all project sources).

Robot frame: mm, x forward, y left, z up (= MuJoCo trunk_base frame, = guide frame).
Leg parts are the guide audit solids (ia_lib cache), which sit at MJCF qpos0; they are moved with
MuJoCo forward kinematics of robot_allcollisions.xml (the model the phase-1 walking runs used).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
IA = HERE.parent
sys.path.insert(0, str(IA))
import ia_lib  # noqa: E402

SIM = IA.parents[2]                      # .../microduck-sim
CB = SIM / 'hardware-design-20260912/whole-robot-20260912/assembly/compact-battery'
PRINTED = SIM / 'build-pack-20260913/assembly/print-parts/current/power-support-integrated-print.stl'
XML = SIM / 'microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml'
PHASE1 = SIM / 'build-pack-20260913/phase1/simulation'
SCRATCH = Path('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/'
               '92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/pso')
SCRATCH.mkdir(parents=True, exist_ok=True)

ORIG_ZMIN = -44.07  # original upstream power_support lowest point (measured in ps_geometry.py)

SIDE = {
    'left': dict(joints=['left_hip_yaw', 'left_hip_roll', 'left_hip_pitch', 'left_knee', 'left_ankle'],
                 parts={'yaw2roll': ['yaw', 'motor9', 'ring9', 'passive', 'washer9'], 'hip_l': ['hip', 'ring8'],
                        'upper_leg_left': ['thigh', 'plate', 'motor8', 'motor7', 'ring7'],
                        'leg': ['lower', 'motor6', 'smallring', 'washer6'], 'ankle_left': ['ankle', 'foot']}),
    'right': dict(joints=['right_hip_yaw', 'right_hip_roll', 'right_hip_pitch', 'right_knee', 'right_ankle'],
                  parts={'bearing_roll': ['right_yaw', 'motor4', 'ring4', 'right_passive', 'washer4'], 'hip_l_2': ['right_hip', 'ring3'],
                         'upper_leg_right': ['right_thigh', 'right_plate', 'motor3', 'motor2', 'ring2'],
                         'leg_2': ['right_lower', 'motor1', 'right_smallring', 'washer1'], 'ankle_right': ['right_ankle', 'right_foot']}),
}
LABEL = {}
for s in ('left', 'right'):
    for k in SIDE[s]['parts'][list(SIDE[s]['parts'])[3]]:
        LABEL[k] = 'shin'
    for k in SIDE[s]['parts'][list(SIDE[s]['parts'])[2]]:
        LABEL[k] = 'thigh/knee'
    for k in SIDE[s]['parts'][list(SIDE[s]['parts'])[4]]:
        LABEL[k] = 'ankle/foot'
    for k in SIDE[s]['parts'][list(SIDE[s]['parts'])[0]] + SIDE[s]['parts'][list(SIDE[s]['parts'])[1]]:
        LABEL[k] = 'hip'

# Region boxes in priority order (first match wins). Derived from build_compact_battery.py
# (deck z -57.5..-55.5 with bosses to -53.5; hanger posts x -37.5..-33.5, |y| 18.0..20.4, z -57.5..-35.5).
REGIONS = [
    ('lower_post_left',  [[-38.0, 17.95, -58.0], [-33.0, 21.0, ORIG_ZMIN]]),
    ('lower_post_right', [[-38.0, -21.0, -58.0], [-33.0, -17.95, ORIG_ZMIN]]),
    ('deck_and_bosses',  [[-60.0, -17.95, -58.0], [-11.0, 17.95, -53.0]]),
    ('upper_post_left',  [[-38.0, 17.95, ORIG_ZMIN], [-33.0, 21.0, -35.4]]),
    ('upper_post_right', [[-38.0, -21.0, ORIG_ZMIN], [-33.0, -17.95, -35.4]]),
    ('small_regulator_holder', [[-20.0, -7.0, 3.0], [9.0, 6.0, 34.0]]),
]


def region_of(p, added: bool | None = None) -> str:
    p = np.asarray(p, float)
    for name, (lo, hi) in REGIONS:
        if np.all(p >= np.array(lo) - 1e-6) and np.all(p <= np.array(hi) + 1e-6):
            return name
    if added is False:
        return 'original_frame_kept'
    return 'battery_bay_and_other_added' if added else 'original_frame_or_bay'


def tm_load(path):
    import trimesh
    return trimesh.load(str(path), force='mesh', process=True)


def solid(key):
    """Guide audit solid (robot frame) as (v, f)."""
    return ia_lib.load_solid(key)


def to_m(v, f):
    return ia_lib.to_manifold(np.asarray(v, float), np.asarray(f, np.int64))


def mesh_to_m(m):
    return to_m(m.vertices, m.faces)


def box_m(lo, hi):
    import manifold3d as m3
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    return m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def from_m(man):
    import trimesh
    v, f = ia_lib.from_manifold(man)
    return trimesh.Trimesh(v, f, process=False)


def affine34(T):
    return [list(map(float, T[0, :4])), list(map(float, T[1, :4])), list(map(float, T[2, :4]))]


class FK:
    """MuJoCo forward kinematics; body transforms relative to trunk_base, mm."""

    def __init__(self):
        import mujoco
        self.mj = mujoco
        self.M = mujoco.MjModel.from_xml_path(str(XML))
        self.D = mujoco.MjData(self.M)
        self.jnames = [self.M.joint(i).name for i in range(self.M.njnt)]
        self.qadr = {n: int(self.M.jnt_qposadr[i]) for i, n in enumerate(self.jnames)}
        self.T0 = self.body_T({})

    def body_T(self, q: dict):
        mj = self.mj; M = self.M; D = self.D
        D.qpos[:] = M.qpos0
        for j, v in q.items():
            D.qpos[self.qadr[j]] = v
        mj.mj_kinematics(M, D)
        tb = M.body('trunk_base').id
        R0 = D.xmat[tb].reshape(3, 3); p0 = D.xpos[tb]
        out = {}
        for i in range(M.nbody):
            T = np.eye(4)
            T[:3, :3] = R0.T @ D.xmat[i].reshape(3, 3)
            T[:3, 3] = R0.T @ (D.xpos[i] - p0) * 1000.0
            out[M.body(i).name] = T
        return out

    def part_T(self, q: dict):
        """Transform taking a qpos0 guide part to pose q, per body."""
        Tq = self.body_T(q)
        return {b: Tq[b] @ np.linalg.inv(self.T0[b]) for b in Tq}

    def anchor(self, jname, q=None):
        mj = self.mj; M = self.M; D = self.D
        self.body_T(q or {})
        j = M.joint(jname).id; tb = M.body('trunk_base').id
        R0 = D.xmat[tb].reshape(3, 3)
        return R0.T @ (D.xanchor[j] - D.xpos[tb]) * 1000.0, R0.T @ D.xaxis[j]


JOINT_ORDER_14 = ["left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle", "neck_pitch", "head_pitch",
                  "head_yaw", "head_roll", "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle"]


def walking_sources():
    """All phase-1 walking trajectories that store per-frame qpos (rows). Adopted = did not fall and not a blend run."""
    files = sorted(PHASE1.glob('phase1-*.json')) + sorted(PHASE1.glob('candidate-*/phase1-*.json'))
    out = []
    for f in files:
        if f.name.endswith('.config.json'):
            continue
        d = json.loads(f.read_text())
        rows = d.get('rows')
        if not isinstance(rows, list) or not rows or 'qpos' not in rows[0]:
            continue
        rel = str(f.relative_to(PHASE1))
        c = d.get('config', {})
        out.append(dict(file=rel, frames=len(rows), fell=bool(d.get('fell')), blend='blend' in rel, command=c.get('command'),
                        kp=c.get('kp'), sensor_delay_ticks=c.get('sensor_delay_ticks') or 0, action_delay_ticks=c.get('action_delay_ticks'),
                        delay_compensation=c.get('delay_compensation'), remove_old_battery_kg=c.get('remove_old_battery_kg')))
    return out


def jdump(obj, path):
    def conv(o):
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))
    Path(path).write_text(json.dumps(obj, indent=1, default=conv))
