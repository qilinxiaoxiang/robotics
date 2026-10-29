"""Write the candidate pose lists: poses_policy.json (head_pose command deltas from the policy default) and
poses_openloop.json (absolute 14-joint open-loop stand targets, STAND legs unless a leg lean is named; leg leans use
stand-pose-study-20261020/stand_sim.back_delta sign conventions: positive hip/ankle = backward lean).

  python3 make_poses.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, MAC)
sys.path.insert(0, os.path.join(MAC, "..", "pi"))
from stand_pose import STAND_POSE as STAND  # noqa: E402

# stand_sim.BACK without importing stand_sim (it re-executes under the sim venv)
BACK = {"ankle": {"right_ankle": -1, "left_ankle": +1}, "hip": {"right_hip_pitch": -1, "left_hip_pitch": +1}}


def lean(**amt):
    d = {}
    for grp, a in amt.items():
        for j, s in BACK[grp].items():
            d[j] = d.get(j, 0.0) + s * a
    return d


policy = {
    "hp-0.50": {"head_pitch": -0.50},
    "hp-0.80": {"head_pitch": -0.80},
    "hp-1.10": {"head_pitch": -1.10},
    "nk+0.40_hp-1.10": {"neck_pitch": 0.40, "head_pitch": -1.10},
    "nk+0.70_hp-0.80": {"neck_pitch": 0.70, "head_pitch": -0.80},
    "nk-0.30_hp-1.10": {"neck_pitch": -0.30, "head_pitch": -1.10},
    "hp-1.10_hr+0.31": {"head_pitch": -1.10, "head_roll": 0.31},
    "nk+0.40_hp-1.10_hy-0.80_hr-0.31": {"neck_pitch": 0.40, "head_pitch": -1.10, "head_yaw": -0.80, "head_roll": -0.31},
    "shawn_nk-0.75_hp-1.10_hy+1.40_hr-0.31": {"neck_pitch": -0.75, "head_pitch": -1.10, "head_yaw": 1.40, "head_roll": -0.31},
}


def ol(head=None, legs=None):
    p = dict(STAND)
    for k, v in (legs or {}).items():
        p[k] += v
    p.update(head or {})
    return p


openloop = {
    "O_hp-0.90": ol({"head_pitch": -0.90}),
    "O_hp-1.27": ol({"head_pitch": -1.271}),
    "O_nk+1.047_hp-0.47": ol({"neck_pitch": 1.047, "head_pitch": -0.471}),
    "O_nk-0.47_hp-1.571": ol({"neck_pitch": -0.471, "head_pitch": -1.571}),
    "O_nk-0.97_hp-1.571": ol({"neck_pitch": -0.971, "head_pitch": -1.571}),
    "O_beg_hip+0.15_hp-0.90": ol({"head_pitch": -0.90}, lean(hip=0.15)),
    "O_beg_hip+0.30_hp-0.90": ol({"head_pitch": -0.90}, lean(hip=0.30)),
    "O_tiptoe_ankle-0.30_hp-0.90": ol({"head_pitch": -0.90}, lean(ankle=-0.30)),
    "O_tiptoe_ankle-0.50_hp-0.90": ol({"head_pitch": -0.90}, lean(ankle=-0.50)),
    "O_roll_hr+0.436_hp-0.90": ol({"head_pitch": -0.90, "head_roll": 0.436}),
    "O_yawback_nk-1.571_hp+0.13_hy-2.967_hr-0.24": ol({"neck_pitch": -1.571, "head_pitch": 0.129, "head_yaw": -2.967, "head_roll": -0.236}),
}

# round 2 (after round 1 fell during the ramp for every head-up pose): the control, milder look-ups, and look-ups with
# the legs leaned forward (negative = forward in stand_sim's convention) to bring the COM back over the feet
openloop2 = {
    "O2_control_STAND": ol(),
    "O2_control_STAND_noise0": ol(),
    "O2_hp-0.30": ol({"head_pitch": -0.30}),
    "O2_hp-0.60": ol({"head_pitch": -0.60}),
    "O2_hp-0.60_ankle-0.10": ol({"head_pitch": -0.60}, lean(ankle=-0.10)),
    "O2_hp-0.90_ankle-0.10": ol({"head_pitch": -0.90}, lean(ankle=-0.10)),
    "O2_hp-0.90_ankle-0.20": ol({"head_pitch": -0.90}, lean(ankle=-0.20)),
    "O2_hp-0.90_hip-0.15": ol({"head_pitch": -0.90}, lean(hip=-0.15)),
    "O2_nk-0.47_hp-1.571_ankle-0.10": ol({"neck_pitch": -0.471, "head_pitch": -1.571}, lean(ankle=-0.10)),
    "O2_nk-0.97_hp-1.571": ol({"neck_pitch": -0.971, "head_pitch": -1.571}),
}

# round 3: no start-pose noise (see sim_batch.openloop_job); the look-ups, the forward-lean compensations, the beg,
# the tiptoe, the roll and the yawed-back pose
openloop3 = {
    "O3_STAND": ol(),
    "O3_hp-0.30": ol({"head_pitch": -0.30}),
    "O3_hp-0.45": ol({"head_pitch": -0.45}),
    "O3_hp-0.60": ol({"head_pitch": -0.60}),
    "O3_hp-0.90": ol({"head_pitch": -0.90}),
    "O3_hp-0.60_ankle-0.10": ol({"head_pitch": -0.60}, lean(ankle=-0.10)),
    "O3_hp-0.90_ankle-0.10": ol({"head_pitch": -0.90}, lean(ankle=-0.10)),
    "O3_hp-0.90_ankle-0.20": ol({"head_pitch": -0.90}, lean(ankle=-0.20)),
    "O3_hp-0.90_hip-0.15": ol({"head_pitch": -0.90}, lean(hip=-0.15)),
    "O3_nk-0.47_hp-1.571": ol({"neck_pitch": -0.471, "head_pitch": -1.571}),
    "O3_nk-0.47_hp-1.571_ankle-0.10": ol({"neck_pitch": -0.471, "head_pitch": -1.571}, lean(ankle=-0.10)),
    "O3_nk-0.97_hp-1.571": ol({"neck_pitch": -0.971, "head_pitch": -1.571}),
    "O3_beg_hip+0.15_hp-0.90": ol({"head_pitch": -0.90}, lean(hip=0.15)),
    "O3_beg_hip+0.30_hp-0.60": ol({"head_pitch": -0.60}, lean(hip=0.30)),
    "O3_tiptoe_ankle-0.30_hp-0.60": ol({"head_pitch": -0.60}, lean(ankle=-0.30)),
    "O3_roll_hr+0.436_hp-0.60": ol({"head_pitch": -0.60, "head_roll": 0.436}),
    "O3_yawback_nk-1.571_hp+0.13_hy-2.967_hr-0.24": ol({"neck_pitch": -1.571, "head_pitch": 0.129, "head_yaw": -2.967, "head_roll": -0.236}),
}
json.dump(openloop3, open(os.path.join(HERE, "poses_openloop3.json"), "w"), indent=1)
json.dump(policy, open(os.path.join(HERE, "poses_policy.json"), "w"), indent=1)
json.dump(openloop, open(os.path.join(HERE, "poses_openloop.json"), "w"), indent=1)
json.dump(openloop2, open(os.path.join(HERE, "poses_openloop2.json"), "w"), indent=1)
# head-only dict for collide.py: every candidate head (policy deltas turned absolute on the NEUTRAL default)
from walk_brain import NEUTRAL, HEAD_JOINTS  # noqa: E402
heads = {}
for k, dl in policy.items():
    heads["P_" + k] = {n: round(NEUTRAL[n] + dl.get(n, 0.0), 4) for n in HEAD_JOINTS}
for k, p in openloop.items():
    heads[k] = {n: p[n] for n in HEAD_JOINTS}
json.dump(heads, open(os.path.join(HERE, "poses_heads.json"), "w"), indent=1)
print(len(policy), len(openloop), len(heads))
