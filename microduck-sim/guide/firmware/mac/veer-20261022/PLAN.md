# MicroDuck veers left when walking forward: test plan for 2026-10-22

Final-goal step advanced: **step 2, walk to the item** (`PROJECT-CONTEXT.json` `final_goal`, D-019). A robot that turns 30-40 deg per second cannot reach a point two body lengths away.

## What the 2026-10-21 log shows

Source: A7Z `~/duck-logs/duck_wired_log_fix1021ankle.jsonl` (right ankle offset 0, commit 65b01c9), read with `veer_check.py`.

- Five forward bursts at vx 0.25 for 1.4-2.3 s turned the trunk +18 to +95 deg, counter-clockwise seen from above: **+23 to +42 deg/s to the left**. Stepping in place at zero command drifted the other way, -2.5 to -8 deg/s.
- The same Brain and policy in the as-built sim (`brain_sim_check.py --model asbuilt --volt 7.0 --drop 0.04 --vx 0.25 --walk-s 2`) turned -6 deg in 2 s. The policy itself walks straight; the cause is on the robot.
- The turn happens mostly while the **left foot carries the load**: +36 deg/s in left stance, +13 deg/s in right stance (stance leg = the leg whose ankle, knee and hip pitch draw 1.5x the other's current).
- Static zero errors do not reproduce it in sim: ID5 one spline tooth off (+-14.4 deg) gives +-2.5 deg per 2 s; a right ankle 8 deg off makes the sim fall in stand.
- The stance hip yaw servos yield 4-6 deg (right -6.4, left +3.9), in the direction that turns the trunk right during left stance, so hip yaw compliance does not explain a left turn in left stance.
- Trunk roll while stepping in place was under 1 deg. With about 7 cm between the hips that bounds a leg length difference to roughly 1 mm, but this is a moving reading; step 1 takes the static one.

Leading hypothesis: the left foot rotates on the floor in left stance, from a slipperier sole or yaw play in the two-half ankle (held only by the slip-fit foot and the toe M2 x 6, `CURRENT-STATE.json` `ankle_bracket`). Leg length is the second suspect.

## Tests, cheapest and most discriminating first

Run every walk on the same floor patch, robot started from the same mark facing the same way, three 2 s bursts at vx 0.25, each logged. After each run, on the A7Z:

    python3 ~/rt/microduck-sim/guide/firmware/mac/veer-20261022/veer_check.py ~/duck-logs/<newest>.jsonl

(copy the script there with `guide/firmware/a7z/install_teleop.sh` or scp it first.)

1. **Baseline.** Three bursts with nothing changed. Expect +20 to +40 deg/s. Gives today's number on today's battery and floor.
2. **Static symmetry, no walking.** Stand mode on a flat table for 10 s; `veer_check.py` prints trunk roll and both legs' joint angles. Then measure hip axis to table height on each side with a ruler or calipers. Roll of 1 deg at 7 cm hip spacing is 1.2 mm. Under 1.5 mm counts as equal length.
3. **Foot play, torque on.** Twist each foot about the vertical, then roll and pitch, by hand. Note which foot moves and by how much. A foot that turns several degrees under finger force is the leading cause.
4. **Sole swap.** Swap the left and right soles (or cover both with the same tape). If the veer follows the sole to the right, the sole is the cause. If it stays left, the sole is cleared.
5. **Floor swap.** Repeat the baseline on carpet or a rubber mat. A slip cause changes a lot with the floor; a geometry cause such as leg length does not.
6. **Leg length sensitivity, only if step 2 shows a difference or steps 3-5 clear the foot.** Put a 2 mm shim under one sole, then under the other. The change in yaw rate per mm tells whether the measured difference can explain 30 deg/s.

Decision: fix the part the tests point to (ankle play: bracket; sole: material; length: shim or reprint), then rerun step 1. **Acceptance: |yaw rate| under 5 deg/s averaged over three 2 s bursts.**

## Software that keeps it straight once the hardware is close

The policy accepts a yaw-rate command. `pickup.py` already turns it at most 1.0 rad/s, which the as-built sim measured as about 31 deg/s while walking (62 deg per 2 s burst). Today's drift of 30-40 deg/s would use all of it, so software alone cannot cancel the current drift. It becomes useful once the hardware drift is below about 10 deg/s.

1. **IMU heading hold inside each burst** (walk_brain). Record the BNO085 yaw at burst start and command `vtheta = clip(k * wrap(yaw_start - yaw), -1, 1)` on top of the requested vtheta. This is the heading-command scheme legged_gym trains with (k 0.5, clip +-1 rad/s; `legged_gym/envs/base/legged_robot.py`, recalled from the public repo, not re-read today). Add a slow integral term so a constant veer turns into a learned trim. Before the robot: add a yaw disturbance torque to `brain_sim_check.py` that reproduces +30 deg/s and confirm the loop holds heading without a fall.
2. **Camera between bursts.** `pickup.py` already re-reads the target bearing between bursts and sets each burst's yaw rate from it. With the heading hold inside the burst, the camera corrects the remaining error at each stop. That combination gets the robot to the target even with a few deg/s of residual drift.
3. **Training, last.** Randomise per-foot friction and leg length in training so the policy uses its gyro to stay straight. Only if 1 and 2 cannot meet the acceptance, and under the code-enforced dollar cap.

## Files

- `veer_check.py`: per-burst yaw, yaw by stance leg, stance hip yaw error, stand symmetry. It also reads `brain_sim_check.py --tick-log` files.
