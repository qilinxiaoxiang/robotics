"""Parameters of the flight-pack printed parts (guide frame, mm: x forward, y left, z up; stand-world z = guide z + 120).
Every fit number comes from ~/code/robotics/cad-practice/print_fit.py; every fan number from FAN (one dict).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "code/robotics/cad-practice"))
import print_fit as F  # noqa: E402

PRINTER = "H2S"                                  # default club printer; one STL serves all three (see HOLE notes)

# ------------------------------------------------------------------ the fan (not in hand; one dict, one source)
FAN = dict(
    source=("QX-Motor 50 mm 12-blade EDF maker drawing, banggood image d33d80c5-ce22-4e71-96e9-32272d8da90b.jpg, read by the "
            "coordinator 2026-11-10 (scratchpad edf-dims/drawing_crop_big.jpg): printed values lip OD 63.0, duct OD 54.0, "
            "housing lip face to rear rim 39.08, motor can OD 25.8; the rest scaled from the drawing +-0.4 mm; bore and leads "
            "from photos. Fans are not in hand: confirm on arrival."),
    lip_od=63.0, lip_t=(0.0, 5.5),               # axial positions t measured from the inlet lip face toward the motor
    band_od=55.5, band_t=(5.5, 9.4),             # raised band: upper axial stop
    duct_od=54.0, duct_t=(9.4, 36.9),            # straight clampable section (27.5 long)
    rim_od=55.0, rim_t=(36.9, 39.08),            # rear rim: lower axial stop
    stator_t=(39.08, 46.5), stator_od=(45.0, 25.8),
    motor_od=25.8, motor_t=(46.5, 75.8),
    bore=50.0,                                   # flow annulus inner duct diameter (photo estimate +-1.5)
    lead_t=(47.0, 49.0), lead_len=70.0, lead_od=1.6,   # three leads leave radially at the motor front ring
    mass_g=80.0,
)
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


# ------------------------------------------------------------------ nacelle clamp
NAC = dict(
    bore=F.clearance("locating") * 2 + FAN["duct_od"] + 0.0,   # 54.30: locating 0.15/side on the bought duct (vertical in print)
    wall=3.0,
    t0=FAN["duct_t"][0] + 0.5, t1=FAN["duct_t"][1] - 0.5,      # 9.9..36.4: 0.5 axial play to the band and the rim (scaled +-0.4)
    split_gap=0.6,                                             # 0.3 per half: screws draw the halves onto the duct (max squeeze 0.15/side)
    relief=FAN["rim_od"] + 1.5,                                # skirt bore below the collar clears the rim (56.5)
    keep_lip_r=FAN["lip_od"] / 2 + 1.0,                        # nothing within r 32.5 above t 9.7 (lip and band)
    ear_r_screw=F.clear("M2", "horizontal") / 2 + 0.0,
    screw_r=34.7,                                              # ear screw axis from the fan axis: 4.5 mm driver room past the 30.2 collar
    ear_out=4.0,                                               # ear material past the screw axis
    inner_y=7.0, outer_y=5.0,                                  # ear/web depth each side of the split (pilot side 7 >= 6, clamp side 5)
    web_x=(-17.5, -6.5), web_screw_t=33.0,
    ear_screw_t=(14.0, 32.0),
    lug_x=(-45.0, -36.8), lug_y=(70.0, 82.0), lug_top=58.0,     # inner half: bolts to the wing arm web front face (x -45)
    lug_screw_y=74.0, lug_screw_z=(37.0, 44.5, 52.0),
)
NAC["r_out"] = NAC["bore"] / 2 + NAC["wall"]
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
