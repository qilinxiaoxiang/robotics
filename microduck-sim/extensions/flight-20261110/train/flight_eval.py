"""Evaluate stand/walk policies in the probe that failed (brain_sim_check.py, the runtime's walk_brain, as-built
MuJoCo model, real-condition flags --volt 7.6 --drop 0.036), with three additions done from outside the probe by
wrapping mujoco.mj_step: peak leg actuator force, a trunk shove, and a landing start (drop + tilt).

  $PY train/flight_eval.py --models <dir with walk61.onnx + stand61.onnx> --manifest <pack manifest> --case walk \
      --episodes 20 --out <file.json> [--shove-ns 0.5 --shove-at 8] [--landing] [--workers 6]

Episode = 20 s: open-loop stand --stand-s (0.3 s, as in sim/walk_probe.sh; 0 for landing so the policy catches the
touchdown), walk mode from 0.3 s at zero command (stand61 until the first step), the case's command from 2 s for
15 s, then 3 s at zero command. Seeds 0..episodes-1 drive the probe's dropped-read draw (and the landing draw).
Cases: stand (vx 0), walk (vx 0.25), turnL (vtheta +0.3), turnR (vtheta -0.3).
Per episode: fell_at, tracked speed (dist_x / 15 s for walk; yaw_walk / 15 s for turns), peak |actuator force| of
the ten leg servos (all ticks, and after 1 s), action jumps. Summary: falls out of N, median speed, max peak force.
"""
import argparse
import contextlib
import io
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RL = HERE.parents[2] / "microduck_rl" if (HERE.parents[2] / "microduck_rl").exists() else Path(os.environ["MICRODUCK_RL"])
LIMIT_NM = 0.538
CASES = {"stand": ["--vx", "0"], "walk": ["--vx", "0.25"], "turnL": ["--vx", "0", "--vtheta", "0.3"],
         "turnR": ["--vx", "0", "--vtheta", "-0.3"]}
WALK_AT, WALK_S = 2.0, 15.0
FRAME_HOOK = None  # optional callable(m, d, t) after every physics step
LEGS = ("left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle",
        "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle")


RECURRENT_MAX_GAP = 5  # control ticks (0.1 s) a recurrent policy's state survives without a call


class _StatefulSession:
    """A history policy (HISTORY-PLAN.md: inputs obs [1, 61] + hist_in, outputs actions + hist_out) seen by
    walk_brain.Brain as a plain 61-input session. hist_out is fed back as the next hist_in; the state is zeroed (the
    graph then back-fills it with the current frame) whenever the previous control tick did not run a policy from the
    same file, i.e. on every entry into the policy. Slots loaded from one file (walk61 and stand61 of a universal policy)
    share one state, so the stand/walk switch inside walk mode keeps the history."""

    def __init__(self, sess, brain, group):
        self.sess, self.brain, self.group = sess, brain, group
        ins = sess.get_inputs()
        self.state_name, self.state_shape = ins[1].name, tuple(ins[1].shape)

    def get_inputs(self):
        return self.sess.get_inputs()[:1]

    def get_outputs(self):
        return self.sess.get_outputs()[:1]

    def get_modelmeta(self):
        return self.sess.get_modelmeta()

    def run(self, out, feed):
        b, tick = self.brain, self.brain._hist_tick
        st = b._hist_state.get(self.group)
        # FLIGHT_HIST_REPEAT=1 (--hist-repeat): always pass an empty state, so the graph fills all slots with the
        # current frame. Same network, no past: the control for "does the policy use the history" (HISTORY-PLAN.md 6)
        # A recurrent policy (TEACHER-STUDENT-PLAN.md: second input named state_in) keeps its state over the control
        # ticks the Brain skips (a dropped servo read; 37 of 1000 ticks in a standing episode, 2026-11-18): the state
        # is zeroed only on entry into the policy, i.e. after more than RECURRENT_MAX_GAP ticks without a call.
        # History policies are unchanged: any skipped tick empties the window and the graph back-fills it.
        gap = tick - b._hist_last.get(self.group, -10 ** 9)
        entered = gap > RECURRENT_MAX_GAP if self.state_name == "state_in" else gap != 1
        # diagnostics only (cold-start study, 2026-11-18; default off): FLIGHT_WARM=<dir> starts the episode with the
        # recurrent state saved by an earlier episode of the same seed (FLIGHT_STATE_DUMP=<dir>, written at the end of
        # an episode without a fall) instead of an empty one
        # experiment only (2026-11-20, pack-fitted flag; default off): FLIGHT_OBS_SET="<col>:<value>" overwrites one
        # actor column of the recurrent policy's input on every call (distill_worker --pack-flag-col)
        oset = os.environ.get("FLIGHT_OBS_SET")
        if oset and self.state_name == "state_in":
            feed = {k: np.array(v, copy=True) for k, v in feed.items()}   # several columns: "60:1.0,59:0.5"
            for k in feed:
                if feed[k].ndim == 2 and feed[k].shape[1] == 61:
                    for cv in oset.split(","):
                        c_, v_ = cv.split(":")
                        feed[k][:, int(c_)] = float(v_)
                    DIAG["stat"]["obs_set_calls"] = DIAG["stat"].get("obs_set_calls", 0) + 1
        # diagnostics only (2026-11-20, falls after the walk command ends; default off): FLIGHT_STATE_ZERO_TICK=<n>
        # empties the recurrent state once, at the first policy call at or after control tick n of the episode
        zt = os.environ.get("FLIGHT_STATE_ZERO_TICK")
        if zt and st is not None and self.state_name == "state_in" and not DIAG["stat"].get("state_zeroed_at_tick"):
            DIAG["stat"].setdefault("tick0", tick)   # DIAG["stat"] is emptied at every episode start
            if tick - DIAG["stat"]["tick0"] >= int(zt):
                st = np.zeros(self.state_shape, dtype=np.float32)
                DIAG["stat"]["state_zeroed_at_tick"] = tick - DIAG["stat"]["tick0"]
        warm = os.environ.get("FLIGHT_WARM")
        warm_file = os.path.join(warm, f"state_{DIAG.get('seed')}.npy") if warm else None
        if st is None and warm_file and self.state_name == "state_in" and os.path.exists(warm_file):
            st = np.load(warm_file).astype(np.float32)
            assert st.shape == tuple(self.state_shape), (st.shape, self.state_shape)
            DIAG["stat"]["warm_state_loaded"] = DIAG["stat"].get("warm_state_loaded", 0) + 1
        elif st is None or entered or os.environ.get("FLIGHT_HIST_REPEAT") == "1":
            st = np.zeros(self.state_shape, dtype=np.float32)
        elif (os.environ.get("FLIGHT_CATCHUP") == "1" and self.state_name == "state_in" and 1 < gap <= RECURRENT_MAX_GAP
              and getattr(self, "_last_feed", None) is not None):
            # diagnostics only (2026-11-18): after g - 1 skipped ticks the state is first stepped g - 1 times on the
            # previous observation (actions discarded), so it advances one step per control tick as in training
            for _ in range(gap - 1):
                st = self.sess.run(None, dict(self._last_feed, **{self.state_name: st}))[1]
                DIAG["stat"]["catchup_steps"] = DIAG["stat"].get("catchup_steps", 0) + 1
        if self.state_name == "state_in":
            self._last_feed = {k: np.array(v, copy=True) for k, v in feed.items()}
        res = self.sess.run(None, dict(feed, **{self.state_name: st}))
        b._hist_state[self.group], b._hist_last[self.group] = res[1], tick
        if os.environ.get("FLIGHT_STATE_DUMP"):
            DIAG["last_state"] = res[1]
        # diagnostics only (round 2 cause study, 2026-11-18; both default off). The student always runs and keeps its
        # state; the privileged teacher (FLIGHT_TEACHER, default ckpt/ts2a999_teacher) is computed from the same
        # observation plus priv_now().
        #   FLIGHT_SHADOW=1                 log per called tick: skipped ticks before it, both actions, trunk pitch/roll/vx
        #   FLIGHT_SWAP=teach_after:N       the teacher's action is applied on the N called ticks after every skip
        #   FLIGHT_SWAP=student_after:N     the teacher drives, the student's action is applied on those N ticks
        #   FLIGHT_SWAP=teach_rand:N:p      the teacher's action on N ticks from random ticks (start probability p)
        #   FLIGHT_SWAP=teach_noise:s       the teacher drives every tick, Gaussian noise of s rad on its action
        #   (student_after:0 = the teacher drives every tick; with FLIGHT_SHADOW the student's action is still logged)
        # DIAG["stat"] counts the calls, the skips seen and the ticks each switch really changed.
        shadow, swap = os.environ.get("FLIGHT_SHADOW") == "1", os.environ.get("FLIGHT_SWAP")
        if shadow or swap:
            obs = np.asarray(feed[self.sess.get_inputs()[0].name], dtype=np.float32)
            ta = _teacher_action(obs)
            skipped = gap - 1 if 1 < gap < 1000 else 0
            stat = DIAG["stat"]
            stat["calls"] = stat.get("calls", 0) + 1
            if skipped:
                stat["calls_after_skip"] = stat.get("calls_after_skip", 0) + 1
                stat["skipped_ticks"] = stat.get("skipped_ticks", 0) + skipped
            use_teacher = False
            if swap:
                kind, *arg = swap.split(":")
                if kind == "teach_noise":   # the teacher drives every tick with Gaussian noise of arg[0] rad on its action
                    stat["teacher_applied_ticks"] = stat.get("teacher_applied_ticks", 0) + 1
                    stat["noise_ticks"] = stat.get("noise_ticks", 0) + 1
                    return [(ta + float(arg[0]) * DIAG["rng"].standard_normal(ta.shape)).astype(np.float32)]
                if kind == "teach_rand":
                    start = DIAG["rng"].random() < float(arg[1])
                else:
                    assert kind in ("teach_after", "student_after"), swap
                    start = bool(skipped)
                if start:
                    DIAG["swap_left"] = int(arg[0])
                    stat["windows"] = stat.get("windows", 0) + 1
                win = DIAG["swap_left"] > 0
                DIAG["swap_left"] = max(0, DIAG["swap_left"] - 1)
                use_teacher = (not win) if kind == "student_after" else win
                stat["window_ticks"] = stat.get("window_ticks", 0) + int(win)
                stat["teacher_applied_ticks"] = stat.get("teacher_applied_ticks", 0) + int(use_teacher)
            if shadow:
                import mujoco
                m, d = PRIV["m"], PRIV["d"]
                R = np.zeros(9)
                mujoco.mju_quat2Mat(R, d.qpos[3:7])
                R = R.reshape(3, 3)
                g = R.T @ np.array([0.0, 0.0, -1.0])
                row = dict(k=int(tick), time=round(float(d.time), 4), skip=int(skipped), s=np.round(res[0][0], 4).tolist(), t=np.round(ta[0], 4).tolist(),
                           pitch=round(math.atan2(-g[0], -g[2]), 4), roll=round(math.atan2(g[1], -g[2]), 4),
                           vx=round(float((R.T @ d.qvel[0:3])[0]), 4), by="t" if use_teacher else "s")
                if tick <= 400 and DIAG.get("seed", 99) < 3:
                    row["obs"] = np.round(obs[0], 4).tolist()
                DIAG["rows"].append(row)
            if use_teacher:
                return [ta]
        # DAgger collection in the runtime simulation (ts2_dagger_modal.py, 2026-11-18; default off): FLIGHT_DAGGER=<beta>
        # stores per called tick the observation, the privileged teacher's label and the ticks skipped before the call.
        # With probability beta, drawn once per episode, the teacher's action is applied from control tick 51 on (the
        # student still runs on every called tick and keeps its state). Counters dagger_ticks / dagger_teacher_ticks.
        dg = os.environ.get("FLIGHT_DAGGER")
        if dg is not None and self.state_name == "state_in":
            obs = np.asarray(feed[self.sess.get_inputs()[0].name], dtype=np.float32)
            ta = _teacher_action(obs)
            if DIAG.get("dagger") is None:
                DIAG["dagger"] = dict(obs=[], lab=[], stu=[], skip=[], tick=[], teach=bool(DIAG["rng"].random() < float(dg)))
            rec = DIAG["dagger"]
            use = rec["teach"] and tick > 50
            rec["obs"].append(obs[0].astype(np.float16))
            rec["lab"].append(ta[0].astype(np.float16))
            rec["stu"].append(res[0][0].astype(np.float16))
            rec["skip"].append(min(gap - 1, 127) if 1 < gap < 1000 else 0)
            rec["tick"].append(int(tick))
            DIAG["stat"]["dagger_ticks"] = DIAG["stat"].get("dagger_ticks", 0) + 1
            DIAG["stat"]["dagger_teacher_ticks"] = DIAG["stat"].get("dagger_teacher_ticks", 0) + int(use)
            if use:
                return [ta]
        # diagnostics only (round 2, 2026-11-18): FLIGHT_HANDOVER="<teacher onnx>:<ticks>" lets the privileged teacher
        # drive the first <ticks> control ticks of the episode while the student still sees every observation and
        # builds its state, then the student's own action is used ("released")
        # diagnostics only (warm-up rule, 2026-11-18; default off): FLIGHT_WARMUP="<61-input onnx>:<ticks>" lets a plain
        # 61-input policy (no privileged inputs, e.g. a models directory's stand61.onnx) drive the first <ticks> control
        # ticks of the episode; the recurrent student is run on every called tick and keeps its state, then drives.
        # Counters: warmup_driver_ticks (the driver's action was applied) and student_ticks (the student's was).
        wu = os.environ.get("FLIGHT_WARMUP")
        if wu:
            if tick <= int(wu.rsplit(":", 1)[1]):
                if "sess" not in _WARMUP:
                    import onnxruntime as ort
                    _WARMUP["sess"] = ort.InferenceSession(wu.rsplit(":", 1)[0])
                    assert len(_WARMUP["sess"].get_inputs()) == 1, "the warm-up driver must be a plain 61-input policy"
                    assert (_WARMUP["sess"].get_modelmeta().custom_metadata_map["default_joint_pos"]
                            == self.sess.get_modelmeta().custom_metadata_map["default_joint_pos"]), "different default pose"
                    _WARMUP["name"] = _WARMUP["sess"].get_inputs()[0].name
                obs = np.asarray(feed[self.sess.get_inputs()[0].name], dtype=np.float32)
                DIAG["stat"]["warmup_driver_ticks"] = DIAG["stat"].get("warmup_driver_ticks", 0) + 1
                return _WARMUP["sess"].run(None, {_WARMUP["name"]: obs})[:1]
            DIAG["stat"]["student_ticks"] = DIAG["stat"].get("student_ticks", 0) + 1
        ho = os.environ.get("FLIGHT_HANDOVER")
        # diagnostics only (2026-11-20, falls after the walk command ends): FLIGHT_HANDOVER_AFTER="<teacher onnx>:<tick>"
        # is the reverse, the student drives up to that control tick and the teacher from then on
        hoa = os.environ.get("FLIGHT_HANDOVER_AFTER")
        if hoa and tick > int(hoa.rsplit(":", 1)[1]):
            ho = hoa.rsplit(":", 1)[0] + ":1000000000"
        if ho and tick <= int(ho.rsplit(":", 1)[1]):
            if "sess" not in _HANDOVER:
                import onnxruntime as ort
                _HANDOVER["sess"] = ort.InferenceSession(ho.rsplit(":", 1)[0])
                _HANDOVER["name"] = _HANDOVER["sess"].get_inputs()[0].name
            if int(_HANDOVER["sess"].get_inputs()[0].shape[1]) == 69:  # a gain-reading teacher: priv_now adds the gain
                PRIV["width"] = 69
            obs = np.asarray(feed[self.sess.get_inputs()[0].name], dtype=np.float32)
            DIAG["stat"]["handover_ticks"] = DIAG["stat"].get("handover_ticks", 0) + 1
            return _HANDOVER["sess"].run(None, {_HANDOVER["name"]: np.concatenate([obs, priv_now()[None]], axis=1)})[:1]
        return res[:1]


def install_stateful_policies(b):
    """Make brain_sim_check's Brain run history policies (no-op for 61-input policies, so every existing models dir
    evaluates exactly as before). The runtime's own walk_brain.Brain is not changed (HISTORY-PLAN.md, runtime change)."""
    if getattr(b, "_flight_stateful", False):
        return
    import hashlib
    base = b.Brain

    class StatefulBrain(base):
        def __init__(self, models, *a, **k):
            super().__init__(models, *a, **k)
            self._hist_tick, self._hist_state, self._hist_last = 0, {}, {}
            for key, sess in list(self.sessions.items()):
                if len(sess.get_inputs()) > 1:
                    # a walk_brain with its own recurrent support (guide/firmware/mac/walk_brain.py from 2026-11-19,
                    # Brain.rec): FLIGHT_NATIVE_STATE=1 leaves the state to the Brain (ts2_runtime_parity.py);
                    # otherwise this wrapper keeps it, as in every evaluation so far
                    rec = getattr(self, "rec", None)
                    if rec is not None and key in rec:
                        if os.environ.get("FLIGHT_NATIVE_STATE") == "1":
                            continue
                        del rec[key]
                    path = os.path.join(models, key + "61.onnx")
                    group = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
                    self.sessions[key] = _StatefulSession(sess, self, group)

        def tick(self, *a, **k):
            self._hist_tick += 1
            # round 3 gap study (2026-11-19; default off): the observation-side switches of the jitter study
            # (guide/firmware/mac/jitter-20261018/jitter_sim.py, same formulas), usable with recurrent policies.
            #   FLIGHT_GYRO_NOISE_DQ=K  gyro noise rms per axis = K x rms leg joint speed (rad/s) this tick
            #   FLIGHT_GYRO_NOISE=S     white gyro noise, rad/s rms per axis
            #   FLIGHT_OBS_DELAY=N      N extra ticks of delay on the IMU quaternion and gyro (joint reads unchanged)
            kdq, gn, od = (float(os.environ.get(n, 0) or 0) for n in ("FLIGHT_GYRO_NOISE_DQ", "FLIGHT_GYRO_NOISE", "FLIGHT_OBS_DELAY"))
            if (kdq or gn or od) and len(a) >= 9 and not k:
                want, t, pos_t, vel_t, quat, gyro, imu_valid, joint_age, imu_age = a[:9]
                wb = b.walk_brain
                if not hasattr(self, "_gap_rng"):
                    self._gap_rng, self._gap_fifo = np.random.default_rng(1000 + int(DIAG.get("seed") or 0)), []
                if od:
                    self._gap_fifo.append((tuple(quat), tuple(gyro)))
                    while len(self._gap_fifo) > int(od) + 1:
                        self._gap_fifo.pop(0)
                    quat, gyro = self._gap_fifo[0]
                    imu_age = imu_age + 0.02 * (len(self._gap_fifo) - 1)
                if gn:
                    gyro = tuple(float(g) + float(x) for g, x in zip(gyro, self._gap_rng.normal(0.0, gn, 3)))
                if kdq:
                    legs = [v * wb.VEL_UNIT for n, v in zip(wb.NAMES, vel_t) if n.startswith(("left_", "right_"))]
                    sd = kdq * float(np.sqrt(np.mean(np.square(legs))))
                    gyro = tuple(float(g) + float(x) for g, x in zip(gyro, self._gap_rng.normal(0.0, sd, 3)))
                a = (want, t, pos_t, vel_t, quat, gyro, imu_valid, joint_age, imu_age) + tuple(a[9:])
            return super().tick(*a, **k)

    b.Brain = StatefulBrain
    b._flight_stateful = True


PRIV = dict(m=None, d=None, kg=0.0, log=[])  # the simulator state the privileged teacher reads (set per episode)
# payload kg and trunk COM of the no-pack robot as the teacher reads them (eval/pk_t2a_999_none.json priv_first)
NOPACK_PRIV = (0.0, -0.0335, 0.0007, 0.0186)
_HANDOVER = {}
_WARMUP = {}
_TEACH = {}
DIAG = dict(rows=[], stat={}, swap_left=0, rng=None, phys=[])   # cause-study switches, reset per episode


def _teacher_action(obs):
    """the privileged teacher's action [1, 14] for a 61-wide observation [1, 61] (cause-study switches only)"""
    if "sess" not in _TEACH:
        import onnxruntime as ort
        _TEACH["sess"] = ort.InferenceSession(os.environ.get("FLIGHT_TEACHER") or str(HERE / "ckpt/ts2a999_teacher/teacher.onnx"))
        _TEACH["name"] = _TEACH["sess"].get_inputs()[0].name
        _TEACH["width"] = int(_TEACH["sess"].get_inputs()[0].shape[1])
    if _TEACH.get("width") == 69:  # a gain-reading teacher shadowing a student: priv_now appends the gain scale
        PRIV["width"] = 69
    return _TEACH["sess"].run(None, {_TEACH["name"]: np.concatenate([obs, priv_now()[None]], axis=1)})[0]


def priv_now():
    """The teacher's seven privileged inputs (microduck_rl/cmu/finetune/flight/teacher.py PRIV_NAMES) read from the
    runtime simulation: payload kg (manifest total minus the no-pack manifest's), loaded trunk_base COM in its body
    frame (model body_ipos), trunk_base linear velocity in its body frame (free-joint velocity rotated by its attitude)."""
    import mujoco
    m, d = PRIV["m"], PRIV["d"]
    assert m is not None, "the teacher was called before the first physics step"
    tb = m.body("trunk_base").id
    ja = m.body_jntadr[tb]
    assert m.jnt_type[ja] == mujoco.mjtJoint.mjJNT_FREE and m.jnt_qposadr[ja] == 0, "trunk_base is not the free root"
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, d.qpos[3:7])
    v = R.reshape(3, 3).T @ d.qvel[0:3]
    p = np.concatenate([[PRIV["kg"]], m.body_ipos[tb], v]).astype(np.float32)
    # diagnostics only (round 2, 2026-11-18: does the teacher need its privileged inputs in the runtime simulation?)
    #   nopack   all seven constant: payload 0, the no-pack trunk COM, velocity 0
    #   loadonly payload and COM as nopack, the true velocity
    #   zero     all seven zero
    fix = os.environ.get("FLIGHT_PRIV_FIX")
    if fix == "zero":
        p[:] = 0.0
    elif fix in ("nopack", "loadonly"):
        p[:4] = NOPACK_PRIV
        if fix == "nopack":
            p[4:] = 0.0
    elif fix:
        raise SystemExit(f"FLIGHT_PRIV_FIX={fix!r} is not nopack | loadonly | zero")
    # precision sweep (ts2_bprec.py): FLIGHT_PRIV_MOD JSON {"kg_scale": 0.9, "comx_add": -0.005, "vel_zero": 1}
    # changes one group of the true inputs: payload scaled, trunk COM x offset (m), the three velocities zeroed
    mod = json.loads(os.environ.get("FLIGHT_PRIV_MOD") or "{}")
    if mod:
        assert set(mod) <= {"kg_scale", "comx_add", "vel_zero"}, mod
        p[0] *= mod.get("kg_scale", 1.0)
        p[1] += mod.get("comx_add", 0.0)
        if mod.get("vel_zero"):
            p[4:] = 0.0
    if PRIV.get("width") == 69:
        # a universal5tg teacher (round 3): its eighth privileged input is the position-gain scale, 1.0 = the
        # runtime's KP_RL 200 (--kp-rl 400 = 2.0)
        import walk_brain
        p = np.concatenate([p, [walk_brain.KP_RL / 200.0]]).astype(np.float32)
    if len(PRIV["log"]) < 3:
        PRIV["log"].append([round(float(x), 4) for x in p])
    return p


class _PrivSession:
    """A privileged teacher ONNX (obs [1, 61 + 7], TEACHER-STUDENT-PLAN.md) seen by walk_brain.Brain as a 61-input
    session: the seven privileged values are appended from the simulator at every call. Evaluation only; a teacher never
    runs on the robot."""

    def __init__(self, sess, obs_names):
        from types import SimpleNamespace
        self.sess = sess
        i0 = sess.get_inputs()[0]
        self.name = i0.name
        self._in = [SimpleNamespace(name=i0.name, shape=[1, 61], type=i0.type)]
        meta = dict(sess.get_modelmeta().custom_metadata_map)
        if "joint_names" not in meta:  # a teacher exported without metadata: its start policy's (same task and joints)
            import onnxruntime as ort
            meta = dict(ort.InferenceSession(str(HERE / "ckpt/ts_start/walk61.onnx")).get_modelmeta().custom_metadata_map)
        meta["observation_names"] = obs_names  # the teacher's own list ends with its privileged term
        self._meta = SimpleNamespace(custom_metadata_map=meta)

    def get_inputs(self):
        return self._in

    def get_outputs(self):
        return self.sess.get_outputs()

    def get_modelmeta(self):
        return self._meta

    def run(self, out, feed):
        obs = np.asarray(feed[self.name], dtype=np.float32)
        return self.sess.run(out, {self.name: np.concatenate([obs, priv_now()[None]], axis=1)})


def install_priv_policies(b):
    """walk_brain builds its sessions through this shim: a 68-input ONNX becomes a _PrivSession, anything else is
    onnxruntime's own session (so every existing models dir evaluates exactly as before)."""
    wb = b.walk_brain
    if getattr(wb, "_flight_priv", False):
        return
    real = wb.ort

    class _Ort:
        def __getattr__(self, k):
            return getattr(real, k)

        @staticmethod
        def InferenceSession(path, *a, **k):
            sess = real.InferenceSession(path, *a, **k)
            if len(sess.get_inputs()) == 1 and sess.get_inputs()[0].shape in ([1, 68], [1, 69]):
                PRIV["width"] = sess.get_inputs()[0].shape[1]  # 69: with the gain scale (priv_now)
                return _PrivSession(sess, wb.OBS_NAMES)
            return sess

    wb.ort = _Ort()
    wb._flight_priv = True


def episode(job):
    models, manifest, case, seed, shove_ns, shove_at, landing = job[:7]
    extra = list(job[7]) if len(job) > 7 else []  # diagnostics only: probe flags appended last (they win)
    sys.path.insert(0, str(RL / "cmu/mac"))
    import mujoco
    import brain_sim_check as b
    install_stateful_policies(b)
    install_priv_policies(b)
    none_parts = json.loads((HERE / "manifests/flightpack-none.json").read_text())["parts"]
    DIAG.update(rows=[], stat={}, swap_left=0, rng=np.random.default_rng(int(seed) + 977), phys=[], seed=int(seed), last_state=None,
                dagger=None)
    PRIV.update(m=None, d=None, log=[], kg=sum(p["mass_kg"] for p in json.loads(Path(manifest).read_text())["parts"])
                - sum(p["mass_kg"] for p in none_parts))
    # diagnostics only (spk3diag, PET_ROBOT_LOG 2026-11-13): JSON {joint: [lo, hi]} replaces walk_brain.JOINT_RANGE
    # entries in this sim process, i.e. the range the runtime Brain clamps policy goals to (unset: unchanged)
    if os.environ.get("SPK3DIAG_JOINT_RANGE"):
        b.walk_brain.JOINT_RANGE.update({k: tuple(v) for k, v in json.loads(os.environ["SPK3DIAG_JOINT_RANGE"]).items()})
    # diagnostics only (ts_sep.py, 2026-11-18): JSON {NAME: number} replaces module constants of walk_brain in this sim
    # process, e.g. {"HEADING_KP": 0, "HEADING_KI": 0} switches the runtime's heading hold off (unset: unchanged)
    if os.environ.get("FLIGHT_BRAIN_SET"):
        for k, v in json.loads(os.environ["FLIGHT_BRAIN_SET"]).items():
            assert hasattr(b.walk_brain, k), k
            setattr(b.walk_brain, k, v)
    # diagnostics only (ts_sep.py, 2026-11-18): JSON merged into the run config that evaluate_delay.load builds the
    # simulated robot from, e.g. {"current_limit": 100} lifts the servo current limit (1.47 A = the 0.538 N m clamp)
    if os.environ.get("FLIGHT_CFG_SET"):
        if not hasattr(b, "_flight_orig_cfg"):
            b._flight_orig_cfg = b.cfg
        b.cfg = lambda *a, **k: dict(b._flight_orig_cfg(*a, **k), **json.loads(os.environ["FLIGHT_CFG_SET"]))

    # the seeing pick (--sp-at) wraps visual.apply_visual_to_spec on every run; worker processes are reused, so a
    # second episode would wrap the wrapper and add the jaw body twice ("repeated name 'jaw' in body", 2026-11-11):
    # restore the original before each episode
    sys.path.insert(0, str(RL / "cmu/model"))
    import visual
    if not hasattr(visual, "_flight_orig_avs"):
        visual._flight_orig_avs = visual.apply_visual_to_spec
    visual.apply_visual_to_spec = visual._flight_orig_avs

    rng = np.random.default_rng([seed, 99])
    st = dict(n=0, peak=0.0, peak_after1=0.0, legs=None, trunk=None, after1=[])
    drop_h = float(rng.uniform(0.02, 0.03)) if landing else 0.0
    tilt = rng.uniform(-5, 5, 2) if landing else np.zeros(2)
    orig = getattr(mujoco, "_flight_orig_step", mujoco.mj_step)  # worker processes are reused: never wrap a wrapper
    mujoco._flight_orig_step = orig

    def step(m, d):
        PRIV["m"], PRIV["d"] = m, d
        if st["legs"] is None:
            st["legs"] = [m.actuator(n).id for n in LEGS]
            st["trunk"] = m.body("trunk_base").id
            if landing:  # release from the hover hand-over: raised and tilted, at rest
                q = d.qpos[3:7].copy()
                r = np.zeros(4)
                mujoco.mju_euler2Quat(r, np.radians([tilt[0], tilt[1], 0.0]), "xyz")
                out = np.zeros(4)
                mujoco.mju_mulQuat(out, r, q)
                d.qpos[3:7] = out
                d.qpos[2] += drop_h + 0.005
                d.qvel[:] = 0
                mujoco.mj_forward(m, d)
        t = st["n"] * m.opt.timestep
        if shove_ns:
            on = shove_at <= t < shove_at + 0.1
            d.xfrc_applied[st["trunk"], 0] = (shove_ns / 0.1) if on else 0.0
        orig(m, d)
        st["n"] += 1
        if os.environ.get("FLIGHT_SLOW_LOOP_MS"):
            # diagnostics only (round 3 gap study, 2026-11-19; default off): a control loop slower than the probe's
            # fixed 20 ms tick. After the last physics step of every tick the world runs on for this many more ms with
            # the servo commands held (the probe's own clock still counts 20 ms per tick): 3.2 = the 43 Hz the robot
            # ran s2r6_4 at. The servo model is not updated during the extra steps.
            sub = round(0.02 / m.opt.timestep)
            if st["n"] % sub == 0:
                st["slow"] = st.get("slow", 0.0) + float(os.environ["FLIGHT_SLOW_LOOP_MS"]) / 1000.0
                while st["slow"] >= m.opt.timestep:
                    orig(m, d)
                    st["slow"] -= m.opt.timestep
        if d.time <= 2.0 and os.environ.get("FLIGHT_VX02") == "1":
            # diagnostics only (default off): the trunk's forward speed in its own frame over the first 2 s
            Rv = np.zeros(9)
            mujoco.mju_quat2Mat(Rv, d.qpos[3:7])
            st.setdefault("vx02", []).append(float((Rv.reshape(3, 3).T @ d.qvel[0:3])[0]))
        if os.environ.get("FLIGHT_SHADOW") == "1" and d.time <= 8.2:
            # cause study, check 3: the true joint-angle sum and trunk gravity after every physics step of the first
            # 8 s, so a logged observation can be matched to the time its readings were taken
            Rm = np.zeros(9)
            mujoco.mju_quat2Mat(Rm, d.qpos[3:7])
            DIAG["phys"].append((round(float(d.time), 4), float(d.qpos[7:].sum()),
                                 (Rm.reshape(3, 3).T @ np.array([0.0, 0.0, -1.0])).round(5).tolist()))
        if FRAME_HOOK is not None:  # flight_video.py renders from here
            FRAME_HOOK(m, d, t)
        f = float(np.max(np.abs(d.actuator_force[st["legs"]])))
        st["peak"] = max(st["peak"], f)
        if t >= 1.0:
            st["peak_after1"] = max(st["peak_after1"], f)
            st["after1"].append(f)
            st.setdefault("z", []).append(float(d.xpos[st["trunk"], 2]))
        st.setdefault("per", []).append(np.abs(d.actuator_force[st["legs"]]).copy())  # every step, from t = 0

    orig_fwd = getattr(mujoco, "_flight_orig_forward", mujoco.mj_forward)  # never wrap a wrapper (reused workers)
    mujoco._flight_orig_forward = orig_fwd

    def forward(m, d):  # the probe calls mj_forward on its model before the first tick: a teacher called with
        if m.nu >= len(LEGS):  # --stand-s 0 reads its privileged inputs before any physics step
            PRIV["m"], PRIV["d"] = m, d
        return orig_fwd(m, d)

    mujoco.mj_forward = forward
    mujoco.mj_step = step
    b.mujoco.mj_step = step
    argv = ["brain_sim_check.py", "--model", "asbuilt", "--manifest", manifest, "--volt", "7.6", "--drop", "0.036",
            "--models", models, "--stand-s", "0" if landing else "0.3", "--walk-at", str(WALK_AT), "--walk-s", str(WALK_S),
            "--seed", str(seed)] + CASES[case] + extra
    sys.argv = argv
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        b.main()
    r = json.loads(buf.getvalue().strip().splitlines()[-1])
    dump = os.environ.get("FLIGHT_STATE_DUMP")
    if dump and r["fell_at"] is None and DIAG.get("last_state") is not None:
        os.makedirs(dump, exist_ok=True)
        np.save(os.path.join(dump, f"state_{int(seed)}.npy"), DIAG["last_state"])
        DIAG["stat"]["state_dumped"] = 1
    speed = None
    if r.get("dist_x") is not None:
        speed = round(r["dist_x"] / WALK_S, 4) if case in ("walk", "stand") else round(math.radians(r["yaw_walk_deg"]) / WALK_S, 4)
    return dict(seed=seed, fell_at=r["fell_at"], fall_dir=r["fall_dir"], max_tilt=r["max_tilt"], speed=speed,
                dist_x=r.get("dist_x"), yaw_walk_deg=r.get("yaw_walk_deg"), action_jumps=r["action_jumps"],
                peak_leg_force_nm=round(st["peak"], 4), peak_leg_force_after1s_nm=round(st["peak_after1"], 4),
                # per physics step, the largest |force| of the ten leg servos, from 1 s on: 99th percentile and the share
                # of steps at or above 95 % of the limit (the BAM model clamps at the limit)
                leg_force_p99_nm=round(float(np.percentile(st["after1"], 99)), 4) if st["after1"] else None,
                leg_force_sat_frac=round(float(np.mean(np.array(st["after1"]) >= 0.95 * LIMIT_NM)), 4) if st["after1"] else None,
                per_joint_all=None if not st.get("per") else {
                    n: dict(mean_nm=round(float(np.mean(col)), 4), p99_nm=round(float(np.percentile(col, 99)), 4),
                            sat_frac=round(float(np.mean(col >= 0.95 * LIMIT_NM)), 4))
                    for n, col in zip(LEGS, np.array(st["per"]).T)},
                # trunk_base height from 1 s on: a policy that rests the trunk or pack on the floor reads low here
                trunk_z_m=None if not st.get("z") else dict(min=round(min(st["z"]), 4), median=round(float(np.median(st["z"])), 4)),
                landing=dict(drop_m=round(drop_h, 4), tilt_deg=np.round(tilt, 2).tolist()) if landing else None,
                priv_first=PRIV["log"] or None,  # a teacher's first privileged inputs (kg, COM xyz, velocity xyz)
                vx_0_2s=round(float(np.mean(st["vx02"])), 4) if st.get("vx02") else None,
                # FLIGHT_DAGGER only: numpy arrays (not JSON; ts2_dagger_modal.py takes them out before any file is written)
                dagger=None if DIAG.get("dagger") is None else dict(
                    obs=np.array(DIAG["dagger"]["obs"], np.float16), lab=np.array(DIAG["dagger"]["lab"], np.float16),
                    stu=np.array(DIAG["dagger"]["stu"], np.float16), skip=np.array(DIAG["dagger"]["skip"], np.int8),
                    tick=np.array(DIAG["dagger"]["tick"], np.int16), teach=DIAG["dagger"]["teach"]),
                diag_stat=dict(DIAG["stat"]) or None, shadow=list(DIAG["rows"]) or None,  # cause-study switches
                shadow_phys=(list(DIAG["phys"]) or None) if seed < 3 else None,
                # the probe's own pass-through fields for the bend and quack studies (absent keys stay None)
                probe={k: r.get(k) for k in ("quack_head_ran", "quack_head_reached", "quack_peak_tilt", "seepick", "groundpick")
                       if r.get(k) is not None})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--case", choices=sorted(CASES), required=True)
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--shove-ns", type=float, default=0.0)
    ap.add_argument("--shove-at", type=float, default=8.0)
    ap.add_argument("--landing", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", default="", help="probe flags appended last, space separated (e.g. '--stand-s 0')")
    ap.add_argument("--seed0", type=int, default=0, help="first seed; seeds are seed0..seed0+episodes-1")
    ap.add_argument("--hist-repeat", action="store_true", help="history policies see the current frame in every slot")
    a = ap.parse_args()
    if a.hist_repeat:
        os.environ["FLIGHT_HIST_REPEAT"] = "1"  # inherited by the worker processes
    jobs = [(os.path.abspath(a.models), os.path.abspath(a.manifest), a.case, s, a.shove_ns, a.shove_at, a.landing,
             a.extra.split()) for s in range(a.seed0, a.seed0 + a.episodes)]
    with ProcessPoolExecutor(min(a.workers, 8)) as ex:   # at most 8 workers on the shared Mac mini (16 GB RAM)
        eps = list(ex.map(episode, jobs))
    falls = [e for e in eps if e["fell_at"] is not None]
    sp = [e["speed"] for e in eps if e["fell_at"] is None and e["speed"] is not None]
    summ = dict(models=a.models, hist_repeat=a.hist_repeat, manifest=Path(a.manifest).name, case=a.case, episodes=len(eps), falls=len(falls),
                fall_times=sorted(e["fell_at"] for e in falls), shove_ns=a.shove_ns, landing=a.landing,
                speed_median_upright=round(float(np.median(sp)), 4) if sp else None,
                speed_min_upright=round(float(np.min(sp)), 4) if sp else None,
                peak_leg_force_nm=max(e["peak_leg_force_nm"] for e in eps),
                peak_leg_force_after1s_nm=max(e["peak_leg_force_after1s_nm"] for e in eps), limit_nm=LIMIT_NM,
                max_tilt=max(e["max_tilt"] for e in eps), action_jumps_median=float(np.median([e["action_jumps"] for e in eps])))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(dict(summary=summ, episodes=eps), indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
