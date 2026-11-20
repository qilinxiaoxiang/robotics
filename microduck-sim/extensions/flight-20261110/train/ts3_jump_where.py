"""Round 3 diagnostic: where the action jumps of a policy happen in a gate walk episode.

  $PY train/ts3_jump_where.py <dir under ckpt> <manifest name> <vx,vx,...> [probe flags ...]
  e.g.  $PY train/ts3_jump_where.py t3h_750 nominal 0.25,0.15,0.10 --stand-s 0

One walking episode per commanded speed, seed 0, through flight_eval.episode (the gate's own code path) with the
probe's tick log and tick diagnostics on. A jump is the gate's own measure: a tick whose action differs from the
previous tick's by more than 0.5 rad on any joint. For every jump the script records the time, which joints moved
more than 0.5 rad, and what the feet did around it (floor force of both feet two ticks before and at the jump), then
prints per speed: jumps, the joints that jump, how many jumps fall within 60 ms after a foot touches down or within
60 ms before a foot lifts, and the time histogram. Mac mini only (mini.sh run). Writes eval/jump_where_<dir>.json.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flight_eval as fe  # noqa: E402

LOADED_N = 0.5  # a foot counts as on the floor at or above this floor force


def run(d, man, vx, extra):
    log = f"/tmp/ts3_jump_{d}_{vx}.jsonl"
    r = fe.episode((str(HERE / "ckpt" / d), str(HERE / f"manifests/flightpack-{man}.json"), "walk", 0, 0.0, 8.0, False,
                    list(extra) + ["--vx", str(vx), "--tick-log", log, "--tick-diag"]))
    rows = [json.loads(x) for x in open(log)]
    os.remove(log)
    return r, rows


def analyse(rows, names):
    acts = [(x["t"], x["action"], x.get("diag")) for x in rows if x.get("action") is not None]
    # touch-down and lift-off times of each foot
    events = []
    for side in ("left", "right"):
        prev = None
        for t, _, dg in acts:
            if not dg or side not in dg:
                continue
            on = dg[side]["fn"] >= LOADED_N
            if prev is not None and on != prev:
                events.append((t, side, "down" if on else "up"))
            prev = on
    jumps, joints, near = [], Counter(), Counter()
    for i in range(1, len(acts)):
        t, a, dg = acts[i]
        dlt = [abs(x - y) for x, y in zip(a, acts[i - 1][1])]
        if max(dlt) <= 0.5:
            continue
        who = [names[k] if k < len(names) else str(k) for k, v in enumerate(dlt) if v > 0.5]
        joints.update(who)
        after_down = [e for e in events if e[2] == "down" and 0.0 <= t - e[0] <= 0.06]
        before_up = [e for e in events if e[2] == "up" and 0.0 <= e[0] - t <= 0.06]
        tag = "after_touch_down" if after_down else ("before_lift_off" if before_up else "mid_stance_or_swing")
        near[tag] += 1
        jumps.append(dict(t=t, joints=who, size=round(max(dlt), 3), phase=tag,
                          feet_n=None if not dg else [dg["left"]["fn"], dg["right"]["fn"]]))
    steps = sum(1 for e in events if e[2] == "down")
    return dict(ticks=len(acts), jumps=len(jumps), joints=dict(joints), phase=dict(near), touch_downs=steps,
                per_second=dict(sorted(Counter(int(j["t"]) for j in jumps).items())), detail=jumps)


def main():
    d, man, vxs, extra = sys.argv[1], sys.argv[2], sys.argv[3].split(","), sys.argv[4:]
    out = {}
    for vx in vxs:
        r, rows = run(d, man, float(vx), extra)
        wb = sys.modules.get("walk_brain")
        names = list(getattr(wb, "NAMES", []))
        if rows and rows[0].get("action") is not None and len(names) != len(rows[0]["action"]):
            names = names[:len(rows[0]["action"])]
        a = analyse(rows, names)
        a.update(fell_at=r["fell_at"], speed=r["speed"], gate_action_jumps=r["action_jumps"], max_tilt=r["max_tilt"])
        out[vx] = a
        print(json.dumps(dict(vx=vx, **{k: v for k, v in a.items() if k != "detail"})))
        for j in a["detail"][:12]:
            print("   ", json.dumps(j))
    (HERE / "eval").mkdir(exist_ok=True)
    (HERE / "eval" / f"jump_where_{d}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
