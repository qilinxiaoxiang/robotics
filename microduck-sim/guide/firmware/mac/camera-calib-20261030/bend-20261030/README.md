# Bent-neck camera model fit (PLAN-continuous-vision N1), 2026-10-30

Result: **acceptance not passed**, `u20cam_mount.json` left unchanged. The best model (a neck-pivot offset of
+1.6 / -12.8 mm in trunk x / z, `bend_fit.json` model `pivot`) takes the rise-pose tick error from -20 / -8 / -0.6 mm
(1 / 2 / 3 cm) to +0.9 / +4.0 / +4.4 mm and the held-phase ruler-edge error from 8-9 mm to 1-2 mm, but the held-out
test of the rise pose is 5.3-6.7 mm (bar 5 mm) and the four held phases show no legible tick, so their x error cannot
be measured at all. Numbers below are from `bendfit.log` / `bend_fit.json`.

## Data

- `frames/*.png`, `rows_matched.json`: 195 frames of the 2026-10-30 ground-pick sweep (`gpsweep.py`), each with the
  measured joints `q`, trunk gravity `gb` and the capture-to-state offset `dt_ms` (within +-14 ms).
- Phases 0.12 / 0.20 / 0.28 / 0.33 (f011957..f012101) are one pose: neck -1.325, head -0.26..-0.31, trunk pitched
  33-36 deg. The camera sits about 2 cm over the floor and the ruler is only a sliver at the right picture edge
  (`check_f0119xx.png`, `check_f0120xx.png`): its scale edge and unlabelled mm ticks, no digit, no long tick that can
  be told from the short ones. No tick identity could be read there.
- The rise (phase 1.0) first dips the head further: f012106..f012117 hold neck -1.60..-1.62, head +0.35..+0.32,
  trunk 10 deg, and show the ruler's 0-3 cm with the digits 1 and 2 legible (`check_f0121xx.png`, 3x crops).
- Standing reference: `../u20cam-mount-1030-far+ruler+bend.json` (far tiles + standing ruler ticks; its by-eye
  `bend_*` rows are dropped and replaced by this folder's readings).
- The ruler is the DigiKey 12-inch PCB ruler (1.6 mm board, ticks on the board top at z = 1.6 mm), cm scale on
  the edge nearest the robot's x axis at foot-frame y = -0.0093, zero at the toe-line midpoint.

## Method

1. `edgeband.py`: the scale edge is the brightness recovery right of the board's dark side, per row, inside a window
   round a guessed line (`scale_edge`). `tickprof.py`: whiteness profiles along the straightened edge (A: ticks,
   edge+2..+9; B: long ticks; C: labels), local maxima of A.
2. `readticks.py` -> `bend_ticks.json`: rise frames f012106/08/10/12/13/14/16, the 1 cm and 2 cm ticks at the centre
   of their digit (the digit is centred under its long tick on this ruler; read by eye on 3x gridded crops, +-8 px
   = +-0.5 mm), the 3 cm tick as the tenth mm tick above the 2 cm tick where that count stays inside the picture
   (f012112 row 11, f012113 row 8). Held frames: 4 per phase, the edge line and the A-peak rows stored with
   `cm = null`. The automatic label pick (profile C) was tried first and mis-chose the white pad right of the digit
   by 15-25 px in several frames, so the digit rows were read by eye and the check pictures verified.
3. `bendfit.py` -> `bend_fit.json`, `bendfit.log`: `BendKin`, a `DuckKin` subclass whose `place()` adds a neck-pivot
   translation (trunk frame), neck / head zero offsets, IMU pitch / roll / yaw biases, and the existing camera
   offsets + lens shift (the head gain 0.92 is kept and, as in `duck_kin.place`, multiplies the MEASURED reading).
   Observations: bend ticks (ray hit on the board top minus toe_x + cm/100, y edge), the detected scale-edge column
   at rows 30..330 of every bend frame (lateral residual only, needs no tick identity), the standing captures with
   the existing `object_centre` convention. Levenberg-Marquardt, one weight per labelled point, std from the
   per-point Jacobian. Held-out test: each bend phase in turn dropped from the fit and predicted.

## Result (mm, model minus true)

Before (current `u20cam_mount.json`): standing rms 6.4, standing holdout point x0.64_y-0.30 15.8; rise ticks
1 / 2 / 3 cm: x -20.0 / -8.0 / -0.6, y -1.8 / -1.2 / -1.4; held-phase edge y rms 8.3 / 8.8 / 8.1 / 9.2 (phases
0.12 / 0.20 / 0.28 / 0.33).

Model `pivot` (pitch 10.85 +-0.15 deg, yaw 1.62 +-0.11, roll -0.57 +-0.21, px +1.55 +-0.72 mm, pz -12.79 +-0.90 mm):
standing rms 4.8, standing holdout 15.9; rise ticks x +0.9 / +4.0 / +4.4, y +4.5 / +4.7 / +4.6; held-phase edge
y rms 1.9 / 1.7 / 1.1 / 1.7. Held out: phase 1.00 (rise) ticks x +5.8 / +6.7 / +5.3 (worst 6.7); phases
0.12 / 0.20 / 0.28 / 0.33 edge y rms 2.1 / 2.0 / 1.3 / 1.9 (no tick x available).

Model `pivot+imuy` (adds an IMU yaw misalignment, 1.7 +-2.7 deg, not determined): rise ticks x +0.8 / +4.2 / +4.8,
held-out rise +3.9 / +5.2 / +4.4 (worst 5.2), standing holdout 17.7; otherwise the same as `pivot`. `bend_fit.json`
names it `best_model` because its held-out tick error is the smaller, but the extra parameter is not determined
(std above value) and the standing holdout is worse, so `pivot` is the model to carry; `acceptance.passed` is false
for both.

Other sets (`bendfit.log`): lens shift, neck / head zero, IMU pitch / roll and a ruler yaw / offset nuisance term
all come back with std at or above their value, lower the full-fit residual by at most 1 mm and make the held-out
rise error worse (9.5-29 mm): the data determine two numbers of the chain, the pivot position in the sagittal plane,
and nothing else. px is weak (std 0.7 of 1.6); pz (-12.8 +-0.9) is the finding.

## What limits it

- Held phases without ticks: at this pose the camera is about 2 cm over the floor and sees the ruler edge only. A
  ground-pick hold with the ruler moved 2-3 cm to the left (under the camera's centre), or the robot placed so the
  ruler's 5-10 cm labels fall in the picture, would give the missing readings.
- The rise ticks keep a slope (+0.9 -> +4.4 mm from 1 to 3 cm) and a +4.6 mm y offset that a pivot shift cannot
  remove: a scale error, e.g. the trunk lower than the rigid leg chain says in the bow (inner-tube soles) or a
  neck link length. One bow pose cannot separate that from the pivot. In the picture (`pred_f012112.png`) the
  fitted ruler still runs about 8 deg steeper than the real scale edge and its 2 and 3 cm ticks sit 47 / 90 px
  below the read rows; the floor-mm residual is small only because the model's px per mm is low there.
- The standing holdout point x0.64_y-0.30 (15.9 mm) is a pre-existing far-point outlier of the standing fit; the
  chain parameters do not move it.

## For duck_kin

`duck_kin.py` has no field for a neck pivot offset; it was not edited. To use the fit: add to `u20cam_mount.json`
`"neck_pivot_offset_m": [0.00155, 0.0, -0.01279]`, read it in `DuckKin.__init__` (`self.neck_pivot =
np.array(mount.get("neck_pivot_offset_m", (0, 0, 0)))`), add it to the `neck` body's `p0` in `place()` (`p0 = b["p0"]
+ (self.neck_pivot if b["name"] == "neck" else 0.0)`), include it in the `place()` cache key, and set
`offsets_deg` to pitch 10.853 / yaw 1.623 / roll -0.567. `BendKin.place` in `bendfit.py` is the reference.

## Files

`edgeband.py`, `tickprof.py`, `readticks.py`, `bendfit.py`, `predict_held.py` (scripts); `bend_ticks.json`
(observations), `bend_fit.json`, `bendfit.log` (fit); `check_*.png` (tick reading checks, 3x), `pred_*.png`
(fitted model's ruler drawn over frames); `f011992.png`, `f012099.png`, `f012112.png`, `montage_rise.png`,
`gpsweep.py`, `rows_matched.json`, `frames/` (the data as captured).
