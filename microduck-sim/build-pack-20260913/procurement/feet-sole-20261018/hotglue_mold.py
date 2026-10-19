"""Hot-glue sole mold for the printed MicroDuck foot: the foot is pressed into a cavity that is its own bottom offset
by T mm, so the glue sets as a coat of even thickness with a smooth outer face.

Geometry, all in the foot STL frame (flat bottom at z = 0, foot above):
  cavity    where the foot bottom is below H_CAST: floor = the foot bottom offset outward by T (lower envelope of
            spheres of radius T on the surface), so the coat is T thick along the normal, on the flat and on the curve
  seal      outside the cavity the mold top is the plane z = H_CAST; the foot touches it along its H_CAST contour,
            which closes the cavity and gives the coat a clean edge
  pins      three 1.6 mm pins in the flat region, top at z = 0: the foot rests on them, so the coat is exactly T deep
  vents     grooves from the cavity edge out to a moat, so excess glue leaves instead of lifting the foot
  tabs      four locating tabs outside the foot outline (C_TAB clearance) up to z = H_TAB: the foot drops in centred
Coat edge height H_CAST = 3 mm covers the 1.6 mm reached by sim floor contacts (sole_contact_sim.py).

  ~/.venvs/microduck-dyn/bin/python hotglue_mold.py      -> hotglue-mold-left.stl, hotglue-mold-right.stl, check JSON
"""
import json
import struct
from pathlib import Path

import numpy as np
from scipy import ndimage

HERE = Path(__file__).resolve().parent
PARTS = HERE / ".." / ".." / "assembly" / "print-parts"
FEET = {"left": PARTS / "community-44.stl", "right": PARTS / "community-46.stl"}

T = 1.0          # mm coat thickness (normal)
H_CAST = 3.0     # mm coat edge above the flat
H_TAB = 12.0     # mm top of the locating tabs (foot frame); the foot is widest from z = 7.9 up
C_TAB = 0.4      # mm lateral clearance foot outline -> tab
TAB_W = 10.0     # mm tab length along the side
TAB_D = 3.0      # mm tab thickness
MOAT = (0.6, 3.4)  # mm moat band, distance outside the foot outline
MOAT_DEPTH = 2.0
VENT_W, VENT_DEPTH, N_VENTS = 1.6, 1.0, 8
PIN_R = 0.8
BASE = 3.0       # mm of solid under the deepest cavity point
MARGIN = 3.0     # mm wall outside the tabs/moat
STEP = 0.2       # mm grid


def load_tris(path):
    b = path.read_bytes()
    n = struct.unpack("<I", b[80:84])[0]
    assert 84 + 50 * n == len(b), "binary STL expected"
    return np.frombuffer(b[84:], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("x", "<u2")]), count=n)["v"].reshape(-1, 3, 3).astype(float)


def height_map(tris, xs, ys):
    """Lowest z of the foot over each grid point (nan where the foot does not cover it)."""
    low = np.full((len(xs), len(ys)), np.nan)
    for tri in tris:
        a, b_, c = tri
        ix = np.where((xs >= tri[:, 0].min()) & (xs <= tri[:, 0].max()))[0]
        iy = np.where((ys >= tri[:, 1].min()) & (ys <= tri[:, 1].max()))[0]
        if not len(ix) or not len(iy):
            continue
        X, Y = np.meshgrid(xs[ix], ys[iy], indexing="ij")
        v0 = b_[:2] - a[:2]; v1 = c[:2] - a[:2]; d = v0[0] * v1[1] - v0[1] * v1[0]
        if abs(d) < 1e-9:
            continue
        px = X - a[0]; py = Y - a[1]
        u = (px * v1[1] - py * v1[0]) / d; w = (v0[0] * py - v0[1] * px) / d
        ins = (u >= -1e-6) & (w >= -1e-6) & (u + w <= 1 + 1e-6)
        z = a[2] + u * (b_[2] - a[2]) + w * (c[2] - a[2])
        sub = low[np.ix_(ix, iy)]; upd = ins & (np.isnan(sub) | (z < sub)); sub[upd] = z[upd]
        low[np.ix_(ix, iy)] = sub
    return low


def offset_down(low, r):
    """Lower envelope of spheres of radius r centred on the height field (true normal offset)."""
    z = np.where(np.isnan(low), np.inf, low)
    out = np.full(z.shape, np.inf)
    k = int(np.ceil(r / STEP))
    for di in range(-k, k + 1):
        for dj in range(-k, k + 1):
            d2 = (di * STEP) ** 2 + (dj * STEP) ** 2
            if d2 > r * r:
                continue
            sh = np.full(z.shape, np.inf)
            si = slice(max(di, 0), z.shape[0] + min(di, 0)); ti = slice(max(-di, 0), z.shape[0] + min(-di, 0))
            sj = slice(max(dj, 0), z.shape[1] + min(dj, 0)); tj = slice(max(-dj, 0), z.shape[1] + min(-dj, 0))
            sh[ti, tj] = z[si, sj]
            out = np.minimum(out, sh - np.sqrt(r * r - d2))
    return out


def write_heightfield_stl(path, xs, ys, S, zbot):
    nx, ny = S.shape
    V = np.zeros((nx, ny, 3)); V[..., 0] = xs[:, None]; V[..., 1] = ys[None, :]; V[..., 2] = S
    tris = []
    a = V[:-1, :-1]; b = V[1:, :-1]; c = V[1:, 1:]; d = V[:-1, 1:]
    tris.append(np.stack([a, b, c], -2).reshape(-1, 3, 3)); tris.append(np.stack([a, c, d], -2).reshape(-1, 3, 3))
    # perimeter, counter-clockwise seen from above
    per = [V[i, 0] for i in range(nx)] + [V[nx - 1, j] for j in range(1, ny)] + \
          [V[i, ny - 1] for i in range(nx - 2, -1, -1)] + [V[0, j] for j in range(ny - 2, 0, -1)]
    per = np.array(per); nper = len(per)
    bot = per.copy(); bot[:, 2] = zbot
    centre = np.array([xs.mean(), ys.mean(), zbot])
    side, bottom = [], []
    for k in range(nper):
        p0, p1 = per[k], per[(k + 1) % nper]; q0, q1 = bot[k], bot[(k + 1) % nper]
        side += [[p0, q0, q1], [p0, q1, p1]]
        bottom.append([centre, q1, q0])
    allt = np.concatenate(tris + [np.array(side), np.array(bottom)])
    nrm = np.cross(allt[:, 1] - allt[:, 0], allt[:, 2] - allt[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    rec = np.zeros(len(allt), dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("x", "<u2")]))
    rec["n"] = nrm; rec["v"] = allt.reshape(-1, 9)
    with open(path, "wb") as f:
        f.write(b"MicroDuck hot-glue sole mold".ljust(80, b" ")); f.write(struct.pack("<I", len(allt))); f.write(rec.tobytes())
    return len(allt)


def build(side):
    tris = load_tris(FEET[side])
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    pad = C_TAB + max(TAB_D, MOAT[1]) + MARGIN
    xs = np.arange(lo[0] - pad, hi[0] + pad + 1e-9, STEP); ys = np.arange(lo[1] - pad, hi[1] + pad + 1e-9, STEP)
    low = height_map(tris, xs, ys)
    foot = ~np.isnan(low)
    # distance outside the foot outline (mm), 0 inside
    dist_out = ndimage.distance_transform_edt(~foot) * STEP
    zoff = offset_down(low, T)
    cavity = foot & (low < H_CAST)
    cavity = ndimage.binary_fill_holes(cavity)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    S = np.full(low.shape, H_CAST)
    S[cavity] = zoff[cavity]
    # flat region and its centre
    flat = foot & (low < 0.1)
    fx, fy = X[flat], Y[flat]
    cx, cy = (fx.min() + fx.max()) / 2, (fy.min() + fy.max()) / 2
    hx, hy = (fx.max() - fx.min()) / 2, (fy.max() - fy.min()) / 2
    # pins: triangle inside the flat, pulled in 35 % from the flat's edges
    # each pin snaps to the nearest grid point whose whole pin disc lies on the flat
    ok = ndimage.binary_erosion(flat, iterations=int(np.ceil((PIN_R + 0.4) / STEP)))
    targets = [(cx - 0.6 * hx, cy - 0.5 * hy), (cx - 0.6 * hx, cy + 0.5 * hy), (cx + 0.65 * hx, cy)]
    pins = []
    for tx, ty in targets:
        d2 = np.where(ok, (X - tx) ** 2 + (Y - ty) ** 2, np.inf)
        i, j = np.unravel_index(np.argmin(d2), d2.shape)
        px, py = X[i, j], Y[i, j]
        m = (X - px) ** 2 + (Y - py) ** 2 <= PIN_R ** 2
        assert flat[m].all(), (side, px, py)
        S[m] = low[m].min()  # pin top touches the lowest point of the flat under it
        pins.append((px, py))
    # moat outside the outline, interrupted at the tabs
    tabs = np.zeros_like(foot)
    oc = (dist_out >= C_TAB) & (dist_out <= C_TAB + TAB_D)
    tabs |= oc & (np.abs(Y - cy) <= TAB_W / 2)            # front and back tabs
    tabs |= oc & (np.abs(X - cx) <= TAB_W / 2)            # side tabs
    moat = (dist_out >= MOAT[0]) & (dist_out <= MOAT[1]) & ~tabs
    S[moat] = H_CAST - MOAT_DEPTH
    S[tabs] = H_TAB
    # vents: radial grooves from the cavity edge to the moat, between the tabs
    ang = np.arctan2(Y - cy, X - cx)
    vent = np.zeros_like(foot)
    for k in range(N_VENTS):
        a0 = np.pi / N_VENTS + 2 * np.pi * k / N_VENTS  # midway between the four tab axes and the diagonals
        dirx, diry = np.cos(a0), np.sin(a0)
        along = (X - cx) * dirx + (Y - cy) * diry
        across = np.abs(-(X - cx) * diry + (Y - cy) * dirx)
        vent |= (across <= VENT_W / 2) & (along > 0) & ~cavity & (dist_out <= MOAT[0] + 0.5) & ~tabs
    S[vent] = np.minimum(S[vent], H_CAST - VENT_DEPTH)
    zbot = min(S.min(), -T) - BASE

    # check the seated foot against the mold: vertical gap foot - mold over the foot's projection
    gap = np.where(foot, low - S, np.inf)
    inter = foot & (gap < -1e-6)
    nrm_gap = []
    # coat thickness along the normal: distance from cavity floor points to the foot surface (sampled)
    pts_f = np.stack([X[foot], Y[foot], low[foot]], 1)
    from scipy.spatial import cKDTree
    tree = cKDTree(pts_f)
    pinm = np.zeros_like(foot)
    for px, py in pins:
        pinm |= (X - px) ** 2 + (Y - py) ** 2 <= PIN_R ** 2
    cav_pts = np.stack([X[cavity & ~pinm], Y[cavity & ~pinm], S[cavity & ~pinm]], 1)
    dn, _ = tree.query(cav_pts)
    check = dict(
        side=side, stl=str(FEET[side].name), coat_T_mm=T, coat_edge_mm=H_CAST,
        interference_cells=int(inter.sum()),
        min_vertical_gap_mm=float(gap[foot].min()),
        coat_normal_thickness_mm=dict(p1=float(np.percentile(dn, 1)), p50=float(np.percentile(dn, 50)), p99=float(np.percentile(dn, 99))),
        cavity_area_mm2=float(cavity.sum() * STEP * STEP),
        coat_volume_cm3=float(np.sum(np.where(cavity & ~pinm, low - S, 0)) * STEP * STEP / 1000),
        flat_mm=[float(2 * hx), float(2 * hy)], flat_unevenness_mm=float(np.ptp(low[flat])), pins=[[round(p, 2) for p in q] for q in pins],
        tab_clearance_mm=float(dist_out[tabs].min()),
        block_mm=[float(xs[-1] - xs[0]), float(ys[-1] - ys[0]), float(H_TAB - zbot)],
    )
    out = HERE / f"hotglue-mold-{side}.stl"
    check["triangles"] = write_heightfield_stl(out, xs, ys, S, zbot)
    np.savez_compressed(HERE / f"hotglue-mold-{side}-maps.npz", xs=xs, ys=ys, S=S, low=low)
    return check


if __name__ == "__main__":
    res = [build(s) for s in ("left", "right")]
    (HERE / "hotglue-mold-check.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
