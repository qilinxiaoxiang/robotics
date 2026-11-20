"""MicroDuck battery backpack rev B charging dock base, release BatteryDock-A1: one printed Orange part, flat on the bed.

    Mac mini:  zsh mini_sync.sh push && zsh mini_sync.sh run '$PY build_dock.py' && zsh mini_sync.sh pull
    (the MacBook swaps; heavy-compute rule. Slicing runs on the MacBook: zsh slices/release-BatteryDock-A1/scripts/run_dock.sh)

Frame: x forward, y left (guide/backpack frame), z = height above the floor with the robot seated, mm. The backpack STLs
of ../battery-v2-cad-20261120 are in the guide frame standing (pad faces at z -46); seated they sit at z 10.9, so
z_seated = z_guide + 56.9. The real Brain sit in the sim (battery-v2-cad-20261120/checks/legsit.json) puts the pads at
10.2 with 1.9 deg trunk pitch; the design keeps the brief's nominal 10.9 and build.json reports both compressions.

Numbered needs (each feature in features.json answers one):
  N1 a seated robot's two pads must each meet one sprung contact, + under the y +9 pad, - under the y -9 pad
  N2 the contacts must be held as Keystone intends (5209 body pressed into a housing groove), with nothing printed that bends
  N3 the robot must be stopped in x so its pads land over the leaves
  N4 the charger plug must enter a panel jack that is wired to the two contacts with short soldered wires
  N5 the dock must stay where it is put (no printed feature: foam tape or Dual Lock under the plate)
Docking guidance (funnel, side rails) is later software work; nothing here steers the robot.

Fits from cad-practice/print_fit.py (H2S, as the backpack CAD): every number below names its class. No snaps, hooks or
flexures; the only sprung parts are the bronze leaves.

Writes build/dock_base-world.stl, build/dock_base-print.stl, build/parts/*-world.stl (bought-part envelopes, seated
positions), build/build.json (geometry, checks, assembly), FITS.json; exit 1 on a failed check.
"""
import json, math, sys
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
MD = HERE.parents[2]                                            # microduck-sim
BV2 = MD / "guide/print/battery-v2-cad-20261120"
PIPE = MD / "build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009"
OUT = HERE / "build"; (OUT / "parts").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(MD.parent / "cad-practice")); import print_fit as F  # noqa: E402
sys.path.insert(0, str(PIPE)); import wall_check as W  # noqa: E402
PRINTER = "H2S"
PLA = 1.24                                                      # g/cm3

# ------------------------------------------------------------------ robot (battery-v2 rev B, seated)
Z_SEAT = 10.9 - (-46.0)                                         # guide -> seated z offset (backpack bottom 10.9)
BACK_X = -75.55                                                 # backpack back face (cap outer face)
SEAT_SIM = 10.2                                                 # pads seated in the sim Brain sit (legsit.json)
LOW_CAP_SCREWS = [(9.0, -46.0 + 7.1 + Z_SEAT), (-9.0, -46.0 + 7.1 + Z_SEAT)]   # (y, z seated) = (+-9, 18.0)
HEAD = (4.0, 1.6)                                               # M2 pan head ISO 7045 dk x k, proud of the cap face
HEAD_SEAT_D = F.HEAD_SEAT["M2"][0]                              # 4.6: pan or button head envelope (print_fit HEAD_SEAT)

# ------------------------------------------------------------------ bought parts (published drawings)
# Keystone 5209 (catalog M65p15): 0.30 phosphor bronze; body 14.0 long, 10.0 across its wings; leaf 7.0 wide, 10.9 REF
# long, free height 7.6 MIN above the body; solder tab 5.0 x 7.0 below the body, 2.01 hole, jogged 1.6 out of plane.
K_T, K_BODY_L, K_BODY_W, K_LEAF_W, K_LEAF_L, K_FREE = 0.30, 14.0, 10.0, 7.0, 10.9, 7.6
K_TAB_W, K_TAB_L, K_JOG = 5.0, 7.0, 1.6
# Same Sky PJ-005A (datasheet rev 1.09, page 2 drawing): bushing 5/16"-32 (7.94) x 5.7 from the flange face, flange 10.8,
# housing 10.0 behind the flange face, 15.5 to the lug ends; nut 10.8 AF x 2.0; washer 10.9 x 0.5. Lugs (side view, item
# numbers): centre-pin terminal (schematic 1) 3.8 mm above the axis, tip spring = sleeve contact (schematic 2) on the
# axis, shunt spring (schematic 3) 4.4 mm below the axis; lug spread 4.0 wide.
J_BUSH_D, J_BUSH_L, J_FLANGE_D, J_BODY_L, J_ALL_L = 7.94, 5.7, 10.8, 10.0, 15.5
J_NUT_AF, J_NUT_T, J_WASH_D, J_WASH_T = 10.8, 2.0, 10.9, 0.5
J_LUG = {"centre pin (+, schematic 1)": 3.8, "sleeve (-, schematic 2)": 0.0, "shunt switch (unused, schematic 3)": -4.4}
J_LUG_W = 4.0

# ------------------------------------------------------------------ fits (print_fit.py, H2S)
LAYER = F.PROFILE["layer"]
PRESS = F.clearance("press", "horizontal")         # +0.05/side: groove height across the 0.30 body (horizontal slot)
LOCATE_H = F.clearance("locating", "horizontal")   # +0.25/side: groove width across the wings, jack bushing hole
LOCATE_V = F.clearance("locating", "vertical")     # +0.15/side: leaf opening (vertical walls, leaf moves along z)
LOOSE_H = F.clearance("loose", "horizontal")       # +0.50/side: insertion slot in the stop wall (passes the whole contact)
GROOVE_H = round(K_T + 2 * PRESS, 3)               # 0.40 = two 0.2 mm layers
GROOVE_W = round(K_BODY_W + 2 * LOCATE_H, 3)       # 10.50
LEAF_OPEN_W = round(K_LEAF_W + 2 * LOCATE_V, 3)    # 7.30 (lips 1.6 wide each)
JACK_HOLE_D = round(J_BUSH_D + 2 * LOCATE_H, 3)    # 8.44, teardrop tip +z (axis x lies in the layer plane)

# ------------------------------------------------------------------ dock geometry
PLATE_T = 2.0
SEAT_Z = 6.0                                       # body underside (groove floor)
BLOCK_TOP = 8.0
X_STOP = -76.5                                     # stop face, 0.95 behind the backpack back face
FRONT_WALL_T = 3.2                                 # 1.5 relief for the cap screw heads + 1.7 wall behind it
RELIEF_D, RELIEF_Z0 = 1.5, None                    # relief channel depth; bottom = insertion slot top (set below)
TOWER_Y, TOWER_WALL, TOWER_TOP = 17.0, 2.0, 22.0
REAR_WALL_T = 2.5                                  # PJ-005A panel limit about 3.2 (5.7 - 2.0 nut - 0.5 washer)
JACK_Z = 10.0                                      # nut corner 3.76 above the floor, flange 4.6 above the plate
LUG_GAP = 2.3                                      # lug ends to the stop wall's inner face (soldering iron room)
BLOCK_Y = 16.5                                     # 1.7 wall beside the insertion-slot pocket that reaches 0.9 into the block
BLOCK_X1 = -58.0
PLATE_Y = 20.0
WIRE_STRIP, WIRE_SLACK = 3.0, 10.0                 # 20 AWG: strip at each end, slack for the iron


def box(lo, hi):
    lo, hi = np.array(lo, float), np.array(hi, float)
    return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
def U(ms): return mf.Manifold.batch_boolean(list(ms), mf.OpType.Add)
def to_tm(M):
    g = M.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=True)
def load_mf(p, dz=0.0):
    m = trimesh.load(p, force="mesh", process=True); m.merge_vertices(); m.apply_translation((0, 0, dz))
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def cyl_x(y, z, d, x0, x1, n=64):
    return mf.Manifold.cylinder(x1 - x0, d / 2, d / 2, n).rotate((0, 90, 0)).translate((x0, y, z))
def hex_x(y, z, af, x0, x1):
    return mf.Manifold.cylinder(x1 - x0, af / math.sqrt(3), af / math.sqrt(3), 6).rotate((0, 90, 0)).translate((x0, y, z))
def teardrop_x(y, z, d, x0, x1):
    """Full circle d plus a 45 deg tip toward +z (PRINT-FIT Teardrops: the tip never narrows the hole)."""
    r = d / 2
    tip = mf.CrossSection([[(0, r * math.sqrt(2)), (-r / math.sqrt(2), r / math.sqrt(2)), (r / math.sqrt(2), r / math.sqrt(2))]])
    cs = mf.CrossSection.circle(r, 64) + tip                    # (y, z) section
    T = [[0, 0, 1, x0], [1, 0, 0, y], [0, 1, 0, z]]
    return mf.Manifold.extrude(cs, x1 - x0).transform(T)
def hull(pts): return mf.Manifold.hull_points([tuple(map(float, p)) for p in pts])


# ------------------------------------------------------------------ robot inputs
def pads():
    P = {}
    for s in ("plus", "minus"):
        P[s] = load_mf(BV2 / f"build/parts/contact_pad_{s}-world.stl", Z_SEAT)
    return P


PADS = pads()
PB = {s: np.array(M.bounding_box()).reshape(2, 3) for s, M in PADS.items()}
PAD_CX = float((PB["plus"][0, 0] + PB["plus"][1, 0]) / 2)                         # -69.5
PAD_Y = {s: float((b[0, 1] + b[1, 1]) / 2) for s, b in PB.items()}                # +9 / -9
PAD_Z = float(PB["plus"][0, 2])                                                    # 10.9
assert PAD_Y["plus"] > 0 and abs(PAD_Z - 10.9) < 1e-3, (PAD_Y, PAD_Z)

BODY_X0, BODY_X1 = PAD_CX - K_BODY_L / 2, PAD_CX + K_BODY_L / 2                    # -76.5 .. -62.5
assert abs(BODY_X0 - X_STOP) < 1e-3, BODY_X0
TOP = SEAT_Z + K_T                                                                 # 6.3 body top face
LEAF_TOP = TOP + K_FREE                                                            # 13.9
LEAF_RUN = math.sqrt(K_LEAF_L ** 2 - K_FREE ** 2)                                  # 7.81
SLOT_Z = (round(SEAT_Z - K_JOG - 0.6, 1), round(LEAF_TOP + 0.7, 1))                # 3.8 .. 14.6 (tab jog down / leaf up)
SLOT_W = round(K_BODY_W + 2 * LOOSE_H, 2)                                          # 11.0
RELIEF_Z0 = SLOT_Z[1]
X_WALL_IN = X_STOP - FRONT_WALL_T                                                  # -79.7
X_FLANGE = X_WALL_IN - LUG_GAP - J_ALL_L                                           # -97.5 (rear wall inner face)
X_REAR = X_FLANGE - REAR_WALL_T                                                    # -100.0
TAB_X0 = BODY_X0 - K_TAB_L                                                         # -83.5


def leaf(y, top_z):
    """Leaf envelope: 0.3 slab from the root at the body's front end up to its tip at top_z (slab 0.4 incl. the bend)."""
    run = math.sqrt(K_LEAF_L ** 2 - (top_z - TOP) ** 2)
    w = K_LEAF_W / 2; x_r = BODY_X1; x_t = BODY_X1 - run
    pts = []
    for yy in (y - w, y + w):
        # root bend: bulges 0.4 past the body end only above the groove roof (the body end itself bears on the groove end)
        pts += [(x_r - 0.1, yy, TOP), (x_r + 0.4, yy, TOP + 0.6), (x_r + 0.4, yy, TOP + 1.0), (x_t, yy, top_z), (x_t - 0.4, yy, top_z - 0.4)]
    return hull(pts), x_t


def contact(y):
    w = K_BODY_W / 2
    body = box((BODY_X0, y - w, SEAT_Z), (BODY_X1, y + w, TOP))
    tab = box((TAB_X0, y - K_TAB_W / 2, SEAT_Z - K_JOG), (BODY_X0 + 0.01, y + K_TAB_W / 2, TOP + K_JOG))  # jog either way
    lf, _ = leaf(y, LEAF_TOP)
    return body + tab + lf


def jack():
    z = JACK_Z
    bush = cyl_x(0, z, J_BUSH_D, X_FLANGE - J_BUSH_L, X_FLANGE)
    housing = cyl_x(0, z, J_FLANGE_D, X_FLANGE, X_FLANGE + J_BODY_L)
    lugs = box((X_FLANGE + J_BODY_L - 0.01, -J_LUG_W / 2, z - 4.4 - 0.6), (X_FLANGE + J_ALL_L, J_LUG_W / 2, z + 3.8 + 0.6))
    wash = cyl_x(0, z, J_WASH_D, X_REAR - J_WASH_T, X_REAR)
    nut = hex_x(0, z, J_NUT_AF, X_REAR - J_WASH_T - J_NUT_T, X_REAR - J_WASH_T)
    return U([bush, housing, lugs, wash, nut])


LEAF_SLOT_HW = K_LEAF_W / 2 + LOOSE_H                                              # 4.0: leaf passage half-width at SLOT_Z[1]
SLOT_EAVE = SLOT_Z[1] - (SLOT_W / 2 - LEAF_SLOT_HW)                                # 13.1: gable starts here
SLOT_APEX = SLOT_EAVE + SLOT_W / 2                                                 # 18.6


def slot(y):
    """Insertion slot through the stop wall: SLOT_W wide from SLOT_Z[0], roof a 45 deg gable (self-supporting; a flat
    11 mm roof drew tree support on the Elegoo profile in the first slice) that still leaves LEAF_SLOT_HW at SLOT_Z[1]."""
    hw = SLOT_W / 2
    cs = mf.CrossSection([[(y - hw, SLOT_Z[0]), (y + hw, SLOT_Z[0]), (y + hw, SLOT_EAVE), (y, SLOT_APEX), (y - hw, SLOT_EAVE)]])
    x0, x1 = X_WALL_IN - 0.5, X_STOP + 0.6   # 0.6 into the block under the body end: no 0.01 notch seams
    T = [[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]]
    # in the screw-head relief layer (front RELIEF_D) the slot runs full width up into the relief: no thin eave wedges
    # 0.3 wider, lower and longer than the gable part so no face is coplanar with it (coplanar seams left pinched vertices)
    front = box((X_STOP - RELIEF_D, y - hw - 0.3, SLOT_Z[0] - 0.3), (x1 + 0.3, y + hw + 0.3, RELIEF_Z0 + 0.5))
    return mf.Manifold.extrude(cs, x1 - x0).transform(T) + front


FEATURES = []
def feat(i): FEATURES.append(i)


def build():
    add = [box((X_REAR, -PLATE_Y, 0), (BLOCK_X1 + 3.0, PLATE_Y, PLATE_T))]; feat("D1-base-plate")
    add.append(box((X_STOP - 0.01, -BLOCK_Y, 0), (BLOCK_X1, BLOCK_Y, BLOCK_TOP))); feat("D2-contact-block")
    # tower: front (stop) wall, side walls, rear (jack) wall; open top
    add.append(box((X_REAR, -TOWER_Y, 0), (X_STOP, TOWER_Y, TOWER_TOP)))   # tower shell; interior cut below
    feat("D3-stop-wall"); feat("D4-tower")
    dock = U(add)
    cuts = []
    for y in PAD_Y.values():
        gw = GROOVE_W / 2
        cuts.append(box((X_STOP - 0.5, y - gw, SEAT_Z), (BODY_X1, y + gw, SEAT_Z + GROOVE_H)))       # closed front at -62.5
        cuts.append(box((X_STOP - 0.5, y - LEAF_OPEN_W / 2, SEAT_Z + GROOVE_H - 0.01),
                        (BODY_X1 + 0.75, y + LEAF_OPEN_W / 2, BLOCK_TOP + 1)))                      # leaf opening, 0.75 past the root
        cuts.append(slot(y))
    feat("D2-grooves"); feat("D2-leaf-openings"); feat("D3-insertion-slots")
    cuts.append(box((X_STOP - RELIEF_D, -TOWER_Y - 1, RELIEF_Z0), (X_STOP + 0.5, TOWER_Y + 1, TOWER_TOP + 1)))
    feat("D3-screw-head-relief")
    cuts.append(teardrop_x(0, JACK_Z, JACK_HOLE_D, X_REAR - 0.5, X_FLANGE + 0.5)); feat("D4-jack-hole")
    cuts.append(box((X_FLANGE, -(TOWER_Y - TOWER_WALL), PLATE_T), (X_WALL_IN, TOWER_Y - TOWER_WALL, TOWER_TOP + 1)))
    feat("D4-tower-open-top")
    dock = dock - U(cuts)
    return U([b for b in dock.decompose() if b.volume() > 1.0])


def overhang(pm, deg=45):
    n = pm.face_normals; zmin = pm.triangles[:, :, 2].min(axis=1)
    bad = (n[:, 2] < -np.cos(np.radians(deg))) & (zmin > 0.2)
    regions = []
    if bad.any():
        sub = pm.submesh([np.where(bad)[0]], append=True)
        for c in sub.split(only_watertight=False):
            regions.append(dict(bbox=c.bounds.round(2).tolist(), area_mm2=round(float(c.area), 1)))
    return round(float(pm.area_faces[bad].sum()), 1), regions


def r3(v): return round(float(v), 3)


def main():
    dock = build()
    fails = []
    parts = {"keystone_5209_plus": contact(PAD_Y["plus"]), "keystone_5209_minus": contact(PAD_Y["minus"]), "pj005a": jack()}
    tm = to_tm(dock); tm.export(OUT / "dock_base-world.stl")
    off = -tm.bounds[0].copy(); off[2] = 0.0                      # print pose: as seated, plate on the bed (z 0 = bed)
    pm = tm.copy(); pm.apply_translation(off); pm.export(OUT / "dock_base-print.stl")
    T = np.eye(4); T[:3, 3] = off
    for n, M in parts.items(): to_tm(M).export(OUT / "parts" / f"{n}-world.stl")
    # ---------------------------------------------------------------- checks
    ck = {}
    ck["solid"] = dict(bodies=len(dock.decompose()), watertight=bool(tm.is_watertight), status=str(dock.status()),
                       winding_consistent=bool(tm.is_winding_consistent))
    if ck["solid"]["bodies"] != 1 or not tm.is_watertight: fails.append(f"dock not one closed body {ck['solid']}")
    ov = {n: r3((dock ^ M).volume()) for n, M in parts.items()}
    ck["dock_vs_parts_overlap_mm3"] = ov
    for n, v in ov.items():
        if v > 0.01: fails.append(f"dock | {n} overlap {v}")
    ck["dock_vs_parts_min_gap_mm"] = {n: r3(dock.min_gap(M, 2.0)) for n, M in parts.items()}
    ck["designed_contacts"] = ("body front end bears on the groove's closed end (x -62.5); jack flange face on the rear "
                               "wall's inner face; washer on its outer face; zero-volume touches, not overlaps")
    robot = {"pad plus": PADS["plus"], "pad minus": PADS["minus"],
             "backpack frame": load_mf(BV2 / "build/battery_v2_frame-world.stl", Z_SEAT),
             "backpack cap": load_mf(BV2 / "build/battery_v2_cap-world.stl", Z_SEAT)}
    for i, (y, z) in enumerate(LOW_CAP_SCREWS):
        robot[f"low cap screw head {'left' if y > 0 else 'right'} (seat envelope {HEAD_SEAT_D})"] = cyl_x(y, z, HEAD_SEAT_D, BACK_X - HEAD[1], BACK_X + 0.01)
    ck["dock_vs_robot_overlap_mm3"] = {n: r3((dock ^ M).volume()) for n, M in robot.items()}
    ck["dock_vs_robot_min_gap_mm"] = {n: r3(dock.min_gap(M, 4.0)) for n, M in robot.items()}
    for n, v in ck["dock_vs_robot_overlap_mm3"].items():
        if v > 0.01: fails.append(f"dock | {n} overlap {v}")
    leaf_c = {}
    for s in ("plus", "minus"):
        lc, xt = leaf(PAD_Y[s], PAD_Z)
        leaf_c[s] = dict(dock_overlap_mm3=r3((dock ^ lc).volume()), tip_x=r3(xt),
                         tip_under_pad=bool(PB[s][0, 0] <= xt <= PB[s][1, 0]))
        if leaf_c[s]["dock_overlap_mm3"] > 0.01 or not leaf_c[s]["tip_under_pad"]: fails.append(f"compressed leaf {s} {leaf_c[s]}")
        lf, xf = leaf(PAD_Y[s], LEAF_TOP)
        leaf_c[s]["free_tip_x"] = r3(xf)
        leaf_c[s]["free_leaf_vs_pad_overlap_mm3 (designed: the seated pad presses the leaf down)"] = r3((lf ^ PADS[s]).volume())
    ck["leaf_compressed_at_seat"] = leaf_c
    top_under_pad = float(max(v[2] for v in tm.vertices if PB["minus"][0, 1] - 1 <= v[1] <= PB["plus"][1, 1] + 1 and X_STOP + 0.01 <= v[0] <= BLOCK_X1))
    ck["block_top_z"] = r3(top_under_pad)
    if top_under_pad > 8.5: fails.append(f"block top {top_under_pad} > 8.5")
    if PAD_Z - top_under_pad < 2.5: fails.append("block top closer than 2.5 to the pads")
    wc = W.check(pm, (), "dock_base")
    ck["wall_check"] = dict(passed=wc["passed"], min_wall_mm=W.MIN_WALL_MM, min_smoothed_mm=wc["minSmoothedMm"],
                            fail_regions=[{k: g[k] for k in ("bbox", "minMm", "areaMm2", "status")} for g in wc["regions"] if g["status"] == "FAIL"],
                            small_thin_patches=wc["smallThinPatches"])
    if not wc["passed"]: fails.append(f"wall check: {wc['failures']}")
    designed_min = dict(base_plate=PLATE_T, block_side_walls=round(BLOCK_Y - (PAD_Y['plus'] + GROOVE_W / 2), 2),
                        block_wall_beside_slot_pocket=round(BLOCK_Y - (PAD_Y['plus'] + SLOT_W / 2 + 0.3), 2),
                        block_centre_web=round(2 * (PAD_Y['plus'] - GROOVE_W / 2), 2),
                        lips=dict(width=round((GROOVE_W - LEAF_OPEN_W) / 2, 2), height=round(BLOCK_TOP - SEAT_Z - GROOVE_H, 2)),
                        groove_floor_above_plate=round(SEAT_Z - PLATE_T, 2), stop_wall_behind_relief=round(FRONT_WALL_T - RELIEF_D, 2),
                        stop_wall_outer_strip=round(TOWER_Y - (PAD_Y['plus'] + SLOT_W / 2 + 0.3), 2),
                        side_walls=TOWER_WALL, rear_wall=REAR_WALL_T, block_front_end=round(BLOCK_X1 - (BODY_X1 + 0.75), 2))
    flat = [designed_min["lips"]["width"], designed_min["lips"]["height"]] + [v for k, v in designed_min.items() if not isinstance(v, dict)]
    ck["designed_walls_mm"] = designed_min
    if min(flat) < 1.6: fails.append(f"designed wall under 1.6: {designed_min}")
    area, regs = overhang(pm)
    ck["overhang_over_45deg"] = dict(area_mm2=area, regions=regs,
                                     note="lip undersides over the grooves (1.6 mm cantilevers off the groove walls, 0.4 mm above "
                                          "the groove floor), insertion-slot roofs (45 deg gables) and the jack teardrop sides "
                                          "are the only down faces; the slicer review reports support extrusion")
    bed = float(pm.area_faces[np.max(np.abs(pm.triangles[:, :, 2]), axis=1) <= .01].sum())
    ck["bed_contact_mm2"] = round(bed, 1)
    ck["print_height_mm"] = r3(pm.bounds[1, 2])
    # ---------------------------------------------------------------- wires and numbers
    tab_hole = lambda y: np.array([TAB_X0 + 1.6, y, SEAT_Z - K_JOG / 2])   # hole near the tab end, jog either way
    lug_end = X_FLANGE + J_ALL_L - 1.5
    wires = {}
    for s, lug in (("plus", "centre pin (+, schematic 1)"), ("minus", "sleeve (-, schematic 2)")):
        d = float(np.linalg.norm(tab_hole(PAD_Y[s]) - np.array([lug_end, 0.0, JACK_Z + J_LUG[lug]])))
        cut = 5 * math.ceil((d + 2 * WIRE_STRIP + WIRE_SLACK) / 5)
        wires[s] = dict(colour="red" if s == "plus" else "black", gauge="20 AWG", from_=f"5209 {s} tab (y {PAD_Y[s]:+.0f})",
                        to=f"PJ-005A {lug} lug", straight_mm=round(d, 1), cut_mm=cut, strip_each_end_mm=WIRE_STRIP)
    info = dict(
        release="BatteryDock-A1", frame="x forward, y left (guide frame), z above the floor with the robot seated, mm",
        z_seated_from_guide=Z_SEAT, printer_fits=PRINTER, features_built=FEATURES,
        bounds_world=tm.bounds.round(3).tolist(), volume_cm3=r3(dock.volume() / 1000),
        mass_g_solid_pla=round(dock.volume() / 1000 * PLA, 1), source_to_print=T.round(6).tolist(),
        print_pose="as seated: base plate on the bed, open tower top up; translation only",
        plus_side=dict(pad="contact_pad_plus at y +9 (battery-v2 build_v2.py bought_parts names the y > 0 pad 'plus'; its "
                           "features/contract give no polarity beyond that name)", dock="keystone_5209_plus in the y +9 groove",
                       charger="Sortfle 8.4 V 1 A, 5.5 x 2.1 plug, centre positive -> PJ-005A centre-pin lug -> + leaf"),
        fit=dict(groove_thickness=dict(class_="press", function="print_fit.clearance('press', 'horizontal')", gap_per_side=PRESS,
                                       groove_h=GROOVE_H, body_t=K_T,
                                       note="print_fit's press class is written for vertical pins; this horizontal slot is the "
                                            "smallest printable gap (two 0.2 layers) over the 0.30 bronze, and the lips' first "
                                            "layer sags onto the wings, which tightens it further"),
                 groove_width=dict(class_="locating", function="clearance('locating', 'horizontal')", gap_per_side=LOCATE_H,
                                   groove_w=GROOVE_W, wings=K_BODY_W),
                 leaf_opening=dict(class_="locating", function="clearance('locating', 'vertical')", gap_per_side=LOCATE_V,
                                   width=LEAF_OPEN_W, leaf=K_LEAF_W),
                 insertion_slot=dict(class_="loose", function="clearance('loose', 'horizontal')", gap_per_side=LOOSE_H,
                                     width=SLOT_W, z=SLOT_Z),
                 jack_hole=dict(class_="locating", function="clearance('locating', 'horizontal')", gap_per_side=LOCATE_H,
                                d=JACK_HOLE_D, bushing=J_BUSH_D, teardrop="tip +z")),
        groove=dict(x=[r3(X_STOP), r3(BODY_X1)], width=GROOVE_W, height=GROOVE_H, floor_z=SEAT_Z, closed_end_x=r3(BODY_X1),
                    open_end="rear, through the stop wall's insertion slot", leaf_opening_width=LEAF_OPEN_W,
                    centres_y=[PAD_Y["plus"], PAD_Y["minus"]]),
        leaf=dict(body_top_z=TOP, free_top_z=LEAF_TOP, compressed_at_nominal_seat=r3(LEAF_TOP - PAD_Z),
                  compressed_at_sim_seat=r3(LEAF_TOP - SEAT_SIM), keystone_working_travel="about 3 mm below free height (M65p36 AA mounting)",
                  sim_note=f"legsit.json real Brain sit: pads at {SEAT_SIM}, trunk pitch -1.9 deg"),
        block=dict(x=[X_STOP, BLOCK_X1], y=[-BLOCK_Y, BLOCK_Y], top_z=BLOCK_TOP, clearance_to_pads=r3(PAD_Z - BLOCK_TOP)),
        tower=dict(stop_face_x=X_STOP, gap_to_backpack_back=r3(BACK_X - X_STOP), x=[X_REAR, X_STOP], y=[-TOWER_Y, TOWER_Y],
                   top_z=TOWER_TOP, walls=dict(stop=FRONT_WALL_T, sides=TOWER_WALL, rear=REAR_WALL_T),
                   insertion_slots=dict(y_centres=[9.0, -9.0], width=SLOT_W, z=SLOT_Z, roof=f"45 deg gable from z {SLOT_EAVE:.1f}, apex z {SLOT_APEX:.1f}; {2 * LEAF_SLOT_HW:.1f} wide at z {SLOT_Z[1]}"),
                   screw_head_relief=dict(depth=RELIEF_D, z=[RELIEF_Z0, TOWER_TOP],
                                          why="the two low cap screw heads stand 1.6 proud of the backpack back face at z 18.0, y +-9"),
                   stop_face_band_z=[PLATE_T, RELIEF_Z0], backpack_contact_band_z=[PAD_Z, RELIEF_Z0]),
        jack=dict(part="Same Sky PJ-005A", axis="x", y=0.0, z=JACK_Z, hole_d=JACK_HOLE_D, rear_wall_x=[X_REAR, X_FLANGE],
                  flange_face_x=X_FLANGE, lug_end_x=X_FLANGE + J_ALL_L, lugs_z={k: JACK_Z + v for k, v in J_LUG.items()},
                  nut_outside="10.8 AF x 2.0 on 0.5 washer, rear (outside) face", plug="from behind (-x)",
                  bushing_left_for_nut=round(J_BUSH_L - REAR_WALL_T - J_WASH_T - J_NUT_T, 2)),
        contacts=dict(part="Keystone 5209", body_x=[r3(BODY_X0), r3(BODY_X1)], tab_x=[r3(TAB_X0), r3(BODY_X0)],
                      tab_ends_inside_tower=bool(TAB_X0 < X_WALL_IN)),
        wires=wires, checks=ck, fails=fails)
    info["assembly"] = [
        "Tools: soldering iron, 20 AWG red and black wire, wire stripper, small flat screwdriver, 11 mm (7/16 in) wrench or pliers.",
        f"Cut one red and one black 20 AWG wire, {wires['plus']['cut_mm']} mm and {wires['minus']['cut_mm']} mm, strip {WIRE_STRIP:.0f} mm at each end.",
        "Off the dock: solder the red wire through the solder-tab hole of one Keystone 5209 (this is the + contact) and the black wire to the other (- contact). Soldering here keeps the iron's heat away from the printed groove.",
        "Stand behind the dock (the tower is nearest you, the low block points away from you). The groove on your left is +, on your right is -.",
        "Lower the + contact into the open top of the tower, leaf up, leaf end pointing away from you, wire trailing toward you. Feed it through the left slot in the tower's front wall and push the flat body into the left groove until its far end stops against the closed end of the groove; push on the body's near edge with the flat screwdriver. The wings go under the two lips, the leaf stands up through the opening, the tab stays inside the tower.",
        "Do the same with the - contact in the right slot and groove.",
        "Check: each leaf springs back when pressed with a finger and does not rub the opening's sides; each body does not move when the leaf is pressed.",
        "Put the PJ-005A in from inside the tower: threaded bushing through the round hole in the rear wall, flange flat against the wall's inside face, lugs pointing toward the contacts, the single off-axis lug with the long reach (centre-pin lug) at the top.",
        "Outside: washer then nut on the bushing; tighten with the 11 mm wrench while holding the lugs straight.",
        "Solder the red wire to the centre-pin lug (top lug, 3.8 mm above the jack axis). Solder the black wire to the sleeve lug (the middle lug on the jack axis). Leave the bottom lug (shunt switch) empty.",
        "Check with a meter: charger plugged into the jack, the + leaf reads +8.4 V against the - leaf.",
        "Stick foam tape or Dual Lock under the base plate and put the dock where the robot sits.",
    ]
    (OUT / "build.json").write_text(json.dumps(info, indent=1, default=float, ensure_ascii=False).replace('"from_"', '"from"').replace('"class_"', '"class"'))
    fits = dict(printer=PRINTER, poses={"dock_base": [[[0, 0, 1], 0.0]]}, fits=[
        dict(id=f"groove-thickness y{y:+.0f}", type="pair", fit_class="press",
             female=dict(part="dock_base", d=GROOVE_H, axis=[1, 0, 0], teardrop=None, at_bed=False, chamfer=0.0),
             male=dict(part=None, d=K_T, axis=[1, 0, 0], teardrop=None, at_bed=False, chamfer=0.0)) for y in PAD_Y.values()] + [
        dict(id=f"groove-width y{y:+.0f}", type="pair", fit_class="locating",
             female=dict(part="dock_base", d=GROOVE_W, axis=[1, 0, 0], teardrop=None, at_bed=False, chamfer=0.0),
             male=dict(part=None, d=K_BODY_W, axis=[1, 0, 0], teardrop=None, at_bed=False, chamfer=0.0)) for y in PAD_Y.values()] + [
        dict(id=f"leaf-opening y{y:+.0f}", type="pair", fit_class="locating",
             female=dict(part="dock_base", d=LEAF_OPEN_W, axis=[0, 0, 1], teardrop=None, at_bed=False, chamfer=0.0),
             male=dict(part=None, d=K_LEAF_W, axis=[0, 0, 1], teardrop=None, at_bed=False, chamfer=0.0)) for y in PAD_Y.values()] + [
        dict(id="jack-hole", type="pair", fit_class="locating",
             female=dict(part="dock_base", d=JACK_HOLE_D, axis=[1, 0, 0], teardrop=[0, 0, 1], at_bed=False, chamfer=0.0),
             male=dict(part=None, d=J_BUSH_D, axis=[1, 0, 0], teardrop=None, at_bed=False, chamfer=0.0))])
    (HERE / "FITS.json").write_text(json.dumps(fits, indent=1))
    print(json.dumps(dict(volume_cm3=info["volume_cm3"], mass_g=info["mass_g_solid_pla"], bounds=info["bounds_world"],
                          block_top=ck["block_top_z"], wall=ck["wall_check"], overlaps=ov, robot=ck["dock_vs_robot_overlap_mm3"],
                          robot_gap=ck["dock_vs_robot_min_gap_mm"], leaf=leaf_c, overhang=area, wires=wires, fails=fails), indent=1, default=float))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
