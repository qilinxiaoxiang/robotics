"""Sit recheck of the BUILT BatteryDock-B1 geometry (not the concept boxes), on the Mac mini.

    $DYN dock_b1_sim.py b1check          -> checks/b1check.jsonl, heartbeat checks/b1check.status.json

The dock is the nine convex pieces b1-deferred/build_dock_b1.py writes to ../b1-deferred/build/collision/ (their union is the part's outside; what
they add over the part is only the cuts: grooves, leaf openings, slots, jack hole). They are moved from the CAD frame to
the sim frame D (x + 3.0) and added as static mesh geoms. The backpack gets its two low cap screw heads (M2 pan head
4.0 x 1.6 proud of the back face at y +-9, seated z 18.0), which the concept sims did not have. Everything else is
grid.one(): the real Brain sit (--model asbuilt --manifest current, --volt 7.6 --drop 0.036), the pad check with the
leaves 5.5 mm forward of A1 in D (B1: 3.0 datum + 2.5 leaves), rail clearance to every non-backpack robot part in stand,
sit and the stand-up. Rail clearance uses the pieces' face planes (a lower bound of the distance outside a convex solid;
its sign is exact).
Cases: the centred case and the concept's R1 tolerance edges (x -9, -6, +3; y -15, -12, +3; yaw -5, +5), seeds 0-2.
"""
import json, math, multiprocessing as mp, os, sys, time, traceback
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
COLL = HERE.parent / "b1-deferred/build/collision"
CK = HERE / "checks"
D_SHIFT = 3.0
BACK_X, HEAD_D, HEAD_K, HEAD_Z_GUIDE = -75.55, 4.0, 1.6, 18.0 - 56.9
OFFS = [(0, 0, 0), (-9, 0, 0), (-6, 0, 0), (3, 0, 0), (0, -15, 0), (0, -12, 0), (0, 3, 0), (0, 0, -5), (0, 0, 5)]


def heads():
    out = []
    for y in (9.0, -9.0):
        a = np.linspace(0, 2 * math.pi, 24, endpoint=False)
        ring = np.c_[np.zeros_like(a), y + HEAD_D / 2 * np.cos(a), HEAD_Z_GUIDE + HEAD_D / 2 * np.sin(a)]
        v = np.vstack([ring + [BACK_X - HEAD_K, 0, 0], ring + [BACK_X, 0, 0]])
        out.append((f"screw_head_{'l' if y > 0 else 'r'}", v))
    return out


def b1_items():
    import trimesh
    items = []
    for f in sorted(COLL.glob("*.stl")):
        m = trimesh.load(f, force="mesh"); m.apply_translation((D_SHIFT, 0, 0))
        h = m.convex_hull
        n = h.face_normals; d = np.einsum("ij,ij->i", n, h.triangles[:, 0, :])
        c = h.vertices.mean(0)
        items.append(dict(name=f.stem, mesh=(h.vertices, h.faces), planes=(n, d), pos=c.tolist()))
    return items


def patch():
    import simcore as S, concept as C
    S.EXTRA_TRUNK[:] = heads()
    orig_geo, orig_sdf = C.dock_geometry, C.box_sdf
    C.dock_geometry = lambda p: b1_items() if p.get("b1") else orig_geo(p)
    def sdf(P, b):
        if "planes" in b:
            n, d = b["planes"]
            return (np.asarray(P) @ n.T - d).max(axis=1)
        return orig_sdf(P, b)
    C.box_sdf = sdf


def worker(case):
    sys.path.insert(0, str(HERE))
    try:
        patch()
        import grid
        return grid.one(case)
    except Exception:
        return dict(case=case, error=traceback.format_exc()[-1500:])


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "b1check"
    cases = [dict(concept="B1 built", params=dict(b1=True, bias=D_SHIFT, leaf_dx=2.5), off=o, seed=s, tag="b1")
             for o in OFFS for s in (0, 1, 2)]
    res_p, st_p = CK / f"{name}.jsonl", CK / f"{name}.status.json"
    t0 = time.time()
    def status(stage, done, extra=None):
        st_p.write_text(json.dumps(dict(plan=name, stage=stage, cases=len(cases), done=done, started=t0,
                                        updated=time.time(), wall_s=round(time.time() - t0, 1), **(extra or {}))))
    status("running", 0)
    n = 0
    try:
        with open(res_p, "w") as f, mp.get_context("spawn").Pool(int(os.environ.get("WORKERS", 7)), maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(worker, cases):
                r.pop("series", None)
                f.write(json.dumps(r, default=str) + "\n"); f.flush()
                n += 1; status("running", n)
        status("DONE", n)
    except Exception:
        status("FAILED", n, dict(error=traceback.format_exc()[-1500:]))
        raise


if __name__ == "__main__":
    main()
