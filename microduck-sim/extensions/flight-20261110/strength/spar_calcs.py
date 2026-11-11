"""Carbon spar option for the wing root: hand calculations (strength/SPAR-OPTION.md).
    /tmp/microduck-cad-venv/bin/python strength/spar_calcs.py     -> out/spar_calcs.json, merged into results.json["spar_option"]

Layout: straight spars along y, behind the battery backpack and the FC stack (the only straight corridor that clears the
duck, the fans, the FC stack and the head and leg sweeps: out/spar_clearance.json). Each nacelle hangs from the spar(s)
on two printed saddles (y 85 and 135, either side of the fans); the spars rest in two centre saddles at y +-S_C on a
printed centre tie that carries the net load forward to the centre plate and the pack posts. Loads per side are the
nacelle loads of hand_calcs.CASES (fans, nacelle, thrust; the trays stay on the wing plate).
Carbon allowables: Easy Composites CFP pultrusion TDS (rev. 2024-09-20) typical lower bounds: flexural 250 MPa,
compressive 200 MPa, short-beam shear 30 MPa. Design values: bending 200 MPa (compression face), shear 30 MPa; SF on top.
"""
import json
import math

import numpy as np
import trimesh

import hand_calcs as hc
from common import BUILD, M2_PULLOUT, MAT, OUT, Pm, resultant, section_raster, section_stress

PLA = MAT["PLA"]
EX, EY, EZ = np.eye(3)
CF = dict(bend=200.0, shear=30.0, src="Easy Composites CFP TDS rev 2024-09-20: flexural 250-400, compressive 200-320, SBS 30-40 MPa (typical)")
X_S = -106.0                    # spar axis x: corridor x <= -98 (8 mm tube, 1 mm margin) at z 20..65, out/spar_clearance.json
Y_SAD = (85.0, 135.0)           # nacelle saddles either side of the fans (fan y 79..141)
Y_NAC = 110.0
S_C = 20.0                      # centre saddles at y +-20 (centre tie no wider than the centre plate; FC stack from y -35.5)
SAD_W = 10.0                    # saddle width along the spar
M2_CAP = M2_PULLOUT["low"]


def tube(od, idd, n, zs, shape="round", g_per_m=None):
    if shape == "round":
        A = math.pi / 4 * (od ** 2 - idd ** 2)
        I = math.pi / 64 * (od ** 4 - idd ** 4)
        J = 2 * I
        tors = lambda T: T * (od / 2) / J if J else 0.0
    else:                       # square box od x od, round or square bore idd
        A = od ** 2 - idd ** 2
        I = (od ** 4 - idd ** 4) / 12
        t = (od - idd) / 2
        Am = (od - t) ** 2
        tors = lambda T: T / (2 * Am * t)
    return dict(od=od, id=idd, n=n, z=zs, shape=shape, A=A, Z=I / (od / 2), tors=tors,
                g_per_m=g_per_m or round(A * 1.4, 1))       # pultrusion density 1.30-1.50 g/cm3 (TDS)


CANDIDATES = {
    "1 x round 10x8 (z 45)": tube(10, 8, 1, (45.0,)),
    "1 x square box 10x10x8 (z 45)": tube(10, 8, 1, (45.0,), shape="square"),
    "2 x round 8x6 (z 27 and 63)": tube(8, 6, 2, (27.0, 63.0)),
    "2 x round 10x8 (z 27 and 63)": tube(10, 8, 2, (27.0, 63.0)),
    "2 x round 12x10 (z 27 and 63)": tube(12, 10, 2, (27.0, 63.0)),
    "2 x rod 4 (z 27 and 63)": tube(4, 0, 2, (27.0, 63.0)),
}
CASES = ["thrust_1.5x_on_ground", "vertical_impact_15.6g", "handling_lift_by_nacelle", "fore_aft_10g", "lateral_10g",
         "topple_strike_front_end"]
ONE_SIDE = {"handling_lift_by_nacelle", "topple_strike_front_end"}


def side_loads(case, side):
    L = hc.CASES[case]["nac"]
    if side > 0:
        return L
    if case in ONE_SIDE:                       # the other nacelle carries only its weight (1 g)
        return hc.inertia([(m, np.asarray(p) * [1, -1, 1]) for m, p in hc.NAC_MASSES], (0, 0, 1))
    if case == "lateral_10g":
        return [(f, np.asarray(p) * [1, -1, 1]) for f, p in L]
    return [(np.asarray(f) * [1, -1, 1], np.asarray(p) * [1, -1, 1]) for f, p in L]


def nacelle_saddles(loads, cand, side):
    """Saddle forces (x, y, z) on the spars from one nacelle, minimum-norm statics of the rigid nacelle.
    Two spars: the pitch moment (about y) is a couple of x forces between the spars. One spar: it stays a torque."""
    F, Mf = resultant(loads)
    ys = [side * y for y in Y_SAD]
    zm = float(np.mean(cand["z"]))
    P0 = np.array([X_S, side * Y_NAC, zm])
    M = Mf(P0)
    sad = [(i, j, np.array([X_S, ys[j], cand["z"][i]])) for i in range(len(cand["z"])) for j in range(2)]
    # unknowns per saddle: fx, fz (axial fy shared equally); rows: Fx, Fz, Mx, My(if 2 spars), Mz
    rows, rhs = [], []
    n = len(sad)
    def r(): return np.zeros(2 * n)
    a = r(); a[0::2] = 1; rows.append(a); rhs.append(F[0])
    a = r(); a[1::2] = 1; rows.append(a); rhs.append(F[2])
    a = r()
    for k, (_, _, p) in enumerate(sad):
        d = p - P0
        a[2 * k + 1] = d[1]            # Mx = dy fz - dz fy (fy handled separately)
    rows.append(a); rhs.append(M[0])
    a = r()
    for k, (_, _, p) in enumerate(sad):
        d = p - P0
        a[2 * k] = -d[1]               # Mz = dx fy - dy fx
    rows.append(a); rhs.append(M[2])
    torque = M[1]
    if len(cand["z"]) > 1:
        a = r()
        for k, (_, _, p) in enumerate(sad):
            d = p - P0
            a[2 * k] = d[2]; a[2 * k + 1] = -d[0]   # My = dz fx - dx fz
        rows.append(a); rhs.append(M[1])
        torque = 0.0
    sol = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)[0]
    out = []
    for k, (i, j, p) in enumerate(sad):
        out.append(dict(spar=i, y=p[1], f=np.array([sol[2 * k], F[1] / n, sol[2 * k + 1]]), p=p))
    return out, torque, F


def evaluate(cand):
    res = {}
    for case in CASES:
        sads, torques = [], []
        for side in (1, -1):
            s, T, F = nacelle_saddles(side_loads(case, side), cand, side)
            sads += s
            torques.append((side, T))
        spar_rows = []
        centre = []
        for i in range(cand["n"]):
            mine = [s for s in sads if s["spar"] == i]
            # spar on two centre supports at y +-S_C; overhang loads from both nacelles
            Fz = sum(s["f"][2] for s in mine); Fx = sum(s["f"][0] for s in mine)
            Mx0 = sum(s["f"][2] * s["y"] for s in mine)   # about y = 0
            Mz0 = sum(s["f"][0] * s["y"] for s in mine)
            # reactions R+ at +S_C, R- at -S_C (z and x): R+ + R- = -F, S_C (R+ - R-) = -M0
            Rz_p = 0.5 * (-Fz - Mx0 / S_C); Rz_m = -Fz - Rz_p
            Rx_p = 0.5 * (-Fx - Mz0 / S_C); Rx_m = -Fx - Rx_p
            # bending at each centre support from the overhang on that side
            Mb = 0.0
            for sgn in (1, -1):
                ov = [s for s in mine if s["y"] * sgn > 0]
                mz = sum(s["f"][2] * (s["y"] - sgn * S_C) for s in ov)
                mx = sum(s["f"][0] * (s["y"] - sgn * S_C) for s in ov)
                Mb = max(Mb, math.hypot(mz, mx))
            T = max(abs(t) for _, t in torques) if cand["n"] == 1 else 0.0
            sig = Mb / cand["Z"]
            tau = cand["tors"](T)
            # nacelle saddle and centre saddle bearing + cap screws (2 x M2 per saddle; the cap takes the load that pulls
            # the spar out of the cradle; the cradle is taken to face whichever direction carries the larger load)
            fs = [math.hypot(s["f"][0], s["f"][2]) for s in mine]
            fc = [math.hypot(Rx_p, Rz_p), math.hypot(Rx_m, Rz_m)]
            spar_rows.append(dict(spar=i, z=cand["z"][i], bending_Nmm=round(Mb, 0), sigma_MPa=round(sig, 1),
                                  torsion_Nmm=round(T, 0), tau_MPa=round(tau, 1),
                                  sf_bending=round(CF["bend"] / sig, 2) if sig > 1e-6 else None,
                                  sf_torsion=round(CF["shear"] / tau, 2) if tau > 1e-6 else None,
                                  nacelle_saddle_max_N=round(max(fs), 1), centre_saddle_max_N=round(max(fc), 1)))
            centre += fc
        sad_max = max(r["nacelle_saddle_max_N"] for r in spar_rows)
        cen_max = max(r["centre_saddle_max_N"] for r in spar_rows)
        d = cand["od"]
        bearing = max(sad_max, cen_max) / (d * SAD_W)
        sf_b = 1.5 * PLA["design_z"] / bearing          # saddle bore across layers (worst print pose)
        sf_screw = 2 * M2_CAP / max(sad_max, cen_max)   # the whole saddle load on the 2 cap screws (worst direction)
        tq = max(abs(t) for _, t in torques)
        res[case] = dict(spars=spar_rows, saddle_bearing_MPa=round(bearing, 2), sf_saddle_bearing=round(sf_b, 2),
                         sf_saddle_screws=round(sf_screw, 2), nacelle_torque_on_one_spar_Nmm=round(tq, 0) if cand["n"] == 1 else 0,
                         friction_clamp_needed_N=round(tq / (d / 2) / 0.3, 0) if cand["n"] == 1 and cand["shape"] == "round" else None)
        sfs = [x for r in spar_rows for x in (r["sf_bending"], r["sf_torsion"]) if x]
        res[case]["sf_spar"] = round(min(sfs), 2) if sfs else None
    return res


def nacelle_cantilever():
    """With the nacelles hung at their rear end (spar at x -106), the nacelle carries both fans as a cantilever.
    Sections of the joined halves at x -60 (through the rear fan collar) and x -80 (rear block)."""
    nin = trimesh.load(BUILD / "nacelle_inner_L-world.stl", force="mesh")
    nout = trimesh.load(BUILD / "nacelle_outer_L-world.stl", force="mesh")
    both = trimesh.util.concatenate([nin, nout])
    out = {}
    for x in (-80.0, -60.0, -36.0):
        r = section_raster(both, [x, 0, 0], [1, 0, 0], (1, 2), build_axis=1, skin_mm=0.3)
        for case in CASES:
            loads = [(f, p) for f, p in hc.CASES[case]["nac"] if p[0] > x]
            if not loads:
                continue
            F, Mf = resultant(loads)
            s = section_stress(r, (1, 2), EX, F, lambda c2, x=x: Mf(np.array([x, c2[1], c2[2]])))
            out.setdefault(case, {})[f"x {x:.0f}"] = dict(sigma_MPa=round(s["sigma"], 1), sf=round(PLA["design_xy"] / s["sigma"], 2))
    return out


def centre_tie_loads():
    """Net load both nacelles put into the centre tie, about the centre plate top (x -48, y 0, z 29): this is what the
    printed tie and the pack posts must carry. The post screws see the same resultant as today (hand_calcs post rows)."""
    c = np.array([-48.0, 0.0, 29.0])
    out = {}
    for case in CASES:
        loads = side_loads(case, 1) + side_loads(case, -1)
        F, Mf = resultant(loads)
        out[case] = dict(F_N=np.round(F, 1).tolist(), M_Nmm=np.round(Mf(c), 0).tolist())
    return out


TIE = np.array([-55.0, 28.0, 50.0])   # where a centre tie can meet the wing plate: the arm tops at |y| 25..33 (see doc)


def wing_band_with_spar():
    """Root band (y 21..31) when the nacelle loads reach the plate through a centre tie at TIE (+-y) and the trays stay on
    the arms. The spars cancel the side bending moments of a symmetric case; the pitch moment (about y) cannot be moved
    by any structure and still enters the centre plate across the band. Hand model of hand_calcs.wing_checks."""
    out = {}
    for case in CASES:
        nets = side_loads(case, 1) + side_loads(case, -1)
        F, Mf = resultant(nets)
        c0 = np.array([TIE[0], 0.0, TIE[2]])
        M0 = Mf(c0)
        # each tie point (+-28) gets half the force and half the pitch moment; the roll and yaw moments become a
        # force couple across the two tie points (2 x 28 mm)
        half = 0.5 * F
        cz = M0[0] / (2 * TIE[1])                 # Mx = sum y fz  -> fz = +-Mx / (2 y)
        cx = -M0[2] / (2 * TIE[1])                # Mz = -sum y fx
        loads_L = [(half + np.array([cx, 0, cz]), TIE)]
        my = 0.5 * M0[1]
        # pitch couple: two equal and opposite z forces 20 mm apart in x at the tie
        loads_L += [(np.array([0, 0, -my / 20.0]), TIE + [10, 0, 0]), (np.array([0, 0, my / 20.0]), TIE - [10, 0, 0])]
        loads = loads_L + hc.CASES[case]["tray"] if case != "topple_strike_front_end" else loads_L
        Fs, Ms = resultant(loads)
        rows = {}
        for y, r in hc.WING_SECTIONS.items():
            if y > 31:
                continue
            s = hc.section_stress(r, (0, 2), EY, Fs, lambda c2, y=y: Ms(np.array([c2[0], y, c2[2]])))
            tau = hc.torsion_open(r, s["torsion"])
            today = [x for x in hc.ROWS if x["case"] == case and x["check"] in (f"bending at y {y:.0f}", f"torsion shear at y {y:.0f}")]
            rows[f"y {y:.0f}"] = dict(sigma_MPa=round(s["sigma"], 1), sf_bending=round(PLA["design_xy"] / s["sigma"], 2),
                                      tau_MPa=round(abs(tau), 1), sf_torsion=round(0.55 * PLA["design_xy"] / max(abs(tau), 1e-9), 2),
                                      today={x["check"].split(" at")[0]: x["safety_factor"] for x in today})
        out[case] = rows
    return out


def clearance():
    D = np.load(OUT / "spar_clearance_Y150.npz")
    keys = [k for k in D.files if k not in ("x", "z")]
    out = {}
    for z in (27.0, 45.0, 63.0):
        i = int(np.argmin(abs(D["x"] - X_S))); k = int(np.argmin(abs(D["z"] - z)))
        out[f"x {X_S:.0f} z {z:.0f}"] = {key: round(float(D[key][i, k]), 1) for key in keys}
    return out


def main():
    res = dict(layout=dict(x_spar=X_S, saddles_y=Y_SAD, centre_saddles_y=S_C, length_mm=290,
                           note="spar |y| <= 145 reaches past the outer saddle at y 135; 500 mm stock cut to 290 (no 290-300 mm stock "
                                "in these sizes was confirmed); 250 mm stock ends at y 125, short of the outer saddle"),
               carbon=CF, candidates={}, clearance_axis_distance_mm=clearance(),
               nacelle_cantilever=nacelle_cantilever(), centre_tie=centre_tie_loads())
    if not hc.ROWS:
        for case, L in hc.CASES.items():
            hc.wing_checks(case, L)
    res["wing_band_with_spar"] = wing_band_with_spar()
    for name, cand in CANDIDATES.items():
        ev = evaluate(cand)
        mass = cand["n"] * cand["g_per_m"] * 0.290
        res["candidates"][name] = dict(od=cand["od"], id=cand["id"], count=cand["n"], z=cand["z"], shape=cand["shape"],
                                       spar_mass_g=round(mass, 1), cases=ev)
    (OUT / "spar_calcs.json").write_text(json.dumps(res, indent=1, default=float))
    for name, c in res["candidates"].items():
        print(name, c["spar_mass_g"], "g")
        for case, r in c["cases"].items():
            print(f"   {case:28s} SF spar {r['sf_spar']}  saddle N {max(s['nacelle_saddle_max_N'] for s in r['spars'])}/"
                  f"{max(s['centre_saddle_max_N'] for s in r['spars'])}  SF bearing {r['sf_saddle_bearing']}  SF screws {r['sf_saddle_screws']}"
                  + (f"  torque {r['nacelle_torque_on_one_spar_Nmm']} Nmm, friction clamp {r['friction_clamp_needed_N']} N" if c['count'] == 1 else ""))
    print(json.dumps(res["nacelle_cantilever"], indent=0))
    print(json.dumps(res["centre_tie"], indent=0))
    print(json.dumps(res["clearance_axis_distance_mm"], indent=0))


if __name__ == "__main__":
    main()
