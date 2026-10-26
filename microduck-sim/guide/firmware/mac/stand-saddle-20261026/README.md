# Open-loop stand with the A7Z on the saddle (2026-10-26)

Result: `STAND_POSE` neck_pitch 0.25 rad (legs at NEUTRAL), D-030. Sim only; not yet stood on the robot.

Robot evidence: Mac mini bridge telemetry history (run app1026-212034). stand61 at zero command held -2.8 deg (back) with the neck at -0.03; switched to the open-loop stand (NEUTRAL, KP 400) it leaned back -5, -8, -10 deg over 2.5 s while the neck went to 0.29, then was handled and torque went off. `stand61_real_1026.json` is the mean stand61 pose (96 rows).

Model: microduck_rl cmu `plugged` manifest at 1f2ab62c (saddle D-022, rear lid; 859.0 g). Whole-robot COM shift dx by the comsim mass pair. Every case starts from the stand61 pose and ramps 2 s to the candidate, as walk_brain does.

- `base`: NEUTRAL at dx 0 rests on the toes (+11 deg); at -2 mm it falls back at 24 s, at -3 mm at 2.5 s (the robot's speed): the robot's COM sits about 3 mm behind the model's. stand61's whole pose or neck falls forward at 0 to -1 mm.
- `neck`, `robust`, `mid`: neck 0.25 holds over -1 to -4 mm, both 0.1 m/s pushes and friction 0.4 at -3 mm (rest 1.4 deg); 0.30 falls back from -3 mm, 0.20 and 0.225 rest on the toes at -3 mm and fall forward at -1.
- `takeover`: stand61 from neck 0.25 at -3 mm: max action 0.27 rad, tilt 2.7 deg; from NEUTRAL the robot has fallen before the switch.
- `walk_neck025_s*.json`: `brain_sim_check.py --manifest plugged --com-x -3 --stand-s 4 --vx 0.25 --walk-s 6`, seeds 0-2: no fall, tilt 5.5-6.2 deg, 0.52 m.

Unmodelled: saddle lid (5.9 g), board screws, the U20CAM and its 1 m cable (Shawn's plan was two turns on the saddle). The calibration to the robot's fall absorbs what was fitted on 10/26; anything added since moves the COM back.

    ~/.venvs/microduck-dyn/bin/python olsearch.py <base|neck|robust|mid|takeover> [--workers N]
