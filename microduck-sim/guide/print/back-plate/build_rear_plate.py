"""Layout C rear converter box for the MicroDuck (coordinator brief 2026-10-14): black two-piece box flush with the shells.
frame  = the rear-pack cover interface (rear_pack_cover geometry: plate x -47..-45, four dia 2.2 holes, lip) + a lower web
         + side/top/bottom walls x -65.9..-47 + bosses; screwed to the pack with the four cover screws before any board.
lid    = 1.2 mm plate x -67.1..-65.9, two M2 x 6 into frame bosses, driven from the back.
Boards: two ROBOTIS XL4015 vertical (long axis z), component side towards -x, IN terminals down, OUT up, PCB centres
y +-17.2, top edge 4.0 below the top wall (revision C2); Adafruit 5991 flat at the bottom, USB-C towards -y through the -y wall.
OUT pairs stay inside: over the boards, down the centre lane, through a 7 x 4 passage in the front plate into the pack channel.
World frame = guide frame (mm, x forward, y left, z up). Every feature is listed in FEATURES with its purpose.
Writes rear_frame-world.stl, rear_lid-world.stl, rear_frame-print.stl, rear_lid-print.stl, xl4015_left-world.stl,
xl4015_right-world.stl, pd5991-world.stl, render/*.stl (decimated boards for the renders), build.json, features.json."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
import manifold3d as m3
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P
import build_rear_pack as BRP

# ------------------------------------------------------------------ parameters (mm, world)
X_PLATE_IN, X_PLATE_OUT = -47.0, -45.0           # cover plate (rear face, pack face)
X_BACK = -65.9                                     # frame back opening = lid inner face (inner depth 18.9)
X_LID = -67.1                                      # lid outer face
HW = 32.05; T = 1.2                                # outer half width (flush with the shells), wall thickness
Z0, Z1 = -44.0, 46.5                               # outer bottom (pack floor level) / top (raised 3.5 in revision C2: 4.0 room over the OUT terminals)
WEB = dict(x0=X_PLATE_IN, x1=X_PLATE_OUT, z0=Z0, z1=-2.0)   # plate continued to the side walls below z -2 (shells start at z 0.26)
# XL4015 (ROBOTIS mesh, local X = component normal, Y = long axis, Z = short axis; PCB faces X -1.95 / -0.40)
XL_SRC = HERE.parent / 'candidates/back-box-20261014/parts/xl4015_board_local_mm.stl'
PCB_MID = -1.175; PIN_SIDE = 3.51
XL_MID_X = X_PLATE_IN - (18.9 - 17.86) / 2 - PIN_SIDE      # -51.03: 0.52 from the pin tips to the plate and from the inductor to the lid
XL_PIN_FACE_X = XL_MID_X + 0.825                            # -50.205: PCB back face around the holes (local X -2.0, plated rings) = boss seat
XL_YC = 17.2                                                # board edges |y| 4.1..30.3: 0.55 to the side-wall inner face (brief allowed 17.5 -> 17.2)
XL_ZC = 10.45                                               # board centre z (C1 value kept); top edge z 41.3, 4.0 below the top-wall inner face z 45.3
R_XL = np.array([[-1, 0, 0], [0, 0, -1], [0, -1, 0]], float)   # local X -> -x, local +Y (IN end, read the board label) -> -z, local Z -> -y
BOARDS = {'left': (0, XL_YC), 'right': (1, -XL_YC)}          # left = +y (7 V to the OpenRB J4), right = -y (5 V jumpers to the Pi)
XL_HOLES_L = [(sy * 28.25, sz * 10.5) for sy in (1, -1) for sz in (1, -1)]
XL_TERM_L = dict(z=(-5.17, 5.0), x=(-0.4, 9.6), entryX=2.5, entryY=30.15, entryZ=(2.5, -2.5), bodyEndY=30.76)
XL_TRIM_L = {'trimmer_a': (11.15, -10.44, 11.57), 'trimmer_b': (11.15, 0.06, 11.57)}
BOSS = dict(r=2.25, pilot_r=0.8, pilot_to=-45.3)            # M2 x 6 through the 1.65 PCB at the holes: 4.35 engagement, pilot 4.9 deep from the seat
# Adafruit 5991 (board file: PCB 20.32 x 27.813; u along 20.32, v along 27.813, w up from the bottom face)
PD_BACK_X = -50.0                                            # 3.0 standoff for the through-hole terminal/USB-C pins
PD_TOP_Z = Z0 + T + 0.5 + 20.32                              # -21.98 (bottom edge 0.5 above the bottom-wall inner face)
PD_YC = 0.0
PD = dict(pcb=(20.32, 27.813, 1.6), holes=[(2.413, 25.273), (17.653, 25.273), (2.54, 2.54), (17.78, 2.54)],
          parts=dict(usbc=((5.69, 21.606), (14.63, 28.956), 3.3), term=((6.76, 0.21), (13.76, 7.21), 8.5),
                     dip=((12.921, 8.603), (18.321, 16.543), 2.0), qt=((0.518, 13.256), (4.818, 19.356), 3.0)))
PD_BOSS = dict(r=2.25, pilot_r=0.8, pilot_to=-45.3)          # M2 x 6 through the 1.6 PCB: 4.4 engagement, tip at x -45.6
USB_OPEN = dict(x=(-57.5, -49.0), z=(-39.14, -25.14))        # 13 x 7.5 overmold + 0.5 all round, centred on the socket (x -53.25, z -32.14)
PASSAGE = dict(y=(-3.5, 3.5), z=(23.0, 27.0), r=1.0)          # front-plate wire passage 7 x 4 at y 0, top at the channel top z 27.0 (pack_lib.DFR_BOX)
LID_BOSS = dict(r=2.5, x1=X_BACK + 5.6, pilot_r=0.8, pilot_depth=5.2, hole_r=1.1,
                pos=[(0.0, 43.0), (22.0, -40.3)])             # top centre lane between the boards (moved up 3.5 with the top wall); bottom +y corner outside the 5991 insertion shadow


def xl_place(V, yc):
    return (np.atleast_2d(np.asarray(V, float)) - [PCB_MID, 0, 0]) @ R_XL.T + np.array([XL_MID_X, yc, XL_ZC])


def pd_w(u, v, w):
    """5991 board (u, v, w) -> world: u -> -z, v -> -y (USB-C edge v = 27.8 towards -y), w -> -x (components out). det +1."""
    return np.array([PD_BACK_X - w, PD_YC + PD['pcb'][1] / 2 - v, PD_TOP_Z - u])


def pd_boxes():
    out = {}
    def bx(uv0, uv1, w0, w1):
        a, b = pd_w(uv0[0], uv0[1], w0), pd_w(uv1[0], uv1[1], w1)
        return np.minimum(a, b), np.maximum(a, b)
    out['pcb'] = bx((0, 0), PD['pcb'][:2], 0, 1.6)
    for k, (a, b, h) in PD['parts'].items():
        out[k] = bx(a, b, 1.6, 1.6 + h)
    return out


def xl_holes(yc):
    return [xl_place([(PCB_MID, y, z)], yc)[0] for (y, z) in XL_HOLES_L]


def pd_holes():
    return [pd_w(u, v, 0) for u, v in PD['holes']]


def cyl_x(r, x0, x1, y, z):
    return P.cyl_x(r, min(x0, x1), max(x0, x1), y, z)


def passage_cutter():
    """rounded rectangle 7 (y) x 4 (z), r 1, through the cover plate x -47..-45 at y 0 (centre lane |y| <= 4.1)."""
    y0, y1 = PASSAGE['y']; z0, z1 = PASSAGE['z']; r = PASSAGE['r']
    return P.union([P.box((X_PLATE_IN - 0.5, y0 + r, z0), (X_PLATE_OUT + 0.5, y1 - r, z1)), P.box((X_PLATE_IN - 0.5, y0, z0 + r), (X_PLATE_OUT + 0.5, y1, z1 - r))]
                   + [cyl_x(r, X_PLATE_IN - 0.5, X_PLATE_OUT + 0.5, y, z) for y in (y0 + r, y1 - r) for z in (z0 + r, z1 - r)])


def out_entries():
    """OUT terminal entries of each board (local -Y end -> top) and their mean (x, y)."""
    res = {}
    for nm, (_, yc) in BOARDS.items():
        e = xl_place([(XL_TERM_L['entryX'], -XL_TERM_L['entryY'], dz) for dz in XL_TERM_L['entryZ']], yc)
        res[nm] = dict(entries=e.round(3).tolist(), centre=[round(float(e[:, 0].mean()), 3), round(float(e[:, 1].mean()), 3)])
    return res


def build_frame():
    cover = BRP.build_cover()
    parts = [cover, P.box((WEB['x0'], -HW, WEB['z0']), (WEB['x1'], HW, WEB['z1']))]
    parts += [P.box((X_BACK, -HW, Z0), (X_PLATE_IN, -HW + T, Z1)), P.box((X_BACK, HW - T, Z0), (X_PLATE_IN, HW, Z1)),
              P.box((X_BACK, -HW, Z1 - T), (X_PLATE_IN, HW, Z1)), P.box((X_BACK, -HW, Z0), (X_PLATE_IN, HW, Z0 + T))]
    cuts = []
    # XL4015 bosses: seat on the PCB pin face, forward to the plate/web or, for the four upper ones above the plate, to x -45
    for nm, (_, yc) in BOARDS.items():
        for h in xl_holes(yc):
            y, z = h[1], h[2]
            parts.append(cyl_x(BOSS['r'], XL_PIN_FACE_X, X_PLATE_OUT, y, z))
            if z > 29.5 - BOSS['r']:          # above the plate top: ribs to the top wall and (outer bosses) the side wall
                parts.append(P.box((XL_PIN_FACE_X, y - 1.5, z), (X_PLATE_IN, y + 1.5, Z1 - T + 0.01)))
                if abs(y) > 20:
                    s = np.sign(y)
                    parts.append(P.box((XL_PIN_FACE_X, min(y, s * (HW - T + 0.01)), z - 1.5), (X_PLATE_IN, max(y, s * (HW - T + 0.01)), z + 1.5)))
            cuts.append(cyl_x(BOSS['pilot_r'], XL_PIN_FACE_X - 1, BOSS['pilot_to'], y, z))
    # 5991 bosses on the plate
    for h in pd_holes():
        parts.append(cyl_x(PD_BOSS['r'], PD_BACK_X, X_PLATE_IN + 0.01, h[1], h[2]))
        cuts.append(cyl_x(PD_BOSS['pilot_r'], PD_BACK_X - 1, PD_BOSS['pilot_to'], h[1], h[2]))
    # lid bosses on the top and bottom walls
    for (y, z) in LID_BOSS['pos']:
        parts.append(cyl_x(LID_BOSS['r'], X_BACK, LID_BOSS['x1'], y, z))
        zw = (Z1 - T + 0.01, z) if z > 0 else (z, Z0 + T - 0.01)
        parts.append(P.box((X_BACK, y - LID_BOSS['r'], min(zw)), (LID_BOSS['x1'], y + LID_BOSS['r'], max(zw))))
        cuts.append(cyl_x(LID_BOSS['pilot_r'], X_BACK - 1, X_BACK + LID_BOSS['pilot_depth'], y, z))
    frame = P.union(parts)
    # cover screw holes again (the web covers the lower pair), OUT slots, USB-C opening
    for (y, z) in BRP.POST['holes']:
        cuts.append(cyl_x(BRP.COVER['hole_r'], X_PLATE_IN - 1, X_PLATE_OUT + 1, y, z))
    cuts.append(passage_cutter())
    cuts.append(P.box((USB_OPEN['x'][0], -HW - 1, USB_OPEN['z'][0]), (USB_OPEN['x'][1], -HW + T + 1, USB_OPEN['z'][1])))
    return frame - P.union(cuts)


def build_lid():
    lid = P.box((X_LID, -HW, Z0), (X_BACK, HW, Z1))
    for (y, z) in LID_BOSS['pos']:
        lid = lid - cyl_x(LID_BOSS['hole_r'], X_LID - 1, X_BACK + 1, y, z)
    return lid


FEATURES = {
 'frame': [
  {'id': 'cover_plate', 'what': 'rear_pack_cover plate x -47..-45 (outline, top corners r1.5, back edges r1), from build_rear_pack.build_cover(); top edge z 29.5 exactly as the cover (the cover has no top notch; the 12 x 6.1 cable notch is in the pack front plate at x -21..-19)', 'purpose': 'unchanged interface to the V1.8 and V1.9 packs; closes the converter channel'},
  {'id': 'cover_holes', 'what': 'four dia 2.2 holes at (+-16.1, 26.0) and (+-16.1, -36.5), cut again after the web', 'purpose': 'four M2 x 6 into the pack posts, driven from the back with the frame empty (frame-first assembly)'},
  {'id': 'cover_lip', 'what': 'x -45..-37.5, |y| <= 13.2, z 27.3..28.5 (as the cover)', 'purpose': 'kept by the brief (interface identical to the cover); locates the frame between the pack side walls (0.4 per side); it decides the print pose (see checks)'},
  {'id': 'lower_web', 'what': 'plate continued to the side walls: x -47..-45, |y| <= 32.05, z -44..-2', 'purpose': 'joins the wall ring to the plate (the cover outline alone meets the walls only along the bottom edge); carries the two lower outer XL4015 bosses; the shells start at z 0.26, so nothing is in front of it'},
  {'id': 'side_walls', 'what': '|y| 30.85..32.05, x -65.9..-47, z -44..46.5', 'purpose': 'box sides flush with the shells (0.55 to the board edges)'},
  {'id': 'top_wall', 'what': 'z 45.3..46.5, x -65.9..-47, no openings', 'purpose': 'box top, 4.0 above the board top edges (z 41.3) so the OUT pairs bend over inside the box; carries the top lid boss'},
  {'id': 'bottom_wall', 'what': 'z -44..-42.8, x -65.9..-47 (pack floor level)', 'purpose': 'box floor under the 5991; carries the bottom lid boss'},
  {'id': 'xl_bosses', 'what': 'eight dia 4.5 bosses on the board holes, seat at the PCB back face x -50.205 (local X -2.0 at the plated holes), dia 1.6 pilots to x -45.3 (M2 x 6, 4.35 engagement); lower four end in the plate/web, upper four (z 38.7) run to x -45 with 3 mm ribs x -50.205..-47 up to the top wall (z 45.3) and, for |y| 27.7, to the side wall', 'purpose': 'XL4015 standoffs (pins 2.74 + 0.52 clearance), screws from the component side; the ribs stay forward of the OUT wire run (x -54.7)'},
  {'id': 'pd_bosses', 'what': 'four dia 4.5 bosses x -50..-47 at the 5991 corner holes, dia 1.6 pilots to x -45.3', 'purpose': '5991 standoffs (3.0 for the through-hole pins), M2 x 6 from the component side'},
  {'id': 'lid_bosses', 'what': 'two dia 5 bosses x -65.9..-60.3 on the top wall (y 0, z 43.0) and the bottom wall (y 22, z -40.3), dia 1.6 pilots 5.2 deep', 'purpose': 'two M2 x 6 through the lid; top: the 8.2 mm lane between the boards is the only top-wall room that is not over a board, and the boss sits behind the OUT wire run (x -60.3 vs -54.7); bottom: +y corner, outside the 5991 insertion path and below its terminal wire exit'},
  {'id': 'wire_passage', 'what': 'rounded rectangle 7 (y) x 4 (z), r 1, through the cover plate x -47..-45 at y -3.5..3.5, z 23..27 (top at the channel top z 27.0, pack_lib.DFR_BOX; 0.3 under the lip)', 'purpose': 'both OUT pairs (two flat 22 AWG pairs 1.6 x 3.2, stacked: 3.2 x 3.2) pass from the centre lane between the boards into the pack channel x -45..-37'},
  {'id': 'usb_opening', 'what': '-y wall cut x -57.5..-49.0, z -39.14..-25.14', 'purpose': 'USB-C plug overmold 13 x 7.5 with 0.5 all round, centred on the 5991 socket'},
 ],
 'wiring': [
  {'id': 'out_route', 'rule': 'each OUT pair leaves its terminal upward (entries z 40.6, terminal end z 41.21), bends over in the 4.0 room under the top wall (z 41.3..45.3) at x about -54.7, runs inward to the centre lane (|y| <= 4.1), down the lane to z 25 and forward through the wire passage into the pack channel; 7 V (left board) continues to OpenRB J4 (-30, -6, 26), 5 V (right board) to the pack front-plate notch (y +-6, z 32.7..38.8 at x -21..-19)'},
  {'id': 'in_route', 'rule': 'at each IN terminal (entries face down, z -19.7) the wire bends outward, toward its own side wall, within the first 2 mm, then runs down the 5.7 mm lane behind the 5991 (x -65.9..-60.2) to the 5991 terminal; the 15 V daisy chain between the two IN terminals runs along the floor lane behind the 5991 (x -65.9..-60.2, z -42.8..-37.7)'},
  {'id': 'pd5991_terminal', 'rule': '5991 screw-terminal entry faces: plane y 13.70 (facing +y), x -60.1..-51.6, z -35.74..-28.74; entry centres (-54.1, 13.7, -30.39) and (-54.1, 13.7, -33.89)'},
 ],
 'lid': [
  {'id': 'lid_plate', 'what': '1.2 mm plate x -67.1..-65.9, |y| <= 32.05, z -44..46.5', 'purpose': 'closes the box; removed (two screws) to set the trimmers and DIP switches'},
  {'id': 'lid_holes', 'what': 'dia 2.2 at (0, 43.0) and (22, -40.3)', 'purpose': 'two M2 x 6 into the lid bosses'},
 ],
}

if __name__ == '__main__':
    frame = build_frame(); lid = build_lid()
    fm = P.clean_mesh(frame); lm = P.clean_mesh(lid)
    fm.export(HERE / 'rear_frame-world.stl'); lm.export(HERE / 'rear_lid-world.stl')
    # print poses: frame standing on its bottom wall (as assembled, z up); lid on its outer face (x -67.1 down)
    f_print = fm.copy(); f_print.apply_translation(-np.array([0, 0, fm.bounds[0][2]])); f_print.export(HERE / 'rear_frame-print.stl')
    Rl = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)       # x' = y, y' = z, z' = x: outer face lowest
    l_print = trimesh.Trimesh(lm.vertices @ Rl.T, lm.faces, process=False); l_print.apply_translation(-l_print.bounds[0]); l_print.export(HERE / 'rear_lid-print.stl')
    # boards in the final poses
    src = trimesh.load(str(XL_SRC), force='mesh')
    (HERE / 'render').mkdir(exist_ok=True)
    info = {'boards': {}}
    for nm, (_, yc) in BOARDS.items():
        m = trimesh.Trimesh(xl_place(src.vertices, yc), src.faces, process=False)
        m.export(HERE / f'xl4015_{nm}-world.stl'); m.simplify_quadric_decimation(face_count=12000).export(HERE / 'render' / f'xl4015_{nm}.stl')
        t = XL_TERM_L
        info['boards'][nm] = dict(
            role='7 V to OpenRB J4' if nm == 'left' else '5 V jumpers to the Pi', pcbCentre=[XL_MID_X, yc, XL_ZC], pcbWorldX=[XL_MID_X - 0.775, XL_PIN_FACE_X],
            rotationLocalToWorld=R_XL.tolist(), worldBounds=np.round(m.bounds, 3).tolist(),
            boardScrewAxes=[np.round(h, 3).tolist() for h in xl_holes(yc)], screwHeadSide='component side (-x); driver from the back with the lid off',
            trimmerScrewTops={k: np.round(xl_place([v], yc)[0], 2).tolist() for k, v in XL_TRIM_L.items()},
            inEntries=xl_place([(t['entryX'], t['entryY'], dz) for dz in t['entryZ']], yc).round(3).tolist(),
            outEntries=xl_place([(t['entryX'], -t['entryY'], dz) for dz in t['entryZ']], yc).round(3).tolist(),
            inTerminalBlockWorld=np.round(np.sort(xl_place([(t['x'][0], t['bodyEndY'], t['z'][0]), (t['x'][1], 23.1, t['z'][1])], yc), axis=0), 3).tolist())
    boxes = pd_boxes()
    pdm = trimesh.util.concatenate([trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2)) for lo, hi in boxes.values()])
    pdm.export(HERE / 'pd5991-world.stl')
    info['pd5991'] = dict(source='https://github.com/adafruit/Adafruit-USB-Type-C-PD-Switchable-PCB (Eagle .brd, fetched 2026-10-14)', pcbBackX=PD_BACK_X,
                          boxes={k: [lo.round(3).tolist(), hi.round(3).tolist()] for k, (lo, hi) in boxes.items()},
                          screwAxes=[np.round(h, 3).tolist() for h in pd_holes()], usbcSocketCentre=[-53.25, round(float((boxes['usbc'][0][1])), 3), -32.14],
                          terminalEntries=[np.round(pd_w(u, 0.21, 4.1), 2).tolist() for u in (8.41, 11.91)], terminalEntriesFace='+y',
                          terminalEntryFaceWorld=dict(y=round(float(boxes['term'][1][1]), 3), x=[round(float(boxes['term'][0][0]), 3), round(float(boxes['term'][1][0]), 3)], z=[round(float(boxes['term'][0][2]), 3), round(float(boxes['term'][1][2]), 3)]))
    info['holes'] = dict(coverScrews=[[X_PLATE_IN, y, z] for (y, z) in BRP.POST['holes']], outEntries=out_entries(),
                         wirePassage=dict(centre=[X_PLATE_OUT - 1.0, 0.0, round(sum(PASSAGE['z']) / 2, 3)], x=[X_PLATE_IN, X_PLATE_OUT], y=list(PASSAGE['y']), z=list(PASSAGE['z']), cornerR=PASSAGE['r']),
                         usbOpening=dict(wall='-y side wall |y| 30.85..32.05', x=list(USB_OPEN['x']), z=list(USB_OPEN['z'])),
                         lidScrews=[[X_LID, y, z] for (y, z) in LID_BOSS['pos']])
    info['envelope'] = dict(frameX=[X_BACK, X_PLATE_OUT], lidX=[X_LID, X_BACK], absY=HW, z=[Z0, Z1], wall=T, innerDepth=round(X_PLATE_IN - X_BACK, 3))
    for name, man, mesh in (('frame', frame, fm), ('lid', lid, lm)):
        info[name] = dict(status=str(man.status()), genus=int(man.genus()), volume_mm3=round(float(man.volume()), 2), tris=int(len(mesh.faces)),
                          watertight=bool(mesh.is_watertight), bodies=int(len(mesh.split(only_watertight=False))), bounds=np.round(mesh.bounds, 3).tolist())
    info['printPoses'] = dict(frame='rear_frame-print.stl: as assembled, bottom wall (z -44) on the bed', lid='rear_lid-print.stl: outer face (x -67.1) on the bed; x\' = y, y\' = z, z\' = x')
    info['params'] = dict(XL_MID_X=XL_MID_X, XL_YC=XL_YC, XL_ZC=XL_ZC, BOSS=BOSS, PD_BACK_X=PD_BACK_X, PD_TOP_Z=PD_TOP_Z, PD_BOSS=PD_BOSS, USB_OPEN=USB_OPEN, LID_BOSS=LID_BOSS, WEB=WEB, PASSAGE=PASSAGE, Z1=Z1)
    P.jdump(info, HERE / 'build.json'); P.jdump(FEATURES, HERE / 'features.json')
    print(json.dumps({k: info[k] for k in ('frame', 'lid', 'envelope')}, indent=1))
    print(json.dumps(info['holes'], indent=0))
