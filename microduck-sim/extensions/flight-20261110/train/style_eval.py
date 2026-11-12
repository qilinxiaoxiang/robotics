"""Gait style, bend and head-motion measurements in the same probe as flight_eval.py (brain_sim_check.py, --volt 7.6
--drop 0.036), recorded from a per-physics-step hook. Run on the Mac mini (train/mini.sh run), never the MacBook.

  $PY train/style_eval.py --models <dir> --manifest <m> --case walk --episodes 20 --out <f.json> [--extra="..."]

Per episode, on top of flight_eval.episode's falls/speed/torque:
  stance foot yaw  heading of each foot (its geom axis that points along the trunk at the start pose) minus the trunk
                   heading, on every physics step the foot touches the floor; toe-out positive on both feet (left
                   +yaw, right -yaw), as the change from the trained start pose (the first physics step) and absolute.
                   Also against the walk's mean heading (what a viewer sees as the walking direction).
  hip joints       mean hip_yaw and hip_roll joint angles (deg) over the window, both legs, and the toe-out these
                   explain: d(foot yaw rel trunk)/d(hip yaw) is fitted per foot in stance (sign and gain).
  trunk yaw osc.   trunk heading minus its 1 s running mean in the window: p95 |.| (deg)
  step width       at each touchdown, distance between the two foot geoms across the trunk heading (mm)
  foot roll        at each touchdown, the sole's roll about the heading, outer edge up positive (deg, change from start)
  trunk pitch      nose-down positive (deg): median in 0.5-1.5 s, min and max after 1 s, largest excursion from that
                   start value
Window: walk cases from WALK_AT + 2 s to the end of the walk command; all other cases from 1 s to the end.
"""
import argparse
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flight_eval as fe  # noqa: E402

FEET = ("left_foot_collision", "right_foot_collision")


def _wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def episode(job):
    case = job[2]
    rec = dict(i=None, rows=[])

    def hook(m, d, t):
        if rec["i"] is None:
            g = [m.geom(n).id for n in FEET]
            tr = m.body("trunk_base").id
            Rt = d.xmat[tr].reshape(3, 3)
            ax, up = [], []
            for gi in g:
                R = d.geom_xmat[gi].reshape(3, 3)
                k = int(np.argmax(np.abs(R.T @ Rt[:, 0])))
                ax.append((k, float(np.sign(R[:, k] @ Rt[:, 0]))))
                j = int(np.argmax(np.abs(R[2, :])))
                up.append((j, float(np.sign(R[2, j]))))
            jq = {n: m.jnt_qposadr[m.joint(n).id] for n in ("left_hip_yaw", "right_hip_yaw", "left_hip_roll", "right_hip_roll",
                                                             "neck_pitch", "head_pitch", "head_yaw")}
            rec["i"] = dict(g=g, tr=tr, ax=ax, up=up, jq=jq, world=set(np.where(m.geom_bodyid == 0)[0].tolist()))
        i = rec["i"]
        Rt = d.xmat[i["tr"]].reshape(3, 3)
        h = math.atan2(Rt[1, 0], Rt[0, 0])
        lat = np.array([-math.sin(h), math.cos(h), 0.0])
        nc = d.ncon
        g1, g2 = d.contact.geom1[:nc], d.contact.geom2[:nc]
        row = [t, h, -math.degrees(math.asin(max(-1.0, min(1.0, Rt[2, 0]))))]
        for f, gi in enumerate(i["g"]):
            R = d.geom_xmat[gi].reshape(3, 3)
            k, s = i["ax"][f]
            fwd = R[:, k] * s
            j, su = i["up"][f]
            u = R[:, j] * su
            touch = bool(np.any(((g1 == gi) & np.isin(g2, list(i["world"]))) | ((g2 == gi) & np.isin(g1, list(i["world"])))))
            row += [math.atan2(fwd[1], fwd[0]), -math.asin(max(-1.0, min(1.0, float(u @ lat)))), float(touch),
                    float(d.geom_xpos[gi] @ lat)]
        row += [float(d.qpos[i["jq"][n]]) for n in ("left_hip_yaw", "right_hip_yaw", "left_hip_roll", "right_hip_roll",
                                                     "neck_pitch", "head_pitch", "head_yaw")]
        rec["rows"].append(row)

    fe.FRAME_HOOK = hook
    r = fe.episode(job)
    fe.FRAME_HOOK = None
    A = np.array(rec["rows"])
    t, h, pitch = A[:, 0], A[:, 1], A[:, 2]
    # columns per foot: heading, roll, touch, lateral position
    fh = [A[:, 3], A[:, 7]]
    roll = [A[:, 4], A[:, 8]]
    touch = [A[:, 5] > 0.5, A[:, 9] > 0.5]
    lp = [A[:, 6], A[:, 10]]
    hy = [A[:, 11], A[:, 12]]
    hr = [A[:, 13], A[:, 14]]
    sgn = (1.0, -1.0)  # toe-out positive: left +yaw, right -yaw; roll outer edge up: left +, right -
    walking = case in ("walk", "turnL", "turnR")
    t0 = fe.WALK_AT + 2.0 if walking else 1.0
    t1 = fe.WALK_AT + fe.WALK_S if walking else t[-1]
    if r["fell_at"] is not None:
        t1 = min(t1, r["fell_at"] - 0.2)
    w = (t >= t0) & (t <= t1)
    out = dict(window_s=[round(t0, 2), round(float(t1), 2)])
    hw = (t >= 1.0) & (t <= (r["fell_at"] if r["fell_at"] is not None else t[-1]))
    if hw.any():  # head and neck joint angles reached (rad): did the policy follow the head commands
        out["head_reached"] = {n: dict(min=round(float(A[hw, c].min()), 3), max=round(float(A[hw, c].max()), 3),
                                       mean=round(float(A[hw, c].mean()), 3))
                               for n, c in (("neck_pitch", 15), ("head_pitch", 16), ("head_yaw", 17))}
    if w.sum() > 50:
        dt = float(np.median(np.diff(t)))
        n1 = max(1, int(round(1.0 / dt)))
        hu = np.unwrap(h)
        run = np.convolve(hu, np.ones(n1) / n1, mode="same")
        out["trunk_yaw_osc_p95_deg"] = round(float(np.degrees(np.percentile(np.abs(hu - run)[w], 95))), 2)
        hmean = float(np.mean(hu[w]))
        feet = {}
        for f, name in enumerate(("left", "right")):
            rel = _wrap(fh[f] - h)
            rel0 = rel[0]
            st = w & touch[f]
            if st.sum() < 10:
                continue
            toe = sgn[f] * np.degrees(rel[st] - rel0)
            toe_abs = sgn[f] * np.degrees(rel[st])
            toe_path = sgn[f] * np.degrees(_wrap(fh[f][st] - hmean) - rel0)
            x = hy[f][st]
            slope = float(np.polyfit(x, rel[st], 1)[0]) if np.ptp(x) > 1e-3 else None
            td = np.where(np.diff(touch[f].astype(int)) == 1)[0] + 1
            td = td[(t[td] >= t0) & (t[td] <= t1)]
            feet[name] = dict(
                stance_toe_out_deg_mean=round(float(np.mean(toe)), 2), stance_toe_out_deg_p95=round(float(np.percentile(toe, 95)), 2),
                stance_toe_out_abs_deg_mean=round(float(np.mean(toe_abs)), 2),
                stance_toe_out_vs_path_deg_mean=round(float(np.mean(toe_path)), 2),
                hip_yaw_deg_mean=round(float(np.degrees(np.mean(hy[f][w]))), 2),
                hip_yaw_deg_start=round(float(np.degrees(hy[f][0])), 2),
                hip_roll_deg_mean=round(float(np.degrees(np.mean(hr[f][w]))), 2),
                hip_roll_deg_start=round(float(np.degrees(hr[f][0])), 2),
                foot_yaw_per_hip_yaw=None if slope is None else round(slope, 3),
                touchdowns=int(len(td)),
                roll_at_touchdown_deg_mean=None if not len(td) else round(float(np.mean(sgn[f] * np.degrees(roll[f][td] - roll[f][0]))), 2),
                stance_frac=round(float(st.sum() / w.sum()), 3))
        out["feet"] = feet
        tds = sorted(np.concatenate([np.where(np.diff(touch[f].astype(int)) == 1)[0] + 1 for f in (0, 1)]).tolist())
        tds = [k for k in tds if t0 <= t[k] <= t1]
        width0 = abs(lp[0][0] - lp[1][0])
        out["step_width_mm_mean"] = round(float(np.mean([abs(lp[0][k] - lp[1][k]) for k in tds])) * 1000, 1) if tds else None
        out["stance_width_start_mm"] = round(width0 * 1000, 1)
        if not walking:
            out["stand_width_mm_mean"] = round(float(np.mean(np.abs(lp[0][w] - lp[1][w]))) * 1000, 1)
    p0 = float(np.median(pitch[(t >= 0.5) & (t <= 1.5)])) if np.any((t >= 0.5) & (t <= 1.5)) else float(pitch[0])
    after = t >= 1.0
    if r["fell_at"] is not None:
        after &= t <= r["fell_at"]
    out["trunk_pitch_deg"] = dict(start=round(p0, 2), min=round(float(pitch[after].min()), 2), max=round(float(pitch[after].max()), 2),
                                  excursion=round(float(np.max(np.abs(pitch[after] - p0))), 2)) if after.any() else None
    r["style"] = out
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--case", choices=sorted(fe.CASES), required=True)
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--extra", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed0", type=int, default=0, help="first seed; seeds are seed0..seed0+episodes-1")
    a = ap.parse_args()
    jobs = [(os.path.abspath(a.models), os.path.abspath(a.manifest), a.case, s, 0.0, 8.0, False, a.extra.split())
            for s in range(a.seed0, a.seed0 + a.episodes)]
    with ProcessPoolExecutor(a.workers) as ex:
        eps = list(ex.map(episode, jobs))
    falls = [e for e in eps if e["fell_at"] is not None]
    sp = [e["speed"] for e in eps if e["fell_at"] is None and e["speed"] is not None]

    def agg(get):
        v = [x for x in (get(e) for e in eps) if x is not None]
        return round(float(np.median(v)), 2) if v else None
    summ = dict(name=a.name, models=a.models, manifest=Path(a.manifest).name, case=a.case, extra=a.extra, episodes=len(eps),
                falls=len(falls), fall_times=sorted(e["fell_at"] for e in falls),
                speed_median_upright=round(float(np.median(sp)), 4) if sp else None,
                leg_force_p99_nm_median=agg(lambda e: e["leg_force_p99_nm"]),
                leg_force_sat_frac_max=max((e["leg_force_sat_frac"] or 0) for e in eps), limit_nm=fe.LIMIT_NM,
                max_tilt=max(e["max_tilt"] for e in eps),
                trunk_pitch_excursion_deg_median=agg(lambda e: (e["style"]["trunk_pitch_deg"] or {}).get("excursion")),
                trunk_pitch_excursion_deg_max=max(((e["style"]["trunk_pitch_deg"] or {}).get("excursion") or 0) for e in eps),
                trunk_yaw_osc_p95_deg=agg(lambda e: e["style"].get("trunk_yaw_osc_p95_deg")),
                step_width_mm=agg(lambda e: e["style"].get("step_width_mm_mean")),
                stance_width_start_mm=agg(lambda e: e["style"].get("stance_width_start_mm")),
                stand_width_mm=agg(lambda e: e["style"].get("stand_width_mm_mean")))
    for n in ("neck_pitch", "head_pitch", "head_yaw"):
        for k in ("min", "max", "mean"):
            summ[f"{n}_{k}"] = agg(lambda e, n=n, k=k: ((e["style"].get("head_reached") or {}).get(n) or {}).get(k))
    for f in ("left", "right"):
        for k in ("stance_toe_out_deg_mean", "stance_toe_out_deg_p95", "stance_toe_out_abs_deg_mean", "stance_toe_out_vs_path_deg_mean",
                  "hip_yaw_deg_mean", "hip_yaw_deg_start", "hip_roll_deg_mean", "hip_roll_deg_start", "foot_yaw_per_hip_yaw",
                  "roll_at_touchdown_deg_mean"):
            summ[f"{f}_{k}"] = agg(lambda e, f=f, k=k: (e["style"].get("feet", {}).get(f) or {}).get(k))
    # leg torque p99 per joint (median over episodes), worst joint
    pj = {}
    for j in eps[0]["per_joint_all"]:
        pj[j] = round(float(np.median([e["per_joint_all"][j]["p99_nm"] for e in eps])), 3)
    summ["joint_p99_nm"] = pj
    qr = [all(e["probe"]["quack_head_ran"].values()) for e in eps if (e.get("probe") or {}).get("quack_head_ran")]
    if qr:  # walk_wired's quack gate, as the probe applies it: episodes in which every quack moved the head
        summ["quack_ran_episodes"] = sum(qr)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(dict(summary=summ, episodes=eps), indent=1))
    print(json.dumps({k: v for k, v in summ.items() if k != "joint_p99_nm"}))


if __name__ == "__main__":
    main()
