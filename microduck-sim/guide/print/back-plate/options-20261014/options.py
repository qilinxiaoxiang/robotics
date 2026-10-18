"""Two-piece converter-box layouts for Shawn's choice (envelope solids only: no bosses, windows or vents).
Frame = cover plate x -47..-45 (build_rear_pack.build_cover: outline, four dia 2.2 holes, lip) + side/top/bottom walls 1.2 mm
(x -65.9..-47); lid = 1.2 mm back plate x -67.1..-65.9. Inner depth 18.9: XL4015 PCB mid-plane x -51.03 leaves 0.52 mm from
the pin tips to the plate (x -47) and from the inductor to the lid (x -65.9).
Layouts: A (wide, horizontal boards, 5991 under the lower board), B (flush, vertical boards, IN bottom / OUT top, as briefed),
B_flip (B with OUT bottom / IN top, so the OUT pairs reach plate passages into the pack channel).
Writes <layout>/*.stl (world frame) and numbers.json."""
import sys, json, time
from pathlib import Path
import numpy as np, trimesh
import manifold3d as m3
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'rear-pack'))
import pack_lib as P
import build_rear_pack as BRP
t0 = time.time()

XL_SRC = HERE.parent.parent / 'candidates/back-box-20261014/parts/xl4015_board_local_mm.stl'
PCB_MID = -1.175; PIN_SIDE = 3.51; COMP_SIDE = 14.35
X_PLATE = -47.0; X_LID_IN = -65.9; X_LID_OUT = -67.1; T = 1.2
MID_X = X_PLATE - (18.9 - 17.86) / 2 - PIN_SIDE            # -51.03
HOLES_L = [(sy * 28.25, sz * 10.5) for sy in (1, -1) for sz in (1, -1)]
TRIM_L = {'trimmer_a': (11.15, -10.44, 11.57), 'trimmer_b': (11.15, 0.06, 11.57)}   # adjusting-screw tops (local X, Y, Z)
ENTRY_L = {'+Y': [(2.5, 30.15, 2.5), (2.5, 30.15, -2.5)], '-Y': [(2.5, -30.15, 2.5), (2.5, -30.15, -2.5)]}
R_H = np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]], float)     # horizontal: local +Y -> -y (IN end assumed local +Y)
R_V_INDOWN = np.array([[-1, 0, 0], [0, 0, -1], [0, -1, 0]], float)   # vertical: local +Y (IN) -> -z, local Z -> -y
R_V_INUP = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], float)       # vertical: local +Y (IN) -> +z, local Z -> +y
for R in (R_H, R_V_INDOWN, R_V_INUP):
    assert abs(np.linalg.det(R) - 1) < 1e-9


def place(R, t):
    return lambda L: (np.atleast_2d(np.asarray(L, float)) - [PCB_MID, 0, 0]) @ R.T + np.asarray(t, float)


def hull_solid(mesh):
    parts = [m3.Manifold.hull_points(np.asarray(p.vertices, float)) for p in mesh.split(only_watertight=False)
             if len(p.vertices) >= 4 and np.ptp(p.vertices, axis=0).min() > 1e-3]
    return P.union(parts)


# ---------------------------------------------------------------- 5991 (Adafruit board file, see ../place_components.py)
PD = dict(pcb=(20.32, 27.813, 1.6), holes=[(2.413, 25.273), (17.653, 25.273), (2.54, 2.54), (17.78, 2.54)],
          parts=dict(usbc=((5.69, 21.606), (14.63, 28.956), 3.3), term=((6.76, 0.21), (13.76, 7.21), 8.5),
                     dip=((12.921, 8.603), (18.321, 16.543), 2.0), qt=((0.518, 13.256), (4.818, 19.356), 3.0)))


def pd5991(back_x, usb_face_z, yc):
    vz = usb_face_z + (28.956 - 27.813)
    W = lambda u, v, w: np.array([back_x - w, u - 10.16 + yc, vz + (27.813 - v)])
    boxes = {}
    def bx(uv0, uv1, w0, w1):
        a, b = W(uv0[0], uv0[1], w0), W(uv1[0], uv1[1], w1)
        return np.minimum(a, b), np.maximum(a, b)
    boxes['pcb'] = bx((0, 0), PD['pcb'][:2], 0, 1.6)
    for k, (a, b, h) in PD['parts'].items():
        boxes[k] = bx(a, b, 1.6, 1.6 + h)
    mesh = trimesh.util.concatenate([trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2)) for lo, hi in boxes.values()])
    holes = [W(u, v, 0).round(3).tolist() for u, v in PD['holes']]
    term_entries = [W(u, 0.21, 1.6 + 2.5).round(2).tolist() for u in (8.41, 11.91)]   # 3.5 mm pitch, entries face v = 0 (up)
    return mesh, {k: [lo.round(3).tolist(), hi.round(3).tolist()] for k, (lo, hi) in boxes.items()}, holes, term_entries


LAYOUTS = {
 'A': dict(title='A wide: horizontal XL4015 x2, 5991 under the lower board', hw=37.55, z0=-44.0, z1=43.0,
           boards={'lower_7V': (R_H, (MID_X, 0.0, 0.5)), 'upper_5V': (R_H, (MID_X, 0.0, 27.9))},
           pd=dict(back_x=-49.0, usb_face_z=-42.8, yc=-3.0),
           holes=[dict(id='usbc_opening', wall='bottom', kind='box', lo=(-56.25, -10.0, -45.0), hi=(-48.25, 4.0, -42.8),
                       purpose='USB-C plug overmold (13 x 7 + 0.5 all round), long side along y'),
                  dict(id='out7V_passage', wall='plate', axis='x', y=11.0, z=-20.0, d=4.0, purpose='7 V pair from the lower board OUT (+y end, down the end lane) into the pack channel'),
                  dict(id='out5V_passage', wall='plate', axis='x', y=11.0, z=-26.0, d=4.5, purpose='5 V jumpers from the upper board OUT (+y end, down the end lane) into the pack channel')]),
 'B': dict(title='B flush: vertical XL4015 x2, IN bottom / OUT top (as briefed), 5991 on the bench', hw=32.05, z0=-44.0, z1=43.0,
           boards={'plusY_7V': (R_V_INDOWN, (MID_X, 13.7, -0.5)), 'minusY_5V': (R_V_INDOWN, (MID_X, -13.7, -0.5))},
           holes=[dict(id='in15V_hole', wall='bottom', axis='z', x=-56.5, y=0.0, d=4.0, purpose='one stranded 22 AWG 15 V pair from the bench 5991, daisy-chained between the two IN terminals'),
                  dict(id='out7V_top_hole', wall='top', axis='z', x=-54.7, y=11.6, d=4.0, purpose='7 V pair, +y board OUT (entries y 11.2 / 16.2); centre held inside |y| 13.6 - 2'),
                  dict(id='out5V_top_hole', wall='top', axis='z', x=-54.7, y=-11.35, d=4.5, purpose='5 V jumpers, -y board OUT')]),
 'B_flip': dict(title='B flipped: vertical XL4015 x2, OUT bottom into the pack channel / IN top, 5991 on the bench', hw=32.05, z0=-44.0, z1=43.0,
           boards={'plusY_7V': (R_V_INUP, (MID_X, 13.7, -0.5)), 'minusY_5V': (R_V_INUP, (MID_X, -13.7, -0.5))},
           holes=[dict(id='in15V_hole', wall='top', axis='z', x=-56.5, y=0.0, d=4.0, purpose='one stranded 22 AWG 15 V pair from the bench 5991, daisy-chained between the two IN terminals'),
                  dict(id='out7V_passage', wall='plate', axis='x', y=8.0, z=-37.0, d=4.0, purpose='7 V pair into the channel floor; joins the current supply route (+Y side of the channel, up the lane to J4 at (-29, 1.5, 27.5))'),
                  dict(id='out5V_passage', wall='plate', axis='x', y=-8.0, z=-37.0, d=4.5, purpose='5 V jumpers into the channel floor; up the channel and lane to the pack top notch (pi_trunk path)')]),
}


def build(L):
    hw, z0, z1 = L['hw'], L['z0'], L['z1']
    walls = [P.box((X_LID_IN, -hw, z0), (X_PLATE, -hw + T, z1)), P.box((X_LID_IN, hw - T, z0), (X_PLATE, hw, z1)),
             P.box((X_LID_IN, -hw, z1 - T), (X_PLATE, hw, z1)), P.box((X_LID_IN, -hw, z0), (X_PLATE, hw, z0 + T))]
    frame = P.union(walls + [BRP.build_cover()])
    lid = P.box((X_LID_OUT, -hw, z0), (X_LID_IN, hw, z1))
    cuts = []
    for h in L['holes']:
        if h['kind'] if 'kind' in h else False:
            cuts.append(P.box(h['lo'], h['hi']))
        elif h['axis'] == 'x':
            cuts.append(P.cyl_x(h['d'] / 2, -48.0, -44.0, h['y'], h['z']))
        else:
            zz = (z0 - 1, z0 + T + 1) if h['wall'] == 'bottom' else (z1 - T - 1, z1 + 1)
            cuts.append(P.cyl_z(h['d'] / 2, zz[0], zz[1], h['x'], h['y']))
    frame = frame - P.union(cuts)
    return frame, lid


src = trimesh.load(str(XL_SRC), force='mesh')
SH = {k: P.solid_m(k) for k in ('shell_left', 'shell_right')}
LEGS = {k: P.solid_m(k) for k in ('lower', 'right_lower', 'ring2', 'ring7')}
PACKS = {f: P.mesh_to_m(P.load_stl(P.WORLD / f)) for f in ('rear_pack-v18.stl', 'rear_pack.stl')}
ORB = P.mesh_to_m(P.openrb_mesh())
DYN = Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/v19-20261014')
items = json.loads((DYN / 'v19-mass-items.json').read_text()); summ = json.loads((DYN / 'v19-walk-summary.json').read_text())
fill = items['fill_fraction_vs_PLA_1p24']; base = summ['mass']['asbuilt-batteryremove60']
M0 = base['total_mass_g']; C0 = np.array(base['whole_robot_com_at_home_in_trunk_frame_mm'])
cov = [i for i in items['bodies']['trunk_base'] if i['id'] == 'add-rear_pack_cover'][0]
shellV = {k: P.solid_mesh(k).vertices for k in SH}
shell_max_abs_y_rear = {k: round(float(np.abs(V[V[:, 0] < -40][:, 1]).max()), 3) for k, V in shellV.items()}

out = {'meta': dict(frame='guide world mm, x forward, y left, z up', method=__doc__, xl4015MidPlaneX=round(MID_X, 3),
                    xl4015PoseNote='the IN end is assumed to be local +Y of the ROBOTIS mesh (not on the mesh); read the board label',
                    boardSolids='convex hull of each connected body of the ROBOTIS mesh', massMethod=f'solid volume x 1.24 g/cm3 x {fill} (v19-mass-items.json) + XL4015 20 g each (estimate) + 5991 3.5 g (datasheet) - V1.8 cover {cov["g"]} g (slicer); baseline asbuilt-batteryremove60 {M0} g, COM {C0.tolist()}',
                    shellMaxAbsYBehindXm40=shell_max_abs_y_rear)}
for name, L in LAYOUTS.items():
    d = HERE / name; d.mkdir(exist_ok=True)
    frame, lid = build(L)
    fm = P.clean_mesh(frame); lm = P.clean_mesh(lid)
    fm.export(d / 'frame-world.stl'); lm.export(d / 'lid-world.stl')
    r = dict(title=L['title'], outer=dict(x=[X_LID_OUT, -45.0], absY=L['hw'], z=[L['z0'], L['z1']]),
             inner=dict(x=[X_LID_IN, X_PLATE], absY=L['hw'] - T, z=[L['z0'] + T, L['z1'] - T]))
    solids = {}; mass_items = []
    for bn, (R, t) in L['boards'].items():
        f = place(R, t)
        m = trimesh.Trimesh(f(src.vertices), src.faces, process=False); m.export(d / f'xl4015_{bn}-world.stl')
        (d / 'render').mkdir(exist_ok=True)
        m.simplify_quadric_decimation(face_count=12000).export(d / 'render' / f'xl4015_{bn}.stl')   # render copy only (MuJoCo memory)
        S = hull_solid(m); solids[bn] = S
        holes = f([(PCB_MID, y, z) for y, z in HOLES_L]).round(3).tolist()
        r.setdefault('boards', {})[bn] = dict(origin=list(t), rotationLocalToWorld=R.tolist(), worldBounds=np.round(m.bounds, 3).tolist(),
            boardScrews_holeAxesWorld=holes, boardScrewsOnPlateMaterial=[bool(abs(h[1]) <= 18.6 - 2.5 and -40 <= h[2] <= 29.5 - 2.5) for h in holes],
            trimmerScrewTopsWorld={k: f([v])[0].round(2).tolist() for k, v in TRIM_L.items()},
            inEntriesWorld=f(ENTRY_L['+Y'])[:, :].round(2).tolist(), outEntriesWorld=f(ENTRY_L['-Y']).round(2).tolist())
        mass_items.append((f'xl4015_{bn}', 20.0, (m.bounds[0] + m.bounds[1]) / 2))
    if 'pd' in L:
        pm, boxes, pholes, tent = pd5991(**L['pd']); pm.export(d / 'pd5991-world.stl'); solids['pd5991'] = hull_solid(pm)
        lower = solids['lower_7V']
        r['pd5991'] = dict(pose=L['pd'], boxes=boxes, holesWorld=pholes, terminalEntriesWorld=tent,
                           gapToLowerBoardMm=round(float(solids['pd5991'].min_gap(lower, 10.0)), 3),
                           terminalTopZ=boxes['term'][1][2], lowerBoardBottomZ=r['boards']['lower_7V']['worldBounds'][0][2], terminalWireRoomAboveMm=round(r['boards']['lower_7V']['worldBounds'][0][2] - boxes['term'][1][2], 3),
                           heightAlongZ=28.956)
        mass_items.append(('pd5991', 3.5, (pm.bounds[0] + pm.bounds[1]) / 2))
    # board/5991 to every wall
    wl = dict(lid=lid, plate=BRP.build_cover(), side_minus_y=P.box((X_LID_IN, -L['hw'], L['z0']), (X_PLATE, -L['hw'] + T, L['z1'])),
              side_plus_y=P.box((X_LID_IN, L['hw'] - T, L['z0']), (X_PLATE, L['hw'], L['z1'])),
              top=P.box((X_LID_IN, -L['hw'], L['z1'] - T), (X_PLATE, L['hw'], L['z1'])), bottom=P.box((X_LID_IN, -L['hw'], L['z0']), (X_PLATE, L['hw'], L['z0'] + T)))
    gaps = {}
    for bn, S in solids.items():
        gaps[bn] = {w: dict(gapMm=round(float(S.min_gap(W, 15.0)), 3), overlapMm3=round(float((S ^ W).volume()), 3)) for w, W in wl.items()}
    names = list(solids)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            gaps[f'{names[i]}__{names[j]}'] = dict(gapMm=round(float(solids[names[i]].min_gap(solids[names[j]], 15.0)), 3),
                                                  overlapMm3=round(float((solids[names[i]] ^ solids[names[j]]).volume()), 3))
    r['clearances'] = gaps
    # free z above / below the boards and wire room at the terminal ends
    allb = np.array([m.bounds for m in [trimesh.load(str(d / f'xl4015_{bn}-world.stl'), force='mesh') for bn in L['boards']]])
    r['freeZ'] = dict(aboveBoards=round(L['z1'] - T - float(allb[:, 1, 2].max()), 3), belowBoards=round(float(allb[:, 0, 2].min()) - (L['z0'] + T), 3))
    r['freeAbsYBeyondBoardEnds'] = round(L['hw'] - T - float(np.abs(allb[:, :, 1]).max()), 3)
    # cover screws covered by boards (dia 5 lane from the head top x -48.3 backwards, lid off)
    cs = {}
    for (y, z) in BRP.POST['holes']:
        lane = P.cyl_x(2.5, -108.0, -48.3, y, z)
        hit = {bn: round(float((lane ^ S).volume()), 2) for bn, S in solids.items() if (lane ^ S).volume() > 1e-6}
        hit.update({w: round(float((lane ^ W).volume()), 2) for w, W in wl.items() if w not in ('lid', 'plate') and (lane ^ W).volume() > 1e-6})
        cs[f'y{y}_z{z}'] = dict(coveredBy=hit, coveredByBoards=any(k in solids for k in hit))
    r['coverScrewsDia5Lanes'] = cs
    # fit at rest
    E = frame + lid
    fit = {k: dict(gapMm=round(float(E.min_gap(S, 15.0)), 3), overlapMm3=round(float((E ^ S).volume()), 3)) for k, S in list(SH.items()) + list(LEGS.items()) + list(PACKS.items())}
    fit['openrb'] = dict(gapMm=round(float(E.min_gap(ORB, 15.0)), 3), overlapMm3=round(float((E ^ ORB).volume()), 3))
    r['fitAtRest'] = fit
    r['shellOverhangPerSideMm'] = {k: round(L['hw'] - v, 3) for k, v in shell_max_abs_y_rear.items()}
    # holes
    r['holes'] = L['holes']
    # mass
    vf = float(frame.volume()) / 1000; vl = float(lid.volume()) / 1000
    mass_items += [('frame', vf * 1.24 * fill, np.array(P.from_m(frame).center_mass)), ('lid', vl * 1.24 * fill, np.array(P.from_m(lid).center_mass)),
                   ('rear_pack_cover_removed', -cov['g'], np.array(cov['com_body_mm']))]
    dm = sum(g for _, g, _ in mass_items); dC = sum(g * (np.asarray(c) - C0) for _, g, c in mass_items) / (M0 + dm)
    r['mass'] = dict(frameCm3=round(vf, 2), lidCm3=round(vl, 2), items={n: dict(g=round(g, 2), com=np.round(c, 2).tolist()) for n, g, c in mass_items},
                     printedG=round((vf + vl) * 1.24 * fill, 1), netAddedG=round(dm, 1), totalRobotG=round(M0 + dm, 1),
                     comShiftMm=np.round(dC, 2).tolist(), newComMm=np.round(C0 + dC, 2).tolist(), note='envelope solids (no bosses, windows, vents); wires excluded')
    out[name] = r
    print(name, json.dumps({k: r[k] for k in ('freeZ', 'freeAbsYBeyondBoardEnds', 'shellOverhangPerSideMm', 'mass')}), flush=True)
    print('  gaps', json.dumps(gaps), flush=True)
    print('  cover', json.dumps(cs), flush=True)
    print('  fit', json.dumps(fit), flush=True)
# onward route for OUT pairs leaving through the top wall (layout B as briefed): shell top surface under a ray from z 80
tops = {}
for k, S in (('shell_left', P.solid_mesh('shell_left')), ('shell_right', P.solid_mesh('shell_right'))):
    sgn = 1 if k == 'shell_left' else -1
    for x in (-44, -40, -36, -32, -28, -24, -20):
        for y in (2, 8, 14):
            loc, _, _ = S.ray.intersects_location(np.array([[x, sgn * y, 80.0]]), np.array([[0, 0, -1.0]]))
            tops[f'{k}_x{x}_y{sgn * y}'] = round(float(loc[:, 2].max()), 2) if len(loc) else None
out['B']['topWallRouteEvidence'] = dict(shellTopZ=tops, note='the torso shell skin closes the top behind the neck (z 35..42 for x -44..-24 at |y| <= 14); the first opening is at x about -20 (no hit at |y| < 14), the neck. A pair leaving the top wall therefore runs about 30 mm over the outside of the shell to x -20 before it can drop to J4 (-29, 1.5, 27.5) or the notch; it cannot reach the pack channel. Plate passages inside |y| <= 13.6 are reachable only below the boards (z < -31.9) via the 4.05 mm lanes beside the board edges, or by flipping the boards (B_flip).')
out['elapsed_s'] = round(time.time() - t0, 1)
P.jdump(out, HERE / 'numbers.json')
print('DONE', out['elapsed_s'])
