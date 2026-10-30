"""Mechanism check: is the sim's version of a shaking robot walk the same oscillation, damped, or a different motion?

For every row of targets-20261030.json and one sweep setting, prints side by side (robot | sim, mean over seeds) for
the leg joints: action rms, q rms and their ratio over the walking window (walk-policy ticks), the dominant action
frequency of hip pitch, knee and hip roll, the left-right correlation of hip-pitch and knee actions (positive: both legs
pitch together, a trunk-pitch bounce; negative: a stride), and the trunk gyro rms. Writes the comparison to
results-20261030/mechanism-<setting>.json.

  ~/.venvs/microduck-dyn/bin/python mechanism_20261030.py SETTING [--logdir DIR]
"""
import argparse
import json
import os

import numpy as np

import jitter_metrics as jm
import sweep_20261030 as sw

DOF = jm.DOF
RUNS = os.path.join(sw.HERE, "..", "robot-runs-20261030-t1")
ROBOT_LOGS = {r[0]: r[4] for r in [
    ("walk61_default", "walk61", None, 3.0, "walk61_see_walks.jsonl"),
    ("t1_default", "models-t1-best", None, 3.0, "2_walk_fell.jsonl"),
    ("t1_neck-0.4", "models-t1-best", -0.4, 3.0, "4_walk_neck.jsonl"),
    ("t2b_default", "models-t2b-best", None, 3.0, "t2b/1_walk.jsonl"),
    ("t2b_neck-0.4", "models-t2b-best", -0.4, 3.0, "t2b/2_walk_neck.jsonl"),
    ("t2b_neck-0.8", "models-t2b-best", -0.8, 2.0, "t2b/3_neck_hold.jsonl")]}
SHORT = {n: n.replace("left_", "L_").replace("right_", "R_") for n in DOF}


def domf(x):
    f = np.fft.rfftfreq(len(x), 0.02)
    P = np.abs(np.fft.rfft((x - x.mean()) * np.hanning(len(x)))) ** 2
    P[f < 0.5] = 0
    return float(f[int(np.argmax(P))])


def describe(seg):
    pol = [r for r in seg if r.get("policy") == "walk" and r.get("action")]
    if len(pol) < 20:
        return None
    A = np.array([r["action"] for r in pol])
    Q = np.array([r["q"] for r in pol])
    G = np.array([r["gyro_body"] for r in pol])
    out = dict(ticks=len(pol), joints={}, gyro_rms=[round(float(x), 3) for x in G.std(axis=0)])
    for j in jm.LEG:
        a, q = float(A[:, j].std()), float(Q[:, j].std())
        out["joints"][DOF[j]] = dict(a_rms=round(a, 3), q_rms=round(q, 3), q_over_a=round(q / max(a, 1e-3), 2), f_a=round(domf(A[:, j]), 2))
    c = lambda i, k: round(float(np.corrcoef(A[:, i], A[:, k])[0, 1]), 2)
    out["lr_corr_a"] = dict(hip_pitch=c(2, 11), knee=c(3, 12), hip_roll=c(1, 10))
    out["lr_corr_q"] = dict(hip_pitch=round(float(np.corrcoef(Q[:, 2], Q[:, 11])[0, 1]), 2), knee=round(float(np.corrcoef(Q[:, 3], Q[:, 12])[0, 1]), 2))
    return out


def mean_desc(ds):
    ds = [d for d in ds if d]
    if not ds:
        return None
    out = dict(n=len(ds), joints={}, gyro_rms=[round(float(np.mean([d["gyro_rms"][i] for d in ds])), 3) for i in range(3)])
    for n in ds[0]["joints"]:
        out["joints"][n] = {k: round(float(np.mean([d["joints"][n][k] for d in ds])), 3) for k in ds[0]["joints"][n]}
    for key in ("lr_corr_a", "lr_corr_q"):
        out[key] = {k: round(float(np.mean([d[key][k] for d in ds])), 2) for k in ds[0][key]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("setting")
    ap.add_argument("--logdir", default=os.environ.get("JITTER_LOGDIR", os.path.join(sw.RESULTS, "ticklogs")))
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    a = ap.parse_args()
    report = dict(setting=a.setting, rows={})
    for rname, models, neck, walk_s in sw.ROWS:
        robot = mean_desc([describe(seg) for seg in jm.robot_segments(jm.load(os.path.join(RUNS, ROBOT_LOGS[rname])))
                           if seg[-1]["t"] - seg[0]["t"] >= 1.5])
        sims = []
        for s in a.seeds:
            p = os.path.join(a.logdir, a.setting, f"{rname}_s{s}.jsonl")
            if os.path.exists(p):
                sims.append(describe(jm.sim_segment(jm.load(p), sw.WALK_AT, walk_s)))
        sim = mean_desc(sims)
        report["rows"][rname] = dict(robot=robot, sim=sim)
        print(f"\n{rname}  (robot | sim {a.setting}, {len(sims)} seeds)")
        if not sim:
            print("  no sim logs")
            continue
        for n in ("left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle"):
            r, s = robot["joints"][n], sim["joints"][n]
            print(f"  {SHORT[n]:12s} a {r['a_rms']:.2f}|{s['a_rms']:.2f}  q {r['q_rms']:.3f}|{s['q_rms']:.3f}  q/a {r['q_over_a']:.2f}|{s['q_over_a']:.2f}  f_a {r['f_a']:.2f}|{s['f_a']:.2f} Hz")
        print(f"  L-R corr of actions hip_pitch {robot['lr_corr_a']['hip_pitch']:+.2f}|{sim['lr_corr_a']['hip_pitch']:+.2f}  knee {robot['lr_corr_a']['knee']:+.2f}|{sim['lr_corr_a']['knee']:+.2f}  hip_roll {robot['lr_corr_a']['hip_roll']:+.2f}|{sim['lr_corr_a']['hip_roll']:+.2f}")
        print(f"  trunk gyro rms xyz {robot['gyro_rms']}|{sim['gyro_rms']}")
    json.dump(report, open(os.path.join(sw.RESULTS, f"mechanism-{a.setting}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
