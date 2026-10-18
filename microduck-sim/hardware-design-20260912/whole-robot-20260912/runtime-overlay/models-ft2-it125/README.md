# models-ft2-it125: walk61 fine-tuned 25 actor iterations in the staged as-built sim (2026-10-16)

`walk61.onnx` here is Modal run ft2 at iteration 125 (100 critic-only warm-up iterations from Pollen's BEST_alpha_walking
= the overlay's walk61, then 25 PPO iterations of the actor, learning rate clamped at 3e-4, staged randomization and
as-built masses; `ft2_run_record.json`). stand61.onnx and groundpick61.onnx are the unchanged overlay files.
Same 61-input layout and metadata as walk61; the runtime needs no change: pass this directory as `--models`.

As-built MuJoCo suite (7.4 V, 10 s walk at 0.3 m/s; `suite_asbuilt_vs_walk61.jsonl`), ft2 vs walk61: no fall in either;
distance 1.74 vs 1.57 m nominal, 1.73 vs 1.56 with 8 % dropped reads and a 35 Hz IMU (a stress case, harsher than the robot; the current sensor condition is in microduck-sim/CURRENT-STATE.json), 1.55 vs 1.43 at 6.3 V,
1.72 vs 1.47 with a 4 deg IMU pitch bias; max tilt 7.7 vs 5.9 deg nominal and 10.9 vs 7.6 in the second drop seed
(worse), 8.3 vs 9.2 in the first (better); action jumps unchanged (2 vs 1 nominal, 32-37 vs 29-31 with drops).
The run was stopped at iteration 125 by a guard that read the command manager's episode-accumulated tracking error,
which grows with episode length (false positive); the resumed run uses per-step tracking instead.

## Caveat found 2026-10-16 20:30 (parent session's re-check, confirmed here): no stepping at 0.25 m/s

As-built sim, 7.4 V, 10 s: walk61 steps at 0.25 m/s (1.15 m) and 0.30 (1.57 m), not at 0.20. ft2 at iteration 100
(actor still frozen) matches walk61 (1.17 m at 0.25). ft2 at iteration 125 does not step at 0.25 (0.003 m, max
|action| 0.35) and still walks at 0.30 (1.74 m); ft2 at iteration 150 does not step even at 0.30. The fine-tune
raised the minimum stepping command within 25 actor iterations and removed stepping within 50: the standing drift
seen in ft1 (D-016), only slower. This policy is therefore a knife-edge: usable only for commands of 0.30 m/s and
up, and on the real servos (friction deadband) its threshold may sit higher still. The robot's everyday 0.25 m/s
command keeps walk61. The resumed run was stopped at iteration 150 ($0.33 total for ft2).
