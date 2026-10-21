"""Offline replay of sitstand61 on the robot's logged observations (no robot, no sim): which observation block keeps
the policy from sitting on the robot while it sits in the as-built sim?"""
import json, sys, os, statistics as st
import numpy as np
FW = "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware"
sys.path.insert(0, FW + "/pi/microduck_rt"); sys.path.insert(0, FW + "/pi")
from constants import MOTOR_TO_ID, OBSERVATION_DOF_ORDER as OBS
import onnxruntime as ort
ID_TO_NAME = {v: k for k, v in MOTOR_TO_ID.items()}
NAMES = [ID_TO_NAME[i] for i in range(1, 15)]
sess = ort.InferenceSession("/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/runtime-overlay/models/sitstand61.onnx")
meta = sess.get_modelmeta().custom_metadata_map
default = dict(zip(OBS, [float(v) for v in meta["default_joint_pos"].split(",")]))
S = os.path.dirname(os.path.abspath(__file__))

def blocks(row):
    q = dict(zip(NAMES, row["q"])); dq = dict(zip(NAMES, row["dq"]))
    return dict(gyro=np.array(row["gyro_body"], dtype=np.float32), grav=np.array(row["gb"], dtype=np.float32),
                qpos=np.array([q[n] - default[n] for n in OBS], dtype=np.float32), qvel=np.array([dq[n] for n in OBS], dtype=np.float32),
                head=np.array(row.get("head_cmd") or [0, 0, 0, 0], dtype=np.float32))

def run(b, last_action, flag):
    obs = np.concatenate([b["gyro"], b["grav"], b["qpos"], b["qvel"], last_action, [flag, 0, 0], b["head"], np.zeros(6)]).astype(np.float32)
    return sess.run(None, {sess.get_inputs()[0].name: obs[None]})[0][0]

rob = [json.loads(l) for l in open("/private/tmp/claude-501/stand/duck_wired_log_app1021-040436.jsonl")]
t0 = rob[0]["t"]
sim = [json.loads(l) for l in open(S + "/sim_sit_seed0.jsonl")]
kL, kR = OBS.index("left_knee"), OBS.index("right_knee")

# 1. reproduce the logged robot actions from the logged observations (sit2, flag 1)
last = None; errs = []
for r in rob:
    if r.get("action") is None:
        continue
    if 104.02 <= r["t"] - t0 < 110 and r.get("sit_flag") == 1.0 and last is not None:
        a = run(blocks(r), np.array(last, dtype=np.float32), 1.0)
        errs.append(max(abs(a - np.array(r["action"]))))
    last = r["action"]
print(f"1. replay of {len(errs)} robot ticks: max |replayed - logged action| = {max(errs):.4f}, median {st.median(errs):.4f}")

# 2. frozen-state recurrence: hold every sensor block at the first flag-1 tick, feed the action back for 1 s
def first_flag1(rows, tkey, tmin):
    for i, r in enumerate(rows):
        if r.get("sit_flag") == 1.0 and tkey(r) >= tmin:
            prev = next(x["action"] for x in reversed(rows[:i]) if x.get("action") is not None)
            return r, prev
r_rob, prev_rob = first_flag1(rob, lambda r: r["t"] - t0, 104.0)
r_sim, prev_sim = first_flag1(sim, lambda r: r["t"], 4.8)
def recur(b, prev, n=50):
    a = np.array(prev, dtype=np.float32); out = []
    for _ in range(n):
        a = run(b, a, 1.0); out.append(round(float(a[kL]), 2))
    return out
print("2. frozen-state recurrence, left knee action per tick (first 12 of 50, then the last):")
for name, b, prev in (("robot", blocks(r_rob), prev_rob), ("sim", blocks(r_sim), prev_sim)):
    s = recur(b, prev); print(f"   {name:<6} {s[:12]} ... {s[-1]}")
print("   robot blocks:", {k: np.round(v, 3).tolist() for k, v in blocks(r_rob).items()})
print("   sim blocks:  ", {k: np.round(v, 3).tolist() for k, v in blocks(r_sim).items()})

# 3. swap one block at a time from the sim into the robot's frozen state (and the reverse)
print("3. block swaps, final left-knee action after 50 frozen ticks (sim sits when it heads to about +1.2):")
for k in ("gyro", "grav", "qpos", "qvel", "head"):
    b = blocks(r_rob); b[k] = blocks(r_sim)[k]
    s = recur(b, prev_rob)
    b2 = blocks(r_sim); b2[k] = blocks(r_rob)[k]
    s2 = recur(b2, prev_sim)
    print(f"   robot with sim {k:<5}: {s[-1]:>6}    sim with robot {k:<5}: {s2[-1]:>6}")
b = blocks(r_rob); s = recur(b, prev_sim); print(f"   robot blocks with the sim's previous action: {s[-1]}")
# 4. gravity sweep on the robot's frozen state: pitch and roll of the gravity vector
print("4. robot frozen state, gravity replaced by pitch/roll (deg): final left-knee action")
import math
for pitch in (-6, -3, 0, 3, 4.4, 6, 9):
    line = []
    for roll in (-4, 0, 4):
        g = np.array([math.sin(math.radians(pitch)), -math.sin(math.radians(roll)), -math.cos(math.radians(pitch)) * math.cos(math.radians(roll))], dtype=np.float32)
        b = blocks(r_rob); b["grav"] = g
        line.append(f"roll {roll:+d}: {recur(b, prev_rob)[-1]:>5}")
    print(f"   pitch {pitch:+5.1f}  " + "  ".join(line))
