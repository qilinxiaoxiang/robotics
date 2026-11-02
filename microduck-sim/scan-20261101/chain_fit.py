"""Which joint or trunk offsets explain the head pose the scans give? Least squares in the foot frame (feet located by their own fits)."""
import sys, os, json, numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
S = sys.argv[1]
MAC = os.path.expanduser("~/code/robotics/microduck-sim/guide/firmware/mac"); sys.path.insert(0, MAC); os.chdir(MAC)
import target_ground as tg
ID = ["right_ankle","right_knee","right_hip_pitch","right_hip_roll","right_hip_yaw","left_ankle","left_knee","left_hip_pitch","left_hip_roll","left_hip_yaw","head_pitch","neck_pitch","head_yaw","head_roll"]
POS = json.load(open(S + "/poses.json")); REP = json.load(open(S + "/color_fit2.json"))
G = tg.DuckGeometry(); m, d = G.m, G.d; hb = m.body("jaw_soft").id; tb = m.body("trunk_base").id
def pose(name, dt=0.0, dn=0.0, dh=0.0):
    q = dict(zip(ID, POS[name]["q"])); q["neck_pitch"] += dn; q["head_pitch"] += dh
    gb = np.array(POS[name]["gb"], float)
    a = np.radians(dt)                     # trunk pitched a further forward: body gravity turns about body y
    gb = np.array([gb[0]*np.cos(a) - gb[2]*np.sin(a), gb[1], gb[0]*np.sin(a) + gb[2]*np.cos(a)])
    G.place(q, gb)
    return d.xpos[hb].copy(), d.xmat[hb].reshape(3,3).copy(), d.xpos[tb].copy(), d.xmat[tb].reshape(3,3).copy()
tgt = {}
for name in POS:
    r = REP[name]; H0 = pose(name)
    Rf, tf = np.array(r["head"]["R"]), np.array(r["head"]["t"])
    # feet: mean planar shift of the two soles, so the head is measured relative to the feet (z stays on the floor)
    fs = (np.array(r["foot_l"]["centre_shift_mm"]) + np.array(r["foot_r"]["centre_shift_mm"])) / 2000
    fs[2] = 0
    tgt[name] = dict(p=Rf @ H0[0] + tf - fs, R=Rf @ H0[1], foot_shift=(fs*1000).round(1).tolist())
    print(name, "foot planar shift mm", tgt[name]["foot_shift"], "head origin real-minus-chain mm (foot-referenced)", np.round((tgt[name]["p"] - H0[0])*1000, 1), "rot deg", np.round(Rot.from_matrix(tgt[name]["R"] @ H0[1].T).as_rotvec(degrees=True), 1))
    Rt = np.array(r["trunk"]["R"]); print("   trunk rot deg", np.round(r["trunk"]["rot_deg"],1), "+-", np.round(r["trunk"]["rot_std"],1), "cost", round(r["trunk"]["cost"],2), "near", r["trunk"]["near"])
def resid(x, on):
    v = dict(zip(on, x)); out = []
    for name in POS:
        p, R, _, _ = pose(name, v.get("dt",0), np.radians(v.get("dn",0)) * 1, np.radians(v.get("dh",0)))
        if "dn_stand" in v and name == "stand": pass
        out += list((p - tgt[name]["p"]) * 1000) + list(Rot.from_matrix(tgt[name]["R"] @ R.T).as_rotvec(degrees=True) * 1.7)
    return np.array(out)
for on in ([], ["dt"], ["dn"], ["dh"], ["dn","dh"], ["dt","dn"], ["dt","dh"], ["dt","dn","dh"]):
    if on:
        s = least_squares(resid, np.zeros(len(on)), args=(on,), diff_step=0.02, x_scale=3.0)
        x, r = s.x, s.fun
    else:
        x, r = [], resid([], [])
    r2 = r.reshape(2,6)
    print(on or "none", np.round(x,2).tolist(), "| rms", round(float(np.sqrt((r**2).mean())),2), "| stand pos mm", np.round(r2[0,:3],1), "rot deg", np.round(r2[0,3:]/1.7,1), "| bend pos mm", np.round(r2[1,:3],1), "rot deg", np.round(r2[1,3:]/1.7,1))
