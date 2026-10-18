"""Geometry facts: Pi/header frame, GPIO envelope composition, final-pose overlaps and swept overlaps of each envelope."""
import json, sys
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
from vc import *

S, prov = solids()
out = {'provenance': prov}
g = load_npz('guide')

def verts(k):
    return np.asarray(g[k][0])

# --- pin axis from the 40 header pins (long axis of each pin)
axes = []
for i in range(1, 41):
    v = verts(f'head_pi_zero_w_header_pin_{i:02d}')
    c = v - v.mean(0)
    w, U = np.linalg.eigh(c.T @ c)
    a = U[:, -1]; a *= np.sign(a[0]); axes.append(a)
a = np.mean(axes, 0); a /= np.linalg.norm(a)
# board normal from the Pi PCB vertices (smallest-variance direction of the board mesh)
vp = verts('pi'); c = vp - vp.mean(0); w, U = np.linalg.eigh(c.T @ c); nb = U[:, 0]; nb *= np.sign(nb[0])
ey = np.array([0., 1., 0.]); cdir = np.cross(a, ey); cdir /= np.linalg.norm(cdir)  # column direction in the header plane
out['pinAxis'] = r3(a); out['pinAxisTiltFromXdeg'] = round(float(np.degrees(np.arccos(a[0]))), 2)
out['boardNormal'] = r3(nb); out['boardNormalVsPinAxisDeg'] = round(float(np.degrees(np.arccos(abs(nb @ a)))), 2)
out['columnDir'] = r3(cdir)

# local coordinates s (along pin axis), y, t (column) with origin at pin 1 base centre
def loc(P, o):
    P = np.asarray(P) - o
    return np.column_stack([P @ a, P[:, 1], P @ cdir])

base = verts('head_pi_zero_w_header_base')
p1 = verts('head_pi_zero_w_header_pin_01'); p2 = verts('head_pi_zero_w_header_pin_02')
o = np.array([0., 0., 0.])
Lb = loc(base, o); L1 = loc(p1, o); L2 = loc(p2, o)
out['headerBase_s'] = r3([Lb[:, 0].min(), Lb[:, 0].max()])
out['pin01_s'] = r3([L1[:, 0].min(), L1[:, 0].max()]); out['pin02_s'] = r3([L2[:, 0].min(), L2[:, 0].max()])
out['pin01_t'] = r3([L1[:, 2].min(), L1[:, 2].max()]); out['pin02_t'] = r3([L2[:, 2].min(), L2[:, 2].max()])
out['headerBase_t'] = r3([Lb[:, 2].min(), Lb[:, 2].max()])
out['pinLengthAboveBaseMm'] = round(float(L1[:, 0].max() - Lb[:, 0].max()), 3)
sb = verts('pi'); Ls = loc(sb, o)
out['pi_s'] = r3([Ls[:, 0].min(), Ls[:, 0].max()])
env = {}
for pin in USED_PINS:
    v = verts(f'head_pi_gpio_pin_{pin:02d}_receiving'); L = loc(v, o)
    env[pin] = dict(s=r3([L[:, 0].min(), L[:, 0].max()]), y=r3([L[:, 1].min(), L[:, 1].max()]), t=r3([L[:, 2].min(), L[:, 2].max()]),
                    xmax=round(float(v[:, 0].max()), 3), nverts=len(v),
                    distinct_s=sorted(set(np.round(L[:, 0], 2).tolist())), distinct_t=sorted(set(np.round(L[:, 2], 2).tolist())))
out['envelopes'] = env
out['envelopeLengthAboveBaseTopMm'] = {p: round(e['s'][1] - out['headerBase_s'][1], 3) for p, e in env.items()}
# hull-check each envelope: convex?
conv = {}
for pin in USED_PINS:
    M = S[f'head_pi_gpio_pin_{pin:02d}_receiving']; H = mf.Manifold.hull(M)
    conv[pin] = round(H.volume() - M.volume(), 4)
out['envelopeHullMinusVolumeMm3'] = conv

# --- moving group and fixed group, final pose overlaps
pi_keys = [k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k)]
gpio = [f'head_pi_gpio_pin_{p:02d}_receiving' for p in USED_PINS]
moving = ['head_cap'] + SPEAKER + ['amplifier'] + pi_keys + gpio
fixed = [k for k in FIXED if k in S]
fin = []
for m in moving:
    for f in fixed:
        v = overlap(S[m], S[f])
        if v > 1e-4:
            fin.append([m, f, round(v, 4)])
out['finalPoseOverlaps'] = fin

# --- swept overlap (exact for convex envelopes: hull of start and end) along +z 40 (cap-on approach [0,0,40])
D = np.array([0, 0, 40.0])
sw = {}
for p in USED_PINS:
    M = S[f'head_pi_gpio_pin_{p:02d}_receiving']
    H = mf.Manifold.hull(union([M, tr(M, D)]))
    hits = {}
    for f in fixed:
        v = overlap(H, S[f]) - overlap(M, S[f])
        if v > 1e-3:
            hits[f] = round(v, 3)
    sw[p] = hits
out['envelopeSweptExcessOverlapMm3'] = sw
json.dump(out, open(HERE / 'inspect1.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != 'provenance'}, indent=1))
print({k: v for k, v in prov.items() if 'hull' in v})
