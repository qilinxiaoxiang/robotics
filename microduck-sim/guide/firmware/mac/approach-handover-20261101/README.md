# Approach hand-over to the T2 bite window (2026-11-01)

Question: when approach.py walks the duck to a 12 mm ball, does the ball end where the T2 picture pick
(`microduck_rl-grasp/cmu/grasp/T2-PIXEL.md`, spx-b_2400) can bite it? T2 picks 70 % within +-3 cm of the landing
spot 8.7 cm ahead of the foot-frame origin (polar window: |r - 0.087| <= w and |bearing| <= w / 0.087 rad, so
+-20 deg at w = 3 cm), 32 % within +-8 cm, 18 % over 8-25 cm.

Setup: `approach_sim.py` (as-built 10/15 model, drift 0.015 N m, trim -1.108, sim walk 0.11 m/s), ball height
0.012 m, 25 placements (r 0.30-0.90 m x bearing -40..+40 deg), one run each, on the Mac mini.
`run_batch.sh <dir>` runs them, `summarize.py <dir>` scores the true end position (`need_w` = the smallest T2
window that contains it). `variant.py` overrides approach.py's STOP_R, DONE_BEARING and DONE_R[1] in the sim only.

Results (arrived / 25, fraction of all 25 placements ending inside the +-3 cm window, falls):

- runs (approach.py as is: STOP_R 0.145, DONE_BEARING 25 deg, DONE_R 0.05-0.20): 23 arrived, 52 % in the window,
  0 falls. The ball ends 9.3-13.6 cm ahead and mostly 10-20 deg left: a fixed offset, about 2.5 cm too far.
- runs-varA (STOP_R 0.125, DONE_BEARING 10, DONE_R max 0.117): 13 arrived, 52 %. Every stop lands in the window, but
  the 10 deg bearing check sends close stops into re-approaches that cannot correct a few degrees.
- runs-varB (STOP_R 0.125, DONE_BEARING 18, DONE_R max 0.117): 23 arrived, 92 %, 0 falls; every arrival is in the
  window (need_w 0.8-2.7 cm). The two others ended "too close" (walk61 does not step back).
- varB with the projection pitch 2 deg off: +2 deg 76 %, -2 deg 80 %.
- drift 0.023 N m (the regime where the trimmed walker cannot turn right): varB 12 %, the original constants 16 %;
  that failure is the drift, not the stop constants.

Expected sim pick from a walk-up with varB: about 0.92 x 0.70, near 65 %.

Not covered: the robot walks 0.15 m/s against the sim's 0.11, so its stride coasts further after the stop; the model
is the 10/15 bench-backpack as-built, not today's charger pack; one seed per placement; T2 itself not run from these
end states (the window rates above are T2's uniform-window rates).
