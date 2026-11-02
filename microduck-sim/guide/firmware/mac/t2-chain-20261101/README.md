# T2 (picture pick) in the as-built brain harness, 2026-11-01

`run_chain.py` runs walk-up plus T2 through the real `walk_brain.Brain` on the as-built MuJoCo model; `diag.py` separates harness from policy; `matrix.py` runs the gap study's nine placements, seeds 0-2 (27 runs per row). Run on the Mac mini; `results/` holds the rows.

Matrix, as train / handback / end / pinched of 27:

- seepick61 (floor object input): 150 mA training ellipsoid 18/18/13/20; real sphere 150 mA 7/5/3/9; sphere 300 and 1470 mA 7/5/4/10.
- spx-b_1800: ellipsoid 150 mA 6/6/0/6; sphere 150 mA 2/1/0/2; sphere 300 and 1470 mA 3/2/0/3.
- spx-a_2500: ellipsoid 2/2/0/3; sphere 0/0/0/0.
- spx-a_1400: ellipsoid 3/0/0/5; sphere 1/1/0/1.
- spx-b_2400: 0 everywhere, though it led the Kaggle evaluation.

spx-b_1800 is the candidate deployed to the robot. On the real sphere jaw current barely changes the result, so jaw force does not explain the sphere gap. No T2 run held to the end. Robot baseline: seepick61 held the real ball once at 150 mA (10/30 03:22), so the sim may be pessimistic for the sphere; the robot run decides.

## First robot run, 2026-11-01 21:01

`seepick.py --color orange --t2` (HSV 170,50,150..18,255,255, spx-b_1800, jaw 150 mA, charger pack). Try 1 lost the ball under the picture after a creep; try 2 picked at dx +1.3 dy -2.1 cm and the jaw held the ball, against the prediction from the matrix above. The duck then fell 0.9 s after the hand-back to stand61. Rows: `robot-20261101/brain_pick_fall.jsonl`.

Cause: with the holding bit on, T2 keeps the neck bowed (robot -1.14 rad at the hand-back, stand61's default +0.35, 1.49 rad off; action -1.05). Without the bit it returns to +0.39 by phase 0.6; seepick61 with the bit returns to +0.42. stand61 then sees a pose outside its training: first-ticks action 2.05 rad on left_hip_pitch, gyro 6 rad/s, action over 3 rad at 0.87 s, the guard's open-loop stand finished the fall. The sim reproduces the bowed neck (`holdbit2.py`) and the shaking (gyro 3.56 rad/s, ball held to the end 0 of 6) but not the fall itself, so sim falls do not clear a repair; compare gyro and held-to-end.

Repairs, six T2 runs that really hold (`handback_fix.py`, median, held at hand-back / held to the end / peak gyro rad/s / stable after s):

- current: 6 / 0 / 3.56 / 1.4-1.6
- holding bit off at phase 0.60 or 0.70: 3 / 0 / 2.0-2.1 / 0.7-1.5
- goal blend 1.5 s: 6 / 0 / 2.98 / 1.8-2.4
- bit off 0.70 + blend 1 s: 3 / 0 / 5.57, 3 falls
- seepick61 finishes the rise from phase 0.50 once holding: 6 / 3 / 1.17 / 0.2-0.8; from 0.44 and 0.58 the same holds at gyro 2.04 and 1.53

The flags are in `walk_brain.Brain` (`sp_rise_old_phase`, off by default, nothing on the robot changed). Six runs of the training ellipsoid: a choice between repairs, not a pass rate.
