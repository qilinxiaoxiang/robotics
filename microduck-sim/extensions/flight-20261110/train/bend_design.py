"""Price bend reward designs offline from the bend audit rollouts (bend_audit.py --diag, BEND-PLAN.md section 5).

Rewards do not change the dynamics, so one deterministic rollout per behaviour gives each term's raw per-second
value (terms_per_s / weight, and diag_raw_per_s for the bend_terms.py candidates). A design is a set of weights; its
reward per second is the weighted sum. Gate: every degenerate behaviour (stand, half_bend, stay_down, sit_back) earns
at most 0.80 of the intended bend at every load (full, nobatt, none).

  python3 bend_design.py out/bendaudit_diag_full.json out/bendaudit_diag_nobatt.json out/bendaudit_diag_none.json
Writes out/bend_design.json: the baseline, the passing designs sorted by fewest changes, the chosen one, and the closest.
"""
import itertools
import json
import sys
from pathlib import Path

GATE = 0.80
TERMS = {"prox_w": "mouth_ground_proximity", "perp_w": "mouth_perpendicular_to_ground", "ar_w": "action_rate_l2",
         "tq_w": "torque_margin", "pose_w": ("ground_pick_return_pose_legs", "ground_pick_return_pose_neck")}


def raw_terms(case):
    t, w = case["terms_per_s"], case["weights"]
    raw = {k: t[k] / w[k] for k in t if w.get(k) and not k.startswith("diag_")}
    raw["hold"] = case["diag_raw_per_s"].get("diag_hold", 0.0)
    raw["rest"] = case["diag_raw_per_s"].get("diag_rest", 0.0)
    return raw


def price(case, base_w, d):
    raw = raw_terms(case)
    w = {k: v for k, v in base_w.items() if v and not k.startswith("diag_")}
    for key, term in TERMS.items():
        for t in (term if isinstance(term, tuple) else (term,)):
            w[t] = d[key]
    total = sum(wk * raw.get(k, 0.0) for k, wk in w.items())
    return total + d["hold_w"] * raw["hold"] + d["rest_w"] * raw["rest"]


def evaluate(loads, d):
    out, ok = {}, True
    for ld, (res, corr) in loads.items():
        base_w = res["intended"]["weights"]
        it = price(res["intended"], base_w, d) + corr
        out[f"{ld}:intended_reward_per_s"] = round(it, 3)
        for k, c in res.items():
            if k == "intended":
                continue
            r = price(c, base_w, d) / it if it > 0 else float("inf")
            out[f"{ld}:{k}"] = round(r, 3)
            ok &= r <= GATE
    return ok, out


def main():
    loads = {}
    for p in sys.argv[1:]:
        d = json.loads(Path(p).read_text())
        res = d["results"]
        for k, v in res.items():  # the weighted sum must reproduce the measured reward per second
            s = sum(x for n, x in v["terms_per_s"].items())
            assert abs(s - v["reward_per_s"]) < 0.02 + 0.01 * abs(v["reward_per_s"]), (p, k, s, v["reward_per_s"])
        loads[d["load"]] = (res, float(d["summary"]["intended_correction"]))
    base = dict(prox_w=3.0, perp_w=2.0, ar_w=-2.0, tq_w=-12.0, pose_w=6.0, hold_w=0.0, rest_w=0.0)
    ok0, out0 = evaluate(loads, base)
    # first grid (hold/rest to -80, proximity to 6) left the worst case at 0.852 on its edge; extended outward
    grid = dict(prox_w=(3.0, 6.0, 9.0), perp_w=(2.0, 4.0, 6.0), ar_w=(-2.0, -1.0, -0.5), tq_w=(-12.0, -6.0, -3.0),
                pose_w=(6.0, 4.0, 8.0), hold_w=(0.0, -40.0, -80.0, -160.0, -240.0), rest_w=(0.0, -40.0, -80.0, -160.0, -240.0))
    passing, closest = [], None
    for vals in itertools.product(*grid.values()):
        d = dict(zip(grid, vals))
        ok, out = evaluate(loads, d)
        worst = max(v for k, v in out.items() if "intended" not in k)
        n = sum(d[k] != base[k] for k in base)
        if closest is None or worst < closest["worst_ratio"]:
            closest = dict(design=d, worst_ratio=worst, checks=out)
        if ok:
            passing.append(dict(design=d, n_changes=n, worst_ratio=worst, checks=out))
    passing.sort(key=lambda p: (p["n_changes"], p["worst_ratio"]))
    chosen = passing[0] if passing else None
    Path("out/bend_design.json").write_text(json.dumps(dict(loads=sorted(loads), baseline=dict(design=base, passes=ok0, checks=out0),
                                                            n_passing=len(passing), chosen=chosen, closest=closest,
                                                            passing=passing[:30]), indent=1))
    print("baseline", "PASS" if ok0 else "FAIL", json.dumps(out0))
    print(f"passing designs {len(passing)} of {len(list(itertools.product(*grid.values())))}")
    print("chosen", json.dumps(chosen) if chosen else None)
    print("closest", json.dumps(closest))


if __name__ == "__main__":
    main()
