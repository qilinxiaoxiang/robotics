# Flight-pack walking and standing: training plan (2026-11-10)

## Problem and the metric that decides
With the 936 g flight pack bolted on (fans off), the duck weighs 1.899 kg instead of 0.960 kg (training-model check,
`out/check_pack_model.json`: 1.8991 kg in the training model, the probe model and `sim/out/mass_report.json`; COM in the
trunk frame -12.0, -1.4, 30.0 mm against -7.6, 0.3, 25.3 mm without the pack; trunk_base body 1.291 kg). Today's
stand61 and walk61 fall in 18 of 18 probe runs (0.5 to 5.7 s), 0 of 6 without the pack
(`sim/out/results.json` walking_summary). Static joint torque is 0.117 of 0.538 N m, so the policies, not the servos,
are the limit in the model.

Success is judged only in the probe that failed (`microduck_rl/cmu/mac/brain_sim_check.py --model asbuilt --manifest
<pack manifest> --volt 7.6 --drop 0.036`, the same real-condition flags as `sim/walk_probe.sh`; values from
`microduck-sim/CURRENT-STATE.json`: servo_rail_v 7.6 V and servo_read_drop_fraction 0.036, both verified 2026-11-06;
imu_rate_hz 50 (full rate, so no --imu-hz); imu_added_delay_ms 0 is dated 2026-10-17 and older than its max age, used
as is because the probe's default sensor delay of one tick is what sim_suite uses for it), through
`train/flight_eval.py`:
- falls out of 20 episodes of 20 s per case: zero-command stand, vx 0.25, vtheta +0.3, vtheta -0.3;
- tracked speed (distance along the command over the walk window / walk time; heading change rate for turns);
- peak |actuator force| of the ten leg servos against the 0.538 N m limit;
- the same after a landing hand-over: the robot released 2 to 3 cm above the floor with up to 5 deg pitch/roll error.
Cases: nominal pack, mass +10 %, COM x +-10 mm, a 0.5 N s shove (5 N for 0.1 s on the trunk) while standing and
while walking, and the no-pack robot if the new policy is meant to cover both. Total reward is never the criterion;
the training guard and checkpoint choice use velocity tracking and the probe.

## Published recipe this follows
- Payload is handled in legged RL by training on the loaded model and randomising the added mass around it, with the
  observation unchanged: legged_gym `added_mass_range = [-1, 1]` kg (ANYmal), Walk These Ways (Margolis and Agrawal
  2022, `scripts/train.py`: `randomize_base_mass = True`, `added_mass_range = [-1.0, 3.0]` kg on a 12 kg Go1, base
  mass not observed). Both read on GitHub 2026-11-10. Their ranges are -10 to +25 % of body mass; a 2x change is far
  outside any trained range, so the base model must be the pack model, with randomisation around it.
- RMA (Kumar et al. 2021) adapts to payload through an extrinsics encoder; that changes the observation and the
  runtime, so it is excluded here.
- Fine-tuning a deployed policy under changed dynamics follows this repo's own ft3 recipe (D-017): warm start from the
  ONNX, critic-only warm-up with the actor frozen, clamped learning rate, EMA velocity tracking (without it a walk61
  fine-tune drifts to standing, ft1/ft2, D-016), guard on tracking error, never on total reward.

## Model variant
`microduck_rl/cmu/model/...` is untouched. The pack enters as a signed-part mass manifest in the schema the worker and
the probe both read: `train/manifests/flightpack-nominal.json` is a snapshot (sha256 b9e06cf25c99bff3...) of
`sim/out/manifest_pack_nominal.json` (battery-20261104 robot + pack v6). Same snapshot for mass+10, comx+-10 and none.
The worker's `apply_asbuilt_masses` applies it (with the usual 90 g NP-F970 removal); check_pack_model.py shows the
training model and the probe model give identical mass and COM.

## Policies, observations, actions
Same 61-D observation, 14 actions, action scale 1 and default pose as walk61/stand61, so the runtime is unchanged.
Separate with-pack checkpoints; today's policies stay for the no-pack robot. Two roles as in the runtime's walk mode:
stand-pack (zero command until the first step, replaces stand61) and walk-pack (replaces walk61, also holds zero
command after a walk). Velocity task `Mjlab-Velocity-Flat-MicroDuck` for both; the stand job sets every standing-env
stage to 1.0 (all envs at zero command, head commands still sampled).

## Rewards
Pollen's velocity reward with ft3's EMA velocity tracking (tau 0.5 s, std sqrt(0.05)) for both fine-tunes; nothing
else changed. The from-scratch run uses Pollen's reward unchanged (the original recipe).

## Randomisation (on top of the originals, which stay: COM +-15 mm on trunk_base and +-10 mm on the head at the final
curriculum stage, Kp +-15 %, Kd +-10 %, BAM friction 0.9-1.1, damping, armature, encoder bias, IMU tilt, pushes
+-0.3 m/s every 3-6 s, start pitch +-10 deg / roll +-5 deg)
- mass: trunk_base mass and inertia scaled together per env (pseudo-inertia alpha) by 0.846 to 1.156, so the whole
  robot spans 1.70 to 2.10 kg (replaces the original +-5 % of the same event);
- pack inertia: pseudo-inertia axis stretch d1=d2=d3 in +-0.05 on trunk_base (second moments x0.90 to x1.11 of the
  whole trunk, about +-20 % of the pack's own share);
- COM +-10 mm in x and y: already inside the original +-15 mm trunk COM randomisation, which stays;
- landing hand-over: reset root height 0.12 to 0.15 m instead of 0.12 to 0.13 m (drops of up to about 3 cm onto the
  feet), combined with the existing start tilt.
Deviation from the brief, with reason: COM is not widened because the walk recipe already randomises +-15 mm.

## Degenerate-policy audit (before any long run)
`train/flight_audit.py` on Modal (2048 envs x 15 s, deterministic): reward per simulated second by term in the
pack training env for (a) walk61 on the no-pack model as the stand-in for the intended walking (the reward has no
mass or torque term, so its terms price the same motion the same way), (b) stand61 there (standing still),
(c) walk61 fed an in-place turn command while the env asks for its own command (shuffling in place), (d) walk61 and
stand61 on the pack model (falling slowly and resetting). Launch only when (a) beats each of (b), (c), (d) on
reward per second and on track_linear_velocity, with standing at most 0.80 of walking (the ft1-calibrated gate).
For the stand job the intended behaviour is the best stander on the no-pack model at zero command; it must beat
falling on the pack model and stepping in place. stand61 lost to stepping in place (audit2), walk61 at zero command
beat it (audit3), so the stand job starts from walk61. Results: `out/audit-audit2.json`, `out/audit-audit3.json`.

## Stop criterion and checkpoint choice
In-run: time and dollar caps only. The tracking and reward guards are off: their baseline is the frozen warm-up
policy, which on the pack model falls within seconds, so any ratio to it means nothing, and total reward is not a
criterion. `model_best` (chosen on reward) is therefore not used. Between checks: checkpoints are pulled from the
run's Modal Volume, converted with `ckpt2onnx.py`, and run in the probe on Modal CPU (`flight_eval_modal.py`; the
Mac mini is saturated by another job): falls out of 20 at vx 0.25 and zero command, nominal pack. A run is stopped when its last two
probed checkpoints are no better than its first, or when tracking falls below the frozen start. The final choice is
the checkpoint with the fewest probe falls, then tracked speed.

## Compute (Kaggle quota read 2026-11-10 19:01: 0.00 of 30 h used, resets 2026-11-14; Modal: monthly metered
$0.11 so far, credits not readable from the CLI; hard cap for this work 35 USD, kept far below it)
Round 1, all independent and launched together after the audit and smoke:
- Modal A10 ($1.417/h with 4 cores and 16 GiB; L4 had no capacity): walk-pack fine-tune from walk61, seed 1 (does
  fine-tuning recover walking?); stand-pack fine-tune from walk61 (does it recover standing?); walk-pack seed 2 with init_std 0.4
  (does more exploration help after a 2x mass jump?). Each its own Volume, time cap in the worker, function timeout
  cap + 0.5 h; worst case per run written in RUNLOG.md.
- Kaggle T4 pair (blind until it ends): from-scratch on the pack model with the original recipe, seeds 1 and 2 (the
  fallback in case fine-tuning collapses), 10.5 h cap.
- Modal CPU (1 core per episode): probe evaluations of pulled checkpoints. The MacBook trains nothing.
Rounds 2 and 3 only on what round 1 shows, each launch with its question written in RUNLOG.md.

Rounds as run (detail and numbers in RUNLOG.md, final comparison in `out/results.json`): round 1 fw1/fw2 (walk) and
fs1 (stand, from walk61); round 2 fq1 and round 3 fq2 add a hinge cost on actuator force above 0.45 N m
(`packwalk_tq`, weights -8 and -12 from audit4) to the fw1 iteration-3000 walker, because every round-1 walker ran at
the 0.538 N m clamp. Checkpoints are chosen by the probe: a walk case below 0.03 m/s counts as failed, then fewest
with-pack falls, then speed. The with-pack probe starts the policy at the first tick (`--stand-s 0`), because the
runtime's open-loop stand mode alone falls with the pack.

## What stays unproven on the robot
This is a simulation result. Earlier sim-better fine-tunes (ft3 it999, t1) fell on the robot; the gaps that apply:
servo softness and deadband under load (the robot's loaded joints ignored errors under 0.05 rad; at twice the mass the
sag and deadband grow, BAM was identified at 0.96 kg), trunk jitter 4-6x the sim's (10/17 sim-ID), ankle play,
the pack's real mass and COM (nothing in the pack is built or weighed), the pack's flex and its strap mounting, foot
slip on the real floor, and the real landing (fan spool-down, ground effect, touchdown speed).
