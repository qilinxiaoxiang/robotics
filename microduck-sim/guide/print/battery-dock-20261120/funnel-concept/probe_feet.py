"""Where the feet are (sole collision geoms, dock frame D) standing, seated and early in the stand-up, and whether they
slide during the sit; baseline run without a dock. Writes checks/feet.json."""
import json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import simcore as S
import mujoco
b = json.loads((S.HERE / "checks/baseline.json").read_text())["seat_pose_world"]
DW = S.yaw_T(b["x_m"] * 1000, b["y_m"] * 1000, b["yaw_rad"])
rec = S.run(dock_boxes=None, sit_at=4.0, unsit_at=9.0, hull=False)
m = rec["m"]
out = {"timestep": float(m.opt.timestep), "rows": []}
for t, q in zip(rec["t"], rec["qpos"]):
    if not (abs(t % 0.25) < 0.011 or 4.8 < t < 6.0 or 9.0 < t < 10.0):
        continue
    p, R, d = S.trunk_pose(m, q)
    row = {"t": round(t, 2), "tilt": round(math.degrees(math.acos(min(1, R[2, 2]))), 1)}
    for g in ("left_foot_collision", "right_foot_collision"):
        gid = m.geom(g).id
        c = S.to_D(d.geom_xpos[gid][None], DW)[0]
        row[g[:5]] = [round(float(v), 1) for v in c]
        if m.geom_type[gid] == mujoco.mjtGeom.mjGEOM_BOX:
            row[g[:5] + "_size"] = [round(float(v) * 1000, 1) for v in m.geom_size[gid]]
    out["rows"].append(row)
out["foot_type"] = int(m.geom_type[m.geom("left_foot_collision").id])
(S.HERE / "checks/feet.json").write_text(json.dumps(out, indent=1))
for r in out["rows"]:
    print(r)
