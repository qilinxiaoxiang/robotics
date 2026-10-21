# MicroDuck problem 6: the quack head move, its speed, and the "two systems" question (2026-10-21)

Robot off, A7Z offline; everything below is from the repository, the copied robot logs and the as-built CPU simulation.
Repo root: `/Users/xiangzheng/code/robotics` (R). Current robot facts from `R/microduck-sim/CURRENT-STATE.json`:
`servo_rail_v` 7.0, `servo_read_drop_fraction` 0.04, `imu_rate_hz` 50, `walking_policy` walk61.onnx (Pollen
BEST_alpha_walking), KP_RL 200, stand mode KP 400.

## Answers (short)

1. **Current behaviour.** A quack opens the jaw to 15 deg for 0.4 s and, in the same tick, starts a head move whose
   target rises over a 0.5 s raised cosine, holds, and is back 1.6 s after the quack (`walk_wired.py:255-268`). The calls
   themselves last 0.12-0.40 s (48 files, median 0.20 s). The head therefore reaches half of its commanded tilt about
   0.5 s after the quack, after the call has ended (sim, below). The 1.6 s was a design choice ("gentle so stand61
   never gets a jolt", `walk_wired.py:261`), not a measured requirement.
2. **The seven seated quacks on 2026-10-21 moved only the jaw** because the version running on the A7Z at 04:07 UTC
   allowed the head move on stand61 only and, independently, `Brain.route` dropped `want["head"]` while seated; both
   were fixed in commit 82d5f87 (00:22 EDT = 04:22 UTC, after the log). Evidence: the log rows carry no `head_cmd` and
   the stdout quack lines carry no head suffix.
3. **Is the slowness necessary? Not for balance in the as-built sim.** The policies were trained on head commands
   that step to a new value every 2-5 s; the runtime adds a 0.2-per-tick EMA. In the plugged as-built sim at the
   CURRENT-STATE condition, the 1.6 s profile, a 0.5 s profile and a plain step all leave the trunk tilt within
   0.12 deg of its rest value on stand61 and seated, 3 seeds each, no fall. The only reason to keep a ramp is the
   seated case, where Pollen saw abrupt head moves tip the real duck backward.
4. **Two systems?** Our stack already has them: Pollen's walk/stand policy is a learned balance controller that takes
   the head pose as a task command (observation slots 55-58), so any program that writes commands inside the trained
   envelope is the "task system". Modern humanoid stacks do the same split (lower-body RL balance + upper-body task
   commands: ExBody 2024, Mobile-TeleVision 2024, AMO 2025; or one whole-body tracker: OmniH2O 2024, HumanPlus 2024).
   No new "quack" policy is needed for head moves inside the envelope. A motion outside it (a bow, a nuzzle that moves
   the trunk) needs a registered fine-tune delta that passes the D-016 reward audit.
5. **Proposed constants:** `QUACK_HEAD_S` 1.6 -> 0.6 s, `QUACK_HEAD_RAMP_S` 0.5 -> 0.15 s, jaw and head keep starting
   together, a quack inside a running move holds the reached pose instead of restarting the ramp. Patch:
   `/private/tmp/claude-501/-Users-xiangzheng-code-robotics/74602e44-fa79-4564-a436-c7a3c8ce2ecd/scratchpad/patch/quack-constants.patch`
   (`git apply --check` passes; not applied).

## 1. Current behaviour (evidence)

### Constants and profile

`R/microduck-sim/guide/firmware/mac/walk_wired.py`:

- 255-256: `QUACK_JAW_DEG = 15.0  # jaw opening for a quack; jaw_limits still caps it by the head pose` / `QUACK_S = 0.4`
- 261-262 (comment): "The move is gentle so stand61 never gets a jolt: the target follows a raised cosine up over
  QUACK_HEAD_RAMP_S, holds, and comes back the same way, and the Brain's own head EMA smooths it further."
- 265-268: `QUACK_HEAD = ({"head_roll": (0.08, 0.18), "head_yaw": (0.0, 0.25)},       # tilt` /
  `{"head_pitch": (0.15, 0.30, -1), "head_roll": (0.0, 0.10)})  # look up` / `QUACK_HEAD_S = 1.6` / `QUACK_HEAD_RAMP_S = 0.5`
- 269: `QUACK_REST_S = 2.0  # walk61 after stepping: a zero command held this long has brought the stride to rest`
- 270-273: "Pollen trained the seated head on small slow commands and saw fast head jerks tip a seated duck backward;
  this move is slow." `QUACK_SIT_SCALE = 1.0`
- 276-279 `quack_head_share(t)`: "0 -> 1 -> 0 over QUACK_HEAD_S: raised-cosine ramps of QUACK_HEAD_RAMP_S at each end,
  1 in between."
- 473-495: the quack handler. Jaw: `jaw.goal_deg, quack_until = QUACK_JAW_DEG, time.perf_counter() + QUACK_S` (479).
  Head, same tick: `why = quack_head_block(...)`; if allowed, a random style, `quack_head_t0 = time.perf_counter()`
  (484-489). So jaw and head already start together; a second quack while a move runs resets `quack_head_t0`,
  i.e. the profile restarts from share 0.
- 601-608: every tick, `want_b["head"] = quack_head_pose(quack_head, tq, brain)` while `tq < QUACK_HEAD_S` and the
  gate still allows it.

### Gating (`quack_head_block`, `walk_wired.py:282-303`)

Docstring 286-288: "Walk mode at zero command: stand61, and walk61 once its stride has come to rest (QUACK_REST_S
after the stop). Seated: the sitstand policy, at QUACK_SIT_SCALE of the move. Never while stepping, sitting down or
standing up, and never in the open-loop stand mode, which cannot rebalance (it tipped over there on 2026-10-20)."
Return values: `"a head command is active"`, `"walking"`, `"the stride is still coming to rest"`, `"sitting down"`,
`"standing up"`, `"open-loop stand mode cannot rebalance"`.

### Call lengths

The deployed folder holds 48 calls (`/private/tmp/claude-501/stand/duck_wired_app1021-040436.out:3`:
`quack: 48 calls in /home/radxa/rt/microduck-sim/guide/firmware/mac/sounds`), i.e. the 4 x 12 simulator chirps with
no mallard file (`install_teleop.sh:73` builds with `${MALLARD:--}`). `bringup/scripts/build_duck_calls.py` filters
and fades each chirp without trimming (`ff(src, c.wav, CHAIN)` then `write(...)`, lines 79-81), so the durations are
the sources'. Rebuilt in the scratchpad and measured with `python wave`:

```
python3 bringup/scripts/build_duck_calls.py - microduck-simulator/app/public/assets/voices <scratch>/calls
48 calls: min 0.117 p25 0.163 median 0.204 p75 0.291 max 0.403 mean 0.225 s ; over 0.3 s: 9 ; under 0.2 s: 23
```

The seven calls played on 2026-10-21: 0.193, 0.206, 0.146, 0.149, 0.403, 0.250, 0.215 s. The jaw opening (0.4 s)
already covers the longest call; the head move (1.6 s) is 4-14 times the call.

### The 2026-10-21 seated quacks: why the head stayed

Log `/private/tmp/claude-501/stand/duck_wired_log_app1021-040436.jsonl` (15357 rows, copied from the A7Z
`~/duck-logs`): seven quack counters at t = 1792555587.6, 588.7, 591.2, 591.9, 594.0, 594.9, 595.6 (0.7-2.5 s apart),
every one with `mode == "sit"`, `sit_phase == "seated"`, policy sitstand; `rows with head_cmd: 0`; the jaw goal
alternates 15.0 -> 2.0 at those times. Stdout lines 132-147 read e.g. `quack 1792555587477: duck2_chirp_f.wav` with
no `head ...` / `head stays (...)` suffix, which the committed code always prints (`walk_wired.py:492-495`).

Inference: the running copy was the 2026-10-20 working tree that commit 82d5f87 describes ("deployed to the A7Z since
2026-10-21 00:59 UTC but never committed"; the commit itself is 2026-10-21 00:22 EDT = 04:22 UTC, after the 04:04-04:07
UTC log). That copy moved the head "on stand61" only, and `Brain.route` "returned a bare {"mode": "sit"} while seated,
so want["head"] never reached the sitstand policy" (commit message; fix at `walk_brain.py:367-368`). Two independent
blocks, both removed in 82d5f87; the committed gate now returns `None` for `brain.sit["phase"] == "seated"`
(`walk_wired.py:297`), and `test_quack_head_moves_wherever_a_policy_rebalances` covers it.

### The 2026-10-20 tip-over in open-loop stand

The only record is the docstring (`walk_wired.py:288`) and the same sentence in 82d5f87. The three robot logs on this
Mac (`duck_wired_log_1020a.jsonl`, `app1021-035737`, `app1021-040436`) contain no quack in stand mode (0 quack rows in
the first two). Independent evidence on that mode: the 2026-10-21 stand-gap study
(`R/microduck-sim/guide/firmware/mac/stand-gap-20261021/README.md`, commit 4ef1d06) found the open-loop stand at KP 400
"tips forward on the robot within about 20 s since 2026-10-20 night" on its own and in the sim "any lean grows"
("KP 400 is too soft to hold the stand, not a COM error"). So in that mode a head move can only add a lean that nothing
corrects; whether the 10/20 head move caused the tip or coincided with the self-tip is unverified. The gate's choice
(never in open-loop stand) is right either way, because that mode has no balance controller.

### Why the move is slow

Design intent, not measurement: `walk_wired.py:261` ("gentle so stand61 never gets a jolt") and 270-272 (Pollen's seated
observation). The sim result quoted in 82d5f87 ("walk61 at rest 0.17-0.25 rad, peak tilt 2.2 deg") is an absolute
peak tilt of the trunk in the model, measured after a walk; in this study the same quantity reads 0.7-0.9 deg on stand61
and seated, 2.1 deg on walk61 at rest (the policy's resting posture, not the move: the rise above rest is 0.06 deg).

## 2. Is the slowness necessary?

### What the policy was trained on

- `R/microduck-sim/microduck_rl/src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py:49`:
  `HEAD_POSE_CMD_RESAMPLE_S = (2.0, 5.0)`; 666-673: `cfg.commands["head_pose"] = microduck_mdp.UniformPoseCommandCfg(
  resampling_time_range=HEAD_POSE_CMD_RESAMPLE_S, ranges=(...))`.
- `tasks/mdp.py:5304-5345` `class UniformPoseCommand`: "Samples each dim independently uniform in cfg.ranges[i] =
  (lo, hi) and holds the value between resamples" (5307-5308); `def _update_command(self) -> None: pass` (5324-5325).
  **The command steps**; nothing in the env ramps or filters it, and the observation term is `mdp.generated_commands`
  (694-697), the raw command.
- Final ranges (curriculum `head_pose_range`, 816-828): neck_pitch +-1.10, head_pitch +-1.10, head_yaw +-1.40,
  head_roll +-0.31 rad at step 2000 x 24. `walk_brain.py:80` `HEAD_RANGE = (1.10, 1.10, 1.40, 0.31)` clips to them
  (`walk_brain.py:385`).
- Reward: `head_pose_tracking` weight 2.0, std 0.5 (710-714) plus `head_pose_bias` on a 1 s EMA (741-745). The
  5yay13u4 note (729-740): a tight instantaneous head tolerance "taxes walking 0.77/step" and the policy "stood still".
- Runtime EMA: `walk_brain.py:81` `HEAD_ALPHA = 0.2`; `:517` `self.head_cmd += HEAD_ALPHA * (self.head_target(want) -
  self.head_cmd)` (walk/stand), `:502` the same when seated. Pollen's simulator does the same: `cmu/simulator/app/src/game/
  game.js:331` `const HEAD_ALPHA = 0.2;`, `:672` the EMA, `:1562-1565` stick deflection x HEAD_MAX as a step target.
  A 0.2-per-tick EMA at 50 Hz reaches 63 % of a step in 0.09 s and 95 % in 0.27 s.
- Seated: `microduck_sitstand_env_cfg.py:27` "Head commandable in BOTH postures (head_pose command + tracking, exactly
  ...)"; 148-157: "Real robot: an abrupt head move while seated tips it BACKWARD; it stays leaned ~30 deg in the sit
  pose and the neck servo overloads. Sim battery (...): fast head wiggles / pitch-down+yaw jumps tip 30-45 % of seated
  robots, none recover (...). Training had neither fast head commands (the head command only resamples every few s)
  nor any leaned-back seated state." Hardening events: `SEATED_HEAD_JERK_INTERVAL_S = (0.3, 0.8)` (163). The deployed
  `sitstand61.onnx` is Pollen's `BEST_alpha_sitstand.onnx` (`runtime-overlay/source-lock.json:33-34`);
  `microduck_rl/docs/sitstand_policy.md:9-10` says Pollen's current sitstand policy is the stage-2 resume `vfhxgrum`
  @ model_2250 with the seated fall-back hardening (validated on their robot 2026-10-01; `seated_head_jerk` 0.3-0.8 s,
  prob 0.2 at iter 1500, 0.4 at 2000, line 62). Whether the simulator's `BEST_alpha_sitstand.onnx` is that checkpoint is
  not verified here (no hash match done); the stage-1 policy "tips backward" on an abrupt seated head move.

So one step per quack, inside +-0.31 roll / +-1.40 yaw / +-1.10 pitch, with at least 2 s between quacks, is exactly the
command pattern the velocity policy saw in training; the runtime EMA makes the policy's input gentler than training.

### Sim comparison (as-built, CURRENT-STATE condition)

Method: `brain_sim_check.py` cannot vary the profile, and the repo must not be edited, so the wrapper
`<scratch>/quack_sim.py` imports `walk_wired`, `walk_brain`, `brain_sim_check` under `~/.venvs/microduck-dyn`,
monkeypatches `walk_wired.QUACK_HEAD_S`, `walk_wired.QUACK_HEAD_RAMP_S` and the copy `brain_sim_check.QUACK_HEAD_S`
(imported by value), replaces `brain_sim_check.Brain` by a subclass that records the measured head joint deltas and the
unrounded IMU-frame tilt every tick, then calls `brain_sim_check.main()`. `--ramp-s 0` makes `quack_head_share` a plain
step (share 1 from the second tick). Model: `--model asbuilt --manifest microduck_rl/cmu/model/manifests/plugged.json
--volt 7.0 --drop 0.04` (the values `robot_state_check.py --print-sim-args` prints), `--walk-s 0` (stand61 from 1 s),
`--quack-at 5.0 15.0 --sit-at 9.0` (seated from about 11.8 s), tilt style at its largest size (roll +0.18, yaw +0.25),
seeds 0-2. 13 runs of 2.9 s wall time each, one process at a time, `timeout 600`:

```
cd <scratch> && ~/.venvs/microduck-dyn/bin/python run_matrix.py        # A/B/C x seeds 0-2 + C_lookup_s0 + B_rapid_s0
~/.venvs/microduck-dyn/bin/python quack_sim.py --profile-s 0.6 --ramp-s 0.15 --out runs/P_s0.json --model asbuilt --manifest <plugged.json> --volt 7.0 --drop 0.04 --walk-s 0 --walk-at 4 --sit-at 9.0 --quack-at 5.0 15.0 --seed 0
~/.venvs/microduck-dyn/bin/python quack_sim.py --profile-s 0.6 --ramp-s 0.15 --out runs/P_walk61_s0.json --model asbuilt --manifest <plugged.json> --volt 7.0 --drop 0.04 --walk-s 3 --walk-at 4 --vx 0.25 --quack-at 9.5 --seed 0
```

Columns: posture; `model_peak` = brain_sim_check's `quack_peak_tilt` (trunk tilt in the model, absolute, window
qt..qt+S+1 s); `rise` = IMU-frame tilt peak minus the median of the 0.5 s before the quack (window to qt+S+2 s);
head peak = measured joint excursion from its pre-quack value, with its share of the command; `t_half` = s after the
quack at which the joint passed half the command; `t90` = s to 90 % of its own peak; `back` = s after the profile end
until the joint is within 0.03 rad of its pre-quack value. Seeds 0/1/2 shown as ranges.

A. current, S 1.6 s, ramp 0.5 s (seeds 0-2)
- stand61: model_peak 0.7-0.9 deg, rise -0.01..0.01 deg; roll 0.187-0.193 (104-107 %), t_half 0.48, t90 0.62;
  yaw 0.210-0.213 (84-85 %), t_half 0.58, t90 0.74; back 0.1-0.3 s; no fall.
- seated: model_peak 0.8-0.9, rise 0.04-0.10; roll 0.144-0.146 (80-81 %), t_half 0.46, t90 0.60-0.64;
  yaw 0.235-0.244 (94-98 %), t_half 0.42-0.44, t90 0.60-0.62; back 0.12-0.38 s; no fall.

B. short, S 0.5 s, ramp 0.15 s (seeds 0-2)
- stand61: model_peak 0.7-0.8, rise -0.01..0.01; roll 0.193-0.198 (107-110 %), t_half 0.30-0.32, t90 0.40;
  yaw 0.178-0.189 (71-75 %), t_half 0.38-0.40, t90 0.46; back 0.22-0.42 s; no fall.
- seated: model_peak 0.9, rise 0.02-0.05; roll 0.143 (79 %), t_half 0.26, t90 0.32; yaw 0.229-0.236 (91-95 %),
  t_half 0.26, t90 0.32; back 0.20-0.46 s; no fall.

C. plain step, S 0.5 s, ramp 0 (seeds 0-2)
- stand61: model_peak 0.7-0.8, rise -0.01..0.01; roll 0.196-0.199 (109-111 %), t_half 0.24-0.26, t90 0.32-0.36;
  yaw 0.207-0.215 (83-86 %), t_half 0.30-0.34, t90 0.46-0.48; back 0.28-0.48 s; no fall.
- seated: model_peak 0.8-0.9, rise 0.01-0.02; roll 0.144 (80 %), t_half 0.20, t90 0.24; yaw 0.241-0.245 (96-98 %),
  t_half 0.18, t90 0.26; back 0.26-0.54 s; no fall.

Extras (seed 0)
- C_lookup (step, pitch -0.30 + roll 0.10): stand61 model_peak 0.9, rise 0.12, pitch 0.296 (99 %) t_half 0.28;
  seated model_peak 1.3, rise 0.01, swing 0.54, pitch 0.294 (98 %) t_half 0.22; head_pitch did not return to within
  0.03 rad of its pre-quack value within 3 s (the policy's resting pitch moved slightly); no fall.
- B_rapid (short profile, quacks at 5.0/5.7 and 15.0/15.7 s): the second quack restarts the profile, so the head dips
  toward the start of the ramp and comes back; excursion relative to the already-raised pose 0.04-0.06 rad;
  rise 0.02-0.08 deg; no fall.
- P (proposed, S 0.6 s, ramp 0.15 s): stand61 model_peak 0.8, rise -0.01, roll 0.198 (110 %) t_half 0.30 t90 0.40,
  yaw 0.206 (82 %) t_half 0.38 t90 0.50; seated model_peak 0.9, rise 0.06, roll 0.143 (79 %) t_half 0.26, yaw 0.236
  (95 %) t_half 0.26 t90 0.32; no fall.
- P_walk61 (proposed profile on walk61 at rest, 2.5 s after a 3 s walk at 0.25 m/s): model_peak 2.1 (the walk61 rest
  posture), rise 0.06; roll 0.167 (93 %) t_half 0.32, yaw 0.168 (67 %) t_half 0.42 t90 0.48; no fall.

Run files: `<scratch>/runs/*.json` (summary per run), `*.rec.jsonl` (per-tick head and tilt), `run_matrix.py`.

Reading: in the as-built sim the profile length changes only how soon the head gets there. The trunk tilt rise is
at most 0.12 deg for every profile and posture (the 0.54 deg seated swing of the look-up step is still under the
1.7 deg quoted for the seated move in 82d5f87). The head reaches half of the commanded tilt at 0.48-0.58 s with the
current profile, 0.26-0.40 s with the 0.5-0.6 s ramped profiles, 0.18-0.34 s with the step. Reached fractions are
set by the policy and the KP 200 servo model, not by the profile (roll 104-111 %, yaw 71-86 % on stand61; roll 79-81 %,
yaw 91-98 % seated), except that the 0.5 s raised cosine on stand61 loses 10 % of yaw because its hold is only 0.2 s.

### Proposed constants

- `QUACK_HEAD_S = 0.6` (the longest call is 0.40 s; the head is at its peak at 0.4-0.5 s and back by about 1 s).
- `QUACK_HEAD_RAMP_S = 0.15` (keeps the seated case a ramp rather than a step, per Pollen's real-robot note; costs
  about 0.06 s against the step).
- Jaw (`QUACK_S` 0.4) and head keep starting in the same tick (already the case).
- A quack inside a running move holds the reached pose for another profile instead of restarting from share 0
  (`quack_head_t0 = max(quack_head_t0, now - QUACK_HEAD_RAMP_S)`), because the remote sends quacks 0.7-2.5 s apart.
- `QUACK_SIT_SCALE` stays 1.0 and the styles stay as they are (all inside the trained ranges).

Patch (unified diff, from a scratchpad copy; the repo is untouched, `git apply --check` passes):
`/private/tmp/claude-501/-Users-xiangzheng-code-robotics/74602e44-fa79-4564-a436-c7a3c8ce2ecd/scratchpad/patch/quack-constants.patch`.
`test_quack_head_tilt_is_a_smooth_bump` (`test_teleop_modes.py`) asserts no share step larger than 7 % per tick;
a 0.15 s ramp has a maximum step of about 21 % per tick, so that test's threshold must be updated with the constants.

## 3. The two-systems question

### What our stack already is

- The balance system is Pollen's policy: 61 inputs = 48 proprioception + `[twist(3), head_pose(4), body_pose(6)]`
  (`microduck_rl/AGENTS.md`, "Obs layout is 61D"), 14 joint goals out, including the four neck/head joints. It was
  rewarded for velocity tracking, air time, uprightness and `head_pose_tracking` at once, so its leg outputs are
  conditioned on the head command: when the command changes, the legs adjust in the same forward pass. That is a
  learned equivalent of the anticipatory postural adjustment in humans (Massion 1992, Prog. Neurobiol. 38:35-56:
  posture is adjusted before and during a voluntary movement to cancel the disturbance the movement will create).
- The task system is any program writing commands: `walk_wired.py`'s quack handler, `pickup.py` (head yaw/pitch to
  look at the object, D-015), the remote. The robot evidence that this works: D-015 amendment, stand61 with head commands
  "0.3/0.6/0.8 rad commanded -> 0.41/0.64/0.82 reached, tilt unchanged" (`DECISIONS.md:106`).
- The envelope: command ranges +-1.10/+-1.10/+-1.40/+-0.31 rad; one step every 2-5 s in training (0.3-0.8 s jerks
  only in the seated policy's hardening); velocity commands walk61 steps for (0.25 m/s and above, `ROBOT.md`
  "What walk61 can and cannot do"); and the modes that have their own policy because the velocity policy never
  saw them: groundpick (phase command), sitstand (posture flag in the vx slot), kick (0.5 s skill window).
  Outside the envelope the body_pose slots are zero-padded (weight 0 in the velocity env, 715-725), so "bow 20 deg"
  or "crouch 3 cm" has no command the walking policy understands.

### Literature (verified 2026-10-21)

- ExBody, Cheng et al. 2024, arXiv 2402.16796 (RSS 2024), https://arxiv.org/abs/2402.16796: upper body imitates
  human motion, legs track a root velocity command; one RL policy, two reward groups.
- OmniH2O, He et al. 2024, arXiv 2406.08858 (CoRL 2024), https://arxiv.org/abs/2406.08858: one whole-body tracking
  policy conditioned on kinematic keypoints (teacher-student).
- HumanPlus, Fu et al. 2024, arXiv 2406.10454 (CoRL 2024), https://arxiv.org/abs/2406.10454: a low-level whole-body
  shadowing policy trained on human motion data, driven by a pose estimate.
- Mobile-TeleVision, Lu et al. 2024, arXiv 2412.07773, https://arxiv.org/abs/2412.07773: upper body by inverse
  kinematics/retargeting, lower body by RL; the authors note the split limits agility.
- AMO, Li et al. 2025, arXiv 2505.03738 (RSS 2025), https://arxiv.org/abs/2505.03738: RL whole-body policy plus an
  adaptive motion optimizer that turns upper-body commands (torso height/orientation) into feasible targets.
- Classical task-priority whole-body control: Koolen et al. 2016, IJHR 13(1):1650007, doi 10.1142/S0219843616500079
  (IHMC Atlas, momentum-based QP); Kuindersma et al. 2016, Autonomous Robots 40:429-455,
  doi 10.1007/s10514-015-9479-3 (MIT Atlas, optimization-based planning/control). Balance (momentum, contacts) is a
  higher-priority task than limb motion in one QP solved every tick.
- Residual policies: Silver et al. 2018, arXiv 1812.06298; Johannink et al. 2019 (ICRA), arXiv 1812.03201: a learned
  correction on top of a base controller.

What applies at MicroDuck scale (15 XL330, A7Z, 50 Hz ONNX): the ExBody/Mobile-TeleVision structure is exactly our
structure (balance policy + task commands), already shipped by Pollen. A task-priority QP needs a dynamics model and
torque or velocity control that XL330 position servos at KP 200 with a 0.05 rad load deadband (`ROBOT.md` "Known
mechanics") do not offer, and a 10 ms QP on the A7Z is unproven; it would also replace a policy that works. A residual
policy would need training compute and a reward audit for no demonstrated gap.

### Do we need a new quack policy?

- Head moves inside the envelope (tilt, look up, look at the object): **no**. Change the command profile (section 2).
- Motions outside it (a deep nuzzle that pitches the trunk, a bow, a head move while stepping, a seated head wiggle
  faster than every 2 s): **yes, as a registered fine-tune delta**, not a separate hand-written policy. The delta
  would be a key in `finetune_worker.py:138` `DELTAS = {"default": ..., "staged": ..., "lowcmd": ...}` with a wider or
  faster `head_pose` command distribution (e.g. `resampling_time_range` (0.5, 5.0) with the velocity env's
  `seated_head_jerk`-style event, or a non-zero `body_pose` range and weight for a bow), under the D-016 gates
  (`DECISIONS.md:109-114`): `finetune.py::run` refuses an unregistered delta (`finetune.py:180`) and one without a
  PASS in `reward-audit.json` (stand61 must collect at most the audited fraction of walk61's reward per second in
  that env, threshold calibrated so the walk61 env passes and the ft1 env fails); the worker's tracking-error guard
  stops a run that drifts to standing. Expected risk, from the 5yay13u4 note: a faster head command distribution
  makes the head term harder, which pushes the optimum toward standing still; the audit margin must be re-measured.
  Not started: no training without Shawn's go (D-016, no-MacBook-training rule).

## 4. Action list

1. Sim comparison: done above (13 runs, `<scratch>/runs/`). Nothing to rerun unless the constants differ from P.
2. Constants: apply `patch/quack-constants.patch` (S 0.6, ramp 0.15, hold-on-repeat), update the 7 %-per-tick
   assertion in `test_teleop_modes.py::test_quack_head_tilt_is_a_smooth_bump` to the new ramp (about 21 %), run
   `test_teleop_modes.py`, redeploy with `install_teleop.sh` (A7Z online). Owner: the session that owns walk_wired.
3. Robot acceptance (Shawn guarding, robot standing on stand61 at zero command, then seated):
   - 10 quacks on stand61 at least 1 s apart and 10 seated, the remote's quack key, with `walk_wired --log`.
   - Pass when: no guard trip (`STOP ->` lines) and no fall; every stdout quack line names a head move; in the log
     the commanded head joint reaches at least 60 % of its delta within 0.5 s of the quack (sim: roll 79-110 % at
     0.26-0.38 s); peak tilt within 3 deg of the pre-quack rest tilt on stand61 and within 3 deg seated (sim rise
     <= 0.12 deg; the real stand61 run on 10/16 showed "tilt unchanged"); seated: no backward lean that persists
     (Pollen's failure mode) and no neck overload (`hw_faults` empty).
   - The seated block is the one the sim cannot vouch for; if a seated quack leans the duck back, set
     `QUACK_SIT_SCALE` 0.5 before touching the profile.
4. Only if a motion outside the envelope is wanted: register the delta, run `finetune.py::audit` for it, read the
   margin, and ask Shawn for the Modal cap before `run`.

## Unverified / open

- The 2026-10-20 tip-over in open-loop stand: no log on this Mac holds it; cause (head move vs the KP 400 self-tip)
  unknown.
- Pollen's seated backward tip is not reproduced by the as-built sim (no tilt rise even for a step); the sim is not
  evidence for the seated step on the real robot, hence the kept ramp and the seated acceptance block.
- Whether the deployed `sitstand61.onnx` is Pollen's hardened stage-2 checkpoint (vfhxgrum@2250) or the stage-1 one
  that tipped on abrupt seated head moves: not hash-matched here.
- Pollen's robotd head low-pass (0.5 on targets, memory `microduck-official-robotd-gaps`, source `control.rs:725-735`)
  could not be re-read: `/private/tmp/pollen_md/microduck` is gone. Our runtime applies the 0.2 EMA on the command,
  as the public simulator does, not a target low-pass.
- Real servo response at KP 200 under load differs from BAM (SIM2REAL.md "The servos move less than commanded"), so the
  real t_half may be longer than the sim's 0.26-0.38 s; the 10/16 head-command run reached 0.41 for 0.3 commanded
  (overshoot), which argues the head joints are not the deadband-limited ones.
- The IMU-frame tilt in the wrapper carries the model's IMU mount offset (about 3.3 deg at rest on stand61); only
  differences (rise, swing) are used. Absolute trunk tilt comes from brain_sim_check's own `quack_peak_tilt`.
- Massion 1992 and the Koolen/Kuindersma papers were verified by search results and DOIs, not by reading the papers.
