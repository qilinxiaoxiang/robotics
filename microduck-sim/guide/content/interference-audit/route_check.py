#!/usr/bin/env python3
"""Quick geometric screen for the torso routes before the full cables.py audit (no bounded runner needed, about 40 s).

Usage: route_check.py [overlay.json]   An overlay has the routes.json route keys to replace plus an optional
"splice_at" {cable id: mm} map; without it the current routes.json and the build_guide_data splice distances are checked.

Composes the torso cables the way build_guide_data.build_cables does (plug mouth + route; feeds end at the splice
point on their link), then reports: (1) cable-to-cable approaches closer than the sum of radii (ignoring bundled pairs
and the first/last 10 mm around shared ends), (2) clearance of every cable sample (outside its first/last 8 mm) to the
pack, cover, upright OpenRB, IMU parts and the envelope boxes, (3) clearance of each splice sleeve (r 1.75), and the
link lengths. Robot frame, mm.
"""
import json, sys, math
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
CONTENT = HERE.parent
WORLD = CONTENT.parent / 'print/world'
sys.path.insert(0, str(CONTENT))
from build_guide_data import point_along  # noqa: E402

cand = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else {}
base = json.loads((CONTENT / 'routes.json').read_text())['routes']
R = dict(base)
AT = {'dxl-r5': 7.0, 'dxl-l10': 7.0, 'dxl-n12': 30.0}
for k, v in cand.items():
    if k == 'splice_at':
        AT.update(v)
    else:
        R[k] = v

mouth = {'dxl5': [-40.5, -0.4, -25.2], 'dxl10': [-40.5, -0.4, -20.2], 'dxl12': [-28.55, 22.4, -22.75]}
cab = {}
splice = {}
for rid, cid in (('dxl5', 'dxl-r5'), ('dxl10', 'dxl-l10'), ('dxl12', 'dxl-n12')):
    p = [mouth[rid]] + R[rid]
    cab[cid] = (p, 1.1)
    splice[cid] = list(point_along(p, AT[cid])[0])
cab['vin20'] = (R['vin20'], 1.2)
cab['vout'] = (R['vout'], 1.4)
cab['feed-r'] = (R['feed_r'] + [splice['dxl-r5']], 0.9)
cab['feed-l'] = (R['feed_l'] + [splice['dxl-l10']], 0.9)
cab['feed-n'] = (R['feed_n'] + [splice['dxl-n12']], 0.9)
cab['orb-pwr'] = (R['openrbpwr'], 0.9)
neck = R['bundle_neck']
cab['pi-trunk'] = (R['trunk'] + neck[1:], 0.9)
cab['imu'] = (R['imu'] + [[p[0], p[1] + 1.5, p[2]] for p in neck[1:]], 0.8)
cab['uart'] = (R['uart_lower'] + [[p[0], p[1] - 1.5, p[2]] for p in neck[1:]], 0.7)
cab['tether'] = (R['tether'], 1.2)


def plen(p):
    return sum(math.dist(a, b) for a, b in zip(p, p[1:]))


def samp(path, step=0.25):
    P = np.array(path, float)
    out, s, cum = [], [], 0.0
    for a, b in zip(P[:-1], P[1:]):
        L = np.linalg.norm(b - a)
        n = max(2, int(L / step) + 1)
        t = np.linspace(0, 1, n, endpoint=False)
        out.append(a + (b - a) * t[:, None])
        s.append(cum + t * L)
        cum += L
    out.append(P[-1:]); s.append(np.array([cum]))
    return np.vstack(out), np.concatenate(s)


SAMP = {k: samp(v[0]) for k, v in cab.items()}
RAD = {k: v[1] for k, v in cab.items()}
print('link lengths (mm, kit cable 180):', {k: round(plen(cab[k][0]), 1) for k in ('dxl-r5', 'dxl-l10', 'dxl-n12')})
print('splice points:', {k: [round(x, 1) for x in v] for k, v in splice.items()})

# ---- cable-cable ----
BUNDLE = {'pi-trunk', 'uart', 'imu'}
OWN = {'feed-r': 'dxl-r5', 'feed-l': 'dxl-l10', 'feed-n': 'dxl-n12'}
FEEDS = {'feed-r', 'feed-l', 'feed-n', 'orb-pwr', 'pi-trunk', 'vout'}
J = np.array([-42.0, 9.0, -17.0])
print('\n--- cable-cable (torso region x<-5, closer than ri+rj-0.05) ---')
keys = list(cab)
for i, a in enumerate(keys):
    for b in keys[i + 1:]:
        if a in BUNDLE and b in BUNDLE:
            continue
        A, sa = SAMP[a]; B, sb = SAMP[b]
        ma = A[:, 0] < -5; mb = B[:, 0] < -5
        if not ma.any() or not mb.any():
            continue
        A2, sa2 = A[ma], sa[ma]; B2, sb2 = B[mb], sb[mb]
        d = np.linalg.norm(A2[:, None, :] - B2[None, :, :], axis=2)
        need = RAD[a] + RAD[b]
        bad = d < need - 0.05
        if not bad.any():
            continue
        # masks for tolerated contact
        tol = np.zeros_like(bad)
        la, lb = sa[-1], sb[-1]
        if OWN.get(a) == b:  # feed meets its own link at the splice: last 12 mm of the feed
            tol |= (sa2 > la - 12)[:, None]
        if OWN.get(b) == a:
            tol |= (sb2 > lb - 12)[None, :]
        if a in FEEDS and b in FEEDS:  # branches leaving J together: within 10 mm of J
            tol |= (np.linalg.norm(A2 - J, axis=1) < 10)[:, None] | (np.linalg.norm(B2 - J, axis=1) < 10)[None, :]
        if a in BUNDLE or b in BUNDLE:  # bundle gathers at neck[0]: within 8 mm of (-16,3,41)
            n0 = np.array([-16.0, 3.0, 41.0])
            tol |= (np.linalg.norm(A2 - n0, axis=1) < 8)[:, None] | (np.linalg.norm(B2 - n0, axis=1) < 8)[None, :]
        real = bad & ~tol
        if real.any():
            dm = np.where(real, d, 99)
            ia, ib = np.unravel_index(np.argmin(dm), dm.shape)
            run = real.any(axis=1).sum() * 0.25
            print(f'  {a:8s} x {b:8s} min {dm.min():.2f} need {need:.1f} at {np.round(A2[ia], 1)} run {run:.1f} mm  <<<')

# ---- cable-solid ----
def box(lo, hi):
    return (np.array(lo, float), np.array(hi, float))

BOXES = {'regulator': box([-45, -13, -3], [-37, 13, 27]), 'junction_j': box([-45, 5, -27], [-39, 13, -15]),
         'xt30_robot': box([-44.6, -5.1, -66], [-39.4, 5.1, -51]), 'motor5': box([-18.5, -27.5, -3], [15.5, -7.5, 23]),
         'motor10': box([-18.5, 7.5, -3], [15.5, 27.5, 23]), 'torso_base': box([-19, -28.5, -1], [17, 28.5, 2])}
MESH = {}
for name, f in (('rear_pack', 'rear_pack.stl'), ('rear_pack_cover', 'rear_pack_cover.stl'), ('openrb_board', 'openrb-board-upright.stl'),
                ('imu_board', 'imu_board.stl'), ('imu_sh4_receiving', 'imu_sh4_receiving.stl')):
    m = trimesh.load(str(WORLD / f), force='mesh')
    MESH[name] = m
    print(f'mesh {name}: {len(m.faces)} faces, bounds {np.round(m.bounds, 1).tolist()}')


def box_dist(P, lo, hi):
    # signed-ish: positive outside (euclidean), negative inside (depth to nearest face)
    d_out = np.maximum(np.maximum(lo - P, P - hi), 0)
    out = np.linalg.norm(d_out, axis=1)
    inside = np.all((P > lo) & (P < hi), axis=1)
    depth = np.minimum(P - lo, hi - P).min(axis=1)
    return np.where(inside, -depth, out)


def mesh_dist(P, m):
    # unsigned closest distance, negative when inside (contains is robust enough for these closed solids)
    _, dist, _ = trimesh.proximity.closest_point(m, P)
    try:
        inside = m.contains(P)
    except Exception:
        inside = np.zeros(len(P), bool)
    return np.where(inside, -dist, dist)


from cables import spline_samples  # noqa: E402


def spl(path):
    X, _ = spline_samples(path)
    X = np.asarray(X, float)
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(X, axis=0), axis=1))])
    return X, s


SPL = {k: spl(v[0]) for k, v in cab.items()}
print('\n--- cable-solid clearance (distance - radius), samples outside first/last 8 mm; worst per cable/solid < 0.5 ---')
WORST = []
for key, (P, s) in list(SAMP.items()) + [(k + '~spline', v) for k, v in SPL.items()]:
    k = key[:-7] if key.endswith('~spline') else key
    k_disp = f"{k}/{'spline' if key.endswith('~spline') else 'poly'}"
    r = RAD[k]
    mid = (s >= 8) & (s <= s[-1] - 8) & (P[:, 0] < -5)
    if not mid.any():
        continue
    Pm = P[mid]
    rows = []
    for name, (lo, hi) in BOXES.items():
        if np.all(Pm.min(axis=0) > hi + 3) or np.all(Pm.max(axis=0) < lo - 3):
            pass
        d = box_dist(Pm, lo, hi) - r
        i = int(np.argmin(d))
        rows.append((name, d[i], Pm[i]))
    for name, m in MESH.items():
        lo, hi = m.bounds
        near = np.all((Pm > lo - 4) & (Pm < hi + 4), axis=1)
        if not near.any():
            continue
        d = mesh_dist(Pm[near], m) - r
        i = int(np.argmin(d))
        rows.append((name, d[i], Pm[near][i]))
    for name, d, p in rows:
        if d < 0.5:
            flag = '  <<< PENETRATES' if d < -0.1 else ('  (touch)' if d < 0 else '')
            print(f'  {k_disp:16s} vs {name:18s} clearance {d:6.2f} at {np.round(p, 1)}{flag}')
            WORST.append((k, name, d))

print('\n--- splice sleeves (r 1.75) ---')
for cid, pt in splice.items():
    P = np.array([pt])
    rows = []
    for name, (lo, hi) in BOXES.items():
        rows.append((name, float(box_dist(P, lo, hi)[0]) - 1.75))
    for name, m in MESH.items():
        rows.append((name, float(mesh_dist(P, m)[0]) - 1.75))
    rows.sort(key=lambda t: t[1])
    others = []
    for k2, (P2, s2) in SAMP.items():
        if k2 == cid or k2 == {'dxl-r5': 'feed-r', 'dxl-l10': 'feed-l', 'dxl-n12': 'feed-n'}[cid]:
            continue
        d = np.linalg.norm(P2 - np.array(pt), axis=1).min() - 1.75 - RAD[k2]
        others.append((k2, round(float(d), 2)))
    others.sort(key=lambda t: t[1])
    print(f'  {cid}: at {np.round(pt, 1)} solids {[(n, round(d, 2)) for n, d in rows[:3]]} cables {others[:3]}')
