"""Can a cap-on path other than straight down help? Translation-only check, per height.

For a cap version (Pi shift dx; V1.6 cap for dx 0, V1.7 cap for dx 4.6) and each height h above the seated pose
(0..40 mm, 1 mm steps):
  allowedRear(h) = largest rearward offset u (populated cap moved by [-u, 0, h]) at which the cap, speaker,
                   amplifier and Pi group (no connectors) add no overlap with the fixed head parts beyond their
                   seated-pose overlap (excess <= 0.05 mm^3); bisection on u in [0, 10] at 0.02 mm, after checking
                   that every u in 0..u passes on a 0.5 mm scan.
  required(h)    = smallest rearward offset u at which the connector set is clear, static at [-u, 0, h]:
                   'sleeves-touch'  every used-pin sleeve of length L has zero overlap,
                   'sleeves-2mm'    every sleeve >= 2 mm from the fixed parts,
                   'wires-1mm'      sleeves >= 2 mm and each sleeve's nominal wire (d 1.4, inner radius 1.4) >= 1 mm;
                                    upper-row wires hairpin up, lower-row wires bend 90 deg towards -y.
A height where required > allowed blocks every path built from horizontal and vertical moves.
Rows follow the real Pi numbering (even pins in the row along the PCB edge; see ../inspect-geometry.json).
Writes ../path-check-dx<dx>-L<L>.json.  Usage: path_check.py <dx> <L>
"""
import json, sys, os, time, resource
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

T0 = time.time()
def prog(msg):
    print(f'[{time.time()-T0:7.1f}s {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:5.0f}MiB] {msg}', flush=True)

dx = float(sys.argv[1]); L = float(sys.argv[2])
cap = load_cap(CAP_V16, CAP_V16_SHA) if dx == 0.0 else load_cap(CAP_V17, CAP_V17_SHA)
S, prov = solids(None)
FX = [k for k in FIXED if k in S]
pi_keys = sorted(k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k))
carried = union([cap] + [S[k] for k in SPEAKER + ['amplifier'] if k in S] + [tr(S[k], [-dx, 0, 0]) for k in pi_keys])
F = union([S[k] for k in FX])
base = overlap(carried, F)
prog(f'carried built, seated overlap {base:.3f}')

def excess(u, h):
    return overlap(tr(carried, [-u, 0, h]), F) - base

rigid, wires = [], []
for pin in USED_PINS:
    row = row_t(pin, physical=True); y0, y1 = col_y(pin)
    rigid.append(local_hull((S_BASE_TOP, S_BASE_TOP + L), (y0, y1), row, d=[-dx, 0, 0]))
    yc = 0.5 * (y0 + y1); tc = 0.5 * (row[0] + row[1]); rho = 1.4 + 0.7
    c0 = P(S_BASE_TOP + L, yc, tc) + np.array([-dx, 0, 0])
    if row == T_HIGH:
        th = np.linspace(0, math.pi, 10); centre = c0 + rho * CT
        pts = [centre - rho * CT * math.cos(t_) + rho * A * math.sin(t_) for t_ in th]
    else:
        th = np.linspace(0, math.pi / 2, 6); centre = c0 - rho * EY
        pts = [centre + rho * EY * math.cos(t_) + rho * A * math.sin(t_) for t_ in th]
        pts.append(pts[-1] - 3.0 * EY)
    wires += [capsule(p, q, 0.7) for p, q in zip(pts[:-1], pts[1:])]
R = union(rigid); W = union(wires)

def ok(u, h, mode):
    d = [-u, 0, h]
    Rm = tr(R, d)
    need_r = 1e-6 if mode == 'sleeves-touch' else 2.0
    for k in FX:
        if gap(Rm, S[k], need_r) < need_r:
            return False
    if mode == 'wires-1mm':
        Wm = tr(W, d)
        for k in FX:
            if gap(Wm, S[k], 1.0) < 1.0:
                return False
    return True

def smallest(pred, hi=10.0, step=0.5, tol=0.02):
    u = 0.0
    while u <= hi:
        if pred(u):
            a, b = max(0.0, u - step), u
            if a == b:
                return 0.0
            while b - a > tol:
                m = 0.5 * (a + b)
                a, b = (a, m) if pred(m) else (m, b)
            return b
        u += step
    return None

def largest(pred, hi=10.0, step=0.5, tol=0.02):
    if not pred(0.0):
        return None
    u = 0.0
    while u + step <= hi and pred(u + step):
        u += step
    if u + step > hi:
        return u
    a, b = u, u + step
    while b - a > tol:
        m = 0.5 * (a + b)
        a, b = (m, b) if pred(m) else (a, m)
    return a

modes = ['sleeves-touch', 'sleeves-2mm', 'wires-1mm']
rows = []
for h in range(0, 41):
    a = largest(lambda u: excess(u, h) <= 0.05)
    rec = {'h': h, 'allowedRearMm': None if a is None else round(a, 2)}
    for m in modes:
        r = smallest(lambda u: ok(u, h, m))
        rec[m] = None if r is None else round(r, 2)
    rows.append(rec)
    prog(json.dumps(rec))
verdict = {}
for m in modes:
    blocked = [r['h'] for r in rows if r[m] is None or r['allowedRearMm'] is None or r[m] > r['allowedRearMm'] + 1e-9]
    verdict[m] = {'blockedHeights': blocked, 'seatedPoseClear': rows[0][m] == 0.0, 'translationPathExists': not blocked}
res = {'dx': dx, 'L': L, 'cap': str(CAP_V16 if dx == 0.0 else CAP_V17), 'seatedOverlapMm3': round(base, 3),
       'rows': rows, 'verdict': verdict}
json.dump(res, open(OUT / f'path-check-dx{dx}-L{L}.json', 'w'), indent=1)
prog('done ' + json.dumps(verdict))
