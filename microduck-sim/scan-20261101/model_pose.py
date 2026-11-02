"""Pose the as-built sim model at the logged joint angles and write per-body surface points in the foot frame."""
import sys, os, json, numpy as np
S = sys.argv[1]
MAC = os.path.expanduser("~/code/robotics/microduck-sim/guide/firmware/mac")
sys.path.insert(0, MAC)
os.chdir(MAC)
import mujoco, trimesh
import target_ground as tg
from duck_kin import DuckKin

ID_NAMES = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "left_ankle", "left_knee", "left_hip_pitch",
            "left_hip_roll", "left_hip_yaw", "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
POSES = json.load(open(S + "/poses.json"))
G = tg.DuckGeometry()
m, d = G.m, G.d
print("names", G.names)
print("ngeom", m.ngeom)
seen = {}
for g in range(m.ngeom):
    b = m.body(m.geom_bodyid[g]).name
    t = m.geom_type[g]
    gn = m.geom(g).name
    mesh = m.mesh(m.geom_dataid[g]).name if t == mujoco.mjtGeom.mjGEOM_MESH else None
    seen.setdefault(b, []).append((gn, int(t), mesh, int(m.geom_group[g]), int(m.geom_contype[g])))
for b, v in seen.items():
    print(b, [(x[2] or x[0], x[3]) for x in v][:14])

res = {}
rng = np.random.default_rng(0)
for name, P in POSES.items():
    q = dict(zip(ID_NAMES, P["q"]))
    gb = P["gb"]
    G.place(q, gb)
    pts, lab, col, gc = [], [], [], []
    for g in range(m.ngeom):
        if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH or m.geom_group[g] > 2:
            continue
        mid = m.geom_dataid[g]
        va, na = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        fa, nf = m.mesh_faceadr[mid], m.mesh_facenum[mid]
        V = m.mesh_vert[va:va + na].copy()
        F = m.mesh_face[fa:fa + nf].copy()
        W = (d.geom_xmat[g].reshape(3, 3) @ V.T).T + d.geom_xpos[g]
        tm = trimesh.Trimesh(W, F, process=False)
        n = max(200, int(tm.area * 1e6 / 2.0))  # ~ one point per 2 mm^2
        p, _ = trimesh.sample.sample_surface(tm, n, seed=0)
        pts.append(p)
        lab += [m.geom_bodyid[g]] * len(p)
        gc += [m.geom(g).name.split("__")[-1]] * len(p)
    pts = np.vstack(pts)
    lab = np.array(lab)
    gc = np.array(gc)
    names = [m.body(i).name for i in range(m.nbody)]
    bodyx = {names[i]: (d.xpos[i].tolist(), d.xmat[i].tolist()) for i in range(m.nbody)}
    # camera chain (with and without the head gain and the bow correction)
    k = DuckKin()
    pc, Rc = k.camera_pose(q, gb)
    pc0, _ = k.camera_from_body(*k.camera_body_pose(q, gb))
    mouth = k.mouth_tip(q, gb)
    res[name] = dict(cam_kin=np.asarray(pc).tolist(), cam_kin_nobow=np.asarray(pc0).tolist(), cam_axis=np.asarray(Rc)[:, 0].tolist(), bow_dz=k.bow_dz(q),
                     mouth_kin=np.asarray(mouth).tolist(), mouth_mj=d.site_xpos[G.mouth].tolist(), cam_site_mj=d.site_xpos[G.site].tolist())
    np.savez(f"{S}/model_{name}.npz", pts=pts, lab=lab, names=np.array(names), gcolor=gc)
    print(name, "pts", len(pts), "z", pts[:, 2].min().round(4), pts[:, 2].max().round(4), "x", pts[:, 0].min().round(4), pts[:, 0].max().round(4), "y", pts[:, 1].min().round(4), pts[:, 1].max().round(4))
    print(" ", {k_: (np.round(v, 4).tolist() if isinstance(v, list) else v) for k_, v in res[name].items()})
    print(" body pts", {names[i]: int((lab == i).sum()) for i in np.unique(lab)})
json.dump(res, open(S + "/model_sites.json", "w"), indent=1)
# consistent with the MuJoCo-posed points (head gain 1), plus the foot tilt the logged joints imply
res2 = {}
for name, P in POSES.items():
    q = dict(zip(ID_NAMES, P["q"]))
    gb = P["gb"]
    G.place(q, gb)
    k = DuckKin()
    pc, Rc = k.camera_from_body(*k.camera_body_pose(q, gb))
    k1 = DuckKin()
    k1.head_gain = 1.0
    k1._key = None
    pc1, Rc1 = k1.camera_from_body(*k1.camera_body_pose(q, gb))
    pb, _ = k.camera_pose(q, gb)
    tilt = {}
    for b in ("ankle_left", "ankle_right"):
        # sole normal: the sole collision mesh's lowest face normal is body-fixed; use its qpos0-free measure below
        sid = [g for g in range(m.ngeom) if m.geom_bodyid[g] == m.body(b).id and m.geom_group[g] == 3][0]
        mid = m.geom_dataid[sid]
        va, na = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        V = (d.geom_xmat[sid].reshape(3, 3) @ m.mesh_vert[va:va + na].T).T + d.geom_xpos[sid]
        lo = V[V[:, 2] < np.quantile(V[:, 2], 0.5)]
        A = np.c_[lo[:, 0] - lo[:, 0].mean(), lo[:, 1] - lo[:, 1].mean(), np.ones(len(lo))]
        c, *_ = np.linalg.lstsq(A, lo[:, 2], rcond=None)
        tilt[b] = dict(pitch_deg=round(float(np.degrees(np.arctan(c[0]))), 2), roll_deg=round(float(np.degrees(np.arctan(c[1]))), 2),
                       toe_heel_z_mm=[round(float(V[:, 2].min() * 1000), 1)])
    res2[name] = dict(cam_gain1=np.asarray(pc1).tolist(), axis_gain1=np.asarray(Rc1)[:, 0].tolist(), cam_kin_nobow=np.asarray(pc).tolist(), cam_kin=np.asarray(pb).tolist(), foot_tilt_deg=tilt,
                      trunk_pitch_deg_from_gb=round(float(np.degrees(np.arcsin(gb[0]))), 2))
    print(name, json.dumps(res2[name])[:600])
json.dump(res2, open(S + "/model_sites2.json", "w"), indent=1)
