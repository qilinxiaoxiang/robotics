"""Layout D render geometry (feasibility pass, not a release build; 2026-10-14).
Two horizontal XL4015 (long axis y, component side to the lid), stacked under the top wall; four side windows at the
terminal blocks; Adafruit 5991 standing under the lower board, USB-C down through the bottom wall, terminal up.
Variant 'frame': C2-style frame (cover outline, holes, lip; walls x -65.9..-47, |y| <= 32.05, z -44..43) on the V1.8 pack.
Variant 'integrated': V1.9 rear_pack-world.stl with the bay walls added (no cover plate, no cover screws), tether opening
filled. Lids: solid and skeletal (x -67.1..-65.9). Envelope gaps at HOME go to envelope.json. No wire routing.
World frame = guide frame (mm, x forward, y left, z up)."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
import manifold3d as m3
HERE = Path(__file__).resolve().parent
BP = HERE.parent
sys.path.insert(0, str(BP.parent / 'rear-pack'))
import pack_lib as P
import build_rear_pack as BRP
import ia_lib

X_IN, X_OUT, X_BACK, X_LID = -47.0, -45.0, -65.9, -67.1
HW, T, Z0, Z1 = 32.05, 1.2, -44.0, 43.0
YI, ZI0, ZI1 = HW - T, Z0 + T, Z1 - T                      # inner 30.85, floor -42.8, top 41.8
XL_SRC = BP.parent / 'candidates/back-box-20261014/parts/xl4015_board_local_mm.stl'
PCB_MID = -1.175
XL_MID_X = -51.03; XL_PIN_FACE_X = XL_MID_X + 0.825        # as C2 (18.9 inner depth, 0.52 to plate and lid)
R_XL = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]], float)  # local X -> -x (components to the lid), +Y (IN) -> +y, Z -> -z
HALF_W = 13.1
ZC_UP = ZI1 - 0.5 - HALF_W                                  # 28.2: top edge 0.5 under the top wall
ZC_LO = ZC_UP - 2 * HALF_W - 1.2                            # 0.8: 1.2 under the upper board
BOARDS = {'upper': ZC_UP, 'lower': ZC_LO}
XL_HOLES_L = [(sy * 28.25, sz * 10.5) for sy in (1, -1) for sz in (1, -1)]
TERM_Z = (-5.17, 5.0); BEND = 2.0 + 0.8                     # 22 AWG solid, 2 mm bend radius, 1.6 OD
# 5991 standing: (u along y, v down, w to -x); USB-C edge v = 27.813 down, socket face (v 28.956) at the floor inner face
PD = dict(pcb=(20.32, 27.813, 1.6), holes=[(2.413, 25.273), (17.653, 25.273), (2.54, 2.54), (17.78, 2.54)],
          parts=dict(usbc=((5.69, 21.606), (14.63, 28.956), 3.3), term=((6.76, 0.21), (13.76, 7.21), 8.5),
                     dip=((12.921, 8.603), (18.321, 16.543), 2.0), qt=((0.518, 13.256), (4.818, 19.356), 3.0)))
PD_BACK_X = -50.0; PD_YC = 0.0
PD_VBOT = ZI0 + (28.956 - 27.813)                           # PCB bottom edge z -41.657 (socket face flush with the floor inner face)


def pd_w(u, v, w):
    return np.array([PD_BACK_X - w, PD_YC + u - PD['pcb'][0] / 2, PD_VBOT + (PD['pcb'][1] - v)])


def pd_boxes():
    out = {}
    def bx(a, b, w0, w1):
        p, q = pd_w(a[0], a[1], w0), pd_w(b[0], b[1], w1)
        return np.minimum(p, q), np.maximum(p, q)
    out['pcb'] = bx((0, 0), PD['pcb'][:2], 0, 1.6)
    for k, (a, b, h) in PD['parts'].items():
        out[k] = bx(a, b, 1.6, 1.6 + h)
    return out


def xl_place(V, zc):
    return (np.atleast_2d(np.asarray(V, float)) - [PCB_MID, 0, 0]) @ R_XL.T + np.array([XL_MID_X, 0.0, zc])


def windows():
    """one per terminal block: full wall thickness, x from the lid seat to the PCB pin face, z = block +- bend room."""
    out = {}
    for nm, zc in BOARDS.items():
        zlo, zhi = zc - TERM_Z[1] - BEND, zc - TERM_Z[0] + BEND
        for side, s in (('IN+y', 1), ('OUT-y', -1)):
            out[f'{nm}_{side}'] = dict(x=[X_BACK, round(XL_PIN_FACE_X, 3)], y=sorted([s * YI, s * HW]), z=[round(zlo, 3), round(zhi, 3)])
    return out


USB_OPEN = dict(x=(-57.5, -49.0), y=(-7.0, 7.0))            # 13 x 7.5 overmold + 0.5 all round, in the bottom wall


def walls():
    return [P.box((X_BACK, -HW, Z0), (X_IN, -YI, Z1)), P.box((X_BACK, YI, Z0), (X_IN, HW, Z1)),
            P.box((X_BACK, -HW, ZI1), (X_IN, HW, Z1)), P.box((X_BACK, -HW, Z0), (X_IN, HW, ZI0))]


def xl_bosses():
    parts, cuts = [], []
    for zc in BOARDS.values():
        for (y, z) in [(h[1], h[2]) for h in xl_place([(PCB_MID, a, b) for a, b in XL_HOLES_L], zc)]:
            parts.append(P.cyl_x(2.25, XL_PIN_FACE_X, X_IN + 0.01, y, z))
            s = np.sign(y); parts.append(P.box((XL_PIN_FACE_X, min(y, s * (YI + 0.01)), z - 1.5), (X_IN, max(y, s * (YI + 0.01)), z + 1.5)))
            cuts.append(P.cyl_x(0.8, XL_PIN_FACE_X - 1, X_IN - 0.3, y, z))
    return parts, cuts


def pd_bosses(x_end):
    parts, cuts = [], []
    for u, v in PD['holes']:
        h = pd_w(u, v, 0)
        parts.append(P.cyl_x(2.25, PD_BACK_X, x_end, h[1], h[2])); cuts.append(P.cyl_x(0.8, PD_BACK_X - 1, x_end - 0.3, h[1], h[2]))
    return parts, cuts


LID_BOSSES = [(-22.0, -40.3), (22.0, -40.3)]                 # bottom corners beside the 5991; the boards fill the top (0.5 under the top wall)


def lid_bosses():
    parts, cuts = [], []
    for y, z in LID_BOSSES:
        parts += [P.cyl_x(2.5, X_BACK, X_BACK + 5.6, y, z), P.box((X_BACK, y - 2.5, ZI0 - 0.01), (X_BACK + 5.6, y + 2.5, z))]
        cuts.append(P.cyl_x(0.8, X_BACK - 1, X_BACK + 5.2, y, z))
    return parts, cuts


def common_cuts():
    c = [P.box((w['x'][0] - 1, w['y'][0] - 1 if w['y'][0] < 0 else w['y'][0] - 0.01, w['z'][0]), (w['x'][1], w['y'][1] + 0.01 if w['y'][1] > 0 else w['y'][1] + 1, w['z'][1])) for w in windows().values()]
    c.append(P.box((USB_OPEN['x'][0], USB_OPEN['y'][0], Z0 - 1), (USB_OPEN['x'][1], USB_OPEN['y'][1], ZI0 + 0.01)))
    return c


def frame_variant():
    xb, xc = xl_bosses(); pb, pc = pd_bosses(X_IN + 0.01); lb, lc = lid_bosses()
    web = P.box((X_IN, -HW, Z0), (X_OUT, HW, -2.0))
    f = P.union([BRP.build_cover(), web] + walls() + xb + pb + lb)
    cuts = xc + pc + lc + common_cuts() + [P.cyl_x(BRP.COVER['hole_r'], X_IN - 1, X_OUT + 1, y, z) for (y, z) in BRP.POST['holes']]
    return f - P.union(cuts)


def integrated_variant():
    pack = P.mesh_to_m(P.load_stl(BP.parent / 'rear-pack-v19' / 'rear_pack-world.stl'))
    pack = pack + P.box((-44.5, -3.0, Z0), (-39.5, 3.0, ZI0))                     # tether opening filled (no battery tether)
    xb, xc = xl_bosses(); pb, pc = pd_bosses(X_OUT); lb, lc = lid_bosses()
    # joint between the bay and the pack: the C2 lower web (x -47..-45, below z -2) and a collar on the pack side walls up to the wall top 28.5
    joint = [P.box((X_IN, -HW, Z0), (X_OUT, HW, -2.0)) - P.box((X_IN - 1, -13.6, ZI0), (X_OUT + 1, 13.6, -1.0)),
             P.box((X_IN, -15.3, -2.01), (X_OUT, -13.6, 28.5)), P.box((X_IN, 13.6, -2.01), (X_OUT, 15.3, 28.5))]
    mount = [P.box((X_IN, -11.0, ZI0 - 0.01), (X_OUT, 11.0, -14.5))]            # 5991 mount web (closes the DFR channel below z -14.5)
    f = P.union([pack] + walls() + joint + mount + xb + pb + lb)
    return f - P.union(xc + pc + lc + common_cuts())


def lid(skeletal):
    l = P.box((X_LID, -HW, Z0), (X_BACK, HW, Z1))
    cuts = [P.cyl_x(1.1, X_LID - 1, X_BACK + 1, y, z) for y, z in LID_BOSSES]
    if skeletal:
        b = 4.0
        bars = [(12.7, 15.1), (-16.0, -13.6)]                   # between the boards (upper trimmers z 16.63); under the lower board (lower trimmers z -10.77)
        edges = [Z0 + b + 3.0] + [v for bar in bars[::-1] for v in bar[::-1]][::-1]
        spans = [(ZI0 + 4.0, bars[1][0]), (bars[1][1], bars[0][0]), (bars[0][1], Z1 - b)]
        for z0, z1 in spans:
            cuts.append(P.box((X_LID - 1, -HW + b, z0), (X_BACK + 1, HW - b, z1)))
    return l - P.union(cuts)


def export(man, name):
    m = P.clean_mesh(man) if hasattr(P, 'clean_mesh') else P.from_m(man)
    m.export(HERE / name); return m


if __name__ == '__main__':
    info = dict(box=dict(x=[X_LID, X_OUT], frameX=[X_BACK, X_OUT], absY=HW, z=[Z0, Z1], wall=T, innerDepth=round(X_IN - X_BACK, 2),
                         innerZ=[ZI0, ZI1], outerSize=[round(X_OUT - X_LID, 2), 2 * HW, Z1 - Z0]))
    fr = frame_variant(); fi = integrated_variant(); ls = lid(False); lk = lid(True)
    for man, nm in ((fr, 'frame_D-world.stl'), (fi, 'pack_integrated_D-world.stl'), (ls, 'lid_solid-world.stl'), (lk, 'lid_skeletal-world.stl')):
        mm = export(man, nm); info[nm] = dict(volume_mm3=round(float(man.volume()), 1), genus=int(man.genus()), bodies=len(mm.split(only_watertight=False)), bounds=np.round(mm.bounds, 2).tolist())
    src = trimesh.load(str(XL_SRC), force='mesh'); info['boards'] = {}
    for nm, zc in BOARDS.items():
        m = trimesh.Trimesh(xl_place(src.vertices, zc), src.faces, process=False); m.export(HERE / f'xl4015_{nm}-world.stl')
        m.simplify_quadric_decimation(face_count=12000).export(HERE / 'render' / f'xl4015_{nm}.stl')
        info['boards'][nm] = dict(centre=[XL_MID_X, 0.0, zc], worldBounds=np.round(m.bounds, 2).tolist(), INend='+y', OUTend='-y',
                                  inEntries=np.round(xl_place([(2.5, 30.15, dz) for dz in (2.5, -2.5)], zc), 2).tolist(),
                                  outEntries=np.round(xl_place([(2.5, -30.15, dz) for dz in (2.5, -2.5)], zc), 2).tolist(),
                                  trimmerTops=np.round(xl_place([(11.15, -10.44, 11.57), (11.15, 0.06, 11.57)], zc), 2).tolist(),
                                  screwAxes=np.round(xl_place([(PCB_MID, a, b) for a, b in XL_HOLES_L], zc), 2).tolist())
    bx = pd_boxes()
    trimesh.util.concatenate([trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2)) for lo, hi in bx.values()]).export(HERE / 'pd5991_standing-world.stl')
    pdlo = np.min([b[0] for b in bx.values()], axis=0); pdhi = np.max([b[1] for b in bx.values()], axis=0)
    lower_bottom = ZC_LO - HALF_W
    info['pd5991'] = dict(boxes={k: [lo.round(3).tolist(), hi.round(3).tolist()] for k, (lo, hi) in bx.items()}, extent=[pdlo.round(2).tolist(), pdhi.round(2).tolist()],
                          room=dict(floorInnerZ=ZI0, lowerBoardBottomZ=lower_bottom, roomMm=round(lower_bottom - ZI0, 2), needed='29 (brief); PCB 27.813 + USB-C 1.143 past the edge = 28.956',
                                    terminalTopZ=round(float(bx['term'][1][2]), 2), terminalTopToLowerBoardMm=round(lower_bottom - float(bx['term'][1][2]), 2), pcbTopToLowerBoardMm=round(lower_bottom - float(bx['pcb'][1][2]), 2)),
                          usbOpening=dict(x=list(USB_OPEN['x']), y=list(USB_OPEN['y']), wall='bottom z -44..-42.8'),
                          plugEnvelope=[[-57.0, -6.5, Z0 - 20.0], [-49.5, 6.5, ZI0]])
    info['windows'] = windows(); info['lidBosses'] = LID_BOSSES
    # envelope gaps at HOME
    man_ = ia_lib.manifest(); SKIP = set(P.RETIRED) | set(P.SELF_KEYS) | {'rear_pack_cover', 'rear_pack', 'rear_frame', 'rear_lid', 'xl4015_left', 'xl4015_right', 'pd5991'}   # C2 parts in the manifest are what D replaces
    G = lambda a, b, s=10.0: round(float(a.min_gap(b, s)), 3); O = lambda a, b: round(float((a ^ b).volume()), 3)
    V18 = P.mesh_to_m(P.load_stl(P.WORLD / 'rear_pack-v18.stl')); ORB = P.mesh_to_m(P.openrb_mesh())
    env = {}
    for vname, body in (('frame_on_v18', fr + ls), ('integrated', fi + ls)):
        mb = P.from_m(body).bounds; rows = {}
        for k, rec in man_.items():
            if k in SKIP:
                continue
            lo, hi = np.array(rec['bounds'])
            if np.all(lo - 10 <= mb[1]) and np.all(hi + 10 >= mb[0]):
                S = P.solid_m(k); rows[k] = dict(module=rec.get('module'), gapMm=G(body, S), overlapMm3=O(body, S))
        if vname == 'frame_on_v18':
            rows['rear_pack-v18 (as built)'] = dict(gapMm=G(body, V18), overlapMm3=O(body, V18), note='cover seat: contact by design')
            rows['rear_pack-v19'] = dict(gapMm=G(fr - P.box((-45.01, -40, -50), (0, 40, 50)), P.solid_m('rear_pack')), note='box part x <= -45 only')
        rows['openrb-board-upright'] = dict(gapMm=G(body, ORB), overlapMm3=O(body, ORB))
        for nm in BOARDS:
            Bm = P.mesh_to_m(P.load_stl(HERE / f'xl4015_{nm}-world.stl')) if False else None
        env[vname] = dict(sorted(rows.items(), key=lambda kv: kv[1]['gapMm']))
    plug = P.box((-57.0, -6.5, Z0 - 20.0), (-49.5, 6.5, Z0))
    cable = P.box((-31.4, -7.3, Z0 - 25.0), (-23.9, 6.7, Z0))                      # OpenRB USB-C data cable in the floor slot, 25 mm down
    prow = {'openrb_floor_slot_cable (slot x -31.4..-23.9 extended 25 down)': dict(gapMm=G(plug, cable, 40.0)),
            'rear_pack-v18 floor': dict(gapMm=G(plug, V18, 20.0)), 'rear_pack-v19 floor': dict(gapMm=G(plug, P.solid_m('rear_pack'), 20.0))}
    for k, rec in man_.items():
        if k in SKIP:
            continue
        lo, hi = np.array(rec['bounds'])
        if np.all(lo - 20 <= [-49.5, 6.5, Z0]) and np.all(hi + 20 >= [-57.0, -6.5, Z0 - 20]):
            prow[k] = dict(module=rec.get('module'), gapMm=G(plug, P.solid_m(k), 20.0), overlapMm3=O(plug, P.solid_m(k)))
    env['usbcPlugEnvelope'] = dict(box=[[-57.0, -6.5, Z0 - 20.0], [-49.5, 6.5, Z0]], parts=dict(sorted(prow.items(), key=lambda kv: kv[1]['gapMm'])))
    # boards inside each variant body
    def hull_solid(mesh, zc):
        parts = []
        for p_ in mesh.split(only_watertight=False):
            if len(p_.vertices) < 4 or np.ptp(p_.vertices, axis=0).min() <= 1e-3:
                continue
            if np.ptp(p_.vertices, axis=0).max() > 60:     # PCB: measured slab at the holes (local X -2.0..-0.35), not its pad hull
                parts.append(P.box((XL_MID_X - 0.825 - 1.65, -30.85, zc - HALF_W), (XL_PIN_FACE_X, 30.85, zc + HALF_W))); continue
            parts.append(m3.Manifold.hull_points(np.asarray(p_.vertices, float)))
        return P.union(parts)
    XLm = {nm: hull_solid(trimesh.load(str(HERE / f'xl4015_{nm}-world.stl'), force='mesh'), BOARDS[nm]) for nm in BOARDS}
    PDm = P.mesh_to_m(trimesh.load(str(HERE / 'pd5991_standing-world.stl'), force='mesh').convex_hull)
    inside = {}
    for vname, body in (('frame', fr), ('integrated', fi)):
        inside[vname] = {nm: dict(overlapMm3=O(body, S)) for nm, S in list(XLm.items()) + [('pd5991', PDm)]}
        inside[vname]['lidSolid'] = {nm: dict(gapMm=G(ls, S, 5.0)) for nm, S in list(XLm.items()) + [('pd5991', PDm)]}
        inside[vname]['gapsMm'] = {nm: G(body, S, 5.0) for nm, S in list(XLm.items()) + [('pd5991', PDm)]}
    inside['note'] = 'per-body convex hulls, PCB as the measured slab; gap 0 = seated on the bosses / PCB end against the wall (0.0 by the brief)'
    packv19 = P.mesh_to_m(P.load_stl(BP.parent / 'rear-pack-v19' / 'rear_pack-world.stl'))
    ext = fi - packv19
    env['integratedAddedPartsOnly'] = {k: dict(gapMm=G(ext, P.solid_m(k), 10.0), overlapMm3=O(ext, P.solid_m(k))) for k in ('shell_left', 'shell_right', 'lower', 'right_lower', 'ring2', 'ring7', 'motor10', 'motor5', 'torso_base')}
    env['bodies'] = dict(packV19=len(P.from_m(packv19).split(only_watertight=False)), integrated=len(P.from_m(fi).split(only_watertight=False)),
                         integratedVolumes=sorted([round(float(b_.volume), 1) for b_ in P.from_m(fi).split(only_watertight=False)]))
    env['boardsInBody'] = inside
    # shell questions for the integrated version
    sh = {k: P.solid_mesh(k) for k in ('shell_left', 'shell_right')}
    shell = {}
    for k, m in sh.items():
        v = m.vertices; s = 1 if k == 'shell_left' else -1
        rear = v[v[:, 0] < -44.0]
        shell[k] = dict(rearmostX=round(float(v[:, 0].min()), 2), maxAbsYNearRear=round(float(np.abs(rear[:, 1]).max()), 2),
                        topZNearRear=round(float(rear[:, 2].max()), 2), topZ=round(float(v[:, 2].max()), 2))
    shell['boxSideAbsY'] = HW; shell['boxFrontPlaneX'] = X_IN; shell['boxTopZ'] = Z1
    env['shells'] = shell
    info['envelope'] = env
    P.jdump(info, HERE / 'layout_d.json')
    print(json.dumps({k: info[k] for k in ('box', 'windows')}, indent=0))
    print(json.dumps(info['pd5991']['room']))
    for k in ('frame_D-world.stl', 'pack_integrated_D-world.stl', 'lid_solid-world.stl', 'lid_skeletal-world.stl'):
        print(k, info[k])
    print(json.dumps(env, indent=0)[:6000])
