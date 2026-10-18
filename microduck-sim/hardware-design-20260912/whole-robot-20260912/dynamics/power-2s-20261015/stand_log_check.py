"""Motor current implied by the real robot's position errors while holding STAND at KP 400 (walk_wired.py stand mode).

Input: the 2026-10-14 wired log (default /tmp/duck_wired_log.jsonl; q in servo-ID order 1..14, model rad, the goal is
walk_brain.STAND with no overrides). For quiet upright samples it takes err = q - STAND per joint and applies the BAM
xl330 m6 control law with zero speed: duty = clip(KP * err * error_gain, +-1), I = duty * V / R, limited to 1.47 A.
This checks the BAM voltage law against the measured 165 mA (sum |Present Current|, 2026-10-13, stand.py, same pose
and KP) without the sim's mass or friction model. The log does not say whether the robot stood on the table or was
held, so this is a bracket, not a measurement.

  ~/.venvs/microduck-dyn/bin/python stand_log_check.py [/tmp/duck_wired_log.jsonl] [--volt 5.0]
"""
import argparse, json, math, sys
import numpy as np
from bam.model import load_model

ID_ORDER = ['right_ankle', 'right_knee', 'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw', 'left_ankle', 'left_knee',
            'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw', 'head_pitch', 'neck_pitch', 'head_yaw', 'head_roll']
NEUTRAL = {"right_hip_yaw": 0.0, "right_hip_roll": 0.0873, "right_hip_pitch": 0.4579, "right_knee": 0.0049,
           "right_ankle": -0.4530, "left_hip_yaw": 0.0, "left_hip_roll": -0.0873, "left_hip_pitch": -0.4579,
           "left_knee": -0.0049, "left_ankle": 0.4530, "neck_pitch": 0.3491, "head_pitch": 0.3491,
           "head_yaw": 0.0, "head_roll": 0.0}
STAND = dict(NEUTRAL, right_ankle=-0.5403, left_ankle=0.5403, neck_pitch=0.5236, head_pitch=0.5236)  # walk_brain.py:61


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('log', nargs='?', default='/tmp/duck_wired_log.jsonl')
    ap.add_argument('--volt', type=float, default=5.0); a = ap.parse_args()
    bam = load_model(motor_name='xl330', model='m6'); act = bam.actuator
    kt, R, eg = float(bam.kt.value), float(bam.R.value), float(act.error_gain)
    goal = np.array([STAND[n] for n in ID_ORDER])
    rows, t_mode, prev = [], None, None
    with open(a.log) as fh:
        for line in fh:
            try: d = json.loads(line)
            except ValueError: continue
            if d.get('mode') != prev: t_mode, prev = d['t'], d.get('mode')
            if d.get('mode') != 'stand' or d.get('kp') != 400 or not d.get('torque'): continue
            if d['t'] - t_mode < 3.0: continue                       # skip the 2 s ramp into STAND
            q, dq, gb = np.array(d['q']), np.array(d['dq']), d['gb']
            if np.abs(dq).max() > 0.05 or gb[2] > -0.95: continue    # quiet and upright
            q = (q + math.pi) % (2 * math.pi) - math.pi              # ID5 encoder seam wraps to +-pi
            rows.append(q - goal)
    err = np.array(rows)
    duty = np.clip(400 * err * eg, -1, 1)
    I = np.clip(duty * a.volt / R, -1.47, 1.47)
    tot = np.abs(I).sum(1)
    out = dict(log=a.log, volt=a.volt, samples=len(err), kt=kt, R=R, error_gain=eg,
               ma_per_deg_error=round(1000 * 400 * eg * math.radians(1) * a.volt / R, 1),
               implied_sum_abs_current_a=dict(p10=round(float(np.percentile(tot, 10)), 3), median=round(float(np.median(tot)), 3),
                                              p90=round(float(np.percentile(tot, 90)), 3)),
               median_abs_error_deg={n: round(float(math.degrees(v)), 2) for n, v in zip(ID_ORDER, np.median(np.abs(err), 0))},
               median_implied_abs_current_a={n: round(float(v), 3) for n, v in zip(ID_ORDER, np.median(np.abs(I), 0))},
               measured_reference_a=0.165)
    print(json.dumps(out, indent=1))
    return out


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
