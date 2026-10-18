"""Layout E (renders + envelope numbers only, 2026-10-14): C2 vertical boards (y +-17.2, centre z 10.45, top edge 0.5 under
the top wall, IN down, OUT up), box z -44..43 with no top raise; two top-wall windows over the OUT terminals (wire enters
from above and loops back in); 5991 flat at the bottom (C2 orientation: USB-C to -y, terminal to +y) in a narrowed pocket,
inner |y| <= 14.4 (27.8 + 2 x 0.5), walls 1.2. Pocket floor at z -47 (inner -45.8): with the floor at -44 the 5991 top
reaches 3.42 mm into the IN wire zone, at -47 0.42 mm. Full-width section ends in a 45 deg chamfer that starts 0.5 under
the board corners. Lid = whole outer profile. Writes STLs and layout_e.json."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union
HERE = Path(__file__).resolve().parent; DD = HERE.parent; BP = DD.parent
sys.path.insert(0, str(BP)); sys.path.insert(0, str(BP.parent / 'rear-pack'))
import build_rear_plate as C
import pack_lib as P, build_rear_pack as BRP, ia_lib
S2 = 2 ** 0.5
X_IN, X_OUT, X_BACK, X_LID = -47.0, -45.0, -65.9, -67.1
HW, T, Z1 = 32.05, 1.2, 43.0
YI, ZI1 = HW - T, Z1 - T
PY_IN = 27.813 / 2 + 0.5; PY_OUT = PY_IN + T          # 14.41 / 15.61
ZB_OUT = -47.0; ZB_IN = ZB_OUT + T
BOARD_BOTTOM = C.XL_ZC - 30.85                          # -20.4
ZCH_IN = BOARD_BOTTOM - 0.5
K_IN = YI - ZCH_IN; K_OUT = K_IN + T * S2
def prof(hw, py, z_side, z_pocket, zb, ztop):
    return Polygon([(-hw, ztop), (hw, ztop), (hw, z_side), (py, z_pocket), (py, zb), (-py, zb), (-py, z_pocket), (-hw, z_side)])
OUTER = prof(HW, PY_OUT, HW - K_OUT, PY_OUT - K_OUT, ZB_OUT, Z1)
INNER = prof(YI, PY_IN, ZCH_IN, PY_IN - K_IN, ZB_IN, ZI1)
C.PD_TOP_Z = ZB_IN + 0.5 + 20.32                        # -24.98
TERM_W = (-5.17, 5.0); BEND = 2.8
LID_SCREWS = [(0.0, 39.5), (-25.5, -24.0), (25.5, -24.0)]


def ext(poly, x0, x1):
    return P.extrude_yz(poly, x0, x1)


def top_windows():
    out = {}
    for nm, (_, yc) in C.BOARDS.items():
        ys = sorted([yc - TERM_W[1] - BEND, yc - TERM_W[0] + BEND])
        out[nm] = dict(x=[X_BACK, round(C.XL_PIN_FACE_X, 3)], y=[round(ys[0], 2), round(ys[1], 2)], z=[ZI1, Z1])
    return out


def frame():
    walls = ext(OUTER, X_BACK, X_IN) - ext(INNER, X_BACK - 1, X_IN + 1)
    web = ext(OUTER.intersection(sbox(-HW - 1, ZB_OUT - 1, HW + 1, -2.0)), X_IN, X_OUT)
    front_low = P.box((X_IN, -PY_OUT, ZB_OUT), (X_OUT, PY_OUT, -44.0 + 0.01))
    parts, cuts = [BRP.build_cover(), web, front_low, walls], []
    for nm, (_, yc) in C.BOARDS.items():
        for h in C.xl_holes(yc):
            y, z = h[1], h[2]
            parts.append(P.cyl_x(C.BOSS['r'], C.XL_PIN_FACE_X, X_OUT, y, z))
            if z > 29.5 - C.BOSS['r']:
                parts.append(P.box((C.XL_PIN_FACE_X, y - 1.5, z), (X_IN, y + 1.5, ZI1 + 0.01)))
                if abs(y) > 20:
                    s = np.sign(y); parts.append(P.box((C.XL_PIN_FACE_X, min(y, s * (YI + 0.01)), z - 1.5), (X_IN, max(y, s * (YI + 0.01)), z + 1.5)))
            cuts.append(P.cyl_x(C.BOSS['pilot_r'], C.XL_PIN_FACE_X - 1, C.BOSS['pilot_to'], y, z))
    for h in C.pd_holes():
        parts.append(P.cyl_x(C.PD_BOSS['r'], C.PD_BACK_X, X_IN + 0.01, h[1], h[2])); cuts.append(P.cyl_x(0.8, C.PD_BACK_X - 1, -45.3, h[1], h[2]))
    for y, z in LID_SCREWS:
        parts.append(P.cyl_x(2.5, X_BACK, X_BACK + 5.6, y, z))
        if z > 0:
            parts.append(P.box((X_BACK, y - 2.5, z), (X_BACK + 5.6, y + 2.5, ZI1 + 0.01)))
        else:
            s = np.sign(y); parts.append(P.box((X_BACK, min(y, s * (abs(y) + 5)), z - 2.5), (X_BACK + 5.6, max(y, s * (abs(y) + 5)), z + 2.5)))
        cuts.append(P.cyl_x(0.8, X_BACK - 1, X_BACK + 5.2, y, z))
    body = P.union(parts) - ext(OUTER.buffer(10).difference(OUTER), X_BACK - 1, X_IN - 0.001)    # trim lid-boss ribs to the outline
    for (y, z) in BRP.POST['holes']:
        cuts.append(P.cyl_x(BRP.COVER['hole_r'], X_IN - 1, X_OUT + 1, y, z))
    for w in top_windows().values():
        cuts.append(P.box((w['x'][0] - 1, w['y'][0], ZI1 - 0.01), (w['x'][1], w['y'][1], Z1 + 1)))
    zc = C.PD_TOP_Z - 10.16
    cuts.append(P.box((-57.5, -HW - 10, zc - 7.0), (-49.0, -13.9, zc + 7.0)))                       # USB-C: overmold 13 x 7.5 + 0.5
    tb = C.pd_boxes()['term']
    cuts.append(P.box((tb[0][0] - 0.5, 13.9, tb[0][2] - BEND), (tb[1][0] + 0.5, HW + 10, tb[1][2] + BEND)))   # terminal window (+y)
    return body - P.union(cuts)


def lid(skeletal):
    l = ext(OUTER, X_LID, X_BACK)
    holes = [P.cyl_x(1.1, X_LID - 1, X_BACK + 1, y, z) for y, z in LID_SCREWS]
    if skeletal:
        keep = unary_union([sbox(-1.5, -60, 1.5, 60), sbox(-HW, -22.0, HW, -19.0)] + [Point(y, z).buffer(4.5) for y, z in LID_SCREWS])
        holes.append(ext(OUTER.buffer(-4.0, join_style=2).difference(keep), X_LID - 1, X_BACK + 1))
    return l - P.union(holes)


if __name__ == '__main__':
    F = frame(); Ls = lid(False); Lk = lid(True); out = {}
    for man, nm in ((F, 'frame_E-world.stl'), (Ls, 'lid_solid_E-world.stl'), (Lk, 'lid_skeletal_E-world.stl')):
        mm = P.clean_mesh(man); mm.export(HERE / nm)
        out[nm] = dict(volume_mm3=round(float(man.volume()), 1), grams=round(float(man.volume()) / 1000 * 1.24 * 0.851, 2), genus=int(man.genus()),
                       bodies=len(mm.split(only_watertight=False)), bounds=np.round(mm.bounds, 2).tolist())
    bx = C.pd_boxes()
    trimesh.util.concatenate([trimesh.creation.box(extents=np.array(hi) - np.array(lo), transform=trimesh.transformations.translation_matrix((np.array(lo) + np.array(hi)) / 2)) for lo, hi in bx.values()]).export(HERE / 'pd5991_E-world.stl')
    zc = C.PD_TOP_Z - 10.16
    out['box'] = dict(x=[X_LID, X_OUT], absY=HW, z=[ZB_OUT, Z1], fullWidthDownToZ=round(HW - K_OUT, 3), pocket=dict(innerY=round(PY_IN, 3), outerY=round(PY_OUT, 3), innerZ=[ZB_IN, round(PY_IN - K_IN, 3)], outerTopZ=round(PY_OUT - K_OUT, 3)),
                      chamfer='45 deg; inner from (|y| 30.85, z -20.9) to (|y| 14.41, z %.2f)' % (PY_IN - K_IN))
    out['windows'] = dict(top=top_windows(), usbc=dict(x=[-57.5, -49.0], y='-y pocket/chamfer wall', z=[round(zc - 7.0, 2), round(zc + 7.0, 2)]),
                          pd5991Terminal=dict(x=[round(float(bx['term'][0][0]) - 0.5, 2), round(float(bx['term'][1][0]) + 0.5, 2)], y='+y pocket/chamfer wall', z=[round(float(bx['term'][0][2]) - BEND, 2), round(float(bx['term'][1][2]) + BEND, 2)]))
    pcb = bx['pcb']
    out['pd5991'] = dict(pcbZ=[round(float(pcb[0][2]), 2), round(float(pcb[1][2]), 2)], pcbY=[round(float(pcb[0][1]), 3), round(float(pcb[1][1]), 3)], roomZ=[ZB_IN, BOARD_BOTTOM],
                         roomMm=round(BOARD_BOTTOM - ZB_IN, 2), needed='20.32 + 0.5 floor', topToBoardBottomMm=round(BOARD_BOTTOM - float(pcb[1][2]), 2),
                         terminalEntryFaceY=round(float(bx['term'][1][1]), 3), terminalFaceToPocketWallMm=round(PY_IN - float(bx['term'][1][1]), 2),
                         usbSocketFaceY=round(float(bx['usbc'][0][1]), 3), usbSocketPastPocketWallMm=round(-PY_IN - float(bx['usbc'][0][1]), 2))
    # IN wire zones (5 mm under the board bottoms, terminal block width), as in C2
    man_ = ia_lib.manifest(); SKIP = set(P.RETIRED) | set(P.SELF_KEYS) | {'rear_pack_cover', 'rear_pack', 'rear_frame', 'rear_lid', 'xl4015_left', 'xl4015_right', 'pd5991'}
    G = lambda a, b, s=40.0: round(float(a.min_gap(b, s)), 3); O = lambda a, b: round(float((a ^ b).volume()), 3)
    PDm = P.mesh_to_m(trimesh.load(str(HERE / 'pd5991_E-world.stl'), force='mesh').convex_hull)
    zones = {}
    for nm, (_, yc) in C.BOARDS.items():
        ys = sorted([yc - TERM_W[1], yc - TERM_W[0]]); Z = P.box((-61.805, ys[0], BOARD_BOTTOM - 5.0), (-51.805, ys[1], BOARD_BOTTOM))
        zones[nm] = dict(box=[[-61.805, ys[0], BOARD_BOTTOM - 5.0], [-51.805, ys[1], BOARD_BOTTOM]], frameOverlapMm3=O(Z, F), frameGapMm=G(Z, F, 10.0),
                         pd5991ProjectedZOverlapMm=round(max(0.0, float(pcb[1][2]) - (BOARD_BOTTOM - 5.0)), 2), pd5991Gap3dMm=G(Z, PDm, 10.0),
                         roomBelowZoneToChamferMm=round((BOARD_BOTTOM - 5.0) - (max(abs(ys[0]), abs(ys[1])) - K_IN), 2))
    out['inWireZones'] = zones
    body = F + Ls; mb = P.from_m(body).bounds; rows = {}
    for k, rec in man_.items():
        if k in SKIP:
            continue
        lo, hi = np.array(rec['bounds'])
        if np.all(lo - 15 <= mb[1]) and np.all(hi + 15 >= mb[0]):
            S = P.solid_m(k); rows[k] = dict(module=rec.get('module'), gapMm=G(body, S), overlapMm3=O(body, S))
    V18 = P.mesh_to_m(P.load_stl(P.WORLD / 'rear_pack-v18.stl')); ORB = P.mesh_to_m(P.openrb_mesh())
    rows['rear_pack-v18 (as built)'] = dict(gapMm=G(body, V18), overlapMm3=O(body, V18), note='cover seat: contact by design')
    rows['openrb-board-upright'] = dict(gapMm=G(body, ORB), overlapMm3=O(body, ORB))
    out['clearancesHOME'] = dict(sorted(rows.items(), key=lambda kv: kv[1]['gapMm']))
    plug = P.box((-57.0, -float(-bx['usbc'][0][1]) - 20.0, zc - 6.5), (-49.5, float(bx['usbc'][0][1]), zc + 6.5))
    prow = {}
    for k, rec in man_.items():
        if k in SKIP:
            continue
        lo, hi = np.array(rec['bounds'])
        if np.all(lo - 20 <= [-49.5, -15, zc + 6.5]) and np.all(hi + 20 >= [-57.0, -35.1, zc - 6.5]):
            prow[k] = G(plug, P.solid_m(k), 20.0)
    prow['frame_E'] = G(plug, F, 5.0)
    out['usbcPlugEnvelope'] = dict(box=[[-57.0, round(float(bx['usbc'][0][1]) - 20.0, 2), round(zc - 6.5, 2)], [-49.5, round(float(bx['usbc'][0][1]), 2), round(zc + 6.5, 2)]], gapsMm=dict(sorted(prow.items(), key=lambda kv: kv[1])))
    out['boardsVsFrame'] = {nm: O(F, P.mesh_to_m(trimesh.load(str(BP / f'xl4015_{nm}-world.stl'), force='mesh').convex_hull)) for nm in ('left', 'right')}
    out['pd5991VsFrame'] = dict(overlapMm3=O(F, PDm), gapMm=G(F, PDm, 5.0))
    P.jdump(out, HERE / 'layout_e.json'); print(json.dumps(out, indent=0)[:6000])
