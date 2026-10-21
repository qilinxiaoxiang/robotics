"""Characterise the stand61 in-place oscillation in robot log 1018d (2026-10-18), after the second walk.
Row format: robot-runs-20261018/README.md line 5 (q/dq/action in walk_brain.OBSERVATION_DOF_ORDER, gb gravity in body,
gyro_body, kp). Read-only analysis; writes osc_1018d.json next to this script."""
import gzip, json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac/robot-runs-20261018/duck_wired_log_1018d.jsonl.gz"
sys.path.insert(0, "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/pi/microduck_rt")
sys.path.insert(0, "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/pi")
# walk_brain.py: info["action"] is in constants.OBSERVATION_DOF_ORDER (line 523-531); q is logged in servo-ID order
# walk_brain.NAMES = [ID_TO_NAME[i] for i in IDS] (line 101-103), verified against NEUTRAL_POSE values in the log
from constants import OBSERVATION_DOF_ORDER, MOTOR_TO_ID  # noqa
NAMES = list(OBSERVATION_DOF_ORDER)          # action order
QNAMES = [{v: k for k, v in MOTOR_TO_ID.items()}[i] for i in range(1, 15)]   # q order
rows = [json.loads(l) for l in gzip.open(LOG, "rt")]
t0 = rows[0]["t"]
walk_t0 = float(open(os.path.join(os.path.dirname(LOG), "walk_t0_1018f")).read().strip()) - t0  # 2nd walk command
def pitch(g): return math.degrees(math.atan2(g[0], -g[2]))
def roll(g): return math.degrees(math.atan2(g[1], -g[2]))
out = {"action_names": NAMES, "q_names": QNAMES, "walk_t0_rel_s": round(walk_t0, 2)}
# window: walk mode after the 2nd walk until the mode leaves walk
W = [r for r in rows if r["mode"] == "walk" and r["t"] - t0 >= walk_t0]
tw = np.array([r["t"] - t0 - walk_t0 for r in W])
out["window_s"] = [round(float(tw[0]), 2), round(float(tw[-1]), 2)]
P = np.array([pitch(r["gb"]) for r in W]); R = np.array([roll(r["gb"]) for r in W])
G = np.array([r["gyro_body"] for r in W])  # rad/s, body frame
A = np.array([[a if a is not None else np.nan for a in (r["action"] or [None] * 14)] for r in W])
Q = np.array([[a if a is not None else np.nan for a in r["q"]] for r in W])
kp = sorted(set(r["kp"] for r in W)); out["kp_in_window"] = kp
import collections
out["policy_field_counts"] = dict(collections.Counter(str(r.get("policy")) for r in W))
pol = [(round(float(t), 2), r.get("policy")) for t, r in zip(tw, W)]
out["policy_changes"] = [pol[0]] + [pol[i] for i in range(1, len(pol)) if pol[i][1] != pol[i - 1][1]]
# 2 s bins: pitch/roll std, gyro rms, per-joint action std, max |action| joint
bins = []
for b0 in np.arange(0, tw[-1], 2.0):
    sel = (tw >= b0) & (tw < b0 + 2.0)
    if sel.sum() < 20: continue
    a = A[sel]; sd = np.nanstd(a, axis=0); i = int(np.nanargmax(sd))
    bins.append(dict(t=round(float(b0), 1), pitch_mean=round(float(P[sel].mean()), 2), pitch_sd=round(float(P[sel].std()), 2),
                     roll_sd=round(float(R[sel].std()), 2), gyro_rms=[round(float(np.sqrt((G[sel][:, k] ** 2).mean())), 3) for k in range(3)],
                     max_abs_action=round(float(np.nanmax(np.abs(a))), 3), top_joint=NAMES[i], top_joint_sd=round(float(sd[i]), 3),
                     action_sd_by_joint={n: round(float(s), 3) for n, s in zip(NAMES, sd)}))
out["bins_2s"] = bins
# spectrum of pitch, roll and head_yaw/leg actions over the last 8 s before the window ends (oscillation phase)
def spectrum(x, fs=50.0):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; x = x - x.mean()
    n = len(x); f = np.fft.rfftfreq(n, 1 / fs); Y = np.abs(np.fft.rfft(x * np.hanning(n))) ** 2
    Y[f < 0.3] = 0  # drop DC/drift
    top = np.argsort(Y)[::-1][:3]
    return [(round(float(f[i]), 2), round(float(Y[i] / Y.max()), 2)) for i in top]
last = tw >= tw[-1] - 8.0
out["spectrum_last8s"] = dict(pitch=spectrum(P[last]), roll=spectrum(R[last]),
                              gyro_x=spectrum(G[last][:, 0]), gyro_y=spectrum(G[last][:, 1]), gyro_z=spectrum(G[last][:, 2]))
for n in ("head_yaw", "head_roll", "head_pitch", "neck_pitch", "left_hip_pitch", "right_hip_pitch", "left_ankle", "right_ankle",
          "left_hip_roll", "right_hip_roll", "left_hip_yaw", "right_hip_yaw", "left_knee", "right_knee"):
    out["spectrum_last8s"]["action_" + n] = spectrum(A[last][:, NAMES.index(n)])
# growth: envelope of pitch and of the head_yaw action over 1 s bins in the last 12 s, log-linear fit
def growth(x, t, span=12.0):
    sel = t >= t[-1] - span
    tt = t[sel]; xx = x[sel]
    env, tc = [], []
    for b0 in np.arange(tt[0], tt[-1], 1.0):
        s = (tt >= b0) & (tt < b0 + 1.0)
        if s.sum() > 10:
            v = xx[s]; v = v[~np.isnan(v)]
            if len(v): env.append(float(v.max() - v.min())); tc.append(float(b0 + 0.5))
    env = np.array(env); tc = np.array(tc)
    ok = env > 1e-6
    k, c = np.polyfit(tc[ok], np.log(env[ok]), 1)
    return dict(pp_per_s=[(round(float(a), 1), round(float(b), 3)) for a, b in zip(tc, env)], exp_rate_per_s=round(float(k), 3),
                doubling_s=round(float(math.log(2) / k), 2) if k > 0 else None)
out["growth"] = dict(pitch_deg=growth(P, tw), roll_deg=growth(R, tw), gyro_y=growth(G[:, 1], tw), gyro_x=growth(G[:, 0], tw),
                     head_yaw_action=growth(A[:, NAMES.index("head_yaw")], tw),
                     hip_pitch_action=growth(A[:, NAMES.index("left_hip_pitch")], tw))
# action-magnitude guard: ticks with |action| > 1.0 (MAX_ACTION) per second in the last 15 s
big = np.nanmax(np.abs(A), axis=1) > 1.0
out["ticks_over_1rad_per_s_last15"] = [(round(float(b0), 0), int(big[(tw >= b0) & (tw < b0 + 1)].sum())) for b0 in np.arange(tw[-1] - 15, tw[-1], 1.0)]
# the open-loop stand that follows: pitch per second until the fall
S = [r for r in rows if r["mode"] == "stand" and r["t"] - t0 > tw[-1] + walk_t0]
ts0 = S[0]["t"]
tr = []
last_k = -1
for r in S:
    k = int(r["t"] - ts0)
    if k != last_k:
        last_k = k; q = r["q"]
        tr.append((k, round(pitch(r["gb"]), 2), round(roll(r["gb"]), 2), r["kp"],
                   None if q[0] is None else {n: round(q[QNAMES.index(n)], 3) for n in ("left_ankle", "right_ankle", "left_knee", "right_knee", "left_hip_pitch", "right_hip_pitch")}))
out["open_loop_after"] = tr[:60]
# where was the pitch while stand61 held still (first 20 s) vs the model: mean q over the still period
still = tw <= 20.0
still = (tw >= 6.0) & (tw <= 24.0)
out["still_6_24s"] = dict(pitch_mean=round(float(P[still].mean()), 2), pitch_sd=round(float(P[still].std()), 2),
                          roll_mean=round(float(R[still].mean()), 2), max_abs_action=round(float(np.nanmax(np.abs(A[still]))), 3),
                          q_mean={n: round(float(np.nanmean(Q[still][:, i])), 4) for i, n in enumerate(QNAMES)},
                          action_mean={n: round(float(np.nanmean(A[still][:, i])), 4) for i, n in enumerate(NAMES)})
json.dump(out, open(os.path.join(HERE, "osc_1018d.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("bins_2s", "open_loop_after")}, indent=1))
print("bins:")
for b in bins: print(b["t"], "pitch", b["pitch_mean"], "sd", b["pitch_sd"], "roll sd", b["roll_sd"], "gyro", b["gyro_rms"], "max|a|", b["max_abs_action"], "top", b["top_joint"], b["top_joint_sd"])
print("open loop after:")
for x in out["open_loop_after"]: print(x)
