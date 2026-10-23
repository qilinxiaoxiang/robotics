"""Offline replay of sitstand61 on the robot's logged rise rows (10/23 run app1023-204119): is the neck dive the
policy's own response to forward pitch?"""
import json, sys, math
import numpy as np
FW = "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware"
sys.path.insert(0, FW + "/pi/microduck_rt")
from constants import MOTOR_TO_ID, OBSERVATION_DOF_ORDER as OBS
import onnxruntime as ort
ID_TO_NAME = {v: k for k, v in MOTOR_TO_ID.items()}
NAMES = [ID_TO_NAME[i] for i in range(1, 15)]
sess = ort.InferenceSession("/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/runtime-overlay/models/sitstand61.onnx")
default = dict(zip(OBS, [float(v) for v in sess.get_modelmeta().custom_metadata_map["default_joint_pos"].split(",")]))
NK = OBS.index("neck_pitch")
def obs(row, last, flag, grav=None):
    q = dict(zip(NAMES, row["q"])); dq = dict(zip(NAMES, row["dq"]))
    return np.concatenate([row["gyro_body"], grav if grav is not None else row["gb"], [q[n] - default[n] for n in OBS],
                           [dq[n] for n in OBS], last, [flag, 0, 0], row.get("head_cmd") or [0, 0, 0, 0], np.zeros(6)]).astype(np.float32)
def run(o): return sess.run(None, {sess.get_inputs()[0].name: o[None]})[0][0]
rows = [json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
P = lambda r: math.degrees(math.atan2(r["gb"][0], -r["gb"][2]))
# rise windows: mode sit with a non-sit command
rises = []; cur = None
for i, r in enumerate(rows):
    on = r["mode"] == "sit" and r["cmd"].get("mode") != "sit"
    if on and cur is None: cur = [i, i]
    if on: cur[1] = i
    if not on and cur: rises.append(cur); cur = None
if cur: rises.append(cur)
print("rises:", len(rises))
for k, (a, b) in enumerate(rises):
    last = None; errs = []
    for r in rows[a - 1:b + 1]:
        if r.get("action") is None: continue
        if last is not None and r is not rows[a - 1]:
            errs.append(float(max(abs(run(obs(r, np.array(last, np.float32), 0.0)) - np.array(r["action"])))))
        last = r["action"]
    print(f" rise {k}: replay max err {max(errs):.4f} over {len(errs)} ticks; peak pitch {max(P(r) for r in rows[a:b+1]):.1f}, "
          f"min neck action {min(r['action'][NK] for r in rows[a:b+1] if r.get('action')):+.2f}")
# pitch sweep on a standing tick of the last good rise (1.0 s after its start), recurrence with frozen sensors
a, b = rises[-2]
r0 = next(r for r in rows[a:b] if r["t"] - rows[a]["t"] >= 1.0 and r.get("action"))
prev = next(x["action"] for x in reversed(rows[a:rows.index(r0)]) if x.get("action"))
print(f"sweep base tick: pitch {P(r0):+.1f}, logged neck action {r0['action'][NK]:+.2f}")
for pitch in (0, 3, 6, 8, 10, 12, 14, 17, 20):
    g = np.array([math.sin(math.radians(pitch)), r0["gb"][1], -math.cos(math.radians(pitch))], np.float32)
    act1 = run(obs(r0, np.array(prev, np.float32), 0.0, g))
    a_ = np.array(prev, np.float32)
    for _ in range(25): a_ = run(obs(r0, a_, 0.0, g))
    print(f"  pitch {pitch:+3d}: neck action one tick {act1[NK]:+.2f}, after 25 frozen ticks {a_[NK]:+.2f}; max|a| {max(abs(a_)):.2f}")

print("\nblock attribution on the last rise: neck action with one block taken from the base tick")
a, b = rises[-1]
seq = [r for r in rows[a:b + 1] if r.get("action")]
base = obs(r0, np.array(prev, np.float32), 0.0)
sl = {"gyro": slice(0, 3), "grav": slice(3, 6), "qpos": slice(6, 20), "qvel": slice(20, 34), "last_act": slice(34, 48)}
NQ = 6 + NK; NV = 20 + NK; NA = 34 + NK
for i in range(1, len(seq)):
    r = seq[i]; t = r["t"] - rows[a]["t"]
    if t < 0.55: continue
    o = obs(r, np.array(seq[i - 1]["action"], np.float32), 0.0)
    line = f" +{t:.2f} pitch {P(r):+5.1f} neck q {r['q'][11]:+.2f} dq {r['dq'][11]:+.2f} last {seq[i-1]['action'][NK]:+.2f} -> act {run(o)[NK]:+.2f} |"
    for k, s in sl.items():
        o2 = o.copy(); o2[s] = base[s]; line += f" {k}:{run(o2)[NK]:+.2f}"
    for nm, idx in (("neck_q", NQ), ("neck_dq", NV), ("neck_last", NA)):
        o2 = o.copy(); o2[idx] = base[idx]; line += f" {nm}:{run(o2)[NK]:+.2f}"
    print(line)
