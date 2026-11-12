#!/usr/bin/env python3
"""Sim-vs-robot gap page for every replayed robot action: the same commands, the robot's tick log against the sim's.

The run ledger (../run_ledger.py tick, every 5 min on the Mac mini) cuts each finished brain log into actions and the
scorecard (../scorecard-20261109/scorecard.py auto) replays each action's commands in the as-built sim. This tool
reads both tick logs with the same code and writes one page per action plus an index next to the ledger's page
(served by the phone remote at :5180/runs/gap/):

  IMU        trunk gyro x/y/z and tilt over time, tick-to-tick gyro jitter, share of gyro power above 5 Hz, the
             largest yaw rate (falls start with a yaw spike)
  servos     per leg joint: how much of the goal motion the encoder shows (amplitude ratio), how late (lag in 20 ms
             ticks) and how often a small goal change moved the joint not at all (dead share = stiction / deadband)
  play       the encoder cannot see play between horn, link, screws and sole: it sits on the servo's output shaft.
             What it can do is predict the trunk's tilt from the joint angles with the stance foot flat (forward
             kinematics on the as-built model). The angle between that prediction and the IMU is the motion the
             joints do not explain: play, loose screws, sole roll and slip. In the rigid sim it is only sole roll, so
             robot minus sim is the part the model is missing. It is split by whether the leg encoders move: in 0.5 s
             windows where all ten stay within 3 ticks (static) the robot is as rigid as the sim (0.10 vs 0.04 deg
             over 11-02..11-12, matching play-locate-20261112's 0.06 deg); the gap sits in the ticks where the
             balance policy moves a joint (2.3 vs 0.19 deg): the trunk does not follow the joint the way the rigid
             model says, which is give under a load change (horn, link, sole), not slack at rest.
  current    the robot's peak leg current (the sim logs none)

  sim_real_gap.py auto            pages for every replayed action not yet drawn; appends ~/duck-walks/gap-runs.jsonl
  sim_real_gap.py one EPISODE_ID  redraw one action
Runs where the sim runs (mujoco): the Mac mini's ~/.venvs/microduck-dyn.
"""
import argparse
import glob
import html
import json
import math
import os
import sys
import time
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
SIM_ROOT = os.path.normpath(os.path.join(MAC, "..", "..", ".."))
sys.path.insert(0, os.path.join(MAC, "scorecard-20261109"))
import scorecard as sc  # noqa: E402

DATA = os.path.expanduser(os.environ.get("DUCK_LEDGER_DATA", "~/duck-walks"))
EPISODES = os.path.join(DATA, "episodes.jsonl")
SIMDIR = os.path.join(DATA, "scorecard-auto")
RUNS = os.path.join(DATA, "gap-runs.jsonl")
OUT = os.path.expanduser(os.environ.get(
    "DUCK_GAP_PAGE_DIR", os.path.join(SIM_ROOT, "microduck-simulator", "app", "public", "runs", "gap")))
SCENE = os.path.join(SIM_ROOT, "microduck_rl", "cmu", "model", "scenes", "scene_battery.xml")

# log rows: q, pos_tick and goal_tick follow servo IDs 1..14 (walk_brain.NAMES)
NAMES = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw",
         "left_ankle", "left_knee", "left_hip_pitch", "left_hip_roll", "left_hip_yaw",
         "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
CN = {"right_ankle": "右踝", "right_knee": "右膝", "right_hip_pitch": "右髋俯仰", "right_hip_roll": "右髋滚转",
      "right_hip_yaw": "右髋偏航", "left_ankle": "左踝", "left_knee": "左膝", "left_hip_pitch": "左髋俯仰",
      "left_hip_roll": "左髋滚转", "left_hip_yaw": "左髋偏航"}
LEGS = list(range(10))
DT = 0.02


# ---------- forward kinematics: trunk tilt the joints predict with the stance foot flat ----------
class Kin:
    def __init__(self):
        import mujoco
        self.mj = mujoco
        self.m = mujoco.MjModel.from_xml_path(SCENE)
        self.d = mujoco.MjData(self.m)
        self.adr = {n: self.m.jnt_qposadr[self.m.joint(n).id] for n in NAMES}
        self.imu = self.m.site("imu").id
        self.feet = [self.m.site("left_foot").id, self.m.site("right_foot").id]

    def frames(self, q):
        """Rotation of each foot site in the IMU site frame and the feet's positions (IMU frame) for one tick."""
        d = self.d
        d.qpos[:] = self.m.qpos0
        for n, v in zip(NAMES, q):
            d.qpos[self.adr[n]] = v
        self.mj.mj_kinematics(self.m, d)
        Ri = d.site_xmat[self.imu].reshape(3, 3)
        pi = d.site_xpos[self.imu]
        out = []
        for f in self.feet:
            Rf = d.site_xmat[f].reshape(3, 3)
            out.append((Ri.T @ Rf, Ri.T @ (d.site_xpos[f] - pi)))
        return out


def wahba(a, b):
    """Rotation C minimising sum |a_i - C b_i|^2."""
    u, _, vt = np.linalg.svd(np.einsum("ni,nj->ij", a, b))
    return u @ np.diag([1.0, 1.0, np.linalg.det(u) * np.linalg.det(vt)]) @ vt


QUIET_GYRO = 0.6   # rad/s: a tick counts as standing still below this trunk rate
QUIET_MIN = 50     # ticks of standing still needed for the play measure


def residual(kin, rows):
    """Play measure, standing still only: per quiet tick, the angle (deg) between the trunk tilt the IMU reads and
    the tilt the joint encoders predict with both soles flat, minus its median over the action.

    gb is gravity in the model's trunk frame (what the policy sees; IMU_MOUNT_QUAT already applied), so the
    prediction is R_imu_foot(q) g_foot with g_foot fitted once per action (absorbing joint-zero and mount offsets).
    With both feet flat the joints fix the trunk's tilt; whatever tilt the IMU sees beyond that is lost motion
    between encoder and floor (horn and link play, screws, sole). While stepping the soles roll and the stance
    foot changes, which the rigid prediction cannot follow (the sim alone shows 5 deg there), so walking ticks are
    left out. Returns (per-tick deg, number of quiet ticks) or (None, n) when there are too few."""
    gyro = np.array([r["gyro_body"] for r in rows], float)
    quiet = [r for r, w in zip(rows, np.linalg.norm(gyro, axis=1)) if w < QUIET_GYRO]
    if len(quiet) < QUIET_MIN:
        return None, len(quiet), []
    gb = np.array([r["gb"] for r in quiet], float)
    gb /= np.linalg.norm(gb, axis=1, keepdims=True)
    out = []
    for k in (0, 1):
        R = [kin.frames(r["q"])[k][0] for r in quiet]
        v = np.median([Rf.T @ g for Rf, g in zip(R, gb)], axis=0)
        v /= np.linalg.norm(v)
        pred = np.array([Rf @ v for Rf in R])
        out.append(np.degrees(np.arccos(np.clip(np.einsum("ni,ni->n", pred, gb), -1.0, 1.0))))
    res = np.minimum(out[0], out[1])   # the foot that better explains the tilt (the one carrying the load)
    return res - np.median(res), len(quiet), [r["t"] - rows[0]["t"] for r in quiet]


# ---------- metrics, the same code for both sides ----------
def hf_share(x):
    x = np.asarray(x, float) - np.mean(x)
    p = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), DT)
    return float(p[f > 5].sum() / max(p[f > 0].sum(), 1e-12))


def spectrum(x):
    x = np.asarray(x, float) - np.mean(x)
    n = len(x)
    w = np.hanning(n)
    p = np.abs(np.fft.rfft(x * w)) ** 2 / max(w.sum() ** 2, 1e-9)
    return np.fft.rfftfreq(n, DT), p


STATIC_W, STATIC_TICKS = 25, 3   # 0.5 s with every leg encoder within 3 ticks = joints at rest
PLAY_KINDS = ("balance", "stand")   # actions where the robot stands still long enough for the play measure


def measure(rows, kin, kind):
    rows = [r for r in rows if r.get("gb") and r.get("goal_tick") and r.get("pos_tick") and r.get("q")
            and r.get("imu_valid", True) is not False]
    if len(rows) < 25:
        return None
    G = np.array([[r["goal_tick"][str(i + 1)] for i in range(14)] for r in rows], float)
    P = np.array([r["pos_tick"] for r in rows], float)
    gy = np.array([r["gyro_body"] for r in rows], float)
    joints = {}
    for j in LEGS:
        g, p = G[:, j] - G[:, j].mean(), P[:, j] - P[:, j].mean()
        xc = [float(np.dot(g[:len(g) - k], p[k:])) for k in range(12)]
        dg, dp = np.diff(G[:, j]), np.diff(P[:, j])
        small = (np.abs(dg) >= 3) & (np.abs(dg) <= 15)   # 0.26-1.3 deg goal steps
        joints[NAMES[j]] = {"amp": round(float(p.std() / max(g.std(), 1e-6)), 3), "lag": int(np.argmax(xc)),
                            "dead": round(float(np.mean(np.abs(dp[small]) < 1)), 3) if small.sum() >= 5 else None,
                            "err_deg": round(float(np.sqrt(np.mean((G[:, j] - P[:, j]) ** 2)) * 360 / 4096), 2)}
    res, n_quiet, t_quiet = residual(kin, rows) if kind in PLAY_KINDS else (None, 0, [])
    play_static = play_moving = moving_share = None
    if res is not None:
        legp = P[:, LEGS]
        static = np.zeros(len(rows), bool)
        for i in range(len(rows) - STATIC_W + 1):
            if (legp[i:i + STATIC_W].max(0) - legp[i:i + STATIC_W].min(0)).max() <= STATIC_TICKS:
                static[i:i + STATIC_W] = True
        sq = static[np.linalg.norm(gy, axis=1) < QUIET_GYRO]
        rms = lambda x: round(float(np.sqrt(np.mean(x ** 2))), 2) if len(x) >= 10 else None
        play_static, play_moving, moving_share = rms(res[sq]), rms(res[~sq]), round(float(np.mean(~sq)), 3)
    cur = [r.get("cur_ma") for r in rows if r.get("cur_ma")]
    return {
        "ticks": len(rows),
        "jitter": [round(float(v), 3) for v in np.std(np.diff(gy, axis=0), axis=0)],
        "hf": [round(hf_share(gy[:, k]), 3) for k in range(3)],
        "yaw_max": round(float(np.abs(gy[:, 2]).max()), 2),
        "tilt_max": round(max(sc.tilt_deg(r["gb"]) for r in rows), 1),
        "quiet_ticks": n_quiet,
        "play_rms": None if res is None else round(float(np.sqrt(np.mean(res ** 2))), 2),
        "play_static": play_static, "play_moving": play_moving, "moving_share": moving_share,
        "play_range": None if res is None else round(float(np.percentile(res, 97.5) - np.percentile(res, 2.5)), 2),
        "amp": round(float(np.mean([v["amp"] for v in joints.values()])), 3),
        "lag": round(float(np.mean([v["lag"] for v in joints.values()])), 2),
        "dead": round(float(np.mean([v["dead"] for v in joints.values() if v["dead"] is not None] or [np.nan])), 3),
        "cur_max": int(np.max(np.array(cur)[:, LEGS])) if cur else None,
        "volt": round(float(np.mean([r["battery_dv"] for r in rows if r.get("battery_dv")])) / 10, 2)
        if any(r.get("battery_dv") for r in rows) else None,
        "joints": joints,
        "_series": {"t": [r["t"] - rows[0]["t"] for r in rows], "gyro": gy.tolist(),
                    "gb": [r["gb"] for r in rows], "play": None if res is None else res.tolist(), "play_t": t_quiet,
                    "G": G.tolist(), "P": P.tolist()},
    }


# ---------- pairing an episode with its sim replay ----------
def windows(e, rows):
    t0, t1 = e["t_start"], e["t_end"]
    if e["outcome"] == "fell":
        fall = next((r["t"] for r in rows if r.get("gb") and r["t"] >= t0 and sc.tilt_deg(r["gb"]) > sc.FALL_DEG), t1 + 1.0)
        t0, t1 = max(t0, fall - sc.AUTO_MAX_S), fall + 1.0
    else:
        t1 = min(t1, t0 + sc.AUTO_MAX_S)
    return t0, t1


def sim_tick_log(eid):
    c = sorted(glob.glob(os.path.join(SIMDIR, f"{eid}.*.seed0.ticks.jsonl")), key=os.path.getmtime)
    return c[-1] if c and os.path.exists(c[-1] + ".out") else None


def pair(e, kin, card):
    rows = sc.rows_of(os.path.join(DATA, e["trajectory"]))
    t0, t1 = windows(e, rows)
    tl = sim_tick_log(e["id"])
    if not tl:
        return None
    # the sim's view stops before a fall (tilt over 45 deg): compare the upright part on both sides
    real_rows = [r for r in rows if t0 <= r["t"] <= t1 and sc.tilt_deg(r.get("gb") or [0, 0, -1]) < 45]
    sim_rows = [r for r in sc.rows_of(tl) if sc.WALK_AT <= r["t"] <= sc.WALK_AT + (t1 - t0)
                and sc.tilt_deg(r.get("gb") or [0, 0, -1]) < 45]
    real, sim = measure(real_rows, kin, e["kind"]), measure(sim_rows, kin, e["kind"])
    if not real or not sim:
        return None
    return {"id": e["id"], "t0": e["t_start"], "kind": e["kind"], "when": e["when"], "outcome": e["outcome"],
            # the scorecard's verdict: majority of 3 seeds, falls read from the .out summary, and a sim fall within 1 s
            # of a replayed stand/monitor counted as the switch's (stop_topple), never as a predicted fall
            "sim_outcome": card.get(e["id"]),
            "commands": e.get("commands"), "real": real, "sim": sim, "sim_log": os.path.basename(tl)}


# ---------- page ----------
CSS = """:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e3e0d8;--real:#c2410c;--sim:#2563eb;--bad:#b91c1c;--ok:#15803d;--card:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,"PingFang SC",sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}h1{font-size:20px;margin:4px 0 2px}h2{font-size:16px;margin:22px 0 6px}
.mut{color:var(--mut);font-size:13px}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(210px,100%),1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.card b{font-size:13px;font-weight:600}.v{font-size:15px;margin-top:2px}.r{color:var(--real)}.s{color:var(--sim)}
.flag{color:var(--bad);font-weight:600}.good{color:var(--ok)}svg{width:100%;height:auto;background:#fff;border:1px solid var(--line);border-radius:8px}
.grid2{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(300px,100%),1fr));gap:10px}a{color:var(--sim);word-break:break-all}
.row{overflow-wrap:anywhere;display:flex;flex-wrap:wrap;gap:4px 12px;padding:8px 0;border-bottom:1px solid var(--line)}p{margin:6px 0;overflow-wrap:anywhere}h1{overflow-wrap:anywhere}"""


def svg_lines(title, xs, series, w=460, h=170, logy=False, xlabel="秒"):
    """series: [(label, color, ys)] over shared or per-series xs ([(xs, ys)])."""
    pad_l, pad_b, pad_t = 44, 24, 36
    allx = np.concatenate([np.asarray(x, float) for x, _, _, _ in series]) if series else np.array([0, 1])
    ally = np.concatenate([np.asarray(y, float) for _, y, _, _ in series])
    if logy:
        ally = np.log10(np.maximum(ally, 1e-9))
    x0, x1 = float(allx.min()), float(allx.max()) or 1.0
    y0, y1 = float(np.percentile(ally, 0.5)), float(np.percentile(ally, 99.5))
    if y1 - y0 < 1e-9:
        y1 = y0 + 1
    sx = lambda x: pad_l + (x - x0) / max(x1 - x0, 1e-9) * (w - pad_l - 8)
    sy = lambda y: pad_t + (1 - (min(max(y, y0), y1) - y0) / (y1 - y0)) * (h - pad_t - pad_b)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img"><text x="{pad_l}" y="14" font-size="12" fill="#1d1d1b">{html.escape(title)}</text>']
    for k in range(5):
        yv = y0 + (y1 - y0) * k / 4
        lab = f"1e{yv:.0f}" if logy else f"{yv:.2g}"
        out.append(f'<line x1="{pad_l}" x2="{w - 8}" y1="{sy(yv):.1f}" y2="{sy(yv):.1f}" stroke="#eee"/>'
                   f'<text x="{pad_l - 4}" y="{sy(yv) + 4:.1f}" font-size="10" text-anchor="end" fill="#6b6a66">{lab}</text>')
    for k in range(5):
        xv = x0 + (x1 - x0) * k / 4
        out.append(f'<text x="{sx(xv):.1f}" y="{h - 6}" font-size="10" text-anchor="middle" fill="#6b6a66">{xv:.3g}</text>')
    out.append(f'<text x="{w - 8}" y="{h - 6}" font-size="10" text-anchor="end" fill="#6b6a66">{xlabel}</text>')
    lx = pad_l
    for xs_, ys, label, color in series:
        ys = np.asarray(ys, float)
        if logy:
            ys = np.log10(np.maximum(ys, 1e-9))
        step = max(1, len(ys) // 700)
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in list(zip(xs_, ys))[::step])
        dash = ' stroke-dasharray="4 3"' if "目标" in label else ""
        out.append(f'<polyline fill="none" stroke="{color}" stroke-width="1.3"{dash} points="{pts}"/>')
        out.append(f'<text x="{lx}" y="29" font-size="11" fill="{color}">{html.escape(label)}</text>')
        lx += 12 + 11 * len(label)
    out.append("</svg>")
    return "".join(out)


def tilt_xy(gb):
    g = np.asarray(gb, float)
    pitch = np.degrees(np.arctan2(g[:, 0], -g[:, 2]))
    roll = np.degrees(np.arctan2(-g[:, 1], -g[:, 2]))
    return pitch, roll


def ratio_card(name, real, sim, unit="", hint="", hi=2.0, lo=0.5, fmt="{:.2f}"):
    if real is None or sim is None or (isinstance(real, float) and math.isnan(real)):
        return ""
    r = real / sim if sim else float("inf")
    flag = r > hi or r < lo
    rt = "∞" if math.isinf(r) else f"{r:.1f}x"
    cls = "flag" if flag else "good"
    return (f'<div class="card"><b>{html.escape(name)}</b><div class="v"><span class="r">真机 {fmt.format(real)}{unit}</span> · '
            f'<span class="s">仿真 {fmt.format(sim)}{unit}</span> · <span class="{cls}">{rt}</span></div>'
            f'<div class="mut">{html.escape(hint)}</div></div>')


def page(p):
    R, S = p["real"], p["sim"]
    rs, ss = R["_series"], S["_series"]
    rg, sg = np.array(rs["gyro"]), np.array(ss["gyro"])
    cards = "".join([
        ratio_card("躯干抖动 x/y/z（逐拍角速度变化）", float(np.mean(R["jitter"])), float(np.mean(S["jitter"])), " rad/s",
                   "真机高很多 = 有仿真里没有的冲击、间隙或打滑"),
        ratio_card("5 Hz 以上抖动占比", float(np.mean(R["hf"])), float(np.mean(S["hf"])), "",
                   "刚体仿真几乎全在 5 Hz 以下"),
        ratio_card("最大偏航角速度", R["yaw_max"], S["yaw_max"], " rad/s", "摔倒前常见偏航冲高", hi=1.5),
        ratio_card("关节静止时：关节解释不了的躯干倾斜（真正的旷量）", R.get("play_static"), S.get("play_static"), "°",
                   "腿部编码器 0.5 秒内都不动时算；平时约 0.1°，和仿真接近", hi=2.0),
        ratio_card("关节在动时：躯干没按运动学跟上", R.get("play_moving"), S.get("play_moving"), "°",
                   "平衡策略动关节时，躯干和预测的差；受力换向时舵盘、连杆、鞋底的让量", hi=2.0),
        ratio_card("旷量指标：静站全部时间（RMS）", R["play_rms"], S["play_rms"], "°",
                   "上面两项合起来；编码器加运动学预测的姿态和 IMU 之差", hi=1.5),
        ratio_card("旷量指标：晃动范围（95%）", R["play_range"], S["play_range"], "°", "拧紧螺丝后应该下降", hi=1.5),
        "" if R["play_rms"] is not None else
        '<div class="card"><b>旷量指标</b><div class="v mut">只在静站和平衡动作里算</div>'
        '<div class="mut">走路时鞋底滚动，运动学预测本身不准；走路时的松动看 5 Hz 以上抖动</div></div>',
        ratio_card("舵机跟随幅度（实际/目标）", R["amp"], S["amp"], "", "低 = 舵机跟不上", hi=1.3, lo=0.77),
        ratio_card("舵机滞后", R["lag"], S["lag"], " 拍(20ms)", "", hi=1.5, lo=0.67, fmt="{:.1f}"),
        ratio_card("小指令不动的比例（死区/静摩擦）", R["dead"], S["dead"] if S["dead"] else 0.0, "",
                   "目标变 0.3 到 1.3 度时关节一点没动的比例", hi=1.5),
        f'<div class="card"><b>真机腿部最大电流</b><div class="v r">{R["cur_max"]} mA</div><div class="mut">'
        f'仿真不记电流；正常行走约 0.6 到 0.9 A</div></div>' if R.get("cur_max") is not None else "",
    ])
    rp, rr = tilt_xy(rs["gb"])
    sp, sr = tilt_xy(ss["gb"])
    charts = []
    for k, ax in enumerate(["x（滚转方向）", "y（俯仰方向）", "z（偏航）"]):
        charts.append(svg_lines(f"躯干角速度 {ax} rad/s", None,
                                [(rs["t"], rg[:, k], "真机", "#c2410c"), (ss["t"], sg[:, k], "仿真", "#2563eb")]))
    charts.append(svg_lines("躯干俯仰 度（IMU 重力方向）", None, [(rs["t"], rp, "真机", "#c2410c"), (ss["t"], sp, "仿真", "#2563eb")]))
    charts.append(svg_lines("躯干滚转 度", None, [(rs["t"], rr, "真机", "#c2410c"), (ss["t"], sr, "仿真", "#2563eb")]))
    if rs["play"] is not None and ss["play"] is not None:
        charts.append(svg_lines("旷量指标（静站拍）：关节解释不了的躯干晃动 度", None,
                                [(rs["play_t"], rs["play"], "真机", "#c2410c"), (ss["play_t"], ss["play"], "仿真", "#2563eb")]))
    for k, ax in enumerate(["x", "y", "z"]):
        fr, pr = spectrum(rg[:, k])
        fs, ps = spectrum(sg[:, k])
        charts.append(svg_lines(f"角速度 {ax} 频谱（功率，对数）", None,
                                [(fr[1:], pr[1:], "真机", "#c2410c"), (fs[1:], ps[1:], "仿真", "#2563eb")],
                                logy=True, xlabel="Hz"))
    joint_charts = []
    deg = 360 / 4096
    for j in [5, 0, 6, 1, 8, 3]:
        Gr, Pr = np.array(rs["G"])[:, j] * deg, np.array(rs["P"])[:, j] * deg
        Gs, Ps = np.array(ss["G"])[:, j] * deg, np.array(ss["P"])[:, j] * deg
        joint_charts.append(svg_lines(f"{CN[NAMES[j]]}：目标（虚线）与实际，度", None,
                                      [(rs["t"], Gr - Gr.mean(), "真机目标", "#fdba74"), (rs["t"], Pr - Gr.mean(), "真机实际", "#c2410c"),
                                       (ss["t"], Gs - Gs.mean() + 0, "仿真目标", "#93c5fd"), (ss["t"], Ps - Gs.mean(), "仿真实际", "#2563eb")]))
    jl = []
    for j in LEGS:
        n = NAMES[j]
        a, b = R["joints"][n], S["joints"][n]
        bad = a["amp"] < 0.7 * b["amp"] or (a["dead"] or 0) > 0.3
        jl.append(f'<div class="row"><b>{CN[n]}</b><span class="r">真机 幅度 {a["amp"]:.2f} 滞后 {a["lag"]} 死区 {a["dead"]}'
                  f' 误差 {a["err_deg"]}°</span><span class="s">仿真 幅度 {b["amp"]:.2f} 滞后 {b["lag"]} 死区 {b["dead"]}'
                  f' 误差 {b["err_deg"]}°</span>{"<span class=flag>差得多</span>" if bad else ""}</div>')
    res_real = "摔倒" if p["outcome"] == "fell" else "没摔"
    res_sim = {"fell": "摔倒", "up": "没摔"}.get(p.get("sim_outcome"), "未评分")
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>仿真真机差异 {html.escape(p['when'])}</title><style>{CSS}</style></head><body><main>
<p><a href="index.html">← 全部动作</a></p>
<h1>{html.escape(p['when'])} {html.escape(p['kind'])}：真机{res_real}，仿真{res_sim}</h1>
<p class="mut">同一串命令在仿真里重放（as-built 模型，同电压，同丢包率）。橙色真机，蓝色仿真。电压 {R.get('volt')} V，命令 {html.escape(json.dumps(p.get('commands'), ensure_ascii=False)[:200])}</p>
<h2>差异一览（红色 = 真机和仿真差两倍以上）</h2><div class="cards">{cards}</div>
<h2>IMU：躯干角速度、姿态和频谱</h2><div class="grid2">{''.join(charts)}</div>
<h2>舵机跟随：目标和实际</h2><p class="mut">每条线减去目标的平均值；实际线比目标线平、晚，就是跟不上。</p><div class="grid2">{''.join(joint_charts)}</div>
<h2>每个腿关节</h2>{''.join(jl)}
<h2>旷量指标怎么算</h2><p>舵机编码器装在舵机输出轴上，舵盘、连杆、螺丝和鞋底的间隙它看不到。这里用编码器读到的关节角，在模型上算出“支撑脚平贴地面时躯干应该是什么姿态”，再和 IMU 实测的姿态比。差出来的角度就是关节解释不了的躯干晃动：舵盘和连杆的间隙、螺丝松动、鞋底变形都在里面。只在静站时算：走路时鞋底在滚、支撑脚在换，刚体预测本身就差几度（仿真里也一样），分不出旷量。仿真是刚体，静站时这个数接近 0，真机多出来的部分就是模型里缺的那块。拧紧螺丝前后各站一次，这个数应该下降。走路时的松动看“5 Hz 以上抖动占比”和频谱。</p>
</main></body></html>"""


def index_page(recs):
    rows = []
    for r in sorted(recs, key=lambda x: x["when"], reverse=True)[:300]:
        R, S = r["real"], r["sim"]
        jr = np.mean(R["jitter"]) / max(np.mean(S["jitter"]), 1e-6)
        play = (f'<span>静站旷量 {R["play_rms"]:.2f}° vs {S["play_rms"]:.2f}°</span>'
                if R.get("play_rms") is not None and S.get("play_rms") is not None else "")
        flag = "flag" if r["outcome"] == "fell" else ""
        rows.append(f'<div class="row"><a href="{html.escape(r["id"])}.html">{html.escape(r["when"])} {html.escape(r["kind"])}</a>'
                    f'<span class="{flag}">{"真机摔" if r["outcome"] == "fell" else "真机没摔"}</span>'
                    f'<span>抖动 {jr:.1f}x</span>{play}'
                    f'<span>跟随 {R["amp"]:.2f} vs {S["amp"]:.2f}</span><span>死区 {R["dead"]}</span>'
                    f'<span>{R.get("volt")} V</span></div>')
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>仿真真机差异</title><style>{CSS}</style></head><body><main><h1>仿真和真机的差异，每个动作一页</h1>
<p class="mut">真机每做完一个动作，运行账本把同一串命令在仿真里重放，这里比较两边的 IMU、舵机跟随和旷量指标。更新于 {time.strftime('%Y-%m-%d %H:%M:%S')}。</p>
{''.join(rows)}</main></body></html>"""


def latest(recs):
    """Pre-run card for the phone remote: the newest action's readings against this robot's own history.

    Each item: ok True (normal), False (worth a look before the next run) or None (not measured yet). The play
    measure of the newest standing action is compared with the median of earlier ones, so a loosened screw shows
    as a rise even though the robot never matches the rigid sim."""
    recs = sorted(recs, key=lambda r: r.get("t0", 0))
    items = []
    for key, label, hint in (("play_static", "旷量（关节静止时躯干的松动）", "：比平时大，查螺丝和舵盘"),
                             ("play_moving", "受力让量（关节在动时躯干没跟上）", "：比平时大，查踝、髋偏航的舵盘和鞋底")):
        stand = [r for r in recs if r["real"].get(key) is not None and r["sim"].get(key) is not None]
        if not stand:
            continue
        now, hist = stand[-1], [r["real"][key] for r in stand[:-1]][-30:]
        med = float(np.median(hist)) if hist else None
        ok = None if med is None else now["real"][key] <= 1.5 * med
        items.append({"label": label, "ok": ok, "page": now["id"] + ".html",
                      "detail": f'{now["when"][11:]} 真机 {now["real"][key]:.2f}°，仿真 {now["sim"][key]:.2f}°'
                                + (f'，平时 {med:.2f}°' if med is not None else "，还没有往常数据")
                                + ("" if ok is not False else hint)})
    moves = [r for r in recs if r["kind"] in ("walk", "turn")]
    if moves:
        now = moves[-1]
        R, S = now["real"], now["sim"]
        hist = [float(np.mean(r["real"]["jitter"])) for r in moves[:-1]][-30:]
        jit = float(np.mean(R["jitter"]))
        med = float(np.median(hist)) if hist else None
        ok = None if med is None else jit <= 1.4 * med
        items.append({"label": "走路抖动（逐拍角速度变化）", "ok": ok, "page": now["id"] + ".html",
                      "detail": f'{now["when"][11:]} {now["kind"]} 真机 {jit:.2f}，仿真 {float(np.mean(S["jitter"])):.2f} rad/s'
                                + (f'，平时 {med:.2f}' if med is not None else "")
                                + ("" if ok is not False else "：比平时大")})
        items.append({"label": "最大偏航角速度", "ok": R["yaw_max"] < 4.5, "page": now["id"] + ".html",
                      "detail": f'真机 {R["yaw_max"]:.1f}，仿真 {S["yaw_max"]:.1f} rad/s（摔倒前常冲到 6 以上）'})
        bad = [CN[n] for n, v in R["joints"].items() if v["amp"] < 0.7 * S["joints"][n]["amp"]]
        items.append({"label": "舵机跟随", "ok": not bad, "page": now["id"] + ".html",
                      "detail": f'实际/目标 {R["amp"]:.2f}（仿真 {S["amp"]:.2f}），滞后 {R["lag"]:.1f} 拍（仿真 {S["lag"]:.1f}）'
                                + (f'；明显跟不上：{"、".join(bad)}' if bad else "")})
        if R.get("cur_max") is not None:
            items.append({"label": "腿部最大电流", "ok": R["cur_max"] < 1100, "page": now["id"] + ".html",
                          "detail": f'{R["cur_max"]} mA（正常行走 0.6 到 0.9 A）'})
        if R.get("volt") is not None:
            items.append({"label": "电压", "ok": None, "page": now["id"] + ".html",
                          "detail": f'{R["volt"]} V（仿真按同一电压重放）'})
    return {"t": time.time(), "when": time.strftime("%Y-%m-%d %H:%M:%S"), "items": items,
            "failed": sum(1 for i in items if i["ok"] is False), "actions": len(recs)}


def strip(p):
    return {**p, "real": {k: v for k, v in p["real"].items() if k != "_series"},
            "sim": {k: v for k, v in p["sim"].items() if k != "_series"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["auto", "one"])
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--kinds", default="walk,turn,balance,bend")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    t_start = time.time()
    record = {"ts": round(t_start, 1), "when": time.strftime("%Y-%m-%d %H:%M:%S"), "status": "ok", "drawn": 0,
              "skipped": 0, "error": None}
    try:
        eps = [json.loads(l) for l in open(EPISODES)]
        summ = os.path.join(OUT, "summary.jsonl")
        # a live log is cut again as it grows: an action is redrawn when its sim replay changed (new cache key)
        done = {(r["id"], r["sim_log"]) for r in map(json.loads, open(summ))} if os.path.exists(summ) else set()
        kinds = set(a.kinds.split(","))
        todo = [e for e in eps if (a.what == "one" and e["id"] == a.episode)
                or (a.what == "auto" and e["kind"] in kinds and e.get("replayable")
                    and sim_tick_log(e["id"]) and (e["id"], os.path.basename(sim_tick_log(e["id"]))) not in done)]
        kin = Kin()
        cp = os.path.join(DATA, "scorecard-auto.json")
        card = {r["id"]: r["sim"] for r in json.load(open(cp))["results"]} if os.path.exists(cp) else {}
        new = []
        for e in todo:
            try:
                p = pair(e, kin, card)
            except Exception:
                record["skipped"] += 1
                record["error"] = traceback.format_exc()[-600:]
                continue
            if not p:
                record["skipped"] += 1
                continue
            with open(os.path.join(OUT, e["id"] + ".html"), "w") as f:
                f.write(page(p))
            new.append(strip(p))
            record["drawn"] += 1
        with open(summ, "a") as f:
            for p in new:
                f.write(json.dumps(p) + "\n")
        recs = list({r["id"]: r for r in map(json.loads, open(summ))}.values()) if os.path.exists(summ) else []
        live = {e["id"] for e in eps}   # actions the ledger no longer lists (a re-cut live log) drop out
        recs = [r for r in recs if r["id"] in live]
        for name, text in (("index.html", index_page(recs)), ("latest.json", json.dumps(latest(recs), ensure_ascii=False))):
            with open(os.path.join(OUT, name + ".tmp"), "w") as f:
                f.write(text)
            os.replace(os.path.join(OUT, name + ".tmp"), os.path.join(OUT, name))
        record["actions"] = len(recs)
        if record["error"]:   # an action that cannot be drawn keeps the run red until it is fixed
            record["status"] = "error"
    except Exception:
        record["status"], record["error"] = "error", traceback.format_exc()[-800:]
    record["dur_s"] = round(time.time() - t_start, 1)
    os.makedirs(DATA, exist_ok=True)
    with open(RUNS, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(json.dumps(record))
    return 0 if record["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
