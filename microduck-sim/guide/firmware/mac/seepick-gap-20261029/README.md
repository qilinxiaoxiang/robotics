# Seeing-pick gap study (2026-10-29)

Final-goal step 4 (pick up with the beak), simulation only: nothing here ran on the robot or the A7Z, and no policy was
trained. The question: `seepick61.onnx` (sp-b-1027_2000) grasps 78-81 % at +-3 cm in its training eval but held 0 of 96 in
the as-built MuJoCo rehearsal through the real runtime (`../seepick-rehearsal-20261027/`). Where does the gap live: the
policy, the runtime, the sim replica, or the beak?

**Decision line (Shawn, 2026-10-29):** the first real-robot pickup target stays the 1.0-1.5 cm printed orange ball; the
block ordering is rejected. The ball is the main case below, the box the comparison.

## Answer

The 0/96 was the rehearsal harness, not the policy, the runtime or the beak. Two defects in the as-built sim replica
hid the object from the beak, and once they are fixed the remaining gap is one number: the jaw torque the runtime
allows the XL330 (100 mA, 0.037 N m) against the torque the policy was trained with (1.0 N m/rad, up to 0.5 N m).

- **Policy**: in its own env, on the rehearsal's exact 54 draws and placements, 0.94 (ball 0.92, box 0.95). Weak only
  at x = -0.03 (0.56). Not the gap.
- **Sim replica, defect 1 (stale collision volumes)**: `evaluate_delay.load` edits body inertias after compile, so the
  head's collision bounding box stayed in the old axes and the midphase dropped the beak-floor and beak-object contacts;
  the upper beak sank 16 mm into the floor with zero contact. `--bvh-refit`: 0/54 -> 12/54 (ball 0, box 12).
- **Sim replica, defect 2 (contact solver)**: the as-built MJCF compiles with the pyramidal cone and impratio 1; the
  training env runs elliptic / 10 (its "sticky friction", `microduck_ground_grasp_env_cfg.py` lines 141-146). Under
  pyramidal / 1 a pinched box creeps forward out of the pads and a ball rolls out of the closing wedge whatever the jaw
  torque or friction. `--sp-cone elliptic --sp-impratio 10`: 12/54 -> 24/54 (ball 5, box 19).
- **Jaw torque (the residual)**: with both corrections, the training-strength jaw holds 54/54 (ball 27, box 27); the
  runtime-reachable 150 mA (jaw_ctl's own `CURRENT_LIMIT_MA`) holds 49/54 (ball 23, box 26); 100 mA as deployed 24/54.
  The training env says so itself (`ground_grasp.py` line 121: "Rémi's brief says to assume enough beak torque").
  Beak friction 1.5 instead of the object's own: 26/54, no lever. Compensation, the jaw cap, real I/O delays and read
  drops: no effect on any run.
- **Beak**: the printed V1.36 beak matches Pollen's CAD within 0.2 mm and the training mouth replica within 2.3 mm at the
  pads; a 10.6-14.4 mm ball fits all three apertures. Not the gap in geometry. Friction is the ball's second lever: at
  150 mA bare PLA lips (0.35-0.5) hold the ball in 7-15 of 27, an inner-tube lining (1.1) in 22 of 27 (section 6a).
- **Ball after the hand-back**: 8 of the 23 balls held at 150 mA leave the beak within 3 s of the hand-back to stand61
  (boxes: none). Outside the training episode; a robot-side item (section 6b).

Where the fix lands: (d) the rehearsal harness (two flags, applied here, plus a proposed loader change), (a) a one-line
runtime proposal (`jaw_ctl.GOAL_CURRENT_MA` 100 -> 150, diff below, not applied), (b) the training env should model the
jaw at the torque the robot will run, which needs a new training run and waits for Shawn's go, (c) nothing in the beak
geometry; a lip lining is a friction lever measured in section 6.

## 1. Result ladder (54 runs each: 9 placements x ball/box x seeds 0-2, the rehearsal's draws)

Measures: *train* = the training env's success (pinched, off the floor, lifted > 1 cm on >= 20 ticks from phase 0.44,
`seeing_audit.SUCCESS_STEPS`); *hand-back* = still held when walk_wired hands back to stand61 at phase 0.9; *end* = still
held 3 s after the hand-back. All runs: as-built model 87979d52 plugged manifest, `--com-x -2.25`, 7.0 V rail and 4 %
read drops from `microduck-sim/CURRENT-STATE.json`, the training camera stand-in with its drawn delay/drops/bias/noise/
stalls, wired guards on. Rows are `results/<stage>.jsonl` (each row carries its full command line); summary in
`results/summary.json` (`python3 run_gap.py summary`), side by side with the training eval in `results/compare.txt`
(`python3 compare.py`).

- **training eval on the same draws** (`results/train_eval.jsonl`): 0.94 overall; ball 0.92; box 0.95.
- **rehearsal as run, 2026-10-27** (`../seepick-rehearsal-20261027/results/main.jsonl`): train 0/54; hand-back 5/54
  (all five are the stale-BVH artefact: the object "lifted" through the floor-less beak); end 0/54.
- **refit** (`--bvh-refit`): train 12/54 (ball 0/27, box 12/27); hand-back 3; end 0; pinched at some point 27/54.
- **refit_sticky** (+ `--sp-cone elliptic --sp-impratio 10`): train 24/54 (ball 5/27, box 19/27); hand-back 24; end 19
  (ball 0, box 19: every held ball left the beak after the hand-back, section 6b).
- **refit_sticky_mu15** (+ beak friction 1.5, the training value): train 26/54 (ball 7, box 19); one fall.
- **refit_sticky_jaw150** (+ jaw at 150 mA, 0.055 N m): train 49/54 (ball 23/27, box 26/27); hand-back 49; end 41.
- **refit_sticky_jaw300** (0.110 N m): see `results/summary.json` (section 5).
- **refit_sticky_jaw600** (0.220 N m): section 5.
- **refit_sticky_kp400** (100 mA, KP 400: stiffness alone): section 5.
- **refit_sticky_tjaw** (1470 mA, KP 400: the training jaw, 0.538 N m at 7.0 V): train 54/54; hand-back 54; end 54.

By placement (train measure, refit_sticky -> jaw150): the deployed 100 mA fails most at x = -0.03 (1/6) and y = +0.03
(2/6); at 150 mA every placement is 5/6 or 6/6 except x = -0.03 (section 5). The training eval's own weak placement is
also x = -0.03 (0.56; 0.94-1.00 everywhere else).

## 2. Step 1: the policy in its own env on the rehearsal's draws

`run_train_eval.py` reads the 54 rows of `../seepick-rehearsal-20261027/results/main.jsonl` (shape, half-sizes, mass,
friction, yaw, offset, seed) and runs each through `cmu/grasp/gap_trace.py --exact` (new flags `--exact`,
`--object-yaw`, branch `cmu/grasp` of `microduck_rl-grasp`): the training env `Mjlab-SeeingPick-FromPick-MicroDuck-CMU-
Plugged`, 8 envs per case, domain randomisation on except the object, which is forced to the rehearsal's draw.

```
# Mac mini, snapshot ~/sims/seepick-gap-20261027 (torch 2.9.1, warp 1.12.0), 3 workers
cd ~/sims/seepick-gap-20261027/rt/microduck-sim/guide/firmware/mac/seepick-gap-20261029
SP_WORKERS=3 python3 run_train_eval.py > logs/train_eval.out 2>&1
# one case, as written in each row's "cmd":
.venv/bin/python cmu/grasp/gap_trace.py --out <dir> --num-envs 8 --seed 0 --exact --shape ball \
  --half 0.00537 0.00678 0.00682 --mass 0.00503 --mu 0.981 --object-yaw 119.6 --offset 0.0 0.0
```

Result (`results/train_eval.jsonl`, 432 episodes): 0.94; ball 0.92 (216), box 0.95 (216). By offset: -0.03,0 0.56;
-0.01,0 0.94; 0,0 0.98; +0.01,0 1.00; +0.03,0 0.98; 0,+-0.01 1.00/0.98; 0,+0.03 1.00; 0,-0.03 1.00. The three ball draws
(seeds 0-2: 13.5 mm mu 0.98, 12.9 mm mu 1.00, 13.5 mm mu 0.55) all succeed at the centre; the policy is not
object-sensitive inside its training ranges. So the gap is downstream of the policy.

## 3. Step 2: traces, then one factor at a time

### 3a. Training trace against runtime trace (matched centre box)

`traces-20261027/` (moved from the rehearsal's `gap/logs`, compared with `cmp.py`): the training env (`tr_nom`, 16/16
held) and the runtime harness (`rt_nom`) on the same box (15 x 15 x 14 mm, 3 g, mu 0.7, yaw 0, deterministic camera).
Through the descent (ticks 30-66) the two agree within millimetres: pad height, pad-to-object offset, head pitch and the
neck at its -1.57 rad limit in **both**, so the neck clamp, `compensate`, the jaw cap and the I/O delays are not where
they part. They part at the close: in `rt_nom` the upper beak box is 16.5 mm below the floor with zero floor contact
while the jaw plate alone carries 4-7 N and is levered from 0.38 to 0.51 rad during the close (ticks 70-80). A beak that
is in the floor cannot be on the object.

### 3b. Defect 1: stale body bounding volumes

MuJoCo stores each body's collision BVH (`bvh_aabb`) in the body's inertial frame at compile time. `evaluate_delay.load`
(`hardware-design-20260912/whole-robot-20260912/delay-repair-20260912/evaluate_delay.py` lines 114-139) compiles, then
`add_signed_inertias` rewrites `body_mass/ipos/iquat/inertia` from the mass manifest and `--com-x`, then `mj_setConst`.
Bodies whose principal axes turned keep a box in the old axes; the midphase drops contacts outside it. `brain_sim_check.py
--bvh-refit` (`refit_body_bvh`) rebuilds every body's box in its current inertial frame and prints the changes: on the
as-built model `trunk_base`, `hip_l`, `leg`, `leg_2`, `ankle_right` and `jaw_soft` change, the last with its axes swapped
(half-sizes 30.8/67.3 mm -> 68.9/32.5 mm); the feet do not change, which is why the walking sims never showed it.

```
cd microduck-sim/guide/firmware/mac/seepick-gap-20261029
SP_WORKERS=3 nice python3 run_gap.py refit > logs/refit.out 2>&1          # Mac mini; results/refit.jsonl
```

### 3c. Defect 2: the contact solver

With the refit alone the matched box is pinched at 1.40 s but creeps forward out of the pads (about 2 mm/s relative,
contact forces 0.05-0.16 N, jaw 0.264 -> 0.235 rad) and drops at phase 0.745; the ball never pinches at all (contacts
flicker at 0.01-0.02 N and the beak rises empty). Single runs on the matched case, each `run_single.sh NAME <flags>`
(MacBook for the first nine under `local_bisect.sh`, Mac mini for the rest under `mini_singles.sh`; output
`results/single/NAME.out`, trace `results/single/NAME.jsonl` kept for refit, refit_sticky, refit_ball,
refit_ball_sticky and the two smoke runs):

- refit (`--bvh-refit`): held 60 ticks, dropped before hand-back (lift -0.1 mm at hand-back).
- refit_tjaw (+ `--sp-jaw-current 1470 --sp-jaw-kp 400`): 18 ticks, dropped.
- refit_mu15 (+ `--sp-beak-mu 1.5`): 59 ticks, dropped. refit_tjaw_mu15: 66 ticks, dropped.
- refit_jaw150 / refit_jaw300: 48 / 36 ticks, dropped.
- refit_comp (+ `--compensation`), refit_nocap (+ `--sp-no-cap`), refit_realio (+ `--drop 0.04 --sp-camera-delay
  0.29 --sp-camera-drop 0.037`): 56 / 60 / 56 ticks, dropped.
- refit_ball, refit_ball_tjaw (13 mm ball): 0 / 1 ticks, never held.
- **refit_sticky** (+ `--sp-cone elliptic --sp-impratio 10`): 93 ticks, held at hand-back (lift 153.1 mm) and 3 s after.
  refit_sticky_mu035 (object mu 0.35): held, 152.5 mm. refit_sticky_realio (real I/O): held, 152.5 mm.
- **refit_ball_sticky**: 93 ticks, held at hand-back (147.2 mm), gone 3 s after (section 6b). refit_ball_sticky_mu035:
  held at hand-back, 146.0 mm, gone after.

So neither torque nor friction nor the runtime's extras move a pyramidal/1 run, and the training solver settings move
every one. The training env chose them for exactly this reason (`microduck_ground_grasp_env_cfg.py` 141-146: "a block
pinched in the beak's forward-opening wedge creeps out ... Elliptic + impratio 10 holds it").

```
SP_WORKERS=3 nice python3 run_gap.py refit_sticky > logs/refit_sticky.out 2>&1   # results/refit_sticky.jsonl
```

### 3d. What the corrected replica still lacks: jaw torque

```
for st in refit_sticky_tjaw refit_sticky_mu15 refit_sticky_jaw150 refit_sticky_jaw300 refit_sticky_jaw600 refit_sticky_kp400; do
  SP_WORKERS=3 nice python3 run_gap.py $st > logs/$st.out 2>&1; done
```

Jaw torque in the replica is the BAM XL330 m6 model at the run's voltage: limit = min(V kt / R, I kt) with kt 0.366
N m/A, R 2.81 ohm, so 0.0366 N m at 100 mA, 0.0549 at 150, 0.110 at 300, 0.220 at 600, 0.538 at 1470 (V kt / R at 7.0 V
is 0.911). The training jaw is `ground_grasp.MOUTH_ACTUATOR`: stiffness 1.0 N m/rad, damping 0.01, effort 0.5 N m, with
the comment that an XL330 at kP 200 is about 0.55 N m/rad and that Rémi's brief says to assume enough torque. Section 1
gives the ladder: 100 mA 24/54, 150 mA 49/54, training jaw 54/54. The ball is the torque-sensitive case (5 -> 23 -> 27
of 27): at 100 mA the jaw at 20 deg opening meets the 13 mm ball and the ball rolls out sideways before the plates
pinch it (section 6b measures the roll); the box, with flat faces, is pinched at 100 mA in 25 of 27 and then held or
not by friction.

## 4. Step 3: the mouth replica against the printed V1.36 beak (mm)

Measured by vertical ray casts on the V1.36 STLs and the Pollen head CAD in the MJCF head frame (an independent
check by a second agent gave the same numbers to 0.1 mm). Frame: up / forward of the head body, mouth pivot at
+0.0037 up, 18.2 forward.

- **Printed V1.36 against Pollen's CAD**: within 0.2 mm everywhere that touches the object. The pad material is solid
  PLA; the upper pad face spans +-36 mm (CAD +-43); twelve 2.5 mm sound holes sit behind `pad_up`; no lining is in any
  decision D-023..D-029.
- **Training mouth replica (`ground_grasp.add_mouth` = the harness `sp_add_mouth`) against the CAD**: upper pad face
  -9.2 against -6.92 at 68 forward (2.3 mm lower); lower pad top -9.4 against -7.52 (1.9 mm lower); jaw underside -17.4
  against -17.41; lip rim -9.2 against -8.09 at 77.5 forward; closed gap 0.2 against 0.6; jaw half-width 44.0 against
  45.7; hinge 0.5-0.7 mm lower. The replica's aperture at 22 deg is 1.2-2.8 mm smaller than the print's.
- **Fit**: a 10.6-14.4 mm ball or a 10-16 mm box enters all three (replica, CAD, print) at the trained 22 deg opening.

Nothing in the geometry explains a 0 % against 94 %, and the replica errs on the tight side, so a policy that grasps in
the replica is not helped by the print's extra 2 mm. Friction of PLA on the printed ball at 0.5 N squeeze is not in any
source and can only be measured on the robot; section 6a gives what the sim says for the two candidate values.

## 5. Jaw current sweep and stiffness (all shapes, train measure)

From `results/summary.json` (train measure; hand-back; held 3 s after), 54 runs each:

- 100 mA, KP 200 (deployed, 0.037 N m): 24; 24; 19. Ball 5/27 (held after: 1), box 19/27 (18).
- 100 mA, KP 400 (stiffness alone): 28; 28; 23. Ball 9/27 (5), box 19/27 (18).
- 150 mA (0.055 N m, the EEPROM ceiling): 49; 49; 41. Ball 23/27 (15), box 26/27 (26).
- 300 mA (0.110 N m): 50; 49; 40. Ball 23/27 (13), box 27/27 (27).
- 600 mA (0.220 N m): 50; 49; 40. Ball 23/27 (13), box 27/27 (27).
- 1470 mA, KP 400 (the training jaw): 54; 54; 54. Ball 27/27 (27), box 27/27 (27).

The ball saturates at 150 mA (23 of 27 at 150, 300 and 600) and the last four need the training jaw's stiffness as
well as its torque; the box is done at 150 mA. Stiffness without current (KP 400) buys 4 runs. By placement at 150 mA:
6/6 at the centre, +0.01, +0.03, 0/-0.01, 0/+-0.03; 5/6 at 0/+0.01; 4/6 at -0.01 and -0.03.

## 6. Shawn's two levers for the ball (ball only: 9 placements x seeds 0-2 = 27 runs per stage, refit + sticky)

```
for st in lip_mu110 lip_mu050 lip_mu035 lip_mu110_jaw150 lip_mu050_jaw150 lip_mu035_jaw150 close_on_contact close_on_contact_jaw150 ball_baseline; do
  SP_SHAPES=ball SP_WORKERS=3 nice python3 run_gap.py $st > logs/$st.out 2>&1; done
```

Two harness additions carry them (`brain_sim_check.py`): `--sp-beak-priority` puts the beak boxes at MuJoCo priority 1 so
`--sp-beak-mu` is the beak-object friction whatever the object's own (without it MuJoCo takes the larger of the pair, so
the default beak 0.01 means "the object's friction"); `--sp-close-on-contact` starts the trained close (phase 0.34 ->
0.40, then grip) at the first beak-object touch when that comes earlier. Every run now also records
`events.first_contact` (when and which half touched first, jaw opening then), `push_contact_to_pinch_mm` (how far the
object travelled between first touch and pinch) and `close_window` (the object's travel over the trained close window
0.34 -> 0.40 and whether it was pinched at 0.40).

### 6a. Lip friction: inner-tube lining (1.1) against bare PLA (0.35, 0.5)

Ball only, 27 runs per stage (`results/lip_*.jsonl`, `results/levers_ball.json`; train measure; hand-back; held 3 s
after; ever pinched). The beak's friction is the pair's (priority 1).

- At the deployed 100 mA: PLA 0.35: 0; 0; 0; never pinched. PLA 0.5: 0; 0; 0; never pinched. Lining 1.1: 7; 7; 1; 7.
  (The ball's own friction draws, 0.98/1.00/0.55: 5; 5; 1; 5.)
- At 150 mA: PLA 0.35: 7; 6; 0; 13. PLA 0.5: 15; 14; 4; 19. Lining 1.1: 22; 22; 10; 23. (Own draws: 23; 23; 15; 24.)

So at the current the robot can run, bare PLA lips hold the ball in 7-15 of 27 and lined lips in 22 of 27; at 100 mA
no lip holds it. Does the ball squirt out at the close? Not sideways: in the world frame the ball moves a median 3-4 mm
during the close window on PLA lips (0.35: 3.4 mm, 2 of 27 over 10 mm; 0.5: 4.2 mm, 3 over 10 mm) and 9-10 mm with
lining or its own friction, almost all of it backward toward the robot (x -7 to -9 mm) because the upper beak, which
touches first in 20-26 of 27 runs, drags it; sideways in the world the median is 0-3.5 mm with four 10-20 mm outliers,
all seed 1 (the 12.9 mm ball). On PLA the ball stays put and the plates slide over it without pinching (0.35: pinched
at phase 0.40 in 7 of 27; 0.5: 10; lining: 17; own draws: 20). The loss is a slip between the plates, not a squirt.

Of the balls held at hand-back at 150 mA, 10 of 22 (lining) and 15 of 23 (own draws) are still held 3 s into
stand61; section 6b.

### 6b. Close timing: how far the ball rolls at contact, and a close on first touch

Measured on the ball-only reruns `ball_baseline` (100 mA) and `ball_jaw150` (`results/levers_ball.json`; the
`first_contact`, `push_contact_to_pinch_mm` and `close_window` fields of each row).

- **When the beak first touches the ball**: at phase 0.34-0.40, median 0.355, in all 27 runs at both currents; never
  before the trained close start (0.34). The upper beak touches first in 21 of 27 (100 mA) and 20 of 27 (150 mA), the
  jaw plate in 5-6, with the jaw at 20.2 deg (15-23). So a close triggered on first lip contact cannot come earlier
  than the trained one: `--sp-close-on-contact` fired in 0 of 27 runs at either current and `close_on_contact` /
  `close_on_contact_jaw150` reproduce the baselines exactly (5/27 and 23/27). The 3-4 mm forward push by the lower
  plate seen in the 2026-10-27 trace was the box under the stale collision volume; with the ball the first touch is the
  upper beak and the push is backward.
- **How far the ball moves at contact** (world frame, close window 0.34 -> 0.40, 0.24 s): median 9.6 mm at 100 mA
  (0.1-20.4; 11 of 27 over 10 mm) and 9.0 mm at 150 mA (2.2-20.2; 8 over 10 mm); x median -8 mm (toward the robot),
  y median +0.3 / +1.4 mm with the seed-1 outliers at 10-17 mm. Touch to pinch takes 0.18-0.22 s median and the ball
  moves 6-10 mm in it. (The same travel in the foot frame reads 19-20 mm because the robot's own trunk and head move
  during the close; the world numbers are the roll.)
- **A faster close**: the trained close (0.34 -> 0.40) is the same command at every current; what the current changes
  is how fast the XL330 follows it against the ball. Pinched at phase 0.40: 3 of 27 at 100 mA, 20 of 27 at 150 mA,
  22 of 27 at 300 mA; held through hand-back 5, 23, 22. The 150 mA step is the whole gain; the training jaw (27/27) adds
  the four that the stiffer actuator closes before the ball slides along the plate.
- **After the hand-back** (not in the training episode): at 150 mA, 8 of the 23 held balls leave the beak within 3 s of
  the hand-back to stand61 (jaw reads closed afterwards, ball on the floor 0.1-0.3 m away); at 100 mA 4 of 5. Boxes
  stay (26 of 26). The ball at 5 deg jaw opening sits deep in the converging wedge; the stand-up's head motion lets it
  out. The robot run should log the jaw opening through the stand-up, and the deployed timeline is a separate decision.

## 7. Where the fix lands

**(d) Rehearsal harness, applied in this study.** `brain_sim_check.py` gained `--sp-cone`, `--sp-impratio`,
`--sp-beak-priority`, `--sp-close-on-contact` and the three contact measurements, and prints a warning when a seepick
run lacks `--bvh-refit --sp-cone elliptic --sp-impratio 10`. `run_rehearsal.base()` in `../seepick-rehearsal-20261027/`
is left as it ran (its rows are the 0/96 record); the next rehearsal grid uses `run_gap.py refit_sticky...` from here.
Proposed, not applied, because it moves every as-built sim that goes through the loader (`brain_sim_check.py`,
`pickup_sim.py`, `target_ground.py`, `stance_switch.py`, `duck_kin_export.py`, `run_experiments.py`) and so every
walking/standing baseline recorded since 2026-09-12; Shawn's call:

```
--- delay-repair-20260912/evaluate_delay.py  (load, after add_signed_inertias)
     if mass_parts:add_signed_inertias(m,mass_parts)
+    refit_body_bvh(m)   # the BVHs were built in the compile-time inertial frames; see seepick-gap-20261029/README.md
     d=mujoco.MjData(m)
```

(`refit_body_bvh` would move from `brain_sim_check.py` into `evaluate_delay.py`; the feet's boxes do not change, so the
walking numbers should not move, but that is to be shown, not assumed.)

**(a) Runtime, proposed diff only (another agent owns `jaw_ctl.py`).** The 150 mA ceiling already exists in the EEPROM
(`CURRENT_LIMIT_MA = 150`); only the goal current moves. The phase-1 runtime accepted 20-150 mA. Heat at 150 mA during a
hold is the one thing the sim cannot answer; the robot acceptance in `PROJECT-CONTEXT.json` (8 of 10 hand-placed
trials, jaw >= 3 deg from closed, object off the floor through the rise) is the test.

```
--- microduck-sim/guide/firmware/mac/jaw_ctl.py
-GOAL_CURRENT_MA = 100     # grip force limit; the phase 1 runtime accepted 20..150 mA (XL330 1 mA per LSB)
+GOAL_CURRENT_MA = 150     # grip force limit at the EEPROM ceiling; 100 mA held 24/54 of the seeing-pick rehearsal
+                          # grid in sim and 150 mA 49/54 (seepick-gap-20261029/README.md); the phase 1 runtime
+                          # accepted 20..150 mA (XL330 1 mA per LSB)
```

`walk_brain.py` and `walk_wired.py` need no change for this gap: the policy's inputs match the training env tick for
tick (section 3a), `compensate` and the jaw cap do not move any run.

**(b) Training env, needs a new run (waits for Shawn's go).** Model the jaw as the robot will run it: a BAM-class
XL330 position actuator at the deployed current limit (0.055 N m at 150 mA, kP 200) instead of 1.0 N m/rad / 0.5 N m, so
the policy learns to centre the ball before the plates meet rather than relying on torque it will not have; keep
`cone elliptic / impratio 10` only if the lip is lined (section 6a decides); the beak friction 1.5 is then the lining's,
not an assumption. Also the x = -0.03 weakness (0.56 in the env's own eval). The current policy stays installed; this
is the next run's recipe, not a change to seepick61.

**(c) Beak hardware.** Geometry: nothing. Lining: for the ball, yes. At 150 mA the sim holds the ball in 22 of 27 with
inner-tube lips (1.1) and in 7-15 of 27 with bare PLA (0.35-0.5); at 100 mA no lip holds it (section 6a). The lining
is the same bike inner tube as the soles, glued on the two pad faces (upper pad face +-36 mm wide, lower pad top); no
reprint. The friction the real pads give at 0.5 N squeeze is then read from the acceptance trials, not assumed.

**Runtime item from 6b, for the robot plan, not this gap:** after the hand-back to stand61 the ball leaves the beak in
8 of 23 sim runs at 150 mA. Log the jaw opening through the stand-up on the robot; whether the timeline or the stand-up
head pose changes is a separate decision.

## 8. Caveats

- The two solver flags make the replica agree with the training env, not with the robot: elliptic / impratio 10 is
  Pollen's "assume enough friction". A held sim grasp at 150 mA is a necessary condition for the robot trial, not a
  prediction of its rate.
- The hand-back at phase 0.9 to stand61 is outside the training episode (scored up to phase 1.0 in seepick mode); every
  ball that was held at hand-back at 100 mA had left the beak 3 s later (section 6b). The robot run should log the jaw
  opening through the stand-up.
- The BAM XL330 m6 model at 100-150 mA has not been measured on the jaw itself; the sweep's torque axis is the
  model's.
- Training-side items that did not change the rehearsal outcome but differ from the robot: the training jaw crushes the
  15 mm box (jaw -0.03..-0.05 rad while "pinched", `traces-20261027/tr_nom.jsonl` ticks 82-199) where the robot's
  stalls at 0.27 rad; the training beak friction 1.5 overrides every object friction through MuJoCo's max rule.

## Files

- `run_train_eval.py`, `results/train_eval.jsonl`, `logs/train_eval.out`: step 1.
- `run_gap.py` (stages above), `results/<stage>.jsonl`, `logs/<stage>.out`, `results/summary.json`: the grids.
- `levers.py`, `results/levers_ball.json`, `results/levers_all.json`: the ball lever numbers (first touch, roll, close
  window, hand-back).
- `compare.py`, `results/compare.txt`, `results/comparison.json`: training eval beside each grid per case.
- `run_single.sh`, `local_bisect.sh`, `mini_singles.sh`, `results/single/*.out|.jsonl`: the matched single runs.
- `cmp.py`, `traces-20261027/`: the 2026-10-27 training/runtime traces (moved from the rehearsal's `gap/`).
- `microduck_rl-grasp/cmu/grasp/gap_trace.py` (branch `cmu/grasp`): `--exact`, `--object-yaw`.
