"""Side by side, per rehearsal case (shape, offset, seed): the policy in its own training env (results/train_eval.jsonl),
the rehearsal as it ran (seepick-rehearsal-20261027/results/main.jsonl), and the runtime grid under each harness change
(results/<stage>.jsonl). Writes results/comparison.json and prints the summary.

Success measures: train = grasp_held paid on >= 20 steps (the training eval's); handback = still held at the 0.9 hand-back
(the rehearsal's). The training env has no hand-back; its episode ends at 4 s with the object held.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REH = os.path.join(os.path.dirname(HERE), "seepick-rehearsal-20261027", "results", "main.jsonl")
STAGES = ("refit", "refit_sticky")


def key(r):
    return (r["shape"], round(r["dx"], 3), round(r["dy"], 3), r["seed"])


def load(path):
    return [json.loads(x) for x in open(path)] if os.path.exists(path) else []


def rt_row(r):
    if "error" in r:
        return dict(error=r["error"][-200:])
    s = r["result"]["seepick"]
    e = s["events"]
    return dict(train=e.get("held_ticks", 0) >= 20, held_ticks=e.get("held_ticks", 0),
                handback=bool((s.get("at_handback") or {}).get("held")), pinched=e["first_pinched_t"] is not None,
                fell=r["result"]["fell_at"] is not None, guard=s["guard"]["why"],
                lip_min_mm=None if e["lip_min_m"] is None else round(e["lip_min_m"] * 1e3, 1),
                beak_floor_n=e["beak_floor_force_max_n"], tilt=e["max_tilt"],
                pad_xy_err_mm=None if not e["close_at"] else round(e["close_at"]["pad_xy_err_m"] * 1e3, 1))


def main():
    cases = {}
    for r in load(REH):
        cases.setdefault(key(r), {})["rehearsal"] = rt_row(r)
        cases[key(r)]["object"] = r["result"]["seepick"]["object"]
    for st in STAGES:
        for r in load(os.path.join(HERE, "results", f"{st}.jsonl")):
            cases.setdefault(key(r), {})[st] = rt_row(r)
    for r in load(os.path.join(HERE, "results", "train_eval.jsonl")):
        res = r.get("result")
        cases.setdefault(key(r), {})["train_eval"] = (dict(error=r["error"][-200:]) if res is None else
                                                      dict(success=res["success"], envs=res["envs"],
                                                           held_steps=res["held_steps"], pinched=res["pinched_ever"]))
    cols = ["rehearsal"] + list(STAGES)
    out = dict(cases=[dict(shape=k[0], dx=k[1], dy=k[2], seed=k[3], **v) for k, v in sorted(cases.items())])

    def count(sel, col, field):
        rows = [v[col] for k, v in cases.items() if sel(k) and col in v and "error" not in v[col]]
        return f"{sum(bool(x[field]) for x in rows)}/{len(rows)}"

    def train_mean(sel):
        rows = [v["train_eval"] for k, v in cases.items() if sel(k) and "train_eval" in v and "error" not in v["train_eval"]]
        n = sum(x["envs"] for x in rows)
        return f"{sum(x['success'] * x['envs'] for x in rows) / n:.2f} ({n} episodes)" if n else "n/a"

    groups = {"all": lambda k: True, "ball": lambda k: k[0] == "ball", "box": lambda k: k[0] == "box"}
    for dx, dy in sorted({(k[1], k[2]) for k in cases}):
        groups[f"offset {dx:+.2f},{dy:+.2f}"] = (lambda k, dx=dx, dy=dy: (k[1], k[2]) == (dx, dy))
    summary = {}
    for name, sel in groups.items():
        summary[name] = {"train_eval success": train_mean(sel)}
        for col in cols:
            summary[name][f"{col} train-measure"] = count(sel, col, "train")
            summary[name][f"{col} held at hand-back"] = count(sel, col, "handback")
            summary[name][f"{col} pinched"] = count(sel, col, "pinched")
    out["summary"] = summary
    json.dump(out, open(os.path.join(HERE, "results", "comparison.json"), "w"), indent=1)
    for name, v in summary.items():
        print(name)
        for kk, vv in v.items():
            print(f"   {kk:34s} {vv}")


if __name__ == "__main__":
    main()
