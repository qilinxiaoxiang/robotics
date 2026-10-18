"""Vertical cap descent of the Pi group and GPIO connector variants: swept overlaps and the Pi shift each variant needs.

Every moving piece here is convex (boxes, the Pi PCB hull), so the swept solid along the straight approach
[0,0,40] is exactly hull(piece, piece + approach). Fixed parts are the full-resolution head solids.
"""
import json, sys
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
from vc import *

S, prov = solids()
APPROACH = np.array([0, 0, 40.0])
c10, s10 = np.cos(np.radians(10)), np.sin(np.radians(10))
A = np.array([c10, 0, -s10]); EY = np.array([0, 1.0, 0]); CT = np.array([s10, 0, c10])  # pin axis, row, column directions
S_BASE_TOP = 43.231                     # header plastic top along the pin axis (measured, inspect1.json)
T_ODD = (123.679, 126.219); T_EVEN = (126.219, 128.759)

def col_y(k):  # pin pair k = 1..20 (pins 2k-1, 2k)
    return (25.4 - 2.54 * k, 25.4 - 2.54 * (k - 1))

def pin_box(pin, L):
    k = (pin + 1) // 2; y = col_y(k); t = T_ODD if pin % 2 else T_EVEN
    return local_box((S_BASE_TOP, S_BASE_TOP + L), y, t)

def local_box(s, y, t):
    pts = np.array([si * A + yi * EY + ti * CT for si in s for yi in y for ti in t])
    return mf.Manifold.hull_points(pts)

def block_2x20(L, wall=0.0):
    return local_box((S_BASE_TOP, S_BASE_TOP + L), (-25.4 - wall, 25.4 + wall), (T_ODD[0] - wall, T_EVEN[1] + wall))

FRONT = [k for k in CAMERA_STACK if k in S]
REAR = [k for k in FIXED if k in S and k not in FRONT]
pi_keys = sorted(k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k))
PI_GROUP = {k: mf.Manifold.hull(S[k]) for k in pi_keys}   # PCB hull is conservative (fills corner notches)

def swept(P, dx):
    Q = tr(P, [-dx, 0, 0])
    return Q, mf.Manifold.hull(union([Q, tr(Q, APPROACH)]))

def hits(P, dx, fixed, tol=1e-3):
    Q, H = swept(P, dx)
    out = {}
    for f in fixed:
        v = overlap(H, S[f])
        if v > tol:
            out[f] = round(v, 3)
    return out

def bisect(pred, lo, hi, it=40):
    """Smallest x in [lo, hi] with pred(x) True, assuming monotone."""
    if pred(lo):
        return lo
    if not pred(hi):
        return None
    for _ in range(it):
        m = (lo + hi) / 2
        lo, hi = (lo, m) if pred(m) else (m, hi)
    return hi

def need_front(pieces):
    return bisect(lambda d: all(not hits(P, d, FRONT) for P in pieces), 0.0, 15.0)

def max_rear(pieces):
    ok = lambda d: all(not hits(P, d, REAR) for P in pieces)
    r = bisect(lambda d: not ok(d), 0.0, 15.0)
    return r

out = {'provenance': prov, 'approach': APPROACH.tolist(), 'frontObstacles': FRONT, 'rearObstacles': REAR, 'piGroup': pi_keys}

# 0. Today: guide envelopes as drawn, Pi group, at dx = 0
guide_env = {p: S[f'head_pi_gpio_pin_{p:02d}_receiving'] for p in USED_PINS}
out['today'] = {'envelopes': {p: hits(M, 0, FRONT + REAR) for p, M in guide_env.items()},
                'piGroup': {k: hits(P, 0, FRONT + REAR) for k, P in PI_GROUP.items() if hits(P, 0, FRONT + REAR)}}
# per-column screen of all 40 positions with the guide length 14.25
out['allPositionsL14_25'] = {p: hits(pin_box(p, 14.25), 0, FRONT) for p in range(1, 41)}
# check that pin_box reproduces the guide envelope
out['pinBoxVsGuideEnvelopeXorMm3'] = {p: round((pin_box(p, 14.25) - guide_env[p]).volume() + (guide_env[p] - pin_box(p, 14.25)).volume(), 4) for p in USED_PINS}

# 1. Required backward shift (touching, dx0) for connector forward extent L from the header plastic top
Ls = [5.96, 7.0, 8.5, 9.5, 10.5, 11.5, 12.5, 14.0, 14.25, 15.25, 16.25]
req = {}
for L in Ls:
    cols = [pin_box(p, L) for p in USED_PINS]
    req[str(L)] = {'usedColumns': need_front(cols), 'full2x20Block': need_front([block_2x20(L)])}
out['requiredShiftTouchingMm'] = req
# 2. Rear limit of the Pi group alone (PCB, header, tails, components), moving straight back
out['piGroupMaxShiftBeforeRearContactMm'] = max_rear(list(PI_GROUP.values()))
first = {}
d = out['piGroupMaxShiftBeforeRearContactMm']
if d is not None:
    for k, P in PI_GROUP.items():
        h = hits(P, d + 0.05, REAR)
        if h:
            first[k] = h
out['piGroupFirstRearContact'] = first
# 3. Pi group at the audit shift 4.6 and at a few others: front and rear hits
for dx in (4.1, 4.6, 5.0, 5.5, 6.0, 6.6):
    out[f'piGroupHits_dx{dx}'] = {k: hits(P, dx, FRONT + REAR) for k, P in PI_GROUP.items() if hits(P, dx, FRONT + REAR)}
json.dump(out, open(HERE / 'study.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ('provenance',)}, indent=1))
