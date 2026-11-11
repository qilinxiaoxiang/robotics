"""Shared inputs of the flight-pack strength check: geometry snapshot, materials, masses, load cases, printed sections.
Guide frame, mm, N, MPa (x forward, y left, z up). Everything here is read from cad/ (read-only) or cited in README.md.
"""
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
FL = H.parent
CAD = FL / "cad"
BUILD = CAD / "build"
OUT = H / "out"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(CAD))
G = 9.81

PARTS = ["wing_plate", "tray_L", "nacelle_inner_L", "nacelle_outer_L", "fc_bracket"]


def snapshot():
    """Commit and file hashes of the geometry every number here was computed from."""
    root = FL.parents[1].parent
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(root), "status", "--short", "--", str(CAD)], capture_output=True, text=True).stdout
    files = {f"build/{p}-world.stl": BUILD / f"{p}-world.stl" for p in PARTS}
    files.update({"flight_params.py": CAD / "flight_params.py", "build_pack.py": CAD / "build_pack.py", "build/build.json": BUILD / "build.json"})
    return dict(git_head=head, cad_dirty=bool(dirty.strip()),
                sha256={k: hashlib.sha256(v.read_bytes()).hexdigest()[:16] for k, v in files.items()})


# ------------------------------------------------------------------ materials (README "Materials" cites each source)
# TDS values: printed at 100 % infill, mostly annealed; "design" = the allowable used here (XY 0.8 x TDS low end, Z 0.5 x
# TDS: brand/colour/printer scatter 16-27 % and up to 50 % Z loss reported, see README), at room temperature.
MAT = {
    "PLA": dict(tds_xy=(39, 52.3), tds_z=(35, 40.5), E_xy=3.0e3, E_z=2.2e3, elong_z=(1.8, 7.5), hdt=(57, 60), tg=(60, 61),
                design_xy=32.0, design_z=17.5, hot55_factor=0.5,
                src="Bambu PLA Basic TDS; Polymaker PolyLite PLA TDS"),
    "PETG": dict(tds_xy=(48, 48), tds_z=(39, 39), E_xy=1.46e3, E_z=1.12e3, elong_z=(5.7, 5.7), hdt=(69, 69), tg=(68, 68),
                 design_xy=38.0, design_z=19.5, hot55_factor=0.8, src="Bambu PETG Basic TDS"),
    "PLA-CF": dict(tds_xy=(28.3, 38), tds_z=(12.5, 26), E_xy=2.8e3, E_z=2.15e3, elong_z=(0.75, 3.6), hdt=(54, 55), tg=(63, 63),
                   design_xy=22.6, design_z=6.3, hot55_factor=0.5, src="Bambu PLA-CF V3 TDS; Polymaker PolyLite PLA-CF TDS"),
    "PA-CF": dict(tds_xy=(81.7, 105), tds_z=(64, 67.7), E_xy=3.86e3, E_z=2.18e3, elong_z=(2.5, 5.2), hdt=(194, 215), tg=(70, 74),
                  design_xy=65.0, design_z=32.0, hot55_factor=0.9,
                  src="Bambu PAHT-CF TDS (dry); Polymaker PolyMide PA6-CF TDS (dry and 70 % RH)"),
}
NU = 0.35
SLICE = dict(walls=4, wall_mm=0.42 + 3 * 0.45, infill=0.30, infill_E_factor=0.15, pattern="gyroid",
             orange=dict(layer=0.2, bottom=3, top=5), black=dict(layer=0.1, bottom=3, top=5),
             src="cad/slices/release-FlightPack-D1-DRAFT/run-h2s/{Orange,Black}/plate_1.gcode header; Orange plate overridden "
                 "to 100 % infill in cad/make_slice_manifest.py (6fa0d176, not yet resliced)")
# gyroid 30 %: relative modulus about 0.1-0.2 (Gibson-Ashby bending-dominated scaling, rho^2 = 0.09 .. rho^1.5 = 0.16);
# 0.15 used, it only matters where a section is thicker than two walls.

# ------------------------------------------------------------------ masses (g), per side unless noted
import flight_params as Pm  # noqa: E402

BJ = json.loads((BUILD / "build.json").read_text())
GRAMS = json.loads((CAD / "slices" / "grams.json").read_text())


def part_g(name):
    """Slicer grams split by CAD volume within its colour plate (H2S slice, Generic PLA)."""
    col = BJ[name]["colour"]
    vols = {k: v["volume_cm3"] for k, v in BJ.items() if isinstance(v, dict) and v.get("colour") == col}
    return GRAMS["plates"][col]["H2S"]["grams"] * BJ[name]["volume_cm3"] / sum(vols.values())


# Masses and their positions: the current mass budget (mass_budget.json, v7 case: ARESWEI HDS001 fans 77 g, printed parts
# CAD volume x 1.24 g/cm3, i.e. solid; the Orange plate is 100 % infill, the Black nacelles are counted solid as an upper
# bound). Positions there are in the stand frame: z = guide + 120.
MB = json.loads((FL / "mass_budget.json").read_text())
MB_CASE = next(k for k in MB["cases"] if k.startswith("v7"))
MBR = {r["name"]: r for r in MB["cases"][MB_CASE]}
Z_STAND = 120.0


def mb_pos(name):
    p = np.array(MBR[name]["pos"], float)
    p[2] -= Z_STAND
    return p


FAN_G = MBR["fan FL"]["g"]                       # 77 g seller figure (CURRENT-STATE parts_flight_pack)
FAN_MASS_F, FAN_MASS_R = mb_pos("fan FL"), mb_pos("fan RL")    # fan mass centre, 45 mm down each axis
BATT_G = Pm.BATT["mass_g"]
SIDE = dict(fan_g=FAN_G, nacelle_g=MBR["nacelle_inner_L"]["g"] + MBR["nacelle_outer_L"]["g"], tray_g=MBR["tray_L"]["g"],
            batt_g=BATT_G, straps_leads_g=4.0 + 15.0)
SIDE["total_g"] = 2 * FAN_G + SIDE["nacelle_g"] + SIDE["tray_g"] + BATT_G + SIDE["straps_leads_g"]
PACK_G = round(sum(r["g"] for r in MB["cases"][MB_CASE]), 1)                      # 967.2 g
PACK_C = np.array([sum(r["g"] * r["pos"][i] for r in MB["cases"][MB_CASE]) / PACK_G for i in range(3)]) - [0, 0, Z_STAND]
# printed structure by plate: the Orange plate (wing plate, trays, FC bracket) prints at 100 % sparse infill
# (cad/make_slice_manifest.py processOverrides); the Black nacelles at the release 30 % gyroid
INFILL_E = dict(Orange=1.0, Black=SLICE["infill_E_factor"])


def fan_centre(which, side=+1):
    """Centre of the clamped collar on the fan axis (load point of the fan on the nacelle)."""
    t = 0.5 * (Pm.NAC["t0"] + Pm.NAC["t1"])
    return np.array(Pm.fan_point(which, t, side))


def thrust_dir(which):
    d = Pm.DIR[which]
    return np.array([-d * Pm.S, 0.0, Pm.C])            # opposite to the exhaust (DIR*S, 0, -C)


# ------------------------------------------------------------------ loads
THRUST_N = 0.980 * G          # seller figure at 16.8 V (CURRENT-STATE parts_flight_pack); not measured
PEAK = 1.5                    # gusts / controller peaks / spin-up overshoot
CASES_G = dict(vertical_impact=15.6, horizontal_strike=10.0)   # sim/out/cut/cut03.json; README "Loads" for the 10 g source
HANDLING_N = 2.0 * G * 1.5    # duck (1.9 kg) lifted by one nacelle, x 1.5 for a jerk
# motor torque: 40 A x 16.8 V seller point, 80 % motor efficiency, 4650 KV x 16.8 V x 0.8 loaded speed
P_SHAFT = 40 * 16.8 * 0.8
OMEGA = 4650 * 16.8 * 0.8 * 2 * math.pi / 60
Q_MOTOR = P_SHAFT / OMEGA     # N m on the stator; sim/flight.py: 30 % reaches the housing (stators recover the rest)
# M2 thread-forming screw in a printed 2.15 pilot: no published pull-out value (README). Range used: low 120 N (sparse
# shell, Z-direction loading, scaled from a 3.5 mm screw in 30 % PLA, ~8-13 N/mm x 4.8 mm, doubled for 4 solid walls
# round the pilot), high 260 N (thread shear on the pilot cylinder, 0.75 fill, tau 0.6 x 17.5 MPa x 4.8 mm). Low end used.
M2_PULLOUT = dict(low=120.0, high=260.0, per_mm_low=120.0 / 4.8)
M2_PRELOAD = dict(snug=0.10 / (0.3 * 0.002), strip=M2_PULLOUT["low"])   # T = K F d, K 0.3, 0.10 N m hand-snug


# ------------------------------------------------------------------ printed sections
def section_raster(mesh, origin, normal, axes, build_axis, skin_mm, wall_mm=SLICE["wall_mm"], step=0.1,
                   infill_E=SLICE["infill_E_factor"], clip=None):
    """Raster the cut of `mesh` by the plane (origin, normal) on the in-plane axes (a, b) = axes (indices into xyz).
    Returns pixel coords, solid-equivalent weights (1 for skins and walls, infill_E elsewhere) and the solid mask.
    build_axis: which of the two in-plane axes is the print build direction (0 or 1), or None if the build direction is
    the section normal (then every pixel is in-layer and walls are found in both in-plane directions).
    clip: optional (amin, amax, bmin, bmax) to keep one region of the cut."""
    from shapely import contains_xy
    from shapely.geometry import Polygon
    sec = mesh.section(plane_origin=origin, plane_normal=normal)
    if sec is None:
        return None
    polys = []
    for e in sec.discrete:
        if len(e) > 3:
            p = Polygon(e[:, list(axes)]).buffer(0)
            if p.area > 0.05:
                polys.append(p)
    shape = None
    for p in sorted(polys, key=lambda p: -p.area):
        shape = p if shape is None else shape.symmetric_difference(p)
    if clip is not None:
        from shapely.geometry import box
        shape = shape.intersection(box(clip[0], clip[2], clip[1], clip[3]))
    a0, b0, a1, b1 = shape.bounds
    A = np.arange(a0, a1, step) + step / 2
    B = np.arange(b0, b1, step) + step / 2
    AA, BB = np.meshgrid(A, B, indexing="ij")
    m = contains_xy(shape, AA, BB)

    def run_dist(mask, ax):
        """Distance (mm) from each solid pixel to the nearest empty pixel along one grid axis."""
        d = np.full(mask.shape, np.inf)
        n = mask.shape[ax]
        for direction in (1, -1):
            cur = np.zeros(mask.shape[1 - ax])
            rng = range(n) if direction > 0 else range(n - 1, -1, -1)
            acc = np.zeros(mask.shape)
            for i in rng:
                sl = (i, slice(None)) if ax == 0 else (slice(None), i)
                cur = np.where(mask[sl], cur + 1, 0)
                acc[sl] = cur
            d = np.minimum(d, acc * step - step / 2)
        return d
    w = np.full(m.shape, infill_E)
    if build_axis is None:
        solid = (run_dist(m, 0) <= wall_mm) | (run_dist(m, 1) <= wall_mm)
    else:
        inlayer = 1 - build_axis
        solid = (run_dist(m, build_axis) <= skin_mm) | (run_dist(m, inlayer) <= wall_mm)
    w[solid] = 1.0
    w[~m] = 0.0
    return dict(A=AA, B=BB, mask=m, w=w, step=step, shape=shape)


def bending_props(r, solid=False):
    """Weighted area, centroid and second moments of a raster section (solid=True ignores the printed structure)."""
    w = r["mask"].astype(float) if solid else r["w"]
    dA = r["step"] ** 2
    Aw = w.sum() * dA
    ca = (w * r["A"]).sum() * dA / Aw
    cb = (w * r["B"]).sum() * dA / Aw
    Ia = (w * (r["B"] - cb) ** 2).sum() * dA     # about the a-direction axis (stress varies with b)
    Ib = (w * (r["A"] - ca) ** 2).sum() * dA     # about the b-direction axis (stress varies with a)
    m = r["mask"] & (w > 0.99) if not solid else r["mask"]
    return dict(area_w=Aw, area=r["mask"].sum() * dA, ca=ca, cb=cb, Ia=Ia, Ib=Ib,
                cb_max=np.abs(r["B"][m] - cb).max(), ca_max=np.abs(r["A"][m] - ca).max())


def section_stress(r, axes, n_hat, F_ext, M_ext_about, solid=False):
    """Normal stress on a raster section from the loads on the loaded side of the cut.
    axes: (ia, ib) xyz indices of the raster axes; n_hat: unit normal pointing from the kept side into the loaded side;
    F_ext, M_ext_about: resultant force and the function giving its moment about a point (both acting on the loaded side).
    Unsymmetric bending with the weighted (printed) section: strain = e0 + ka u + kb v, stress = w E strain.
    Returns peak |sigma| (MPa) on solid pixels, its (a, b) location, torsion and shear resultants, and the props."""
    w = r["mask"].astype(float) if solid else r["w"]
    dA = r["step"] ** 2
    Aw = w.sum() * dA
    ca = (w * r["A"]).sum() * dA / Aw
    cb = (w * r["B"]).sum() * dA / Aw
    U, V = r["A"] - ca, r["B"] - cb
    Iuu, Ivv, Iuv = (w * U * U).sum() * dA, (w * V * V).sum() * dA, (w * U * V).sum() * dA
    ea, eb = np.eye(3)[axes[0]], np.eye(3)[axes[1]]
    c3 = np.zeros(3); c3[axes[0]] = ca; c3[axes[1]] = cb
    # centroid's third coordinate: on the cut plane (caller passes M about a point on the plane; shift handled by caller)
    M = np.asarray(M_ext_about(c3))
    F = np.asarray(F_ext)
    Mu, Mv = M @ np.cross(ea, n_hat), M @ np.cross(eb, n_hat)     # = int sigma u dA, int sigma v dA
    N = F @ n_hat
    ka, kb = np.linalg.solve([[Iuu, Iuv], [Iuv, Ivv]], [Mu, Mv])    # E * curvatures (MPa/mm)
    s = w * (N / Aw + ka * U + kb * V)
    s = np.where(r["mask"] & (w > 0.99) if not solid else r["mask"], s, 0.0)
    i = np.unravel_index(np.argmax(np.abs(s)), s.shape)
    return dict(sigma=float(abs(s[i])), at=(round(float(r["A"][i]), 2), round(float(r["B"][i]), 2)),
                torsion=float(M @ n_hat), shear=float(np.linalg.norm(F - N * n_hat)), N=float(N),
                props=dict(area=float(r["mask"].sum() * dA), area_w=float(Aw), centroid=(round(ca, 2), round(cb, 2)),
                           Iuu=float(Iuu), Ivv=float(Ivv), Iuv=float(Iuv)))


def resultant(loads):
    """loads: list of (F, P) -> (F_total, function giving the moment about a point)."""
    F = sum(np.asarray(f, float) for f, _ in loads)
    return F, (lambda c: sum(np.cross(np.asarray(p, float) - c, np.asarray(f, float)) for f, p in loads))
