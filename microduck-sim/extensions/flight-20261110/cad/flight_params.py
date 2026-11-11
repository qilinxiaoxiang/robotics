"""Parameters of the flight-pack printed parts (guide frame, mm: x forward, y left, z up; stand-world z = guide z + 120).
Every fit number comes from ~/code/robotics/cad-practice/print_fit.py; every fan number from FAN (one dict).
"""
import math
import sys
from pathlib import Path

# the cad-practice beside this checkout (robotics/cad-practice), so the Mac mini mirror uses the synced copy, not its own
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "cad-practice"))
import print_fit as F  # noqa: E402

PRINTER = "H2S"                                  # default club printer; one STL serves all three (see HOLE notes)

# ------------------------------------------------------------------ the fan: one named parameter set, one source
# Axial positions t are measured from the inlet lip face toward the motor (mm). Every fan-dependent dimension of the
# nacelle (bore, axial stops, clamp length, ear pockets, screw radius, middle web), the fan envelope used by the
# clearance checks, the lead exits and the lead lengths derive from the active set. "tol" is the band (mm) every
# position and size may be off by; the nacelle fits any fan inside it (clamp range "clamp_od", foam liner, stop and
# pocket clearances), and the fan envelope used by the clearance checks is the largest fan in the band.
# Optional keys: band_* (raised band above the clamp), spinner_* (nose cone ahead of the lip face), ear_* (moulded ears).
FANS = {
    "QX_50_12B": dict(
        source=("QX-Motor 50 mm 12-blade EDF maker drawing, banggood image d33d80c5-ce22-4e71-96e9-32272d8da90b.jpg, read by "
                "the coordinator 2026-11-10: printed values lip OD 63.0, duct OD 54.0, housing lip face to rear rim 39.08, "
                "motor can OD 25.8; the rest scaled from the drawing +-0.4 mm. Not bought (replaced by ARESWEI_HDS001)."),
        lip_od=63.0, lip_t=(0.0, 5.5),
        band_od=55.5, band_t=(5.5, 9.4),         # raised band: upper axial stop
        duct_od=54.0, duct_t=(9.4, 36.9),        # straight clampable section (27.5 long)
        rim_od=55.0, rim_t=(36.9, 39.08),        # rear rim: lower axial stop
        stator_t=(39.08, 46.5), stator_od=(45.0, 25.8),
        motor_od=25.8, motor_t=(46.5, 75.8),
        lead_t=(47.0, 49.0), lead_len=70.0, lead_od=1.6,   # three leads leave radially at the motor front ring
        mass_g=80.0, tol=0.4, clamp_od=(53.6, 54.4),
    ),
    "ARESWEI_HDS001": dict(
        source=("ARESWEI HDS001 50 mm 11-blade 4650KV (Amazon B0H4KJLR6P CW / B0H4KSDT77 CCW). Fan dimensions come from the "
                "listing dimension drawing, no caliper step (Shawn 2026-11-10). STATED (each rounded to 0.1 inch, so +-1.3 mm): "
                "overall spinner tip to motor end 3.3 in = 83.8, inlet lip OD 2.3 in = 58.4, rear ring OD 2.0 in = 50.8, "
                "housing lip face to rear ring 1.3 in = 33.0, motor can OD 0.9 in = 22.9. PIXEL-SCALED from the same drawing "
                "with the 2.3 in lip as the scale (9.33 px/mm): straight duct OD 50.6, rear ring 52.9 (the stated 2.0 in and "
                "the pixels disagree by 2 mm: the band below spans both), inlet flare 5.4 long, spinner tip 12.8 ahead of the "
                "lip face, ear block t 17.9..27.6 reaching r ~31.5 (inlet view), leads leaving the motor front ring at t "
                "41..44.5. Seller: 77 g, leads ~140 mm, 3.5 mm bullets. Ear width and hole, and which of the mirror-image "
                "lead directions the moulding has, are not shown: the nacelle accepts every option."),
        tol=1.5,                                 # every position and size below may be off by this much (stated +-1.3)
        lip_od=58.4, lip_t=(0.0, 5.4),           # removable inlet ring (flare), modelled as a cylinder of its largest OD
        duct_od=50.6, duct_t=(5.4, 32.0),        # straight clampable duct (pixel); ends at the rear ring
        clamp_od=(49.1, 52.5),                   # duct OD range the clamp must close on: pixel 50.6 +-1.5, and at least 49.5..52.5
        rim_od=52.9, rim_t=(32.0, 33.0),         # rear ring (pixel 52.9; stated 2.0 in = 50.8), back face at the stated 33.0
        stator_t=(33.0, 43.0), stator_od=(52.0, 20.0),     # tail cone behind the rim
        motor_od=22.9, motor_t=(43.0, 71.0),     # stated can OD; motor end = overall 83.8 - spinner 12.8
        spinner_od=22.0, spinner_t=(-12.8, 0.0), # nose cone ahead of the lip face
        ear_t=(17.9, 27.6), ear_r=31.5, ear_w=8.0,          # two moulded ears 180 deg apart, screw boss each (not used)
        lead_t=(41.0, 44.5), lead_len=140.0, lead_od=2.4,
        mass_g=77.0,
    ),
}
FAN_ID = "ARESWEI_HDS001"
FAN = FANS[FAN_ID]
CANT_DEG = 6.0                                   # Shawn: front fans' exhaust tilts forward, rear fans' rearward
FAN_X = {"front": 20.0, "rear": -44.0}           # lip-face centres (decision of 2026-11-10)
FAN_Y = 110.0
LIP_TOP_Z = 75.0                                 # stand 195: head clearance
S, C = math.sin(math.radians(CANT_DEG)), math.cos(math.radians(CANT_DEG))
LIP_Z = LIP_TOP_Z - FAN["lip_od"] / 2 * S        # lip-face centre (the tilted lip's highest point sits at LIP_TOP_Z)
DIR = {"front": +1, "rear": -1}                  # exhaust direction down the axis: (DIR*S, 0, -C)


def fan_point(which, t, side=+1):
    """Point on the fan axis at axial distance t (mm) behind the lip face."""
    d = DIR[which]
    return (FAN_X[which] + d * S * t, side * FAN_Y, LIP_Z - C * t)


def lead_angles(side=+1):
    """Every direction (deg in the plane across the fan axis, 0 = +x forward, 90 = +y left) in which the three motor leads
    may leave. With ears the fan is turned so both ears lie in the nacelle split plane (0 / 180 deg, captured between the
    halves); the inlet view shows the leads 45 deg off the ears, and a mirror-image moulding cannot be ruled out, so all
    four diagonals are possible: the nacelle leaves each one open and the lead lengths take the longest. Without ears:
    straight inboard."""
    if "ear_t" not in FAN:
        return [270.0 if side > 0 else 90.0]
    return [45.0, 135.0, 225.0, 315.0]


# ------------------------------------------------------------------ nacelle clamp (every number from FAN or print_fit)
PIL_M2 = F.pilot("M2", "horizontal", "any", PRINTER)          # 2.15 on the H2S (same call as build_pack PIL_H)
# Clamp that fits every fan in the band, nothing measured: one layer of 1 mm foam double-sided tape lines each bore (the
# foam tape on record in the robotics memory, and Shawn allows 3M foam tape); the largest duct (clamp_od max) presses the
# tape to TAPE["firm"] with the halves fully open, and the smallest grips once the tape is at TAPE["grip"]; the halves
# close the difference at both seams under the five clamp screws. The screw bite then stays inside 2.5 d (PRINT-FIT.md
# "Engagement") over the whole travel because each head sits in a counterbore that leaves TAPE-independent "under_head".
TAPE = dict(free=1.0, grip=0.8, firm=0.35)
TOL = FAN.get("tol", 0.0)
CLAMP = FAN.get("clamp_od", (FAN["duct_od"], FAN["duct_od"]))
_bore = CLAMP[1] + 2 * TAPE["firm"]
_travel = _bore - (CLAMP[0] + 2 * TAPE["grip"])                # how far the halves close between the largest and smallest fan
_res = 0.5                                                     # seam gap left at the smallest fan
_eng_max = F.MAX_ENGAGEMENT_D["any"] * 2.0                     # 5.0 mm bite at the smallest fan
NAC = dict(
    bore=round(_bore, 2), tape=TAPE, clamp_od=CLAMP,
    travel=round(_travel, 2), split_gap=round(_travel + _res, 2),   # printed gap at each seam; closes by "travel" at most
    # an M2 washer (ISO 7089, 5.0 x 0.3) under each clamp head in a 5.4 seat: the bare head bearing was SF 1.62 at snug and
    # 1.04 at the strip load (strength/README.md, "Clamp screw head bearing"); with the washer about 4
    washer=F.WASHER["M2"], head_seat=F.WASHER_SEAT["M2"],
    # M2 x 12 (the post screws' Zuorery kit length): with 6.2 mm under the washer the head top stands level with the outer
    # block face (outer_y 9.4 is set by the ear-pocket skin), so the driver corridor starts outside the face where the end
    # walls keep 4 mm free (PRINT-FIT "Access": a counterbore wall above the head top counts as a wall; M2 x 10 left the
    # head 1.8 mm down a 5.4 seat, free radius 2.7). Bite window unchanged.
    screw_len=12.0, under_head=round(12.0 - F.WASHER["M2"]["t"] - _eng_max - _res, 2),   # material under the washer: bite 5.0 (smallest) .. 5.0 - travel (largest)
    wall=3.0,
    # collar ends clear the lip flare and the rear ring by tol + 0.5 whichever way the fan is off
    t0=FAN["duct_t"][0] + TOL + 0.5, t1=FAN["duct_t"][1] - TOL - 0.5,
    relief=FAN["rim_od"] + 2 * TOL + 1.0,                      # skirt bore below the collar clears the largest rear ring
    front_t=FAN["lip_t"][1] + TOL + 0.3,                       # lip (and band) keep-out ends here
    keep_lip_r=(max(FAN["lip_od"], FAN.get("band_od", 0.0)) + 2 * TOL) / 2 + 1.0,
    ear_out=4.0,                                               # block material past the screw axis
    inner_y=7.0, outer_y=5.0,                                  # block/web depth each side of the split plane (minimums)
    lug_x=(-45.0, -36.8), lug_y=(70.0, 82.0), lug_top=58.0,     # inner half: bolts to the wing arm web front face (x -45)
    lug_screw_y=74.0, lug_screw_z=(37.0, 44.5, 52.0),
)
NAC["bite"] = (round(NAC["screw_len"] - NAC["washer"]["t"] - NAC["under_head"] - NAC["split_gap"], 2), round(_eng_max, 2))   # largest .. smallest fan
# the skirt below the collar is bored out to clear the rim: keep >= 1.6 mm of wall there too
NAC["wall"] = max(NAC["wall"], round((NAC["relief"] - NAC["bore"]) / 2 + 1.6, 1))
NAC["r_out"] = NAC["bore"] / 2 + NAC["wall"]
if "ear_t" in FAN:
    # one pocket per ear, centred on the split plane (half in each half). Clearance: the ear may be tol off in position and
    # size each way, plus 0.3; across the split, also the half's own travel (the halves sit split_gap / 2 off the plane
    # when printed and close to _res / 2), so the ear never bears on a pocket side before the clamp grips.
    hw = (FAN["ear_w"] + TOL) / 2 + TOL + 0.3 + (NAC["split_gap"] - _res) / 2
    NAC["ear_pocket"] = dict(t=(FAN["ear_t"][0] - TOL - 0.3, FAN["ear_t"][1] + TOL + 0.3), r=FAN["ear_r"] + TOL + 0.3,
                             half_w=round(hw, 2))
    # each half keeps >= 1.6 mm of skin outside the pocket (rule: nothing under 1.2 mm)
    NAC["outer_y"] = max(NAC["outer_y"], round(hw + 1.6, 1))
    NAC["inner_y"] = max(NAC["inner_y"], round(hw + 1.6, 1))
# the clamp side must hold the head seat over under_head; the pilot side must take the 5.0 mm bite plus 1 mm
NAC["outer_y"] = max(NAC["outer_y"], round(NAC["split_gap"] / 2 + NAC["under_head"], 1))
NAC["inner_y"] = max(NAC["inner_y"], round(NAC["split_gap"] / 2 + _eng_max + 1.0 + 1.2, 1))
# clamp screws along y through the fore and aft blocks: 4.5 mm driver room past the collar, and >= 2 mm of wall to an ear pocket
NAC["screw_r"] = round(max(NAC["r_out"] + 4.5, NAC.get("ear_pocket", {}).get("r", 0.0) + NAC["head_seat"][0] / 2 + 2.0), 2)
# Collar wall where each screw block (and the middle web) ends: tightening bends the 3.4 mm wall there, SF 0.42 at snug
# (strength/README.md, "Nacelle clamp: fails at assembly"); the check sized 7.0 mm for SF 2.0. The thick wall's face stands
# 4.0 mm from the screw axis (driver corridor), which gives >= 7.0; it tapers back to the normal wall over 10 mm of arc.
NAC["end_wall"] = round(NAC["screw_r"] - 4.0 - NAC["bore"] / 2, 2)
NAC["end_taper"] = 10.0
# At the outer-end blocks (front fan +x, rear fan -x) the 2026-11-10 rerun on 6fa0d176 put the snug-preload bending at the
# taper end: outer-face max principal (95th pct per 5 deg) 20 / 50 / 54 / 35 / 30 / 28 / 22 / 18 MPa at 25..65 deg from the
# block axis (strength FEA probe, clamp_band binning). The thick wall now runs to 50 deg there and tapers back over 20 mm of
# arc (at r_out) with a smoothstep profile; the middle-web side (<= 22 MPa) keeps the short 10 mm taper.
NAC["end_thick_deg"] = 50.0
NAC["end_taper_long"] = 20.0
assert NAC["end_wall"] >= 7.0, f"block-end collar wall {NAC['end_wall']} < 7.0 (strength check)"
# Fillet where the inner half's lug meets the rear collar on its +x face: FEA put the handling case at SF ~1.8 there from
# shear lag (strength/README.md, "Nacelle inner half under handling")
NAC["lug_fillet_r"] = 3.0
# upper screw: 1.6 mm of skin between the block top (collar top) and the tip of the head-seat teardrop (r * sqrt 2);
# t0 + 4.1 left 0.85 mm there once the seat grew to 4.6 mm (2026-11-10 check)
NAC["ear_screw_t"] = (round(NAC["t0"] + (1.6 + NAC["head_seat"][0] / 2 * 2 ** 0.5) / C, 2), round(NAC["t1"] - 4.4, 2))
# middle web between the two collars: its faces stand 2.8 mm past each collar's outer surface at the collar bottom, where
# the canted collars reach furthest apart, so a web face never crosses a collar surface (that left a 1.0 mm sliver).
# Its screw sits above the ear pockets when there is room (below them the web runs into the print bed), else below.
_xr = FAN_X["rear"] - S * NAC["t1"] + NAC["r_out"] / C
_xf = FAN_X["front"] + S * NAC["t1"] - NAC["r_out"] / C
NAC["web_x"] = (round(_xr - 2.8, 2), round(_xf + 2.8, 2))
if "ear_pocket" in NAC:
    # web screw above the two facing ear pockets, centred between the pocket tops (+1.2 skin under its head seat) and the
    # lip keep-out planes over it (+1.2 skin above); the web rises to the collar top between the two lip keep-outs
    _p, _rh, _xm = NAC["ear_pocket"], NAC["head_seat"][0] / 2, sum(NAC["web_x"]) / 2
    _z_lo = LIP_Z - C * _p["t"][0] - S * _p["r"] + 1.2 + _rh
    _ft = NAC["front_t"]

    def _plane(x, which):
        d = abs(x - fan_point(which, _ft)[0]) / C
        return LIP_Z - _ft * C - d * S if d < NAC["keep_lip_r"] else LIP_Z - NAC["t0"] * C
    # bound on the hole centre: 1.2 skin over the teardrop tip (r * sqrt 2, at the centre x) and over the round sides
    # (r, at x -+ r); the old bound left the planes unreduced and the 5.4 washer seat came to 0.9 mm (2026-11-10 check)
    _tip = _rh * 2 ** 0.5
    _z_hi = min(_plane(_xm, "rear") - _tip, _plane(_xm, "front") - _tip, _plane(_xm - _rh, "rear") - _rh,
                _plane(_xm + _rh, "front") - _rh, LIP_Z - NAC["t0"] * C - _tip) - 1.2
    assert _z_lo < _z_hi, f"no room for the middle web screw: {_z_lo:.2f} .. {_z_hi:.2f}"
    NAC["web_screw_t"] = round((LIP_Z - (_z_lo + _z_hi) / 2) / C, 2)
    NAC["web_screw_room_z"] = (round(_z_lo, 2), round(_z_hi, 2))
else:
    NAC["web_screw_t"] = round(NAC["t1"] - 3.4, 2)
NAC["bed_z"] = LIP_Z - NAC["t1"] * C - NAC["r_out"] * S          # lowest collar point: print bed plane of both halves
if "ear_pocket" in NAC:
    # the canted pocket floor dips toward the middle web; keep 1.6 mm of floor under its lowest corner (it sat 0.25 mm
    # above the collar-bottom bed, 2026-11-10 check)
    _p = NAC["ear_pocket"]
    NAC["bed_z"] = min(NAC["bed_z"], LIP_Z - _p["t"][1] * C - _p["r"] * S - 1.6)

# ------------------------------------------------------------------ wing plate (one piece, printed front face down)
WING = dict(
    # centre: 6.9 mm on the pack posts (shared M2 x 12, Shawn '用 M2×12'); the backpack sits 3.4 mm further back so the
    # root band can be 8.5 deep (strength/SPAR-OPTION.md "Thrust centre and the arm": landing SF 0.89 -> 2.03)
    x_front=-45.0, x_centre_back=-45.0 - 6.9,
    post_screw="M2 x 12", backpack_plate_t=2.0,
    x_band_back=-45.0 - 8.5,                     # root band, column and transition at |y| 18.9..root_y: solid 8.5 deep
    root_y=32.1,                                 # deep part stops 0.5 inside the cross-harness run at |y| 32.6
    # corner fill of the first strength report (strength/fea_setup.py ROOT_FIX): the band raised to z 42.5 behind the shell
    # lip / saddle zone, from |y| 23 (2 mm below the backpack top plugs at |y| <= 21, z 43) to 30; and the column front
    # filled down to z -1 at |y| 28.5..30 (28.2 in fea_setup touched the right shell at |y| 28.3, so it starts at the column face)
    root_fix=[dict(x=(-45.0 - 8.5, -46.8), y=(23.0, 30.0), z=(28.0, 42.5)),
              dict(x=(-46.8, -45.0), y=(28.5, 30.0), z=(-1.0, 24.9))],
    x_recess=-46.8,                              # front face where the shell rear lips (to x -46.3) / saddle (x -45, 1.5 mm) are
    x_back=-50.2,                                # behind the band: backpack box front moves to x -50.5
    x_back_out=-51.8,                            # outboard of |y| 32.8 (backpack is |y| <= 32)
    centre_half_w=18.6, centre_ext_w=20.3,       # centre outline |y| <= 18.6; solid extension to 20.3 (shell side lip starts at 20.5)
    centre_top=29.0, centre_bot=-44.0,           # 1.75 mm above the upper post holes (z 26, d 2.5)
    holes=[(16.1, 26.0), (16.1, -36.5), (-16.1, 26.0), (-16.1, -36.5)],
    band_y=(20.3, 28.5), band_z=(-1.0, 28.0), band_lip_z=9.0,   # below z 9 the band is full depth (shell lip starts z 9.5)
    col_y=(28.5, 37.9), col_z=(9.0, 28.0),                     # outer column: legs reach z 4 at |y| 30..35 (half joint range)
    saddle_zone=dict(y=37.9, z=24.9),                          # |y| < 37.9, z > 24.9: front face <= -46.5 (1.5 mm from the saddle)
    trans_y=(30.0, 37.9), trans_z=(9.0, 42.5),                 # transition column -> arm, kept under z 45
    arm_y=(37.9, 79.0), arm_z=(18.0, 59.5), arm_x_rear=-64.0,  # arm web x -50.2..-45 (5.2): M2 x 10 from behind bites 4.8
    flange_t=3.5, gussets=[(37.9, 40.0), (52.5, 54.5), (67.6, 69.4)],
    # third tray screw high on the raised inboard flange: the two at z 31 pulled 81 / 99 N on a 9 mm lever at the 15.6 g
    # landing, SF 1.2 (strength/README.md, "Tray flange screws"); with (46, 45) the worst is 60 N, SF 2.0 at the low
    # pull-out (results.json fixes.tray). Both screws cannot rise to z 45: y 63 is inside the lead window
    tray_screws=[(46.0, 31.0), (63.0, 31.0), (46.0, 45.0)],
    # battery XT60 + balance lead through the arm web into the bay; 11 x 18 so the pack's XT60 (XT60_ENV, 15.8 x 8.2
    # across its axis) passes upright at every battery change; top 4 mm under the arm top, bottom 1.5 over the tray flange
    lead_window=dict(y=(55.5, 66.5), z=(37.5, 55.5)),
    # NOT CUT since round E (2026-11-10): the front fan leads now run outboard of the tray and round the arm's outer end
    # into the bay (they lay under the battery here). Kept only because wiring/build_wiring.py still draws through it.
    fan_window=dict(y=(70.5, 77.0), z=(26.0, 32.0)),
    # harness and left battery tail along the bays behind the web; the windows of the gussets listed in open_rear run out
    # through the gusset's rear edge (x -64) so the left battery pigtail, soldered to the ESC on the bench, is laid in from
    # behind with its XT60 on (an XT60 does not pass an 8 x 12 window)
    gusset_window=dict(x=(-60.0, -52.0), z=(22.0, 34.0), open_rear=((37.9, 40.0), (52.5, 54.5)), x_open=-64.6),
    # lift by one nacelle peaks at the top front corner (x -52, z 34) of the rear-open slots: R 2.5 corner fillet there
    # (strength/README.md, variant wing_wedge_slot_corner, commit 13955e83)
    slot_fillet_r=2.5,
    # lift by one nacelle peaks where the arm web bottom (z 18) steps up from the transition column bottom (z 9):
    # a web-depth wedge (x_back..x_front) under each arm, (|y|, z) profile ramping linearly from z 9 at |y| 37.85 to
    # z 15.75 at |y| 43.9, flat to |y| 46 (strength/README.md, variant wing_arm_root_wedge)
    arm_root_wedge=((37.85, 9.0), (43.9, 15.75), (46.0, 15.75), (46.0, 18.1), (37.85, 18.1)),
    # swap plugs 3 (XT30) + 4 (MR30): the backpack-side halves pass the wing centre with their leads on, plug axis along x;
    # world bp_swap_plugs bodies are 5.2 / 4.8 thick (x) and 10.2 wide, so the window is 7.0 high (backpack window 4.9)
    swap_window=dict(y=(-11.5, 11.5), z=(4.6, 11.6)),
    # existing camera USB cable (guide cable cam-usb, r 2.0, passes (-46, 39.5, 50.5) -> (-52.5, 30, 52)): notch in the
    # arm web's inboard top corner, open to the inboard side (nothing at |y| < 37.9 above the transition top z 42.5), so
    # the fitted cable is laid in sideways; 1 mm round the drawn tube
    cam_notch=dict(x=(-51.0, -44.9), y=(37.8, 43.0), z=(47.0, 54.0)),
    centre_step=dict(y=17.0, z=26.0, y_low=19.8),              # recessed to x_recess: |y| > 17 above z 26 (shell top lip), |y| > 19.8 above z 9 (side lip)
    # Cross harness (left fans' 6 x 16 AWG + left battery pair): the slot along the wing plate between the backpack
    # front (x -50.5) and the shell lip / saddle (x -46.1 / -46.5) is 3.8 x 11.5 mm = 44 mm2 for a ~61 mm2 bundle, so the
    # harness runs back outboard of the backpack (|y| 32.6..37.6) and crosses behind the backpack cap below the hatch.
    # The rear crossing follows the backpack cap 3.4 mm further back since the centre grew to 6.9 mm (M2 x 12 decision).
    harness_side=dict(x=(-80.6 - 3.4, -50.4), y=(32.6, 37.6), z=(14.0, 28.0)),
    harness_rear=dict(x=(-86.8 - 3.4, -80.6 - 3.4), y=(-33.0, 37.6), z=(4.0, 16.0)),   # ends at the ESC's inboard edge on the right
)
WING["harness_cross_x"] = round(sum(WING["harness_rear"]["x"]) / 2, 2)    # route line of the rear crossing (lead_lengths)

# ------------------------------------------------------------------ battery tray (printed flat)
BATT = dict(size=(74.0 + 4.0, 33.0, 31.0), listed=(74.0, 33.0, 31.0), mass_g=151.0,    # +4 mm length slack (listing +-1..5)
            x0=-36.0, y0=42.5)                                                       # rear end (0.8 from the nacelle lug), inner face
TRAY = dict(deck_z=(22.0, 26.0), x=(-45.0, 42.4), y=(37.9, 80.5),
            flange_x=(-45.0, -37.0), flange_z=(26.0, 36.0), flange_y=(39.0, 54.5),   # flange stops under the lead window
            flange2_y=(59.0, 69.5),
            # inboard flange raised to z 50 for the third screw (strength case above); the outboard one stays at z 36,
            # under the lead window (y 55.5..66.5, z 38..52) the battery XT60 and balance lead pass through
            flange_top=(50.0, 36.0),
            # the raised part starts at y 41.5: at y 39.5, z 46.5 the head reaches it in the 50 % random head poses
            flange_raised_y0=41.5,
            strap_w=16.0 + 2.0, strap_t=3.0, strap_x=[(-30.0, -12.0), (14.0, 32.0)],
            strap_y_in=(39.3, 42.3), strap_y_out=(75.8, 78.8),
            # camera USB cable (cam-usb, r 2.0) along y 40, z 50 over the raised inboard flange's inboard top corner
            cam_notch=dict(x=(-46.0, -36.0), y=(41.4, 43.5), z=(47.0, 50.1)))

# ------------------------------------------------------------------ electronics (procurement.json cad_handoff)
FC = dict(board=(36.0, 36.0, 8.0), esc=(41.0, 41.0, 6.0), pattern=30.5, hole=4.0, mass_g=24.0, hw_g=6.0)
MTF01 = dict(size=(29.3, 17.0, 14.5), holes=(24.3, 12.0), hole_d=2.5, mass_g=4.5, cone_half_deg=21.0)
CAP = dict(d=13.0, h=25.0)
# XT60 housing across its axis, mm (Amass XT60 as commonly listed, 15.8 x 8.2 x 16; the Amass PDF in wiring.json sources
# was not readable on 2026-11-10, so this is a listing figure): sizes the battery lead window and the FC plate window
XT60_ENV = (15.8, 8.2)
PLA_DENSITY = 1.24      # g/cm3
