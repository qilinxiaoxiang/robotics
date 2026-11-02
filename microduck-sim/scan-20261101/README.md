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
