"""Print-fit numbers for FDM PLA parts on Shawn's printers (Bambu X1C, Bambu H2S, Elegoo Centauri Carbon).

Rules and evidence: PRINT-FIT.md in this folder. Every number assumes the release profiles' fit settings:
0.4 mm nozzle, 0.2 mm layers, 4 walls, X-Y hole and contour compensation 0, Bambu circle compensation off,
elephant-foot compensation 0.1 to 0.15, classic walls. A profile that changes those voids the table.

Diameters are CAD diameters (what the model carries), not the size the printer produces.
Orientation is the hole axis in the PRINT pose: "vertical" = axis within 30 deg of Z, else "horizontal".
"""
import math

PROFILE = dict(nozzle=0.4, layer=0.2, walls=4, xy_hole_compensation=0.0, xy_contour_compensation=0.0,
               circle_compensation=False, elephant_foot={"X1C": 0.10, "Elegoo-CC": 0.10, "H2S": 0.15})

# Screw pilots. Shawn's rule: the screw kind is never prescribed. A pilot takes a machine screw (ISO 7380, DIN 912,
# ISO 7045) or a thread-forming screw (TAP, PT, ROBOTIS PTS) of its size, so kind "any" (the default) is the value both
# drive into: thread-forming screws still bite, machine screws form their thread without a drill.
# kind "tap" is the as-built MicroDuck evidence (TAP screws only); it is kept for checking old parts, never for new ones.
PILOT = {
    "any": {
        "M2":   {"vertical": 1.85, "horizontal": 2.05},
        "M2.5": {"vertical": 2.30, "horizontal": 2.50},
        "M2.6": {"vertical": 2.35, "horizontal": 2.55},
        "M3":   {"vertical": 2.80, "horizontal": 3.00},
    },
    "tap": {
        "M2":   {"vertical": 1.70, "horizontal": 1.90},
        "M2.5": {"vertical": 2.20, "horizontal": 2.40},
        "M2.6": {"vertical": 2.10, "horizontal": 2.30},
        "M3":   {"vertical": 2.60, "horizontal": 2.80},
    },
}
PILOT["machine"] = PILOT["any"]
PILOT_BAND = (-0.10, +0.15)        # accepted CAD deviation from PILOT: smaller binds, larger strips
MAX_ENGAGEMENT_D = {"any": 2.5, "tap": 3.0, "machine": 2.0}   # thread engagement limit in screw diameters

# Per-printer pilot offset (added to every pilot and clearance diameter). All three printers receive identical hole
# toolpaths from identical fit settings (PRINT-FIT.md, "Per-printer offsets"); the H2S value is PROVISIONAL: both plates
# printed at the club since the H2S arrived (RIG 1.3 on the H2S, the V1.40 battery pack) needed their pilots drilled
# while no earlier X1C or Elegoo duck pilot did. Replace it with the measured
# coupon result (coupons/pilot-coupon.stl) the day it is printed.
PRINTER_OFFSET = {"X1C": 0.00, "Elegoo-CC": 0.00, "H2S": 0.10}
PRINTER_OFFSET_STATUS = {"X1C": "as-built", "Elegoo-CC": "as-built", "H2S": "provisional, coupon not yet measured"}

# Screw stock and seats the pilots must accept (Shawn's rule: pilots through or deep enough for common lengths, seats for
# pan and button heads).
COMMON_LENGTHS = {"M2": (4, 6, 8, 10), "M2.5": (6, 8), "M2.6": (6, 8), "M3": (6, 8, 10, 12, 16)}
HEAD_SEAT = {             # (seat diameter, seat depth) that takes a pan head (ISO 7045 / ISO 14583) or a button head (ISO 7380)
    "M2": (4.6, 1.7), "M2.5": (5.6, 1.9), "M2.6": (5.6, 1.9), "M3": (6.3, 2.1)}


def pilot_depth(screw, clamped, max_len=None):
    """Blind pilot depth below the clamped stack's underside that takes the longest common length (or max_len) plus 1 mm.
    A pilot that cannot be that deep runs through."""
    L = max_len if max_len is not None else max(COMMON_LENGTHS[screw])
    return round(max(0.0, L - clamped) + 1.0, 2)


# Clearance (screw passes freely) holes
CLEAR = {"M2": {"vertical": 2.4, "horizontal": 2.6}, "M2.5": {"vertical": 2.9, "horizontal": 3.1},
         "M2.6": {"vertical": 3.0, "horizontal": 3.2}, "M3": {"vertical": 3.4, "horizontal": 3.6},
         "M5": {"vertical": 5.5, "horizontal": 5.8}, "M6": {"vertical": 6.6, "horizontal": 6.9}}

# Gap per side (CAD) between a male and a female feature, by fit class, for a VERTICAL female feature away from the bed.
# Negative = interference.
FIT_CLASS = {
    "press": (-0.05, 0.00),        # pins tapped in; vertical features only, never on the first layer
    "crush_rib": (-0.15, -0.10),   # rib tip interference; ribs triangular, base >= 0.8, vertical axis only
    "locating": (0.15, 0.20),      # dowels, cups over bosses, ribs in grooves: positions without force
    "sliding": (0.20, 0.30),       # hinges, pivot pins, lids, tongues sliding into slots
    "loose": (0.40, 0.60),         # drop-in, bought parts with their own tolerance, gloved assembly
}
ADD_HORIZONTAL = 0.10              # per side, when the female feature (hole, slot, groove) is horizontal in print
ADD_BED = 0.10                     # per side, when either mating surface lies in the first 0.4 mm and has no chamfer
BED_CHAMFER = 0.4                  # 45 deg chamfer on any fit edge in the first layer (male: edge; female: mouth)
BED_ZONE = 0.4                     # height above the bed counted as first-layer zone
MIN_HOLE = 1.5                     # smallest printed hole kept as a hole; below it, mark a dimple and drill-free redesign

VERTICAL_LIMIT_DEG = 30.0          # axis within this angle of Z counts as vertical
TEARDROP_UP_TOL_DEG = 15.0         # teardrop tip must point within this angle of +Z (hole) or -Z (male cylinder)


def pilot(screw, orientation="vertical", kind="any", printer=None):
    """CAD pilot diameter for `screw` ("M2", "M2.5", "M2.6", "M3") threading into PLA, for any screw kind of that size,
    plus the printer's offset when `printer` ("X1C", "H2S", "Elegoo-CC") is given."""
    return round(PILOT[kind][screw][orientation] + (PRINTER_OFFSET[printer] if printer else 0.0), 3)


def clear(screw, orientation="vertical", printer=None):
    """CAD clearance-hole diameter for `screw`, plus the printer's offset."""
    return round(CLEAR[screw][orientation] + (PRINTER_OFFSET[printer] if printer else 0.0), 3)


def clearance(fit_class, orientation="vertical", at_bed=False, chamfered=False):
    """Minimum CAD gap per side for `fit_class`, with the orientation and first-layer adders."""
    lo = FIT_CLASS[fit_class][0]
    if orientation == "horizontal":
        lo += ADD_HORIZONTAL
    if at_bed and not chamfered:
        lo += ADD_BED
    return round(lo, 3)


# ------------------------------------------------------------------ print-pose geometry
def _rot(axis, deg):
    a = math.radians(deg)
    n = math.sqrt(sum(c * c for c in axis))
    x, y, z = (c / n for c in axis)
    c, s, C = math.cos(a), math.sin(a), 1 - math.cos(a)
    return [[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C]]


def to_print(vec, print_rot):
    """Rotate a part-frame direction into the print pose. print_rot = [((ax, ay, az), deg), ...] applied in order
    (the cadlib._to_print convention; translations do not matter for directions)."""
    v = list(vec)
    for axis, deg in print_rot:
        R = _rot(axis, deg)
        v = [sum(R[i][j] * v[j] for j in range(3)) for i in range(3)]
    return v


def tilt_deg(vec):
    """Angle between a direction and the print Z axis (0 = vertical)."""
    n = math.sqrt(sum(c * c for c in vec))
    return math.degrees(math.acos(min(1.0, abs(vec[2]) / n)))


def orientation(axis_part, print_rot):
    return "vertical" if tilt_deg(to_print(axis_part, print_rot)) <= VERTICAL_LIMIT_DEG else "horizontal"
