"""The leg policy (walk61/stand61 through the runtime's Brain) inside flight.py's physics loop.

Same sensor and actuation path as microduck_rl/cmu/mac/brain_sim_check.py with the probe's real-condition flags
(--volt 7.6 --drop 0.036, sensor delay 1 tick, action delay 1 tick, IMU every tick, no IMU pitch, no compensation,
walk_ramp 0, no breakaway, no zero offsets) and the policy from the first tick (--stand-s 0): every 20 ms the Brain gets
{"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0} (stand61 at zero command) and its goals and P gains go to the servos.
The fans and the flight controller never talk to it: on the real robot walk_wired.py and ArduPilot are separate programs.
"""
import collections
import math
import sys
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
MAC = H.parents[2] / "microduck_rl" / "cmu" / "mac"
if str(MAC) not in sys.path:
    sys.path.insert(0, str(MAC))

from walk_brain import IMU_MOUNT_QUAT, MOUNT_FIX, NAMES, SIGN, VEL_UNIT, Brain, apply_inverse, qmul, to_tick  # noqa: E402
from walk_brain import STAND as BRAIN_STAND  # noqa: E402

POLICY_DIR = H.parent / "train" / "policy"      # fq2 1999 (walk61.onnx = stand61.onnx), read only
DROP = 0.036                                    # probe flag --drop
ZERO_CMD = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}


def conj(q):
    return (q[0], -q[1], -q[2], -q[3])


def apply(q, v):
    return apply_inverse(conj(q), v)


class PolicyLegs:
    def __init__(self, m, d, names, c, bam, seed, models=POLICY_DIR, drop=DROP, sensor_delay=1, action_delay=1):
        self.m, self.d, self.names, self.c, self.bam, self.drop = m, d, names, c, bam, drop
        self.idx = {n: names.index(n) for n in NAMES}
        ji = [m.joint(n).id for n in names]
        self.qa, self.va = m.jnt_qposadr[ji], m.jnt_dofadr[ji]
        self.gyro_adr = m.sensor("imu_ang_vel").adr[0]
        self.brain = Brain(str(models), compensation=False, walk_ramp=0.0, yaw_trim_file=None)
        p0 = np.array([BRAIN_STAND[n] for n in names])
        self.aq = collections.deque([p0.copy()] * (action_delay + 1), maxlen=action_delay + 1)
        self.sq = collections.deque(maxlen=sensor_delay + 1)
        self.age = sensor_delay * 0.02 + 0.004
        self.rng = np.random.default_rng(seed)  # brain_sim_check's rng: one draw per tick for the dropped read
        self.first_policy = None
        self.max_action = 0.0
        c.q_target = p0.copy()

    def tick(self, t, want=None):
        """want: the control-file command this tick (default zero-command walk, i.e. stand61)."""
        d = self.d
        q_trunk = d.qpos[3:7].copy()
        q_sensor = qmul(qmul(tuple(q_trunk), conj(IMU_MOUNT_QUAT)), conj(MOUNT_FIX))
        w_body = d.sensordata[self.gyro_adr:self.gyro_adr + 3].copy()
        g_sensor = apply(MOUNT_FIX, apply(IMU_MOUNT_QUAT, w_body))
        sample = (q_sensor, tuple(float(x) for x in g_sensor), d.qpos[self.qa].copy(), d.qvel[self.va].copy())
        if not self.sq:
            self.sq.extend([sample] * self.sq.maxlen)
        self.sq.append(sample)
        q_s, g_s, qm, dqm = self.sq[0]
        pos_t = [to_tick(n, float(qm[self.idx[n]])) for n in NAMES]
        vel_t = [int(round(float(dqm[self.idx[n]]) / VEL_UNIT / SIGN[n])) for n in NAMES]
        fresh = self.rng.random() >= self.drop
        goal, kp, info = self.brain.tick(dict(want or ZERO_CMD), t, pos_t, vel_t, tuple(q_s), g_s, fresh, self.age, self.age)
        if info.get("action") is not None:
            if self.first_policy is None:
                self.first_policy = round(t, 2)
            self.max_action = max(self.max_action, max(abs(a) for a in info["action"]))
        if goal is not None and all(n in goal for n in self.names):
            target = np.array([goal[n] for n in self.names])
            if isinstance(kp, dict):
                self.bam.actuator.kp = np.array([float(kp[n]) for n in self.names])
            elif kp:
                self.bam.actuator.kp = kp
        else:
            target = self.aq[-1].copy()
        self.aq.append(target.copy())
        self.c.q_target = self.aq[0].copy()
        return info
