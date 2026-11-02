"""Do physical offsets (trunk, neck, head) with the camera rotation survive the hold-out test that the old pivot models failed
(fit on one group of bend poses plus standing, predict the other)? Also: where do free fits land, against the scan values?"""
import os, sys, math, numpy as np
B = os.path.expanduser("~/code/robotics/microduck-sim/guide/firmware/mac/camera-calib-20261030/bend-20261030")
sys.path.insert(0, B); os.chdir(B)
import bendfit as bf
obs = bf.load_obs(1.0, 1.0)[0]
rows = [o for o in obs if o["kind"] in ("stand", "tick")]
def ev(k, test):
    g = {}
    for o, r in zip(test, bf.residuals(k, test)):
        if r is not None: g.setdefault(o["point"], []).append(r[0] * 1000)
    return {p: float(np.mean(v)) for p, v in g.items()}
def stats(m):
    x = np.array(list(m.values())); return f"n {len(x)} worst {np.abs(x).max():.1f} rms {np.sqrt((x**2).mean()):.1f} mean {x.mean():+.1f}"
def stand_rms(k):
    st = [o for o in rows if o["kind"] == "stand"]
    m = bf.group_means(st, bf.residuals(k, st))
    return math.sqrt(np.mean([a*a + b*b for a, b in m.values() if not np.isnan(a)]))
SETS = {"bow-free chain: camera rot only": ["pitch","yaw","roll"],
        "neck": ["pitch","yaw","roll","neck0"], "trunk": ["pitch","yaw","roll","imu_p"], "neck+head": ["pitch","yaw","roll","neck0","head0"], "trunk+neck": ["pitch","yaw","roll","imu_p","neck0"],
        "trunk+neck+head": ["pitch","yaw","roll","imu_p","neck0","head0"]}
START = {"neck0": -10.0, "imu_p": -5.0, "head0": -5.0}
for label, names in SETS.items():
    k = bf.BendKin(); k.bow = None
    k.set_params({n: START[n] for n in names if n in START})
    p, std, _ = bf.fit(k, rows, names)
    print(f"\n{label}: {[(n, round(p[n],2), round(std[n],2)) for n in names]}\n   full: ticks {stats(ev(k, [o for o in rows if o['kind']=='tick']))} | stand rms {stand_rms(k):.1f}")
    for tr, te, nm in ((lambda o: o["sweep"] != "sweep1", lambda o: o["sweep"] == "sweep1", "train s2+s3 -> test s1 (rise)"), (lambda o: o["sweep"] in (None, "sweep1"), lambda o: o["sweep"] in ("sweep2","sweep3"), "train s1 -> test s2+s3 (bow)")):
        k2 = bf.BendKin(); k2.bow = None
        k2.set_params({n: START[n] for n in names if n in START})
        p2, _, _ = bf.fit(k2, [o for o in rows if tr(o)], names)
        print(f"   {nm}: {stats(ev(k2, [o for o in rows if o['kind']=='tick' and te(o)]))} params {[round(p2[n],1) for n in names]}")
