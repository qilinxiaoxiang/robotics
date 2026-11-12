#!/usr/bin/env python3
"""Print the short form of play_locate.py outputs: frame fit, gyro vs residual rms per stance foot, joint ratios."""
import json
import sys

for p in sys.argv[1:]:
    d = json.load(open(p))
    f = d["frame"]
    print(f"== {p}: lag {f['lag_ticks']} ticks, fit on {f['fit_ticks']} ticks, Q diag {[row[i] for i, row in enumerate(f['Q'])]}")
    for s, v in d["side_axis"].items():
        print(f"  {s} stance {v['ticks']} ticks  " + "  ".join(
            f"{a}: gyro {v[a]['gyro_rms']} kin {v[a]['kin_rms']} resid {v[a]['residual_rms']}" for a in ("roll_x", "pitch_y", "yaw_z")))
    print("  joints (reversals, ratio):", {k: (v["reversals"], v.get("ratio")) for k, v in d["joints"].items()})
