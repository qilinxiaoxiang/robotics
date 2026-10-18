# OpenRB tray leg clearance (2026-10-09)

Verdict: keep the tray as printed. In the 98 adopted simulated walking traces (0.3 m/s, microduck-sim/build-pack-20260913/phase1/simulation), a leg only gets within 2 mm of the tray at frames where the same part already touches the existing power support. Poses where the tray is the only nearby obstacle need hip pitch beyond the walking range, combined with inward hip yaw: left pitch above about +0.42 rad with a straight knee, or above about +0.12 rad with the knee at −0.487. The right leg mirrors this. A hip-pitch limit tight enough to exclude them (about ±0.12 rad on IDs 8 and 3) would stop walking. The guide's unpowered checks include a hand test of this clearance.

Open findings (separate tasks):
- The left shin reaches the printed power support (0.00 mm) in walking. The training MJCF uses the upstream power support collision.
- Commanded walking targets exceed the MJCF joint ranges (left hip pitch down to −2.004 rad). runtime/core.py stops on any target outside the calibrated limits. The target ordering was matched by consistency (inference).

Files: p5-summary.json (per-leg boundaries), p5-grid*.json (pitch × yaw × roll sweeps; outward = yaw away from the body), p5-exact.json and p5-contactpt.json (exact point-to-mesh checks at the deciding poses), p5-frames*.json (sampled walking frames, every 25th of 147,000), p5-min.json, p5-walk-targets.json, and the scripts. Distance fields are 1 mm grids and read 0.5–0.75 mm high; ankle was held at home in the grid sweeps.
