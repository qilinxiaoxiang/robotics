"""Batches of brain_sim_check.py sit -> rise -> hand-over runs through rise_run.py, with per-tick metrics of the rise.
Mac mini only (sims); one JSON row per run in results/<set>.jsonl, tick logs under ~/sims/sit-rise-20261029/ticks/.

  ~/.venvs/microduck-dyn/bin/python rise_batch.py SET [SET ...] [--jobs 8]

Every run: as-built plant, real-condition flags from microduck-sim/CURRENT-STATE.json (7.0 V, 4 % dropped reads, via
robot_state_check.py --print-sim-args on 2026-10-29), walk at zero command, {"mode": "sit"} at 4 s, a walk at zero
command at 10 s (the stand-up), the plugged manifest of microduck_rl 87979d52 unless a variant names another.
"""
import argparse
import concurrent.futures as cf
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(MAC, "..", "..", "..", ".."))
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
TICKS = os.path.expanduser("~/sims/sit-rise-20261029/ticks")
if os.path.basename(ROOT) != "rt":  # a bisect copy (make_variant.sh): its own tick folder
    TICKS = os.path.join(TICKS, os.path.basename(ROOT))
SIMS = os.path.expanduser("~/sims")
MAN = {
    "now": os.path.join(ROOT, "microduck-sim/microduck_rl/cmu/model/manifests/plugged.json"),
    "old1019": os.path.join(SIMS, "bvh-refit-20261029/plugged-20261019.json"),
    "saddle": os.path.join(ROOT, "microduck-sim/guide/print/a7z-saddle/balance/manifest-saddle.json"),
    "asbuilt": None,  # the asbuilt config's own 10-15 manifest
}
HF_MODELS = os.path.join(SIMS, "sit-rise-20261029/models-hfsit")  # runtime-overlay/models with HF alpha_sitstand (665ae4e)
SIT_AT, UNSIT_AT = 4.0, 10.0
sys.path.insert(0, MAC)
from walk_brain import NAMES, SIT_KNEE_MIN  # noqa: E402

LK, RK = NAMES.index("left_knee"), NAMES.index("right_knee")


def V(label, seeds, rr=(), man="now", volt=7.0, drop=0.04, model="asbuilt", extra=(), until=None, models=None,
      sit=True):
    return dict(label=label, seeds=list(seeds), rr=list(rr), man=man, volt=volt, drop=drop, model=model,
                extra=list(extra), until=until, models=models, sit=sit)


LONG = ["--unsit-s", "14"]  # the rise runs 14 s: does it ever finish?
ROBOTD = ["--rise-kp", "160", "--sit-lowpass", "0.7", "--head-lowpass", "0.5"]
SETS = {
    "cause": [
        V("long_now", range(4), LONG, until=30),
        V("long_drop0", [0], LONG, drop=0.0, until=30),
        V("long_v74", range(4), LONG, volt=7.4, until=30),
        V("long_v80", range(2), LONG, volt=8.0, until=30),
        V("long_old1019", range(4), LONG, man="old1019", until=30),
        V("long_asbuilt1015", range(2), LONG, man="asbuilt", until=30),
        V("long_saddle", range(2), LONG, man="saddle", until=30),
        V("long_v19", range(2), LONG, man="asbuilt", model="v19", until=30),
        V("long_kp160", range(4), LONG + ["--rise-kp", "160"], until=30),
        V("long_lowpass", range(4), LONG + ["--sit-lowpass", "0.7", "--head-lowpass", "0.5"], until=30),
        V("long_robotd", range(4), LONG + ROBOTD, until=30),
        V("long_hf", range(4), LONG, until=30, models=HF_MODELS),
        V("long_hf_robotd", range(4), LONG + ROBOTD, until=30, models=HF_MODELS),
    ],
    # walk_brain.py's Wi-Fi main (fake_pi + the runner) runs Brain(compensation=True); walk_wired.py on the A7Z and
    # brain_sim_check.py default to none
    "comp": [
        V("long_comp", range(4), LONG, extra=["--compensation"], until=30),
        V("timer2_comp", range(8), extra=["--compensation"]),
        V("long_comp_drop0", [0], LONG, drop=0.0, extra=["--compensation"], until=30),
        V("long_comp_asbuilt1015", range(2), LONG, man="asbuilt", extra=["--compensation"], until=30),
    ],
    # fake_pi.py's plant: dynamics/evaluate.py load (no BVH refit), the 10-15 asbuilt manifest, no read drops
    "stale": [
        V("long_stale_asbuilt1015", range(2), LONG + ["--stale-bvh"], man="asbuilt", until=30),
        V("long_stale_asbuilt1015_drop0", [0], LONG + ["--stale-bvh"], man="asbuilt", drop=0.0, until=30),
        V("long_stale_asbuilt1015_comp_drop0", [0], LONG + ["--stale-bvh"], man="asbuilt", drop=0.0,
          extra=["--compensation"], until=30),
        V("long_stale_now", range(2), LONG + ["--stale-bvh"], until=30),
        V("timer2_stale_asbuilt1015_comp_drop0", [0], ["--stale-bvh"], man="asbuilt", drop=0.0, extra=["--compensation"]),
    ],
    # loop latency: brain_sim_check defaults to a 1-tick sensor delay and a 1-tick action delay
    "latency": [
        V("long_sd0", range(4), LONG, extra=["--sensor-delay", "0"], until=30),
        V("long_ad0", range(4), LONG, extra=["--action-delay", "0"], until=30),
        V("long_sd0_ad0", range(2), LONG, extra=["--sensor-delay", "0", "--action-delay", "0"], until=30),
        V("long_sd2", range(2), LONG, extra=["--sensor-delay", "2"], until=30),
        V("long_sd0_asbuilt1015_drop0", [0], LONG, man="asbuilt", drop=0.0, extra=["--sensor-delay", "0"], until=30),
    ],
    # fake_pi's loop in-process: its plant (stale BVH, 10-15 manifest, no drops, compensation on) with the shorter
    # loop delay its servo emulation gives (applied age 17 ms, the brain's read 12 ms) instead of the 1 + 1 tick default
    "fakepi_like": [
        V("long_fp_ad0", range(2), LONG + ["--stale-bvh"], man="asbuilt", drop=0.0,
          extra=["--compensation", "--action-delay", "0"], until=30),
        V("long_fp_sd0", range(2), LONG + ["--stale-bvh"], man="asbuilt", drop=0.0,
          extra=["--compensation", "--sensor-delay", "0"], until=30),
        V("long_fp_sd0_ad0", range(2), LONG + ["--stale-bvh"], man="asbuilt", drop=0.0,
          extra=["--compensation", "--sensor-delay", "0", "--action-delay", "0"], until=30),
        V("long_fp_nocomp_ad0", range(2), LONG + ["--stale-bvh"], man="asbuilt", drop=0.0,
          extra=["--action-delay", "0"], until=30),
        V("long_fp_nocomp_sd0_ad0", range(2), LONG + ["--stale-bvh"], man="asbuilt", drop=0.0,
          extra=["--sensor-delay", "0", "--action-delay", "0"], until=30),
        V("long_fp_sd0_ad0_now", range(2), LONG,
          extra=["--compensation", "--sensor-delay", "0", "--action-delay", "0"], until=30),
    ],
    # the same sit -> stand-up under whatever walk_brain.py the snapshot holds: run in the repository snapshot (the
    # evidence hand-over) and in a copy with walk_brain.py from e4a92b4 (the 2 s timer) for before/after
    "ba": [
        V("ba_now", range(8)),
        V("ba_comp", range(8), extra=["--compensation"]),
        V("ba_sd0", range(8), extra=["--sensor-delay", "0"]),
        V("ba_tostand", range(4), ["--to-stand"]),
        V("ba_old1019", range(4), man="old1019"),
        V("ba_v74", range(4), volt=7.4),
    ],
    # the open-loop stand reached through stand61 after the rise (robotd reaches every pose through velstand)
    "stand_route": [
        V("via61_2", range(8), ["--stand-after", "2"], until=20),
        V("via61_4", range(8), ["--stand-after", "4"], until=20),
        V("via61_4_comp", range(4), ["--stand-after", "4"], extra=["--compensation"], until=20),
    ],
    # control: the same stand61 -> open-loop stand switch with no sit before it
    "stand_switch": [
        V("nosit_stand_at8", range(8), ["--stand-at", "8"], until=16, sit=False),
        V("nosit_stand_at8_v74", range(4), ["--stand-at", "8"], volt=7.4, until=16, sit=False),
        V("nosit_stand_at8_old1019", range(4), ["--stand-at", "8"], man="old1019", until=16, sit=False),
    ],
    "handover": [
        V("timer2_now", range(8)),
        V("timer1_now", range(8), ["--unsit-s", "1.0"]),
        V("timer2_tostand", range(4), ["--to-stand"]),
    ],
}


def metrics(path):
    rows = [json.loads(l) for l in open(path)]
    rise = next((r["t"] for r in rows if r.get("sit_phase") == "rise"), None)
    if rise is None:
        return dict(rise_t0=None)
    hand = next((r["t"] for r in rows if r["t"] > rise and r["mode"] != "sit"), None)
    seg = [r for r in rows if rise <= r["t"] and (hand is None or r["t"] < hand)]
    tilt = lambda r: math.degrees(math.acos(max(-1.0, min(1.0, -r["gb"][2]))))
    seg = [r for r in seg if r.get("q")]
    knee = [(r["t"], max(abs(r["q"][LK]), abs(r["q"][RK])), r["gyro_body"][1]) for r in seg]
    up_t, up_tilt, run = None, None, 0
    for r, (t, k, gy) in zip(seg, knee):  # the proposed evidence: knees under SIT_KNEE_MIN, pitch rate under 1 rad/s, 0.3 s
        run = run + 1 if k < SIT_KNEE_MIN and abs(gy) < 1.0 else 0
        if run >= 15 and up_t is None:
            up_t, up_tilt = round(t - rise, 2), round(tilt(r), 1)
    rise_tilt = [tilt(r) for r in seg]
    rises = sum(1 for (_, k0, _), (_, k1, _) in zip(knee, knee[1:]) if k0 >= 1.0 > k1)  # knee passes 1.0 going up
    last = [k for t, k, _ in knee if t >= knee[-1][0] - 2.0] if knee else []
    at = next((r for r in rows if hand is not None and r["t"] >= hand), None)
    after = [r for r in rows if hand is not None and hand <= r["t"] <= hand + 4.0]
    return dict(rise_t0=rise, handover_t=hand, rise_s=None if hand is None else round(hand - rise, 2),
                tilt_max_rise=round(max(rise_tilt), 1) if rise_tilt else None,
                fell_in_rise=bool(rise_tilt) and max(rise_tilt) > 60.0, evidence_tilt=up_tilt,
                end_mode=rows[-1]["mode"], end_tilt=round(tilt(rows[-1]), 1),
                knee_min=round(min(k for _, k, _ in knee), 3) if knee else None, knee_up_crossings=rises,
                knee_last2s=[round(min(last), 3), round(max(last), 3)] if last else None,
                evidence_up_s=up_t,
                knee_at_handover=None if at is None else round(max(abs(at["q"][LK]), abs(at["q"][RK])), 3),
                knee_rate_at_handover=None if at is None else round((at["dq"][LK] - at["dq"][RK]) / 2, 2),
                tilt_at_handover=None if at is None else round(tilt(at), 1),
                tilt_max_4s_after=round(max(tilt(r) for r in after), 1) if after else None,
                trace=[(round(t - rise, 2), round(k, 3)) for t, k, _ in knee[::5]])


def one(v, seed):
    tag = f"{v['label']}_s{seed}"
    tick = os.path.join(TICKS, tag + ".jsonl")
    cmd = [PY, os.path.join(HERE, "rise_run.py")] + v["rr"] + ["--", "brain_sim_check.py", "--model", v["model"],
           "--volt", str(v["volt"]), "--drop", str(v["drop"]), "--walk-s", "0", "--seed", str(seed),
           "--tick-log", tick] + v["extra"]
    if v["sit"]:
        cmd += ["--sit-at", str(SIT_AT), "--unsit-at", str(UNSIT_AT)]
    if MAN[v["man"]]:
        cmd += ["--manifest", MAN[v["man"]]]
    if v["until"]:
        cmd += ["--until", str(v["until"])]
    if v["models"]:
        cmd += ["--models", v["models"]]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=MAC)
    js = [l for l in p.stdout.splitlines() if l.startswith("{")]
    if not js:
        return dict(label=v["label"], seed=seed, error=p.stderr[-600:])
    r = json.loads(js[-1])
    sit = r.get("sit") or {}
    return dict(label=v["label"], seed=seed, rr=v["rr"], man=v["man"], volt=v["volt"], drop=v["drop"], model=v["model"],
                models=v["models"], fell_at=r.get("fell_at"), max_tilt=r.get("max_tilt"),
                sit={k: sit.get(k) for k in ("start", "flag1", "rise", "done", "peak_tilt", "seated_tilt",
                                              "seated_trunk_z", "stable_after_s", "end_trunk_z")},
                stalled=any("STALLED" in l for l in p.stdout.splitlines()), **metrics(tick), cmd=" ".join(cmd[1:]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sets", nargs="+")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--reanalyze", action="store_true", help="recompute the metrics from the kept tick logs, no sims")
    a = ap.parse_args()
    os.makedirs(TICKS, exist_ok=True)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    for s in a.sets:
        if a.reanalyze:
            rows = [json.loads(l) for l in open(os.path.join(HERE, "results", s + ".jsonl"))]
            for r in rows:
                if "error" not in r:
                    r.update(metrics(os.path.join(TICKS, f"{r['label']}_s{r['seed']}.jsonl")))
        else:
            jobs = [(v, seed) for v in SETS[s] for seed in v["seeds"]]
            with cf.ProcessPoolExecutor(a.jobs) as ex:
                rows = list(ex.map(one, *zip(*jobs)))
        with open(os.path.join(HERE, "results", s + ".jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        for r in rows:
            g = r.get
            print(s, g("label"), g("seed"), "ERR " + g("error", "")[-120:] if "error" in r else
                  f"fell {g('fell_at')} rise_fall {g('fell_in_rise')} rise_tilt {g('tilt_max_rise')} rise {g('rise_s')} "
                  f"knee_min {g('knee_min')} up_xings {g('knee_up_crossings')} evid_up {g('evidence_up_s')}@{g('evidence_tilt')} "
                  f"hand knee {g('knee_at_handover')} tilt_after {g('tilt_max_4s_after')} end {g('end_mode')} {g('end_tilt')}",
                  flush=True)
