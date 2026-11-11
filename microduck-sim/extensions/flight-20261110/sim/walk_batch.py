"""Ground phase with the pack, zero-training options (sim/walk_case.py over brain_sim_check), N seeds each, 20 s episodes.

Real-condition flags: --volt 7.6 --drop 0.036 (robot_state_check.py --print-sim-args, 2026-11-10).
Policies: walk61/stand61 (CURRENT-STATE walking_policy: walk61 at 0.25 m/s, KP_RL 200, stand KP 400, verified 2026-10-18).
Commands: stand = walk mode at zero command (stand61) from t 0; vx025 = 0.25 m/s from t 3 for 17 s.

  $PY sim/walk_batch.py [--seeds 10] [--jobs 6] [--only case,...]  -> sim/out/walk/<case>__<cmd>__s<seed>.json, summary.json
"""
import argparse
import json
import os
import statistics as st
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

H = Path(__file__).resolve().parent
OUT = H / "out" / "walk"
BASE = ["--model", "asbuilt", "--volt", "7.6", "--drop", "0.036", "--stand-s", "0"]
CMDS = {"stand": ["--walk-at", "3", "--walk-s", "17", "--vx", "0"],
        "vx025": ["--walk-at", "3", "--walk-s", "17", "--vx", "0.25"],
        "turnL": ["--walk-at", "3", "--walk-s", "17", "--vx", "0", "--vtheta", "0.3"],
        "turnR": ["--walk-at", "3", "--walk-s", "17", "--vx", "0", "--vtheta", "-0.3"]}


def man(v):
    return ["--manifest", str(H / "out" / f"manifest_pack_{v}.json")]


CASES = {
    # (a) battery placement (design variants), and the earlier COM-forward variant
    "none": man("none"), "nominal": man("nominal"),
    "batt_fwd40": man("batt_fwd40"), "batt_down20": man("batt_down20"), "batt_fwd40_down20": man("batt_fwd40_down20"),
    # (b) servo gain and action scaling for the doubled mass
    "kp300": man("nominal") + ["--kp-rl", "300"], "kp400": man("nominal") + ["--kp-rl", "400"],
    "act0.8": man("nominal") + ["--action-scale", "0.8"], "act1.25": man("nominal") + ["--action-scale", "1.25"],
    # (d) crouch held open-loop the whole episode, and crouch for 2 s then stand61
    "crouchA_hold": man("nominal") + ["--crouch", "10,-20,10", "--stand-s", "20"],
    "crouchB_hold": man("nominal") + ["--crouch", "-10,20,-10", "--stand-s", "20"],
    "crouchA_then61": man("nominal") + ["--crouch", "10,-20,10", "--stand-s", "2"],
    "crouchB_then61": man("nominal") + ["--crouch", "-10,20,-10", "--stand-s", "2"],
    # (e) partial thrust with the attitude loop (fans as a balance aid), and collective only
    "thrust25": man("nominal") + ["--thrust-frac", "0.25", "--thrust-at", "0"],
    "thrust40": man("nominal") + ["--thrust-frac", "0.40", "--thrust-at", "0"],
    "thrust50": man("nominal") + ["--thrust-frac", "0.50", "--thrust-at", "0"],
    "thrust40_yaw": man("nominal") + ["--thrust-frac", "0.40", "--thrust-at", "0", "--yaw-hold", "1"],
    "thrust50_yaw": man("nominal") + ["--thrust-frac", "0.50", "--thrust-at", "0", "--yaw-hold", "1"],
    "thrust40_noatt": man("nominal") + ["--thrust-frac", "0.40", "--thrust-at", "0", "--att-wn", "0"],
    "thrust50_noatt": man("nominal") + ["--thrust-frac", "0.50", "--thrust-at", "0", "--att-wn", "0"],
}
MAIN = {"none", "nominal", "thrust25", "thrust40", "thrust50", "thrust40_yaw", "thrust50_yaw"}


def one(job):
    case, cmd, seed = job
    f = OUT / f"{case}__{cmd}__s{seed}.json"
    if f.exists():
        return
    args = list(CASES[case])
    if "--stand-s" in args:     # the case sets its own open-loop time: drop BASE's
        b = [x for x in BASE]
        i = b.index("--stand-s"); del b[i:i + 2]
    else:
        b = BASE
    subprocess.run([sys.executable, str(H / "walk_case.py"), *b, *args, *CMDS[cmd], "--seed", str(seed), "--out", str(f)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def summarize():
    summ = {}
    for f in sorted(OUT.glob("*__*__s*.json")):
        case, cmd, _ = f.stem.split("__")
        r = json.loads(f.read_text())
        summ.setdefault(f"{case}|{cmd}", []).append(r)
    out = {}
    for k, rs in summ.items():
        p = [r["pack"] for r in rs]
        ok = [r for r in rs if r["fell_at"] is None]
        def mean(v):
            v = [x for x in v if x is not None]; return round(st.mean(v), 3) if v else None
        out[k] = dict(n=len(rs), falls=len(rs) - len(ok), fell_at=sorted(r["fell_at"] for r in rs if r["fell_at"] is not None)[:5],
                      fall_dirs=sorted({r["fall_dir"] for r in rs if r["fall_dir"]}),
                      speed_mps=mean([q["speed_mps"] for q in p]), dist_x_m=mean([r["dist_x"] for r in ok]),
                      yaw_walk_deg=mean([abs(r["yaw_walk_deg"]) for r in ok if r["yaw_walk_deg"] is not None]),
                      trunk_rms_roll_deg=mean([q["trunk_rms_deg"]["roll"] for q in p]), trunk_rms_pitch_deg=mean([q["trunk_rms_deg"]["pitch"] for q in p]),
                      tau_peak_max_nm=round(max(max(q["tau_peak_nm"].values()) for q in p), 3),
                      tau_peak_joint=max(p[0]["tau_peak_nm"], key=p[0]["tau_peak_nm"].get),
                      tau_rms_max_nm=round(max(max(q["tau_rms_nm"].values()) for q in p), 3),
                      time_at_limit_max_s=round(max(max(q["time_at_limit_s"].values()) for q in p), 2),
                      servo_limit_nm=p[0]["servo_limit_nm"], fan_current_avg_a=mean([q["fan_current_avg_a"] for q in p]),
                      pack_current_peak_a=mean([q["pack_current_peak_a"] for q in p]),
                      minutes_80pct=mean([q["minutes_per_2600mah_80pct"] for q in p]), max_tilt=round(max(r["max_tilt"] for r in rs), 1))
    (OUT / "summary.json").write_text(json.dumps(dict(base=BASE, cmds=CMDS, cases=CASES, summary=out), indent=1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--screen-seeds", type=int, default=5)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cases = a.only.split(",") if a.only else list(CASES)
    jobs = []
    for c in cases:
        n = a.seeds if c in MAIN else a.screen_seeds
        jobs += [(c, m, s) for m in ("stand", "vx025") for s in range(n)]
        if c in MAIN:
            jobs += [(c, m, s) for m in ("turnL", "turnR") for s in range(a.screen_seeds)]
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(one, jobs))
    for k, v in summarize().items():
        print(k, f"falls {v['falls']}/{v['n']}", "at", v["fell_at"], v["fall_dirs"], "speed", v["speed_mps"], "yaw", v["yaw_walk_deg"],
              "rms r/p", v["trunk_rms_roll_deg"], v["trunk_rms_pitch_deg"], "tau_pk", v["tau_peak_max_nm"], v["tau_peak_joint"],
              "lim_s", v["time_at_limit_max_s"], "I", v["fan_current_avg_a"], "min", v["minutes_80pct"])
