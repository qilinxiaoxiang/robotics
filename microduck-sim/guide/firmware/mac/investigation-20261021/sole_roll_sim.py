"""What-if: the two sole collision geoms rolled about the robot's forward axis by (left_deg, right_deg) in the as-built model
(10/20 manifest copy, real flags 7.0 V / 4 % drops), then (a) the open-loop stand (walk_brain stand mode, NEUTRAL, KP 400)
for T s and/or (b) stand61 at zero command from t = 1 s for T-1 s. Implemented as a rotated foot geom (m.geom_quat of
left_foot_collision / right_foot_collision), not as an ankle offset, so the joints and the policy see nothing different:
only the floor contact changes. Sim only.  Usage: sole_roll_sim.py <left_deg> <right_deg> <ol|s61> <T> <out.json>"""
import json, math, os, sys
sys.path.insert(0, "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac/stand-pose-study-20261020")
import stand_sim as S  # noqa: E402  (re-execs under the sim venv)
import mujoco, numpy as np  # noqa: E402
sg = sys.modules[S.bsc.feet_flat_rot.__module__]
L, R, MODE, T, OUT = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3], float(sys.argv[4]), sys.argv[5]
_orig = S._load

def _load(kp, volt, friction, head_g, lid, cal=None):
    m, d, c, names, bam = _orig(kp, volt, friction, head_g, lid, cal)
    sg.setup(m, d, names, {n: 0.0 for n in S.wb.NAMES})
    for g, deg in (("left_foot_collision", L), ("right_foot_collision", R)):
        gid = m.geom(g).id
        Rg = d.geom_xmat[gid].reshape(3, 3)
        ax_local = Rg.T @ np.array([1.0, 0, 0])     # world x (forward) at qpos0, in the geom frame
        qrot = np.zeros(4); mujoco.mju_axisAngle2Quat(qrot, ax_local, math.radians(deg))
        qn = np.zeros(4); mujoco.mju_mulQuat(qn, m.geom_quat[gid], qrot); m.geom_quat[gid] = qn
    mujoco.mj_forward(m, d)
    return m, d, c, names, bam

S._load = _load
if MODE == "ol":
    r = S.run_case(dict(S.NEUTRAL), T=T)
else:
    r = S.run_case(dict(S.NEUTRAL), T=T, walk_at=1.0, walk_s=T - 1.0)
tr = r.pop("trace")
r.update(left_roll_deg=L, right_roll_deg=R, mode=MODE, pitch_trace=[(t, p) for t, _, p, _ in tr[::10]],
         tilt_trace=[(t, tl) for t, tl, _, _ in tr[::10]])
json.dump(r, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in r.items() if k not in ("pitch_trace", "tilt_trace")}))
