"""Price universal reward designs offline from the audit2 rollouts (flight_audit.py --jobs universal2 --diag).

The audit's rollouts are deterministic and rewards do not change the dynamics, so one rollout per case gives every
term's raw per-second value: the main terms as terms_per_s / weight, the candidate terms (pose with a tighter hip-yaw
tolerance, tracking with a tighter std, the stance-foot-heading cost) from diag_raw_per_s. A design is a set of
weights and choices; its reward per second is the weighted sum. Gate (coordinator 2026-11-11): every degenerate case
(stand, shuffle, lean_fwd, lean_back) earns at most 0.80 of the intended walk at every load (full, nobatt, none), and
the walker's velocity tracking is higher than each degenerate case's.

  python3 train/reward_design.py out/audit2_diag_full.json out/audit2_diag_nobatt.json out/audit2_diag_none.json
Writes out/reward_design.json: the baseline, every passing design sorted by how little it changes, and the chosen one.
"""
import itertools
import json
import sys
from pathlib import Path

GATE = 0.80
DEGEN = ("stand", "shuffle", "lean_fwd", "lean_back")
POSE = {0.30: "pose", 0.15: "diag_pose_hy015", 0.10: "diag_pose_hy010"}  # walking hip-yaw std -> term
TRACK = {0.224: "diag_track_std022", 0.15: "diag_track_std015", 0.10: "diag_track_std010"}


def raw_terms(case):
    t, w = case["terms_per_s"], case["weights"]
    raw = {k: t[k] / w[k] for k in t if w.get(k) and not k.startswith("diag_") and k != "stance_foot_heading"}
    raw.update(case["diag_raw_per_s"])
    return raw


def price(raw, base_w, d):
    w = dict(base_w)
    w["pose"] = d["pose_w"]
    w["air_time"] = d["air_w"]
    w["track_linear_velocity"] = d["track_w"]
    # terms every upright behaviour earns alike (runtime-range audit 2026-11-11: upright 1.86 / 1.67-1.87 and head
    # pose tracking 1.91 / 1.65-1.77 per s for walk / stand): lowering them shifts the share to the walk-only terms
    w["upright"] = d.get("upright_w", w["upright"])
    w["head_pose_tracking"] = d.get("head_w", w["head_pose_tracking"])
    total = 0.0
    for k, wk in w.items():
        if k.startswith("diag_") or k == "stance_foot_heading" or not wk:
            continue
        key = POSE[d["hip_yaw_std"]] if k == "pose" else TRACK[d["track_std"]] if k == "track_linear_velocity" else k
        total += wk * raw[key]
    total += d["foot_w"] * raw["diag_foot_heading"]
    return total, raw[TRACK[d["track_std"]]]


def evaluate(cases, base_w, d):
    out, ok = {}, True
    for ld in sorted({k.split(":")[0] for k in cases}):
        it_r, it_t = price(raw_terms(cases[f"{ld}:intended"]), base_w, d)
        for dg in DEGEN:
            c = cases.get(f"{ld}:{dg}")
            if c is None:
                continue
            r, t = price(raw_terms(c), base_w, d)
            ratio = r / it_r
            win = ratio <= GATE and t < it_t
            ok &= win
            out[f"{ld}:{dg}"] = dict(ratio=round(ratio, 3), track_ratio=round(t / it_t, 3), passes=win)
        out[f"{ld}:intended_reward_per_s"] = round(it_r, 3)
        sp = cases.get(f"{ld}:splay_fq2")
        if sp is not None:  # Shawn 2026-11-11: splayed fq2 (faster) against straight-footed walk61, same commands
            r, t = price(raw_terms(sp), base_w, d)
            out[f"{ld}:splay_fq2"] = dict(ratio=round(r / it_r, 3), track_ratio=round(t / it_t, 3),
                                          straight_preferred=bool(r < it_r))
    return ok, out


def changes(d, base):
    return sum(d[k] != base[k] for k in base)


def main():
    cases, base_w = {}, None
    for p in sys.argv[1:]:
        res = json.loads(Path(p).read_text())["results"]["universal2"]
        for k, v in res.items():
            if k == "verdict":
                continue
            cases[k] = v
            if v.get("obs_command_override") is None and base_w is None:
                base_w = v["weights"]
    for k, v in cases.items():  # the weighted sum must reproduce the measured reward per second
        s = sum(x for n, x in v["terms_per_s"].items())
        assert abs(s - v["reward_per_s"]) < 0.02 + 0.01 * abs(v["reward_per_s"]), (k, s, v["reward_per_s"])
    base = dict(pose_w=1.0, air_w=3.0, track_w=2.0, hip_yaw_std=0.30, track_std=0.224, foot_w=0.0,
                upright_w=base_w["upright"], head_w=base_w["head_pose_tracking"])
    ok0, out0 = evaluate(cases, base_w, base)
    grid = dict(pose_w=(1.0, 0.75, 0.5), air_w=(3.0, 4.0, 5.0, 6.0), track_w=(2.0, 3.0), hip_yaw_std=(0.30, 0.15, 0.10),
                track_std=(0.224, 0.15, 0.10), foot_w=(0.0, -1.0, -2.0, -4.0, -8.0),
                upright_w=(base_w["upright"], 1.0, 0.5), head_w=(base_w["head_pose_tracking"], 1.0))
    passing, speed_only_designs = [], []
    closest = None
    for vals in itertools.product(*grid.values()):
        d = dict(zip(grid, vals))
        ok, out = evaluate(cases, base_w, d)
        worst_any = max(v["ratio"] for k, v in out.items() if isinstance(v, dict) and ":splay" not in k)
        if closest is None or worst_any < closest["worst_ratio"]:
            closest = dict(design=d, worst_ratio=round(worst_any, 3), checks=out)
        straight = all(v["straight_preferred"] for k, v in out.items() if ":splay" in k)
        speed_only = d["foot_w"] == 0 and d["hip_yaw_std"] == 0.30
        if speed_only:
            speed_only_designs.append(dict(design=d, straight_preferred=straight, degenerate_gate=ok,
                                           splay={k: v for k, v in out.items() if ":splay" in k}))
        if ok:
            worst = max(v["ratio"] for k, v in out.items() if isinstance(v, dict) and ":splay" not in k)
            passing.append(dict(design=d, n_changes=changes(d, base), worst_ratio=round(worst, 3),
                                straight_preferred=straight, checks=out))
    # Shawn's style requirement fixes two changes: the stance-foot-heading term and the tighter hip-yaw tolerance;
    # the speed requirement (2026-11-11 "外八 ... 肯定很慢"): tracking made stronger (weight 3 or a tighter std)
    styled = [p for p in passing if p["design"]["foot_w"] < 0 and p["design"]["hip_yaw_std"] < 0.30
              and (p["design"]["track_w"] > 2.0 or p["design"]["track_std"] < 0.224) and p["straight_preferred"]]
    styled.sort(key=lambda p: (p["n_changes"], p["worst_ratio"]))
    chosen = styled[0] if styled else None
    Path("out/reward_design.json").write_text(json.dumps(dict(
        loads=sorted({k.split(":")[0] for k in cases}), baseline=dict(design=base, passes=ok0, checks=out0),
        n_passing=len(passing), n_passing_with_style=len(styled), chosen=chosen, passing_with_style=styled[:20],
        closest=closest,
        speed_only=dict(n=len(speed_only_designs), n_straight_preferred=sum(x["straight_preferred"] for x in speed_only_designs),
                        designs=speed_only_designs),
        speeds={k: v.get("speed_along_cmd") for k, v in cases.items()}), indent=1))
    print("baseline", "PASS" if ok0 else "FAIL", json.dumps(out0))
    print(f"passing designs {len(passing)}, with the style terms {len(styled)}")
    print(f"speed-only designs (no foot term, hip-yaw std 0.30): {len(speed_only_designs)}, "
          f"straight preferred in {sum(x['straight_preferred'] for x in speed_only_designs)}")
    if chosen:
        print("chosen", json.dumps(chosen["design"]), json.dumps(chosen["checks"]))


if __name__ == "__main__":
    main()
