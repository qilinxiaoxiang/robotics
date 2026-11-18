"""Acceptance of a universal checkpoint (UNIVERSAL-PLAN.md sections 4, 5, 7, 8) on the Mac mini, policy from the first tick.

  python3 train/accept_universal.py run <models dir under train/ckpt> [--episodes 20] [--chunk 8]
  python3 train/accept_universal.py score <models dir> [--ref fq2_1999]
`run` builds the case list, runs it through train/mini.sh in chunks (one simulation at a time, each chunk well under
10 minutes, style_eval.py for every case it covers and flight_eval.py for the shove and landing cases), pulls the
results to train/eval/ua_<dir>_<case>.json. `score` checks every acceptance line, against the reference dir's results
from the same machine (run the reference with `run` too), and writes out/accept_<dir>.json.
Cases (36):
  with the pack (make_suite.py's 14): nominal stand / walk / turnL / turnR; mass +10 %, COM x +-10 mm (stand, walk);
    0.5 N s shove at 8 s (stand, walk); landing hand-over (stand, walk)
  no pack, started as today (0.3 s open-loop stand): stand, walk, turnL, turnR
  partial loads 25 / 50 / 75 % and batteries out: stand, walk; full pack walk (load100) for the style line
  head motion at none / batteries out / full: standing scan (approach.py's), walking with head pitch 0.5 and 1.1
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
S0 = "--stand-s 0"
# Two seed sets (2026-11-12): checkpoints are picked on "dev" (seeds 0..19, files ua_*), the verdict on a picked one is
# run on "final" (seeds 1000..1099, files uaf_*), which is never used for picking. Each set has its own result files,
# so a final run never skips because a dev file exists, and score refuses files whose seeds or count do not match.
SETS = {"dev": dict(prefix="ua", seed0=0, episodes=20), "final": dict(prefix="uaf", seed0=1000, episodes=100)}
SET = SETS["dev"]
SCAN = "--dance train/specs/head_scan_dance.json"


def cases(models):
    c = []

    def add(name, manifest, case, extra=S0, tool="style", flags=""):
        c.append(dict(name=name, manifest=manifest, case=case, extra=extra, tool=tool, flags=flags))
    for k in ("stand", "walk", "turnL", "turnR"):
        add(f"nominal_{k}", "nominal", k)
    for m in ("mass+10", "comx+10", "comx-10"):
        for k in ("stand", "walk"):
            add(f"{m}_{k}", m, k)
    for k in ("stand", "walk"):
        add(f"nominal_{k}_shove05", "nominal", k, tool="flight", flags="--shove-ns 0.5 --shove-at 8")
        add(f"nominal_{k}_landing", "nominal", k, tool="flight", flags="--landing")
    for k in ("stand", "walk", "turnL", "turnR"):
        add(f"nopack_{k}", "none", k, extra="")
    for ld in ("load025", "load050", "load075", "nobatt"):
        for k in ("stand", "walk"):
            add(f"{ld}_{k}", ld, k)
    add("load100_walk", "load100", "walk")
    for ld, ex in (("none", ""), ("nobatt", S0), ("load100", S0)):
        add(f"head_scan_{ld}", ld, "stand", extra=f"{ex} {SCAN}".strip())
        add(f"head_walk05_{ld}", ld, "walk", extra=f"{ex} --head-pitch 0.5".strip())
        add(f"head_walk11_{ld}", ld, "walk", extra=f"{ex} --head-pitch 1.1".strip())
    return c


def command(models, e, episodes):
    out = f"train/eval/{SET['prefix']}_{models}_{e['name']}.json"
    man = f"train/manifests/flightpack-{e['manifest']}.json"
    tool = "style_eval.py" if e["tool"] == "style" else "flight_eval.py"
    name = f"--name {SET['prefix']}_{models}_{e['name']} " if e["tool"] == "style" else ""
    return (f"$PY train/{tool} {name}--models train/ckpt/{models} --manifest {man} --case {e['case']} --episodes {episodes} "
            f"--workers 8 --seed0 {SET['seed0']} {e['flags']} --extra='{e['extra']}' --out {out} > /dev/null 2>&1; echo done {e['name']}")


def run(a):
    mini = str(TRAIN / "mini.sh")
    subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
    todo = [e for e in cases(a.models) if (not a.only or e["name"] in a.only.split(","))
            and (a.redo or not (TRAIN / f"eval/{SET['prefix']}_{a.models}_{e['name']}.json").exists())]
    print(f"{len(todo)} cases to run for {a.models} ({a.set}: seeds {SET['seed0']}..{SET['seed0'] + a.episodes - 1})", flush=True)
    for i in range(0, len(todo), a.chunk):
        cmd = "; ".join(command(a.models, e, a.episodes) for e in todo[i:i + a.chunk])
        r = subprocess.run(["zsh", mini, "run", cmd], capture_output=True, text=True)
        print(r.stdout.replace("busy\n", "").strip()[-400:], flush=True)
        subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)


def load(models, name):
    p = TRAIN / f"eval/{SET['prefix']}_{models}_{name}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    s = d["summary"]
    eps = d.get("episodes", [])
    want = list(range(SET["seed0"], SET["seed0"] + SET["episodes"]))
    got = sorted(e.get("seed") for e in eps)
    if got != want:  # wrong seed set or a short run: not a result for this set
        print(f"seed check: {p.name} has {len(got)} episodes, seeds {got[:1]}..{got[-1:]}, expected {want[0]}..{want[-1]}")
        return None
    s["seeds"] = f"{want[0]}..{want[-1]}"
    yaws = [e.get("yaw_walk_deg") for e in eps if e.get("yaw_walk_deg") is not None and e.get("fell_at") is None]
    s["turn_rate_rad_s_median"] = round(sorted(yaws)[len(yaws) // 2] / 15.0 / 57.2958, 3) if yaws else None
    return s


def hip_p99(s):
    jp = s.get("joint_p99_nm") or {}
    v = [x for k, x in jp.items() if "hip" in k]
    return max(v) if v else None


def score(a):
    refs = a.ref.split(",")
    lines, ok_all, missing = lines_for(a.models, refs[0])
    for i, rn in enumerate(refs):
        ref_by = {ln["line"]: ln for ln in lines_for(rn, refs[0])[0]}
        for ln in lines:
            r = ref_by.get(ln["line"])
            ln["ref" if i == 0 else f"ref_{rn}"] = f"{r['result']} {r['detail']}" if r else None
    out = dict(models=a.models, ref=a.ref, missing=missing, verdict="PASS" if ok_all and not missing else "FAIL", lines=lines)
    suffix = "" if a.set == "dev" else f"_{a.set}"
    out["set"], out["seeds"] = a.set, f"{SET['seed0']}..{SET['seed0'] + SET['episodes'] - 1}"
    (TRAIN / f"out/accept_{a.models}{suffix}.json").write_text(json.dumps(out, indent=1))
    for ln in lines:
        extra = "".join(f"  || {rn}: {ln[f'ref_{rn}']}" for rn in refs[1:])
        print(f"{ln['result']:7s} {ln['line']}: {ln['detail']}  || {refs[0]}: {ln['ref']}{extra}")
    print(f"verdict {out['verdict']}; missing cases {missing}")


def lines_for(models, ref):
    class A:
        pass
    a = A()
    a.models, a.ref = models, ref
    lines, ok_all = [], True

    def line(name, ok, detail):
        nonlocal ok_all
        ok_all &= bool(ok)
        lines.append(dict(line=name, result="PASS" if ok else ("FAIL" if ok is not None else "MISSING"), detail=detail))

    cs = cases(a.models)
    R = {e["name"]: load(a.models, e["name"]) for e in cs}
    F = {e["name"]: load(a.ref, e["name"]) for e in cs}
    missing = [k for k, v in R.items() if v is None]
    pack = [e["name"] for e in cs[:14]]
    if all(R[k] for k in pack):
        falls = sum(R[k]["falls"] for k in pack)
        rf = sum(F[k]["falls"] for k in pack) if all(F[k] for k in pack) else None
        # One line per scenario (2026-11-12): the 14-case sum let a gain in one case hide a loss in another.
        for k in pack:
            fk = F[k]["falls"] if F[k] else None
            line(f"with pack, {k}: falls no more than the reference", fk is not None and R[k]["falls"] <= fk,
                 f"{R[k]['falls']} vs {a.ref} {fk}")
        lines.append(dict(line="with pack: falls summed over the 14 cases (information, not a gate)", result="INFO",
                          detail=f"{falls} vs {a.ref} {rf}"))
        # Walk speed is judged by the 0.15 m/s floor at every load below (the old 0.099 line was a weaker duplicate).
        p = R["nominal_walk"].get("leg_force_p99_nm_median")
        line("with pack: walk torque p99 at most 0.48 N m", p is not None and p <= 0.48, f"{p}")
    nop = [f"nopack_{k}" for k in ("stand", "walk", "turnL", "turnR")]
    if all(R[k] for k in nop):
        line("no pack: 0 falls (80 episodes)", sum(R[k]["falls"] for k in nop) == 0, str({k: R[k]["falls"] for k in nop}))
        v = R["nopack_walk"]["speed_median_upright"]
        # The old 0.082-0.15 band came from the earlier with-pack plan and contradicted the 0.15 m/s floor below
        # (2026-11-11); one rule now: no upper limit, same floor as every load.
        line("no pack: walk at least 0.15 m/s on the 0.25 command", v is not None and v >= 0.15, f"{v}")
        tl, tr = R["nopack_turnL"]["turn_rate_rad_s_median"], R["nopack_turnR"]["turn_rate_rad_s_median"]
        line("no pack: turns within 10 % of +-0.3 rad/s", tl is not None and tr is not None and abs(abs(tl) - 0.3) <= 0.03
             and abs(abs(tr) - 0.3) <= 0.03, f"turnL {tl}, turnR {tr}")
    for ld in ("load025", "load050", "load075", "nobatt"):
        st, wk = R[f"{ld}_stand"], R[f"{ld}_walk"]
        if st and wk:
            hp = max(x for x in (hip_p99(st), hip_p99(wk)) if x is not None)
            sat = max(st.get("leg_force_sat_frac_max", 0), wk.get("leg_force_sat_frac_max", 0))
            line(f"{ld}: 0 falls, hip p99 <= 0.45, <= 1 % at 95 % of clamp (speed: the 0.15 floor line)",
                 st["falls"] == 0 and wk["falls"] == 0 and hp <= 0.45 and sat <= 0.01,
                 f"falls {st['falls']}/{wk['falls']}, walk {wk['speed_median_upright']}, hip p99 {hp}, sat {sat}")
    st, wk = R["nominal_stand"], R["load100_walk"]
    if st and wk:
        line("load100 (full pack): 0 falls stand and walk (per-load view of the with-pack line)",
             st["falls"] == 0 and wk["falls"] == 0,
             f"falls {st['falls']}/{wk['falls']}, walk fall times {wk.get('fall_times', [])[:6]}, walk {wk['speed_median_upright']}")
    sp = {k: R[k]["speed_median_upright"] for k in ("nopack_walk", "load025_walk", "load050_walk", "load075_walk",
                                                       "nobatt_walk", "load100_walk", "nominal_walk") if R[k]}
    line("speed floor: at least 0.15 m/s on the 0.25 command at every load (section 4)", bool(sp) and min(sp.values()) >= 0.15,
         json.dumps(sp))
    for ld, k in (("none", "nopack_walk"), ("nobatt", "nobatt_walk"), ("full", "load100_walk")):
        s = R[k]
        if s:
            lm, rm = s.get("left_stance_toe_out_deg_mean"), s.get("right_stance_toe_out_deg_mean")
            lp, rp = s.get("left_stance_toe_out_deg_p95"), s.get("right_stance_toe_out_deg_p95")
            sw = s.get("step_width_mm")
            ok = None if None in (lm, rm, lp, rp, sw) else (lm <= 12 and rm <= 9 and max(lp, rp) <= 15 and sw <= 105)
            line(f"toe-out at {ld}: mean <= 12 L / 9 R deg, p95 <= 15, step width <= 105 mm", ok,
                 f"mean {lm} / {rm}, p95 {lp} / {rp}, step width {sw}")
    for ld in ("none", "nobatt", "load100"):
        hs = [R[f"head_{c}_{ld}"] for c in ("scan", "walk05", "walk11")]
        if all(hs):
            line(f"head motion at {ld}: scan and head-down walks 0 falls", all(h["falls"] == 0 for h in hs),
                 f"falls {[h['falls'] for h in hs]}, head-down walk speeds {hs[1]['speed_median_upright']} / {hs[2]['speed_median_upright']}")
    return lines, ok_all, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("run", "score"))
    ap.add_argument("models")
    ap.add_argument("--set", choices=sorted(SETS), default="dev")
    ap.add_argument("--episodes", type=int, default=None, help="default: the set's count (dev 20, final 100)")
    ap.add_argument("--only", default="", help="comma-separated case names to run (score still needs every case)")
    ap.add_argument("--chunk", type=int, default=None, help="cases per Mac mini job (default 8 for dev, 2 for final)")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--ref", default="fq2_1999")
    a = ap.parse_args()
    global SET
    SET = dict(SETS[a.set])
    if a.episodes:
        SET["episodes"] = a.episodes
    a.episodes = SET["episodes"]
    a.chunk = a.chunk or (8 if a.set == "dev" else 2)
    run(a) if a.mode == "run" else score(a)


if __name__ == "__main__":
    main()
