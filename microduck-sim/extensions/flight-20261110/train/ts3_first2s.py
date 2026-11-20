"""Round 3 check of the walk61-anchored student's risk: it has to tell pack from no pack out of its history. What do
the first 2 s after the episode start and the first 2 s after the stand -> walk mode change look like?

  $PY train/ts3_first2s.py <seeds> <dir> [<dir> ...]      (Mac mini only: zsh train/mini.sh run '...')

Per policy folder under ckpt/ (walk61 = the deployed one), per load (none, nominal) and per seed: one gate walk
episode through flight_eval.episode with the tick log on. Counted per window (start: the first 2 s of the log; mode
change: the 2 s after the first tick whose policy is "walk"; rest: everything later): action jumps (a tick whose
action differs from the previous tick's by more than 0.5 rad on any joint, the gate's measure), the largest
tick-to-tick action change, and falls inside the window. Writes eval/first2s_<first dir>.json.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flight_eval as fe  # noqa: E402
import ts3_jump_where as jw  # noqa: E402

WALK61 = HERE / "../../../microduck_rl/cmu/whole/runtime-overlay/models"


def episode(d, man, seed):
    models = str(WALK61.resolve()) if d == "walk61" else str(HERE / "ckpt" / d)
    log = f"/tmp/ts3_first2s_{d}_{man}_{seed}.jsonl"
    r = fe.episode((models, str(HERE / f"manifests/flightpack-{man}.json"), "walk", seed, 0.0, 8.0, False,
                    # the gate's pack cells start in the walk policy (--stand-s 0): with the pack there is no stand phase,
                    # so the pack case has a start window and no mode change
                    ([] if man == "none" else ["--stand-s", "0"]) + ["--tick-log", log, "--tick-diag"]))
    rows = [json.loads(x) for x in open(log)]
    os.remove(log)
    return r, rows


def windows(r, rows, checked):
    wb = sys.modules.get("walk_brain")
    if not checked:
        jw.check_order(rows, list(wb.OBSERVATION_DOF_ORDER), wb)
    acts = [(x["t"], x["action"], x.get("policy")) for x in rows if x.get("action") is not None]
    t0 = acts[0][0]
    tw = next((t for t, _, p in acts if p == "walk"), None)
    fell = r["fell_at"]
    out = {}
    for name, a, b in (("start", t0, t0 + 2.0), ("mode_change", tw, None if tw is None else tw + 2.0),
                       ("rest", None if tw is None else tw + 2.0, 1e9)):
        if a is None:
            out[name] = None
            continue
        steps = [max(abs(x - y) for x, y in zip(acts[i][1], acts[i - 1][1])) for i in range(1, len(acts))
                 if a <= acts[i][0] < b]
        dur = (min(b, acts[-1][0]) - a) if steps else 0.0
        out[name] = dict(ticks=len(steps), seconds=round(dur, 2), jumps=sum(1 for s in steps if s > 0.5),
                         max_step=round(max(steps), 3) if steps else None,
                         fell=bool(fell is not None and a <= fell < b))
    out["walk_starts_at"] = tw
    out["fell_at"] = fell
    return out


def main():
    seeds, dirs = int(sys.argv[1]), sys.argv[2:]
    res, checked = {}, False
    for d in dirs:
        for man in ("none", "nominal"):
            eps = []
            for s in range(seeds):
                r, rows = episode(d, man, s)
                eps.append(windows(r, rows, checked))
                checked = True
            agg = {}
            for w in ("start", "mode_change", "rest"):
                ws = [e[w] for e in eps if e[w]]
                agg[w] = dict(episodes=len(ws), jumps_total=sum(x["jumps"] for x in ws),
                              jumps_per_10s=round(10 * sum(x["jumps"] for x in ws) / max(sum(x["seconds"] for x in ws), 1e-9), 2),
                              max_step=max([x["max_step"] or 0 for x in ws], default=None), falls=sum(x["fell"] for x in ws))
            res[f"{d}:{man}"] = dict(windows=agg, walk_starts_at=eps[0]["walk_starts_at"], fell_at=[e["fell_at"] for e in eps],
                                     episodes=eps)
            print(f"{d} {man}: walk starts at {eps[0]['walk_starts_at']} s; " + "; ".join(
                f"{w} jumps {v['jumps_total']} ({v['jumps_per_10s']} per 10 s) max step {v['max_step']} falls {v['falls']}/{v['episodes']}"
                for w, v in agg.items()), flush=True)
    (HERE / "eval").mkdir(exist_ok=True)
    (HERE / "eval" / f"first2s_{dirs[0]}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
