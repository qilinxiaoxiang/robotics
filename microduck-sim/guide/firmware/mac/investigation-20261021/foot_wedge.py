"""Old (community-44/46, press fit, printed V1.8) vs new (V1.22 slip-fit) foot: is the foot a wedge?  Pure mesh geometry.
In the foot print frame (flat bottom at z = 0, +x toe, +y across): for each foot, (a) the sole plane fit over the bottom
band, (b) the top-surface height z_top(y) along the inner and outer edges of the socket region (x in [-18, 10] mm), (c) the
sole's lowest 4 mm band left/right extent, (d) bounding boxes. Also the guide's source foot if it can be found."""
import json, os, sys
import numpy as np, trimesh
HERE = os.path.dirname(os.path.abspath(__file__))
SIM = "/Users/xiangzheng/code/robotics/microduck-sim"
P = SIM + "/build-pack-20260913/assembly/print-parts/"
FS = SIM + "/guide/print/foot-slipfit-20261019/"
files = {"old_left": P + "community-44.stl", "old_right": P + "community-46.stl",
         "new_left": FS + "foot-left-slipfit.stl", "new_right": FS + "foot-right-slipfit.stl"}
out = {}
for k, fn in files.items():
    if not os.path.exists(fn):
        out[k] = "missing " + fn; continue
    t = trimesh.load(fn, force="mesh")
    lo, hi = t.bounds
    v = t.vertices
    bottom = v[v[:, 2] < 0.3]
    # sole plane fit
    c = bottom.mean(0); n = np.linalg.svd(bottom - c)[2][-1]; n = n if n[2] > 0 else -n
    # top height along y at the socket region, sampled by ray casting from above
    xs = np.linspace(-18, 10, 15)
    ys = np.linspace(lo[1] + 1.0, hi[1] - 1.0, 13)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    origins = np.stack([X.ravel(), Y.ravel(), np.full(X.size, hi[2] + 5)], 1)
    dirs = np.tile([0, 0, -1.0], (len(origins), 1))
    loc, idx, _ = t.ray.intersects_location(origins, dirs, multiple_hits=False)
    ztop = np.full(len(origins), np.nan); ztop[idx] = loc[:, 2]
    ztop = ztop.reshape(X.shape)
    prof = {round(float(y), 1): round(float(np.nanmedian(ztop[:, j])), 2) for j, y in enumerate(ys)}
    # wall height at the extreme y edges (outer walls), as the eye sees "thickness" from the side
    yin_i, yout_i = 0, len(ys) - 1
    out[k] = dict(file=fn, bounds_mm=np.round(t.bounds, 2).tolist(), volume_mm3=round(float(t.volume), 1),
                  sole_plane_normal=np.round(n, 4).tolist(), sole_tilt_about_x_deg=round(float(np.degrees(np.arctan2(n[1], n[2]))), 2),
                  sole_tilt_about_y_deg=round(float(np.degrees(np.arctan2(n[0], n[2]))), 2),
                  top_height_by_y_mm=prof, bottom4mm_y_extent=np.round([v[v[:, 2] < 4][:, 1].min(), v[v[:, 2] < 4][:, 1].max()], 2).tolist(),
                  y_sign_note="y<0 and y>0 edges; which is inner depends on the side: left foot inner = -y? see foot_roll_static.json")
# old vs new difference field (new minus old) over the same grid
for side in ("left", "right"):
    a, b = out.get("old_" + side), out.get("new_" + side)
    if isinstance(a, dict) and isinstance(b, dict):
        out["new_minus_old_top_mm_" + side] = {y: round(b["top_height_by_y_mm"][y] - a["top_height_by_y_mm"][y], 2) for y in a["top_height_by_y_mm"]}
json.dump(out, open(os.path.join(HERE, "foot_wedge.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
