"""Fit the neck-chain / camera parameters of duck_kin on the bend data (bend_ticks.json) together with the standing
captures (u20cam-mount-1030-far+ruler+bend.json without its by-eye bend rows), compare parameter sets by held-out
error per bend phase, check the standing fit stays within tolerance, and write bend_fit.json.

Model (BendKin, a DuckKin whose place() takes extra parameters; duck_kin.py itself is not edited):
  pitch, yaw, roll   camera offsets in deg (the mount file's offsets_deg are the start)
  sx, sy, sz         lens shift in the camera frame, mm (optical axis, image left, image up)
  px, py, pz         neck pivot offset: translation of the `neck` body (the neck_pitch axis) in the trunk frame, mm
  neck0, head0       joint zero offsets added to the measured neck_pitch / head_pitch readings, deg
  imu_p, imu_r       IMU pitch / roll bias: gb is turned by these before trunk_rotation, deg
  imu_y              IMU yaw misalignment about the trunk z axis, deg: invisible when the trunk is level, it turns a
                     trunk pitch of p into a false roll p sin(imu_y) in the bow
  ruler_yaw, ruler_dy  nuisance terms of the bend run only: the ruler's scale edge is y = -0.0093 + ruler_dy/1000 +
                     tan(ruler_yaw) (x - toe_x) (the robot may have shifted or turned a little during the bow)
head_pitch_gain stays the mount file's 0.92 and multiplies the MEASURED reading (duck_kin.place: ang = q - qpos0,
ang *= head_gain), so this fit, which feeds measured q, uses it as the robot does.

Observations and residuals (m, on the floor):
  tick   bend tick with a read cm: the pixel ray's hit on the board top (z = 1.6 mm) minus (toe_x + cm/100, y_edge(x))
  edge   the detected scale-edge column at rows 30, 90, .. 330 of every bend frame (no tick identity needed): the
         ray's hit minus y_edge(x) in y only (x residual 0)
  stand  standing capture: cam_calib.object_centre with radius 0.006 minus the stored (x, y), the convention of the
         existing fit (ruler rows store true x + 0.006)
Every labelled point weighs the same whatever its frame count (1/sqrt(n) per row); bend ticks times --wbend, edge
rows times --wedge.

usage: python bendfit.py [--wbend 1.0] [--wedge 1.0] [--models base,shift,pivot,...] [--out bend_fit.json]
"""
import argparse
import datetime
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, MAC)
import cam_calib  # noqa: E402
import duck_kin  # noqa: E402
from duck_kin import _rx, _ry, _rz, axis_angle, trunk_rotation  # noqa: E402

BOARD = 0.0016
Y_EDGE = -0.0093
R_STAND = 0.006
EDGE_ROWS = (30, 90, 150, 210, 270, 330)
STANDING = os.path.join(MAC, "camera-calib-20261030", "u20cam-mount-1030-far+ruler+bend.json")
PARAMS = ["pitch", "yaw", "roll", "sx", "sy", "sz", "px", "py", "pz", "neck0", "head0", "imu_p", "imu_r", "imu_y",
          "ruler_yaw", "ruler_dy"]
STEP = dict(pitch=0.01, yaw=0.01, roll=0.01, sx=0.1, sy=0.1, sz=0.1, px=0.1, py=0.1, pz=0.1, neck0=0.01, head0=0.01,
            imu_p=0.01, imu_r=0.01, imu_y=0.01, ruler_yaw=0.01, ruler_dy=0.1)
B = ["pitch", "yaw", "roll"]
MODELS = {
    "base": B,
    "shift": B + ["sx", "sy", "sz"],
    "pivot": B + ["px", "pz"],
    "pivot3": B + ["px", "py", "pz"],
    "zeros": B + ["neck0", "head0"],
    "imu": B + ["imu_p", "imu_r"],
    "imuy": B + ["imu_y"],
    "pivot+imuy": B + ["px", "pz", "imu_y"],
    "pivot3+imuy": B + ["px", "py", "pz", "imu_y"],
    "pivot+ryaw": B + ["px", "pz", "ruler_yaw", "ruler_dy"],
    "pivot+imuy+ryaw": B + ["px", "pz", "imu_y", "ruler_yaw", "ruler_dy"],
    "pivot+shift": B + ["sx", "sz", "px", "pz"],
    "pivot+imuy+shift": B + ["sx", "sy", "sz", "px", "pz", "imu_y"],
    "pivot+imuy+neck0": B + ["px", "pz", "imu_y", "neck0"],
    "pivot+imuy+imu": B + ["px", "pz", "imu_y", "imu_p", "imu_r"],
}


class BendKin(duck_kin.DuckKin):
    def __init__(self):
        super().__init__()
        self.neck_body = self.body_names.index("neck")
        self.p = dict((k, 0.0) for k in PARAMS)
        self.p.update(pitch=self.offsets[0], yaw=self.offsets[1], roll=self.offsets[2],
                      sx=self.shift[0] * 1000, sy=self.shift[1] * 1000, sz=self.shift[2] * 1000)
        self._leg_key2 = None

    def set_params(self, p):
        self.p.update(p)
        self.set_mount_offsets(self.p["pitch"], self.p["yaw"], self.p["roll"],
                               (self.p["sx"] / 1000, self.p["sy"] / 1000, self.p["sz"] / 1000))

    def gb_corrected(self, gb):
        g = np.asarray(gb, float)
        return _rz(math.radians(self.p["imu_y"])) @ _ry(math.radians(self.p["imu_p"])) @ _rx(math.radians(self.p["imu_r"])) @ g

    def place(self, q, gb=duck_kin.UPRIGHT):
        g = self.gb_corrected(gb)
        pivot = np.array([self.p["px"], self.p["py"], self.p["pz"]]) / 1000.0
        Rs, ps = [], []
        for i, b in enumerate(self.bodies):
            if b["parent"] < 0:
                R, p = trunk_rotation(g), np.zeros(3)
            else:
                Rp, pp = Rs[b["parent"]], ps[b["parent"]]
                p0 = b["p0"] + (pivot if i == self.neck_body else 0.0)
                R, p = Rp @ b["R0"], pp + Rp @ p0
                for j in b["joints"]:
                    ang = float(q[j["name"]]) - j["qpos0"]
                    if j["name"] == "head_pitch":
                        ang = ang * self.head_gain + math.radians(self.p["head0"])
                    elif j["name"] == "neck_pitch":
                        ang += math.radians(self.p["neck0"])
                    Rj = axis_angle(j["axis"], ang)
                    p = p + R @ (j["pos"] - Rj @ j["pos"])
                    R = R @ Rj
            Rs.append(R)
            ps.append(p)
        leg_key = (tuple(round(float(q[n]), 6) for n in self.names if "hip" in n or "knee" in n or "ankle" in n),
                   tuple(np.round(g, 6)))
        if leg_key != self._leg_key2:
            self._leg_key2 = leg_key
            self._zmin2 = min(float(((f["v"] @ f["R"].T + f["p"]) @ Rs[f["body"]].T + ps[f["body"]])[:, 2].min())
                              for f in self.feet)
        ps = [p - np.array([0.0, 0.0, self._zmin2]) for p in ps]
        return Rs, ps

    def toe_x(self, q, gb):
        """cam_calib.toe_x cached on the leg joints and the corrected gravity (the feet do not move with the
        camera parameters)."""
        key = (tuple(round(float(q[n]), 6) for n in self.names if "hip" in n or "knee" in n or "ankle" in n),
               tuple(np.round(self.gb_corrected(gb), 6)))
        cache = getattr(self, "_toe_cache", None)
        if cache is None:
            cache = self._toe_cache = {}
        if key not in cache:
            cache[key] = cam_calib.toe_x(self, q, gb)
        return cache[key]

    def y_edge(self, x, toe_x):
        return Y_EDGE + self.p["ruler_dy"] / 1000.0 + math.tan(math.radians(self.p["ruler_yaw"])) * (x - toe_x)


def load_obs(wbend, wedge):
    bend = json.load(open(os.path.join(HERE, "bend_ticks.json")))
    stand = json.load(open(STANDING))
    rows = {r["name"]: r for r in json.load(open(os.path.join(HERE, "rows_matched.json")))}
    obs = []
    for o in stand["obs"]:
        if o["point"].startswith("bend_"):
            continue   # the by-eye rows of the earlier fit; replaced by bend_ticks.json
        obs.append(dict(kind="stand", point=o["point"], u=o["u"], v=o["v"], w=o["w"], h=o["h"], q=o["q"], gb=o["gb"],
                        x=o["x"], y=o["y"], holdout=bool(o.get("holdout")), phase=None, wmul=1.0))
    for o in bend["obs"]:
        if o["cm"] is None:
            continue
        obs.append(dict(kind="tick", point=f"tick_p{o['phase']:.2f}_{o['cm']}cm", u=o["u"], v=o["v"], w=640, h=360,
                        q=o["q"], gb=o["gb"], cm=o["cm"], holdout=False, phase=o["phase"], frame=o["frame"], wmul=wbend))
    for name, d in bend["detail"].items():
        r = rows[name]
        for v in EDGE_ROWS:
            if str(v) in d["edge"]:
                obs.append(dict(kind="edge", point=f"edge_p{r['cmd_phase']:.2f}_r{v}", u=d["edge"][str(v)], v=float(v),
                                w=640, h=360, q=r["q"], gb=r["gb"], holdout=False, phase=r["cmd_phase"], frame=name,
                                wmul=wedge))
    return obs, bend


def predict_row(kin, o):
    pos, R = kin.camera_pose(o["q"], o["gb"])
    if o["kind"] == "stand":
        c = cam_calib.object_centre(kin, o["u"], o["v"], pos, R, o["w"], o["h"], R_STAND)
        return None if c is None else (c[0] - o["x"], c[1] - o["y"])
    xy = kin.pixel_to_ground_pose(o["u"], o["v"], pos, R, o["w"], o["h"], z=BOARD)
    if xy is None:
        return None
    tx = kin.toe_x(o["q"], o["gb"])
    ye = kin.y_edge(xy[0], tx)
    if o["kind"] == "tick":
        return xy[0] - (tx + o["cm"] / 100.0), xy[1] - ye
    return 0.0, xy[1] - ye


def residuals(kin, obs):
    return [predict_row(kin, o) for o in obs]


def group_means(obs, res):
    g = {}
    for o, r in zip(obs, res):
        g.setdefault(o["point"], []).append((np.nan, np.nan) if r is None else r)
    return {k: (float(np.nanmean([e[0] for e in v]) * 1000), float(np.nanmean([e[1] for e in v]) * 1000))
            for k, v in g.items()}


def fit(kin, obs, names, iters=40):
    """Levenberg-Marquardt over the parameters `names` (others fixed at kin.p). Returns p, std (dicts), group means."""
    count = {}
    for o in obs:
        count[o["point"]] = count.get(o["point"], 0) + 1
    wts = np.array([o["wmul"] / math.sqrt(count[o["point"]]) for o in obs])
    p = np.array([kin.p[n] for n in names], float)

    def resid(pv):
        kin.set_params(dict(zip(names, pv)))
        out = []
        for o, r, wt in zip(obs, residuals(kin, obs), wts):
            out += [0.5, 0.5] if r is None else [wt * r[0], wt * r[1]]
        return np.array(out)

    r = resid(p)
    lam = 1e-3
    J = None
    for _ in range(iters):
        J = np.empty((len(r), len(names)))
        for k, n in enumerate(names):
            dp = np.zeros(len(names))
            dp[k] = STEP[n]
            J[:, k] = (resid(p + dp) - r) / STEP[n]
        A, g = J.T @ J, J.T @ r
        improved = False
        while lam < 1e9:
            step = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-12), g)
            rn = resid(p + step)
            if rn @ rn < r @ r:
                p, r, lam, improved = p + step, rn, max(lam / 3, 1e-9), True
                break
            lam *= 4
        if not improved or np.max(np.abs(step)) < 1e-5:
            break
    kin.set_params(dict(zip(names, p)))
    means = group_means(obs, residuals(kin, obs))
    npt = len(count)
    dof = max(1, 2 * npt - len(names))
    s2 = sum(m[0] ** 2 + m[1] ** 2 for m in means.values() if not np.isnan(m[0])) / 1e6 / dof
    Jp = J / np.repeat(wts, 2)[:, None]
    rows = {}
    for i, o in enumerate(obs):
        rows.setdefault(o["point"], []).append(Jp[2 * i:2 * i + 2])
    Jm = np.concatenate([np.mean(v, axis=0) for v in rows.values()])
    try:
        cov = np.linalg.inv(Jm.T @ Jm) * s2
        std = np.sqrt(np.abs(np.diag(cov)))
    except np.linalg.LinAlgError:
        std = np.full(len(names), np.inf)
    return dict(zip(names, map(float, p))), dict(zip(names, map(float, std))), means


def split(means):
    stand = {k: m for k, m in means.items() if not (k.startswith("tick_") or k.startswith("edge_"))}
    tick = {k: m for k, m in means.items() if k.startswith("tick_")}
    edge = {k: m for k, m in means.items() if k.startswith("edge_")}
    rms = math.sqrt(np.mean([m[0] ** 2 + m[1] ** 2 for m in stand.values()])) if stand else float("nan")
    edge_rms = {}
    for k, m in edge.items():
        ph = k.split("_")[1]
        edge_rms.setdefault(ph, []).append(m[1])
    edge_rms = {ph: round(float(np.sqrt(np.mean(np.square(v)))), 1) for ph, v in edge_rms.items()}
    return rms, tick, edge_rms


def show(label, means):
    rms, tick, edge_rms = split(means)
    print(f"  [{label}] standing rms {rms:.1f} mm; edge y rms per phase (mm) {edge_rms}; ticks (model - true, x y mm):")
    for k in sorted(tick):
        print(f"      {k:22s} {tick[k][0]:+6.1f} {tick[k][1]:+6.1f}")
    return rms, tick, edge_rms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wbend", type=float, default=1.0)
    ap.add_argument("--wedge", type=float, default=1.0)
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--out", default=os.path.join(HERE, "bend_fit.json"))
    args = ap.parse_args()
    obs, bend = load_obs(args.wbend, args.wedge)
    fit_rows = [o for o in obs if not o["holdout"]]
    stand_hold = [o for o in obs if o["holdout"]]
    phases = sorted({o["phase"] for o in obs if o["phase"] is not None})
    n = {k: sum(o["kind"] == k for o in fit_rows) for k in ("stand", "tick", "edge")}
    print(f"fit rows {n}, bend phases {phases}, {len(stand_hold)} standing holdout rows")

    kin0 = BendKin()
    print("\n== current mount file (no fit) ==")
    before = show("current", group_means(obs, residuals(kin0, obs)))
    hold0 = group_means(stand_hold, residuals(kin0, stand_hold))
    print("  standing holdout:", {k: round(math.hypot(*v), 1) for k, v in hold0.items()})

    results = {}
    for mname in args.models.split(","):
        names = MODELS[mname]
        print(f"\n== model {mname}: {names} ==")
        kin = BendKin()
        p, std, means = fit(kin, fit_rows, names)
        print("  params:", {k: round(p[k], 3) for k in names})
        print("  std   :", {k: round(std[k], 3) for k in names})
        rms, tick, edge_rms = show("full fit", means)
        hold = group_means(stand_hold, residuals(kin, stand_hold))
        hold_err = {k: round(math.hypot(*v), 1) for k, v in hold.items()}
        print("  standing holdout (mm):", hold_err)
        phase_hold = {}
        for ph in phases:
            train = [o for o in fit_rows if o["phase"] != ph]
            test = [o for o in fit_rows if o["phase"] == ph]
            kin_h = BendKin()
            ph_p, _, _ = fit(kin_h, train, names)
            m = group_means(test, residuals(kin_h, test))
            tx = {k: [round(v[0], 1), round(v[1], 1)] for k, v in m.items() if k.startswith("tick_")}
            ey = [v[1] for k, v in m.items() if k.startswith("edge_")]
            worst = max((abs(v[0]) for v in tx.values()), default=None)
            phase_hold[f"{ph:.2f}"] = dict(ticks=tx, worst_abs_x_mm=worst,
                                           edge_y_rms_mm=round(float(np.sqrt(np.mean(np.square(ey)))), 1) if ey else None,
                                           params={k: round(ph_p[k], 3) for k in names})
            print(f"  held-out phase {ph:.2f}: tick worst |x| {worst} mm, ticks {tx}, edge y rms "
                  f"{phase_hold[f'{ph:.2f}']['edge_y_rms_mm']} mm")
        results[mname] = dict(params=p, std=std, standing_rms_mm=round(rms, 2), standing_holdout_mm=hold_err,
                              tick_residual_mm={k: [round(v[0], 1), round(v[1], 1)] for k, v in tick.items()},
                              edge_y_rms_mm=edge_rms, phase_holdout=phase_hold,
                              all_residual_mm={k: [round(v[0], 1), round(v[1], 1)] for k, v in means.items()})
    # acceptance: held-out tick |x| <= 5 mm in every bend phase and the standing holdout <= 10 mm
    verdict = {}
    for mname, r in results.items():
        tick_ok = [h["worst_abs_x_mm"] is not None and h["worst_abs_x_mm"] <= 5.0 for h in r["phase_holdout"].values()]
        verdict[mname] = dict(passed=bool(all(tick_ok)) and all(v <= 10.0 for v in r["standing_holdout_mm"].values()),
                              phases_with_ticks=[ph for ph, h in r["phase_holdout"].items() if h["worst_abs_x_mm"] is not None],
                              phases_without_ticks=[ph for ph, h in r["phase_holdout"].items() if h["worst_abs_x_mm"] is None],
                              worst_tick_holdout_mm=max((h["worst_abs_x_mm"] for h in r["phase_holdout"].values()
                                                         if h["worst_abs_x_mm"] is not None), default=None),
                              standing_holdout_mm=r["standing_holdout_mm"])
    best = min(results, key=lambda m: (verdict[m]["worst_tick_holdout_mm"] or 1e9, results[m]["standing_rms_mm"]))
    print("\nacceptance:", json.dumps(verdict, indent=1))
    print("best model by held-out tick error:", best)
    out = dict(date=datetime.datetime.now().isoformat(timespec="seconds"), wbend=args.wbend, wedge=args.wedge,
               acceptance=dict(rule="held-out tick |x| <= 5 mm in every bend phase and standing holdout <= 10 mm",
                               per_model=verdict, best_model=best, passed=verdict[best]["passed"],
                               mount_file_written=False,
                               duck_kin_change="duck_kin has no neck-pivot field: add neck_pivot_offset_m to "
                                               "u20cam_mount.json, read it in DuckKin.__init__, add it to the `neck` "
                                               "body's p0 in place() (see BendKin.place) and to the place() cache key"),
               before=dict(standing_rms_mm=round(before[0], 2),
                           tick_residual_mm={k: [round(v[0], 1), round(v[1], 1)] for k, v in before[1].items()},
                           edge_y_rms_mm=before[2],
                           standing_holdout_mm={k: round(math.hypot(*v), 1) for k, v in hold0.items()}),
               models=results, params_doc=__doc__)
    json.dump(out, open(args.out, "w"), indent=1)
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
