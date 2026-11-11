"""Airborne perturbation batch: every case x scenario x seed through flight.py in a process pool, then a summary.

Take-off configuration for all cases (from the drift tests, sim/out/drift/summary3.txt): hover trim calibrated
(--com-est true: the mixer knows the nominal COM in the start pose, not the perturbation), level attitude target on the
ground, collective ramp to 1.6 x weight in 0.1 s.

  $PY sim/batch.py [--seeds 3] [--jobs N] [--only case,case]     -> sim/out/batch/<case>__<scenario>__s<seed>.json, summary.json
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
OUT = H / "out" / "batch"
FORCE = False
FIX = ["--com-est", "true", "--ground-pitch", "level", "--takeoff-twr", "1.6", "--takeoff-ramp", "0.1"]
SCEN = ["hover", "table_up", "table_down"]
CASES = {
    "nominal": [],
    "thrust90": ["--thrust", "0.9"], "thrust80": ["--thrust", "0.8"], "thrust70": ["--thrust", "0.7"],
    "mass+5": ["--mass-variant", "mass+5"], "mass+10": ["--mass-variant", "mass+10"],
    "comx+5": ["--mass-variant", "comx+5"], "comx-5": ["--mass-variant", "comx-5"],
    "comx+10": ["--mass-variant", "comx+10"], "comx-10": ["--mass-variant", "comx-10"],
    "comy+5": ["--mass-variant", "comy+5"], "comy-5": ["--mass-variant", "comy-5"],
    "comy+10": ["--mass-variant", "comy+10"], "comy-10": ["--mass-variant", "comy-10"],
    # the held stand pose falls within 0.6 s at these COM offsets (ground failure); armed at t 0 the fans catch it
    "comx+5_arm0": ["--mass-variant", "comx+5", "--arm-at", "0.0"], "comx-5_arm0": ["--mass-variant", "comx-5", "--arm-at", "0.0"],
    "comx+10_arm0": ["--mass-variant", "comx+10", "--arm-at", "0.0"], "comx-10_arm0": ["--mass-variant", "comx-10", "--arm-at", "0.0"],
    "tau0.05": ["--tau", "0.05"], "tau0.15": ["--tau", "0.15"], "tau0.20": ["--tau", "0.20"],
    "tau0.20_retune": ["--tau", "0.20", "--retune"],
    "delay20ms": ["--sensor-delay", "0.02"], "delay50ms": ["--sensor-delay", "0.05"],
    "weak_RF": ["--weak-fan", "0"], "weak_LR": ["--weak-fan", "1"], "weak_LF": ["--weak-fan", "2"], "weak_RR": ["--weak-fan", "3"],
    "push2N": ["--gust", "2.0"], "push4N": ["--gust", "4.0"],
    "soc30": ["--soc", "0.3"],
    "fan113": ["--mass-variant", "fan113"],
    "naive_range": ["--naive-range"],
    "eff-30pct": ["--power-scale", str(1 / 0.7)], "eff-60pct": ["--power-scale", str(1 / 0.4)],
    # ARESWEI HDS001 4650KV (fan change 2026-11-10): vendor point 980 g, 40 A at 16.8 V
    "ARE_nominal": ["--fan", "areswei"], "ARE_thrust90": ["--fan", "areswei", "--thrust", "0.9"],
    "ARE_thrust80": ["--fan", "areswei", "--thrust", "0.8"], "ARE_thrust70": ["--fan", "areswei", "--thrust", "0.7"],
    "ARE_eff-30pct": ["--fan", "areswei", "--power-scale", str(1 / 0.7)],
    "ARE_eff-60pct": ["--fan", "areswei", "--power-scale", str(1 / 0.4)],
    # is the 70-80 % thrust failure the lean limit (headroom) or the thrust itself? one knob: lean limit 10 deg
    "thrust80_lean10": ["--thrust", "0.8", "--lean-max", "10"], "thrust70_lean10": ["--thrust", "0.7", "--lean-max", "10"],
    "nominal_lean10": ["--lean-max", "10"],
}


def one(job):
    case, scen, seed = job
    f = OUT / f"{case}__{scen}__s{seed}.json"
    if f.exists() and not FORCE:
        return f
    cmd = [sys.executable, str(H / "flight.py"), "--scenario", scen, "--case", case, "--seed", str(seed), *FIX, *CASES[case],
           "--out", str(f)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f


def summarize():
    rows = [json.load(open(f)) for f in sorted(OUT.glob("*__*__s*.json"))]
    summ = {}
    for case in CASES:
        for scen in SCEN:
            rs = [r for r in rows if r["case"] == case and r["scenario"] == scen]
            if not rs:
                continue
            def vals(k, sub=None):
                v = [(r.get(k) or {}).get(sub) if sub else r.get(k) for r in rs]
                return [x for x in v if x is not None]
            def mx(k, sub=None):
                v = vals(k, sub); return round(max(v), 3) if v else None
            def mean(k):
                v = vals(k); return round(st.mean(v), 3) if v else None
            summ[f"{case}|{scen}"] = dict(
                n=len(rs), airborne_success=sum(r["airborne_success"] for r in rs), full_success=sum(r["success"] for r in rs),
                max_tilt_deg=mx("max_tilt_deg"), touchdown_vz_worst=min(vals("landing_vz_mps"), default=None),
                touchdown_pos_err_max_m=mx("touchdown_pos_err_m"), takeoff_drift_max_m=mx("takeoff_drift_m"),
                hover_throttle_pct=mean("hover_throttle_pct"), thrust_to_weight=mean("thrust_to_weight"),
                hover_current_a=mean("hover_current_a"), hover_minutes_80pct=mean("hover_minutes_80pct"),
                pack_current_peak_a=mx("pack_current_peak_a"), pack_current_avg_a=mean("pack_current_avg_a"),
                esc_channel_peak_a=mx("esc_channel_peak_a"), mah_used=mean("mah_used"), flight_s=mean("flight_s"),
                mixer_saturated_s=mx("mixer_saturated_s"), range_jumps=[r["range_jumps_at"][:4] for r in rs][:1],
                fell_at=[r["fell_at"] for r in rs], acc_v_peak_g=mx("trunk_acc_peak_g", "vertical"),
                acc_h_peak_g=mx("trunk_acc_peak_g", "horizontal"))
    (OUT / "summary.json").write_text(json.dumps(dict(fix=FIX, cases=CASES, summary=summ), indent=1))
    return summ


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument("--only", default=None)
    ap.add_argument("--air", action="store_true", help="airborne part only: start hovering 0.3 m above the start surface, trunk level")
    ap.add_argument("--force", action="store_true", help="rerun cases whose result file exists")
    a = ap.parse_args()
    FORCE = a.force
    if a.air:
        OUT = H / "out" / "batch_air"
        FIX += ["--start-air", "0.3", "--air-level"]
    OUT.mkdir(parents=True, exist_ok=True)
    cases = a.only.split(",") if a.only else list(CASES)
    jobs = [(c, s, k) for c in cases for s in SCEN for k in range(a.seeds)
            if not (c == "naive_range" and s == "hover")]
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(one, jobs))
    s = summarize()
    for k, v in s.items():
        print(k, "air", f"{v['airborne_success']}/{v['n']}", "full", v["full_success"], "tilt", v["max_tilt_deg"], "vz", v["touchdown_vz_worst"],
              "err", v["touchdown_pos_err_max_m"], "drift", v["takeoff_drift_max_m"], "I_hov", v["hover_current_a"], "Ipk", v["pack_current_peak_a"],
              "esc", v["esc_channel_peak_a"], "mAh", v["mah_used"])
