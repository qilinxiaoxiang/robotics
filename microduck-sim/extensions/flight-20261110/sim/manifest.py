"""Mass manifest of the four-EDF flight pack, as signed parts on trunk_base (same schema as
microduck_rl/cmu/model/manifests/*.json), plus whole-robot totals for the duck with and without the pack.

Every pack item carries mass, position, inertia or box size, basis and source. Positions are in the trunk_base frame
(metres), which equals the CAD guide frame of flight-20261110/cad (x forward, y left, z up; stand-world z = guide z + 120
mm). Read-only inputs: cad/build/build.json (printed-part volumes and centroids), cad/build/screws.json, cad/flight_params.py
(fan positions and cant), the CAD dummy boxes, procurement.json (bought-part masses).

  microduck_rl/.venv/bin/python sim/manifest.py      -> sim/out/pack_parts.json, sim/out/manifest_*.json, sim/out/mass_report.json
"""
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
FL = H.parent
CMU = FL.parents[1] / "microduck_rl" / "cmu"
OUT = H / "out"
BASE_MANIFEST = CMU / "model" / "manifests" / "battery-20261104.json"
SCENE = CMU / "model" / "scenes" / "scene_battery-20261104.xml"

sys.path.insert(0, str(FL / "cad"))
import flight_params as FP  # noqa: E402  (read only; imports cad-practice/print_fit)

PLA = 1.24          # g/cm3, flight_params.PLA_DENSITY
PRINT_FRACTION = 0.851   # effective print fraction the project uses for every printed part (battery-20261104 provenance)
STEEL_SCREW_G = {"M2 x 10": 0.316, "M2 x 8": 0.26, "M2 x 6": 0.21, "M2 x 4": 0.15}   # 0.316 g: the model's M2 x 10 estimate
NYLON_STANDOFF_G = 0.30
WIRE_G_PER_M = {"16AWG": 15.0, "14AWG": 24.0}   # silicone wire: copper 1.31/2.08 mm2 x 8.96 g/cm3 + jacket (estimate)


def stl_bounds(path):
    b = path.read_bytes(); n = struct.unpack("<I", b[80:84])[0]
    v = np.frombuffer(b[84:84 + 50 * n], dtype=np.dtype([("n", "<3f4"), ("v", "<3f4", (3,)), ("a", "<u2")]))["v"].reshape(-1, 3)
    return v.min(0).astype(float), v.max(0).astype(float)


def part(pid, g, pos_mm, src, basis="estimate", size_mm=None, inertia=None, group="pack"):
    p = dict(id=pid, body="trunk_base", mass_kg=float(g) / 1000.0, position_m=[round(float(x) / 1000.0, 6) for x in pos_mm],
             basis=basis, label=basis, source=src, group=group)
    if inertia is not None:
        p["inertia_about_com_kg_m2"] = inertia
    else:
        p["dimensions_m"] = [round(float(x) / 1000.0, 6) for x in (size_mm if size_mm is not None else (10, 10, 10))]
    return p


def fan_inertia(g, which):
    """Fan as a solid cylinder r 22 mm, length 76 mm along its canted axis (estimate)."""
    m, r, L = g / 1000.0, 0.022, 0.076
    ia, it = 0.5 * m * r * r, m * (3 * r * r + L * L) / 12
    th = math.radians(FP.CANT_DEG) * FP.DIR[which]
    a = np.array([-math.sin(th), 0, math.cos(th)])          # axis up the fan (thrust direction)
    I = it * np.eye(3) + (ia - it) * np.outer(a, a)
    return I.round(12).tolist()


def pack_parts():
    build = json.loads((FL / "cad/build/build.json").read_text())
    screws = json.loads((FL / "cad/build/screws.json").read_text())
    proc = json.loads((FL / "procurement.json").read_text())
    parts = []
    # fans: mass centre on the axis 45 mm behind the lip face (duct + rotor ~30 g near t 20, motor ~46 g at t 46..76)
    for which in ("front", "rear"):
        for side, s in (("L", +1), ("R", -1)):
            p = FP.fan_point(which, 45.0, s)
            parts.append(part(f"fan-{which}-{side}", FP.FAN["mass_g"], p,
                              "76 g listing (qwinout spec table, procurement.json) + 4 g leads = flight_params.FAN mass_g 80; "
                              "mass centre t 45 mm on the canted axis (cad/flight_params.fan_point); cylinder inertia estimate",
                              basis="vendor+estimate", inertia=fan_inertia(FP.FAN["mass_g"], which)))
    # batteries: CAD dummy box (listing 74 x 33 x 31 + 4 mm slack), 151 g listing
    for side in ("L", "R"):
        lo, hi = stl_bounds(FL / f"cad/build/dummy_battery_{side}-world.stl")
        parts.append(part(f"battery-{side}", 151.0, (lo + hi) / 2, "CNHL 4S 1300 130C, 151 g +-5 (procurement.json fit quote); "
                          "centre of cad/build/dummy_battery_" + side + "-world.stl", basis="vendor", size_mm=[74, 33, 31]))
    # printed parts: H2S slicer grams (cad/slices/grams.json, v6 CAD) at the CAD centroid; volume x PLA x 0.851 only as fallback
    sliced = {}
    gp = FL / "cad/slices/grams.json"
    if gp.exists():
        sliced = json.loads(gp.read_text()).get("parts", {})
    for name, v in build.items():
        if not isinstance(v, dict) or v.get("volume_cm3") is None:
            continue
        g = sliced.get(name, v["volume_cm3"] * PLA * PRINT_FRACTION)
        src_g = (f"H2S slicer {g} g (cad/slices/grams.json)" if name in sliced else
                 f"{v['volume_cm3']} cm3 x {PLA} g/cm3 PLA x {PRINT_FRACTION} print fraction")
        lo, hi = np.array(v["bounds"][0]), np.array(v["bounds"][1])
        size = (hi - lo) * 0.6   # bounding box shrunk: the parts are shells and webs, not solid blocks (estimate)
        parts.append(part(f"print-{name}", g, v["centroid"], f"cad/build/build.json {name}: {src_g}; CAD centroid",
                          basis="slicer" if name in sliced else "CAD-volume", size_mm=size))
    # electronics
    def box(stem):
        lo, hi = stl_bounds(FL / f"cad/build/{stem}-world.stl"); return (lo + hi) / 2, hi - lo
    c, s = box("dummy_fc_esc_stack")
    parts.append(part("fc-esc-stack", FP.FC["mass_g"] + FP.FC["hw_g"], c, "MicoAir743v2 10 g + AM32 55A 14 g (procurement.json cad_handoff) "
                      "+ 6 g standoffs/hardware (flight_params.FC hw_g); dummy_fc_esc_stack box", basis="vendor+estimate", size_mm=s))
    c, s = box("dummy_mtf01")
    parts.append(part("mtf01", FP.MTF01["mass_g"], c, "MTF-01 4.5 g (micoair.com, procurement.json)", basis="vendor", size_mm=s))
    c, s = box("dummy_esc_capacitor")
    parts.append(part("capacitor", 5.0, c, "Rubycon 1000 uF 35 V 12.5 x 20 mm with leads, 5 g (estimate)", size_mm=s))
    # wiring (lengths are routing estimates along the CAD harness paths)
    c, s = box("dummy_cross_harness")
    parts.append(part("wire-left-fan-ext", 6 * 0.30 * WIRE_G_PER_M["16AWG"], [-45.0, 55.0, 25.0],
                      "6 x 16 AWG x 0.30 m, left fans to the ESC on the right (front of the tray, through the web, cross harness "
                      "behind the backpack); 15 g/m silicone estimate; centroid of the route", size_mm=[60, 120, 25]))
    parts.append(part("wire-right-fan-ext", 6 * 0.15 * WIRE_G_PER_M["16AWG"], [-50.0, -85.0, 35.0],
                      "6 x 16 AWG x 0.15 m, right fans to the ESC; 15 g/m estimate", size_mm=[60, 50, 25]))
    parts.append(part("wire-battery-pigtails", (0.30 + 0.12) * 2 * WIRE_G_PER_M["14AWG"], [-60.0, -5.0, 30.0],
                      "2 x 14 AWG pairs, left 0.30 m (crosses), right 0.12 m; 24 g/m estimate (RoboClub wire)", size_mm=[40, 120, 30]))
    parts.append(part("xt60-male-x2", 6.0, [-55.0, 0.0, 45.0], "two XT60 male housings with contacts, 3 g each (estimate; RoboClub stock)", size_mm=[20, 100, 15]))
    parts.append(part("bullet-connectors", 12.0, [-20.0, 0.0, 30.0], "12 pairs 3.5 mm bullets at the fan leads, 1 g per pair (estimate)", size_mm=[60, 200, 20]))
    parts.append(part("signal-leads", 3.0, [-85.0, -40.0, 30.0], "SH1.0 ESC 8-pin, MTF-01 4-pin, FC to A7Z UART 4-pin, 3 g (estimate)", size_mm=[30, 60, 30]))
    parts.append(part("solder-heatshrink-ties", 6.0, [-55.0, 0.0, 30.0], "solder, heat shrink and zip ties, 6 g (estimate)", size_mm=[40, 150, 30]))
    for side, s in (("L", 1), ("R", -1)):
        lo, hi = stl_bounds(FL / f"cad/build/dummy_battery_{side}-world.stl")
        parts.append(part(f"strap-{side}", 4.0, (lo + hi) / 2 + np.array([0, 0, 0]), "Pyrodrone strap 16 x 250 mm, 4 g (listing)", basis="vendor", size_mm=[40, 40, 40]))
    # screws from the CAD screw list, plus the 4 shared post screws going from M2 x 6 to M2 x 10 (+0.106 g each)
    for sc in screws:
        if "existing" in sc["spec"]:
            continue          # the shared post screws: counted below as the M2 x 6 -> M2 x 10 difference
        g = NYLON_STANDOFF_G if "standoff" in sc["spec"] else STEEL_SCREW_G[sc["spec"].split(" (")[0]]
        parts.append(part(f"screw-{sc['id']}", g, sc["seat"], f"cad/build/screws.json {sc['spec']}; steel estimate", size_mm=[4, 4, 10]))
    for i, (y, z) in enumerate(FP.WING["holes"]):
        parts.append(part(f"screw-post-upgrade-{i}", STEEL_SCREW_G["M2 x 10"] - STEEL_SCREW_G["M2 x 6"], [-48.5, y, z],
                          "shared post screw M2 x 6 -> M2 x 10 (Shawn 2026-11-10 '共用螺丝'), mass difference", size_mm=[4, 4, 10]))
    # the battery backpack moves 3.5 mm back on the 3.5 mm wing-plate centre: move its parts' mass -3.5 mm in x
    base = json.loads(BASE_MANIFEST.read_text())["parts"]
    bp = [p for p in base if p["body"] == "trunk_base" and p["id"].startswith("add-bp")]
    bpg = sum(p["mass_kg"] for p in bp) * 1000
    bpc = sum(np.array(p["position_m"]) * p["mass_kg"] for p in bp) / max(1e-9, sum(p["mass_kg"] for p in bp)) * 1000
    parts.append(part("backpack-shift-minus", -bpg, bpc, f"battery backpack parts of battery-20261104 ({bpg:.1f} g) removed at their COM ...",
                      basis="geometry", size_mm=[1, 1, 1], group="shift"))
    parts.append(part("backpack-shift-plus", bpg, bpc + np.array([-3.5, 0, 0]), "... and put back 3.5 mm behind (wing plate centre 3.5 mm, cad/flight_params.WING)",
                      basis="geometry", size_mm=[1, 1, 1], group="shift"))
    return parts, proc


def variant(parts, mass_scale=1.0, shift_mm=(0, 0, 0), m_total_kg=None, m_pack_kg=None):
    """Pack perturbation: scale pack masses, or move the whole pack so the whole-robot COM moves by shift_mm."""
    out = []
    k = np.zeros(3)
    if any(shift_mm):
        k = np.array(shift_mm, float) * m_total_kg / m_pack_kg   # pack displacement that moves the whole COM by shift_mm
    for p in parts:
        q = dict(p)
        if p["group"] == "pack":
            q["mass_kg"] = p["mass_kg"] * mass_scale
            q["position_m"] = (np.array(p["position_m"]) + k / 1000).round(6).tolist()
            if "inertia_about_com_kg_m2" in q:
                q["inertia_about_com_kg_m2"] = (np.array(q["inertia_about_com_kg_m2"]) * mass_scale).tolist()
        out.append(q)
    return out


def robot_totals(parts):
    """Mass, COM (trunk frame, stand keyframe) and inertia about the COM of the whole robot with the given extra parts."""
    import mujoco
    sys.path.insert(0, str(CMU / "model"))
    from apply_masses import apply_parts_to_spec
    spec = mujoco.MjSpec.from_file(str(SCENE))
    if parts:
        apply_parts_to_spec(spec, [dict(p) for p in parts])
    m = spec.compile(); d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, 1); mujoco.mj_forward(m, d)
    M = float(m.body_mass[1:].sum()); com = (d.xipos[1:] * m.body_mass[1:, None]).sum(0) / M
    I = np.zeros((3, 3))
    for b in range(1, m.nbody):
        R = d.ximat[b].reshape(3, 3); r = d.xipos[b] - com
        I += R @ np.diag(m.body_inertia[b]) @ R.T + m.body_mass[b] * (r @ r * np.eye(3) - np.outer(r, r))
    t = m.body("trunk_base").id
    com_trunk = d.xmat[t].reshape(3, 3).T @ (com - d.xpos[t])
    return dict(mass_g=round(M * 1000, 1), com_trunk_mm=(com_trunk * 1000).round(1).tolist(),
                inertia_about_com_kgm2=dict(xx=round(I[0, 0], 5), yy=round(I[1, 1], 5), zz=round(I[2, 2], 5),
                                            xy=round(I[0, 1], 6), xz=round(I[0, 2], 6), yz=round(I[1, 2], 6)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    parts, proc = pack_parts()
    pack = [p for p in parts if p["group"] == "pack"]
    pack_g = sum(p["mass_kg"] for p in pack) * 1000
    pack_com = sum(np.array(p["position_m"]) * p["mass_kg"] for p in pack) / (pack_g / 1000) * 1000
    groups = {}
    for p in pack:
        k = p["id"].split("-")[0]
        groups[k] = groups.get(k, 0) + p["mass_kg"] * 1000
    base = json.loads(BASE_MANIFEST.read_text())
    duck = robot_totals([])
    full = robot_totals(parts)
    report = dict(
        date="2026-11-10",
        frame="trunk_base = CAD guide frame, mm, x forward y left z up, stand keyframe (stand-world z = guide z + 120)",
        duck_without_pack=dict(duck, model="cmu/model/scenes/scene_battery-20261104.xml (battery-20261104 manifest, 960.45 g "
                               "component estimate, never weighed)"),
        pack=dict(mass_g=round(pack_g, 1), com_trunk_mm=pack_com.round(1).tolist(), by_group_g={k: round(v, 1) for k, v in groups.items()},
                  backpack_shift="battery backpack moved 3.5 mm back (two signed parts, net 0 g)"),
        duck_with_pack=full,
        vs_old_mass_budget=dict(old_pack_g=730, note="mass_budget.json (pre-procurement): batteries 2 x 100 g, printed 120 g, wiring 45 g; "
                                "now 2 x 151 g batteries, printed parts from CAD volumes, wiring from routed lengths"),
        assumptions=[
            "printed parts: H2S slicer grams of the v6 CAD (cad/slices/grams.json, Generic PLA 0.20 mm); "
            "PETG (1.27) would add 2 %",
            "fan 80 g (76 g listing + leads); one heavier listing said 113 g (not used; see mass +10 % case)",
            "wire lengths are routing estimates; connector, solder and strap masses are estimates",
            "nothing in the pack is in hand or weighed",
        ],
        missing_or_assumed_vs_robot_now=[
            "the duck itself (960.45 g) is the battery-20261104 component estimate, never weighed; its backpack, saddle, A7Z and camera "
            "lead are estimates in that manifest",
            "the pack is not built; the CAD is still being edited (cad/ is read at run time)",
            "no tray-to-wing screws listed in cad/build/screws.json yet (about 4 x M2, 1.3 g, not counted)",
            "MTF-01 and FC-to-A7Z cable lengths not known",
        ],
    )
    (OUT / "pack_parts.json").write_text(json.dumps(dict(schema="signed parts on trunk_base, as cmu/model/manifests", parts=parts), indent=1))
    variants = {
        "none": [],
        "nominal": variant(parts),
        "mass+5": variant(parts, mass_scale=1.05),
        "mass+10": variant(parts, mass_scale=1.10),
    }
    Mt, Mp = full["mass_g"] / 1000, pack_g / 1000
    for ax, idx in (("x", 0), ("y", 1)):
        for dmm in (-10, -5, 5, 10):
            sh = [0, 0, 0]; sh[idx] = dmm
            variants[f"com{ax}{dmm:+d}"] = variant(parts, shift_mm=sh, m_total_kg=Mt, m_pack_kg=Mp)
    report["variants"] = {}
    for name, vp in variants.items():
        man = dict(schema=base.get("schema"), build=f"battery-20261104 + flight pack ({name}) from extensions/flight-20261110/sim/manifest.py; "
                   "generated, do not edit", frame=base.get("frame"), parts=base["parts"] + vp)
        (OUT / f"manifest_pack_{name}.json").write_text(json.dumps(man))
        if name not in ("nominal", "none"):
            report["variants"][name] = robot_totals(vp)
    (OUT / "mass_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ("duck_without_pack", "pack", "duck_with_pack")}, indent=1))
    for k, v in report["variants"].items():
        print(k, v["mass_g"], v["com_trunk_mm"])


if __name__ == "__main__":
    main()
