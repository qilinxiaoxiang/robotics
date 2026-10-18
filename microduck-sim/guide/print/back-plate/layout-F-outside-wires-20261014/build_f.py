"""Layout F / G (2026-10-14). F is the V1.11 release source (python build_f.py); G stays a study.
F: three horizontal tiers in one box, z from 43 down: XL4015 #1 (7 V) on top, XL4015 #2 (5 V) in the middle, both
long axis y, IN ends -y, OUT ends +y (real world), components to the lid (-x) as in layout D; Adafruit 5991 at the
bottom in a narrow tier (PCB normal x, long axis y, terminal to -y, USB-C socket to +y).
Handedness: the kit photo (bringup/parts/photos/xl4015_robotis_kit_top.jpg) and the mesh put IN at board-local -Y
(regulator IC and IN-side caps at local Y < 0, coil at Y > 0). With R_XL (local Y -> world +y) the IN end is world -y.
The whole layout is computed in a DESIGN frame, the y-mirror of the real world, where IN is at +y: boards enter it as
diag(1,-1,1) @ R_XL (point reflection, used only for points and hulls), the 5991 is the real board turned 180 deg about
x, and every internal check (radii, wire-board, wire-frame, wire-wire gaps) is mirror invariant. Every output STL and
JSON and every check against the robot (HOME manifest, shells, USB-C plug, hip sweep) is in the real world. Straight step between the tiers, every
outer edge rounded (rounded rear edges, rounded y-z corners, concave step blend) through shellkit.
Wires (22 AWG, tube dia 1.8, centreline bend radius 3): each terminal is reached through a side window; the wire
leaves the terminal, makes one U-loop outside the wall and comes back into the rear lane (the space between the
component tops and the lid), every other run is internal. 7 V and 5 V leave forward through the gap between the two
XL tiers and the front passage at y 0 into the pack channel.
G (python build_f.py G): F without the 5991 tier (the 5991 moves into the reprinted pack, see pack_study.py); the box
moves 3 mm back (front plate x -50..-48) so the pack channel can be 13 deep; the 15 V pair comes from the pack
through a second front passage into the same tier gap.
World = guide frame (mm, x forward, y left, z up). Writes STLs, layout_f.json / layout_g.json, render_spec.json."""
import sys, json, math
from pathlib import Path
import numpy as np, trimesh
import manifold3d as m3
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
HERE = Path(__file__).resolve().parent; BP = HERE.parent; DD = BP / 'layout-D-20261014'; PRINT = BP.parent   # DD: shellkit, study variants
sys.path.insert(0, str(DD)); sys.path.insert(0, str(PRINT / 'rear-pack'))
import pack_lib as P, build_rear_pack as BRP, ia_lib
import shellkit as K

VARIANT = sys.argv[1] if len(sys.argv) > 1 else 'F'
OUTDIR = HERE if VARIANT == 'F' else DD / 'layout-G'
OUTDIR.mkdir(exist_ok=True)
DX = 0.0 if VARIANT == 'F' else -3.0                    # G: whole box 3 mm back
X_IN, X_OUT = -47.0 + DX, -45.0 + DX                    # front plate (cover) faces
T = 1.2; HW = 32.05; YI = HW - T; Z1 = 43.0; ZI1 = Z1 - T
X_LI = -65.9 + DX                                       # lid inner face = frame rim (layout D depth, see lane check)
X_LID = X_LI - T
GRAMS = lambda v: round(v / 1000 * 1.24 * 0.851, 2)     # as narrow / E

# ------------------------------------------------------------------ XL4015 (layout D placement)
XL_SRC = PRINT / 'candidates/back-box-20261014/parts/xl4015_board_local_mm.stl'
PCB_MID = -1.175; XL_MID_X = -51.03 + DX; XL_PIN_FACE_X = XL_MID_X + 0.825
R_XL = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]], float)      # REAL: local X -> -x, Y -> +y (IN = local -Y -> -y), Z -> -z
MIR = np.diag([1.0, -1.0, 1.0])                                  # design frame <-> real world
R_DES = MIR @ R_XL                                               # design-frame board placement (IN at +y)
HALF_W = 13.1
ZT = ZI1 - 0.5 - HALF_W                                  # 28.2
WIRE_R, BEND, CLR = 0.9, 3.0, 0.3
GAP_PCB = 2.4                                            # tier gap between PCB edges: wire dia 1.8 + 0.3 each side
ZG = ZT - HALF_W - GAP_PCB / 2                           # 13.9 wire plane in the gap
ZM = ZT - 2 * HALF_W - GAP_PCB                           # -0.4
BOARDS = {'top_7V': ZT, 'mid_5V': ZM}
XL_HOLES_L = [(sy * 28.25, sz * 10.5) for sy in (1, -1) for sz in (1, -1)]
X_E = XL_MID_X - (2.5 + 1.175)                           # terminal wire entry plane (local X 2.5)
X_W = X_LI + WIRE_R + 0.4                                # rear lane wire plane
TERM_FACE = 30.76; ENTRY_Y = 30.15
Y_T = 31.4                                               # loop turn start (0.64 straight out of the terminal face)
Y_FAR = Y_T + BEND                                       # 34.4 loop extreme (centreline)
MID_BOTTOM = ZM - HALF_W                                 # -13.5
Z_STEP_IN = MID_BOTTOM - 0.5; Z_STEP_OUT = Z_STEP_IN - T  # -14.0 / -15.2

# ------------------------------------------------------------------ 5991 tier (F only)
PD_PCB = (20.32, 27.813, 1.6)
PD_HOLES = [(2.413, 25.273), (17.653, 25.273), (2.54, 2.54), (17.78, 2.54)]
PD_PARTS = dict(usbc=((5.69, 21.606), (14.63, 28.956), 3.3), term=((6.76, 0.21), (13.76, 7.21), 8.5),
                dip=((12.921, 8.603), (18.321, 16.543), 2.0), qt=((0.518, 13.256), (4.818, 19.356), 3.0))
PD_BACK_X = -50.0; PD_TOP = Z_STEP_IN                    # PCB top edge level with the step inner face, 0.5 under the mid PCB
PY_IN = PD_PCB[1] / 2 + 0.5; PY_OUT = PY_IN + T          # 14.41 / 15.61
PD_BOT = PD_TOP - PD_PCB[0]
ZB_IN = PD_BOT - 0.5; ZB_OUT = ZB_IN - T                 # floor


def pd_w(u, v, w):
    """5991 (u along 20.32, v along 27.8, w up from the PCB back) -> DESIGN frame: u -> +z from the PCB bottom edge,
    v -> -y (USB-C to -y here, +y in the real world), w -> -x. Real board = this placement turned 180 deg about x."""
    return np.array([PD_BACK_X - w, PD_PCB[1] / 2 - v, PD_BOT + u])


def pd_boxes():
    out = {}
    def bx(a, b, w0, w1):
        p, q = pd_w(a[0], a[1], w0), pd_w(b[0], b[1], w1)
        return np.minimum(p, q), np.maximum(p, q)
    out['pcb'] = bx((0, 0), PD_PCB[:2], 0, 1.6)
    for k, (a, b, h) in PD_PARTS.items():
        out[k] = bx(a, b, 1.6, 1.6 + h)
    return out


PD_TERM_Z = [PD_BOT + 8.51, PD_BOT + 12.01]              # 2-pos 3.5 pitch entries: + (feed_p) lower, - (feed_q) upper (5991 photo)
PD_X_E = PD_BACK_X - 4.6                                 # entry height 3.0 above the PCB
PD_FACE_Y = PD_PCB[1] / 2 - 0.21                         # 13.696
USB_C = dict(x=(-57.5, -49.0), z=(PD_TOP - 10.16 - 7.0, PD_TOP - 10.16 + 7.0))   # overmold 13 x 7.5 + 0.5


def xl_place(V, zc, R=R_DES):
    return (np.atleast_2d(np.asarray(V, float)) - [PCB_MID, 0, 0]) @ R.T + np.array([XL_MID_X, 0.0, zc])


def real_m(man):
    return man.mirror([0.0, 1.0, 0.0])


def real_pts(p):
    return np.asarray(p, float) * [1.0, -1.0, 1.0]


def real_window(w):
    w = dict(w); w['side'] = -w['side']; return w


def real_yz(y, z):
    return (-y, z)


# ------------------------------------------------------------------ outline
# The lid is a rounded CAP (x -67.1 .. X_SPLIT): all rear-edge rounding lies in the cap, so the frame keeps a constant inner
# cross-section from its rim (X_SPLIT = X_LID + the largest rear radius) to the front plate and every board slides straight in
# from the rear (print gate steps audit; the XL4015 PCBs span the full inner width |y| 30.85). Radii start at the wall
# thickness and grow as far as the boards and wires allow (search_radii).
R_REAR = T
X_SPLIT = X_LI                                           # set in __main__ after the radius search
CAP_DROP = 1.2                                           # the cap slides on 1.2 low, then lifts its teeth into the top-wall slots


def outline():
    if VARIANT == 'F':
        W = K.Rect(-HW, HW, Z_STEP_OUT, Z1, 0.0, 0.0, 'side', 'top', 'step')
        N = K.Rect(-PY_OUT, PY_OUT, ZB_OUT, Z_STEP_OUT + 8.0, 0.0, 0.0, 'nside', 'top', 'nbot')
        return K.Outline(W=W, N=N, rf=0.0, R=dict(side=R_REAR, top=R_REAR, step=R_REAR, nside=R_REAR, nbot=R_REAR), X_LID=X_LID, X_IN=X_IN, T=T)
    W = K.Rect(-HW, HW, Z_STEP_OUT, Z1, 0.0, 0.0, 'side', 'top', 'step')
    return K.Outline(W=W, R=dict(side=R_REAR, top=R_REAR, step=R_REAR), X_LID=X_LID, X_IN=X_IN, T=T)


def outline_poly(ol):
    def rr(r):
        p = sbox(r.y0, r.z0, r.y1, r.z1)
        top = p.intersection(sbox(r.y0 - 1, 0.5 * (r.z0 + r.z1), r.y1 + 1, r.z1 + 1)); bot = p.difference(top)
        def rnd(q, rc):
            return q.buffer(-rc, join_style=1).buffer(rc, join_style=1) if rc > 0 else q
        a = rnd(sbox(r.y0, r.z0, r.y1, r.z1), r.rc_top).intersection(top.buffer(0.01))
        b = rnd(sbox(r.y0, r.z0, r.y1, r.z1), r.rc_bot).intersection(bot.buffer(0.01))
        return unary_union([a, b])
    u = rr(ol.W) if ol.N is None else unary_union([rr(ol.W), rr(ol.N)])
    if ol.rf > 0:
        u = u.buffer(ol.rf, join_style=1).buffer(-ol.rf, join_style=1)
    return u.simplify(0.02)


# ------------------------------------------------------------------ windows (side cuts at the terminals)
WIN_X1 = X_E + WIRE_R + 0.6                              # front edge of every XL window (-53.2 in F)


def windows():
    w = {}
    for nm, zc in BOARDS.items():
        for side, s in (('IN', 1), ('OUT', -1)):
            w[f'{nm}_{side}'] = dict(x=[round(X_LI, 3), round(WIN_X1, 3)], side=s, yWall=[YI, HW], z=[round(zc - 5.2, 3), round(zc + 5.2, 3)])
    if VARIANT == 'F':
        tb = pd_boxes()['term']
        w['pd5991_term'] = dict(x=[round(X_LI, 3), round(PD_X_E + WIRE_R + 0.6, 3)], side=1, yWall=[PY_IN, PY_OUT],
                                z=[round(float(tb[0][2]) - 0.5, 3), round(float(tb[1][2]) + 0.5, 3)])
        w['pd5991_usbc'] = dict(x=[round(X_LI, 3), USB_C['x'][1]], side=-1,   # open to the rim: the socket overhangs the PCB edge and slides in along it
                                 yWall=[PY_IN, PY_OUT], z=[round(USB_C['z'][0], 3), round(USB_C['z'][1], 3)])
    return w


def window_cuts():
    cs = []
    for k, w in windows().items():
        s = w['side']; ya, yb = w['yWall'][0] - (8.0 if k != 'pd5991_usbc' else 0.6), w['yWall'][1] + 12
        lo, hi = sorted([s * ya, s * yb])
        cs.append(P.box((w['x'][0] - 0.01, lo, w['z'][0]), (w['x'][1], hi, w['z'][1])))
    return cs


def in_window_band(p):
    for k, w in windows().items():
        if w['x'][0] - 1.5 <= p[0] <= w['x'][1] + 0.5 and w['z'][0] - 0.2 <= p[2] <= w['z'][1] + 0.2 and w['side'] * p[1] >= w['yWall'][0] - 8:
            return True
    return False


# ------------------------------------------------------------------ wires
def loop_out(x_e, s, z0, z1, y_far, x_w=X_W):
    """terminal entry -> out through the window -> U-loop -> back into the lane heading to the box centre."""
    return [(x_e, s * ENTRY_Y, z0), (x_e, s * y_far, z0), (x_w, s * y_far, z1)]


XA = -58.5 + DX


def offset_2d(pts, d):
    """offset a 2D polyline by d to its left (miter corners), so parallel wires keep their perpendicular spacing."""
    P_ = np.asarray(pts, float); out = []
    def nrm(a, b):
        t = (b - a) / np.linalg.norm(b - a); return np.array([-t[1], t[0]])
    for i in range(len(P_)):
        if i == 0:
            out.append(P_[0] + d * nrm(P_[0], P_[1]))
        elif i == len(P_) - 1:
            out.append(P_[-1] + d * nrm(P_[-2], P_[-1]))
        else:
            n1, n2 = nrm(P_[i - 1], P_[i]), nrm(P_[i], P_[i + 1]); m = (n1 + n2) / np.linalg.norm(n1 + n2)
            out.append(P_[i] + m * d / (m @ n1))
    return out


def wires():
    g = {}
    s = -1                                               # OUT ends
    # (design frame, OUT ends at -y) 7 V pair (top OUT): down in the lane at y -21.0 / -18.8, forward through the tier gap as
    # a 2-wire ribbon with a 45 deg jog to the passage (y -11.1 / -8.9). 5 V pair (mid OUT): up in the lane at y -12.8 / -10.6
    # (outboard of the inductor, which sits at y -8.9..-1.8 on the OUT half and reaches x -65.4), then forward in the tier gap
    # as a second ribbon inside the 7 V one with a parallel 45 deg jog to y -6.7 / -4.5
    ref = [(X_W, -21.0), (XA, -21.0), (XA + 9.9, -11.1), (X_OUT + 4.0, -11.1)]
    def ribbon(d):
        return [(x, y, ZG) for x, y in offset_2d(ref, d)]
    g['7V_a'] = loop_out(X_E, s, ZT - 2.5, ZT - 2.5, Y_FAR) + [(X_W, -21.0, ZT - 2.5)] + ribbon(0.0)
    g['7V_b'] = loop_out(X_E, s, ZT + 2.5, ZT + 2.5, Y_FAR) + [(X_W, -18.8, ZT + 2.5)] + ribbon(2.2)
    XJ = -12.8 - (37.5 + 2.2 * math.sqrt(2) + 2.2 * math.sqrt(2)) + DX   # 5V_a corner on the line 2.2 inside 7V_b's diagonal
    ref5 = [(X_W, -12.8), (XJ, -12.8), (XJ + 6.1, -6.7), (X_OUT + 4.0, -6.7)]
    def ribbon5(d):
        return [(x, y, ZG) for x, y in offset_2d(ref5, d)]
    g['5V_a'] = loop_out(X_E, s, ZM + 2.5, ZM + 2.5, Y_FAR) + [(X_W, -12.8, ZM + 2.5)] + ribbon5(0.0)
    g['5V_b'] = loop_out(X_E, s, ZM - 2.5, ZM - 2.5, Y_FAR) + [(X_W, -10.6, ZM - 2.5)] + ribbon5(2.2)
    # 15 V link mid IN -> top IN (same pole stays on the same level side; C_p crosses through an outer loop)
    s = 1
    top_in = lambda yl, z: [(X_W, yl, z), (X_W, s * Y_FAR, z), (X_E, s * Y_FAR, z), (X_E, s * ENTRY_Y, z)]
    g['15V_link_p'] = loop_out(X_E, s, ZM - 2.5 + 1.0, ZM + 3.5, Y_FAR + 2.0) + [(X_W, 24.6, ZM + 3.5)] + top_in(24.6, ZT - 2.5)
    g['15V_link_q'] = loop_out(X_E, s, ZM + 2.5 + 1.0, ZM + 1.5, Y_FAR) + [(X_W, 22.4, ZM + 1.5)] + top_in(22.4, ZT + 2.5)
    if VARIANT == 'F':
        pd_in = lambda yl, z: [(X_W, yl, z), (X_W, 17.4, z), (PD_X_E, 17.4, z), (PD_X_E, PD_FACE_Y - 0.5, z)]
        g['15V_feed_p'] = loop_out(X_E, s, ZM - 2.5 - 1.0, ZM - 3.5, Y_FAR) + [(X_W, 17.5, ZM - 3.5), (X_W, 17.5, -11.5), (X_W, 11.4, -11.5)] + pd_in(11.4, PD_TERM_Z[0])
        # + is the lower screw at both ends, so the pair must cross once: feed_q steps 2.2 forward (x -62.4, over the terminal
        # block top x -60.1) below the middle board and crosses in front of feed_p inside the narrow tier
        X2 = X_W + 2.2
        g['15V_feed_q'] = loop_out(X_E, s, ZM + 2.5 - 1.0, ZM - 1.5, Y_FAR) + [(X_W, 15.3, ZM - 1.5), (X_W, 15.3, -9.5), (X_W, 9.2, -9.5), (X_W, 9.2, -14.5), (X2, 9.2, -16.7),
                                                                            (X2, 9.2, PD_TERM_Z[1]), (X2, 17.4, PD_TERM_Z[1]), (PD_X_E, 17.4, PD_TERM_Z[1]), (PD_X_E, PD_FACE_Y - 0.5, PD_TERM_Z[1])]
    else:
        # G: 15 V comes from the pack through passage P2 (y 9.0 / 11.2) along the tier gap into the lane, then outward
        def from_pack(y_pass, y_lane, z_lane):
            return [(X_OUT + 4.0, y_pass, ZG), (-51.0 + DX, y_pass, ZG), (-60.0 + DX, y_lane, ZG), (X_W, y_lane, ZG), (X_W, y_lane, z_lane)]
        # inside the pack (layout G pack_study placement: 5991 PCB back x -36.96, terminal entries x -41.56, z -5.44 / -8.94, face y 13.70):
        # out +y, up at y 16.4 in a pack-wall recess (|y| <= 17.6), inward at z 13.9 and back through passage P2
        XP = -41.56; ZPP, ZPQ = 3.07 - 8.51, 3.07 - 12.01
        pack_p = [(XP, 13.2, ZPP), (XP, 16.4, ZPP), (XP, 16.4, ZG), (XP, 9.0, ZG)]
        pack_q = [(XP, 13.2, ZPQ), (XP, 16.4, ZPQ), (-45.5, 16.4, ZPQ + 2.5), (-45.5, 16.4, ZG), (-47.0, 11.2, ZG)]
        g['15V_feed_p'] = pack_p + from_pack(9.0, 15.3, ZM - 3.5)[1:] + list(reversed(loop_out(X_E, s, ZM - 2.5 - 1.0, ZM - 3.5, Y_FAR)))
        g['15V_feed_q'] = pack_q + from_pack(11.2, 17.5, ZM - 1.5)[1:] + list(reversed(loop_out(X_E, s, ZM + 2.5 - 1.0, ZM - 1.5, Y_FAR)))
    return g


NET = {'7V_a': '7V', '7V_b': '7V', '5V_a': '5V', '5V_b': '5V', '15V_link_p': 'p', '15V_link_q': 'q', '15V_feed_p': 'p', '15V_feed_q': 'q'}
COL = {'7V': [1.0, 0.5, 0.0, 1], '5V': [1.0, 0.9, 0.0, 1], 'p': [0.85, 0.05, 0.05, 1], 'q': [0.05, 0.05, 0.05, 1]}


def path_pts(wp):
    return K.fillet_path(wp, BEND, n=8)


def trim_start(pts, L):
    """drop the first L mm (wire inside the terminal clamp) for the collision checks."""
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    i = np.searchsorted(d, L); return pts[i:]


# ------------------------------------------------------------------ frame parts
def xl_bosses():
    parts, cuts = [], []
    for zc in BOARDS.values():
        for h in xl_place([(PCB_MID, a, b) for a, b in XL_HOLES_L], zc):
            y, z = h[1], h[2]
            parts.append(P.cyl_x(2.25, XL_PIN_FACE_X, X_IN + 0.01, y, z))
            sg = np.sign(y); parts.append(P.box((XL_PIN_FACE_X, min(y, sg * (YI + 0.01)), z - 1.5), (X_IN, max(y, sg * (YI + 0.01)), z + 1.5)))
            cuts.append(P.cyl_x(0.8, XL_PIN_FACE_X - 1, X_OUT - 0.3, y, z))   # pilot to x -45.3 as C2: M2 x 6 through the 1.65 PCB bites 4.35
    return parts, cuts


BOSS_LEN = 5.0                                           # board boss length from its seat where the torso shells allow it


def stub_spec(z):
    """(radius, front end x) of the boss stub in front of the front wall (x -47) at an XL4015 hole of real height z, or
    None. The torso shells close in diagonally ahead of the wall at the z 17.7 and z 10.1 holes (shell gap to the boss at
    x -47: 1.29 / 1.17 and 2.09 / 1.97 mm, falling about 0.95 mm per mm forward whatever the stub diameter), so:
    z 17.7: no stub, boss 3.2 long, M2 x 6 engages 3.2 mm, the tip stands 1.15 mm proud of the wall (each board keeps
    two screws at full engagement at its other holes); z 10.1: stub to x -46.0, boss 4.2 long (shell gap 1.18 / 1.04)."""
    if 15.0 < z < 20.0:
        return None
    if 5.0 < z < 15.0:
        return 2.25, -46.0
    return 2.25, XL_PIN_FACE_X + BOSS_LEN                # z 38.7 (shell gap over 3 mm) and z -10.9 (inside the cover plate)


def boss_extensions():
    """boss stubs in front of the front wall (x -47) where no cover plate backs the boss."""
    parts = []
    for zc in BOARDS.values():
        for h in xl_place([(PCB_MID, a, b) for a, b in XL_HOLES_L], zc):
            sp = stub_spec(h[2])
            if sp:
                parts.append(P.cyl_x(sp[0], X_IN - 0.01, sp[1], h[1], h[2]))
    if VARIANT == 'F':
        for u, v in PD_HOLES:
            h = pd_w(u, v, 0); parts.append(P.cyl_x(2.25, X_IN - 0.01, PD_BACK_X + BOSS_LEN, h[1], h[2]))
    return parts


def pd_bosses():
    parts, cuts = [], []
    if VARIANT != 'F':
        return parts, cuts
    for u, v in PD_HOLES:
        h = pd_w(u, v, 0)
        parts.append(P.cyl_x(2.25, PD_BACK_X, X_IN + 0.01, h[1], h[2])); cuts.append(P.cyl_x(0.8, PD_BACK_X - 1, X_OUT - 0.3, h[1], h[2]))   # pilot to x -45.3: M2 x 6 through the 1.6 PCB bites 4.4
    return parts, cuts


# Cap retention: two M2 x 6 through ears under the step (outside the box, beside the narrow tier) into frame bosses, and two
# tongues at the top corners of the cap that run forward under the frame top wall with a tooth in a slot through the wall.
# design +y = real -y: that screw sits under the step. Design -y = real +y: the USB-C plug envelope (x -57 .. -49.5, z -30.66 ..
# -17.66) fills the space under the step there, so that screw sits low beside the narrow tier, under the plug, with a web
# into the narrow tier side wall.
LID_SCREWS = [(23.8, -17.4), (-23.8, -33.6)]
LID_EARS = [((21.3, -17.4), (26.3, -14.6)), ((-23.8, -34.2), (-15.0, -32.2))]   # (y0, z0), (y1, z1) web from the box wall to each ear
LID_BOSS_R = [2.5, 2.25]                                 # low boss dia 4.5: top z -31.35, 0.69 under the plug envelope
TONGUE_Y = (24.0, 30.2)                                  # |y| range of each tongue (top corners: bodies there stay below z 33.4)
TONGUE_Z = (ZI1 - 1.2, ZI1)                              # under the top wall inner face z 41.8
TONGUE_L = 5.5; TOOTH = (2.5, 4.5); TOOTH_H = 1.0; SLOT_CLR = 0.2


def lid_bosses():
    """frame bosses for the two cap screws: dia 5, X_SPLIT .. +5.6, merged into the step underside (outside the box)."""
    parts, cuts = [], []
    for (y, z), ((y0, z0), (y1, z1)), rb in zip(LID_SCREWS, LID_EARS, LID_BOSS_R):
        parts.append(P.cyl_x(rb, X_SPLIT, X_SPLIT + 5.6, y, z)); parts.append(P.box((X_SPLIT, y0, z0), (X_SPLIT + 5.6, y1, z1)))
        cuts.append(P.cyl_x(0.8, X_SPLIT - 1, X_SPLIT + 5.2, y, z))
    for sg in (1, -1):                                   # tooth slots through the top wall
        lo, hi = sorted([sg * (TONGUE_Y[0] - SLOT_CLR), sg * (TONGUE_Y[1] + SLOT_CLR)])
        cuts.append(P.box((X_SPLIT + TOOTH[0] - SLOT_CLR, lo, ZI1 - 0.1), (X_SPLIT + TOOTH[1] + SLOT_CLR, hi, Z1 + 0.5)))
    return parts, cuts


def cap_features():
    """cap ears (1.2 flange at the seam) and the two top tongues with their teeth."""
    parts, holes = [], []
    for (y, z), ((y0, z0), (y1, z1)), rb in zip(LID_SCREWS, LID_EARS, LID_BOSS_R):
        parts += [P.cyl_x(rb, X_SPLIT - 1.2, X_SPLIT, y, z), P.box((X_SPLIT - 1.2, y0, z0), (X_SPLIT, y1, z1 + (0.4 if z > -20 else 0.0)))]
        holes.append(P.cyl_x(1.1, X_SPLIT - 2, X_SPLIT + 1, y, z))
    for sg in (1, -1):
        lo, hi = sorted([sg * TONGUE_Y[0], sg * TONGUE_Y[1]])
        parts.append(P.box((X_SPLIT - 2.0, lo, TONGUE_Z[0]), (X_SPLIT, hi, TONGUE_Z[1] + 0.2)))       # root, merged into the cap top wall
        parts.append(P.box((X_SPLIT - 0.1, lo, TONGUE_Z[0]), (X_SPLIT + TONGUE_L, hi, TONGUE_Z[1])))   # tongue, flush under the frame top wall
        parts.append(P.box((X_SPLIT + TOOTH[0], lo + sg * 0.0, TONGUE_Z[1]), (X_SPLIT + TOOTH[1], hi, TONGUE_Z[1] + TOOTH_H)))
    return parts, holes


COVER_LANE_R = 2.2
PASSAGES = {}   # outside-wires draft 2026-10-14: P1 deleted, front plate solid (Shawn); G keeps its own P2 below
P1_RETIRED = {'P1_out': dict(y=(-12.7, -2.9), z=(ZG - 1.4, ZG + 1.4))}
if VARIANT == 'G':
    PASSAGES['P2_15V'] = dict(y=(7.6, 13.0), z=(ZG - 1.4, ZG + 1.4))


def passage_cut(p, r=1.0):
    y0, y1 = p['y']; z0, z1 = p['z']; x0, x1 = X_IN - 0.5, X_OUT + 0.5
    return P.union([P.box((x0, y0 + r, z0), (x1, y1 - r, z1)), P.box((x0, y0, z0 + r), (x1, y1, z1 - r))]
                   + [P.cyl_x(r, x0, x1, y, z) for y in (y0 + r, y1 - r) for z in (z0 + r, z1 - r)])


def build(ol, outer, inner):
    shell = (outer - inner) ^ P.box((X_SPLIT, -60, -60), (X_IN + 0.5, 60, 60))
    cover = BRP.build_cover().translate([DX, 0, 0])
    poly = outline_poly(ol)
    web = P.extrude_yz(poly.intersection(sbox(-HW - 1, -80, HW + 1, -2.0)), X_IN, X_OUT)
    xb, xc = xl_bosses(); pb, pc = pd_bosses(); lb, lc = lid_bosses(); cf, ch = cap_features()
    parts = P.union(xb + pb) ^ (outer + P.extrude_yz(poly, X_IN - 0.5, X_OUT + 1))
    frame = P.union([shell, cover, web, parts, P.union(boss_extensions()), P.union(lb) - inner])
    cuts = xc + pc + lc + window_cuts() + [passage_cut(p) for p in PASSAGES.values()]
    cuts += [P.cyl_x(BRP.COVER['hole_r'], X_IN - 1, X_OUT + 1, y, z) for (y, z) in BRP.POST['holes']]
    # lower cover screws (|y| 16.1, z -36.5) sit at the narrow tier's bottom corners: a dia 4.4 head and driver lane from the
    # plate face to the rim (M2 head dia 3.8 + 0.3 radial)
    cuts += [P.cyl_x(COVER_LANE_R, X_LID - 1, X_IN, y, z) for (y, z) in BRP.POST['holes'] if z < 0]
    frame = frame - P.union(cuts)
    cap = (outer - inner) ^ P.box((X_LID - 1, -60, -60), (X_SPLIT, 60, 60))
    wcut = [c for c, k in zip(window_cuts(), windows()) if k != 'pd5991_usbc']   # the cap closes the rim end of the USB-C slot
    lid = (P.union([cap] + cf) - P.union(wcut + ch))
    return frame, lid


# ------------------------------------------------------------------ body points for the rounding limits
def board_meshes(R=R_DES):
    src = trimesh.load(str(XL_SRC), force='mesh')
    return {nm: trimesh.Trimesh(xl_place(src.vertices, zc, R), src.faces, process=False) for nm, zc in BOARDS.items()}


def board_solids(meshes):
    out = {}
    for nm, m in meshes.items():
        zc = BOARDS[nm]; parts = []
        for p_ in m.split(only_watertight=False):
            if len(p_.vertices) < 4 or np.ptp(p_.vertices, axis=0).min() <= 1e-3:
                continue
            if np.ptp(p_.vertices, axis=0).max() > 60:
                parts.append(P.box((XL_MID_X - 0.825 - 1.65 + 0.0, -30.85, zc - HALF_W), (XL_PIN_FACE_X, 30.85, zc + HALF_W))); continue
            parts.append(m3.Manifold.hull_points(np.asarray(p_.vertices, float)))
        out[nm] = P.union(parts)
    if VARIANT == 'F':
        out['pd5991'] = P.union([P.box(lo, hi) for lo, hi in pd_boxes().values()])
    return out


def body_points(meshes, wp):
    pts, clr, tag = [], [], []
    for nm, m in meshes.items():
        v = np.unique(np.round(m.vertices, 3), axis=0)
        pcb_end = np.abs(v[:, 1]) > 30.5          # PCB ends and terminal-block ends sit at the side wall by design (layout D)
        pts.append(v); clr.append(np.where(pcb_end, -0.02, CLR)); tag += [f'{nm}:{"board end at the side wall" if e else "body"}' for e in pcb_end]
    if VARIANT == 'F':
        for k, (lo, hi) in pd_boxes().items():
            if k == 'usbc':
                continue
            c = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in np.linspace(lo[1], hi[1], 5) for z in np.linspace(lo[2], hi[2], 5)])
            pts.append(c); clr.append(np.full(len(c), CLR)); tag += [f'pd5991:{k}'] * len(c)
    for k, w in wp.items():
        p = path_pts(w); p = np.array([q for q in p if q[0] < X_IN - 0.5 and not in_window_band(q)])
        if len(p):
            cw = np.minimum(WIRE_R + CLR + 0.1, (p[:, 0] - X_LI) - 1e-3)   # 0.1 mesh tolerance; flat lid face is exact (lane plane 1.3)
            pts.append(p); clr.append(cw); tag += [f"wire {k}"] * len(p)
    P_ = np.vstack(pts); C_ = np.concatenate(clr)
    # the cap slides on CAP_DROP low: every body or wire point in the cap zone also has to clear the cap raised by CAP_DROP
    # (equivalently, the point lowered... the cap lowered = the point raised relative to it)
    cz = P_[:, 0] < X_LID + RCAP
    P_ = np.vstack([P_, P_[cz] + [0.0, 0.0, CAP_DROP]]); C_ = np.concatenate([C_, C_[cz]]); tag = tag + [t + ' (cap slide, 1.2 low)' for t, c in zip(tag, cz) if c]
    keep = np.array([not in_window_band(q) for q in P_])
    return P_[keep], C_[keep], [t for t, k in zip(tag, keep) if k]


RCAP = 8.0


def search_radii(ol, pts, clr, tags, use_flat_rear=True):
    def ok_pts():
        return ol.inner_np(pts) <= -clr
    def flat():
        return min(ol.flat_ok(y, z) for y, z in LID_SCREWS) >= 0
    res = {}
    def scan(name, setter, getter, hi, lo, step=0.1, use_flat=True):
        keep = getter(); best = None; lim = None
        for R in np.arange(hi, lo - 1e-9, -step):
            setter(float(R)); sv = ol.inner_np(pts) + clr; okv = sv <= 0
            fl = flat() if use_flat else True
            if okv.all() and fl:
                best = round(float(R), 2); break
            if not okv.all():
                i = int(np.argmax(sv)); lim = f'{tags[i]} at {np.round(pts[i], 2).tolist()}'
            else:
                lim = 'lid screw head seat (flat lid face) at ' + str(min(LID_SCREWS, key=lambda s: ol.flat_ok(*s)))
        setter(best if best is not None else keep)
        res[name] = dict(radius=best, limitedBy=lim if (best is not None and best < hi - 1e-6) else 'cap %.1f' % hi)
    W, N = ol.W, ol.N
    corner = [('W top corners (y-z)', lambda r: setattr(W, 'rc_top', r), lambda: W.rc_top, 6.0, 0.0),
              ('W step corners (y-z, convex)', lambda r: setattr(W, 'rc_bot', r), lambda: W.rc_bot, 6.0, 0.0)]
    if N is not None:
        corner += [('N bottom corners (y-z)', lambda r: setattr(N, 'rc_bot', r), lambda: N.rc_bot, 6.0, 0.0),
                   ('step concave blend (y-z)', lambda r: setattr(ol, 'rf', r), lambda: ol.rf, 3.0, 0.0)]
    for args in corner:
        scan(*args, use_flat=False)
    rear = [('rear vertical edges, full width', 'side'), ('rear top edge', 'top'), ('rear step edge (underside of the step)' if N is not None else 'rear bottom edge', 'step')]
    if N is not None:
        rear += [('rear vertical edges, 5991 tier', 'nside'), ('rear bottom edge, 5991 tier', 'nbot')]
    for _ in range(2):                                   # all rounding lives in the cap; limits are the boards, wires and the dropped cap slide
        for nm, c in rear:
            scan(nm, lambda r, c=c: ol.R.__setitem__(c, r), lambda c=c: ol.R[c], RCAP, R_REAR, use_flat=False)
    return res


def gap(a, b, s=10.0):
    return round(float(a.min_gap(b, s)), 3)


import time as _t
_T0 = _t.time()
def stage(m):
    print(f'[{_t.time() - _T0:6.1f}s] {m}', flush=True)


if __name__ == '__main__':
    out = dict(variant=VARIANT)
    meshes = board_meshes(); WP = wires()
    for nm, m in board_meshes(R_XL).items():                         # real boards, real world
        m.export(OUTDIR / f'xl4015_{nm}-world.stl')
        m.simplify_quadric_decimation(face_count=12000).export(OUTDIR / f'xl4015_{nm}_render.stl')
    if VARIANT == 'F':
        bx = pd_boxes()
        trimesh.util.concatenate([trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix(real_pts((lo + hi) / 2))) for lo, hi in bx.values()]).export(OUTDIR / 'pd5991_F-world.stl')
    stage('boards'); ol = outline()
    pts, clr, tags = body_points(meshes, WP)
    stage('points %d' % len(pts))
    import copy
    olb = copy.deepcopy(ol); body_only = search_radii(olb, pts, clr, tags, use_flat_rear=False)
    out['rounding'] = search_radii(ol, pts, clr, tags)
    out['rounding']['bodiesOnlyNoLidScrews'] = body_only
    out['rounding']['note'] = ('outer radii; inner radius = outer - 1.2 (constant wall). Limits from every board-mesh vertex (per-body, 0.3 clearance; '
                               'PCB ends may touch the side wall as in D), the 5991 part boxes, the wire centrelines (0.9 + 0.3) and the flat '
                               'seat of each lid screw head (dia 4.2). Bodies inside a window band do not limit (the wall is cut there).')
    out['rounding']['final'] = dict(R={k: round(v, 2) for k, v in ol.R.items()}, rcTop=ol.W.rc_top, rcStep=ol.W.rc_bot,
                                    rcNbot=(ol.N.rc_bot if ol.N else None), rf=ol.rf)
    X_SPLIT = round(math.ceil((X_LID + max(ol.R.values())) * 20) / 20, 2)      # frame rim: the cap holds all rear rounding
    out['rounding']['final']['frameRimX'] = X_SPLIT
    stage('radii ' + json.dumps(out['rounding']['final'])); outer, inner = ol.solids(0.3, x_shift=0.15)   # grid planes off the cap seam X_SPLIT (watertight cap)
    stage('solids')
    frame, lid = build(ol, outer, inner)
    tag = 'F' if VARIANT == 'F' else 'G'
    if VARIANT == 'F':
        frameR, lidR = real_m(frame), real_m(lid)
    else:
        frameR, lidR = frame, lid
    for man, nm in ((frameR, f'frame_{tag}-world.stl'), (lidR, f'lid_{tag}-world.stl')):
        mm = P.from_m(man); mm.merge_vertices(); mm.export(OUTDIR / nm)
        out[nm] = dict(volume_mm3=round(float(man.volume()), 1), grams=GRAMS(float(man.volume())), genus=int(man.genus()),
                       bodies=sum(1 for q in mm.split(only_watertight=False) if abs(q.volume) > 1.0), bounds=np.round(mm.bounds, 2).tolist())
    out['massTotalG'] = round(out[f'frame_{tag}-world.stl']['grams'] + out[f'lid_{tag}-world.stl']['grams'], 2)
    b = P.from_m(frame + lid).bounds
    out['box'] = dict(xExtent=[round(float(b[0][0]), 2), round(float(b[1][0]), 2)], frameRimX=X_SPLIT, capX=[X_LID, X_SPLIT], capInnerRearFaceX=X_LI, frontPlateX=[X_IN, X_OUT],
                      outerDepthBehindFrontPlate=round(X_IN - X_LID, 2), absY=HW, zTop=Z1,
                      zBottom=(ZB_OUT if VARIANT == 'F' else Z_STEP_OUT), packFloorZ=-44.0,
                      bottomAbovePackFloorMm=round((ZB_OUT if VARIANT == 'F' else Z_STEP_OUT) + 44.0, 2))
    stack = dict(topWallInner=ZI1, top7V=dict(zc=ZT, pcbZ=[ZT - HALF_W, ZT + HALF_W]), tierGap=dict(pcbGapMm=GAP_PCB, wirePlaneZ=ZG),
                 mid5V=dict(zc=ZM, pcbZ=[MID_BOTTOM, ZM + HALF_W]), stepInnerZ=Z_STEP_IN, stepOuterZ=Z_STEP_OUT)
    if VARIANT == 'F':
        stack['pd5991'] = dict(pcbZ=[round(PD_BOT, 3), PD_TOP], pcbBackX=PD_BACK_X, narrowInnerAbsY=round(PY_IN, 3), narrowOuterAbsY=round(PY_OUT, 3),
                               narrowWidth=round(2 * PY_OUT, 2), floorInnerZ=round(ZB_IN, 3), floorOuterZ=round(ZB_OUT, 3),
                               terminalEntryZ=[round(z, 2) for z in PD_TERM_Z], usbSocketCentre=[-53.25, round(PD_PCB[1] / 2 + 1.143, 3), round(PD_TOP - 10.16, 2)],
                               terminalSide='-y', usbSide='+y')
    out['stack'] = stack
    # lane: depth over the tallest bodies the wires cross
    out['lane'] = dict(wirePlaneX=round(X_W, 3), lidInnerX=X_LI, extraDepthVsLayoutD=0.0,
                       note='lid inner face kept at layout D depth (inductor top x %.3f needs 0.3); every lane run crosses only terminals, caps, '
                            'diode and screw heads, never the inductor or the trimmers' % (XL_MID_X - 14.345))
    RW = (lambda w: real_window(w)) if VARIANT == 'F' else (lambda w: w)
    RY = (lambda y: tuple(sorted((-y[0], -y[1])))) if VARIANT == 'F' else (lambda y: y)
    out['frame'] = 'real world (y-mirror of the design frame)' if VARIANT == 'F' else 'world'
    out['windows'] = {k: RW(w) for k, w in windows().items()}
    out['passages'] = {k: dict(x=[X_IN, X_OUT], y=RY(v['y']), z=v['z']) for k, v in PASSAGES.items()}
    out['lidScrews'] = [real_yz(y, z) if VARIANT == 'F' else (y, z) for y, z in LID_SCREWS]
    out['capRetention'] = dict(screws=dict(positionsYZ=out['lidScrews'], earX=[round(X_SPLIT - 1.2, 2), X_SPLIT], bossX=[X_SPLIT, round(X_SPLIT + 5.6, 2)], screw='M2 x 6, 4.8 engagement'),
                               tongues=dict(absY=TONGUE_Y, z=list(TONGUE_Z), x=[round(X_SPLIT - 2.0, 2), round(X_SPLIT + TONGUE_L, 2)],
                                            toothX=[round(X_SPLIT + TOOTH[0], 2), round(X_SPLIT + TOOTH[1], 2)], toothZ=[TONGUE_Z[1], TONGUE_Z[1] + TOOTH_H],
                                            slotX=[round(X_SPLIT + TOOTH[0] - SLOT_CLR, 2), round(X_SPLIT + TOOTH[1] + SLOT_CLR, 2)], slotAbsY=[TONGUE_Y[0] - SLOT_CLR, TONGUE_Y[1] + SLOT_CLR]),
                               fitting='slide the cap forward 1.2 mm low until it meets the rim, lift it 1.2 mm so the teeth enter the top-wall slots, screw the two ears',
                               approachPath=[[-15.0, 0.0, -CAP_DROP], [0.0, 0.0, -CAP_DROP], [0.0, 0.0, 0.0]])
    out['ends'] = dict(xlIN='-y', xlOUT='+y', pd5991Terminal='-y', pd5991USB='+y') if VARIANT == 'F' else None
    # wires
    stage('frame built'); S = board_solids(meshes); stage('board solids')
    tubes = {}; wrow = {}
    FRAME_TM = P.from_m(frame); BF_TRIM = lambda q: trim_start(trim_start(q, 1.6)[::-1], 1.6)[::-1]
    for k, w in WP.items():
        p = path_pts(w); tubes[k] = K.tube(p, WIRE_R)
        chk = K.tube(trim_start(trim_start(p, 1.6)[::-1], 1.6)[::-1], WIRE_R)
        wrow[k] = dict(net=NET[k], lengthMm=round(K.path_length(p), 1), minBendRadius=round(float(K.min_bend_radius(p)), 2),
                       gapFrame=gap(chk, frame), frameNearest=K.nearest(BF_TRIM(p), FRAME_TM, WIRE_R), gapLid=gap(chk, lid), gapBoards={nm: gap(chk, s_) for nm, s_ in S.items()},
                       maxAbsY=round(float(np.abs(p[:, 1]).max() + WIRE_R), 2))
    if VARIANT == 'G':
        PDG = P.union([P.mesh_to_m(b.convex_hull) for b in trimesh.load(str(OUTDIR / 'pd5991_G-world.stl'), force='mesh').split(only_watertight=False)])
        ORBg = P.mesh_to_m(P.openrb_mesh()); V18g = P.mesh_to_m(P.load_stl(P.WORLD / 'rear_pack-v18.stl')); PLG = P.mesh_to_m(trimesh.load(str(OUTDIR / 'usbc_plug_G-world.stl'), force='mesh'))
        for k in ('15V_feed_p', '15V_feed_q'):
            p = path_pts(WP[k]); chk = K.tube(trim_start(p, 1.6), WIRE_R)
            wrow[k].update(gapPd5991InPack=gap(chk, PDG), gapOpenRB=gap(chk, ORBg), gapAsBuiltPackV18=gap(chk, V18g),
                           packPortionNote='x > -48 runs inside the reprinted pack; as-built V18 contact is the side-wall recess listed in pack_study')
        out['pd5991InPackVsFrameG'] = dict(gap=gap(frame, PDG, 10.0), overlapMm3=round(float((frame ^ PDG).volume()), 3))
        out['usbcPlugVsFrameG'] = gap(frame, PLG, 10.0)
    stage('per-wire'); ww = {}
    ks = list(WP)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b_ = ks[i], ks[j]
            same = NET[a] == NET[b_] and NET[a] in ('p', 'q')
            ta = tubes[a] if not same else K.tube(trim_start(path_pts(WP[a]), 6.0), WIRE_R)
            tb = tubes[b_] if not same else K.tube(trim_start(path_pts(WP[b_]), 6.0), WIRE_R)
            ww[f'{a}|{b_}'] = gap(ta, tb, 5.0)
    out['wires'] = dict(perWire=wrow, wireWireGapMm=dict(sorted(ww.items(), key=lambda kv: kv[1])),
                        note='gaps exclude the 1.6 mm inside each terminal clamp; same-pole wires sharing a clamp are compared from 6 mm out; '
                             'a negative wire-wire gap would be interpenetration (touching insulation is fine)')
    RP = real_pts if VARIANT == 'F' else (lambda q: np.asarray(q, float))
    P.jdump({k: dict(points=np.round(RP(path_pts(w)), 3).tolist(), net=NET[k]) for k, w in WP.items()}, OUTDIR / f'wires_{tag}_inside_reference.json')   # the inside wires still drive the radius search so the cap stays identical
    stage('wire-wire')
    man_ = ia_lib.manifest(); SKIP = set(P.RETIRED) | set(P.SELF_KEYS) | {'rear_pack_cover', 'rear_pack', 'rear_frame', 'rear_lid', 'xl4015_left', 'xl4015_right', 'pd5991'}
    body = frameR + lidR; mb = P.from_m(body).bounds; rows = {}
    allw = P.union([K.tube(RP(K.fillet_path(w, BEND, n=4)), WIRE_R, seg=8) for w in WP.values()])
    for k, rec in man_.items():
        if k in SKIP:
            continue
        lo, hi = np.array(rec['bounds'])
        if np.all(lo - 15 <= mb[1] + 6) and np.all(hi + 15 >= mb[0] - 6):
            S_ = P.solid_m(k); rows[k] = dict(module=rec.get('module'), boxGapMm=gap(body, S_, 20.0), wiresGapMm=gap(allw, S_, 20.0), overlapMm3=round(float((body ^ S_).volume()), 3))
    V18 = P.mesh_to_m(P.load_stl(P.WORLD / 'rear_pack-v18.stl')); ORB = P.mesh_to_m(P.openrb_mesh())
    rows['rear_pack-v18 (as built)'] = dict(boxGapMm=gap(body, V18, 20.0), wiresGapMm=gap(allw, V18, 20.0), note='cover seat: contact by design' if VARIANT == 'F' else 'G needs the pack 3 mm deeper (pack_study)')
    rows['openrb-board-upright'] = dict(boxGapMm=gap(body, ORB, 20.0), wiresGapMm=gap(allw, ORB, 20.0))
    out['clearancesHOME'] = dict(sorted(rows.items(), key=lambda kv: kv[1]['boxGapMm']))
    stage('home'); SH = {sk: P.solid_m(sk) for sk in ('shell_left', 'shell_right')}; out['shellPerWire'] = {k: {sk: gap(K.tube(RP(path_pts(WP[k])), WIRE_R), SH[sk], 20.0) for sk in ('shell_left', 'shell_right')} for k in WP}
    if VARIANT == 'F':
        zc = PD_TOP - 10.16; sy = PD_PCB[1] / 2 + 1.143          # real world: socket mouth at +y
        plug = P.box((-57.0, sy, zc - 6.5), (-49.5, sy + 25.0, zc + 6.5))
        prow = {}
        for k, rec in man_.items():
            if k in SKIP:
                continue
            lo, hi = np.array(rec['bounds'])
            if np.all(lo - 25 <= [-49.5, sy + 25, zc + 6.5]) and np.all(hi + 25 >= [-57.0, sy, zc - 6.5]):
                prow[k] = gap(plug, P.solid_m(k), 30.0)
        prow['frame_F'] = gap(plug, frameR, 5.0)
        out['usbcPlugEnvelope'] = dict(box=[[-57.0, round(sy, 2), round(zc - 6.5, 2)], [-49.5, round(sy + 25.0, 2), round(zc + 6.5, 2)]], note='13 x 7.5 body, 25 long, real world +y', gapsMm=dict(sorted(prow.items(), key=lambda kv: kv[1])))
    out['boardsVsFrame'] = {nm: dict(overlapMm3=round(float((frame ^ s_).volume()), 3), gapMm=gap(frame, s_, 5.0)) for nm, s_ in S.items()}
    out['boardsVsLid'] = {nm: gap(lid, s_, 5.0) for nm, s_ in S.items()}
    P.jdump(out, OUTDIR / f'layout_{tag.lower()}.json')
    print(json.dumps({k: out[k] for k in ('rounding', 'box', 'massTotalG', 'boardsVsFrame', 'boardsVsLid')}, indent=0)[:5000])
    print(json.dumps(out['wires'], indent=0)[:6000])
