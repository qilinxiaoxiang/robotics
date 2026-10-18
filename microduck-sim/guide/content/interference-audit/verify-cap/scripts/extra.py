"""Extra checks: screw sweeps during cap-on, per-pin shift needed, bundle_head route near the moved Pi."""
import json, sys, os, math
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(__file__))
from vc import *
S, prov = solids()
c10, s10 = np.cos(np.radians(10)), np.sin(np.radians(10))
A = np.array([c10, 0, -s10]); EY = np.array([0, 1.0, 0]); CT = np.array([s10, 0, c10])
S_BASE_TOP = 43.231; T_ODD = (123.679, 126.219); T_EVEN = (126.219, 128.759)
FRONT = [k for k in CAMERA_STACK if k in S]
def local_box(s_, y, t):
    return mf.Manifold.hull_points(np.array([si * A + yi * EY + ti * CT for si in s_ for yi in y for ti in t]))
def pin_box(pin, L):
    k = (pin + 1) // 2; y = (25.4 - 2.54 * k, 25.4 - 2.54 * (k - 1)); t = T_ODD if pin % 2 else T_EVEN
    return local_box((S_BASE_TOP, S_BASE_TOP + L), y, t)
def hits(P, dx, fx, tol=1e-3):
    Q = tr(P, [-dx, 0, 0]); H = mf.Manifold.hull(union([Q, tr(Q, [0, 0, 40.0])]))
    return {f: round(overlap(H, S[f]), 3) for f in fx if overlap(H, S[f]) > tol}
def bisect(pred, lo, hi, it=40):
    if pred(lo): return lo
    for _ in range(it):
        m = (lo + hi) / 2
        lo, hi = (lo, m) if pred(m) else (m, hi)
    return hi

DX = float(os.environ.get('DX', '4.6'))
out = {'DX': DX}
fixed = [k for k in FIXED if k in S]
ax = np.array([-0.984808, 0.0, 0.173648])
seats = {'E-pi-01 (-y lower)': [61.941, -29.0, 117.245], 'E-pi-02 (+y lower)': [61.941, 29.0, 117.245],
         'E-pi-03 (-y upper)': [65.935, -29.0, 139.895], 'E-pi-04 (+y upper)': [65.935, 29.0, 139.895]}
sw = {}
for name, c in seats.items():
    for label, d in [('V1.6', 0.0), ('candidate', DX)]:
        p0 = np.array(c) + [-d, 0, 0]
        for L in (6.0, 5.0, 4.0):
            cyl = to_mf(trimesh.creation.cylinder(radius=1.0, segment=[p0, p0 + L * ax], sections=24))
            H = mf.Manifold.hull(union([cyl, tr(cyl, [0, 0, 40])]))
            h = {k: round(overlap(H, S[k]), 3) for k in fixed if overlap(H, S[k]) > 1e-3}
            sw[f'{name} {label} M2x{L:.0f}'] = h
out['screwSweepHits'] = sw
# per used pin: shift needed for its own 14.25 mm housing column (touching) and the governing obstacle
per = {}
for p in USED_PINS:
    P = pin_box(p, 14.25)
    d0 = bisect(lambda d: not hits(P, d, FRONT), 0.0, 15.0)
    per[p] = {'touchShiftMm': round(d0, 3), 'blockers': hits(P, 0.0, FRONT), 'clearanceAtDXmm': round(DX - d0, 3)}
out['perPin'] = per
json.dump(out, open(HERE / f'extra-DX{DX}.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
