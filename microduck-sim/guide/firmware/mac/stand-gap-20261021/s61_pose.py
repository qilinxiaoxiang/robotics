"""Candidate open-loop stand pose: the joint pose stand61 holds on the real robot (mean measured q over tonight's
zero-command stand61 rows, real_pose_compare_1021.json 's61'). Sim, 120 s, as-built, real flags. Cases: nominal and
with the feet rocked 3 deg forward on the ankles (the real robot pivots on its feet). Sim only."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "stand-pose-study-20261020"))
import stand_sim as S
REAL = json.load(open(os.path.join(HERE, "real_pose_compare_1021.json")))
which, fwd = sys.argv[1], float(sys.argv[2]); kp = int(sys.argv[3]) if len(sys.argv) > 3 else 400
pose = dict(S.NEUTRAL) if which == "neutral" else {k: float(v) for k, v in REAL["s61"].items()}
if which == "s61_legs":  # legs from stand61, head at NEUTRAL
    for k in ("head_pitch", "neck_pitch", "head_yaw", "head_roll"): pose[k] = S.NEUTRAL[k]
r = math.radians(fwd); pose["right_ankle"] += r; pose["left_ankle"] -= r
out = S.run_case(pose, T=120.0, kp=kp)
tr = out.pop("trace"); out.update(case=f"{which} fwd{fwd} kp{kp}", pitch_trace=[(t, p) for t, _, p, _ in tr[::20]])
print(json.dumps(out))
