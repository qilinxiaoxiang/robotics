"""V2.0 source: the head's seven M2.5 screws become M2, and the M2.6 x 6 check for the parts already printed.

Shawn, 2026-10-13: M2.5 is hard to find; M2.6 is on hand from the OMX kits; M2 is best because the rest of the robot uses it.
Printed parts that need a change go into V2.0.

The seven screws (fasteners.json): H-jaw_support-01..04 (down through the jaw support base plate, -03 also through the head
wire clip tab, into the yellow lower head shell) and K-head_close-01..03 (up through a lower-shell tab into an orange cap
boss). Every one is vertical.

(A) Printed parts, no reprint: M2.6 x 6 TAP in all seven. Measures thread engagement at r = 0.45 d, the narrowest through
    hole, head overlap with every final-pose part and the tip against the pilot bottom.
(B) V2.0 head_bottom and head_cap: each of the seven pilots is filled (dia 2.4, cut to the part's own local convex hull) and
    re-cut at dia 1.6 over the same span (a blind pilot stops 0.3 mm short of its old bottom), so M2 self-taps. The 2.8 mm entry chamfers stay. No other change; the through
    holes in the jaw support, the clip tab and the lower-shell tabs stay (2.6-2.8 mm, clearance for M2).
    Screws: M2 x 6 at the three bare jaw-support holes, M2 x 8 through the clip tab and at the three cap closures.
Writes head_bottom_v20-world.stl, head_cap_v20-world.stl and v20-head-m2.json here. Run under the bounded CAD runner.
"""
import sys, json, hashlib, time
from pathlib import Path
import numpy as np
import trimesh
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P  # noqa: E402
import ia_lib  # noqa: E402

t0 = time.time()
G = HERE.parent.parent
fast = {f['id']: f for f in json.load(open(G / 'content' / 'fasteners.json'))['screws']}
data = json.load(open(G / 'data' / 'guide-data.json'))
man = ia_lib.manifest()
IDS = ['H-jaw_support-01', 'H-jaw_support-02', 'H-jaw_support-03', 'H-jaw_support-04',
       'K-head_close-01', 'K-head_close-02', 'K-head_close-03']
M2_LEN = {'H-jaw_support-01': 6.0, 'H-jaw_support-02': 6.0, 'H-jaw_support-03': 8.0, 'H-jaw_support-04': 6.0,
          'K-head_close-01': 8.0, 'K-head_close-02': 8.0, 'K-head_close-03': 8.0}
HEAD = {'M2': (4.0, 1.5), 'M2.6': (4.5, 1.8)}          # fasteners.json conventions.headDimensions
LEAD = 0.3
FILL_R, PILOT_R = 1.2, 0.8
KEYS = ('head_bottom', 'head_cap')
res = {'inputs': {k: dict(path=str(ia_lib.solid_path(k)), source=man[k].get('source'),
                          sha256=hashlib.sha256(ia_lib.solid_path(k).read_bytes()).hexdigest(),
                          volumeMm3=round(float(P.solid_mesh(k).volume), 2)) for k in KEYS}}
present = set()
for s in data['steps']:
    present |= set(s.get('show', [])) | set(s.get('add', []))
present -= set(P.RETIRED)
present = sorted(k for k in present if k in man)
ANG = np.linspace(0, 2 * np.pi, 16, endpoint=False)


def ring(c, r):
    return np.array([c + np.array([r * np.cos(a), r * np.sin(a), 0.0]) for a in ANG])


def solid_len(mesh, c, a, r, t_from, t_to, step=0.02):
    """Median over 16 rays at radius r of the solid length of `mesh` between t_from and t_to along a from c."""
    ts = np.arange(t_from, t_to, step)
    lens = []
    for p0 in ring(c, r):
        pts = p0[None, :] + ts[:, None] * a[None, :]
        lens.append(float(mesh.contains(pts).sum()) * step)
    return float(np.median(lens))


def hole_span(mesh, c, a, t_max=16.0, step=0.02):
    """Contiguous span along the axis where the axis is void and the r 1.4 ring is solid (the pilot below the chamfer)."""
    ts = np.arange(0.0, t_max, step)
    axis_in = mesh.contains(c[None, :] + ts[:, None] * a[None, :])
    ring_in = np.ones_like(axis_in)
    for p0 in ring(c, 1.4):
        ring_in &= mesh.contains(p0[None, :] + ts[:, None] * a[None, :])
    ok = (~axis_in) & ring_in
    idx = np.flatnonzero(ok)
    i0 = idx[0]; i1 = i0
    while i1 + 1 < len(ok) and ok[i1 + 1]:
        i1 += 1
    # what follows the span on the axis: solid (blind hole) or void (open past the boss)
    after = 'blind' if i1 + 1 < len(ts) and axis_in[i1 + 1] else 'open'
    # entry: first t where any ring point at r 1.4 meets the part (top of the chamfer)
    any_in = np.zeros_like(axis_in)
    for p0 in ring(c, 1.4):
        any_in |= mesh.contains(p0[None, :] + ts[:, None] * a[None, :])
    entry = float(ts[np.flatnonzero(any_in)[0]])
    return float(ts[i0]), float(ts[i1]), after, entry


def min_void_dia(mesh, c, a, t_from, t_to):
    """Largest dia (0.05 mm steps) whose 16-point ring stays void over the span: the narrowest point of a through hole."""
    ts = np.arange(t_from + 0.05, t_to - 0.05, 0.05)
    best = 0.0
    for r in np.arange(0.5, 1.6, 0.025):
        hit = False
        for p0 in ring(c, r):
            if mesh.contains(p0[None, :] + ts[:, None] * a[None, :]).any():
                hit = True; break
        if hit:
            break
        best = 2 * r
    return round(best, 2)


def overlaps(solid, skip=()):
    b = P.from_m(solid).bounds
    out = {}
    for k in present:
        if k in skip:
            continue
        bb = np.array(man[k]['bounds'])
        if np.any(bb[0] > b[1] + 0.5) or np.any(bb[1] < b[0] - 0.5):
            continue
        v = float((solid ^ P.solid_m(k)).volume())
        if v > 1e-4:
            out[k] = round(v, 4)
    return out


def head_solid(c, a, d, h):
    z0, z1 = (c[2], c[2] + h) if a[2] < 0 else (c[2] - h, c[2])   # the head stands behind the seat, against the travel
    return P.cyl_z(d / 2, z0, z1, c[0], c[1])


meshes = {k: P.solid_mesh(k) for k in KEYS}
solids = {k: P.mesh_to_m(meshes[k]) for k in KEYS}
fills = {k: [] for k in KEYS}
cuts = {k: [] for k in KEYS}
res['screws'] = {}
for sid in IDS:
    f = fast[sid]
    c = np.array(f['center'], float); a = np.array(f['axis'], float)
    into = f['intoPart']; mesh = meshes[into]
    t_lo, t_hi, after, entry = hole_span(mesh, c, a)
    row = dict(intoPart=into, throughParts=f['throughParts'], center=f['center'], axis=f['axis'], currentSpec=f['spec'],
               pilotSpanFromSeatMm=[round(t_lo, 2), round(t_hi, 2)], pastPilot=after, chamferTopFromSeatMm=round(entry, 2),
               pilotDiaPrinted=f['pilotDiameterRangeMm'])
    # through holes, measured on each through part over its own span
    th = {}
    for k in f['throughParts']:
        tm = P.solid_mesh(k)
        ts = np.arange(-1.0, 10.0, 0.02)
        hit = np.zeros(len(ts), bool)
        for p0 in ring(c, 1.6):
            hit |= tm.contains(p0[None, :] + ts[:, None] * a[None, :])
        span = ts[hit]
        th[k] = dict(spanFromSeatMm=[round(float(span.min()), 2), round(float(span.max()), 2)],
                     minHoleDiaMm=min_void_dia(tm, c, a, float(span.min()), float(span.max())))
    row['throughHoles'] = th
    # (A) M2.6 x 6 in the printed parts
    L = 6.0
    eng = solid_len(mesh, c, a, 0.45 * 2.6, 0.0, L) - LEAD
    hd, hh = HEAD['M2.6']
    row['M2.6x6_printed'] = dict(engagementMm=round(eng, 2), tipToPilotEndMm=round(t_hi - L, 2) if after == 'blind' else f'pilot {after} past the tip',
                                 throughHoleVsScrew={k: round(v['minHoleDiaMm'] - 2.6, 2) for k, v in th.items()},
                                 headOverlapMm3=overlaps(head_solid(c, a, hd, hh)))
    # (B) M2 in the V2.0 pilot
    zz = sorted([(c + a * (t_lo - 0.02))[2], (c + a * (t_hi + 0.02))[2]])
    box = P.box([c[0] - 3.5, c[1] - 3.5, zz[0] - 0.5], [c[0] + 3.5, c[1] + 3.5, zz[1] + 0.5])
    hull = P.mesh_to_m(P.from_m(solids[into] ^ box).convex_hull)
    fills[into].append(P.cyl_z(FILL_R, zz[0], zz[1], c[0], c[1]) ^ hull)
    pz = sorted([(c + a * (entry - 0.5))[2], (c + a * (t_hi + (0.5 if after == 'open' else -0.3)))[2]])
    cuts[into].append(P.cyl_z(PILOT_R, pz[0], pz[1], c[0], c[1]))
    row['_m2'] = dict(length=M2_LEN[sid])
    res['screws'][sid] = row
    print(sid, json.dumps(row, default=str), flush=True)

new = {}
for k in KEYS:
    new[k] = (solids[k] + P.union(fills[k])) - P.union(cuts[k])
new_mesh = {k: P.from_m(new[k]) for k in KEYS}

for sid in IDS:
    row = res['screws'][sid]; f = fast[sid]
    c = np.array(f['center'], float); a = np.array(f['axis'], float)
    mesh = new_mesh[row['intoPart']]
    L = row.pop('_m2')['length']
    eng = solid_len(mesh, c, a, 0.45 * 2.0, 0.0, L) - LEAD
    # pilot void on the axis just past the tip, and the dia of the new pilot at mid-depth
    tip_void = not bool(mesh.contains([c + a * (L + 0.2)])[0])
    mid = row['pilotSpanFromSeatMm'][0] + 1.5
    pil = min_void_dia(mesh, c, a, mid - 0.5, mid + 0.5)
    hd, hh = HEAD['M2']
    row['M2_v20'] = dict(spec=f'M2 x {L:g} TAP', engagementMm=round(eng, 2), pilotDiaMm=pil, voidPastTip=tip_void,
                         throughHoleVsScrew={k: round(v['minHoleDiaMm'] - 2.0, 2) for k, v in row['throughHoles'].items()},
                         headOverlapMm3=overlaps(head_solid(c, a, hd, hh)))
    print(sid, 'M2', row['M2_v20'], flush=True)

res['changeOnly'] = {}
for k in KEYS:
    added = new[k] - solids[k]; removed = solids[k] - new[k]
    ab = P.from_m(added).bounds
    res['changeOnly'][k] = dict(addedMm3=round(float(added.volume()), 3), removedMm3=round(float(removed.volume()), 3),
                                addedVsOtherParts=overlaps(added, skip=(k,)),
                                addedOutsideOldBoundsMm=round(float(max(0.0, (meshes[k].bounds[0] - ab[0]).max(), (ab[1] - meshes[k].bounds[1]).max())), 3))

out = {}
for k in KEYS:
    mesh = P.clean_mesh(new[k])
    name = f'{k}_v20-world.stl'
    mesh.export(HERE / name)
    out[name] = dict(sha256=hashlib.sha256((HERE / name).read_bytes()).hexdigest(), tris=int(len(mesh.faces)),
                     watertight=bool(mesh.is_watertight), bodies=int(len(mesh.split(only_watertight=False))),
                     volumeMm3=round(float(new[k].volume()), 2), genus=int(new[k].genus()),
                     printedGenus=int(solids[k].genus()))
res['outputs'] = out
res['elapsed_s'] = round(time.time() - t0, 1)
P.jdump(res, HERE / 'v20-head-m2.json')
print(json.dumps({k: res[k] for k in ('outputs', 'changeOnly', 'elapsed_s')}, indent=1, default=str))
