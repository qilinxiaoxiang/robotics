"""Round 2 cause study (2026-11-18): analysis of the shadow logs and the observation-parity records made by
ts2_cause.py (eval/cz_<dir>_shadow.json, eval/cz_<dir>_shadow_nodrop.json) and ts2_parity_env.py (eval/cz_parity_env.json).

  python3 train/ts2_cause_analyse.py

Writes out/ts2_cause_shadow.json (check 1) and out/ts2_cause_parity.json (check 3, numbers only; the reading with
line references is in RUNLOG.md).
"""
import json
from pathlib import Path

import numpy as np

TRAIN = Path(__file__).resolve().parent
JOINTS = ["left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle", "neck_pitch", "head_pitch", "head_yaw",
          "head_roll", "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle"]
LEGS = [0, 1, 2, 3, 4, 9, 10, 11, 12, 13]
DIRS = ["s2g_200", "s2d_300"]
T_WALK = 2.0      # the walk command starts at 2.0 s
# runtime observation slots (walk_brain.py: gyro 3, gravity 3, joint position 14, joint velocity 14, last action 14,
# command 3, head 4, body 6)
SL = dict(gyro=(0, 3), grav=(3, 6), q=(6, 20), dq=(20, 34), last=(34, 48), cmd=(48, 51))


def categories(rows):
    """per row: 1 / 2 / 3 = first / second / third called tick after a skipped tick, 0 = no skipped tick within the
    last 10 control ticks, -1 = anything else (4 to 10 ticks after a skip)"""
    out, last_skip_k, since = [], -10 ** 9, 99
    for r in rows:
        if r["skip"] > 0:
            last_skip_k, since = r["k"] - 1, 1
        else:
            since += 1
        out.append(since if since <= 3 else (0 if r["k"] - last_skip_k > 10 else -1))
    return out


def stats(diffs):
    """diffs [n, 14] -> per joint median and p90, plus the mean over the leg joints"""
    if len(diffs) == 0:
        return dict(n=0)
    d = np.asarray(diffs)
    return dict(n=int(len(d)), leg_mean_of_medians=round(float(np.median(d, axis=0)[LEGS].mean()), 4),
                leg_mean_of_p90=round(float(np.percentile(d, 90, axis=0)[LEGS].mean()), 4),
                all_joint_mean=round(float(d.mean()), 4),
                median={j: round(float(v), 4) for j, v in zip(JOINTS, np.median(d, axis=0))},
                p90={j: round(float(v), 4) for j, v in zip(JOINTS, np.percentile(d, 90, axis=0))})


def windows(d, cell):
    """per time window (standing start 0-2 s, walk start 2-4 s, walking 4 s on): the student-teacher difference, the
    trunk pitch and forward speed, and the falls; a falling episode's last 0.5 s is left out"""
    p = TRAIN / f"eval/cz_{d}_{cell}.json"
    if not p.exists():
        return None
    j = json.loads(p.read_text())
    out = dict(file=f"eval/cz_{d}_{cell}.json", driver="teacher" if cell == "tshadow" else "student", falls_of_20=j["summary"]["falls"])
    for name, lo, hi in (("standing_start_0_2s", 0.0, 2.0), ("walk_start_2_4s", 2.0, 4.0), ("walking_4s_on", 4.0, 1e9)):
        dd, pit, vx = [], [], []
        for e in j["episodes"]:
            f = e["fell_at"]
            for r in e["shadow"] or []:
                if lo <= r["time"] < hi and (f is None or r["time"] <= f - 0.5):
                    dd.append(np.array(r["s"]) - np.array(r["t"]))
                    pit.append(r["pitch"])
                    vx.append(r["vx"])
        a = np.abs(np.array(dd))
        sg = np.array(dd).mean(axis=0)
        out[name] = dict(n=len(dd), falls=sum(1 for e in j["episodes"] if e["fell_at"] is not None and lo <= e["fell_at"] < hi),
                         leg_abs_diff_median=round(float(np.median(a, axis=0)[LEGS].mean()), 4),
                         leg_abs_diff_p90=round(float(np.percentile(a, 90, axis=0)[LEGS].mean()), 4),
                         trunk_pitch_mean=round(float(np.mean(pit)), 4), trunk_pitch_std=round(float(np.std(pit)), 4),
                         forward_speed_mean=round(float(np.mean(vx)), 4),
                         signed_mean_diff={JOINTS[i]: round(float(sg[i]), 3) for i in LEGS})
    return out


def shadow(d):
    j = json.loads((TRAIN / f"eval/cz_{d}_shadow.json").read_text())
    nd = json.loads((TRAIN / f"eval/cz_{d}_shadow_nodrop.json").read_text())
    names = {1: "first_after_skip", 2: "second_after_skip", 3: "third_after_skip", 0: "no_skip_in_last_10"}
    groups = {g: {n: [] for n in names.values()} for g in ("falling", "surviving")}
    falls, counters = [], {}
    for e in j["episodes"]:
        rows = e["shadow"] or []
        for k, v in (e.get("diag_stat") or {}).items():
            counters[k] = counters.get(k, 0) + v
        cat = categories(rows)
        fell = e["fell_at"]
        g = "falling" if fell is not None else "surviving"
        for r, c in zip(rows, cat):
            # walking only; a falling episode's last 0.5 s is left out (the fall itself, not the cause)
            if r["time"] < T_WALK or c not in names or (fell is not None and r["time"] > fell - 0.5):
                continue
            groups[g][names[c]].append(np.abs(np.array(r["s"]) - np.array(r["t"])))
        if fell is not None:
            skips = [r["time"] - 0.02 * i for r in rows if r["skip"] > 0 for i in range(1, r["skip"] + 1) if r["time"] - 0.02 * i <= fell]
            tilt = [(r["time"], float(np.hypot(r["pitch"], r["roll"]))) for r in rows]
            # onset: the last time before the fall the trunk tilt was still under 0.25 rad
            onset = max([t for t, x in tilt if x < 0.25 and t <= fell], default=None)
            last05 = [np.abs(np.array(r["s"]) - np.array(r["t"])) for r in rows if fell - 0.5 <= r["time"] <= fell]
            m = np.mean(last05, axis=0) if last05 else None
            pre = [np.abs(np.array(r["s"]) - np.array(r["t"])) for r in rows if onset is not None and onset - 0.5 <= r["time"] <= onset]
            mp = np.mean(pre, axis=0) if pre else None
            falls.append(dict(seed=e["seed"], fell_at=fell, fall_dir=e.get("fall_dir"), phase="standing start (before the walk command)"
                              if fell < T_WALK else "walking",
                              last_skipped_tick_at=round(max(skips), 2) if skips else None,
                              s_from_last_skip_to_fall=round(fell - max(skips), 2) if skips else None,
                              skips_in_last_1s=sum(1 for s in skips if s > fell - 1.0),
                              tilt_onset_at=onset,
                              s_from_last_skip_before_onset=(round(onset - max([s for s in skips if s <= onset], default=float("nan")), 2)
                                                             if onset is not None and any(s <= onset for s in skips) else None),
                              skips_in_1s_before_onset=sum(1 for s in skips if onset is not None and onset - 1.0 < s <= onset),
                              largest_diff_joint_last_0p5s=JOINTS[int(np.argmax(m))] if m is not None else None,
                              largest_diff_rad_last_0p5s=round(float(np.max(m)), 3) if m is not None else None,
                              largest_diff_joint_0p5s_before_onset=JOINTS[int(np.argmax(mp))] if mp is not None else None,
                              largest_diff_rad_0p5s_before_onset=round(float(np.max(mp)), 3) if mp is not None else None,
                              pitch_at_onset=next((r["pitch"] for r in rows if onset is not None and r["time"] >= onset), None)))
    base = {g: [] for g in ("falling", "surviving")}
    for e in nd["episodes"]:
        g = "falling" if e["fell_at"] is not None else "surviving"
        for r in e["shadow"] or []:
            if r["time"] >= T_WALK and (e["fell_at"] is None or r["time"] <= e["fell_at"] - 0.5):
                base[g].append(np.abs(np.array(r["s"]) - np.array(r["t"])))
    return dict(files=[f"eval/cz_{d}_shadow.json", f"eval/cz_{d}_shadow_nodrop.json"],
                falls_of_20=j["summary"]["falls"], falls_of_20_drops_off=nd["summary"]["falls"],
                counters_sum_over_episodes=counters,
                a_abs_student_minus_teacher_rad={g: {n: stats(v) for n, v in groups[g].items()} for g in groups},
                b_falls=falls,
                c_drops_off_baseline={g: stats(v) for g, v in base.items()},
                by_time_window={c: windows(d, c) for c in ("shadow", "shadow_nodrop", "tshadow")})


def parity_runtime(d):
    """numeric confirmation on the episodes with logged observations (seeds 0 to 2, first 8 s)"""
    j = json.loads((TRAIN / f"eval/cz_{d}_shadow.json").read_text())
    res = dict(file=f"eval/cz_{d}_shadow.json", last_action_slot={}, joint_reading_age={}, gravity_reading_age={}, command_slot={})
    la = {"after_skip": [], "no_skip": []}
    la_alt = []
    qres = {"after_skip": {k: [] for k in range(4)}, "no_skip": {k: [] for k in range(4)}}
    gres = {"after_skip": {k: [] for k in range(4)}, "no_skip": {k: [] for k in range(4)}}
    cmd = {"after_skip": [], "no_skip": []}
    printed = None
    for e in j["episodes"]:
        if not e.get("shadow_phys"):
            continue
        rows = [r for r in e["shadow"] if "obs" in r]
        phys = {round(t, 4): (s, g) for t, s, g in e["shadow_phys"]}
        # the joint-sum offset (default pose and zero offsets) from the ticks without a skip, readings one tick old
        off = [sum(r["obs"][6:20]) - phys[round(r["time"] - 0.02, 4)][0] for r in rows
               if r["skip"] == 0 and round(r["time"] - 0.02, 4) in phys]
        c = float(np.median(off))
        # the same for gravity: the constant difference between the observed vector (IMU frame after the mount and
        # trim rotations) and the trunk's own, from the ticks without a skip at one tick of age
        cg = np.median([np.array(r["obs"][3:6]) - np.array(phys[round(r["time"] - 0.02, 4)][1]) for r in rows
                        if r["skip"] == 0 and round(r["time"] - 0.02, 4) in phys], axis=0)
        for a, r in zip(rows, rows[1:]):
            if r["k"] - a["k"] != r["skip"] + 1 or r["time"] < T_WALK + 0.2:
                continue
            key = "after_skip" if r["skip"] else "no_skip"
            la[key].append(float(np.max(np.abs(np.array(r["obs"][34:48]) - np.array(a["s"])))))
            cmd[key].append(float(np.max(np.abs(np.array(r["obs"][48:51]) - np.array(a["obs"][48:51])))))
            for lag in range(4):
                t = round(r["time"] - 0.02 * lag, 4)
                if t in phys:
                    qres[key][lag].append(abs(sum(r["obs"][6:20]) - phys[t][0] - c))
                    gres[key][lag].append(float(np.linalg.norm(np.array(r["obs"][3:6]) - np.array(phys[t][1]) - cg)))
            if r["skip"] == 1 and printed is None and r["time"] > 3.0:
                printed = dict(seed=e["seed"], tick_before_skip=a["k"], skipped_tick=r["k"] - 1, first_tick_after=r["k"],
                               obs_before=a["obs"], student_action_before=a["s"], obs_after=r["obs"],
                               student_action_after=r["s"], teacher_action_after=r["t"],
                               slots="gyro 0-2, gravity 3-5, joint position 6-19, joint velocity 20-33, last action 34-47, command 48-50, head 51-54, body 55-60")
    res["last_action_slot"] = {k: dict(n=len(v), max_abs_diff_to_student_last_output=round(max(v), 5) if v else None) for k, v in la.items()}
    res["command_slot"] = {k: dict(n=len(v), median_change_from_previous_called_tick=round(float(np.median(v)), 5) if v else None,
                                   max_change=round(max(v), 5) if v else None) for k, v in cmd.items()}
    res["joint_reading_age"] = {k: {f"residual_at_{lag}_ticks_old": round(float(np.median(v[lag])), 5) for lag in range(4) if v[lag]}
                                for k, v in qres.items()}
    res["gravity_reading_age"] = {k: {f"residual_at_{lag}_ticks_old": round(float(np.median(v[lag])), 5) for lag in range(4) if v[lag]}
                                  for k, v in gres.items()}
    res["example"] = printed
    return res


def parity_env():
    p = TRAIN / "eval/cz_parity_env.json"
    if not p.exists():
        return None
    j = json.loads(p.read_text())
    off, sl = 0, {}
    for n, dm in zip(j["terms"], j["dims"]):
        sl[n] = (off, off + dm)
        off += dm
    rows = j["rows"]
    la, lah = [], []
    grav = "projected_gravity" if "projected_gravity" in sl else "raw_accelerometer"
    qres = {"after_hold": {k: [] for k in range(4)}, "other": {k: [] for k in range(4)}}
    gres = {"after_hold": {k: [] for k in range(4)}, "other": {k: [] for k in range(4)}}
    act_term = next(n for n in sl if "action" in n)
    for i in range(4, len(rows)):
        a, r = rows[i - 1], rows[i]
        if any(x.get("done_after") for x in rows[max(0, i - 4):i]):
            continue
        d = float(np.max(np.abs(np.array(r["obs"][slice(*sl[act_term])]) - np.array(a["applied"]))))
        key = "after_hold" if a["held"] else "other"
        (lah if a["held"] else la).append(d)
        for lag in range(4):
            qres[key][lag].append(float(np.median(np.abs(np.array(r["obs"][slice(*sl["joint_pos"])]) - np.array(rows[i - lag]["q_true"])))))
            gres[key][lag].append(float(np.linalg.norm(np.array(r["obs"][slice(*sl[grav])]) - np.array(rows[i - lag]["g_true"]))))
    h = j["hold_ticks"][0]
    return dict(file="eval/cz_parity_env.json", delta=j["delta"], loop_delay=j["loop_delay"], terms=j["terms"], dims=j["dims"],
                term_info=j["term_info"], hold_ticks=j["hold_ticks"],
                last_action_slot=dict(max_abs_diff_to_applied_action_after_a_held_tick=round(max(lah), 5) if lah else None,
                                      max_abs_diff_to_applied_action_other_ticks=round(max(la), 5) if la else None, n_held=len(lah), n_other=len(la)),
                joint_reading_age={k: {f"median_abs_residual_at_{lag}_ticks_old": round(float(np.median(v[lag])), 5) for lag in range(4) if v[lag]}
                                   for k, v in qres.items()},
                gravity_reading_age={k: {f"residual_at_{lag}_ticks_old": round(float(np.median(v[lag])), 5) for lag in range(4) if v[lag]}
                                     for k, v in gres.items()},
                example=dict(tick_before_hold=rows[h - 1]["t"], held_tick=rows[h]["t"], first_tick_after=rows[h + 1]["t"],
                             obs_at_held_tick=rows[h]["obs"], applied_at_held_tick=rows[h]["applied"],
                             applied_before=rows[h - 1]["applied"], obs_after=rows[h + 1]["obs"]))


# check 3, the reading of the code (line numbers as of 2026-11-18; microduck_rl/cmu/mac and cmu/finetune/flight)
READING = [
    dict(point="last-action slot on the first tick after a skipped tick",
         runtime="the policy's own last output, unchanged by the skip: walk_brain.py:978 sets last_action only when the policy "
                 "runs, a skipped tick falls through to :1013 (keep the last goal); the slot is read at :968",
         training="the action applied on the dropped tick, which is the held previous action: distill_worker.py:223 (act_s = "
                  "prev_act), :226 venv.step(applied), env term 'actions' with no delay or noise",
         mismatch="none (runtime 0.0 on the after-skip ticks, env 0.0 on the held ticks). Outside the skip question: half of the "
                  "training envs carry --act-noise 0.10 on the applied action, so their slot holds the noisy action"),
    dict(point="joint position and velocity readings",
         runtime="fresh, one tick old: the sensor queue takes a sample every tick whether or not the read is dropped "
                 "(brain_sim_check.py:1229), the Brain gets sq[0] (:1237, queue length sensor_delay + 1 = 2, :1119)",
         training="joint_pos lag 1 tick, joint_vel lag 2 ticks on every tick (flight_worker.py:138 LOOP_DELAY); the env steps on "
                  "a dropped tick like on any other, so the reading after it is as fresh as usual",
         mismatch="none at a skip. Constant difference on every tick: velocity is 2 ticks old in training, 1 tick in the runtime "
                  "simulation (the teacher was trained the same way and does not fall)"),
    dict(point="IMU fields (gyro, gravity)",
         runtime="same sample as the joints, one tick old (brain_sim_check.py:1237; imu_age :1355)",
         training="base_ang_vel and projected_gravity lag 1 tick (flight_worker.py:138)",
         mismatch="none at a skip"),
    dict(point="sensor and action delay queues across a skipped tick",
         runtime="sensor queue advances every tick (:1229). Action queue: the Brain returns its held goal (walk_brain.py:1013), "
                 "which is appended again (brain_sim_check.py:1423) and reaches the servos one tick later (:1424): the goal is "
                 "repeated once, nothing is lost or reordered",
         training="the held action goes through env.step and the actuator's command lag (4 to 9 physics steps) like any action",
         mismatch="none at a skip"),
    dict(point="command slot",
         runtime="the turn command is the heading hold's output (walk_brain.py:934-941) and moves every tick; the skipped tick "
                 "does not run it (:849 gate, turn_t at :920), so the step to the next called tick is larger",
         training="the twist command is constant between resamplings",
         mismatch="the only difference found at a skip: the turn command steps by a median 0.040 rad/s after a skip against 0.022 "
                  "on other ticks (max 0.104 against 0.063). It is also present with drops off, where the students do not fall"),
]


def main():
    sh ={d: shadow(d) for d in DIRS if (TRAIN / f"eval/cz_{d}_shadow.json").exists() and (TRAIN / f"eval/cz_{d}_shadow_nodrop.json").exists()}
    (TRAIN / "out/ts2_cause_shadow.json").write_text(json.dumps(sh, indent=1))
    for d, s in sh.items():
        print(f"== {d}: falls {s['falls_of_20']}/20 with drops, {s['falls_of_20_drops_off']}/20 drops off; counters {s['counters_sum_over_episodes']}")
        for g, v in s["a_abs_student_minus_teacher_rad"].items():
            for n, x in v.items():
                if x["n"]:
                    print(f"   {g:9s} {n:20s} n {x['n']:6d}  leg median {x['leg_mean_of_medians']}  leg p90 {x['leg_mean_of_p90']}")
        for g, x in s["c_drops_off_baseline"].items():
            if x["n"]:
                print(f"   drops off {g:9s} n {x['n']:6d}  leg median {x['leg_mean_of_medians']}  leg p90 {x['leg_mean_of_p90']}")
        for c, w in s["by_time_window"].items():
            if w:
                for n in ("standing_start_0_2s", "walk_start_2_4s", "walking_4s_on"):
                    x = w[n]
                    print(f"   {c:14s} ({w['driver']} drives) {n:20s} falls {x['falls']}  leg |diff| median {x['leg_abs_diff_median']} "
                          f"p90 {x['leg_abs_diff_p90']}  pitch {x['trunk_pitch_mean']} +- {x['trunk_pitch_std']}  vx {x['forward_speed_mean']}")
        for f in s["b_falls"]:
            print("   fall", {k: f[k] for k in ("seed", "fell_at", "fall_dir", "s_from_last_skip_to_fall", "tilt_onset_at",
                                                 "s_from_last_skip_before_onset", "skips_in_1s_before_onset",
                                                 "largest_diff_joint_last_0p5s", "largest_diff_rad_last_0p5s",
                                                 "largest_diff_joint_0p5s_before_onset", "largest_diff_rad_0p5s_before_onset")})
    par = dict(reading=READING, runtime={d: parity_runtime(d) for d in DIRS[:1] if (TRAIN / f"eval/cz_{d}_shadow.json").exists()}, training_env=parity_env())
    (TRAIN / "out/ts2_cause_parity.json").write_text(json.dumps(par, indent=1))
    for d, r in par["runtime"].items():
        print(f"== parity runtime {d}:", json.dumps({k: r[k] for k in ("last_action_slot", "command_slot", "joint_reading_age", "gravity_reading_age")}))
    if par["training_env"]:
        e = par["training_env"]
        print("== parity training env:", json.dumps({k: e[k] for k in ("terms", "dims", "last_action_slot", "joint_reading_age", "gravity_reading_age")}))


if __name__ == "__main__":
    main()
