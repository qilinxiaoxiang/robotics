"""Wire routes for the drop-in notch option (Shawn 2026-10-14: wires drop into the pack where the shell top meets the
box; no wire over the roof). World frame (guide), mm. 22 AWG, tube dia 1.8, centreline bend radius 3 (shellkit.fillet_path).
- 15 V link and feed (-y side): unchanged from route_outside.py (window to window outside the -y wall).
- 7 V and 5 V (+y side): out of the OUT windows, up the outside of the +y wall at y 34.0 in four x columns, over the
  top edge, inward across the box top at centreline z 45.0 to their lane y, forward to x -50.8, down through notch A
  (top-wall front edge, x -49.3..-47.0) into the box front cavity at x -47.8 (in front of the top board's pin face
  x -49.65, behind the box front plane), down to z 33, forward under the shell lip through notch B (cover-plate top edge,
  floor z 28.5) at centreline z 30.0, into the pack on the cover lip (top z 28.5).
  Lanes (y): 7V_a 4.4, 7V_b 6.5, 5V_a 8.6, 5V_b 10.7 (pitch 2.1, 0.3 between tubes). The column nearest the box front
  turns inward last (largest y) so no two wires cross on the box top.
  7 V (inner lanes): along the cover lip to x -36.5, down to OpenRB J4 (-31.5, +-1.25, 25.4) as the guide's pw-7v (via (-33, y, 26.8)).
  5 V (outer lanes): along the cover lip under the shell roof rib (bottom z 31.5..32, x -41.5..-34.5) to x -34.5 / -33, up in
  front of the rib and over the (by then lower) 7 V to the head-notch slots (5V_a y 1.9 z 35.3, 5V_b y 1.5 z 37.6), out
  through the pack plate's head notch and up to the neck bundle point
  (-6, -14, 43.5) of the current pi-lead route (via its (-16, 3, 41) waypoint), which it follows to the Pi.
Writes wires_F.json (format of layout-F/wires_F.json) and routes_notch.json (lengths, clearances, cut lengths)."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree
HERE = Path(__file__).resolve().parent; BP = HERE.parent
sys.path.insert(0, str(BP / 'layout-D-20261014')); import shellkit as K
IA = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit')
sys.path.insert(0, str(IA)); import ia_lib
from cables import spline_samples
import route_outside as RO
OPT = BP / 'layout-F-ear-20261014' / 'options'
WIRE_R, BEND = 0.9, 3.0
XE, YE, YI, ZTOP = RO.XE, RO.YE, RO.YI, RO.ZTOP
COL = {'7V_a': -63.3, '7V_b': -60.9, '5V_a': -51.4, '5V_b': -47.8}   # +y wall columns (x); 7 V go back from the top window, 5 V forward from the middle one
LANE = {'7V_a': 4.4, '7V_b': 6.5, '5V_a': 8.6, '5V_b': 10.7}       # lanes on the box top / through the notches: the front column turns inward last
XTURN = -50.8                                            # start of the bend down (arc centre x -50.8 + 3 = -47.8)
XLEG = -47.8                                             # vertical leg in the box front cavity
ZLIP = 30.0                                              # centreline under the shell lip / on the cover lip
SLOT = {'5V_a': (1.9, 35.3), '5V_b': (1.5, 37.6)}        # head-notch slots (the ones the old pi-lead / pw-7v left free)
J4Y = {'7V_a': 1.25, '7V_b': -1.25}
JOIN = RO.JOIN; T1 = np.array([-16.0, 3.0, 41.0])        # current pi-lead waypoints after the notch


def wires():
    g = RO.wires()                                       # -y side as before; +y side replaced below
    # +y wall columns (x) and exits (z): the wire that leaves lower never crosses the one that leaves higher
    z0 = {'7V_a': 25.7, '7V_b': 30.7, '5V_a': 2.1, '5V_b': -2.9}
    for k, x in COL.items():
        y = LANE[k]
        w = [(XE, YE, z0[k]), (XE, YI, z0[k])]
        if abs(x - XE) > 6.0 - 1e-6:
            w.append((x, YI, z0[k]))
        elif abs(x - XE) > 1e-6:                          # forward run shorter than two 3 mm fillets: 45 deg diagonal up
            w.append((x, YI, z0[k] + abs(x - XE)))
        w.append((x, YI, ZTOP))
        if abs(x - XLEG) < 1e-6:                          # front column: bend down in the y-z plane straight into the notch
            w += [(XLEG, y, ZTOP)]
        elif XLEG - x < 6.0:                             # short forward run: 40 deg diagonal instead of two 90 deg turns
            w += [(x, y + 3.0, ZTOP), (XLEG, y, ZTOP)]
        else:
            w += [(x, y, ZTOP), (XLEG, y, ZTOP)]
        w += [(XLEG, y, ZLIP)]
        g[k] = w
    # inside the pack: 7 V (inner lanes) straight down to J4; 5 V (outer lanes) along the cover lip under the shell roof rib
    # (bottom z 31.5..32 at x -41.5..-34.5), then up in front of the rib to the head-notch slots, over the 7 V
    # 7V_a (inner lane) drops first to J4 +y; 7V_b stays at z 30 to x -33.8, crosses over it and drops to J4 -y
    g['7V_a'] += [(-36.5, LANE['7V_a'], ZLIP), (-35.0, J4Y['7V_a'], 27.6), (-31.5, J4Y['7V_a'], 25.4)]
    g['7V_b'] += [(-34.0, LANE['7V_b'], ZLIP), (-33.3, J4Y['7V_b'], 28.4), (-31.5, J4Y['7V_b'], 25.4)]
    d = JOIN[:2] - T1[:2]; d = d / np.linalg.norm(d); nrm = np.array([-d[1], d[0]])
    rise = {'5V_a': [(-34.5, LANE['5V_a'], ZLIP), (-31.5, 1.9, 35.0), (-22.0, 1.9, 35.3), (-18.5, 2.3, 35.5), (-13.5, 2.9, 38.6)],
            '5V_b': [(-33.0, LANE['5V_b'], ZLIP), (-30.5, 4.5, 37.2), (-26.0, 1.5, 37.6), (-22.0, 1.5, 37.6), (-18.5, 1.8, 37.8), (-15.5, 3.3, 42.2)]}
    for k, s in (('5V_a', -1.2), ('5V_b', 1.2)):           # side by side into the bundle point: 1.2 across, 0.6 up/down
        e = JOIN[:2] + s * nrm
        g[k] += rise[k] + [(float(e[0]), float(e[1]), JOIN[2] + s * 0.5)]
    return g


def main():
    WP = wires(); paths = {k: np.asarray(K.fillet_path(w, BEND, n=10)) for k, w in WP.items()}
    man = ia_lib.manifest(); parts = {}
    for k, rec in man.items():
        if k in ('rear_frame', 'rear_lid'):
            continue
        parts[k] = np.array(rec['bounds'])
    extra = {'frame_notch': HERE / 'frame_hidden_noP1_notch-world.stl', 'lid_hidden': OPT / 'lid_hidden-world.stl', 'screw_hidden': OPT / 'screw_hidden-world.stl'}
    cache = {}
    def mesh(k):
        if k not in cache:
            cache[k] = trimesh.load(str(extra[k]), force='mesh') if k in extra else trimesh.Trimesh(*ia_lib.load_solid(k), process=False)
        return cache[k]
    for k in extra:
        parts[k] = np.array(mesh(k).bounds)
    rows = {}; samples = {}
    for w, p in paths.items():
        q, s = RO.resample(p); L = RO.arclen(p)[-1]
        keep = (s > 1.6) & (s < L - (2.0 if RO.ENDS[w][1] == 'J4' else (0.5 if RO.ENDS[w][1] == 'bundle' else 1.6)))
        q, s = q[keep], s[keep]; samples[w] = (q, s); gaps = {}
        lo, hi = q.min(0) - 3, q.max(0) + 3
        for k, b in parts.items():
            if np.any(b[1] < lo) or np.any(b[0] > hi):
                continue
            near = np.all((q >= b[0] - 3) & (q <= b[1] + 3), axis=1)
            if not near.any():
                continue
            m = mesh(k); idx = np.flatnonzero(near); sd = np.empty(len(idx))
            for i in range(0, len(idx), 256):
                sd[i:i + 256] = trimesh.proximity.signed_distance(m, q[idx[i:i + 256]])
            d = -sd - WIRE_R; j = int(np.argmin(d))
            if d[j] < 5.0:
                gaps[k] = dict(gapMm=round(float(d[j]), 2), at=np.round(q[idx[j]], 1).tolist(), arcMm=round(float(s[idx[j]]), 1))
        rows[w] = dict(net=RO.NET[w], ends=list(RO.ENDS[w]), lengthMm=round(float(L), 1), minBendRadius=round(float(K.min_bend_radius(p)), 2),
                       nearestParts=dict(sorted(gaps.items(), key=lambda kv: kv[1]['gapMm'])[:7]))
    ww = {}; ks = list(paths)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b = ks[i], ks[j]; qa, sa = samples[a]; qb, sb = samples[b]
            if RO.NET[a] == RO.NET[b] and RO.NET[a] in ('p', 'q'):
                qa, qb = qa[sa > 6.0], qb[sb > 6.0]
            d, _ = cKDTree(qb).query(qa); ww[f'{a}|{b}'] = round(float(d.min() - 2 * WIRE_R), 2)
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
    pl = np.array([c for c in G['cables'] if c['id'] == 'pi-lead'][0]['path'], float)
    xs, _ = spline_samples(pl); sel = (xs[:, 0] > -36) & (xs[:, 0] < -5) & (xs[:, 2] > 26)
    ref = {}
    for cid, (x, r, tr) in cab.items():
        dd, _ = tr.query(xs[sel]); ref[cid] = round(float(dd.min() - r - 0.9), 2)
    ref = dict(sorted(ref.items(), key=lambda kv: kv[1])[:6])
    i0 = int(np.argmin(np.linalg.norm(pl - JOIN, axis=1))); beyond = float(RO.arclen(pl[i0:])[-1])
    # cut lengths (guide rule): longer wire of the pair + 15 per screw-terminal end, up to 5; pi lead: box part + beyond + 15 + 45 slack
    L = {k: rows[k]['lengthMm'] for k in rows}
    up5 = lambda v: int(np.ceil(v / 5.0) * 5)
    cut = {'pw-15v': up5(max(L['15V_feed_p'], L['15V_feed_q']) + 30), 'pw-15v-link': up5(max(L['15V_link_p'], L['15V_link_q']) + 30),
           'pw-7v': up5(max(L['7V_a'], L['7V_b']) + 30), 'pi-lead': up5(max(L['5V_a'], L['5V_b']) + beyond + 15 + 45)}
    out = dict(method=__doc__, boxParts='frame_hidden_noP1_notch (this folder) + lid_hidden + screw_hidden (layout-F-ear-20261014/options)',
               lanesY=LANE, notchSlots=SLOT, perWire=rows, wireWireGapMm=dict(sorted(ww.items(), key=lambda kv: kv[1])), existingCableGapsMm=cg,
               piLeadBeyondJoinMm=round(beyond, 1), joinPoint=JOIN.tolist(), cutMm=cut, currentPiLeadVsCablesPackToBundleMm=ref,
               note='gaps are tube surface to part surface, excluding 1.6 mm inside each terminal clamp (2.0 at J4); negative = overlap')
    (HERE / 'routes_notch.json').write_text(json.dumps(out, indent=1) + '\n')
    with open(HERE / 'wires_F.json', 'w') as f:
        json.dump({k: dict(points=np.round(p, 3).tolist(), net=RO.NET[k]) for k, p in paths.items()}, f, indent=1)
    for w, r in rows.items():
        print(w, r['lengthMm'], 'bend', r['minBendRadius'], {k: (v['gapMm'], v['at']) for k, v in list(r['nearestParts'].items())[:5]})
    print('wire-wire', list(out['wireWireGapMm'].items())[:8])
    for w, r in cg.items():
        print('cables', w, {k: v['gapMm'] for k, v in list(r.items())[:5]})
    print('ref pi-lead vs cables', ref)
    print('cut', cut, 'beyond', round(beyond, 1))


if __name__ == '__main__':
    main()
