# 2026-10-23 sit/stand: head hit the floor on the 4th rise (run app1023-204119)

Evidence: `sit-region.jsonl` (log rows from line 42800 of the A7Z tick log), `run.out`, `ana2.py`, `replay_rise.py`.

- Four sits all reached the seat (knees 1.28 / -1.24). Rises 0-2 peaked at 8.6, 5.8 and 7.5 deg forward pitch, with the neck action never below -0.43 rad. The as-built sim rises peak at 4.6 deg with the neck at no less than -0.36 (4 seeds, `brain_sim_check.py --model asbuilt --drop 0.04 --sit-at 3 --unsit-at 7`).
- Rise 3: pitch passed 10 deg at +0.71 s. From there the sitstand61 neck action ran away: -0.34, -0.79, -1.23, -1.60, -2.53, -3.45, -3.75 rad within 0.3 s, and the body pitched to 25 deg. An offline replay reproduces every logged action to 0.003 rad. Swapping any single observation block (gyro, gravity, joint pos, joint vel, last action) back to a good-rise tick does not stop it. This is a closed loop: the head moving forward pitches the body further. Pitch alone produces only -0.55 at 20 deg.
- The hard-action guard clipped two ticks to -3.0 rad, sent them, and on the third tick stopped to monitor while holding the last goals. Neck ID12 goal tick 3776 (about -2.65 rad, outside the trained MJCF range of -1.57..+1.05) was held at full gain. The neck reached -2.50 rad (q) with the head pressed on the floor. The body itself came back to 0 deg pitch, so it did not fall.

## Fix (2026-10-23, in the repo, not yet on the A7Z)

- `walk_brain.JOINT_RANGE` / `clamp_goal`: every policy goal is clamped to the trained MJCF hinge ranges, including the clipped goals the hard-limit guard sends. On the robot, about 10 % of the 1442 sit policy ticks asked for goals outside those ranges, mostly hip roll (up to 0.79 rad past the range). The measured joints never left the ranges, so the clamp removes only goals the servos never reached. It still changes the servo push, so robot acceptance is pending.
- `Brain.hold_head`: on a sit or ground-pick trip the head joints hold their measured positions and the legs keep their last goals.
- Rejected: gliding the head to STAND after the trip. With the robot's logged neck runaway injected into the as-built sim (`inject_runaway.py`), the head lands on the floor at about 30 deg trunk pitch, and raising the head levers the trunk forward: it fell at 8.84 and 8.86 s (seeds 0 and 1), and at 9.1-9.3 s at P 50. Holding the head stood until the stand command in both seeds; the old behaviour fell at 8.7 s in seed 1. Every variant then fell under the open-loop stand ramp from the head-planted pose, so after a trip Shawn rights the robot by hand before `stand`.
- The injection replays the actions open loop, so it cannot show whether the clamp cuts the closed-loop runaway itself. That needs a robot sit/stand run.
- Tests: `test_sit_runaway.py`. On the old code it fails at -2.15 rad (clamp) and -2.65 rad (trip); without `hold_head` it fails on a neck goal 1172 ticks from the measured position; on the new code it passes. The other suites pass: test_teleop_modes, test_sit_stall, test_walk_wired_battery (its runaway test now injects the runaway, because clamped goals no longer run away in the physics-free fake world), test_walk_wired_touch, test_pickup_modes, test_pickup, test_hold and test_yaw_trim.
- Sim regression (as-built, 7.0 V, 4 % drops, wired guards): sit/stand on 4 seeds, seated trunk 0.0573-0.0574 m, peak tilt 9.4-9.9 deg (10.4-10.7 before); walk 0.25 m/s for 8 s on 2 seeds, 0.88 m, no fall; ground pick on 2 seeds, mouth 21 mm above the floor, no fall.

Open: why the robot's rises pitch 2-4 deg further forward than the sim's (the runaway's trigger). Narrowed below.

## Where the extra forward lean comes from (side photos, 2026-10-23 evening)

Problem: under the policy the trunk sits 3-4 deg further nose-down than the leg encoders imply with flat feet (IMU minus feet-flat FK: +0.1 vs -4.0 in the sit run, +3.09 vs -0.01 here); the offset between modes is the same on every surface, the absolute value moves with the floor slope.

Test: run app1023-180320, robot on the floor, phone on the floor beside it (left side facing the camera), IMG_7104 in stand61 at zero command (22:12:00 UTC), IMG_7105 in open-loop stand (22:12:29 UTC), both still. Ankle halves screwed together at the toe (CURRENT-STATE `ankle_bracket`). `photo_rot.py` measures the image rotation of each part between the two photos (SIFT, RANSAC similarity, run on the full-resolution 4032 x 3024 originals; the box coordinates are in those pixels; the saved JPGs are 1600 px) minus the camera's own rotation from the background; `seg_fk2.py` gives the model's world rotation of each body from the logged joints with both feet flat.

- IMU: closed 3.33, open 3.15 deg, the same. Joints: the trunk turns 2.95 deg between the modes.
- Photo: trunk +0.16 deg (+-0.14). The photo agrees with the IMU, so the IMU and its 4 deg trim are right and the joint readings miss about 3 deg.
- Photo, left leg from the floor up: foot -0.13 (+-0.02), shin (ankle servo body) +1.99 (+-0.15), thigh cover +3.02 (+-0.17), trunk +0.16. Relative turns: ankle 2.1, knee 1.0, hip 2.9 deg.
- Model, left leg from the same encoders: ankle 0.8, knee 0.4, hip 2.7 deg, with the knee turning the other way. The hip agrees; the knee and ankle each turn about 1.3-1.5 deg more in the photo than their encoders report, which together cancel the hip's 2.9 deg and keep the trunk still.
- Conclusion: between closed and open loop the left knee and ankle rotate about 1.3-1.5 deg each beyond what their encoders read, so a load-dependent rotation sits after the encoders (horn, horn screws, printed bracket or link) at those two joints. Under the policy this puts the trunk about 3 deg further forward than the joint readings the policy was trained to pair with that IMU reading.
- Limits: one leg seen (the right leg is hidden); the thigh measurement rests on 22 feature inliers.

Next: locate the interface on the left knee and ankle (powered: hold position, push the foot or shin, see whether the part moves while the encoder does not; unpowered: horn screws and horn seating), fix it, then repeat the two photos from both sides. Acceptance: the photo's trunk-to-foot change matches the encoder FK within 0.5 deg and IMU minus FK differs by less than 1 deg between the modes.
