"""Cap lower-corner retention study for the layout F rear box (2026-10-14). Study only: no release, no gate.
Starts from the released layout F meshes (../layout-F/rear_frame-world.stl, rear_lid-world.stl, real world, guide frame:
x forward, y left, z up) and edits them with booleans, so the outline and every rounding stay exactly as released.
Options:
  current  layout F as released: M2 x 6 ears at (y -23.8, z -17.4) and (y +23.8, z -33.6), both outside the outline.
  delete   the +Y ear, its frame boss and web are removed. The -Y ear stays. Complement: a slot hook, a 1.7 mm tab of the cap
           side wall that slides into the rear end of the USB-C slot and lifts its tooth into a notch in the slot top edge.
  hidden   both ears, bosses and webs are removed. One M2 x 10 runs from a driver hole in the cap back, through a column
           inside the cap, through the 5991 mounting hole at (y +11.37, z -16.67) into that hole's existing frame boss.
           Complement: a window hook on -Y (same tab and tooth in the top edge of the 5991 terminal window).
python ear_options.py  (CAD venv, bounded runner). Writes options/*.stl and ear_options.json."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
import manifold3d as m3
from shapely import contains_xy
HERE = Path(__file__).resolve().parent; LF = HERE.parent / 'layout-F'
sys.argv = ['build_f.py', 'F']; sys.path.insert(0, str(LF))
import build_f as B
P, K = B.P, B.K
OUT = HERE / 'options'; OUT.mkdir(exist_ok=True)

frame0 = P.mesh_to_m(trimesh.load(str(LF / 'rear_frame-world.stl'), force='mesh'))
lid0 = P.mesh_to_m(trimesh.load(str(LF / 'rear_lid-world.stl'), force='mesh'))
RIM = -59.1

# ---------------------------------------------------------------- removal of the ears (regions lie outside the outline)
FRAME_EAR_P = P.box((RIM - 0.1, 15.63, -36.1), (-53.3, 27.0, -31.0))      # +Y boss dia 4.5 at (23.8, -33.6) and web
FRAME_EAR_M = P.box((RIM - 0.1, -26.6, -20.2), (-53.3, -21.0, -15.25))    # -Y boss dia 5.0 at (-23.8, -17.4) and web
LID_EAR_P = P.box((-60.4, 15.63, -36.1), (RIM + 0.1, 27.0, -31.0))
LID_EAR_M = P.box((-60.4, -26.6, -20.2), (RIM + 0.1, -21.0, -15.25))

# ---------------------------------------------------------------- hooks: tab + tooth in a side-wall opening, notch above it
WALL = (14.406, 15.606)            # narrow tier side wall |y|
DROP = B.CAP_DROP                  # 1.2: the cap slides on low, then lifts
TOOTH_H, NOTCH_H = 1.0, 1.2
TOOTH_X = (-58.2, -57.4); NOTCH_X = (-58.4, -57.3)


def hook(side, edge_z, x_root):
    """side +1/-1; edge_z = top edge of the opening in the frame; returns (cap parts, frame cut)."""
    lo, hi = sorted([side * WALL[0], side * WALL[1]])
    tab = P.box((x_root, lo, edge_z - 1.2), (TOOTH_X[1], hi, edge_z))          # tab under the edge (low: 1.2 lower, clear)
    tooth = P.box((TOOTH_X[0], lo, edge_z - 0.01), (TOOTH_X[1], hi, edge_z + TOOTH_H))
    lo2, hi2 = sorted([side * (WALL[0] - 0.3), side * (WALL[1] + 0.3)])
    notch = P.box((NOTCH_X[0], lo2, edge_z - 0.05), (NOTCH_X[1], hi2, edge_z + NOTCH_H))
    root = P.box((x_root, lo, edge_z - 1.2), (RIM - 0.02, hi, edge_z + 0.4)) if x_root < RIM - 0.5 else None   # bonds into the cap wall above the window
    return [tab, tooth] + ([root] if root else []), notch


USB_TOP = -17.16; TERM_TOP = -20.06
hookP_parts, hookP_cut = hook(+1, USB_TOP, RIM - 0.05)      # cap side wall is uncut at the USB-C slot: tab grows from the rim
hookM_parts, hookM_cut = hook(-1, TERM_TOP, -60.3)          # terminal window is cut through the cap: tab roots 1.2 into the cap

# ---------------------------------------------------------------- hidden screw: column in the cap, M2 x 10 into the 5991 boss
SY, SZ = 11.37, -16.67             # 5991 hole (real +y upper), boss pilot to x -45.3
SEAT_X = -56.1; COL_FRONT = -55.1; COL_R = 2.8; BORE_R = 2.2; CLEAR_R = 1.15
HEAD = dict(d=3.8, h=1.6)
col = P.union([P.cyl_x(COL_R, -66.6, -63.0, SY, SZ) ^ P.mesh_to_m(P.from_m(lid0).convex_hull), P.cyl_x(COL_R, -63.5, COL_FRONT, SY, SZ)])   # hull trims only the part inside the rounded back
col_cut = P.union([P.cyl_x(BORE_R, -68.5, SEAT_X, SY, SZ), P.cyl_x(CLEAR_R, SEAT_X - 0.1, COL_FRONT + 0.1, SY, SZ)])
screw_body = P.union([P.cyl_x(HEAD['d'] / 2, SEAT_X - HEAD['h'], SEAT_X, SY, SZ), P.cyl_x(1.0, SEAT_X, SEAT_X + 10.0, SY, SZ)])

OPT = {}
OPT['current'] = (frame0, lid0)
OPT['delete'] = ((frame0 - FRAME_EAR_P) - hookP_cut, P.union([lid0 - LID_EAR_P] + hookP_parts))
OPT['delete_plain'] = (frame0 - FRAME_EAR_P, lid0 - LID_EAR_P)
lid_h = P.union([(lid0 - LID_EAR_P) - LID_EAR_M, col] + hookM_parts) - col_cut
OPT['hidden'] = (((frame0 - FRAME_EAR_P) - FRAME_EAR_M) - hookM_cut, lid_h)

# ---------------------------------------------------------------- reference bodies (real world)
S_des = B.board_solids(B.board_meshes())
S = {k: B.real_m(v) for k, v in S_des.items()}
W = json.loads((LF / 'wires_F.json').read_text())
tubes = {k: K.tube(B.trim_start(B.trim_start(np.array(v['points']), 1.6)[::-1], 1.6)[::-1], B.WIRE_R) for k, v in W.items()}
PLUG = P.box((-57.0, 15.05, -30.66), (-49.5, 40.05, -17.66))
_lo, _hi = B.pd_boxes()['usbc']
USBC_BOX = P.box((_lo[0], -_hi[1], _lo[2]), (_hi[0], -_lo[1], _hi[2]))
ol = B.outline(); ol.W.rc_top = 1.8; ol.W.rc_bot = 1.8; ol.N.rc_bot = 2.1; ol.rf = 3.0
POLY = B.outline_poly(ol)          # y-z outline (symmetric, so design = real)


def outside(man, tol=0.2):
    """largest distance of any vertex (x < -47.05, i.e. behind the front plate) outside the y-z outline, and where."""
    v = P.from_m(man).vertices; v = v[v[:, 0] < -47.05]
    out = ~contains_xy(POLY.buffer(tol), v[:, 1], v[:, 2])
    if not out.any():
        return dict(maxMm=0.0, at=None, count=0)
    from shapely.geometry import Point
    d = np.array([POLY.exterior.distance(Point(p[1], p[2])) for p in v[out]])
    i = int(np.argmax(d)); return dict(maxMm=round(float(d[i]), 2), at=np.round(v[out][i], 2).tolist(), count=int(out.sum()))


def vol(a, b):
    return round(float((a ^ b).volume()), 3)


PATH = [(-15.0 + s, 0.0, -DROP) for s in np.arange(0.0, 15.01, 0.5)] + [(0.0, 0.0, -DROP + t) for t in np.arange(0.1, DROP + 1e-6, 0.1)]
res = {}
for nm, (fr, ld) in OPT.items():
    r = dict(frameVolume=round(float(fr.volume()), 1), lidVolume=round(float(ld.volume()), 1), frameGenus=int(fr.genus()), lidGenus=int(ld.genus()),
             frameBodies=len(P.from_m(fr).split(only_watertight=False)), lidBodies=len(P.from_m(ld).split(only_watertight=False)))
    r['outsideOutline'] = dict(frame=outside(fr), lid=outside(ld))
    r['lidVsBoards'] = {k: B.gap(ld, s) for k, s in S.items()}
    r['frameVsBoardsOverlapMm3'] = {k: vol(fr, s) for k, s in S.items()}
    r['wireGap'] = {k: dict(frame=B.gap(t, fr), lid=B.gap(t, ld)) for k, t in tubes.items()}
    r['wireGapMin'] = dict(frame=min(v['frame'] for v in r['wireGap'].values()), lid=min(v['lid'] for v in r['wireGap'].values()))
    r['plugEnvelopeGap'] = dict(frame=B.gap(PLUG, fr), lid=B.gap(PLUG, ld))
    cp_f, cp_b = [], []
    for o in PATH:
        lt = ld.translate(list(map(float, o)))
        cp_f.append(vol(lt, fr)); cp_b.append(max(vol(lt, s) for s in S.values()))
    i = int(np.argmax(cp_f[:-1])); j = int(np.argmax(cp_b))
    r['capPath'] = dict(path='[-15,0,-1.2] -> [0,0,-1.2] -> [0,0,0]', frameMaxOverlapBeforeFinalMm3=cp_f[i], atOffset=list(map(float, PATH[i])),
                        frameOverlapFinalMm3=cp_f[-1], boardsMaxOverlapMm3=cp_b[j], boardsAt=list(map(float, PATH[j])))
    res[nm] = r
    if nm != 'current':
        for man, part in ((fr, 'frame'), (ld, 'lid')):
            mm = P.from_m(man); mm.merge_vertices(); mm.export(OUT / f'{part}_{nm}-world.stl')
    print(nm, json.dumps({k: r[k] for k in ('frameVolume', 'lidVolume', 'frameBodies', 'lidBodies', 'outsideOutline', 'lidVsBoards', 'wireGapMin', 'plugEnvelopeGap', 'capPath')}), flush=True)

# hidden screw: stack and clearances
res['hiddenScrew'] = dict(axisYZ=[SY, SZ], screw='M2 x 10 (stock)', seatX=SEAT_X, tipX=SEAT_X + 10.0, bossPilotEndX=-45.3,
                          engagementInBossMm=round(SEAT_X + 10.0 - B.PD_BACK_X, 2), throughPcbX=[-51.6, -50.0],
                          columnFrontX=COL_FRONT, columnR=COL_R, boreR=BORE_R,
                          screwVsUsbcSocket=B.gap(screw_body, USBC_BOX), columnVsUsbcSocketFinal=B.gap(col, USBC_BOX),
                          columnVsUsbcSocketLowPosition=B.gap(col.translate([0, 0, -DROP]), USBC_BOX),
                          columnVsMidBoard=B.gap(col, S['mid_5V']), columnXRange=np.round(P.from_m(col).bounds[:, 0], 2).tolist())
mm = P.from_m(screw_body); mm.export(OUT / 'screw_hidden-world.stl')
for nm, parts in (('hookP', hookP_parts), ('hookM', hookM_parts)):
    P.from_m(P.union(parts)).export(OUT / f'{nm}-world.stl')
res['hooks'] = dict(toothX=TOOTH_X, notchX=NOTCH_X, toothH=TOOTH_H, notchH=NOTCH_H, drop=DROP,
                    plusY=dict(opening='USB-C slot (+y narrow wall)', edgeZ=USB_TOP, tabZ=[USB_TOP - 1.2, USB_TOP]),
                    minusY=dict(opening='5991 terminal window (-y narrow wall)', edgeZ=TERM_TOP, tabZ=[TERM_TOP - 1.2, TERM_TOP]))
P.jdump(res, HERE / 'ear_options.json'); print(json.dumps(res['hiddenScrew']))
print('done')
