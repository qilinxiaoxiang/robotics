"""Which leg part reaches the rails at the end of the stand-up, and where (dock frame), for one params set."""
import json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import simcore as S, concept as C
P = json.loads(sys.argv[1]); seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
seat = json.loads((S.HERE / "checks/baseline.json").read_text())["seat_pose_world"]
boxes = C.dock_geometry(P)
rec = S.run(dock_boxes=boxes, seat_pose=(seat["x_m"], seat["y_m"], seat["yaw_rad"]), offset=(0, 0, 0), sit_at=4.0,
            unsit_at=9.0, seed=seed)
m, DW = rec["m"], rec["DW"]
rails = [b for b in boxes if b["name"].startswith("rail")]
T = np.array(rec["t"])
env = {b: [] for b in S.LEG_BODIES}
for i, t in enumerate(T):
    if not 9.0 <= t <= 10.2: continue
    p, R, d = S.trunk_pose(m, rec["qpos"][i])
    for b in S.LEG_BODIES:
        g = S.mesh_geoms(m, [b])
        Pd = S.to_D(S.world_pts(m, d, g)[::2], DW)
        dd = np.min([C.box_sdf(Pd, rb) for rb in rails], axis=0)
        k = int(np.argmin(dd))
        env[b].append(Pd)
        if dd[k] < 1.0:
            print(round(t, 2), "trunk z", round(p[2] * 1000, 1), b, round(float(dd[k]), 2), Pd[k].round(1).tolist())
allp = np.vstack([np.vstack(v) for v in env.values()])
lowp = allp[allp[:, 2] < 30]
print("legs below z 30 during 9.0-10.2 s: x", lowp[:, 0].min().round(1), "..", lowp[:, 0].max().round(1))
for yb in ((20, 45), (-45, -20)):
    s = lowp[(lowp[:, 1] > yb[0]) & (lowp[:, 1] < yb[1])]
    if len(s): print("  y", yb, "x min", s[:, 0].min().round(1), "z min at that", s[np.argmin(s[:, 0]), 2].round(1))
