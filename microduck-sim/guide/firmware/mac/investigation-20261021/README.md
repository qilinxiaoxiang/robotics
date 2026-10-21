# MicroDuck problem sweep, 2026-10-21: what holds up

The robot was off all evening; everything here is log, literature and as-built sim work. None of the nine problems was
fixed on the robot. Current values come only from `microduck-sim/CURRENT-STATE.json`. The Chinese pages
`~/code/reports/20261021-microduck-*.html` and the `findings-*.md` notes mix withdrawn claims; this list supersedes them.

## Measured, worth building on

- Sit (log `robot-runs-20261021-a7z/duck_wired_log_app1021-040436`): `sitstand61` got correct inputs (offline ONNX
  replay matches the logged actions to 0.001 rad). In the 0.5 s after the posture flag the leg goals moved about
  0.10 rad and the leg joints 0.000-0.004 rad, while the head joints followed. The loaded legs did not respond to the
  policy's first small moves, so the closed-loop sit never started.
- Stand, same logs: KP 400 held every leg joint within 0.01-0.03 rad of its goal. At leans under 8 deg the trunk pitch
  still swung (p90 2.2 deg; 10/19: 0.06 deg) with all ten leg encoders frozen, and every stand61 run oscillated at
  3.5-4.5 Hz before tipping. The cause is not established. `policy-churn/stand_check.py` measures both numbers on a log.
- Sim gravity load is about right: steady goal-minus-position in closed-loop stand61, sim knees +0.23 / -0.25 rad,
  robot 10/21 +0.19 / -0.26, 10/19 +0.12 / -0.18.
- One friction scale cannot fit the robot: BAM friction x1.5 on every term already stops walk61 stepping in the sim,
  x3 reproduces the sit stall, and the real robot does step (0.25 m/s on 10/16). Floor friction alone does not explain
  the trips either: mu 1.0 down to 0.1 never fell in 42 runs; low mu only made walk61 stop stepping.
- Replaying logged goals open-loop into the free-floating sim tips it within 0.5 s, so it is not a per-joint servo
  test. Joint identification from logs needs the trunk held (fixed base or lifted legs).
- A7Z heat (`findings-cooling.md`): on 10/21 the loop p50 rose from 14.1 to 21.8 ms in 12 minutes (49.9 to 43.7
  ticks/s). Earlier resets happened at about 86 deg C against a 110 deg C trip, so a 5 V dip is the open lead.
- Training cost, measured: a 1000-iteration fine-tune is 56 min and $1.04 on a Modal L4.

## Not established, do not build on

- The +-8 deg free play under the ankle and the all-term friction x3 in the sim: each was tuned to reproduce one
  symptom and is contradicted by other logs (10/19 shows no play; x1.5 already kills stepping).
- "KP 400 too soft" and the KP 600 stand trial: withdrawn, never applied.
- The two-half-ankle explanation for the 10/21 falls: inference, not checked on the robot.

## Next step that was not run

Scale only BAM's static (Stribeck) friction terms (`friction_stribeck`, `load_friction_*_stribeck`;
`bam/mujoco.py` `MujocoController.update()` recomputes `dof_frictionloss` from them every step) and look for one value
where the sim stalls the sit like the robot and walk61 still steps. Accept only if that value also leaves stand61
matching the logs above, without any foot-play hinge.

## Code changes committed, not on the robot yet

`sit: STALLED` notice (`walk_brain.py`, `test_sit_stall.py`); quack head move 0.6 s with 0.15 s ramps; servo current
and head touch pads in the tick log. They reach the A7Z with the next `install_teleop.sh`.

Files: `findings-*.md` and their scripts (sit, stand, quack, slope, touch, cooling, sim2real, pickup), `policy-churn/`
(stand acceptance and churn tools).
