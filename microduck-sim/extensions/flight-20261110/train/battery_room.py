"""How far can the flight batteries move forward or down? Free room around the left battery in the current CAD.

Battery and tray deck as one box in the guide frame (trunk_base frame, mm, +x forward, +z up), from cad/flight_params.py:
battery 78 x 33 x 31 (listing + 4 mm length slack) from x -36, y 42.5 outward, on the deck z 22-26. The box is moved
dx forward and dz down; the minimum distance from it to the moving-part pose clouds (cad/build/pose_clouds.npz, the
sweep_check.py sets the pack was accepted against; stand-world = guide + 120 z) and to the inner nacelle half
(cad/build/nacelle_inner_L-world.stl) is reported per set. The tray and straps would be reprinted with the move; the
nacelle and the robot are fixed. The right battery is the mirror image.
  $PY train/battery_room.py --clouds <pose_clouds.npz> --nacelle <nacelle_inner_L-world.stl> --out train/out/battery_room.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

BOX = dict(x=(-36.0, 42.0), y=(42.5, 75.5), z=(22.0, 57.0))  # battery 26-57 on the 22-26 deck
SETS_USED = ("stand", "50 %", "head scan", "head yaw alone", "logged real bend")


def stl_vertices(path):
    b = Path(path).read_bytes()
    n = int(np.frombuffer(b[80:84], np.uint32)[0])
    rec = np.frombuffer(b[84:84 + 50 * n], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return rec["v"].reshape(-1, 3).astype(float)


def box_dist(P, lo, hi):
    d = np.maximum(np.maximum(lo - P, P - hi), 0.0)
    return np.linalg.norm(d, axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clouds", required=True)
    ap.add_argument("--nacelle", required=True)
    ap.add_argument("--need-mm", type=float, default=1.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    z = np.load(a.clouds, allow_pickle=True)
    names = [str(n) for n in z["names"]]
    clouds = {n: z[f"s{i}"].astype(float) - np.array([0, 0, 120.0]) for i, n in enumerate(names)
              if any(k in n for k in SETS_USED)}
    clouds["nacelle_inner_L (fixed)"] = stl_vertices(a.nacelle)
    lo0 = np.array([BOX["x"][0], BOX["y"][0], BOX["z"][0]])
    hi0 = np.array([BOX["x"][1], BOX["y"][1], BOX["z"][1]])
    near = {}
    for n, P in clouds.items():  # only points that can come near any tested move
        m = np.all((P > lo0 - [5, 5, 40]) & (P < hi0 + [70, 5, 5]), axis=1)
        near[n] = P[m]
    base = {n: (float(box_dist(P, lo0, hi0).min()) if len(P) else None) for n, P in near.items()}

    def gaps(dx, dz):
        sh = np.array([dx, 0.0, -dz])
        return {n: (float(box_dist(P, lo0 + sh, hi0 + sh).min()) if len(P) else None) for n, P in near.items()}

    def ok(g):  # every set keeps need_mm, or no less than it has today where today is already below
        return all(v is None or v >= min(a.need_mm, base[n] if base[n] is not None else a.need_mm) - 1e-6 for n, v in g.items())

    fwd = [dx for dx in np.arange(0, 61, 1.0) if ok(gaps(dx, 0.0))]
    down = [dz for dz in np.arange(0, 31, 1.0) if ok(gaps(0.0, dz))]
    max_fwd = 0.0
    for dx in np.arange(0, 61, 1.0):
        if not ok(gaps(dx, 0.0)):
            break
        max_fwd = float(dx)
    max_down = 0.0
    for dz in np.arange(0, 31, 1.0):
        if not ok(gaps(0.0, dz)):
            break
        max_down = float(dz)
    first_block_fwd = {n: v for n, v in gaps(max_fwd + 1, 0.0).items() if v is not None and v < min(a.need_mm, base[n] or a.need_mm)}
    first_block_down = {n: v for n, v in gaps(0.0, max_down + 1).items() if v is not None and v < min(a.need_mm, base[n] or a.need_mm)}
    res = dict(box_guide_mm=BOX, need_mm=a.need_mm, gaps_today_mm={n: None if v is None else round(v, 2) for n, v in base.items()},
               max_forward_mm=max_fwd, max_down_mm=max_down,
               blocked_forward_by={n: round(v, 2) for n, v in first_block_fwd.items()},
               blocked_down_by={n: round(v, 2) for n, v in first_block_down.items()},
               scan_forward={int(dx): {n: None if v is None else round(v, 1) for n, v in gaps(dx, 0.0).items()} for dx in (0, 5, 10, 20, 40)},
               scan_down={int(dz): {n: None if v is None else round(v, 1) for n, v in gaps(0.0, dz).items()} for dz in (0, 5, 10, 20)})
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(dict(max_forward_mm=max_fwd, max_down_mm=max_down, blocked_forward_by=res["blocked_forward_by"],
                          blocked_down_by=res["blocked_down_by"], gaps_today=res["gaps_today_mm"]), indent=0))


if __name__ == "__main__":
    main()
