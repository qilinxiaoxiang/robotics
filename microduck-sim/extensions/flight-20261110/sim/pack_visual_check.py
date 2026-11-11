"""Check the drawn flight pack: physics identical with and without visual_parts, and stills of the stand pose.

  $PY sim/pack_visual_check.py [--variant nominal] [--out sim/out/pack_visual]
1. loads the duck through evaluate_delay.load with sim/out/manifest_pack_<variant>.json and with its visual copy
   (sim/out/visual/), compares every mass, inertia, COM and collision array, then steps both 2 s from the stand pose
   with the servos holding it and compares qpos and qvel bit for bit;
2. renders the stand pose from the side, the front-left and above (<out>/stand_<view>.png);
3. reports the lowest fan-intake normal z (should be near cos 6 deg, intake up) and the smallest distance between the
   pack's visual vertices and the head bodies' visual geoms at the stand pose (> 0 = no overlap of bounding boxes).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import flight as F  # noqa: E402  (paths, cfg, evaluate_delay)
import mujoco  # noqa: E402
import pack_visual  # noqa: E402

ARRAYS = ["body_mass", "body_inertia", "body_ipos", "body_iquat", "geom_contype", "geom_conaffinity", "geom_size",
          "body_bvhnum", "bvh_aabb", "nbody", "njnt", "nu"]


def build(manifest):
    c = F.cfg(0.09, model="asbuilt", kp=400, voltage=F.SERVO_V)
    c["mass_manifest"] = str(manifest)
    return F.ev.load(c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="nominal")
    ap.add_argument("--out", default=str(H / "out" / "pack_visual"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    base = H / "out" / f"manifest_pack_{a.variant}.json"
    vis = pack_visual.with_visuals(base)
    m0, d0, c0, names, _ = build(base)
    m1, d1, c1, _, _ = build(vis)
    rep = dict(manifest=str(base), visual=str(vis), ngeom=[m0.ngeom, m1.ngeom], nmesh=[m0.nmesh, m1.nmesh])
    collide0 = [i for i in range(m0.ngeom) if m0.geom_contype[i] or m0.geom_conaffinity[i]]
    collide1 = [i for i in range(m1.ngeom) if m1.geom_contype[i] or m1.geom_conaffinity[i]]
    rep["colliding_geoms"] = [len(collide0), len(collide1)]
    rep["total_mass_g"] = [round(float(m0.body_mass.sum()) * 1000, 4), round(float(m1.body_mass.sum()) * 1000, 4)]
    diffs = {}
    for k in ARRAYS:
        x, y = getattr(m0, k), getattr(m1, k)
        if k.startswith("geom_"):
            x, y = np.asarray(x)[collide0], np.asarray(y)[collide1]
        same = np.array_equal(np.asarray(x), np.asarray(y))
        if not same:
            diffs[k] = "differs"
    rep["model_arrays_equal"] = not diffs
    rep["model_array_diffs"] = diffs
    # 2 s with the servos holding the stand pose (same controller call as the flight sim's idle phase)
    for m, d, c in ((m0, d0, c0), (m1, d1, c1)):
        d.qpos[:7] = [0, 0, 0.12, 1, 0, 0, 0]
        ji = np.array([m.actuator(n).trnid[0] for n in names]); qa = m.jnt_qposadr[ji]
        d.qpos[qa] = F.ev.HOME
        mujoco.mj_forward(m, d)
        c.q_target = d.qpos[qa].copy()
        for _ in range(800):
            c.update()
            mujoco.mj_step(m, d)
    rep["qpos_bit_identical_after_2s"] = bool(np.array_equal(d0.qpos, d1.qpos))
    rep["qvel_bit_identical_after_2s"] = bool(np.array_equal(d0.qvel, d1.qvel))
    rep["qpos_max_abs_diff"] = float(np.abs(d0.qpos - d1.qpos).max())
    # stills of the stand pose with the pack
    d = mujoco.MjData(m1)
    d.qpos[:7] = [0, 0, 0.12, 1, 0, 0, 0]
    ji = np.array([m1.actuator(n).trnid[0] for n in names]); d.qpos[m1.jnt_qposadr[ji]] = F.ev.HOME
    mujoco.mj_forward(m1, d)
    import imageio
    r = mujoco.Renderer(m1, 720, 960)
    cam = mujoco.MjvCamera(); cam.lookat[:] = d.xpos[m1.body("trunk_base").id] + [0, 0, 0.03]
    for view, (az, el, dist) in dict(side=(90, -8, 0.75), front_left=(135, -20, 0.8), above=(180, -60, 0.8), rear=(-30, -20, 0.8)).items():
        cam.azimuth, cam.elevation, cam.distance = az, el, dist
        r.update_scene(d, cam); imageio.imwrite(str(out / f"stand_{view}.png"), r.render())
    # fan intake direction and head clearance
    pack = [i for i in range(m1.ngeom) if m1.geom(i).name.startswith("payload_")]
    fans = [i for i in pack if "fan" in m1.geom(i).name]
    up = []
    for g in fans:
        mid = m1.geom_dataid[g]
        v = m1.mesh_vert[m1.mesh_vertadr[mid]:m1.mesh_vertadr[mid] + m1.mesh_vertnum[mid]]
        R = d.geom_xmat[g].reshape(3, 3); w = v @ R.T + d.geom_xpos[g]
        # the fan's long axis (largest principal direction) points from exhaust to intake; intake = the higher end
        c = w.mean(0); u = np.linalg.svd(w - c)[2][0]
        up.append(round(float(abs(u[2])), 3))
    rep["fan_axis_vertical_component"] = up
    head = [i for i in range(m1.ngeom) if m1.body(m1.geom_bodyid[i]).name in ("neck", "neck_pitch", "yaw_roll_motion",
                                                                                "bearing_roll", "jaw_soft")
            and m1.geom_contype[i] == 0 and m1.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH]
    def verts(g):
        mid = m1.geom_dataid[g]
        v = m1.mesh_vert[m1.mesh_vertadr[mid]:m1.mesh_vertadr[mid] + m1.mesh_vertnum[mid]]
        return v @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]
    if head:
        from scipy.spatial import cKDTree
        hv = np.vstack([verts(g) for g in head]); tree = cKDTree(hv)
        dmin = min(float(tree.query(verts(g))[0].min()) for g in pack)
        rep["pack_to_head_min_vertex_distance_mm"] = round(dmin * 1000, 1)
        rep["head_bodies"] = sorted({m1.body(m1.geom_bodyid[i]).name for i in head})
    (out / "check.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
