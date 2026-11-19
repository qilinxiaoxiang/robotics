"""Parity of the runtime's own recurrent-policy support (guide/firmware/mac/walk_brain.py, Brain.run_policy, 2026-11-19)
with the evaluation wrapper every result of round 2 was measured through (flight_eval.py StatefulBrain).

  <venv python> train/ts2_runtime_parity.py [--models ckpt/s2r6_4] [--seeds 5] [--workers 8]
  -> train/out/ts2_runtime_parity.json; exit 1 on any difference

The same runtime-simulation episodes (brain_sim_check through flight_eval.episode, default dropped reads) run twice:
  wrapper  the walk_brain the probe imports today (microduck_rl/cmu/mac, no recurrent support) + flight_eval's wrapper
  native   guide/firmware/mac/walk_brain.py loaded in its place (the only edit: the WHOLE path line, exactly what
           cmu/sync_from_robotics.py does), FLIGHT_NATIVE_STATE=1 so the wrapper stays out and Brain keeps the state
Cells: comx+10 walk, nominal walk with a 0.5 N s shove at 8 s, none walk; seeds 0 .. seeds-1.
Plain check: the current 61-input policy (the probe's default models directory) through both walk_brain files, no pack,
walk, seeds 0 and 1: a plain policy must behave exactly as before.
Compared per control tick: whether a policy ran, which slot (stand / walk), and the 14 actions (Brain.last_action).
Every episode runs in its own process (the walk_brain module is chosen per process).
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import types
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NEW_BRAIN = HERE.parents[2] / "guide/firmware/mac/walk_brain.py"
OLD_WHOLE = 'os.path.join(HERE, "..", "..", "..", "hardware-design-20260912", "whole-robot-20260912")'
S0 = ["--stand-s", "0"]
CELLS = dict(comx=("comx+10", "walk", 0.0, S0), shove=("nominal", "walk", 0.5, S0), none=("none", "walk", 0.0, []))


def run(job):
    path, models, cell, seed = job
    sys.path.insert(0, str(HERE))
    import flight_eval as fe
    mac = fe.RL / "cmu/mac"
    sys.path.insert(0, str(mac))
    if path in ("native", "plain_new"):
        src = NEW_BRAIN.read_text()
        assert src.count(OLD_WHOLE) == 1
        mod = types.ModuleType("walk_brain")
        mod.__file__ = str(mac / "walk_brain.py")
        sys.modules["walk_brain"] = mod
        exec(compile(src.replace(OLD_WHOLE, 'os.path.join(HERE, "..", "whole")'), str(NEW_BRAIN), "exec"), mod.__dict__)
        os.environ["FLIGHT_NATIVE_STATE"] = "1"
    import walk_brain as wb
    assert hasattr(wb.Brain, "run_policy") == (path in ("native", "plain_new")), path
    log, orig = [], wb.Brain.tick

    def tick(self, *a, **k):
        r = orig(self, *a, **k)
        info = r[2]
        log.append(None if info.get("action") is None else (info["policy"], self.last_action.copy()))
        return r

    wb.Brain.tick = tick
    man, case, shove, extra = CELLS[cell]
    if models is None:
        import brain_sim_check
        models = brain_sim_check.MODELS
    r = fe.episode((str(models), str(HERE / f"manifests/flightpack-{man}.json"), case, seed, shove, 8.0, False, extra))
    return dict(path=path, cell=cell, seed=seed, fell_at=r["fell_at"],
                ran=[x is not None for x in log], slot=[x[0] for x in log if x is not None],
                act=np.array([x[1] for x in log if x is not None], dtype=np.float32))


def hooks(models):
    """The state rules of the new Brain without a simulation: fed back, kept over a gap of RECURRENT_MAX_GAP ticks,
    zeroed after a longer one, zeroed by reset_policy_state and by a new policy_reset id, shared by walk and stand."""
    sys.path.insert(0, str(HERE))
    import flight_eval as fe
    mac = fe.RL / "cmu/mac"
    sys.path.insert(0, str(mac))
    src = NEW_BRAIN.read_text()
    mod = types.ModuleType("walk_brain")
    mod.__file__ = str(mac / "walk_brain.py")
    sys.modules["walk_brain"] = mod
    exec(compile(src.replace(OLD_WHOLE, 'os.path.join(HERE, "..", "whole")'), str(NEW_BRAIN), "exec"), mod.__dict__)
    b = mod.Brain(str(models))
    rng = np.random.default_rng(0)
    o1, o2 = (rng.normal(0, 0.3, 61).astype(np.float32) for _ in range(2))

    def call(slot, obs, dt=1):
        b.rec_tick += dt
        return b.run_policy(slot, obs).copy()

    cold = call("walk", o2)
    b.reset_policy_state()
    call("walk", o1)
    warm = call("walk", o2)
    b.reset_policy_state()
    call("walk", o1)
    kept = call("walk", o2, mod.RECURRENT_MAX_GAP)
    b.reset_policy_state()
    call("walk", o1)
    lost = call("walk", o2, mod.RECURRENT_MAX_GAP + 1)
    b.reset_policy_state()
    call("stand", o1)
    shared = call("walk", o2)
    b.reset_policy_state("test")
    after_reset = call("walk", o2)
    call("walk", o1)
    idle = ([2048] * 14, [0] * 14, (1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0), False, None, None)
    b.tick({"mode": "monitor", "policy_reset": "b"}, 0.0, *idle)  # a new id in the command file: one reset
    after_id = call("walk", o2, 0)
    call("walk", o1)
    b.tick({"mode": "monitor", "policy_reset": "b"}, 0.02, *idle)  # the same id again: nothing
    same_id = call("walk", o2, 0)
    eq = lambda x, y: bool(np.array_equal(x, y))  # noqa: E731
    return dict(state_is_used=not eq(cold, warm), kept_over_gap_of_max=eq(kept, warm), zeroed_after_longer_gap=eq(lost, cold),
                walk_and_stand_share_state=eq(shared, warm), reset_hook_zeroes=eq(after_reset, cold),
                reset_by_command_id_zeroes=eq(after_id, cold), same_command_id_keeps_state=not eq(same_id, cold), slots=sorted(b.rec),
                groups=sorted({v[0] for v in b.rec.values()}))


def compare(a, b):
    same = a["ran"] == b["ran"] and a["slot"] == b["slot"] and a["act"].shape == b["act"].shape
    return dict(cell=a["cell"], seed=a["seed"], ticks=len(a["ran"]), policy_ticks=int(sum(a["ran"])),
                skipped_ticks=int(len(a["ran"]) - sum(a["ran"])), same_ticks_and_slots=bool(same),
                max_abs_action_diff=float(np.abs(a["act"] - b["act"]).max()) if same else None,
                fell_at=[a["fell_at"], b["fell_at"]], same_fall=a["fell_at"] == b["fell_at"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="ckpt/s2r6_4")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    models = HERE / args.models
    jobs = [(p, models, c, s) for p in ("wrapper", "native") for c in CELLS for s in range(args.seeds)]
    jobs += [(p, None, "none", s) for p in ("plain_old", "plain_new") for s in range(2)]
    with mp.get_context("spawn").Pool(min(args.workers, 8), maxtasksperchild=1) as pool:
        res = {(r["path"], r["cell"], r["seed"]): r for r in pool.imap_unordered(run, jobs)}
        hk = pool.apply(hooks, (models,))
    rec = [compare(res["wrapper", c, s], res["native", c, s]) for c in CELLS for s in range(args.seeds)]
    plain = [compare(res["plain_old", "none", s], res["plain_new", "none", s]) for s in range(2)]
    ok = all(r["same_ticks_and_slots"] and r["same_fall"] and r["max_abs_action_diff"] == 0.0 for r in rec + plain)
    ok = ok and all(v for k, v in hk.items() if isinstance(v, bool)) and len(hk["groups"]) == 1
    out = dict(models=args.models, new_brain=str(NEW_BRAIN), recurrent=rec, plain_policy=plain, state_rules=hk,
               recurrent_max_abs_action_diff=max((r["max_abs_action_diff"] if r["max_abs_action_diff"] is not None else float("inf"))
                                                 for r in rec),
               plain_max_abs_action_diff=max((r["max_abs_action_diff"] if r["max_abs_action_diff"] is not None else float("inf"))
                                             for r in plain),
               recurrent_policy_ticks=sum(r["policy_ticks"] for r in rec), recurrent_skipped_ticks=sum(r["skipped_ticks"] for r in rec),
               falls_wrapper=sum(r["fell_at"][0] is not None for r in rec), falls_native=sum(r["fell_at"][1] is not None for r in rec),
               identical=bool(ok))
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out/ts2_runtime_parity.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("recurrent", "plain_policy")}))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
