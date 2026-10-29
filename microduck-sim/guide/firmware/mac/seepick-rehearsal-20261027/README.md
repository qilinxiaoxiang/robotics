# Seeing-pick deployment rehearsal (2026-10-27)

**2026-10-29:** the 0 of 96 below was the harness, not the policy: the loader's post-compile inertia edits left the
head's collision bounding volume in the old axes (the beak sank into the floor without contact) and the as-built MJCF
runs the pyramidal cone at impratio 1 where the training env runs elliptic / 10. Corrected (`brain_sim_check.py
--bvh-refit --sp-cone elliptic --sp-impratio 10`) the same 54 draws hold 24/54 at the deployed 100 mA jaw current and
49/54 at 150 mA. Study, numbers and the proposed fixes: `../seepick-gap-20261029/README.md`. The rows and text below are
kept as the record of the run as it was.

Final-goal step 4 (pick up with the beak). Sim only: nothing here talks to the robot.

**Result: 0 of 96 runs grasped or held the object.** No run fell and no wired guard tripped. The failure does not move with any single change tried: training-time masses, no COM calibration, a training-strength jaw, training beak friction, zero I/O delay, no jaw cap, a "stopped" holding bit. The policy ends every run with the beak beside the object, not around it.

## What runs

`walk_brain.Brain` with `seepick61.onnx` (from sp-b-1027_2000, md5 f317c04d...) drives the as-built MuJoCo model through `brain_sim_check.py --sp-at 4`. The harness adds:

- **Mouth:** a replica of `ground_grasp.add_mouth` (jaw hinge, lip and pad sites, boxes). The jaw is a BAM XL330 model at walk_wired's jaw settings (KP 200, 100 mA, so 0.037 N m).
- **Jaw path:** the jaw command goes through `jaw_limits.limit_targets` as `jaw_ctl.goal_tick` does.
- **Camera:** a stand-in with the training camera's logic (10 fps, delay, drops, stalls, bias, noise, field of view from the `head_camera` site).
- **Holding bit:** as `jaw_ctl.holding()` defines it.
- **Guards and hand-back:** walk_wired's guards, and the hand-back at phase 0.9.

Inputs:

- **Model:** model 87979d52 plugged manifest, `--com-x -2.25` (D-030 addendum).
- **Robot conditions:** from `microduck-sim/CURRENT-STATE.json`: 7.0 V servo rail, 4 % read drops.
- **Objects:** one random draw per seed from the training ranges (ball radius 5.3-7.2 mm, box half-sides 5-10 mm, 0.5-10 g, mu 0.35-1.1).
- **Placement:** at the trained landing spot (0.087, 0.0) m in the trunk frame plus the stated offset.

```
cd microduck-sim/guide/firmware/mac/seepick-rehearsal-20261027
SP_WORKERS=3 python3 run_rehearsal.py main     # 54 runs
SP_WORKERS=3 python3 run_rehearsal.py mass     # 12 runs
SP_WORKERS=3 python3 run_rehearsal.py diag     # 30 runs
python3 run_rehearsal.py summary               # results/summary.json
```

Every row in `results/<stage>.jsonl` carries its full command line. One single run looks like this:

```
~/.venvs/microduck-dyn/bin/python brain_sim_check.py --model asbuilt \
  --manifest ../../../microduck_rl/cmu/model/manifests/plugged.json --com-x -2.25 --volt 7.0 --drop 0.04 \
  --wired-guards --walk-s 0 --sp-at 4 --sp-offset 0.01 0 --sp-shape box --seed 2 [--sp-log trace.jsonl]
```

The main grid ran on the MacBook. The mass and diag stages, and one rerun of a crashed main case, ran on the Mac mini from a file snapshot in `~/sims/seepick-rehearsal-20261027/`. The snapshot's walk_brain.py, walk_wired.py, brain_sim_check.py and seepick61.onnx hashes match the MacBook copies.

Two runs crashed in libc++ (`recursive_mutex lock failed`), once under heavy load on each machine. Both reruns completed and are the rows kept.

## Main grid

The main grid has 54 runs: 9 placements (landing spot, ±1 and ±3 cm in x and y) × ball/box × seeds 0-2. All runs use the as-built model.

- **Grasp:** grasped or held after the rise: 0/54. A pinch (both beak halves touching the object) ever happened in 9/54, always for at most 0.04 s.
- **Fall and guards:** fell 0/54. Guard trips 0/54, and 0 clipped ticks.
- **Peak trunk tilt:** 43.1-55.1 deg, median 52.3. The seepick guard is at 55 deg (`--max-tilt-gp`). One run reached 55.1 deg in sim truth; the IMU-side guard did not trip.
- **Max action:** 1.92-2.13 rad, median 1.98. The guard limit is 3.0.
- **Beak and floor:** the beak touches the floor in every run. Lowest lip point is -0.5 to -4.6 mm below the floor surface (penetration), and peak beak-floor force is 4-38 N.
- **Pad position at close start (phase 0.34):** pad height 18.6-25.2 mm, median 21. The pad-to-object xy error is 1.2-26 mm. It grows with the y offset: up to 26 mm at y = +3 cm.
- **Holding bit without a pinch:** set for 5-18 ticks per run, every run.
- **Jaw cap** (`jaw_limits.pose_jaw_cap_deg`, while the jaw is meant open):
  - Minimum cap 25.0 deg in every run.
  - Never below the trained 22 deg opening and never clamped.
  - Never in the closed zone.
  - Highest commanded head pitch while open: 55.5 deg (the rule-1 limit is 65).

Per-run numbers: `results/summary.json` (`main`).

## Mass comparison and diagnostics (landing spot, ball and box, seeds 0-2)

Each case has 6 runs; grasped or held is 0/6 in every case.

- **Training-time masses** (1f2ab62c plugged, com 0): pinch 0. Tilt 51.8-52.9 deg, action ≤ 2.03 rad.
- **As-built 87979d52 without COM calibration** (com 0): pinch 1. Tilt 50.8-54.1 deg.
- **Training jaw** (1470 mA, KP 400, so about the training actuator's 0.5 N m): pinch 0. Holding bit without a pinch drops to 3-4 ticks.
- **Training jaw plus training beak friction 1.5:** pinch 0.
- **No I/O delay** (sensor 0, action 0, drop 0): pinch 0. Lip penetration falls to 1.6-2.1 mm.
- **No jaw cap:** pinch 1. Identical to the capped runs apart from noise, because the cap never bit.
- **Holding bit needs a stopped jaw:** pinch 0. Holding bit without a pinch is 0.

No case fell or tripped a guard. The robot's mass model and COM calibration do not decide the outcome here.

## Mechanism (traced: training jaw, box, seed 0, `results/trace_train_jaw_box_s0.jsonl`)

Positions are in mm, world frame. The object stays at (86.4, 2.0, 8.1) until touched.

1. **Phase 0.34-0.345: contact on approach.** The beak comes down over the object: lower pad at x 77, upper pad at x 97, pad height 21-25 mm. The lower jaw plate touches the object top (2-3 N) and pushes it 3-4 mm forward. The jaw is driven open from 21.8 to 23.2 deg while it is told to close.
2. **Phase 0.35-0.40: the beak moves sideways during the close.** The beak pads move sideways by 23 mm (pad y 3 → 26 mm) while the jaw closes. The object stays at y = 3 mm. When the jaw reaches the closed position at phase 0.43, both pads are 20 mm to the side of the object. The rise then starts with an empty beak.
3. **Head and neck tracking:** the head and neck do not track the policy's head and neck targets during the crouch.
   - Neck pitch sits on its lower range limit (-1.571 rad) from phase 0.20 to 0.44 while its target is -1.0 to -1.4.
   - Head pitch lags its target by 0.3-0.7 rad.
   - Head roll targets swing ±0.44 rad and the measured roll moves less than 0.15.

The policy's object slot during the close is stale: the last frame is 0.4-1 s old, because the object leaves the camera view in the descent.

## Findings in walk_brain.py / walk_wired.py / jaw_ctl.py (no change made)

1. **`jaw_ctl.holding()` sets the holding bit while the jaw is still sweeping shut with nothing in it.** It has no "stopped" check, so the bit is 1 for 5-18 ticks after "grip" in every run. The policy reads it as body slot 4. In training this slot is a real two-beak pinch, delayed 2 steps.
   - **Fix:** in `holding()`, also require that the opening changed by less than about 0.3 deg per read over the last 2 reads, or that Present Current is within about 20 % of Goal Current. With the stopped check (`--sp-holding stopped`), the false bit fell to 0 ticks.
2. **`walk_brain` seepick without an `"object"` in the control file runs the policy on body slots (0, 0, 0, age 2).** That case is "object at the robot's own feet".
   - **Fix:** in the seepick branch, refuse the switch, staying in the current mode with an info reason, until `want["object"]` has been seen once.
3. **Trunk tilt margin is under 1 deg.** Peak trunk tilt is within 0-1 deg of the 55 deg seepick guard (one run 55.1 deg in sim truth). With real IMU noise, a guard trip mid-pick is plausible. This is a fact for the tilt-guard setting; no change is proposed here.
4. **walk_wired turns jaw torque on only when the jaw is calibrated.** An uncalibrated jaw runs seepick with a limp mouth, and nothing refuses the mode.
   - **Fix:** refuse `seepick` in walk_wired when the jaw is not calibrated.

## Not modelled, or assumed

- **Jaw state before seepick:** assumed held at 2 deg.
- **Jaw servo behaviour:** speed, friction and current-limit response come from the BAM XL330 m6 model at 100 mA. They are not measured on this jaw.
- **Camera:** the training camera's random model replaces the real detector and its projection (cam_calib.py).
- **Hold check:** "held" uses contact force > 0 between the object and each beak half. The training env uses contact sensors.
- **Contact details:** no rolling friction, and no lip pad material.
- **Mouth geometry:** the replica follows `ground_grasp.add_mouth` at microduck_rl-grasp 0a520062. It is not checked against the printed V1.36 beak.
- **Untested differences from training:** two differences remain that this rehearsal could not vary.
  - The BAM servo dynamics of the as-built model versus the training actuators.
  - walk_brain's observation latency compensation (`compensate`). It is a no-op only in the no-I/O-delay case, which also failed.

  The next discriminating check is to run seepick61.onnx in the training env's own eval with this rehearsal's object draws. If it grasps there, the gap lies in these two items or in the mouth replica.
