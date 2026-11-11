"""Parameters of the flight-pack printed parts (guide frame, mm: x forward, y left, z up; stand-world z = guide z + 120).
Every fit number comes from ~/code/robotics/cad-practice/print_fit.py; every fan number from FAN (one dict).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "code/robotics/cad-practice"))
import print_fit as F  # noqa: E402

PRINTER = "H2S"                                  # default club printer; one STL serves all three (see HOLE notes)

# ------------------------------------------------------------------ the fan: one named parameter set, one source
# Axial positions t are measured from the inlet lip face toward the motor (mm). Every fan-dependent dimension of the
# nacelle (bore, axial stops, clamp length, ear pockets, screw radius, middle web), the fan envelope used by the
# clearance checks, the lead exit and the lead lengths derive from the active set. When the real fan is measured
# (cad/FAN-MEASURE.md), edit only FANS["ARESWEI_HDS001"] and rebuild.
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
        mass_g=80.0,
    ),
    "ARESWEI_HDS001": dict(
        source=("ARESWEI HDS001 50 mm 11-blade 4650KV (Amazon B0H4KJLR6P CW / B0H4KSDT77 CCW). PROVISIONAL: no maker drawing. "
                "Pixel-scaled from the listing side view (3.3 / 2.3 / 2.0 / 1.3 / 0.9 inch labels, inch values rounded to 0.1, "
                "so +-3 %): scale 9.24 px/mm from the 2.3 inch lip; front view for the ears and the lead direction. Duct OD "
                "conflict: the coordinator read 53..54.5, the duct/lip pixel ratio 0.867 gives 50.3..52.0 (rotor 49 mm per "
                "the seller fits the smaller value); 52.0 used until measured. Seller: 77 g, leads ~140 mm, 3.5 mm bullets. "
                "Measure on arrival (cad/FAN-MEASURE.md) before the nacelle plate is sliced."),
        lip_od=59.0, lip_t=(0.0, 5.4),           # removable inlet ring (flare), modelled as a cylinder of its largest OD
        duct_od=52.0, duct_t=(5.4, 32.6),        # straight clampable duct
        rim_od=54.6, rim_t=(32.6, 33.6),         # rear rim flange (1.3 mm proud of the duct): lower axial stop
        stator_t=(33.6, 43.0), stator_od=(53.0, 20.0),     # tail cone behind the rim
        motor_od=25.5, motor_t=(43.0, 69.0),     # can 25..26, end cap and shaft tip at t 69 (overall 81..84 with the spinner)
        spinner_od=22.0, spinner_t=(-12.8, 0.0), # nose cone stands 12.8 above the lip face
        ear_t=(17.9, 27.6), ear_r=31.5, ear_w=8.0,          # two moulded ears 180 deg apart, screw boss each (hole unknown)
        ear_from_lead_deg=(-45.0, 135.0),        # seen from the inlet, counter-clockwise: ears at lead -45 and lead +135
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


def lead_angle(side=+1):
    """Direction (deg in the plane across the fan axis, 0 = +x forward, 90 = +y left) in which the three motor leads leave.
    With ears the fan is turned so both ears lie in the nacelle split plane (0 / 180 deg, captured between the halves);
    the moulding then leaves two possible lead directions and the more inboard one is used. Without ears: straight inboard."""
    if "ear_t" not in FAN:
        return 270.0 if side > 0 else 90.0
    cands = sorted({(e - o) % 360 for e in (0.0, 180.0) for o in FAN["ear_from_lead_deg"]})
    return min(cands, key=lambda a: side * math.sin(math.radians(a)))


# ------------------------------------------------------------------ nacelle clamp (every number from FAN or print_fit)
PIL_M2 = F.pilot("M2", "horizontal", "any", PRINTER)          # 2.15 on the H2S (same call as build_pack PIL_H)
NAC = dict(
    bore=F.clearance("locating") * 2 + FAN["duct_od"],         # locating 0.15/side on the bought duct (vertical in print)
    wall=3.0,
    t0=FAN["duct_t"][0] + 0.5, t1=FAN["duct_t"][1] - 0.5,      # collar on the straight duct, 0.5 axial play to the stops
    split_gap=0.6,                                             # 0.3 per half: screws draw the halves onto the duct (max squeeze 0.15/side)
    relief=FAN["rim_od"] + 1.5,                                # skirt bore below the collar clears the rim
    front_t=FAN["duct_t"][0] + 0.3,                            # lip (and band) keep-out ends here
    keep_lip_r=max(FAN["lip_od"], FAN.get("band_od", 0.0)) / 2 + 1.0,
    ear_r_screw=F.clear("M2", "horizontal") / 2 + 0.0,
    ear_out=4.0,                                               # block material past the screw axis
    inner_y=7.0, outer_y=5.0,                                  # block/web depth each side of the split (pilot side 7 >= 6, clamp side 5)
    lug_x=(-45.0, -36.8), lug_y=(70.0, 82.0), lug_top=58.0,     # inner half: bolts to the wing arm web front face (x -45)
    lug_screw_y=74.0, lug_screw_z=(37.0, 44.5, 52.0),
)
# the skirt below the collar is bored out to clear the rim: keep >= 1.6 mm of wall there too
NAC["wall"] = max(NAC["wall"], round((NAC["relief"] - NAC["bore"]) / 2 + 1.6, 1))
NAC["r_out"] = NAC["bore"] / 2 + NAC["wall"]
if "ear_t" in FAN:   # pocket for each ear, half in each nacelle half (ears lie in the split plane)
    NAC["ear_pocket"] = dict(t=(FAN["ear_t"][0] - 0.5, FAN["ear_t"][1] + 0.5), r=FAN["ear_r"] + 0.5, w=FAN["ear_w"] + 0.6)
    # each half keeps >= 1.6 mm of skin outside its half of the pocket (rule: nothing under 1.2 mm)
    NAC["outer_y"] = max(NAC["outer_y"], round(NAC["ear_pocket"]["w"] / 2 + 1.6, 1))
    NAC["inner_y"] = max(NAC["inner_y"], round(NAC["ear_pocket"]["w"] / 2 + 1.6, 1))
# clamp screws along y through the fore and aft blocks: 4.5 mm driver room past the collar, and >= 2 mm of wall to an ear pocket
NAC["screw_r"] = round(max(NAC["r_out"] + 4.5, NAC.get("ear_pocket", {}).get("r", 0.0) + PIL_M2 / 2 + 2.0), 2)
NAC["ear_screw_t"] = (round(NAC["t0"] + 4.1, 2), round(NAC["t1"] - 4.4, 2))
# middle web between the two collars: its faces stand 2.8 mm past each collar's outer surface at the collar bottom, where
# the canted collars reach furthest apart, so a web face never crosses a collar surface (that left a 1.0 mm sliver);
# its screw sits below the ear pockets
_xr = FAN_X["rear"] - S * NAC["t1"] + NAC["r_out"] / C
_xf = FAN_X["front"] + S * NAC["t1"] - NAC["r_out"] / C
NAC["web_x"] = (round(_xr - 2.8, 2), round(_xf + 2.8, 2))
NAC["web_screw_t"] = round(max(NAC["t1"] - 3.4, NAC.get("ear_pocket", {}).get("t", (0, 0))[1] + PIL_M2 / 2 + 1.5), 2)
NAC["bed_z"] = LIP_Z - NAC["t1"] * C - NAC["r_out"] * S          # lowest collar point: print bed plane of both halves

# ------------------------------------------------------------------ wing plate (one piece, printed front face down)
WING = dict(
    x_front=-45.0, x_centre_back=-48.5,          # centre: 3.5 mm on the pack posts (shared M2 x 10)
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
    tray_screws=[(46.0, 31.0), (63.0, 31.0)],
    lead_window=dict(y=(55.5, 66.5), z=(38.0, 52.0)),          # battery XT60 + balance lead through the arm web into the bay
    fan_window=dict(y=(70.5, 77.0), z=(26.0, 32.0)),           # front fan leads (along the tray top) through the web
    gusset_window=dict(x=(-60.0, -52.0), z=(22.0, 34.0)),      # harness passes along the bays behind the web
    swap_window=dict(y=(-11.5, 11.5), z=(4.6, 9.5)),           # matches the backpack front-plate window: swap plugs 3 + 4 leads
    centre_step=dict(y=17.0, z=26.0, y_low=19.8),              # recessed to x_recess: |y| > 17 above z 26 (shell top lip), |y| > 19.8 above z 9 (side lip)
    # Cross harness (left fans' 6 x 16 AWG + left battery pair): the slot along the wing plate between the backpack
    # front (x -50.5) and the shell lip / saddle (x -46.1 / -46.5) is 3.8 x 11.5 mm = 44 mm2 for a ~61 mm2 bundle, so the
    # harness runs back outboard of the backpack (|y| 32.6..37.6) and crosses behind the backpack cap below the hatch.
    harness_side=dict(x=(-80.6, -50.4), y=(32.6, 37.6), z=(14.0, 28.0)),
    harness_rear=dict(x=(-86.8, -80.6), y=(-33.0, 37.6), z=(4.0, 16.0)),   # ends at the ESC's inboard edge on the right
)

# ------------------------------------------------------------------ battery tray (printed flat)
BATT = dict(size=(74.0 + 4.0, 33.0, 31.0), listed=(74.0, 33.0, 31.0), mass_g=151.0,    # +4 mm length slack (listing +-1..5)
            x0=-36.0, y0=42.5)                                                       # rear end (0.8 from the nacelle lug), inner face
TRAY = dict(deck_z=(22.0, 26.0), x=(-45.0, 42.4), y=(37.9, 80.5),
            flange_x=(-45.0, -37.0), flange_z=(26.0, 36.0), flange_y=(39.0, 54.5),   # flange stops under the lead window
            flange2_y=(59.0, 69.5),
            strap_w=16.0 + 2.0, strap_t=3.0, strap_x=[(-30.0, -12.0), (14.0, 32.0)],
            strap_y_in=(39.3, 42.3), strap_y_out=(75.8, 78.8))

# ------------------------------------------------------------------ electronics (procurement.json cad_handoff)
FC = dict(board=(36.0, 36.0, 8.0), esc=(41.0, 41.0, 6.0), pattern=30.5, hole=4.0, mass_g=24.0, hw_g=6.0)
MTF01 = dict(size=(29.3, 17.0, 14.5), holes=(24.3, 12.0), hole_d=2.5, mass_g=4.5, cone_half_deg=21.0)
CAP = dict(d=13.0, h=25.0)
PLA_DENSITY = 1.24      # g/cm3
