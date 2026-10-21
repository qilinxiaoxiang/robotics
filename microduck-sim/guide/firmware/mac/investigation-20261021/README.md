# MicroDuck problem sweep, 2026-10-21

Shawn asked for every open MicroDuck problem to be investigated and turned into step-by-step guides that serve the final
goal (`microduck-sim/PROJECT-CONTEXT.json` `final_goal`, D-019). The robot was off and the A7Z offline: everything here
is file, log, literature and as-built simulation work. Current robot values come only from
`microduck-sim/CURRENT-STATE.json`.

The Chinese guide pages that cite these notes live on Shawn's MacBook in `~/code/reports/20261021-microduck-*.html`
(overview page `20261021-microduck-overview.html` first). The scripts were run from a session scratch folder; `<scratch>`
in a note means that folder, and the outputs it names are copied here.

- `findings-sit.md`, `replay_sit.py`: why the remote sit stalls standing (the loaded leg servos do not follow the
  sitstand policy's first moves); the `sit: STALLED` notice that came out of it is in `walk_brain.py` and
  `test_sit_stall.py`.
- `findings-stand.md`, `osc_1018d.py`/`.json`, `an_1018d.py`, `an_lift.py`, `foot_wedge.py`/`.json`,
  `foot_roll_static.py`/`.json`, `sole_roll_sim.py`, `run_sole_roll.sh`/`.log`, `roll_*.json`: stand falls and the new
  feet (KP 400 too soft, the foot wedge is the same on old and new feet, sole roll changes nothing for stand61).
- `findings-quack.md`, `quack_sim.py`, `run_matrix.py`, `quack-runs/*.json`: quack head profile study behind
  `QUACK_HEAD_S` 0.6 s and `QUACK_HEAD_RAMP_S` 0.15 s.
- `findings-slope.md`, `slope_sim.py`, `slope-results.jsonl`: the tilted RoboClub table; measure it before any slope
  training.
- `findings-touch.md`, `touch-gesture/`: stroke versus pat recognition from the five head pads plus servo load; draft
  recorder, features and trainer, not yet run on the robot.
- `findings-cooling.md`, `cooling/`: A7Z heat and resets (resets at 86 °C against a 110 °C trip, so a 5 V dip is the lead), loop slowdown with heat, heatsink gap, vent zones, face notches, Zero 2 W comparison.
- `findings-sim2real.md`: the gap list, one real failure at a time into the sim.
- `findings-pickup.md`: the four-step pickup roadmap and what each step still needs.
