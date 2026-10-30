"""Closed-loop bend calibration data: Pollen's ground-pick policy descends to each commanded phase and holds it.
Every new camera frame during the whole sequence is saved with the joint state nearest its capture time, so the
holds give static bend-pose points on the ruler and the transitions give the timing data. Ends with phase 1.0
(rise); walk_wired then hands back to stand61 by itself. Runs on the A7Z."""
import json, os, sys, time
sys.path.insert(0, os.path.expanduser("~/rt/microduck-sim/guide/firmware/mac"))
import cv2
import numpy as np
import a7z_cam, duck_kin, cam_calib
from approach import LogTail, find_log

PHASES = [float(a) for a in sys.argv[1:]] or [0.12, 0.20, 0.28, 0.33]
HOLD_S = 4.0
os.makedirs("/tmp/gp", exist_ok=True)
kin = duck_kin.DuckKin()
tail = LogTail(find_log())
t0 = time.time()
while tail.latest() is None and time.time() - t0 < 5:
    time.sleep(0.1)
rows, last_idx = [], None


def send(cmd):
    tmp = "/tmp/duck_cmd.json.gp.tmp"
    json.dump(cmd, open(tmp, "w"))
    os.replace(tmp, "/tmp/duck_cmd.json")


def record(until, phase):
    global last_idx
    while time.time() < until:
        fr = a7z_cam.read_frame()
        if fr is None or fr[2] == last_idx:
            time.sleep(0.02)
            continue
        last_idx = fr[2]
        st = tail.at(fr[1]) or tail.latest()
        if st is None:
            time.sleep(0.05)
            continue
        img = np.frombuffer(fr[0], np.uint8).reshape(a7z_cam.H, a7z_cam.W, 3).copy()
        name = f"f{fr[2]:06d}"
        cv2.imwrite(f"/tmp/gp/{name}.png", img)
        q, gb = dict(st["q"]), list(st["gb"])
        rows.append(dict(name=name, cmd_phase=phase, t_cap=fr[1], t_state=st["t"], q=q, gb=gb))
    st = tail.latest(); q, gb = dict(st["q"]), st["gb"]
    tx = cam_calib.toe_x(kin, q, gb)
    bottom = kin.pixel_to_ground(320, 359, q, gb, 640, 360)
    tilt = float(np.degrees(np.arccos(-gb[2])))
    print(f"phase {phase:.2f} held: neck {q['neck_pitch']:+.3f} head {q['head_pitch']:.3f} trunk tilt {tilt:.1f} deg | "
          f"model bottom {None if bottom is None else round((bottom[0] - tx) * 100, 1)} cm in front of the toes | frames {len(rows)}", flush=True)


for p in PHASES:
    send({"mode": "groundpick", "phase": p})
    record(time.time() + 3.0 + HOLD_S, p)
send({"mode": "groundpick", "phase": 1.0})
record(time.time() + 6.0, 1.0)
json.dump(rows, open("/tmp/gp/rows.json", "w"))
st = tail.latest()
print("end: gb", [round(x, 3) for x in st["gb"]], "cmd", open("/tmp/duck_cmd.json").read(), flush=True)
