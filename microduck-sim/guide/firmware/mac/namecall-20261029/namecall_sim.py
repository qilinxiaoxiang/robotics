"""The whole name-call chain against the as-built duck sim under stand61: synthetic 4-channel calls from known
directions -> namecall.py's detector and localiser -> the take -> walk_brain.Brain's head path -> MuJoCo.

Same plant and head path as pet/express/duck_sim.py (its 360-call evidence): as-built model with the saddle manifest,
BAM servos, one tick of sensor and action delay, servo read drops, stand61 at zero command, head targets through
Brain.tick's own EMA. Per call: detected or missed, azimuth error, head latency from the sound's onset (detection plus
the take's own reaction latency), overshoot past the wanted command, trunk tilt, drift, fall. One MuJoCo run per seed
(all its calls in one standing episode).

  ~/.venvs/microduck-dyn/bin/python namecall_sim.py --seeds 0-7 --n 6 --jobs 4 --out results/sim_real.json
  ... --volt 6.6 --drop 0.08 --out results/sim_stress.json        (the stress bracket pet/express used)

One sim at a time on the MacBook (sim_host_guard); batches run on the Mac mini.
"""
import argparse
import json
import math
import os
import sys
import time

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(MAC, "..", "..", "..", ".."))
sys.path.insert(0, MAC)
sys.path.insert(0, ROOT)
import sim_host_guard  # noqa: E402
import namecall as nc  # noqa: E402
from pet.express import duck_sim  # noqa: E402
from pet.express.duck import HEAD_JOINTS, ema  # noqa: E402

FS, B = nc.FS, nc.BLOCK


def scene(calls, dur, seed, snr_db=20.0, floor_hum=True):
    """Room floor (white noise 20 dB under the call, plus a 50 Hz-ish fan hum and a faint 7 kHz servo whine when
    floor_hum) with voice-like calls (t, az_deg, kind)."""
    rng = np.random.default_rng(seed)
    n = int(dur * FS)
    ref = nc.synth_call(seed=seed)
    rms = float(np.sqrt(np.mean(ref ** 2)))
    x = rng.standard_normal((n, 4)).astype(np.float32) * rms * 10 ** (-snr_db / 20)
    x[:, 3] = 0
    if floor_hum:
        t = np.arange(n) / FS
        hum = 0.5 * rms * 10 ** (-snr_db / 20) * (np.sin(2 * math.pi * 52 * t) + 0.4 * np.sin(2 * math.pi * 7100 * t))
        x[:, :3] += hum[:, None].astype(np.float32)
    for i, (tc, az, kind) in enumerate(calls):
        sig = nc.synth_call(seed=seed * 100 + i, kind=kind, f0=float(rng.uniform(150, 280)))
        y, _ = nc.render_scene(sig, math.radians(az), pre_s=0.0, post_s=0.0, snr_db=200, seed=seed * 100 + i)
        k = int(tc * FS)
        x[k:k + len(y)] += y[: n - k]
    return x


def blocks(x):
    for i in range(0, len(x) - B + 1, B):
        yield i / FS, x[i:i + B]


def wrap_deg(d):
    return (d + 180) % 360 - 180


def run_seed(seed, n_calls, gap, volt, drop, snr_db, behind_frac, smooth):
    rng = np.random.default_rng(seed + 500)
    calls = []
    for i in range(n_calls):
        side = 1 if i % 2 == 0 else -1
        if rng.random() < behind_frac:
            az = side * float(rng.uniform(100, 170))
        else:
            az = side * float(rng.uniform(20, 70))
        calls.append((1.0 + i * gap, az, "clap" if rng.random() < 0.25 else "voice"))
    until = 1.0 + n_calls * gap
    x = scene(calls, until + 0.5, seed, snr_db)
    a = nc.parse_args(["--no-gate", "--no-sound", "--mute", "--dry", "--seed", str(seed), "--quiet"] + (["--smooth"] if smooth else []))
    log = nc.Log(None, echo=False)
    chain = nc.NameCall(a, log, now=lambda: 0.0)
    chain.head.default = dict(nc.DEFAULT_HEAD)   # the policy default head pose; the sim's Brain has the same values
    rows = []
    dets = chain.run_blocks(blocks(x), head_rows=rows)
    n_ticks = int(round(until / 0.02)) + 1
    r = np.zeros((n_ticks, 4))
    last = np.zeros(4)
    k_last = -1
    for t, head, _ in rows:
        k = int(round(t / 0.02))
        if 0 <= k < n_ticks:
            row = np.array([head[j] - nc.DEFAULT_HEAD[j] for j in HEAD_JOINTS])
            if k_last >= 0 and k > k_last + 1:
                r[k_last + 1:k] = last        # the file holds between writes
            r[k] = row
            last, k_last = row, k
    if k_last >= 0:
        r[k_last + 1:] = last
    tr = duck_sim.simulate(r, seed, volt, drop)
    n_settle = int(round(duck_sim.SETTLE_S / 0.02))
    y_full = np.vstack([np.zeros((n_settle, 4)), ema(r)])
    out_calls = []
    for i, (tc, az, kind) in enumerate(calls):
        det = next((d for d in dets if abs(d["t"] - tc) < 0.3), None)
        m = duck_sim.call_metrics(tr, tc, gap * 0.65, y_full)
        rec = dict(call=i + 1, t=tc, kind=kind, az_true_deg=round(az, 1), detected=det is not None, **m)
        if det is not None:
            rec.update(az_est_deg=det["az_deg"], az_err_deg=round(abs(wrap_deg(det["az_deg"] - az)), 1),
                       decided_after_s=round(det["decided_t"] - det["t"], 3), take=det.get("take"), behind=det.get("behind"),
                       target_yaw=det.get("target_yaw"), quack_events=len([e for e in det.get("events", []) if e.get("kind") == "call"]),
                       front_back_margin=det.get("margin"))
        out_calls.append(rec)
    false_alarms = len([d for d in dets if not any(abs(d["t"] - tc) < 0.3 for tc, _, _ in calls)])
    return dict(seed=seed, volt=volt, drop=drop, snr_db=snr_db, calls=out_calls, false_alarms=false_alarms,
                fell_any=bool((tr["gz"] > duck_sim.FALL_GZ).any()),
                tilt_max_deg=round(float(np.hypot(tr["roll"] - tr["roll"][:50].mean(), tr["pitch"] - tr["pitch"][:50].mean()).max()), 2),
                writes=chain.writer.writes if chain.writer else None)


def _job(kw):
    return run_seed(**kw)


def summarise(runs):
    calls = [c for r in runs for c in r["calls"]]
    det = [c for c in calls if c["detected"]]
    lat = [c["head_latency_s"] for c in det if c["head_latency_s"] is not None]
    q = lambda v, p: None if not v else round(float(np.percentile(v, p)), 3)
    return dict(seeds=len(runs), calls=len(calls), detected=len(det), missed=len(calls) - len(det),
                false_alarms=sum(r["false_alarms"] for r in runs), falls=sum(1 for c in calls if c["fell"]),
                falls_any_run=sum(1 for r in runs if r["fell_any"]),
                az_err_deg=dict(mean=None if not det else round(float(np.mean([c["az_err_deg"] for c in det])), 2),
                                p90=q([c["az_err_deg"] for c in det], 90), max=None if not det else max(c["az_err_deg"] for c in det),
                                mirror_errors=sum(1 for c in det if c["az_err_deg"] > 90)),
                head_latency_s=dict(median=q(lat, 50), p10=q(lat, 10), p90=q(lat, 90), max=None if not lat else max(lat)),
                decided_after_s=dict(median=q([c["decided_after_s"] for c in det], 50), max=None if not det else max(c["decided_after_s"] for c in det)),
                overshoot_rad=dict(median=q([c["head_extra_overshoot_rad"] for c in det], 50), p90=q([c["head_extra_overshoot_rad"] for c in det], 90),
                                   max=None if not det else max(c["head_extra_overshoot_rad"] for c in det)),
                tilt_max_deg=dict(median=q([c["tilt_max_deg"] for c in calls], 50), p95=q([c["tilt_max_deg"] for c in calls], 95),
                                  max=None if not calls else max(c["tilt_max_deg"] for c in calls)),
                drift_mm_max=None if not calls else max(c["drift_mm"] for c in calls),
                takes={t: sum(1 for c in det if c.get("take") == t) for t in sorted({c.get("take") for c in det if c.get("take")})},
                behind=sum(1 for c in det if c.get("behind")), quacks=sum(c.get("quack_events", 0) for c in det))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0-3", help="a-b inclusive")
    ap.add_argument("--n", type=int, default=6, help="calls per seed")
    ap.add_argument("--gap", type=float, default=4.0)
    ap.add_argument("--volt", type=float, default=None)
    ap.add_argument("--drop", type=float, default=None)
    ap.add_argument("--snr-db", type=float, default=20.0)
    ap.add_argument("--behind", type=float, default=0.25, help="fraction of calls from behind (past the yaw cap)")
    ap.add_argument("--smooth", action="store_true")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "sim.json"))
    a = ap.parse_args()
    v, dr = duck_sim.state_defaults()
    volt = v if a.volt is None else a.volt
    drop = dr if a.drop is None else a.drop
    lo, hi = (int(s) for s in a.seeds.split("-")) if "-" in a.seeds else (int(a.seeds), int(a.seeds))
    jobs = [dict(seed=s, n_calls=a.n, gap=a.gap, volt=volt, drop=drop, snr_db=a.snr_db, behind_frac=a.behind, smooth=a.smooth)
            for s in range(lo, hi + 1)]
    t0 = time.time()
    if a.jobs > 1 and not sim_host_guard.on_laptop():
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(a.jobs) as pool:
            runs = pool.map(_job, jobs)
    else:
        sim_host_guard.one_sim_on_laptop("namecall_sim")
        runs = [run_seed(**j) for j in jobs]
    for r in runs:
        print(f"seed {r['seed']}: {sum(c['detected'] for c in r['calls'])}/{len(r['calls'])} detected, "
              f"tilt max {r['tilt_max_deg']} deg, fell {r['fell_any']}, false alarms {r['false_alarms']}", flush=True)
    res = dict(volt=volt, drop=drop, snr_db=a.snr_db, gap_s=a.gap, n_per_seed=a.n, behind_frac=a.behind, smooth=a.smooth,
               started=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)), wall_s=round(time.time() - t0, 1),
               host=os.uname().nodename, summary=summarise(runs), runs=runs)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res["summary"], indent=1))


if __name__ == "__main__":
    main()
