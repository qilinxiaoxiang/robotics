# Extra head mass (6530B heatsink what-if), simulation only, 2026-10-22

Question (Shawn): would 50 g more in the head (Radxa 6530B heatsink on the back-to-back A7Z, D-020) still balance?
Mass placed at `stand_sim.PI_POS` on `jaw_soft` (the head board position, world x 0.059 m ahead of the trunk origin,
z 0.250 m). As-built MuJoCo model (`brain_sim_check.cfg(model="asbuilt")`), 7.0 V, 4 % read drops. Scripts need the
dyn venv: `~/.venvs/microduck-dyn/bin/python <script>`.

- `head_mass_sim.py` / `head_mass_sim.json`: neck joint gravity loads from the model. Head subtree 0.314 kg of 0.829 kg;
  the most loaded neck joint (head_roll) carries 0.058 N m, +0.025 N m for 50 g at the board: 0.08 N m against the
  XL330-M288-T stall 0.52 N m at 5 V. Servo load is not the limit.
- `openloop_stand_0-40g.jsonl` (`head_mass_threshold.py`): open-loop STAND (walk_brain stand mode, kp 400) with
  +0/10/20/30/40 g, 12 s. +10 g leans 4.4 deg, +20 g 12.2 deg forward, +30 g falls forward at 8.1 s, +40 g at 4.7 s.
  The servo model gives under the forward lever; the static toe margin (head_mass.py, 21.7 mm at +50 g) does not
  save an open-loop stand.
- `stand61_0-60g.jsonl` (`head_mass_stand61.py`): stand61 (walk mode, zero command) from 1.0 s for 20 s, seeds 0/1.
  All stand through the 20 s; the "fell_at" 21.5-21.8 s is the known walk->stand swap fall at the switch back. Max
  tilt during stand61: 4.5 deg (+0), 5.5 (+20), 7.1 (+30), 11.7 (+50), 16.0 (+60 g); at +60 g actions jump (4-6
  jumps, |a| up to 1.8) and the feet slip 70-137 mm.
- `stand_ramp_then_stand61_at12s.jsonl`: the first run (open-loop ramp, stand61 only from 12 s): +50 g fell at 1.76 s
  and +60 g at 1.36 s in the ramp; +0 g stood and fell only at the switch back (27.7 s).
- `walk-runs/` plus seeds 0/1 in the session log: walk61 at 0.25 m/s for 6 s (`brain_sim_check.py --model asbuilt
  --manifest manifest-head+NNg.json --volt 7.0 --drop 0.04 --vx 0.25 --walk-at 4 --walk-s 6 --seed S`). Baseline 6/6
  stand, max tilt 5.9-6.2 deg, 1-3 action jumps. +50 g 6/6 stand, max tilt 11.7 deg, 0-5 jumps, |a| up to 1.4 (0.9
  baseline). +60 g 4/6 stand (seeds 1 and 2 fell about 1 s into walking), max tilt 16 deg, 11-30 jumps.

Reading: the learned policies absorb +50 g in simulation with half their tilt margin gone and +60 g is the edge. The
real robot has less margin than this model (10/17 jitter study: trunk gyro 4-6x sim; ft3 fell on the robot where the
sim never fell), so 50 g at the head board is not acceptable on the robot. Decision input for the D-020 revisit.
