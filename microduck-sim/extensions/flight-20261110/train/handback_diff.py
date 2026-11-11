"""Why does the no-pack groundpick hand-back fall on the 960 g model (18/20) but not on the default as-built model (0/3)?

1. Mass diff: compile the probe's as-built model with its default manifest (asbuilt-20261015) and with
   flightpack-none.json; per body, mass and COM (body frame) and the robot total and trunk-frame COM.
2. Swap test: hybrid manifests that take the default manifest and replace ONE body's parts with the 960 g model's,
   for every body that differs; the bend + hand-back is rerun (groundpick61 no pack, as style_probe.sh bend) on each,
   so the body whose change makes the hand-back fall is named.
Run on the Mac mini (mini.sh run): $PY train/handback_diff.py --out train/out/handback_diff.json [--episodes 6]
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flight_eval as fe  # noqa: E402

BEND = "--walk-at 1 --walk-s 0 --gp-at 2 --gp-phase 0.33 --gp-hold-s 4".split()
DEFAULT = fe.RL / "cmu/whole/dynamics/asbuilt-20261015/asbuilt-mass-manifest.json"


def compile_masses(manifest):
    sys.path.insert(0, str(fe.RL / "cmu/mac"))
    import brain_sim_check as b
    c0 = b.cfg(0.09, model="asbuilt", kp=200, voltage=7.6)
    if manifest is not None:
        c0["mass_manifest"] = str(Path(manifest).resolve())
    m, d, c, names, bam = b.ev.load(c0)
    import mujoco
    mujoco.mj_forward(m, d)
    tr = m.body("trunk_base").id
    R = d.xmat[tr].reshape(3, 3)
    com_t = R.T @ (d.subtree_com[0] - d.xpos[tr])
    return dict(total_kg=float(m.body_subtreemass[0]), com_trunk_frame_m=com_t.round(5).tolist(),
                bodies={m.body(i).name: dict(mass=round(float(m.body_mass[i]), 5), ipos=np.round(m.body_ipos[i], 5).tolist())
                        for i in range(1, m.nbody)})


def bend_job(job):
    manifest, seed = job
    r = fe.episode((str(HERE / "ckpt/bend_spec"), str(manifest), "stand", seed, 0.0, 8.0, False, list(BEND)))
    return dict(seed=seed, fell_at=r["fell_at"], max_tilt=r["max_tilt"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--none", default=str(HERE / "manifests/flightpack-none.json"))
    ap.add_argument("--episodes", type=int, default=6)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    dflt = json.loads(DEFAULT.read_text())
    none = json.loads(Path(a.none).read_text())
    A, B = compile_masses(DEFAULT), compile_masses(a.none)
    diff = {}
    for n in A["bodies"]:
        x, y = A["bodies"][n], B["bodies"].get(n)
        if y is None:
            continue
        dm = y["mass"] - x["mass"]
        dc = float(np.linalg.norm(np.array(y["ipos"]) - np.array(x["ipos"])))
        if abs(dm) > 1e-3 or dc > 1e-3:
            diff[n] = dict(default_kg=x["mass"], none_kg=y["mass"], d_kg=round(dm, 4), d_com_mm=round(1000 * dc, 1),
                           default_ipos=x["ipos"], none_ipos=y["ipos"])
    res = dict(default_manifest=str(DEFAULT.name), none_manifest=Path(a.none).name,
               default_total_kg=round(A["total_kg"], 4), none_total_kg=round(B["total_kg"], 4),
               default_com_trunk_mm=[round(1000 * v, 1) for v in A["com_trunk_frame_m"]],
               none_com_trunk_mm=[round(1000 * v, 1) for v in B["com_trunk_frame_m"]], bodies_differing=diff,
               manifest_part_count=dict(default=len(dflt["parts"]), none=len(none["parts"])))
    print(json.dumps({k: v for k, v in res.items() if k != "bodies_differing"}), flush=True)
    print("differing bodies:", {k: (v["d_kg"], v["d_com_mm"]) for k, v in diff.items()}, flush=True)
    # swap test: default manifest with one body's parts taken from the 960 g manifest
    tmp = HERE / "logs/handback_hybrids"
    tmp.mkdir(parents=True, exist_ok=True)
    variants = {"default": DEFAULT, "none": Path(a.none)}
    for n in diff:
        h = dict(dflt)
        h["parts"] = [p for p in dflt["parts"] if p.get("body") != n] + [p for p in none["parts"] if p.get("body") == n]
        h["build"] = f"hybrid: default as-built manifest with body {n} from {Path(a.none).name}"
        f = tmp / f"hybrid_{n}.json"
        f.write_text(json.dumps(h))
        variants[f"swap_{n}"] = f
    jobs = [(v, s) for v in variants.values() for s in range(a.episodes)]
    with ProcessPoolExecutor(a.workers) as ex:
        out = list(ex.map(bend_job, jobs))
    res["swap_test"] = {}
    k = 0
    for name in variants:
        eps = out[k:k + a.episodes]
        k += a.episodes
        res["swap_test"][name] = dict(falls=sum(e["fell_at"] is not None for e in eps), episodes=a.episodes,
                                      fall_times=[e["fell_at"] for e in eps if e["fell_at"] is not None],
                                      max_tilt=max(e["max_tilt"] for e in eps))
        print(f"[handback] {name}: falls {res['swap_test'][name]['falls']}/{a.episodes}", flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
