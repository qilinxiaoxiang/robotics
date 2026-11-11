"""Merge the hand calculations and the FEA runs into strength/results.json, and size the fixes.
    /tmp/microduck-cad-venv/bin/python strength/build_results.py      (seconds; reads out/hand_calcs.json and out/fea_*.json)

Verdict rule per part and case: the governing value is the larger of the hand value and the FEA value converted to the
printed structure (FEA is solid isotropic, so its section stress is multiplied by the printed/solid ratio the hand
section gives at the same cut). Corner peaks from the voxel FEA are recorded separately: they sit on stair-stepped
re-entrant edges, grow with mesh refinement and say where a crack starts, not how large the nominal stress is.
"""
import json
import math

import numpy as np

from common import M2_PRELOAD, M2_PULLOUT, MAT, OUT, Pm, snapshot

H = json.loads((OUT / "hand_calcs.json").read_text())
FEA = {m: json.loads((OUT / f"fea_{m}.json").read_text()) for m in ("wing", "wing_fix", "nacelle_inner", "nacelle_outer_preload")}
PLA = MAT["PLA"]
SF_TARGET = 2.0
RHO_PLA = 1.24          # g/cm3 solid; added material is counted solid (walls dominate small features)


def hand_rows(part=None, case=None, contains=None):
    out = []
    for r in H["rows"]:
        if part and r["part"] != part:
            continue
        if case and r["case"] != case:
            continue
        if contains and contains not in r["check"]:
            continue
        out.append(r)
    return out


def printed_ratio(case, y):
    """printed/solid ratio of the hand section nearest y (the note carries it)."""
    best = None
    for r in hand_rows("wing_plate", case, "bending at y"):
        yy = float(r["check"].split("y ")[-1])
        k = float(r["note"].split("printed/solid ")[-1])
        if best is None or abs(yy - y) < abs(best[0] - y):
            best = (yy, k)
    return best[1] if best else 1.4


# ------------------------------------------------------------------ wing root: hand vs FEA, section by section
def wing_rows(model):
    rows = []
    for case, r in FEA[model]["cases"].items():
        for s in r["sections"]:
            y = s["at"]
            k = printed_ratio(case, y)
            hs = hand_rows("wing_plate", case, f"bending at y {y:.0f}")
            hand_solid = float(hs[0]["note"].split("solid-section value ")[1].split(" MPa")[0]) if hs else None
            fea_printed = s["sigma_nn_peak"] * k
            gov = max(fea_printed, hs[0]["peak_MPa_or_N"] if hs else 0.0)
            rows.append(dict(model=model, case=case, y=y, fea_solid_MPa=s["sigma_nn_peak"], printed_over_solid=k,
                             fea_printed_MPa=round(fea_printed, 1), hand_solid_MPa=hand_solid,
                             hand_printed_MPa=hs[0]["peak_MPa_or_N"] if hs else None,
                             fea_over_hand=round(s["sigma_nn_peak"] / hand_solid, 2) if hand_solid else None,
                             governing_MPa=round(gov, 1), allowable_MPa=PLA["design_xy"], safety_factor=round(PLA["design_xy"] / gov, 2),
                             where=s["where"]))
        rows.append(dict(model=model, case=case, y="corner peak", fea_solid_MPa=r["max_principal"]["peak"], where=r["max_principal"]["at"],
                         note="voxel re-entrant corner (band lower lip meets column lip), mesh-dependent; crack start point"))
    return rows


# ------------------------------------------------------------------ fixes, each sized against SF 2
def fix_clamp():
    """Collar wall bends where the screw block ends: the screw pulls along y at screw_r, the wall mid-plane sits at
    r_in + t/2, so M = P e acts on a wall strip as long as the collar (b). sigma = 6 (2P) e / (b t^2) + 2P / (b t)."""
    N = Pm.NAC
    r_in, b = N["r_out"] - N["wall"], (N["t1"] - N["t0"]) * Pm.C
    out = []
    for t in (N["wall"], 5.0, 6.0, 7.0, 7.4):
        e = N["screw_r"] - (r_in + t / 2)
        for lab, P in (("snug 167 N", M2_PRELOAD["snug"]), ("at the low strip load 120 N", M2_PULLOUT["low"])):
            sig = 6 * 2 * P * e / (b * t * t) + 2 * P / (b * t)
            out.append(dict(wall_mm=t, preload=lab, e_mm=round(e, 2), sigma_MPa=round(sig, 1), safety_factor=round(PLA["design_xy"] / sig, 2)))
    # outer face of a 7.0 mm wall sits at r 33.6: 4.0 mm clear of the screw axis, the driver-shaft radius the access rule asks
    t_fix = 7.0
    added = (t_fix - N["wall"]) * b * 10.0 * 0.75 / 1000 * RHO_PLA      # per block end: 10 mm taper back to the 3.4 wall
    return dict(model="beam strip at the end of each screw block", rows=out, fea_corner_peak_MPa=dict(
        snug=FEA["nacelle_outer_preload"]["cases"]["preload_snug"]["max_principal"]["peak"],
        strip_260=FEA["nacelle_outer_preload"]["cases"]["preload_to_strip_260N"]["max_principal"]["peak"],
        middle_web_snug=FEA["nacelle_outer_preload"]["cases"]["preload_snug"]["regions"]["middle_web"]["max_principal"]),
        preload_needed=dict(per_screw_N=round(2 * 12.24 / 0.3 / (1061.0 / 167.0), 1),
                            note="15.6 g downward hold at SF 2 with mu 0.3 needs ~82 N normal per fan; snug gives 1061 N, so ~13 N per screw would do"),
        fix=dict(what=f"collar wall {N['wall']} -> {t_fix} mm where each screw block ends, tapering back over 10 mm; same on the middle web",
                 mass_g_per_nacelle=round(4 * added, 1), mass_g_total=round(8 * added, 1)))


def fix_tray():
    import hand_calcs as hc
    L = hc.CASES["vertical_impact_15.6g"]
    F, Mf = hc.resultant(L["tray"])
    out = {}
    variants = {
        "as built (flange z 26..36, screws z 31)": (hc.TRAY_FACE, hc.TRAY_BOLTS),
        "flange 1 raised to z 50, third screw at (46, 45)": (
            [(Pm.TRAY["flange_y"][0], Pm.TRAY["flange_y"][1], 26.0, 50.0), hc.TRAY_FACE[1], hc.TRAY_FACE[2]],
            hc.TRAY_BOLTS + [(46.0, 45.0)]),
        "both flanges raised to z 50, screws at z 45": (
            [(Pm.TRAY["flange_y"][0], Pm.TRAY["flange_y"][1], 26.0, 50.0), (Pm.TRAY["flange2_y"][0], Pm.TRAY["flange2_y"][1], 26.0, 50.0),
             hc.TRAY_FACE[2]], [(46.0, 45.0), (63.0, 45.0)]),
    }
    for lab, (face, bolts) in variants.items():
        T, S, p = hc.bolt_group(face, bolts, F, Mf)
        out[lab] = dict(tensions_N=np.round(T, 1).tolist(), sf_low_pullout=round(M2_PULLOUT["low"] / T.max(), 2),
                        sf_high_pullout=round(M2_PULLOUT["high"] / T.max(), 2))
    fl = (Pm.TRAY["flange_x"][1] - Pm.TRAY["flange_x"][0]) * (Pm.TRAY["flange_y"][1] - Pm.TRAY["flange_y"][0]) * 14.0
    fl2 = (Pm.TRAY["flange_x"][1] - Pm.TRAY["flange_x"][0]) * (Pm.TRAY["flange2_y"][1] - Pm.TRAY["flange2_y"][0]) * 14.0
    return dict(case="vertical_impact_15.6g", variants=out,
                room=f"battery starts at x {Pm.BATT['x0']}, flange ends at x {Pm.TRAY['flange_x'][1]}; the arm web front face reaches z 59 at y 40..66",
                mass_g=dict(flange1=round(fl * 0.6 / 1000 * RHO_PLA, 1), both=round((fl + fl2) * 0.6 / 1000 * RHO_PLA, 1),
                            note="per tray, counted at 60 % fill"))


def fix_lug():
    import hand_calcs as hc
    out = {}
    for case in ("handling_lift_by_nacelle", "lateral_10g", "topple_strike_front_end"):
        F, Mf = hc.resultant(hc.CASES[case]["nac"])
        for lab, bolts in (("as built, 3 screws at y 74", hc.LUG_BOLTS),
                           ("4 screws, two columns y 72.5 / 79.5 at z 44.5 and 52 (+ z 37)",
                            [(72.5, 37.0), (72.5, 52.0), (79.5, 44.5), (79.5, 52.0)])):
            T, S, p = hc.bolt_group(hc.LUG_FACE, bolts, F, Mf)
            out.setdefault(case, {})[lab] = dict(max_tension_N=round(float(T.max()), 1), sf_low=round(M2_PULLOUT["low"] / T.max(), 2),
                                                 sf_high=round(M2_PULLOUT["high"] / T.max(), 2))
    return out


def fix_root():
    """Wing root, fore-aft 10 g (the case that governs once the topple is taken out). Reductions combined
    multiplicatively from: the FEA root-fix variant (out/fea_wing_fix.json), 100 % infill (printed/solid -> 1.0),
    a bonded 3 mm carbon rod in the free slot (cad/checks/variant_root_rod.json ratio bonded/today at y 21 and 29),
    and the material allowable."""
    rod = json.loads((Pm.HERE / "checks" / "variant_root_rod.json").read_text()) if hasattr(Pm, "HERE") else None
    if rod is None:
        from common import CAD
        rod = json.loads((CAD / "checks" / "variant_root_rod.json").read_text())
    ratio = {s["y"]: s["rod_bonded_MPa"]["B"] / s["today_MPa"]["B"] for s in rod["sections"]}
    ratio_vert = {s["y"]: s["rod_bonded_MPa"]["A"] / s["today_MPa"]["A"] for s in rod["sections"]}
    base = {s["at"]: s["sigma_nn_peak"] for s in FEA["wing"]["cases"]["fore_aft_10g"]["sections"]}
    fixd = {s["at"]: s["sigma_nn_peak"] for s in FEA["wing_fix"]["cases"]["fore_aft_10g"]["sections"]}
    k = printed_ratio("fore_aft_10g", 21.0)
    combos = []
    for y in (21.0, 29.0):
        for lab, solid, kk, rr, mat in (
                ("today, PLA", base[y], k, 1.0, "PLA"),
                ("100 % infill, PLA", base[y], 1.0, 1.0, "PLA"),
                ("root-fix variant + 100 % infill, PLA", fixd[y], 1.0, 1.0, "PLA"),
                ("bonded 3 mm CF rod, 100 % infill, PLA", base[y], 1.0, ratio[y], "PLA"),
                ("bonded 3 mm CF rod, 100 % infill, PETG", base[y], 1.0, ratio[y], "PETG"),
                ("root-fix variant + bonded rod + 100 % infill, PA-CF", fixd[y], 1.0, ratio[y], "PA-CF"),
                ("bonded rod + 100 % infill, PA-CF", base[y], 1.0, ratio[y], "PA-CF")):
            sig = solid * kk * rr
            combos.append(dict(y=y, option=lab, sigma_MPa=round(sig, 1), allowable=MAT[mat]["design_xy"],
                               safety_factor=round(MAT[mat]["design_xy"] / sig, 2)))
    return dict(case="fore_aft_10g, FEA section peak (solid) x printed factor x rod ratio", rod_ratio_bonded=ratio,
                rod_ratio_vertical=ratio_vert,
                root_fix_added_cm3=json.loads((OUT / "fea_inputs.json").read_text())["wing_fix"]["added_cm3"], combos=combos,
                mass_g=dict(rod="3 mm CF rod 60 mm ~0.7 g + epoxy", root_fix=1.3,
                            infill_100="wing plate 39.5 g today (slicer share) -> 43.7 cm3 solid: 54 g PLA, about 52 g PA-CF (+13..15 g)"),
                note="re-orienting cannot help: the root bending stress is sigma_yy, already in the layer plane (layers x = const)")


def main():
    wing = wing_rows("wing") + wing_rows("wing_fix")
    nac = []
    for case, r in FEA["nacelle_inner"]["cases"].items():
        for s in r["sections"]:
            ax, at = s["axis"], s["at"]
            hs = hand_rows("nacelle_inner_L", case, f"beam bending at x {at:.0f}") if ax == "x" else hand_rows("nacelle_inner_L", case, "lug-to-collar root")
            nac.append(dict(case=case, section=f"{ax} {at}", fea_solid_MPa=s["sigma_nn_peak"],
                            hand_MPa=hs[0]["peak_MPa_or_N"] if hs else None,
                            fea_over_hand=round(s["sigma_nn_peak"] / hs[0]["peak_MPa_or_N"], 2) if hs and hs[0]["peak_MPa_or_N"] else None))
        nac.append(dict(case=case, section="corner peak", fea_solid_MPa=r["max_principal"]["peak"], where=r["max_principal"]["at"]))
    fails = sorted([r for r in H["rows"] if r["safety_factor"] < SF_TARGET], key=lambda r: r["safety_factor"])
    wing_fail = sorted([r for r in wing if isinstance(r["y"], float) and r["model"] == "wing" and r["safety_factor"] < SF_TARGET],
                       key=lambda r: r["safety_factor"])
    res = dict(geometry=snapshot(), sf_target=SF_TARGET, materials=MAT, slicing=H["slicing"], load_cases=H["cases"],
               side_masses_g=H["side_masses_g"], topple_strike_N=H["topple_strike_N"],
               hand_rows=H["rows"], hand_fails=fails, wing_sections_hand_vs_fea=wing, wing_fea_fails=wing_fail,
               nacelle_inner_hand_vs_fea=nac,
               clamp=fix_clamp(), fixes=dict(tray=fix_tray(), lug=fix_lug(), root=fix_root()),
               sim_probe={k: json.loads((OUT / "sim_probe" / f"{k}.json").read_text()) for k in
                          ("cut03", "hover_nominal", "comx+10_table_up_s2_air", "ARE_thrust80_table_down_s2")})
    for k in res["sim_probe"].values():
        k.pop("args", None)
    (OUT.parent / "results.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(dict(clamp=res["clamp"], fixes=res["fixes"]), indent=1, default=float))
    print("wing FEA fails:", [(r["case"], r["y"], r["safety_factor"]) for r in wing_fail])


if __name__ == "__main__":
    main()
