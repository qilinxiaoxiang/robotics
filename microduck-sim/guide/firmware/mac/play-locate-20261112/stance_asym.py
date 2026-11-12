#!/usr/bin/env python3
"""Mac mini: did one leg joint shift against its encoder, and when?

Standing still on both feet the left and right leg are mirror images: in the model q_left = -q_right for every joint
(sim stand row). A horn that slipped on its shaft, a bracket that moved or a bent part shows as a constant left-right
difference in the encoders while the robot stands level, appearing on the day it happened. Per log, in time order:
quiet-stand ticks (torque on, zero command, |gyro| < 0.05 rad/s, encoders still), median of q_left + q_right per joint
in degrees, the IMU pitch and roll, and the walking gait's left/right swing lengths.

  python3 stance_asym.py
"""
import glob
import os
import time

import numpy as np

CACHE = os.path.expanduser("~/sims/fall-onset-20261112/cache")
J = ("ankle", "knee", "hip_pitch", "hip_roll", "hip_yaw")   # servo IDs 1-5 right, 6-10 left


def main():
    print("log                when         n_quiet | q_left + q_right, deg: ankle  knee  hipP  hipR  hipY | IMU pitch roll |"
          " right q: ankle knee hipP | left q: ankle knee hipP | cur mA R ank knee hipP | L ank knee hipP")
    for f in sorted(glob.glob(os.path.join(CACHE, "duck_wired_log_*.npz")), key=lambda p: np.load(p)["t"][0] if len(np.load(p)["t"]) else 0):
        L = dict(np.load(f))
        t = L["t"]
        if len(t) < 500:
            continue
        g = L["gb"] / np.maximum(np.linalg.norm(L["gb"], axis=1, keepdims=True), 1e-9)
        pitch = np.degrees(np.arctan2(-g[:, 0], -g[:, 2]))
        roll = np.degrees(np.arctan2(g[:, 1], -g[:, 2]))
        tilt = np.degrees(np.arccos(np.clip(-g[:, 2], -1, 1)))
        gy = np.linalg.norm(L["gyro"], axis=1)
        still = np.r_[True, np.max(np.abs(np.diff(L["pos"][:, :10], axis=0)), axis=1) <= 2]
        quiet = (L["torque"] > 0) & ((L["mode"] == 2) | (L["mode"] == 1)) & (np.abs(L["vx"]) < 1e-3) & (np.abs(L["vth"]) < 1e-3) \
            & (gy < 0.05) & still & (tilt < 12) & np.isfinite(L["q"][:, :10]).all(axis=1) & (np.nan_to_num(L["hold_s"], nan=1.0) > 0.99) \
            & (L["policy"] > 0)
        # by half-day blocks inside a long log, so a shift inside one log shows
        idx = np.where(quiet)[0]
        if len(idx) < 100:
            continue
        blocks = np.array_split(idx, max(1, int((t[idx[-1]] - t[idx[0]]) // 1200) + 1))
        for b in blocks:
            if len(b) < 100:
                continue
            q = np.degrees(L["q"][b, :10])
            asym = np.median(q[:, 5:10] + q[:, 0:5], axis=0)
            qr, ql = np.median(q[:, 0:5], axis=0), np.median(q[:, 5:10], axis=0)
            cur = np.nanmedian(L["cur"][b, :10], axis=0)
            print(f"{os.path.basename(f)[15:-4]:18s} {time.strftime('%m-%d %H:%M', time.localtime(t[b[0]]))} {len(b):7d} |"
                  + "                        " + " ".join(f"{a:5.1f}" for a in asym)
                  + f" | {np.median(pitch[b]):9.1f} {np.median(roll[b]):4.1f} |          "
                  + " ".join(f"{a:5.1f}" for a in qr[:3]) + " |        " + " ".join(f"{a:5.1f}" for a in ql[:3])
                  + " |         " + " ".join(f"{a:5.0f}" for a in cur[:3]) + " |  " + " ".join(f"{a:5.0f}" for a in cur[5:8]))


if __name__ == "__main__":
    main()
