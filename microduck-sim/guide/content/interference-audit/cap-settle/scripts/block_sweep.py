"""Height budget for multi-position connector bodies (for example a 2x20 IDC socket) seated on the Pi header.

Block = box in the header frame: s from the header plastic top (43.231) to 43.231 + H; across the rows
t in tc +- W/2 (tc = 126.219, header centre); along the row y in [y0, y1]. Carried by the cap with Pi shift dx and
lowered by [0, 0, 40]. For each block and dx:
  HmaxTouch / Hmax2mm = largest H whose exact swept solid is clear of / >= 2 mm from every fixed head part;
  final pose at H = Hmax2mm: exact gap to the carried parts (cap, Pi parts other than the header and its tails,
  Pi screw heads E-pi-01..04 as 4.0 x 1.5 mm cylinders from fasteners.json, speaker, amplifier).
  Ribbon exits (flexible, 1 mm criterion): a 1.0 mm thick strip on top of the block continuing 3 mm past the
  lower (-t) or upper (+t) edge, then folding back towards the board; the fold is modelled as a 1.0 x 4.0 mm strip
  running back along -A from the top face. Reported as the exact swept gap at H = Hmax2mm.
Writes ../block-sweep.json.  Usage: block_sweep.py
"""
import json, sys, os, time, resource
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

T0 = time.time()
def prog(msg):
    print(f'[{time.time()-T0:7.1f}s {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:5.0f}MiB] {msg}', flush=True)

DXS = [float(a) for a in os.environ.get('DXS', '0,4.6').split(',')]
DZ = float(os.environ.get('DZ', '0'))   # optional Pi seat raise; the carried-part check then omits the cap
TAG = os.environ.get('TAG', '')
TC = 0.5 * (T_LOW[0] + T_HIGH[1])
BLOCKS = {
    '2x20 W5.08 (bare housing pitch envelope)': (5.08, -25.4, 25.4),
    '2x20 W7.0': (7.0, -26.4, 26.4),
    '2x20 W8.9 (typical IDC socket)': (8.9, -28.0, 28.0),
    '2x20 W10.2': (10.2, -28.6, 28.6),
    '2x7 pins 1-14 W8.9': (8.9, 25.4 - 17.78 - 2.6, 25.4 + 2.6),
    '2x7 pins 1-14 W5.08': (5.08, 25.4 - 17.78, 25.4),
}
S, prov = solids(None)
FX = [k for k in FIXED if k in S]
FB = {k: bbox(S[k]) for k in FX}
caps = {0.0: load_cap(CAP_V16, CAP_V16_SHA), 4.6: load_cap(CAP_V17, CAP_V17_SHA)}
pi_keys = sorted(k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k
                 and 'header' not in k and 'solder_tails' not in k))
fas = json.load(open(ROOT / 'guide/content/fasteners.json'))['screws']
heads = []
for s_ in fas:
    if s_['id'].startswith('E-pi'):
        c = np.array(s_['center']) + np.array([4.6, 0, 0])   # fasteners.json holds V1.7 seats; back to V1.6
        ax = -np.array(s_['axis'])                           # head stands proud of the board, towards +A
        cyl = trimesh.creation.cylinder(radius=s_['headDiameterMm'] / 2, segment=[c, c + s_['headHeightMm'] * ax], sections=32)
        heads.append((s_['id'], to_mf(cyl)))
prog('loaded')

def clear(pieces, need=None, search=8.0):
    best, who = (need if need is not None else search), None
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

def blk(W, y0, y1, H, dx):
    return local_hull((S_BASE_TOP, S_BASE_TOP + H), (y0, y1), (TC - W / 2, TC + W / 2), d=[-dx, 0, DZ])

def ribbon(W, y0, y1, H, dx, side):
    st = S_BASE_TOP + H; d = [-dx, 0, DZ]
    yy = (max(y0, -25.4), min(y1, 25.4))
    if side == 'down':
        e = TC - W / 2
        a = local_hull((st - 1.0, st), yy, (e - 3.0, e), d)
        b = local_hull((st - 5.0, st), yy, (e - 4.0, e - 3.0), d)
    else:
        e = TC + W / 2
        a = local_hull((st - 1.0, st), yy, (e, e + 3.0), d)
        b = local_hull((st - 5.0, st), yy, (e + 3.0, e + 4.0), d)
    return [a, b]

def bis(pred, lo=2.0, hi=24.0, tol=0.01):
    if not pred(lo):
        return None
    if pred(hi):
        return hi
    while hi - lo > tol:
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if pred(m) else (lo, m)
    return lo

out = {'tc': TC, 'dz': DZ, 'blocks': {}}
for name, (W, y0, y1) in BLOCKS.items():
    rec = {'W': W, 'y': [y0, y1]}
    for dx in DXS:
        r = {}
        r['HmaxTouch'] = bis(lambda H: clear([blk(W, y0, y1, H, dx)], 1e-6)[1] is None)
        r['Hmax2mm'] = bis(lambda H: clear([blk(W, y0, y1, H, dx)], 2.0)[1] is None)
        H2 = r['Hmax2mm']
        if H2:
            g, who = clear([blk(W, y0, y1, H2, dx)]); r['sweptGapAtHmax2mm'] = [round(g, 3), who]
            B = blk(W, y0, y1, H2, dx)
            fin = {}
            cap = caps.get(dx) if DZ == 0 else None
            items = ([('head_cap', cap)] if cap is not None else []) + [(k, tr(S[k], [-dx, 0, DZ])) for k in pi_keys] + \
                    [(n, tr(Mh, [-dx, 0, DZ])) for n, Mh in heads] + [(k, S[k]) for k in SPEAKER + ['amplifier'] if k in S]
            for n, M in items:
                gg = gap(B, M, 5.0)
                if gg < 5.0:
                    fin[n] = round(gg, 3)
            r['finalPoseGapToCarriedAtHmax2mm'] = dict(sorted(fin.items(), key=lambda kv: kv[1])[:8])
            for side in ('down', 'up'):
                g, who = clear(ribbon(W, y0, y1, H2, dx, side)); r[f'ribbon-{side} sweptGapAtHmax2mm'] = [round(g, 3), who]
        rec[str(dx)] = rnd(r, 3)
        prog(f'{name} dx {dx}: {rec[str(dx)]}')
    out['blocks'][name] = rec
    json.dump(out, open(OUT / f'block-sweep{TAG}.json', 'w'), indent=1)
prog('done')
