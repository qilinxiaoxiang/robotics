"""Round 2 cold-start study (2026-11-18): reads the cells of ts2_start.py (runtime simulation) and ts2_start_env.py
(distillation env) and writes out/ts2_cause_start.json.

  <venv python> train/ts2_start_analyse.py
"""
import json
from pathlib import Path

import numpy as np

TRAIN = Path(__file__).resolve().parent
LEGS = [0, 1, 2, 3, 4, 9, 10, 11, 12, 13]
D = "s2g_200"
# cell -> (file stem, what it is)
RUNTIME = {"cold_comx10": (f"cz_{D}_shadow", "empty state, COM x +10 mm, walk from 2 s (the earlier shadow cell)"),
           "warm_comx10": (f"cz_{D}_warm", "state of a finished episode of the same seed, COM x +10 mm, walk from 2 s"),
           "cold_nominal": (f"cz_{D}_nominal", "empty state, nominal pack, walk from 2 s"),
           "cold_none": (f"cz_{D}_none", "empty state, no pack, walk from 2 s"),
           "teacher_comx10": (f"cz_{D}_tshadow", "the teacher drives, COM x +10 mm, walk from 2 s (earlier cell)"),
           "stand_cold_comx10": (f"cz_{D}_stand", "empty state, COM x +10 mm, zero command all episode"),
           "stand_warm_comx10": (f"cz_{D}_stand_warm", "warm state, COM x +10 mm, zero command all episode"),
           "stand_teacher_comx10": (f"cz_{D}_stand_teacher", "the teacher drives, COM x +10 mm, zero command all episode"),
           "landing_cold_comx10": (f"cz_{D}_landing", "empty state, COM x +10 mm, released 2.5-3.5 cm above the floor tilted up to 5 deg, walk from 2 s"),
           "landing_teacher_comx10": (f"cz_{D}_landing_teacher", "the teacher drives the same landing start"),
           "dump_none": (f"cz_{D}_dump_none", "no pack, drops off: the run whose end states are reused below"),
           "warm_from_none_comx10": (f"cz_{D}_warm_from_none", "state saved at the end of a no-pack episode, used at COM x +10 mm, walk from 2 s"),
           "landing_warm_from_none_comx10": (f"cz_{D}_landing_warm_from_none", "the same no-pack state, landing start at COM x +10 mm")}
# part A, the reading of the code and config (line numbers as of 2026-11-18; microduck_rl/...)
READING = [
    dict(point="share of distillation ticks with an exactly zero twist command",
         source="standing envs get the whole command zeroed (mjlab velocity_command.py:84, :136); the share is the standing_envs "
                "curriculum's last stage 0.25 (src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py:798-804), reached at once "
                "because build_env sets the step counter past every stage (cmu/finetune/flight/distill_worker.py:59); 15 % of envs "
                "are turn-in-place and are taken out of the standing set (microduck_velocity_env_cfg.py:25, mdp.py:4771). "
                "Expected 0.25 x 0.85 = 0.21 of command draws",
         measured="training_env.as_distilled: zero_twist_tick_fraction over the first 400 ticks of a fresh env (a lower bound: the "
                  "curriculum value applies from an env's first resample) and resets_starting_at_zero_twist_fraction"),
    dict(point="does an episode begin at zero command from reset with an empty student state",
         source="yes: the command is redrawn at reset and the student's state is zeroed for the reset envs "
                "(distill_worker.py:230); about one reset in five starts at zero command (measured share above)"),
    dict(point="reset state against the runtime episode's first tick with --stand-s 0",
         source="training: joints exactly at the default pose, zero velocities (mjlab velocity_env_cfg.py reset_robot_joints "
                "position_range (0, 0), velocity_range (0, 0)), trunk upright with a random yaw, base at 0.12-0.15 m "
                "(cmu/finetune/flight/flight_worker.py:53 drop_z, :247-248): the robot is released above the floor and lands. "
                "Runtime: the Brain's stand pose with the soles 0.5 mm above the floor, at rest "
                "(cmu/mac/brain_sim_check.py:1096-1104), the policy runs from the first tick (--stand-s 0)",
         measured="training_env.as_distilled.state_right_after_reset and runtime.first_observation"),
    dict(point="does COM x reach +10 mm in the training range",
         source="whole-robot x offset uniform in +-12 mm at every load, redrawn at every reset (flight_worker.py:95, "
                "cmu/finetune/flight/payload.py:124-128). The runtime's comx+10 manifest puts the loaded trunk COM at x = -6.4 mm "
                "(eval/pk_t2a_999_comx.json priv_first; nominal -21.1 mm), which is +11.5 mm in the env's whole-robot terms: "
                "0.5 mm inside the edge, so 2 % of full-pack resets are at or beyond it and 8 % beyond +10 mm",
         measured="training_env.as_distilled.full_pack_trunk_com_x_m"),
]
REFS = {"none": f"pk_{D}_none", "full": f"pk_{D}_full", "comx": f"pk_{D}_comx", "nobatt": f"pk_{D}_nobatt", "shove_nominal": f"pk_{D}_shove"}


def cell(stem, what):
    p = TRAIN / f"eval/{stem}.json"
    if not p.exists():
        return None
    j = json.loads(p.read_text())
    eps = j["episodes"]
    stat = {}
    for e in eps:
        for k, v in (e.get("diag_stat") or {}).items():
            stat[k] = stat.get(k, 0) + v
    falls = sorted(e["fell_at"] for e in eps if e["fell_at"] is not None)
    out = dict(what=what, file=f"eval/{stem}.json", manifest=j["summary"]["manifest"], case=j["summary"]["case"],
               falls_of_20=len(falls), fall_times=[round(x, 2) for x in falls],
               falls_before_2s=sum(1 for x in falls if x < 2), falls_2_to_4s=sum(1 for x in falls if 2 <= x < 4),
               falls_after_4s=sum(1 for x in falls if x >= 4), counters_sum_over_episodes=stat,
               episodes_with_warm_state=sum(1 for e in eps if (e.get("diag_stat") or {}).get("warm_state_loaded")),
               dist_x_median_m=round(float(np.median([e["dist_x"] for e in eps if e.get("dist_x") is not None and e["fell_at"] is None] or [np.nan])), 4))
    rows_all = [(e, r) for e in eps for r in (e.get("shadow") or []) if e["fell_at"] is None or r["time"] <= e["fell_at"] - 0.5]
    if rows_all:
        def win(lo, hi):
            rr = [r for _, r in rows_all if lo <= r["time"] < hi]
            if not rr:
                return None
            dd = np.abs(np.array([r["s"] for r in rr]) - np.array([r["t"] for r in rr]))[:, LEGS]
            return dict(n=len(rr), forward_speed_mean=round(float(np.mean([r["vx"] for r in rr])), 4),
                        trunk_pitch_mean=round(float(np.mean([r["pitch"] for r in rr])), 4),
                        leg_abs_diff_median=round(float(np.median(dd, axis=0).mean()), 4),
                        leg_abs_diff_p90=round(float(np.percentile(dd, 90, axis=0).mean()), 4))
        out["first_2s"] = win(0.0, 2.0)
        out["forward_speed_by_half_second_0_2s"] = [(win(a, a + 0.5) or {}).get("forward_speed_mean") for a in (0.0, 0.5, 1.0, 1.5)]
        if j["summary"]["case"] == "stand":
            out["forward_speed_by_2s"] = [(win(a, a + 2.0) or {}).get("forward_speed_mean") for a in range(0, 20, 2)]
        # per episode: forward speed over the first 2 s (or until 0.5 s before its fall)
        per = {}
        for e, r in rows_all:
            if r["time"] < 2.0:
                per.setdefault(e["seed"], []).append(r["vx"])
        v = [float(np.mean(x)) for x in per.values()]
        out["episodes_creeping_over_0p05_mps_in_first_2s"] = sum(1 for x in v if x > 0.05)
        out["episode_forward_speed_first_2s_quartiles"] = [round(float(np.percentile(v, p)), 4) for p in (25, 50, 75)]
    return out


def first_tick():
    """the runtime episode's first observation (seeds 0 to 2 carry the observation vector)"""
    p = TRAIN / f"eval/cz_{D}_shadow.json"
    if not p.exists():
        return None
    out = []
    for e in json.loads(p.read_text())["episodes"]:
        r = next((r for r in e.get("shadow") or [] if "obs" in r), None)
        if r is not None:
            o = np.array(r["obs"])
            out.append(dict(seed=e["seed"], tick=r["k"], joint_offset_from_default_abs_max=round(float(np.abs(o[6:20]).max()), 4),
                            joint_offset_from_default=o[6:20].round(4).tolist(), gravity=o[3:6].round(4).tolist(),
                            joint_velocity_abs_max=round(float(np.abs(o[20:34]).max()), 4), trunk_pitch=r["pitch"]))
    return out


def env(stem):
    p = TRAIN / f"eval/{stem}.json"
    return json.loads(p.read_text()) if p.exists() else None


def main():
    rt = {k: cell(*v) for k, v in RUNTIME.items()}
    refs = {}
    for k, stem in REFS.items():
        p = TRAIN / f"eval/{stem}.json"
        if p.exists():
            s = json.loads(p.read_text())["summary"]
            refs[k] = dict(file=f"eval/{stem}.json", manifest=s["manifest"], falls_of_20=s["falls"], fall_times=[round(x, 2) for x in s["fall_times"]])
    dist = env("cz_start_env_dist")
    if dist:
        dist["full_pack_trunk_com_x_m"].pop("values", None)
    out = dict(student=D, runtime=dict(cells=rt, references_without_switch=refs, first_observation=first_tick()),
               training_env=dict(reading=READING, as_distilled=dist,
                                 standing_start_comx10=env("cz_start_env_comx10"), standing_start_comx0=env("cz_start_env_comx0"),
                                 standing_start_comx11p5_zero_head_cmd=env("cz_start_env_g115"),
                                 standing_start_comx0_zero_head_cmd=env("cz_start_env_g0"),
                                 note="standing_start_comx10 / comx0 ran with the head and body commands at their full training range "
                                      "(the zeroing did not take effect, first_tick.head_body_command_abs_max); the two zero_head_cmd "
                                      "records have them at zero and add the drivers with resets on the floor (_ground)"))
    (TRAIN / "out/ts2_cause_start.json").write_text(json.dumps(out, indent=1))
    for k, c in rt.items():
        if c:
            f2 = c.get("first_2s") or {}
            print(f"{k:22s} falls {c['falls_of_20']:2d} (<2 s {c['falls_before_2s']}, 2-4 s {c['falls_2_to_4s']}, later {c['falls_after_4s']}) "
                  f"vx 0-2 s {f2.get('forward_speed_mean')} by 0.5 s {c.get('forward_speed_by_half_second_0_2s')} "
                  f"diff {f2.get('leg_abs_diff_median')}/{f2.get('leg_abs_diff_p90')} creeping eps {c.get('episodes_creeping_over_0p05_mps_in_first_2s')} "
                  f"counters {c['counters_sum_over_episodes']}")
            if c.get("forward_speed_by_2s"):
                print("    ", "vx by 2 s", c["forward_speed_by_2s"], "falls at", c["fall_times"])
    print("refs", {k: v["falls_of_20"] for k, v in refs.items()})
    for k in ("standing_start_comx10", "standing_start_comx0", "standing_start_comx11p5_zero_head_cmd", "standing_start_comx0_zero_head_cmd"):
        e = out["training_env"][k]
        if e:
            print(k, "standing height", e.get("standing_height_at_2s_teacher"), "ground z", e.get("ground_reset_z"))
            for dr, x in e["drivers"].items():
                print(k, dr, {n: x[n] for n in ("falls_of_envs", "forward_speed_mean_0_2s", "forward_speed_by_half_second", "leg_abs_diff_median",
                                                "leg_abs_diff_p90", "zero_twist_fraction_of_alive_ticks", "dropped_ticks")})
            print("   first tick", e["drivers"]["student"]["first_tick"])
    if dist:
        print("dist", {k: dist[k] for k in ("zero_twist_tick_fraction", "resets", "resets_starting_at_zero_twist_fraction", "payload_kind_counts",
                                            "state_right_after_reset")}, dist["full_pack_trunk_com_x_m"])
        print(json.dumps(dist["config"])[:2500])
    for f in out["runtime"]["first_observation"] or []:
        print("runtime first obs", f)


if __name__ == "__main__":
    main()
