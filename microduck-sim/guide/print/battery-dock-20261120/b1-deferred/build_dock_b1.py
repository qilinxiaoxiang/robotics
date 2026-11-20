"""MicroDuck battery backpack rev B charging dock base, release BatteryDock-B1: one printed Orange part, flat on the bed,
with mechanical docking guidance (side guide rails, a forward datum and a rear lead-in) from the funnel concept Shawn
approved on 2026-11-20 ("导轨倒是可以 ... 看看能不能把它对准坐下去", then "出 CAD"; DESIGN-CONTRACT.json).

    DEFERRED (Shawn 2026-11-20: "我们是不是能先做个更大电池的背包 对准以后再说 充电器就用那个白色头 反正是翘在外面的
    是不是简单一点"): not released, not sliced, not in the guide; BatteryDock-A1 (../build_dock.py) stays what the guide shows.
    Mac mini, from ..:  zsh mini_sync.sh push && zsh mini_sync.sh run 'cd b1-deferred && $PY build_dock_b1.py'
    then rsync mac-mini:code/robotics/microduck-sim/guide/print/battery-dock-20261120/b1-deferred/build/ back here.
    Outputs stay in this folder (build/, FITS.json), apart from A1's.

Supersedes BatteryDock-A1 (git dd7fa204 and earlier hold its build_dock.py): in the real Brain sit the A1 leaf tip lay
behind the pad in all 46 sim runs, even with the robot exactly centred (funnel-concept/checks/results.json).

Frame: x forward, y left (guide/backpack frame), z = height above the floor with the robot seated, mm; the A1 frame (the
robot's backpack back face at x -75.55, the stop face 0.95 behind it). The concept sheet and the funnel sims draw in the
sim frame D, where the whole dock sits 3.0 mm further forward: D x = this x + 3.0. The backpack STLs of
../battery-v2-cad-20261120 are in the guide frame standing (pad faces at z -46); seated they sit at z 10.9, so
z_seated = z_guide + 56.9. The real Brain sit puts the pads at 10.2 with 1.9 deg trunk pitch and pushes the backpack
against the stop face (funnel-concept); build.json reports the checks at the nominal seat and against the stop.

Numbered needs (each feature in features.json answers one):
  N1 a seated robot's two pads must each meet one sprung contact, + under the y +9 pad, - under the y -9 pad
  N2 the contacts must be held as Keystone intends (5209 body pressed into a housing groove), with nothing printed that bends
  N3 the robot must be stopped in x so its pads land over the leaves
  N4 the charger plug must enter a panel jack that is wired to the two contacts with short soldered wires
  N5 the dock must stay where it is put (no printed feature: foam tape or Dual Lock under the plate)
  N6 a robot that sits down off to one side must be pushed sideways until each pad is over its own leaf (F1 rails)
  N7 a robot that sits down too far back must slide forward onto the stop, never hang on the dock (F3 rear lead-in)
  N8 the guidance must never touch the legs or feet in stand, sit and stand-up (F4 rail extent)

Fits from cad-practice/print_fit.py (H2S, as the backpack CAD): every number below names its class. No snaps, hooks or
flexures; the only sprung parts are the bronze leaves. The rails and the lead-in are solid, wide, upward-facing slopes.

Writes build/dock_base-world.stl, build/dock_base-print.stl, build/parts/*-world.stl (bought-part envelopes, seated
positions), build/features/*-world.stl (feature solids for DESIGN-CONTRACT.json), build/collision/*.stl (the convex
pieces whose union is the dock's outside, for the sit sim), build/build.json (geometry, checks, assembly), FITS.json;
exit 1 on a failed check.
"""
import json, math, sys
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
MD = HERE.parents[3]                                            # microduck-sim
BV2 = MD / "guide/print/battery-v2-cad-20261120"
PIPE = MD / "build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009"
POSE_PTS = HERE.parent / "funnel-concept/checks/pose_points.npz"       # robot leg envelope in D over stand, sit and rise
OUT = HERE / "build"
for d in ("parts", "features", "collision"): (OUT / d).mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(MD.parent / "cad-practice")); import print_fit as F  # noqa: E402
sys.path.insert(0, str(PIPE)); import wall_check as W  # noqa: E402
RELEASE = "BatteryDock-B1"
PRINTER = "H2S"
PLA = 1.24                                                      # g/cm3
D_SHIFT = 3.0                                                   # sim frame D x = this frame's x + 3.0

# ------------------------------------------------------------------ robot (battery-v2 rev B, seated)
Z_SEAT = 10.9 - (-46.0)                                         # guide -> seated z offset (backpack bottom 10.9)
BACK_X = -75.55                                                 # backpack back face (cap outer face)
SEAT_SIM = 10.2                                                 # pads seated in the sim Brain sit (legsit.json)
TIER_Y = (-25.3, 21.8)                                          # backpack lower tier y, seated z 10.9..42 (frame + cap STLs)
LOW_CAP_SCREWS = [(9.0, -46.0 + 7.1 + Z_SEAT), (-9.0, -46.0 + 7.1 + Z_SEAT)]   # (y, z seated) = (+-9, 18.0)
HEAD = (4.0, 1.6)                                               # M2 pan head ISO 7045 dk x k, proud of the cap face
HEAD_SEAT_D = F.HEAD_SEAT["M2"][0]                              # 4.6: pan or button head envelope (print_fit HEAD_SEAT)
# robot poses for the checks (dx, dz): nominal = 0.95 gap to the stop; against the stop; against it at the sim's seat height
# (0.94 rather than 0.95: a 0.01 gap keeps the zero-volume touch of the back face on the stop face out of the overlap sum)
POSES = {"nominal seat": (0.0, 0.0), "against the stop": (-0.94, 0.0), "against the stop, sim seat height": (-0.94, SEAT_SIM - 10.9)}

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
X_STOP = -76.5                                     # F2 stop face (sheet D -73.5), 0.95 behind the backpack back face
LEAF_DX = 2.5                                      # F2: contact bodies 2.5 forward of the stop face (sim seat is nose-up)
FRONT_WALL_T = 11.1                                # 9.5 of F3 slope to the tower top, then 1.6 flat at z 22 on solid wall
TOWER_Y, TOWER_WALL, TOWER_TOP = 17.0, 2.0, 22.0
REAR_WALL_T = 2.5                                  # PJ-005A panel limit about 3.2 (5.7 - 2.0 nut - 0.5 washer)
JACK_Z = 10.0                                      # nut corner 3.76 above the floor, flange 4.6 above the plate
LUG_GAP = 2.3                                      # lug ends to the stop wall's inner face (soldering iron room)
BLOCK_Y = 16.5
BLOCK_X1 = -57.5                                   # block front face: 1.75 wall in front of the leaf opening
PLATE_X1 = -55.0                                   # plate front edge (A1's, the edge the funnel sims ran with)
PLATE_Y = 20.0
WIRE_STRIP, WIRE_SLACK = 3.0, 10.0                 # 20 AWG: strip at each end, slack for the iron
# F3 rear lead-in: 45 deg plane rising rearward from the stop face's top edge (x X_STOP, z Z_LEAD). The concept started it
# at z 14.6; the two low cap screw heads (1.6 proud at z 18.0, not in the sim's backpack hull) would rest on that plane
# with the robot against the stop, so it starts at 12.5 (checks: screw_heads_vs_lead_in).
Z_LEAD, LEAD_DEG = 12.5, 45.0
# The stop wall is longer than the slope (9.5 + 1.6): a 3.2 wall left either a 45 deg knife edge at its inner face (0.4 mm,
# wall check) or, capped with a 1.6 mm flat at z 14.1, a ledge the robot hung on in the first B1 sit recheck (start 6 mm
# back: pads at z 13.8). Now the slope runs from the stop face's top edge to the tower top and the 1.6 flat sits at the
# tower top's own height (z 22), so the centre post between the slots ends square, not in a knife edge.
LEAD_RUN = (TOWER_TOP - Z_LEAD) / math.tan(math.radians(LEAD_DEG))                # 9.5
assert FRONT_WALL_T - LEAD_RUN >= 1.6 - 1e-9
# F1 side guide rails (concept R1): faces 3.0 outside the lower tier, vertical to 12.5, 60 deg lead-in to 24, 2.5 flat top
RAIL_PLAY, RAIL_ZV, RAIL_ZTOP, RAIL_DEG, RAIL_TOP_W = 3.0, 12.5, 24.0, 60.0, 2.5
RAIL_X = (-80.0, -62.0)                            # F4: sheet D -77..-59; ends 11 mm behind the stand-up's foot (D x -51)
RAIL_RUN = (RAIL_ZTOP - RAIL_ZV) / math.tan(math.radians(RAIL_DEG))      # 6.64
RAIL_IN = {"left": TIER_Y[1] + RAIL_PLAY, "right": TIER_Y[0] - RAIL_PLAY}  # +24.8 / -28.3
RAIL_OUT = {"left": RAIL_IN["left"] + RAIL_RUN + RAIL_TOP_W, "right": RAIL_IN["right"] - RAIL_RUN - RAIL_TOP_W}


def box(lo, hi):
    lo, hi = np.array(lo, float), np.array(hi, float)
    return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
def U(ms): return mf.Manifold.batch_boolean(list(ms), mf.OpType.Add)
def to_tm(M):
    g = M.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=True)
def load_mf(p, dx=0.0, dz=0.0):
    m = trimesh.load(p, force="mesh", process=True); m.merge_vertices(); m.apply_translation((dx, 0, dz))
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def cyl_x(y, z, d, x0, x1, n=64):
    return mf.Manifold.cylinder(x1 - x0, d / 2, d / 2, n).rotate((0, 90, 0)).translate((x0, y, z))
def cyl_z(x, y, r, z0, z1, n=48):
    return mf.Manifold.cylinder(z1 - z0, r, r, n).translate((x, y, z0))
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
def prism_x(yz, x0, x1):
    """(y, z) polygon extruded along x from x0 to x1 (convex if the polygon is)"""
    pts = [(x, y, z) for x in (x0, x1) for (y, z) in yz]
    return hull(pts)
def prism_y(xz, y0, y1):
    return hull([(x, y, z) for y in (y0, y1) for (x, z) in xz])


# ------------------------------------------------------------------ robot inputs
def pads(dx=0.0, dz=0.0):
    return {s: load_mf(BV2 / f"build/parts/contact_pad_{s}-world.stl", dx, Z_SEAT + dz) for s in ("plus", "minus")}


PADS = pads()
PB = {s: np.array(M.bounding_box()).reshape(2, 3) for s, M in PADS.items()}
PAD_CX = float((PB["plus"][0, 0] + PB["plus"][1, 0]) / 2)                         # -69.5
PAD_Y = {s: float((b[0, 1] + b[1, 1]) / 2) for s, b in PB.items()}                # +9 / -9
PAD_Z = float(PB["plus"][0, 2])                                                    # 10.9
assert PAD_Y["plus"] > 0 and abs(PAD_Z - 10.9) < 1e-3, (PAD_Y, PAD_Z)

BODY_X0 = X_STOP + LEAF_DX                                                         # -74.0
BODY_X1 = BODY_X0 + K_BODY_L                                                       # -60.0 (groove closed end)
TOP = SEAT_Z + K_T                                                                 # 6.3 body top face
LEAF_TOP = TOP + K_FREE                                                            # 13.9
SLOT_Z = (round(SEAT_Z - K_JOG - 0.6, 1), round(LEAF_TOP + 0.7, 1))                # 3.8 .. 14.6 (tab jog down / leaf up)
SLOT_W = round(K_BODY_W + 2 * LOOSE_H, 2)                                          # 11.0
X_WALL_IN = X_STOP - FRONT_WALL_T                                                  # -79.7
X_FLANGE = X_WALL_IN - LUG_GAP - J_ALL_L                                           # -97.5 (rear wall inner face)
X_REAR = X_FLANGE - REAR_WALL_T                                                    # -100.0
TAB_X0 = BODY_X0 - K_TAB_L                                                         # -81.0
assert BLOCK_X1 - (BODY_X1 + 0.75) >= 1.6
def lead_z(x): return Z_LEAD + (X_STOP - x) * math.tan(math.radians(LEAD_DEG))     # F3 plane height at x (x <= X_STOP)


def leaf(y, top_z):
    """Leaf envelope: 0.3 slab from the root at the body's front end up to its tip at top_z (slab 0.4 incl. the bend)."""
    run = math.sqrt(K_LEAF_L ** 2 - (top_z - TOP) ** 2)
    w = K_LEAF_W / 2; x_r = BODY_X1; x_t = BODY_X1 - run
    pts = []
    for yy in (y - w, y + w):
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
    """Insertion slot through the stop wall: SLOT_W wide from SLOT_Z[0], open to the top. A1 roofed it with a 45 deg
    gable from z 13.1; in B1 the lead-in plane (z 12.5 at the stop face, 15.7 at the wall's inner face) runs below that
    eave, and the gable's remains between the plane and the roof were 0.2-0.9 mm slivers (wall check, first B1 build).
    The slot runs on into the block to 0.6 past the body's rear end, because the body now sits 2.5 forward of the stop
    face and its solder tab (jogged 1.6 either way) lies in the block's first 2.5 mm."""
    hw = SLOT_W / 2
    return box((X_WALL_IN - 0.5, y - hw, SLOT_Z[0]), (BODY_X0 + 0.6, y + hw, TOWER_TOP + 5))


def rail(side):
    """F1: (y, z) section extruded along RAIL_X: vertical guide face to RAIL_ZV, RAIL_DEG lead-in to RAIL_ZTOP, flat top,
    vertical outer face, standing on the floor (merges with the plate)."""
    s = 1 if side == "left" else -1
    yi = RAIL_IN[side]
    yz = [(yi, 0.0), (yi, RAIL_ZV), (yi + s * RAIL_RUN, RAIL_ZTOP), (RAIL_OUT[side], RAIL_ZTOP), (RAIL_OUT[side], 0.0)]
    return prism_x(yz, *RAIL_X)


FEATURES = []
def feat(i):
    if i not in FEATURES: FEATURES.append(i)


def pieces():
    """The convex positive solids of the dock, named. Their union minus CUTS is the part; the sit sim collides with them."""
    P = {
        "plate": box((X_REAR, -PLATE_Y, 0), (PLATE_X1, PLATE_Y, PLATE_T)),
        "plate_rail_bridge": box((RAIL_X[0], RAIL_OUT["right"], 0), (RAIL_X[1], RAIL_OUT["left"], PLATE_T)),
        "block": box((X_STOP - 0.01, -BLOCK_Y, 0), (BLOCK_X1, BLOCK_Y, BLOCK_TOP)),
        # stop wall: section x X_WALL_IN..X_STOP, top the F3 plane from the stop face's top edge to the tower top
        "stop_wall": prism_y([(X_WALL_IN, 0), (X_STOP, 0), (X_STOP, Z_LEAD), (X_STOP - LEAD_RUN, TOWER_TOP), (X_WALL_IN, TOWER_TOP)],
                             -TOWER_Y, TOWER_Y),
        "rail_left": rail("left"), "rail_right": rail("right"),
        "tower_back": box((X_REAR, -TOWER_Y, 0), (X_FLANGE, TOWER_Y, TOWER_TOP)),
    }
    xk = X_STOP - LEAD_RUN                                                          # -86.0: lead-in meets the tower top
    P["tower_side_left"] = box((X_FLANGE, TOWER_Y - TOWER_WALL, 0), (X_WALL_IN + 0.01, TOWER_Y, TOWER_TOP))
    P["tower_side_right"] = box((X_FLANGE, -TOWER_Y, 0), (X_WALL_IN + 0.01, -TOWER_Y + TOWER_WALL, TOWER_TOP))
    return P, xk


def build():
    P, xk = pieces()
    feat("D1-base-plate"); feat("D2-contact-block"); feat("D3-stop-wall"); feat("D4-tower")
    feat("F1-side-guide-rails"); feat("F2-forward-datum"); feat("F3-rear-lead-in"); feat("F4-rail-extent")
    dock = U(P.values())
    cuts = []
    for y in PAD_Y.values():
        gw = GROOVE_W / 2
        cuts.append(box((X_STOP - 0.5, y - gw, SEAT_Z), (BODY_X1, y + gw, SEAT_Z + GROOVE_H)))       # closed front at -60.0
        cuts.append(box((X_STOP - 0.5, y - LEAF_OPEN_W / 2, SEAT_Z + GROOVE_H - 0.01),
                        (BODY_X1 + 0.75, y + LEAF_OPEN_W / 2, BLOCK_TOP + 1)))                      # leaf opening, 0.75 past the root
        cuts.append(slot(y))
    feat("D2-grooves"); feat("D2-leaf-openings"); feat("D3-insertion-slots")
    cuts.append(teardrop_x(0, JACK_Z, JACK_HOLE_D, X_REAR - 0.5, X_FLANGE + 0.5)); feat("D4-jack-hole")
    feat("D4-tower-open-top")                     # the pieces leave the interior x X_FLANGE..X_WALL_IN, |y| < 15 open
    dock = dock - U(cuts)
    dock = U([b for b in dock.decompose() if b.volume() > 1.0])
    return dock, P, U(cuts), xk


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


def probe_rail(tm, side):
    """Ray-cast the built rail's guide surface across y at several heights in the middle of the rail; returns the hit y
    and the y the approved section predicts (vertical face to RAIL_ZV, RAIL_DEG slope to RAIL_ZTOP)."""
    s = 1 if side == "left" else -1
    out = []
    x = (RAIL_X[0] + RAIL_X[1]) / 2
    for z in (3.0, 6.0, 9.0, 12.0, 14.0, 17.0, 20.0, 23.0):          # above the plate (z 2), from the open gap at |y| 20
        o = np.array([[x, s * 20.0, z]]); d = np.array([[0.0, s, 0.0]])
        loc, _, _ = tm.ray.intersects_location(o, d)
        ys = [p[1] for p in loc if s * p[1] > 20]
        hit = min(ys, key=lambda v: s * v) if ys else None
        want = RAIL_IN[side] + (0 if z <= RAIL_ZV else s * (z - RAIL_ZV) / math.tan(math.radians(RAIL_DEG)))
        out.append(dict(z=z, hit_y=None if hit is None else r3(hit), approved_y=r3(want),
                        ok=hit is not None and abs(hit - want) < 0.02))
    return out


def probe_lead(tm):
    """Ray-cast down on the stop wall and tower side walls: the top must follow the 45 deg plane from (X_STOP, Z_LEAD)."""
    out = []
    for (y, x) in ((0.0, X_STOP - 0.3), (0.0, X_STOP - 1.5), (16.0, X_STOP - 1.0), (16.0, -82.0), (16.0, -85.5), (-16.0, -84.0)):
        loc, _, _ = tm.ray.intersects_location(np.array([[x, y, 60.0]]), np.array([[0, 0, -1.0]]))
        hit = max(p[2] for p in loc) if len(loc) else None
        out.append(dict(x=x, y=y, top_z=None if hit is None else r3(hit), plane_z=r3(lead_z(x)),
                        ok=hit is not None and abs(hit - lead_z(x)) < 0.02))
    return out


def main():
    dock, P, CUTS, xk = build()
    fails = []
    parts = {"keystone_5209_plus": contact(PAD_Y["plus"]), "keystone_5209_minus": contact(PAD_Y["minus"]), "pj005a": jack()}
    tm = to_tm(dock); tm.export(OUT / "dock_base-world.stl")
    off = -tm.bounds[0].copy(); off[2] = 0.0                      # print pose: as seated, plate on the bed (z 0 = bed)
    pm = tm.copy(); pm.apply_translation(off); pm.export(OUT / "dock_base-print.stl")
    T = np.eye(4); T[:3, 3] = off
    for n, M in parts.items(): to_tm(M).export(OUT / "parts" / f"{n}-world.stl")
    # feature solids (the built part cut to each feature's region) for DESIGN-CONTRACT.json
    feat_solids = {"rail_left": P["rail_left"] ^ dock, "rail_right": P["rail_right"] ^ dock, "stop_wall": P["stop_wall"] ^ dock,
                   "rear_lead_in": (P["stop_wall"] + P["tower_side_left"] + P["tower_side_right"]) ^ dock
                   ^ box((xk - 0.01, -TOWER_Y, Z_LEAD - 3.2), (X_STOP + 0.01, TOWER_Y, TOWER_TOP + 0.01))}
    for n, M in feat_solids.items(): to_tm(M).export(OUT / "features" / f"{n}-world.stl")
    for n, M in P.items(): to_tm(M).export(OUT / "collision" / f"{n}.stl")
    # ---------------------------------------------------------------- checks
    ck = {}
    ck["solid"] = dict(bodies=len(dock.decompose()), watertight=bool(tm.is_watertight), status=str(dock.status()),
                       winding_consistent=bool(tm.is_winding_consistent))
    if ck["solid"]["bodies"] != 1 or not tm.is_watertight: fails.append(f"dock not one closed body {ck['solid']}")
    pieces_u = U(P.values())
    ck["collision_pieces"] = dict(names=list(P), part_outside_pieces_mm3=r3((dock - pieces_u).volume()),
                                  pieces_minus_part_mm3=r3((pieces_u - dock).volume()), cuts_mm3=r3((pieces_u ^ CUTS).volume()),
                                  note="the sit sim collides with these convex pieces; what they add over the part is only "
                                       "the cuts (grooves, leaf openings, insertion slots, jack hole), none of them on a "
                                       "surface the backpack can reach except the slot mouths in the stop face")
    if ck["collision_pieces"]["part_outside_pieces_mm3"] > 0.01: fails.append("part has material outside the collision pieces")
    if abs(ck["collision_pieces"]["pieces_minus_part_mm3"] - ck["collision_pieces"]["cuts_mm3"]) > 0.5:
        fails.append(f"collision pieces differ from the part by more than the cuts {ck['collision_pieces']}")
    ov = {n: r3((dock ^ M).volume()) for n, M in parts.items()}
    ck["dock_vs_parts_overlap_mm3"] = ov
    for n, v in ov.items():
        if v > 0.01: fails.append(f"dock | {n} overlap {v}")
    ck["dock_vs_parts_min_gap_mm"] = {n: r3(dock.min_gap(M, 2.0)) for n, M in parts.items()}
    ck["designed_contacts"] = ("body front end bears on the groove's closed end (x -60.0); jack flange face on the rear "
                               "wall's inner face; washer on its outer face; zero-volume touches, not overlaps")
    # robot: every backpack STL (frame, cap, each bought part incl. the XIAO USB-C plug) and the two low cap screw heads,
    # in three seated poses
    robot_files = {"backpack frame": BV2 / "build/battery_v2_frame-world.stl", "backpack cap": BV2 / "build/battery_v2_cap-world.stl"}
    for f in sorted((BV2 / "build/parts").glob("*-world.stl")):
        robot_files[f.name.replace("-world.stl", "")] = f
    ck["robot"] = {}
    for pose, (dx, dz) in POSES.items():
        rob = {n: load_mf(f, dx, Z_SEAT + dz) for n, f in robot_files.items()}
        for (y, z) in LOW_CAP_SCREWS:
            rob[f"low cap screw head {'left' if y > 0 else 'right'} (seat envelope {HEAD_SEAT_D})"] = \
                cyl_x(y, z + dz, HEAD_SEAT_D, BACK_X + dx - HEAD[1], BACK_X + dx + 0.01)
        ovr = {n: r3((dock ^ M).volume()) for n, M in rob.items()}
        gap = {n: r3(dock.min_gap(M, 6.0)) for n, M in rob.items() if n.startswith(("backpack", "low cap", "contact_pad", "XIAO_USB"))}
        ck["robot"][pose] = dict(robot_dx_dz=[dx, dz], overlap_mm3={n: v for n, v in ovr.items() if v > 0}, min_gap_mm=gap)
        for n, v in ovr.items():
            if v > 0.01: fails.append(f"{pose}: dock | {n} overlap {v}")
    heads = {pose: {n: v for n, v in c["min_gap_mm"].items() if n.startswith("low cap")} for pose, c in ck["robot"].items()}
    dxs, dzs = POSES["against the stop, sim seat height"]
    for dy in (-RAIL_PLAY, RAIL_PLAY):                    # the rails leave the seated backpack +-3 mm of side play
        heads[f"against the stop, sim seat height, y {dy:+.0f}"] = {
            f"low cap screw head {'left' if y > 0 else 'right'}": r3(dock.min_gap(
                cyl_x(y + dy, z + dzs, HEAD_SEAT_D, BACK_X + dxs - HEAD[1], BACK_X + dxs + 0.01), 6.0)) for (y, z) in LOW_CAP_SCREWS}
    ck["screw_heads_vs_lead_in"] = dict(gaps_mm=heads, lead_in_start_z=Z_LEAD,
                                        note="A1 had a 1.5 mm relief across the stop face above z 14.6; F3 replaces it, so "
                                             "the heads must clear the lead-in plane with the backpack against the stop")
    for pose, g in heads.items():
        for n, v in g.items():
            if v < 0.3: fails.append(f"screw head {n} {pose}: gap {v} < 0.3")
    # leaves under the pads
    leaf_c = {}
    for s in ("plus", "minus"):
        lc, xt = leaf(PAD_Y[s], PAD_Z)
        lf, xf = leaf(PAD_Y[s], LEAF_TOP)
        r = dict(dock_overlap_mm3=r3((dock ^ lc).volume()), tip_x_at_10_9=r3(xt), free_tip_x=r3(xf))
        for pose, (dx, dz) in POSES.items():
            x0, x1 = PB[s][0, 0] + dx, PB[s][1, 0] + dx
            zf = PAD_Z + dz
            _, xtp = leaf(PAD_Y[s], zf)
            r[pose] = dict(pad_x=[r3(x0), r3(x1)], pad_z=r3(zf), tip_x=r3(xtp), margin=r3(min(xtp - x0, x1 - xtp)),
                           compression=r3(LEAF_TOP - zf))
            if r[pose]["margin"] < 0.5: fails.append(f"leaf {s} {pose}: tip margin {r[pose]['margin']}")
        r["free_leaf_vs_pad_overlap_mm3 (designed: the seated pad presses the leaf down)"] = r3((lf ^ PADS[s]).volume())
        if r["dock_overlap_mm3"] > 0.01: fails.append(f"compressed leaf {s} overlaps the dock")
        leaf_c[s] = r
    ck["leaf_under_pad"] = leaf_c
    top_under_pad = float(max(v[2] for v in tm.vertices if PB["minus"][0, 1] - 1 <= v[1] <= PB["plus"][1, 1] + 1 and X_STOP + 0.01 <= v[0] <= BLOCK_X1))
    ck["block_top_z"] = r3(top_under_pad)
    if top_under_pad > 8.5: fails.append(f"block top {top_under_pad} > 8.5")
    # F1 / F3 shape as approved
    ck["rail_section_probe"] = {s: probe_rail(tm, s) for s in ("left", "right")}
    ck["lead_in_probe"] = probe_lead(tm)
    for s, rows in ck["rail_section_probe"].items():
        if not all(r["ok"] for r in rows): fails.append(f"rail {s} section differs from the approved section {rows}")
    if not all(r["ok"] for r in ck["lead_in_probe"]): fails.append(f"lead-in differs from the 45 deg plane {ck['lead_in_probe']}")
    # F4: legs and feet in stand, sit and stand-up (sim leg envelope from the nominal funnel run, D frame -> this frame)
    if POSE_PTS.exists():
        Z = np.load(POSE_PTS)
        res = {}
        lo, hi = tm.bounds[0] - 12, tm.bounds[1] + 12
        pq = trimesh.proximity.ProximityQuery(tm)
        for k in ("leg_envelope", "stand_legs", "seated_legs"):
            pts = Z[k] - np.array([D_SHIFT, 0, 0])
            pts = pts[np.all((pts > lo) & (pts < hi), axis=1)]
            if len(pts) == 0:
                res[k] = dict(points_near=0, min_mm=None); continue
            if len(pts) > 60000: pts = pts[:: int(math.ceil(len(pts) / 60000))]
            sd = -pq.signed_distance(pts)                         # trimesh: positive inside -> flip: positive outside
            i = int(np.argmin(sd))
            res[k] = dict(points_near=int(len(pts)), min_mm=r3(sd[i]), at=pts[i].round(1).tolist())
            if sd[i] <= 0: fails.append(f"legs ({k}) touch the dock at {pts[i].round(1).tolist()}: {sd[i]:.2f}")
        ck["legs_vs_dock"] = dict(source=str(POSE_PTS.relative_to(HERE.parent)), frame_shift_x=-D_SHIFT, by_set=res,
                                  note="the envelope is every leg mesh vertex over stand, sit and stand-up (trunk to 100 mm) "
                                       "of the nominal funnel sim; the B1 sit recheck measures clearance per run")
    else:
        ck["legs_vs_dock"] = "pose_points.npz missing (run funnel-concept/probe_pose_points.py on the Mac mini)"
        fails.append("legs_vs_dock not checked")
    # soldering iron access: a 3.5 mm radius iron barrel straight down onto each solder joint, and tilted 30 deg back
    iron = {}
    tab_hole = lambda y: np.array([TAB_X0 + 1.6, y, SEAT_Z - K_JOG / 2])
    lug_end = X_FLANGE + J_ALL_L - 1.5
    joints = {"centre-pin lug": (lug_end, 0.0, JACK_Z + 3.8), "sleeve lug": (lug_end, 0.0, JACK_Z)}
    for name, (x, y, z) in joints.items():
        for tilt in (0, 30):
            L = 80.0
            c = mf.Manifold.cylinder(L, 3.5, 3.5, 32).translate((0, 0, 1.5))
            c = c.rotate((0, -tilt, 0)).translate((x, y, z))       # leaning toward -x (rear) when tilted
            iron[f"{name}, {tilt} deg"] = r3((c ^ dock).volume())
    ck["soldering_iron_access_mm3_in_dock"] = dict(joints=iron, tabs="the 5209 tabs are soldered off the dock (assembly step 3)")
    if min(v for k, v in iron.items()) > 0.01 and all(v > 0.01 for v in iron.values()):
        fails.append(f"no clear iron approach to the jack lugs {iron}")
    for k in ("centre-pin lug, 0 deg", "sleeve lug, 0 deg"):
        if iron[k] > 0.01: fails.append(f"iron straight down blocked at {k}: {iron[k]} mm3")
    # walls and print
    wc = W.check(pm, (), "dock_base")
    ck["wall_check"] = dict(passed=wc["passed"], min_wall_mm=W.MIN_WALL_MM, min_smoothed_mm=wc["minSmoothedMm"],
                            fail_regions=[{k: g[k] for k in ("bbox", "minMm", "areaMm2", "status")} for g in wc["regions"] if g["status"] == "FAIL"],
                            small_thin_patches=wc["smallThinPatches"])
    if not wc["passed"]: fails.append(f"wall check: {wc['failures']}")
    designed_min = dict(base_plate=PLATE_T, block_side_walls=round(BLOCK_Y - (PAD_Y['plus'] + GROOVE_W / 2), 2),
                        block_centre_web=round(2 * (PAD_Y['plus'] - GROOVE_W / 2), 2),
                        lips=dict(width=round((GROOVE_W - LEAF_OPEN_W) / 2, 2), height=round(BLOCK_TOP - SEAT_Z - GROOVE_H, 2)),
                        groove_floor_above_plate=round(SEAT_Z - PLATE_T, 2), stop_wall=FRONT_WALL_T,
                        stop_wall_centre_post=round(2 * (PAD_Y['plus'] - SLOT_W / 2), 2),
                        stop_wall_outer_strip=round(TOWER_Y - (PAD_Y['plus'] + SLOT_W / 2), 2),
                        side_walls=TOWER_WALL, rear_wall=REAR_WALL_T, block_front_end=round(BLOCK_X1 - (BODY_X1 + 0.75), 2),
                        rail_top_flat=RAIL_TOP_W, rail_base_width=round(RAIL_RUN + RAIL_TOP_W, 2))
    flat = [designed_min["lips"]["width"], designed_min["lips"]["height"]] + [v for k, v in designed_min.items() if not isinstance(v, dict)]
    ck["designed_walls_mm"] = designed_min
    if min(flat) < 1.6: fails.append(f"designed wall under 1.6: {designed_min}")
    area, regs = overhang(pm)
    ck["overhang_over_45deg"] = dict(area_mm2=area, regions=regs,
                                     note="lip undersides over the grooves, the remaining insertion-slot gables and the jack "
                                          "teardrop sides; the rails and the lead-in face upward")
    bed = float(pm.area_faces[np.max(np.abs(pm.triangles[:, :, 2]), axis=1) <= .01].sum())
    ck["bed_contact_mm2"] = round(bed, 1)
    ck["print_height_mm"] = r3(pm.bounds[1, 2])
    ck["flexures_snaps"] = "none: every feature is a solid prism, wall or slope; the only sprung parts are the bronze leaves"
    # ---------------------------------------------------------------- wires and numbers
    wires = {}
    for s, lug in (("plus", "centre pin (+, schematic 1)"), ("minus", "sleeve (-, schematic 2)")):
        d = float(np.linalg.norm(tab_hole(PAD_Y[s]) - np.array([lug_end, 0.0, JACK_Z + J_LUG[lug]])))
        cut = 5 * math.ceil((d + 2 * WIRE_STRIP + WIRE_SLACK) / 5)
        wires[s] = dict(colour="red" if s == "plus" else "black", gauge="20 AWG", from_=f"5209 {s} tab (y {PAD_Y[s]:+.0f})",
                        to=f"PJ-005A {lug} lug", straight_mm=round(d, 1), cut_mm=cut, strip_each_end_mm=WIRE_STRIP)
    info = dict(
        release=RELEASE, supersedes=dict(release="BatteryDock-A1", git="dd7fa204",
                                         why="in the real Brain sit the leaf tip lay behind the pad in all 46 sim runs, even "
                                             "centred (funnel-concept/checks/results.json)"),
        frame="x forward, y left (guide frame), z above the floor with the robot seated, mm; the A1 frame. Sim frame D x = x + 3.0",
        z_seated_from_guide=Z_SEAT, printer_fits=PRINTER, features_built=FEATURES,
        bounds_world=tm.bounds.round(3).tolist(), volume_cm3=r3(dock.volume() / 1000),
        mass_g_solid_pla=round(dock.volume() / 1000 * PLA, 1), source_to_print=T.round(6).tolist(),
        print_pose="as seated: base plate on the bed, open tower top up, rail slopes up; translation only",
        plus_side=dict(pad="contact_pad_plus at y +9 (battery-v2 build_v2.py names the y > 0 pad 'plus')",
                       dock="keystone_5209_plus in the y +9 groove",
                       charger="Sortfle 8.4 V 1 A, 5.5 x 2.1 plug, centre positive -> PJ-005A centre-pin lug -> + leaf"),
        fit=dict(groove_thickness=dict(class_="press", function="print_fit.clearance('press', 'horizontal')", gap_per_side=PRESS,
                                       groove_h=GROOVE_H, body_t=K_T),
                 groove_width=dict(class_="locating", function="clearance('locating', 'horizontal')", gap_per_side=LOCATE_H,
                                   groove_w=GROOVE_W, wings=K_BODY_W),
                 leaf_opening=dict(class_="locating", function="clearance('locating', 'vertical')", gap_per_side=LOCATE_V,
                                   width=LEAF_OPEN_W, leaf=K_LEAF_W),
                 insertion_slot=dict(class_="loose", function="clearance('loose', 'horizontal')", gap_per_side=LOOSE_H,
                                     width=SLOT_W, z=SLOT_Z),
                 jack_hole=dict(class_="locating", function="clearance('locating', 'horizontal')", gap_per_side=LOCATE_H,
                                d=JACK_HOLE_D, bushing=J_BUSH_D, teardrop="tip +z")),
        rails=dict(x=list(RAIL_X), x_in_sim_frame_D=[RAIL_X[0] + D_SHIFT, RAIL_X[1] + D_SHIFT],
                   guide_faces_y=RAIL_IN, outer_faces_y={k: r3(v) for k, v in RAIL_OUT.items()}, play_per_side=RAIL_PLAY,
                   vertical_face_to_z=RAIL_ZV, lead_in_deg=RAIL_DEG, top_z=RAIL_ZTOP, top_flat=RAIL_TOP_W,
                   gap_between_guide_faces=r3(RAIL_IN["left"] - RAIL_IN["right"]), backpack_tier_y=list(TIER_Y)),
        rear_lead_in=dict(deg=LEAD_DEG, from_=dict(x=X_STOP, z=Z_LEAD), meets_tower_top_x=r3(xk), concept_start_z=14.6,
                          why_lower="screw heads (1.6 proud at z 18.0) would rest on a plane from 14.6 with the robot against the stop"),
        groove=dict(x=[r3(X_STOP), r3(BODY_X1)], width=GROOVE_W, height=GROOVE_H, floor_z=SEAT_Z, closed_end_x=r3(BODY_X1),
                    body_x=[r3(BODY_X0), r3(BODY_X1)], empty_behind_body=LEAF_DX,
                    open_end="rear, through the stop wall's insertion slot", leaf_opening_width=LEAF_OPEN_W,
                    centres_y=[PAD_Y["plus"], PAD_Y["minus"]]),
        leaf=dict(body_top_z=TOP, free_top_z=LEAF_TOP, compressed_at_nominal_seat=r3(LEAF_TOP - PAD_Z),
                  compressed_at_sim_seat=r3(LEAF_TOP - SEAT_SIM), keystone_working_travel="about 3 mm below free height (M65p36 AA mounting)"),
        block=dict(x=[X_STOP, BLOCK_X1], y=[-BLOCK_Y, BLOCK_Y], top_z=BLOCK_TOP, clearance_to_pads=r3(PAD_Z - BLOCK_TOP)),
        tower=dict(stop_face_x=X_STOP, stop_face_in_sim_frame_D=X_STOP + D_SHIFT, gap_to_backpack_back=r3(BACK_X - X_STOP),
                   x=[X_REAR, X_STOP], y=[-TOWER_Y, TOWER_Y], top_z=TOWER_TOP,
                   walls=dict(stop=FRONT_WALL_T, sides=TOWER_WALL, rear=REAR_WALL_T),
                   insertion_slots=dict(y_centres=[9.0, -9.0], width=SLOT_W, z_from=SLOT_Z[0], top="open through the lead-in"),
                   stop_face_band_z=[PLATE_T, Z_LEAD], backpack_contact_band_z=[SEAT_SIM, Z_LEAD]),
        jack=dict(part="Same Sky PJ-005A", axis="x", y=0.0, z=JACK_Z, hole_d=JACK_HOLE_D, rear_wall_x=[X_REAR, X_FLANGE],
                  flange_face_x=X_FLANGE, lug_end_x=X_FLANGE + J_ALL_L, lugs_z={k: JACK_Z + v for k, v in J_LUG.items()},
                  nut_outside="10.8 AF x 2.0 on 0.5 washer, rear (outside) face", plug="from behind (-x)",
                  bushing_left_for_nut=round(J_BUSH_L - REAR_WALL_T - J_WASH_T - J_NUT_T, 2)),
        contacts=dict(part="Keystone 5209", body_x=[r3(BODY_X0), r3(BODY_X1)], tab_x=[r3(TAB_X0), r3(BODY_X0)],
                      tab_end_inside_tower=bool(TAB_X0 < X_WALL_IN)),
        wires=wires, checks=ck, fails=fails)
    info["assembly"] = [
        "Tools: soldering iron, 20 AWG red and black wire, wire stripper, small flat screwdriver, 11 mm (7/16 in) wrench or pliers.",
        f"Cut one red and one black 20 AWG wire, {wires['plus']['cut_mm']} mm and {wires['minus']['cut_mm']} mm, strip {WIRE_STRIP:.0f} mm at each end.",
        "Off the dock: solder the red wire through the solder-tab hole of one Keystone 5209 (the + contact) and the black wire to the other (- contact).",
        "Stand behind the dock (the tower is nearest you, the two rails point away from you). The groove on your left is +, on your right is -.",
        "Lower the + contact into the open top of the tower, leaf up, leaf end pointing away from you, wire trailing toward you. Feed it through the left slot in the tower's front wall and push the flat body into the left groove until its far end stops against the closed end of the groove.",
        "Do the same with the - contact in the right slot and groove.",
        "Check: each leaf springs back when pressed and does not rub the opening's sides; each body does not move when the leaf is pressed.",
        "Put the PJ-005A in from inside the tower: bushing through the round hole in the rear wall, flange flat on the inside face, centre-pin lug at the top.",
        "Outside: washer then nut; tighten with the 11 mm wrench while holding the lugs straight.",
        "Solder red to the centre-pin lug (top), black to the sleeve lug (middle). Leave the bottom lug empty.",
        "Check with a meter: charger plugged in, the + leaf reads +8.4 V against the - leaf.",
        "Stick foam tape or Dual Lock under the base plate and put the dock where the robot sits.",
    ]
    (OUT / "build.json").write_text(json.dumps(info, indent=1, default=float, ensure_ascii=False)
                                    .replace('"from_"', '"from"').replace('"class_"', '"class"'))
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
        dict(id=f"insertion-slot y{y:+.0f}", type="pair", fit_class="loose",
             female=dict(part="dock_base", d=SLOT_W, axis=[1, 0, 0], teardrop=None, at_bed=False, chamfer=0.0),
             male=dict(part=None, d=K_BODY_W, axis=[1, 0, 0], teardrop=None, at_bed=False, chamfer=0.0)) for y in PAD_Y.values()] + [
        dict(id="jack-hole", type="pair", fit_class="locating",
             female=dict(part="dock_base", d=JACK_HOLE_D, axis=[1, 0, 0], teardrop=[0, 0, 1], at_bed=False, chamfer=0.0),
             male=dict(part=None, d=J_BUSH_D, axis=[1, 0, 0], teardrop=None, at_bed=False, chamfer=0.0))])
    (HERE / "FITS.json").write_text(json.dumps(fits, indent=1))
    print(json.dumps(dict(release=RELEASE, volume_cm3=info["volume_cm3"], mass_g=info["mass_g_solid_pla"], bounds=info["bounds_world"],
                          block_top=ck["block_top_z"], wall=ck["wall_check"], overlaps=ov,
                          robot={p: c["overlap_mm3"] for p, c in ck["robot"].items()}, heads=heads,
                          leaf={s: {p: leaf_c[s][p]["margin"] for p in POSES} for s in leaf_c}, legs=ck["legs_vs_dock"],
                          iron=iron, collision=ck["collision_pieces"], overhang=area, wires=wires, fails=fails), indent=1, default=float))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
