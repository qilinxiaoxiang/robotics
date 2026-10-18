"""Free vertical height map inside the head cap (amplifier excluded): floor = top of the parts below z 131,
ceiling = lowest cap / part surface above z 131. Jaw parts are taken as the envelope over their open sweep."""
import numpy as np, trimesh
from scene import load, rot_y, SCRATCH, JAW_MOVING
M, src, nb = load()
pts = []
for k, m in M.items():
    if k == 'amplifier': continue
    n = int(min(400000, max(5000, m.area / 0.04)))
    p, _ = trimesh.sample.sample_surface(m, n, seed=1); p = np.vstack([p, m.vertices])
    if k in JAW_MOVING:
        allp = [p]
        for d in range(-15, 61, 5):
            T = rot_y(d); allp.append(p @ T[:3, :3].T + T[:3, 3])
        p = np.vstack(allp)
    pts.append(p)
P = np.vstack(pts)
xs = np.arange(-20, 57, 2.0); ys = np.arange(-36, 41, 2.0)
ix = np.floor((P[:, 0] + 21) / 2).astype(int); iy = np.floor((P[:, 1] + 37) / 2).astype(int)
H = np.full((len(xs), len(ys)), np.nan); F = np.full_like(H, np.nan); C = np.full_like(H, np.nan)
for i, x in enumerate(xs):
    for j, y in enumerate(ys):
        s = P[(abs(P[:, 0] - x) < 1) & (abs(P[:, 1] - y) < 1)][:, 2]
        lo = s[s <= 131]; hi = s[s > 131]
        F[i, j] = lo.max() if len(lo) else np.nan; C[i, j] = hi.min() if len(hi) else np.nan
H = C - F
np.savez(SCRATCH / 'heightmap.npz', xs=xs, ys=ys, F=F, C=C)
print('rows x, cols y:', ' '.join('%4.0f' % y for y in ys))
for nm, A in (('ceiling z', C), ('floor z', F), ('free height', H)):
    print(nm)
    for i, x in enumerate(xs):
        print('x=%4.0f ' % x + ' '.join('  - ' if np.isnan(a) else '%4.0f' % a for a in A[i]))
