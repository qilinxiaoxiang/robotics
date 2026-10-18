"""Descent clearance of single female jumper sleeves and their wire exits, per header position, per cap version.

For every header position in a used pin column (column k = 1..20, row low/high) and every Pi shift dx:
  sleeve  = 2.54 x 2.54 box from the header plastic (s = 43.231) to s = 43.231 + L, carried by the cap;
  descent = exact convex sweep hull(piece, piece + [0, 0, 40]); clearance = exact mesh distance (manifold3d min_gap)
            from the swept piece to every fixed head part (CAMERA_STACK + jaw, motors, head_bottom, ...).
  Lmax_touch / Lmax_2mm: largest L with zero overlap / with >= 2 mm (bisection, 0.01 mm).
  wire    = wire of outside diameter d leaving the sleeve end along the pin axis, bending right at the exit with
            inner radius r, either 90 deg towards a direction (down = -t, up = +t, +y, -y) followed by a 3 mm run,
            or 180 deg (hairpin back along the sleeve, bend plane down/up/+y/-y) followed by a 3 mm run back.
            Pieces are capsules (polyhedra circumscribing the true round wire, conservative by <= 0.03 mm).
  Lmax_wire1mm: largest L with >= 1 mm between every swept wire piece and the fixed parts.
Also the curve gap(L) for the sleeve and the wires over L = 10..16 mm.
Writes ../sleeve-sweep-<tag>.json.  Usage: sleeve_sweep.py <dx> [<dx> ...]   env WIRES=nominal,tight,loose
"""
import json, sys, os, time, resource
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

T0 = time.time()
def prog(msg):
    print(f'[{time.time()-T0:7.1f}s {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:5.0f}MiB] {msg}', flush=True)

DXS = [float(a) for a in sys.argv[1:]] or [0.0, 4.6]
WIRE_MODELS = {'tight': {'d': 1.2, 'r': 0.6}, 'nominal': {'d': 1.4, 'r': 1.4}, 'loose': {'d': 1.6, 'r': 2.4}}
WSEL = os.environ.get('WIRES', 'tight,nominal,loose').split(',')
DIRS = {'down': -CT, 'up': CT, '+y': EY, '-y': -EY}
RUN = 3.0
L_GRID = [10.0, 11.0, 12.0, 13.0, 13.5, 14.0, 14.5, 15.0, 16.0]
SEARCH = 8.0
DZ = float(os.environ.get('DZ', '0'))   # optional Pi seat raise (robot +z) on top of the shift dx

S, prov = solids(FIXED)
EXCLUDE = [k for k in os.environ.get('EXCLUDE', '').split(',') if k]   # what-if: fixed parts taken away
FX = [k for k in FIXED if k in S and k not in EXCLUDE]
FB = {k: bbox(S[k]) for k in FX}
prog(f'solids {len(FX)}')

def clear(pieces, need=None):
    """Smallest exact gap between the swept pieces and the fixed parts, and the governing part.
    With `need`, stops early once a gap below `need` is found (returns that gap)."""
    best, who = (need if need is not None else SEARCH), None
    for Pc in pieces:
        H = sweep(Pc); hb = bbox(H)
        for k in FX:
            b = FB[k]
            dd = np.maximum(0, np.maximum(hb[0] - b[1], b[0] - hb[1]))
            if np.linalg.norm(dd) >= best:
                continue
            g = gap(H, S[k], best)
            if g < best:
                best, who = g, k
                if need is not None:
                    return best, who
    return best, who

def sleeve(k, row, L, dx):
    y = (25.4 - 2.54 * k, 25.4 - 2.54 * (k - 1))
    return local_hull((S_BASE_TOP, S_BASE_TOP + L), y, row, d=[-dx, 0, DZ])

def wire(k, row, L, dx, wm, dname, mode):
    y = 25.4 - 2.54 * k + 1.27; tc = 0.5 * (row[0] + row[1])
    c0 = P(S_BASE_TOP + L, y, tc) + np.array([-dx, 0, DZ])
    rho = wm['r'] + wm['d'] / 2
    D = DIRS[dname]
    if mode == '90':
        pieces, _ = wire_chain(c0, A, D, rho, RUN, wm['d'] / 2, n_arc=6)
        return pieces
    # hairpin: 180 deg in the plane (A, D), then a run back along -A
    th = np.linspace(0, math.pi, 10)
    centre = c0 + rho * D
    pts = [centre - rho * D * math.cos(t_) + rho * A * math.sin(t_) for t_ in th]
    pieces = [capsule(p, q, wm['d'] / 2) for p, q in zip(pts[:-1], pts[1:])]
    pieces.append(capsule(pts[-1], pts[-1] - RUN * A, wm['d'] / 2))
    return pieces

def bisect_L(pred, lo=4.0, hi=24.0, tol=0.01, step=0.5):
    """Largest L in [lo, hi] such that pred holds for every L' <= L (scan upward in `step`, then bisect the first
    failing step). Robust to the non-monotone case where a long piece clears an obstacle by passing beyond it."""
    if not pred(lo):
        return None
    a = lo
    while a + step <= hi:
        if not pred(a + step):
            b = a + step
            while b - a > tol:
                m = 0.5 * (a + b)
                a, b = (m, b) if pred(m) else (a, m)
            return a
        a += step
    return a

COLS = sorted({(p + 1) // 2 for p in USED_PINS})
out = {'dxs': DXS, 'dz': DZ, 'excludedFixedParts': EXCLUDE, 'wireModels': WIRE_MODELS, 'run': RUN, 'lGrid': L_GRID, 'search': SEARCH, 'solidProvenance': prov,
       'positions': {}}
for dx in DXS:
    res = {}
    for k in COLS:
        for rname, row in [('low', T_LOW), ('high', T_HIGH)]:
            key = f'col{k:02d}-{rname}'
            r = {'pinCAD': 2 * k - 1 if rname == 'low' else 2 * k, 'pinPhysicalIfRowsSwapped': 2 * k if rname == 'low' else 2 * k - 1}
            r['LmaxTouch'] = bisect_L(lambda L: clear([sleeve(k, row, L, dx)], 1e-6)[1] is None)
            r['Lmax2mm'] = bisect_L(lambda L: clear([sleeve(k, row, L, dx)], 2.0)[1] is None)
            curve = {}
            for L in L_GRID:
                g, who = clear([sleeve(k, row, L, dx)])
                curve[str(L)] = {'gapMm': round(g, 3), 'by': who} if g > 0 else \
                    {'gapMm': 0.0, 'overlapExcessLengthMm': round(L - r['LmaxTouch'], 3) if r['LmaxTouch'] else None, 'by': who}
            r['sleeveGap'] = curve
            wires = {}
            for wn in WSEL:
                wm = WIRE_MODELS[wn]
                for mode in ('90', '180'):
                    for dname in (DIRS if wn == 'nominal' else ('down', 'up')):
                        lim = bisect_L(lambda L: clear(wire(k, row, L, dx, wm, dname, mode), 1.0)[1] is None, hi=r['LmaxTouch'] or 4.0)
                        rec = {'Lmax1mm': lim}
                        if wn == 'nominal':
                            rec['gap'] = {}
                            for L in (12.0, 13.0, 14.0, 15.0):
                                g, who = clear(wire(k, row, L, dx, wm, dname, mode))
                                rec['gap'][str(L)] = [round(g, 3), who]
                        wires[f'{wn}/{mode}/{dname}'] = rec
            r['wires'] = wires
            res[key] = rnd(r, 3)
            prog(f'dx {dx} {key} touch {r["LmaxTouch"]} 2mm {r["Lmax2mm"]} wire-nominal-90-down {wires.get("nominal/90/down", {}).get("Lmax1mm")}')
    out['positions'][str(dx)] = res
    tag = os.environ.get('TAG', '-'.join(str(d) for d in DXS))
    json.dump(out, open(OUT / f'sleeve-sweep-{tag}.json', 'w'), indent=1)
prog('done')
