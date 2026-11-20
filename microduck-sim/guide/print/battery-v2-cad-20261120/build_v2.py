"""MicroDuck battery backpack V2 rev B: printable frame and cap (Shawn approved the concept 2026-11-19/20, "可以，加购物车").

    Mac mini:  zsh mini_sync.sh push && zsh mini_sync.sh run 'zsh mini_chain.sh' && zsh mini_sync.sh pull

Source: ../battery-v2-concept-20261119 (README features F1-F12, concept_v2.py envelopes). Frame: backpack local = guide
frame = sim trunk frame, mm, x forward, y left, z up; standing, world z = guide z + 120. Both parts print in Orange.
Bought parts are drawn at their largest published size (battery 74 x 34 x 20). Fits come from cad-practice/print_fit.py
(H2S values; they sit inside the accepted band for the X1C and Elegoo too). No snaps, hooks, flexures or latches: every
part is held by walls and ribs, foam tape, or a screw.

Changes from the concept envelopes, each forced by a rule the concept did not apply (recorded in features.json):
- lower tier left wall moved out 1.8 mm (outer y 20.0 -> 21.8): the lower-left fixing screw's driver corridor needs 4 mm
  free radius (PRINT-FIT Access, Shawn "no screw hole parallel to and close to a wall"); the concept left 0.7 mm.
- front wall cut where the shell rear lips reach behind x -45 (guide mating shells): the concept drew a full front plate.
- battery left rib split around the lower-left driver corridor; column right wall stops at z 17 (XIAO room, finger zone).
- top battery stops: two pillars hung from the roof (front) and two tabs on the cap ribs (rear), both clear of the lead
  exit in the middle of the pack's top face (the concept's full-width ribs would block the leads when the pack slides in).
- high left cap screw z 17 -> 19 (its head would touch the flight-pack harness crossing at z 16).
- XIAO USB-C window turned to 7.5 (y) x 13 (z): the receptacle's long side runs along z with the board on the wall.
- low cap screws moved from bosses behind the pack (+-9, -38.9, through the pad tabs) to full-depth columns in the wings
  (17.6, -28) and (-27.825, -8); the pad tabs are located by two 3.4 pins on the cap and the pads go in after the battery.
  The guide print gate (steps_audit bv2-battery, 2026-11-20) found the rev B1 bosses and tabs blocking the battery's
  floor push; checks.py now sweeps every part pushed in after the frame is on the robot.

Writes build/: battery_v2_frame-world.stl, battery_v2_cap-world.stl, *-print.stl, parts (bought-part envelopes,
world frame) and build.json (geometry numbers, features built, print poses).
"""
import json, sys
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
MD = HERE.parents[2]                                            # microduck-sim
BP = MD / "microduck_rl/cmu/hardware/battery-backpack"
OUT = HERE / "build"; OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(MD.parent / "cad-practice")); import print_fit as F  # noqa: E402
PRINTER = "H2S"                                                 # fit values for the H2S (+0.10); inside the X1C/Elegoo band

# ------------------------------------------------------------------ parameters the part-selection results may change
# button: E-Switch PV6F240SS-331 (DigiKey EG4731-ND), green LED ring, Off-(On) SPST-NO, flat stainless actuator.
# PV6 datasheet (E-Switch 6.16.2021, LED-illumination body drawing p2, panel cutout p3): M16 x 1.0 thread, panel cutout
# 16.00 +0.20/-0, panel 1-10 mm, bezel 18.0 dia x 1.50 above the panel, body 16.50 and 20.0 to the terminal tips behind
# the panel face, green LED 2.8 V at 20 mA without a resistor (harness: 120 ohm 1/4 W from the 5 V line, 18 mA).
# Box limit at this spot: 24.65 mm behind the cap face (upper-left fixing screw head at x -48.6, 0.3 gap, 2 mm wires).
BTN_THREAD_D = 16.0
BTN_HOLE_D = round(BTN_THREAD_D + 2 * F.clearance("locating"), 2)   # 16.3 printed (vertical in the cap's print pose):
                             # locating fit 0.15/side; the datasheet cutout band is 16.00-16.20
BTN_NUT_CLEAR_D = 22.0       # keep-out for the M16 x 1 hex nut sweep; the PV6 drawing does not dimension the nut, so the
BTN_NUT_T = 3.0              # box keeps the 22 x 3 circle the 560's published nut needed (19 AF, 21.94 corners, 3 thick)
BTN_BEZEL = (18.0, 1.5)      # bezel diameter, height outside the panel
BTN_BODY_D = 16.0            # body = thread diameter
BTN_DEPTH = 20.0             # body + terminals behind the panel face (drawing)
BTN_WIRE = 2.0               # solder joints and wire bend behind the terminal tips
BTN_BODY_L = BTN_DEPTH + BTN_WIRE
BTN_C = (19.3, 30.2)         # (y, z) of the button axis on the cap
# contact pads: Keystone 615 right-angle bracket (catalog K75p129; purchase-decision-20261120-charging.json)
PAD_W = 7.1                  # bracket width (y)
PAD_FACE_L = 8.7             # horizontal leg L, under the floor along x
PAD_T = 0.81                 # brass thickness (floor pocket and tab recess depth)
PAD_TAB_H = 10.7             # vertical leg H, up the frame back face from the box bottom
PAD_HOLE_D = 3.7             # vertical-leg hole (the low cap screw passes it)
PAD_HOLE_Z = 7.1             # vertical-leg hole centre above the horizontal leg's outer face
PAD_FLAT_HOLE = (5.2, 3.3)   # horizontal-leg hole: centre from the vertical leg's outer face, diameter (unused, open)
PADS_Y = (9.0, -9.0)         # pad centres, 18 mm apart

# ------------------------------------------------------------------ outline (concept rev B, with the changes above)
WALL, FLOOR, ROOF, BACK, PLATE = 1.7, 2.1, 1.7, 1.7, 2.0   # floor 2.1: 1.29 stays under the 0.81 pad pocket (>= 1.2)
UP = ((-75.55, -32.05, -15.2), (-45.0, 32.05, 43.0))
LOW_Y_LEFT = 21.8            # concept 20.0; +1.8 for the lower-left driver corridor (fixing screw y 16.1 + 4.0 + wall 1.7)
LOW = ((-75.55, -25.3, -46.0), (-45.0, LOW_Y_LEFT, -15.2))
CHAMFER, CHAMFER_IN = 3.8, 2.5
CHAMFER_LEFT = 1.8         # front-left lower edge: the left leg passed the square corner at 7.41 mm (legsit.py) after the
                           # 1.8 mm widening; 1.8 keeps 1.34 mm of wall at the inner corner (x -47, y 20.1)
SPLIT_X = -73.85             # frame open to the back over the full height; cap = back plate x -75.55..-73.85
X_IN = UP[1][0] - PLATE      # -47.0, inner face of the front wall
# ------------------------------------------------------------------ bought parts (published sizes), positions
PLAY = 0.3
BAT = ((-69.3, -23.3, -43.9), (-49.3, 10.7, 30.1))      # 20 x 34 x 74 (listing text 72 x 34 x 20, drawing 74 x 34 x 19)
BY0, BY1 = BAT[0][1] - PLAY, BAT[1][1] + PLAY           # -23.6 .. 11.0: column inner faces
TAPE = 1.0                                              # 3M foam tape
POLOLU = ((-68.0, 25.15, -12.0), (-47.7, 29.35, 13.4))  # pololu.com 0.8 x 1.0 x 0.16 in; taped to the left wall (30.35)
DFR = ((-73.6, 14.2, -13.5), (-47.6, 22.2, 16.5))        # 30 x 26 x 8; taped to the thickened column rib (13.2)
XIAO = ((-73.3, -29.35, 17.5), (-52.3, -24.85, 35.0))    # 21 x 17.5, 4.5 with USB-C; taped to the right wall (-30.35)
XIAO_USB = dict(y=(-28.35, -25.15), z=(26.25 - 4.47, 26.25 + 4.47))   # receptacle 8.94 x 3.2 on the board's top face
DIODE = ((-66.0, -14.0, 31.0), (-56.5, -8.7, 36.3))     # 1N5822 DO-201AD in the lead bay
FOAM = ((-70.3, BAT[0][1], -36.0), (-69.3, BAT[1][1], 28.0))   # 1 mm foam pad behind the pack, above the low bosses (z <= -36.4)
# fixing screws (unchanged): M2 x 6 from inside the box through the front wall into the OpenRB pack posts
SCREWS = [(16.1, 26.0), (-16.1, 26.0), (16.1, -36.5), (-16.1, -36.5)]
HEAD_D, HEAD_H = 3.8, 1.6
# cap screws from behind into frame bosses: two M2 x 8 high, two M2 x 6 low through the pad tabs
BOSS_D = 5.0
# Every boss sits outside the paths of the parts pushed in from the open back after the frame is on the robot (battery,
# boards, diode, pads: insertion sweep in checks.py). The low screws are in the wings beside the battery column, on
# full-depth columns from the front wall (vertical in the front-down print pose, so no support): rev B1 had them on
# low bosses behind the pack, which blocked the battery's floor push (guide gate steps_audit bv2-battery, 2026-11-20).
COL_PILOT = 10.0             # blind pilot in the low columns: print_fit.pilot_depth(M2, 1.7 cap) = 9.3 for the longest M2
CAP_SCREWS = [dict(id="cap-high-left", yz=(29.0, 19.0), L=8, boss=5.0, pilot="through", column=None),
              dict(id="cap-high-right", yz=(-29.0, 39.0), L=8, boss=5.0, pilot="through", column=None),
              # lower-left wing, above the lower-left fixing screw's driver lane (16.1, -36.5): 6.0 mm from its axis
              dict(id="cap-low-left", yz=(17.6, -28.0), L=6, boss=None, pilot=COL_PILOT,
                   column=((15.1, -30.5), (LOW_Y_LEFT - WALL + 0.05, -25.5))),
              # right wing under the XIAO ledge, wall to column wall, standing on the step floor
              dict(id="cap-low-right", yz=(-27.825, -8.0), L=6, boss=None, pilot=COL_PILOT,
                   column=((UP[0][1] + WALL - 0.05, UP[0][2] + WALL - 0.05), (LOW[0][1] + 0.05, -4.5)))]
# contact pad tabs: located by two pins on the cap through their 3.7 holes (no screw; the horizontal leg sits in its
# floor pocket, the cap face holds the tab against the pocket's front end with 0.5 mm play)
PIN_D = round(PAD_HOLE_D - 2 * F.clearance("locating"), 2)     # 3.4: locating 0.15/side in the bought 3.7 hole
PIN_L = 2.5                                                     # from the cap face: through the 0.81 tab, 1.69 past it,
                                                                # tip 1.05 behind the foam (x -70.3)
CLEAR_D = F.clear("M2", "vertical", printer=PRINTER)            # 2.5 (cap holes, front-wall holes; both vertical in print)
PILOT_D = F.pilot("M2", "vertical", printer=PRINTER)            # 1.95 (boss pilots, vertical in print)
MOUTH = F.BED_CHAMFER                                           # 0.4 x 45 deg mouth chamfer on every hole end
LOOSE = F.clearance("loose", "horizontal")                      # 0.5 per side: pad pockets (bought part; the pocket's
                                                                # entry axis, world z, lies horizontal in the frame's print pose)
SHELL_CLEAR = 0.5                                               # gap kept to the shell rear lips
FLIGHT_CLEAR = 0.3                                              # gap kept to the flight wing plate cheeks


def box(lo, hi):
    lo, hi = np.array(lo, float), np.array(hi, float)
    return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
def U(ms): return mf.Manifold.batch_boolean(list(ms), mf.OpType.Add)
def to_tm(M):
    g = M.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=True)
def load_mf(p):
    m = trimesh.load(p, force="mesh", process=True); m.merge_vertices()
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def cyl_x(c_yz, r, x0, x1, r1=None, n=64):
    return mf.Manifold.cylinder(x1 - x0, r, r if r1 is None else r1, n).rotate((0, 90, 0)).translate((x0, c_yz[0], c_yz[1]))
def hole_x(c_yz, d, x0, x1, chamfer=MOUTH):
    """Through hole along x with a 45 deg mouth chamfer at both ends."""
    r = d / 2
    if chamfer <= 0: return cyl_x(c_yz, r, x0 - 0.5, x1 + 0.5)
    return U([cyl_x(c_yz, r, x0 - 0.5, x1 + 0.5), cyl_x(c_yz, r + chamfer + 0.5, x0 - 0.5, x0 + chamfer, r1=r),
              cyl_x(c_yz, r, x1 - chamfer, x1 + 0.5, r1=r + chamfer + 0.5)])
def corner_prism(x, y, c, z0, z1):
    a = c * np.sqrt(2.0)
    return mf.Manifold.cube((a, a, z1 - z0), True).rotate((0, 0, 45)).translate((x, y, (z0 + z1) / 2))
def prism_x(cs, x0, x1):
    """Extrude a (y, z) CrossSection along x from x0 to x1."""
    T = [[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]]
    return mf.Manifold.extrude(cs, x1 - x0).transform(T)


def shell_keepout():
    """(y, z) footprint of the shell rear lips behind x -44, grown by SHELL_CLEAR, cut through x -49.5..-44."""
    parts = []
    for f in ("shell_left.stl", "shell_right.stl"):
        piece = load_mf(BP / "mating" / f) ^ box((-60, -40, -60), (-44.0, 40, 60))
        if piece.volume() <= 0: continue
        T = [[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]]          # (x, y, z) -> (y, z, x): projection drops x
        cs = piece.transform(T).project().offset(SHELL_CLEAR, mf.JoinType.Round, 2.0, 32)
        parts.append(prism_x(cs, -49.5, -44.0))
    return U(parts)


def flight_keepout():
    """Wing-plate cheeks (flight pack, extensions/flight-20261110/cad/build/wing_plate-world.stl) that reach behind its back
    face x -51.95 by 1.55 mm at |y| 18.9..32.1, z -1..42.5. In flight the backpack sits 6.9 mm back on that plate, so the
    cheeks land in the frame's front wall: their (y, z) footprint, grown by FLIGHT_CLEAR, is cut through x -47.5..-44.
    FLIGHT_CLEAR is 0.3 (not 0.5) so the web beside the upper fixing holes (y +-16.1) stays 1.25 mm; a cheek that ends
    under 1.2 mm below the roof top (z 42.5 + 0.3 against 43) is cut through the top so no sliver is left."""
    W = load_mf(MD / "extensions/flight-20261110/cad/build/wing_plate-world.stl")
    piece = (W ^ box((-60, -40, -60), (-51.95, 40, 60))).translate((6.9, 0, 0))
    T = [[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]]
    cs = piece.transform(T).project().offset(FLIGHT_CLEAR, mf.JoinType.Round, 2.0, 32)
    cut = prism_x(cs, -47.5, -44.0)
    tops = []
    for b in piece.decompose():
        (x0, y0, z0, x1, y1, z1) = b.bounding_box()
        if b.volume() > 1.0 and UP[1][2] - 1.2 < z1 + FLIGHT_CLEAR < UP[1][2] + 1.0 and y0 < UP[1][1] and y1 > UP[0][1]:
            tops.append(box((-47.5, y0 - FLIGHT_CLEAR, z1 - 1.0), (-44.0, y1 + FLIGHT_CLEAR, UP[1][2] + 1.0)))
    return cut + U(tops) if tops else cut


def button_solid():
    y, z = BTN_C; x0 = UP[0][0]
    return U([cyl_x((y, z), BTN_BEZEL[0] / 2, x0 - BTN_BEZEL[1], x0), cyl_x((y, z), BTN_BODY_D / 2, x0, x0 + BTN_BODY_L),
              cyl_x((y, z), BTN_NUT_CLEAR_D / 2, SPLIT_X, SPLIT_X + BTN_NUT_T)])


def pad_solid(y):
    z0 = LOW[0][2]
    face = box((SPLIT_X, y - PAD_W / 2, z0), (SPLIT_X + PAD_FACE_L, y + PAD_W / 2, z0 + PAD_T))
    tab = box((SPLIT_X, y - PAD_W / 2, z0), (SPLIT_X + PAD_T, y + PAD_W / 2, z0 + PAD_TAB_H))
    flat = mf.Manifold.cylinder(PAD_T + 0.2, PAD_FLAT_HOLE[1] / 2, PAD_FLAT_HOLE[1] / 2, 48).translate((SPLIT_X + PAD_FLAT_HOLE[0], y, z0 - 0.1))
    return (face + tab) - hole_x((y, z0 + PAD_HOLE_Z), PAD_HOLE_D, SPLIT_X - 0.1, SPLIT_X + PAD_T + 0.1, chamfer=0.0) - flat


def pad_seat(y):
    """Floor pocket for the pad face and back-face recess for its tab, PAD_T deep, LOOSE per side."""
    z0, w = LOW[0][2], PAD_W / 2 + LOOSE
    face = box((SPLIT_X - 1, y - w, z0 - 1), (SPLIT_X + PAD_FACE_L + LOOSE, y + w, z0 + PAD_T))
    tab = box((SPLIT_X - 1, y - w, z0 - 1), (SPLIT_X + PAD_T, y + w, z0 + PAD_TAB_H + LOOSE))
    return face + tab


def bought_parts():
    P = {"battery 2S 3000 (B08LZ8L4YD)": box(*BAT), "battery foam pad": box(*FOAM),
         "Pololu 2813": box(*POLOLU), "Pololu tape": box((POLOLU[0][0], POLOLU[1][1], POLOLU[0][2]), (POLOLU[1][0], POLOLU[1][1] + TAPE, POLOLU[1][2])),
         "DFR1202": box(*DFR), "DFR1202 tape": box((DFR[0][0], DFR[0][1] - TAPE, DFR[0][2]), (DFR[1][0], DFR[0][1], DFR[1][2])),
         "XIAO SAMD21": box(*XIAO), "XIAO tape": box((XIAO[0][0], XIAO[0][1] - TAPE, XIAO[0][2]), (XIAO[1][0], XIAO[0][1], XIAO[1][2])),
         "XIAO USB-C plug (12.5 x 7 overmold)": box((-95.0, -30.25, 26.25 - 6.25), (XIAO[0][0] - 0.01, -23.25, 26.25 + 6.25)) ^ box((-95, -40, -60), (-60, 40, 60)),
         "16 mm LED button (E-Switch PV6F240SS-331)": button_solid(), "Schottky 1N5822 (DO-201AD)": box(*DIODE)}
    for y in PADS_Y: P[f"contact pad {'plus' if y > 0 else 'minus'}"] = pad_solid(y)
    return P


def slug(n):
    import re
    return re.sub(r"[^A-Za-z0-9]+", "_", n.split(" (")[0]).strip("_")


FEATURES = []          # ids of features built, checked against features.json
def feat(i): FEATURES.append(i)


def build():
    low_ov = (LOW[0], (LOW[1][0], LOW[1][1], LOW[1][2] + 0.5))     # 0.5 into the upper tier: no coplanar seam at z -15.2
    outer = box(*UP) + (box(*low_ov) - corner_prism(LOW[1][0], LOW[0][1], CHAMFER, LOW[0][2] - 1, LOW[1][2] + 0.6)
                        - corner_prism(LOW[1][0], LOW[1][1], CHAMFER_LEFT, LOW[0][2] - 1, LOW[1][2] + 0.6))
    feat("F1-lower-tier"); feat("F1-chamfer"); feat("F1-chamfer-left"); feat("upper-tier"); feat("F3-lead-bay")
    up_in = box((SPLIT_X - 1, UP[0][1] + WALL, UP[0][2] + WALL), (X_IN, UP[1][1] - WALL, UP[1][2] - ROOF))
    low_in = box((SPLIT_X - 1, LOW[0][1] + WALL, LOW[0][2] + FLOOR), (X_IN, LOW[1][1] - WALL, LOW[1][2] + WALL + 1))
    low_in = low_in - corner_prism(X_IN, LOW[0][1] + WALL, CHAMFER_IN, LOW[0][2], LOW[1][2] + WALL + 2)
    body = (outer ^ box((SPLIT_X, -40, -60), (0, 40, 60))) - up_in - low_in
    add = []
    # F2 battery column
    add.append(box((-70.3, LOW[0][1], LOW[1][2] + 0.2), (-47.0 + 0.01, BY0, 17.0)))               # right wall, upper tier, to z 17 (starts inside the step floor)
    feat("F2-column-right-wall")
    add.append(box((-70.3, BY1, LOW[0][2] + FLOOR - 0.01), (X_IN + 0.01, BY1 + 1.5, -41.5)))       # left rib, floor stub
    add.append(box((-70.3, BY1, -32.0), (X_IN + 0.01, BY1 + 1.5, 17.0)))                          # left rib, above the corridor
    add.append(box((-73.6, BY1, DFR[0][2]), (X_IN + 0.01, DFR[0][1] - TAPE, DFR[1][2] - 2.0)))     # thickened: DFR tape face 13.2
    feat("F2-left-rib"); feat("F5-dfr-rib")
    add.append(box((-49.3, -12.0, LOW[0][2] + FLOOR - 0.01), (X_IN + 0.01, 8.0, -41.0)))           # front floor stop
    feat("F2-front-stop")
    for y0, y1 in ((-8.0, -4.0), (1.0, 5.0)):                                                     # front top stops
        add.append(box((-52.3, y0, BAT[1][2] + PLAY), (-49.3, y1, UP[1][2] - ROOF + 0.01)))
    feat("F2-front-top-pillars")
    # F5 DFR ledge, F4 Pololu ribs, F6 XIAO ledge
    add.append(box((DFR[0][0], DFR[0][1] - TAPE - 0.01, -15.0), (X_IN + 0.01, LOW[1][1] - WALL + 0.01, DFR[0][2] - 0.1)))
    feat("F5-dfr-ledge")
    add.append(box((POLOLU[0][0] - 1.9, POLOLU[0][1] + 1.0, UP[0][2] + WALL - 0.01), (POLOLU[0][0] - 0.4, UP[1][1] - WALL + 0.01, POLOLU[1][2])))
    add.append(box((POLOLU[0][0] + 2.0, POLOLU[0][1] + 1.0, UP[0][2] + WALL - 0.01), (POLOLU[1][0] - 2.0, UP[1][1] - WALL + 0.01, POLOLU[0][2] - 0.2)))
    feat("F4-pololu-ribs")
    add.append(box((XIAO[0][0] + 0.5, UP[0][1] + WALL - 0.01, 15.8), (XIAO[1][0] - 3.0, XIAO[0][1] + 2.0, XIAO[0][2] - 0.2)))
    feat("F6-xiao-ledge")
    # F11 cap screw bosses (frame side): high bosses 5 mm with through pilots, low columns full depth with blind pilots
    for s in CAP_SCREWS:
        if s["column"] is None:
            add.append(cyl_x(s["yz"], BOSS_D / 2, SPLIT_X, SPLIT_X + s["boss"]))
        else:
            (y0, z0), (y1, z1) = s["column"]
            add.append(box((SPLIT_X, y0, z0), (X_IN + 0.01, y1, z1)))
    feat("F11-bosses"); feat("F11-low-columns")
    frame = body + U(add)
    cuts = []
    for s in CAP_SCREWS:
        if s["pilot"] == "through":
            cuts.append(hole_x(s["yz"], PILOT_D, SPLIT_X, SPLIT_X + s["boss"]))
        else:   # blind: mouth chamfer at the back face only
            cuts.append(U([cyl_x(s["yz"], PILOT_D / 2, SPLIT_X - 0.5, SPLIT_X + s["pilot"]),
                           cyl_x(s["yz"], PILOT_D / 2 + MOUTH + 0.5, SPLIT_X - 0.5, SPLIT_X + MOUTH, r1=PILOT_D / 2)]))
    feat("F11-pilots")
    for y, z in SCREWS:
        cuts.append(hole_x((y, z), CLEAR_D, X_IN, UP[1][0]))
    feat("fixing-holes")
    for y in PADS_Y: cuts.append(pad_seat(y))
    feat("F8-pad-pockets")
    cuts.append(box((SPLIT_X - 0.01, 22.6, UP[0][2] - 0.01), (-60.0, 26.1, UP[0][2] + WALL + 0.01)))
    feat("F10-lead-slot")
    cuts.append(shell_keepout())
    feat("shell-keepout")
    cuts.append(flight_keepout())
    feat("flight-keepout")
    frame = frame - U(cuts)

    cap = (outer ^ box((UP[0][0] - 1, -40, -60), (SPLIT_X, 40, 60)))
    feat("F11-cap-plate")
    ribs = []
    for y0, y1 in ((-19.0, -17.0), (6.0, 8.0)):
        ribs.append(box((SPLIT_X - 0.01, y0, -34.0), (FOAM[0][0], y1, BAT[1][2] + PLAY + 3.0)))    # rear stop through the foam
        ribs.append(box((SPLIT_X - 0.01, y0, BAT[1][2] + PLAY), (-66.0, y1, BAT[1][2] + PLAY + 3.0)))  # rear top stop over the pack
    feat("F2-cap-ribs"); feat("F2-cap-top-tabs")
    for y in PADS_Y:   # pad pins, 0.4 tip chamfer
        z = LOW[0][2] + PAD_HOLE_Z
        ribs.append(cyl_x((y, z), PIN_D / 2, SPLIT_X - 0.01, SPLIT_X + PIN_L - 0.4))
        ribs.append(cyl_x((y, z), PIN_D / 2, SPLIT_X + PIN_L - 0.4, SPLIT_X + PIN_L, r1=PIN_D / 2 - 0.4))
    feat("F8-cap-pad-pins")
    cap = cap + U(ribs)
    ccuts = [hole_x(s["yz"], CLEAR_D, UP[0][0], SPLIT_X) for s in CAP_SCREWS]
    feat("F11-cap-holes")
    ccuts.append(hole_x(BTN_C, BTN_HOLE_D, UP[0][0], SPLIT_X))
    feat("F7-button-hole")
    ccuts.append(box((UP[0][0] - 1, -30.5, 26.25 - 6.5), (SPLIT_X + 0.01, -23.0, 26.25 + 6.5)))
    feat("F6-usb-window")
    cap = cap - U(ccuts)
    return keep_main(frame), keep_main(cap)


def keep_main(M):
    """Drop zero-volume slivers left by coincident faces (a real second body fails the solids check in checks.py)."""
    bodies = [b for b in M.decompose() if b.volume() > 1.0]
    return U(bodies)


FRONT_DOWN = np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]], float)   # front face (x -45) on the bed
BACK_DOWN = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)     # back (min x) on the bed
POSES = {   # print rotation (part frame -> print frame)
    # frame: front face down. The open back is up, so the box has no ceiling; rim-down (V1.40 frame pose) makes the front
    # wall a 60 mm ceiling (2026-11-20 build: overhang 4175 mm2 rim-down against 275 front-down, bed contact 509 vs 4360)
    "battery_v2_frame": FRONT_DOWN,
    "battery_v2_cap": BACK_DOWN,                                     # back face down, ribs up
}
def print_rot(R):
    """POSES matrix as one print_fit rotation [[axis, deg]] (the fit_check pose format), checked on the three axes."""
    w, v = np.linalg.eig(R); axis = np.real(v[:, np.argmin(np.abs(w - 1))]); axis /= np.linalg.norm(axis)
    ang = np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))
    for sgn in (1, -1):
        rot = [[axis.round(6).tolist(), round(float(sgn * ang), 6)]]
        if all(np.allclose(F.to_print(e, rot), R @ e, atol=1e-6) for e in np.eye(3)): return rot
    raise ValueError("pose matrix is not a proper rotation")


def to_print(M, R):
    m = to_tm(M); T = np.eye(4); T[:3, :3] = R; m.apply_transform(T); off = -m.bounds[0]; m.apply_translation(off)
    T2 = np.eye(4); T2[:3, 3] = off
    return m, (T2 @ T)


def overhang_mm2(pm, deg=45):
    n = pm.face_normals; zmin = pm.triangles[:, :, 2].min(axis=1)
    bad = (n[:, 2] < -np.cos(np.radians(deg))) & (zmin > 0.2)
    return round(float(pm.area_faces[bad].sum()), 1)


def bed_mm2(pm): return round(float(pm.area_faces[np.max(np.abs(pm.triangles[:, :, 2]), axis=1) <= .01].sum()), 1)


def main():
    frame, cap = build()
    info = dict(frame="guide/trunk frame, mm", printer_fits=PRINTER, features_built=FEATURES,
                params=dict(BTN_PART='E-Switch PV6F240SS-331', BTN_THREAD_D=BTN_THREAD_D, BTN_HOLE_D=BTN_HOLE_D, BTN_DEPTH=BTN_DEPTH, BTN_BODY_L=BTN_BODY_L,BTN_NUT_CLEAR_D=BTN_NUT_CLEAR_D, BTN_NUT_T=BTN_NUT_T, BTN_C=BTN_C,
                            PAD_W=PAD_W, PAD_FACE_L=PAD_FACE_L, PAD_T=PAD_T, PAD_TAB_H=PAD_TAB_H, PAD_HOLE_D=PAD_HOLE_D, PAD_HOLE_Z=PAD_HOLE_Z,
                            PADS_Y=PADS_Y, PIN_D=PIN_D, PIN_L=PIN_L, COL_PILOT=COL_PILOT, LOW_Y_LEFT=LOW_Y_LEFT, CLEAR_D=CLEAR_D, PILOT_D=PILOT_D, LOOSE=LOOSE),
                outline=dict(UP=UP, LOW=LOW, SPLIT_X=SPLIT_X, X_IN=X_IN), battery=BAT, screws=SCREWS, cap_screws=CAP_SCREWS)
    solids = {}
    for name, M in (("battery_v2_frame", frame), ("battery_v2_cap", cap)):
        tm = to_tm(M); tm.export(OUT / f"{name}-world.stl")
        pm, T = to_print(M, POSES[name]); pm.export(OUT / f"{name}-print.stl")
        solids[name] = dict(bodies=len(M.decompose()), status=str(M.status()), volume_cm3=round(M.volume() / 1000, 2),
                            mass_g_solid=round(M.volume() / 1000 * 1.24, 1), bounds=tm.bounds.round(3).tolist(),
                            watertight=bool(tm.is_watertight), source_to_print=T.round(6).tolist(),
                            print_height_mm=round(float(pm.bounds[1, 2]), 2), bed_contact_mm2=bed_mm2(pm),
                            overhang_over_45deg_mm2=overhang_mm2(pm))
    pf, _ = to_print(frame, BACK_DOWN)
    solids["battery_v2_frame"]["alternative_back_down"] = dict(bed_contact_mm2=bed_mm2(pf), overhang_over_45deg_mm2=overhang_mm2(pf),
                                                                print_height_mm=round(float(pf.bounds[1, 2]), 2))
    info["parts"] = solids
    pdir = OUT / "parts"; pdir.mkdir(exist_ok=True)
    for n, M in bought_parts().items():
        to_tm(M).export(pdir / (slug(n) + "-world.stl"))
    info["bought_parts"] = sorted(p.name for p in pdir.glob("*-world.stl"))
    (OUT / "build.json").write_text(json.dumps(info, indent=1, default=float))
    print(json.dumps(solids, indent=1, default=float))


if __name__ == "__main__":
    main()
