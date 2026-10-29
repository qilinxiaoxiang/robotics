"""Acceptance for the loader refit (seconds, no stepping): on every manifest the baselines use, after evaluate_delay.load
no colliding body's geometry reaches outside its collision box, and a second refit changes nothing.

  nice -n 19 ~/.venvs/microduck-dyn/bin/python check_loader_refit.py      # exit 0 and one line per manifest
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
WHOLE = os.path.join(MAC, "..", "..", "..", "hardware-design-20260912", "whole-robot-20260912")
for p in (os.path.join(WHOLE, "delay-repair-20260912"), os.path.join(WHOLE, "dynamics", "realgap-20261014"), MAC):
    sys.path.insert(0, p)
import mujoco  # noqa: E402
import evaluate_delay as ev  # noqa: E402
from static_gap import cfg  # noqa: E402

SIM = os.path.normpath(os.path.join(MAC, "..", "..", ".."))
MANIFESTS = {"asbuilt": None, "saddle": os.path.join(SIM, "guide/print/a7z-saddle/balance/manifest-saddle.json"),
             "plugged": os.path.join(SIM, "microduck_rl/cmu/model/manifests/plugged.json")}


def outside_mm(m):
    """Largest distance (mm) by which any colliding geom's AABB corner lies outside its body's root box."""
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    worst = 0.0
    for g in range(m.ngeom):
        b = m.geom_bodyid[g]
        if b == 0 or not (m.geom_contype[g] or m.geom_conaffinity[g]) or m.body_bvhadr[b] < 0:
            continue
        box = m.bvh_aabb[m.body_bvhadr[b]]
        R, p = d.ximat[b].reshape(3, 3), d.xipos[b]
        Rg, cg, a = d.geom_xmat[g].reshape(3, 3), d.geom_xpos[g], m.geom_aabb[g]
        for s in np.array(np.meshgrid([-1, 1], [-1, 1], [-1, 1])).T.reshape(-1, 3):
            q = R.T @ (cg + Rg @ (a[:3] + s * a[3:]) - p)
            worst = max(worst, float(np.max(np.abs(q - box[:3]) - box[3:])))
    return worst * 1000


ok = True
for name, man in MANIFESTS.items():
    c0 = cfg(0.09, model="asbuilt", kp=200, voltage=7.0)
    if man:
        c0["mass_manifest"] = man
    m = ev.load(c0)[0]
    out = outside_mm(m)
    again = ev.refit_body_bvh(m)
    good = out <= 0.0 and again == {}
    ok &= good
    print(f"{name}: geometry outside its box {max(out, 0):.2f} mm, second refit changes {sorted(again) or 'nothing'}: {'OK' if good else 'FAIL'}")
sys.exit(0 if ok else 1)
