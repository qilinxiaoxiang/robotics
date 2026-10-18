"""2x20 IDC ribbon socket on the Pi header: descent and final-pose clearance per Pi seat (shift dx back, raise dz up).

Socket model (manufacturer drawings, see ../README.md "Connector data"):
  body   s from the header plastic top (43.231) to 43.231 + H; along the row y in +-27.8 (40-way length 55.27 to 55.48);
         across the rows from 1.85 mm below the physical even-row centre (board-edge row, plain face: 3M 6.05 body,
         FCI 6.2 MAX, TE 6.10, Wurth 6.0) to 1.85 mm above the physical odd-row centre.
  key    1.5 mm bump on the odd-row face (3M .06 [1.5]; FCI 1 mm), 3.8 mm long, centred on the row; full body height.
         The pin-1 triangle puts the key on the odd row, which on a real Pi is the inner row (away from the board edge),
         so the key faces up the board (+t) and the plain face faces the head_bottom floor.
  exit   the ribbon leaves the key-side long face 5.5 to 8.5 mm above the mating face (drawings: ribbon clamped between
         body and cover, about 6.5 to 7.5 mm up) and is modelled as a flexible 3 mm thick band running 14 mm up the
         board (+t) over the used column ranges; flexible criterion 1 mm.
Physical rows: the CAD has the odd row along the PCB edge; a real Pi has the even row there (see inspect-geometry.json).
Here the physical even row is t 123.679..126.219 (centre 124.949) and the odd row t 126.219..128.759 (centre 127.489).

For each case (dx, dz) and height H: exact swept gap (manifold3d min_gap of hull(piece, piece + [0, 0, 40])) to every
fixed head part, per part; HmaxTouch and Hmax2mm (all fixed parts, and without head_bottom); the Pi group's own
rear clearance (each Pi part as a convex hull, swept) to the fixed parts; final-pose gap from the socket to the
carried parts (Pi screw heads E-pi-01..04, Pi components, speaker, amplifier; the cap itself only for V1.6 and V1.7).
Env CASES="dx:dz,..."  HS="9.27,10.6,11.0,11.79"  TAG  EXIT_FULL=1 (full-width ribbon band instead of the used columns).  Writes ../idc-study<TAG>.json.
"""
import json, sys, os, time, resource
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

T0 = time.time()
def prog(msg):
    print(f'[{time.time()-T0:7.1f}s {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:5.0f}MiB] {msg}', flush=True)

CASES = [tuple(float(v) for v in c.split(':')) for c in os.environ.get('CASES', '0:0,4.6:0').split(',')]
HS = [float(h) for h in os.environ.get('HS', '9.27,10.6,11.0,11.79').split(',')]
TAG = os.environ.get('TAG', '')
EVEN_C, ODD_C = 0.5 * sum(T_LOW), 0.5 * sum(T_HIGH)
HALF = 1.85; KEY = 1.5; KEY_Y = 1.9; YH = 27.8
EXIT_S = (5.5, 8.5); RISE = 14.0
USED_Y = [(25.4 - 2.54 * 7, 25.4), (25.4 - 2.54 * 20, 25.4 - 2.54 * 17)]   # columns 1-7 and 18-20
if os.environ.get('EXIT_FULL', '0') == '1':
    USED_Y = [(-25.4, 25.4)]   # the whole 40-way ribbon (40 x 1.27 = 50.8 mm) as it leaves the socket

S, prov = solids(None)
FX = [k for k in FIXED if k in S]
FB = {k: bbox(S[k]) for k in FX}
caps = {(0.0, 0.0): load_cap(CAP_V16, CAP_V16_SHA), (4.6, 0.0): load_cap(CAP_V17, CAP_V17_SHA)}
pi_keys = sorted(k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k and 'header_pin' not in k))
PIH = {k: mf.Manifold.hull(S[k]) for k in pi_keys}
fas = json.load(open(ROOT / 'guide/content/fasteners.json'))['screws']
heads = []
for s_ in fas:
    if s_['id'].startswith('E-pi'):
        c = np.array(s_['center']) + np.array([4.6, 0, 0])   # fasteners.json holds the V1.7 seats; back to the V1.6 seat
        ax = -np.array(s_['axis'])
        cyl = trimesh.creation.cylinder(radius=s_['headDiameterMm'] / 2, segment=[c, c + s_['headHeightMm'] * ax], sections=32)
        heads.append((s_['id'], to_mf(cyl)))
prog(f'loaded {len(FX)} fixed, {len(pi_keys)} Pi parts')


def per_part(pieces, keys=None, search=8.0):
    """Exact swept gap from the union of the pieces' sweeps to each fixed part (capped at search)."""
    Hs = [sweep(Pc) for Pc in pieces]
    out = {}
    for k in (keys or FX):
        b = FB[k]; best = search
        for H in Hs:
            hb = bbox(H)
            dd = np.maximum(0, np.maximum(hb[0] - b[1], b[0] - hb[1]))
            if np.linalg.norm(dd) >= best:
                continue
            best = min(best, gap(H, S[k], best))
        if best < search:
            out[k] = round(best, 3)
    return dict(sorted(out.items(), key=lambda kv: kv[1]))


def ok(pieces, need, skip=()):
    for Pc in pieces:
        H = sweep(Pc); hb = bbox(H)
        for k in FX:
            if k in skip:
                continue
            b = FB[k]
            dd = np.maximum(0, np.maximum(hb[0] - b[1], b[0] - hb[1]))
            if np.linalg.norm(dd) >= need:
                continue
            if gap(H, S[k], need) < need:
                return False
    return True


def socket(H, dx, dz):
    d = [-dx, 0, dz]
    body = local_hull((S_BASE_TOP, S_BASE_TOP + H), (-YH, YH), (EVEN_C - HALF, ODD_C + HALF), d)
    key = local_hull((S_BASE_TOP, S_BASE_TOP + H), (-KEY_Y, KEY_Y), (ODD_C + HALF, ODD_C + HALF + KEY), d)
    return [body, key]


def exit_band(dx, dz):
    d = [-dx, 0, dz]
    s0, s1 = S_BASE_TOP + EXIT_S[0], S_BASE_TOP + EXIT_S[1]
    return [local_hull((s0, s1), yr, (ODD_C + HALF, ODD_C + HALF + RISE), d) for yr in USED_Y]


def bis(pred, lo=4.0, hi=16.0, tol=0.01):
    if not pred(lo):
        return None
    if pred(hi):
        return hi
    while hi - lo > tol:
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if pred(m) else (lo, m)
    return lo


out = {'model': {'halfWidthFromRowCentreMm': HALF, 'keyMm': KEY, 'keyLengthMm': 2 * KEY_Y, 'lengthHalfMm': YH,
                 'exitBandAboveMatingFaceMm': EXIT_S, 'exitRiseMm': RISE, 'usedColumnY': USED_Y,
                 'physicalEvenRowT': T_LOW, 'physicalOddRowT': T_HIGH},
       'heights': HS, 'solidProvenance': prov, 'cases': {}}
for dx, dz in CASES:
    key = f'dx{dx}-dz{dz}'
    r = {'dx': dx, 'dz': dz}
    r['HmaxTouch'] = bis(lambda H: ok(socket(H, dx, dz), 1e-6))
    r['Hmax2mm'] = bis(lambda H: ok(socket(H, dx, dz), 2.0))
    r['Hmax2mmIgnoringFloor'] = bis(lambda H: ok(socket(H, dx, dz), 2.0, skip=('head_bottom',)))
    r['perHeight'] = {}
    for H in HS:
        rec = {'sweptGapPerFixedPart': per_part(socket(H, dx, dz))}
        rec['exitBandSweptGapPerFixedPart'] = per_part(exit_band(dx, dz))
        # final pose against what the cap carries
        body = union(socket(H, dx, dz)); fin = {}
        cap = caps.get((dx, dz))
        items = ([('head_cap', cap)] if cap is not None else []) + \
                [(k, tr(S[k], [-dx, 0, dz])) for k in pi_keys if 'header' not in k and 'solder_tails' not in k] + \
                [(n, tr(Mh, [-dx, 0, dz])) for n, Mh in heads] + [(k, S[k]) for k in SPEAKER + ['amplifier'] if k in S]
        for n, M in items:
            gg = gap(body, M, 5.0)
            if gg < 5.0:
                fin[n] = round(gg, 3)
        rec['finalPoseGapToCarried'] = dict(sorted(fin.items(), key=lambda kv: kv[1]))
        r['perHeight'][str(H)] = rec
    # the Pi group's own rear clearance (rigid): each Pi part's convex hull, swept
    rear = {}
    for k in pi_keys:
        g = per_part([tr(PIH[k], [-dx, 0, dz])])
        if g:
            n, v = next(iter(g.items()))
            rear[k] = [v, n]
    r['piGroupSweptGap'] = dict(sorted(rear.items(), key=lambda kv: kv[1][0]))
    sh = {}
    for n, Mh in heads:
        g = per_part([tr(Mh, [-dx, 0, dz])])
        if g:
            sh[n] = next(iter(g.items()))
    r['piScrewHeadSweptGap'] = sh
    out['cases'][key] = rnd(r, 3)
    prog(f'{key}: touch {r["HmaxTouch"]} 2mm {r["Hmax2mm"]} 2mm-no-floor {r["Hmax2mmIgnoringFloor"]} '
         f'rear {next(iter(r["piGroupSweptGap"].items()), None)}')
    json.dump(out, open(OUT / f'idc-study{TAG}.json', 'w'), indent=1)
prog('done')
