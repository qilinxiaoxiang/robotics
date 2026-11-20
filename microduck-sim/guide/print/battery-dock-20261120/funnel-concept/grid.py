"""Run a grid of dock sit cases on the Mac mini, in parallel, one fresh process per case.

    $DYN grid.py <plan name>      plans are defined in PLANS below; results checks/<plan>.jsonl, heartbeat
                                  checks/<plan>.status.json (stage, counts, last update, DONE/FAILED)

Each case: the real Brain sit (simcore.run: teleop sit_stand case, --volt 7.6 --drop 0.036, seed), sit at 4 s, stand-up
command at 9 s. The dock (released base as boxes, plus the concept's rails when concept = "A") is placed at the baseline
seated pose (checks/baseline.json) moved by the start offset. Pass = both pads over their own leaves with the margins in
concept.pad_check, no fall before the stand-up command, and no robot part other than the backpack within 0 mm of a
rail at any time in stand, sit or the stand-up (until 20 deg of tilt: the stand-up itself falls in this model with or
without a dock, checks/hull_effect.json).
"""
import itertools, json, math, multiprocessing as mp, os, sys, time, traceback
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
CK = HERE / "checks"

STANDUP_TILT_CUT = 15.0   # deg: past this the sim stand-up is falling (it falls without a dock too)
A_PARAMS = dict(c=1.5, z_v=14.0, z_top=34.0, slope_deg=45.0, x0=-78.0, x1=-50.0, w=3.0, rear_ramp=False)


def plan(name):
    Y = [-15, -12, -9, -6, -3, 0, 3, 6, 9, 12, 15]
    X = [-8, -6, -4, -2, 0, 2, 4, 6]
    W = [-15, -10, -5, 0, 5, 10, 15]
    cases = []
    if name == "axes":
        for concept in ("none", "A"):
            for seed in (0, 1):
                for y in Y: cases.append(dict(concept=concept, off=(0, y, 0), seed=seed))
                for x in X:
                    if x: cases.append(dict(concept=concept, off=(x, 0, 0), seed=seed))
                for w in W:
                    if w: cases.append(dict(concept=concept, off=(0, 0, w), seed=seed))
    elif name == "smoke":
        cases = [dict(concept="none", off=(0, 0, 0), seed=0), dict(concept="A", off=(0, 0, 0), seed=0),
                 dict(concept="A", off=(0, 8, 0), seed=0), dict(concept="none", off=(0, 8, 0), seed=0)]
    elif name.startswith("custom:"):
        cases = json.loads(Path(name.split(":", 1)[1]).read_text())
    else:
        cases = json.loads((HERE / f"plans/{name}.json").read_text())
    for c in cases:
        if "params" not in c:
            c["params"] = dict(A_PARAMS, rails=True) if c["concept"] == "A" else {}
    return cases


def one(case):
    import simcore as S
    import concept as C
    import mujoco
    t0 = time.time()
    seat = json.loads((CK / "baseline.json").read_text())["seat_pose_world"]
    prm = dict(case.get("params") or {})
    if case["concept"] == "A" and "rails" not in prm:
        prm["rails"] = True
    boxes = C.dock_geometry(prm)
    leaf_dx = prm.get("bias", 0.0) + prm.get("leaf_dx", 0.0)
    rec = S.run(dock_boxes=boxes, seat_pose=(seat["x_m"], seat["y_m"], seat["yaw_rad"]), offset=tuple(case["off"]),
                mu_rail=case.get("mu_rail", 0.35), floor_mu=case.get("floor_mu", 1.0), sit_at=4.0, unsit_at=9.0,
                every=10, seed=case["seed"])
    m, DW = rec["m"], rec["DW"]
    T = np.array(rec["t"])
    pads = S.pad_verts_mm()
    trunk = m.body("trunk_base").id
    legs = S.mesh_geoms(m, S.LEG_BODIES)
    bp = S.backpack_verts_mm(); lo, hi = bp.min(0), bp.max(0)
    others = [g for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and g not in legs
              and not m.geom(g).name.startswith("bp_hull") and m.geom_bodyid[g] != 0]
    seated = None
    clear = {p: {"rails_legs": 1e9, "rails_trunk": 1e9, "base_legs": 1e9} for p in ("stand", "sit", "rise", "after")}
    risen = [None]
    where = {}
    series = []
    for i, (t, q) in enumerate(zip(T, rec["qpos"])):
        dense = 4.7 < t < 6.2 or 8.95 < t < 10.5
        if not dense and i % 5:
            continue
        p, R, d = S.trunk_pose(m, q)
        tilt = math.degrees(math.acos(max(-1, min(1, R[2, 2]))))
        if t >= 9.0 and tilt > STANDUP_TILT_CUT:
            continue
        if t >= 9.0 and risen[0] is None and p[2] > 0.100:
            risen[0] = round(float(t), 2)
        ph = "stand" if t < 4.8 else "sit" if t < 9.0 else "rise" if risen[0] is None else "after"
        if 8.3 <= t <= 8.95:
            seated = (t, q)
        Lw = S.to_D(S.world_pts(m, d, legs)[::2], DW)
        Ow = S.world_pts(m, d, others)
        loc = (Ow - p) @ R * 1000
        Ow = Ow[~np.all((loc > lo - 0.5) & (loc < hi + 0.5), axis=1)][::2]
        Ow = S.to_D(Ow, DW)
        rl = 1e9
        for b in boxes:
            israil = b["name"].startswith("rail")
            dl = float(C.box_sdf(Lw, b).min())
            key = "rails_legs" if israil else "base_legs"
            if israil:
                rl = min(rl, dl)
            if dl < clear[ph][key]:
                clear[ph][key] = dl; where[(ph, key)] = (round(float(t), 2), b["name"])
            if israil:
                do = float(C.box_sdf(Ow, b).min())
                if do < clear[ph]["rails_trunk"]:
                    clear[ph]["rails_trunk"] = do; where[(ph, "rails_trunk")] = (round(float(t), 2), b["name"])
        if ph in ("rise", "after") or 5.2 < t < 5.8:
            series.append((round(float(t), 2), round(tilt, 1), round(rl, 2), round(float(p[2]) * 1000, 1)))
    out = dict(case=case, series=series)
    if seated is None:
        out.update(error="no seated sample")
        return out
    p, R, d = S.trunk_pose(m, seated[1])
    padsD = {k: S.to_D((v / 1000.0) @ R.T + p, DW) for k, v in pads.items()}
    pad_ok, pad = C.pad_check(padsD, leaf_dx=leaf_dx)
    padc = S.to_D(((np.array([-69.5, 0, -46.0]) / 1000) @ R.T + p)[None], DW)[0]
    yaw_rel = math.degrees(math.atan2(R[1, 0], R[0, 0]) - math.atan2(DW[1, 0], DW[0, 0]))
    sm = rec["summary"]
    fell_at = sm.get("fell_at")
    fell = fell_at is not None and fell_at < 9.0
    touched = {(c[0] or c[1]) for cs, t in zip(rec["contacts"], T) if 4.0 < t < 9.0 for c in cs}
    # pass: no rail contact in stand, sit and the rise (to trunk 100 mm); the steps after the rise are reported only
    rail_leg_ok = all(clear[ph]["rails_legs"] > 0 and clear[ph]["rails_trunk"] > 0 for ph in ("stand", "sit", "rise"))
    out.update(pass_=bool(pad_ok and not fell and rail_leg_ok), pad_ok=pad_ok, fell_before_unsit=fell, fell_at=fell_at,
               rail_clear_ok=rail_leg_ok, pads=pad,
               seated_pad_centre_D=[round(float(v), 2) for v in padc], seated_yaw_rel_deg=round(yaw_rel, 2),
               clearance_mm={ph: {k: round(v, 2) for k, v in c.items()} for ph, c in clear.items()},
               clearance_where={f"{a}/{b}": v for (a, b), v in where.items()},
               robot_geoms_touching_dock_in_sit=sorted(touched),
               seated_tilt=sm.get("sit", {}).get("seated_tilt"), risen_at=risen[0], wall_s=round(time.time() - t0, 1))
    return out


def worker(case):
    sys.path.insert(0, str(HERE))
    try:
        return one(case)
    except Exception:
        return dict(case=case, error=traceback.format_exc()[-1500:])


def main():
    name = sys.argv[1]
    cases = plan(name)
    res_p = CK / f"{name.replace('/', '_').replace(':', '_')}.jsonl"
    st_p = CK / f"{name.replace('/', '_').replace(':', '_')}.status.json"
    t0 = time.time()
    def status(stage, done, extra=None):
        st_p.write_text(json.dumps(dict(plan=name, stage=stage, cases=len(cases), done=done, started=t0,
                                        updated=time.time(), wall_s=round(time.time() - t0, 1), **(extra or {}))))
    status("running", 0)
    n = 0
    try:
        with open(res_p, "w") as f, mp.get_context("spawn").Pool(int(os.environ.get("WORKERS", 7)), maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(worker, cases):
                f.write(json.dumps(r, default=str) + "\n"); f.flush()
                n += 1
                status("running", n)
        status("DONE", n)
    except Exception:
        status("FAILED", n, dict(error=traceback.format_exc()[-1500:]))
        raise


if __name__ == "__main__":
    main()
