"""Round 2 DAgger in the runtime simulation (2026-11-18): the current student drives brain_sim_check episodes from an
empty state on Modal CPU containers; per called tick the 61 inputs, the privileged teacher's label (teacher t2a_999
through flight_eval.priv_now) and the ticks skipped before the call are stored (flight_eval FLIGHT_DAGGER=<beta>).

  modal run train/ts2_dagger_modal.py --rnd 1 --models ckpt/s2g_200 --beta 0.5 --episodes 600
  -> train/out/dagger/r1.npz (float16 obs / lab / stu, int8 skip, int16 tick, episode offsets) + r1.json (per episode:
     seed, manifest, case, drop, landing, shove, fell_at, teacher-driven, called ticks)

Seeds: 10000 * rnd + i, so never 0..19 or 2000..2019 (held out for evaluation). Coverage per episode, drawn from the
seed: manifest (comx+10 x3, load100 and nominal x2, the eight others x1), case (walk 55 %, stand 15 %, walk with the
landing start 12 %, walk with a 0.5 N s shove at 4 to 14 s 8 %, turn left / right 5 % each), dropped-read rate uniform
0 to 0.08, 0.3 s open-loop stand on half of the no-pack episodes (as the acceptance cell "none"), otherwise --stand-s 0.
beta: share of episodes in which the teacher's action is applied from 1 s on (the student still runs every tick).
One container per episode, 1 core, retries 1, timeout 900 s; about 0.001 USD per episode.
"""
import json
import sys
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
# in the container this file sits in /root, the train folder (with flight_eval_modal.py) is in the image
sys.path.insert(0, str(HERE) if modal.is_local() else "/root/robotics/microduck-sim/extensions/flight-20261110/train")
import flight_eval_modal as fem  # noqa: E402  (the eval image: same code, probe and pins)

app = modal.App("microduck-flight-dagger", image=fem.image)
# rounds 1 to 3 were drawn with comx+10 x3 (20 %); from round 4 on x5 (29 %; with load100 and nominal 53 %)
MANIFESTS = ["comx+10"] * 5 +["load100", "nominal"] * 2 + ["none", "nobatt", "load000", "load025", "load050", "load075", "comx-10", "mass+10"]
CASES = [("walk", False, False)] * 55 + [("stand", False, False)] * 15 + [("walk", True, False)] * 12 + [("walk", False, True)] * 8 \
    + [("turnL", False, False)] * 5 + [("turnR", False, False)] * 5


@app.function(cpu=1.0, memory=1024, timeout=900, retries=1, single_use_containers=True)
def collect(job: dict) -> dict:
    import os
    os.environ["FLIGHT_DAGGER"] = str(job["beta"])
    os.environ["FLIGHT_VX02"] = "1"
    sys.path.insert(0, str(fem.TRAIN))
    import flight_eval
    r = flight_eval.episode((str(fem.TRAIN / job["models"]), str(fem.TRAIN / f"manifests/flightpack-{job['manifest']}.json"), job["case"],
                             job["seed"], job["shove_ns"], job["shove_at"], job["landing"], job["extra"]))
    keep = {k: r[k] for k in ("seed", "fell_at", "fall_dir", "speed", "vx_0_2s", "diag_stat")}
    return dict(job=job, res=keep, dagger=r["dagger"])


@app.local_entrypoint()
def main(rnd: int, models: str, beta: float, episodes: int = 600, walk_s: float = 15.0):
    # walk_s: length of the walk command (15 s as the evaluation; 3 s gives 8 s episodes, 2.5 x as many starts per dollar)
    import numpy as np
    out = HERE / "out/dagger"
    out.mkdir(parents=True, exist_ok=True)
    assert not (out / f"r{rnd}.npz").exists(), f"out/dagger/r{rnd}.npz exists"
    assert (HERE / models / "walk61.onnx").exists(), models
    jobs = []
    for i in range(episodes):
        seed = 10000 * rnd + i
        assert seed >= 1000 and not 2000 <= seed <= 2019
        g = np.random.default_rng([seed, 31])
        # from round 5 on: comx+10 and comx-10 a quarter each (6 + 6 of 24), load100 x3, nominal x2, the seven others x1
        pool = MANIFESTS if rnd < 5 else (["comx+10", "comx-10"] * 6 + ["load100"] * 3 + ["nominal"] * 2
                                          + ["none", "nobatt", "load000", "load025", "load050", "load075", "mass+10"])
        man = pool[int(g.integers(len(pool)))]
        # from round 6 on the landing start is 22 % (walk 45 %): the landing cells were the weak report cells of round 5
        cases = CASES if rnd < 6 else CASES[10:] + [("walk", True, False)] * 10
        case, landing, shove = cases[int(g.integers(len(cases)))]
        drop = round(float(g.uniform(0.0, 0.08)), 4)
        extra = ["--drop", str(drop)]
        if not (man == "none" and g.random() < 0.5):
            extra += ["--stand-s", "0"]
        if walk_s != 15.0:
            extra += ["--walk-s", str(walk_s)]
        jobs.append(dict(models=models, manifest=man, case=case, seed=seed, landing=landing, shove_ns=0.5 if shove else 0.0,
                         shove_at=round(float(g.uniform(4.0, 14.0 if walk_s == 15.0 else 1.0 + walk_s)), 2), extra=extra, beta=beta,
                         drop=drop, walk_s=walk_s))
    print(f"round {rnd}: {len(jobs)} episodes, student {models}, beta {beta}", flush=True)
    eps, arr, failed = [], dict(obs=[], lab=[], stu=[], skip=[], tick=[]), 0
    for r in collect.map(jobs, order_outputs=False, return_exceptions=True):
        if isinstance(r, Exception):
            failed += 1
            print("episode failed:", repr(r)[:300], flush=True)
            continue
        d = r["dagger"]
        if d is None or len(d["obs"]) == 0:
            failed += 1
            continue
        for k in arr:
            arr[k].append(d[k])
        eps.append(dict(r["job"], **r["res"], teacher_driven=bool(d["teach"]), calls=int(len(d["obs"]))))
    off = np.cumsum([0] + [e["calls"] for e in eps])
    np.savez_compressed(out / f"r{rnd}.npz", offsets=off, **{k: np.concatenate(v) for k, v in arr.items()})
    falls = [e for e in eps if e["fell_at"] is not None]
    summ = dict(round=rnd, models=models, beta=beta, episodes_planned=episodes, episodes=len(eps), failed=failed,
                called_ticks=int(off[-1]), falls=len(falls), teacher_driven_episodes=sum(e["teacher_driven"] for e in eps),
                falls_student_driven=sum(1 for e in falls if not e["teacher_driven"]),
                by_manifest={m: dict(episodes=sum(1 for e in eps if e["manifest"] == m),
                                     falls=sum(1 for e in falls if e["manifest"] == m)) for m in sorted(set(MANIFESTS))})
    (out / f"r{rnd}.json").write_text(json.dumps(dict(summary=summ, episodes=eps), indent=1))
    print(json.dumps(summ))
