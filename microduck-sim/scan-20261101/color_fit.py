"""Colour-classed, two-way (scan->model and model->scan) rigid fit of the head and feet, multi-start. Sliding along a
smooth shell is what spoiled the first fit: the white/yellow border and the model->scan term pin it."""
import sys, json, os, numpy as np
from scipy.spatial import cKDTree as KD
from scipy.spatial.transform import Rotation as Rot


S = sys.argv[1]
GLOBAL = {"a": (-29.18, [-0.0031, 0.0035, 0.0]), "b": (-5.46, [0.0224, 0.005, 0.0])}


def rz(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])


def classes(C):
    c = C.astype(float) / 255
    mx, mn = c.max(1), c.min(1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    hue = np.zeros(len(c))
    r, g, b = c.T
    d = np.maximum(mx - mn, 1e-6)
    m = mx == r
    hue[m] = ((g - b)[m] / d[m]) % 6
    m = mx == g
    hue[m] = (b - r)[m] / d[m] + 2
    m = mx == b
    hue[m] = (r - g)[m] / d[m] + 4
    hue *= 60
    out = np.full(len(c), "x", dtype="U1")
    out[(sat < 0.28) & (mx > 0.55)] = "w"
    out[(sat > 0.45) & (hue > 40) & (hue < 68) & (mx > 0.45)] = "y"
    out[(sat > 0.5) & (hue >= 5) & (hue <= 38) & (mx > 0.45)] = "o"
    return out


def solve(a, b):
    ca, cb = a.mean(0), b.mean(0)
    U, W, Vt = np.linalg.svd((a - ca).T @ (b - cb))
    Dg = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ Dg @ U.T
    return R, cb - R @ ca


def fit(src, P, R0, t0, iters=40):
    """src: {class: scan pts}, P: {class: model pts}. Finds model->real pose T: x_real = R p + t."""
    R, t = R0, t0
    trees_m = {k: KD(v) for k, v in P.items()}
    trees_s = {k: KD(v) for k, v in src.items()}
    for it in range(iters):
        gate = 0.025 + (0.005 - 0.025) * min(1, it / (iters * 0.7))
        A, B = [], []
        for k in P:
            X = P[k] @ R.T + t  # model in real frame
            d, i = trees_s[k].query(X, distance_upper_bound=gate)  # model->scan
            ok = np.isfinite(d)
            if ok.sum() > 30:
                ok &= d <= np.quantile(d[ok], 0.8)
                A.append(P[k][ok]); B.append(src[k][i[ok]])
            pinv = (src[k] - t) @ R
            d, i = trees_m[k].query(pinv, distance_upper_bound=gate)  # scan->model
            ok = np.isfinite(d)
            if ok.sum() > 30:
                ok &= d <= np.quantile(d[ok], 0.8)
                A.append(P[k][i[ok]]); B.append(src[k][ok])
        if not A:
            return None
        R, t = solve(np.vstack(A), np.vstack(B))
    cost, cov, n = 0.0, 0.0, 0
    for k in P:
        X = P[k] @ R.T + t
        d, _ = trees_s[k].query(X)
        d = np.minimum(d, 0.012)
        cost += (d ** 2).sum(); cov += (d < 0.004).sum(); n += len(d)
        d, _ = trees_m[k].query((src[k] - t) @ R)
        d = np.minimum(d, 0.012)
        cost += (d ** 2).sum(); n += len(d)
    return R, t, float(np.sqrt(cost / n) * 1000), cov / max(1, sum(len(v) for v in P.values()))


rng = np.random.default_rng(3)
report = {}
for scan, pose in (("a", "stand"), ("b", "bend")):
    D = np.load(f"{S}/{scan}_robot.npz")
    L, C = D["L"], D["C"]
    yaw, tg = GLOBAL[scan]
    Q = L @ rz(yaw).T + np.array(tg)
    cls = classes(C)
    M = np.load(f"{S}/model_{pose}.npz", allow_pickle=True)
    mp, lab, names, gcl = M["pts"], M["lab"], list(M["names"]), M["gcolor"]
    site = json.load(open(f"{S}/model_sites2.json"))[pose]
    print(f"\n===== {scan} {pose}; class counts scan", {k: int((cls == k).sum()) for k in "wyo"})
    report[pose] = {}
    for part, body, want in (("head", "jaw_soft", {"white": "w", "yellow": "y"}), ("foot_l", "ankle_left", {"yellow": "y", "orange": "o"}), ("foot_r", "ankle_right", {"yellow": "y", "orange": "o"})):
        idx = lab == names.index(body)
        Pm = {want[k]: mp[idx & (gcl == k)][::2] for k in want}
        c = np.vstack(list(Pm.values())).mean(0)
        src = {}
        for k in Pm:
            # scan points of this colour within 45 mm of the posed part, floor excluded except for colour
            d, _ = KD(Pm[k]).query(Q, distance_upper_bound=0.045)
            m = np.isfinite(d) & (cls == k) & (Q[:, 2] > 0.001)
            src[k] = Q[m]
        results = []
        for s in range(30):
            ang = rng.normal(0, np.radians(6), 3) if s else np.zeros(3)
            R0 = Rot.from_rotvec(ang).as_matrix()
            tt = rng.uniform(-0.025, 0.025, 3) if s else np.zeros(3)
            t0 = c - R0 @ c + tt
            f = fit(src, Pm, R0, t0)
            if f:
                results.append(f)
        results.sort(key=lambda f: f[2])
        best = results[0]
        Rb, tb, cost, cov = best
        close = [f for f in results if f[2] < cost * 1.1]
        def T(f, p):
            return f[0] @ p + f[1]
        rv = Rot.from_matrix(Rb).as_rotvec(degrees=True)
        print(f"{part:7s} scan {[(k, len(v)) for k, v in src.items()]} cost {cost:.2f} mm cov {cov:.2f} near-best {len(close)}/{len(results)} | centre shift mm {np.round((T(best, c) - c) * 1000, 1)} | rot deg {np.round(rv, 1)}")
        costs = [round(f[2], 2) for f in results[:8]]
        print("        costs", costs)
        report[pose][part] = dict(R=Rb.tolist(), t=tb.tolist(), cost=cost, cov=float(cov), centre_shift_mm=((T(best, c) - c) * 1000).tolist(), rot_deg=rv.tolist())
        if part == "head":
            cam = np.array(site["cam_gain1"])
            r = T(best, cam)
            spread = np.array([T(f, cam) for f in close]) * 1000
            print("  camera: chain gain1", np.round(cam * 1000, 1), "scan", np.round(r * 1000, 1), "real-minus-chain", np.round((r - cam) * 1000, 1), "spread among near-best", np.round(spread.std(0), 1))
            print("  chain gain .92 no bow", np.round(np.array(site["cam_kin_nobow"]) * 1000, 1), " with bow", np.round(np.array(site["cam_kin"]) * 1000, 1))
            ax = np.array(site["axis_gain1"])
            print("  axis chain", np.round(ax, 3), "scan", np.round(Rb @ ax, 3), "angle deg", round(float(np.degrees(np.arccos(np.clip(ax @ (Rb @ ax), -1, 1)))), 1))
            # direct floor gap of the real head, from yellow and white class points, without the fit
            X = np.vstack(list(src.values()))
            H = np.vstack([Pm[k] @ Rb.T + tb for k in Pm])
            print("  head lowest: model posed z", np.round(np.vstack(list(Pm.values()))[:, 2].min() * 1000, 1), " fitted model z", np.round(H[:, 2].min() * 1000, 1), " scan class pts z p0.2/p1", np.round(np.percentile(X[:, 2], [0.2, 1]) * 1000, 1))
            report[pose]["camera_real_minus_chain_mm"] = ((r - cam) * 1000).tolist()
            np.savez(f"{S}/head_{scan}.npz", Q=Q, cls=cls)
            # overlay after the fit
            from PIL import Image
            hm = np.vstack([Pm[k] @ Rb.T + tb for k in Pm])
            scanp = np.vstack(list(src.values()))
            res = 0.3
            lo = np.vstack([hm, scanp]).min(0); hi = np.vstack([hm, scanp]).max(0)
            W, Hh = int((hi[0] - lo[0]) * 1000 / res) + 3, int((hi[2] - lo[2]) * 1000 / res) + 3
            im = np.full((Hh, W, 3), 255, np.uint8)
            for pts, colr in ((hm, (170, 185, 240)), (scanp, (210, 40, 30))):
                im[Hh - 1 - ((pts[:, 2] - lo[2]) * 1000 / res).astype(int), ((pts[:, 0] - lo[0]) * 1000 / res).astype(int)] = colr
            Image.fromarray(im).save(f"{S}/head_overlay_{scan}.png")
    # sole size from colour on the floor plane (scale check): yellow within 3-14 mm height
    for part in ("foot_l", "foot_r"):
        Rf = np.array(report[pose][part]["R"]); tf = np.array(report[pose][part]["t"])
        body = "ankle_left" if part == "foot_l" else "ankle_right"
        idx = (lab == names.index(body)) & (gcl == "yellow")
        Pf = mp[idx]
        X = (Q[cls == "y"] - tf) @ Rf  # scan in the model part's frame
        d, _ = KD(Pf).query(X, distance_upper_bound=0.01)
        X = X[np.isfinite(d)]
        cen = Pf[:, :2].mean(0)
        w, v = np.linalg.eigh(np.cov((Pf[:, :2] - cen).T))
        a = v[:, 1]; b = v[:, 0]
        ext = lambda A, u: np.ptp(np.percentile((A[:, :2] - cen) @ u, [0.5, 99.5]))
        print(f"  {part} sole: CAD length {ext(Pf, a) * 1000:.1f} width {ext(Pf, b) * 1000:.1f} | scan length {ext(X, a) * 1000:.1f} width {ext(X, b) * 1000:.1f} mm (n {len(X)})")
    print("   foot-frame sole min z model vs real-floor: scan yellow z p0.5", np.round(np.percentile(Q[cls == "y", 2], 0.5) * 1000, 1))
json.dump(report, open(f"{S}/color_fit.json", "w"), indent=1)
