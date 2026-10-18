"""V1.17 native review for one White plate slice (pipeline v2): release-V1.12/scripts/review_v112.py with the cap key set to the A7Z
cap (head_cap_a7z) and the plate's six objects (cap, two shells, two thighs, A7Z face). Every check is the V1.12 one; the face
is covered by the per-part first-layer and brim checks. Read-only on all inputs; writes review/White_<Machine>-review.json.

    /tmp/microduck-cad-venv/bin/python scripts/review_v117.py <run-dir> White Bambu

Checks (PLAN-V1.12.md C4 "What the next slice must show"):
- objects and bed: six objects, extrusion inside the bed (release_pipeline_v2.first_layer);
- first layer: every part's first-layer model area >= 0.8 x its manifest flat contact (cap: about 104 mm2 on the crown strip);
- brim per object: release_pipeline_v2.brim_review against the per-part plan (brim on the cap only);
- support settings readback from the sliced config: 3 interface layers, 0.15 mm interface spacing, 0.2 mm top z gap,
  support ironing on (Bambu enable_support_ironing, Elegoo support_ironing);
- cap posts and pilots: the seat_support.py zones (orientation-study/scripts) for the cap on this plate: support under
  down-facing hole ends (hole radius + 2 mm, 1.5 mm below), under down-facing boss faces (radius + 1 mm), and inside hole cores.
  Holes are split by role: screw pilots (a fasteners.json screw into or through the cap on the hole axis), the speaker grille
  (sound holes in the slot box, whose down end is the supported outer crown) and other holes. Required: 0 mm under boss faces,
  0 mm under and inside pilots and other holes, 0 mm inside grille hole cores;
- cap crown map (PLAN C1 method): the topmost support-interface point of each 0.5 mm cell is cast up to the cap; a hit within
  1 mm whose downward ray leaves the cap is outer skin on interface, otherwise inside the cap. Hits are mapped back to the robot
  frame. The same is done for the support ironing toolpaths. In the sound-slot region above the speaker (robot x -11.6..18.1,
  |y| < 10, z 146.8..151.2) the review reports interface area, the share of interface cells that also carry an ironing pass,
  and the interface cells that lie under a roof opening (a sound hole, found by casting robot -z rays onto the cap).
"""
import sys, json, re, math
from pathlib import Path
import numpy as np
import trimesh
sys.dont_write_bytecode = True
PRINT = Path(__file__).resolve().parents[2]
SIM = PRINT.parents[1]
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
sys.path.insert(0, str(PRINT / 'release-V1.6-final/scripts'))
sys.path.insert(0, str(PRINT / 'orientation-study'))
import release_pipeline_v2 as r2  # noqa: E402
import review_final as rf  # noqa: E402  (grams parser shared with the V1.6 to V1.11 reviews)
from orientation_check import detect_holes, load_mesh  # noqa: E402

CAP = 'head_cap_a7z'
SLOT = dict(x=(-11.6, 18.1), yAbs=10.0, z=(146.8, 151.2))
WANT = {'support_interface_top_layers': '3', 'support_interface_spacing': '0.15', 'support_top_z_distance': '0.2'}
IRON = {'Bambu': 'enable_support_ironing', 'Elegoo': 'support_ironing'}
CELL = 0.5


def val(cfg, k):
    v = cfg.get(k)
    return v[0] if isinstance(v, list) and len(v) == 1 else v


def segments(g, offset):
    """Extruding XY moves: (x0, y0, x1, y1, z, kind) with the Bambu extruder offset applied."""
    kind, xyz, out, relative, e = '', [0.0, 0.0, 0.0], [], True, 0.0
    for line in g.decode(errors='replace').splitlines():
        if line.startswith(('; FEATURE:', ';TYPE:')):
            kind = line.split(':', 1)[1].strip(); continue
        if line.startswith('M82'): relative = False
        elif line.startswith('M83'): relative = True
        if line.startswith('G92 '):
            m = re.search(r'E([-+\d.]+)', line)
            if m: e = float(m[1])
        if not re.match(r'^G[0123] ', line): continue
        v = {k: float(t) for k, t in re.findall(r'([XYZE])([-+]?\d*\.?\d+)', line.split(';')[0])}
        end = [v.get(k, xyz[i]) for i, k in enumerate('XYZ')]
        de = v.get('E', 0.0) if relative else v.get('E', e) - e
        if 'E' in v: e = e + v['E'] if relative else v['E']
        if de > 0 and end[:2] != xyz[:2]:
            out.append((xyz[0] + offset[0], xyz[1] + offset[1], end[0] + offset[0], end[1] + offset[1], end[2], kind))
        xyz = end
    return out


def raster(segs, step=0.4):
    pts = []
    for a, b, c, d, z in segs:
        n = max(1, int(math.hypot(c - a, d - b) / step)); t = (np.arange(n) + 0.5) / n
        pts.append(np.c_[a + (c - a) * t, b + (d - b) * t, np.full(n, z)])
    return np.vstack(pts) if pts else np.zeros((0, 3))


def top_cells(P):
    if not len(P): return P, np.zeros(0, np.int64)
    cell = np.floor(P[:, :2] / CELL).astype(np.int64); key = cell[:, 0] * 1000003 + cell[:, 1]
    order = np.lexsort((-P[:, 2], key)); k2 = key[order]; first = np.r_[True, k2[1:] != k2[:-1]]
    return P[order][first], k2[first]


def map_to_cap(P, mesh_p, Tinv):
    """Cast each point up to the cap; keep hits within 1 mm. Returns print hits, robot-frame hits, outer flag, cell keys."""
    top, keys = top_cells(P)
    if not len(top): return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros(0, bool), np.zeros(0, np.int64)
    loc, ri, _ = mesh_p.ray.intersects_location(top + [0, 0, 0.01], np.tile([0, 0, 1.0], (len(top), 1)), multiple_hits=False)
    near = loc[:, 2] - top[ri, 2] < 1.0; loc, ri = loc[near], ri[near]
    outer = ~mesh_p.ray.intersects_any(top[ri] - [0, 0, 0.05], np.tile([0, 0, -1.0], (len(ri), 1)))
    world = (np.c_[loc, np.ones(len(loc))] @ Tinv.T)[:, :3]
    return loc, world, outer, keys[ri]


def in_slot(w):
    return (w[:, 0] >= SLOT['x'][0]) & (w[:, 0] <= SLOT['x'][1]) & (np.abs(w[:, 1]) < SLOT['yAbs']) & (w[:, 2] >= SLOT['z'][0]) & (w[:, 2] <= SLOT['z'][1])


def openings(world_mesh, step=0.25):
    xs = np.arange(SLOT['x'][0], SLOT['x'][1] + 1e-9, step); ys = np.arange(-SLOT['yAbs'], SLOT['yAbs'] + 1e-9, step)
    X, Y = np.meshgrid(xs, ys, indexing='ij'); O = np.c_[X.ravel(), Y.ravel(), np.full(X.size, 170.0)]
    loc, ri, _ = world_mesh.ray.intersects_location(O, np.tile([0, 0, -1.0], (len(O), 1)), multiple_hits=False)
    z = np.full(len(O), -np.inf); z[ri] = loc[:, 2]
    return O[z < SLOT['z'][0] - 6.0][:, :2], step   # nothing of the roof above robot z 140.8: a through opening


def cap_review(prep, row, segs, cfg):
    part = next(p for p in prep['parts'] if p['key'] == CAP); place = next(pl for pl in row['placements'] if pl['key'] == CAP)
    T = np.array(part['sourceToPrint'], float); T[2, 3] += part['dropToBedMm']; T[:3, 3] += np.array(place['translation'], float)
    Tinv = np.linalg.inv(T)
    world_mesh = trimesh.load(part['source']['path'], force='mesh'); mesh_p = world_mesh.copy(); mesh_p.apply_transform(T)
    lo, hi = mesh_p.bounds[0] - [6, 6, 0], mesh_p.bounds[1] + [6, 6, 0]
    own = [s for s in segs if lo[0] <= (s[0] + s[2]) / 2 <= hi[0] and lo[1] <= (s[1] + s[3]) / 2 <= hi[1]]
    kinds = sorted({s[5] for s in own})
    iface = [s[:5] for s in own if s[5].lower() == 'support interface']
    # Bambu labels the support ironing pass 'Support ironing'; OrcaSlicer (Elegoo) labels it 'Ironing'. With top-surface
    # ironing off (ironing_type 'no ironing') every Orca 'Ironing' path is the support ironing pass.
    orca_support_iron = str(val(cfg, 'ironing_type')) == 'no ironing'
    iron = [s[:5] for s in own if s[5].lower() == 'support ironing' or (s[5].lower() == 'ironing' and orca_support_iron)]
    support_all = [s for s in own if 'support' in s[5].lower()]
    # crown map
    res = dict(featureKindsNearCap=kinds, supportInterfaceToolpathMm=round(sum(math.hypot(c - a, d - b) for a, b, c, d, _ in iface), 1),
               supportIroningToolpathMm=round(sum(math.hypot(c - a, d - b) for a, b, c, d, _ in iron), 1))
    loc, w, outer, keys = map_to_cap(raster(iface), mesh_p, Tinv)
    iloc, iw, iouter, ikeys = map_to_cap(raster(iron), mesh_p, Tinv)
    A = CELL * CELL
    def band(m, ww, l):
        return dict(areaMm2=round(float(m.sum()) * A, 1)) | (dict(robotZ=[round(float(ww[m, 2].min()), 2), round(float(ww[m, 2].max()), 2)],
                    robotX=[round(float(ww[m, 0].min()), 1), round(float(ww[m, 0].max()), 1)], robotAbsYMax=round(float(np.abs(ww[m, 1]).max()), 1),
                    printZ=[round(float(l[m, 2].min()), 2), round(float(l[m, 2].max()), 2)]) if m.any() else {})
    res['interfaceOuterSkin'] = band(outer, w, loc); res['interfaceInsideCap'] = band(~outer, w, loc)
    res['ironingOuterSkin'] = band(iouter, iw, iloc)
    iron_keys = set(ikeys[iouter].tolist())
    cov = np.array([k in iron_keys for k in keys[outer]], bool)
    res['ironingCoverOfOuterSkinInterfaceCells'] = round(float(cov.mean()), 3) if len(cov) else None
    s = in_slot(w) & outer
    sc = np.array([k in iron_keys for k in keys[s]], bool)
    opens, step = openings(world_mesh)
    # an interface cell under an opening: its robot-frame point lies within one grid step of an open cell
    if len(opens) and s.any():
        from scipy.spatial import cKDTree
        d, _ = cKDTree(opens).query(w[s][:, :2]); under = d <= step
    else:
        under = np.zeros(int(s.sum()), bool)
    # interface toolpath points (all, not only the topmost) whose robot-frame XY falls inside an opening
    P = raster(iface); Pw = (np.c_[P, np.ones(len(P))] @ Tinv.T)[:, :3] if len(P) else np.zeros((0, 3))
    inslot = (Pw[:, 0] >= SLOT['x'][0]) & (Pw[:, 0] <= SLOT['x'][1]) & (np.abs(Pw[:, 1]) < SLOT['yAbs']) if len(Pw) else np.zeros(0, bool)
    if len(opens) and inslot.any():
        from scipy.spatial import cKDTree
        d2, _ = cKDTree(opens).query(Pw[inslot][:, :2]); span_pts = Pw[inslot][d2 <= step / 2]
    else:
        span_pts = np.zeros((0, 3))
    # one record per opening (connected open cells): does support interface run across it?
    from scipy import ndimage
    from scipy.spatial import cKDTree
    keyed = {(round(x / step), round(y / step)) for x, y in opens}
    if keyed:
        ix = np.array(sorted(keyed)); i0 = ix.min(0); grid = np.zeros(ix.max(0) - i0 + 1, bool); grid[tuple((ix - i0).T)] = True
        lab, n = ndimage.label(grid); per = []
        tree = cKDTree(span_pts[:, :2]) if len(span_pts) else None
        for k in range(1, n + 1):
            cells = (np.argwhere(lab == k) + i0) * step; c = cells.mean(0)
            hit = len(tree.query_ball_point(c, r=max(step, float(np.ptp(cells, 0).max()) / 2 + step))) if tree is not None else 0
            per.append(dict(robotXY=[round(float(c[0]), 1), round(float(c[1]), 1)], areaMm2=round(len(cells) * step * step, 2), interfacePointsInside=int(hit)))
    else:
        per = []
    res['slotOpenings'] = per
    res['slotRegion'] = dict(box=SLOT, roofOpeningAreaMm2=round(len(opens) * step * step, 1), openings=len(per),
                             openingsWithInterfaceAcross=sum(1 for o in per if o['interfacePointsInside'] > 0),
                             interfaceOuterSkinAreaMm2=round(float(s.sum()) * A, 1),
                             ironingCoverOfInterfaceCells=round(float(sc.mean()), 3) if len(sc) else None,
                             interfaceCellsUnderOpenings=int(under.sum()),
                             interfaceToolpathPointsInsideOpenings=int(len(span_pts)),
                             interfaceInsideOpeningsRobotZ=[round(float(span_pts[:, 2].min()), 2), round(float(span_pts[:, 2].max()), 2)] if len(span_pts) else None)
    res['seats'] = seats(part['source']['path'], T, support_all)
    return res


SCREWS = [x for x in json.loads((PRINT.parent / 'content/fasteners.json').read_text())['screws']
          if x.get('intoPart') == 'head_cap' or 'head_cap' in (x.get('throughParts') or [])]


def role(h):
    """pilot: a fasteners.json screw into or through the cap runs along the hole axis (within 1 mm); grille: a hole whose ends
    lie in the sound-slot box; other: anything else."""
    ax = np.asarray(h['axis'], float); c = np.asarray(h['ends'][0]['centre'], float)
    for sc in SCREWS:
        a = np.asarray(sc['axis'], float); a /= np.linalg.norm(a); d = c - np.asarray(sc['center'], float)
        if abs(ax @ a) > 0.9 and np.linalg.norm(d - (d @ a) * a) <= 1.0:
            h['screw'] = sc['id']; return 'pilot'
    if all(SLOT['x'][0] <= e['centre'][0] <= SLOT['x'][1] and abs(e['centre'][1]) < SLOT['yAbs'] for e in h['ends']):
        return 'grille'
    return 'other'


def seats(path, T, segs):
    """orientation-study/scripts/seat_support.py zones, for one part placed on a multi-part plate."""
    S = np.array([((a + c) / 2, (b + d) / 2, z, math.hypot(c - a, d - b)) for a, b, c, d, z, _ in segs]) if segs else np.zeros((0, 4))
    mesh = load_mesh(path); R, t = T[:3, :3], T[:3, 3]; feats = detect_holes(mesh)
    boss_total = 0.0; seen = set(); holes = []; bosses = []
    for h in feats:
        if h['kind'] != 'boss': continue
        ax = R @ h['axis']
        for e in h['ends']:
            c, n = R @ e['centre'] + t, R @ e['normal']
            if n[2] >= -0.7 or c[2] < 0.6 or e['facet'] in seen or not len(S): continue
            seen.add(e['facet']); d = S[:, :3] - c; rad = np.linalg.norm(d - np.outer(d @ ax, ax), axis=1)
            mm = float(S[(rad <= h['r'] + 1.0) & (S[:, 2] <= c[2] + .01) & (S[:, 2] >= c[2] - 1.5), 3].sum()); boss_total += mm
            bosses.append(dict(diameterMm=round(2 * h['r'], 2), zMm=round(float(c[2]), 2), supportUnderFaceMm=round(mm, 1)))
    for h in feats:
        if h['kind'] != 'hole': continue
        ax = R @ h['axis']; ends = [(R @ e['centre'] + t, R @ e['normal']) for e in h['ends']]
        rec = dict(diameterMm=round(2 * h['r'], 2), robotCentre=[round(float(x), 1) for x in h['ends'][0]['centre']], ends=[])
        rl = role(h); rec['screw'] = h.get('screw')
        for c, n in ends:
            state = 'down' if n[2] < -0.7 else 'up' if n[2] > 0.7 else 'side'; mm = 0.0
            if state == 'down' and c[2] > 0.05 and len(S):
                d = S[:, :3] - c; rad = np.linalg.norm(d - np.outer(d @ ax, ax), axis=1)
                mm = float(S[(rad <= h['r'] + 2.0) & (S[:, 2] <= c[2] + .01) & (S[:, 2] >= c[2] - 1.5), 3].sum())
            rec['ends'].append(dict(state=state, printZMm=round(float(c[2]), 2), supportUnderEndMm=round(mm, 1)))
        core = 0.0
        if len(S):
            d = S[:, :3] - ends[0][0]; along = d @ ax; rad = np.linalg.norm(d - np.outer(along, ax), axis=1)
            lo_, hi_ = min(0.0, *[(c - ends[0][0]) @ ax for c, _ in ends]), max(0.0, *[(c - ends[0][0]) @ ax for c, _ in ends])
            if hi_ - lo_ < 0.2: lo_, hi_ = (-3.0, 0.0) if ends[0][1] @ ax > 0 else (0.0, 3.0)
            core = float(S[(rad <= max(h['r'] - .15, .2)) & (along >= lo_) & (along <= hi_), 3].sum())
        rec['supportInCoreMm'] = round(core, 1); rec['role'] = rl; holes.append(rec)
    def tot(rl, f):
        return round(sum(f(h) for h in holes if h['role'] == rl), 1)
    under_end = lambda h: sum(e['supportUnderEndMm'] for e in h['ends'])
    out = dict(downFacingBossFaces=bosses, supportUnderDownBossFacesMm=round(boss_total, 1),
               pilots=dict(holes=sum(1 for h in holes if h['role'] == 'pilot'), screws=sorted({h['screw'] for h in holes if h.get('screw')}),
                           supportUnderDownEndsMm=tot('pilot', under_end), supportInHoleCoresMm=tot('pilot', lambda h: h['supportInCoreMm'])),
               grille=dict(holes=sum(1 for h in holes if h['role'] == 'grille'), supportUnderDownEndsMm=tot('grille', under_end),
                           supportInHoleCoresMm=tot('grille', lambda h: h['supportInCoreMm']),
                           note='Sound holes through the roof above the speaker: their down end is the outer crown skin, which prints on support '
                                'interface by design (PLAN-V1.12.md C1); reported, not a seat.'),
               other=dict(holes=sum(1 for h in holes if h['role'] == 'other'), supportUnderDownEndsMm=tot('other', under_end),
                          supportInHoleCoresMm=tot('other', lambda h: h['supportInCoreMm'])),
               holesWithSupport=[h for h in holes if h['supportInCoreMm'] > 0 or any(e['supportUnderEndMm'] > 0 for e in h['ends'])])
    out['passed'] = bool(boss_total == 0 and out['pilots']['supportUnderDownEndsMm'] == 0 and out['pilots']['supportInHoleCoresMm'] == 0
                         and out['other']['supportUnderDownEndsMm'] == 0 and out['other']['supportInHoleCoresMm'] == 0
                         and out['grille']['supportInHoleCoresMm'] == 0)
    return out


def review(run, color, machine):
    F = Path(run).resolve(); prep = r2.read(F / 'preparation.json')
    row = next(x for x in prep['rows'] if x['color'] == color and x['machine'] == machine); project = r2.bound(row['project'])
    res = r2.read(F / f'native/{color}_{machine}/result.json'); arch = r2.bound(res['archive'])
    g, cfg, _ = r2.native_payload(arch); assert r2.digest(g) == res['gcodeSha256']; r2.check_profile(cfg, machine)
    parts = [p for p in prep['parts'] if p['color'] == color]
    rows, foot = r2.first_layer(g, project, machine); brims = r2.brim_review(rows, parts, machine)
    first = {}
    for p in parts:
        name = f'{p["key"]}_1'; fl = next((x for x in rows if x['name'] == name), None)
        area = round(fl['model_area_mm2'], 2) if fl else None
        first[name] = dict(modelAreaMm2=area, islands=fl['modelIslands'] if fl else None, manifestFlatContactMm2=round(p['flatContactAreaMm2'], 2),
                           rule='first-layer model area >= 0.8 x manifest flat contact', passed=bool(fl and area >= .8 * p['flatContactAreaMm2']))
    settings = {k: val(cfg, k) for k in sorted(set(WANT) | {IRON[machine], 'enable_support_ironing', 'support_ironing', 'support_ironing_flow',
                                                           'support_ironing_spacing', 'support_style', 'support_type', 'support_interface_speed',
                                                           'bridge_speed', 'support_interface_pattern', 'support_threshold_angle'}) if k in cfg}
    settings_ok = all(str(settings.get(k)) == v for k, v in WANT.items()) and str(settings.get(IRON[machine])) == '1'
    off = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0.0, 0.0]
    cap = cap_review(prep, row, segments(g, off), cfg)
    ironing_present = cap['supportIroningToolpathMm'] > 0 and cap['ironingOuterSkin']['areaMm2'] > 0
    nobj = sum(p['quantity'] for p in parts)
    ok = (len(rows) == nobj and foot['insideBed'] and brims['passed'] and all(v['passed'] for v in first.values()) and settings_ok
          and ironing_present and cap['seats']['passed'])
    out = dict(color=color, machine=machine, archive=r2.ref(arch), gcodeSha256=res['gcodeSha256'], pipeline=r2.ref(r2.__file__),
               estimatedSeconds=r2.time_seconds(g, machine), filamentGrams=rf.grams(g, machine), objects=len(rows), objectsExpected=nobj,
               insideBed=foot['insideBed'], minConservativeGapMm=round(min((p['conservativeGapMm'] for p in foot['pairs']), default=0), 2),
               firstLayer=first, brimReview=brims, supportSettings=settings, supportSettingsAsPlanned=bool(settings_ok),
               supportIroningPresentUnderCrown=bool(ironing_present), cap=cap,
               slicerLog=(F / f'native/{color}_{machine}/cli.log').read_text(errors='replace').strip()[-2000:], passed=bool(ok))
    (F.parent / 'review').mkdir(exist_ok=True); r2.write(F.parent / f'review/{color}_{machine}-review.json', out); return out


if __name__ == '__main__':
    o = review(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(dict(machine=o['machine'], passed=o['passed'], secs=o['estimatedSeconds'], grams=o['filamentGrams'], objects=o['objects'],
                          settings=o['supportSettings'], settingsOK=o['supportSettingsAsPlanned'], ironing=o['supportIroningPresentUnderCrown'])))
    for k, v in o['firstLayer'].items(): print('   first layer', k, v)
    for k, v in o['brimReview']['objects'].items(): print('   brim', k, v)
    c = o['cap']; print('   cap kinds', c['featureKindsNearCap'])
    for k in ('supportInterfaceToolpathMm', 'supportIroningToolpathMm', 'interfaceOuterSkin', 'interfaceInsideCap', 'ironingOuterSkin',
              'ironingCoverOfOuterSkinInterfaceCells', 'slotRegion'): print('   cap', k, c[k])
    print('   seats', {k: v for k, v in c['seats'].items() if k not in ('downFacingBossFaces', 'holesWithSupport')})
    for h in c['seats']['holesWithSupport']: print('      hole with support', h)
