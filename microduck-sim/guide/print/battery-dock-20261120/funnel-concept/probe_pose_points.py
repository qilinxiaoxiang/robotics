"""Robot points in the dock frame for the concept sheet: seated (t 8.5), standing (t 3), and the leg envelope over the
stand, sit and rise (trunk to 100 mm), from the nominal datum+rails case. Writes checks/pose_points.npz."""
import json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import simcore as S, concept as C
import mujoco
P = dict(rear=True, bias=3.0, leaf_dx=2.5, rails=True, c=3.0, z_v=13.0, z_top=26.0, slope_deg=55.0, x0=-92.0, x1=-50.0, w=2.5)
seat = json.loads((S.HERE / "checks/baseline.json").read_text())["seat_pose_world"]
rec = S.run(dock_boxes=C.dock_geometry(P), seat_pose=(seat["x_m"], seat["y_m"], seat["yaw_rad"]), offset=(0, 0, 0),
            sit_at=4.0, unsit_at=9.0, seed=0)
m, DW = rec["m"], rec["DW"]
legs = S.mesh_geoms(m, S.LEG_BODIES)
others = [g for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and g not in legs
          and not m.geom(g).name.startswith("bp_hull") and m.geom_bodyid[g] != 0]
T = np.array(rec["t"])
out = {}
def pts(i, gs, step=3):
    p, R, d = S.trunk_pose(m, rec["qpos"][i])
    return S.to_D(S.world_pts(m, d, gs)[::step], DW), p, R
for nm, want in (("stand", 3.0), ("seated", 8.5)):
    i = int(np.argmin(np.abs(T - want)))
    out[nm + "_legs"], p, R = pts(i, legs)
    out[nm + "_body"], _, _ = pts(i, others)
    bp = S.backpack_verts_mm() / 1000.0
    out[nm + "_backpack"] = S.to_D(bp @ R.T + p, DW)
    pads = S.pad_verts_mm()
    out[nm + "_pads"] = np.vstack([S.to_D((v / 1000.0) @ R.T + p, DW) for v in pads.values()])
env = []
risen = None
for i, t in enumerate(T):
    if i % 3: continue
    p, R, d = S.trunk_pose(m, rec["qpos"][i])
    if t >= 9.0 and p[2] > 0.100: break
    env.append(S.to_D(S.world_pts(m, d, legs)[::6], DW))
out["leg_envelope"] = np.vstack(env)
np.savez_compressed(S.HERE / "checks/pose_points.npz", **out)
print({k: v.shape for k, v in out.items()})
