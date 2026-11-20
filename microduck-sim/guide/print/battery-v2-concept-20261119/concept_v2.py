"""Battery backpack V2 concept (power system V2, 2026-11-19, rev B "sits down"): envelopes, checks and the concept sheet.

    Mac mini:  cd ~/code/robotics/microduck-sim/guide/print/battery-v2-concept-20261119
               ~/.venvs/flight-cad/bin/python concept_v2.py          (calls leg_check.py with ~/.venvs/microduck-dyn)
               ~/.venvs/microduck-dyn/bin/python sit_clearance.py    (real Brain sit; writes sit_clearance.json)
               ~/.venvs/flight-cad/bin/python concept_v2.py          (again, to fold the seated numbers in)

Concept stage only: rectangular envelopes of the printed parts and listing-size dummies of the bought parts, enough to
judge layout, size, mass, balance, leg clearance, seated clearance and the flight-pack conflict. Rounded edges, holders
and pilots come in the CAD stage, after Shawn's nod, from the published part sizes (largest value where sources differ). Frame: backpack local =
guide frame = sim trunk frame, mm, x forward, y left, z up; stand-world z = guide z + 120.
Writes concept.json and concept-sheet.png next to this file; reads sit_clearance.json when present.
"""
import base64, json, subprocess, sys, textwrap
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = Path(__file__).resolve().parent
MD = HERE.parents[2]                                           # microduck-sim
BP = MD / "microduck_rl/cmu/hardware/battery-backpack"
FLIGHT = MD / "extensions/flight-20261110"
sys.path.insert(0, str(MD.parent / "cad-practice")); import print_fit as F  # noqa: E402

# ------------------------------------------------------------------ hard limits
SEAT_MIN_MM = 10.0            # seated clearance of the lowest backpack point (Shawn's sit-down constraint)
BOTTOM_MIN_Z = -46.0          # trunk-frame z that gives SEAT_MIN_MM in the 2026-11-19 sit run (clearance ~1:1 with z)
LEG_MIN_MM = 6.0

# ------------------------------------------------------------------ envelopes (lo, hi), mm
WALL, FLOOR, ROOF, BACK, PLATE = 1.7, 2.0, 1.7, 1.7, 2.0
UP = ((-75.55, -32.05, -15.2), (-45.0, 32.05, 43.0))           # upper tier: today's outline, unchanged
SHIFT_Y = -6.3                                                 # battery moved 6.3 mm to the robot's right
LOW = ((-75.55, -25.3, -46.0), (-45.0, 20.0, -15.2))           # lower tier: today x -75.55, |y| 18.6, z -34 (plate -44)
CHAMFER = 3.8                                                  # 45 deg on the lower tier's front-right vertical edge (right shin)
CHAMFER_IN = 2.5                                               # matching inner chamfer: wall stays 1.7 normal to the cut
# leg-check stand-in for the chamfered lower tier: the rear box plus a 4-step staircase outside the chamfer line
LOW_LEG = [[[-75.55, -25.3, -46.0], [-49.0, 20.0, -15.2]], [[-49.0, -24.5, -46.0], [-48.0, 20.0, -15.2]],
           [[-48.0, -23.5, -46.0], [-47.0, 20.0, -15.2]], [[-47.0, -22.5, -46.0], [-46.0, 20.0, -15.2]],
           [[-46.0, -21.5, -46.0], [-45.0, 20.0, -15.2]]]
TODAY_LOW = ((-75.55, -18.6, -34.0), (-45.0, 18.6, -15.2))
TODAY_PLATE = ((-47.0, -18.6, -44.0), (-45.0, 18.6, -34.0))    # today's front plate reaches z -44 (frame STL)
CAP_SPLIT_X = -73.85                                           # frame open to the back over the full height; cap = back plate
BAT = ((-69.3, -17.0 + SHIFT_Y, -44.0), (-49.3, 17.0 + SHIFT_Y, 30.0))   # 20 x 34 x 74: largest published size (listing text 72 x 34 x 20, listing drawing 74 x 34 x 19), leads end UP, on the floor
BAT_FOAM = ((-70.3, BAT[0][1], -38.0), (-69.3, BAT[1][1], 28.0))          # 1 mm foam behind, notched below z -38 (cap bosses)
PLAY = 0.3
RIB_TOP_Z = BAT[1][2] + PLAY                                   # top ribs 0.3 over the pack: it slides in under them
BTN_C = (19.3, 30.2)                                          # button centre (y, z) on the cap, beside the battery
PADS_Y = (9.0, -9.0)
PAD_W, PAD_T, PAD_FACE_X = 6.0, 0.5, (-73.85, -65.85)          # L pad: face under the floor, tab up the frame's back face
PAD_TAB_TOP = -35.0
PARTS = {   # bought parts (listing sizes), positions chosen here
    "battery 2S 3000 (B08LZ8L4YD)": dict(box=BAT, g=110.0, src="listing text 72 x 34 x 20, drawing 74 x 34 x 19; envelope 74 x 34 x 20; scale photo 107.5 g"),
    "Pololu 2813": dict(box=((-68.0, 26.15, -12.0), (-47.7, 30.35, 13.4)), g=2.7, src="pololu.com 0.8 x 1.0 x 0.16 in, 2.7 g"),
    "DFR1202": dict(box=((-73.6, 14.2, -13.5), (-47.6, 22.2, 16.5)), g=6.0, src="30 x 26 x 8 mm (team README), 6 g manifest"),
    "XIAO SAMD21": dict(box=((-73.3, -30.35, 17.5), (-52.3, -25.85, 35.0)), g=3.0, src="21 x 17.5 mm board, 4.5 mm with USB-C; 3 g estimate"),
    "16 mm LED button (Adafruit 560)": dict(button=dict(c=BTN_C), g=10.0,
                                            src="PM161F family drawing: bezel 18.5, nut 19 AF / 21.8 corners, 20 behind panel; 10 g estimate"),
    "Schottky 1N5822 (DO-201AD)": dict(box=((-66.0, -14.0, 31.0), (-56.5, -8.7, 36.3)), g=1.1, src="DO-201AD body 9.5 x 5.3, in the top bay on the charge lead"),
    "contact pad +": dict(pad=PADS_Y[0], g=0.5, src="L contact 6 x 0.5 mm, brass or nickel-plated steel; part not yet chosen"),
    "contact pad -": dict(pad=PADS_Y[1], g=0.5, src="same"),
}
# fixing screws (unchanged): M2 x 6 forward into the rear-pack posts; heads on the plate's inner face
SCREWS = [(16.1, 26.0), (-16.1, 26.0), (16.1, -36.5), (-16.1, -36.5)]
HEAD = dict(d=3.8, h=1.6)
DRIVER_R = 1.5                                                 # PH0 / 1.5 mm hex shaft radius
# cap screws from behind into frame bosses (dia 5): two M2 x 8 high, two M2 x 6 low that also clamp the pad tabs
CAP_SCREWS = [dict(yz=(29.0, 17.0), screw="M2 x 8", boss_l=6.0, clamped=BACK),
              dict(yz=(-29.0, 39.0), screw="M2 x 8", boss_l=6.0, clamped=BACK),
              dict(yz=(PADS_Y[0], -41.5), screw="M2 x 6", boss_l=3.8, clamped=BACK + PAD_T, tab=True),
              dict(yz=(PADS_Y[1], -41.5), screw="M2 x 6", boss_l=3.8, clamped=BACK + PAD_T, tab=True)]
BOSS_D = 5.0
# cap stop ribs: the battery's rear stop (through its foam), with the wire channel left open between them
CAP_RIBS = [((-73.85, -19.0, -34.0), (-70.3, -17.0, 26.0)), ((-73.85, 6.0, -34.0), (-70.3, 8.0, 26.0))]
FRONT_STOP = ((-49.3, -12.0, -44.0), (-47.0, 8.0, -41.0))      # floor strip: the battery's front stop under the screw heads
BTN_BACK = -75.55                                              # outer face of the cap back wall (panel 1.7 mm)
BTN_BODY = 20.0 + 3.0                                          # body + terminals behind the outer face, + 3 mm solder joints
NUT_R = 10.9                                                   # 21.8 across corners; the nut turns when tightened

def box(lo, hi): lo, hi = np.array(lo, float), np.array(hi, float); return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
def to_tm(M): g = M.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=True)
def load_mf(p):
    m = trimesh.load(p, force="mesh", process=True); m.merge_vertices()
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def cyl_x(c_yz, r, x0, x1): return mf.Manifold.cylinder(x1 - x0, r, r, 64).rotate((0, 90, 0)).translate((x0, c_yz[0], c_yz[1]))
def cyl_z(c_xy, r, z0, z1): return mf.Manifold.cylinder(z1 - z0, r, r, 48).translate((c_xy[0], c_xy[1], z0))
def button_solid(c):
    """PM161F-family envelope: bezel 18.5 x 1.5 outside, M16 body behind the panel face (terminals included) + solder
    joints, hex nut 19 AF / 21.8 corners x 3 behind the panel, drawn as its 21.8 circle (any angle after tightening)."""
    y, z = c
    bezel = cyl_x((y, z), 9.25, BTN_BACK - 1.5, BTN_BACK)
    body = cyl_x((y, z), 8.0, BTN_BACK, BTN_BACK + BTN_BODY)
    nut = cyl_x((y, z), NUT_R, BTN_BACK + BACK, BTN_BACK + BACK + 3.0)
    return bezel + body + nut
PANEL_HOLE = lambda c: cyl_x(c, 8.05, BTN_BACK - 1, BTN_BACK + BACK + 0.01)
def pad_solid(y):
    face = box((PAD_FACE_X[0], y - PAD_W / 2, LOW[0][2]), (PAD_FACE_X[1], y + PAD_W / 2, LOW[0][2] + PAD_T))
    tab = box((PAD_FACE_X[0], y - PAD_W / 2, LOW[0][2]), (PAD_FACE_X[0] + PAD_T, y + PAD_W / 2, PAD_TAB_TOP))
    return face + tab
def pad_seat(y):   # floor pocket for the face + frame-face recess for the tab (both 0.5 deep, loose fit added in CAD)
    face = box((PAD_FACE_X[0] - 0.01, y - PAD_W / 2 - 0.15, LOW[0][2] - 0.01), (PAD_FACE_X[1] + 0.15, y + PAD_W / 2 + 0.15, LOW[0][2] + PAD_T))
    tab = box((PAD_FACE_X[0] - 0.01, y - PAD_W / 2 - 0.15, LOW[0][2] - 0.01), (PAD_FACE_X[0] + PAD_T, y + PAD_W / 2 + 0.15, PAD_TAB_TOP + 0.5))
    return face + tab
def part_solid(p):
    if "button" in p: return button_solid(p["button"]["c"])
    if "pad" in p: return pad_solid(p["pad"])
    return box(*p["box"])
r3 = lambda v: round(float(v), 2)

def corner_prism(x, y, c, z0, z1):
    """Removes the 45 deg corner triangle (legs c) at vertical edge (x, y) of a box lying at x' <= x, y' >= y."""
    a = c * np.sqrt(2.0)
    return mf.Manifold.cube((a, a, z1 - z0), True).rotate((0, 0, 45)).translate((x, y, (z0 + z1) / 2))

def build():
    outer = box(*UP) + (box(*LOW) - corner_prism(LOW[1][0], LOW[0][1], CHAMFER, LOW[0][2] - 1, LOW[1][2]))
    # interior: upper tier and lower tier hollow, open where they meet; front plate 2.0, walls 1.7, floor 2.0; back open
    up_in = box((UP[0][0] + BACK, UP[0][1] + WALL, UP[0][2] + WALL), (UP[1][0] - PLATE, UP[1][1] - WALL, UP[1][2] - ROOF))
    low_in = box((LOW[0][0] + BACK, LOW[0][1] + WALL, LOW[0][2] + FLOOR), (LOW[1][0] - PLATE, LOW[1][1] - WALL, LOW[1][2] + WALL + 1))
    low_in = low_in - corner_prism(LOW[1][0] - PLATE, LOW[0][1] + WALL, CHAMFER_IN, LOW[0][2], LOW[1][2] + WALL + 2)
    shell = outer - up_in - low_in
    by0, by1 = BAT[0][1] - PLAY, BAT[1][1] + PLAY
    # battery column: right wall in the upper tier continues the lower-tier right wall; a 1.5 mm left rib from the floor
    # to z 20 (it stops under the button body); front stop strip on the floor; top ribs front and back over the pack
    col = (box((-70.3, LOW[0][1], -15.3), (-47.0, by0, BAT[1][2])) + box((-70.3, by1, LOW[0][2] + 1), (-49.3, by1 + 1.5, 20.0))
           + box(*FRONT_STOP)
           + box((-52.3, by0, RIB_TOP_Z), (-49.3, by1, RIB_TOP_Z + 3)) + box((-70.3, by0, RIB_TOP_Z), (-67.3, by1, RIB_TOP_Z + 3)))
    bosses = [cyl_x(s["yz"], BOSS_D / 2, CAP_SPLIT_X, CAP_SPLIT_X + s["boss_l"] + (PAD_T if s.get("tab") else 0)) for s in CAP_SCREWS]
    body = shell + col + mf.Manifold.batch_boolean(bosses, mf.OpType.Add)
    body = body - PANEL_HOLE(BTN_C)
    body = body - box((CAP_SPLIT_X - 2, -28.1 - 6.5, 26.25 - 3.75), (CAP_SPLIT_X + 0.01, -28.1 + 6.5, 26.25 + 3.75))   # USB-C window
    for y in PADS_Y: body = body - pad_seat(y)
    body = body - box((CAP_SPLIT_X - 0.01, 22.6, UP[0][2] - 0.01), (-60.0, 26.1, UP[0][2] + WALL + 0.01))           # F10 lead slot
    keep_frame = box((CAP_SPLIT_X, -40, -60), (0, 40, 50))
    frame, cap = body ^ keep_frame, body - keep_frame
    cap = cap + mf.Manifold.batch_boolean([box(*r) for r in CAP_RIBS], mf.OpType.Add)
    return outer, frame, cap

def mass_props(M, dens=1.24 * 0.851):
    t = to_tm(M); return t.volume / 1000 * dens, np.array(t.center_mass)

# ------------------------------------------------------------------ layouts explored (envelopes only; all bottoms >= -46 except where noted)
def lowbox(x0, y0, y1, z0=-46.0): return ((x0, y0, z0), (-45.0, y1, -15.2))
OPTIONS = {
    "A": dict(name="Pack upright, centred, shorter lead bay (bottom z -46), button over the pack",
              boxes=[UP, lowbox(-75.55, -20.0, 20.0)], pack=((-69.3, -17.0, -44.0), (-49.3, 17.0, 28.0))),
    "B": dict(name="Pack upright, 6.3 mm to the right; button beside it on the upper left; DFR1202 moved to the left wing; "
                   "3.8 mm chamfer on the lower tier's front-right edge",
              boxes=[UP, LOW], pack=BAT, leg_lower=LOW_LEG),
    "C": dict(name="Pack upright, centred; button in the lower-tier back, the lower tier grows back past the button body",
              boxes=[UP, lowbox(-97.25, -20.0, 20.0)], pack=((-69.3, -17.0, -44.0), (-49.3, 17.0, 28.0))),
    "D": dict(name="Pack lying lengthwise (72 along x) in the lower tier, growing backward",
              boxes=[UP, lowbox(-124.0, -19.0, 19.0)], pack=((-121.3, -17.0, -44.0), (-49.3, 17.0, -24.0))),
    "E": dict(name="Pack lying flat across the back (72 along y)",
              boxes=[((-75.55, -38.0, -15.2), (-45.0, 38.0, 43.0)), lowbox(-75.55, -38.0, 38.0)],
              pack=((-69.3, -36.0, -44.0), (-49.3, 36.0, -10.0))),
    "F": dict(name="Pack upright, turned 90 degrees (34 deep along x, 20 wide)",
              boxes=[((-86.0, -32.05, -15.2), (-45.0, 32.05, 43.0)), lowbox(-86.0, -12.0, 12.0)],
              pack=((-83.3, -10.0, -44.0), (-49.3, 10.0, 28.0))),
}
VERDICT = {
    "A": "rejected: the 16 mm button needs its body (16 mm) and nut corners (21.8 mm) above the pack top at z 28, but the "
         "bay is 13.3 mm; the nut would reach z 46.9 against a roof at 43, and the wings (11.4 mm inside) cannot take a 16 mm body",
    "B": "chosen: meets every constraint with no added depth (lower tier back stays at today's x -75.55)",
    "C": "rejected: works (seated 10.2 mm), but adds 21.7 mm of depth behind today's lower tier, for no gain over B",
    "D": "rejected: adds 48.5 mm of depth, its long tail sits 9.4 mm off the floor seated (under the 10 mm rule), and the "
         "battery centre moves 26 mm further back than in B",
    "E": "rejected: needs |y| 38 for a 72 mm pack; the width limit is |y| 32.05 and the legs pass at |y| about 33",
    "F": "rejected: 34 mm along x does not fit the unchanged upper tier (26.9 mm inside); its back would reach x -86, through "
         "the flight harness crossing at x -77.1 (z 4 to 16)",
}
FIXED_PARTS_G = 12.0 + 1.0 + 1.0     # leads/pigtails/connectors, foam, cap screws

def option_estimate(o, M0, C0, rem):
    """Shell (outer minus 1.7 mm inset) x density + the bought parts; pack at the option's position, the rest as in B."""
    outer = mf.Manifold.batch_boolean([box(*b) for b in o["boxes"]], mf.OpType.Add)
    ins = []
    for i, b in enumerate(o["boxes"]):
        lo, hi = np.array(b[0]) + WALL, np.array(b[1]) - WALL
        if i == 1: hi[2] += 2 * WALL
        ins.append(box(lo, hi))
    shell = outer - mf.Manifold.batch_boolean(ins, mf.OpType.Add)
    ms, cs = mass_props(shell)
    add = [(ms, cs), (110.0, (np.array(o["pack"][0]) + np.array(o["pack"][1])) / 2)]
    for n, p in PARTS.items():
        if "battery" in n: continue
        add.append((p["g"], np.array(to_tm(part_solid(p)).center_mass)))
    add.append((FIXED_PARTS_G, np.array([-62.0, 0.0, 15.0])))
    ma, mr = sum(m for m, _ in add), sum(m for _, m, _ in rem)
    M1 = M0 + ma - mr
    C1 = (M0 * C0 + sum(m * c for m, c in add) - sum(m * c for _, m, c in rem)) / M1
    t = to_tm(outer)
    return dict(bbox=[t.bounds[0].round(2).tolist(), t.bounds[1].round(2).tolist()],
                depth_added_mm=r3(-75.55 - t.bounds[0][0]), backpack_g_est=r3(ma), robot_g_est=r3(M1),
                com_shift_mm_est=(C1 - C0).round(2).tolist())

def main():
    outer, frame, cap = build()
    out = {"frame": "guide/trunk frame, mm", "status": "concept rev B (sits down), not approved, not a print release"}
    tm_outer = to_tm(outer)
    out["outline"] = dict(upper_tier=UP, lower_tier=LOW, today_lower_tier=TODAY_LOW, today_front_plate=TODAY_PLATE,
                          bbox=[tm_outer.bounds[0].round(2).tolist(), tm_outer.bounds[1].round(2).tolist()],
                          today_bbox=[[-75.55, -32.05, -44.0], [-45.0, 32.05, 43.0]],
                          depth_behind_plate_upper=r3(UP[1][0] - UP[0][0]), depth_lower=r3(LOW[1][0] - LOW[0][0]),
                          depth_added_mm=r3(-75.55 - LOW[0][0]), height=r3(UP[1][2] - LOW[0][2]), today_height=77.0,
                          note="today's box ends at z -34, its front plate at z -44 (frame STL); this box ends at z -46")
    out["volume_outer_cm3"] = dict(new=r3(tm_outer.volume / 1000),
                                   today=r3((to_tm(box(*UP) + box(*TODAY_LOW))).volume / 1000))
    solids = {n: part_solid(p) for n, p in PARTS.items()}
    printed = frame + cap
    out["overlap_mm3"] = {n: r3((s ^ printed).volume()) for n, s in solids.items()}
    names = list(solids)
    out["part_part_overlap_mm3"] = {f"{a} | {b}": r3((solids[a] ^ solids[b]).volume())
                                    for i, a in enumerate(names) for b in names[i + 1:] if (solids[a] ^ solids[b]).volume() > 0.01}
    bat = solids["battery 2S 3000 (B08LZ8L4YD)"]
    btn = solids["16 mm LED button (Adafruit 560)"]
    out["gaps_mm"] = dict(button_body_to_battery_y=r3((BTN_C[0] - 8.0) - BAT[1][1]),
                          button_nut_to_wing_wall_y=r3((UP[1][1] - WALL) - (BTN_C[0] + NUT_R)),
                          button_nut_to_roof_z=r3((UP[1][2] - ROOF) - (BTN_C[1] + NUT_R)),
                          lower_bosses_to_battery_x=r3(BAT[0][0] - (CAP_SPLIT_X + 3.8 + PAD_T)),
                          lead_bay_over_battery_z=r3((UP[1][2] - ROOF) - BAT[1][2]))
    # screw heads and driver lanes (driver from the open back along +x to the head; frame on its own, before the battery)
    lanes = {}
    for y, z in SCREWS:
        head = cyl_x((y, z), HEAD["d"] / 2, -47.0 - HEAD["h"], -47.0)
        lane = cyl_x((y, z), DRIVER_R, -90.0, -47.0 - HEAD["h"])
        side = (LOW[1][1] - WALL) - (y + DRIVER_R) if y > 0 else (y - DRIVER_R) - (LOW[0][1] + WALL)
        lanes[f"y{y:+.1f} z{z:+.1f}"] = dict(head_vs_battery=r3((head ^ bat).volume()), head_vs_button=r3((head ^ btn).volume()),
                                            lane_vs_frame=r3((lane ^ frame).volume()),
                                            wall_gap_mm=r3(side) if z < -15.2 else None)
    out["fixing_screws_M2x6"] = lanes
    out["cap_screws"] = [dict(yz=s["yz"], screw=s["screw"], boss_len=s["boss_l"], clamped=r3(s["clamped"]),
                              engaged=r3(float(s["screw"].split("x")[1]) - s["clamped"]), clamps_pad_tab=bool(s.get("tab")))
                         for s in CAP_SCREWS]
    # masses and centre of mass against today's backpack (manifest battery-20261104)
    mfr, cfr = mass_props(frame); mcp, ccp = mass_props(cap)
    add = [("frame (print)", mfr, cfr), ("cap (print)", mcp, ccp)]
    for n, p in PARTS.items():
        s = to_tm(solids[n]); add.append((n, p["g"], np.array(s.center_mass)))
    add += [("leads, pigtails, connectors", 12.0, np.array([-60.0, -5.0, 25.0])), ("foam tape", 1.0, np.array([-65.0, 0.0, -5.0])),
            ("cap screws 2 x M2 x 8 + 2 x M2 x 6", 1.0, np.array([-74.0, 0.0, -7.0]))]
    man = json.load(open(MD / "microduck_rl/cmu/model/manifests/battery-20261104.json"))
    gone_ids = ("add-bp-switch", "add-bp-dfr1202", "add-bp-frame-v140", "add-bp-cap-v141", "add-bp-hatch-v141", "add-bp-bars-d037",
                "add-bp-battery-tattu-2s-650-d037", "add-bp-plug1-top-d037", "add-bp-balance-top-d037", "add-bp-wires-d037",
                "add-bp-hatch-tape", "add-bp-bar-screw", "add-bp-cap-screw")
    rem = [(p["id"], p["mass_kg"] * 1000, np.array(p["position_m"]) * 1000) for p in man["parts"]
           if p["id"].startswith(gone_ids) and p.get("body") == "trunk_base"]
    poses = json.load(open(FLIGHT / "duck_poses.json"))
    M0 = poses["mass_g"]; C0 = np.array(poses["com_mm"]) - [0, 0, 120]
    ma, mr = sum(m for _, m, _ in add), sum(m for _, m, _ in rem)
    M1 = M0 + ma - mr
    C1 = (M0 * C0 + sum(m * c for _, m, c in add) - sum(m * c for _, m, c in rem)) / M1
    out["mass"] = dict(robot_today_g=r3(M0), backpack_today_g=r3(mr), backpack_new_g=r3(ma), delta_g=r3(ma - mr), robot_new_g=r3(M1),
                       com_today_mm=C0.round(2).tolist(), com_new_mm=C1.round(2).tolist(), com_shift_mm=(C1 - C0).round(2).tolist(),
                       new_items={n: [r3(m), c.round(1).tolist()] for n, m, c in add},
                       removed_items={n: [r3(m), c.round(1).tolist()] for n, m, c in rem},
                       basis="prints: envelope volume x 1.24 g/cm3 x 0.851 (repo method); listing masses where given; estimates marked in PARTS")
    # robot trunk (without today's orange backpack and saddle) against the new envelope
    rp = robot_points(poses)
    # (today's backpack contents, which this backpack replaces, are excluded: everything inside today's outline)
    trunk = np.vstack([v for b, v, f, c in rp if b == "trunk_base" and not (c[0] > 0.7 and c[1] < 0.7)])
    def inside(P, b, m=0.0): return np.all((P >= np.array(b[0]) - m) & (P <= np.array(b[1]) + m), axis=1)
    trunk = trunk[~(inside(trunk, UP) | inside(trunk, TODAY_LOW) | inside(trunk, TODAY_PLATE))]
    out["trunk_points_inside_new_lower_tier"] = int(inside(trunk, LOW).sum())
    out["trunk_points_within_2mm_of_new_lower_tier"] = int(inside(trunk, LOW, 2.0).sum())
    out["trunk_check_basis"] = "duck_poses.json trunk meshes without today's backpack (orange) and without anything inside today's outline"
    # flight pack: the backpack sits 6.9 mm further back on the wing-plate centre (flight_params WING x_centre_back)
    shift = (-6.9, 0, 0)
    today = load_mf(BP / "stl/battery_backpack_frame-world.stl") + load_mf(BP / "stl/battery_backpack_cap-world.stl")
    flight_meshes = [(f.stem, load_mf(f)) for f in sorted((FLIGHT / "cad/build").glob("*-world.stl"))
                     if not ("wing_plate" in f.name and f.name != "wing_plate-world.stl")]
    def flight_overlap(Mb):
        res = {}
        for stem, M in flight_meshes:
            a = (Mb ^ M).volume()
            if a > 0.01: res[stem] = r3(a)
        return res
    out["flight_overlap_mm3 (backpack shifted -6.9 x)"] = flight_overlap((today + box(*LOW)).translate(shift))
    out["flight_harness_rear_gap_mm"] = dict(upper_tier_back_flying=r3(UP[0][0] - 6.9), harness_rear_x_max=-84.0,
                                             lower_tier_top_z=LOW[1][2], harness_rear_z_min=4.0)
    # legs: hip pitch +-30, roll +-10 about the stand keyframe, both legs
    env = {"upper tier": [list(UP[0]), list(UP[1])], "lower tier (new)": LOW_LEG,
           "lower tier (new) without the chamfer": [list(LOW[0]), list(LOW[1])],
           "contact pads": [[PAD_FACE_X[0], -12.0, LOW[0][2]], [PAD_FACE_X[1], 12.0, PAD_TAB_TOP]],
           "lower tier (today)": [list(TODAY_LOW[0]), list(TODAY_LOW[1])], "front plate (today)": [list(TODAY_PLATE[0]), list(TODAY_PLATE[1])]}
    for k, o in OPTIONS.items():
        for i, b in enumerate(o["boxes"]): env[f"opt {k} {i}"] = [list(b[0]), list(b[1])]
        if "leg_lower" in o: env[f"opt {k} 1"] = o["leg_lower"]
    leg = subprocess.run([str(Path.home() / ".venvs/microduck-dyn/bin/python"), str(HERE / "leg_check.py"), json.dumps(env)],
                         capture_output=True, text=True, check=True)
    legs = json.loads(leg.stdout)
    out["leg_clearance_mm (hip pitch +-30, roll +-10)"] = {k: v for k, v in legs.items() if not k.startswith("opt ")}
    # seated clearance from sit_clearance.py (real Brain sit, current as-built model), when it has been run on this outline
    sitf = HERE / "sit_clearance.json"
    sit = json.load(open(sitf)) if sitf.exists() else None
    if sit and sit.get("boxes", {}).get("new_lower") != [list(LOW[0]), list(LOW[1])]:
        sit = dict(stale=True, note="sit_clearance.json was run on another outline; rerun sit_clearance.py")
    out["seated_clearance_mm"] = sit
    # options table
    opts = {}
    for k, o in OPTIONS.items():
        est = option_estimate(o, M0, C0, rem)
        lg = min(legs[f"opt {k} {i}"]["min_mm"] for i in range(len(o["boxes"])))
        seat = None
        if sit and not sit.get("stale"):
            vals = [sit["seated"].get(f"opt_{k}_{i}") for i in range(len(o["boxes"]))]
            seat = min(v for v in vals if v is not None) if any(v is not None for v in vals) else None
        fl = flight_overlap((today + box(*o["boxes"][1])).translate(shift) if o["boxes"][0] == UP else
                            mf.Manifold.batch_boolean([box(*b) for b in o["boxes"]], mf.OpType.Add).translate(shift))
        opts[k] = dict(name=o["name"], boxes=o["boxes"], pack=o["pack"], **est, leg_clearance_mm=r3(lg), seated_clearance_mm=seat,
                       flight_overlap_mm3=fl, verdict=VERDICT[k])
    out["options"] = opts
    out["options_basis"] = ("bbox, depth, leg and seated clearance from the envelopes; mass and balance-point shift are "
                            "estimates (shell = outer minus a 1.7 mm inset); option B's detailed numbers are under 'mass'")
    # contacts
    seat_pad = sit["seated"].get("contact_pads") if sit and not sit.get("stale") else None
    out["contacts"] = dict(kind="two fixed L pads (no moving part on the robot); springs on the dock plates",
                           pad_face_local=[[[PAD_FACE_X[0], y - PAD_W / 2, LOW[0][2]], [PAD_FACE_X[1], y + PAD_W / 2, LOW[0][2]]] for y in PADS_Y],
                           pad_box=[[PAD_FACE_X[0], -12.0, LOW[0][2]], [PAD_FACE_X[1], 12.0, LOW[0][2] + PAD_T]],
                           spacing_mm=PADS_Y[0] - PADS_Y[1], facing="down (-z), flush with the box bottom",
                           stand_height_mm=r3(120 + LOW[0][2]), seated_height_mm=seat_pad,
                           retention="face in a 0.5 mm floor pocket (takes the dock push); tab clamped between the cap and the "
                                     "frame's back face by the lower M2 x 6 cap screw")
    # fits from print_fit (declared for the CAD stage)
    out["fits_H2S"] = dict(fixing_screw="M2 x 6 into existing rear-pack pilots (unchanged), plate clearance "
                                         f"{F.clear('M2', 'vertical', printer='H2S')} (plate prints back-face down, axis vertical)",
                           cap_screw_clear=F.clear("M2", "vertical", printer="H2S"), cap_screw_pilot_in_frame_boss=F.pilot("M2", "vertical", printer="H2S"),
                           cap_screw_pilot_runs_through="bosses shorter than pilot_depth: pilot runs through (print_fit.pilot_depth rule)",
                           head_seat=F.HEAD_SEAT["M2"],
                           button_hole="16.0 +0.2/-0 (vendor panel cutout; through the cap back, vertical in print)",
                           pad_pockets=f"pad + 2 x {F.clearance('loose')} (loose) in y, 0.5 deep",
                           bought_board_pockets=f"listing size + 2 x {F.clearance('loose')} (loose), held by foam tape")
    json.dump(out, open(HERE / "concept.json", "w"), indent=1)
    sheet(out, frame, cap, solids, rp)
    print(json.dumps({k: out[k] for k in ("outline", "gaps_mm", "fixing_screws_M2x6", "leg_clearance_mm (hip pitch +-30, roll +-10)",
                                          "seated_clearance_mm", "flight_overlap_mm3 (backpack shifted -6.9 x)", "overlap_mm3",
                                          "part_part_overlap_mm3", "trunk_points_inside_new_lower_tier")}, indent=1))
    print(json.dumps({k: {kk: v[kk] for kk in ("bbox", "depth_added_mm", "backpack_g_est", "com_shift_mm_est", "leg_clearance_mm",
                                               "seated_clearance_mm", "flight_overlap_mm3")} for k, v in opts.items()}, indent=1))
    m = out["mass"]; print("mass", m["backpack_today_g"], m["backpack_new_g"], m["robot_new_g"], m["com_shift_mm"])

# ------------------------------------------------------------------ sheet
COL = {"battery": "#4c9a5b", "Pololu": "#2d6fb7", "DFR1202": "#1f3f7a", "XIAO": "#7a3fa0", "button": "#c0392b",
       "Schottky": "#555555", "contact": "#d4a017"}
def colour(n): return next((c for k, c in COL.items() if k in n), "#888")

def robot_points(poses):
    pts = []
    for p in poses["parts"]:
        v = np.frombuffer(base64.b64decode(p["pos"]), np.float32).reshape(-1, 3).astype(float)
        v[:, 2] -= 120
        pts.append((poses["bodies"][str(p["body"])], v, np.frombuffer(base64.b64decode(p["idx"]), np.uint32).reshape(-1, 3) if "idx" in p else None, p["color"]))
    return pts

def rect(ax, lo, hi, i, j, **kw):
    ax.add_patch(Rectangle((lo[i], lo[j]), hi[i] - lo[i], hi[j] - lo[j], **kw))

def sheet(out, frame, cap, solids, rp):
    fig = plt.figure(figsize=(28, 15), dpi=100)
    fig.suptitle("MicroDuck battery backpack V2 - CONCEPT rev B for approval (2026-11-19, not a print release)  |  sits down: bottom z -46, "
                 "battery 6.3 mm right, button beside it, no added depth", fontsize=14, weight="bold")
    # --- 3D view with the robot
    ax = fig.add_subplot(2, 4, 1, projection="3d")
    for b, v, f, c in rp:
        if f is None: continue
        if b == "trunk_base" and c[0] > 0.7 and c[1] < 0.7: continue          # today's orange backpack and saddle mesh
        ax.add_collection3d(Poly3DCollection(v[f[::2]], facecolor=(*c, 0.18), edgecolor="none"))
    for M, colr in ((frame, (1.0, 0.55, 0.1, 0.35)), (cap, (1.0, 0.75, 0.3, 0.35))):
        t = to_tm(M); ax.add_collection3d(Poly3DCollection(t.vertices[t.faces], facecolor=colr, edgecolor="none"))
    for n, s in solids.items():
        t = to_tm(s); ax.add_collection3d(Poly3DCollection(t.vertices[t.faces], facecolor=colour(n), edgecolor="none", alpha=0.9))
    ax.set_xlim(-140, 60); ax.set_ylim(-100, 100); ax.set_zlim(-125, 75); ax.set_box_aspect((200, 200, 200))
    ax.view_init(elev=18, azim=-140); ax.set_title("On the robot (stand pose, from behind left); grey = robot, orange = new box")
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z (guide)")

    # --- side section y = 0
    ax = fig.add_subplot(2, 4, 2)
    for b, v, f, c in rp:
        if b in ("jaw_soft",) or (b == "trunk_base" and c[0] > 0.7 and c[1] < 0.7): continue
        s = v[np.abs(v[:, 1]) < 45]; ax.plot(s[::7, 0], s[::7, 2], ",", color="#bbbbbb")
    ax.plot([-75.55, -45, -45, -47, -47, -75.55, -75.55], [43, 43, -44, -44, -34, -34, 43], "k--", lw=1.5)
    for b in (UP, LOW): rect(ax, b[0], b[1], 0, 2, fc=(1, 0.6, 0.2, 0.25), ec="#e07000", lw=2)
    ax.plot([CAP_SPLIT_X, CAP_SPLIT_X], [LOW[0][2], 43], color="#e07000", ls=":", lw=1)
    for n, p in PARTS.items():
        if "box" in p and p["box"][0][1] <= 0 <= p["box"][1][1]: rect(ax, p["box"][0], p["box"][1], 0, 2, fc=colour(n), alpha=0.85)
    rect(ax, BAT_FOAM[0], BAT_FOAM[1], 0, 2, fc="#f2e6a0")
    for x0 in (-52.3, -70.3): rect(ax, (x0, 0, RIB_TOP_Z), (x0 + 3, 0, RIB_TOP_Z + 3), 0, 2, fc="#e07000")
    rect(ax, FRONT_STOP[0], FRONT_STOP[1], 0, 2, fc="#e07000")
    for y, z in SCREWS: rect(ax, (-48.6, 0, z - 1.9), (-47.0, 0, z + 1.9), 0, 2, fc="k")
    ax.plot([PAD_FACE_X[0], PAD_FACE_X[1]], [LOW[0][2] + 0.25] * 2, color=COL["contact"], lw=4)
    ax.plot([PAD_FACE_X[0] + 0.25] * 2, [LOW[0][2], PAD_TAB_TOP], color=COL["contact"], lw=3)
    rect(ax, (CAP_SPLIT_X, 0, -44), (CAP_SPLIT_X + 4.3, 0, -39), 0, 2, fc="#b35900")
    ax.annotate("battery 74 x 34 x 20\nleads up (110 g)", (-59.3, -10), ha="center", color="w", fontsize=9, weight="bold")
    ax.annotate("lead bay 11.3 mm:\nXT30 joint, XH, diode", (-60, 33), ha="center", fontsize=8)
    ax.annotate("2 L pads flush with the bottom;\nlower cap screw clamps each tab", (-128, -60), fontsize=8, color="#8a6d00")
    ax.annotate("cap | frame", (CAP_SPLIT_X - 9, 46), fontsize=8, color="#e07000")
    ax.annotate("dashed = today (box z -34, front plate z -44)", (-128, 52), fontsize=8)
    ax.annotate("floor (stand)", (-128, -118), fontsize=8)
    ax.plot([-130, 10], [-120, -120], "k-", lw=0.5)
    ax.set_xlim(-130, 10); ax.set_ylim(-122, 60); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title("Side section y = 0 (x forward to the right), guide z"); ax.set_xlabel("x mm"); ax.set_ylabel("z mm")

    # --- back view (viewer behind the robot: robot's left on the image left)
    ax = fig.add_subplot(2, 4, 3)
    def r_back(lo, hi, **kw): ax.add_patch(Rectangle((-hi[1], lo[2]), hi[1] - lo[1], hi[2] - lo[2], **kw))
    ax.plot([-32.05, 32.05, 32.05, 18.6, 18.6, -18.6, -18.6, -32.05, -32.05], [43, 43, -15.2, -15.2, -34, -34, -15.2, -15.2, 43], "k--", lw=1.5)
    ax.plot([-18.6, 18.6], [-44, -44], "k--", lw=1)
    for b in (UP, LOW): r_back(b[0], b[1], fc=(1, 0.6, 0.2, 0.25), ec="#e07000", lw=2)
    for n, p in PARTS.items():
        if "box" in p: r_back(p["box"][0], p["box"][1], fc=colour(n), alpha=0.85)
    ax.add_patch(Circle((-BTN_C[0], BTN_C[1]), NUT_R, fc="none", ec=COL["button"], ls="--"))
    ax.add_patch(Circle((-BTN_C[0], BTN_C[1]), 9.25, fc=COL["button"], alpha=0.85)); ax.add_patch(Circle((-BTN_C[0], BTN_C[1]), 6.0, fc="#7fd27f"))
    ax.add_patch(Rectangle((28.1 - 6.5, 26.25 - 3.75), 13, 7.5, fc="w", ec="k"))
    for y in PADS_Y: ax.add_patch(Rectangle((-y - PAD_W / 2, LOW[0][2] - 1.5), PAD_W, 1.5, fc=COL["contact"]))
    for s in CAP_SCREWS: ax.add_patch(Circle((-s["yz"][0], s["yz"][1]), 1.25, fc="w", ec="k"))
    ax.annotate("LED button (push = ON)\nnut circle dashed", (-BTN_C[0], 44.5), ha="center", fontsize=8, color=COL["button"])
    ax.annotate("XIAO USB-C\nwindow", (28, 31.5), ha="center", fontsize=8)
    ax.annotate("Pololu", (-28.2, 0), ha="center", fontsize=8, rotation=90, color="w")
    ax.annotate("DFR1202", (-18.2, 0), ha="center", fontsize=8, rotation=90, color="w")
    ax.annotate("XIAO", (28, 23), ha="center", fontsize=7, color="w")
    ax.annotate("battery\n(6.3 mm right)", (-BAT[0][1] - 17, -20), ha="center", fontsize=9, color="w", weight="bold")
    ax.annotate("2 pads, 18 mm apart, flush", (0, -54), ha="center", fontsize=8, color="#8a6d00")
    ax.annotate("robot LEFT (+y)", (-34, 50), fontsize=8); ax.annotate("robot RIGHT (-y)", (12, 50), fontsize=8)
    ax.set_xlim(-45, 45); ax.set_ylim(-60, 55); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title("Back view (seen from behind), dashed = today; white = 4 cap screws")

    # --- top section at z 30 (lead bay and button)
    ax = fig.add_subplot(2, 4, 4)
    rect(ax, UP[0], UP[1], 0, 1, fc=(1, 0.6, 0.2, 0.25), ec="#e07000", lw=2)
    rect(ax, LOW[0], LOW[1], 0, 1, fill=False, ec="#e07000", ls=":", lw=1.5)
    rect(ax, BAT[0], BAT[1], 0, 1, fill=False, ec=COL["battery"], ls="--", lw=1.5)
    for n, p in PARTS.items():
        if "box" in p and p["box"][0][2] < 30 < p["box"][1][2]: rect(ax, p["box"][0], p["box"][1], 0, 1, fc=colour(n), alpha=0.85)
    rect(ax, (BTN_BACK - 1.5, BTN_C[0] - 9.25, 0), (BTN_BACK, BTN_C[0] + 9.25, 0), 0, 1, fc=COL["button"])
    rect(ax, (CAP_SPLIT_X, BTN_C[0] - 9.5, 0), (CAP_SPLIT_X + 3, BTN_C[0] + 9.5, 0), 0, 1, fc=COL["button"], alpha=0.5)
    rect(ax, (CAP_SPLIT_X + 3, BTN_C[0] - 8, 0), (BTN_BACK + BTN_BODY, BTN_C[0] + 8, 0), 0, 1, fc=COL["button"], alpha=0.3)
    rect(ax, (-64, -14, 0), (-58.8, 2, 0), 0, 1, fc="#ffd200", ec="k")
    for y, z in SCREWS[:2]: rect(ax, (-48.6, y - 1.9, 0), (-47.0, y + 1.9, 0), 0, 1, fc="k")
    ax.plot([-45.0, -45.0 - CHAMFER], [LOW[0][1] + CHAMFER, LOW[0][1]], color="#e07000", ls=":", lw=1.5)
    ax.annotate("lower-tier chamfer\n(right shin)", (-52, -38.5), fontsize=7, color="#e07000")
    ax.annotate("XT30 battery to\nPololu VIN joint", (-61, -21), ha="center", fontsize=8)
    ax.annotate("button body\nbeside the battery", (-63, 23), ha="center", fontsize=8)
    ax.annotate("dashed green = battery below", (-84, -38), fontsize=8, color=COL["battery"])
    ax.set_xlim(-85, -40); ax.set_ylim(-40, 40); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title("Top section z = 30 (lead bay); dotted = lower tier below"); ax.set_xlabel("x"); ax.set_ylabel("y")

    # --- wiring block diagram
    ax = fig.add_subplot(2, 4, 5); ax.axis("off"); ax.set_title("Wiring (one line = one wire pair)")
    txt = ("POWER (16 AWG)\n"
           "  battery XT30 -> Pololu 2813 VIN\n"
           "  Pololu VOUT -> plug 3 XT30 -> OpenRB J4\n"
           "  Pololu VOUT -> DFR1202 VIN (22 AWG)\n"
           "  DFR1202 5 V -> plug 4 MR30 pins 1-2 -> A7Z\n"
           "CHARGE (20 AWG, 2 A)\n"
           "  pad + -> 1N5822 -> Pololu VIN pad (pack node)\n"
           "  pad - -> Pololu GND pad (pack -)\n"
           "  battery DC5.5 lead unused, capped in the bay\n"
           "BUTTON (push = ON only, a knock cannot switch off)\n"
           "  NO contact: VIN -10k-> Pololu ON\n"
           "  LED ring (6 V, own resistor) <- DFR1202 5 V\n"
           "XIAO SAMD21 (5 V from DFR1202, 26 AWG)\n"
           "  A0 <- VOUT 100k/33k    A1 <- mid cell XH 100k/100k\n"
           "  A2 <- pad + 100k/33k   A3 <- ON line 100k/33k\n"
           "  D6 -1N4148-> Pololu OFF <-1N4148- A7Z GPIO\n"
           "     (A7Z GPIO on plug 4 MR30 pin 3); OFF 100k to GND\n"
           "  cut: pack < 6.3 V or a cell < 3.1 V for 3 s;\n"
           "  hold button 2 s while on = shutdown request\n"
           "BALANCE: battery XH -> XH socket on the XIAO harness;\n"
           "  unplug it for the monthly B3 balance charge")
    ax.text(0.0, 1.0, txt, family="monospace", fontsize=9, va="top")

    # --- numbers
    ax = fig.add_subplot(2, 4, 6); ax.axis("off"); ax.set_title("Numbers (concept envelopes; CAD from the published sizes)")
    m, o, g = out["mass"], out["outline"], out["gaps_mm"]
    leg = out["leg_clearance_mm (hip pitch +-30, roll +-10)"]
    fl = out["flight_overlap_mm3 (backpack shifted -6.9 x)"]
    sit = out["seated_clearance_mm"] or {}
    seated = sit.get("seated") or {}
    lines = [
        "Upper tier unchanged: x -45..-75.55, |y| 32.05, top z 43.",
        "Lower tier: x -45..-75.55 (as today), y -25.3..+20, bottom z -46,",
        "  3.8 mm chamfer front-right (today: box -34, plate -44). Depth added: 0.",
        f"Height {o['today_height']:.0f} -> {o['height']:.0f} mm; outer volume {out['volume_outer_cm3']['today']:.0f} -> {out['volume_outer_cm3']['new']:.0f} cm3.",
        f"Seated, lowest point above the floor: box {seated.get('new_lower', '?')} mm, pads {seated.get('contact_pads', '?')} mm",
        f"  (today: box {seated.get('today_lower', '?')}, front plate {seated.get('today_front_plate', '?')}; rule >= {SEAT_MIN_MM:.0f}).",
        f"Legs (hip pitch +-30, roll +-10): {leg['lower tier (new)']['min_mm']} mm min (today {leg['lower tier (today)']['min_mm']}; rule >= 6).",
        f"Backpack {m['backpack_today_g']:.0f} -> {m['backpack_new_g']:.0f} g ({m['delta_g']:+.0f} g); robot {m['robot_today_g']:.0f} -> {m['robot_new_g']:.0f} g.",
        f"Robot COM moves {-m['com_shift_mm'][0]:.1f} mm back, {-m['com_shift_mm'][2]:.1f} mm down, {-m['com_shift_mm'][1]:.1f} mm right.",
        "Flight pack (box 6.9 mm back): " + (", ".join(f"{k} {v} mm3" for k, v in fl.items()) or "no overlap"),
        f"Lead bay over the battery {g['lead_bay_over_battery_z']} mm; button body {g['button_body_to_battery_y']} mm",
        f"  beside the battery, nut {g['button_nut_to_wing_wall_y']} mm to the wing wall, {g['button_nut_to_roof_z']} to the roof.",
        "Pads: y +-9 (18 mm apart), face x -73.85..-65.85, flush at z -46,",
        f"  {120 + LOW[0][2]:.0f} mm up standing, {seated.get('contact_pads', '?')} mm seated, facing down.",
        "Screws: 4 x M2 x 6 fixing (unchanged); cap 2 x M2 x 8 + 2 x M2 x 6.",
        "Boards on 3M foam tape; battery boxed by walls, ribs and foam.",
        "No snaps, hooks or flexures; walls 1.5-1.7, floor 2.0 mm.",
    ]
    ax.text(0.0, 1.0, "\n".join(lines), fontsize=10, va="top")

    # --- options considered
    ax = fig.add_subplot(2, 4, (7, 8)); ax.axis("off"); ax.set_title("Layouts explored (seated and leg clearance from the sims; mass estimates)")
    t = []
    for k, v in out["options"].items():
        cs = v["com_shift_mm_est"]
        t.append(f"{k}  {v['name']}")
        t.append(f"   depth +{v['depth_added_mm']} mm, seated {v['seated_clearance_mm']} mm, legs {v['leg_clearance_mm']} mm, "
                 f"backpack ~{v['backpack_g_est']:.0f} g, COM {cs[0]:+.1f} x {cs[2]:+.1f} z")
        t += textwrap.wrap(v["verdict"], 118, initial_indent="   ", subsequent_indent="   ")
    ax.text(0.0, 1.0, "\n".join(t), fontsize=9.5, va="top", family="monospace")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(HERE / "concept-sheet.png"); plt.close(fig)

if __name__ == "__main__":
    main()
