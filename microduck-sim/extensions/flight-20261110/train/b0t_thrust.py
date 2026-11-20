"""Stage B0T of ../TRAIN-CONTRACT.json (2026-11-20): is the fan-thrust test well-posed, and does it reproduce results that
are already on record, before any policy is scored on it? Nothing is trained.

  $PY train/b0t_thrust.py [workers=7] [seeds=60] [seed0=4000] [diag=20] [stride=8] [out=yardstick_b0t] [only=<substring>]
  (Mac mini only, through train/b0t_thrust.sh under train/mini_lock.sh)

Why a new test. The thrust test of 12:55 (ts3_thrust_gap.py, out/thrust_gap) held 0.75 to 1.05 of the robot's weight on
the fans for seconds while the feet were on the floor, with a stand-in attitude loop of 0.12 N m/rad that holds the lean
the robot had at thrust start. sim/flight.py, whose take-off and landing rows succeed, passes 0.5 to 1.0 of the weight in
about 0.1 s at take-off and 0.3 s at landing, with a ground attitude loop four times stiffer that aims at level. The thrust
turns with the trunk, so a trunk that leans by an angle a is pushed sideways with thrust x sin(a) while the feet carry
only (1 - thrust share) of the weight. Whether standing at 0.75 and 0.9 can be held at all is therefore asked first, with
the legs out of the question (cell group 0).

Cells (contract threshold items 0 to 3; 60 episodes each on seeds seed0..seed0+59):
  (0) lock_t000 .. lock_t090   sim/flight.py with --legs held --rigid-legs (leg joints locked at the stand pose by joint
      limits; attempt 1 used servo-held legs at gain 400, which tip backward without any thrust), pack fitted
      (sim/out/manifest_pack_nominal.json), the settings of the recorded full-sequence rows (sim/batch.py FIX and the
      ARE_nominal fan), and the new --ground-hold option: the robot settles for 2.0 s, the fans then ramp in 0.5 s to
      0, 0.25, 0.5, 0.75 or 0.9 of the weight and hold it for 10 s with the ground attitude loop of flight.py (target
      level, natural frequency 8 rad/s, integrator frozen on the ground, sensor noise and delay as in flight.py). At 0
      the fans are never armed. "Stands 10 s" = no fall through settle, ramp and hold (the probe's rule: tilt over 45 deg
      or trunk lower than 0.04 m) AND the trunk has moved less than 0.10 m from where it stood at thrust start (the
      12:55 review: the fall rule counted a robot drifting at 0.35 m/s as upright). Both counts are written.
      Seeds change only the sensor noise and gyro bias here: 60 episodes of one cell are close to one result repeated.
      Not in the verdict, 20 episodes each: diag_gi_* at 0.75 and 0.9 (locked legs, attitude integrator running on the
      ground), diag_gi_slow_t090 (the same with the thrust raised to 0.9 over 8 s instead of 0.5 s), and diag_servo_* at
      0 and 0.75 (legs held by the servos at gain 400 instead of locked). They say what would have to change if a level
      of group 0 does not hold.
      Expected from statics, written before any run (held pose: trunk about 4.1 deg nose down, weight line about 35 mm
      behind the toe edge and 15 mm ahead of the heel edge in sim/out/ground rows, centre of mass about 0.147 m up):
      the fans push forward with share x weight x sin(lean), so the feet must carry their load farther forward by
      share x sin(lean) x height / (1 - share x cos(lean)) = 3.5, 10.5, 31 and 92 mm at 0.25, 0.5, 0.75 and 0.9. The
      loop's pull toward level gives 0.035 N m nose up. So 0 to 0.5 should hold, 0.75 is close (about 24 of 35 mm
      used), and 0.9 should tip forward: it needs about 0.11 N m nose up from the fans.
  (1) walk61_none_stand, walk61_none_walk   the deployed pair (runtime-overlay/models) without the pack, zero thrust, the
      gate episode of b0_yardstick.py (stand mode to 2.0 s, command 0 or 0.25 m/s to 17.0 s, zero to 20.0 s).
      walk61_none_stand is the CALM LINE: median action jumps per 10 s and median leg joint travel per 10 s. A standing
      cell flails above max(1.5 x reference, reference + 2) jumps per 10 s (the contract's rule; joint travel is
      written beside it without a limit of its own).
  (2) fq2_pack_stand, fq2_pack_walk   fq2 iteration 1999 (ckpt/fq2_1999) with the pack (manifests/flightpack-nominal.json,
      --stand-s 0 as the pack cells of ts3_gates.py), zero thrust, same episode.
      fq2_fullseq   the full take-off and landing sequence of sim/flight.py as recorded in sim/out/fullseq_handover
      (9 of 9): --legs handover, sim/batch.py FIX, ARE_nominal fan, scenarios hover, table_up, table_down, 20 seeds
      each = 60. Success = flight.py's own full_success.
  (3) walk61_pack_t040, walk61_pack_t050   the deployed pair with the pack and the fans at 0.40 and 0.50 of the weight
      from 0 s (ramp 0.5 s, stand-in loop of sim/walk_case.py at 4 rad/s), zero command, 23 s: the rows thrust40|stand
      (0 of 10) and thrust50|stand (2 of 10) of sim/out/walk/summary.json. Falls are counted over the whole episode as
      there. Manifest: manifests/flightpack-nominal.json, the 19:05 snapshot taken between the first and the last of
      those rows (2026-11-10 19:01 to 19:25); sim/out/manifest_pack_nominal.json was rewritten at 21:36.
Thrust is applied only to a settled robot in group 0 (from 2.0 s; the 12:55 test started at 0.5 s). Group 3 starts at
0 s because the rows it must reproduce did.

Per step. One row per `stride` physics steps (8 = one 20 ms control tick; stride=1 for every 2.5 ms step) goes to
out/<out>/steps/<cell>.npz (one array per episode, columns in `cols`): time, roll, pitch (flight.py's sign: positive =
nose down), tilt, centre of pressure against the box of the soles in the heading frame (offset from the box centre,
margin to heel, toe and nearer side edge), normal force and delivered fan force as shares of the weight, trunk
position, summed leg joint travel, feet on the floor. Normal force, centre of pressure and fan force are means over the
row's physics steps. Summaries per episode are in out/<out>/<cell>.json, per cell in summary.json.

Gain. Before every episode that runs a policy the runtime's walk gain is set to the robot's value (CURRENT-STATE.json
walking_policy, KP_RL 200) and asserted after it; --legs held episodes assert the stand-mode gain 400 in flight.py's row.

Writes out/<out>/<cell>.json and summary.json (with verdict()) after every cell; heartbeat logs/b0t_thrust_heartbeat.txt
(logs/b0t_thrust_<out>_heartbeat.txt for another out), last line DONE or FAILED. A cell whose file is complete is kept
(resume). verdict() evaluates the contract's threshold items as written; where the text leaves a choice (items 1 and 2:
"0 falls of 60 at zero thrust" is read on the standing cell) the walking cell is written beside it.
"""
import contextlib
import hashlib
import io
import json
import math
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FL = HERE.parent
SIM = FL / "sim"
SIMROOT = FL.parents[1]
sys.path.insert(0, str(HERE))
opts = dict(a.split("=", 1) for a in sys.argv[1:])
SEEDS, SEED0, WORKERS = int(opts.get("seeds", 60)), int(opts.get("seed0", 4000)), min(int(opts.get("workers", 7)), 8)
DIAG, STRIDE = int(opts.get("diag", 20)), int(opts.get("stride", 8))
NAME = opts.get("out", "yardstick_b0t")
OUT = HERE / "out" / NAME
HB = HERE / "logs" / ("b0t_thrust_heartbeat.txt" if NAME == "yardstick_b0t" else f"b0t_thrust_{NAME}_heartbeat.txt")
STATE = (HERE / "../../../CURRENT-STATE.json").resolve()
OVERLAY = (HERE / "../../../microduck_rl/cmu/whole/runtime-overlay").resolve()
DEPLOYED, FQ2, POLICY = OVERLAY / "models", HERE / "ckpt/fq2_1999", HERE / "policy"
NONE, PACK = HERE / "manifests/flightpack-none.json", HERE / "manifests/flightpack-nominal.json"
SIM_PACK = SIM / "out" / "manifest_pack_nominal.json"
ONNX = ("walk61.onnx", "stand61.onnx")

N_REQ = 60                                    # the contract counts out of 60
LEVELS = (0.0, 0.25, 0.5, 0.75, 0.9)          # thrust as a share of the whole robot's weight
SETTLE_S, RAMP_S, HOLD_S = 2.0, 0.5, 10.0     # group 0: thrust starts on a settled robot
SLOW_RAMP_S = 8.0                             # diag_gi_slow_t090: thrust rises slowly enough for the integrator to follow
DRIFT_MAX_M = 0.10                            # group 0: farther than this from the place at thrust start is not standing
FIX = ["--com-est", "true", "--ground-pitch", "level", "--takeoff-twr", "1.6", "--takeoff-ramp", "0.1"]  # sim/batch.py FIX
FAN = ["--fan", "areswei"]                    # sim/batch.py case ARE_nominal
SCEN = ("hover", "table_up", "table_down")
FS_PER = max(1, SEEDS // len(SCEN))           # full sequence: seeds per scenario (20 at 60)
REF = "walk61_none_stand"                     # the calm line
THRESHOLD = (
    "(0) well-posedness: legs locked at the stand pose (sim/flight.py --legs held), pack fitted, attitude loop on: 60 of 60 "
    "episodes stand 10 s at each of thrust 0, 0.25, 0.5, 0.75 and 0.9; and a calm line is fixed from walk61 standing at zero "
    "thrust without the pack (median action jumps per 10 s and joint travel per 10 s; a standing cell counts as flailing "
    "above max(1.5 x reference, reference + 2) jumps); (1) walk61 without the pack at zero thrust: 0 falls of 60; (2) fq2 "
    "iteration 1999 with the pack: 0 falls of 60 at zero thrust and at least 54 of 60 successes in the full take-off and "
    "landing sequence of sim/flight.py (its recorded result is 9 of 9, sim/out/fullseq_handover); (3) walk61 with the pack "
    "at thrust 0.40 and 0.50 from 0 s: fall rates inside the 95 % interval of sim/out/walk/summary.json (0 of 10 and 2 of "
    "10), that is at most 15 of 60 and between 2 and 33 of 60; (4) every cell left in the gate is listed with its PASS line "
    "in train/ts3_gates.py under the names REQUIREMENTS.json coverage uses")
LEGS = ("left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle",
        "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle")
COLS = ("t_s", "roll_deg", "pitch_deg", "tilt_deg", "cop_fwd_mm", "cop_left_mm", "heel_margin_mm", "toe_margin_mm",
        "side_margin_mm", "normal_share", "thrust_share", "thrust_up_share", "x_m", "y_m", "z_m", "leg_travel_rad",
        "feet_on", "other_contact_share")
CI = {n: i for i, n in enumerate(COLS)}
LAST = {"w": None}     # gate path: the fan wrench of the current physics step (ts3_thrust.Thrust.apply)


def state_number(pattern):
    value = json.loads(STATE.read_text())["facts"]["walking_policy"]["value"]
    m = re.search(pattern, value)
    assert m, f"{STATE}: walking_policy does not match {pattern!r}"
    return int(m.group(1))


KP_ROBOT = state_number(r"KP_RL (\d+)")           # walk mode, 200
KP_STAND = state_number(r"stand mode KP (\d+)")   # the held legs of sim/flight.py, 400


def tag(f):
    return f"t{int(round(f * 100)):03d}"


def hb(msg):
    HB.parent.mkdir(parents=True, exist_ok=True)
    with open(HB, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def clean_env():
    for k in [k for k in os.environ if k.startswith(("FLIGHT_", "SPK3DIAG_"))]:
        os.environ.pop(k)  # no diagnostic switch of flight_eval is on in a verdict episode


# ---------------------------------------------------------------- per-step log (both simulation paths)
def rpy_of(R):
    """sim/flight.py rpy_of (copied so that the gate path imports nothing new before the probe): pitch > 0 = nose down"""
    return math.atan2(R[2, 1], R[2, 2]), math.asin(-max(-1.0, min(1.0, R[2, 0]))), math.atan2(R[1, 0], R[0, 0])


class Tele:
    """callable(m, d, t) after every physics step: flight_eval.FRAME_HOOK or flight.STEP_HOOK"""

    def __init__(self, thrust_of):
        self.thrust_of = thrust_of      # callable(tele, m, d) -> the fans' force on the trunk this step, world frame, N
        self.rows, self.n, self.tb = [], 0, None
        self.fell, self.fall_dir, self.fall_feet, self.sole_ok = None, None, None, True

    def _init(self, m, d):
        import mujoco
        self.mj = mujoco
        self.tb = m.body("trunk_base").id
        self.feet = (m.geom("left_foot_collision").id, m.geom("right_foot_collision").id)
        self.mesh = []
        for g in self.feet:              # static_gap.sole_points: the foot collision meshes' vertices
            mid = int(m.geom_dataid[g])
            if mid < 0:                  # no mesh behind the foot geom: no sole box, the margins stay empty
                self.sole_ok = False
                mid = 0
            a, k = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
            self.mesh.append(np.array(m.mesh_vert[a:a + k], dtype=float))
        self.is_world = np.asarray(m.geom_bodyid) == 0          # floor and table
        self.W = float(m.body_mass[1:].sum()) * 9.81
        self.qadr = np.array([m.jnt_qposadr[m.joint(n).id] for n in LEGS])
        self.q_prev, self.travel = d.qpos[self.qadr].copy(), 0.0
        self.f6 = np.zeros(6)
        self.acc = np.zeros(6)          # normal force, force x, force y, non-foot normal force, |fan force|, fan force up

    def __call__(self, m, d, t):
        if self.tb is None:
            self._init(m, d)
        on = [False, False]
        for j in range(d.ncon):
            c = d.contact[j]
            g1, g2 = int(c.geom1), int(c.geom2)
            w1, w2 = bool(self.is_world[g1]), bool(self.is_world[g2])
            if w1 == w2:
                continue
            other = g2 if w1 else g1
            self.mj.mj_contactForce(m, d, j, self.f6)
            fn = float(self.f6[0])
            for i in (0, 1):
                if other == self.feet[i]:
                    on[i] = True
            if fn <= 0.0:
                continue
            self.acc[0] += fn
            self.acc[1] += fn * float(c.pos[0])
            self.acc[2] += fn * float(c.pos[1])
            if other not in self.feet:
                self.acc[3] += fn
        fv = np.asarray(self.thrust_of(self, m, d), dtype=float)
        self.acc[4] += float(np.linalg.norm(fv))
        self.acc[5] += float(fv[2])
        q = d.qpos[self.qadr]
        self.travel += float(np.abs(q - self.q_prev).sum())
        self.q_prev = q.copy()
        R = d.xmat[self.tb].reshape(3, 3)
        p = d.xpos[self.tb]
        tilt = math.degrees(math.acos(max(-1.0, min(1.0, float(R[2, 2])))))
        roll, pitch, yaw = rpy_of(R)
        ch, sh = math.cos(yaw), math.sin(yaw)
        if self.fell is None and (tilt > 45.0 or float(p[2]) < 0.04):    # brain_sim_check's fall rule
            fwd, left = float(R[0, 2]) * ch + float(R[1, 2]) * sh, -float(R[0, 2]) * sh + float(R[1, 2]) * ch
            self.fell = round(float(t), 3)
            self.fall_dir = ("forward" if fwd > 0 else "backward") if abs(fwd) >= abs(left) else ("left" if left > 0 else "right")
            self.fall_feet = int(on[0]) + int(on[1])
        self.n += 1
        if self.n % STRIDE:
            return
        k = float(STRIDE)
        row = [float(t), math.degrees(roll), math.degrees(pitch), tilt] + [float("nan")] * 5
        if self.acc[0] > 1e-6 and self.sole_ok:
            try:
                sp = np.vstack([v @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g] for v, g in zip(self.mesh, self.feet)])
                sp = sp[sp[:, 2] < sp[:, 2].min() + 0.003]
                rel = sp[:, :2] - p[:2]
                sx, sy = rel[:, 0] * ch + rel[:, 1] * sh, -rel[:, 0] * sh + rel[:, 1] * ch
                cx_w, cy_w = self.acc[1] / self.acc[0] - p[0], self.acc[2] / self.acc[0] - p[1]
                cx, cy = cx_w * ch + cy_w * sh, -cx_w * sh + cy_w * ch
                row[4:9] = [1000 * (cx - (sx.min() + sx.max()) / 2), 1000 * (cy - (sy.min() + sy.max()) / 2),
                            1000 * (cx - sx.min()), 1000 * (sx.max() - cx), 1000 * min(cy - sy.min(), sy.max() - cy)]
            except Exception:   # a foot geom that is no mesh: the margins stay empty, the rest of the log is kept
                self.sole_ok = False
        row += [self.acc[0] / k / self.W, self.acc[4] / k / self.W, self.acc[5] / k / self.W, float(p[0]), float(p[1]),
                float(p[2]), self.travel, float(int(on[0]) + int(on[1])), self.acc[3] / k / self.W]
        self.rows.append(row)
        self.acc[:] = 0.0

    def array(self):
        return np.array(self.rows, dtype=np.float32).reshape(-1, len(COLS))


SUMMARY_KEYS = ("pitch_before_deg", "pitch_mean_deg", "pitch_min_deg", "pitch_max_deg", "pitch_end_deg", "roll_mean_deg",
                "roll_min_deg", "roll_max_deg", "tilt_max_deg", "cop_fwd_mean_mm", "cop_left_mean_mm", "heel_margin_min_mm",
                "toe_margin_min_mm", "side_margin_min_mm", "normal_share_mean", "thrust_share_mean", "thrust_share_peak",
                "thrust_over_cmd", "drift_net_m", "drift_max_m", "trunk_z_min_m", "leg_travel_rad_per_10s", "feet_any_share",
                "feet_both_share", "other_contact_share_max")


def tele_summary(A, t0, th, t1, cmd):
    """One episode's numbers from its per-step rows. Window = t0 (thrust start, or the end of settling) to t1 (the fall,
    or the end); hold = th (thrust at its level) to t1; cmd = the commanded thrust share (None: no fixed level)."""
    out = dict.fromkeys(SUMMARY_KEYS)
    if A.shape[0] == 0:
        return out
    t = A[:, 0]
    w, h, pre = A[(t >= t0 - 1e-4) & (t < t1)], A[(t >= th - 1e-4) & (t < t1)], A[(t >= t0 - 0.5) & (t < t0 - 1e-4)]

    def st(B, name, fn, nd=2):
        v = B[:, CI[name]].astype(float)
        v = v[np.isfinite(v)]
        return round(float(fn(v)), nd) if v.size else None

    out.update(pitch_before_deg=st(pre, "pitch_deg", np.mean))
    if w.shape[0]:
        out.update(pitch_mean_deg=st(w, "pitch_deg", np.mean), pitch_min_deg=st(w, "pitch_deg", np.min),
                   pitch_max_deg=st(w, "pitch_deg", np.max), pitch_end_deg=round(float(w[-1, CI["pitch_deg"]]), 2),
                   roll_mean_deg=st(w, "roll_deg", np.mean), roll_min_deg=st(w, "roll_deg", np.min),
                   roll_max_deg=st(w, "roll_deg", np.max), tilt_max_deg=st(w, "tilt_deg", np.max),
                   heel_margin_min_mm=st(w, "heel_margin_mm", np.min, 1), toe_margin_min_mm=st(w, "toe_margin_mm", np.min, 1),
                   side_margin_min_mm=st(w, "side_margin_mm", np.min, 1), thrust_share_peak=st(w, "thrust_share", np.max, 3),
                   trunk_z_min_m=st(w, "z_m", np.min, 4), feet_any_share=round(float(np.mean(w[:, CI["feet_on"]] >= 1)), 3),
                   feet_both_share=round(float(np.mean(w[:, CI["feet_on"]] >= 2)), 3),
                   other_contact_share_max=st(w, "other_contact_share", np.max, 3))
        dxy = np.hypot(w[:, CI["x_m"]] - w[0, CI["x_m"]], w[:, CI["y_m"]] - w[0, CI["y_m"]]).astype(float)
        out.update(drift_net_m=round(float(dxy[-1]), 3), drift_max_m=round(float(dxy.max()), 3))
        span = float(w[-1, 0] - w[0, 0])
        if span > 0.2:
            out.update(leg_travel_rad_per_10s=round(float(w[-1, CI["leg_travel_rad"]] - w[0, CI["leg_travel_rad"]]) / span * 10, 3))
    if h.shape[0]:
        out.update(cop_fwd_mean_mm=st(h, "cop_fwd_mm", np.mean, 1), cop_left_mean_mm=st(h, "cop_left_mm", np.mean, 1),
                   normal_share_mean=st(h, "normal_share", np.mean, 3), thrust_share_mean=st(h, "thrust_share", np.mean, 3))
        if cmd and out["thrust_share_mean"] is not None:
            out.update(thrust_over_cmd=round(out["thrust_share_mean"] / cmd, 3))
    return out


# ---------------------------------------------------------------- cells
def cells():
    c = {}

    def hold(f, role, n, more=(), ramp=RAMP_S):
        return dict(path="flight", role=role, n=n, frac=f, ramp=ramp,
                    flags=["--scenario", "hover", "--case", "b0t", "--legs", "held", "--arm-at", str(SETTLE_S), "--ground-hold", str(f),
                           "--ground-hold-s", str(HOLD_S), "--ground-hold-ramp", str(ramp)] + FIX + FAN + list(more))

    # Attempt 2 (2026-11-20): "locked" means the leg joints locked by joint limits (--rigid-legs). Attempt 1's smoke showed
    # the servo-held open-loop pose with the pack sagging about 2.8 deg nose-up in 2.6 s and tipping backward at 3.39 s with
    # the fans never armed, so a servo-held leg cannot be the control of a thrust question. It stays as diag_servo_*.
    lock = ["--rigid-legs"]
    for f in LEVELS:
        c[f"lock_{tag(f)}"] = hold(f, "item 0", SEEDS, lock)
    c["fq2_fullseq"] = dict(path="flight", role="item 2", n=len(SCEN) * FS_PER, frac=None, ramp=None,
                            flags=["--case", "ARE_nominal", "--legs", "handover"] + FIX + FAN)
    for f in (0.75, 0.9):
        c[f"diag_gi_{tag(f)}"] = hold(f, "diagnostic", DIAG, lock + ["--ground-i"])
    for f in (0.0, 0.75):
        c[f"diag_servo_{tag(f)}"] = hold(f, "diagnostic", DIAG)
    c["diag_gi_slow_t090"] = hold(0.9, "diagnostic", DIAG, lock + ["--ground-i"], ramp=SLOW_RAMP_S)
    gate = dict(path="gate", n=SEEDS, extra=[], thrust=None, ep_s=20.0, t0=2.0, th=2.0, cmd=None)
    c[REF] = dict(gate, role="item 1 and the calm line", models=str(DEPLOYED), manifest=str(NONE), case="stand")
    c["walk61_none_walk"] = dict(gate, role="beside item 1", models=str(DEPLOYED), manifest=str(NONE), case="walk")
    s0 = ["--stand-s", "0"]
    c["fq2_pack_stand"] = dict(gate, role="item 2", models=str(FQ2), manifest=str(PACK), case="stand", extra=s0)
    c["fq2_pack_walk"] = dict(gate, role="beside item 2", models=str(FQ2), manifest=str(PACK), case="walk", extra=s0)
    for f in (0.40, 0.50):   # sim/walk_batch.py: BASE --stand-s 0, command "stand" --walk-at 3 --walk-s 17 --vx 0, --thrust-at 0
        c[f"walk61_pack_{tag(f)}"] = dict(
            gate, role="item 3", models=str(DEPLOYED), manifest=str(PACK), case="stand",
            extra=s0 + ["--walk-at", "3", "--walk-s", "17"], ep_s=23.0, t0=0.0, th=0.5, cmd=f,
            thrust=dict(unit="whole", pts=[[0.0, 0.0], [0.5, f]], att_wn=4.0))
    if "only" in opts:
        c = {k: v for k, v in c.items() if opts["only"] in k}
    return c


def jobs_of(label, spec):
    if spec["path"] == "gate":
        return [(label, spec, s) for s in range(SEED0, SEED0 + spec["n"])]
    if label == "fq2_fullseq":
        return [(label, spec["flags"] + ["--scenario", sc], s, f"{sc}_s{s}", None, None)
                for sc in SCEN for s in range(SEED0, SEED0 + FS_PER)]
    return [(label, spec["flags"], s, f"s{s}", spec["frac"], spec["ramp"]) for s in range(SEED0, SEED0 + spec["n"])]


# ---------------------------------------------------------------- one episode, sim/flight.py path (a fresh process each)
def one_flight(job):
    label, flags, seed, key, frac, ramp = job
    clean_env()
    import ts3_thrust
    F = ts3_thrust._flight()     # sim/flight.py, imported the way sim/walk_case.py and ts3_thrust.py import it
    if str(SIM) not in sys.path:
        sys.path.insert(0, str(SIM))
    handover = "handover" in flags
    kp_found = None
    if handover:
        import policy_legs      # as flight.run does: brings in the runtime's walk_brain
        wb = sys.modules["walk_brain"]
        kp_found = int(wb.KP_RL)
        wb.KP_RL = KP_ROBOT
        assert Path(policy_legs.POLICY_DIR).resolve() == POLICY.resolve(), policy_legs.POLICY_DIR
    tele = Tele(lambda tl, m, d: d.xfrc_applied[tl.tb, 0:3])
    keep, buf, t_wall = sys.argv, io.StringIO(), time.time()
    sys.argv = ["flight.py"] + list(flags) + ["--seed", str(seed)]
    F.STEP_HOOK = tele
    try:
        with contextlib.redirect_stdout(buf):
            F.main()
    finally:
        sys.argv, F.STEP_HOOK = keep, None
    row = json.loads(buf.getvalue().strip().splitlines()[-1])
    A = tele.array()
    ep = dict(key=key, seed=seed, legs=row["legs"], mass_g=row["mass_g"], secs=round(time.time() - t_wall, 2),
              kp_rl=None, kp_rl_found_on_entry=kp_found, servo_kp_held=row["params"]["kp"],
              fell_at=tele.fell, fall_dir=tele.fall_dir, fall_feet_on=tele.fall_feet, cop_margins_logged=tele.sole_ok,
              flight_fell45_at=row.get("fell45_at"), flight_fell60_at=row.get("fell_at"),
              mixer_saturated_s=row.get("mixer_saturated_s"), support_end=row.get("support_end"),
              tilt_end_deg=row.get("tilt_end_deg"), phase_end=row.get("phase_end"))
    if handover:
        ep["kp_rl"] = int(sys.modules["walk_brain"].KP_RL)
        assert ep["kp_rl"] == KP_ROBOT, f"{label} {key}: the episode ran at walk gain {ep['kp_rl']}, not {KP_ROBOT}"
        assert row["legs"] == "handover" and row["policy"]["first_tick_s"] is not None, f"{label} {key}: no policy tick"
    else:
        assert row["legs"] == "held" and row["params"]["kp"] == KP_STAND, f"{label} {key}: held legs at gain {row['params']['kp']}"
    if frac is None:    # the full sequence: flight.py's own outcome
        scenario = flags[flags.index("--scenario") + 1]
        ep.update(scenario=scenario, full_success=bool(row["full_success"]), airborne_success=bool(row["airborne_success"]),
                  flight_success=bool(row["success"]), fell45_phase=row.get("fell45_phase"), liftoff=row.get("liftoff"),
                  disarm_t=row.get("disarm_t"), after_disarm_s=row.get("after_disarm_s"), max_tilt_deg=row.get("max_tilt_deg"),
                  touchdown_tilt_deg=row.get("touchdown_tilt_deg"), landing_vz_mps=row.get("landing_vz_mps"),
                  takeoff_pitch_excursion_deg=row.get("takeoff_pitch_excursion_deg"), nacelle_hit_at=row.get("nacelle_hit_at"),
                  policy=row.get("policy"))
        t_last = float(A[-1, 0]) + 1e-3 if A.shape[0] else 0.0
        ep.update(tele_summary(A, 0.0, 0.0, t_last, None))
    else:               # standing on the ground with the fans carrying frac of the weight
        gh = row["ground_hold"]
        assert abs(gh["frac"] - frac) < 1e-9 and gh["armed"] == (frac > 0), f"{label} {key}: {gh}"
        reached = gh["t_end"] >= SETTLE_S + ramp + HOLD_S - 0.01
        t1 = tele.fell if tele.fell is not None else gh["t_end"] + 1e-3
        ep.update(tele_summary(A, SETTLE_S, SETTLE_S + ramp, t1, frac if frac > 0 else None))
        ep.update(thrust_share_commanded=frac, ramp_s=ramp, lifted_off_at=gh["first_air"], run_end_s=gh["t_end"],
                  stood_no_fall=bool(tele.fell is None and reached))
        ep["stood"] = bool(ep["stood_no_fall"] and ep["drift_net_m"] is not None and ep["drift_net_m"] <= DRIFT_MAX_M)
    return label, ep, A


# ---------------------------------------------------------------- one episode, gate path (flight_eval.episode)
def one_gate(job):
    label, spec, seed = job
    clean_env()
    if spec["thrust"]:
        os.environ["FLIGHT_THRUST"] = json.dumps(spec["thrust"])
    import flight_eval as fe
    import ts3_thrust
    base = getattr(ts3_thrust, "_b0t_base", None) or ts3_thrust.Thrust   # worker processes are reused: never wrap a wrapper
    ts3_thrust._b0t_base = base

    class Rec(base):        # same force model; the wrench of every step is also kept for the per-step log
        def apply(self, m, d, t):
            LAST["w"] = super().apply(m, d, t)
            return LAST["w"]

    ts3_thrust.Thrust = Rec
    LAST["w"] = None
    tele = Tele(lambda tl, m, d: LAST["w"][0:3] if LAST["w"] is not None else np.zeros(3))
    wb = sys.modules.get("walk_brain")   # None in a fresh worker; a reused one keeps what the last episode left
    kp_found = None if wb is None else int(wb.KP_RL)
    if wb is not None:
        wb.KP_RL = KP_ROBOT
    t_wall = time.time()
    fe.FRAME_HOOK = tele
    try:
        r = fe.episode((spec["models"], spec["manifest"], spec["case"], seed, 0.0, 8.0, False, spec["extra"]))
    finally:
        fe.FRAME_HOOK = None
        ts3_thrust.Thrust = base
    kp = int(sys.modules["walk_brain"].KP_RL)
    assert kp == KP_ROBOT, f"{label} seed {seed}: the episode ran at walk gain {kp}, not {KP_ROBOT}"
    assert r.get("priv_first") is None, f"{label}: a privileged input was read"
    assert (r.get("thrust") is not None) == bool(spec["thrust"]), f"{label} seed {seed}: thrust record {r.get('thrust')}"
    A = tele.array()
    fell = r["fell_at"]
    ep = {k: r.get(k) for k in ("seed", "fell_at", "fall_dir", "max_tilt", "speed", "dist_x", "action_jumps", "thrust", "trunk_z_m")}
    ep.update(key=f"s{seed}", kp_rl=kp, kp_rl_found_on_entry=kp_found, secs=round(time.time() - t_wall, 2),
              tele_fell_at=tele.fell, fall_feet_on=tele.fall_feet, cop_margins_logged=tele.sole_ok,
              jumps_per_10s=round(r["action_jumps"] / max(fell if fell is not None else spec["ep_s"], 0.5) * 10, 1))
    ep.update(tele_summary(A, spec["t0"], spec["th"], fell if fell is not None else spec["ep_s"] + 1e-3, spec["cmd"]))
    return label, ep, A


# ---------------------------------------------------------------- per cell
def wilson(k, n):
    z = 1.96
    p = k / n
    mid, half = (p + z * z / (2 * n)) / (1 + z * z / n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, mid - half), 3), round(min(1.0, mid + half), 3)]


def summarise(label, spec, eps):
    eps = sorted(eps, key=lambda e: (e.get("scenario") or "", e["seed"]))
    n = len(eps)

    def vals(k):
        return sorted(e[k] for e in eps if e.get(k) is not None)

    def med(k):
        v = vals(k)
        return v[len(v) // 2] if v else None

    def quart(k):
        v = vals(k)
        return [v[len(v) // 4], v[(3 * len(v)) // 4]] if v else None

    def ext(k, fn):
        v = vals(k)
        return fn(v) if v else None

    s = dict(cell=label, role=spec["role"], path=spec["path"], seeds=n, seed0=SEED0,
             flags=spec.get("flags") or spec.get("extra"), thrust=spec.get("thrust") or spec.get("frac"),
             secs_per_episode_median=med("secs"), kp_rl=sorted({e["kp_rl"] for e in eps if e.get("kp_rl") is not None}),
             cop_margins_logged=all(e.get("cop_margins_logged", True) for e in eps))
    if label == "fq2_fullseq":
        ok = [e["full_success"] for e in eps]
        s.update(successes=sum(ok), successes_wilson95=wilson(sum(ok), n), airborne_successes=sum(e["airborne_success"] for e in eps),
                 by_scenario={sc: dict(successes=sum(e["full_success"] for e in eps if e["scenario"] == sc),
                                       of=sum(1 for e in eps if e["scenario"] == sc)) for sc in SCEN},
                 failed=[dict(key=e["key"], fell45_at=e["flight_fell45_at"], fell45_phase=e["fell45_phase"], phase_end=e["phase_end"],
                              airborne_success=e["airborne_success"], nacelle_hit_at=e["nacelle_hit_at"]) for e in eps if not e["full_success"]],
                 takeoff_pitch_excursion_deg_max=ext("takeoff_pitch_excursion_deg", max), mass_g=med("mass_g"))
    else:
        fell = [e["fell_at"] is not None for e in eps]
        s.update(falls=sum(fell), falls_wilson95=wilson(sum(fell), n), fall_times=vals("fell_at"),
                 fall_dirs=dict(Counter(e["fall_dir"] for e in eps if e["fell_at"] is not None)),
                 falls_per_block_of_10=[sum(fell[i:i + 10]) for i in range(0, n, 10)],
                 falls_with_feet_on_floor=sum(1 for e in eps if e["fell_at"] is not None and (e.get("fall_feet_on") or 0) > 0))
    if spec["path"] == "flight" and spec["frac"] is not None:
        s.update(stood=sum(e["stood"] for e in eps), stood_no_fall=sum(e["stood_no_fall"] for e in eps),
                 lifted_off=sum(1 for e in eps if e["lifted_off_at"] is not None), mass_g=med("mass_g"),
                 pitch_end_deg_median=med("pitch_end_deg"), mixer_saturated_s_max=ext("mixer_saturated_s", max))
    if spec["path"] == "gate":
        sp = [e["speed"] for e in eps if e["speed"] is not None and e["fell_at"] is None]
        s.update(jumps_per_10s_median=med("jumps_per_10s"), jumps_per_10s_quartiles=quart("jumps_per_10s"),
                 speed_mean_upright=round(sum(sp) / len(sp), 4) if sp else None, max_tilt=ext("max_tilt", max))
        if spec["thrust"]:
            got = [e["thrust"]["mean_fan_sum_over_commanded"] for e in eps if e.get("thrust") and e["thrust"]["mean_fan_sum_over_commanded"]]
            s.update(fan_sum_over_commanded_mean=round(sum(got) / len(got), 3) if got else None,
                     fan_peak_share_max=max((e["thrust"]["peak_share_of_robot_weight"] for e in eps if e.get("thrust")), default=None))
    s.update(leg_travel_rad_per_10s_median=med("leg_travel_rad_per_10s"), leg_travel_rad_per_10s_quartiles=quart("leg_travel_rad_per_10s"),
             pitch_before_deg_median=med("pitch_before_deg"), pitch_mean_deg_median=med("pitch_mean_deg"),
             pitch_min_deg=ext("pitch_min_deg", min), pitch_max_deg=ext("pitch_max_deg", max),
             roll_min_deg=ext("roll_min_deg", min), roll_max_deg=ext("roll_max_deg", max), tilt_max_deg=ext("tilt_max_deg", max),
             cop_fwd_mean_mm_median=med("cop_fwd_mean_mm"), cop_left_mean_mm_median=med("cop_left_mean_mm"),
             heel_margin_min_mm=ext("heel_margin_min_mm", min), toe_margin_min_mm=ext("toe_margin_min_mm", min),
             side_margin_min_mm=ext("side_margin_min_mm", min), heel_margin_min_mm_median=med("heel_margin_min_mm"),
             toe_margin_min_mm_median=med("toe_margin_min_mm"), normal_share_mean_median=med("normal_share_mean"),
             thrust_share_mean_median=med("thrust_share_mean"), thrust_share_peak_max=ext("thrust_share_peak", max),
             thrust_over_cmd_median=med("thrust_over_cmd"), drift_net_m_median=med("drift_net_m"),
             drift_net_m_max=ext("drift_net_m", max), feet_any_share_min=ext("feet_any_share", min),
             other_contact_share_max=ext("other_contact_share_max", max))
    return s


def gate_names():
    """(names REQUIREMENTS.json FP-R8 coverage uses, {name: listed as a quoted name in ts3_gates.py})"""
    req = json.loads((FL / "REQUIREMENTS.json").read_text())["requirements"]
    names = next((r.get("coverage", {}).get("gate_cells", []) for r in req if r.get("id") == "FP-R8"), [])
    text = (HERE / "ts3_gates.py").read_text()
    return names, {n: f'"{n}"' in text for n in names}


def verdict(summ):
    """The contract's threshold items as written (THRESHOLD). An item is complete only on 60 episodes per cell."""
    def full(s):
        return s is not None and s["seeds"] == N_REQ

    ref = summ.get(REF)
    calm = None
    if ref is not None and ref["jumps_per_10s_median"] is not None:
        r = ref["jumps_per_10s_median"]
        calm = dict(cell=REF, seeds=ref["seeds"], jumps_per_10s_median=r, jumps_per_10s_quartiles=ref["jumps_per_10s_quartiles"],
                    flail_limit_jumps_per_10s=round(max(1.5 * r, r + 2), 2),
                    leg_travel_rad_per_10s_median=ref["leg_travel_rad_per_10s_median"],
                    leg_travel_rad_per_10s_quartiles=ref["leg_travel_rad_per_10s_quartiles"])
    out = {}
    # (0) locked legs stand 10 s at every level, and the calm line exists
    lock = {tag(f): summ.get(f"lock_{tag(f)}") for f in LEVELS}
    c0 = all(full(s) for s in lock.values()) and full(ref) and calm is not None
    out["0_locked_legs_stand"] = {
        "complete": c0, "pass": bool(c0 and all(s["stood"] == N_REQ for s in lock.values())),
        "stood_10s": {k: None if s is None else s["stood"] for k, s in lock.items()},
        "no_fall": {k: None if s is None else s["stood_no_fall"] for k, s in lock.items()},
        "of": {k: None if s is None else s["seeds"] for k, s in lock.items()},
        "fall_dirs": {k: None if s is None else s["fall_dirs"] for k, s in lock.items()},
        "fall_times_median": {k: None if s is None or not s["fall_times"] else s["fall_times"][len(s["fall_times"]) // 2] for k, s in lock.items()},
        "toe_margin_min_mm": {k: None if s is None else s["toe_margin_min_mm"] for k, s in lock.items()},
        "heel_margin_min_mm": {k: None if s is None else s["heel_margin_min_mm"] for k, s in lock.items()},
        "drift_net_m_max": {k: None if s is None else s["drift_net_m_max"] for k, s in lock.items()},
        "calm_line": calm,
        "diagnostics_not_in_the_verdict": {k: dict(stood=s["stood"], no_fall=s["stood_no_fall"], of=s["seeds"], fall_dirs=s["fall_dirs"])
                                           for k, s in summ.items() if k.startswith("diag_")}}
    # (1) walk61 without the pack at zero thrust
    wk = summ.get("walk61_none_walk")
    out["1_walk61_no_pack"] = {"complete": full(ref), "pass": bool(full(ref) and ref["falls"] == 0),
                               "standing_falls": None if ref is None else ref["falls"], "of": None if ref is None else ref["seeds"],
                               "walking_falls_beside_it": None if wk is None else wk["falls"],
                               "pass_if_walking_counts_too": bool(full(ref) and full(wk) and ref["falls"] == 0 and wk["falls"] == 0)}
    # (2) fq2 iteration 1999 with the pack: zero thrust, and the full sequence
    fs_, fw, fq = summ.get("fq2_pack_stand"), summ.get("fq2_pack_walk"), summ.get("fq2_fullseq")
    c2 = full(fs_) and full(fq)
    out["2_fq2_with_pack"] = {"complete": c2, "pass": bool(c2 and fs_["falls"] == 0 and fq["successes"] >= 54),
                              "standing_falls": None if fs_ is None else fs_["falls"], "full_sequence_successes": None if fq is None else fq["successes"],
                              "full_sequence_by_scenario": None if fq is None else fq["by_scenario"], "full_sequence_needed": 54,
                              "of": N_REQ, "walking_falls_beside_it": None if fw is None else fw["falls"],
                              "pass_if_walking_counts_too": bool(c2 and full(fw) and fs_["falls"] == 0 and fw["falls"] == 0 and fq["successes"] >= 54)}
    # (3) walk61 with the pack at 0.40 and 0.50 from 0 s against sim/out/walk/summary.json
    a, b = summ.get("walk61_pack_t040"), summ.get("walk61_pack_t050")
    c3 = full(a) and full(b)
    out["3_walk_reference"] = {"complete": c3, "pass": bool(c3 and a["falls"] <= 15 and 2 <= b["falls"] <= 33),
                               "falls_at_040": None if a is None else a["falls"], "limit_at_040": "at most 15 of 60",
                               "falls_at_050": None if b is None else b["falls"], "limit_at_050": "between 2 and 33 of 60",
                               "reference": "sim/out/walk/summary.json thrust40|stand 0 of 10, thrust50|stand 2 of 10"}
    # (4) the gate lists every thrust cell under the names the requirement's coverage uses
    names, listed = gate_names()
    out["4_gate_lists_the_cells"] = {"complete": True, "pass": bool(names) and all(listed.values()), "names": names, "listed_in_ts3_gates": listed,
                                     "note": "checks the names only; a PASS line per cell in ts3_gates.py is read by a person"}
    # the owner's no-flailing rule on the standing cells that run a policy
    flail = {}
    for k in ("fq2_pack_stand", "walk61_pack_t040", "walk61_pack_t050"):
        s = summ.get(k)
        if s is not None and calm is not None and s["jumps_per_10s_median"] is not None:
            ratio = (None if not calm["leg_travel_rad_per_10s_median"] or s["leg_travel_rad_per_10s_median"] is None
                     else round(s["leg_travel_rad_per_10s_median"] / calm["leg_travel_rad_per_10s_median"], 2))
            flail[k] = dict(jumps_per_10s_median=s["jumps_per_10s_median"], limit=calm["flail_limit_jumps_per_10s"],
                            flailing=s["jumps_per_10s_median"] > calm["flail_limit_jumps_per_10s"],
                            leg_travel_rad_per_10s_median=s["leg_travel_rad_per_10s_median"], leg_travel_over_reference=ratio)
    out["flailing_of_standing_policy_cells"] = flail
    items = [v for k, v in out.items() if k[0].isdigit()]
    out["complete"] = all(v["complete"] for v in items)
    out["pass"] = bool(out["complete"] and all(v["pass"] for v in items))
    return out


# ---------------------------------------------------------------- the run
def preflight(C):
    """Input files, their hashes and, for the sim/flight.py cells, the scene file and the drawn-pack manifest copy, made
    once here so that the workers only read them. Imports flight.py; no physics step is taken."""
    flight = any(v["path"] == "flight" for v in C.values())
    need = [STATE, NONE, PACK, FL / "REQUIREMENTS.json", HERE / "ts3_gates.py", SIM / "flight.py", SIM / "out" / "mass_report.json"]
    need += [d / f for d in (DEPLOYED, FQ2) for f in ONNX]
    if flight:
        need += [SIM_PACK, SIM / "policy_legs.py", SIM / "pack_visual.py"] + [POLICY / f for f in ONNX]
    missing = [str(p) for p in need if not Path(p).exists()]
    assert not missing, f"input files missing on this machine: {missing}"

    def kg(p):
        return round(sum(x["mass_kg"] for x in json.loads(Path(p).read_text())["parts"]), 4)

    info = dict(model_files_sha256_16={n: {f: sha(d / f) for f in ONNX} for n, d in (("deployed", DEPLOYED), ("fq2_1999", FQ2))},
                pack_kg=dict(gate_path_manifest=round(kg(PACK) - kg(NONE), 4), manifest=str(PACK.relative_to(FL))),
                robot_gains=dict(walk_kp_rl=KP_ROBOT, stand_kp=KP_STAND, source=f"{STATE} facts.walking_policy"))
    if flight:
        for f in ONNX:   # sim/policy_legs.py reads train/policy: it must be fq2 iteration 1999
            assert sha(POLICY / f) == sha(FQ2 / f), f"train/policy/{f} is not ckpt/fq2_1999/{f}"
        text = (SIM / "flight.py").read_text()
        assert "--ground-hold" in text and "--ground-i" in text and "STEP_HOOK" in text, "sim/flight.py lacks the B0T options"
        import ts3_thrust
        F = ts3_thrust._flight()
        if str(SIM) not in sys.path:
            sys.path.insert(0, str(SIM))
        import pack_visual
        scene = SIM / "out" / "scene_flight.xml"
        if not scene.exists():
            F.write_scene(scene)
        try:
            vis = Path(pack_visual.with_visuals(SIM_PACK))
        except OSError as e:   # the mirror holds no cad/slices: the drawn-pack copy cannot be rebuilt here
            raise AssertionError(f"sim/out/visual/{SIM_PACK.name} is missing or older than its source and cannot be rebuilt on "
                                 f"this machine ({e}); copy both files from the MacBook with their times kept (rsync -a)") from e
        lost = [p["file"] for p in json.loads(vis.read_text()).get("visual_parts", []) if not (SIMROOT / p["file"]).exists()]
        assert not lost, f"{vis}: drawn-pack meshes missing: {lost[:4]}"
        info["pack_kg"].update(flight_path_manifest=round(kg(SIM_PACK) - kg(NONE), 4), flight_manifest=str(SIM_PACK.relative_to(FL)))
        info["flight_py"] = dict(sha256_16=sha(SIM / "flight.py"), fan_geometry_from_cad=F.FP is not None,
                                 fans=[dict(name=f["name"], p_m=[round(float(x), 4) for x in f["p"]],
                                            axis=[round(float(x), 4) for x in f["a"]]) for f in F.FANS],
                                 hold_flags=cells_flags_note())
    return info


def cells_flags_note():
    return dict(fix=FIX, fan=FAN, settle_s=SETTLE_S, ramp_s=RAMP_S, hold_s=HOLD_S, drift_max_m=DRIFT_MAX_M,
                fall_rule="tilt over 45 deg or trunk_base lower than 0.04 m (brain_sim_check)")


def line(label, s):
    if label == "fq2_fullseq":
        return (f"{label}: full sequence {s['successes']} of {s['seeds']} (95 % {s['successes_wilson95']}; airborne part "
                f"{s['airborne_successes']}; by scenario {s['by_scenario']})")
    t = f"{label}: falls {s['falls']} of {s['seeds']} (95 % {s['falls_wilson95']}, directions {s['fall_dirs']})"
    if "stood" in s:
        t += (f"; stood 10 s in place {s['stood']}, without a fall {s['stood_no_fall']}; fans {s['thrust_share_mean_median']} of the "
              f"weight; pitch before {s['pitch_before_deg_median']} deg, range {s['pitch_min_deg']} to {s['pitch_max_deg']}; smallest "
              f"margin heel {s['heel_margin_min_mm']} mm toe {s['toe_margin_min_mm']} mm; drift max {s['drift_net_m_max']} m")
    else:
        t += (f"; jumps/10 s median {s['jumps_per_10s_median']} quartiles {s['jumps_per_10s_quartiles']}; leg travel/10 s median "
              f"{s['leg_travel_rad_per_10s_median']} rad; fans {s['thrust_share_mean_median']} of the weight; speed {s['speed_mean_upright']}")
    return t


def main():
    assert STRIDE >= 1
    (OUT / "steps").mkdir(parents=True, exist_ok=True)
    C, summ = cells(), {}
    specs = dict(C)
    for label in list(C):  # resume: a cell whose files are complete is kept
        try:
            old = json.loads((OUT / f"{label}.json").read_text())
            if len(old["episodes"]) == C[label]["n"] and old["summary"]["seed0"] == SEED0 and (OUT / "steps" / f"{label}.npz").exists():
                summ[label] = old["summary"]
                del C[label]
        except (OSError, ValueError, KeyError, IndexError):
            pass
    info = preflight(C)
    hb(f"START pid {os.getpid()}: {len(C)} cells ({sum(v['n'] for v in C.values())} episodes) on seeds from {SEED0} "
       f"({len(summ)} cells kept from files), {WORKERS} workers, one log row per {STRIDE} physics steps; walk gain {KP_ROBOT}, "
       f"held-leg gain {KP_STAND}; model files {json.dumps(info['model_files_sha256_16'])}; pack kg {json.dumps(info['pack_kg'])}")
    got, arr = {k: [] for k in C}, {k: {} for k in C}

    def write():
        (OUT / "summary.json").write_text(json.dumps(dict(
            stage="B0T", threshold=THRESHOLD, settings=cells_flags_note(), inputs=info, seeds=SEEDS, seed0=SEED0,
            cells_planned={k: dict(role=v["role"], path=v["path"], episodes=v["n"]) for k, v in specs.items()},
            step_log=dict(folder="steps", rows_every_physics_steps=STRIDE, cols=COLS), cells=summ, verdict=verdict(summ)),
            indent=1, default=str))

    def consume(results):
        for label, ep, A in results:
            got[label].append(ep)
            arr[label][ep["key"]] = A
            if len(got[label]) < C[label]["n"]:
                continue
            s = summarise(label, C[label], got[label])
            summ[label] = s
            np.savez_compressed(OUT / "steps" / f"{label}.npz", cols=np.array(COLS), **arr.pop(label))
            (OUT / f"{label}.json").write_text(json.dumps(dict(summary=s, episodes=got[label]), indent=1, default=str))
            write()
            hb(line(label, s))

    fj = [j for label, spec in C.items() if spec["path"] == "flight" for j in jobs_of(label, spec)]
    gj = [j for label, spec in C.items() if spec["path"] == "gate" for j in jobs_of(label, spec)]
    if fj:   # sim/flight.py was recorded one process per run (sim/batch.py): a fresh worker for every episode
        with ProcessPoolExecutor(WORKERS, max_tasks_per_child=1) as ex:
            consume(ex.map(one_flight, fj))
    if gj:
        with ProcessPoolExecutor(WORKERS) as ex:
            consume(ex.map(one_gate, gj))
    write()
    v = verdict(summ)
    for k, item in v.items():
        if k[0].isdigit():
            short = {a: b for a, b in item.items() if a not in ("calm_line", "diagnostics_not_in_the_verdict", "note", "reference", "names")}
            hb(f"VERDICT {k}: {'PASS' if item['pass'] else 'incomplete' if not item['complete'] else 'FAIL'} {json.dumps(short, default=str)}")
    hb(f"VERDICT calm line {json.dumps(v['0_locked_legs_stand']['calm_line'])}; flailing {json.dumps(v['flailing_of_standing_policy_cells'])}")
    hb(f"VERDICT B0T: {'PASS' if v['pass'] else 'incomplete' if not v['complete'] else 'FAIL'}")
    hb("DONE")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        hb(f"FAILED {type(e).__name__}: {e}")
        raise
