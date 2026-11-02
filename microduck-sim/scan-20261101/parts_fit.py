"""Colour-classed two-way fit of the body parts between foot and head, each started where the logged joints put it."""
import sys, json, numpy as np
S = sys.argv[1]
sys.argv = [sys.argv[0], S]
exec(open(S + "/cfit_lib.py").read())
rng = np.random.default_rng(5)
PARTS = (("trunk", "trunk_base", {"white": "w", "orange": "o"}), ("thigh_l", "upper_leg_left", {"white": "w"}), ("thigh_r", "upper_leg_right", {"white": "w"}), ("neck", "neck", {"orange": "o"}), ("hip_l", "hip_l", {"orange": "o"}), ("hip_r", "hip_l_2", {"orange": "o"}))
rep = json.load(open(S + "/color_fit.json"))
for scan, pose in (("a", "stand"), ("b", "bend")):
    D = np.load(f"{S}/{scan}_robot.npz"); L, C = D["L"], D["C"]
    yaw, tg = GLOBAL[scan]
    Q = L @ rz(yaw).T + np.array(tg); cls = classes(C)
    M = np.load(f"{S}/model_{pose}.npz", allow_pickle=True)
    mp, lab, names, gcl = M["pts"], M["lab"], list(M["names"]), M["gcolor"]
    print("=====", pose)
    for part, body, want in PARTS:
        idx = lab == names.index(body)
        Pm = {want[k]: mp[idx & (gcl == k)][::2] for k in want if (idx & (gcl == k)).sum() > 200}
        if not Pm: print(part, "no model colour"); continue
        c = np.vstack(list(Pm.values())).mean(0)
        src = {}
        for k in Pm:
            d, _ = KD(Pm[k]).query(Q, distance_upper_bound=0.03)
            src[k] = Q[np.isfinite(d) & (cls == k) & (Q[:, 2] > 0.001)]
        res = []
        for s in range(16):
            ang = rng.normal(0, np.radians(5), 3) if s else np.zeros(3)
            R0 = Rot.from_rotvec(ang).as_matrix(); tt = rng.uniform(-0.012, 0.012, 3) if s else np.zeros(3)
            f = fit(src, Pm, R0, c - R0 @ c + tt)
            if f: res.append(f)
        res.sort(key=lambda f: f[2]); b = res[0]
        near = [f for f in res if f[2] < b[2] * 1.08]
        rv = np.array([Rot.from_matrix(f[0]).as_rotvec(degrees=True) for f in near])
        sh = np.array([(f[0] @ c + f[1] - c) * 1000 for f in near])
        print(f"{part:8s} n {[len(v) for v in src.values()]} cost {b[2]:.2f} cov {b[3]:.2f} near {len(near)}/{len(res)} shift mm {np.round(sh[0], 1)} +-{np.round(sh.std(0), 1)} rot deg {np.round(rv[0], 1)} +-{np.round(rv.std(0), 1)}")
        rep[pose][part] = dict(R=b[0].tolist(), t=b[1].tolist(), cost=b[2], cov=float(b[3]), near=len(near), rot_deg=rv[0].tolist(), rot_std=rv.std(0).tolist(), centre_shift_mm=sh[0].tolist())
json.dump(rep, open(S + "/color_fit2.json", "w"), indent=1)
