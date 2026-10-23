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
