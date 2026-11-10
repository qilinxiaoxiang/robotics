"""Write the CAD-derived layout and mass case into ../pack_geometry.json and ../mass_budget.json (stand-keyframe world
frame = guide + 120 z, mm), and drop the deleted compass module from every layout and case (Shawn 2026-11-10, '删掉').
    /tmp/microduck-cad-venv/bin/python cad/update_layout.py      (after build_pack.py; reads build/, slices/grams.json if present)
Printed-part grams come from the slicer (slices/grams.json, per part, the H2S plate split by CAD volume) when present,
otherwise CAD volume x 1.24 g/cm3 (solid: every wall is under 4 walls + 2 mm, so the slicer infill changes little).
"""
import json
import math
from pathlib import Path
import numpy as np
import trimesh

import flight_params as Pm

H = Path(__file__).resolve().parent
B = H / "build"
Z = 120.0
LAYOUT = "v6 CAD (cad/build_pack.py): wing plate, trays, clamp nacelles, FC bracket with flow shelf; no compass"


def bounds(name, ysel=None):
    m = trimesh.load(B / f"{name}-world.stl", force="mesh")
    v = m.vertices
    if ysel is not None:
        v = v[(v[:, 1] >= ysel[0]) & (v[:, 1] <= ysel[1])]
    lo, hi = v.min(0), v.max(0)
    return dict(lo=[round(float(lo[0]), 1), round(float(lo[1]), 1), round(float(lo[2] + Z), 1)],
                hi=[round(float(hi[0]), 1), round(float(hi[1]), 1), round(float(hi[2] + Z), 1)])


def union(*bs):
    return dict(lo=[min(b["lo"][i] for b in bs) for i in range(3)], hi=[max(b["hi"][i] for b in bs) for i in range(3)])


def centroid(name):
    m = trimesh.load(B / f"{name}-world.stl", force="mesh")
    c = m.center_mass
    return [round(float(c[0]), 1), round(float(c[1]), 1), round(float(c[2] + Z), 1)]


def main():
    info = json.loads((B / "build.json").read_text())
    vol = {k: v["volume_cm3"] for k, v in info.items() if isinstance(v, dict) and "volume_cm3" in v}
    gp = H / "slices" / "grams.json"
    grams = json.loads(gp.read_text())["parts"] if gp.exists() else {k: round(v * Pm.PLA_DENSITY, 1) for k, v in vol.items()}
    src = "slicer (slices/grams.json)" if gp.exists() else "CAD volume x 1.24 g/cm3"

    vols = {}
    for s, nm in ((1, "L"), (-1, "R")):
        ys = (20.3, 200) if s > 0 else (-200, -20.3)
        vols[f"wing_{nm}"] = bounds("wing_plate", ys)
        vols[f"nacelle_{nm}"] = union(bounds(f"nacelle_inner_{nm}"), bounds(f"nacelle_outer_{nm}"))
        vols[f"fans_{nm}"] = union(bounds(f"dummy_fan_front_{nm}"), bounds(f"dummy_fan_rear_{nm}"))
        vols[f"batt_{nm}"] = union(bounds(f"dummy_battery_{nm}"), bounds(f"dummy_battery_leads_{nm}"))
        vols[f"tray_{nm}"] = bounds(f"tray_{nm}")
    vols["wing_centre"] = bounds("wing_plate", (-20.3, 20.3))
    vols["stack_R"] = union(bounds("fc_bracket"), bounds("dummy_fc_esc_stack"), bounds("dummy_esc_capacitor"))
    vols["flow"] = bounds("dummy_mtf01")
    vols["harness"] = bounds("dummy_cross_harness")
    pg = json.loads((H.parent / "pack_geometry.json").read_text())
    for lay in pg["layouts"].values():
        lay["volumes"].pop("compass_L", None)
    pg["layouts"][LAYOUT] = dict(note="current design: envelopes of the built parts and bought-part dummies (bounding boxes per group)",
                                 volumes=vols)
    for k, lay in pg["layouts"].items():
        if k != LAYOUT and lay.get("note") == "current design":
            lay["note"] = "superseded by v6 CAD"
    (H.parent / "pack_geometry.json").write_text(json.dumps(pg, indent=1))

    def fan_com(which, side):
        x, y, z = Pm.fan_point(which, 45.0, side)      # housing + motor: mass centre about 45 mm down the axis
        return [round(x, 1), round(y, 1), round(z + Z, 1)]

    def box_c(name):
        b = bounds(name)
        return [round((b["lo"][i] + b["hi"][i]) / 2, 1) for i in range(3)]

    def items(fan_g):
        it = []
        for s, nm in ((1, "L"), (-1, "R")):
            it += [dict(name=f"fan F{nm}", g=fan_g, pos=fan_com("front", s)), dict(name=f"fan R{nm}", g=fan_g, pos=fan_com("rear", s))]
            for half in ("inner", "outer"):
                k = f"nacelle_{half}_{nm}"
                it.append(dict(name=k, g=grams[k], pos=centroid(k)))
            it.append(dict(name=f"battery {nm}", g=Pm.BATT["mass_g"], pos=box_c(f"dummy_battery_{nm}")))
            it.append(dict(name=f"tray_{nm}", g=grams[f"tray_{nm}"], pos=centroid(f"tray_{nm}")))
        it += [dict(name="wing_plate", g=grams["wing_plate"], pos=centroid("wing_plate")),
               dict(name="fc_bracket", g=grams["fc_bracket"], pos=centroid("fc_bracket")),
               dict(name="FC + 4in1 ESC stack + M3 standoffs/nuts", g=Pm.FC["mass_g"] + Pm.FC["hw_g"], pos=box_c("dummy_fc_esc_stack")),
               dict(name="ESC capacitor", g=6.0, pos=box_c("dummy_esc_capacitor")),
               dict(name="flow + range module", g=Pm.MTF01["mass_g"], pos=box_c("dummy_mtf01")),
               dict(name="cross harness (left fans 6 x 16 AWG ~250/200 mm, left battery pair, bullets)", g=50.0, pos=box_c("dummy_cross_harness")),
               dict(name="right leads, XT60s, capacitor leads", g=25.0, pos=[-70.0, -60.0, 150.0]),
               dict(name="screws, straps, ties", g=20.0, pos=[-30.0, 0.0, 150.0])]
        return it

    mb = json.loads((H.parent / "mass_budget.json").read_text())
    for case in mb["cases"].values():
        case[:] = [i for i in case if "compass" not in i["name"]]
    mb["cases"]["v6 CAD, fans 80 g"] = items(80.0)
    mb["cases"]["v6 CAD, fans 113 g"] = items(113.0)
    mb["note_v6"] = (f"v6 cases: printed parts from {src}; fans 80 g at 45 mm down each axis; batteries 151 g (CNHL listing); "
                     "stack 24 g + 6 g hardware; MTF-01 4.5 g; compass deleted (Shawn 2026-11-10); wiring 95 g estimated from the "
                     "routed lengths (16 AWG ~15 g/m, 12 AWG pair ~36 g/m per lead, XT60 4 g, bullets).")
    (H.parent / "mass_budget.json").write_text(json.dumps(mb, indent=1))
    tot = sum(i["g"] for i in mb["cases"]["v6 CAD, fans 80 g"])
    print(f"layout written; v6 pack {tot:.0f} g (fans 80 g); printed parts {src}:", {k: grams[k] for k in sorted(grams)})


if __name__ == "__main__":
    main()
