"""Backpack rear surface in the trunk frame: scan (via the trunk's fitted pose) against the model."""
import sys, json, numpy as np
from scipy.spatial import cKDTree as KD
S = sys.argv[1]
exec(open(S + "/cfit_lib.py").read())
rep = json.load(open(S + "/color_fit2.json"))
for scan, pose in (("a", "stand"), ("b", "bend")):
    D = np.load(f"{S}/{scan}_robot.npz"); L, C = D["L"], D["C"]
    yaw, tg = GLOBAL[scan]; Q = L @ rz(yaw).T + np.array(tg); cls = classes(C)
    M = np.load(f"{S}/model_{pose}.npz", allow_pickle=True); mp, lab, names, gcl = M["pts"], M["lab"], list(M["names"]), M["gcolor"]
    idx = lab == names.index("trunk_base"); Pm = mp[idx]
    R, t = np.array(rep[pose]["trunk"]["R"]), np.array(rep[pose]["trunk"]["t"])
    Qt = (Q - t) @ R                       # scan into the model's posed trunk
    near = KD(Pm).query(Qt, distance_upper_bound=0.04)[0]; m = np.isfinite(near) & (cls == "o") & (Qt[:, 2] > 0.02)
    g = np.array(json.load(open(S + "/poses.json"))[pose]["gb"])
    # trunk axes in foot frame via the posed model trunk's PCA-free frame: use gravity tilt only (pitch)
    p = np.arcsin(g[0]); ex = np.array([np.cos(p), 0, -np.sin(p)]); ez = np.array([np.sin(p), 0, np.cos(p)])
    f = lambda A, u, q: float(np.percentile(A @ u, q) * 1000)
    orange = Pm[gcl[idx] == "orange"]
    print(pose, "rear-most along trunk x (p0.5): model orange", round(f(orange, ex, 0.5), 1), "scan orange", round(f(Qt[m], ex, 0.5), 1), "| top along trunk z (p99.5): model", round(f(orange, ez, 99.5), 1), "scan", round(f(Qt[m], ez, 99.5), 1), "| width y: model", round(np.ptp(np.percentile(orange[:, 1], [0.5, 99.5])) * 1000, 1), "scan", round(np.ptp(np.percentile(Qt[m, 1], [0.5, 99.5])) * 1000, 1))
