# Problem 5: the tilted RoboClub table. Findings, 2026-10-21

Repo: /Users/xiangzheng/code/robotics (paths below are relative to it unless absolute). Robot off; nothing moved. No
Modal/Kaggle/GPU job. No repo file edited; wrapper and results in this scratchpad directory. D-019 step advanced:
step 2 (walk to it), evidence: where the current policies can be tested without a slope confound.

## Answers

### 1. walk61/stand61 were not shown to have trained on slopes; the push/friction DR does not cover a constant pull

- Identity chain. `walk61.onnx` sha256 e36332d3... and `stand61.onnx` 15692687... (hardware-design-20260912/whole-robot-20260912/runtime-overlay/source-lock.json:14-15; official repo pollen-robotics/microduck-simulator commit 73a3f18a, lines 21-23). The same bytes are `microduck-simulator/app/public/policies/BEST_alpha_walking.onnx` / `BEST_alpha_stand.onnx` (shasum run 2026-10-21) and the Hugging Face Hub files `pollen-robotics/microduck-policies/alpha_walking.onnx` and `alpha_stand.onnx` (HF API tree fetched 2026-10-21: lfs oid e36332d3... and 15692687...). The swap-in commit in the simulator is 836975a, 2026-08-25 ("chore: swap in updated alpha walking/stand policy checkpoints"); `microduck_rl/cmu/finetune/modal/FINETUNE-DELTA.md:15-17` records that no `.pt` is public and Pollen's wandb project is private.
- Which run and task. `microduck_rl/AGENTS.md` (section "Training ops & reading a run", bullet "Deployed-policy provenance") says the Hub ONNX files carry `run_path=None` and that the walk policy was matched by last-layer weights to wandb run `441tzs6d` @ 3750 (2026-09). `microduck_rl/docs/velstand_policy.md:27` calls that run the "velocity recipe" walk teacher (`alpha_walking.onnx`). The Hub `manifest.json` (fetched 2026-10-21) gives a `training.task_id` for `velstand.onnx` (`Mjlab-VelStand-Rough-Backlash-MicroDuck`) and `alpha_sitstand.onnx` (`Mjlab-SitStand-Flat-MicroDuck`) but none for `alpha_walking.onnx`. So the task that produced walk61 is not recorded anywhere readable.
- Inference (labelled): the velocity recipe's documented training command is the Flat task (`microduck_rl/docs/UPSTREAM-README.md:35`, `:68`); velstand v1 built on this walk teacher was flat and rough terrain only entered velstand at v5/v6 with a "rough-terrain spawn fix" (`docs/velstand_policy.md:29-30`, commit e40fbda0 2026-09-13). The slope sub-terrain `pyramid_slope` was added to `MICRODUCK_ROUGH_TERRAINS_CFG` on 2026-08-20 (microduck_rl commit 4dd0d5e0 "trying to fix head drooping and adding slopes in rough terrain"), five days before the policy file was swapped in; rough terrain itself exists since 2026-03-07 (02538e60). Even a Rough run could therefore have met slopes only if it was trained in those five days. Conclusion for the decision: no evidence that walk61 ever walked on a slope.
- Terrain code. Flat: `cfg.scene.terrain.terrain_type = "plane"` (`microduck_rl/src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py:748-750`); Rough: `MICRODUCK_ROUGH_TERRAINS_CFG` (`:752-753`) with `pyramid_slope` proportion 0.20, `slope_range=(0.03, 0.10)` rise/run = 1.7 to 5.7 deg, platform 2.0 m, 1 mm vertical scale (`:154-166`); stairs 0 to 1.5 cm (`:134-140`); random grid 0 to 1 cm (`:148-153`); flat 0.25 (`:133`). Task ids `Mjlab-Velocity-Flat-MicroDuck` and `Mjlab-Velocity-Rough-MicroDuck` (`microduck_rl/src/mjlab_microduck/tasks/__init__.py:81-95`); the terrain-level curriculum is deleted for Flat only (`env_cfg.py:888-889`). Our as-built tasks `Mjlab-Velocity-{Flat,Rough}-MicroDuck-CMU-{Plugged,Battery}` (`microduck_rl/cmu/README.md`, "Three ways in").
- Push and friction randomization (training only): velocity pushes on, every 3 to 6 s, a velocity jump of +-0.3 m/s in x and y (`env_cfg.py:39`, `:79-83`, `:390-406`; was +-0.5, narrowed after the 2026-07 audit, `:80-83`); no yaw push (ft1 added one, D-016). Foot friction 0.7 to 1.3 (`:377`); BAM joint-friction scale 0.9 to 1.1 (`:76`); mass and inertia +-5 % (`:73`); trunk COM +-3 mm ramped to +-8 mm (`:57`); IMU mounting error up to 6 deg on a random axis, zero-centred (`:84`); initial-tilt randomization is off (`ENABLE_BASE_ORIENTATION_RANDOMIZATION = False`, `:42`; the +-10/+-5 deg constants at `:86-87` are unused).
- What a slope is in those terms: a constant acceleration g*sin(theta) along the floor = 0.34 m/s^2 at 2 deg, 0.51 at 3 deg, 0.86 at 5 deg. The trained push is an impulse of at most 0.3 m/s every 3 to 6 s; a 5 deg slope adds 0.86 m/s every second if nothing opposes it, about three maximum trained kicks per second, continuously. Statically, at the policy's nominal trunk height 0.095 m (`env_cfg.py:722`) the slope moves the COM over the feet by 95 mm * tan(theta) = 3.3 mm (2 deg), 5.0 mm (3 deg), 8.3 mm (5 deg); the suite's "com+5" real case (COM 5 mm forward, `microduck_rl/cmu/simcheck/sim_suite.py:49`) is the static twin of a 3 deg descending slope. What the policy sees: projected gravity tilted by theta, inside the 6 deg IMU-misalignment DR, the one trained channel a slope resembles; the dynamics (a constant pull) are in no DR term.

### 2. As-built sim on tilted floors (plugged manifest, 7.0 V, 4 % dropped reads)

Mass manifest check before the runs (AGENTS.md rule): `microduck_rl/cmu/model/manifests/plugged.json` (212 parts, net +190.8 g on Pollen's bodies, the 90 g NP-F970 removed by the loader), build string "plugged ... Pi Zero W replaced by the Radxa Cubie A7Z and the AC019 antenna ... Camera Module 3 entry kept". Against the robot now (CURRENT-STATE.json facts, D-018/D-019):

- Matches: bench box (rear frame 11.33 g slicer, two XL4015 at 20 g each, estimate, PD trigger 3.5 g) = CURRENT-STATE `power` (5991 bench supply, two XL4015, no battery, verified 2026-10-16); OpenRB 13 g, IMU 2.5 g, speaker 2.3 g + amplifier 1.2 g (audio fitted, D-012); A7Z in the head (`a7z_imu_bus`, `a7z_network`, 2026-10-18) at 18 g, label "estimate", bounded 15 to 20 g (`cmu/ROBOT.md` "Body and mass"; `manifests/plugged.json` derived block: removed add-pi 9.3 g, added add-a7z 18.0 g estimate, add-antenna-ac019 1.5 g estimate).
- Gaps: (a) XIAO ESP32-S3 touch board, its wires and five copper pads are on the robot (`a7z_touch_bus`, verified 2026-10-21) but absent from the manifest (its "excluded" list still says "XIAO ESP32-S3 touch board and copper pads (D-013: not bought)"); a few grams in the head, unweighed. (b) The camera entry is the 4 g Camera Module 3 (datasheet); the fitted Radxa Camera 13M 214 is "of the same order, not weighed" (build string). (c) The head prints are the V1.8/V1.9 slicer masses (`add-head_cap_v19` 40.4 g, inference+slicer); whether the V1.17 A7Z cap/face/clip are fitted is not recorded in CURRENT-STATE. (d) No sole entry (ROBOT.md "Feet": 2026-10-18 runs used sandpaper on 0.5 mm foam tape; a 27-run sweep showed the rigid stack does not change the sim); which sole and which foot/ankle prints are on the robot today is not a CURRENT-STATE fact. (e) ID5 horn refit (D-018) changes no mass. None of these gaps is of a size that would move the slope results (the head gap is about 1 to 2 % of robot mass at the largest lever arm); they are listed, not fixed, because the brief forbids repo edits and the parts are unweighed.

How the world was tilted. Neither `guide/firmware/mac/brain_sim_check.py` (flags at `:345-394`) nor `guide/firmware/mac/stand-pose-study-20261020/stand_sim.py` has a slope, gravity or floor-rotation flag (grep for gravity/tilt/slope/incline: only the push and the tilt readouts). The scene floor is an infinite plane at the origin (`microduck_rl/src/mjlab_microduck/robot/microduck/scene.xml:22`, `<geom name="floor" ... type="plane">`), so the wrapper `slope_sim.py` (this directory) rotates the gravity vector `m.opt.gravity` by theta about a horizontal axis after `evaluate_delay.load` and rotates the trunk quaternion handed to `walk_brain.Brain.tick` into the gravity frame (q' = conj(q_slope) x q_sensor), which is what the robot's BNO085 would report. For a flat plane this is the same as tilting the floor by theta: the angle between the floor normal and gravity is theta, the robot still starts with its feet flat on the plane (`brain_sim_check.py:85-91`, `static_gap.feet_flat_rot`), the dynamics feel the tilted gravity, and the policy's projected gravity and the Brain's 30 deg tilt guard see the true gravity (self-check in the wrapper: an upright trunk sees `gravity_dir`; readback: at 5 deg sideways the policy's body gravity y = +0.094, about sin 5 deg plus the stand sag). What stays floor-relative, as in `brain_sim_check.py:275-277`: the fall criterion (trunk height above the plane < 0.04 m, or tilt against the plane normal > 45 deg). Floor friction is the scene's 1.0; the table's is unknown. Directions: down_ahead = floor descends in the walking direction (gravity pulls forward), up_ahead = ascends, down_left = descends to the robot's left. All three mode cases run the real condition from `robot_state_check.py --print-sim-args` (= `--volt 7.0 --drop 0.04`; CURRENT-STATE `servo_rail_v` 7.0 verified 2026-10-16, `servo_read_drop_fraction` 0.04 verified 2026-10-17; IMU 50 Hz so no `--imu-hz`; added delay 0 so the default `--sensor-delay 1`).

Protocol note. `brain_sim_check.py` starts every run with 1 s of open-loop stand mode (KP 400, `--stand-s 1`, `:159-160`) before the policy. On a 5 deg slope ahead or behind that unsupported open-loop phase fell at 0.58 to 0.68 s, before the first policy tick (rows with polPeak "-"), so those four rows measure the open-loop stand, not the policies. On the robot the duck is held by hand in stand mode and released once stand61 runs, so the policy rows were rerun with `--stand-s 0` (suffix `_h`: the policy takes over from the held stand pose at t = 0). Walk cases keep the suite's schedule (stand61 until 4 s, 0.25 m/s for 10 s, stand61 3 s; T = 17 s); stand61 cases run zero command for 20 s; open-loop stand cases hold stand mode for 20 s.

Commands (all from this scratchpad directory, serial, one process at a time, each under `timeout 600`; 26 runs, 1.0 to 4.3 s wall each; the brief's cap of about 20 was exceeded by six because four runs were confounded by the open-loop phase and two 3 deg runs were needed to bracket the threshold):

```
PY=~/.venvs/microduck-dyn/bin/python
MAN=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl/cmu/model/manifests/plugged.json
# batch 1 (run_grid.sh): stand-s 1 (brain_sim_check default)
timeout 600 $PY slope_sim.py --slope-deg S --direction D --case stand61     -- --model asbuilt --volt 7.0 --drop 0.04 --manifest $MAN --vx 0 --walk-at 2 --walk-s 15
timeout 600 $PY slope_sim.py --slope-deg S --direction D --case walk61_0.25 -- --model asbuilt --volt 7.0 --drop 0.04 --manifest $MAN --vx 0.25 --walk-at 4 --walk-s 10
timeout 600 $PY slope_sim.py --slope-deg S --direction D --case stand_kp400 -- --model asbuilt --volt 7.0 --drop 0.04 --manifest $MAN --stand-s 20 --walk-at 17 --walk-s 0
# batch 2 (run_grid2.sh): hand-held handoff, --stand-s 0 added to the pass-through flags, cases stand61_h / walk61_0.25_h
```

Result rows (fell_at s; tiltG = peak trunk tilt against gravity, deg; polPeak = same but only over ticks in which a policy ran; end = tilt at the last tick; dx/dy = trunk displacement in the floor plane over the whole run, m, x = initial heading, y = left; distX = brain_sim_check's dist_x from --walk-at; yaw = heading change, deg; jumps = ticks with an action jump > 0.5 rad; raw rows with per-second tilt in `slope-results.jsonl`):

```
case           stand_s slope dir        fell   tiltG polPeak end   dx      dy      distX   yaw    jumps
stand61        1       0    flat       none    4.0   4.0    0.6  -0.001  -0.000   0.001    0.1   0
walk61_0.25    1       0    flat       none    6.3   6.3    1.9  +1.167  +0.056   1.168   -1.0   1
stand_kp400    20      0    flat       none    4.7   -      4.7  +0.005  +0.000   0.0     -0.0   0
stand61        1       2    down_ahead none   12.3  12.3    2.1  +0.013  -0.002   0.012    0.7   0
stand61        1       2    up_ahead   none    7.7   7.7    0.9  -0.027  +0.005  -0.007   -0.4   1
stand61        1       2    down_left  none    4.5   4.5    2.3  -0.000  +0.012   0.001    0.1   0
stand61        1       5    down_ahead 0.68   48.5   -     48.5  +0.075  +0.000   -        -     0   (fell in the open-loop phase)
stand61        1       5    up_ahead   0.58   48.7   -     48.7  -0.084  +0.000   -        -     0   (fell in the open-loop phase)
stand61        1       5    down_left  none    6.9   6.9    5.5  +0.000  +0.028   0.001    0.1   0
walk61_0.25    1       2    down_ahead none   12.3  12.3    3.5  +1.738  +0.099   1.735    3.3   4
walk61_0.25    1       2    up_ahead   none    7.7   7.7    0.6  +0.885  +0.052   0.905  -17.3   4
walk61_0.25    1       5    down_ahead 0.68   48.5   -     48.5  +0.075  +0.000   -        -     0   (fell in the open-loop phase)
walk61_0.25    1       5    up_ahead   0.58   48.7   -     48.7  -0.084  +0.000   -        -     0   (fell in the open-loop phase)
stand_kp400    20      2    down_ahead 2.0    46.3   -     46.3  +0.077  +0.000   -        -     0
stand_kp400    20      2    up_ahead   none    2.9   -      2.9  -0.022  +0.000  -0.003   -0.0   0
stand_kp400    20      2    down_left  none   13.0   -     13.0  +0.014  +0.014   0.0      0.0   0
stand_kp400    20      5    down_ahead 0.68   48.5   -     48.5  +0.075  +0.000   -        -     0
stand_kp400    20      5    up_ahead   0.58   48.7   -     48.7  -0.084  +0.000   -        -     0
stand_kp400    20      5    down_left  none   12.6   -     12.6  +0.011  +0.033   0.0     -0.1   0
stand61_h      0       0    flat       none    7.2   7.2    0.7  -0.002  +0.003  -0.0     -0.5   0
stand61_h      0       5    down_ahead none    9.7   9.7    5.1  +0.119  +0.018   0.027   -2.3   2
stand61_h      0       5    up_ahead   none    9.5   9.5    3.5  -0.361  +0.056  -0.201   63.9  13
walk61_0.25_h  0       3    down_ahead none   11.3  11.3    4.8  +2.203  +0.077   2.157   35.2   5
walk61_0.25_h  0       3    up_ahead   none    8.4   8.4    0.6  +0.732  +0.030   0.771   -4.7   6
walk61_0.25_h  0       5    down_ahead none   14.3  14.3    6.3  +2.897  -0.060   2.802   23.7  19
walk61_0.25_h  0       5    up_ahead   none    9.7   9.7    4.4  +0.170  +0.014   0.388   67.1  20
```

Reference for the flat rows: `microduck_rl/cmu/simcheck/reference-walk61-plugged.jsonl` vx0.25 (no fall, max_tilt 6.3, dist_x 1.165, yaw -2.0, 1 jump) matches the wrapper's flat walk row (6.3, 1.168, -1.0, 1), so the wrapper reproduces the suite at 0 deg. The wrapper's 2 deg stand61 rows at stand-s 1 inherit the open-loop tipping of the first second (12.1 deg at t < 1 s down_ahead, `tilt_by_s` in the jsonl): the policy took over an already tipping robot and recovered it; the hand-held variant is the milder handoff.

Reading:

- stand61 (walk mode, zero command): no fall at 2 or 5 deg in any direction. At 2 deg the steady tilt is 0.9 to 2.4 deg against gravity (0.6 to 0.7 flat) and the drift over 20 s is 1 to 3 cm. At 5 deg descending ahead it creeps 12 cm downhill in 20 s and settles 5.1 deg from vertical; at 5 deg ascending ahead it creeps 36 cm backwards (downhill), turns 64 deg and shows 13 action jumps, no longer a quiet stand; at 5 deg sideways it leans 5.5 deg and drifts 2.8 cm.
- walk61 at 0.25 m/s: no fall at 2, 3 or 5 deg, but the gait changes with the slope. Downhill it runs away: 1.74 m (2 deg), 2.16 m (3 deg), 2.80 m (5 deg) in the 10 s window against 1.17 m flat, with 24 to 35 deg of heading drift at 3 to 5 deg and 5 to 19 action jumps (1 flat). Uphill it stalls: 0.91 m (2 deg), 0.77 m (3 deg), 0.39 m (5 deg), with -17 deg yaw at 2 deg and 67 deg at 5 deg (20 jumps). Peak trunk tilt while walking rises from 6.3 deg (flat) to 7.7 to 8.4 (2 to 3 deg) and 9.7 to 14.3 (5 deg).
- Open-loop stand (stand mode, KP 400, unsupported): sags 4.7 deg forward on a flat floor in 20 s (the 2026-10-21 stand-gap study, robotics commit 4ef1d06: "KP 400 is too soft to hold the stand"); falls at 2.0 s on a 2 deg descending slope; falls at 0.6 to 0.7 s at 5 deg ahead or behind; survives sideways and 2 deg ascending but leans 12.6 to 13.0 deg sideways. This matters because stand mode is where the Brain's guards (tilt > 30 deg, three action jumps in ten ticks, `cmu/ROBOT.md` "Guards") put the robot after a trip: on a slope the fallback itself falls.
- Side slope for walk61 and the 1 deg cases were not run (budget); 1 deg is bracketed by the 0 and 2 deg rows.

### 3. Recommendation with numbers

- Threshold: up to 2 deg in either axis the current policies behave inside the suite's accepted spread (stand tilt within 2.5 deg, drift <= 3 cm per 20 s, walk 0.9 to 1.7 m per 10 s against 1.17 flat, heading within 17 deg; the 3 deg descending case is the static twin of the accepted com+5 real case and gives the same picture: tilt 11.3 vs 14.0, yaw 35 vs 27, 2.16 vs 2.14 m). Above 2 deg the walk is a different gait (downhill 0.22 to 0.28 m/s with the heading wandering 24 to 35 deg, uphill 0.04 to 0.08 m/s with up to 67 deg of turn and 20x the flat action jumps) and the open-loop fallback falls within 2 s. The sim shows no policy fall at any tested slope, but the sim also does not reproduce the robot's falls after 3 to 4 s on a flat floor (`microduck_rl/cmu/SIM2REAL.md`, "What the sim reproduces and what it does not"), so a sim "no fall" is not a margin; the systematic effects (speed, heading, tilt, fallback) are the usable result.
- Move to a flat floor rather than fine-tune. D-019 step 2's acceptance is written "on a level floor"; the robot's falls are being investigated on the flat-floor assumption, and a slope adds a constant pull that is in no training term. Practical: on a table, a downhill 10 s walk covers 2.2 to 2.9 m in the sim; the table edge, not the slope, is the first hazard. Shim only if the floor is unavailable: shim height = table length * tan(theta) (1.2 m table: 21 mm at 1 deg, 42 mm at 2 deg, 63 mm at 3 deg) under the low legs, re-measured after.
- Fine-tuning for slopes would be a new registered delta in `microduck_rl/cmu/finetune/modal/finetune_worker.py:138` (`DELTAS = {"default", "staged", "lowcmd"}`), e.g. `slope` on `Mjlab-Velocity-Rough-MicroDuck-CMU-Plugged` (pyramid_slope 1.7 to 5.7 deg, proportion 0.20) or a tilted plane. D-016 requires `finetune.py::audit` to write a PASS for that variant (stand61 collects at most 0.8 of walk61's reward per second over 2048 envs x 15 s) before `finetune.py::run` launches, plus the tracking guard and `--max-lr`; the launch itself needs Shawn's go and a dollar cap (ft3: L4, 999 iterations, 56 min, $1.04, D-017). D-017's history is the risk: ft1 and ft2 drifted to standing; ft3 passed the audit, beat walk61 in every real-condition sim case and then fell on the robot in 3 of 3 walks at 0.20 m/s. A slope delta does not touch the measured failure mode (trunk shake 5 to 25 Hz, stiction at KP 200, yaw-rate spikes; SIM2REAL.md), so by the repo's own rule it would be a sim win that does not transfer, and it would be queued before the literature pass the rules require. Not now.

### 4. Measuring the table, and checking the floor

1. Phone level app (iPhone: Measure app, "Level" tab; Android: the level in Google's Measure or any bubble-level app), phone flat on the table at the spot where the duck stands, long axis along the duck's walking direction. Read the angle. Turn the phone 180 deg in place and read again: the slope is the average of the two readings; half their difference is the phone's own zero error (if it is over 0.5 deg, keep using the average, do not trust a single reading).
2. Turn the phone 90 deg and repeat for the across-table axis.
3. Repeat both at the start, 0.5 m and 1.0 m along the walking path (tables sag and stand on uneven legs); record the largest value per axis.
4. Verdict: <= 1 deg both axes = flat enough for everything here; 1 to 2 deg = usable for standing and 4 s walks, not for the step-2 acceptance; > 2 deg = move or shim.
5. Floor: the same four steps on a 2 m x 1 m patch of the candidate floor (hard floor; carpet pile is outside what the foot-friction and sole sweeps covered). Accept <= 1 deg at all three spots.
6. Record: the two angles, the spot and the date as a CURRENT-STATE fact (the `current-state` skill owns the format; proposal `test_surface_slope_deg` with `measure` = the phone-flip procedure), quoted in every walk-run README from then on. Done = the fact exists and the next walk log names it.

## What remains unverified

- The task (Flat or Rough) and date of wandb run 441tzs6d: private to Pollen; only the inference above.
- Hub `alpha_walking.onnx` = walk61 is verified by sha256 (API tree); that the Hub file is the one matched to 441tzs6d is the repo's claim (`microduck_rl/AGENTS.md`), not re-derived here.
- Masses: A7Z (18 g estimate), XIAO touch board (absent), Radxa camera (4 g stand-in), head cap version, sole and foot prints on the robot today. Floor friction of the table (sim uses 1.0).
- The sim's open-loop stand falls on a 2 deg descending slope; the robot's open-loop stand sags 0.05 to 0.067 rad (SIM2REAL.md) and has not been tried on a measured slope. Walk61 on a side slope and all 1 deg cases were not run.
- The sim does not reproduce the robot's falls after 3 to 4 s; "no fall in sim" at 3 to 5 deg is therefore not a safety margin.
- Shim heights assume a 1.2 m table; measure the actual length.

## Files

- Wrapper: /private/tmp/claude-501/-Users-xiangzheng-code-robotics/74602e44-fa79-4564-a436-c7a3c8ce2ecd/scratchpad/slope_sim.py
- Batch scripts: /private/tmp/claude-501/-Users-xiangzheng-code-robotics/74602e44-fa79-4564-a436-c7a3c8ce2ecd/scratchpad/run_grid.sh and run_grid2.sh
- Raw rows (26, with per-second tilt): /private/tmp/claude-501/-Users-xiangzheng-code-robotics/74602e44-fa79-4564-a436-c7a3c8ce2ecd/scratchpad/slope-results.jsonl
