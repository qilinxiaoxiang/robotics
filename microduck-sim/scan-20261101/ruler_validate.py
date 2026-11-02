"""Independent test: offsets taken from the 3D scans (not fitted to the ruler). Refit only the camera rotation on the
STANDING captures, then predict the 54 bend ruler ticks. No bow correction unless the case names it."""
import os, sys, math, numpy as np
B = os.path.expanduser("~/code/robotics/microduck-sim/guide/firmware/mac/camera-calib-20261030/bend-20261030")
sys.path.insert(0, B); os.chdir(B)
import bendfit as bf
obs_all = bf.load_obs(1.0, 1.0)
obs = obs_all[0]
stand = [o for o in obs if o["kind"] == "stand"]
tick = [o for o in obs if o["kind"] == "tick"]
edge = [o for o in obs if o["kind"] in ("edge",)]
print("rows stand", len(stand), "tick", len(tick), "edge", len(edge))
CASES = [("chain only, no bow", {}, False, True), ("current: chain + bow -13 mm, mount as deployed", {}, True, False),
         ("scan: neck -10.4 deg", {"neck0": -10.41}, False, True), ("scan: trunk +9.7 deg (imu_p +)", {"imu_p": 9.69}, False, True), ("scan: trunk +9.7 deg (imu_p -)", {"imu_p": -9.69}, False, True),
         ("scan: neck -16.4 head -8.0", {"neck0": -16.44, "head0": -8.02}, False, True), ("scan: trunk +5.7 neck -9.3 head -6.7", {"imu_p": -5.72, "neck0": -9.32, "head0": -6.68}, False, True),
         ("sign check: neck +10.4", {"neck0": 10.41}, False, True)]
names = ["pitch", "yaw", "roll"]
for label, fixed, keep_bow, refit in CASES:
    k = bf.BendKin()
    if not keep_bow: k.bow = None
    k.set_params(fixed)
    if refit:
        p, std, means = bf.fit(k, stand, names)
    else:
        p = {n: k.p[n] for n in names}; means = bf.group_means(stand, bf.residuals(k, stand))
    sr = [m for m in means.values() if not np.isnan(m[0])]
    srms = math.sqrt(np.mean([a*a + b*b for a, b in sr]))
    # sweep ruler dy are nuisance on y only; tick x is what the acceptance reads
    res = bf.residuals(k, tick)
    g = {}
    for o, r in zip(tick, res):
        if r is not None: g.setdefault(o["point"], []).append(r[0] * 1000)
    m = {pt: float(np.mean(v)) for pt, v in g.items()}
    x = np.array(list(m.values()))
    groups = {}
    for pt, v in m.items():
        groups.setdefault(pt[5:].rsplit("_", 1)[0], []).append(round(v, 1))
    print(f"\n{label}: mount {[round(p[n],2) for n in names]} stand rms {srms:.1f} mm | ticks n {len(x)} worst |x| {np.abs(x).max():.1f} rms {np.sqrt((x**2).mean()):.1f} mean {x.mean():+.1f} mm")
    print("  ", groups)
