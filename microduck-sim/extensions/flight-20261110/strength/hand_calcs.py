"""Hand calculations of the flight-pack printed parts, every load case, left side (the right side is the mirror).
Sections are cut from the built meshes and weighted for the printed structure (4 walls, 30 % gyroid, skins);
bolt groups are rigid plates on compression-only contact with tension-only screws.
    /tmp/microduck-cad-venv/bin/python strength/hand_calcs.py      -> strength/out/hand_calcs.json  (seconds)
"""
import json
import math

import numpy as np
import trimesh

from common import (BUILD, G, HANDLING_N, M2_PRELOAD, M2_PULLOUT, MAT, OUT, PACK_G, PEAK, Pm, Q_MOTOR, SIDE, SLICE,
                    THRUST_N, fan_centre, resultant, section_raster, section_stress, snapshot, thrust_dir)

PLA = MAT["PLA"]
EX, EY, EZ = np.eye(3)

# ------------------------------------------------------------------ the side assemblies: masses and their centroids
BJ = json.loads((BUILD / "build.json").read_text())
batt_c = np.array([Pm.BATT["x0"] + Pm.BATT["size"][0] / 2, Pm.BATT["y0"] + Pm.BATT["size"][1] / 2,
                   Pm.TRAY["deck_z"][1] + Pm.BATT["size"][2] / 2])
nac_c = 0.5 * (np.array(BJ["nacelle_inner_L"]["centroid"]) + np.array(BJ["nacelle_outer_L"]["centroid"]))
tray_c = np.array(BJ["tray_L"]["centroid"])
FAN_F, FAN_R = fan_centre("front"), fan_centre("rear")
NAC_MASSES = [(SIDE["fan_g"], FAN_F), (SIDE["fan_g"], FAN_R), (SIDE["nacelle_g"], nac_c), (7.5, (FAN_F + FAN_R) / 2)]
TRAY_MASSES = [(SIDE["batt_g"], batt_c), (SIDE["tray_g"], tray_c), (11.5, batt_c)]
NAC_TIP_FRONT = np.array([64.0, 110.0, 50.0])      # nacelle front end (build.json bounds x max 64.3), mid height
NAC_TIP_REAR = np.array([-88.0, 110.0, 50.0])
NAC_TOP_OUT = np.array([FAN_F[0], 138.0, 64.0])    # hand round the front collar's outer top


def inertia(masses, acc_g):
    """Loads (F, P) of masses (g) under acceleration acc_g (vector, in g): F = -m a (the part's inertia)."""
    return [(-m / 1000 * G * np.asarray(acc_g, float), np.asarray(p, float)) for m, p in masses]


def thrust(k=PEAK):
    return [(k * THRUST_N * thrust_dir("front"), FAN_F), (k * THRUST_N * thrust_dir("rear"), FAN_R)]


# strike force on a nacelle end when the duck topples after landing: sim 10 ms mean, both boxes, MuJoCo soft contact
PROBE = {k: json.loads((OUT / "sim_probe" / f"{k}.json").read_text()) for k in ("cut03", "hover_nominal",
                                                                                 "ARE_thrust80_table_down_s2", "comx+10_table_up_s2_air")}
TOPPLE_N = max(PROBE["cut03"]["nac"]["peak_10ms_mean_N"], PROBE["hover_nominal"]["nac"]["peak_10ms_mean_N"])

# Load cases on one side. Each: loads on the nacelle assembly, loads on the tray assembly.
# inertia() takes the acceleration with gravity folded in as +1 g up; the sim's 15.6 g is the trunk's kinematic upward
# acceleration at touchdown (flight.py: d.qacc, gravity excluded), so the equivalent is 15.6 + 1 = 16.6 g up.
IMPACT_G = 15.6 + 1.0
CASES = {
    "thrust_1.5x_on_ground": dict(nac=thrust() + inertia(NAC_MASSES, (0, 0, 1)), tray=inertia(TRAY_MASSES, (0, 0, 1)),
                                  src="980 g seller thrust x 1.5 per fan, feet still on the ground (no inertia relief), weight 1 g"),
    "vertical_impact_15.6g": dict(nac=inertia(NAC_MASSES, (0, 0, IMPACT_G)), tray=inertia(TRAY_MASSES, (0, 0, IMPACT_G)),
                                  src="throttle cut from 0.3 m, 2.44 m/s, trunk peak 15.6 g upward (sim qacc, gravity excluded) through the feet, so the side masses carry 16.6 g downward (strength/out/sim_probe/cut03.json: feet 304 N, nacelles 0 at that instant)"),
    "fore_aft_10g": dict(nac=inertia(NAC_MASSES, (10, 0, 1)), tray=inertia(TRAY_MASSES, (10, 0, 1)),
                         src="10 g horizontal on the side masses (inertia only, trunk struck elsewhere)"),
    "lateral_10g": dict(nac=inertia(NAC_MASSES, (0, -10, 1)), tray=inertia(TRAY_MASSES, (0, -10, 1)),
                        src="10 g sideways on the side masses (inertia only)"),
    "handling_lift_by_nacelle": dict(nac=[(HANDLING_N * EZ, NAC_TOP_OUT)] + inertia(NAC_MASSES, (0, 0, 1)),
                                     tray=inertia(TRAY_MASSES, (0, 0, 1)),
                                     src="duck (1.9 kg, 2 kg used) lifted by one nacelle's front collar, x 1.5 jerk"),
    "topple_strike_front_end": dict(nac=[(-TOPPLE_N * EX, NAC_TIP_FRONT)], tray=[],
                                    src=(f"duck falls on its face after the fans stop; floor pushes the nacelle front end rearward, {TOPPLE_N:.0f} N "
                                         "= sim 10 ms mean of the nacelle-box contact (cut03 / hover landing), all on one nacelle; soft "
                                         "MuJoCo contact (20 ms), a hard floor gives more")),
    "topple_strike_rear_end": dict(nac=[(TOPPLE_N * EX, NAC_TIP_REAR)], tray=[],
                                   src="duck falls on its back; floor pushes the nacelle rear end forward; same force"),
}

ROWS = []


def row(part, case, what, peak, at, allow_dir, allowable, note="", fea=None):
    sf = allowable / peak if peak > 1e-9 else float("inf")
    ROWS.append(dict(part=part, case=case, check=what, peak_MPa_or_N=round(peak, 2), location=at, direction=allow_dir,
                     allowable=round(allowable, 1), safety_factor=round(sf, 2), passes=bool(sf >= 2.0), note=note))


# ------------------------------------------------------------------ 1. wing plate root and arm sections (y = const)
wing = trimesh.load(BUILD / "wing_plate-world.stl", force="mesh")
WING_SECTIONS = {}
for y in (21.0, 29.0, 31.0, 35.0, 45.0, 60.0):
    WING_SECTIONS[y] = section_raster(wing, [0, y, 0], [0, 1, 0], (0, 2), build_axis=0, skin_mm=0.6)


def wing_checks(case, L):
    loads = L["nac"] + L["tray"]
    F, Mf = resultant(loads)
    for y, r in WING_SECTIONS.items():
        def M_about(c2, y=y):
            return Mf(np.array([c2[0], y, c2[2]]))
        s = section_stress(r, (0, 2), EY, F, M_about)
        ss = section_stress(r, (0, 2), EY, F, M_about, solid=True)
        # torsion of the open section (thin rectangles, J = sum b t^3 / 3 from the raster: per-row max run)
        tau = torsion_open(r, s["torsion"])
        row("wing_plate", case, f"bending at y {y:.0f}", s["sigma"], f"y {y:.0f}, (x, z) {s['at']}", "in-layer (sigma_yy, layers x = const)",
            PLA["design_xy"], f"solid-section value {ss['sigma']:.2f} MPa (for the FEA comparison); printed/solid {s['sigma'] / max(ss['sigma'], 1e-9):.2f}")
        if abs(tau) > 0.5:
            row("wing_plate", case, f"torsion shear at y {y:.0f}", abs(tau), f"y {y:.0f}", "in-layer shear",
                0.55 * PLA["design_xy"], "open-section torsion")


def torsion_open(r, T):
    """Shear stress of an open thin-walled section: tau = T t_max / J, J = sum over strips of b t^3 / 3 (raster runs along
    the longer direction)."""
    m = r["mask"]
    st = r["step"]
    # thickness of each column (along a = x) and of each row (along b = z): take the decomposition into the longer strips
    tx = m.sum(axis=0) * st          # thickness in x at each z row
    J = (tx[tx > 0] ** 3 / 3).sum() * st
    tmax = tx.max()
    return T * tmax / J if J > 0 else 0.0


# ------------------------------------------------------------------ 2. bolt groups (rigid plate, compression-only face)
def bolt_group(face_rects, bolts, F, M_about, plane_x=-45.0, normal=-EX):
    """Rigid plate pressed on a plane face (normal pointing from the part into the web). face_rects: (y0, y1, z0, z1);
    bolts: (y, z). Loads on the part. Returns bolt tensions (N), bolt shear (N), peak contact pressure (MPa)."""
    st = 0.25
    pts = []
    for (y0, y1, z0, z1) in face_rects:
        Y, Z = np.meshgrid(np.arange(y0, y1, st) + st / 2, np.arange(z0, z1, st) + st / 2)
        pts.append(np.c_[Y.ravel(), Z.ravel()])
    P = np.vstack(pts)
    kc = 1.0 * st * st          # contact stiffness per pixel (relative)
    kb = 40.0                   # bolt stiffness (relative): a screw is much stiffer than its share of the face
    B = np.array(bolts, float)
    c = np.array([plane_x, P[:, 0].mean(), P[:, 1].mean()])
    Mc = M_about(c)
    nx = normal[0]
    # generalized coordinates q = (u_x, theta_y, theta_z) of the rigid part; approach toward the web at face point (y, z):
    # d = n . (u + theta x r) = nx (u_x + theta_y (z - cz) - theta_z (y - cy)); spring force on the part -k d n
    # (contact active for d > 0, screws for d < 0); conjugate external forces (F_x, M_y, M_z) about c.
    def A_of(Q):
        return np.c_[np.full(len(Q), nx), nx * (Q[:, 1] - c[2]), -nx * (Q[:, 0] - c[1])]
    Ac, Ab = A_of(P), A_of(B)
    rhs = np.array([F[0], Mc[1], Mc[2]])
    act_c = np.ones(len(P), bool)
    act_b = np.ones(len(B), bool)
    for _ in range(80):
        K = (Ac.T * (kc * act_c)) @ Ac + (Ab.T * (kb * act_b)) @ Ab
        q = np.linalg.solve(K + 1e-12 * np.eye(3), rhs)
        dc, db = Ac @ q, Ab @ q
        nc, nb = dc > 0, db < 0
        if (nc == act_c).all() and (nb == act_b).all():
            break
        act_c, act_b = nc, nb
    tension = np.where(act_b, -kb * db, 0.0)
    pres = np.where(act_c, kc * dc, 0.0) / (st * st)
    # in-plane force and the twist about x go to the screws in shear (no friction counted)
    Fs = F - (F @ normal) * normal
    Mx = Mc[0]
    rb = B - B.mean(axis=0)
    J = (rb ** 2).sum()
    sh = []
    for i in range(len(B)):
        twist = Mx * np.array([-rb[i, 1], rb[i, 0]]) / J if J > 1e-9 else np.zeros(2)
        sh.append(float(np.hypot(Fs[1] / len(B) + twist[0], Fs[2] / len(B) + twist[1])))
    return tension, np.array(sh), float(pres.max())


LUG_FACE = [(Pm.NAC["lug_y"][0], Pm.NAC["lug_y"][1], BJ["nacelle"]["bed_z"], Pm.NAC["lug_top"])]
LUG_BOLTS = [(Pm.NAC["lug_screw_y"], z) for z in Pm.NAC["lug_screw_z"]]
TRAY_FACE = [(Pm.TRAY["flange_y"][0], Pm.TRAY["flange_y"][1], 26.0, 36.0), (Pm.TRAY["flange2_y"][0], Pm.TRAY["flange2_y"][1], 26.0, 36.0),
             (Pm.TRAY["y"][0], Pm.TRAY["y"][1], Pm.TRAY["deck_z"][0], Pm.TRAY["deck_z"][1])]
TRAY_BOLTS = [tuple(p) for p in Pm.WING["tray_screws"]]


def joint_checks(case, L):
    for name, loads, face, bolts, part in (("nacelle lug to arm web (3 x M2 x 10)", L["nac"], LUG_FACE, LUG_BOLTS, "nacelle_inner_L"),
                                           ("tray flange to arm web (2 x M2 x 10)", L["tray"], TRAY_FACE, TRAY_BOLTS, "tray_L")):
        if not loads:
            continue
        F, Mf = resultant(loads)
        T, S, p = bolt_group(face, bolts, F, Mf)
        i = int(np.argmax(T))
        row(part, case, f"{name}: screw pull-out", float(T.max()), f"screw at (y, z) {bolts[i]}", "thread in a horizontal pilot",
            M2_PULLOUT["low"], f"tensions {np.round(T, 1).tolist()} N; low-end M2 capacity {M2_PULLOUT['low']:.0f} N (no published value)")
        bear = float(S.max()) / (2.0 * (10.0 - 5.2))
        row(part, case, f"{name}: thread bearing", bear, "pilot wall", "in-layer bearing", 1.2 * PLA["design_xy"],
            f"screw shear {np.round(S, 1).tolist()} N on d 2 x 4.8 mm, friction not counted")


# ------------------------------------------------------------------ 3. nacelle inner half: lug root and the beam to the front fan
nin = trimesh.load(BUILD / "nacelle_inner_L-world.stl", force="mesh")
NAC_SECTIONS = {}
for x in (-36.0, -25.0, -12.0, 0.0, 10.0):
    NAC_SECTIONS[x] = section_raster(nin, [x, 0, 0], [1, 0, 0], (1, 2), build_axis=1, skin_mm=0.3)
LUG_ROOT = section_raster(nin, [0, 80.5, 0], [0, 1, 0], (0, 2), build_axis=1, skin_mm=0.3,
                          clip=(Pm.NAC["lug_x"][0], Pm.NAC["lug_x"][1] + 6, 30, 70))


def nacelle_checks(case, L):
    loads = L["nac"]
    if not loads:
        return
    # loads that act forward of a cut x (front fan and anything ahead of it); the nacelle is held at the lug (x -45..-36.8)
    for x, r in NAC_SECTIONS.items():
        fwd = [(f, p) for f, p in loads if p[0] > x]
        if not fwd:
            continue
        F, Mf = resultant(fwd)
        s = section_stress(r, (1, 2), EX, F, lambda c2, x=x: Mf(np.array([x, c2[1], c2[2]])))
        row("nacelle_inner_L", case, f"beam bending at x {x:.0f}", s["sigma"], f"x {x:.0f}, (y, z) {s['at']}",
            "in-layer (sigma_xx, layers z = const)", PLA["design_xy"])
    F, Mf = resultant(loads)
    s = section_stress(LUG_ROOT, (0, 2), -EY, F, lambda c2: Mf(np.array([c2[0], 80.5, c2[2]])))
    row("nacelle_inner_L", case, "lug-to-collar root (y 80.5)", s["sigma"], f"(x, z) {s['at']}",
        "sigma_yy in-layer; z-varying part crosses layers", PLA["design_z"], "allowable taken across layers (bending about x puts layer lines in tension at the root ends)")


# ------------------------------------------------------------------ 4. tray deck bending (cantilever from the web face)
tray = trimesh.load(BUILD / "tray_L-world.stl", force="mesh")
TRAY_SECTIONS = {x: section_raster(tray, [x, 0, 0], [1, 0, 0], (1, 2), build_axis=1, skin_mm=0.6) for x in (-36.5, -29.0, -20.0, 15.0)}


def tray_checks(case, L):
    loads = L["tray"]
    if not loads:
        return
    # the battery load spread over its length: 8 slices from x0 to x0 + length
    lx = Pm.BATT["size"][0]
    spread = []
    for f, p in loads:
        for k in range(8):
            q = np.array(p, float); q[0] = Pm.BATT["x0"] + lx * (k + 0.5) / 8
            spread.append((np.asarray(f) / 8, q))
    for x, r in TRAY_SECTIONS.items():
        fwd = [(f, p) for f, p in spread if p[0] > x]
        F, Mf = resultant(fwd)
        s = section_stress(r, (1, 2), EX, F, lambda c2, x=x: Mf(np.array([x, c2[1], c2[2]])))
        row("tray_L", case, f"deck bending at x {x:.1f}", s["sigma"], f"x {x:.1f}, (y, z) {s['at']}", "in-layer", PLA["design_xy"])
    # flange-to-deck joint (layer interface z 26): screw tension pulls the flange, the deck pushes; interlayer tension
    F, Mf = resultant(loads)
    T, S, p = bolt_group(TRAY_FACE, TRAY_BOLTS, F, Mf)
    A_if = (Pm.TRAY["flange_x"][1] - Pm.TRAY["flange_x"][0]) * ((Pm.TRAY["flange_y"][1] - Pm.TRAY["flange_y"][0]) + (Pm.TRAY["flange2_y"][1] - Pm.TRAY["flange2_y"][0]))
    Mif = T.sum() * (31.0 - 26.0)
    Sif = A_if / 8.0 * 8.0 ** 2 / 6
    sig = Mif / Sif + T.sum() / A_if
    row("tray_L", case, "flange-to-deck layer interface (z 26)", sig, "flange root", "across layers", PLA["design_z"],
        f"screw pull {T.sum():.1f} N at 5 mm above the interface")


# ------------------------------------------------------------------ 5. shared post screws (whole pack on the duck)
POSTS = [(16.1, 26.0), (16.1, -36.5), (-16.1, 26.0), (-16.1, -36.5)]


def post_checks():
    pack_c = np.array([-16.0, -3.2, 34.7])
    duck_c = np.array([-7.6, 0.3, 25.3])
    cases = {
        "vertical_impact_15.6g": [(-PACK_G / 1000 * G * IMPACT_G * EZ, pack_c)],
        "thrust_1.5x_on_ground": [(4 * PEAK * THRUST_N * EZ - PACK_G / 1000 * G * EZ, pack_c)],
        "fore_aft_10g": [(-PACK_G / 1000 * G * 10 * EX, pack_c)],
        "topple_strike_front_end": [(-TOPPLE_N * EX, NAC_TIP_FRONT)],
    }
    for case, loads in cases.items():
        F, Mf = resultant(loads)
        # wing centre on the pack posts: the centre face (x -45) bears on the pack; loads on the wing, normal into the pack +x
        face = [(-18.6, 18.6, -40.5, 29.0)]
        T, S, p = bolt_group(face, POSTS, F, Mf, plane_x=-45.0, normal=EX)
        row("wing_plate + OpenRB pack posts", case, "post screw pull-out (4 x M2 x 10, 4.5 mm bite)", float(T.max()),
            "post pilots in the OpenRB pack", "thread", M2_PULLOUT["low"] * 4.5 / 4.8, f"tensions {np.round(T, 1).tolist()} N")
        # tear-out of the upper post holes toward the top edge (1.75 mm ligament above d 2.5 hole) under shear S
        e = Pm.WING["centre_top"] - 26.0
        A = 2 * 3.5 * (e - 1.25 * math.cos(math.radians(40)))
        row("wing_plate", case, "upper post hole tear-out (1.75 mm ligament)", float(S.max()) / A, "centre plate top edge",
            "in-layer shear", 0.55 * PLA["design_xy"], f"screw shear {np.round(S, 1).tolist()} N; shear-out area {A:.1f} mm2")


# ------------------------------------------------------------------ 6. clamp ring under screw preload (membrane estimate)
def clamp_checks():
    N = Pm.NAC
    L_col = N["t1"] - N["t0"]
    for lab, P in (("snug", min(M2_PRELOAD["snug"], M2_PULLOUT["high"])), ("tightened to strip", M2_PULLOUT["high"])):
        end = 2 * P      # front block: two screws on one end of the front collar
        sig = end / (N["wall"] * L_col)
        row("nacelle halves", f"clamp_preload_{lab}", "collar hoop membrane at the screw block", sig, "collar beside the front block",
            "in-layer hoop", PLA["design_xy"], f"{P:.0f} N per M2; uniform contact assumed")
        # the screws pull along y at screw_r, the wall mid-plane is at r_in + wall / 2: the eccentricity bends the wall
        # where the block ends (FEA: out/fea_nacelle_outer_preload.json, peak on that corner)
        e = N["screw_r"] - (N["r_out"] - N["wall"] / 2)
        b = L_col * Pm.C
        sigb = 6 * end * e / (b * N["wall"] ** 2) + end / (b * N["wall"])
        row("nacelle halves", f"clamp_preload_{lab}", "collar wall bending where the screw block ends", sigb,
            "collar at the end of the front and rear blocks", "in-layer hoop", PLA["design_xy"],
            f"{P:.0f} N per M2, eccentricity {e:.1f} mm, wall {N['wall']} mm over {b:.1f} mm; the seams stay open with the largest fan")
        # head seat bearing in the outer half (pan head d 3.8 on the counterbore floor)
        A = math.pi / 4 * (3.8 ** 2 - 2.7 ** 2)
        row("nacelle_outer_L", f"clamp_preload_{lab}", "screw head bearing on the seat floor", P / A, "head seat",
            "compression (horizontal screw: in-layer)", 1.5 * PLA["design_xy"], "compressive bearing allowable 1.5 x tensile")
    # thrust held by the ear pockets (upper face) and the clamp friction
    Fear = PEAK * THRUST_N / 2
    A = (Pm.FAN["ear_w"] - Pm.TOL) * (Pm.FAN["ear_r"] - Pm.FAN["duct_od"] / 2 - Pm.TOL)
    row("nacelle halves", "thrust_1.5x_on_ground", "ear on the pocket roof: bearing", Fear / A, "pocket roof t 16.1", "compression",
        PLA["design_xy"], f"{Fear:.1f} N per ear, smallest ear {A:.0f} mm2")
    # pocket roof as a ledge: shear through the collar wall above the pocket over the pocket width (both halves)
    A_sh = 2 * N["ear_pocket"]["half_w"] * N["wall"]
    row("nacelle halves", "thrust_1.5x_on_ground", "pocket roof shear-out", PEAK * THRUST_N / 2 / A_sh, "collar above each ear",
        "across layers (axial shear on z planes)", 0.55 * PLA["design_z"])
    # downward (drop) the pockets are open into the skirt: friction alone holds the fan
    Fdown = SIDE["fan_g"] / 1000 * G * IMPACT_G
    for lab, P in (("snug", min(M2_PRELOAD["snug"], M2_PULLOUT["high"])), ("10 % preload left after creep", 0.1 * min(M2_PRELOAD["snug"], M2_PULLOUT["high"]))):
        Nn = 4 / math.pi * 2.5 * P * 2        # cos-distributed contact, 2.5 screws per half, two halves
        cap = 0.3 * Nn
        row("nacelle halves", "vertical_impact_15.6g", f"fan held downward by clamp friction ({lab})", Fdown, "foam tape liner",
            "friction mu 0.3", cap, f"normal force {Nn:.0f} N; the tape's own adhesion is extra")
    # motor reaction torque on the ears
    Qh = Q_MOTOR * 1.5 * 1000
    row("nacelle halves", "motor_torque", "motor reaction torque on the ear pocket sides", Qh / (2 * Pm.FAN["ear_r"]) / (Pm.NAC["t1"] - 17.9) / 2.0,
        "pocket side", "bearing", PLA["design_xy"], f"Q = {Q_MOTOR * 1000:.0f} N mm full motor torque x 1.5 (only ~30 % reaches the housing)")


def main():
    for case, L in CASES.items():
        wing_checks(case, L)
        joint_checks(case, L)
        nacelle_checks(case, L)
        tray_checks(case, L)
    post_checks()
    clamp_checks()
    res = dict(geometry=snapshot(), side_masses_g=SIDE, topple_strike_N=TOPPLE_N,
               cases={k: v["src"] for k, v in CASES.items()}, slicing=SLICE,
               rows=ROWS)
    (OUT / "hand_calcs.json").write_text(json.dumps(res, indent=1, default=float))
    worst = sorted(ROWS, key=lambda r: r["safety_factor"])
    for r in worst[:40]:
        print(f"{r['safety_factor']:6.2f}  {r['part']:22s} {r['case']:28s} {r['check']:50s} {r['peak_MPa_or_N']:8.2f}  {r['location']}")


if __name__ == "__main__":
    main()
