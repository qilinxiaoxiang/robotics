# Open-loop stand falls forward: robot vs sim (2026-10-21)

Problem: the open-loop stand (walk_brain stand mode, NEUTRAL pose, stand KP 400) tips forward on the robot within about 20 s since 2026-10-20 night. Sim only from here; no robot motion.

## Robot evidence (A7Z logs app1021-035737, app1021-040436, copied from ~/duck-logs)

- Every logged torque-on tick from 10/18 to tonight runs stand mode at KP 400 (the `kp` field). A stand KP of 600 was discussed earlier but never applied or recorded.
- Settled open-loop stands: 10/18 rest 6.5-9.5 deg IMU pitch, held 19-65 s; 10/19 5.6-7.5 deg, held 42-111 s; tonight 5.5-14.9 deg, settled 2-18 s and then fell forward. Mean measured leg joints tonight differ from 10/19 by at most 1.5 deg (`rest2.py` in the session scratch, `real_pose_compare_1021.json` here).
- IMU pitch minus the model's flat-foot trunk pitch at the same joints (`gap_trace.py`, `gap_tonight.json`, `gap_1018_1019.json`) is not constant inside one stand (-7 to +9.6 deg, also on 10/18 and 10/19): the trunk rotates on the feet (toe or heel lift, or foot play on the ankle) while the joints hold.
- stand61 at zero command, robot minus sim (same policy): hips about 0.043 rad further back, ankles and knees within 0.01 rad. The real COM sits a few millimetres further forward than the model's.

## Sim evidence (as-built 2026-10-20 manifest, real flags 7.0 V, 4 % drops)

- Mass: 200 g extra at the head moves the model COM only 10 mm toward the toe at the robot's pose (`head_mass.py`); the A7Z swap (team model `plugged`, +0.5 mm) is negligible. Mass alone does not explain the fall.
- NEUTRAL at KP 400 (`s61_pose.py neutral 0`): creeps 0.1 -> 5.7 deg in 60 s, tips onto the toes at about 65 s and rests at 11.6 deg, the robot's resting angle tonight.
- Forward perturbation (the feet rocked d deg forward, `ankle_offset.py`, `s61_pose.py`):
  - KP 400: NEUTRAL falls in 1.4 s at 3 deg; the robot's stand61 leg pose holds unperturbed but falls in 3.4 s at 3 deg; with stand61's head pose it falls in 2 s.
  - KP 600: holds at 0 deg (1.1 deg), rests on the toes at 3 deg (10.5 deg), falls in 7.4 s at 5 deg.
  - KP 800: holds at 0, 3 and 5 deg for 120 s (0.7, 8.5, 10.6 deg).
- Mechanism: at KP 400 the ankle, knee and hip in series are too soft to hold the trunk as an inverted pendulum; any lean grows. The pose only chooses the direction and the time to fall (the 10/20 backward-lean shortlist fell backward after 65-95 s at 120 s).

## Decision pending

Stand-mode KP (walk_wired `--kp-stand`, default `constants.KP_DEFAULT`) is the lever the sim shows; a pose change alone delays the fall. Open model gap: the robot pivots on its feet, the sim feet are rigid; the as-built manifest still carries the Pi Zero W head (A7Z, Radxa camera, touch board not modelled).
