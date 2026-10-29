"""Render what the U20CAM sees from a posture, with a person stand-in, in the as-built MuJoCo model (one local process).

The model's `head_camera` camera (on jaw_soft, the Radxa site) is moved to the U20CAM mount of u20cam_mount.json
(duck_kin.DuckKin().cam_site, body frame) and given the pinhole vertical FOV that matches the fisheye's focal length
at the image centre (2 atan(180 / 359.5) = 53.2 deg; the real fisheye reaches 57.4 deg top to bottom, so the frame
edges here are 2 deg short of the real ones). The person is a stand-in: a box body, a sphere head whose centre is the
face height, two dark eye spheres 63 mm apart facing the robot, standing at the horizontal distance D along the
robot's forward axis. The robot is posed from a joint dict and the trunk gravity gb (feet flat for standing postures,
or a sim row's reached pose), rested on its lowest collision point.

  ~/.venvs/microduck-dyn/bin/python render_views.py scenes.json -> results/renders/<name>.png (camera view and a side view)
scenes.json: [{"name": .., "q": {14 joints} | "head": {..} (legs STAND), "gb": [3] (optional), "dist_m": D, "face_m": H}]
"""
import argparse
import json
import math
import os
import sys

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, MAC)
import sim_host_guard  # noqa: E402
sim_host_guard.one_sim_on_laptop("face-view render")
import brain_sim_check as bsc  # noqa: E402
import duck_kin  # noqa: E402
import facegeom as fg  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from walk_brain import STAND  # noqa: E402

MANIFEST = os.path.abspath(os.path.join(MAC, "..", "..", "..", "microduck_rl", "cmu", "model", "manifests", "plugged.json"))
W, H = 640, 360
OUT = os.path.join(HERE, "results", "renders")


def install_person_hook(dist, face_z):
    sys.path.insert(0, str(bsc.ev.MODEL_DIR.parents[3] / "cmu" / "model"))
    import visual
    orig = visual.apply_visual_to_spec

    def hooked(spec, *a, **kw):
        n = orig(spec, *a, **kw)
        body_h = max(0.2, face_z - 0.12)
        p = spec.worldbody.add_body(name="person", pos=[dist + 0.12, 0.0, 0.0])
        p.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.12, 0.22, body_h / 2], pos=[0, 0, body_h / 2],
                   rgba=[0.3, 0.4, 0.7, 1], contype=0, conaffinity=0, mass=0)
        p.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[0.11], pos=[0, 0, face_z], rgba=[0.9, 0.75, 0.6, 1],
                   contype=0, conaffinity=0, mass=0)
        for y in (-0.0315, 0.0315):  # eyes 63 mm apart on the face toward the robot (-x)
            p.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[0.012], pos=[-0.105, y, face_z + 0.02],
                       rgba=[0.05, 0.05, 0.05, 1], contype=0, conaffinity=0, mass=0)
        p.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.004, 0.02, 0.006], pos=[-0.108, 0.0, face_z - 0.045],
                   rgba=[0.6, 0.2, 0.2, 1], contype=0, conaffinity=0, mass=0)  # mouth
        for k in list(spec.keys):
            spec.delete(k)
        return n

    visual.apply_visual_to_spec = hooked
    return lambda: setattr(visual, "apply_visual_to_spec", orig)


def lowest_point(m, d):
    floor = m.geom("floor").id
    lo = 1e9
    for g in range(m.ngeom):
        if g == floor or m.body(m.geom_bodyid[g]).name == "person" or not (m.geom_contype[g] or m.geom_conaffinity[g]):
            continue
        if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
            mid = m.geom_dataid[g]
            v = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]]
            w = v @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]
            lo = min(lo, float(w[:, 2].min()))
        else:
            lo = min(lo, float(d.geom_xpos[g, 2] - m.geom_rbound[g]))
    return lo


def pose_robot(m, d, names, q, gb):
    R = duck_kin.trunk_rotation(gb) if gb is not None else bsc.feet_flat_rot(m, d, names, q)
    quat = np.zeros(4)
    mujoco.mju_mat2Quat(quat, np.asarray(R).ravel())
    bsc.setup(m, d, names, q, tuple(quat))
    d.qpos[0] = 0.0; d.qpos[2] = 0.5
    mujoco.mj_forward(m, d)
    d.qpos[2] -= lowest_point(m, d)
    mujoco.mj_forward(m, d)


def aim_camera(m, kin):
    cid = m.camera("head_camera").id
    s = kin.cam_site
    Rc = s["R"] @ kin._offset()
    Rm = np.column_stack([-Rc[:, 1], Rc[:, 2], -Rc[:, 0]])  # MuJoCo camera: x right, y up, looks along -z
    quat = np.zeros(4)
    mujoco.mju_mat2Quat(quat, Rm.ravel())
    m.cam_pos[cid] = s["p"] + Rc @ kin.shift
    m.cam_quat[cid] = quat
    m.cam_fovy[cid] = math.degrees(2 * math.atan((H / 2) / kin.K.fy))
    return cid


def render_scene(sc, kin):
    q = dict(STAND, **sc["head"]) if "head" in sc else dict(sc["q"])
    gb = tuple(sc["gb"]) if sc.get("gb") else None
    restore = install_person_hook(sc["dist_m"], sc["face_m"])
    try:
        c0 = bsc.cfg(0.09, model="asbuilt", kp=400, voltage=7.0)
        c0["mass_manifest"] = MANIFEST
        m, d, c, names, bam = bsc.ev.load(c0)
    finally:
        restore()
    pose_robot(m, d, names, q, gb)
    cid = aim_camera(m, kin)
    mujoco.mj_forward(m, d)
    r = mujoco.Renderer(m, height=H, width=W)
    r.update_scene(d, camera=cid)
    cam_img = r.render().copy()
    # side view: free camera looking at the robot and the person from the robot's left
    free = mujoco.MjvCamera()
    free.type = mujoco.mjtCamera.mjCAMERA_FREE
    mid = np.array([sc["dist_m"] / 2, 0.0, max(0.35, sc["face_m"] / 2)])
    free.lookat[:] = mid
    free.distance = max(1.2, 1.3 * (sc["dist_m"] + sc["face_m"]))
    free.azimuth, free.elevation = 90, -8
    r.update_scene(d, camera=free)
    side_img = r.render().copy()
    r.close()
    pos, R = kin.camera_pose(q, gb or duck_kin.UPRIGHT)
    f = fg.face_view(pos, R, sc["dist_m"], sc["face_m"])
    im = Image.fromarray(cam_img)
    dr = ImageDraw.Draw(im)
    txt = (f"{sc['name']}: camera z {pos[2]:.2f} m, elev {fg.elevation_deg(R):+.0f} deg; face {sc['face_m']} m at {sc['dist_m']} m -> "
           f"{'in frame' if f['inside'] else 'OUT of frame'}, IPD {f['ipd_px']} px, seen from {f['los_up_deg']} deg below")
    dr.rectangle([0, 0, W, 14], fill=(0, 0, 0))
    dr.text((3, 1), txt, fill=(255, 255, 255))
    if f["u"] is not None:
        dr.ellipse([f["u"] - 6, f["v"] - 6, f["u"] + 6, f["v"] + 6], outline=(255, 0, 0), width=2)
    os.makedirs(OUT, exist_ok=True)
    im.save(os.path.join(OUT, f"{sc['name']}_camera.png"))
    Image.fromarray(side_img).save(os.path.join(OUT, f"{sc['name']}_side.png"))
    print(txt)
    return dict(name=sc["name"], face=f, cam_z=round(float(pos[2]), 3), elev=round(fg.elevation_deg(R), 1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes")
    args = ap.parse_args()
    kin = duck_kin.DuckKin()
    rows = [render_scene(sc, kin) for sc in json.load(open(args.scenes))]
    with open(os.path.join(OUT, "renders.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
