"""Whole-robot COM of the loaded MuJoCo model in the trunk frame (held stand pose) vs the controller's estimate from
out/mass_report.json, and the pitch moment of the mixer's hover thrust set about the true COM."""
import json
import sys

import mujoco
import numpy as np

sys.argv = [sys.argv[0], "--scenario", "hover"] + sys.argv[1:]
import flight as F  # noqa: E402

for variant in ("nominal", "none"):
    c0 = F.cfg(0.09, model="asbuilt", kp=400, voltage=F.SERVO_V)
    c0["mass_manifest"] = str(F.H / "out" / f"manifest_pack_{variant}.json")
    c0["scene"] = str(F.H / "out" / "scene_flight.xml")
    m, d, c, names, bam = F.ev.load(c0)
    pose = dict(F.STAND_POSE)
    for side, sgn in (("left", +1), ("right", -1)):
        pose[f"{side}_ankle"] += sgn * np.radians(-4.0)
    p0 = np.array([pose[n] for n in names])
    Rt = F.feet_flat_rot(m, d, names, dict(zip(names, p0)))
    q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
    F.setup(m, d, names, dict(zip(names, p0)), q)
    mujoco.mj_forward(m, d)
    tb = m.body("trunk_base").id
    R = d.xmat[tb].reshape(3, 3)
    com_t = R.T @ (d.subtree_com[tb] - d.xpos[tb])
    print(variant, "mass_kg", round(float(m.body_mass[1:].sum()), 4), "true COM trunk frame mm", np.round(com_t * 1000, 1))
    if variant == "nominal":
        rep = json.loads((F.H / "out" / "mass_report.json").read_text())["duck_with_pack"]
        est = np.array(rep["com_trunk_mm"]) / 1000
        W = float(m.body_mass[1:].sum()) * F.G
        ctl = F.Controller(rep["mass_g"] / 1000, [1, 1, 1], est)
        T = ctl.Binv @ np.array([W, 0, 0, 0])
        Mtrue = np.zeros(3)
        for i, f in enumerate(F.FANS):
            Mtrue += np.cross(f["p"] - com_t, T[i] * f["a"])
        print("estimate COM mm", np.round(est * 1000, 1), "error mm", np.round((com_t - est) * 1000, 1),
              "hover thrust set N", np.round(T, 3), "moment about true COM N m (roll, pitch, yaw)", np.round(Mtrue, 4),
              "pitch moment of 1 mm x error", round(W * 0.001, 4))
