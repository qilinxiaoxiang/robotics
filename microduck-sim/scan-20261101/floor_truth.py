"""Absolute posture of the scanned robot against the scan's own floor: which side of the pelvis is lower, how each sole
lies, and what the logged joint angles alone predict for a range of pelvis rolls.

    python floor_truth.py <dir> <scan> <pose>     # after model_pose.py and fit_scan.py; reads fit_<scan>.json, poses.json

Why this exists: fit_scan.py prints "real minus model" angles, and model_pose.py places the model trunk with the IMU
gravity of the pose (target_ground.place(q, gb)). Those angles are therefore relative to what the IMU says and can never
confirm or refute the IMU. On 2026-11-12 a trunk "+3.8 deg" from fit_scan.py was reported as the robot's lean and as
agreement with the IMU; it was neither. Everything printed here is in the floor frame (floor = RANSAC plane of the scan,
fit_scan.py's global step only turns and shifts on it), and the last block uses no IMU at all.
Weigh the parts by their fit: the soles touch the floor and fit best; a trunk or thigh fit above about 4 mm rms or with
scale far from 1 is weak evidence."""
import json
import os
import sys

import numpy as np

MAC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "guide", "firmware", "mac")
sys.path.insert(0, MAC)
os.chdir(MAC)
import target_ground as tg  # noqa: E402

S, scan, pose = sys.argv[1:4]
ID_NAMES = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "left_ankle", "left_knee",
            "left_hip_pitch", "left_hip_roll", "left_hip_yaw", "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
P = json.load(open(f"{S}/poses.json"))[pose]
fit = json.load(open(f"{S}/fit_{scan}.json"))["parts"]
q, gb = dict(zip(ID_NAMES, P["q"])), np.array(P["gb"], float)
G = tg.DuckGeometry()
m, d = G.m, G.d
FEET = (("ankle_left", "foot_l"), ("ankle_right", "foot_r"))


def side(z):
    return f"left side {'DOWN' if z < 0 else 'UP'} {abs(np.degrees(np.arcsin(z))):.2f} deg"


def sole_vertices(body):
    sid = [g for g in range(m.ngeom) if m.geom_bodyid[g] == m.body(body).id and m.geom_group[g] == 3][0]
    mid = m.geom_dataid[sid]
    va, na = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
    return (d.geom_xmat[sid].reshape(3, 3) @ m.mesh_vert[va:va + na].T).T + d.geom_xpos[sid]


def slope_left(W, lh):
    lo = W[W[:, 2] < np.quantile(W[:, 2], 0.5)]
    c, *_ = np.linalg.lstsq(np.c_[(lo - lo.mean(0)) @ lh, np.ones(len(lo))], lo[:, 2], rcond=None)
    return np.degrees(np.arctan(c[0]))


def horizontal_left():
    lh = d.xmat[m.body("trunk_base").id].reshape(3, 3)[:, 1].copy()
    lh[2] = 0
    return lh / np.linalg.norm(lh)


def real(part, p):  # model point -> where the scan puts it
    return (np.asarray(p) - np.array(fit[part]["t"])) @ np.array(fit[part]["R"])


G.place(q, gb.tolist())
left = d.xmat[m.body("trunk_base").id].reshape(3, 3)[:, 1].copy()
lh = horizontal_left()
print("1. What the IMU says (model trunk placed with the pose's gravity):", side(left[2]))
print("2. What the scan says, floor frame (+ slope = the sole's left edge is higher):")
for body, part in FEET:
    V = sole_vertices(body)
    R = np.array([real(part, v) for v in V])
    print(f"   {body}: sole slope {slope_left(R, lh):+.2f} deg, lowest point {R[:, 2].min() * 1000:+.1f} mm"
          f"   (fit {fit[part]['rms_mm']:.1f} mm rms, scale {fit[part]['scale_scan_to_cad']:.3f})")
print(f"   trunk fit: {side(float((left @ np.array(fit['trunk']['R']))[2]))}"
      f"   (fit {fit['trunk']['rms_mm']:.1f} mm rms, scale {fit['trunk']['scale_scan_to_cad']:.3f})")
hips = {s: (d.xanchor[m.joint(f"{s}_hip_pitch").id].copy(), th) for s, th in (("left", "thigh_l"), ("right", "thigh_r"))}
v = real(hips["left"][1], hips["left"][0]) - real(hips["right"][1], hips["right"][0])
vm = hips["left"][0] - hips["right"][0]
print(f"   hips from the thigh fits: left hip {'LOWER' if v[2] < 0 else 'HIGHER'} by "
      f"{abs(np.degrees(np.arctan2(v[2], np.linalg.norm(v[:2])))):.2f} deg; hip spacing {np.linalg.norm(v) * 1000:.1f} mm"
      f" against {np.linalg.norm(vm) * 1000:.1f} in the model (a mismatch here means these fits slid)")
print("3. What the logged joint angles alone predict (no IMU, no scan). Hip roll deg: right "
      f"{np.degrees(q['right_hip_roll']):+.1f}, left {np.degrees(q['left_hip_roll']):+.1f}")
n = np.hypot(gb[1], gb[2])
for r in np.arange(-2, 5.01, 0.5):
    g = gb.copy()
    g[1], g[2] = n * np.sin(np.radians(r)), -n * np.cos(np.radians(r))
    G.place(q, g.tolist())
    lh = horizontal_left()
    row = [(sole_vertices(b)[:, 2].min() * 1000, slope_left(sole_vertices(b), lh)) for b, _ in FEET]
    print(f"   pelvis left side down {r:+.1f} deg: left sole slope {row[0][1]:+.2f}, lowest {row[0][0]:+.1f} mm | "
          f"right sole slope {row[1][1]:+.2f}, lowest {row[1][0]:+.1f} mm")
print("Read block 3 against block 2: the pelvis roll whose predicted soles match the scanned soles is the scan's answer;"
      " compare that with block 1 to judge the IMU.")
