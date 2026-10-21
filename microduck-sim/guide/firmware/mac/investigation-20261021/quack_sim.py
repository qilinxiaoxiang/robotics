#!/usr/bin/env python
"""Run guide/firmware/mac/brain_sim_check.py with a patched quack head profile (no repo edit) and record the head
response per tick.

  quack_sim.py --profile-s S --ramp-s R --out OUT.json [brain_sim_check.py args...]

The repo constants walk_wired.QUACK_HEAD_S / QUACK_HEAD_RAMP_S (and the copy brain_sim_check imported by value) are
monkeypatched before run(); --ramp-s 0 makes quack_head_share a plain step (0 on the first tick, 1 until the end of
the profile, 0 after). Brain is wrapped so every tick records the measured head joint deltas (model rad, from the
servo ticks the Brain was handed, i.e. one sensor-delay tick old like the robot) and the gravity vector.
"""
import argparse
import io
import json
import math
import os
import sys

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

MAC = "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac"
sys.path.insert(0, MAC)

ap = argparse.ArgumentParser()
ap.add_argument("--profile-s", type=float, required=True)
ap.add_argument("--ramp-s", type=float, required=True, help="raised-cosine ramp at each end; 0 = plain step")
ap.add_argument("--out", required=True)
args, rest = ap.parse_known_args()

import walk_wired  # noqa: E402
import walk_brain  # noqa: E402
import brain_sim_check  # noqa: E402

walk_wired.QUACK_HEAD_S = args.profile_s
walk_wired.QUACK_HEAD_RAMP_S = max(args.ramp_s, 1e-9)
brain_sim_check.QUACK_HEAD_S = args.profile_s

REC = []


class RecBrain(walk_brain.Brain):
    def tick(self, want, now, pos_t, vel_t, quat, gyro, imu_valid, joint_age, imu_age):
        goal, kp, info = super().tick(want, now, pos_t, vel_t, quat, gyro, imu_valid, joint_age, imu_age)
        q = {n: walk_brain.to_model(n, t) for n, t in zip(walk_brain.NAMES, pos_t)}
        g = walk_brain.apply_inverse(walk_brain.body_quat(quat), [0.0, 0.0, -1.0])  # unrounded gravity in the body
        tilt = math.degrees(math.atan2(math.hypot(float(g[0]), float(g[1])), -float(g[2])))
        REC.append(dict(t=round(now, 3), mode=self.mode, policy=info.get("policy"), gb=info["gb"], tilt=round(tilt, 3),
                        head_cmd=info.get("head_cmd"), want_head=want.get("head"),
                        head={n: round(q[n] - self.default[n], 4) for n in walk_brain.HEAD_JOINTS}))
        return goal, kp, info


brain_sim_check.Brain = RecBrain

sys.argv = [os.path.join(MAC, "brain_sim_check.py")] + rest
buf = io.StringIO()
real_stdout = sys.stdout
sys.stdout = buf
try:
    brain_sim_check.main()
finally:
    sys.stdout = real_stdout
lines = [l for l in buf.getvalue().splitlines() if l.strip()]
res = json.loads(lines[-1])

# brain_sim_check's own flags, for the per-quack analysis
p = argparse.ArgumentParser()
p.add_argument("--quack-at", type=float, nargs="*", default=[])
p.add_argument("--quack-roll", type=float, default=0.18)
p.add_argument("--quack-yaw", type=float, default=0.25)
p.add_argument("--quack-pitch", type=float, default=0.0)
p.add_argument("--seed", type=int, default=0)
qa, _ = p.parse_known_args(rest)
cmd = {"head_roll": qa.quack_roll, "head_yaw": qa.quack_yaw, "head_pitch": qa.quack_pitch}


def tilt_deg(gb):  # kept for the rounded vector; the analysis uses the per-tick unrounded r["tilt"]
    return math.degrees(math.acos(max(-1.0, min(1.0, -gb[2]))))


S = args.profile_s
per_quack = {}
for qt in qa.quack_at:
    pre = [r for r in REC if qt - 0.5 <= r["t"] < qt]
    win = [r for r in REC if qt <= r["t"] < qt + S + 1.5]
    after = [r for r in REC if qt + S <= r["t"] < qt + S + 3.0]
    tilt_win = [r for r in REC if qt - 1.0 <= r["t"] < qt + max(S, 0.5) + 2.0]
    if not pre or not win:
        per_quack[str(qt)] = None
        continue
    base_tilt = sorted(r["tilt"] for r in pre)[len(pre) // 2]
    peak_tilt = max(r["tilt"] for r in tilt_win if r["t"] >= qt)
    min_tilt = min(r["tilt"] for r in tilt_win if r["t"] >= qt)
    joints = {}
    for n, dn in cmd.items():
        if abs(dn) < 1e-6:
            continue
        base = sum(r["head"][n] for r in pre) / len(pre)
        exc = [(r["t"] - qt, (r["head"][n] - base) * (1 if dn > 0 else -1)) for r in win]
        peak_t, peak = max(exc, key=lambda x: x[1])
        t90 = next((t for t, e in exc if e >= 0.9 * peak), None)
        t50cmd = next((t for t, e in exc if e >= 0.5 * abs(dn)), None)
        back = next((r["t"] - (qt + S) for r in after if abs(r["head"][n] - base) < 0.03), None)
        joints[n] = dict(command=dn, peak=round(peak, 3), peak_frac=round(peak / abs(dn), 2), t_peak=round(peak_t, 2),
                         t90_of_peak=round(t90, 2) if t90 is not None else None,
                         t_half_command=round(t50cmd, 2) if t50cmd is not None else None,
                         back_within_0p03_after_end_s=round(back, 2) if back is not None else None)
    mode = win[0]["mode"] + "/" + str(win[0]["policy"])
    per_quack[str(qt)] = dict(mode=mode, base_tilt=round(base_tilt, 2), peak_tilt=round(peak_tilt, 2),
                              tilt_rise=round(peak_tilt - base_tilt, 2), tilt_swing=round(peak_tilt - min_tilt, 2),
                              joints=joints,
                              ran=res.get("quack_head_ran", {}).get(str(qt)))

out = dict(profile_s=S, ramp_s=args.ramp_s, seed=qa.seed, fell_at=res.get("fell_at"), max_tilt=res.get("max_tilt"),
           end_mode=res.get("end_mode"), sit=res.get("sit"), quack_head_ran=res.get("quack_head_ran"),
           quack_head_reached=res.get("quack_head_reached"), quack_peak_tilt=res.get("quack_peak_tilt"),
           per_quack=per_quack, args=rest)
with open(args.out, "w") as f:
    json.dump(out, f, indent=1)
with open(args.out.replace(".json", ".rec.jsonl"), "w") as f:
    for r in REC:
        f.write(json.dumps(r) + "\n")
print(json.dumps(dict(profile_s=S, ramp_s=args.ramp_s, seed=qa.seed, fell_at=out["fell_at"], per_quack=per_quack)))
