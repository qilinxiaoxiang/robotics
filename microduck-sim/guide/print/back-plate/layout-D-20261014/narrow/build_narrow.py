"""Layout D narrowed (renders only, 2026-10-14): above the lower XL4015 as layout D; below it a narrow pocket for the
standing 5991 (inner |y| <= 10.66 = 20.32/2 + 0.5, walls 1.2, outer |y| <= 11.86) down to a new bottom at z -47.
Transition: 45 deg chamfer (inner face starts 0.5 under the lower board corners at |y| 30.85, z -12.8), self-supporting
when printed upright. The pocket has its own back wall (x -67.1..-65.9); the lid covers the full-width part and the
chamfer down to z -33.49. Frame on the pack (split version). Writes STLs, narrow.json."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union
HERE = Path(__file__).resolve().parent; DD = HERE.parent
sys.path.insert(0, str(DD))
import build_layout_d as D
P, BRP = D.P, D.BRP
S2 = 2 ** 0.5
HW, T = D.HW, D.T
PY_IN = D.PD['pcb'][0] / 2 + 0.5                  # 10.66
PY_OUT = PY_IN + T                                # 11.86
ZB_OUT = -47.0; ZB_IN = ZB_OUT + T                # floor -47..-45.8
LOWER_BOTTOM = D.ZC_LO - D.HALF_W                 # -12.3
ZCH_IN = LOWER_BOTTOM - 0.5                       # inner chamfer starts at (|y| 30.85, z -12.8)
# inner chamfer z = |y| - (30.85 - ZCH_IN) ; outer chamfer parallel, 1.2 normal offset
K_IN = D.YI - ZCH_IN; K_OUT = K_IN + T * S2
Z_IN_POCKET = PY_IN - K_IN; Z_OUT_POCKET = PY_OUT - K_OUT; Z_OUT_SIDE = HW - K_OUT
def prof(hw, py, z_side, z_pocket, zb, ztop):
    return Polygon([(-hw, ztop), (hw, ztop), (hw, z_side), (py, z_pocket), (py, zb), (-py, zb), (-py, z_pocket), (-hw, z_side)])
OUTER = prof(HW, PY_OUT, Z_OUT_SIDE, Z_OUT_POCKET, ZB_OUT, D.Z1)
INNER = prof(D.YI, PY_IN, ZCH_IN, Z_IN_POCKET, ZB_IN, D.ZI1)
Z_LID_BOTTOM = Z_OUT_POCKET                       # lid = outer profile above the pocket walls
LID_OUTLINE = OUTER.intersection(sbox(-HW - 1, Z_LID_BOTTOM, HW + 1, D.Z1 + 1))
POCKET_BACK = OUTER.intersection(sbox(-HW - 1, ZB_OUT - 1, HW + 1, Z_LID_BOTTOM))
LID_SCREWS = [(-12.5, -31.0), (12.5, -31.0)]       # bosses merge into the chamfer walls; 5991 parts at this height stay at x >= -54.9
# 5991 lowered: socket face flush with the new floor inner face
D.PD_VBOT = ZB_IN + (28.956 - 27.813)


def ext(poly, x0, x1):
    return P.extrude_yz(poly, x0, x1)


def frame():
    walls = ext(OUTER, D.X_BACK, D.X_IN) - ext(INNER, D.X_BACK - 1, D.X_IN + 1)
    back = ext(POCKET_BACK, D.X_LID, D.X_BACK + 0.01)
    web = ext(OUTER.intersection(sbox(-HW - 1, ZB_OUT - 1, HW + 1, -2.0)), D.X_IN, D.X_OUT)
    front_low = P.box((D.X_IN, -PY_OUT, ZB_OUT), (D.X_OUT, PY_OUT, -44.0 + 0.01))
    xb, xc = D.xl_bosses(); pb, pc = D.pd_bosses(D.X_IN + 0.01)
    lb, lc = [], []
    for y, z in LID_SCREWS:
        s = np.sign(y)
        lb += [P.cyl_x(2.5, D.X_BACK, D.X_BACK + 5.6, y, z), P.box((D.X_BACK, min(y, s * (abs(y) + 4.0)), z - 2.5), (D.X_BACK + 5.6, max(y, s * (abs(y) + 4.0)), z + 2.5))]
        lc.append(P.cyl_x(0.8, D.X_BACK - 1, D.X_BACK + 5.2, y, z))
    body = P.union([BRP.build_cover(), web, front_low, walls, back] + xb + pb + lb)
    cuts = xc + pc + lc + [P.cyl_x(BRP.COVER['hole_r'], D.X_IN - 1, D.X_OUT + 1, y, z) for (y, z) in BRP.POST['holes']]
    for w in D.windows().values():
        cuts.append(P.box((w['x'][0] - 1, w['y'][0] - 1 if w['y'][0] < 0 else w['y'][0] - 0.01, w['z'][0]), (w['x'][1], w['y'][1] + 0.01 if w['y'][1] > 0 else w['y'][1] + 1, w['z'][1])))
    cuts.append(P.box((D.USB_OPEN['x'][0], D.USB_OPEN['y'][0], ZB_OUT - 1), (D.USB_OPEN['x'][1], D.USB_OPEN['y'][1], ZB_IN + 0.01)))
    return body - P.union(cuts)


def lid(skeletal):
    l = ext(LID_OUTLINE, D.X_LID, D.X_BACK)
    holes = [P.cyl_x(1.1, D.X_LID - 1, D.X_BACK + 1, y, z) for y, z in LID_SCREWS]
    if skeletal:
        keep = unary_union([sbox(-HW, 12.7, HW, 15.1), sbox(-HW, -16.0, HW, -13.6)] + [Point(y, z).buffer(4.0) for y, z in LID_SCREWS])
        cut = LID_OUTLINE.buffer(-4.0, join_style=2).difference(keep)
        holes.append(ext(cut, D.X_LID - 1, D.X_BACK + 1))
    return l - P.union(holes)


if __name__ == '__main__':
    F = frame(); Ls = lid(False); Lk = lid(True)
    out = {}
    for man, nm in ((F, 'frame_Dn-world.stl'), (Ls, 'lid_solid_Dn-world.stl'), (Lk, 'lid_skeletal_Dn-world.stl')):
        mm = P.clean_mesh(man); mm.export(HERE / nm)
        out[nm] = dict(volume_mm3=round(float(man.volume()), 1), grams=round(float(man.volume()) / 1000 * 1.24 * 0.851, 2), genus=int(man.genus()),
                       bodies=len(mm.split(only_watertight=False)), bounds=np.round(mm.bounds, 2).tolist())
    bx = D.pd_boxes()
    trimesh.util.concatenate([trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2)) for lo, hi in bx.values()]).export(HERE / 'pd5991_standing_Dn-world.stl')
    out['pocket'] = dict(innerY=[-PY_IN, PY_IN], outerY=[-PY_OUT, PY_OUT], innerZ=[ZB_IN, round(Z_IN_POCKET, 3)], outerZ=[ZB_OUT, round(Z_OUT_POCKET, 3)], x=[D.X_LID, D.X_IN],
                         innerDepthX=round(D.X_IN - D.X_BACK, 2), chamfer=dict(inner=[[D.YI, ZCH_IN], [PY_IN, round(Z_IN_POCKET, 3)]], outer=[[HW, round(Z_OUT_SIDE, 3)], [PY_OUT, round(Z_OUT_POCKET, 3)]], angleDeg=45),
                         backWall=dict(x=[D.X_LID, D.X_BACK], z=[ZB_OUT, round(Z_LID_BOTTOM, 3)]), usbOpening=dict(x=list(D.USB_OPEN['x']), y=list(D.USB_OPEN['y']), z=[ZB_OUT, ZB_IN]))
    out['pd5991'] = dict(pcbZ=[round(float(bx['pcb'][0][2]), 3), round(float(bx['pcb'][1][2]), 3)], terminalTopZ=round(float(bx['term'][1][2]), 3),
                         terminalTopToLowerBoardMm=round(LOWER_BOTTOM - float(bx['term'][1][2]), 2), pcbTopToLowerBoardMm=round(LOWER_BOTTOM - float(bx['pcb'][1][2]), 2),
                         sideClearanceMm=round(PY_IN - D.PD['pcb'][0] / 2, 2), toFloorMm=0.0, screwAxes=[np.round(D.pd_w(u, v, 0), 3).tolist() for u, v in D.PD['holes']])
    out['lid'] = dict(outline=[[round(x, 2), round(y, 2)] for x, y in LID_OUTLINE.exterior.coords], note='y, z; full width z -13.3..43, 45 deg chamfer to |y| 11.86 at z -33.49', screws=LID_SCREWS)
    # clearances at HOME
    man_ = D.ia_lib.manifest(); SKIP = set(P.RETIRED) | set(P.SELF_KEYS) | {'rear_pack_cover', 'rear_pack', 'rear_frame', 'rear_lid', 'xl4015_left', 'xl4015_right', 'pd5991'}
    G = lambda a, b, s=40.0: round(float(a.min_gap(b, s)), 3); O = lambda a, b: round(float((a ^ b).volume()), 3)
    Dfull = P.mesh_to_m(P.load_stl(DD / 'frame_D-world.stl')) + P.mesh_to_m(P.load_stl(DD / 'lid_solid-world.stl'))
    body = F + Ls; mb = P.from_m(body).bounds; rows = {}
    for k, rec in man_.items():
        if k in SKIP:
            continue
        lo, hi = np.array(rec['bounds'])
        if np.all(lo - 15 <= mb[1]) and np.all(hi + 15 >= mb[0]):
            S = P.solid_m(k); rows[k] = dict(module=rec.get('module'), narrowGapMm=G(body, S), fullWidthDGapMm=G(Dfull, S), overlapMm3=O(body, S))
    V18 = P.mesh_to_m(P.load_stl(P.WORLD / 'rear_pack-v18.stl')); ORB = P.mesh_to_m(P.openrb_mesh())
    rows['rear_pack-v18 (as built)'] = dict(narrowGapMm=G(body, V18), overlapMm3=O(body, V18), note='cover seat: contact by design')
    rows['openrb-board-upright'] = dict(narrowGapMm=G(body, ORB), overlapMm3=O(body, ORB))
    out['clearancesHOME'] = dict(sorted(rows.items(), key=lambda kv: kv[1]['narrowGapMm']))
    plug = P.box((-57.0, -6.5, ZB_OUT - 20.0), (-49.5, 6.5, ZB_OUT))
    cable = P.box((-31.4, -7.3, -44.0 - 25.0), (-23.9, 6.7, -44.0))
    prow = {'openrb_floor_slot_cable': G(plug, cable, 40.0), 'rear_pack-v18': G(plug, V18, 20.0), 'rear_pack-v19': G(plug, P.solid_m('rear_pack'), 20.0)}
    for k, rec in man_.items():
        if k in SKIP:
            continue
        lo, hi = np.array(rec['bounds'])
        if np.all(lo - 20 <= [-49.5, 6.5, ZB_OUT]) and np.all(hi + 20 >= [-57.0, -6.5, ZB_OUT - 20]):
            prow[k] = G(plug, P.solid_m(k), 20.0)
    out['usbcPlugEnvelope'] = dict(box=[[-57.0, -6.5, ZB_OUT - 20.0], [-49.5, 6.5, ZB_OUT]], gapsMm=dict(sorted(prow.items(), key=lambda kv: kv[1])))
    XL = {nm: P.mesh_to_m(trimesh.load(str(DD / f'xl4015_{nm}-world.stl'), force='mesh').convex_hull) for nm in ('upper', 'lower')}
    PDm = P.mesh_to_m(trimesh.load(str(HERE / 'pd5991_standing_Dn-world.stl'), force='mesh').convex_hull)
    out['inside'] = dict(pd5991=dict(frameOverlapMm3=O(F, PDm), frameGapMm=G(F, PDm, 5.0), lidGapMm=G(Ls, PDm, 10.0)),
                         lowerBoardToChamferMm=round(LOWER_BOTTOM - ZCH_IN, 2))
    P.jdump(out, HERE / 'narrow.json')
    print(json.dumps({k: v for k, v in out.items() if k not in ('lid',)}, indent=0)[:5000])
