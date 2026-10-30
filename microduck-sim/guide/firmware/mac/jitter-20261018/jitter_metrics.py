"""One metric set for robot walk slices and jitter_sim tick logs (same row shape), 2026-10-30 targets.

Definitions copied from robot-runs-20261030-t1/compare_walks.py so sim and robot are scored the same way:
a segment is consecutive walk-mode rows with a commanded vx above 0.05 (robot rows carry "cmd"; sim rows are
windowed by time, walk_at .. walk_at + cmd_s, since brain_sim_check rows carry no cmd); tilt is the angle between
body gravity and straight down over every row of the segment; a jump is a tick-to-tick change of any action above
0.5 rad between consecutive walk-policy ticks; jump_rate_per_s divides by the segment duration. Robot files that hold
several walks (walk61_see_walks.jsonl) are split at time gaps above 0.5 s.

Extras from compare.py / band.py over the same window: leg q_rms / action_rms (how much of the commanded oscillation the
joints realise), trunk gyro rms per axis, and the 2-8 Hz band rms of every joint's action and q, so the shaking can be
located joint by joint.

  python3 jitter_metrics.py LOG [--sim WALK_AT CMD_S]
"""
import json
import math
import sys

import numpy as np

DOF = ["left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle", "neck_pitch", "head_pitch",
       "head_yaw", "head_roll", "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle"]
LEG = [0, 1, 2, 3, 4, 9, 10, 11, 12, 13]
DT = 0.02


def load(path):
    rows = []
    for line in open(path):
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def tilt(gb):
    g = math.sqrt(sum(x * x for x in gb)) or 1.0
    return math.degrees(math.acos(max(-1.0, min(1.0, -gb[2] / g))))


def robot_segments(rows, gap_s=0.5):
    seg, last_t = [], None
    for r in rows:
        cmd = r.get("cmd") or {}
        vx = float(cmd.get("vx") or 0)
        walking = r.get("mode") == "walk" and vx > 0.05 and r.get("gb")
        if walking and (last_t is None or r["t"] - last_t <= gap_s):
            seg.append(r)
        else:
            if seg:
                yield seg
            seg = [r] if walking else []
        last_t = r["t"]
    if seg:
        yield seg


def sim_segment(rows, walk_at, cmd_s):
    return [r for r in rows if walk_at <= r["t"] < walk_at + cmd_s and r.get("mode") == "walk" and r.get("gb")]


def band(x, lo=2.0, hi=8.0):
    x = np.nan_to_num(x - np.nanmean(x))
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), DT)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def stats(seg, min_dur=1.5):
    t0 = seg[0]["t"]
    dur = seg[-1]["t"] - t0
    if dur < min_dur:
        return None
    walk_rows = [r for r in seg if r.get("policy") == "walk" and r.get("action")]
    tilts = [tilt(r["gb"]) for r in seg]
    acts = [max(abs(a) for a in r["action"]) for r in walk_rows]
    jumps, prev = [], None
    for r in walk_rows:
        if prev is not None:
            jumps.append(max(abs(x - y) for x, y in zip(r["action"], prev)))
        prev = r["action"]
    srt = sorted(acts) or [0]
    out = dict(dur=round(dur, 2), n_rows=len(seg), n_policy=len(walk_rows), tilt_max=round(max(tilts), 1),
               tilt_mean=round(sum(tilts) / len(tilts), 2), act_p95=round(srt[int(0.95 * (len(srt) - 1))], 2),
               act_max=round(max(srt), 2), jumps_over_0p5=sum(1 for j in jumps if j > 0.5),
               jump_rate_per_s=round(sum(1 for j in jumps if j > 0.5) / dur, 2), fell=max(tilts) > 45)
    # compare.py extras on the 20 ms grid (hold the last row across dropped ticks)
    ts = np.array([r["t"] for r in seg])
    tg = np.arange(t0, t0 + dur, DT)
    ix = np.clip(np.searchsorted(ts, tg, side="right") - 1, 0, len(seg) - 1)
    q = np.array([seg[i]["q"] for i in ix], dtype=float)
    act = np.array([seg[i]["action"] if seg[i].get("action") else [np.nan] * 14 for i in ix], dtype=float)
    gy = np.array([seg[i].get("gyro_body") or [np.nan] * 3 for i in ix], dtype=float)
    if len(tg) >= 32 and not np.all(np.isnan(act)):
        a_rms = np.nanstd(act[:, LEG], axis=0)
        out["leg_q_over_a"] = round(float(np.nanmedian(np.nanstd(q[:, LEG], axis=0) / np.maximum(a_rms, 1e-4))), 2)
        out["gyro_rms"] = [round(float(np.nanstd(gy[:, i])), 3) for i in range(3)]
        A = np.array([band(act[:, j]) for j in range(14)])
        Q = np.array([band(q[:, j]) for j in range(14)])
        out["band_a_rms"] = {DOF[j]: round(float(A[j].std()), 3) for j in range(14)}
        out["band_q_rms"] = {DOF[j]: round(float(Q[j].std()), 3) for j in range(14)}
        P = np.sum(np.abs(np.fft.rfft(A * np.hanning(A.shape[1]), axis=1)) ** 2, axis=0)
        f = np.fft.rfftfreq(A.shape[1], DT)
        out["band_f_dom_hz"] = round(float(f[int(np.argmax(P))]), 2)
    return out


def main():
    args = sys.argv[1:]
    sim = None
    if "--sim" in args:
        i = args.index("--sim")
        sim = (float(args[i + 1]), float(args[i + 2]))
        args = args[:i] + args[i + 3:]
    for p in args:
        rows = load(p)
        segs = [sim_segment(rows, *sim)] if sim else list(robot_segments(rows))
        for seg in segs:
            s = stats(seg) if seg else None
            if s:
                s["log"] = p.rsplit("/", 1)[-1]
                s["start"] = round(seg[0]["t"], 2)
                print(json.dumps(s))


if __name__ == "__main__":
    main()
