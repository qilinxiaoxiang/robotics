"""Round 2 cold-start study (2026-11-18), training side. Does the distillation env (delta universal4) reproduce the
student's forward creep at zero command after a reset, and what does a distillation episode start look like?
CPU, no training, no learning: policies are only run.

  --phase dist    the env as distilled (512 envs, the teacher drives 400 ticks): share of ticks with an exactly zero
                  twist command, share of resets that start at zero command, the state right after a reset, the
                  loaded trunk COM x the payload event draws, and the config values behind them
  --phase start   payload pinned to the full pack, whole-robot COM x fixed (--comx m, payload.py
                  com_x_fixed_whole_m), every env standing (zero twist, zero head and body commands), no pushes:
                  from a reset with an empty student state, 100 ticks (2 s), driven by the student, by the student
                  with dropped ticks (0.036), and by the teacher. Forward speed, falls, |student - teacher|.

Run from the microduck_rl folder of the mirror:
  .venv/bin/python <train>/ts2_start_env.py --phase start --comx 0.010 --student-pt <model_200.pt> \
      --teacher-onnx <teacher.onnx> --manifest <flightpack-none.json> --audit <audit.json> --out <json>
"""
import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path.cwd() / "cmu/finetune/flight"))

ap = argparse.ArgumentParser()
ap.add_argument("--phase", choices=("dist", "start"), required=True)
ap.add_argument("--comx", type=float, default=0.0)
ap.add_argument("--student-pt", default="")
ap.add_argument("--teacher-onnx", required=True)
ap.add_argument("--manifest", required=True)
ap.add_argument("--audit", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--num-envs", type=int, default=256)
ap.add_argument("--ground", action="store_true", help="phase start: repeat the three drivers with resets at standing height")
a = ap.parse_args()

import distill_worker as dw  # noqa: E402
import flight_worker as fl  # noqa: E402
import recurrent as rc  # noqa: E402
import teacher as tc  # noqa: E402

fw = fl.fw
LEGS = [0, 1, 2, 3, 4, 9, 10, 11, 12, 13]
torch.manual_seed(1)


def q(x, ps=(5, 25, 50, 75, 95)):
    x = torch.as_tensor(x, dtype=torch.float32).flatten()
    return {f"p{p}": round(float(torch.quantile(x, p / 100)), 5) for p in ps} if len(x) else None


def cfg_dump(env_cfg):
    tw = env_cfg.commands["twist"]
    ev = env_cfg.events
    out = dict(twist={k: str(getattr(tw, k, None)) for k in ("rel_standing_envs", "rel_heading_envs", "rel_turn_in_place_envs",
                                                            "resampling_time_range", "ranges")},
               standing_stages=str(env_cfg.curriculum["standing_envs"].params.get("standing_stages")) if "standing_envs" in env_cfg.curriculum else None,
               reset_base=str(ev["reset_base"].params), reset_robot_joints=str(ev["reset_robot_joints"].params),
               randomize_com_ranges=str(ev["randomize_com"].params.get("ranges")),
               com_range_curriculum=str(env_cfg.curriculum["com_range"].params) if "com_range" in env_cfg.curriculum else None,
               payload={k: v for k, v in ev["randomize_com"].params["payload"].items() if k not in ("J_rest", "J_batt")},
               push_robot=str(ev["push_robot"].params) + " interval " + str(ev["push_robot"].interval_range_s) if "push_robot" in ev else None,
               episode_length_s=env_cfg.episode_length_s, events=sorted(ev.keys()))
    return out


if a.phase == "dist":
    dump = {}
    env, venv, delta = dw.build_env(fw, "universal4", a.manifest, a.audit, 0.0, 512, 1, "cpu", mutate=lambda c: dump.update(cfg_dump(c)))
    env.episode_length_buf = torch.randint_like(env.episode_length_buf, high=int(env.max_episode_length))  # as distill_worker
    obs = venv.get_observations()
    teacher = tc.TorchPolicy(a.teacher_onnx)
    robot, cm = env.scene["robot"], env.command_manager
    st = env._payload_state
    kind = st["kind"]
    zero_ticks, ticks, resets, resets_zero = 0, 0, 0, 0
    after = dict(joint_abs_max=[], grav_xy=[], height=[], lin_speed=[], ang_speed=[])
    comx_full = [env._payload_obs[kind == 0, 1].clone()]
    with torch.no_grad():
        for t in range(400):
            o = obs["actor"]
            obs, _, dones, extras = venv.step(teacher(torch.cat([o, tc.priv_obs(env)], dim=1)))
            cmd = cm.get_command("twist")
            z = cmd.abs().sum(dim=1) == 0
            zero_ticks += int(z.sum())
            ticks += len(z)
            d = dones.bool()
            if bool(d.any()):
                resets += int(d.sum())
                resets_zero += int((z & d).sum())
                oo = obs["actor"][d]
                after["joint_abs_max"].append(oo[:, 6:20].abs().max(dim=1).values)
                after["grav_xy"].append(oo[:, 3:5].norm(dim=1))
                after["height"].append(robot.data.root_link_pos_w[d, 2])
                after["lin_speed"].append(robot.data.root_link_lin_vel_b[d].norm(dim=1))
                after["ang_speed"].append(robot.data.root_link_ang_vel_b[d].norm(dim=1))
                comx_full.append(env._payload_obs[d & (kind == 0), 1].clone())
    cx = torch.cat(comx_full)
    out = dict(phase="dist", config=dump, loop_delay=delta.get("loop_delay"), envs=512, ticks_per_env=400,
               zero_twist_tick_fraction=round(zero_ticks / ticks, 4), resets=resets,
               resets_starting_at_zero_twist=resets_zero, resets_starting_at_zero_twist_fraction=round(resets_zero / max(resets, 1), 4),
               payload_kind_counts={s: int((kind == i).sum()) for i, s in enumerate(("full", "nobatt", "none", "scaled"))},
               state_right_after_reset={k: q(torch.cat(v)) for k, v in after.items() if v},
               full_pack_trunk_com_x_m=dict(n=len(cx), quantiles=q(cx, (1, 5, 25, 50, 75, 95, 99)), min=round(float(cx.min()), 5),
                                            max=round(float(cx.max()), 5), values=[round(float(v), 5) for v in cx[:4000]]))
    Path(a.out).write_text(json.dumps(out, indent=1))
    print("[start_env] dist", {k: out[k] for k in ("zero_twist_tick_fraction", "resets", "resets_starting_at_zero_twist_fraction")}, flush=True)
    sys.exit(0)

# phase start
fw.DELTAS["cause_start"] = dict(fw.DELTAS["universal4"], standing_frac=1.0)


def mutate(c):
    c.events.pop("push_robot", None)
    c.events["randomize_com"].params["payload"]["com_x_fixed_whole_m"] = float(a.comx)
    for name in ("head_pose", "body_pose"):
        c.commands[name].ranges = tuple((0.0, 0.0) for _ in c.commands[name].ranges)
        c.commands[name].zero_command_prob = 1.0   # the range curriculum rewrites the ranges; this keeps the command at zero
    c.commands["twist"].rel_turn_in_place_envs = 0.0


N = a.num_envs
env, venv, delta = dw.build_env(fw, "cause_start", a.manifest, a.audit, 0.0, N, 1, "cpu",
                                pin=dict(full=1.0, nobatt=0.0, none=0.0, scaled=0.0), mutate=mutate)
teacher = tc.TorchPolicy(a.teacher_onnx)
ck = torch.load(a.student_pt, map_location="cpu", weights_only=False)
sp = ck["spec"]
student = rc.Student(sp["core"], teacher.mean[:, :rc.OBS], teacher.div[:, :rc.OBS], d=sp["d"], layers=sp["layers"])
student.load_state_dict(ck["student"])
student.eval()
robot, cm = env.scene["robot"], env.command_manager
out = dict(phase="start", comx_whole_m=a.comx, envs=N, student=dict(file=Path(a.student_pt).name, iter=int(ck["iter"]), spec=sp), drivers={})
RUNS = [("student", 0.0, ""), ("student_drop036", 0.036, ""), ("teacher", 0.0, "")]
if a.ground:
    RUNS += [("student", 0.0, "_ground"), ("student_drop036", 0.036, "_ground"), ("teacher", 0.0, "_ground")]
h_stand = None
for driver, p_drop, tag in RUNS:
    if tag and "ground_reset_z" not in out:
        # --ground: every reset places the robot at its standing height (the teacher's height at 2 s plus 2 mm)
        # instead of 0.12-0.15 m, so the episode starts loaded on the floor like the runtime simulation's first tick
        z = round(h_stand + 0.002, 4)
        env.event_manager.get_term_cfg("reset_base").params["pose_range"]["z"] = (z, z)
        out["ground_reset_z"] = z
    obs, _ = venv.reset()
    state = student.init_state(N)
    alive = torch.ones(N, dtype=torch.bool)
    prev = None
    vx_t, diff, falls, fall_ticks, zero_cmd, dropped, alive_n = [], [], 0, [], 0, 0, 0
    first = dict(joint_abs_max=q(obs["actor"][:, 6:20].abs().max(dim=1).values), grav_xy=q(obs["actor"][:, 3:5].norm(dim=1)),
                 height=q(robot.data.root_link_pos_w[:, 2]), trunk_com_x=q(env._payload_obs[:, 1]), payload_kg=q(env._payload_obs[:, 0]),
                 head_body_command_abs_max=round(float(obs["actor"][:, 51:61].abs().max()), 5))
    with torch.no_grad():
        for t in range(100):
            o = obs["actor"]
            lab = teacher(torch.cat([o, tc.priv_obs(env)], dim=1))
            ran = torch.ones(N, dtype=torch.bool) if (p_drop == 0 or prev is None) else torch.rand(N) >= p_drop
            act_new, state_new = student.step(o, state)
            state = torch.where(ran.view(N, 1), state_new, state)
            dropped += int((~ran & alive).sum())
            act_s = act_new if prev is None else torch.where(ran.view(N, 1), act_new, prev)
            applied = lab if driver == "teacher" else act_s
            diff.append((act_new - lab).abs()[alive & ran][:, LEGS])
            zero_cmd += int(((cm.get_command("twist").abs().sum(dim=1) == 0) & alive).sum())
            alive_n += int(alive.sum())
            obs, _, dones, extras = venv.step(applied)
            prev = applied
            v = robot.data.root_link_lin_vel_b[:, 0]
            d = dones.bool()
            to = extras.get("time_outs", torch.zeros_like(d)).bool()
            fell = d & ~to & alive
            falls += int(fell.sum())
            fall_ticks += [t] * int(fell.sum())
            alive = alive & ~d
            vx_t.append(float(v[alive].mean()) if bool(alive.any()) else float("nan"))
    dd = torch.cat(diff)
    if driver == "teacher" and not tag:
        h_stand = float(robot.data.root_link_pos_w[alive, 2].median())
        out["standing_height_at_2s_teacher"] = round(h_stand, 4)
    driver = driver + tag
    out["drivers"][driver] = dict(
        falls_of_envs=falls, fall_ticks=sorted(fall_ticks)[:60], alive_at_2s=int(alive.sum()),
        forward_speed_mean_0_2s=round(float(torch.tensor(vx_t).nanmean()), 4),
        forward_speed_by_half_second=[round(float(torch.tensor(vx_t[i:i + 25]).nanmean()), 4) for i in range(0, 100, 25)],
        leg_abs_diff_median=round(float(dd.median(dim=0).values.mean()), 4),
        leg_abs_diff_p90=round(float(torch.quantile(dd, 0.9, dim=0).mean()), 4),
        zero_twist_fraction_of_alive_ticks=round(zero_cmd / max(alive_n, 1), 4),
        dropped_ticks=dropped, first_tick=first)
    print("[start_env]", a.comx, driver, {k: out["drivers"][driver][k] for k in ("falls_of_envs", "forward_speed_mean_0_2s", "leg_abs_diff_median", "leg_abs_diff_p90")}, flush=True)
Path(a.out).write_text(json.dumps(out, indent=1))
