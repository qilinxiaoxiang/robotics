"""Pair every run without and with the refit (results/<group>.jsonl) and report what changed.

  python3 compare.py [results-dir]      # prints per-group lines, writes <results-dir>/summary.json

A pair is "identical" when the harness's whole result row is equal (the refit changed nothing the run touched). For the
others the outcome fields are listed side by side, with the floor and self contacts of the bodies the refit moves.
"""
import json
import os
import statistics
import sys

RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
MOVED = ("trunk_base", "hip_l", "hip_l_2", "leg", "leg_2", "jaw_soft")
FIELDS = {
    "suite": ("fell_at", "max_tilt", "max_action", "action_jumps", "dist_x", "yaw_deg", "end_mode"),
    "teleop": ("fell_at", "max_tilt", "max_action", "action_jumps", "end_mode", "behaviour"),
    "failure": ("fell_at", "max_tilt", "max_action", "dist_x", "yaw_walk_deg", "guard_stop"),
    "getup": ("success", "up_after_s", "fell_after_up", "guard_stop_at", "max_action", "sat_s_max_joint", "final_gz"),
    "approach": ("ok", "why", "true_r", "true_bearing_deg", "fell_at", "trips", "max_tilt", "path_m", "elapsed_s"),
    "namecall": ("summary",),
}


def behaviour(r):
    for k in ("kick", "sit", "groundpick"):
        if r.get(k):
            b = r[k]
            return {k: {x: b.get(x) for x in ("stable_after_s", "mouth_min_z", "fell", "done_at") if x in b}}
    return None


def pick(group, r):
    out = {}
    for f in FIELDS[group]:
        if f == "behaviour":
            out[f] = behaviour(r)
        elif f == "summary":
            s = r.get("summary", r)
            out[f] = {k: s.get(k) for k in ("detected", "missed", "false_alarms", "falls", "tilt_max_deg", "head_latency_s") if k in s}
        else:
            out[f] = r.get(f)
    return out


def contacts(row):
    c = (row.get("contacts") or [{}])[0]
    floor = {b: v["steps"] for b, v in c.get("floor", {}).items() if b in MOVED}
    missed = {b: [v["samples"], v["deepest_mm"]] for b, v in c.get("missed", {}).items()}
    pairs = {k: v for k, v in c.get("pairs", {}).items()}
    return dict(floor=floor, missed=missed, pairs=pairs)


def main():
    summary = {}
    for group in ("suite", "teleop", "getup", "getup_imu4", "getup_guard3", "getup_velstand", "approach", "namecall", "failure"):
        path = os.path.join(RES, f"{group}.jsonl")
        if not os.path.exists(path):
            continue
        kind = "getup" if group.startswith("getup") else group
        rows = [json.loads(ln) for ln in open(path) if ln.strip()]
        by = {}
        for r in rows:
            by.setdefault((r["case"], r["seed"]), {})[r["refit"]] = r
        g = dict(pairs=0, identical=0, errors=[], changed=[], missed_without={}, floor_steps={0: {}, 1: {}}, self_pairs={0: {}, 1: {}})
        print(f"\n== {group}")
        for (case, seed), pr in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
            if 0 not in pr or 1 not in pr or "error" in pr[0] or "error" in pr[1]:
                g["errors"].append([case, seed, [pr.get(k, {}).get("error", "missing")[-300:] for k in (0, 1)]])
                continue
            g["pairs"] += 1
            a, b = pr[0]["result"], pr[1]["result"]
            ca, cb = contacts(pr[0]), contacts(pr[1])
            for b_, (n, depth) in ca["missed"].items():
                m = g["missed_without"].setdefault(b_, dict(runs=0, samples=0, deepest_mm=0.0))
                m["runs"] += 1
                m["samples"] += n
                m["deepest_mm"] = min(m["deepest_mm"], depth)
            for k, cc in ((0, ca), (1, cb)):
                for b_, n in cc["floor"].items():
                    g["floor_steps"][k][b_] = g["floor_steps"][k].get(b_, 0) + n
                for p, n in cc["pairs"].items():
                    g["self_pairs"][k][p] = g["self_pairs"][k].get(p, 0) + n
            if a == b:
                g["identical"] += 1
                continue
            pa, pb = pick(kind, a), pick(kind, b)
            diff = {f: [pa[f], pb[f]] for f in pa if pa[f] != pb[f]}
            g["changed"].append(dict(case=case, seed=seed, diff=diff, contacts_without=ca, contacts_with=cb))
            print(f"{case} seed {seed}: " + "; ".join(f"{f} {v[0]} -> {v[1]}" for f, v in diff.items())
                  + f" | missed without {ca['missed']} | moved-body floor steps {ca['floor']} -> {cb['floor']}")
        print(f"{group}: {g['pairs']} pairs, {g['identical']} identical, {len(g['changed'])} differ, {len(g['errors'])} errors")
        print(f"  missed contacts without the refit: {g['missed_without']}")
        print(f"  moved-body floor steps without / with: {g['floor_steps'][0]} / {g['floor_steps'][1]}")
        print(f"  self-contact steps without / with: {g['self_pairs'][0]} / {g['self_pairs'][1]}")
        if kind == "getup":
            for k in (0, 1):
                rs = [r["result"] for r in rows if r["refit"] == k and "result" in r]
                for pose in ("face_down", "face_up", "side", "sitting", "push"):
                    p = [r for r in rs if r["start"] == pose]
                    up = sorted(r["up_after_s"] for r in p if r["up_after_s"] is not None)
                    line = dict(ok=sum(r["success"] for r in p), n=len(p), up_median=up[len(up) // 2] if up else None,
                                up_max=up[-1] if up else None, max_action=max(r["max_action"] for r in p),
                                down_again=sum(sum(ph[1] == "limp" for ph in r["phases"]) > 1 for r in p),
                                gave_up=sum(any(ph[1] == "gave_up" for ph in r["phases"]) for r in p),
                                guard_stops=sum(r["guard_stop_at"] is not None for r in p),
                                sat_max=max(r["sat_s_max_joint"] for r in p))
                    g.setdefault("per_start", {}).setdefault(pose, {})[k] = line
            for pose, v in g["per_start"].items():
                print(f"  {pose}: without {v[0]} | with {v[1]}")
        if group == "approach":
            for k in (0, 1):
                for dname in ("nodrift", "drift015"):
                    rs = [r["result"] for r in rows if r["refit"] == k and "result" in r and r["case"].startswith(dname)]
                    g.setdefault("passed", {}).setdefault(dname, {})[k] = f"{sum(r['ok'] for r in rs)}/{len(rs)}"
            print(f"  passed without / with: {g['passed']}")
        if group in ("suite", "teleop", "failure"):
            for k in (0, 1):
                rs = [r["result"] for r in rows if r["refit"] == k and "result" in r]
                g.setdefault("falls", {})[k] = sum(r.get("fell_at") is not None for r in rs)
                g.setdefault("max_tilt_median", {})[k] = round(statistics.median(r["max_tilt"] for r in rs), 2) if rs else None
            print(f"  falls without / with: {g['falls']}; median max_tilt {g['max_tilt_median']}")
        if group == "namecall":
            for k in (0, 1):
                rs = [r["result"] for r in rows if r["refit"] == k and "result" in r]
                g.setdefault("totals", {})[k] = {f: sum((r.get("summary", r).get(f) or 0) for r in rs)
                                                  for f in ("calls", "detected", "false_alarms", "falls")}
                g.setdefault("tilt_max", {})[k] = max((r.get("summary", r).get("tilt_max_deg") or {}).get("max", 0) for r in rs) if rs else None
            print(f"  totals without / with: {g['totals']}; tilt max {g['tilt_max']}")
        summary[group] = g
    json.dump(summary, open(os.path.join(RES, "summary.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
