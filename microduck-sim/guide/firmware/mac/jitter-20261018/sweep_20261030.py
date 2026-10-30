"""Sweep jitter_sim.py hypothesis settings against the six 2026-10-30 robot rows (targets-20261030.json).

One setting = one list of extra jitter_sim/brain_sim_check flags applied to all three policies (never tuned per
policy). Every setting runs the six rows (walk61 default head; T1 default and neck -0.4; t2b default, neck -0.4 and
neck -0.8 for 2 s) at vx 0.25 for the robot's walk length (3 s, 2 s for the neck hold) on --seeds, with the real-condition
flags from robot_state_check.py --print-sim-args (CURRENT-STATE.json: 7.0 V, 4 % dropped reads) and the plugged
manifest. Metrics come from jitter_metrics.stats on the walking window, so sim and robot are scored identically.

Score per row: sim / robot ratio of jump_rate_per_s and tilt_max; a row passes when both lie within a factor of 2.
Ordering passes when every calm row (walk61, t2b default) has fewer jumps per s than every shaking row.

  ~/.venvs/microduck-dyn/bin/python sweep_20261030.py [--only NAME ...] [--seeds 0 1 2] [--list] [--summary]
  ~/.venvs/microduck-dyn/bin/python sweep_20261030.py --extra NAME FLAG ...   # one ad-hoc setting

Tick logs go to --logdir (default: this session's scratchpad); results to results-20261030/<name>.json (resumable).
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
SIM = os.path.join(HERE, "jitter_sim.py")
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
WHOLE = os.path.join(MAC, "..", "..", "..", "hardware-design-20260912", "whole-robot-20260912")
OVERLAY = os.path.join(WHOLE, "runtime-overlay")
MANIFEST = os.path.join(MAC, "..", "..", "..", "microduck_rl-grasp", "cmu", "model", "manifests", "plugged.json")
RESULTS = os.path.join(HERE, "results-20261030")
TARGETS = os.path.join(HERE, "targets-20261030.json")
WALK_AT = 4.0
TAIL = 3.0
TIMEOUT_S = 240

ROWS = [  # name, models dir, neck_pitch, walk s  (same order and names as make_targets.py)
    ("walk61_default", "models", None, 3.0),
    ("t1_default", "models-t1-best", None, 3.0),
    ("t1_neck-0.4", "models-t1-best", -0.4, 3.0),
    ("t2b_default", "models-t2b-best", None, 3.0),
    ("t2b_neck-0.4", "models-t2b-best", -0.4, 3.0),
    ("t2b_neck-0.8", "models-t2b-best", -0.8, 2.0),
]
CALM = ("walk61_default", "t2b_default")

SETTINGS = {
    "base": [],
    # servo position deadband on the legs (E1 10/15: loaded legs ignored 0.03-0.05 rad at P 200/400)
    "db0.02": ["--deadband", "0.02"],
    "db0.03": ["--deadband", "0.03"],
    "db0.04": ["--deadband", "0.04"],
    "db0.05": ["--deadband", "0.05"],
    "db0.06": ["--deadband", "0.06"],
    "db0.04h": ["--deadband", "0.04", "--deadband-head"],
    # BAM friction
    "stic1.5": ["--stiction-scale", "1.5"],
    "stic2.0": ["--stiction-scale", "2.0"],
    "fric1.25": ["--bam-friction-scale", "1.25"],
    "fric1.5": ["--bam-friction-scale", "1.5"],
    # firmware P gain the brain uses (real: KP_RL 200 = base)
    "kp160": ["--kp-rl", "160"],
    "kp300": ["--kp-rl", "300"],
    # measured ranges of the sensor path (drops 3.3-5.2 %, IMU 38-51/s)
    "drop0.052": ["--drop", "0.052"],
    "imu38": ["--imu-hz", "38"],
    # delays (ticks); base is sensor 1 / action 1 as trained
    "sdel2": ["--sensor-delay", "2"],
    "sdel3": ["--sensor-delay", "3"],
    "adel2": ["--action-delay", "2"],
    "obsdel1": ["--obs-delay", "1"],
    "obsdel2": ["--obs-delay", "2"],
    # head mass beyond the plugged manifest (U20CAM camera and lead in the head are not weighed there)
    "head+20g": ["--head-mass-g", "20"],
    "head+50g": ["--head-mass-g", "50"],
    # Pollen robotd filters (the runtime has none; effect only)
    "lp0.7": ["--lowpass", "0.7", "0.5"],
    "ascale0.9": ["--action-scale", "0.9"],
    # observation-side noise (robot trunk gyro 4-6x sim, broadband)
    "gn0.1": ["--gyro-noise", "0.1"],
    "gn0.3": ["--gyro-noise", "0.3"],
    "gn0.6": ["--gyro-noise", "0.6"],
    "gn1.0": ["--gyro-noise", "1.0"],
    "grn0.02": ["--grav-noise", "0.02"],
    "grn0.05": ["--grav-noise", "0.05"],
    "an0.02": ["--act-noise", "0.02"],
    "an0.05": ["--act-noise", "0.05"],
    # second wave: foot/floor (the robot's trunk gyro is 2-3x the sim's in the shaking rows while the leg actions are
    # only 1.3-2x, so the trunk is excited more per unit of leg motion: ankle play, sole, floor friction)
    "fp2": ["--foot-play", "2"],
    "fp4": ["--foot-play", "4"],
    "fp2roll": ["--foot-play", "2", "--foot-play-axis", "roll"],
    "soft0.05": ["--sole-solref", "0.05", "1"],
    "hard0.01": ["--sole-solref", "0.01", "1"],
    "mu0.7": ["--floor-mu", "0.7"],
    "mu1.3": ["--floor-mu", "1.3"],
    # second wave: after wave 1, gyro noise is the only single switch that keeps the ordering and lifts the calm rows
    # to the robot's level (gn0.3), but a constant floor cannot lift the shaking rows 3x more than the calm ones;
    # the robot's extra gyro power sits above 5 Hz and grows with the shaking, so try vibration proportional to leg
    # motion, intermediate noise levels, and noise combined with the friction and gain settings that raised the
    # shaking rows (fric1.25/1.5, kp160, stic2.0)
    "gn0.4": ["--gyro-noise", "0.4"],
    "gn0.45": ["--gyro-noise", "0.45"],
    "gndq0.15": ["--gyro-noise-dq", "0.15"],
    "gndq0.25": ["--gyro-noise-dq", "0.25"],
    "gndq0.4": ["--gyro-noise-dq", "0.4"],
    "gn0.3+fric1.25": ["--gyro-noise", "0.3", "--bam-friction-scale", "1.25"],
    "gn0.3+fric1.4": ["--gyro-noise", "0.3", "--bam-friction-scale", "1.4"],
    "gn0.3+kp160": ["--gyro-noise", "0.3", "--kp-rl", "160"],
    "gn0.3+stic2.0": ["--gyro-noise", "0.3", "--stiction-scale", "2.0"],
    "gn0.3+grn0.03": ["--gyro-noise", "0.3", "--grav-noise", "0.03"],
    "gn0.2+grn0.05": ["--gyro-noise", "0.2", "--grav-noise", "0.05"],
    "fric1.4": ["--bam-friction-scale", "1.4"],
    "fric1.25+kp160": ["--bam-friction-scale", "1.25", "--kp-rl", "160"],
    "gndq0.25+fric1.25": ["--gyro-noise-dq", "0.25", "--bam-friction-scale", "1.25"],
    # third wave: motion-driven gyro noise separates T1 from t2b as the robot does (17-18 vs 5 jumps/s); friction 1.5
    # alone made exactly the t2b neck rows shake (15/14 jumps/s, falls) but stopped walk61; try the two together
    "gndq0.25+fric1.4": ["--gyro-noise-dq", "0.25", "--bam-friction-scale", "1.4"],
    "gndq0.2+fric1.5": ["--gyro-noise-dq", "0.2", "--bam-friction-scale", "1.5"],
    "gndq0.3+fric1.4": ["--gyro-noise-dq", "0.3", "--bam-friction-scale", "1.4"],
    "gndq0.25+stic2.0": ["--gyro-noise-dq", "0.25", "--stiction-scale", "2.0"],
    "gndq0.25+fric1.25+stic1.5": ["--gyro-noise-dq", "0.25", "--bam-friction-scale", "1.25", "--stiction-scale", "1.5"],
}
WAVE2 = ["fp2", "fp4", "fp2roll", "soft0.05", "hard0.01", "mu0.7", "mu1.3", "gn0.4", "gn0.45", "gndq0.15", "gndq0.25",
         "gndq0.4", "gn0.3+fric1.25", "gn0.3+fric1.4", "gn0.3+kp160", "gn0.3+stic2.0", "gn0.3+grn0.03", "gn0.2+grn0.05",
         "fric1.4", "fric1.25+kp160", "gndq0.25+fric1.25"]


def real_condition():
    out = subprocess.check_output([sys.executable, os.path.join(MAC, "robot_state_check.py"), "--print-sim-args"], text=True)
    return out.split()


def run_one(name, row, seed, flags, logdir, cond):
    rname, models, neck, walk_s = row
    log = os.path.join(logdir, name, f"{rname}_s{seed}.jsonl")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    cmd = [PY, SIM, "--model", "asbuilt", "--manifest", MANIFEST, *cond, "--vx", "0.25", "--walk-at", str(WALK_AT),
           "--cmd-s", str(walk_s), "--tail", str(TAIL), "--seed", str(seed), "--models", os.path.join(OVERLAY, models),
           "--tick-log", log]
    if neck is not None:
        cmd += ["--neck-pitch", str(neck)]
    cmd += flags
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return dict(row=rname, seed=seed, error="timeout", wall_s=round(time.time() - t0, 1))
    js = None
    for line in reversed(p.stdout.splitlines()):
        if line.startswith("{"):
            js = json.loads(line)
            break
    if js is None:
        return dict(row=rname, seed=seed, error=(p.stderr or "")[-600:], wall_s=round(time.time() - t0, 1))
    sys.path.insert(0, HERE)
    import jitter_metrics as jm
    rows = jm.load(log)
    seg = jm.sim_segment(rows, WALK_AT, walk_s)
    m = jm.stats(seg, min_dur=1.0) if seg else None
    out = dict(row=rname, seed=seed, wall_s=round(time.time() - t0, 1), fell_at=js.get("fell_at"), run_max_tilt=js.get("max_tilt"),
               run_action_jumps=js.get("action_jumps"), dist_x=js.get("dist_x"), metrics=m)
    return out


def aggregate(runs):
    ok = [r for r in runs if r.get("metrics")]
    if not ok:
        return dict(n=0)
    def mean(k):
        v = [r["metrics"][k] for r in ok if r["metrics"].get(k) is not None]
        return round(sum(v) / len(v), 2) if v else None
    agg = dict(n=len(ok), jump_rate_per_s=mean("jump_rate_per_s"), tilt_max=mean("tilt_max"), tilt_mean=mean("tilt_mean"),
               act_p95=mean("act_p95"), leg_q_over_a=mean("leg_q_over_a"),
               jump_rate_range=[min(r["metrics"]["jump_rate_per_s"] for r in ok), max(r["metrics"]["jump_rate_per_s"] for r in ok)],
               tilt_max_range=[min(r["metrics"]["tilt_max"] for r in ok), max(r["metrics"]["tilt_max"] for r in ok)],
               fell=sum(1 for r in ok if r["metrics"]["fell"] or r.get("fell_at") is not None), dist_x=round(sum(r["dist_x"] or 0 for r in ok) / len(ok), 2))
    g = [r["metrics"]["gyro_rms"] for r in ok if r["metrics"].get("gyro_rms")]
    if g:
        agg["gyro_rms"] = [round(sum(x[i] for x in g) / len(g), 3) for i in range(3)]
    ba = {}
    for r in ok:
        for j, v in (r["metrics"].get("band_a_rms") or {}).items():
            ba[j] = ba.get(j, 0) + v / len(ok)
    agg["band_a_rms"] = {j: round(v, 3) for j, v in ba.items()}
    return agg


def score(agg_by_row, targets):
    """Per row: sim/robot ratios; pass = both within a factor of 2. Plus the calm-vs-shaking ordering."""
    rows, worst = {}, 0.0
    for t in targets["rows"]:
        a = agg_by_row.get(t["name"])
        if not a or not a.get("n"):
            rows[t["name"]] = dict(missing=True)
            worst = max(worst, 99)
            continue
        rj = (a["jump_rate_per_s"] or 1e-3) / t["jump_rate_per_s"]
        rt = (a["tilt_max"] or 1e-3) / t["tilt_max"]
        lj, lt = abs(math.log2(max(rj, 1e-3))), abs(math.log2(max(rt, 1e-3)))
        rows[t["name"]] = dict(jump_ratio=round(rj, 2), tilt_ratio=round(rt, 2), passes=lj <= 1 and lt <= 1,
                               sim=dict(jumps=a["jump_rate_per_s"], tilt=a["tilt_max"]),
                               robot=dict(jumps=t["jump_rate_per_s"], tilt=t["tilt_max"]))
        worst = max(worst, lj, lt)
    calm = [agg_by_row[n]["jump_rate_per_s"] for n in CALM if agg_by_row.get(n, {}).get("n")]
    shaking = [agg_by_row[n]["jump_rate_per_s"] for n, *_ in ROWS if n not in CALM and agg_by_row.get(n, {}).get("n")]
    ordering = bool(calm and shaking) and max(calm) < min(shaking)
    return dict(rows=rows, n_pass=sum(1 for r in rows.values() if r.get("passes")), ordering=ordering, worst_log2=round(worst, 2))


def one_line(name, res):
    s = res["score"]
    parts = []
    for rn, *_ in ROWS:
        a = res["rows"].get(rn, {})
        parts.append(f"{a.get('jump_rate_per_s', '-')}/{a.get('tilt_max', '-')}" + ("F" if a.get("fell") else ""))
    return f"{name:12s} " + " ".join(f"{p:>10s}" for p in parts) + f"  pass {s['n_pass']}/6 order {'y' if s['ordering'] else 'n'} worst2^{s['worst_log2']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--extra", nargs="+", action="append", default=[], metavar=("NAME", "FLAG"))
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    ap.add_argument("--logdir", default=os.environ.get("JITTER_LOGDIR", os.path.join(HERE, "results-20261030", "ticklogs")))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    settings = dict(SETTINGS)
    for e in a.extra:
        settings[e[0]] = e[1:]
    if a.list:
        for k, v in settings.items():
            print(k, " ".join(v))
        return
    targets = json.load(open(TARGETS))
    os.makedirs(RESULTS, exist_ok=True)
    if a.summary:
        print(f"{'setting':12s} " + " ".join(f"{r[0][:10]:>10s}" for r in ROWS) + "   (jumps/s / peak tilt deg, F = fell)")
        tgt = " ".join(f"{t['jump_rate_per_s']}/{t['tilt_max']}".rjust(10) for t in targets["rows"])
        print(f"{'ROBOT':12s} {tgt}")
        summary = dict(targets=os.path.relpath(TARGETS, HERE), columns=[r[0] for r in ROWS], settings={})
        for f in sorted(os.listdir(RESULTS)):
            if f.endswith(".json") and not f.startswith(("mechanism-", "long10s-", "summary")):
                res = json.load(open(os.path.join(RESULTS, f)))
                print(one_line(res["name"], res))
                summary["settings"][res["name"]] = dict(flags=res["flags"], score=res["score"], rows={
                    rn: {k: a.get(k) for k in ("n", "jump_rate_per_s", "jump_rate_range", "tilt_max", "tilt_max_range", "tilt_mean", "fell", "dist_x", "leg_q_over_a", "gyro_rms")}
                    for rn, a in res["rows"].items()})
        json.dump(summary, open(os.path.join(RESULTS, "summary.json"), "w"), indent=1)
        return
    cond = real_condition()
    names = a.only if a.only else ([e[0] for e in a.extra] or list(settings))
    for name in names:
        flags = settings[name]
        path = os.path.join(RESULTS, f"{name}.json")
        if os.path.exists(path) and not a.force:
            res = json.load(open(path))
            print(one_line(name, res), "(cached)", flush=True)
            continue
        runs = []
        for row in ROWS:
            for seed in a.seeds:
                r = run_one(name, row, seed, flags, a.logdir, cond)
                runs.append(r)
                if r.get("error"):
                    print(f"  {name} {row[0]} s{seed} ERROR {r['error'][:200]}", flush=True)
        agg = {rn: aggregate([r for r in runs if r["row"] == rn]) for rn, *_ in ROWS}
        res = dict(name=name, flags=flags, real_condition=cond, manifest=os.path.relpath(MANIFEST, HERE), seeds=a.seeds,
                   walk_at=WALK_AT, tail=TAIL, rows=agg, score=score(agg, targets), runs=runs, logdir=a.logdir)
        json.dump(res, open(path, "w"), indent=1)
        print(one_line(name, res), flush=True)


if __name__ == "__main__":
    main()
