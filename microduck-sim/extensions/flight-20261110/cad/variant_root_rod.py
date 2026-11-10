"""Sketch only (not in the release part): a 3 mm carbon rod along the wing-plate root band, and the root stress it gives.
The rod lies on the band top (z 28) in the one free slot between the battery backpack front (x -50.5) and the saddle /
shell-lip faces (x -46.5 / -46.1): rod axis x -48.45, z 29.6 (a 1.6 mm deep groove in the band top), |y| <= 30 (the
transition columns rise above z 28 at |y| 30..37.9 and stop it), spanning the weak band sections y 20..29.
Load cases per side as in the main check: A vertical, 2 x hover thrust share at y 110; B fore-aft, 5 g on the side mass
(two fans, nacelle, battery, tray) at y 95. Section properties from the built wing mesh (cut planes y = const); the rod
counts as E_cf / E_pla = 34 times PLA (pultruded CF 120 GPa, PLA 3.5 GPa).
Two bounds: bonded (rod shares the section, parallel-axis term counted) and loose (rod only follows the curvature, its
own I only).
    /tmp/microduck-cad-venv/bin/python cad/variant_root_rod.py      -> checks/variant_root_rod.json
"""
import json
from pathlib import Path
import numpy as np
import trimesh
from shapely import contains_xy
from shapely.geometry import Polygon

H = Path(__file__).resolve().parent
N = 120.0 / 3.5
ROD = dict(d=3.0, x=-48.45, z=29.6, y=(-30.0, 30.0))
SLOT = dict(x=(-50.5, -46.5), note="backpack front plate x -50.5 behind; saddle zone face x -46.5 (shell top lip x -46.1 at |y| < 18) in front")


def section(wing, y):
    sec = wing.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    shape = None
    for e in sorted((Polygon(e[:, [0, 2]]).buffer(0) for e in sec.discrete if len(e) > 3), key=lambda p: -p.area):
        shape = e if shape is None else shape.symmetric_difference(e)
    xs = np.arange(shape.bounds[0], shape.bounds[2], 0.1) + 0.05
    zs = np.arange(shape.bounds[1], shape.bounds[3], 0.1) + 0.05
    X, Z = np.meshgrid(xs, zs)
    m = contains_xy(shape, X, Z)
    cx, cz = X[m].mean(), Z[m].mean()
    return dict(cx=cx, cz=cz, Ix=((Z[m] - cz) ** 2).sum() * 0.01, Iz=((X[m] - cx) ** 2).sum() * 0.01,
                cxm=np.abs(X[m] - cx).max(), czm=np.abs(Z[m] - cz).max(), area=m.sum() * 0.01)


def main():
    wing = trimesh.load(H / "build" / "wing_plate-world.stl", force="mesh")
    total_g = 1883.0                                  # v6 all-up, fans 80 g (mass_budget.json)
    side_g = 2 * 80 + 25.4 + 21.2 + 151 + 14.5
    FA, FB = 2 * total_g / 1000 * 9.81 / 2, 5 * side_g / 1000 * 9.81
    A = np.pi * ROD["d"] ** 2 / 4
    Ir = np.pi * ROD["d"] ** 4 / 64
    rows = []
    for y in (21.0, 25.0, 29.0):
        s = section(wing, y)
        MA, MB = FA * (110 - y), FB * (95 - y)
        base = dict(A=MA * s["czm"] / s["Ix"], B=MB * s["cxm"] / s["Iz"])
        loose = dict(A=MA * s["czm"] / (s["Ix"] + N * Ir), B=MB * s["cxm"] / (s["Iz"] + N * Ir))
        dz, dx = ROD["z"] - s["cz"], ROD["x"] - s["cx"]
        bonded = dict(A=MA * s["czm"] / (s["Ix"] + N * (Ir + A * dz ** 2)), B=MB * s["cxm"] / (s["Iz"] + N * (Ir + A * dx ** 2)))
        rows.append(dict(y=y, today_MPa={k: round(v, 1) for k, v in base.items()}, rod_loose_MPa={k: round(v, 1) for k, v in loose.items()},
                         rod_bonded_MPa={k: round(v, 1) for k, v in bonded.items()}, section_area_mm2=round(s["area"], 1)))
    out = dict(rod=ROD, slot=SLOT, loads_N=dict(A_vertical_2x_hover=round(FA, 1), B_fore_aft_5g=round(FB, 1)), sections=rows,
               screw_points=("none fit: the slot is 4.0 mm wide (x -50.5..-46.5) and a 3 mm rod leaves 0.5 mm per side; an M2 pan "
                             "head (3.8) or a strap screw beside the rod needs 3 + 3.8 + 1.2 = 8 mm. At |y| < 17 the shell top lip "
                             "narrows it to 2.4 mm above the centre plate. Driving from above also fails the 4 mm driver corridor "
                             "once the backpack is on."),
               retention=("captured in x by the backpack front plate and the saddle-zone face, in -z by the 1.6 mm groove; free "
                          "upward. Holding it needs epoxy in the groove (adhesive is Shawn's call) or a reprinted backpack front "
                          "plate with a lip over the rod."),
               pla_in_layer_MPa=45, verdict=None)
    worst = max(r["today_MPa"]["B"] for r in rows)
    out["verdict"] = (f"fore-aft 5 g at the band: today {worst} MPa; with the rod {max(r['rod_loose_MPa']['B'] for r in rows)} MPa loose, "
                      f"{max(r['rod_bonded_MPa']['B'] for r in rows)} MPa bonded (PLA in-layer about 45 MPa)")
    (H / "checks" / "variant_root_rod.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out["sections"]), "\n", out["verdict"])


if __name__ == "__main__":
    main()
