# T1 robot test, 2026-10-30 10:27-10:29 (models-t1-best on the robot)

Policy under test: `runtime-overlay/models-t1-best` (fork run t1, iteration 800; fork
`cmu/finetune/modal/FINETUNE-DELTA.md`, "Run t1"). Brain started by `../t1_robot_test.py restart`; A7Z log
`~/duck-logs/duck_wired_log_t11030-102129.jsonl`. Shawn ran every step at the robot. The brain went back to walk61
at 10:29:05 (`t1_robot_test.py back`, log `duck_wired_log_walk611030-102905.jsonl`).

## Result

The neck now follows the command on the robot, but the gait is not stable enough to deploy: one of three 0.25 m/s
walks fell, and every walk wobbled about twice as far as walk61 with ten times its action jumps.

- **Neck, walking at 0.25 m/s**: command -0.4, reached -0.38..-0.42 (walk61 on the robot reached -0.09 standing,
  PET_ROBOT_LOG). Command -0.8, reached -0.70..-0.92 while walking.
- **Neck, standing after a 2 s walk**: held -0.816 against -0.8 for 10 s at 1.9 deg tilt.
- **Plain walk, no head command (step 2)**: fell sideways 3.4 s after the command. Tilt built 6.5 -> 12 deg over
  three seconds, then rolled to 29 deg while still walking; the tilt guard switched to open-loop stand at 36 deg and
  the duck lay on its side at 104-109 deg.
- **Stops**: when the walk command ends, tilt rose to 20 deg (step 4) and 19 deg (step 7) before settling to 2 deg.
- **Step 5 is not a fall**: tilt 18-29 deg with leg current down from 300 to 130 mA and the hold logic dropping leg
  gains to 80, with zero policy output. Shawn lifted the duck.
- **Standing on stand61 (steps 1, 3, 6)**: 2.3-2.6 deg tilt, actions 0.13-0.20, as before.

## Against walk61 on the same robot

walk61 rows are the five 0.25 m/s walks of the 10/30 `--see` session (A7Z log `duck_wired_log_app1030-040713.jsonl`,
copied as seek windows; walk rows only in `walk61_see_walks.jsonl`). `compare_walks.py` computes both.

    walks at vx 0.25        peak tilt      mean tilt    action p95   action max   jumps > 0.5 rad    servo read misses
    walk61 (5 walks)        7.4-8.6 deg    3.4-4.0      0.91-1.19    1.10-1.37    1.4-2.7 per s      1.4-6.1 %
    T1 it800 (3 walks)      13.8-29.3      6.6-7.2      1.77-2.06    2.10-2.58    17-22 per s        3.1-4.9 %

Read misses are the same, so the bus is not the difference. The sim suite predicted the direction (vx 0.25: 14 jumps
per 10 s against walk61's 1, peak tilt 9.6 against 6.3), and it is the pattern ft3 showed before it fell at 0.20 m/s
on 10/17-18 (`../robot-runs-20261018`). The sim underestimates how much it costs on the robot: no sim case fell.

## Files

- `1_stand` ... `8_home.jsonl`: the brain rows of each step as `t1_robot_test.py` copied them.
- `walk61_see_walks.jsonl`, `walk61_results.jsonl`, `t1_results.jsonl`: the comparison above.
