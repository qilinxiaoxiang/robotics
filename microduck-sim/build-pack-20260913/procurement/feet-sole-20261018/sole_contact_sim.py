"""Where does the sole touch the floor while walking (sim)? Patches mj_step in brain_sim_check, records contacts on the foot collision geoms."""
import os, sys, json
MAC = "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac"
sys.path.insert(0, MAC)
import numpy as np
import mujoco
import brain_sim_check as bsc

OUT = sys.argv.pop(1)
rows = []
state = {}
step0 = mujoco.mj_step

def setup(m, d):
    gids = [i for i in range(m.ngeom) if m.geom(i).name and "foot" in m.geom(i).name and "coll" in m.geom(i).name]
    if not gids:  # fall back: geoms with mesh named sole*
        gids = [i for i in range(m.ngeom) if m.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH and "sole" in m.mesh(m.geom_dataid[i]).name]
    state["gids"] = gids
    state["names"] = [m.geom(i).name or m.mesh(m.geom_dataid[i]).name for i in gids]
    print("sole geoms", state["names"], file=sys.stderr)

def verts_body(m, g):
    mid = m.geom_dataid[g]
    v = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]]
    R = np.zeros(9); mujoco.mju_quat2Mat(R, m.geom_quat[g]); R = R.reshape(3, 3)
    return v @ R.T + m.geom_pos[g]

def body_pose(d, b):
    return d.xpos[b].copy(), d.xmat[b].reshape(3, 3).copy()

def mj_step(m, d):
    if "gids" not in state:
        setup(m, d)
    step0(m, d)
    t = d.time
    if "plane" not in state and t >= 3.5:  # standing, settled: flat patch = verts within 0.3 mm of floor
        planes = []
        for g in state["gids"]:
            b = m.geom_bodyid[g]
            p, R = body_pose(d, b)
            vb = verts_body(m, g)
            vw = vb @ R.T + p
            z0 = vw[:, 2].min()
            flat = vb[vw[:, 2] < z0 + 0.0003]
            n_world = np.array([0, 0, 1.0]); n_body = R.T @ n_world
            off = flat @ n_body  # plane: n_body . x = off.mean()
            # in-plane axes in body frame
            a1 = np.cross(n_body, [1, 0, 0]); a1 = a1 if np.linalg.norm(a1) > 0.1 else np.cross(n_body, [0, 1, 0]); a1 /= np.linalg.norm(a1)
            a2 = np.cross(n_body, a1)
            hgt = vb @ n_body - off.mean()
            planes.append(dict(n=n_body, off=off.mean(), a1=a1, a2=a2,
                               flat_box=[(flat @ a1).min(), (flat @ a1).max(), (flat @ a2).min(), (flat @ a2).max()],
                               all_box=[(vb @ a1).min(), (vb @ a1).max(), (vb @ a2).min(), (vb @ a2).max()],
                               nflat=len(flat), hmax=hgt.max(), z0=z0,
                               # edge profile: height of the lowest vertex vs distance beyond the flat box along a1 / a2
                               verts=vb))
        state["plane"] = planes
    if "plane" in state and int(round(t / m.opt.timestep)) % 2 == 0:
        for i in range(d.ncon):
            c = d.contact[i]
            for k, g in enumerate(state["gids"]):
                if c.geom1 == g or c.geom2 == g:
                    pl = state["plane"][k]
                    b = m.geom_bodyid[g]
                    p, R = body_pose(d, b)
                    xb = R.T @ (c.pos - p)
                    nz = (R @ pl["n"])[2]
                    rows.append(dict(t=round(t, 4), foot=k, h_mm=1000 * (xb @ pl["n"] - pl["off"]),
                                     u=1000 * xb @ pl["a1"], v=1000 * xb @ pl["a2"], dist=c.dist,
                                     tilt_deg=float(np.degrees(np.arccos(np.clip(-nz if nz < 0 else nz, -1, 1))))))

bsc.mujoco.mj_step = mj_step

import atexit
def dump():
    pl = state.get("plane", [])
    meta = [dict(name=state["names"][k], flat_box_mm=[1000 * x for x in p["flat_box"]], all_box_mm=[1000 * x for x in p["all_box"]],
                 nflat=p["nflat"], hmax_mm=1000 * p["hmax"]) for k, p in enumerate(pl)]
    prof = []
    for k, p in enumerate(pl):
        vb = p["verts"]; h = 1000 * (vb @ p["n"] - p["off"]); u = 1000 * vb @ p["a1"]; v = 1000 * vb @ p["a2"]
        prof.append(dict(u=u.tolist(), v=v.tolist(), h=h.tolist()))
    json.dump(dict(meta=meta, rows=rows, prof=prof), open(OUT, "w"))
atexit.register(dump)
bsc.main()
