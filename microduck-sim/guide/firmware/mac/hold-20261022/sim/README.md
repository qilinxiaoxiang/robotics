# Lifted by the head, then set down: graded hold in simulation (2026-10-22)

Problem: Shawn lifts the MicroDuck by its head while stand61 runs (walk mode, zero command), and the policy "struggles, overreacts, then locks up". `../../hold.py` (HoldEstimator) lowers the policy authority `s` and the leg P gains as the head pads are gripped and the feet unload. This folder checks it on the as-built model with the real Brain (`walk_brain.Brain.tick`), driven by `../../brain_sim_check.py`.

All numbers below are simulation measurements unless a sentence says "inference".

## Gripped while walking (walk_wired.py GripStop, 2026-10-23)

Shawn (2026-10-23): a held head means stop, and the hold must also act when the robot is lifted mid-walk. walk_wired.py
now latches a walk command that meets a head grip (engagement e > 0.3, hold on and calibrated) to zero velocity, lets the
hold act at once (no 2 s wait for the stride), keeps the robot stopped after the hand leaves until the control file's
command goes to zero, and, once the applied authority is at or below 0.05, clears walk61's stepped latch so the set-down
runs stand61. `brain_sim_check.py --wired-hold` runs the same code (command smoothing, GripStop, hold_allowed, the
authority ramp). Cases `w_*` in `run_hold_sims.py`: walk 0.25 m/s from 4 s, grip at 6.0 s, lift 6.4 s, lower 9.0 s,
release 10.2 s, seeds 0-3.

- No hold (`w_base_lift`): 4 of 4 fall at 10.5 s; legs swing 2.5-3.1 rad in the air (walk61 keeps stepping).
- Hold, rigid grip (`w_hold_lift_rigidgrip`): 4 of 4 stand; legs 0.09-0.13 rad in the air; stable 0-0.2 s after release.
- Hold, pivot hand, without the stand61 hand-back (`w_hold_lift_nosettle`): 2 of 4 fall (seeds 1, 2) about 0.4-1 s
  after release. The body swings to 20-35 deg in the hand, lands 14-22 deg tilted, and walk61 at zero command fails
  to catch it.
- Hold, pivot hand, with the hand-back (`w_hold_lift`): 4 of 4 stand; stable 0.04-0.94 s after release, largest
  action jump in the 0.3 s after release 0.04-0.64 rad; legs 0.38-0.52 rad in the air (touchdown bounces, as in the
  standing pivot case).
- Grip without a lift (`w_hold_grip_only`, hand 6.0-8.0 s): 4 of 4 stop and stand, max tilt 7.0-9.8 deg.
- Standing lift with the gate on (`b_hold_wired_seed0`): identical to `b_hold_seed0`.

## Update after these runs: the touchdown latch (hold.py, 2026-10-22)

The pivot-hand set-down below was fixed in hold.py without dropping the hand term: once the feet have been off the
ground under a grip (h_load > 0.5) and carry the robot again (load share > 0.8), only the load term counts until the
hand leaves. A grip before any lift still lowers `s` toward 0.4, as Shawn asked. Reruns with the latch
(`run_hold_sims.py`, same commands; the earlier results are kept as `latch/*.before.json`):

- Pivot hand, seeds 0 and 1: no fall; in the air the applied action is 0.0 rad and the legs hold still. At touchdown the
  robot lands tilted 17-18 deg and gets its authority back at once (s 0.96 one tick later); its catch applies up to
  1.38 / 1.45 rad. Stable 0.16 / 0.02 s after the hand leaves (before: 1.94 / 1.06 s), largest jump in the 0.3 s after
  release 0.06 / 0.09 rad (before: 1.30 / 1.02). "Leg range in the air" now reads 0.45 / 0.49 rad because contact
  bounces at touchdown count as air ticks; before touchdown the applied action is 0.
- Rigid grip, seeds 0 and 1: unchanged (tilt 4.0 deg, stable at once, jump 0.02 rad).
- Hand on the head without a lift: unchanged (s 0.4, tilt 4.1 deg, stable 0.20 s after release).
- Lift without a grip: unchanged, identical to the baseline (no softening).

walk_wired.py also refuses to apply the hold until the leg currents are calibrated, which removes the uncalibrated case
below (1 of 2 pivot set-downs fell).

## Results (before the latch)

**The outcome depends on how the hand holds the head, so every case was run with two hand models.** The "rigid grip" holds the head's orientation with a 5 N m/rad angular spring, like a palm closed over the head. The "pivot" hand applies only a force at the head's centre of mass, so the body swings below the hand like a pendulum (31.8 deg peak trunk tilt while hanging, even with the legs still). Only the rigid-grip baseline reproduces what Shawn reported: a struggle, then a guard stop that locks the robot in STAND, then a fall after release. Inference: Shawn's real grip is closer to the rigid grip.

**With the rigid grip, the graded hold fixes the lift.** Today's behaviour struggled in both seeds and fell once. With `--hold`, the robot hangs quietly, nothing jumps at release and it stands at once.

**With the pivot hand, the hold calms the hang but makes the set-down worse.** The hand term `A_TOUCH` keeps `s` at 0.4 while the hand is still on the head and the feet already carry the robot. Recovery after release takes 1.06 to 1.94 s, against 0.28 s for the baseline. Setting `A_TOUCH` to 0 removes this (0.18 to 0.20 s) and changes nothing with the rigid grip. A slower give-back (`UP_RATE` 2) makes it worse: both pivot seeds fell.

**Before hold_session.py calibrates the leg currents, the load share is unknown and only the hand term acts** (`s` stays at 0.4). In that state the pivot hand fell in 1 of 2 seeds, 0.92 s after release.

### Baseline, today's behaviour (no `--hold`; the estimate is computed but not applied)

Pivot hand, seeds 0 and 1: no fall. In the air (3.60 to 6.82 s) stand61 struggles. The largest raw (= applied) action is 3.07 and 2.83 rad; seed 0 had one tick over the 3.0 rad hard limit, which was clipped. Leg joints swing over 2.09 and 2.11 rad (right_hip_pitch), still 1.94 and 2.06 rad after the first 0.5 s in the air, at an RMS leg speed of 5.36 rad/s. That leg motion lifts the feet up to 84 mm. In the air, neck_pitch torque peaks at 0.538 and 0.472 N m and head_pitch at 0.538 and 0.519 N m. 0.538 N m is the simulated servo's torque limit at 7.0 V, so the neck saturates. The means are 0.17 and 0.12 N m, against 0.068 and 0.057 N m while standing. The peak trunk tilt is 23.1 and 21.8 deg, under the 30 deg guard. After release the robot stands stably within 0.28 s; the largest action jump in the 0.3 s after release is 0.20 and 0.24 rad. The whole run has 114 and 107 tick-to-tick action jumps over 0.5 rad.

Rigid grip, seed 0: the struggle (raw action 2.19 rad, leg range 1.31 rad, RMS leg speed 2.55 rad/s) tilts the trunk past 30 deg at 5.74 s while it hangs. walk_wired's tilt stop then switches to stand mode, which keeps the open-loop STAND for the rest of the run: this is the lock-up. The robot is set down tilted 16.5 deg in STAND and falls forward at 7.70 s, 0.5 s after the hand leaves. Neck torque in the air peaks at 0.448 N m (mean 0.231) and head_pitch at 0.538 N m (mean 0.181). Seed 1: no guard stop. Raw action 2.70 rad, leg range 1.65 rad, RMS leg speed 4.42 rad/s, neck 0.432 / 0.217 N m and head_pitch 0.538 / 0.175 N m (peak / mean). After release the trunk tilts to 16.8 deg, the largest action jump is 1.10 rad, and it stands stably after 1.80 s.

### Graded hold on (`--hold`), grip at 3.0 s, lift at 3.4 s, lower at 6.0 s, release at 7.2 s

Rigid grip, seeds 0 and 1: no fall; peak trunk tilt 4.0 deg over the whole run. `s` falls from 1 to 0.69 in the 0.4 s of grip before the lift, reaches 0 at 3.7 s as the feet unload, and comes back once the feet carry the robot again. Leg P gain goes 200 to 80 and neck P gain 200 to 500. The largest action is 0.24 rad raw and 0.11 rad applied over the lift window, and 0.04 rad applied in the air. The legs move 0.07 rad once, from the stand61 pose to the default stance, then 0.015 rad. RMS leg speed in the air is 0.05 rad/s. In the air, neck_pitch carries 0.315 N m peak (0.251 mean) and head_pitch 0.145 (0.138), both under the 0.538 N m limit. The feet lift 31 mm. After release: stable at once (0.0 s), largest action jump 0.03 rad, tilt 1.9 deg, zero action jumps over 0.5 rad in the whole run.

Pivot hand, seeds 0 and 1: no fall. In the air the applied action stays at 0.03 rad and the legs are still: range 0.066 rad, then 0.014 rad; RMS speed 0.044 rad/s. The policy's raw action is still 1.0 rad. Neck_pitch carries 0.161 N m peak (0.140 mean) and head_pitch 0.034 (0.025): with a pivoting head the body hangs under the hand, which loads the neck less. The body swings to 31.8 deg tilt. The 30 deg tilt stop was skipped for 12 ticks because grip engagement e > 0.3; without the skip it would have locked the robot in STAND in the air. The robot lands tilted 18.5 deg. While the hand is still on the pads (6.6 to 7.2 s), `s` stays at 0.4 (1 - A_TOUCH). The policy's raw action grows to 1.57 rad, but only 40 % of it is applied. When the hand leaves, `s` returns to 1 in 0.18 s. The largest action jump in the next 0.3 s is 1.30 and 1.02 rad, the trunk tilts to 32.6 and 13.8 deg, and stable standing comes after 1.94 and 1.06 s. The hanging robot also turns 94 to 134 deg about the vertical in the hand.

### Hand on the head, no lift (`--hold`, grip 3.0 to 7.2 s)

The hand alone does not tip it. `s` settles at 0.4 and the trunk creeps from 0.5 to 4.1 deg during the grip. After release it is stable within 0.20 s, with a 0.07 rad largest action jump. A 22 s rest (grip 3 to 25 s) levels off at 4.5 deg from 10 s on and recovers in 0.22 s. The leg P gain dipped to 193 while standing: the simulated foot contact flickers between 0.8 and 1.0 of the weight, and that flicker passes through the grip gate.

### Lift without a grip (`--hold`, no pad contact)

The result matches baseline seed 0 in every number: `s` stays 1.0 and every P gain stays 200. So no softening without the hand, as intended. The struggle is the same: 3.07 rad action, 2.09 rad leg range, 0.28 s to stable after the hand lets go.

### Hold on before calibration (`--hold --hold-uncal`: no load share, as walk_wired before hold_session.py)

Pivot hand: seed 0 falls forward at 8.12 s, 0.92 s after release. In the air, `s` is 0.4 with leg and neck gains unchanged at 200. The raw action reaches 2.48 rad and the applied action 1.29 rad, with a 0.96 rad leg range. After release the applied action reaches 2.77 rad. The topple was faster than the tilt stop: the IMU read 28 deg on the last tick before the trunk passed 45 deg. Seed 1 survives: tilt 27.5 deg, stable after 1.84 s. Rigid grip, seeds 0 and 1: no fall. Tilt 7.8 and 7.2 deg, leg range 0.56 rad, stable 0.32 and 0.30 s after release.

### hold.py constant sensitivity (module constants overridden per run with `--hold-set`; hold.py itself unchanged)

`A_TOUCH 0`, pivot hand, seeds 0 and 1: no fall. Stable 0.20 and 0.18 s after release; largest jump 0.07 and 0.05 rad; tilt after release 3.6 and 3.5 deg. The hang is unchanged, because the load term alone takes `s` to 0 in the air. The cost is at touchdown. `s` returns to about 0.96 within 0.1 s of the feet landing, while the hand is still holding the head, and the applied action reaches 1.17 to 1.21 rad there. In seed 0, contact bounces at touchdown count as air ticks, so the "leg range in the air" reads 0.43 rad. Rigid grip, seeds 0 and 1: same as the default (stable 0.0 s, jump 0.02 rad).

`UP_RATE 2` (authority returns over 0.5 s instead of 0.1 s), pivot hand: both seeds fell. The tilt stop fired at 7.94 and 7.92 s, and the robot fell left at 8.00 and 7.96 s. Rigid grip: unchanged from the default.

## What the sim's guards and metrics do

Before this change, brain_sim_check.py had no walk_wired stops. It ended a run as a fall at trunk tilt over 45 deg (80 in groundpick and sit) or trunk height under 0.04 m. It reported max_action, action_jumps (tick-to-tick jumps over 0.5 rad), and the settle metric for kick, sit and groundpick.

`--wired-guards` now mirrors walk_wired.py's walk-mode stops, using its own constants (HARD_MAX_ACTION, OVER_LIMIT_TICKS, HARD_WINDOW, MAX_TILT_DEG):

- **Action limit**: one tick over 3.0 rad is clipped. 3 such ticks in 10 trigger a stop.
- **Tilt stop**: IMU tilt over 30 deg triggers a stop.
- **What a stop does**: it holds the last goals, then switches to stand mode for the rest of the run. walk_wired writes the stop to the control file, so the stop also holds there until a new command.
- **Applied action**: both checks read `info["action"]`, which the Brain scales by `s`.
- **Grip skip**: with `--hold`, the tilt stop is skipped while e > 0.3. Without `--hold` it is never skipped, which is today's behaviour.

The 45 deg fall check pauses while the hand carries the robot, because a tilted hang is not a fall. The trunk-height check stays on.

## How it is simulated

**Grip**: synthetic raw counts. L1, R1 and M read their rest value plus hold.PAD_HI between `--grip-at` and `--release-at`, which is full coverage (792 mm² against GRIP_FULL_MM2 500). The step is instant, and the touch age is 0.

**Load share**: the summed foot-floor normal contact force over m g (0.838 kg), clipped to 0..1 and fed as `load=`. The real robot will use the calibrated leg current instead.

**Hand**: an `xfrc_applied` spring-damper on the head body `jaw_soft`, the body that carries the head_roll joint. It is updated every 2.5 ms physics step and has three parts:

- **Vertical**: 2000 N/m and 60 N s/m toward a target that rises 40 mm over 0.6 s at 3.4 s and returns over 0.8 s at 6.0 s.
- **Horizontal**: 500 N/m and 20 N s/m toward the head's position at the lift.
- **Rotation**: 0.02 N m s/rad of angular damping (pivot hand). The rigid grip uses 5 N m/rad toward the head's orientation at the lift plus 0.1 N m s/rad.

The hand lets go at `--release-at`, or 1.2 s after `--lower-at` when there is no grip.

**Gains**: the Brain's per-joint kp dict becomes a 14-element array on the BAM actuator, `bam.actuator.kp`, in model order. BAM computes `duty = (q_target - q) * kp * error_gain` element-wise, so each joint gets its own P gain without any change to shared model code.

**Torque**: `d.actuator_force` of neck_pitch and head_pitch. "Standing" is the 1 s before the grip (before the lift when there is no grip). "In the air" means the hand is active and the foot load is under 5 %.

**Settle metric**: as for kick and sit. The trunk tilt stays within 2 deg of the pre-grip stance and |gyro| < 0.3 rad/s for 1 s, timed from the moment the hand leaves.

Not covered:

- The real pad response (the 1.7 mm wall, partial coverage, ramps).
- Leg-current load estimation and its lag.
- Neck sag under the hang, because joint deflection was not logged.
- Hands between the two grip models.
- Any lift other than 40 mm straight up.

## Suggested hold.py changes (inference from the runs above; not applied)

1. **Do not let the hand alone cut authority once the feet carry the robot.** The `A_TOUCH * e` term is what keeps `s` at 0.4 between touchdown and release. That one window explains every bad set-down in these runs, through three pieces of evidence:
   - With the pivot hand, A_TOUCH 0 cut the recovery from 1.06 to 1.94 s down to 0.18 to 0.20 s, and the release jump from 1.0 to 1.3 rad down to 0.05 to 0.07 rad.
   - Slowing the give-back instead (UP_RATE 2) made both seeds fall.
   - The uncalibrated case, which is the A_TOUCH term alone, fell in 1 of 2 pivot seeds.

   The two simplest candidates are A_TOUCH = 0, or applying the hand term only while the load share is low or unknown. A_TOUCH 0 costs about 1.2 rad of applied action right at touchdown with the pivot hand. With the rigid grip it changed nothing. The grip-only runs give no reason to keep A_TOUCH: the robot never tipped with the hand alone, and A_TOUCH 0.6 only let it lean to 4.5 deg.
2. **Keep UP_RATE fast (10 /s or faster).** The slower return failed in both pivot seeds.
3. **Calibrate the legs before turning the hold on with a real lift.** Without a load share, the hold gives only `s` 0.4: no leg softening, no neck stiffening, and one fall in two pivot seeds.
4. **Neck torque check for KP_NECK_HOLD 500**: with the rigid grip the hang put 0.25 / 0.14 N m mean on neck_pitch / head_pitch, under the 0.538 N m limit. Without the hold, the struggle saturated head_pitch at the limit in every rigid and pivot baseline run. KP_LEG_MIN 80 kept the legs at 0.015 rad of motion in the air. The runs gave no evidence to change either value.

## Commands

All runs go one at a time through the runner, each under `timeout 600`. Each run takes about 4 s on the MacBook. The runner writes `<case>.json`, the full brain_sim_check result with the `hold` block, a 0.1 s trace and the exact `command`.

```
cd ~/code/robotics/microduck-sim/guide/firmware/mac/hold-20261022/sim
~/.venvs/microduck-dyn/bin/python run_hold_sims.py              # all 23 cases
~/.venvs/microduck-dyn/bin/python run_hold_sims.py b_hold_seed0 # one case
```

The base arguments match teleop_sim_batch.py: `--model asbuilt --manifest microduck_rl/cmu/model/manifests/plugged.json` plus `robot_state_check.py --print-sim-args`, which gave `--volt 7.0 --drop 0.04` on 2026-10-22. Every case adds `--walk-s 0 --until 12 --wired-guards`. For example, case (b), seed 0:

```
~/.venvs/microduck-dyn/bin/python ../../brain_sim_check.py --model asbuilt \
  --manifest ../../../../../microduck_rl/cmu/model/manifests/plugged.json --volt 7.0 --drop 0.04 \
  --walk-s 0 --until 12 --wired-guards --grip-at 3.0 --release-at 7.2 --lift-at 3.4 --lower-at 6.0 \
  --lift-height 0.04 --hold --seed 0
```

Each case adds the following to that base:

- **a_baseline**: grip and lift flags, without `--hold`.
- **c_grip_only**: only `--grip-at 3.0 --release-at 7.2 --hold`.
- **c_grip_only_long**: `--release-at 25 --until 30`.
- **d_lift_no_grip**: only the lift flags plus `--hold`.
- **rigidgrip**: `--hand-krot 5 --hand-crot 0.1`.
- **uncal**: `--hold-uncal`.
- **Sensitivity cases**: `--hold-set A_TOUCH 0` or `--hold-set UP_RATE 2`.

The full list is in `run_hold_sims.py`, and every JSON records its own command. Rerunning the full matrix reproduced every number exactly. Runs without the new flags are unchanged: kick and sit from stand61, seed 0, match teleop-sim-check.json.
