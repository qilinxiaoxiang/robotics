"""Where along each leg does the roll sit? Colour-classed two-way rigid fits (cfit_lib.fit, no scale, multi-start) of
trunk, hip brackets, thighs and feet, reported as roll about the robot's forward axis, real minus the posed model.

    python lean_fit.py <dir> <scan>:<pose>:<yaw_deg>:<tx>:<ty> [...]     # yaw and t from fit_scan.py's "global planar ICP" line

The model trunk is placed with the pose's IMU gravity, so every angle here is relative to "encoders plus IMU". The useful
numbers are the differences along a chain (hip bracket minus trunk = angle hidden at the hip roll joint; thigh minus hip
bracket = hidden at the hip yaw joint; foot minus thigh = hidden below), and the left chain against the right.
+ roll = the part's left side is higher than the model has it. The +- is the spread among near-best random starts; a part
whose starts disagree by more than about 1 deg is not measured.
fit_scan.py's plain ICP with free scale (0.75 to 0.98 on legs) slides and must not be used for these parts."""
import json
import os
import sys

import numpy as np

S = sys.argv[1]
JOBS = [a.split(":") for a in sys.argv[2:]]
_argv = sys.argv
sys.argv = [_argv[0], S]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cfit_lib.py")).read())
sys.argv = _argv

PARTS = (("trunk", "trunk_base", {"white": "w", "orange": "o"}, 0.03),
         ("hip_l", "hip_l", {"orange": "o"}, 0.03), ("hip_r", "hip_l_2", {"orange": "o"}, 0.03),
         ("thigh_l", "upper_leg_left", {"white": "w"}, 0.03), ("thigh_r", "upper_leg_right", {"white": "w"}, 0.03),
         ("foot_l", "ankle_left", {"yellow": "y", "orange": "o"}, 0.045), ("foot_r", "ankle_right", {"yellow": "y", "orange": "o"}, 0.045))
out = {}
for scan, pose, yaw, tx, ty in JOBS:
    rng = np.random.default_rng(7)
    D = np.load(f"{S}/{scan}_robot.npz")
    Q = D["L"] @ rz(float(yaw)).T + np.array([float(tx), float(ty), 0.0])
    cls = classes(D["C"])
    M = np.load(f"{S}/model_{pose}.npz", allow_pickle=True)
    mp, lab, names, gcl = M["pts"], M["lab"], list(M["names"]), M["gcolor"]
    print(f"===== scan {scan}, pose {pose}")
    rec = out[scan] = {}
    for part, body, want, reach in PARTS:
        if body not in names:
            print(f"{part:8s} body {body} not in the model")
            continue
        idx = lab == names.index(body)
        Pm = {want[k]: mp[idx & (gcl == k)][::2] for k in want if (idx & (gcl == k)).sum() > 200}
        if not Pm:
            print(f"{part:8s} no model colour")
            continue
        c = np.vstack(list(Pm.values())).mean(0)
        src = {}
        for k in Pm:
            d, _ = KD(Pm[k]).query(Q, distance_upper_bound=reach)
            src[k] = Q[np.isfinite(d) & (cls == k) & (Q[:, 2] > 0.001)]
        if min(len(v) for v in src.values()) < 60:
            print(f"{part:8s} too few scan points {[len(v) for v in src.values()]}")
            continue
        res = []
        for s in range(24):
            R0 = Rot.from_rotvec(rng.normal(0, np.radians(5), 3) if s else np.zeros(3)).as_matrix()
            f = fit(src, Pm, R0, c - R0 @ c + (rng.uniform(-0.012, 0.012, 3) if s else np.zeros(3)))
            if f:
                res.append(f)
        res.sort(key=lambda f: f[2])
        b = res[0]
        near = [f for f in res if f[2] < b[2] * 1.08]
        rv = np.array([Rot.from_matrix(f[0]).as_rotvec(degrees=True) for f in near])
        sh = (b[0] @ c + b[1] - c) * 1000
        rec[part] = dict(roll=float(rv[0][0]), roll_sd=float(rv[:, 0].std()), pitch=float(rv[0][1]), yaw=float(rv[0][2]),
                         cost_mm=b[2], near=len(near), starts=len(res), shift_mm=sh.tolist(), R=b[0].tolist(), t=b[1].tolist())
        print(f"{part:8s} n {[len(v) for v in src.values()]} cost {b[2]:.2f} mm, {len(near)}/{len(res)} starts agree | roll {rv[0][0]:+.2f} +-{rv[:, 0].std():.2f}"
              f" pitch {rv[0][1]:+.2f} +-{rv[:, 1].std():.2f} yaw {rv[0][2]:+.2f} +-{rv[:, 2].std():.2f} deg | shift mm {np.round(sh, 1)}")
    g = lambda p: rec.get(p, {}).get("roll")
    for side in "lr":
        ch = [("trunk", g("trunk")), ("hip bracket", g(f"hip_{side}")), ("thigh", g(f"thigh_{side}")), ("foot", g(f"foot_{side}"))]
        have = [(n, v) for n, v in ch if v is not None]
        print(f"  {'left ' if side == 'l' else 'right'} chain roll: " + " -> ".join(f"{n} {v:+.1f}" for n, v in have)
              + " | steps: " + ", ".join(f"{have[i + 1][0]} minus {have[i][0]} {have[i + 1][1] - have[i][1]:+.1f}" for i in range(len(have) - 1)))
json.dump(out, open(f"{S}/lean_fit.json", "w"), indent=1)
