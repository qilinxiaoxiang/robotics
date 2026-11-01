# t3bt_a on the robot, 2026-10-31 evening

Brain restarted 20:17:56 with `models-t3bt-a` (t3b + charger-lead training, seed 1 final; fork branch cmu/t3-tether,
FINETUNE-DELTA.md). Robot on the charger backpack with the lead trailing (CURRENT-STATE `power`, 7.2 V idle).
namecall (`--turn`, another session) attached in the background; no call during these steps. Battery guard armed by
`--supply auto` on the 7.2 V charger rail (rule assumes only a 2S pack reads 7.2 V); it did not trigger.

- `0_stand.jsonl` (20:19:47, closed-loop stand): tilt 1.1 -> 0.3-0.4 deg, max|a| 0.20, 2/247 missing reads, IMU age ~0.03 s.
- `1_walk.jsonl` (20:19:57, 0.25 m/s for 3 s, default head): no fall. `compare_walks.py`: tilt max 7.8 deg, mean 4.3,
  act p95 1.04, 10 jumps (3.33/s), missing reads 4.3 % in the segment; settled to 1.9 deg after the stop.

Same metric on earlier robot walks: walk61 6.4 / 7.5 deg, 2.01 jumps/s (t2b/4_walk61_after_a/b); walk61 over its
camera-session walks max 8.6 deg; t2b default head 8.7 deg, 1.67/s; T1 (2_walk_fell) 29.3 deg, 21.8/s. One walk only:
t3bt_a sits in walk61's tilt range; its jump count is above walk61's two walks, which the calibrated sim did not
predict (0.87 vs 3.38/s).
