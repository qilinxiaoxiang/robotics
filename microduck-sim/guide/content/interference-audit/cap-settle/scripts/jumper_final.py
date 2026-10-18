"""Deciding numbers for single female jumper sleeves, per used pin in PHYSICAL numbering, per cap version.

Real Pi row layout: the even row runs along the board edge (CAD t 123.679..126.219), the odd row is the inner row
(CAD t 126.219..128.759). Sleeve = 2.54 x 2.54 box from the header plastic top, length L; wire = OD d leaving the
sleeve end along the pin axis with a bend of inner radius r right at the exit, 90 deg (then 3 mm run) or 180 deg
(hairpin, then 3 mm back) towards down / up / +y / -y; capsule chains circumscribing the round wire.
For each version (Pi seat shift), pin and L: exact swept gap of the sleeve (governing part) and, per wire model,
the best bend direction (largest exact swept gap) with every direction's gap recorded.
Env VERSIONS="name:dx:dz,..."  LS="13.85,14.0,14.25,15.24"  WLS="13.85,14.25".  Writes ../jumper-final.json.
"""
import json, sys, os, time, resource
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

T0 = time.time()
def prog(msg):
    print(f'[{time.time()-T0:7.1f}s {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:5.0f}MiB] {msg}', flush=True)

VERSIONS = [(v.split(':')[0], float(v.split(':')[1]), float(v.split(':')[2]))
            for v in os.environ.get('VERSIONS', 'V1.6:0:0,V1.7:4.6:0').split(',')]
LS = [float(x) for x in os.environ.get('LS', '13.85,14.0,14.25,15.24').split(',')]
WLS = [float(x) for x in os.environ.get('WLS', '13.85,14.25').split(',')]
WIRE_MODELS = {'tight': {'d': 1.2, 'r': 0.6}, 'nominal': {'d': 1.4, 'r': 1.4}, 'loose': {'d': 1.6, 'r': 2.4}}
DIRS = {'down': -CT, 'up': CT, '+y': EY, '-y': -EY}
RUN = 3.0; SEARCH = 8.0
S, prov = solids(FIXED)
FX = [k for k in FIXED if k in S]
FB = {k: bbox(S[k]) for k in FX}
prog('loaded')


def clear(pieces):
    best, who = SEARCH, None
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
    return best, who


def row_of(pin):
    return row_t(pin, physical=True)


def sleeve(pin, L, d):
    return local_hull((S_BASE_TOP, S_BASE_TOP + L), col_y(pin), row_of(pin), d=d)


def wire(pin, L, d, wm, dname, mode):
    y0, y1 = col_y(pin); r0, r1 = row_of(pin)
    c0 = P(S_BASE_TOP + L, 0.5 * (y0 + y1), 0.5 * (r0 + r1)) + d
    rho = wm['r'] + wm['d'] / 2; D = DIRS[dname]
    if mode == '90':
        pieces, _ = wire_chain(c0, A, D, rho, RUN, wm['d'] / 2, n_arc=6)
        return pieces
    th = np.linspace(0, math.pi, 10); centre = c0 + rho * D
    pts = [centre - rho * D * math.cos(t_) + rho * A * math.sin(t_) for t_ in th]
    pieces = [capsule(p, q, wm['d'] / 2) for p, q in zip(pts[:-1], pts[1:])]
    pieces.append(capsule(pts[-1], pts[-1] - RUN * A, wm['d'] / 2))
    return pieces


out = {'rows': 'physical (even row along the board edge)', 'lengths': LS, 'wireLengths': WLS, 'wireModels': WIRE_MODELS,
       'versions': {}}
for name, dx, dz in VERSIONS:
    d = np.array([-dx, 0.0, dz]); vres = {}
    for pin in USED_PINS:
        r = {'row': 'inner (odd)' if pin % 2 else 'edge (even)', 'column': (pin + 1) // 2, 'sleeve': {}, 'wire': {}}
        for L in LS:
            g, who = clear([sleeve(pin, L, d)])
            r['sleeve'][str(L)] = [round(g, 3), who]
        for L in WLS:
            wr = {}
            for wn, wm in WIRE_MODELS.items():
                per = {}
                for mode in ('90', '180'):
                    for dname in DIRS:
                        g, who = clear(wire(pin, L, d, wm, dname, mode))
                        per[f'{mode}/{dname}'] = [round(g, 3), who]
                best = max(per.items(), key=lambda kv: kv[1][0])
                wr[wn] = {'best': [best[0]] + best[1], 'all': per}
            r['wire'][str(L)] = wr
        vres[str(pin)] = r
        prog(f'{name} pin {pin}: sleeve {r["sleeve"]} wire14.25 best ' +
             str({wn: v['best'] for wn, v in r['wire'][str(WLS[-1])].items()}))
    out['versions'][name] = {'dx': dx, 'dz': dz, 'pins': vres}
    json.dump(out, open(OUT / 'jumper-final.json', 'w'), indent=1)
prog('done')
