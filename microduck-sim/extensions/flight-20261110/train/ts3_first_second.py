"""Round 3 diagnostic: what a policy does in the first second of a gate episode (m3w_250 falls backward at 0.76 s
with the nominal pack at nominal gain on every seed and stands at gain400).

  $PY train/ts3_first_second.py <dir under ckpt> <manifest name> [probe flags ...]
  e.g.  $PY train/ts3_first_second.py m3w_250 nominal --stand-s 0
        $PY train/ts3_first_second.py m3w_250 nominal --stand-s 0 --kp-rl 400

One standing episode, seed 0, through flight_eval.episode (the gate's own code path). Prints every 0.1 s up to 1 s:
trunk pitch (deg, + = nose down), trunk height, and for the left leg the servo goal, the joint angle and the actuator
force of hip pitch, knee and ankle. Mac mini only (mini.sh run).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flight_eval as fe  # noqa: E402

rows = []
J = ["left_hip_pitch", "left_knee", "left_ankle"]


def hook(m, d, t):
    import mujoco
    if d.time > 1.0:
        return
    k = round(d.time / 0.1)
    if abs(d.time - k * 0.1) > m.opt.timestep / 2 or (rows and rows[-1]["t"] == k * 0.1):
        return
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, d.qpos[3:7])
    g = R.reshape(3, 3).T @ np.array([0.0, 0.0, -1.0])
    row = dict(t=round(k * 0.1, 1), pitch_deg=round(float(np.degrees(np.arctan2(-g[0], -g[2]))), 1), z=round(float(d.qpos[2]), 4))
    for j in J:
        a = m.actuator(j)
        jid = m.joint(j).id
        row[j] = (round(float(d.ctrl[a.id]), 3), round(float(d.qpos[m.jnt_qposadr[jid]]), 3), round(float(d.actuator_force[a.id]), 3))
    rows.append(row)


fe.FRAME_HOOK = hook
d, man, extra = sys.argv[1], sys.argv[2], sys.argv[3:]
r = fe.episode((str(HERE / "ckpt" / d), str(HERE / f"manifests/flightpack-{man}.json"), "stand", 0, 0.0, 8.0, False, extra))
print(json.dumps(dict(dir=d, manifest=man, extra=extra, fell_at=r["fell_at"], fall_dir=r["fall_dir"], max_tilt=r["max_tilt"])))
print("t  pitch  z   | " + " | ".join(f"{j} goal/angle/force" for j in J))
for x in rows:
    print(x["t"], x["pitch_deg"], x["z"], "|", " | ".join(" ".join(str(v) for v in x[j]) for j in J))
