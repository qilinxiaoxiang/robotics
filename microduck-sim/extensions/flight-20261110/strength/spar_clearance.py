"""Where can a straight carbon spar run along y, left nacelle to right nacelle, without hitting the duck?

For every line (x, z) parallel to y over |y| <= Y (guide frame, mm) this gives the smallest distance from the line to:
the world parts at rest (as built, backpack shifted as in cad/check_parts.py), the bought-part dummies of the pack (fans,
batteries and leads, FC/ESC stack, harness, MTF-01, capacitor, A7Z link) and the moving-part pose clouds
(cad/build/pose_clouds.npz from sweep_check.py: legs and head, stand, 50 % random, pickup scan, yaw alone, logged bends).
The printed pack parts (wing plate, trays, nacelles, FC bracket) are not obstacles: in the spar option they become saddles.
Subtract the spar radius from a distance to get the gap.

Run on the Mac mini (MacBook swaps), cad/ read-only:
    zsh cad/mini_sync.sh push && zsh cad/mini_sync.sh run '$PY strength/spar_clearance.py'
    rsync mac-mini:code/flight-cad-mirror/robotics/microduck-sim/extensions/flight-20261110/strength/out/spar_clearance.* strength/out/
"""
import json
import sys
from pathlib import Path

import types

import numpy as np
import trimesh
from scipy.spatial import cKDTree

H = Path(__file__).resolve().parent
CAD = H.parent / "cad"


def _check_parts_defs():
    """The world-part selection of cad/check_parts.py (WORLD, SKIP, BACKPACK, BACKPACK_SHIFT), read from its source so
    flight_params (and its print_fit import) is not needed here."""
    src = (CAD / "check_parts.py").read_text()
    ns = {}
    for name in ("BACKPACK_SHIFT", "BACKPACK", "SKIP"):
        start = src.index(f"\n{name} = ") + 1
        end = start
        depth = 0
        for i, ch in enumerate(src[start:], start):
            depth += ch in "([{"
            depth -= ch in ")]}"
            if ch == "\n" and depth == 0:
                end = i
                break
        exec(src[start:end], {}, ns)
    B = CAD / "build"
    return types.SimpleNamespace(
        WORLD=H.parents[2] / "guide" / "print" / "world", B=B, SKIP=ns["SKIP"], BACKPACK=ns["BACKPACK"],
        BACKPACK_SHIFT=ns["BACKPACK_SHIFT"], DUMMIES=sorted(p.name[6:-10] for p in B.glob("dummy_*-world.stl")),
        load=lambda path, shift=None: (lambda m: (m.apply_translation(shift) if shift is not None else None, m)[1])(
            trimesh.load(path, force="mesh")),
        samples=lambda t, spacing=0.5: np.vstack([trimesh.sample.sample_surface_even(
            t, int(min(400000, max(2000, t.area / spacing ** 2))), seed=1)[0], t.vertices]))


C = _check_parts_defs()

OUT = H / "out"
OUT.mkdir(exist_ok=True)
REGION_LO, REGION_HI = np.array([-140.0, -170.0, -50.0]), np.array([110.0, 170.0, 140.0])
GRID_X = np.arange(-125.0, 95.01, 1.0)
GRID_Z = np.arange(-30.0, 120.01, 1.0)
HALF_LENGTHS = (125.0, 150.0)          # 250 and 300 mm stock, centred
CANDIDATES = {   # (x, z) lines checked in detail; see strength/SPAR-OPTION.md
    "rear_behind_backpack": (-84.0, 53.0),
    "front_ahead_of_chest": (58.0, 53.0),
    "root_slot": (-48.45, 29.6),
}


def in_region(P):
    return P[np.all((P >= REGION_LO) & (P <= REGION_HI), axis=1)]


def main():
    groups = {}
    world = []
    for f in sorted(C.WORLD.glob("*.stl")):
        stem = f.stem
        if any(stem.startswith(k) for k in C.SKIP) or "-v1" in stem or "_v18" in stem or "-2026" in stem or stem.startswith("a7z_"):
            continue
        shift = [C.BACKPACK_SHIFT, 0, 0] if f.name.startswith(C.BACKPACK) else None
        m = C.load(f, shift)
        if np.any(m.bounds[1] < REGION_LO) or np.any(m.bounds[0] > REGION_HI):
            continue
        P = in_region(C.samples(m, 1.0))
        if len(P):
            world.append(P)
            groups.setdefault("duck_at_rest", []).append((stem, P))
    for n in C.DUMMIES:
        m = C.load(C.B / f"dummy_{n}-world.stl")
        key = "fans" if n.startswith("fan_") else "batteries" if n.startswith("battery") else \
              "fc_stack" if "fc_esc" in n else "other_dummies"
        groups.setdefault(key, []).append((n, in_region(C.samples(m, 1.0))))
    pc = np.load(C.B / "pose_clouds.npz")
    names = [str(s) for s in pc["names"]]
    for i, nm in enumerate(names):
        if "100 %" in nm:
            continue          # full-range random poses hit every pack part already (sweep_v6.txt); not a design case
        g = "legs" if ("legs" in nm) else "head"
        P = in_region(pc[f"s{i}"].astype(float) - np.array([0, 0, 120.0]))
        groups.setdefault(f"{g}_moving", []).append((nm, P))

    G = np.stack(np.meshgrid(GRID_X, GRID_Z, indexing="ij"), -1).reshape(-1, 2)
    res = dict(frame="guide, mm; distance from the spar axis to the nearest point (subtract the radius for the gap)",
               grid=dict(x=[GRID_X[0], GRID_X[-1], 1.0], z=[GRID_Z[0], GRID_Z[-1], 1.0]), maps={}, candidates={})
    maps = {}
    for Y in HALF_LENGTHS:
        for key, items in groups.items():
            P = np.vstack([p for _, p in items if len(p)])
            P = P[np.abs(P[:, 1]) <= Y]
            d, _ = cKDTree(P[:, [0, 2]]).query(G)
            maps[(Y, key)] = d.reshape(len(GRID_X), len(GRID_Z))
        for cname, (x, z) in CANDIDATES.items():
            row = {}
            for key, items in groups.items():
                best = (1e9, None)
                for nm, p in items:
                    p = p[np.abs(p[:, 1]) <= Y] if len(p) else p
                    if not len(p):
                        continue
                    d = np.hypot(p[:, 0] - x, p[:, 2] - z)
                    k = int(np.argmin(d))
                    if d[k] < best[0]:
                        best = (float(d[k]), dict(item=nm, at=np.round(p[k], 1).tolist()))
                row[key] = dict(axis_distance_mm=round(best[0], 1), nearest=best[1])
            res["candidates"].setdefault(cname, {})[f"half_length_{Y:.0f}"] = dict(x=x, z=z, **row)
    # corridors: lines whose clearance (axis distance) is >= r + margin to everything, per tube radius
    for Y in HALF_LENGTHS:
        allmin = np.minimum.reduce([maps[(Y, k)] for k in groups])
        for od in (4.0, 5.0, 6.0, 8.0):
            ok = allmin >= od / 2 + 2.0
            pts = G.reshape(len(GRID_X), len(GRID_Z), 2)[ok]
            res["maps"][f"Y{Y:.0f}_od{od:.0f}_free_lines"] = dict(count=int(ok.sum()),
                                                                  x_range=[float(pts[:, 0].min()), float(pts[:, 0].max())] if len(pts) else None,
                                                                  samples=pts[:: max(1, len(pts) // 60)].round(0).tolist())
        np.savez_compressed(OUT / f"spar_clearance_Y{Y:.0f}.npz", x=GRID_X, z=GRID_Z,
                            **{k: v for (yy, k), v in maps.items() if yy == Y})
    (OUT / "spar_clearance.json").write_text(json.dumps(res, indent=1))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        Y = HALF_LENGTHS[0]
        fig, ax = plt.subplots(figsize=(11, 7))
        allmin = np.minimum.reduce([maps[(Y, k)] for k in groups])
        im = ax.pcolormesh(GRID_X, GRID_Z, np.clip(allmin, 0, 15).T, cmap="RdYlGn", shading="auto")
        fig.colorbar(im, ax=ax, label="distance from spar axis to nearest obstacle, mm (clipped at 15)")
        for k, col in (("fans", "k"), ("fc_stack", "m"), ("head_moving", "b"), ("legs_moving", "c"), ("duck_at_rest", "0.4")):
            if (Y, k) in maps:
                ax.contour(GRID_X, GRID_Z, maps[(Y, k)].T, levels=[4.0], colors=col, linewidths=0.8)
        for cname, (x, z) in CANDIDATES.items():
            ax.plot(x, z, "k+", ms=10)
            ax.annotate(cname, (x, z), fontsize=7)
        ax.set_xlabel("x (forward), guide mm")
        ax.set_ylabel("z (up), guide mm")
        ax.set_title(f"straight spar along y, |y| <= {Y:.0f}: free lines (green); 4 mm contours: fans k, FC stack m, head b, legs c, duck grey")
        ax.set_aspect("equal")
        fig.savefig(OUT / "spar_clearance.png", dpi=110, bbox_inches="tight")
    except Exception as e:  # plot is optional
        print("plot skipped:", e)
    print(json.dumps(res["candidates"], indent=1)[:6000])
    print(json.dumps({k: (v["count"], v["x_range"]) for k, v in res["maps"].items()}, indent=1))


if __name__ == "__main__":
    main()
