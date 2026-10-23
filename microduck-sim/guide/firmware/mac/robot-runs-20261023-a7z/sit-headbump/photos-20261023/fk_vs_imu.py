"""Trunk pitch from the leg joint readings (feet flat on a level floor, as-built model) against the logged IMU pitch.
Same comparison on sim tick logs gives the method's baseline (sim has no sensor offset and its feet are exactly modelled)."""
import json, math, sys, statistics as st
import numpy as np, mujoco
sys.path.insert(0, "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac")
import brain_sim_check as b
import evaluate_delay as ev
from static_gap import cfg, feet_flat_rot
import walk_brain as wb
m, d, c, names, bam = ev.load(cfg(0.09, model="asbuilt", kp=200, voltage=7.0))
trunk = m.body("trunk_base").id
def fk_pitch(q):
    pose = dict(zip(wb.NAMES, q))
    R = feet_flat_rot(m, d, names, pose)          # world rotation of the trunk with both soles flat
    x = R @ np.array([1.0, 0, 0])                  # trunk forward axis in world
    return math.degrees(math.atan2(-x[2], math.hypot(x[0], x[1])))  # + = nose down
P = lambda r: math.degrees(math.atan2(r["gb"][0], -r["gb"][2]))
def still(r): return max(abs(v) for v in r["gyro_body"]) < 0.15
def summarize(label, rows):
    rows = [r for r in rows if still(r)][::5]
    if not rows: print(label, "no still rows"); return
    fk = [fk_pitch(r["q"]) for r in rows]; imu = [P(r) for r in rows]
    diff = [i - f for i, f in zip(imu, fk)]
    print(f"{label:34s} n={len(rows):3d}  IMU pitch {st.median(imu):+5.1f}  joints-say {st.median(fk):+5.1f}  IMU minus joints {st.median(diff):+5.1f} (p10 {sorted(diff)[len(diff)//10]:+5.1f}, p90 {sorted(diff)[9*len(diff)//10]:+5.1f})")
def load(f): return [json.loads(l) for l in open(f) if l.startswith("{")]
for f in sys.argv[1:]:
    rows = load(f); t0 = rows[0]["t"]
    tag = f.split("/")[-1]
    summarize(tag + " stand (open loop)", [r for r in rows if r["mode"] == "stand"])
    summarize(tag + " walk zero (stand61)", [r for r in rows if r["mode"] == "walk" and not any(r.get("cmd", {}).get(k) for k in ("vx",))])
    rise_end = []
    for i, r in enumerate(rows):
        if r["mode"] == "sit" and r.get("cmd", {}).get("mode", "sit") != "sit": rise_end.append(r)
    summarize(tag + " sit rise (sitstand, standing part)", [r for r in rise_end if abs(r["q"][6]) < 0.3])
