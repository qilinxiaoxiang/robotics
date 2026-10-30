"""Mount fit from the far tile captures plus the ruler ticks read in the head-down frames (ruler 0 at the toe-line
midpoint, along the centre line). Writes the merged capture file for cam_calib.py --mount --from."""
import json, os, sys
MAC = "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac"
sys.path.insert(0, MAC)
import numpy as np
import duck_kin, cam_calib

HERE = os.path.dirname(os.path.abspath(__file__))
R = 0.006   # the far captures' ball radius; the fitter adds it along the ground ray, so a ruler tick (the floor point itself) stores true x + R
# frame -> {cm: picture row of the labelled tick}, read from the 5x gridded crops
TICKS = {
    "h1.29_0": {15: 235, 14: 262, 13: 288, 12: 314, 11: 341},
    "h1.22_0": {16: 251, 15: 273, 14: 296, 13: 321, 12: 346},
    "h1.09_0": {20: 250, 19: 267, 18: 287, 17: 307, 16: 326, 15: 347},
    "h0.96_0": {30.48: 176},     # the far end of the 12-inch ruler
    "manual": {18: 112, 17: 138, 16: 157, 15: 182, 14: 204, 12: 256, 11: 281, 10: 312},   # head 1.319, the controller's limit
}
RULER_Y = -0.022   # the ruler's centre line sits 2.2 cm right of the foot-frame x axis (constant y residual of the far fit)
shots = {s["name"]: s for s in json.load(open(f"{HERE}/ruler/shots.json"))}
ms = json.load(open(f"{HERE}/ruler/manual_state.json")); shots["manual"] = dict(name="manual", t=0.0, **ms)
edges = json.load(open(f"{HERE}/ruler/edges.json"))
import cv2
im = cv2.imread(f"{HERE}/ruler/manual.png"); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
mk = cv2.inRange(hsv, (0, 90, 60), (12, 255, 255)) | cv2.inRange(hsv, (165, 90, 60), (180, 255, 255))
mk = cv2.morphologyEx(mk, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
edges["manual"] = {str(y): (int(np.nonzero(mk[y])[0].min()), int(np.nonzero(mk[y])[0].max())) for y in range(360) if (mk[y] > 0).sum() > 30}
far = json.load(open(f"{MAC}/camera-calib-20261030/u20cam-mount-1030-merged6.json"))
rows = []
for name, ticks in TICKS.items():
    s = shots[name]
    for cm, v in ticks.items():
        e = edges[name].get(str(v)) or edges[name][min(edges[name], key=lambda k: abs(int(k) - v))]
        u = 0.5 * (e[0] + e[1])
        rows.append(dict(point=f"ruler_{cm}cm_{name}", x=s["toe_x"] + cm / 100 + R, y=RULER_Y, u=float(u), v=float(v),
                         w=640, h=360, area=0, t=s["t"], q=s["q"], gb=s["gb"], holdout=False, ruler=True))
print(len(rows), "ruler rows;", len(far["obs"]), "far rows")
out = dict(far, obs=far["obs"] + rows, ruler_note="ruler rows: x stored = true x + 0.006 (the fitter pushes the pixel 0.006 further out, as for a ball bottom)",
           head={"head_pitch": "0.8 far / 0.96-1.29 ruler", "head_yaw": 0.0})
path = f"{MAC}/camera-calib-20261030/u20cam-mount-1030-far+ruler.json"
json.dump(out, open(path, "w"))
print("wrote", path)

def show(res, tag):
    print(f"\n{tag}: pitch {res['pitch']:.2f} yaw {res['yaw']:.2f} roll {res['roll']:.2f} shift_m {np.round(res['shift_m'], 4).tolist()} "
          f"kept {res['shift_kept']} rms {res['rms_mm']:.1f} mm")
    for k, e in sorted(res["residual_mm"].items(), key=lambda kv: kv[0]):
        print(f"   {k:26s} {e[0]:+6.1f} {e[1]:+6.1f} mm")

for fs in (False, True):
    kin = duck_kin.DuckKin(); kin.set_mount_offsets(0, 0, 0)
    obs = [dict(o) for o in out["obs"]]
    show(cam_calib.fit_mount(kin, obs, radius=R, fit_shift=fs), f"fit_shift={fs}")
# ruler-only check of the current (rotation-only, far) fit
kin = duck_kin.DuckKin()
print("\ncurrent mount file on the ruler ticks (model - true, mm):")
for o in rows:
    pos, Rm = kin.camera_pose(o["q"], o["gb"])
    c = cam_calib.object_centre(kin, o["u"], o["v"], pos, Rm, 640, 360, R)
    print(f"   {o['point']:26s} {1000*(c[0]-o['x']-R):+6.1f} {1000*(c[1]-o['y']):+6.1f}")
