"""Sim analogue of the real stand61 mean stance: stand61 at zero command on the floor from NEUTRAL_POSE for 30 s
(as-built model, real-condition flags), mean encoder pose over upright ticks after the first 3 s. Writes
results/sim_stand61_mean.json (delta_from_neutral, joint names as in walk_brain)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stand_sim as S  # re-execs under the sim venv
out = {}
for hg in (0, 10, 20):
    r = S.run_case(dict(S.NEUTRAL), T=33.0, walk_at=1.0, walk_s=32.0, head_g=hg)
    out[f"head{hg:+d}"] = dict(fell_at=r["fell_at"], max_tilt=r["walk"]["max_tilt"], ticks=r["walk"]["mean_q_ticks"],
                               delta_from_neutral=r["walk"]["mean_q_delta_from_target"])
    print(hg, json.dumps(out[f"head{hg:+d}"]))
res = dict(out["head+0"], by_head=out)
os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
json.dump(res, open(os.path.join(HERE, "results", "sim_stand61_mean.json"), "w"), indent=1)
