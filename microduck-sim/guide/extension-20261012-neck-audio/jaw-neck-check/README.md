# Jaw versus neck in the real pickup postures (2026-10-12)

Problem: P0/P6 visual beak pickup. Question: does the open V1.8 jaw frame hit the head-pitch bracket, motor 11/12 or the
torso in the postures the robot actually uses, rather than in the synthetic 27-posture grid of
`../integrated/jaw-pickup.json`? Read-only on V1.8, guide and simulator sources; nothing here is committed to git.

## Answer

- **Grasping is clear.** In every reach, clamp, lift, hold and carry posture of the accepted simulated pickups (table,
  ground ball, household), the jaw at its full trained opening (0.32 rad = 18.33 deg) has no contact; for the phase
  medians nothing is within 10 mm. The first contact needs 34.75 to 40 deg of jaw at the phase medians (motor 11) and
  30.5 deg at the most turned accepted row (head-pitch bracket, head_yaw 33.3), so the margin above the trained opening
  is at least 12 deg.
- **The head-pitch bracket is never reached.** Over 1.15 million simulated rows, the bracket, its ring and idler 11
  stay at least 3 mm from the jaw. In the most turned accepted row the bracket is 6.9 mm from the jaw at the trained opening (table, head_yaw
  33.3).
- **The release head-tip collides.** The ground and household runs release the object by tipping the head to
  head_pitch 71 to 85 deg (neck_pitch about +12) while the jaw is at 16 to 18.3 deg. There the jaw frame passes through
  motor 12 (2169 mm3, 6.85 mm deep in the accepted ground release at head_pitch 84.7, jaw 18.3) and through the torso
  shell (shell_left 71 mm3, 4.0 mm deep in the same row). Rows with interference: 8,884 in 100 traces against motor 12
  and the neck links, 8,643 in 97 traces against the shells. 7,888 of the rows with head_pitch >= 70 are ground-ball
  release rows. The deepest shell overlap (586 mm3, 10.5 mm) is an exploratory household row with head_yaw 95 deg. The closed head clears this posture
  (no head part touches between head_pitch 50 and 90 at neck_pitch 12), so the jaw opening alone causes it.
- **The simulator could not see this.** `robot_allcollisions.xml` (identical in `microduck_rl` and
  `microduck-simulator/app/public/robot/mjlab`) has no jaw joint and no collision geometry on the neck, head-pitch or
  yaw bodies; motors are visual only. `preparePhysicsXml` (app/src/game/physics-model.js) adds the beak hinge (0..0.32
  rad) and beak contact pieces, then deletes every visual geom. The beak can therefore touch only the NP-F970 battery
  mesh, hips, legs, soles and the floor. The V1.8 torso shells, rear pack, neck links, motors 11/12 and the bracket are
  absent, so the training and acceptance never registered the release overlap.

## Turned head, full jaw range (owner report and `margin-yaw.json`, 2026-10-13)

Owner observation on the built robot: with the head straight ahead the open jaw does not touch the neck; with the head
turned it touches a little. `scripts/yaw_sweep.py` (neck_pitch 0, roll 0, head_pitch -45/0/30, head_yaw 0..170 step 10
plus -45/-90; 2 minutes under the bounded runner) agrees:

- Straight ahead (yaw 0) the jaw is clear to 40 deg. Any yaw brings the head-pitch bracket (`neck_pitch`) into reach:
  first contact at 39 deg (yaw 10), 35 (20), 31.5 (30), 29 (40), 27.25 (50), then a minimum of **26.25 deg at yaw
  60 and 120**, symmetric in yaw sign and about yaw 90 (30 deg). Head pitch -45..30 does not change the bracket numbers.
- A jaw cap of **25 deg** therefore clears the bracket at every yaw. The trained policy uses at most 18.33 deg, so the
  cap costs the learned pickup nothing.
- Separate case: head pitched down (-45) and turned backwards (yaw 110..160), the jaw meets the torso shells from 6 deg.
  No accepted pickup row is in that region; keep it out of commanded postures.
- Recommended action, no print change: clamp ID15 commands to 25 deg of jaw in the Pi control code, and set ID15's
  position limit on the robot from a measured reading (head turned to yaw 60, open the jaw by hand until it touches the
  bracket, read the position, set the limit about 2 deg short of it).

## Joint-angle margin

First jaw contact angle falls about 0.85 deg per degree of head_pitch above 50 deg (neck_pitch 12, yaw -4, roll 0, 1 deg
steps, `margin-release-yaw-4.0.json`): 23.75 deg at head_pitch 70, 19.0 at 76, 18.0 at 77, 16.5 at 79, 11.0 at 85.

- Jaw at 18.33 deg (trained maximum): clear up to head_pitch 76; at |head_roll| 10, up to about 70; at |head_roll| 25,
  up to about 60 (neck links). The torso shells limit the same opening at about 75 to 80 for any neck_pitch.
- Use (Shawn, 2026-10-13): pickup is always a straight-ahead forward bend; head roll and yaw are used only for
  expressions with a small jaw opening. The roll and yaw rows below therefore do not constrain pickup.
- Shawn (2026-10-13): the release should not tip the head that far; 70 deg is already exaggerated. The simulated
  85 deg head-tip is a controller choice to replace, not a required motion.
- Hard ceiling while the jaw is open for pickup or release (yaw and roll near 0): **head_pitch <= 70 deg**, which
  leaves 5.4 deg more jaw opening before contact at the trained 18.33 deg (first contact 23.75 deg at head_pitch 70).
- Earlier general rule, kept for expression poses with a wide jaw: head_pitch <= 65 deg with |head_roll| <= 10 deg, or
  head_pitch <= 55 deg for larger roll. At the trained 18.33 deg this leaves 6.7 deg more jaw opening before contact at |head_roll| 10
  (first contact 25 deg at head_pitch 65), 8.9 deg at roll 0, and 3.7 deg at head_roll 25 and head_pitch 55 (first
  contact 22 deg). The roll cases come from the 5 deg map.
- Grasp side (negative head_pitch): no limit is needed at 18.33 deg. Keep the jaw command at or below 30 deg anyway:
  the bracket is reached from 30.5 deg at yaw 35 or roll 25, and motor 11 from about 32 deg.

Hip pitch (bend-forward) does not change any of these numbers: the jaw and every checked part ride on the chain above
trunk_base, so only neck_pitch, head_pitch, head_yaw, head_roll and the jaw angle enter.

## Evidence

- Real postures (`postures.json`, `postures-rows.npz`): 1,193 traces, 1,153,913 rows from `microduck-simulator`
  `rl/runs/` and `app/test-results/*.zip`. Every embedded model uses beak_joint range 0..0.32 rad; the largest jaw
  angle in any row is 20.4 deg (limit overshoot). Pickup medians of accepted runs: table clamp neck -58 / head -44;
  ground clamp -82 / -38; household clamp -84 / -44 (jaw 13 to 18); ground release +12 / +85.
- Hinge equivalence: the simulator's beak hinge at head-body (0.003, 0, -0.01796) m maps to robot-frame
  (26.06, 0, 118.615) mm, axis +y, against the V1.8 pivot (26.1, 0, 118.6146); +0.32 rad moves the beak tip to
  (61.32, 0, 92.08) against (61.34, 0, 92.12) for +18.33 deg about the V1.8 pivot. Simulator jaw angles therefore map
  directly to the V1.8 jaw frame.
- Geometry: interference-audit closed solids (`ia_lib.CACHE`), checked in `trace-check.json` `solids` against the
  current `guide/print/world/` STLs (jaw_frame, neck_pitch_ring, rear pack, cover: 0.0 mm bound deviation) and the
  `guide-data.json` display meshes (<= 0.011 mm). Kinematics: `../neck-route/nr_lib.FK` (MJCF). Exact manifold3d
  overlap volume and min_gap; classes as in `jaw_pickup.py` (interference > 0.01 mm3, contact < 0.2 mm gap).
- `trace-check.json`: every row screened per body (bracket group by yaw/roll at 1 deg; neck group by head
  pitch/yaw/roll at 1 deg; torso by all four joints at 2 deg, each bin at its largest jaw row); every bin within 3 mm
  re-evaluated at each distinct row (0.1 deg).
- `margin-postures.json`: jaw swept 0..40 deg for each phase median and extreme accepted row.
  `margin-neck.json`, `margin-torso.json`: first-contact maps over head_pitch -90..90 (5 deg).
  `results.json`: derived limits and the combined summary (`scripts/summarize.py`).
- Synthetic grid reconciled: of its 27 postures only the nine with head_pitch +90 touch at a jaw angle within the
  trained 18.33 deg; the others need 32 to 40 deg.

## Limits and open checks

- The release limit is a geometric result. Whether the ball or object still falls out at head_pitch 65 is untested:
  rerun the ground-ball and household release acceptance with the cap before adopting it.
- Yaw 0 and +4 1-deg release runs were stopped by the bounded runner's machine-memory guard
  (`run-margin-release-yaw0.0.json`, `run-margin-release-yaw4.0.json`); the 5-deg neck map at yaw 0 and 5 gives the same
  values (20 deg at 75, 16 deg at 80). `run-margin.json` and `run-margin-release.json` record earlier stopped combined runs.
- Jaw versus legs, feet and floor is outside this check. The simulator's own contact model covers those surfaces.
- Physical clearances and print tolerance are not modelled; a 0.2 mm contact threshold is geometric only.

## Re-running

From `scripts/`, one job at a time under
`microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py --max-mib 1536`:
`extract_postures.py` (45 s), `check_traces.py` (8 min), `margin.py postures` (1.5 min), `margin.py neck` (26 min),
`margin.py torso` (5.5 min), `margin.py release -4.0` (5 min), then `summarize.py` (no geometry). Set `TMPDIR` to a
scratch directory for the neck-route helper.
