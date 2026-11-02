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
- The trunk reading conflicts with `IMU_PITCH_TRIM_DEG` = 4 (`walk_brain.py`), which assumes the sensor over-reads forward. Lead, untested.
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

- Holding the logged goals open loop (`sim_static.py --settle`): the model falls or folds, because on the robot the policy keeps correcting. No conclusion about the offsets. A closed-loop run with hidden offsets has not been done.
- Position error as a load gauge (`load_check.py`): standing neck error 0.045 rad gives 0.08 Nm/rad on the chain and 1.0 on neck -10.4 deg, against about 0.96 in the sim's servo, which favours a real forward offset. But standing head error reads 0.176 rad at low load after the rise (0.14 Nm/rad), so friction can hold that much error. Weak support only. Logged `cur_ma` runs about 8 times under the torque the same errors imply; do not read it as absolute torque.
- Bend neck: the error falls from 0.229 to 0.10 rad the moment motion stops while the modelled load stays 0.23 Nm. Friction or the head resting on the floor would both do this; the fitted head clearance is about 3 mm.
