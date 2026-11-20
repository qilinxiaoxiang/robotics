"""Baseline sit and stand-up without a dock: seated trunk pose (the dock frame origin), how far the tail moves in x/y/yaw
during the sit, the robot's collision geoms, and a keep-out height map of every leg/foot vertex and the non-backpack
trunk underside in the dock frame over stand, sit and stand-up. Writes checks/baseline.json and checks/keepout.npz."""
import json, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import simcore as S  # noqa: E402
import mujoco  # noqa: E402

CK = S.HERE / "checks"; CK.mkdir(exist_ok=True)
t0 = time.time()
rec = S.run(dock_boxes=None, sit_at=4.0, unsit_at=10.0, every=10, hull=False)
m = rec["m"]
T = np.array(rec["t"])
coll = []
for g in range(m.ngeom):
    if m.geom_contype[g] or m.geom_conaffinity[g]:
        coll.append(dict(name=m.geom(g).name, body=m.body(m.geom_bodyid[g]).name, type=int(m.geom_type[g]),
                         contype=int(m.geom_contype[g]), conaff=int(m.geom_conaffinity[g])))
# seated pose: mean trunk pose over 8.5..9.9 s (before the unsit at 10)
poses = []
for q in rec["qpos"]:
    p, R, _ = S.trunk_pose(m, q)
    poses.append((p, R))
yaw = np.array([np.arctan2(R[1, 0], R[0, 0]) for _, R in poses])
P = np.array([p for p, _ in poses])
seat = (T > 8.5) & (T < 9.9)
sx, sy, syaw = float(P[seat, 0].mean()), float(P[seat, 1].mean()), float(yaw[seat].mean())
DW = S.yaw_T(sx * 1000, sy * 1000, syaw)
# pad centre track in D
padc = np.array([-69.5, 0.0, -46.0]) / 1000.0
track = []
for (p, R), t in zip(poses, T):
    w = R @ padc + p
    dpt = S.to_D(w[None], DW)[0]
    track.append([round(float(t), 2), *[round(float(v), 2) for v in dpt], round(float(np.degrees(np.arctan2(R[1, 0], R[0, 0]) - syaw)), 2)])
# keep-out map: legs (all leg-chain mesh geoms) and trunk/head (minus the backpack v2 box) in D
legs = S.mesh_geoms(m, S.LEG_BODIES)
others = [g for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and g not in legs
          and m.geom(g).name != "bp_hull_geom"]
bp = S.backpack_verts_mm(); lo, hi = bp.min(0), bp.max(0)
xs = np.arange(-130, 80.1, 1.0); ys = np.arange(-60, 60.1, 1.0)
H = {k: np.full((len(xs), len(ys)), np.inf) for k in ("legs", "trunk")}
phase = {k: {} for k in ("stand", "sit", "seated", "standup")}
def ph(t):
    return "stand" if t < 4 else "sit" if t < 7 else "seated" if t < 10 else "standup"
PH = {p: {k: np.full((len(xs), len(ys)), np.inf) for k in ("legs", "trunk")} for p in ("stand", "sit", "seated", "standup")}
for q, t in zip(rec["qpos"][::2], T[::2]):
    p, R, d = S.trunk_pose(m, q)
    if t > 10.0 and np.degrees(np.arccos(np.clip(R[2, 2], -1, 1))) > 20:  # stand-up: stop at 20 deg tilt (it falls in this model)
        continue
    for k, gs in (("legs", legs), ("trunk", others)):
        w = S.world_pts(m, d, gs)
        if k == "trunk":  # drop the backpack (its own envelope, the rails are meant to touch it)
            loc = (w - p) @ R * 1000
            keep = ~np.all((loc > lo - 0.5) & (loc < hi + 0.5), axis=1)
            w = w[keep]
        D = S.to_D(w, DW)
        ix = np.round(D[:, 0] - xs[0]).astype(int); iy = np.round(D[:, 1] - ys[0]).astype(int)
        ok = (ix >= 0) & (ix < len(xs)) & (iy >= 0) & (iy < len(ys))
        np.minimum.at(H[k], (ix[ok], iy[ok]), D[ok, 2])
        np.minimum.at(PH[ph(t)][k], (ix[ok], iy[ok]), D[ok, 2])
np.savez(CK / "keepout.npz", xs=xs, ys=ys, legs=H["legs"], trunk=H["trunk"],
         **{f"{p}_{k}": PH[p][k] for p in PH for k in PH[p]})
# backpack lowest z in D over time, seated
out = dict(seat_pose_world=dict(x_m=sx, y_m=sy, yaw_rad=syaw), summary=rec["summary"], collision_geoms=coll,
           pad_centre_track_D=[r for r in track if r[0] % 0.5 < 0.03 or 4.8 < r[0] < 6.0 or 9.9 < r[0] < 11.5],
           wall_s=round(time.time() - t0, 1))
(CK / "baseline.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps({k: out[k] for k in ("seat_pose_world", "wall_s")}, default=str))
print("collision geoms:", [(c["name"], c["body"]) for c in coll])
for r in out["pad_centre_track_D"]:
    print(r)
