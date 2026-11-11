"""Hand calculations of the flight-pack printed parts, every load case, left side (the right side is the mirror).
Sections are cut from the built meshes and weighted for the printed structure (4 walls, 30 % gyroid, skins);
bolt groups are rigid plates on compression-only contact with tension-only screws.
    /tmp/microduck-cad-venv/bin/python strength/hand_calcs.py      -> strength/out/hand_calcs.json  (seconds)
"""
import json
import math

import numpy as np
import trimesh

from common import (BUILD, FAN_MASS_F, FAN_MASS_R, G, HANDLING_N, INFILL_E, M2_PRELOAD, M2_PULLOUT, MAT, MB_CASE, OUT,
                    PACK_C, PACK_G, PEAK, Pm, Q_MOTOR, SIDE, SLICE, THRUST_N, fan_centre, resultant, section_raster,
                    section_stress, snapshot, thrust_dir, pullout)

PLA = MAT["PLA"]
EX, EY, EZ = np.eye(3)

# ------------------------------------------------------------------ the side assemblies: masses and their centroids
BJ = json.loads((BUILD / "build.json").read_text())
batt_c = np.array([Pm.BATT["x0"] + Pm.BATT["size"][0] / 2, Pm.BATT["y0"] + Pm.BATT["size"][1] / 2,
                   Pm.TRAY["deck_z"][1] + Pm.BATT["size"][2] / 2])
nac_c = 0.5 * (np.array(BJ["nacelle_inner_L"]["centroid"]) + np.array(BJ["nacelle_outer_L"]["centroid"]))
tray_c = np.array(BJ["tray_L"]["centroid"])
FAN_F, FAN_R = fan_centre("front"), fan_centre("rear")
# fan masses at their own centre (45 mm down each axis, mass_budget.json); thrust acts at the collar (FAN_F / FAN_R)
NAC_MASSES = [(SIDE["fan_g"], FAN_MASS_F), (SIDE["fan_g"], FAN_MASS_R), (SIDE["nacelle_g"], nac_c), (7.5, (FAN_F + FAN_R) / 2)]
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
# both arms (480610d1: the camera-cable notch at y 37.8..43, z 47..54 is on the left arm only); y 40 / 42 cut the notch,
# y 60 the 11 x 18 lead window
WING_Y = (21.0, 29.0, 31.0, 35.0, 40.0, 42.0, 45.0, 60.0)
for y in WING_Y + tuple(-v for v in WING_Y):
    WING_SECTIONS[y] = section_raster(wing, [0, y, 0], [0, 1, 0], (0, 2), build_axis=0, skin_mm=0.6,
                                      infill_E=INFILL_E[BJ["wing_plate"]["colour"]])


def mirror_y(loads):
    return [(np.asarray(f, float) * [1, -1, 1], np.asarray(p, float) * [1, -1, 1]) for f, p in loads]


def wing_checks(case, L, sides=(1, -1)):
    """Sections of the arm(s) carrying the case's one-side loads: the left arm takes L, the right arm the mirror of L
    (symmetric cases load both; a one-nacelle case names its side)."""
    for y, r in WING_SECTIONS.items():
        s_ = 1 if y > 0 else -1
        if s_ not in sides:
            continue
        loads = L["nac"] + L["tray"] if s_ > 0 else mirror_y(L["nac"] + L["tray"])
        F, Mf = resultant(loads)

        def M_about(c2, y=y, Mf=Mf):
            return Mf(np.array([c2[0], y, c2[2]]))
        s = section_stress(r, (0, 2), s_ * EY, F, M_about)
        ss = section_stress(r, (0, 2), s_ * EY, F, M_about, solid=True)
        # Saint-Venant torsion of the real section shape (Prandtl stress function on the raster, free warping)
        tau = torsion_sv(r, s["torsion"])
        row("wing_plate", case, f"bending at y {y:.0f}", s["sigma"], f"y {y:.0f}, (x, z) {s['at']}", "in-layer (sigma_yy, layers x = const)",
            PLA["design_xy"], f"solid-section value {ss['sigma']:.2f} MPa (for the FEA comparison); printed/solid {s['sigma'] / max(ss['sigma'], 1e-9):.2f}")
        if abs(tau) > 0.5:
            row("wing_plate", case, f"torsion shear at y {y:.0f}", abs(tau), f"y {y:.0f}", "in-layer shear",
                0.55 * PLA["design_xy"], f"Saint-Venant torsion, T {s['torsion']:.0f} N mm, J {r['J']:.0f} mm4 (free warping; FEA has the restraint)")
            vm = math.hypot(s["sigma"], math.sqrt(3) * abs(tau))
            row("wing_plate", case, f"combined (von Mises) at y {y:.0f}", vm, f"y {y:.0f}", "in-layer", PLA["design_xy"],
                "peak bending and peak torsion shear added as if at one point (upper bound)")


def torsion_sv(r, T, step=0.1):
    """Saint-Venant torsion of the section on its raster: Prandtl stress function, laplacian(phi) = -2 inside, phi = 0 on
    the boundary; J = 2 int phi dA, tau = |grad phi| T / J. Works for open, closed-off and solid shapes alike (a solid
    8.5 x 19 rectangle at 0.1 mm: J within 0.1 %, tau within 3 % of Roark). Cached on r."""
    if "J" not in r:
        import scipy.sparse as sp
        import scipy.sparse.linalg as spl
        k = max(1, int(round(step / r["step"])))
        m = r["mask"][::k, ::k]
        h = r["step"] * k
        m = np.pad(m, 1)
        idx = -np.ones(m.shape, int)
        idx[m] = np.arange(m.sum())
        # cell-centred grid, phi = 0 on the true edge half a cell outside the last pixel (ghost value -phi)
        rows, cols, vals = [], [], []
        ii, jj = np.nonzero(m)
        me = idx[ii, jj]
        diag = np.full(len(me), -4.0)
        edge_g = np.zeros(len(me))
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = idx[ii + di, jj + dj]
            ok = nb >= 0
            rows += list(me[ok]); cols += list(nb[ok]); vals += [1.0] * int(ok.sum())
            diag[~ok] -= 1.0
            edge_g[~ok] = 1.0
        n = int(m.sum())
        A = sp.csr_matrix((vals, (rows, cols)), shape=(n, n)) + sp.diags(diag)
        phi_v = spl.spsolve(A.tocsc(), -2 * h * h * np.ones(n))
        phi = np.zeros(m.shape)
        phi[m] = phi_v
        gy, gx = np.gradient(phi, h)
        g_in = np.hypot(gx, gy)[m]
        g_edge = np.where(edge_g > 0, 2 * phi_v / h, 0.0)             # phi falls to 0 over the half cell to the edge
        r["J"] = float(2 * phi.sum() * h * h)
        r["tau_unit"] = float(max(g_in.max(), g_edge.max()) / r["J"])  # tau per N mm of torque
    return T * r["tau_unit"]


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
# tray contact on the arm web front face: both flanges z 26..36, the inboard one raised to flange_top from flange_raised_y0
# (6fa0d176), and the deck edge
_FZ = Pm.TRAY["flange_z"]
TRAY_FACE = [(Pm.TRAY["flange_y"][0], Pm.TRAY["flange_y"][1], _FZ[0], _FZ[1]), (Pm.TRAY["flange2_y"][0], Pm.TRAY["flange2_y"][1], _FZ[0], _FZ[1]),
             (Pm.TRAY["y"][0], Pm.TRAY["y"][1], Pm.TRAY["deck_z"][0], Pm.TRAY["deck_z"][1])]
for _fy, _top in zip((Pm.TRAY["flange_y"], Pm.TRAY["flange2_y"]), Pm.TRAY["flange_top"]):
    if _top > _FZ[1]:
        TRAY_FACE.append((Pm.TRAY["flange_raised_y0"], _fy[1], _FZ[1], _top))
TRAY_BOLTS = [tuple(p) for p in Pm.WING["tray_screws"]]


LUG_SCREW, LUG_LEN = Pm.NAC["lug_screw"], Pm.NAC["lug_screw_len"]
LUG_D = float(LUG_SCREW[1:])


def joint_checks(case, L):
    for name, loads, face, bolts, part, scr, d, bite in (
            (f"nacelle lug to arm web ({len(LUG_BOLTS)} x {LUG_SCREW} x {LUG_LEN:.0f})", L["nac"], LUG_FACE, LUG_BOLTS, "nacelle_inner_L",
             LUG_SCREW, LUG_D, LUG_LEN - 5.2),
            (f"tray flange to arm web ({len(TRAY_BOLTS)} x M2 x 10)", L["tray"], TRAY_FACE, TRAY_BOLTS, "tray_L", "M2", 2.0, 10.0 - 5.2)):
        if not loads:
            continue
        F, Mf = resultant(loads)
        T, S, p = bolt_group(face, bolts, F, Mf)
        i = int(np.argmax(T))
        cap = pullout(scr, bite)
        row(part, case, f"{name}: screw pull-out", float(T.max()), f"screw at (y, z) {bolts[i]}", "thread in a horizontal pilot",
            cap["low"], f"tensions {np.round(T, 1).tolist()} N; low-end {scr} capacity {cap['low']:.0f} N at {bite:.1f} mm bite "
            f"(M2 120 N x pilot d x bite; high end {cap['high']:.0f} N; no published value)")
        bear = float(S.max()) / (d * bite)
        row(part, case, f"{name}: thread bearing", bear, "pilot wall", "in-layer bearing", 1.2 * PLA["design_xy"],
            f"screw shear {np.round(S, 1).tolist()} N on d {d:.0f} x {bite:.1f} mm, friction not counted")


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
TRAY_SECTIONS = {x: section_raster(tray, [x, 0, 0], [1, 0, 0], (1, 2), build_axis=1, skin_mm=0.6, infill_E=INFILL_E[BJ["tray_L"]["colour"]])
                 for x in (-36.5, -29.0, -20.0, 15.0)}


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
    # each screw pulls its flange off the web; the flange bends about its root on the deck (x thickness 8, layer planes z)
    fx = Pm.TRAY["flange_x"][1] - Pm.TRAY["flange_x"][0]
    for k, (fy, top) in enumerate(zip((Pm.TRAY["flange_y"], Pm.TRAY["flange2_y"]), Pm.TRAY["flange_top"])):
        on = [i for i, (y, z) in enumerate(TRAY_BOLTS) if fy[0] <= y <= fy[1]]
        for z_if, y0 in ((_FZ[0], fy[0]), (_FZ[1], Pm.TRAY["flange_raised_y0"])) if top > _FZ[1] else ((_FZ[0], fy[0]),):
            lev = [(T[i], TRAY_BOLTS[i][1] - z_if) for i in on if TRAY_BOLTS[i][1] > z_if]
            if not lev:
                continue
            A_if = fx * (fy[1] - y0)
            Mif = sum(t * d for t, d in lev)
            sig = 6 * Mif / ((fy[1] - y0) * fx ** 2) + sum(t for t, _ in lev) / A_if
            row("tray_L", case, f"flange {k + 1} layer interface (z {z_if:.0f})", sig, f"flange {k + 1} root, y {y0}..{fy[1]}",
                "across layers", PLA["design_z"], f"screw pulls {[round(float(t), 1) for t, _ in lev]} N on levers {[round(float(d), 1) for _, d in lev]} mm")


# ------------------------------------------------------------------ 5. shared post screws (whole pack on the duck)
POSTS = [tuple(p) for p in Pm.WING["holes"]]
W_CENTRE_T = Pm.WING["x_front"] - Pm.WING["x_centre_back"]                    # 6.9
POST_LEN = float(Pm.WING["post_screw"].split("x")[1])                         # M2 x 12
POST_BITE = round(POST_LEN - Pm.WING["backpack_plate_t"] - W_CENTRE_T, 2)     # 3.1 into the 4.8 pilot


def post_checks():
    pack_c = PACK_C
    cases = {
        "vertical_impact_15.6g": [(-PACK_G / 1000 * G * IMPACT_G * EZ, pack_c)],
        "thrust_1.5x_on_ground": [(4 * PEAK * THRUST_N * EZ - PACK_G / 1000 * G * EZ, pack_c)],
        "fore_aft_10g": [(-PACK_G / 1000 * G * 10 * EX, pack_c)],
        "lateral_10g": [(PACK_G / 1000 * G * 10 * EY, pack_c)],
        # duck lifted by the left nacelle: the hand force on the nacelle, the pack's own weight x 1.5; the rest (the duck)
        # hangs from the posts
        "handling_lift_by_nacelle": [(HANDLING_N * EZ, NAC_TOP_OUT), (-PACK_G / 1000 * G * 1.5 * EZ, pack_c)],
        "topple_strike_front_end": [(-TOPPLE_N * EX, NAC_TIP_FRONT)],
    }
    for case, loads in cases.items():
        F, Mf = resultant(loads)
        # wing centre on the pack posts: the centre face (x -45) bears on the pack; loads on the wing, normal into the pack +x
        hw = Pm.WING["centre_half_w"]
        face = [(-hw, hw, Pm.WING["centre_bot"] + 3.5, Pm.WING["centre_top"])]
        T, S, p = bolt_group(face, POSTS, F, Mf, plane_x=Pm.WING["x_front"], normal=EX)
        row("wing_plate + OpenRB pack posts", case, f"post screw pull-out (4 x {Pm.WING['post_screw']}, {POST_BITE} mm bite)", float(T.max()),
            "post pilots in the OpenRB pack", "thread", M2_PULLOUT["low"] * POST_BITE / 4.8,
            f"tensions {np.round(T, 1).tolist()} N; capacity scaled by bite {POST_BITE} / 4.8 from the low estimate; high estimate "
            f"{M2_PULLOUT['high'] * POST_BITE / 4.8:.0f} N")
        # tear-out of the upper post holes toward the top edge (1.75 mm ligament above d 2.5 hole) under shear S
        e = Pm.WING["centre_top"] - 26.0
        A = 2 * W_CENTRE_T * (e - 1.25 * math.cos(math.radians(40)))
        row("wing_plate", case, "upper post hole tear-out (1.75 mm ligament)", float(S.max()) / A, "centre plate top edge",
            "in-layer shear", 0.55 * PLA["design_xy"], f"screw shear {np.round(S, 1).tolist()} N; shear-out area {A:.1f} mm2")


# ------------------------------------------------------------------ 5b. FC bracket on the right arm (stack + MTF-01)
_SCR = json.loads((BUILD / "screws.json").read_text())
_SCR = _SCR if isinstance(_SCR, list) else _SCR.get("screws", list(_SCR.values()))
FCB_SCREWS = [(s["seat"][1], s["seat"][2]) for s in _SCR if s["id"].startswith("fcb-")]
FCB_BITE = 8.0 - 3.0                         # M2 x 8 through the 3 mm plate into the arm flange boss
_MB = {r["name"]: r for r in json.loads((BUILD.parents[1] / "mass_budget.json").read_text())["cases"][MB_CASE]}
_mbp = lambda n: np.array(_MB[n]["pos"], float) - [0, 0, 120.0]
_stack = next(n for n in _MB if n.startswith("FC + 4in1"))
_flow = next(n for n in _MB if n.startswith("flow"))
FCB_MASSES = [(_MB[_stack]["g"], _mbp(_stack)), (_MB[_flow]["g"], _mbp(_flow))]
# accelerations of the carried masses (g, gravity folded in as +1 up): lift by one nacelle accelerates the duck at
# HANDLING_N / (2 kg g) = 1.5 g -> 1.5 g apparent; thrust on the ground 1 g; landing / 10 g cases information only
FCB_CASES = {"thrust_1.5x_on_ground": (0, 0, 1), "handling_lift_by_nacelle": (0, 0, HANDLING_N / (2.0 * G)),
             "vertical_impact_15.6g": (0, 0, IMPACT_G), "fore_aft_10g": (10, 0, 1), "lateral_10g": (0, 10, 1)}


def fc_bracket_checks():
    for case, acc in FCB_CASES.items():
        F, Mf = resultant(inertia(FCB_MASSES, acc))
        # plate front face (x -64) on the four flange bosses; loads on the plate, normal into the arm (+x)
        face = [(min(y for y, _ in FCB_SCREWS) - 3, max(y for y, _ in FCB_SCREWS) + 3,
                 min(z for _, z in FCB_SCREWS) - 3, max(z for _, z in FCB_SCREWS) + 3)]
        T, S, p = bolt_group(face, FCB_SCREWS, F, Mf, plane_x=-64.0, normal=EX)
        row("fc_bracket", case, "plate screws pull-out (4 x M2 x 8 into the arm flange bosses)", float(T.max()),
            "flange boss pilots", "thread", M2_PULLOUT["low"] * FCB_BITE / 4.8, f"tensions {np.round(T, 2).tolist()} N")


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
        tw = N["end_wall"]          # thick collar wall where each block ends (4a5232a1)
        e = N["screw_r"] - (N["bore"] / 2 + tw / 2)
        b = L_col * Pm.C
        sigb = 6 * end * e / (b * tw ** 2) + end / (b * tw)
        row("nacelle halves", f"clamp_preload_{lab}", "collar wall bending where the screw block ends", sigb,
            "collar at the end of the front and rear blocks", "in-layer hoop", PLA["design_xy"],
            f"{P:.0f} N per M2, eccentricity {e:.1f} mm, end wall {tw} mm over {b:.1f} mm; the seams stay open with the largest fan")
        # seat bearing in the outer half: M2 washer (OD 5.0) under the pan head on the 5.4 seat floor
        A = math.pi / 4 * (N["washer"]["od"] ** 2 - 2.7 ** 2)
        row("nacelle_outer_L", f"clamp_preload_{lab}", "washer bearing on the seat floor", P / A, "head seat",
            "compression (horizontal screw: in-layer)", 1.5 * PLA["design_xy"],
            f"washer OD {N['washer']['od']} on a d 2.7 clearance; compressive bearing allowable 1.5 x tensile")
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
        one_side = case.startswith("handling") or case.startswith("topple")
        wing_checks(case, L, sides=(1,) if one_side else (1, -1))
        if case == "handling_lift_by_nacelle":      # the same lift by the right nacelle (the arms differ since 480610d1)
            wing_checks("handling_lift_by_right_nacelle", L, sides=(-1,))
        joint_checks(case, L)
        nacelle_checks(case, L)
        tray_checks(case, L)
    post_checks()
    fc_bracket_checks()
    clamp_checks()
    res = dict(geometry=snapshot(), side_masses_g=SIDE, topple_strike_N=TOPPLE_N,
               cases=dict({k: v["src"] for k, v in CASES.items()},
                          handling_lift_by_right_nacelle="the same lift by the right nacelle (mirror); wing plate only"),
               slicing=SLICE,
               rows=ROWS)
    (OUT / "hand_calcs.json").write_text(json.dumps(res, indent=1, default=float))
    worst = sorted(ROWS, key=lambda r: r["safety_factor"])
    for r in worst[:40]:
        print(f"{r['safety_factor']:6.2f}  {r['part']:22s} {r['case']:28s} {r['check']:50s} {r['peak_MPa_or_N']:8.2f}  {r['location']}")


if __name__ == "__main__":
    main()
