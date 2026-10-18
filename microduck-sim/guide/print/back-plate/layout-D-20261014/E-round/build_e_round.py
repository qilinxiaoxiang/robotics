"""Layout E-round (renders + numbers only, 2026-10-14): layout E (C2 vertical XL4015 at y +-17.2, IN down, OUT up; 5991
flat in a narrow pocket, USB-C -y, terminal +y; top-wall OUT windows) with the 45 deg chamfer replaced by a straight step
and every outer edge rounded through shellkit (rear edges, y-z corners, concave step blend), lid rounded to match.
The step sits 0.5 under the IN wire zone (5 mm under the board bottoms, where the IN wires leave the terminals and bend),
so the full-width part ends at z -27.1 instead of the chamfer start -21.4.
Wires (for the shell / frame clearance numbers): both OUT pairs loop over the top wall through the E top windows, run down
the rear lane and forward through the centre lane to the C2 passage (y +-3.5, z 23..27); the 15 V star leaves the 5991
terminal through the +y pocket window, loops, rises in the lane and reaches each IN terminal from below.
World = guide frame (mm). Writes STLs, layout_e_round.json."""
import sys, json, copy
from pathlib import Path
import numpy as np, trimesh
import manifold3d as m3
from shapely.geometry import box as sbox
from shapely.ops import unary_union
HERE = Path(__file__).resolve().parent; DD = HERE.parent; BP = DD.parent; PRINT = BP.parent
sys.path.insert(0, str(DD)); sys.path.insert(0, str(BP)); sys.path.insert(0, str(PRINT / 'rear-pack')); sys.path.insert(0, str(BP / 'layout-F'))
sys.argv = sys.argv[:1] + ['F']
import build_rear_plate as C
import pack_lib as P, build_rear_pack as BRP, ia_lib
import shellkit as K
import build_f as BF                                     # outline_poly, offset helpers, gap, search, trim

X_IN, X_OUT, X_LI = -47.0, -45.0, -65.9; T = 1.2; X_LID = X_LI - T
HW, Z1 = 32.05, 43.0; YI, ZI1 = HW - T, Z1 - T
PY_IN = 27.813 / 2 + 0.5; PY_OUT = PY_IN + T
ZB_OUT = -47.0; ZB_IN = ZB_OUT + T
BOARD_BOTTOM = C.XL_ZC - 30.85                           # -20.4
Z_STEP_IN = BOARD_BOTTOM - 5.0 - 0.5                     # under the IN wire zone: -25.9
Z_STEP_OUT = Z_STEP_IN - T
C.PD_TOP_Z = ZB_IN + 0.5 + 20.32                         # -24.98 (layout E)
TERM_W = (-5.17, 5.0); BEND = 3.0; WIRE_R = 0.9
X_E = C.XL_MID_X - (2.5 + 1.175); X_W = X_LI + WIRE_R + 0.4
LID_SCREWS = [(0.0, 35.0), (0.0, -14.0)]            # centre lane |y| <= 4.1 between the boards (C used two lid screws too)
GRAMS = BF.GRAMS


def outline():
    W = K.Rect(-HW, HW, Z_STEP_OUT, Z1, 0.0, 0.0, 'side', 'top', 'step')
    N = K.Rect(-PY_OUT, PY_OUT, ZB_OUT, Z_STEP_OUT + 8.0, 0.0, 0.0, 'nside', 'top', 'nbot')
    return K.Outline(W=W, N=N, rf=0.0, R=dict(side=1.3, top=1.3, step=1.3, nside=1.3, nbot=1.3), X_LID=X_LID, X_IN=X_IN, T=T)


def top_windows():
    out = {}
    for nm, (_, yc) in C.BOARDS.items():
        ys = sorted([yc - TERM_W[1] - 2.8, yc - TERM_W[0] + 2.8])
        out[nm] = dict(x=[X_LI, round(C.XL_PIN_FACE_X, 3)], y=[round(ys[0], 2), round(ys[1], 2)], z=[ZI1, Z1])
    return out


def windows():
    w = {f'top_{k}': dict(x=v['x'], y=v['y'], z=v['z'], wall='top') for k, v in top_windows().items()}
    zc = C.PD_TOP_Z - 10.16; tb = C.pd_boxes()['term']
    w['pd5991_usbc'] = dict(x=[-57.5, -49.0], y=[-HW - 10, -13.9], z=[round(zc - 7.0, 2), round(zc + 7.0, 2)], wall='-y pocket')
    zl = [C.PD_TOP_Z - 8.51 + 1.0, C.PD_TOP_Z - 12.01 - 1.3]                       # outermost 15 V loop levels (two wires per clamp)
    w['pd5991_term'] = dict(x=[X_LI, round(C.PD_BACK_X - 4.6 + 1.5, 2)], y=[13.9, HW + 10], z=[round(zl[1] - 1.3, 2), round(zl[0] + 1.3, 2)], wall='+y pocket')
    return w


def in_window_band(p):
    for k, w in windows().items():
        if w['wall'] == 'top':
            if w['x'][0] - 1.5 <= p[0] <= w['x'][1] + 0.5 and w['y'][0] - 0.2 <= p[1] <= w['y'][1] + 0.2 and p[2] >= ZI1 - 8:
                return True
        elif w['x'][0] - 1.5 <= p[0] <= w['x'][1] + 0.5 and w['z'][0] - 0.2 <= p[2] <= w['z'][1] + 0.2 and (p[1] >= 6 if w['y'][0] > 0 else p[1] <= -6):
            return True
    return False


def window_cuts():
    cs = []
    for k, w in windows().items():
        if w['wall'] == 'top':
            cs.append(P.box((w['x'][0] - 0.01, w['y'][0], ZI1 - 8.0), (w['x'][1], w['y'][1], Z1 + 12)))
        elif k == 'pd5991_usbc':
            cs.append(P.box((w['x'][0], w['y'][0], w['z'][0]), (w['x'][1], w['y'][1], w['z'][1])))
        else:
            cs.append(P.box((w['x'][0] - 0.01, PY_IN - 6.0, w['z'][0]), (w['x'][1], w['y'][1], w['z'][1])))
    return cs


def wires():
    """E plan, made explicit for the check.
    OUT: each wire leaves its terminal upward (entry z 40.6), loops over the top wall through the E top window and comes
    back down behind the terminal block at the lane plane X_W; the inner wire of the pair (entry nearer y 0) runs inward
    at z 36.3, the outer at z 34.4, both diagonally forward to x -55 / -57 in the centre lane (|y| <= 4.1, in front of the
    top lid boss at x <= -60.3), down to the passage rows z 25.95 / 24.05 at y +-1.1 and forward through the C2 passage.
    15 V: the 5991 terminal clamps two wires per pole; they leave +y through the pocket window, loop and come back in
    behind the 5991 (lane x -65.9..-60.1) in two planes (left board X_W, right board X_W + 2.1), rise in the pocket,
    and at the IN wire zone (z -24.4 / -22.3) turn outward and forward to the IN entries (z -19.7) from below."""
    g = {}
    zfar = 41.21 + 0.64 + BEND
    ze = C.XL_ZC + 30.15
    for nm, (_, yc) in C.BOARDS.items():
        s = 1 if yc > 0 else -1; net = '7V' if nm == 'left' else '5V'
        y_in, y_out = yc - s * 2.5, yc + s * 2.5
        g[f'{net}_a'] = [(X_E, y_in, ze), (X_E, y_in, zfar), (X_W, y_in, zfar), (X_W, y_in, 36.3), (X_W, s * 7.2, 36.3), (-55.0, s * 7.2, 36.3),
                         (-55.0, s * 1.1, 36.3), (-55.0, s * 1.1, 25.95), (X_OUT + 4.0, s * 1.1, 25.95)]
        g[f'{net}_b'] = [(X_E, y_out, ze), (X_E, y_out, zfar), (X_W, y_out, zfar), (X_W, y_out, 34.2), (X_W, s * 9.2, 34.2), (-57.0, s * 9.2, 34.2),
                         (-57.0, s * 1.1, 34.2), (-57.0, s * 1.1, 24.05), (X_OUT + 4.0, s * 1.1, 24.05)]
    zu = [C.PD_TOP_Z - 8.51, C.PD_TOP_Z - 12.01]; xe5 = C.PD_BACK_X - 4.6; face = 13.696; X2 = X_W + 2.1
    ZP, ZQ = -24.6, -22.7
    spec = {'15V_L_p': (X_W, zu[0] + 1.0, 8.5, 17.2 - 2.5, ZP), '15V_R_p': (X2, zu[0] - 1.0, 8.0, -17.2 - 2.5, ZQ),
            '15V_L_q': (X_W, zu[1] + 0.6, 6.3, 17.2 + 2.5, ZQ), '15V_R_q': (X2, zu[1] - 1.3, 6.0, -17.2 + 2.5, ZP)}
    for k, (xp, zl, yl, yt, zc) in spec.items():
        g[k] = [(xe5, face - 0.5, zl), (xe5, 17.4, zl), (xp, 17.4, zl), (xp, yl, zl), (xp, yl, zc), (xp, yt, zc), (X_E, yt, zc), (X_E, yt, C.XL_ZC - 30.15)]
    return g


NET = {'7V_a': '7V', '7V_b': '7V', '5V_a': '5V', '5V_b': '5V', '15V_L_p': 'p', '15V_R_p': 'p', '15V_L_q': 'q', '15V_R_q': 'q'}


def bosses():
    parts, cuts = [], []
    for nm, (_, yc) in C.BOARDS.items():
        for h in C.xl_holes(yc):
            y, z = h[1], h[2]
            parts.append(P.cyl_x(C.BOSS['r'], C.XL_PIN_FACE_X, X_OUT, y, z))
            if z > 29.5 - C.BOSS['r']:
                parts.append(P.box((C.XL_PIN_FACE_X, y - 1.5, z), (X_IN, y + 1.5, ZI1 + 0.5)))
                if abs(y) > 20:
                    s = np.sign(y); parts.append(P.box((C.XL_PIN_FACE_X, min(y, s * (YI + 0.5)), z - 1.5), (X_IN, max(y, s * (YI + 0.5)), z + 1.5)))
            cuts.append(P.cyl_x(C.BOSS['pilot_r'], C.XL_PIN_FACE_X - 1, C.BOSS['pilot_to'], y, z))
    for h in C.pd_holes():
        parts.append(P.cyl_x(C.PD_BOSS['r'], C.PD_BACK_X, X_IN + 0.01, h[1], h[2])); cuts.append(P.cyl_x(0.8, C.PD_BACK_X - 1, -45.3, h[1], h[2]))
    for y, z in LID_SCREWS:
        parts.append(P.cyl_x(2.5, X_LI, X_LI + 5.6, y, z))
        if z > 0:
            parts.append(P.box((X_LI, y - 1.5, z), (X_LI + 5.6, y + 1.5, ZI1 + 0.5)))
        else:
            parts.append(P.box((X_LI, y - 1.5, z - 1.5), (X_IN, y + 1.5, z + 1.5)))      # 3 x 3 bar forward to the front plate
        cuts.append(P.cyl_x(0.8, X_LI - 1, X_LI + 5.2, y, z))
    return parts, cuts


def build(ol, outer, inner):
    shell = (outer - inner) ^ P.box((X_LI, -60, -60), (X_IN + 0.5, 60, 60))
    poly = BF.outline_poly(ol)
    web = P.extrude_yz(poly.intersection(sbox(-HW - 1, -80, HW + 1, -2.0)), X_IN, X_OUT)
    pb, pc = bosses()
    parts = P.union(pb) ^ (outer + P.extrude_yz(poly, X_IN - 0.5, X_OUT + 1))
    frame = P.union([shell, BRP.build_cover(), web, parts])
    cuts = pc + window_cuts() + [C.passage_cutter()] + [P.cyl_x(BRP.COVER['hole_r'], X_IN - 1, X_OUT + 1, y, z) for (y, z) in BRP.POST['holes']]
    frame = frame - P.union(cuts)
    lid = (outer ^ P.box((X_LID - 1, -60, -60), (X_LI, 60, 60))) - P.union([P.cyl_x(1.1, X_LID - 1, X_LI + 1, y, z) for y, z in LID_SCREWS])
    return frame, lid


def board_meshes():
    src = trimesh.load(str(BF.XL_SRC), force='mesh')
    return {nm: trimesh.Trimesh(C.xl_place(src.vertices, yc), src.faces, process=False) for nm, (_, yc) in C.BOARDS.items()}


def body_points(meshes, wp):
    pts, clr, tag = [], [], []
    for nm, m in meshes.items():
        v = np.unique(np.round(m.vertices, 3), axis=0)
        pts.append(v); clr.append(np.full(len(v), 0.3)); tag += [f'xl4015_{nm}'] * len(v)
    for k, (lo, hi) in C.pd_boxes().items():
        if k == 'usbc':
            continue
        c = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in np.linspace(lo[1], hi[1], 5) for z in np.linspace(lo[2], hi[2], 5)])
        pts.append(c); clr.append(np.where(np.abs(c[:, 1]) > 13.5, 0.2, 0.3)); tag += [f'pd5991:{k}'] * len(c)
    for nm, (_, yc) in C.BOARDS.items():                 # IN wire zone (5 mm under the board bottom over the terminal width)
        ys = sorted([yc - TERM_W[1], yc - TERM_W[0]])
        c = np.array([[x, y, z] for x in (-61.805, -51.805) for y in ys for z in (BOARD_BOTTOM - 5.0, BOARD_BOTTOM)])
        pts.append(c); clr.append(np.full(len(c), 0.3)); tag += [f'IN wire zone {nm}'] * len(c)
    for k, w in wp.items():
        p = K.fillet_path(w, BEND); p = np.array([q for q in p if q[0] < X_IN - 0.5])
        pts.append(p); clr.append(np.minimum(WIRE_R + 0.3 + 0.1, (p[:, 0] - X_LI) - 1e-3)); tag += [f'wire {k}'] * len(p)
    P_ = np.vstack(pts); C_ = np.concatenate(clr)
    keep = np.array([not in_window_band(q) for q in P_])
    return P_[keep], C_[keep], [t for t, k in zip(tag, keep) if k]


if __name__ == '__main__':
    out = {}
    BF.LID_SCREWS[:] = LID_SCREWS                       # search_radii reads the lid screw list from build_f
    meshes = board_meshes(); WP = wires(); ol = outline()
    pts, clr, tags = body_points(meshes, WP)
    olb = copy.deepcopy(ol); body_only = BF.search_radii(olb, pts, clr, tags, use_flat_rear=False)
    out['rounding'] = BF.search_radii(ol, pts, clr, tags); out['rounding']['bodiesOnlyNoLidScrews'] = body_only
    out['rounding']['final'] = dict(R={k: round(v, 2) for k, v in ol.R.items()}, rcTop=ol.W.rc_top, rcStep=ol.W.rc_bot, rcNbot=ol.N.rc_bot, rf=ol.rf)
    outer, inner = ol.solids(0.3)
    frame, lid = build(ol, outer, inner)
    for man, nm in ((frame, 'frame_Eround-world.stl'), (lid, 'lid_Eround-world.stl')):
        mm = P.from_m(man); mm.merge_vertices(); mm.export(HERE / nm)
        out[nm] = dict(volume_mm3=round(float(man.volume()), 1), grams=GRAMS(float(man.volume())), genus=int(man.genus()),
                       bodies=sum(1 for q in mm.split(only_watertight=False) if abs(q.volume) > 1.0), bounds=np.round(mm.bounds, 2).tolist())
    out['massTotalG'] = round(out['frame_Eround-world.stl']['grams'] + out['lid_Eround-world.stl']['grams'], 2)
    out['massLayoutE_sharp_solidLid'] = dict(frame=14.41, lidSolid=6.57, total=20.98)
    out['box'] = dict(x=[X_LID, X_OUT], absY=HW, z=[ZB_OUT, Z1], fullWidthDownToZ=Z_STEP_OUT, stepInnerZ=Z_STEP_IN,
                      pocket=dict(innerAbsY=round(PY_IN, 3), outerAbsY=round(PY_OUT, 3)), chamferReplacedBy='straight step at z %.1f (outer)' % Z_STEP_OUT)
    out['windows'] = windows(); out['lidScrews'] = LID_SCREWS
    bx = C.pd_boxes(); trimesh.util.concatenate([trimesh.creation.box(extents=np.array(hi) - np.array(lo), transform=trimesh.transformations.translation_matrix((np.array(lo) + np.array(hi)) / 2)) for lo, hi in bx.values()]).export(HERE / 'pd5991_Eround-world.stl')
    S = {}
    for nm, m in meshes.items():
        parts = []
        for p_ in m.split(only_watertight=False):
            if len(p_.vertices) < 4 or np.ptp(p_.vertices, axis=0).min() <= 1e-3:
                continue
            if np.ptp(p_.vertices, axis=0).max() > 60:
                yc = dict(C.BOARDS)[nm][1] if False else [v for k_, v in C.BOARDS.items() if k_ == nm][0][1]
                parts.append(P.box((C.XL_MID_X - 2.475, yc - 13.1, C.XL_ZC - 30.85), (C.XL_PIN_FACE_X, yc + 13.1, C.XL_ZC + 30.85))); continue
            parts.append(m3.Manifold.hull_points(np.asarray(p_.vertices, float)))
        S[nm] = P.union(parts)
    S['pd5991'] = P.union([P.box(lo, hi) for lo, hi in bx.values()])
    tubes, wrow = {}, {}
    FRAME_TM = P.from_m(frame); BF_TRIM = lambda q: BF.trim_start(BF.trim_start(q, 1.6)[::-1], 1.6)[::-1]
    for k, w in WP.items():
        p = K.fillet_path(w, BEND); tubes[k] = K.tube(p, WIRE_R)
        chk = K.tube(BF.trim_start(BF.trim_start(p, 1.6)[::-1], 1.6)[::-1], WIRE_R)
        wrow[k] = dict(net=NET[k], lengthMm=round(K.path_length(p), 1), minBendRadius=round(float(K.min_bend_radius(p)), 2),
                       gapFrame=BF.gap(chk, frame), frameNearest=K.nearest(BF_TRIM(p), FRAME_TM, WIRE_R), gapLid=BF.gap(chk, lid), gapBoards={nm: BF.gap(chk, s_) for nm, s_ in S.items()},
                       maxZ=round(float(p[:, 2].max() + WIRE_R), 2))
    ww = {}
    ks = list(WP)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b_ = ks[i], ks[j]
            same = NET[a] == NET[b_] and NET[a] in ('p', 'q')
            ta = tubes[a] if not same else K.tube(BF.trim_start(K.fillet_path(WP[a], BEND), 6.0), WIRE_R)
            tb = tubes[b_] if not same else K.tube(BF.trim_start(K.fillet_path(WP[b_], BEND), 6.0), WIRE_R)
            ww[f'{a}|{b_}'] = BF.gap(ta, tb, 5.0)
    out['wires'] = dict(perWire=wrow, wireWireGapMm=dict(sorted(ww.items(), key=lambda kv: kv[1])),
                        note='E-round wire runs are a check model of the E plan (not re-planned); a 0 wire-wire gap marks a crossing that needs a two-layer pass')
    P.jdump({k: dict(points=np.round(K.fillet_path(w, BEND), 3).tolist(), net=NET[k]) for k, w in WP.items()}, HERE / 'wires_Eround.json')
    man_ = ia_lib.manifest(); SKIP = set(P.RETIRED) | set(P.SELF_KEYS) | {'rear_pack_cover', 'rear_pack', 'rear_frame', 'rear_lid', 'xl4015_left', 'xl4015_right', 'pd5991'}
    body = frame + lid; mb = P.from_m(body).bounds; rows = {}
    allw = P.union([K.tube(K.fillet_path(w, BEND, n=4), WIRE_R, seg=8) for w in WP.values()])
    for k, rec in man_.items():
        if k in SKIP:
            continue
        lo, hi = np.array(rec['bounds'])
        if np.all(lo - 15 <= mb[1] + 6) and np.all(hi + 15 >= mb[0] - 6):
            S_ = P.solid_m(k); rows[k] = dict(module=rec.get('module'), boxGapMm=BF.gap(body, S_, 20.0), wiresGapMm=BF.gap(allw, S_, 20.0), overlapMm3=round(float((body ^ S_).volume()), 3))
    V18 = P.mesh_to_m(P.load_stl(P.WORLD / 'rear_pack-v18.stl')); ORB = P.mesh_to_m(P.openrb_mesh())
    rows['rear_pack-v18 (as built)'] = dict(boxGapMm=BF.gap(body, V18, 20.0), note='cover seat: contact by design')
    rows['openrb-board-upright'] = dict(boxGapMm=BF.gap(body, ORB, 20.0), wiresGapMm=BF.gap(allw, ORB, 20.0))
    out['clearancesHOME'] = dict(sorted(rows.items(), key=lambda kv: kv[1]['boxGapMm']))
    SH = {sk: P.solid_m(sk) for sk in ('shell_left', 'shell_right')}
    out['shellPerWire'] = {k: {sk: BF.gap(t, SH[sk], 20.0) for sk in SH} for k, t in tubes.items()}
    out['boardsVsFrame'] = {nm: dict(overlapMm3=round(float((frame ^ s_).volume()), 3), gapMm=BF.gap(frame, s_, 5.0)) for nm, s_ in S.items()}
    out['boardsVsLid'] = {nm: BF.gap(lid, s_, 5.0) for nm, s_ in S.items()}
    zc = C.PD_TOP_Z - 10.16; sy = float(bx['usbc'][0][1])
    plug = P.box((-57.0, sy - 25.0, zc - 6.5), (-49.5, sy, zc + 6.5)); prow = {}
    for k, rec in man_.items():
        if k in SKIP:
            continue
        lo, hi = np.array(rec['bounds'])
        if np.all(lo - 25 <= [-49.5, sy, zc + 6.5]) and np.all(hi + 25 >= [-57.0, sy - 25, zc - 6.5]):
            prow[k] = BF.gap(plug, P.solid_m(k), 30.0)
    prow['frame_Eround'] = BF.gap(plug, frame, 5.0)
    out['usbcPlugEnvelope'] = dict(box=[[-57.0, round(sy - 25.0, 2), round(zc - 6.5, 2)], [-49.5, round(sy, 2), round(zc + 6.5, 2)]], gapsMm=dict(sorted(prow.items(), key=lambda kv: kv[1])))
    P.jdump(out, HERE / 'layout_e_round.json')
    print(json.dumps({k: out[k] for k in ('rounding', 'box', 'massTotalG', 'boardsVsFrame', 'boardsVsLid')}, indent=0)[:5000])
    print(json.dumps(out['wires'], indent=0)[:4000])
