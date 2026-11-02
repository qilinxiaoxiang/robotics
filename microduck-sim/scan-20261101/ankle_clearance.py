"""Clearance between foot and shin meshes of the as-built model as the ankle closes, knee and hip fixed, foot free of the floor.

    ~/.venvs/microduck-dyn/bin/python ankle_clearance.py

Answers whether the CAD geometry itself stops the ankle near the 1.25 rad the robot holds in the bend.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "guide", "firmware", "mac"))
import mujoco  # noqa: E402
import trimesh  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
import target_ground as tg  # noqa: E402

G = tg.DuckGeometry()
m, d = G.m, G.d


def body_meshes(body):
    out = []
    for g in range(m.ngeom):
        if m.geom_bodyid[g] == body and m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and m.geom_group[g] <= 2:
            mid = m.geom_dataid[g]
            va, na = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
            fa, nf = m.mesh_faceadr[mid], m.mesh_facenum[mid]
            out.append((g, m.mesh_vert[va:va + na].copy(), m.mesh_face[fa:fa + nf].copy(), m.geom(g).name))
    return out


def world(g, V):
    return V @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]


for side, sgn in (("left", 1.0), ("right", -1.0)):
    jid = m.joint(f"{side}_ankle").id
    foot = m.jnt_bodyid[jid]
    chain = []
    p = m.body_parentid[foot]
    while p > 0 and len(chain) < 2:   # the shin and the body above it
        chain.append(p)
        p = m.body_parentid[p]
    print(side, "foot body", m.body(foot).name, "above", [m.body(b).name for b in chain], "range", m.jnt_range[jid])
    foot_m = body_meshes(foot)
    others = [x for b in chain for x in body_meshes(b)]
    print("  foot geoms", [x[3] for x in foot_m], "shin geoms", [x[3] for x in others][:6])
    for q in (1.0, 1.1, 1.2, 1.25, 1.3, 1.35, 1.4, 1.5, 1.57):
        for dirn in (sgn,):
            d.qpos[:] = m.qpos0
            d.qpos[m.jnt_qposadr[jid]] = q * dirn
            mujoco.mj_kinematics(m, d)
            pivot = d.xanchor[jid].copy()
            axis = d.xaxis[jid].copy()
            best = 1e9
            for g, V, F, fname in foot_m:
                Pf = trimesh.sample.sample_surface(trimesh.Trimesh(world(g, V), F, process=False), 4000, seed=1)[0]
                # the horn and its screw circle turn about the axis inside the servo: not a stop
                r = Pf - pivot
                radial = np.linalg.norm(r - np.outer(r @ axis, axis), axis=1)
                Pf = Pf[radial > 0.016]
                if not len(Pf):
                    continue
                for go, Vo, Fo, nm in others:
                    Ps = trimesh.sample.sample_surface(trimesh.Trimesh(world(go, Vo), Fo, process=False), 4000, seed=2)[0]
                    dist, _ = cKDTree(Ps).query(Pf)
                    if dist.min() < best:
                        best, who = float(dist.min()), f"{fname} / {nm}"
            print(f"  ankle {q * dirn:+.2f}: nearest surface beyond 16 mm of the axis {best * 1000:.1f} mm ({who})")
