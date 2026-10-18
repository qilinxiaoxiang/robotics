# Foot sole material, 2026-10-18

Official reference: Pollen's maintainer notes that the real Microduck has a grippy polyurethane (PU) sole, while training randomised foot friction mu 0.7-1.3 (`microduck_rl/scripts/infer_policy.py`, `--foot-friction` help, commit bfc0ed4, 2026-08-19). The runtime repo (pollen-robotics/microduck, read 2026-10-18) names no sole material.

Our feet ran on sandpaper over 0.5 mm 3M foam tape. RoboClub had only a 2 mm rubber roll. Selected: 0.8 mm 60A silicone sheet with adhesive backing, Amazon B0B4X47N19 (9 x 12 in, arrives Tue 10/20), $14.99, in the cart, not paid ([offers](offers.json), [authorization](authorization.json)).

Cutting: the foot bottom is flat over about 39 x 27 mm and curves up 1 mm at 3.5 mm and 2 mm at 5 mm past that edge. In the sim walk at 0.25 m/s about 90 % of floor contacts sit on that curve (foot tilt 6-10 deg), so the sheet covers it: trace the foot outline on the backing paper, cut 2 mm inside the line (about 50 x 38 mm), cut a small V notch at each corner, and press the sheet over the curve from the centre outward.

Contact study: `~/.venvs/microduck-dyn/bin/python sole_contact_sim.py out.json --model asbuilt --volt 7.0 --drop 0.04 --vx 0.25 --walk-at 4 --walk-s 6` (walk61, as-built model, real-condition flags). Standing: all contacts on the flat. Walking: contact height above the flat median 0.5 mm, 90th percentile 1.1 mm, max 1.6 mm.
