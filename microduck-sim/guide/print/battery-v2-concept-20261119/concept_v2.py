"""Battery backpack V2 concept (power system V2, 2026-11-19): envelopes, checks and the concept sheet.

    ~/.venvs/microduck-cad/bin/python concept_v2.py      (calls leg_check.py with ~/.venvs/microduck-dyn)

Concept stage only: rectangular envelopes of the printed parts and listing-size dummies of the bought parts, enough to
judge layout, size, mass, balance, leg clearance and the flight-pack conflict. Rounded edges, holders and pilots come in
the CAD stage, after Shawn's nod and after the parts are in hand and measured. Frame: backpack local = guide frame = sim
trunk frame, mm, x forward, y left, z up; stand-world z = guide z + 120.
Writes concept.json and concept-sheet.png next to this file.
"""
import base64, json, subprocess, sys
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

# ------------------------------------------------------------------ envelopes (lo, hi), mm
WALL, FLOOR, ROOF, BACK, PLATE = 1.7, 2.0, 1.7, 1.7, 2.0
UP = ((-75.55, -32.05, -15.2), (-45.0, 32.05, 43.0))           # upper tier: today's outline, unchanged
LOW = ((-80.0, -20.0, -55.0), (-45.0, 20.0, -15.2))            # lower tier: today x -75.55, |y| 18.6, z -34
TODAY_LOW = ((-75.55, -18.6, -34.0), (-45.0, 18.6, -15.2))
CAP_SPLIT_X = -73.85                                           # upper tier: frame open to the back here; cap = back plate
CAP_SPLIT_X_LOW = -78.3                                        # lower tier: the heel (walls, floor, contacts) is frame
BAT = ((-69.3, -17.0, -53.0), (-49.3, 17.0, 19.0))             # 20 x 34 x 72 listing, leads end UP
BAT_FOAM = ((-70.3, -17.0, -53.0), (-69.3, 17.0, 19.0))        # 1 mm foam pad behind the battery
BAT_STOP = ((-52.3, -17.3, 19.0), (-49.3, 17.3, 22.0))         # front rib over the battery top (frame); rear rib on the cap
PARTS = {   # bought parts (listing sizes), positions chosen here
    "battery 2S 3000 (B08LZ8L4YD)": dict(box=BAT, g=110.0, src="listing 72 x 34 x 20 mm, 110 g"),
    "Pololu 2813": dict(box=((-68.0, 26.15, -12.0), (-47.7, 30.35, 13.4)), g=2.7, src="pololu.com 0.8 x 1.0 x 0.16 in, 2.7 g"),
    "DFR1202": dict(box=((-73.6, -30.35, -13.5), (-47.6, -22.35, 16.5)), g=6.0, src="30 x 26 x 8 mm (team README), 6 g manifest"),
    "XIAO SAMD21": dict(box=((-73.3, -30.35, 17.5), (-52.3, -25.85, 35.0)), g=3.0, src="21 x 17.5 mm board, 4.5 mm with USB-C; 3 g estimate"),
    "16 mm LED button (Adafruit 560)": dict(button=dict(c=(17.0, 30.5)), g=10.0,
                                            src="PM161F family drawing: bezel 18.5, nut 21.8 AF corners, 20 behind panel; 10 g estimate"),
    "Schottky 1N5822 (DO-201AD)": dict(box=((-66.0, -14.0, 22.0), (-56.5, -8.7, 27.3)), g=1.1, src="DO-201AD body 9.5 x 5.3, in the top bay on the DC5.5 pigtail"),
    "spring contact +": dict(cyl=dict(c=(9.0, None), r=2.0, z=(-56.5, -42.0), x0=-76.1), g=0.5, src="pin class: barrel <= 4 mm, travel >= 1.5"),
    "spring contact -": dict(cyl=dict(c=(-9.0, None), r=2.0, z=(-56.5, -42.0), x0=-76.1), g=0.5, src="same"),
}
# fixing screws (unchanged): M2 x 6 forward into the rear-pack posts; heads on the plate's inner face
SCREWS = [(16.1, 26.0), (-16.1, 26.0), (16.1, -36.5), (-16.1, -36.5)]
HEAD = dict(d=3.8, h=1.6)
DRIVER_R = 1.5                                                 # PH0 / 1.5 mm hex shaft radius
CAP_SCREWS = [(29.0, 39.0), (-29.0, 39.0), (15.5, -50.0), (-15.5, -50.0)]   # M2 x 8 from behind, into frame bosses (dia 5)
BOSS_D, BOSS_L = 5.0, 6.0
# the cap's lower plate carries one solid block that fills the heel behind the battery: it is the battery's rear stop
# below z -15.2 and bears on both contact flanges, so the pins cannot be pushed up into the box (no clamp screws)
CAP_BLOCK = ((-78.3, -12.5, -53.0), (-70.4, 12.5, -20.0))

def box(lo, hi): lo, hi = np.array(lo, float), np.array(hi, float); return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
def inset(b, d, open_back=False):
    lo, hi = np.array(b[0], float) + d, np.array(b[1], float) - d
    if open_back: lo[0] -= d + 1
    return lo, hi
def to_tm(M): g = M.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=True)
def load_mf(p):
    m = trimesh.load(p, force="mesh", process=True); m.merge_vertices()
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def cyl_x(c_yz, r, x0, x1): return mf.Manifold.cylinder(x1 - x0, r, r, 64).rotate((0, 90, 0)).translate((x0, c_yz[0], c_yz[1]))
def cyl_z(c_xy, r, z0, z1): return mf.Manifold.cylinder(z1 - z0, r, r, 48).translate((c_xy[0], c_xy[1], z0))
BTN_BACK = -75.55                                              # outer face of the cap back wall (panel 1.7 mm)
def button_solid(c):
    """PM161F-family envelope: bezel 18.5 x 1.5 outside, M16 body 20 behind the panel face (terminals included), hex nut
    19 AF / 21.8 corners x 3 behind the panel, flats horizontal; + 5 mm of wire bend behind the terminals."""
    y, z = c
    bezel = cyl_x((y, z), 9.25, BTN_BACK - 1.5, BTN_BACK)
    body = cyl_x((y, z), 8.0, BTN_BACK, BTN_BACK + 20.0 + 5.0)
    nut = mf.Manifold.cylinder(3.0, 10.9, 10.9, 6).rotate((0, 0, 30)).rotate((0, 90, 0)).translate((BTN_BACK + BACK, y, z))
    return bezel + body + nut
PANEL_HOLE = lambda c: cyl_x(c, 8.05, BTN_BACK - 1, BTN_BACK + BACK + 0.01)
def part_solid(p):
    if "button" in p: return button_solid(p["button"]["c"])
    if "box" in p: return box(*p["box"])
    c = p["cyl"]
    if "x" in c: return cyl_x(c["c"], c["r"], *c["x"])
    return cyl_z((c["x0"], c["c"][0]), c["r"], *c["z"])
r3 = lambda v: round(float(v), 2)

def build():
    outer = box(*UP) + box(*LOW)
    # interior: upper tier and lower tier hollow, open where they meet; front plate 2.0, walls 1.7
    up_in = box((UP[0][0] + BACK, UP[0][1] + WALL, UP[0][2] + WALL), (UP[1][0] - PLATE, UP[1][1] - WALL, UP[1][2] - ROOF))
    low_in = (box((UP[0][0] + BACK, LOW[0][1] + WALL, LOW[0][2] + FLOOR), (LOW[1][0] - PLATE, LOW[1][1] - WALL, LOW[1][2] + WALL + 1))
              + box((LOW[0][0] + BACK, LOW[0][1] + WALL, LOW[0][2] + FLOOR), (UP[0][0] + BACK + 0.01, LOW[1][1] - WALL, LOW[1][2] - WALL)))
    shell = outer - up_in - low_in
    # battery column walls in the upper tier (|y| 17.3..19.0 up to the battery top) and the two top stops
    col = (box((-70.3, 17.3, -15.3), (-47.0, 19.0, 19.0)) + box((-70.3, -19.0, -15.3), (-47.0, -17.3, 19.0))
           + box(*BAT_STOP) + box((-70.3, -17.3, 19.0), (-67.3, 17.3, 22.0)))
    bosses = [cyl_x((y, z), BOSS_D / 2, (CAP_SPLIT_X if z > -15.2 else CAP_SPLIT_X_LOW),
                    (CAP_SPLIT_X if z > -15.2 else CAP_SPLIT_X_LOW) + BOSS_L) for y, z in CAP_SCREWS]
    body = shell + col + mf.Manifold.batch_boolean(bosses, mf.OpType.Add)
    pin_block = box(*CAP_BLOCK) - cyl_z((-76.1, 9.0), 2.2, -60, -48) - cyl_z((-76.1, -9.0), 2.2, -60, -48)
    body = body + pin_block - PANEL_HOLE((17.0, 30.5))
    body = body - box((CAP_SPLIT_X - 2, -28.1 - 6.5, 26.25 - 3.75), (CAP_SPLIT_X + 0.01, -28.1 + 6.5, 26.25 + 3.75))   # USB-C window
    for y in (9.0, -9.0): body = body - cyl_z((-76.1, y), 2.2, -60, -50)                                         # contact bores
    keep_frame = box((CAP_SPLIT_X, -40, -15.2), (0, 40, 50)) + box((CAP_SPLIT_X_LOW, -40, -60), (0, 40, -15.2))
    frame, cap = body ^ keep_frame, body - keep_frame
    frame = frame - box(*CAP_BLOCK)
    cap = cap + (pin_block ^ body)
    return outer, frame, cap

def mass_props(M, dens=1.24 * 0.851):
    t = to_tm(M); return t.volume / 1000 * dens, np.array(t.center_mass)

def main():
    outer, frame, cap = build()
    out = {"frame": "guide/trunk frame, mm", "status": "concept, not approved, not a print release"}
    tm_outer = to_tm(outer)
    out["outline"] = dict(upper_tier=UP, lower_tier=LOW, today_lower_tier=TODAY_LOW,
                          bbox=[tm_outer.bounds[0].round(2).tolist(), tm_outer.bounds[1].round(2).tolist()],
                          today_bbox=[[-75.55, -32.05, -34.0], [-45.0, 32.05, 43.0]],
                          depth_behind_plate_upper=r3(UP[1][0] - UP[0][0]), depth_lower=r3(LOW[1][0] - LOW[0][0]),
                          height=r3(UP[1][2] - LOW[0][2]), today_height=77.0)
    out["volume_outer_cm3"] = dict(new=r3(tm_outer.volume / 1000),
                                   today=r3((to_tm(box(*UP) + box(*TODAY_LOW))).volume / 1000))
    solids = {n: part_solid(p) for n, p in PARTS.items()}
    # interference: bought parts against printed parts and each other
    printed = frame + cap
    out["overlap_mm3"] = {n: r3((s ^ printed).volume()) for n, s in solids.items() if "contact" not in n}
    names = list(solids)
    out["part_part_overlap_mm3"] = {f"{a} | {b}": r3((solids[a] ^ solids[b]).volume())
                                    for i, a in enumerate(names) for b in names[i + 1:] if (solids[a] ^ solids[b]).volume() > 0.01}
    # screw heads and driver lanes (driver from the open back along +x to the head)
    lanes = {}
    for y, z in SCREWS:
        head = cyl_x((y, z), HEAD["d"] / 2, -47.0 - HEAD["h"], -47.0)
        lane = cyl_x((y, z), DRIVER_R, -90.0, -47.0 - HEAD["h"])
        lanes[f"y{y:+.1f} z{z:+.1f}"] = dict(head_vs_battery=r3((head ^ solids["battery 2S 3000 (B08LZ8L4YD)"]).volume()),
                                            lane_vs_frame=r3((lane ^ frame).volume()),
                                            wall_gap_mm=r3((LOW[1][1] - WALL) - (abs(y) + DRIVER_R)) if z < -15.2 else None)
    out["fixing_screws_M2x6"] = lanes
    # masses and centre of mass against today's backpack (manifest battery-20261104)
    mfr, cfr = mass_props(frame); mcp, ccp = mass_props(cap)
    add = [("frame (print)", mfr, cfr), ("cap (print)", mcp, ccp)]
    for n, p in PARTS.items():
        s = to_tm(solids[n]); add.append((n, p["g"], np.array(s.center_mass)))
    add += [("leads, pigtails, connectors", 12.0, np.array([-60.0, 0.0, 15.0])), ("foam tape", 1.0, np.array([-65.0, 0.0, -10.0])),
            ("cap screws 4 x M2 x 8", 1.0, np.array([-77.0, 0.0, -5.0]))]
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
    # flight pack: the backpack sits 6.9 mm further back on the wing-plate centre (flight_params WING x_centre_back)
    fl = {}
    shift = (-6.9, 0, 0)
    # the upper tier keeps today's printed front and outline, so the flying check uses today's real frame and cap there and
    # the new lower-tier envelope below z -15.2 (an envelope box would claim the wing root band's recess, x -51.9..-53.5)
    today = load_mf(BP / "stl/battery_backpack_frame-world.stl") + load_mf(BP / "stl/battery_backpack_cap-world.stl")
    new_fl, old_fl = (today + box(*LOW)).translate(shift), today.translate(shift)
    for f in sorted((FLIGHT / "cad/build").glob("*-world.stl")):
        if "wing_plate" in f.name and f.name != "wing_plate-world.stl": continue
        M = load_mf(f)
        a, b = (new_fl ^ M).volume(), (old_fl ^ M).volume()
        if a > 0.01 or b > 0.01: fl[f.stem] = dict(new_mm3=r3(a), today_mm3=r3(b))
    out["flight_overlap_mm3 (backpack shifted -6.9 x)"] = fl
    h = FLIGHT / "cad/build/dummy_cross_harness-world.stl"
    out["flight_harness_rear_gap_mm"] = dict(upper_tier_back_flying=r3(UP[0][0] - 6.9), harness_rear_x_max=-84.0,
                                             lower_tier_top_z=LOW[1][2], harness_rear_z_min=4.0)
    # legs: hip pitch +-30, roll +-10 about the stand keyframe, both legs
    env = {"upper tier": [list(UP[0]), list(UP[1])], "lower tier (new)": [list(LOW[0]), list(LOW[1])],
           "contact tips": [[-78.1, -11.0, -56.5], [-74.1, 11.0, -55.0]], "lower tier (today)": [list(TODAY_LOW[0]), list(TODAY_LOW[1])]}
    leg = subprocess.run([str(Path.home() / ".venvs/microduck-dyn/bin/python"), str(HERE / "leg_check.py"), json.dumps(env)],
                         capture_output=True, text=True, check=True)
    out["leg_clearance_mm (hip pitch +-30, roll +-10)"] = json.loads(leg.stdout)
    # contacts in the stand pose
    out["contacts"] = dict(local_tip=[[-76.1, 9.0, -56.5], [-76.1, -9.0, -56.5]], spacing_mm=18.0, travel_mm=">= 1.5 (pin class)",
                           stand_world_tip=[[-76.1, 9.0, 63.5], [-76.1, -9.0, 63.5]], facing="down (-z)",
                           note="tips 1.5 mm below the floor at z -55; the box bottom is the lowest point of the robot behind the feet")
    # fits from print_fit (declared for the CAD stage)
    out["fits_H2S"] = dict(fixing_screw="M2 x 6 into existing rear-pack pilots (unchanged), plate clearance "
                                         f"{F.clear('M2', 'vertical', printer='H2S')} (plate prints back-face down, axis vertical)",
                           cap_screw_clear=F.clear("M2", "vertical", printer="H2S"), cap_screw_pilot_in_frame_boss=F.pilot("M2", "vertical", printer="H2S"),
                           pilot_depth_M2_clamped_2mm=F.pilot_depth("M2", 2.0), head_seat=F.HEAD_SEAT["M2"],
                           button_hole="16.0 +0.2/-0 (vendor panel cutout; through the cap back, vertical in print)",
                           pin_bore=f"pin barrel + 2 x {F.clearance('locating')} (locating), clamp strip with 2 x M2 x 6",
                           bought_board_pockets=f"listing size + 2 x {F.clearance('loose')} (loose), held by foam tape")
    json.dump(out, open(HERE / "concept.json", "w"), indent=1)
    sheet(out, frame, cap, solids, poses)
    print(json.dumps({k: out[k] for k in ("outline", "mass", "fixing_screws_M2x6", "leg_clearance_mm (hip pitch +-30, roll +-10)",
                                          "flight_overlap_mm3 (backpack shifted -6.9 x)", "overlap_mm3", "part_part_overlap_mm3")}, indent=1))

# ------------------------------------------------------------------ sheet
COL = {"battery": "#4c9a5b", "Pololu": "#2d6fb7", "DFR1202": "#1f3f7a", "XIAO": "#7a3fa0", "button": "#c0392b",
       "Schottky": "#555555", "contact": "#d4a017"}
def colour(n): return next((c for k, c in COL.items() if k in n), "#888")

def robot_points(poses, bodies_out=("trunk_base",)):
    pts = []
    for p in poses["parts"]:
        v = np.frombuffer(base64.b64decode(p["pos"]), np.float32).reshape(-1, 3).astype(float)
        v[:, 2] -= 120
        pts.append((poses["bodies"][str(p["body"])], v, np.frombuffer(base64.b64decode(p["idx"]), np.uint32).reshape(-1, 3) if "idx" in p else None, p["color"]))
    return pts

def rect(ax, lo, hi, i, j, **kw):
    ax.add_patch(Rectangle((lo[i], lo[j]), hi[i] - lo[i], hi[j] - lo[j], **kw))

def sheet(out, frame, cap, solids, poses):
    fig = plt.figure(figsize=(22, 15), dpi=110)
    fig.suptitle("MicroDuck battery backpack V2 - CONCEPT for approval (2026-11-19, not a print release)  |  2S 3000 mAh fixed pack, "
                 "Pololu 2813 soft switch, XIAO cutoff, 16 mm LED button, contacts under the tail", fontsize=14, weight="bold")
    rp = robot_points(poses)
    # --- 3D view with the robot
    ax = fig.add_subplot(2, 3, 1, projection="3d")
    for b, v, f, c in rp:
        if f is None: continue
        if b == "trunk_base" and c[0] > 0.7 and c[1] < 0.7: continue          # today's orange backpack and saddle mesh
        tri = v[f[::2]]
        ax.add_collection3d(Poly3DCollection(tri, facecolor=(*c, 0.18), edgecolor="none"))
    for M, colr in ((frame, (1.0, 0.55, 0.1, 0.35)), (cap, (1.0, 0.75, 0.3, 0.35))):
        t = to_tm(M); ax.add_collection3d(Poly3DCollection(t.vertices[t.faces], facecolor=colr, edgecolor="none"))
    for n, s in solids.items():
        t = to_tm(s); ax.add_collection3d(Poly3DCollection(t.vertices[t.faces], facecolor=colour(n), edgecolor="none", alpha=0.9))
    ax.set_xlim(-140, 60); ax.set_ylim(-100, 100); ax.set_zlim(-125, 75); ax.set_box_aspect((200, 200, 200))
    ax.view_init(elev=18, azim=-140); ax.set_title("On the robot (stand pose, from behind left); grey = robot, orange = new box")
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z (guide)")

    # --- side section y = 0
    ax = fig.add_subplot(2, 3, 2)
    for b, v, f, c in rp:
        if b in ("jaw_soft",) or (b == "trunk_base" and c[0] > 0.7 and c[1] < 0.7): continue
        s = v[np.abs(v[:, 1]) < 45]; ax.plot(s[::7, 0], s[::7, 2], ",", color="#bbbbbb")
    rect(ax, (-75.55, 0, -34), (-45, 0, 43), 0, 2, fill=False, ls="--", lw=1.5, ec="k")
    for b in (UP, LOW): rect(ax, b[0], b[1], 0, 2, fc=(1, 0.6, 0.2, 0.25), ec="#e07000", lw=2)
    ax.plot([CAP_SPLIT_X, CAP_SPLIT_X], [-15.2, 43], color="#e07000", ls=":", lw=1)
    for n, p in PARTS.items():
        if "box" in p and abs((p["box"][0][1] + p["box"][1][1]) / 2) < 1: rect(ax, p["box"][0], p["box"][1], 0, 2, fc=colour(n), alpha=0.85)
    rect(ax, BAT_FOAM[0], BAT_FOAM[1], 0, 2, fc="#f2e6a0"); rect(ax, *BAT_STOP, 0, 2, fc="#e07000")
    rect(ax, (-75.55 - 1.5, 0, 30.5 - 9.25), (-55.55, 0, 30.5 + 9.25), 0, 2, fill=False, ec=COL["button"], ls="--", lw=1.5)
    for y, z in SCREWS: rect(ax, (-48.6, 0, z - 1.9), (-47.0, 0, z + 1.9), 0, 2, fc="k")
    ax.plot([-76.1, -76.1], [-56.5, -42], color=COL["contact"], lw=4)
    ax.plot([-85, 0], [-120 + 0, -120 + 0], "k-", lw=0.5)
    ax.annotate("battery 72 x 34 x 20\nleads up (110 g)", (-59.3, -20), ha="center", color="w", fontsize=9, weight="bold")
    ax.annotate("top bay: leads, XT30 joint,\nbalance plug parks here", (-60, 31), ha="center", fontsize=8)
    ax.annotate("button (behind, y +17)", (-77, 41), fontsize=8, color=COL["button"])
    ax.annotate("contacts in the heel;\ncap block holds them", (-100, -66), fontsize=8, color="#8a6d00")
    rect(ax, CAP_BLOCK[0], CAP_BLOCK[1], 0, 2, fc="#f5b041", alpha=0.8)
    ax.plot([CAP_SPLIT_X_LOW, CAP_SPLIT_X_LOW], [-55, -15.2], color="#e07000", ls=":", lw=1)
    ax.annotate("cap | frame", (CAP_SPLIT_X - 9, 46), fontsize=8, color="#e07000")
    ax.annotate("dashed = today's box (bottom z -34)", (-128, 50), fontsize=8)
    ax.annotate("floor (stand)", (-128, -118), fontsize=8)
    ax.set_xlim(-130, 10); ax.set_ylim(-122, 60); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title("Side section y = 0 (x forward to the right), guide z"); ax.set_xlabel("x mm"); ax.set_ylabel("z mm")

    # --- back view (viewer behind the robot: robot's left on the image left)
    ax = fig.add_subplot(2, 3, 3)
    def r_back(lo, hi, **kw): ax.add_patch(Rectangle((-hi[1], lo[2]), hi[1] - lo[1], hi[2] - lo[2], **kw))
    r_back((0, -32.05, -34), (0, 18.6, 43), fill=False)  # placeholder (replaced below)
    ax.patches[-1].remove()
    ax.plot([-32.05, 32.05, 32.05, 18.6, 18.6, -18.6, -18.6, -32.05, -32.05], [43, 43, -15.2, -15.2, -34, -34, -15.2, -15.2, 43], "k--", lw=1.5)
    for b in (UP, LOW): r_back(b[0], b[1], fc=(1, 0.6, 0.2, 0.25), ec="#e07000", lw=2)
    for n, p in PARTS.items():
        if "box" in p: r_back(p["box"][0], p["box"][1], fc=colour(n), alpha=0.85)
    ax.add_patch(Circle((-17.0, 30.5), 9.25, fc=COL["button"], alpha=0.85)); ax.add_patch(Circle((-17.0, 30.5), 6.0, fc="#7fd27f"))
    ax.add_patch(Rectangle((28.1 - 6.5, 26.25 - 3.75), 13, 7.5, fc="w", ec="k"))
    for y in (9.0, -9.0): ax.add_patch(Rectangle((-y - 2, -56.5), 4, 1.5, fc=COL["contact"]))
    for y, z in CAP_SCREWS: ax.add_patch(Circle((-y, z), 1.25, fc="w", ec="k"))
    ax.annotate("LED button\n(push = ON)", (-17, 42), ha="center", fontsize=8, color=COL["button"])
    ax.annotate("XIAO USB-C\nwindow", (28, 31.5), ha="center", fontsize=8)
    ax.annotate("Pololu\n2813", (-28.2, 14.5), ha="center", fontsize=8)
    ax.annotate("DFR\n1202", (26.3, -5), ha="center", fontsize=8, color="w")
    ax.annotate("XIAO", (28, 23), ha="center", fontsize=7, color="w")
    ax.annotate("battery", (0, -20), ha="center", fontsize=9, color="w", weight="bold")
    ax.annotate("2 contacts, 18 mm apart", (0, -66), ha="center", fontsize=8, color="#8a6d00")
    ax.annotate("robot LEFT (+y)", (-34, 47), fontsize=8); ax.annotate("robot RIGHT (-y)", (12, 47), fontsize=8)
    ax.set_xlim(-45, 45); ax.set_ylim(-72, 55); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title("Back view (seen from behind), dashed = today; white circles = 4 cap screws M2 x 8")

    # --- top section at z 30 (top bay)
    ax = fig.add_subplot(2, 3, 4)
    rect(ax, UP[0], UP[1], 0, 1, fc=(1, 0.6, 0.2, 0.25), ec="#e07000", lw=2)
    rect(ax, LOW[0], LOW[1], 0, 1, fill=False, ec="#e07000", ls=":", lw=1.5)
    for n, p in PARTS.items():
        if "box" in p and p["box"][0][2] < 30 < p["box"][1][2]: rect(ax, p["box"][0], p["box"][1], 0, 1, fc=colour(n), alpha=0.85)
    rect(ax, (-75.55 - 1.5, 17 - 9.25, 0), (-75.55, 17 + 9.25, 0), 0, 1, fc=COL["button"])
    rect(ax, (-73.85, 17 - 10.9, 0), (-70.85, 17 + 10.9, 0), 0, 1, fc="#c0392b", alpha=0.5)
    rect(ax, (-70.85, 17 - 8, 0), (-55.55, 17 + 8, 0), 0, 1, fc="#c0392b", alpha=0.3)
    rect(ax, (-64, -12, 0), (-58.8, 2, 0), 0, 1, fc="#ffd200", ec="k")
    for y, z in SCREWS[:2]: rect(ax, (-48.6, y - 1.9, 0), (-47.0, y + 1.9, 0), 0, 1, fc="k")
    ax.annotate("XT30 battery to\nPololu VIN joint", (-61, -20), ha="center", fontsize=8)
    ax.annotate("button body\n20 mm deep", (-63, 26.5), ha="center", fontsize=8)
    ax.annotate("upper fixing\nscrews", (-50, 34), fontsize=7)
    ax.set_xlim(-85, -40); ax.set_ylim(-36, 40); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title("Top section z = 30 (top bay over the battery); dotted = lower tier below"); ax.set_xlabel("x"); ax.set_ylabel("y")

    # --- wiring block diagram
    ax = fig.add_subplot(2, 3, 5); ax.axis("off"); ax.set_title("Wiring (one line = one wire pair)")
    txt = ("POWER (16 AWG)\n"
           "  battery XT30 -> Pololu 2813 VIN\n"
           "  Pololu VOUT -> plug 3 XT30 -> OpenRB J4\n"
           "  Pololu VOUT -> DFR1202 VIN (22 AWG)\n"
           "  DFR1202 5 V -> plug 4 MR30 pins 1-2 -> A7Z\n"
           "CHARGE (20 AWG, 2 A)\n"
           "  contact + -> 1N5822 -> battery DC5.5 lead +\n"
           "  contact - -> battery DC5.5 lead -\n"
           "BUTTON (push = ON only, a knock cannot switch off)\n"
           "  NO contact: VIN -10k-> Pololu ON\n"
           "  LED ring (6 V, own resistor) <- DFR1202 5 V\n"
           "XIAO SAMD21 (5 V from DFR1202, 26 AWG)\n"
           "  A0 <- VOUT 100k/33k    A1 <- mid cell XH 100k/100k\n"
           "  A2 <- contact + 100k/33k  A3 <- ON line 100k/33k\n"
           "  D6 -1N4148-> Pololu OFF <-1N4148- A7Z GPIO\n"
           "     (A7Z GPIO on plug 4 MR30 pin 3); OFF 100k to GND\n"
           "  cut: pack < 6.3 V or a cell < 3.1 V for 3 s;\n"
           "  hold button 2 s while on = shutdown request\n"
           "BALANCE: battery XH -> XH socket on the XIAO harness;\n"
           "  unplug it for the monthly B3 balance charge")
    ax.text(0.0, 1.0, txt, family="monospace", fontsize=8.6, va="top")

    # --- numbers
    ax = fig.add_subplot(2, 3, 6); ax.axis("off"); ax.set_title("Numbers (concept envelopes; CAD after the parts are measured)")
    m, o = out["mass"], out["outline"]
    leg = out["leg_clearance_mm (hip pitch +-30, roll +-10)"]
    fl = out["flight_overlap_mm3 (backpack shifted -6.9 x)"]
    lines = [
        "Upper tier unchanged: x -45..-75.55, |y| 32.05, top z 43.",
        "Lower tier: bottom z -34 -> -55 (21 mm lower),",
        "  |y| 18.6 -> 20.0, back -75.55 -> -80 (4.45 mm heel).",
        f"Height {o['today_height']:.0f} -> {o['height']:.0f} mm; outer volume {out['volume_outer_cm3']['today']:.0f} -> {out['volume_outer_cm3']['new']:.0f} cm3.",
        f"Backpack {m['backpack_today_g']:.0f} -> {m['backpack_new_g']:.0f} g ({m['delta_g']:+.0f} g); robot {m['robot_today_g']:.0f} -> {m['robot_new_g']:.0f} g.",
        f"Robot COM moves {-m['com_shift_mm'][0]:.1f} mm back and {-m['com_shift_mm'][2]:.1f} mm down.",
        f"Legs (hip pitch +-30, roll +-10): {leg['lower tier (new)']['min_mm']} mm min",
        f"  (today {leg['lower tier (today)']['min_mm']}; rule >= 6); contacts {leg['contact tips']['min_mm']} mm.",
        "Flight pack (box 6.9 mm back): " + (", ".join(f"{k} {v['new_mm3']} mm3" for k, v in fl.items()) or "no overlap"),
        "Contacts: 2 spring pins, y +-9 (18 mm apart), x -76.1,",
        "  tips z -56.5 = 63.5 mm above the floor standing, facing down.",
        "Screws: 4 x M2 x 6 fixing (unchanged), 4 x M2 x 8 cap.",
        "Boards on 3M foam tape; battery boxed by walls + foam pads.",
        "No snaps, hooks or flexures; walls 1.7, floor 2.0 mm.",
    ]
    ax.text(0.0, 1.0, "\n".join(lines), fontsize=10, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(HERE / "concept-sheet.png"); plt.close(fig)

if __name__ == "__main__":
    main()
