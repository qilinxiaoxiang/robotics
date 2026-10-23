# 2026-10-23 A7Z run app1023-204119: two forward walks with the heading hold

Final-goal step advanced: step 2, walk to the item (D-019). Policy walk61 at vx 0.25, heading hold from commit 0ce6061 (A7Z copy md5 equal).

## Result

- Walk 1 (11.3 s straight, trim -0.42): the turn command reached the -1.0 rad/s limit within about 3 s and stayed there (413 of 1406 ticks at the limit). The heading still crept left, 0 to +30 deg. The trim then learned -0.648.
- Walk 2: 5 s straight (heading -9 to +17 deg), then 9 s with a manual right turn (-0.8 + trim, clipped to -1.0): nearly straight (+5 deg). The -194 deg after the walk, at zero command, is the robot being carried back.
- As-built sim (`brain_sim_check.py --model asbuilt --volt 7.0 --drop 0.04 --vx 0.25 --walk-s 6`): straight 0.1 deg; with `--vtheta -1.0` it turns -53 deg/s. On the robot the same full right command only cancels the drift.

## Where the turn happens

- Left stance phases last 192 ms, right ones 89 ms (51 vs 28 phases, 9.8 s vs 2.5 s). The trunk turns +149 deg in left stance, -60 deg in right stance.
- In left stance the trunk turn equals the left hip-yaw joint motion (-187 deg joint, so the foot did not rotate on the floor). The policy's own goal for that joint, read 5 ticks earlier to undo the 100 ms servo lag, moved -656 deg the same way.
- Left knee (ID7) in left stance: present minus goal +23.4 deg, 272 mA. Right knee (ID2) in right stance: -11.2 deg, 112 mA. Over all forward ticks the left leg draws 281 mA, the right 158 mA. In stand both knees sit within 1 deg and draw 17-19 mA, and trunk roll is +0.22 deg (no leg length difference).

Lead: the left knee gives under load, so the robot sinks onto and stays on the left leg, and the yaw of each long left stance wins. Not yet confirmed by a one-leg load test.

Scripts: `walk_segments.py LOG` (per-walk heading, turn command and dead-reckoned path, path uses the commanded speed so its metres are too long: the sim covers 0.65 m in 6 s at vx 0.25), `stance_yaw_split.py LOG` (trunk yaw vs stance hip-yaw motion).

## Run app1023-210115: the first walk with TURN_MAX 2.0 flailed within 0.4 s

- The brain restarted at 21:01 UTC (TURN_MAX 2.0, trim -0.466). Walk came straight from monitor with the robot upright (gravity -1.00). Within 0.4 s the walk61 goals ran away; by 1.2 s head yaw and head pitch goals reached +145 and +150 deg, leg current 5.3 A, servo rail 6.2 V. The head swing pulled the A7Z power lead out (Shawn), so the log ends unflushed.
- The turn command stayed within +-1.0 (peak -0.99), so the wider limit was never used.
- Cause: the control loop ran at 35.7 Hz (tick 29 ms, loop 26.6 ms, brain process 81-103 % of one core) against 48.4 Hz on the walk at 20:41. thermal.log: SoC 85-86 C with both CPU clusters capped at 416 MHz from about 21:00 on; at the 20:41 walk the SoC was at 39 C with the 1794 / 2002 MHz maxima. walk61 runs at 50 Hz; at 36 Hz it diverged.

## Runs app1023-223352 and app1023-225437: closed-loop arcs at 0.3 rad/s, wound-up integral

- First robot arcs with the IMU-held arc rate (target 17 deg/s). `arc_chunks.py` gives the mean yaw rate per command chunk after its first 0.5 s.
- Right arcs: +2.0, -5.1 and -14.6 deg/s, with the turn command pinned at -2.0 for most of each arc. Left arcs: +3.1, +4.8, +14.6 and +8.4 deg/s.
- Cause of the slow left arcs: the heading integral kept growing while the right arc held the command at -2.0. The left arc after it kept the command at -1.7 to -2.0 for 1.5 s (225437, t 85.5-87) or the whole 3.7 s arc (223352), then overshot to +1.9.
- Fix (walk_brain.py): the integral learns only on straight walks and stops growing while the command is at TURN_MAX. As-built sim, straight 2 s, right arc 4 s, left arc 4 s (`--vtheta-seq`), yaw torque 0.025 N m: left arc in its first, second and last two seconds -0.2 / +3.2 / +9.5 deg/s before, +12.6 / +15.0 / +22.0 after; 0.020 N m -1.6 / +25.2 / +23.7 before, +4.0 / +16.6 / +19.5 after; no torque unchanged; straight walk -2.1 deg/s, no fall.
- Not fixed by this: at 0.025 N m the right arc reaches only +1.9 deg/s in the sim before and after, as on the robot. With the command already at -2.0, the drift of the moment is larger than the right turn walk61 can make.
