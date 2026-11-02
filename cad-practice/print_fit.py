"""Print-fit numbers for FDM PLA parts on Shawn's printers (Bambu X1C, Bambu H2S, Elegoo Centauri Carbon).

Rules and evidence: PRINT-FIT.md in this folder. Every number assumes the release profiles' fit settings:
0.4 mm nozzle, 0.2 mm layers, 4 walls, X-Y hole and contour compensation 0, Bambu circle compensation off,
elephant-foot compensation 0.1 (X1C, Elegoo) or 0.15 (H2S). A profile that changes those voids the table.

Diameters are CAD diameters (what the model carries), not the size the printer produces.
Orientation is the hole axis in the PRINT pose: "vertical" = axis within 30 deg of Z, else "horizontal".
"""
import math

PROFILE = dict(nozzle=0.4, layer=0.2, walls=4, xy_hole_compensation=0.0, xy_contour_compensation=0.0,
               circle_compensation=False, elephant_foot={"X1C": 0.10, "Elegoo-CC": 0.10, "H2S": 0.15})

# Screw thread-forming pilots. kind "tap": screws made to self-tap plastic (Shawn's "M2 x N TAP" stock, ROBOTIS PTS,
# PT/ST tapping screws). kind "machine": metric machine screws (ISO 7380, DIN 912, ISO 7045) cutting their own thread
# in PLA: avoid; use a tap screw or a nut. Vertical tap values for M2 / M2.6 are MicroDuck as-built.
PILOT = {
    "tap": {
        "M2":   {"vertical": 1.70, "horizontal": 1.90},
        "M2.5": {"vertical": 2.20, "horizontal": 2.40},
        "M2.6": {"vertical": 2.10, "horizontal": 2.30},
        "M3":   {"vertical": 2.60, "horizontal": 2.80},
    },
    "machine": {
        "M2":   {"vertical": 1.90, "horizontal": 2.10},
        "M2.5": {"vertical": 2.30, "horizontal": 2.50},
        "M3":   {"vertical": 2.80, "horizontal": 3.00},
    },
}
PILOT_BAND = (-0.10, +0.15)        # accepted CAD deviation from PILOT: smaller binds, larger strips (MicroDuck 1.6-1.7 M2 TAP)
MAX_ENGAGEMENT_D = {"tap": 3.0, "machine": 2.0}   # thread engagement limit in screw diameters

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


def pilot(screw, orientation="vertical", kind="tap"):
    """CAD pilot diameter for `screw` ("M2", "M2.5", "M2.6", "M3") threading into PLA."""
    return PILOT[kind][screw][orientation]


def clear(screw, orientation="vertical"):
    """CAD clearance-hole diameter for `screw`."""
    return CLEAR[screw][orientation]


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
