# 3D scans against the as-built chain, 2026-11-01

Problem: the head camera's position in the bend and the gap between the sim chain and the robot (final goal steps 3-4).

Two Scaniverse LiDAR meshes, charger pack on, of the robot holding still under torque. Joint angles and gravity come from the brain log of the same minutes (`duck_wired_log_app1101-203552.jsonl` on the A7Z; held means in `poses.json`, joint spread 0.0006 rad):

- Stand: 20:38:00-20:39:40, walk mode at zero command, neck +0.187, head +0.385, IMU trunk pitch -1.0 deg.
- Bend: 20:40:30-20:41:50, groundpick phase 0.33, neck -1.266, head -0.256, IMU trunk pitch +37.4 deg.

Raw zips: `raw/` (ignored by git).

## Result

All offsets are real minus chain, foot frame, x forward, z up. The chain is `target_ground.DuckGeometry` at the logged angles.

- Scale needs no ruler: a free scale on the head's outer surface gives 0.998 and 1.005. Sole length reads 54.6 mm against 54.5 mm CAD on the cleanest foot; the others read up to 5 mm long.
- Bend, head: lowest point about 3 mm over the floor against 22 mm in the chain.
- Bend, camera height: 14.5 mm (+-2) against 30.4 mm in the chain and 16.6 mm with the deployed `bow_height_correction`. This agrees with the ruler's -13 mm from a separate method and a separate day.
- Bend, camera x -9.6 mm (feet-referenced), optical axis 6.9 deg off the chain.
- Stand, camera: +22 mm x, -11 mm z, optical axis 11.3 deg further nose-down. The deployed mount has no standing position correction; its +11.97 deg pitch offset holds about the same angle as a lens mount error.
- Stand-only refit of the camera rotation with a -10.4 deg neck offset drops the mount pitch from 11.95 to 0.97 deg, so most of that pitch belongs to the chain and little to the lens mount.
- Chain residual, head origin: stand 23 mm and bend 16 mm. One constant explains most of it, either trunk +9.7 deg or neck -10.4 deg (rms 4.6 and 4.9 against 10.7).

Not settled:

- Where the angle sits. Trunk reads +2.7 to +8 deg forward of the IMU by fit method, and a free fit on the ruler ticks gives trunk +5.0 +- 1.5 deg. Thighs standing read +2.8 and +4.9 deg (+-1.9), which points at the lower leg as well. Single scans do not separate these.
- The trunk reading conflicts with `IMU_PITCH_TRIM_DEG` = 4 (`walk_brain.py`), which assumes the sensor over-reads forward. The closed-loop run below does not separate them, because the bias trades against a small hidden ankle angle; the scan's trunk fits also carry 7-8 mm of wire error.
- Backpack position. The crude colour check (`pack.py`) gave 1 to 21 mm disagreement between poses, polluted by wires. No number from it is usable.

## What did not pass

Constant trunk, neck and head offsets refit on the ruler do not reach the 5 mm tick bar: best full-fit worst tick 9.1 mm, and held-out poses 11-21 mm (`ruler_holdout.py`). The deployed -13 mm correction stays best on those ticks (worst 4.8 mm), so the camera code and mount are unchanged.

## Repeating it

```
crop and inspect:     inspect_scan.py <obj> <out>; crop_robot.py <out>
log:                  log_windows.py <dir>  (slice copied off the A7Z with tail, never parsed there)
model:                model_pose.py <dir>   (microduck-dyn venv)
fit:                  fit_scan.py, then color_fit.py, parts_fit.py, chain_fit.py
ruler cross-check:    ruler_validate.py, ruler_holdout.py (duck-see venv)
```

`fit_scan.py` alone is not enough. A plain fit slides along the smooth head shell and first read the bend error as 2 mm. The two-way colour fit in `color_fit.py` pins the white and yellow border: 17-24 of 30 random starts reach the same answer, with a camera spread of 0.3-2 mm.

## In the sim: centre of mass and support (`sim_static.py`)

Mass model: `manifest-charger-20261101.json`, the plugged variant plus the head sensors (918.6 g, parts not weighed; `variant-charger-20261101.json`). The default as-built manifest is the 10/15 robot (827.8 g) and moves the standing COM 3.8 mm against this one. Feet flat, foot frame, margins from the COM to the sole's front and rear edges along x:

- Stand, chain as logged: front 29.8 mm, rear 19.9 mm, COM 5 mm behind the sole centre.
- Stand, scan best: front 22.3 mm, rear 27.4 mm, COM 2.5 mm ahead of the centre. Forward shift 7.5 mm.
- Bend, chain as logged: front 27.1 mm, rear 29.2 mm, COM 1 mm ahead of the centre.
- Bend, scan best: front 17.8 mm, rear 38.6 mm, COM 10.4 mm ahead of the centre. Forward shift 9.3 mm.

"Scan best" sets the trunk at the untrimmed IMU pitch by a hidden ankle angle and gives the neck the rest of the head's angle (stand ankles 2.5, neck -5 deg; bend ankles 9, neck -1 deg). It comes from the scan fits, not a fit to the COM. The extremes: ankles alone 9.7 deg leave a front margin of 9.6 mm standing and 17.1 mm bent; neck alone -10.4 deg leaves 25.2 mm and 28.6 mm.

Feet-flat trunk pitch from the leg encoders alone: +0.5 deg standing and +32.4 deg bent. The IMU reads -1.0 and +37.4 with the 4 deg trim, +3.0 and +41.4 without it. The scan's trunk fits sit nearer the untrimmed values, so the hidden angle is about 2.5 deg standing and 9 deg in the bend, growing with leg load. That is a lead for ankle play (`foot_play` in `evaluate_delay.py`) and against the trim. Neither is changed.

Checks that did not settle it:

- Holding the logged goals open loop (`sim_static.py --settle`): the model falls or folds, because on the robot the policy keeps correcting. No conclusion about the offsets. The closed-loop run is below.
- Position error as a load gauge (`load_check.py`): standing neck error 0.045 rad gives 0.08 Nm/rad on the chain and 1.0 on neck -10.4 deg, against about 0.96 in the sim's servo, which favours a real forward offset. But standing head error reads 0.176 rad at low load after the rise (0.14 Nm/rad), so friction can hold that much error. Weak support only. Logged `cur_ma` runs about 8 times under the torque the same errors imply; do not read it as absolute torque.
- Bend neck: the error falls from 0.229 to 0.10 rad the moment motion stops while the modelled load stays 0.23 Nm. Friction or the head resting on the floor would both do this; the fitted head clearance is about 3 mm.

## Closed loop against the robot's log (`closed_loop.py`)

`walk_brain.Brain` (the A7Z's file, md5 799f636f) and the A7Z's own walk61 and groundpick61 run the charger-pack model on the Mac mini through the session's commands: walk at zero with two nudges, groundpick phase 0.33, phase 1, walk with the head commands. Each hold is compared with `real_windows.json`; the scan's camera heights (stand 226.3 mm, bend 14.5 mm) were not used to choose the cases, so they act as a held-out check. About 3 s per run.

The main result: in the bend both real ankles stall. Their goals sit on the 1.571 rad clamp from about 1 s after the command until the rise, and the joints stop at -1.241 and +1.256 within 1 s, moving 0.02 rad at most in the next 30 s. The servo holds 0.32 rad of error against a goal it never reaches. The sim's ankles go on to -1.37 and +1.43 with 0.07-0.11 rad of error.

Trunk pitch as the brain sees it, sim minus robot in stand / bend / second stand, camera height stand / bend:

- Chain, sensor bias 4 deg: +0.6, -4.6, -0.5 deg; 239.8, 23.9 mm. Mean joint error 0.071 rad.
- Ankle limit 1.25 rad, sensor bias 4: +0.6, +0.3, -0.5 deg; 239.8, 15.6 mm. Mean joint error 0.057 rad.
- Ankle limit 1.25 rad plus neck -5 deg, sensor bias 4: +0.1, -1.4, -1.0 deg; 228.9, 15.8 mm. Mean joint error 0.043 rad. Standing neck error -0.041 rad against the robot's -0.046, where the chain gives the opposite sign (+0.06).
- Ankle limit 1.25 rad plus hidden ankle 2.5 deg, sensor bias 2 (the trim half right): +1.8, -0.6, -0.2 deg; 229.4, 15.5 mm. Mean joint error 0.043 rad. At bias 0: +0.1, -2.2, -2.1 deg; 225.4, 15.2 mm, joint error 0.052 rad.

Across all 189 plant and bias pairs (128 stayed up), 8 of the 10 lowest joint errors carry the ankle limit, and none of the limit-free cases fits both the joints and the bend. The sensor bias stays open: it trades against a small hidden ankle angle, so bias 4 with none, bias 2 with 2.5 deg and bias 0 with 2.5 deg all land within the sim's own 2 deg spread between holds. This run gives no reason to change the 4 deg trim and no proof of it.

The limit was set from the robot's own ankle angle, so the matching ankle error proves nothing. The bend trunk and camera height were free to miss and did not.

Why this is contact and not servo weakness: `ankle_clearance.py` closes the model's ankle with foot and shin meshes. Away from the hinge the foot's orange part comes 1.4 mm from the shin servo at 1.25 rad, 0.8 mm at 1.30 and under 0.5 mm from 1.35. The largest ankle angle in the logged robot runs is 1.40 rad, in a fall at KP 400 with the foot off the floor (`robot-runs-20261030-t1/11_walk_at_015_neck08_fell.jsonl`), which fits that geometry. A 0.05-0.15 rad gap remains between the robot's 1.25 and the mesh's contact; the model's foot may not be the V1.24/V1.25 bracket on the robot, and nobody has looked at the real ankle in the bend. The sim has no collision between these parts and the policy's trained range runs to 1.571 rad.

Tried and dropped:

- Fixed ankle offsets alone (2.5, 5, 9.7 deg): they fit the bend or the stand, never both, because the bend needs about 5 deg more than the stand. Free ankle play (`foot_play` 1-9 deg) has the same problem and 9 deg falls on the rise.
- An upward force on the jaw during the hold, standing for the head resting on the floor: at 1 N the trunk loses 5-8 deg and the camera rises to 25-31 mm, and 1.5 N or more tips the robot. The neck still reads -1.41. The head is not carried by the floor to any useful degree; a light touch remains possible (the sim itself shows 0.2-0.5 N in the best cases).
- Floor friction 1.5: no change; 2.0 and up tips over during the nudges.

Not explained: in the bend the sim's knees and neck sag 2-3 times more than the robot's encoders show (knee error -0.29, +0.38 against -0.12, +0.18; neck -0.28 against -0.11, neck angle -1.40 against -1.27). The robot's camera is as low as the sim's while its neck encoder reads 0.13 rad higher, which suggests sag the encoder does not see. The one test of that (`blind` cases, encoder reads a fraction of the way toward the goal) makes the policy unstable and tips the robot during the nudges, so it says nothing either way. The 5 deg between the encoder chain and the IMU in the bend is therefore still open: the sim reaches 37 deg through more knee bend than the robot has.

Nothing on the robot, in the camera code or in the training model changed.

```
real reference:   python3 real_windows.py <brain_slice.jsonl>
all cases:        ~/.venvs/microduck-dyn/bin/python closed_loop.py --jobs 8 --only <plants> --out <json>   (Mac mini)
report:           python3 closed_loop.py --report <json>
clearance:        ~/.venvs/microduck-dyn/bin/python ankle_clearance.py
```
