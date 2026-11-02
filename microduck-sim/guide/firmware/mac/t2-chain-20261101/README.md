# T2 (picture pick) in the as-built brain harness, 2026-11-01

`run_chain.py` runs walk-up plus T2 through the real `walk_brain.Brain` on the as-built MuJoCo model; `diag.py` separates harness from policy; `matrix.py` runs the gap study's nine placements, seeds 0-2 (27 runs per row). Run on the Mac mini; `results/` holds the rows.

Matrix, as train / handback / end / pinched of 27:

- seepick61 (floor object input): 150 mA training ellipsoid 18/18/13/20; real sphere 150 mA 7/5/3/9; sphere 300 and 1470 mA 7/5/4/10.
- spx-b_1800: ellipsoid 150 mA 6/6/0/6; sphere 150 mA 2/1/0/2; sphere 300 and 1470 mA 3/2/0/3.
- spx-a_2500: ellipsoid 2/2/0/3; sphere 0/0/0/0.
- spx-a_1400: ellipsoid 3/0/0/5; sphere 1/1/0/1.
- spx-b_2400: 0 everywhere, though it led the Kaggle evaluation.

spx-b_1800 is the candidate deployed to the robot. On the real sphere jaw current barely changes the result, so jaw force does not explain the sphere gap. No T2 run held to the end. Robot baseline: seepick61 held the real ball once at 150 mA (10/30 03:22), so the sim may be pessimistic for the sphere; the robot run decides.
