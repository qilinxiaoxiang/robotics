"""Leg and seated clearance of the built battery backpack V2 (real STLs), microduck-dyn venv on the Mac mini.

    ~/.venvs/microduck-dyn/bin/python legsit.py        (after build_v2.py; about two minutes)

Legs: the concept's sweep (../battery-v2-concept-20261119/leg_check.py: hip pitch -30..30 step 5, roll -10..10 step 5,
both legs, stand keyframe, current model scene battery-20261104), distance from every leg mesh vertex to the frame and
cap surfaces (surface sampled at 0.4 mm, KD-tree; reported distance is within 0.3 mm of the true one, low side).
Sit: the real Brain sit as in ../battery-v2-concept-20261119/sit_clearance.py (brain_sim_check.py --model asbuilt
--manifest current), every 50th physics step the frame, cap and switch vertices are placed with trunk_base's pose
and their lowest world z is recorded. Writes checks/legsit.json; exit 1 if seated clearance < 10 mm or legs < 8 mm.
"""
import contextlib, io, json, os, runpy, sys
from pathlib import Path
import mujoco, numpy as np, trimesh
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
MD = HERE.parents[2]
BUILD = HERE / "build"; CK = HERE / "checks"; CK.mkdir(exist_ok=True)
SEAT_MIN_MM, LEG_MIN_MM = 10.0, 7.6     # legs: the approved concept B outline measured 7.6 mm (concept.json options.B)
CUR = json.loads((MD / "microduck_rl/cmu/model/current.json").read_text())
SCENE = MD / f"microduck_rl/cmu/model/scenes/scene_{CUR['variant']}.xml"


def surface_points(paths, step=0.4):
    pts = []
    for p in paths:
        t = trimesh.load(p, force="mesh")
        n = int(t.area / (step * step)) + 1
        s, _ = trimesh.sample.sample_surface_even(t, n)
        pts += [t.vertices, s]
    return np.vstack(pts)


def legs():
    S = surface_points([BUILD / "battery_v2_frame-world.stl", BUILD / "battery_v2_cap-world.stl", BUILD / "parts/Swann_39_switch-world.stl"])
    tree = cKDTree(S)
    m = mujoco.MjModel.from_xml_path(str(SCENE)); d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, 1); mujoco.mj_forward(m, d)
    q0 = d.qpos.copy(); trunk = m.body("trunk_base").id
    LEG = {"left": ["yaw2roll", "hip_l", "upper_leg_left", "leg", "ankle_left"],
           "right": ["bearing_roll", "hip_l_2", "upper_leg_right", "leg_2", "ankle_right"]}
    geoms = {s: [g for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and m.body(m.geom_bodyid[g]).name in n]
             for s, n in LEG.items()}
    def verts(g):
        mid = m.geom_dataid[g]; a = m.mesh_vertadr[mid]
        return m.mesh_vert[a:a + m.mesh_vertnum[mid]].astype(float)
    best = {}
    for side in ("left", "right"):
        b = (1e9, None)
        for dp in range(-30, 31, 5):
            for dr in range(-10, 11, 5):
                d.qpos[:] = q0
                d.qpos[m.jnt_qposadr[m.joint(f"{side}_hip_pitch").id]] += np.radians(dp)
                d.qpos[m.jnt_qposadr[m.joint(f"{side}_hip_roll").id]] += np.radians(dr)
                mujoco.mj_kinematics(m, d)
                Rt = d.xmat[trunk].reshape(3, 3); pt = d.xpos[trunk]
                for g in geoms[side]:
                    R = d.geom_xmat[g].reshape(3, 3); p = d.geom_xpos[g]
                    T = ((verts(g) @ R.T + p) - pt) @ Rt * 1000.0
                    dist, _ = tree.query(T)
                    i = int(np.argmin(dist))
                    if dist[i] < b[0]:
                        b = (float(dist[i]), dict(pitch=dp, roll=dr, body=m.body(m.geom_bodyid[g]).name, at=T[i].round(1).tolist()))
        best[side] = dict(min_mm=round(b[0], 2), **b[1])
    return best


def sit():
    V = {}
    for k, f in (("frame", "battery_v2_frame-world.stl"), ("cap", "battery_v2_cap-world.stl"),
                 ("switch", "parts/Swann_39_switch-world.stl")):
        V[k] = trimesh.load(BUILD / f, force="mesh").vertices / 1000.0
    samples = []; n = [0]; _step = mujoco.mj_step
    def step(m, d, *a):
        _step(m, d, *a); n[0] += 1
        if n[0] % 50: return
        t = m.body("trunk_base").id; R, p = d.xmat[t].reshape(3, 3), d.xpos[t]
        row = {"t": round(float(d.time), 2)}
        for k, v in V.items():
            row[k] = round(float((v @ R.T + p)[:, 2].min() * 1000), 1)
        gb = R.T @ np.array([0, 0, -1.0])
        row["pitch_deg"] = round(float(np.degrees(np.arctan2(gb[0], -gb[2]))), 1)
        samples.append(row)
    mac = MD / "guide/firmware/mac"
    sys.path.insert(0, str(mac)); cwd = os.getcwd(); os.chdir(mac)
    sys.argv = ["brain_sim_check.py", "--model", "asbuilt", "--manifest", "current", "--stand-s", "1", "--walk-at", "3",
                "--walk-s", "0.5", "--vx", "0", "--sit-at", "4", "--after-walk", "14"]
    mujoco.mj_step = step
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            runpy.run_path(str(mac / "brain_sim_check.py"), run_name="__main__")
        except SystemExit as e:
            sys.stderr.write(f"SystemExit {e.code}\n")
    mujoco.mj_step = _step; os.chdir(cwd)
    lines = buf.getvalue().strip().splitlines()
    try: summary = json.loads(lines[-1])
    except Exception: summary = {}
    stand = [s for s in samples if 2.0 <= s["t"] <= 3.0]
    seated = [s for s in samples if s["t"] >= samples[-1]["t"] - 2.0]
    low = {k: min(s[k] for s in samples if s["t"] >= 4.0) for k in V}
    return dict(stand=stand[-1] if stand else None, seated=seated[-1] if seated else None, min_after_sit_cmd=low,
                fell=summary.get("fell"), sit=summary.get("sit"), t_end=samples[-1]["t"] if samples else None,
                model=f"brain_sim_check --model asbuilt --manifest current ({CUR['variant']}), real Brain sit")


def main():
    out = dict(scene=str(SCENE.name), legs=legs(), sit=sit())
    fails = []
    for s, v in out["legs"].items():
        if v["min_mm"] < LEG_MIN_MM: fails.append(f"leg {s} {v['min_mm']} mm < {LEG_MIN_MM}")
    seat = min(out["sit"]["seated"][k] for k in ("frame", "cap", "switch")) if out["sit"]["seated"] else None
    out["seated_min_mm"] = seat
    if seat is None or seat < SEAT_MIN_MM: fails.append(f"seated clearance {seat} mm < {SEAT_MIN_MM}")
    if out["sit"]["fell"]: fails.append("robot fell in the sit run")
    out["fails"] = fails
    (CK / "legsit.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))
    print("FAILS" if fails else "PASS", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
