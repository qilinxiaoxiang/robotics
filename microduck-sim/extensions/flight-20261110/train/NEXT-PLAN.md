# Next training round: universal3 and bend4 (plan, NOT approved, NOT launched)

Status 2026-11-12: written for Shawn's review. Nothing has been pushed to Kaggle; the coordinator launches after
checking this plan and its audit files. Sim only; nothing goes to the robot, the A7Z or the team repository.

Robot model: `microduck_rl/cmu/model/current.json` names battery-20261104 (mass manifest sha256 232708646e618ee4). The
flight manifests in `manifests/flightpack-*.json` are built on that variant, so they need no rebase. Supply, sensor and
servo facts come from `microduck-sim/CURRENT-STATE.json`.

Kaggle quota, read from the account at 2026-11-12 03:30 EST with
`python3 cmu/finetune/flight/kaggle_flight.py quota` (run from `microduck_rl`): GPU 26.75 h used, 3.25 h left of 30 h,
refresh at 2026-11-14T00:00:00 (the CLI prints no time zone). Another session's kernel (`microduck-play-a`) was
RUNNING at that time and is still drawing on the 3.25 h, so this round should launch after the refresh. A paired
two-GPU session counts once: this week's recorded kernel wall times sum to the quota used (25.23 h against 25.24 h
before play-a started).

This round is one paired session (universal3 on GPU 0, bend4 on GPU 1): about 3.6 h of quota (the longer job, bend4,
3.3-3.5 h, plus setup), within the 30 h after the refresh and above the 3.25 h left now.

## 1. universal3 (one stand/walk policy for every load), from run A final

### Cause evidence
Run A final (`ckpt/uni_a/walk61.onnx`, sha256 3aadc94a, the same file as
`kaggle/out/fk-uni-a2/runs/fk-uni-a2/fk-uni-a2.onnx`) fails `out/accept_uni_a.json` on six lines. Causes:
- COM 10 mm forward (stand 5/20, walk 19/20 falls at about 0.9 s, torque saturated from the first tick). This is a
  training-coverage gap, not physics. Run A's payload event adds U(-15, 15) mm to the loaded trunk COM; the trunk is
  68.3 % of the robot with the full pack and 36.7 % without it, so that is +-10.2 mm whole-robot with the pack and
  +-5.5 mm without, and only 1.2 % of full-pack resets reach +10 mm forward (0 % without the pack;
  `out/plan_statics.json` training_offset). The case is statically easy: at the brain stand pose the comx+10 robot has
  its COM 16 mm inside the sole patch and needs at most 0.161 N m (centred lean 0.226 N m; `plan_statics.json`
  stand.comx+10), and fq2 1999 holds it with 0 falls (`out/accept_fq2_1999.json`).
- 0.5 N s shove while walking (11/20 falls): the shove is about 0.26 m/s at 1.9 kg. Training pushes are +-0.3 m/s
  set velocities every 3-6 s, so only about 7 % reach 0.26 forward. Falls are forward.
- Step width 123 mm against 105: no universal2 term acts on stance width (the hip-roll pose std is already 0.05 rad);
  walk61 walks 94 mm, so it is a learned habit.
- Walk torque p99 0.53 against 0.48 and 75 % load saturation 1.08 %: the torque hinge at 0.45 N m has weight -12.
- Full pack with head pitch 1.1 while walking, 3/20 falls: the same forward-COM gap (the head moves the COM forward).
- Stepping in place nearly pays: in the universal3 audit before the progress term, a walker that steps in place
  earned 0.84 of the walk at batteries out (`out/audit3_u3c_shuffle_nobatt.json`) because the Gaussian velocity
  tracking (std 0.22 m/s) pays 0.89 of the walker's tracking at 0.03 m/s against 0.14 m/s.

### Published practice and what changes
- legged_gym (https://github.com/leggedrobotics/legged_gym/blob/master/legged_gym/envs/base/legged_robot_config.py):
  pushes as velocity sets of up to 1 m/s every 15 s; base added mass +-1 kg. Adopted in kind: universal3 widens the
  forward/back push to +-0.35 m/s (13 % of pushes now exceed the acceptance shove instead of 7 %). Not to 0.5: the
  2026-07 note says +-0.5 trained a nervous gait on this robot.
- RMA (https://arxiv.org/abs/2107.04034): payload 0-6 kg and COM +-0.15 m in training, wider at test; the base policy
  trains on the whole test range. Adopted: the COM x offset is now drawn in whole-robot terms, U(-12, 12) mm at every
  load (trunk offset 17.6 mm at full, 32.7 mm without the pack). P(|x| >= 10 mm) = 17 %, P(x >= +10 mm) = 8 % at every
  load, against 1.2 % / 0 % before. RMA's 0.5 s history adaptation module is refuted for this round: it changes the
  61-input runtime contract; it stays the fallback.
- Walk These Ways (https://github.com/Improbable-AI/walk-these-ways/blob/master/go1_gym/envs/go1/go1_config.py):
  COM +-0.1 m, mass -1 to 3 kg on a proprioceptive actor. Consistent with keeping the 61-input actor.
- Humanoid-Gym (https://github.com/roboterax/humanoid-gym/blob/main/humanoid/envs/custom/humanoid_config.py): push
  0.2 m/s every 4 s, frame stack 15. The frame stack is refuted for the same runtime reason.
- BDX (https://arxiv.org/abs/2501.05204): force pushes with a curriculum. Refuted for now: a velocity-set push of the
  same impulse is already in the env and the shove failures are at the edge of its range, so the range is widened.
- Stance width and torque have no published recipe beyond penalising the quantity; adopted as costs (below).

### What the actor observes
Unchanged: 61 inputs, one frame (trunk angular velocity 3, gravity 3, 14 joint angles, 14 joint velocities, 14
previous actions, command 13). No load or COM input; the runtime needs no change. The critic keeps its 80 inputs with
payload kg and loaded trunk COM.

### Changes against run A (delta `universal2`) = delta `universal3`
Reward mods `rm_universal3.json` (equal to `flight_worker.UNIVERSAL3_MODS`, checked at push by `kaggle_flight.py`):
- COM x range: whole-robot U(-12, 12) mm at every load (`com_x_whole_m` 0.012, `payload.trunk_payload`).
- Pushes x: +-0.35 m/s (was +-0.3); y unchanged.
- New `step_width_over` cost, weight -15, above 100 mm (`style_terms.step_width_over`).
- Torque hinge at 0.45 N m: weight -20 (was -12).
- New `progress_along_cmd` reward, weight 8: the 0.5 s EMA velocity along the command as a fraction of the commanded
  speed, in [0, 1], for commands of at least 0.10 m/s (`style_terms.progress_along_cmd`). Capped at the command, so
  walking faster than asked earns nothing more.
- Everything else as universal2 (runtime command ranges, air time 6, tracking 3, upright 0.5, head-pose tracking 1,
  hip-yaw std 0.15, stance-foot-heading -8, the payload states and weights).

### Incentive audit (Mac mini, CPU, 128 envs x 400 steps, one case per job)
Job `universal3` of `microduck_rl/cmu/finetune/flight/flight_audit.py`. The intended behaviour at every load is run A
final walking (the stander-at-small-command split of the runtime); the degenerate cases are the same policy standing
(zero command), stepping in place (an in-place turn command while the env asks for a walk) and leaning and holding
forward and back. Pass: every degenerate case earns at most 0.80 of the walk per second. Verdict PASS at full,
batteries out and no pack, recorded in `out/audit_gate.json` (delta universal3, 18 files).
- Training command range, `out/audit3_u3e_<case>_<load>.json`: stand 0.545 / 0.543 / 0.544 (full / batteries out /
  none), step in place 0.705 / 0.718 / 0.693, lean forward 0.523 / 0.508 / 0.525, lean back 0.520 / 0.507 / 0.516.
  The walk earns 10.29 / 10.42 / 10.37 per s at 0.142 / 0.138 / 0.155 m/s along the command.
- Commands of 0.15-0.30 m/s forward only (`rm_u3e_fast` = the same mods with that command range),
  `out/audit3_u3efast_<case>_<load>.json`: stand 0.515 / 0.495 / 0.507, step in place 0.617 / 0.630 / 0.606.
- Before the progress term (same mods without it) stepping in place earned 0.843 at batteries out
  (`out/audit3_u3c_shuffle_nobatt.json`, FAIL); with weight 4 it earned 0.773 (`out/audit3_u3d_shuffle_nobatt.json`),
  too close to the gate for the 0.04 run-to-run spread seen between two samples of the same case (0.796 and 0.843).
- The walker used as "intended" walks 0.136-0.155 m/s under commands of 0.15-0.30: it is slower than asked. The
  audit shows walking out-earns standing and stepping at those commands; the speed itself is an acceptance line.

### Run
- Start checkpoint: `/root/assets/init/uni_a.onnx` (run A final, shipped by `kaggle_flight.py` from `ckpt/uni_a`).
- 2000 iterations at about 0.19 it/s, about 2.9 h plus 5 min setup; cap `--max-hours 3.5`.
- Checkpoints every 250 iterations (`--save-interval 250`), 8 checkpoints plus the final and best ONNX.
- Stop conditions (task metrics only): the worker's tracking guard `--track-guard 2.0` (stops when velocity tracking
  error doubles, or speed along the command or the low-command speed halves, against the 100-iteration warm-up, on two
  saves). The reward guard is off (`--guard-fraction 0.0`). Manual stop by the coordinator at any fetch of the
  progress file if the speed along the command falls below 0.10 m/s on two saves.
- Acceptance: `accept_universal.py run uni3` then `score`, reference fq2 1999 and uni_a on the same machine; it
  passes only if every current line passes (comx+10 and shove falls no more than fq2's, step width at most 105 mm,
  walk p99 at most 0.48, load075 saturation at most 1 %, speed floor 0.15 m/s, head motion falls).

### What could still fail
- The shove and COM+10 failures could need history (the policy cannot tell a COM offset from a lean in one frame).
  Then the fallback is RMA-style history, a runtime change that needs Shawn's decision.
- The progress term could make the no-pack walk overshoot the 0.15 m/s band less than it does now, or push torque up
  at full load; both are acceptance lines and are checked.
- The step-width cost may trade against toe-out (stance-foot-heading). Both are acceptance lines.

## 2. bend4 (the bend with the pack), from the original groundpick61

### Cause evidence
The bend run (fk-bend-a2, delta bend3, `ckpt/bend_a2`) fails `out/accept_bend_bend_a2.json`: no-fall 2 / 19 / 4 of 20
at full / batteries out / none, every fall at 11.3-12.3 s, after the rise and the hand-back to the stander; trunk pitch
16 / 14 / 13 deg against 25-45; mouth within 3 cm in 9/17, 7/17, 14/17 held episodes; knee p99 0.538 (the clamp).
- It squats. At its lowest point the knee is at the joint limit (median |q| 1.575 rad at every load, limit 1.571;
  original groundpick61 0.58-0.63), hip pitch near 0, trunk 14.8 deg, mouth 2.0 cm, static right knee 0.51 N m
  (`out/plan_statics.json` bend_policy_lowest).
- bend3's reward paid the squat more than the bend. Pricing bend3's reward on the squat (bend_a2 itself, real
  dynamics) against groundpick61's bend: 1.72 of the bend at batteries out, 1.00 without the pack
  (`out/bendaudit4_b4diag_nobatt.json`, `_none.json`). bend3 had nothing on trunk pitch or knee angle.
- The bend is physically available and is not a squat. The lowest-torque bend-like pose at full pack (hip -1.442, knee
  0.142, ankle 1.028, neck -1.571, head -0.141) has trunk 31.9 deg, mouth 2.9 cm, worst leg torque 0.238 N m and the
  COM 8.8 mm inside the sole (`plan_statics.json` bend_statics_best); 1065 bend-like poses have every leg joint at or
  under 0.50 N m. No acceptance line conflicts with physics. The squat is still statically cheaper (0.186 against
  0.238 N m), so the reward has to make it lose.
- The hand-back was never trained: the episode never handed over, so nothing in training priced the state the bend
  leaves for the stander. In the audit below, run A's walker standing at zero command falls 2.2-6.4 times per
  stander-minute when it takes over from a stander (stand case) and 4.6-17 after groundpick61's bend.

### Published practice and what changes
- DeepMimic (https://arxiv.org/abs/1804.02717) and AMP (https://arxiv.org/abs/2104.02180): a task reward alone finds
  unnatural solutions; both add a pose or style term (DeepMimic pose weight 0.65; AMP task and style 0.5 each). Multi-AMP
  (https://arxiv.org/abs/2203.14912) reports a style prior fixing a sit-down that fell forward. Adopted in the cheap
  form: state costs that define the bend (trunk pitch band, knee margin) instead of a learned style discriminator,
  which would need reference motion we do not have.
- Haarnoja et al. soccer (https://arxiv.org/abs/2304.13653): skill transitions are trained by running the next skill
  inside the episode (and by distillation); the get-up reward uses torso orientation. Lee et al. 2019
  (https://arxiv.org/abs/1901.07517): the behaviour selector trains from the states the other behaviours leave.
  Adopted: the in-episode hand-back below. Distillation into one policy is refuted for this round (the runtime keeps
  separate bend and stand slots).
- BDX (https://arxiv.org/abs/2501.05204): neck imitation weight far above the legs'. Not adopted; there is no
  reference motion for this bend.

### What the actor observes
Unchanged from groundpick61: 61 inputs, one frame, the phase in the twist slots as [cos 2 pi phase, sin 2 pi phase, 0].
No load input; the critic keeps payload kg and trunk COM (78 inputs). During the hand-back the phase stays at 0 and
the stander sees the same frame with the twist slots zeroed, as walk_brain sends it.

### Changes against bend3 = delta `bend4`
Reward mods `rm_bend4.json` (equal to `flight_worker.BEND4_MODS`, checked at push):
- bend3's two mouth costs unchanged (-240 each: mouth above 3 cm during the hold, below 18 cm during the rest).
- New `trunk_pitch_off_band`, weight -150: trunk nose-down pitch outside 25-45 deg during the low hold (phase
  0.33-0.45), in rad (`bend_terms.trunk_pitch_off_band`).
- New `knee_near_limit`, weight -20: |knee| beyond 1.25 rad at every step, both knees.
- New `stance_off_at_rest`, weight -20: mean squared leg-joint error from the stand pose during the rest window (phase
  0.85-1.0), so the bend ends where the stander starts.
Environment (`flight_worker.BEND4_HANDBACK`, `bend_terms.install_handback`):
- Hand-back inside the episode: at the end of a cycle, in a quarter of the cycles, the phase stays at 0 for 2 s and run
  A's walker (`init/uni_a.onnx`, zero twist command) drives the joints from the state the bend left. A fall there ends
  the episode, so the bend policy's value at the rise carries the stander's outcome. Its own actions during the 2 s
  have no effect, so their policy-gradient term has zero mean. Then the next cycle starts from the stander's pose,
  which is also the runtime's stand-to-bend switch.
- Held crouch as bend3: half the envs hold phase 0.33 for 4 s once per cycle.
- Bend guard (`bend_terms.bend_guard`, a watcher at weight 1e-9): every 6000 env steps (one save interval) it logs the
  hold's median knee, mean trunk pitch, median mouth height, falls per env-minute and hand-back falls, and stops
  training when two windows in a row (after the first) show the squat (median knee above 1.30 rad or pitch under
  20 deg) or falls above twice the first window's. Checked on the Mac mini (`logs/bend4_guardtest.log`: it raised the
  stop on the second window as designed).
- Not adopted: a cost on the ankle past 1.20 rad. CURRENT-STATE.json (ankle_bend_stall) says the robot's ankles stop
  at about 1.25 rad in the held bend (the rear-socket plug meets the foot) while the sim stops them at 1.36. The
  audit's bend proxy, groundpick61, itself spends ankle beyond 1.20 (raw 0.18-0.23 rad per s), so any such weight sinks
  the intended case below zero and cannot be audited. This is the open sim-to-real gap of the bend, listed below.

### Incentive audit (Mac mini, CPU, 128 envs x 400 steps, `microduck_rl/cmu/finetune/flight/bend_audit.py --delta bend4`)
Intended: groundpick61 following the phase command, the pack's weight carried by an upward force at the payload COM at
pack loads (no policy bends with the pack yet), its reward lowered by the static extra torque cost (-0.005 / -0.001 per
s). Degenerate: stand (the pack stander fq2 or stand61 at zero command), half bend (phase capped at 0.15), stay down
(phase capped at 0.40), sit back (pack loads: groundpick61 on the real pack dynamics) and the squat (bend_a2 itself,
real dynamics). The hand-back runs in every case. Pass: every degenerate case at most 0.80 of the intended per second.
Verdict PASS at full, batteries out and no pack, recorded in `out/audit_gate.json` (delta bend4, 8 files
`out/bendaudit4_b4h{a,b,c}_<load>.json`).
- Intended reward per s: 0.551 / 2.178 / 5.523 (full / batteries out / none).
- Squat: -16.7 / -4.08 / -1.51 of the intended (it earned 1.72 and 1.00 under bend3). Its pitch-band and knee costs
  are 8.3 and 8.3 per s at full.
- Stay down: -0.83 / 0.065 / -0.009. Half bend: -8.1 / -1.3 / -0.86. Stand: -49.6 / -13.6 / -6.0. Sit back: -6.6 /
  -4.3.
- The margin is thin in one place: at full pack the intended earns only 0.551 per s, because the compensated
  groundpick61 still pays the rest-window mouth cost (-2.06) and the pitch band (-2.02). Every degenerate case is
  negative there, so the ratio gate holds, but a behaviour the audit does not list that earns a little above zero at
  full pack would beat this proxy.
- Hand-back survival, every cycle handed back (`--handback-frac 1.0`, intended only, `out/bendaudit4_b4hhb_<load>.json`;
  a measurement, not a gate file): the stander falls 13.4 / 9.5 / 3.1 times per stander-minute after groundpick61's
  bend (258-277 s of stander time per load). With every cycle handed back the intended reward at full pack drops to
  -0.43 per s, so the hand-back share stays at a quarter in training; raising it would need the audit rerun.

### Run
- Start checkpoint: `/root/assets/init/groundpick61.onnx` (the original, sha256 ffbf5109; not bend_a2, which sits in
  the squat basin).
- 2000 iterations at about 0.17 it/s (bend3's rate; the stander adds one small MLP per step), about 3.3 h plus 5 min
  setup; cap `--max-hours 3.5`, which ends it before iteration 2000 if it runs slower than 0.16 it/s.
- Checkpoints every 250 iterations.
- Stop conditions (task metrics only): the bend guard above. The reward guard is off (`--guard-fraction 0.0`).
- Acceptance: `accept_bend.sh` / `score_bend.py` as for bend_a2, reference the original groundpick61: no-fall 18 of 20
  at full, batteries out and none with the hand-back; mouth within 3 cm and trunk pitch 25-45 deg over the hold; hip,
  knee and ankle p99 at most 0.50 N m; knee at the lowest point well off 1.571 (reported, with the leg pose).
  Add to the report: the ankle angle over the hold against the robot's 1.25 rad stop.

### What could still fail
- The stander: run A's walker falls after groundpick61's bend at 4.6-17 per stander-minute. If the bend cannot learn a
  rise the stander holds, the hand-back stays the failure. The guard logs it per window.
- The ankle: a bend learned against the sim's 1.36 rad stop may need more ankle than the robot's 1.25. Fixing it in
  the sim means a model change (a 1.25 rad ankle limit, which CURRENT-STATE.json says closes the bend's trunk and
  camera gap) through `cmu/model/current.json`; that needs a decision, not a reward weight.
- A degenerate the audit does not list. The guard's pitch and knee checks cover the squat family on the training data.

## 3. The push (ready, not pushed)
Kernel `shawnxiang9527/microduck-fk-uni3`, jobs fk-uni3 (GPU 0) and fk-bend4 (GPU 1). From `microduck_rl`:

    python3 cmu/finetune/flight/kaggle_flight.py push run --run-name fk-uni3 --pair-run-name fk-bend4 -- \
      --delta universal3 --onnx /root/assets/init/uni_a.onnx --manifest /root/assets/manifests/flightpack-none.json \
      --max-iters 2000 --max-hours 3.5 --save-interval 250 --warmup-iters 100 --max-lr 0.0003 \
      --guard-fraction 0.0 --track-guard 2.0 --seed 1 -- \
      --task Mjlab-GroundPick-Flat-MicroDuck --delta bend4 --onnx /root/assets/init/groundpick61.onnx \
      --manifest /root/assets/manifests/flightpack-none.json --max-iters 2000 --max-hours 3.5 --save-interval 250 \
      --warmup-iters 100 --max-lr 0.0003 --guard-fraction 0.0 --seed 1

The push uploads a new version of the private dataset microduck-flight-src first (the source changed), then the kernel.
Checked without uploading (scratch `push_check.py` through `kaggle_flight.py`'s own functions, 2026-11-12 05:27):
both flag lists are accepted, the assets exist (`init/uni_a.onnx` = `ckpt/uni_a/walk61.onnx` is newly shipped by
`kaggle_flight.py`), the audit gate passes for universal3 and bend4, and both deltas' reward mods equal the audited
`rm_universal3.json` and `rm_bend4.json`. Training smokes on the Mac mini (3 PPO iterations, 64 envs, CPU):
`logs/bend4_smoke.log` (hand-back stander loaded, every new term logged) and `logs/universal3_smoke.log` (progress 8,
step width -15, torque -20 active).
Status and fetch: `python3 cmu/finetune/flight/kaggle_flight.py status fk-uni3`, then `... fetch fk-uni3`.
