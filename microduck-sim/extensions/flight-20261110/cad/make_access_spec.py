"""Driver and finger access of every flight-pack screw at the moment it is driven (cad-practice/access_check.py, rules in
PRINT-FIT.md "Access"). Writes the robot-side meshes (backpack group shifted as check_parts.py) to build-access/ and
checks/access.screws.json, then runs the checker into checks/access.json.
    /tmp/microduck-cad-venv/bin/python cad/make_access_spec.py
Assembly order (each step's solids are present for its screws): nacelle halves on the bench around the fans; wing plate and
backpack frame on the pack posts (bars, cap, hatch and battery off, as today); trays on the arm webs; nacelles on the arm webs; FC bracket
on the right arm (it covers the right tray and lug screw heads, so it comes after them); MTF-01 under the shelf. The four M3
nylon standoffs are turned by hand into their pilots and are not driver screws.
"""
import json
import subprocess
import sys
from pathlib import Path

import check_parts as CP

H = Path(__file__).resolve().parent
OUT = H / "build-access"
OUT.mkdir(exist_ok=True)
HEAD = dict(head_d=3.8, head_h=1.6, drive="phillips")     # M2 pan head, the larger common head; Phillips takes the least tilt
BENCH_FAN = {"L": ["dummy_fan_front_L", "dummy_fan_rear_L"], "R": ["dummy_fan_front_R", "dummy_fan_rear_R"]}


def main():
    meshes = {}
    for f in CP.world_files():
        stem = f.stem
        shift = [CP.BACKPACK_SHIFT, 0, 0] if f.name.startswith(CP.BACKPACK) else None
        CP.load(f, shift).export(OUT / f.name)
        meshes[stem] = f.name
    for f in sorted(CP.B.glob("*-world.stl")):
        if f.name.startswith(("wing_plate_centre", "wing_plate_mid")):
            continue
        meshes[f.name[:-10]] = str(f.relative_to(OUT, walk_up=True))
    robot = [k for k in meshes if not k.startswith(("dummy_",)) and k not in CP.PARTS]
    # post screws go in with the backpack frame alone on the pack: cap, hatch, battery and the two bars (removable, the
    # battery change unscrews them today) come after
    closed = [k for k in robot if not k.startswith(("battery_backpack_cap", "battery_hatch", "bp_battery", "battery_backpack_bars"))]
    trays = ["tray_L", "tray_R"]
    nac = ["nacelle_inner_L", "nacelle_outer_L", "nacelle_inner_R", "nacelle_outer_R"] + sum(BENCH_FAN.values(), [])
    present = {
        "wing plate and backpack on the pack": (closed + ["wing_plate"], None),
        "tray L on wing": (robot + ["wing_plate"] + trays, None),
        "tray R on wing": (robot + ["wing_plate"] + trays, None),
        "nacelle L on wing": (robot + ["wing_plate"] + trays + nac, None),
        "nacelle R on wing": (robot + ["wing_plate"] + trays + nac, None),
        "FC bracket on wing (before the stack)": (robot + ["wing_plate", "fc_bracket"] + trays + nac, None),
        "flow module": (robot + ["wing_plate", "fc_bracket", "dummy_fc_esc_stack"] + trays + nac, None),
        "stack": (robot + ["wing_plate", "fc_bracket", "dummy_esc_capacitor"] + trays + nac, None),
        "nacelle L": (["nacelle_inner_L", "nacelle_outer_L"] + BENCH_FAN["L"], None),
        "nacelle R": (["nacelle_inner_R", "nacelle_outer_R"] + BENCH_FAN["R"], None),
    }
    screws = []
    for s in json.loads((CP.B / "screws.json").read_text()):
        if s["id"].startswith(("fc-standoff", "esc-fc-spacer")):
            continue
        length = int(s["spec"].split("x")[1].split()[0])
        pres, table = present[s["step"]]
        head = dict(HEAD, head_d=5.5, head_h=2.4) if s["spec"].startswith("M3") else HEAD   # M3 pan head
        screws.append(dict(id=s["id"], step=s["step"], spec=s["spec"], where=s["joins"], seat=s["seat"], axis=s["axis"],
                           length=length, through_mm=round(s["through_mm"], 2), present=pres, movable=[], table_z=table, **head))
    spec = dict(mesh_dir=str(OUT), meshes=meshes, screws=screws)
    sp = H / "checks" / "access.screws.json"
    sp.write_text(json.dumps(spec, indent=1))
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[4] / "cad-practice/access_check.py"), str(sp),
                        "--json", str(H / "checks" / "access.json")], capture_output=True, text=True)
    print(r.stdout[-6000:], r.stderr[-2000:])
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
