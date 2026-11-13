"""T7 of fault stand-leans-left-on-left-outer-edge: why walk61 at zero command holds the hips wider on the robot.

Reads a robot brain-log slice and a brain_sim_check.py --tick-log, both at zero command after a walk, and
  1. tabulates per leg joint: default pose, action, intended goal (default + action, action scale 1), goal sent
     (goal_tick) and position, in degrees;
  2. replays walk61.onnx on the logged rows (observation built as walk_brain.Brain.tick builds it) and reports the
     reproduction error;
  3. swaps one observation group at a time from the robot's window mean to the sim's and reports the hip roll actions,
     open loop (last action as logged) and closed loop (last action iterated to its fixed point).

Actions are in OBSERVATION_DOF_ORDER (left leg, head, right leg); q, dq, goal_tick in servo ID order.

  python t7_replay.py ROBOT.jsonl SIM.jsonl [--robot-window HH:MM:SS HH:MM:SS] [--sim-window S0 S1] [--out FILE.json]
"""
import argparse
import datetime
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import walk_brain as wb  # noqa: E402  (read only: constants, conversions, compensation)

ODO = wb.OBSERVATION_DOF_ORDER
NAMES = wb.NAMES
LEGS = [n for n in NAMES if n.startswith(("right_", "left_"))]
DEG = 180 / np.pi


def load(path):
    rows = []
    with open(path) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def session():
    sess = wb.ort.InferenceSession(os.path.join(wb.WHOLE, "runtime-overlay", "models", "walk61.onnx"), wb.session_options())
    meta = sess.get_modelmeta().custom_metadata_map
    default = dict(zip(ODO, [float(v) for v in meta["default_joint_pos"].split(",")]))
    return sess, default


def run(sess, obs):
    return sess.run(None, {sess.get_inputs()[0].name: np.asarray(obs, dtype=np.float32)[None]})[0][0]


def state_of(row, default, comp, exact_gravity):
    """The 34 numbers gyro3 + gravity3 + q14 + dq14 as Brain.tick hands them to the policy."""
    q = dict(zip(NAMES, row["q"]))
    dq = dict(zip(NAMES, row["dq"]))
    if "pos_tick" in row and exact_gravity:
        q = {n: wb.to_model(n, t) for n, t in zip(NAMES, row["pos_tick"])}
    gb = row["gb"]
    if exact_gravity and row.get("quat"):
        gb = wb.body_gravity(tuple(row["quat"]))
    state = np.array(list(row["gyro_body"]) + list(gb) + [q[n] - default[n] for n in ODO] + [dq[n] for n in ODO])
    if comp and row.get("age_used"):
        cfg = {"delay_compensation": "constant_velocity", "prediction_fraction": 1.0, "predict_heading": True}
        js, _ = wb.compensate(state, 0.0, row["age_used"][0], cfg)
        im, _ = wb.compensate(state, 0.0, row["age_used"][1], cfg)
        state = np.concatenate([im[:6], js[6:]])
    return state


def obs_rows(rows, default, comp, exact_gravity):
    """(obs, logged action) for every row where walk61 ran and the previous policy row is the tick before."""
    out, last = [], None
    for r in rows:
        if r.get("action") is None:
            continue
        act = np.array(r.get("action_raw") or r["action"], dtype=float)
        if last is not None and r.get("policy", "walk") == "walk":
            cmd = r.get("cmd") or {}
            command = [float(cmd.get("vx", 0)), float(cmd.get("vy", 0)), float(r.get("turn", 0.0))]
            head = r.get("head_cmd") or [0.0] * 4
            obs = np.concatenate([state_of(r, default, comp, exact_gravity), last, command, head, np.zeros(6)])
            out.append((obs, act, r))
        last = np.array(r["action"], dtype=float)
    return out


def table(rows, default, label):
    pol = [r for r in rows if r.get("action") is not None]
    act = np.mean([r["action"] for r in pol], axis=0)
    q = np.mean([r["q"] for r in rows], axis=0)
    goal = {n: np.mean([wb.to_model(n, r["goal_tick"][str(i)]) for r in rows if r.get("goal_tick")]) for i, n in zip(wb.IDS, NAMES)}
    gb = np.mean([r["gb"] for r in rows], axis=0)
    cur = np.mean([r["cur_ma"] for r in rows], axis=0) if "cur_ma" in rows[0] else None
    res = {"rows": len(rows), "policy_rows": len(pol), "kp": sorted({json.dumps(r.get("kp")) for r in rows}),
           "roll_deg": round(float(np.degrees(np.arctan2(gb[1], -gb[2]))), 2),
           "pitch_deg": round(float(np.degrees(np.arctan2(-gb[0], -gb[2]))), 2), "gb": gb.round(4).tolist(), "joints": {}}
    print(f"\n{label}: {len(rows)} rows, {len(pol)} policy rows, kp {res['kp']}, roll {res['roll_deg']:+.2f} deg (gb_y {gb[1]:+.4f}), "
          f"pitch {res['pitch_deg']:+.2f} deg")
    print(f"  {'joint':16s} {'default':>8s} {'action':>8s} {'intended':>9s} {'goal sent':>9s} {'position':>9s} {'goal-pos':>9s} {'mA':>6s}")
    for k, n in enumerate(NAMES):
        if n not in LEGS:
            continue
        a = act[ODO.index(n)]
        d = default[n]
        j = dict(default=d * DEG, action=a * DEG, action_rad=float(a), intended=(d + a) * DEG, goal=goal[n] * DEG, pos=q[k] * DEG,
                 err=(goal[n] - q[k]) * DEG, cur_ma=None if cur is None else float(cur[k]))
        res["joints"][n] = {kk: (None if v is None else round(float(v), 3)) for kk, v in j.items()}
        print(f"  {n:16s} {j['default']:8.2f} {j['action']:8.2f} {j['intended']:9.2f} {j['goal']:9.2f} {j['pos']:9.2f} {j['err']:9.2f} "
              f"{'' if cur is None else format(cur[k], '6.0f')}")
    return res


GROUPS = {"gyro": slice(0, 3), "gravity": slice(3, 6), "joint_pos": slice(6, 20), "joint_vel": slice(20, 34),
          "last_action": slice(34, 48), "command": slice(48, 51), "head_cmd": slice(51, 55), "body": slice(55, 61)}


def idx(group, names):
    base = GROUPS[group].start
    return [base + ODO.index(n) for n in names]


def fixed_point(sess, obs, n=400):
    o = np.array(obs, dtype=float)
    for _ in range(n):
        a = run(sess, o)
        o[GROUPS["last_action"]] = a
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("robot")
    ap.add_argument("sim")
    ap.add_argument("--robot-window", nargs=2, default=["20:04:10", "20:05:40"])
    ap.add_argument("--date", default="2026-11-12")
    ap.add_argument("--sim-window", nargs=2, type=float, default=[17.6, 37.6])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    sess, default = session()
    t0, t1 = (datetime.datetime.strptime(f"{args.date} {s}", "%Y-%m-%d %H:%M:%S").timestamp() for s in args.robot_window)
    rob = [r for r in load(args.robot) if t0 <= r["t"] <= t1 and r.get("mode") == "walk"]
    sim = [r for r in load(args.sim) if args.sim_window[0] <= r["t"] <= args.sim_window[1] and r.get("mode") == "walk"]
    out = {"robot_file": args.robot, "sim_file": args.sim, "robot_window": args.robot_window, "sim_window": args.sim_window}
    print("default pose (deg):", {n: round(default[n] * DEG, 2) for n in LEGS})
    print("robot cmd in window:", sorted({json.dumps(r.get("cmd")) for r in rob})[:5], "policies", sorted({str(r.get("policy")) for r in rob}),
          "hold s", sorted({r.get("hold_s") for r in rob})[:5])
    out["robot"] = table(rob, default, "ROBOT")
    out["sim"] = table(sim, default, "SIM")

    # 2. reproduction
    out["reproduce"] = {}
    for label, rows in (("robot", rob), ("sim", sim)):
        for comp in (False, True):
            for exact in (False, True):
                pairs = obs_rows(rows, default, comp, exact)
                if not pairs:
                    continue
                err = np.array([run(sess, o) - a for o, a, _ in pairs])
                key = f"{label} compensation={comp} exact_gravity_and_ticks={exact}"
                hr = [ODO.index("right_hip_roll"), ODO.index("left_hip_roll")]
                out["reproduce"][key] = dict(n=len(pairs), max_abs=float(np.abs(err).max()), rms=float(np.sqrt((err ** 2).mean())),
                                             hip_roll_max_abs=float(np.abs(err[:, hr]).max()))
                print(f"reproduce {key}: n {len(pairs)}, max |err| {np.abs(err).max():.4f} rad, rms {np.sqrt((err ** 2).mean()):.4f}, "
                      f"hip roll max {np.abs(err[:, hr]).max():.4f}")

    # 3. swaps on window means (as the brain ran: no compensation unless the reproduction says otherwise)
    best = min((k for k in out["reproduce"] if k.startswith("robot")), key=lambda k: out["reproduce"][k]["rms"])
    comp, exact = "compensation=True" in best, "ticks=True" in best
    print("swaps use the robot observation as in:", best)
    R = np.mean([o for o, _, _ in obs_rows(rob, default, comp, exact)], axis=0)
    S = np.mean([o for o, _, _ in obs_rows(sim, default, False, False)], axis=0)
    ir, il = ODO.index("right_hip_roll"), ODO.index("left_hip_roll")

    def show(tag, o):
        a, f = run(sess, o), fixed_point(sess, o)
        print(f"  {tag:46s} open loop R {a[ir]:+.4f} L {a[il]:+.4f} | fixed point R {f[ir]:+.4f} L {f[il]:+.4f}  "
              f"(goal R {(default['right_hip_roll'] + f[ir]) * DEG:+.2f} L {(default['left_hip_roll'] + f[il]) * DEG:+.2f} deg)")
        return dict(open_R=float(a[ir]), open_L=float(a[il]), fixed_R=float(f[ir]), fixed_L=float(f[il]))

    print("\nhip roll actions (rad), R = right_hip_roll, L = left_hip_roll; mean logged action robot "
          f"R {out['robot']['joints']['right_hip_roll']['action_rad']:+.4f} L {out['robot']['joints']['left_hip_roll']['action_rad']:+.4f}, "
          f"sim R {out['sim']['joints']['right_hip_roll']['action_rad']:+.4f} L {out['sim']['joints']['left_hip_roll']['action_rad']:+.4f}")
    sw = out["swaps"] = {}
    sw["robot mean obs"] = show("robot mean obs", R)
    sw["sim mean obs"] = show("sim mean obs", S)
    print("  robot obs with ONE group from the sim:")
    for g in GROUPS:
        o = R.copy()
        o[GROUPS[g]] = S[GROUPS[g]]
        sw[f"robot<-sim {g}"] = show(f"robot <- sim {g}", o)
    print("  sim obs with ONE group from the robot:")
    for g in GROUPS:
        o = S.copy()
        o[GROUPS[g]] = R[GROUPS[g]]
        sw[f"sim<-robot {g}"] = show(f"sim <- robot {g}", o)
    print("  finer: robot obs with part of a group from the sim")
    parts = {"gravity x (pitch)": [3], "gravity y (roll)": [4],
             "pos hip rolls": idx("joint_pos", ["right_hip_roll", "left_hip_roll"]),
             "pos right leg": idx("joint_pos", [n for n in LEGS if n.startswith("right")]),
             "pos left leg": idx("joint_pos", [n for n in LEGS if n.startswith("left")]),
             "pos hip pitch+knee+ankle": idx("joint_pos", [n for n in LEGS if "roll" not in n and "yaw" not in n]),
             "pos hip yaws": idx("joint_pos", ["right_hip_yaw", "left_hip_yaw"]),
             "pos head 4": idx("joint_pos", [n for n in NAMES if n not in LEGS])}
    for tag, ii in parts.items():
        o = R.copy()
        o[ii] = S[ii]
        sw[f"robot<-sim {tag}"] = show(f"robot <- sim {tag}", o)
    print("  finer: sim obs with part of a group from the robot")
    for tag, ii in parts.items():
        o = S.copy()
        o[ii] = R[ii]
        sw[f"sim<-robot {tag}"] = show(f"sim <- robot {tag}", o)
    print("\nobservation means, robot / sim (rad, rad/s):")
    lab = ["gyro_x", "gyro_y", "gyro_z", "grav_x", "grav_y", "grav_z"] + ["pos " + n for n in ODO] + ["vel " + n for n in ODO] + \
          ["act " + n for n in ODO] + ["vx", "vy", "turn"] + ["head" + str(i) for i in range(4)] + ["body" + str(i) for i in range(6)]
    for k, n in enumerate(lab):
        if abs(R[k] - S[k]) > 0.01:
            print(f"  {n:22s} {R[k]:+.4f} / {S[k]:+.4f}   diff {R[k] - S[k]:+.4f}")
    out["obs_mean_robot"], out["obs_mean_sim"], out["obs_labels"] = R.round(5).tolist(), S.round(5).tolist(), lab
    if args.out:
        with open(args.out, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
