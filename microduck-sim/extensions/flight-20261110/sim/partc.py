"""Part C, thrust-assisted walking with today's policies (no training): sim/walk_case.py cases through walk_batch's pool.

  (a) vertical offload 0/25/50/75 % of the with-pack weight (attitude loop on), at vx 0.25 / 0.4 / 0.6, vs the duck without pack
  (b) shove survival during a 0.25 m/s walk: 0.5 / 1.0 / 1.5 / 2.0 N s lateral at t 8, no pack vs 25 / 50 % offload
  (c) idealised forward force 5 / 10 % of weight on top of 50 % offload at vx 0.4 / 0.6 (an upper bound: the fixed fans
      make forward force only by leaning the trunk or by fore-aft differential, which also pitches)

  $PY sim/partc.py [--seeds 5] [--jobs 6]   -> sim/out/partc/<case>__<cmd>__s<seed>.json, summary.json
"""
import argparse
from concurrent.futures import ThreadPoolExecutor

import walk_batch as wb

wb.OUT = wb.H / "out" / "partc"
wb.CMDS = {f"vx{v}": ["--walk-at", "3", "--walk-s", "17", "--vx", v] for v in ("0.25", "0.4", "0.6")}
wb.CMDS["vx0.25_shove"] = ["--walk-at", "3", "--walk-s", "17", "--vx", "0.25", "--shove-at", "8"]
NOM, NONE = wb.man("nominal"), wb.man("none")
C = {"none": NONE}
for f in ("0.25", "0.50", "0.75"):
    C[f"off{f}"] = NOM + ["--thrust-frac", f, "--thrust-at", "0"]
for ns in ("0.5", "1.0", "1.5", "2.0"):
    C[f"none_shove{ns}"] = NONE + ["--shove-ns", ns]
    C[f"off0.25_shove{ns}"] = NOM + ["--thrust-frac", "0.25", "--thrust-at", "0", "--shove-ns", ns]
    C[f"off0.50_shove{ns}"] = NOM + ["--thrust-frac", "0.50", "--thrust-at", "0", "--shove-ns", ns]
for fw in ("0.05", "0.10"):
    C[f"off0.50_fwd{fw}"] = NOM + ["--thrust-frac", "0.50", "--thrust-at", "0", "--fwd-frac", fw]
wb.CASES = C

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    wb.OUT.mkdir(parents=True, exist_ok=True)
    jobs = []
    for c in C:
        if "shove" in c:
            cmds = ["vx0.25_shove"]
        elif "fwd" in c:
            cmds = ["vx0.4", "vx0.6"]
        else:
            cmds = ["vx0.25", "vx0.4", "vx0.6"]
        jobs += [(c, m, s) for m in cmds for s in range(a.seeds)]
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(wb.one, jobs))
    for k, v in wb.summarize().items():
        print(k, f"falls {v['falls']}/{v['n']}", "at", v["fell_at"], "speed", v["speed_mps"], "dist", v["dist_x_m"], "yaw", v["yaw_walk_deg"],
              "rms r/p", v["trunk_rms_roll_deg"], v["trunk_rms_pitch_deg"], "tau_pk", v["tau_peak_max_nm"], "tau_rms", v["tau_rms_max_nm"],
              "lim_s", v["time_at_limit_max_s"], "I", v["fan_current_avg_a"], "min", v["minutes_80pct"])
