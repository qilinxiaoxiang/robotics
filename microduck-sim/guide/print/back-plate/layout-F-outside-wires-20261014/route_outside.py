"""Outside wire routes for layout F without passage P1 (draft, 2026-10-14). World frame (guide), mm.

Every wire leaves its terminal straight out through its side window and stays outside the box. 22 AWG, tube dia 1.8,
centreline bend radius 3 (shellkit.fillet_path). Terminal entry points are the V1.11 ones (wires_F_inside_reference.json).
- 15 V link (-y): mid IN -> top IN up the outside of the -y wall; link_p (both lower screws) runs at y -34.0, x -51.4,
  link_q at y -36.2, x -54.705, so the two never cross.
- 15 V feed (-y): mid IN -> 5991 terminal: down the outside of the -y wall (feed_p y -34.0 at x -58.0, feed_q y -36.2 at
  x -54.705), inward under the step and down to the 5991 window; feed_q inner (y -17.4), feed_p outer (y -19.8), + lower
  at both ends.
- 7 V and 5 V (+y): out of the OUT windows, up the outside of the +y wall at y 34.0 in four x columns (7V_a -58.0,
  7V_b -54.705, 5V_a -51.4, 5V_b -48.1), over the top edge, inward across the box top at z 45.0, forward over the
  shell roof. 7 V: round the front edge of the shell roof, down in front of the pack plate and back through the plate's
  head notch to OpenRB J4. 5 V: forward over the neck base to the neck bundle point (-6, -14, 43.5) of the current
  pi-lead route, which it follows to the Pi.
Writes wires_F.json (same format as layout-F/wires_F.json) and routes_outside.json (lengths and clearances)."""
import sys, json, math
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree
HERE = Path(__file__).resolve().parent; BP = HERE.parent
sys.path.insert(0, str(BP / 'layout-D-20261014')); import shellkit as K
IA = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit')
sys.path.insert(0, str(IA)); import ia_lib
from cables import spline_samples
OPT = BP / 'layout-F-ear-20261014' / 'options'
WIRE_R, BEND = 0.9, 3.0
XE, YE = -54.705, 30.15                      # XL4015 terminal entry plane and entry |y|
YI, YO = 34.0, 36.2                          # outside lanes (inner, outer)
ZTOP = 45.0                                  # run across the box top (top wall z 43)
ZROOF = 43.6                                 # run over the shell roof (roof top 40.8..41.7 at x -24)
PD = dict(x=-54.6, y=-13.196, p=-25.81, q=-22.31)
# +y columns: every jog is >= 6 mm so both corners keep the 3 mm bend radius
COL = {'7V_b': XE, '7V_a': -48.5, '5V_a': -60.9, '5V_b': -63.3}
ROOFY = {'5V_b': -3.6, '5V_a': -1.2, '7V_b': 1.2, '7V_a': 3.6}
# head-notch slots (plate x -21..-19, notch |y| <= 6 down to z 32.7): 7V_b takes the slot the Pi lead leaves free (between
# UART and link L), 7V_a the one below it (between link N and link L)
SLOT = {'7V_b': (1.5, 37.6), '7V_a': (1.9, 35.3)}
XF = {'7V_b': -17.6, '7V_a': -15.2}          # front of each hairpin round the shell roof edge
J4Y = {'7V_a': 1.25, '7V_b': -1.25}          # J4 ends; the guide's pw-7v is one centreline ending at (-31.5, 0, 25.4)
JOIN = np.array([-6.0, -14.0, 43.5])         # pi-lead / neck bundle point


def wires():
    g = {}
    # ---- -y side, 15 V
    g['15V_link_p'] = [(XE, -YE, -1.9), (XE, -YI, -1.9), (-48.5, -YI, -1.9), (-48.5, -YI, 25.7), (XE, -YI, 25.7), (XE, -YE, 25.7)]
    g['15V_link_q'] = [(XE, -YE, 3.1), (XE, -YO, 3.1), (XE, -YO, 30.7), (XE, -YE, 30.7)]
    g['15V_feed_q'] = [(XE, -YE, 1.1), (XE, -YO, 1.1), (XE, -YO, -17.6), (PD['x'], -20.2, -17.6), (PD['x'], -15.5, PD['q']), (PD['x'], PD['y'], PD['q'])]
    g['15V_feed_p'] = [(XE, -YE, -3.9), (XE, -YI, -3.9), (-60.9, -YI, -3.9), (-60.9, -YI, -20.0), (-60.9, -22.4, -20.0), (PD['x'], -22.4, -20.0),
                       (PD['x'], -16.59, PD['p']), (PD['x'], PD['y'], PD['p'])]
    # ---- +y side, up the wall and over the top
    z0 = {'7V_a': 25.7, '7V_b': 30.7, '5V_a': 2.1, '5V_b': -2.9}
    for k, x in COL.items():
        w = [(XE, YE, z0[k]), (XE, YI, z0[k])]
        if abs(x - XE) > 1e-6:
            w.append((x, YI, z0[k]))
        g[k] = w + [(x, YI, ZTOP), (x, ROOFY[k], ZTOP), (-44.0, ROOFY[k], ZTOP), (-24.0, ROOFY[k], ZROOF)]
    # 7 V: round the shell roof front edge (x about -20.8), down in front of the pack plate, back through the head notch and
    # over the OpenRB to J4 (approach as the current guide pw-7v: (-33, y, 26.8) -> (-31.5, y, 25.4))
    back = {'7V_b': [(-22.0, 1.5, 37.6), (-33.0, 1.0, 37.4), (-34.5, J4Y['7V_b'], 30.5)],
            '7V_a': [(-22.0, 1.9, 35.3), (-31.5, 1.9, 35.0), (-33.8, J4Y['7V_a'], 30.0)]}
    for k in ('7V_a', '7V_b'):
        ys, zs = SLOT[k]; yj = J4Y[k]
        yt = ROOFY[k] if k == '7V_a' else ys      # 7V_a keeps its roof lane over 7V_b's hairpin and shifts y on the way down
        g[k] += [(XF[k], yt, ZROOF), (XF[k], ys, zs)] + back[k] + [(-33.0, yj, 26.8), (-31.5, yj, 25.4)]
    # 5 V: forward over the neck base to the bundle point, side by side (2.4 apart)
    d = JOIN[:2] - np.array([-21.0, -2.4]); d = d / np.linalg.norm(d); nrm = np.array([-d[1], d[0]])
    for k, s in (('5V_a', 1.2), ('5V_b', -1.2)):
        e = JOIN[:2] + s * nrm
        g[k] += [(-21.0, ROOFY[k], ZROOF), (float(e[0]), float(e[1]), JOIN[2])]
    return g


NET = {'7V_a': '7V', '7V_b': '7V', '5V_a': '5V', '5V_b': '5V', '15V_link_p': 'p', '15V_link_q': 'q', '15V_feed_p': 'p', '15V_feed_q': 'q'}
ENDS = {k: ('terminal', 'terminal') for k in NET}
ENDS.update({'7V_a': ('terminal', 'J4'), '7V_b': ('terminal', 'J4'), '5V_a': ('terminal', 'bundle'), '5V_b': ('terminal', 'bundle')})


def arclen(p):
    return np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]


def resample(p, step=0.25):
    s = arclen(p); t = np.arange(0, s[-1], step)
    return np.c_[[np.interp(t, s, p[:, i]) for i in range(3)]].T, t


def main():
    WP = wires(); paths = {k: np.asarray(K.fillet_path(w, BEND, n=10)) for k, w in WP.items()}
    man = ia_lib.manifest()
    parts = {}
    for k, rec in man.items():
        if k in ('rear_frame', 'rear_lid'):
            continue
        parts[k] = (np.array(rec['bounds']), None)
    extra = {'frame_hidden_noP1': HERE / 'frame_hidden_noP1-world.stl', 'lid_hidden': OPT / 'lid_hidden-world.stl', 'screw_hidden': OPT / 'screw_hidden-world.stl'}
    cache = {}

    def mesh(k):
        if k not in cache:
            cache[k] = trimesh.load(str(extra[k]), force='mesh') if k in extra else trimesh.Trimesh(*ia_lib.load_solid(k), process=False)
        return cache[k]
    for k in extra:
        parts[k] = (np.array(mesh(k).bounds), None)
    rows = {}; samples = {}
    for w, p in paths.items():
        q, s = resample(p); L = s[-1] if len(s) else 0.0
        keep = (s > 1.6) & (s < arclen(p)[-1] - (2.0 if ENDS[w][1] == 'J4' else (0.5 if ENDS[w][1] == 'bundle' else 1.6)))
        q, s = q[keep], s[keep]; samples[w] = (q, s)
        gaps = {}
        lo, hi = q.min(0) - 3, q.max(0) + 3
        for k, (b, _) in parts.items():
            if np.any(b[1] < lo) or np.any(b[0] > hi):
                continue
            near = np.all((q >= b[0] - 3) & (q <= b[1] + 3), axis=1)
            if not near.any():
                continue
            m = mesh(k); idx = np.flatnonzero(near); sd = np.empty(len(idx))
            for i in range(0, len(idx), 256):
                sd[i:i + 256] = trimesh.proximity.signed_distance(m, q[idx[i:i + 256]])
            g = -sd - WIRE_R; j = int(np.argmin(g))
            gaps[k] = dict(gapMm=round(float(g[j]), 2), at=np.round(q[idx[j]], 1).tolist(), arcMm=round(float(s[idx[j]]), 1))
        rows[w] = dict(net=NET[w], ends=ENDS[w], lengthMm=round(float(arclen(p)[-1]), 1), minBendRadius=round(float(K.min_bend_radius(p)), 2),
                       maxAbsY=round(float(np.abs(p[:, 1]).max() + WIRE_R), 2),
                       nearestParts=dict(sorted(gaps.items(), key=lambda kv: kv[1]['gapMm'])[:6]))
    # wire-wire (same-screw pairs compared from 6 mm out)
    ww = {}; ks = list(paths)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b = ks[i], ks[j]
            qa, sa = samples[a]; qb, sb = samples[b]
            if NET[a] == NET[b] and NET[a] in ('p', 'q'):
                qa, qb = qa[sa > 6.0], qb[sb > 6.0]
            d, _ = cKDTree(qb).query(qa); ww[f'{a}|{b}'] = round(float(d.min() - 2 * WIRE_R), 2)
    # existing guide cables (the old pw-* and pi-lead routes are replaced by these wires)
    G = ia_lib.load_guide(); cab = {}
    for c in G['cables']:
        if c['id'] in ('pw-15v', 'pw-15v-link', 'pw-7v', 'pi-lead'):
            continue
        x, _ = spline_samples(c['path']); r = float(c.get('radius') or 0.9); cab[c['id']] = (x, r, cKDTree(x))
    cg = {}
    for w, (q, s) in samples.items():
        row = {}
        for cid, (x, r, tr) in cab.items():
            if np.any(x.max(0) < q.min(0) - 8) or np.any(x.min(0) > q.max(0) + 8):
                continue
            d, ii = tr.query(q); j = int(np.argmin(d)); g = float(d[j] - r - WIRE_R)
            if g < 5:
                row[cid] = dict(gapMm=round(g, 2), at=np.round(q[j], 1).tolist(), cableRadius=r)
        cg[w] = dict(sorted(row.items(), key=lambda kv: kv[1]['gapMm']))
    # reference: the current pi-lead against the same cables between the notch and the bundle point
    pl = np.array([c for c in G['cables'] if c['id'] == 'pi-lead'][0]['path'], float)
    xs, _ = spline_samples(pl); sel = (xs[:, 0] > -27) & (xs[:, 0] < -5) & (xs[:, 2] > 33)
    ref = {}
    for cid, (x, r, tr) in cab.items():
        d, _ = tr.query(xs[sel]); ref[cid] = round(float(d.min() - r - 0.9), 2)
    ref = dict(sorted(ref.items(), key=lambda kv: kv[1])[:6])
    # pi lead beyond the bundle point (current guide route)
    i0 = int(np.argmin(np.linalg.norm(pl - JOIN, axis=1)))
    beyond5 = float(arclen(pl[i0:])[-1])
    out = dict(method=__doc__, boxParts='frame_hidden_noP1 (this folder) + lid_hidden + screw_hidden (layout-F-ear-20261014/options)',
               perWire=rows, wireWireGapMm=dict(sorted(ww.items(), key=lambda kv: kv[1])), existingCableGapsMm=cg,
               currentPiLeadVsCablesNotchToBundleMm=ref,
               piLeadBeyondJoinMm=round(beyond5, 1), joinPoint=JOIN.tolist(),
               note='gaps exclude 1.6 mm inside each terminal clamp (2.0 at J4); negative = tube overlap')
    (HERE / 'routes_outside.json').write_text(json.dumps(out, indent=1) + '\n')
    with open(HERE / 'wires_F.json', 'w') as f:
        json.dump({k: dict(points=np.round(p, 3).tolist(), net=NET[k]) for k, p in paths.items()}, f, indent=1)
    for w, r in rows.items():
        print(w, r['lengthMm'], 'bend', r['minBendRadius'], {k: v['gapMm'] for k, v in list(r['nearestParts'].items())[:5]})
    print('wire-wire', list(out['wireWireGapMm'].items())[:6])
    for w, r in cg.items():
        print('cables', w, {k: v['gapMm'] for k, v in list(r.items())[:5]})
    print('ref pi-lead', ref, 'beyond', round(beyond5, 1))


if __name__ == '__main__' and len(sys.argv) == 1:
    main()


def hook_margins():
    """gap of the two 15 V feed wires to the hidden-option cap hook tab (x -60.3..-57.4, z -21.26..-20.06 at the top edge of
    the 5991 terminal window) and to the frame around the tab notch, exact closest point on the cropped meshes."""
    W = json.loads((HERE / 'wires_F.json').read_text())
    lid = trimesh.load(str(OPT / 'lid_hidden-world.stl'), force='mesh'); fr = trimesh.load(str(HERE / 'frame_hidden_noP1-world.stl'), force='mesh')
    def crop(m, lo, hi):
        c = m.triangles_center; keep = np.all((c >= lo) & (c <= hi), axis=1)
        return m.submesh([np.flatnonzero(keep)], append=True)
    tab = crop(lid, [-61.0, -17.5, -22.0], [-56.5, -13.0, -19.0])
    notch = crop(fr, [-61.5, -17.5, -22.5], [-56.0, -13.0, -18.5])
    out = {}
    for k in ('15V_feed_p', '15V_feed_q'):
        q, s = resample(np.array(W[k]['points'])); q = q[(s > 1.6) & (s < s[-1] - 1.6)]
        out[k] = {}
        for nm, m in (('capHookTab', tab), ('frameAroundTabNotch', notch)):
            _, d, _ = trimesh.proximity.closest_point(m, q); j = int(np.argmin(d))
            out[k][nm] = dict(gapMm=round(float(d[j] - WIRE_R), 2), at=np.round(q[j], 2).tolist())
    out['tabBounds'] = np.round(tab.bounds, 2).tolist(); out['frameCropBounds'] = np.round(notch.bounds, 2).tolist()
    d = json.loads((HERE / 'routes_outside.json').read_text()); d['hookTabMargins'] = out
    (HERE / 'routes_outside.json').write_text(json.dumps(d, indent=1) + '\n'); print(json.dumps(out))


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'hook':
    hook_margins()
