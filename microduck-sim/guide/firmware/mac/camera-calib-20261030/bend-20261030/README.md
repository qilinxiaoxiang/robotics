# Bent-neck camera model fit (PLAN-continuous-vision N1), 2026-10-30

Result: **acceptance not passed**, `u20cam_mount.json` left unchanged. Four captures (the 00:29 sweep1 and the hold
sweeps 2-4 with the ruler re-placed each time) now give 54 identified cm-tick rows in six bend poses. The best
model (`bend_fit.json` model `pivot`: a neck-pivot offset of +3.1 / -12.9 mm in trunk x / z) brings the full-fit
tick error from -20..+2 mm to within +-7.2 mm, but held out by phase the worst tick error is 8.8 mm (bar 5 mm), held
out by sweep 8.2-9.0 mm, and the standing holdout point stays at 18.5 mm (bar 10 mm). The pictures also show the
camera 20-60 % closer to the ruler than any fitted chain says, so the defect is not a parameter the chain has.
Numbers below are from `bendfit.log` / `bend_fit.json` / `spacing_check.log`.

## Data

- sweep1 (`frames/`, `rows_matched.json`): the 00:29 ground-pick sweep. Phases 0.12 / 0.20 / 0.28 / 0.33 are one
  pose (neck -1.33, head -0.26..-0.31, trunk 33-36 deg); the ruler is a sliver at the right picture edge without
  any legible digit. The rise (phase 1.00, f012106..f012117: neck -1.60, head +0.33, trunk 10 deg) shows the ruler's
  0-3 cm with the digits 1 and 2 legible. Ruler centre y = -0.022 (cm edge -0.0093), zero at the toe-line midpoint.
- sweep2 (`sweep2/`, 351 frames): holds 0.05 / 0.08 / 0.12 / 0.18 / 0.25 / 0.33 then the rise; neck -1.335, head
  -0.07 / -0.15 / -0.20 / -0.27 / -0.30 / -0.30, trunk 27-34 deg. Ruler re-placed, zero on the toe line, side not
  recorded. Digits 6 and 7 legible at 0.08, 6 at 0.05; 0.12 is a sliver, 0.18 and deeper pure blur (the lens cannot
  focus at 2 cm).
- sweep3 (`sweep3/`, 228 frames): holds 0.05 / 0.08 / 0.12 then rise; neck -1.282, head -0.03 / -0.07 / -0.17,
  trunk 25-29 deg. Ruler about 3 cm further left; digits 6 and 7 (0.08, 0.12) and 6 (0.05) legible.
- sweep4 (`sweep4/`, 224 frames): same holds, neck -1.290, head -0.06 / -0.11 / -0.19, trunk 26-30 deg. Ruler a
  further 3 cm left, through the middle of the picture with the cm scale at the left picture edge; the mm ticks are
  seen but no digit is legible on any frame (blur), so sweep4 contributes edge rows only.
- Joint states of sweeps 2-4: `rows.json` stores, for every frame of a hold window, the state logged at the END of
  the previous window (lag up to 6.9 s), so `sweeps_match.py` takes the hold pose of window k from the rows of window
  k+1 and keeps only the last static stretch of each window (`rows_matched.json`, field `use`).
- Standing reference: `../u20cam-mount-1030-far+ruler+bend.json` (far tiles + standing ruler ticks; its by-eye
  `bend_*` rows are dropped). Intrinsics: `../../u20cam_intrinsics.json` (calibrated fisheye, rms 0.40 px, 22 frames).

## Method

1. `edgeband.py`: the scale edge is the brightness recovery right of the board's dark side, per row, inside a window
   round a guessed line. `tickprof.py`: whiteness profiles along the straightened edge, local maxima = mm ticks.
2. `readticks.py` (sweep1) and `readticks_sweeps.py` (sweeps 2-4) -> `bend_ticks.json` and `check_<frame>.png` (3x
   crops with the detected edge, the mm peaks and the assigned cm rows). The digit rows were read by eye on 5x CLAHE
   crops of one frame per hold window (the digit is centred under its long cm tick on this ruler, +-8 px = +-0.5 mm);
   in the other static frames of the window the row is snapped to the nearest mm peak within 8 px. Where only one
   digit was legible the second cm tick is the tenth mm tick from it, checked against the long tick in the picture.
   Verified by eye on `check_f012106..16` (sweep1), `check_f091060`, `check_f091111`, `check_f093206`,
   `check_f093294`, `check_f093320`. Rows per frame agree within 7 px (< 0.5 mm).
3. `bendfit.py` -> `bend_fit.json`, `bendfit.log`: `BendKin`, a `DuckKin` subclass whose `place()` adds a neck-pivot
   translation (trunk frame), neck / head zero offsets, IMU pitch / roll / yaw biases, the camera offsets + lens
   shift, and one RULER_Y nuisance per re-placed ruler (sweeps 2-4; weak prior at the described placement, sigma
   20 mm). Head gain 0.92 kept and, as in `duck_kin.place`, applied to the MEASURED reading. Observations: ticks
   (ray hit on the board top minus toe_x + cm/100 and the sweep's y edge), the scale-edge column at rows 30..330 of
   every frame (lateral only, needs no identity), the standing captures with the existing `object_centre`
   convention. Levenberg-Marquardt, one weight per labelled point, std from the per-point Jacobian. Held out (a) by
   (sweep, phase) group, (b) by sweep: sweep1 -> sweeps 2-4, sweeps 2-4 -> sweep1, and each of sweeps 2-4 left out;
   for a held-out sweep only its RULER_Y is re-fitted on the test rows, which cannot change a tick's x residual.
4. `spacing_check.py` -> `spacing_check.log`: the model's predicted mm spacing along the edge (px/mm) against the
   spacing the pictures show. `predict_held.py` -> `pred_<frame>.png`: the fitted ruler drawn over frames.

## Result (mm, model minus true; x along the ruler, y lateral)

Before (current `u20cam_mount.json`, sweeps 2-4 ruler at the described position): standing rms 6.4, standing
holdout 15.8; sweep1 rise 1 / 2 / 3 cm x -20.0 / -8.0 / -0.6; sweep2 0.05 (5 / 6 cm) -15.9 / -5.6, 0.08 (6 / 7)
-9.1 / -0.6; sweep3 0.05 -9.5 / -1.7, 0.08 -3.6 / +2.0, 0.12 -7.4 / +2.2. Every frame shows the same slope of
+5.6..+10.3 mm per cm (the farther tick less negative). Edge y rms 8-9 (sweep1 holds), 11-17 (sweep2), 27-36
(sweep3), 16-20 (sweep4): the described ruler positions are off by 1-3 cm, see RULER_Y below.

Model `pivot` (pitch 10.96 +-0.11 deg, yaw 1.62 +-0.09, roll -0.44 +-0.17, px +3.07 +-0.47 mm, pz -12.93 +-0.70 mm):
standing rms 4.9, standing holdout 18.5. Full-fit ticks: sweep1 rise +2.9 / +5.7 / +6.0 (y +4.7); sweep2 0.05
-7.2 / -3.8, 0.08 -5.2 / -2.6; sweep3 0.05 -3.0 / -0.4, 0.08 -1.1 / 0.0, 0.12 -2.4 / +1.1. Edge y rms 0.4-4.8 in
every group. Slope within a frame +1.1..+3.5 mm per cm, i.e. a third of before but not gone.

Held out by phase (`pivot`): s1 rise 8.8 (ticks +8.3 / +8.8 / +7.1), s2 0.05 7.7, s2 0.08 5.5, s3 0.05 3.2,
s3 0.08 1.1, s3 0.12 2.5; the sweep1 holds, sweep2 0.12 and all of sweep4 have no tick (edge y rms 0.6-3.5).
Held out by sweep: train sweep1 -> test sweeps 2-4 worst 9.0 (s2 0.05 -9.0 / -5.3, s2 0.08 -6.8 / -3.8, s3 within
-4.7..-0.2); train sweeps 2-4 -> test sweep1 worst 19.9 (+19.9 / +15.5 / +9.9, trained pz -24.1); all but s2 ->
s2 8.2; all but s3 -> s3 3.5. The two poses disagree about the pivot: sweep1 alone wants pz -12.8, sweeps 2-4 alone
pz -24, and each pose predicts the other with 9-20 mm error.

Other sets (`bendfit.log`): `pivot+imuy` (imu_y 3.1 +-0.6, determined now by the lateral rows) and `pivot3+imuy`
change the tick errors by < 1 mm, make the standing holdout worse (19-20) and the sweep1 holdout much worse (17-19,
imu_y undetermined without sweep1). `pivot+shift` (sx -7.9 +-1.6, sz -12.3 +-1.9, px +16 +-2) and `pivot+zeros`
(neck0 +7.0 +-1.2 deg, head0 +11.6 +-1.8 deg, pitch 5.6) lower the full-fit residual by 1-2 mm and improve the
sweeps 2-4 holdout to 6.7-6.8, but their sweep1 holdout is 25-38 mm: they fit the bow by moving the camera and
cannot fit the rise. `base` (offsets only) leaves everything as before.

RULER_Y (cm edge = -0.0093 + dy, `pivot`): sweep2 dy -5.6 +-0.6 mm (data move it 6 mm right of the described
-0.022 centre), sweep3 +2.8 +-0.5 (described +30: the ruler was 8 mm, not 3 cm, left of sweep2's), sweep4 +32.5
+-0.7 (described +60: 38 mm left of sweep2's). Every model agrees within 1 mm. The lateral tick residuals of sweeps
2-3 are then 0-4 mm; sweep1's +4.6 mm lateral offset remains (its ruler y is fixed at the measured -0.022).

## What limits it

- **Picture scale** (`spacing_check.log`): the pictures show 13-20 px per mm along the ruler; the current mount
  predicts 9-12 (ratio 1.65) and the `pivot` model 8-16 (ratio 1.3: 1.1-1.26 in sweeps 2-3, 1.5-1.6 in the sweep1
  rise). The real camera is that much closer to the ruler than the chain says (in `pivot` the camera sits 2.2-3.5 cm
  over the floor; the pictures want about 2 cm in the bow and 1.5 cm in the rise). The in-frame slope of
  +1..+3.5 mm per cm is this scale error, and the sweep1 / sweeps 2-4 disagreement is the same error at two neck
  angles. A pivot translation, a lens shift, joint zeros or an IMU bias each fix the floor x of the ticks at one
  pose and not the scale, so none of them passes. Candidates the fit cannot see with these poses: a neck or head
  link length (the chain's head geometry from the CAD), the real head_pitch gain in the bow (0.92 is a standing
  fit), and servo give under the head's weight in the bow.
- Held poses deeper than 0.12 have no legible tick (blur, camera about 2 cm from the floor) and sweep4's middle
  placement is blur at every height; sweep1's holds have no digit at all.
- The standing holdout point x0.64_y-0.30 (16-20 mm) is a pre-existing far-point outlier of the standing fit.

Which heights another sweep would be worth: nothing closer than the 0.12 hold (digits need the camera at least
about 3 cm from the ruler, 0.18 and deeper is blur). What is missing is poses BETWEEN the bow and the rise, e.g.
neck -0.6 / -0.9 / -1.1 with head 0 and trunk level, camera 5-10 cm over the floor with the ruler's 5-15 cm in
focus, and the rise pose (neck -1.6, head +0.33) at two trunk pitches; those separate a link-length / gain error
(which grows with neck angle) from a pivot offset (which does not).

## For duck_kin

`duck_kin.py` has no field for a neck pivot offset; it was not edited and the mount file is unchanged. If the
`pivot` set is wanted despite the failed acceptance: add `"neck_pivot_offset_m": [0.00307, 0.0, -0.01293]` to
`u20cam_mount.json`, read it in `DuckKin.__init__` (`self.neck_pivot = np.array(mount.get("neck_pivot_offset_m",
(0, 0, 0)))`), add it to the `neck` body's `p0` in `place()` (`p0 = b["p0"] + (self.neck_pivot if b["name"] ==
"neck" else 0.0)`), include it in the `place()` cache key, and set `offsets_deg` to pitch 10.964 / yaw 1.616 /
roll -0.440. `BendKin.place` in `bendfit.py` is the reference.

## Files

`edgeband.py`, `tickprof.py`, `readticks.py`, `readticks_sweeps.py`, `sweeps_match.py` (`sweep2_match.py` is its
sweep2-only first version), `bendfit.py`, `predict_held.py`, `spacing_check.py` (scripts); `bend_ticks.json`
(observations), `bend_fit.json`, `bendfit.log`, `spacing_check.log`, `predict_sweeps.log` (fit and checks);
`check_*.png` (tick reading checks, 3x), `pred_*.png` (fitted ruler over frames); `frames/`, `rows_matched.json`,
`sweep2/`, `sweep3/`, `sweep4/` (data as captured, each with `rows_matched.json`), `f011992.png`, `f012099.png`,
`f012112.png`, `montage_rise.png`, `gpsweep.py`.
