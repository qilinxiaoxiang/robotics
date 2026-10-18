"""Checks for layout C (build_rear_plate.py). Exact manifold3d booleans; boards = convex hull of each connected body of the
ROBOTIS mesh; 5991 = box model from the Adafruit board file. Environment = the audit solids (guide rest pose) plus the
V1.8 pack world/rear_pack-v18.stl. Writes checks.json."""
import sys, json, time
from pathlib import Path
import numpy as np, trimesh
import manifold3d as m3
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P
import build_rear_plate as C
import build_rear_pack as BRP
import ia_lib
t0 = time.time()
B = json.loads((HERE / 'build.json').read_text())
fm = P.load_stl(HERE / 'rear_frame-world.stl'); lm = P.load_stl(HERE / 'rear_lid-world.stl')
F = P.mesh_to_m(fm); L = P.mesh_to_m(lm)


def hull_solid(mesh, pcb_box=None):
    """convex hull per connected body; the PCB body (spans > 60 mm) is replaced by pcb_box, the measured board slab at the
    holes (local X -2.0..-0.35): its hull would carry the 0.05 mm pads of the whole board onto the boss seats."""
    parts = []
    for p in mesh.split(only_watertight=False):
        if len(p.vertices) < 4 or np.ptp(p.vertices, axis=0).min() <= 1e-3:
            continue
        if pcb_box is not None and np.ptp(p.vertices, axis=0).max() > 60:
            parts.append(pcb_box); continue
        parts.append(m3.Manifold.hull_points(np.asarray(p.vertices, float)))
    return P.union(parts)


xm = {nm: trimesh.load(str(HERE / f'xl4015_{nm}-world.stl'), force='mesh') for nm in ('left', 'right')}
XL = {nm: hull_solid(m, P.box((C.XL_MID_X - 0.825 - 1.65, *(np.array([B['boards'][nm]['pcbCentre'][1] - 13.1, C.XL_ZC - 30.85])),), (C.XL_PIN_FACE_X, B['boards'][nm]['pcbCentre'][1] + 13.1, C.XL_ZC + 30.85))) for nm, m in xm.items()}
PCBV = {nm: [p.vertices for p in m.split(only_watertight=False) if np.ptp(p.vertices, axis=0).max() > 60][0] for nm, m in xm.items()}
pdm = trimesh.load(str(HERE / 'pd5991-world.stl'), force='mesh'); PD = hull_solid(pdm)
man = ia_lib.manifest()
SKIP = set(P.RETIRED) | set(P.SELF_KEYS) | {'rear_pack_cover'}
V18 = P.mesh_to_m(P.load_stl(P.WORLD / 'rear_pack-v18.stl'))
res = {}
G = lambda a, b, s=10.0: round(float(a.min_gap(b, s)), 3)
O = lambda a, b: round(float((a ^ b).volume()), 3)

# ---------------------------------------------------------------- 1 manifold
res['1_manifold'] = {nm: dict(watertight=bool(m.is_watertight), bodies=int(len(m.split(only_watertight=False))), volumeMm3=round(float(m.volume), 2),
                              genus=int(M.genus()), status=str(M.status())) for nm, m, M in (('frame', fm, F), ('lid', lm, L))}
res['1_manifold']['frameLidOverlapMm3'] = O(F, L); res['1_manifold']['frameLidGapMm'] = G(F, L, 2.0)
res['1_manifold']['pass'] = all(v['watertight'] and v['bodies'] == 1 for k, v in res['1_manifold'].items() if isinstance(v, dict)) and res['1_manifold']['frameLidOverlapMm3'] < 1e-6
print('1', res['1_manifold'], flush=True)

# ---------------------------------------------------------------- 2 fit at rest: every audit solid within 8 mm of the frame or lid, plus the V1.8 pack
rows = []
E = F + L; eb = np.vstack([fm.bounds, lm.bounds]); eb = (eb.min(0), eb.max(0))
for k, rec in sorted(man.items()):
    if k in SKIP:
        continue
    lo, hi = np.array(rec['bounds'])
    if not (np.all(lo - 8 <= eb[1]) and np.all(hi + 8 >= eb[0])):
        continue
    S = P.solid_m(k)
    rows.append(dict(key=k, module=rec.get('module'), frameOverlapMm3=O(F, S), frameGapMm=G(F, S, 8.0), lidOverlapMm3=O(L, S), lidGapMm=G(L, S, 8.0)))
rows.append(dict(key='rear_pack-v18.stl (as built)', frameOverlapMm3=O(F, V18), frameGapMm=G(F, V18, 8.0), lidOverlapMm3=O(L, V18), lidGapMm=G(L, V18, 8.0)))
ORB = P.mesh_to_m(P.openrb_mesh())
rows.append(dict(key='openrb-board-upright', frameOverlapMm3=O(F, ORB), frameGapMm=G(F, ORB, 8.0), lidOverlapMm3=O(L, ORB), lidGapMm=G(L, ORB, 8.0)))
# box part only (behind the plate plane) and the lower web outside the cover outline, against both packs
box_part = F ^ P.box((-70, -40, -50), (C.X_PLATE_IN, 40, 50))
web_out = (F ^ P.box((C.X_PLATE_IN, -40, -50), (C.X_PLATE_OUT, 40, 0))) - P.box((C.X_PLATE_IN - 1, -18.61, -50), (C.X_PLATE_OUT + 1, 18.61, 30))
VP19 = P.solid_m('rear_pack')
res['2_fitAtRest'] = dict(parts=rows, overlaps=[r for r in rows if r['frameOverlapMm3'] > 1e-6 or r['lidOverlapMm3'] > 1e-6],
                          under2mm=[r for r in rows if min(r['frameGapMm'], r['lidGapMm']) < 2.0],
                          boxPartToPack=dict(v18=G(box_part, V18), v19=G(box_part, VP19)), lowerWebOutsideCoverOutlineToPack=dict(v18=G(web_out, V18), v19=G(web_out, VP19)))
res['2_fitAtRest']['pass'] = len(res['2_fitAtRest']['overlaps']) == 0
print('2 overlaps', res['2_fitAtRest']['overlaps'], 'under2', [(r['key'], r['frameGapMm'], r['lidGapMm']) for r in res['2_fitAtRest']['under2mm']], res['2_fitAtRest']['boxPartToPack'], res['2_fitAtRest']['lowerWebOutsideCoverOutlineToPack'], flush=True)

# ---------------------------------------------------------------- 3 boards vs walls, bosses, each other
walls = dict(lid=L, side_plus_y=P.box((C.X_BACK, C.HW - C.T, C.Z0), (C.X_PLATE_IN, C.HW, C.Z1)), side_minus_y=P.box((C.X_BACK, -C.HW, C.Z0), (C.X_PLATE_IN, -C.HW + C.T, C.Z1)),
             top=P.box((C.X_BACK, -C.HW, C.Z1 - C.T), (C.X_PLATE_IN, C.HW, C.Z1)), bottom=P.box((C.X_BACK, -C.HW, C.Z0), (C.X_PLATE_IN, C.HW, C.Z0 + C.T)),
             plate_and_web=F ^ P.box((C.X_PLATE_IN, -40, -50), (-37, 40, 50)), frame_whole=F)
items = dict(xl_left=XL['left'], xl_right=XL['right'], pd5991=PD)
r3 = {a: {w: dict(gapMm=G(S, W, 15.0), overlapMm3=O(S, W)) for w, W in walls.items()} for a, S in items.items()}
r3['xl_left__xl_right'] = dict(gapMm=G(XL['left'], XL['right'], 15.0), overlapMm3=O(XL['left'], XL['right']))
r3['xl_left__pd5991'] = dict(gapMm=G(XL['left'], PD, 15.0), overlapMm3=O(XL['left'], PD))
r3['xl_right__pd5991'] = dict(gapMm=G(XL['right'], PD, 15.0), overlapMm3=O(XL['right'], PD))
r3['pcbVerticesInsideFrame'] = {nm: int(fm.contains(V).sum()) for nm, V in PCBV.items()}
r3['note'] = 'frame_whole gap 0 = the PCB pin face / 5991 back face seated on the bosses (contact by design); overlap must be 0'
r3['pass'] = all(v['frame_whole']['overlapMm3'] < 1e-3 and v['lid']['overlapMm3'] < 1e-6 for k, v in r3.items() if k in items) and all(r3[k]['overlapMm3'] < 1e-6 for k in ('xl_left__xl_right', 'xl_left__pd5991', 'xl_right__pd5991'))
res['3_boardsInBox'] = r3
print('3', json.dumps(r3), flush=True)

# ---------------------------------------------------------------- 4 wire room
r4 = {}
bl = B['boards']
r4['outEntryFaceToTopWallMm'] = round(C.Z1 - C.T - (C.XL_ZC + C.XL_TERM_L['bodyEndY']), 3)
r4['boardTopToTopWallMm'] = round(C.Z1 - C.T - (C.XL_ZC + 30.85), 3)
# OUT pairs inside the box: up out of the terminal, over the board top under the top wall, inward to the centre lane,
# down the lane to the passage height, forward through the front-plate passage into the pack channel (x -45..-37)
pas = B['holes']['wirePassage']; zc = pas['centre'][2]; xe = bl['left']['outEntries'][0][0]; zr = 43.3
PAIR_T, PAIR_W = 1.6, 3.2
J4 = np.array([-30.0, -6.0, 26.0]); NOTCH_BOTTOM = np.array([-20.0, 0.0, 32.7]); NOTCH_CENTRE = np.array([-20.0, 0.0, 35.75])
route = {}
solids = []
for nm in ('left', 'right'):
    e = np.array(bl[nm]['outEntries']); s_ = np.sign(e[0][1]); ym = float(e[:, 1].mean())
    pts = np.array([[xe, ym, e[0][2]], [xe, ym, zr], [xe, 0.0, zr], [xe, 0.0, zc], [C.X_PLATE_OUT, 0.0, zc]])
    L_ = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
    tend = C.XL_ZC + C.XL_TERM_L['bodyEndY']
    rise = P.union([P.box((xe - 0.8, y - 0.8, tend), (xe + 0.8, y + 0.8, zr + 0.8)) for y in e[:, 1]])
    run = P.box((xe - PAIR_W / 2, min(0, s_ * (abs(e[:, 1]).max() + 0.8)), zr - 0.8), (xe + PAIR_W / 2, max(0, s_ * (abs(e[:, 1]).max() + 0.8)), zr + 0.8))
    lane_ = P.box((xe - PAIR_W / 2, min(0, s_ * PAIR_T), zc - PAIR_W / 2), (xe + PAIR_W / 2, max(0, s_ * PAIR_T), zr + 0.8))
    solids += [rise, run, lane_]
    route[nm] = dict(role=bl[nm]['role'], entries=bl[nm]['outEntries'], polyline=np.round(pts, 3).tolist(), pathLengthToPassageMm=round(L_, 1),
                     straightLineEntryToPassageCentreMm=round(float(np.linalg.norm(np.array([xe, ym, e[0][2]]) - np.array(pas['centre']))), 1))
fwd = P.box((xe - PAIR_W / 2, -PAIR_W / 2, zc - PAIR_T), (C.X_PLATE_OUT, PAIR_W / 2, zc + PAIR_T))     # both pairs stacked: 3.2 (y) x 3.2 (z)
chan = P.box((C.X_PLATE_OUT, -PAIR_W / 2, zc - PAIR_T), (-37.0, PAIR_W / 2, zc + PAIR_T))
inbox = P.union(solids + [fwd])
pc = np.array([C.X_PLATE_OUT, 0.0, zc])
r4['outRoute'] = dict(
    rule='OUT pairs: up from the terminal (end z %.2f), over the board top at z %.1f (room z %.1f..%.1f), inward to y 0, down the centre lane (|y| <= 4.1) to z %.1f, forward through the passage' % (C.XL_ZC + C.XL_TERM_L['bodyEndY'], zr, C.XL_ZC + 30.85, C.Z1 - C.T, zc),
    pairs=route, wireModel='each pair 1.6 x 3.2 flat; single conductors dia 1.6 at the terminal; both pairs stacked 3.2 x 3.2 through the passage',
    passage=dict(centreWorld=pas['centre'], packFaceCentre=pc.tolist(), y=pas['y'], z=pas['z'], cornerR=pas['cornerR'], channelTopZ_packlib=float(P.DFR_BOX[1][2]), lipUndersideZ=27.3,
                 clearanceAroundStackedPairs=dict(yMm=round((pas['y'][1] - pas['y'][0] - PAIR_W) / 2, 2), zMm=round((pas['z'][1] - pas['z'][0] - PAIR_W) / 2, 2))),
    passageToJ4Mm=round(float(np.linalg.norm(J4 - pc)), 1), passageToNotchBottomCentreMm=round(float(np.linalg.norm(NOTCH_BOTTOM - pc)), 1),
    passageToNotchCentreMm=round(float(np.linalg.norm(NOTCH_CENTRE - pc)), 1), J4=J4.tolist(), notch=dict(x=[-21.0, -19.0], y=[-6.0, 6.0], z=[32.7, 38.8], source='rear-pack/build_rear_pack.py PL notch'),
    insideBox=dict(frameOverlapMm3=O(inbox, F), frameGapMm=G(inbox, F, 5.0), boardsOverlapMm3=O(inbox, XL['left'] + XL['right']), boardsGapMm=G(inbox, XL['left'] + XL['right'], 5.0),
                   pdOverlapMm3=O(inbox, PD), lidOverlapMm3=O(inbox, L), lidGapMm=G(inbox, L, 5.0),
                   note='the rise segments start at the terminal end face (z %.2f), so boardsGap is the wire leaving its own terminal' % (C.XL_ZC + C.XL_TERM_L['bodyEndY'])),
    runOverBoards=dict(gapToBoardsMm=G(P.union(solids[1::3]), XL['left'] + XL['right'], 5.0), gapToTopWallMm=round(C.Z1 - C.T - (zr + 0.8), 2)),
    laneDescent=dict(gapToBoardsMm=G(P.union(solids[2::3]), XL['left'] + XL['right'], 5.0), gapToFrameMm=G(P.union(solids[2::3]), F, 5.0)),
    throughPassage=dict(frameOverlapMm3=O(fwd, F), frameGapMm=G(fwd, F, 5.0)),
    inChannel=dict(box=[[C.X_PLATE_OUT, -PAIR_W / 2, zc - PAIR_T], [-37.0, PAIR_W / 2, zc + PAIR_T]], v18OverlapMm3=O(chan, V18), v18GapMm=G(chan, V18, 5.0),
                   v19OverlapMm3=O(chan, P.solid_m('rear_pack')), openrbGapMm=G(chan, P.mesh_to_m(P.openrb_mesh()), 10.0), frameOverlapMm3=O(chan, F), lipGapMm=G(chan, F, 5.0)))
# raised top wall against the shells, neck and head at HOME (everything above z 43)
up = (F ^ P.box((-70, -40, 43.0), (-30, 40, 60))) + (L ^ P.box((-70, -40, 43.0), (-30, 40, 60)))
upb = (np.array([-67.1, -32.05, 43.0]), np.array([-45.0, 32.05, C.Z1]))
near = {}
for k, rec in man.items():
    if k in SKIP:
        continue
    lo, hi = np.array(rec['bounds'])
    if hi[2] >= 30 and lo[0] <= 40:          # every part reaching above z 30 (shells, neck, head), search 80 mm
        S = P.solid_m(k); near[k] = dict(module=rec.get('module'), gapMm=G(up, S, 80.0), overlapMm3=O(up, S))
nearest = sorted(near.items(), key=lambda kv: kv[1]['gapMm'])
r4['raisedTopWall'] = dict(region='frame and lid above z 43 (top wall z 45.3..46.5, upper side walls, lid top); every audit solid with top above z 30, HOME pose, 80 mm search',
                           nearest=dict(nearest[:12]), nearestHead=next(dict(key=k, **v) for k, v in nearest if v['module'] == 'head'),
                           nearestNeckNonShell=next(dict(key=k, **v) for k, v in nearest if v['module'] == 'neck' and not k.startswith('shell')),
                           shellRearmostPoint=dict(x=-46.13, y=0.05, z=32.12, note='shell vertices with |y| <= 32.05: rearmost x -46.13 for z 29.5..35, -44.34 for z 35..43, none above z 43'),
                           boxFrontPlaneX=C.X_PLATE_IN)
# IN wire-entry zones (5 mm below the board bottom edge, over the terminal block width) vs the 5991
zones = {}
pdb = B['pd5991']['boxes']
for nm in ('left', 'right'):
    tb = np.array(bl[nm]['inTerminalBlockWorld']); bottom = bl[nm]['worldBounds'][0][2]
    lo = np.array([tb[0][0], tb[0][1], bottom - 5.0]); hi = np.array([tb[1][0], tb[1][1], bottom])
    Z = P.box(lo, hi)
    pcb = np.array(pdb['pcb'])
    yov = max(0.0, min(hi[1], pcb[1][1]) - max(lo[1], pcb[0][1])); zov = max(0.0, min(hi[2], pcb[1][2]) - max(lo[2], pcb[0][2]))
    zones[nm] = dict(zoneBox=[lo.round(3).tolist(), hi.round(3).tolist()], projectedOverlapWith5991PcbYZ=dict(yMm=round(yov, 3), zMm=round(zov, 3)),
                     overlap3dWith5991Mm3=O(Z, PD), gap3dTo5991Mm=G(Z, PD, 10.0), zoneVsFrameOverlapMm3=O(Z, F),
                     inEntries=bl[nm]['inEntries'], entryXvs5991ComponentFaceX=[bl[nm]['inEntries'][0][0], pdb['pcb'][0][0]])
r4['inZones'] = zones
r4['inZonesNote'] = 'projected z overlap 3.42 mm > 2 mm (brief threshold), accepted by the coordinator in revision C2 with the IN routing rule (features.json wiring.in_route); in 3D the zone box sits 0.7 mm behind the 5991 PCB plane and the wire entries are at x -54.7, 3.1 mm behind the 5991 component face (x -51.6), and the 5991 has no part at its corners inside the zone (mounting holes only), so the wires hang past the 5991 edge'
# 5991 terminal exit room (+y), the daisy-chain lane behind the 5991, USB-C plug path
room = P.box((-60.1, 13.71, -36.0), (-51.6, C.HW - C.T, -28.5))
r4['pd5991TerminalExitRoom'] = dict(box=[[-60.1, 13.71, -36.0], [-51.6, C.HW - C.T, -28.5]], frameOverlapMm3=O(room, F), boardsOverlapMm3=O(room, XL['left'] + XL['right']), lengthToWallMm=round(C.HW - C.T - 13.71, 2))
lane = P.box((C.X_BACK, -C.HW + C.T, -37.7), (-60.2, C.HW - C.T, -22.0))
r4['daisyChainLaneBehind5991'] = dict(box=[[C.X_BACK, -C.HW + C.T, -37.7], [-60.2, C.HW - C.T, -22.0]], depthMm=round(-60.2 - C.X_BACK, 2), frameOverlapMm3=O(lane, F), boardsOverlapMm3=O(lane, XL['left'] + XL['right']), pdOverlapMm3=O(lane, PD))
plug_in = P.box((-57.0, -C.HW - 20.0, -38.64), (-49.5, -15.05, -25.64))
r4['usbcPlugEnvelope'] = dict(box=[[-57.0, -C.HW - 20.0, -38.64], [-49.5, -15.05, -25.64]], note='13 (z) x 7.5 (x) from the socket face (y -15.05) to 20 mm beyond the wall outer face (y -52.05)',
                              frameOverlapMm3=O(plug_in, F), frameGapMm=G(plug_in, F, 5.0), boardsGapMm=G(plug_in, XL['left'] + XL['right'], 10.0))
envp = {}
for k, rec in man.items():
    if k in SKIP:
        continue
    lo, hi = np.array(rec['bounds'])
    if np.all(lo - 15 <= [-49.5, -15.05, -25.64]) and np.all(hi + 15 >= [-57.0, -52.05, -38.64]):
        S = P.solid_m(k); envp[k] = dict(gapMm=G(plug_in, S, 15.0), overlapMm3=O(plug_in, S))
r4['usbcPlugEnvelope']['environment'] = envp
res['4_wireRoom'] = r4
print('4', json.dumps(r4), flush=True)

# ---------------------------------------------------------------- 5 driver lanes dia 5 x 60
r5 = {}
def lane_hits(lane, obst):
    out = {}
    for k, S in obst.items():
        v = O(lane, S)
        if v > 1e-6:
            out[k] = v
    return out
for (y, z) in BRP.POST['holes']:
    ln = P.cyl_x(2.5, -108.3, -48.3, y, z); hd = P.cyl_x(2.0, -48.3, -47.0, y, z)
    r5[f'cover_y{y}_z{z}_frameAlone'] = dict(laneHits=lane_hits(ln, dict(frame=F)), headHits=lane_hits(hd, dict(frame=F)), gapToFrameMm=G(ln, F, 3.0))
obst_all = dict(frame=F, xl_left=XL['left'], xl_right=XL['right'], pd5991=PD)
for nm in ('left', 'right'):
    V = xm[nm].vertices
    for h in bl[nm]['boardScrewAxes']:
        y, z = h[1], h[2]
        ln = P.cyl_x(2.5, -111.9, -51.9, y, z)
        own = {k: v for k, v in obst_all.items() if k != f'xl_{nm}'}
        sel = V[V[:, 0] < -51.9]; rr = np.hypot(sel[:, 1] - y, sel[:, 2] - z)
        r5[f'xl_{nm}_y{y}_z{z}'] = dict(laneHitsOther=lane_hits(ln, own), ownComponentRadiusMm=round(float(rr.min()), 3), gapToFrameMm=G(ln, F, 3.0))
for h in B['pd5991']['screwAxes']:
    y, z = h[1], h[2]
    ln = P.cyl_x(2.5, -111.7, -51.7, y, z)
    sel = pdm.vertices[pdm.vertices[:, 0] < -51.7]
    box_hits = {k: bb for k, bb in B['pd5991']['boxes'].items() if k != 'pcb'}
    dmin = min(float(np.hypot(max(bb[0][1] - y, 0, y - bb[1][1]), max(bb[0][2] - z, 0, z - bb[1][2]))) for bb in box_hits.values())
    r5[f'pd5991_y{y}_z{z}'] = dict(laneHitsOther=lane_hits(ln, dict(frame=F, xl_left=XL['left'], xl_right=XL['right'])), ownComponentRadiusMm=round(dmin, 3))
for h in B['holes']['lidScrews']:
    ln = P.cyl_x(2.5, -127.1, -67.1, h[1], h[2])
    r5[f'lid_y{h[1]}_z{h[2]}'] = dict(laneHits=lane_hits(ln, dict(frame=F, lid=L, **{k: v for k, v in obst_all.items() if k != 'frame'})))
r5['pass'] = all(not v.get('laneHits') and not v.get('headHits') and not v.get('laneHitsOther') and v.get('ownComponentRadiusMm', 9) >= 2.5 for k, v in r5.items() if isinstance(v, dict))
res['5_driverLanesDia5'] = r5
print('5', json.dumps(r5), flush=True)

# ---------------------------------------------------------------- 6 assembly order: frame on pack, 5991, left board, right board, lid
def sweep(mover, mb, path, obst, search=3.0):
    worst = dict(maxOverlapMm3=0.0, minGapMm=search, closest=None, collisionSteps=0, firstCollision=None)
    for off in path:
        mv = mover.translate(list(map(float, off)))
        lo = mb[0] + off; hi = mb[1] + off
        ov = 0.0
        for k, (S, sb) in obst.items():
            if not (np.all(sb[0] - search <= hi) and np.all(sb[1] + search >= lo)):
                continue
            v = float((mv ^ S).volume())
            if v > 1e-3:
                ov = max(ov, v)
                if worst['firstCollision'] is None:
                    worst['firstCollision'] = dict(offset=list(map(float, off)), obstacle=k, overlapMm3=round(v, 3))
            g = float(mv.min_gap(S, search))
            if g < worst['minGapMm'] and not np.allclose(off, 0):
                worst.update(minGapMm=round(g, 3), closest=k, closestOffset=list(map(float, off)))
        if ov > 1e-3:
            worst['collisionSteps'] += 1
        worst['maxOverlapMm3'] = max(worst['maxOverlapMm3'], round(ov, 3))
    worst['steps'] = len(path); worst['pass'] = worst['collisionSteps'] == 0
    return worst
line = lambda d: [np.array([-(d - 0.5 * i), 0.0, 0.0]) for i in range(int(round(d / 0.5)) + 1)]
bnd = lambda m: (m.bounds[0], m.bounds[1])
def mbounds(S):
    mm_ = P.from_m(S); return (mm_.bounds[0], mm_.bounds[1])
env = {}
for k, rec in man.items():
    if k in SKIP:
        continue
    lo, hi = np.array(rec['bounds'])
    if np.all(lo - 3 <= [-37.5, 32.05, 43.0]) and np.all(hi + 3 >= [-95.9, -32.05, -44.0]):
        env[k] = (P.solid_m(k), (lo, hi))
env_v18 = {k: v for k, v in env.items() if k != 'rear_pack'}; env_v18['rear_pack-v18'] = (V18, bnd(P.load_stl(P.WORLD / 'rear_pack-v18.stl')))
r6 = {}
r6['frame_plus_x_30_v19pack'] = sweep(F, bnd(fm), line(30.0), env)
r6['frame_plus_x_30_v18pack'] = sweep(F, bnd(fm), line(30.0), env_v18)
print('6 frame', r6['frame_plus_x_30_v19pack'], r6['frame_plus_x_30_v18pack'], flush=True)
inbox = dict(frame=(F, bnd(fm)))
r6['pd5991_plus_x_25'] = sweep(PD, mbounds(PD), line(25.0), inbox)
inbox['pd5991'] = (PD, mbounds(PD))
r6['xl_left_plus_x_25'] = sweep(XL['left'], mbounds(XL['left']), line(25.0), inbox)
inbox['xl_left'] = (XL['left'], mbounds(XL['left']))
r6['xl_right_plus_x_25'] = sweep(XL['right'], mbounds(XL['right']), line(25.0), inbox)
inbox['xl_right'] = (XL['right'], mbounds(XL['right']))
r6['lid_plus_x_15'] = sweep(L, bnd(lm), line(15.0), inbox)
r6['order'] = ['frame onto the pack (+x), four cover screws from the back (frame empty, lanes clear: check 5)', '5991 onto its four bosses from the back (+x), USB-C towards the -y opening, four M2 x 6',
               'wire the 15 V pair: 5991 terminal (+y, entries y 13.7) -> left board IN; daisy chain left IN -> right IN behind the 5991 (lane x -65.9..-60.2)',
               'left board, then right board, onto their bosses from the back (+x), four M2 x 6 each from the component side; IN wires screwed in before seating',
               'OUT pairs pushed down through the top slots into the OUT terminals; terminal screws from the back', 'set the trimmers (component side, lid off)', 'lid (+x), two M2 x 6']
r6['pass'] = all(v['pass'] for k, v in r6.items() if isinstance(v, dict))
res['6_assembly'] = r6
print('6', {k: (v['pass'], v['minGapMm'], v['closest'], v['firstCollision']) for k, v in r6.items() if isinstance(v, dict)}, flush=True)

# ---------------------------------------------------------------- 7 printability
import networkx as nx
def regions(mesh, mask):
    adj = mesh.face_adjacency; keep = mask[adj[:, 0]] & mask[adj[:, 1]]
    g = nx.Graph(); g.add_nodes_from(np.flatnonzero(mask)); g.add_edges_from(adj[keep]); out = []
    for comp in nx.connected_components(g):
        comp = np.array(sorted(comp)); tri = mesh.triangles[comp].reshape(-1, 3)
        out.append(dict(areaMm2=round(float(mesh.area_faces[comp].sum()), 2), bbox=[np.round(tri.min(0), 2).tolist(), np.round(tri.max(0), 2).tolist()]))
    return sorted(out, key=lambda r: -r['areaMm2'])
def analyse(mesh, R, note):
    m = trimesh.Trimesh(mesh.vertices @ R.T, mesh.faces, process=False); n = m.face_normals; bed = float(m.bounds[0][2])
    fz = m.triangles[:, :, 2].max(1); on_bed = (np.abs(n[:, 2] + 1) < 1e-3) & (fz < bed + 0.02)
    over = (n[:, 2] < -0.7072) & ~on_bed
    regs = regions(m, over)
    return dict(pose=note, bedContactAreaMm2=round(float(m.area_faces[on_bed].sum()), 1), heightMm=round(float(m.bounds[1][2] - bed), 2),
                overhangAreaMm2=round(float(m.area_faces[over].sum()), 2), overhangRegions=regs[:12], regionsCount=len(regs))
Rp = np.array([[0, -1, 0], [0, 0, 1], [-1, 0, 0]], float)
r7 = dict(frame_bottomWallOnBed=analyse(fm, np.eye(3), 'as assembled, bottom wall z -44 on the bed (rear_frame-print.stl)'),
          frame_plateOnBed=analyse(fm, Rp, "pack face x -45 down: x' = -y, y' = z, z' = -x"),
          frame_plateOnBed_ifLipDropped=analyse(P.from_m(F - P.box((C.X_PLATE_OUT, -14, 27.0), (-37.0, 14, 29.0))), Rp, 'same pose with the lip (x -45..-37.5) removed: information for the lip decision'),
          lid_outerFaceOnBed=analyse(lm, np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float), 'outer face x -67.1 on the bed (rear_lid-print.stl)'))
res['7_printability'] = r7
for k, v in r7.items():
    print('7', k, {kk: vv for kk, vv in v.items() if kk != 'overhangRegions'}, v['overhangRegions'][:6], flush=True)

iz = r4['inZones']; zmax = max(v['projectedOverlapWith5991PcbYZ']['zMm'] for v in iz.values())
res['summary'] = dict(
    passFlags={k: bool(res[k]['pass']) for k in ('1_manifold', '2_fitAtRest', '3_boardsInBox', '5_driverLanesDia5', '6_assembly')},
    inZoneProjectedZOverlapMm=float(zmax), inZoneThresholdMm=2.0, inZoneWithinThreshold=bool(zmax < 2.0), inZoneAccepted='coordinator 2026-10-14 revision C2 (3D gap 0.205; IN routing rule in features.json)',
    inZoneGap3dTo5991Mm=min(v['gap3dTo5991Mm'] for v in iz.values()),
    outPassageCentre=r4['outRoute']['passage']['centreWorld'], outRouteFrameOverlapMm3=r4['outRoute']['insideBox']['frameOverlapMm3'], outRouteChannelV18OverlapMm3=r4['outRoute']['inChannel']['v18OverlapMm3'],
    raisedTopMinGapMm=min(v['gapMm'] for v in r4['raisedTopWall']['nearest'].values()),
    usbcPlugMinEnvironmentGapMm=min(v['gapMm'] for v in r4['usbcPlugEnvelope']['environment'].values()),
    printability='informational: frame bottom-wall-down overhang %.0f mm2 (top wall bridge + lip underside); lid 0' % r7['frame_bottomWallOnBed']['overhangAreaMm2'],
    notRun=['walking-pose sweep of legs against the box and USB-C plug'])
print('SUMMARY', json.dumps(res['summary']), flush=True)
res['elapsed_s'] = round(time.time() - t0, 1)
P.jdump(res, HERE / 'checks.json')
print('DONE', res['elapsed_s'])
