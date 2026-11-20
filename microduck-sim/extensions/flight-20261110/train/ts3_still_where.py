"""Round 3 check (2026-11-20): why a walk61-anchored student steps in place without the pack at gain 400 and a zero
command, where walk61 (its label there) stands still.

  $PY train/ts3_still_where.py <dir under ckpt> <seeds, e.g. 0,1,2> [kp=400] [first=<ticks>] [after=<tick>] [drop=<f>]
                                                                                              (Mac mini only)
One gate standing episode without the pack per seed (the none_g400_stand cell at kp=400), with the deployed walk61
computed on every observation the student sees (flight_eval FLIGHT_SHADOW61, nothing of it applied) and the student's
own action from an EMPTY recurrent state on the same observation (FLIGHT_STATE_EMPTY). Per 2 s:
  student-walk61  rms difference of the two actions over the 14 joints, rad (the anchor's training error, live)
  empty-walk61    the same for the student with an empty state
  step            mean over ticks of the largest tick-to-tick action change: student / walk61 on the same states
  jumps           ticks with a student step over 0.5 rad (the gate's measure)
first=<ticks>  walk61 drives the first <ticks> control ticks, then the student (which saw every observation)
after=<tick>   the student drives up to that tick, then walk61: does walk61 bring the student's stepping to rest?
drop=<f>       the probe's dropped-read fraction (--drop)
No joint index is used: all quantities are over the whole action vector.
"""
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flight_eval as fe  # noqa: E402

W61 = str((HERE / "../../../microduck_rl/cmu/whole/runtime-overlay/models/walk61.onnx").resolve())


def main():
    d, seeds = sys.argv[1], [int(s) for s in sys.argv[2].split(",")]
    opts = dict(x.split("=") for x in sys.argv[3:])
    kp = opts.get("kp", "400")
    extra = ["--kp-rl", kp] + (["--drop", opts["drop"]] if "drop" in opts else [])
    os.environ["FLIGHT_SHADOW61"] = W61
    os.environ["FLIGHT_STATE_EMPTY"] = "1"
    if "first" in opts:
        os.environ["FLIGHT_HANDOVER"] = W61 + ":" + opts["first"]
    if "after" in opts:
        os.environ["FLIGHT_HANDOVER_AFTER"] = W61 + ":" + opts["after"]
    for seed in seeds:
        r = fe.episode((str(HERE / "ckpt" / d), str(HERE / "manifests/flightpack-none.json"), "stand", seed, 0.0, 8.0,
                        False, extra))
        rows = fe.DIAG["stat"].get("sh61", [])
        t0 = rows[0][0]
        print(f"{d} none stand kp {kp} {' '.join(f'{k}={v}' for k, v in opts.items() if k != 'kp')} seed {seed}: fell at "
              f"{r['fell_at']}; gate jumps {r['action_jumps']}; policy calls {len(rows)}; handover ticks "
              f"{fe.DIAG['stat'].get('handover_ticks', 0)}; gain flag {fe.DIAG['stat'].get('gain_flag_value')}", flush=True)
        per = {}
        for i in range(1, len(rows)):
            tk, stu, ref, cold = rows[i][0], np.array(rows[i][1]), np.array(rows[i][2]), np.array(rows[i][3])
            if tk - rows[i - 1][0] != 1:
                continue
            p = per.setdefault(int((tk - t0) // 100) * 2, dict(n=0, e=0.0, c=0.0, ss=0.0, rs=0.0, j=0))
            p["n"] += 1
            p["e"] += float(((stu - ref) ** 2).mean())
            p["c"] += float(((cold - ref) ** 2).mean())
            st = float(np.abs(stu - np.array(rows[i - 1][1])).max())
            p["ss"] += st
            p["rs"] += float(np.abs(ref - np.array(rows[i - 1][2])).max())
            p["j"] += st > 0.5
        for s in sorted(per):
            p = per[s]
            print(f"  {s:2d}-{s + 2:2d} s: student-walk61 rms {(p['e'] / p['n']) ** 0.5:.3f}  empty-walk61 rms "
                  f"{(p['c'] / p['n']) ** 0.5:.3f}  step student {p['ss'] / p['n']:.3f} / walk61 on the same states "
                  f"{p['rs'] / p['n']:.3f}  jumps {p['j']}", flush=True)


if __name__ == "__main__":
    main()
