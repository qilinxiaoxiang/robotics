"""What-if: the robot's feet sit d degrees more forward-leaning on the ankles than the encoders report (an ankle zero
error after the V1.22 refit). In the sim the open-loop stand then holds NEUTRAL + d at the ankles (true frame).
Does it fall forward like the robot (12 deg rest, falls after ~20 s)? Sim only."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "stand-pose-study-20261020"))
import stand_sim as S
d = float(sys.argv[1]); r = math.radians(d)
pose = dict(S.NEUTRAL); pose["right_ankle"] += r; pose["left_ankle"] -= r   # opposite of stand_sim.BACK["ankle"]
out = S.run_case(pose, start=pose, T=60.0)
tr = out.pop("trace")
out["deg"] = d; out["pitch_trace"] = [(t, p) for t, _, p, _ in tr[::10]]
print(json.dumps(out))
