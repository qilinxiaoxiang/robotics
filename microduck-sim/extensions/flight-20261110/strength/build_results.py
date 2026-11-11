"""Merge the hand calculations and the FEA runs into strength/results.json (current geometry), keeping earlier rounds
under "history".
    /tmp/microduck-cad-venv/bin/python strength/build_results.py      (seconds; reads out/hand_calcs.json and out/fea_*.json)

Verdict rule at a wing section: the governing stress is the FEA von Mises of the element-mean stress on that cut, away
from supports and load patches (exclude_mm); the hand combined value (peak bending and peak Saint-Venant torsion shear
as von Mises, at one point) is recorded beside it as an upper bound. The wing plate prints at 100 % infill, so the solid FEA stress is the
printed stress. Corner peaks from the voxel FEA are recorded separately: they sit on stair-stepped re-entrant edges,
grow with mesh refinement and say where a crack starts, not how large the nominal stress is.
"""
import json

from common import MAT, OUT, snapshot

H = json.loads((OUT / "hand_calcs.json").read_text())
CFG = json.loads((OUT / "fea_inputs.json").read_text())
FEA = {m: json.loads((OUT / f"fea_{m}.json").read_text()) for m in CFG if m != "geometry" and (OUT / f"fea_{m}.json").exists()}
PLA = MAT["PLA"]
SF_TARGET = 2.0
ROOT_Y = (21.0, 25.0, 29.0, 31.0, 33.0)          # band and deep column (solid to x -53.5 out to |y| 32.1)
ARM_Y = (35.0, 37.0, 40.0, 45.0, 60.0)           # column outboard of the deep part, transition and arm web


def hand_rows(part=None, case=None, contains=None):
    return [r for r in H["rows"] if (not part or r["part"] == part) and (not case or r["case"] == case)
            and (not contains or contains in r["check"])]


def hand_at(case, kind, y):
    rs = hand_rows("wing_plate", case, f"{kind} at y {y:.0f}")
    return rs[0]["peak_MPa_or_N"] if rs else None


def wing_rows(model):
    rows = []
    for case, r in FEA[model]["cases"].items():
        for s in r["sections"]:
            y = s["at"]
            hb, ht, hv = hand_at(case, "bending", y), hand_at(case, "torsion shear", y), hand_at(case, "combined (von Mises)", y)
            # the FEA decides (restrained warping and the real shape); the hand combined value adds peak bending and the
            # Saint-Venant shear peak, which on the raster sits at a re-entrant corner, so it is an upper bound kept beside it
            gov = s["vm_peak_far"]
            rows.append(dict(model=model, case=case, y=y, part="root" if y in ROOT_Y else "column/arm",
                             fea_sigma_nn_MPa=s["sigma_nn_peak"], fea_tau_MPa=s["tau_peak"], fea_vm_MPa=s["vm_peak"],
                             fea_vm_far_MPa=s["vm_peak_far"], fea_vm_far_at=s["vm_far_where"], fea_torque_Nmm=s["torque_about_centroid"],
                             hand_sigma_MPa=hb, hand_tau_MPa=ht, hand_vm_MPa=hv,
                             fea_over_hand_vm=round(s["vm_peak_far"] / hv, 2) if hv else None,
                             governing_MPa=round(gov, 1), allowable_MPa=PLA["design_xy"],
                             safety_factor=round(PLA["design_xy"] / gov, 2) if gov > 0 else None))
        rows.append(dict(model=model, case=case, y="corner peak", fea_max_principal_MPa=r["max_principal"]["peak"],
                         where=r["max_principal"]["at"], fea_von_mises_MPa=r["von_mises"]["peak"], vm_where=r["von_mises"]["at"],
                         regions=r.get("regions"),
                         note="voxel peak away from supports; re-entrant corners are mesh-dependent, crack start point"))
    return rows


def case_summary(wing):
    """Per case, the smallest SF of each load path (wing root, column/arm, post screws, tray and lug screws)."""
    out = {}
    for case in H["cases"]:
        d = {}
        for part in ("root", "column/arm"):
            rs = [r for r in wing if r["case"] == case and r.get("part") == part and r["safety_factor"]]
            if rs:
                w = min(rs, key=lambda r: r["safety_factor"])
                d[f"wing {part}"] = dict(sf=w["safety_factor"], y=w["y"], fea_vm_MPa=w["governing_MPa"],
                                         hand_upper_bound_MPa=w["hand_vm_MPa"])
        for lab, part, key in (("post screws", "wing_plate + OpenRB pack posts", "post screw pull-out"),
                               ("tray screws", "tray_L", "screw pull-out"), ("lug screws", "nacelle_inner_L", "screw pull-out"),
                               ("tray flange layers", "tray_L", "layer interface"), ("nacelle inner (hand)", "nacelle_inner_L", "")):
            rs = [r for r in hand_rows(part, case, key) if r["safety_factor"] != float("inf")]
            if lab == "nacelle inner (hand)":
                rs = [r for r in rs if "arm web" not in r["check"]]
            if rs:
                w = min(rs, key=lambda r: r["safety_factor"])
                d[lab] = dict(sf=w["safety_factor"], check=w["check"])
        out[case] = d
    return out


def history():
    """Earlier rounds, compact: their verdicts and fixes. Full files: git show <commit>:<path>."""
    old = json.loads((OUT.parent / "results.json").read_text())
    hist = old.get("history", {})
    if "geometry" in old and "first check" not in json.dumps(list(hist)):
        hist["first check, geometry 1b392541 (wing centre 3.5, band 5.1 open, 30 % infill)"] = dict(
            full_file="git show 2458251d:microduck-sim/extensions/flight-20261110/strength/results.json",
            geometry=old["geometry"], hand_fails=old["hand_fails"], wing_fea_fails=old["wing_fea_fails"], clamp=old["clamp"],
            fixes=old["fixes"],
            note="hand torsion then used J = sum t^3/3 per z row; at y >= 35 (web plus flanges) that overstated J several "
                 "times, so the arm torsion shear was under-reported there; the root band (y 21..31) was not affected")
        for k in ("spar_option", "root_alignment"):
            if k in old:
                hist[f"{k} study (on 1b392541 / 4a5232a1 geometry; strength/SPAR-OPTION.md)"] = old[k]
    return hist


def main():
    hist = history()
    wing = wing_rows("wing")
    variants = {m: wing_rows(m) for m in FEA if m.startswith("wing_")}
    nac = []
    if "nacelle_inner" in FEA:
        for case, r in FEA["nacelle_inner"]["cases"].items():
            for s in r["sections"]:
                ax, at = s["axis"], s["at"]
                hs = hand_rows("nacelle_inner_L", case, f"beam bending at x {at:.0f}") if ax == "x" else hand_rows("nacelle_inner_L", case, "lug-to-collar root")
                nac.append(dict(case=case, section=f"{ax} {at}", fea_solid_MPa=s["sigma_nn_peak"], fea_vm_far_MPa=s.get("vm_peak_far"),
                                hand_MPa=hs[0]["peak_MPa_or_N"] if hs else None,
                                fea_over_hand=round(s["sigma_nn_peak"] / hs[0]["peak_MPa_or_N"], 2) if hs and hs[0]["peak_MPa_or_N"] else None))
            nac.append(dict(case=case, section="corner peak", fea_solid_MPa=r["max_principal"]["peak"], where=r["max_principal"]["at"],
                            regions=r.get("regions")))
    clamp = dict(hand=[r for r in H["rows"] if r["case"].startswith("clamp_preload")])
    if "nacelle_outer_preload" in FEA:
        clamp["fea"] = {k: dict(max_principal=v["max_principal"], von_mises=v["von_mises"], regions=v.get("regions"))
                        for k, v in FEA["nacelle_outer_preload"]["cases"].items()}
    fails = sorted([r for r in H["rows"] if r["safety_factor"] < SF_TARGET], key=lambda r: r["safety_factor"])
    wing_fail = sorted([r for r in wing if isinstance(r["y"], float) and r["safety_factor"] and r["safety_factor"] < SF_TARGET],
                       key=lambda r: r["safety_factor"])
    res = dict(geometry=snapshot(), fea_geometry=CFG["geometry"], sf_target=SF_TARGET, materials=MAT, slicing=H["slicing"],
               load_cases=H["cases"], side_masses_g=H["side_masses_g"], topple_strike_N=H["topple_strike_N"],
               summary_by_case=case_summary(wing), hand_rows=H["rows"], hand_fails=fails,
               wing_sections_hand_vs_fea=wing, wing_fails=wing_fail, wing_variants=variants,
               nacelle_inner_hand_vs_fea=nac, clamp=clamp,
               sim_probe={k: json.loads((OUT / "sim_probe" / f"{k}.json").read_text()) for k in
                          ("cut03", "hover_nominal", "comx+10_table_up_s2_air", "ARE_thrust80_table_down_s2")},
               history=hist)
    for k in res["sim_probe"].values():
        k.pop("args", None)
    def finite(o):          # strict JSON: an unloaded check has SF inf -> null
        if isinstance(o, float) and o in (float("inf"), float("-inf")):
            return None
        if isinstance(o, dict):
            return {k: finite(v) for k, v in o.items()}
        if isinstance(o, list):
            return [finite(v) for v in o]
        return o
    res = finite(json.loads(json.dumps(res, default=float)))
    (OUT.parent / "results.json").write_text(json.dumps(res, indent=1, allow_nan=False))
    print(json.dumps(res["summary_by_case"], indent=1))
    print("wing fails:", [(r["case"], r["y"], r["safety_factor"]) for r in wing_fail])


if __name__ == "__main__":
    main()
