"""Where the legs are after the stand-up from the dock (concept A, offset 0): per leg body, its D-frame extent at chosen
times, and the closest leg point to the rails; plus the same stand-up without rails (base only) and with no dock."""
import json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import simcore as S, concept as C, grid as G
seat = json.loads((S.HERE / "checks/baseline.json").read_text())["seat_pose_world"]
out = {}
for name, boxes in (("A", C.concept_geometry(G.A_PARAMS)), ("base", C.base_boxes())):
    rec = S.run(dock_boxes=boxes, seat_pose=(seat["x_m"], seat["y_m"], seat["yaw_rad"]), offset=(0, 0, 0), sit_at=4.0,
                unsit_at=9.0, seed=0)
    m, DW = rec["m"], rec["DW"]
    rails = [b for b in boxes if b["name"].startswith("rail")]
    res = {"summary_fell_at": rec["summary"].get("fell_at"), "sit": rec["summary"].get("sit"), "t": {}}
    for want in (3.0, 8.5, 9.3, 9.6, 10.0, 12.0, 14.5):
        i = int(np.argmin(np.abs(np.array(rec["t"]) - want)))
        p, R, d = S.trunk_pose(m, rec["qpos"][i])
        row = {"trunk_D": [round(float(v), 1) for v in S.to_D(p[None], DW)[0]],
               "tilt": round(math.degrees(math.acos(min(1, R[2, 2]))), 1)}
        for b in S.LEG_BODIES:
            g = S.mesh_geoms(m, [b])
            if not g: continue
            P = S.to_D(S.world_pts(m, d, g), DW)
            row[b] = [P.min(0).round(1).tolist(), P.max(0).round(1).tolist()]
            if rails:
                dd = np.min([C.box_sdf(P, rb) for rb in rails], axis=0)
                k = int(np.argmin(dd))
                row[b] += [round(float(dd[k]), 2), P[k].round(1).tolist()]
        res["t"][str(want)] = row
    out[name] = res
(S.HERE / "checks/standup_probe.json").write_text(json.dumps(out, indent=1, default=str))
for n, r in out.items():
    print("==", n, r["summary_fell_at"], (r["sit"] or {}).get("done"))
    for t, row in r["t"].items():
        print(t, row["trunk_D"], row["tilt"])
        for b in S.LEG_BODIES:
            if b in row and len(row[b]) > 2 and row[b][2] < 5:
                print("    ", b, row[b])
