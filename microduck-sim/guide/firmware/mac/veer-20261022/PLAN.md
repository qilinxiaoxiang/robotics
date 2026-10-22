# MicroDuck veers left when walking forward: test procedure for 2026-10-22

Final-goal step advanced: **step 2, walk to the item** (`PROJECT-CONTEXT.json` `final_goal`, D-019).
**Acceptance:** |yaw rate| under 5 deg/s averaged over three 2 s bursts at vx 0.25.

## Why these tests

From the 2026-10-21 log (A7Z `~/duck-logs/duck_wired_log_fix1021ankle.jsonl`, right ankle offset 0, commit 65b01c9):

- Five forward bursts at vx 0.25 turned the trunk **+23 to +42 deg/s to the left** (counter-clockwise seen from above). Stepping in place drifted slightly right (-2.5 to -8 deg/s).
- The same policy in the as-built sim turned -6 deg in 2 s. The policy walks straight; the cause is on the robot.
- The turn happens mostly while the **left foot carries the load**: +36 deg/s in left stance, +13 deg/s in right stance.
- A static zero error does not reproduce it in sim (ID5 one spline tooth off: +-2.5 deg per 2 s).
- Trunk roll while stepping was under 1 deg, about 1 mm of leg length difference at 7 cm hip spacing. That reading was taken while moving; step 2 takes the static one.

Since that log both soles have a hot-glue coat (Shawn, 2026-10-21 evening), so the baseline in step 1 is new.
Suspects in order: left foot yaw play in the two-half ankle, a leg length difference, foot slip on the floor.

## Step 0: start (5 min)

1. Charge or connect the supply. Put the robot on its side as usual and power it up.
2. On the Mac, check the A7Z answers: `ssh a7z hostname`.
3. Start the brain, or let the app start it: `ssh a7z '~/duck-run.sh veer1022a'`. It comes up in monitor mode with torque untouched.
4. Put the robot on its feet in the app (stand), then walk at zero command (stand61). The robot steps in place.
5. Mark a start point and a straight line 1 m long on the floor with tape. Use the same floor patch for every run in steps 1-3.

## Step 1: baseline (5 min)

1. Put the robot on the start mark, facing along the tape line, stepping in place.
2. On the Mac, in `microduck-sim/guide/firmware/mac/veer-20261022`: `bash burst.sh`. The robot walks forward at 0.25 m/s for 2 s and stops; the script prints the burst's yaw in deg and deg/s.
3. Carry it back to the mark and repeat twice more. Then `bash burst.sh report 3` prints all three and the split by stance leg.
4. Write down: the mean yaw rate, left-stance and right-stance yaw rates, and where the robot ended relative to the tape (photo).

If the mean is already under 5 deg/s, the hot glue fixed it: skip to step 5.

## Step 2: leg length, no walking (10 min)

1. Command stand in the app and leave the robot standing still on a flat table for 15 s.
2. `bash burst.sh report 1`. The first line gives the trunk roll. 1 deg of roll is about 1.2 mm of leg length difference.
3. With a ruler or calipers, measure from the table to the centre of each hip pitch servo horn, left and right. Photo of each reading.
4. Under 1.5 mm difference counts as the same length. Over that, note which leg is shorter.

## Step 3: ankle play, torque on (5 min)

1. Robot standing (stand mode, torque on), held by the body.
2. Twist the left foot about the vertical axis, gently, both ways. Then the right foot. Then rock each foot in roll and pitch.
3. Note for each foot whether it moves against the leg and roughly how many degrees. A short phone video of each foot helps.
4. A foot that turns visibly under finger force is the leading cause, especially the left one.

## Step 4: decide and fix (time depends on the cause)

- **Left foot moves in step 3:** tighten that two-half ankle (toe M2 x 6, slip-fit) or shim the slip fit, then repeat step 1.
- **Step 2 shows a difference over 1.5 mm:** shim the short leg's sole to equal length (tape layers, then measure again), then repeat step 1.
- **Neither:** the floor test separates slip from geometry. Repeat step 1 on carpet or a rubber mat. A slip cause changes a lot with the floor; leg length does not. Then put a 2 mm shim under one sole and repeat step 1 to measure how much 1 mm of length difference turns the robot.

Repeat until the acceptance holds on the tape floor.

## Step 5: software heading hold (after the hardware is close)

The policy accepts a yaw-rate command, at most 1.0 rad/s, about 31 deg/s while walking in the as-built sim. The 10/21 drift of 30-40 deg/s would use all of it, so this step comes after the hardware drift is under about 10 deg/s.

1. **IMU heading hold in each burst** (walk_brain): keep the yaw at burst start and add `vtheta = clip(k * wrap(yaw_start - yaw), -1, 1)` to the requested yaw rate, plus a slow integral that learns a constant trim. This is the heading-command scheme legged_gym trains with (k 0.5, clip +-1 rad/s; `legged_gym/envs/base/legged_robot.py`, recalled from the public repo, not re-read). Check it in `brain_sim_check.py` with an added yaw disturbance that reproduces +30 deg/s before the robot.
2. **Camera between bursts:** `pickup.py` already re-reads the target bearing between bursts and sets each burst's yaw rate from it. With the heading hold inside each burst, the camera removes what is left at each stop.
3. **Training last:** randomise per-foot friction and leg length so the policy stays straight on its own, only if 1 and 2 miss the acceptance, under the code-enforced dollar cap.

## Tools

- `burst.sh`: one 2 s forward burst from the Mac and its yaw; `burst.sh report N` for the newest N bursts. Env `VX`, `SECS` change speed and length. It refuses when walk_wired.py is not running.
- `veer_check.py LOG [--last N]`: per-burst yaw, yaw by stance leg, stance hip yaw error, stand roll and joint angles. Also reads `brain_sim_check.py --tick-log` files.
