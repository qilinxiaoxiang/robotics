"""Write targets-20261030.json: the six robot rows of 2026-10-30 (0.25 m/s commanded) scored with jitter_metrics.

Sources: microduck-sim/guide/firmware/mac/robot-runs-20261030-t1/ (walk61 five --see walks, T1 steps 2 and 4,
t2b steps 1-3). walk61's five walks are reported as a range (min-max) and their mean is the target.

  python3 make_targets.py
"""
import json
import os

import jitter_metrics as jm

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "robot-runs-20261030-t1")
ROWS = [
    ("walk61_default", "walk61", None, 3.0, "walk61_see_walks.jsonl"),
    ("t1_default", "models-t1-best", None, 3.0, "2_walk_fell.jsonl"),
    ("t1_neck-0.4", "models-t1-best", -0.4, 3.0, "4_walk_neck.jsonl"),
    ("t2b_default", "models-t2b-best", None, 3.0, "t2b/1_walk.jsonl"),
    ("t2b_neck-0.4", "models-t2b-best", -0.4, 3.0, "t2b/2_walk_neck.jsonl"),
    ("t2b_neck-0.8", "models-t2b-best", -0.8, 2.0, "t2b/3_neck_hold.jsonl"),
]
KEYS = ("jump_rate_per_s", "tilt_max", "tilt_mean", "act_p95", "act_max", "leg_q_over_a", "gyro_rms", "band_f_dom_hz")


def main():
    out = dict(date="2026-10-30", vx=0.25, source=os.path.relpath(RUNS, HERE),
               definitions="jitter_metrics.stats: compare_walks.py definitions (jump = any action changes > 0.5 rad "
                           "between consecutive walk-policy ticks; rate per segment second; tilt over all segment rows)",
               rows=[])
    for name, models, neck, walk_s, f in ROWS:
        segs = [s for s in (jm.stats(seg) for seg in jm.robot_segments(jm.load(os.path.join(RUNS, f)))) if s]
        row = dict(name=name, models=models, neck_pitch=neck, walk_s=walk_s, log=f, n_walks=len(segs), walks=segs)
        for k in KEYS:
            vals = [s[k] for s in segs if s.get(k) is not None]
            if not vals:
                continue
            if isinstance(vals[0], list):
                row[k] = [round(sum(v[i] for v in vals) / len(vals), 3) for i in range(len(vals[0]))]
            else:
                row[k] = round(sum(vals) / len(vals), 2)
                if len(vals) > 1:
                    row[k + "_range"] = [min(vals), max(vals)]
        row["fell"] = any(s["fell"] for s in segs)
        # joints carrying the 2-8 Hz action power (mechanism check), mean over walks
        ba = {}
        for s in segs:
            for j, v in s.get("band_a_rms", {}).items():
                ba[j] = ba.get(j, 0) + v / len(segs)
        row["band_a_rms"] = {j: round(v, 3) for j, v in ba.items()}
        out["rows"].append(row)
        print(name, {k: row.get(k) for k in ("n_walks", "jump_rate_per_s", "jump_rate_per_s_range", "tilt_max",
                                              "tilt_max_range", "tilt_mean", "leg_q_over_a", "gyro_rms", "fell")})
    json.dump(out, open(os.path.join(HERE, "targets-20261030.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
