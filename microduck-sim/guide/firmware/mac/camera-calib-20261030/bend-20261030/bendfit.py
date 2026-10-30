"""Fit the neck-chain / camera parameters of duck_kin on the bend data (bend_ticks.json: the 00:29 sweep1 plus the
hold sweeps sweep2 / sweep3 / sweep4) together with the standing captures (u20cam-mount-1030-far+ruler+bend.json
without its by-eye bend rows), compare parameter sets by held-out error per bend phase and per sweep, check the
standing fit stays within tolerance, and write bend_fit.json.

Model (BendKin, a DuckKin whose place() takes extra parameters; duck_kin.py itself is not edited):
  pitch, yaw, roll   camera offsets in deg (the mount file's offsets_deg are the start)
  sx, sy, sz         lens shift in the camera frame, mm (optical axis, image left, image up)
  px, py, pz         neck pivot offset: translation of the `neck` body (the neck_pitch axis) in the trunk frame, mm
  neck0, head0       joint zero offsets added to the measured neck_pitch / head_pitch readings, deg
  imu_p, imu_r       IMU pitch / roll bias: gb is turned by these before trunk_rotation, deg
  imu_y              IMU yaw misalignment about the trunk z axis, deg: invisible when the trunk is level, it turns a
                     trunk pitch of p into a false roll p sin(imu_y) in the bow
  ruler_yaw, ruler_dy  nuisance terms of sweep1 only: its scale edge is y = -0.0093 + ruler_dy/1000 +
                     tan(ruler_yaw) (x - toe_x) (fixed at 0 unless a model names them; the 00:29 placement was measured)
  ruler_dy_s2/3/4    RULER_Y nuisance of sweeps 2-4 (mm, added to -0.0093): the ruler was re-placed for each of
                     them. Always fitted when the sweep's rows are in the fit; a weak prior (sigma 20 mm) at the
                     placement Shawn described (s2: -0.022 centre = 0 mm, s3: about 3 cm left = +30 mm, s4: about
                     6 cm left = +60 mm) only breaks ties; the edge rows determine it.
head_pitch_gain stays the mount file's 0.92 and multiplies the MEASURED reading (duck_kin.place: ang = q - qpos0,
ang *= head_gain), so this fit, which feeds measured q, uses it as the robot does.

Observations and residuals (m, on the floor):
  tick   bend tick with a read cm: the pixel ray's hit on the board top (z = 1.6 mm) minus (toe_x + cm/100, y_edge)
  edge   the detected scale-edge column at rows 30, 90, .. 330 of every bend frame (no tick identity needed): the
         ray's hit minus y_edge in y only (x residual 0)
  stand  standing capture: cam_calib.object_centre with radius 0.006 minus the stored (x, y), the convention of the
         existing fit (ruler rows store true x + 0.006)
  prior  (ruler_dy_sN - prior) / 20 mm, scaled to a 2 mm point
Every labelled point weighs the same whatever its frame count (1/sqrt(n) per row); bend ticks times --wbend, edge
rows times --wedge. Groups: s<sweep>_p<phase>.

Held-out tests: (a) every (sweep, phase) group in turn dropped from the fit and predicted; (b) by sweep: fit on
sweep1 + standing, test on sweeps 2-4; fit on sweeps 2-4 + standing, test on sweep1; and each of sweeps 2-4 left
out of the full fit. For a held-out sweep 2-4 only its ruler_dy_sN is re-fitted on the test rows (the ruler was
moved; the chain parameters stay as trained), which cannot change a tick's x residual.

usage: python bendfit.py [--wbend 1.0] [--wedge 1.0] [--models base,pivot,...] [--out bend_fit.json]
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
SWEEP_DY = {"sweep1": "ruler_dy", "sweep2": "ruler_dy_s2", "sweep3": "ruler_dy_s3", "sweep4": "ruler_dy_s4"}
DY_PRIOR = {"ruler_dy_s2": 0.0, "ruler_dy_s3": 30.0, "ruler_dy_s4": 60.0}   # mm, from Shawn's placement notes
DY_PRIOR_SIGMA = 20.0   # mm
POINT_SIGMA = 2.0       # mm, the prior row is scaled to look like one point of this precision
PARAMS = ["pitch", "yaw", "roll", "sx", "sy", "sz", "px", "py", "pz", "neck0", "head0", "imu_p", "imu_r", "imu_y",
          "ruler_yaw", "ruler_dy", "ruler_dy_s2", "ruler_dy_s3", "ruler_dy_s4"]
STEP = dict(pitch=0.01, yaw=0.01, roll=0.01, sx=0.1, sy=0.1, sz=0.1, px=0.1, py=0.1, pz=0.1, neck0=0.01, head0=0.01,
            imu_p=0.01, imu_r=0.01, imu_y=0.01, ruler_yaw=0.01, ruler_dy=0.1, ruler_dy_s2=0.1, ruler_dy_s3=0.1,
            ruler_dy_s4=0.1)
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
    "pivot+zeros": B + ["px", "pz", "neck0", "head0"],
}
DEFAULT_MODELS = "base,pivot,pivot+imuy,pivot3+imuy,pivot+shift,pivot+zeros"
_TOE_CACHE = {}


class BendKin(duck_kin.DuckKin):
    def __init__(self):
        super().__init__()
        self.neck_body = self.body_names.index("neck")
        self.p = dict((k, 0.0) for k in PARAMS)
        self.p.update(pitch=self.offsets[0], yaw=self.offsets[1], roll=self.offsets[2],
                      sx=self.shift[0] * 1000, sy=self.shift[1] * 1000, sz=self.shift[2] * 1000)
        self.p.update(DY_PRIOR)
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
        if key not in _TOE_CACHE:
            _TOE_CACHE[key] = cam_calib.toe_x(self, q, gb)
        return _TOE_CACHE[key]

    def y_edge(self, x, toe_x, sweep="sweep1"):
        return Y_EDGE + self.p[SWEEP_DY[sweep]] / 1000.0 + math.tan(math.radians(self.p["ruler_yaw"])) * (x - toe_x)


def load_obs(wbend, wedge):
    bend = json.load(open(os.path.join(HERE, "bend_ticks.json")))
    stand = json.load(open(STANDING))
    rows = {}
    for sweep, sub in (("sweep1", "rows_matched.json"), ("sweep2", "sweep2/rows_matched.json"),
                       ("sweep3", "sweep3/rows_matched.json"), ("sweep4", "sweep4/rows_matched.json")):
        for r in json.load(open(os.path.join(HERE, sub))):
            rows[(sweep, r["name"])] = r
    obs = []
    for o in stand["obs"]:
        if o["point"].startswith("bend_"):
            continue   # the by-eye rows of the earlier fit; replaced by bend_ticks.json
        obs.append(dict(kind="stand", point=o["point"], u=o["u"], v=o["v"], w=o["w"], h=o["h"], q=o["q"], gb=o["gb"],
                        x=o["x"], y=o["y"], holdout=bool(o.get("holdout")), group=None, sweep=None, wmul=1.0))
    for o in bend["obs"]:
        if o["cm"] is None:
            continue
        s = o.get("sweep", "sweep1")
        g = f"s{s[-1]}_p{o['phase']:.2f}"
        obs.append(dict(kind="tick", point=f"tick_{g}_{o['cm']}cm", u=o["u"], v=o["v"], w=640, h=360, q=o["q"],
                        gb=o["gb"], cm=o["cm"], holdout=False, group=g, sweep=s, frame=o["frame"], wmul=wbend))
    sweeps = {"sweep1"}
    for name, d in bend["detail"].items():
        s = d.get("sweep", "sweep1")
        r = rows[(s, name)]
        ph = r["cmd_phase"] if s == "sweep1" else r["phase"]
        g = f"s{s[-1]}_p{ph:.2f}"
        sweeps.add(s)
        for v in EDGE_ROWS:
            if str(v) in d["edge"]:
                obs.append(dict(kind="edge", point=f"edge_{g}_r{v}", u=d["edge"][str(v)], v=float(v), w=640, h=360,
                                q=r["q"], gb=r["gb"], holdout=False, group=g, sweep=s, frame=name, wmul=wedge))
    for s in sorted(sweeps - {"sweep1"}):
        obs.append(dict(kind="prior", point=f"prior_{SWEEP_DY[s]}", name=SWEEP_DY[s], holdout=False,
                        group=f"s{s[-1]}_prior", sweep=s, wmul=1.0))
    return obs, bend


def predict_row(kin, o):
    if o["kind"] == "prior":
        return 0.0, (kin.p[o["name"]] - DY_PRIOR[o["name"]]) / 1000.0 * (POINT_SIGMA / DY_PRIOR_SIGMA)
    pos, R = kin.camera_pose(o["q"], o["gb"])
    if o["kind"] == "stand":
        c = cam_calib.object_centre(kin, o["u"], o["v"], pos, R, o["w"], o["h"], R_STAND)
        return None if c is None else (c[0] - o["x"], c[1] - o["y"])
    xy = kin.pixel_to_ground_pose(o["u"], o["v"], pos, R, o["w"], o["h"], z=BOARD)
    if xy is None:
        return None
    tx = kin.toe_x(o["q"], o["gb"])
    ye = kin.y_edge(xy[0], tx, o["sweep"])
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


def dy_names(obs):
    return sorted({SWEEP_DY[o["sweep"]] for o in obs if o["sweep"] not in (None, "sweep1")})


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
    s2 = sum(m[0] ** 2 + m[1] ** 2 for k, m in means.items() if not np.isnan(m[0]) and not k.startswith("prior_")) / 1e6 / dof
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
    stand = {k: m for k, m in means.items() if not k.startswith(("tick_", "edge_", "prior_"))}
    tick = {k: m for k, m in means.items() if k.startswith("tick_")}
    edge = {k: m for k, m in means.items() if k.startswith("edge_")}
    rms = math.sqrt(np.mean([m[0] ** 2 + m[1] ** 2 for m in stand.values()])) if stand else float("nan")
    edge_rms = {}
    for k, m in edge.items():
        edge_rms.setdefault(k.split("_r")[0][5:], []).append(m[1])
    edge_rms = {g: round(float(np.sqrt(np.mean(np.square(v)))), 1) for g, v in sorted(edge_rms.items())}
    return rms, tick, edge_rms


def tick_table(tick):
    """{group: {cm: [x, y]}} plus per group the x slope between its ticks (mm per cm) and the mean y (lateral)."""
    out = {}
    for k, m in tick.items():
        g, cm = k[5:].rsplit("_", 1)
        out.setdefault(g, {})[int(cm[:-2])] = [round(m[0], 1), round(m[1], 1)]
    summary = {}
    for g, d in out.items():
        cms = sorted(d)
        slope = (d[cms[-1]][0] - d[cms[0]][0]) / (cms[-1] - cms[0]) if len(cms) > 1 else None
        summary[g] = dict(ticks={str(c): d[c] for c in cms}, worst_abs_x_mm=max(abs(d[c][0]) for c in cms),
                          x_slope_mm_per_cm=None if slope is None else round(slope, 2),
                          mean_y_mm=round(float(np.mean([d[c][1] for c in cms])), 1))
    return summary


def show(label, means):
    rms, tick, edge_rms = split(means)
    tt = tick_table(tick)
    print(f"  [{label}] standing rms {rms:.1f} mm; edge y rms per group (mm) {edge_rms}")
    for g in sorted(tt):
        print(f"      ticks {g:12s} x/y mm {tt[g]['ticks']}  slope {tt[g]['x_slope_mm_per_cm']} mm/cm, mean y {tt[g]['mean_y_mm']}")
    return rms, tick, edge_rms, tt


def holdout_eval(kin, test, names):
    """Residuals of `test` rows under the trained kin; for a held-out sweep 2-4 its ruler_dy is re-fitted on the
    test rows first (the ruler was moved; the chain parameters stay)."""
    dys = [n for n in dy_names(test) if n not in names]
    kin_t = BendKin()
    kin_t.set_params(kin.p)
    if dys:
        fit(kin_t, test, dys, iters=15)
    m = group_means(test, residuals(kin_t, test))
    tt = tick_table({k: v for k, v in m.items() if k.startswith("tick_")})
    ey = [v[1] for k, v in m.items() if k.startswith("edge_")]
    worst = max((t["worst_abs_x_mm"] for t in tt.values()), default=None)
    return dict(ticks={g: t["ticks"] for g, t in tt.items()}, worst_abs_x_mm=worst,
                x_slope_mm_per_cm={g: t["x_slope_mm_per_cm"] for g, t in tt.items()},
                edge_y_rms_mm=round(float(np.sqrt(np.mean(np.square(ey)))), 1) if ey else None,
                refit_dy={n: round(kin_t.p[n], 1) for n in dys})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wbend", type=float, default=1.0)
    ap.add_argument("--wedge", type=float, default=1.0)
    ap.add_argument("--models", default=DEFAULT_MODELS)
    ap.add_argument("--out", default=os.path.join(HERE, "bend_fit.json"))
    args = ap.parse_args()
    obs, bend = load_obs(args.wbend, args.wedge)
    fit_rows = [o for o in obs if not o["holdout"]]
    stand_hold = [o for o in obs if o["holdout"]]
    groups = sorted({o["group"] for o in obs if o["group"] is not None and not o["group"].endswith("_prior")})
    sweeps = sorted({o["sweep"] for o in obs if o["sweep"]})
    n = {k: sum(o["kind"] == k for o in fit_rows) for k in ("stand", "tick", "edge", "prior")}
    print(f"fit rows {n}, groups {groups}, sweeps {sweeps}, {len(stand_hold)} standing holdout rows")

    kin0 = BendKin()
    print("\n== current mount file (no fit; sweeps 2-4 ruler at the prior position) ==")
    before = show("current", group_means(obs, residuals(kin0, obs)))
    hold0 = group_means(stand_hold, residuals(kin0, stand_hold))
    print("  standing holdout:", {k: round(math.hypot(*v), 1) for k, v in hold0.items()})

    def rows_of(pred):
        return [o for o in fit_rows if pred(o)]

    sweep_tests = {
        "train s1 -> test s2+s3+s4": (lambda o: o["sweep"] in (None, "sweep1"), lambda o: o["sweep"] in ("sweep2", "sweep3", "sweep4")),
        "train s2+s3+s4 -> test s1": (lambda o: o["sweep"] != "sweep1", lambda o: o["sweep"] == "sweep1"),
        "all but s2 -> test s2": (lambda o: o["sweep"] != "sweep2", lambda o: o["sweep"] == "sweep2"),
        "all but s3 -> test s3": (lambda o: o["sweep"] != "sweep3", lambda o: o["sweep"] == "sweep3"),
        "all but s4 -> test s4": (lambda o: o["sweep"] != "sweep4", lambda o: o["sweep"] == "sweep4"),
    }

    results = {}
    for mname in args.models.split(","):
        chain = MODELS[mname]
        names = chain + dy_names(fit_rows)
        print(f"\n== model {mname}: {names} ==")
        kin = BendKin()
        p, std, means = fit(kin, fit_rows, names)
        print("  params:", {k: round(p[k], 3) for k in names})
        print("  std   :", {k: round(std[k], 3) for k in names})
        rms, tick, edge_rms, tt = show("full fit", means)
        hold = group_means(stand_hold, residuals(kin, stand_hold))
        hold_err = {k: round(math.hypot(*v), 1) for k, v in hold.items()}
        print("  standing holdout (mm):", hold_err)
        dy = {k: dict(value_mm=round(p[k], 1), std_mm=round(std[k], 1), prior_mm=DY_PRIOR[k],
                      moved_mm=round(p[k] - DY_PRIOR[k], 1)) for k in names if k.startswith("ruler_dy_s")}
        print("  ruler dy per sweep:", dy)
        # (a) held out by (sweep, phase) group
        phase_hold = {}
        for g in groups:
            train = rows_of(lambda o: o["group"] != g)
            test = rows_of(lambda o: o["group"] == g)
            kin_h = BendKin()
            tr_names = chain + dy_names(train)
            ph_p, _, _ = fit(kin_h, train, tr_names)
            h = holdout_eval(kin_h, test, tr_names)
            h["params"] = {k: round(ph_p[k], 3) for k in tr_names}
            phase_hold[g] = h
            print(f"  held-out group {g}: tick worst |x| {h['worst_abs_x_mm']} mm, ticks {h['ticks']}, "
                  f"slope {h['x_slope_mm_per_cm']}, edge y rms {h['edge_y_rms_mm']} mm")
        # (b) held out by sweep
        sweep_hold = {}
        for label, (tr, te) in sweep_tests.items():
            train, test = rows_of(tr), rows_of(te)
            if not test:
                continue
            kin_h = BendKin()
            tr_names = chain + dy_names(train)
            s_p, s_std, _ = fit(kin_h, train, tr_names)
            h = holdout_eval(kin_h, test, tr_names)
            h["params"] = {k: round(s_p[k], 3) for k in tr_names}
            h["std"] = {k: round(s_std[k], 3) for k in tr_names}
            sweep_hold[label] = h
            print(f"  held-out {label}: tick worst |x| {h['worst_abs_x_mm']} mm, ticks {h['ticks']}, slope "
                  f"{h['x_slope_mm_per_cm']}, edge y rms {h['edge_y_rms_mm']} mm, train params "
                  f"{ {k: round(s_p[k], 2) for k in chain} }, refit dy {h['refit_dy']}")
        results[mname] = dict(chain_params=chain, params=p, std=std, standing_rms_mm=round(rms, 2),
                              standing_holdout_mm=hold_err, ruler_dy=dy, tick_residual_mm=tt, edge_y_rms_mm=edge_rms,
                              phase_holdout=phase_hold, sweep_holdout=sweep_hold,
                              all_residual_mm={k: [round(v[0], 1), round(v[1], 1)] for k, v in means.items()})
    # acceptance: held-out tick |x| <= 5 mm in every bend phase (group) and the standing holdout <= 10 mm
    verdict = {}
    for mname, r in results.items():
        with_t = {g: h["worst_abs_x_mm"] for g, h in r["phase_holdout"].items() if h["worst_abs_x_mm"] is not None}
        verdict[mname] = dict(passed=bool(with_t) and all(v <= 5.0 for v in with_t.values())
                              and all(v <= 10.0 for v in r["standing_holdout_mm"].values()),
                              phase_worst_abs_x_mm=with_t,
                              phases_without_ticks=[g for g, h in r["phase_holdout"].items() if h["worst_abs_x_mm"] is None],
                              worst_tick_holdout_mm=max(with_t.values(), default=None),
                              sweep_holdout_worst_abs_x_mm={k: h["worst_abs_x_mm"] for k, h in r["sweep_holdout"].items()},
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
               before=dict(standing_rms_mm=round(before[0], 2), tick_residual_mm=before[3], edge_y_rms_mm=before[2],
                           standing_holdout_mm={k: round(math.hypot(*v), 1) for k, v in hold0.items()}),
               models=results, params_doc=__doc__)
    json.dump(out, open(args.out, "w"), indent=1)
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
