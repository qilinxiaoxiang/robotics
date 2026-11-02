"""Register one scan to the posed as-built model: global yaw/xy on the floor, then per-body trimmed ICP (optional scale).
Reports each part's rigid offset from where the logged joint angles put it, in the foot frame."""
import sys, json, numpy as np
from scipy.spatial import cKDTree as KD
from scipy.spatial.transform import Rotation as Rot
from PIL import Image

S, scan, pose = sys.argv[1:4]
D = np.load(f"{S}/{scan}_robot.npz")
L, C, keep = D["L"], D["C"], D["keep"]
M = np.load(f"{S}/model_{pose}.npz", allow_pickle=True)
mp, lab, names = M["pts"], M["lab"], list(M["names"])
sites = json.load(open(f"{S}/model_sites.json"))[pose]
q = L[keep & (L[:, 2] > 0.003)]
col = C[keep & (L[:, 2] > 0.003)]
print(scan, pose, "scan pts", len(q), "model pts", len(mp))
tree = KD(mp[::3])


def score(Q, thr=0.012):
    d, _ = tree.query(Q, distance_upper_bound=0.05)
    d = np.minimum(d, 0.05)
    return np.mean(d < thr), d


def rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


# global: yaw grid with xy refinement on the floor plane
sub = q[np.random.default_rng(0).choice(len(q), min(8000, len(q)), replace=False)]
cm, cq = mp[:, :2].mean(0), sub[:, :2].mean(0)
best = (-1, None)
for a in np.radians(np.arange(0, 360, 6)):
    Rz = rz(a)
    Q0 = sub @ Rz.T
    t = cm - Q0[:, :2].mean(0)
    for _ in range(6):
        QQ = Q0 + np.r_[t, 0]
        d, i = tree.query(QQ, distance_upper_bound=0.04)
        ok = np.isfinite(d)
        if ok.sum() < 50:
            break
        t += (tree.data[i[ok], :2] - QQ[ok, :2]).mean(0)
    s = score(Q0 + np.r_[t, 0])[0]
    if s > best[0]:
        best = (s, (a, t.copy()))
print("best global yaw deg", np.degrees(best[1][0]).round(1), "frac<12mm", round(best[0], 3))


def icp(src, dst_tree, dst, R, t, s=1.0, iters=40, gate0=0.02, gate1=0.006, trim=0.85, use_scale=False, planar=False):
    """Align src -> dst: x' = s R x + t. Trimmed point-to-point with shrinking gate."""
    for k in range(iters):
        gate = gate0 + (gate1 - gate0) * min(1, k / (iters * 0.7))
        X = s * src @ R.T + t
        d, i = dst_tree.query(X, distance_upper_bound=gate)
        ok = np.isfinite(d)
        if ok.sum() < 80:
            return R, t, s, None
        if trim < 1:
            th = np.quantile(d[ok], trim)
            ok &= d <= th
        a, b = src[ok], dst[i[ok]]
        ca, cb = a.mean(0), b.mean(0)
        H = (a - ca).T @ (b - cb)
        if planar:
            th = np.arctan2(H[0, 1] - H[1, 0], H[0, 0] + H[1, 1])
            Rn = rz(th)
        else:
            U, W, Vt = np.linalg.svd(H)
            Dg = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
            Rn = Vt.T @ Dg @ U.T
        if use_scale:
            s = (W * np.diag(Dg)).sum() / ((a - ca) ** 2).sum()
        R, t = Rn, cb - s * Rn @ ca
        if planar:
            t[2] = 0.0
    X = s * src @ R.T + t
    d, _ = dst_tree.query(X, distance_upper_bound=gate1 * 2)
    return R, t, s, d[np.isfinite(d)]


a0, t0 = best[1]
Rg, tg, _, dg = icp(q, tree, tree.data, rz(a0), np.r_[t0, 0.0], planar=True, gate0=0.02, gate1=0.008, trim=0.7)
print("global planar ICP yaw", np.degrees(np.arctan2(Rg[1, 0], Rg[0, 0])).round(2), "t", tg.round(4), "rms mm", round(float(np.sqrt((dg ** 2).mean())) * 1000, 2), "n", len(dg))
Qg = q @ Rg.T + tg  # scan in the model's foot frame, z preserved (floor)

GROUPS = {
    "head": ["jaw_soft"],
    "trunk": ["trunk_base"],
    "foot_l": ["ankle_left"], "foot_r": ["ankle_right"],
    "shin_l": ["leg"], "shin_r": ["leg_2"],
    "thigh_l": ["upper_leg_left"], "thigh_r": ["upper_leg_right"],
    "neck": ["neck"],
}
out = dict(scan=scan, pose=pose, global_rms_mm=float(np.sqrt((dg ** 2).mean()) * 1000))
out["parts"] = {}
for g, bl in GROUPS.items():
    idx = np.isin(lab, [names.index(b) for b in bl])
    P = mp[idx]
    tr = KD(P)
    # scan points that could belong to this part: within 25 mm of it and nearer to it than 8 mm beyond the rest
    other = KD(mp[~idx][::2])
    d1, _ = tr.query(Qg, distance_upper_bound=0.03)
    d2, _ = other.query(Qg, distance_upper_bound=0.03)
    sel = np.isfinite(d1) & (d1 <= d2 + 0.004)
    src = Qg[sel]
    if len(src) < 150:
        out["parts"][g] = {"n": int(len(src))}
        print(g, "too few", len(src))
        continue
    # fit scan part -> model part; the part's real pose = inverse of this applied to the model part
    R, t, s, d = icp(src, tr, P, np.eye(3), np.zeros(3), trim=0.8, gate0=0.02, gate1=0.006)
    Rs, ts, ss, ds = icp(src, tr, P, R, t, trim=0.8, use_scale=True, gate0=0.008, gate1=0.005, iters=25)
    c = P.mean(0)
    # real part location of a model point p: x = R^T (p - t)
    real_c = (c - t) @ R
    ang = Rot.from_matrix(R.T).as_rotvec(degrees=True)
    rec = dict(n=int(len(src)), inliers=None if d is None else int(len(d)), rms_mm=None if d is None else float(np.sqrt((d ** 2).mean()) * 1000), scale_scan_to_cad=float(ss), rotvec_deg=np.round(ang, 2).tolist(),
               centre_shift_mm=np.round((real_c - c) * 1000, 1).tolist(), R=R.tolist(), t=t.tolist(), centre=c.tolist())
    out["parts"][g] = rec
    print(f"{g:8s} n {rec['n']:6d} inl {rec['inliers']} rms {rec['rms_mm']:.2f} mm scale {ss:.4f}  real-minus-model centre mm {rec['centre_shift_mm']} rot deg {rec['rotvec_deg']}")

# camera and mouth points through the head's fitted rigid pose
H = out["parts"].get("head", {})
if "R" in H:
    R, t = np.array(H["R"]), np.array(H["t"])
    for nm, key in (("camera", "cam_kin_nobow"), ("mouth", "mouth_kin")):
        p = np.array(sites[key])
        r = (p - t) @ R
        out[nm] = dict(model=p.tolist(), scan=r.tolist())
        print(nm, "model (chain, no bow correction)", np.round(p * 1000, 1), "scan-implied", np.round(r * 1000, 1), "real-minus-model mm", np.round((r - p) * 1000, 1))
    print("chain camera with bow correction", np.round(np.array(sites["cam_kin"]) * 1000, 1))
# lowest scan point under the head
he = np.isin(lab, [names.index("jaw_soft")])
d1, _ = KD(mp[he]).query(Qg, distance_upper_bound=0.03)
print("head scan points z min (p1, p50 lowest)", np.percentile(Qg[np.isfinite(d1), 2], [0.5, 2]).round(4), " model head z min", mp[he, 2].min().round(4))
np.savez(f"{S}/fit_{scan}.npz", Qg=Qg, col=col)
json.dump(out, open(f"{S}/fit_{scan}.json", "w"), indent=1)

# overlay: side view (x,z), model gray, scan coloured
res = 0.4
A = np.vstack([Qg, mp])
lo, hi = A.min(0), A.max(0)
W, Hh = int((hi[0] - lo[0]) * 1000 / res) + 3, int((hi[2] - lo[2]) * 1000 / res) + 3
for nm, (u, v, flip) in {"xz": (0, 2, False), "yz": (1, 2, False)}.items():
    W = int((hi[u] - lo[u]) * 1000 / res) + 3
    im = np.full((Hh, W, 3), 255, np.uint8)
    i = ((mp[:, u] - lo[u]) * 1000 / res).astype(int)
    j = Hh - 1 - ((mp[:, v] - lo[v]) * 1000 / res).astype(int)
    im[j, i] = (185, 195, 235)
    i = ((Qg[:, u] - lo[u]) * 1000 / res).astype(int)
    j = Hh - 1 - ((Qg[:, v] - lo[v]) * 1000 / res).astype(int)
    im[j, i] = (200, 40, 30)
    Image.fromarray(im).save(f"{S}/overlay_{scan}_{nm}.png")
