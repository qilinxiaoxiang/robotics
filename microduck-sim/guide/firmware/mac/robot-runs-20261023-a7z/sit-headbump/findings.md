# 2026-10-23 sit/stand: head hit the floor on the 4th rise (run app1023-204119)

Evidence: `sit-region.jsonl` (log rows from line 42800 of the A7Z tick log), `run.out`, `ana2.py`, `replay_rise.py`.

- Four sits all reached the seat (knees 1.28 / -1.24). Rises 0-2 peaked at 8.6, 5.8 and 7.5 deg forward pitch, with the neck action never below -0.43 rad. The as-built sim rises peak at 4.6 deg with the neck at no less than -0.36 (4 seeds, `brain_sim_check.py --model asbuilt --drop 0.04 --sit-at 3 --unsit-at 7`).
- Rise 3: pitch passed 10 deg at +0.71 s. From there the sitstand61 neck action ran away: -0.34, -0.79, -1.23, -1.60, -2.53, -3.45, -3.75 rad within 0.3 s, and the body pitched to 25 deg. An offline replay reproduces every logged action to 0.003 rad. Swapping any single observation block (gyro, gravity, joint pos, joint vel, last action) back to a good-rise tick does not stop it. This is a closed loop: the head moving forward pitches the body further. Pitch alone produces only -0.55 at 20 deg.
- The hard-action guard clipped two ticks to -3.0 rad, sent them, and on the third tick stopped to monitor while holding the last goals. Neck ID12 goal tick 3776 (about -2.65 rad, outside the trained MJCF range of -1.57..+1.05) was held at full gain. The neck reached -2.50 rad (q) with the head pressed on the floor. The body itself came back to 0 deg pitch, so it did not fall.

Fix candidates (not applied): clamp policy goals to the trained joint ranges; on a sit/groundpick trip, send the head joints back to default instead of holding the runaway goal; find out why the robot's rise pitches 2-4 deg further forward than the sim.
