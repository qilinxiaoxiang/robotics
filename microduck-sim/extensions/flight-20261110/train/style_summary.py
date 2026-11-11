"""Collect the style_probe.sh results (train/eval/st_*.json) into train/out/style_bend_head.json.

  python3 train/style_summary.py
Toe-out: per foot stance yaw against the trunk heading (toe-out positive, change from the trained start pose), hip yaw
and hip roll means, step width, roll at touchdown, trunk yaw oscillation. Bend and head: falls of 20 (with times),
trunk pitch (nose-down positive) excursion, leg torque p99 against 0.538 N m, head/neck angles reached.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS_TOE = ("falls", "speed_median_upright", "left_stance_toe_out_deg_mean", "right_stance_toe_out_deg_mean",
            "left_stance_toe_out_deg_p95", "right_stance_toe_out_deg_p95", "left_stance_toe_out_vs_path_deg_mean",
            "right_stance_toe_out_vs_path_deg_mean", "left_hip_yaw_deg_mean", "right_hip_yaw_deg_mean",
            "left_hip_roll_deg_mean", "right_hip_roll_deg_mean", "left_hip_roll_deg_start", "right_hip_roll_deg_start",
            "left_foot_yaw_per_hip_yaw", "right_foot_yaw_per_hip_yaw", "step_width_mm", "stand_width_mm",
            "stance_width_start_mm", "left_roll_at_touchdown_deg_mean", "right_roll_at_touchdown_deg_mean",
            "trunk_yaw_osc_p95_deg", "leg_force_p99_nm_median")
KEYS_MOVE = ("falls", "fall_times", "speed_median_upright", "max_tilt", "trunk_pitch_excursion_deg_median",
             "trunk_pitch_excursion_deg_max", "leg_force_p99_nm_median", "leg_force_sat_frac_max", "joint_p99_nm",
             "neck_pitch_min", "neck_pitch_max", "head_pitch_min", "head_pitch_max", "head_pitch_mean", "head_yaw_min",
             "head_yaw_max")


def main():
    out = dict(note=__doc__.strip().splitlines()[0], toe={}, bend={}, head={})
    for f in sorted((HERE / "eval").glob("st_*.json")):
        name = f.stem[3:]
        if name == "test":
            continue
        s = json.loads(f.read_text())["summary"]
        grp = "toe" if name.startswith("toe_") else "bend" if name.startswith("bend_") else "head"
        keys = KEYS_TOE if grp == "toe" else KEYS_MOVE
        out[grp][name] = dict(models=s["models"], manifest=s["manifest"], case=s["case"], extra=s["extra"],
                              episodes=s["episodes"], **{k: s.get(k) for k in keys})
        if grp == "bend":  # trunk pitch extremes per episode: nose-down max and nose-up min
            eps = json.loads(f.read_text())["episodes"]
            tp = [e["style"]["trunk_pitch_deg"] for e in eps if e["style"]["trunk_pitch_deg"]]
            out[grp][name]["trunk_pitch_max_nose_down_deg_median"] = sorted(p["max"] for p in tp)[len(tp) // 2]
            out[grp][name]["trunk_pitch_min_deg_median"] = sorted(p["min"] for p in tp)[len(tp) // 2]
            out[grp][name]["fall_dirs"] = sorted({e["fall_dir"] for e in eps if e["fall_dir"]})
    (HERE / "out" / "style_bend_head.json").write_text(json.dumps(out, indent=1))
    print({g: len(v) for g, v in out.items() if isinstance(v, dict)})


if __name__ == "__main__":
    main()
