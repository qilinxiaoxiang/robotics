# History-input universal policy (plan, NOT approved, NOT launched)

Problem: FP-R3, one stand/walk policy for 0 to about 1 kg of flight pack. Run A final (`ckpt/uni_a/walk61.onnx`, one
frame, 61 inputs) fails `out/accept_uni_a.json` on comx+10 (stand 5/20 and walk 19/20 falls, at about 0.9 s, torque
saturated from the first tick), the 0.5 N s walking shove (11/20), walk torque p99 0.53 (limit 0.48) and step width
123 mm (limit 105). universal3 (kernel microduck-fk-uni3, still one frame) widens the COM and push ranges. This plan
prepares the next step if universal3 is not enough: an actor that sees its own recent past, built the way the 16-831
course teaches (a privileged teacher distilled into a history student), with the runtime change it needs.

Recommendation in short (revised 2026-11-12 after an outside review): wait for universal3's checkpoints and run the
decision rule in section 6. If the target cases still fail, run design A once with a fixed budget against a
one-frame control, to measure what history alone buys; the course's teacher-student pair (design B: a PPO teacher
that sees the true load, then a DAgger student that sees the 61 inputs plus 0.5 s of its own proprioception) follows
only on evidence that the extra information helps. Not established: that history fixes the comx+10 falls. The student's observation, ONNX contract,
warm start and evaluator support are implemented and smoke-tested now (delta `universal3h`, which also runs alone as
the one-stage design A); the teacher delta and the distillation worker are not written yet.

## 1. What the course teaches (16-831 Introduction to Robot Learning, Guanya Shi)

Sources read: `Lecture_5` (MDP and imitation learning) p16-42, `Lecture_6-Imitation_Learning.pdf` p7-24 and its
explained page, `Lecture_11-Advanced_RL_Algorithms_Part_1.pdf` p22-38 and its explained page, transcripts
2026-09-08 lecture-5, 2026-09-10 lecture-6, 2026-09-29 lecture-11 and 2026-10-01 lecture-12 under `05-transcripts`.

Behavior cloning and why it breaks. Lecture 5 p16 defines BC as supervised learning of pi_theta(a_t | o_t) on expert
pairs. p19-22: it is not standard supervised learning, because the policy's own actions choose the next states, so
the i.i.d. assumption fails and a small mistake leads into states the expert never visited, where mistakes compound
(the "cliff walking" picture). p26-27 name the fixes: better data collection, and DAgger.

DAgger. Lecture 5 p32-41 (Ross 2011): run the current policy pi_n, ask the expert for the right action in every state
pi_n visited, aggregate those labels into the data set, retrain, repeat. p41 shows BC beside DAgger; p42 states that
DAgger is online learning with a regret guarantee, at the price of querying the expert throughout. In class
(lecture-5 01:08:23) the key idea is "interaction"; at 01:13:16 BC is "a one-shot version of DAgger"; at
01:15:09-01:15:32 the guarantee and its cost; lecture-6 00:01:32 recaps that DAgger is "in general, better than BC".
The reason it is preferred: its training states come from the student's own distribution, the states it will meet.

Privileged teacher, history student. Lecture 6 p13: a teacher pi_p(a_t | p_t) acts on privileged information p_t
that only the simulator has; the student pi_theta(a_t | o_t) acts on what the robot senses. p15 says why it works:
the teacher is a white box that can be queried anywhere (so DAgger is easy, transcript 00:24:05-00:24:18), its
optimization is easier, and it gives invariance and easy augmentation. p7-8: the student uses history,
pi_theta(a_t | o_1..o_t), with a fully connected or a time-series model. p16-18 (Lee et al. 2020, legged locomotion):
p_t is contact, terrain, friction and disturbance, the teacher is trained with PPO, the student sees proprioceptive
history. Transcript 00:28:38-00:29:05 (privileged information, PPO teacher), 00:29:49 ("the students need ... a
history"), 00:30:01-00:30:35 (PPO teacher, then DAgger with the loss in action space), 00:30:40-00:31:04 (locomotion
policies run at about 50 Hz; action chunking is not the norm there), 00:26:08 (most locomotion demos use this
pipeline). 00:31:30-00:31:45: the privileged information must be identifiable from the student's observations,
otherwise a teacher-student gap remains. Lecture 11 p32-33 repeats the recipe: teacher trained by RL (PPO, p22-27,
clip epsilon 0.2, the go-to algorithm for locomotion p24-26), distilled to the student by DAgger.

RMA as the latent variant. Lecture 6 p20 and transcript 00:33:27-00:35:23: RMA's phase 1 trains the base policy with
an encoded latent z of the environment; phase 2 freezes and shares that policy and regresses z from history, which
the lecture calls latent system identification.

Asymmetric actor-critic. Lecture 11 p35-38: only the critic gets privileged state ("value is only useful in
training", "especially useful for sim2real RL", ASAP as the example). Lecture-12 00:59:51-01:00:40 recaps
teacher-student as "really important", and 01:02:02-01:02:17 calls the asymmetric actor-critic "equivalent in a way,
but ... more efficient because you don't even need two-stage". Lecture 6 p24 (FALCON) pairs the asymmetric critic
with an actor that sees the current proprioception plus a short history. Run A and universal3 are already the
one-stage asymmetric form: the actor sees 61 inputs, the critic 80 including payload kg and loaded trunk COM.

## 2. Published recipes (pages opened 2026-11-12)

- RMA (https://arxiv.org/abs/2107.04034, html v1): state x_t 30-D plus a_{t-1} 12-D; environment vector e_t 17-D
  encoded to an 8-D z_t by an MLP [256, 128]; the adaptation module reads the last 50 steps (0.5 s at 100 Hz), an MLP
  embedding to 32-D and a three-layer 1-D CNN, and runs at 10 Hz beside a 100 Hz base policy (3 layers, 128 units).
  Training ranges: payload 0-6 kg, COM +-0.15 m. Table II success: domain randomization alone 62.4 %, direct system
  identification 56.5 %, RMA without adaptation 52.1 %, RMA 73.5 %, privileged expert 76.2 %.
- Walk These Ways (https://github.com/Improbable-AI/walk-these-ways, `scripts/train.py`, `go1_config.py`,
  `ppo_cse/actor_critic.py`): 30 stacked observations at 50 Hz (0.6 s), 70 per frame; an adaptation MLP [256, 128]
  regresses 2 privileged values (friction, restitution) and its estimate is concatenated to the actor input, trained
  concurrently with PPO (one stage). Added mass -1 to 3 kg; COM randomization off in train.py.
- legged_gym (`legged_gym/envs/base/legged_robot_config.py`): single frame, actor [512, 256, 128]; an LSTM option
  (512 units, 1 layer) is present but commented out. Added mass +-1 kg.
- Humanoid-Gym (`humanoid/envs/custom/humanoid_config.py`): 15 stacked frames at 100 Hz (0.15 s) of 47 values; the
  critic stacks 3 frames. Added mass +-5 kg, pushes up to 0.2 m/s every 4 s.
- Disney BDX (https://arxiv.org/abs/2501.05204): no history beyond the two previous actions a_{t-1}, a_{t-2}, 50 Hz;
  the critic gets noise-free state plus friction; mass properties randomized, disturbance forces applied.
- Berkeley Humanoid (https://arxiv.org/abs/2407.21781): immediate state only, explicitly without a history or
  teacher-student; actor [512, 256, 128] at 50 Hz.
- Open Duck Mini v2 (`apirrone/Open_Duck_Playground`, `open_duck_mini_v2/joystick.py`, `common/randomize.py`): one
  frame (gyro, accelerometer, command, joints, velocities, last 3 actions, motor targets, contacts, phase); its IMU
  history only simulates delay. Torso COM +-0.05 m, torso mass +-0.1 kg.

Read together: the small bipeds walk with one frame; history appears where the load or terrain varies a lot (RMA,
Walk These Ways), always at about 0.5 s, and RMA's own table puts the gain of adaptation over randomization alone at
11 points.

## 3. Candidate designs

Shared student contract (implemented, used by A and B). Actor input 61 + 25 x 48 = 1261: the usual 61, then the last
25 frames (0.5 s at 50 Hz, oldest first, current last) of the first 48 inputs (gyro 3, gravity 3, joint angles 14,
joint velocities 14, previous action 14). The frames are the actor's own noisy, delayed inputs. After a reset the
history is back-filled with the first frame. Critic unchanged (80). ONNX: inputs `obs [1, 61]` and `hist_in
[1, 1200]`, outputs `actions [1, 14]` and `hist_out [1, 1200]`; the caller feeds `hist_out` back and passes zeros
when the policy (re)starts, which the graph back-fills like the training reset. The first input and the
`observation_names` metadata are unchanged, so the 61-input checks in walk_brain hold. Warm start: uni_a (or
universal3's best) with zero weights on the 1200 history inputs and each history slot's normalizer copied from the
matching current slot, so iteration 0 equals the start policy.

Runtime change (the same for A, B and C). `guide/firmware/mac/walk_brain.py`, about 15-20 lines: in `Brain.__init__`
(line 432 asserts a [1, 61] first input), accept a second state input and allocate a zero state per model file; at
the call site (line 947, `sess.run(None, {sess.get_inputs()[0].name: obs[None]})`) feed the state and keep
`hist_out`; zero the state when the policy is (re)entered, and share it between walk and stand when they are the same
file. Also `cmu/mac/walk_brain.py` through `cmu/sync_from_robotics.py`, `scripts/infer_policy.py` (it reads only the
first input), and the publish shape gate (`src/mjlab_microduck/publish/manifest.py`), which runs one input. Stand,
groundpick and seepick stay 61-input files and pass through unchanged, so the hot-swap contract survives. Cost per
call, single thread on the Mac mini: 6.5 us p50 for uni_a against 16.6 us for the history ONNX (2.5x); this says
nothing about the A7Z. On the A7Z, CURRENT-STATE.json holds two loop figures from different conditions. The 23.6 ms
p50 / 24.6 ms p90 brain loop (about 42 ticks/s) in `a7z_closed_head_thermal_and_resets` was measured 2026-10-22 with
the board inside the closed V1.17 head, both CPU clusters throttled to 416 MHz, on a bench supply; the acceptance it
was judged against is a p90 of 18 ms or less and 49 ticks/s or more after a one-hour soak. The board now sits on the
V1.35 saddle on the Radxa 6530B heatsink, saddle lid not fitted (`parts_a7z_extensions`, recorded as inferred from
Shawn's 2026-10-26 report), and the newest loop record is 46.4-48.8 ticks/s (20.5-21.6 ms per tick) over nine brain
logs of 2026-11-02 to 11-06 (`imu_rate_hz` source), with no p90 and no separate policy cost. Before any deploy, measure
in that installation: the full control loop (tick rate, p50 and p90) with the two-input ONNX for walk and stand, the
switching between stand and walk, and that the history state is zeroed on every policy re-entry.

### Design A: stacked history, one stage (cheapest; implemented as delta `universal3h`)
- Actor: the shared 1261 inputs. Critic: 80 (payload kg, loaded trunk COM xyz). This is lecture 11's asymmetric
  actor-critic with lecture 6 p24's history actor.
- Training: PPO, universal3's env and reward mods unchanged (`UNIVERSAL3_MODS`, audited `rm_universal3.json`), from
  universal3's best (or uni_a). RL has to discover how to use the history weights from reward alone.
- GPU: about one universal3 run, 2000 iterations at about 0.19 it/s, 2.9 h on a T4 (inference: the actor is about 4x
  the MACs of the 61-input MLP, 0.81 M against 0.2 M, small against the sim; the CPU smoke ran 3 iterations in 10.5 s
  against 6.3 s for universal3 at 64 envs). The first 50 iterations' rate decides the --max-hours cap.
- Risk: lowest code risk; the policy may simply leave the history weights near zero.

### Design B: teacher-student distillation, as taught (recommended if history is needed)
- Teacher pi_p(a_t | p_t): the 61 inputs plus privileged p_t = payload kg, loaded trunk COM x, y, z (the critic's
  payload term, 4 values) and trunk linear velocity (3, which carries the shove), 68 inputs. Trained by PPO (lecture
  11 p33) on universal3's env and reward, warm-started from universal3's best with zero weights on the 7 new
  columns. GPU: about one universal3 run, 2.9 h T4.
- The teacher is a gate on distilling this teacher, not a bound on the history route. One trained teacher can fail
  for reasons of budget, reward, start point or coverage, so a failing teacher does not show that history cannot
  work; a passing teacher shows that the extra information can help, not that a student can infer it from its
  sensors. Rule: if the teacher does not improve the target cases (comx+10, walking shove, torque) over the
  one-frame policy from the same start with the same budget, it is not distilled and its failure is diagnosed first.
- The teacher's 7 extra inputs mix two kinds of information (load: kg and COM; motion: trunk linear velocity). Two
  teachers are compared when the teacher stage is run: load only (4 inputs) and load plus velocity (7), so a gain is
  attributed to the right one.
- Student pi_theta(a_t | o_{t-24..t}): the shared 1261-input contract above. Trained by DAgger in action space
  (lecture 6 transcript 00:30:15, lecture 11 p33): the student drives the sim, the teacher labels every visited state,
  MSE loss on actions. rsl_rl 5.0.1 ships this as `algorithms/distillation.py` (student acts, teacher labels) with
  `runners/distillation_runner.py`. Warm start: uni3 best padded, so the student starts as a working walker and its
  first rollouts are not falls. Budget: 500-1000 distillation iterations (about 50-100 M sim steps at 4096 envs x 24
  steps), GPU because the sim is the cost, about 1-1.5 h on a T4 (inference: no critic, sim-bound). Optional short
  PPO fine-tune of the student afterwards (lecture 5 transcript 01:15:47: in practice people fine-tune).
- What runs on the robot: only the student, the same two-input ONNX as design A, with the runtime change above.
- Where it follows the lecture and where it follows RMA:
  - Loss in action space with DAgger (lecture), not RMA's latent regression: the teacher is a warm-started 61-input
    MLP with raw privileged columns and no encoder, so there is no latent z to regress, and action-space DAgger is what
    rsl_rl implements. RMA's phase 1 would need an encoder and a base policy retrained from scratch around it.
  - Student acts during collection (DAgger, lecture 5 p32-41), not offline BC on teacher rollouts: the comx+10 falls
    are exactly the compounding-error states BC never sees.
  - Fully connected stacked history (lecture 6 p7-8 allows either), not RMA's 1-D CNN: an MLP keeps the warm start
    from the existing walker; RMA starts from nothing.
  - History length 0.5 s, as RMA (50 steps at 100 Hz) and close to Walk These Ways (0.6 s).
  - Privileged set follows RMA's e_t in kind (mass, COM) plus the push state that Lee et al. list as disturbance.
  - Direct estimation of e_t and feeding it to the policy is not used: RMA's Table II puts system identification at
    56.5 % against 73.5 %.
- New code needed (not written): a teacher delta (append payload_obs and trunk linear velocity to the actor group;
  the new columns need real normalizer statistics, which the history warm start does not need), and a distillation
  worker in `cmu/finetune/flight/` around rsl_rl's Distillation with the teacher loaded from its ONNX, the student from
  `history.load_padded`, the export through `history.HistoryOnnx`, and its own task-metric stop.

### Design C: recurrent actor (GRU/LSTM)
- Actor: 61 inputs and a hidden state (for example 1 layer, 256 units); ONNX state in/out like A and B, so the same
  runtime change. Critic 80.
- No warm start: a recurrent actor cannot load the 61-input MLP, so it trains from scratch with BPTT; the last
  from-scratch pair ran its whole 10 h cap standing still (RUNLOG 2026-11-12). Highest GPU cost (inference: several
  universal runs) and highest risk. Rejected for this round.

### Comparison
GPU hours per single run: A about 3 h, B about 4-4.5 h (teacher 2.9 h plus student 1-1.5 h), C several runs; the
counts with controls and both teachers are in section 6. Runtime change: the
same for all three (the two-input stateful ONNX). Risk: A may not use its history; B has a stage-1 gate that tells
whether load knowledge helps at all before the student is trained, and the student gets a supervised target for
every state instead of a reward signal; C has no warm start. Kaggle: 26.75 of 30 h used at 03:30 on 2026-11-12,
refresh 2026-11-14 00:00, so B fits one weekly quota only after universal3 is done.

## 4. The timing question: does a history estimator have time before the fall?

Run A falls about 0.9 s after a comx+10 start, with torque saturated from the first tick. A 0.5 s history is full at
0.5 s. The probe below asks how much of the load a linear readout can extract from the actor's inputs, early and late.

Method (`cmu/finetune/flight/history_probe.py`, run by `zsh train/mini_train_smoke.sh probe 1024 200` on the Mac mini
CPU; `out/history_probe.json`, `logs/history_probe.log`). 1024 envs of the universal3h env with universal3's COM and
payload randomization, uni_a driving at its own commands for 200 steps (4 s). Targets: the whole-robot COM x offset
that the payload event drew for that env and episode (range -11.9 to +12.0 mm, sd 6.8 mm), and the payload mass (sd
290 g). Features: the same 61 current inputs with and without the 25-frame history (61 against 1261). Time is each
env's own frames since its last reset (18 envs reset during the probe and restart their clock); the pooled fit uses
only frames whose whole history is real (0.5 s or more since reset), every 5th step. Ridge regression, lambda chosen
on an inner split of the 768 training envs, scores on the 256 held-out envs (about 1030 samples per time bin over
both sets, of which 47 held-out samples sit at +8 mm or more).

COM x offset, held-out RMSE (and at offsets of +8 mm or more: mean signed error, RMSE), 61 inputs against 1261:
- 0.1 s: 2.6 mm (-1.5, 3.0) against 2.2 mm (-1.0, 2.5); R^2 0.85 against 0.89.
- 0.2 s: 2.2 mm (-0.9, 2.3) against 2.0 mm (-0.8, 2.1); R^2 0.90 against 0.91.
- 0.3 s: 2.4 mm (-1.4, 3.0) against 1.9 mm (-0.7, 2.0).
- 0.5 s: 2.9 mm (-1.8, 3.7) against 2.0 mm (-0.7, 2.1).
- 0.8 s: 3.6 mm (-3.3, 4.6) against 2.5 mm (-1.6, 3.1).
- 1.0 s: 3.6 mm (-3.4, 4.3) against 3.0 mm (-2.0, 3.6).
- Pooled, 0.5 s and later: 3.8 mm (-3.5, 4.4), R^2 0.69, against 3.3 mm (-2.6, 3.9), R^2 0.76.

Payload mass, held-out RMSE, 61 inputs against 1261: 183 g against 138 g at 0.1 s, 155 against 109 at 0.2 s, 221
against 107 at 0.3 s, 239 against 115 at 0.5 s, 248 against 208 at 0.8 s, 240 against 219 at 1.0 s; pooled 266 g
(R^2 0.16) against 205 g (R^2 0.50).

What this supports, and no more:
- A linear readout of the 61 current inputs already locates the COM offset to about 2-3 mm in the first 0.1-0.3 s,
  before the 0.9 s fall; the history lowers that error by 0.2-0.9 mm in every bin and roughly halves the bias at the
  +10 mm end. At the forward end both readouts underestimate the offset, the 61-input one by 1-3.5 mm.
- The readout is easiest early, while the robot settles from the reset pose, and worse once the gait runs.
- The history helps the mass much more than the COM (for example 107 against 221 g at 0.3 s).
- It does not show what the policy uses, nor whether 2-4 mm of COM error is small enough to avoid the fall. It
  therefore does not establish whether the comx+10 falls are a coverage problem or an information problem. fq2 1999
  holding comx+10 with 0 falls on one frame is an existence proof that one frame can suffice for that case, nothing
  more. The universal3 checkpoints and the gates in section 6 decide it.
- Limits: linear readout under one driving policy (a trained network may extract more, or use less); one seed; per
  bin only 47 held-out samples at the forward end.

## 5. Incentive audit and task-metric stop

The reward is universal3's, unchanged, so the degenerate pricing is the same as the audited universal3 gate (18 cases
PASS, worst 0.718, stand, step in place and lean among them). The history columns only change what the actor sees.
Before a launch the coordinator records the gate for the new delta name, one case per job:

    python3 cmu/finetune/flight/flight_audit.py --jobs universal3h --cases <case> --loads <load> \
      --reward-mods "$(cat ../extensions/flight-20261110/train/rm_universal3.json)"

and `train/audit_gate.py` must pass for `universal3h` (the Kaggle launcher refuses otherwise; it now checks
`universal3h`'s mods against `rm_universal3.json`). One case was run to show the audit works in the history env
(the degenerate and intended policies load padded, so they act as in the one-frame env): shuffle at batteries out,
128 envs, 400 steps, `out/audit3_u3h_shuffle_nobatt.json`, reward ratio 0.736, PASS, against 0.718 for universal3
(`out/audit3_u3e_shuffle_nobatt.json`; the intended walker's falls per env-minute 0.29 against 0.23, so the rollouts
differ slightly, which is not explained yet). Stop: the worker's `--track-guard 2.0` on velocity tracking, the
launcher refuses a job without it. For B, the teacher reuses this audit and stop; the distillation worker needs its
own stop on a task metric (student falls and tracking against the teacher's in the same envs), not on the loss.

Acceptance: `train/accept_universal.py run <ckpt> && train/accept_universal.py score <ckpt>` unchanged. The evaluator
now runs two-input ONNX files: `train/flight_eval.py install_stateful_policies` wraps a session with a state input,
carries `hist_out` between ticks and zeros it when the policy is re-entered; 61-input dirs are untouched (shown below).

## 6. Decision rule from universal3

For each universal3 checkpoint (iterations 250 to 2000 and best), run the comx+10 walk and stand cases and the walking
shove through accept_universal.py. History is not needed if comx+10 walk falls drop to fq2 1999's count (0) and the
shove to its line without the nominal or no-pack lines getting worse. If comx+10 falls stay flat across checkpoints
although forward-COM coverage rose from 1.2 % to 8 % of resets, or trade against the nominal or no-pack lines, the
next run is design A with a fixed budget against a one-frame control of the same length from the same start
checkpoint and seed. A differs from the control in more than the time information (more parameters, a separate
step scale), so a better A shows that the whole change helps, not yet that the past is used. The picked A checkpoint
therefore gets one more evaluation: normal history against the current frame repeated into all 25 slots; only a
clear loss with repeated frames shows the policy uses the past.

After A: if A meets the acceptance, stop there; B is not run. If a gap worth closing remains, the teacher stage of B
is run, and the student is distilled only if a teacher clearly beats the one-frame control on that gap. If the
torque or step-width lines are what remains, the choice between history and the constraint route of section 7 is
made from the A-against-control result on those lines (history may help the load-dependent torque; automatic
weights are not guaranteed to meet both lines either), not fixed in advance.

Budget, counted per run (T4 hours, estimates from the universal3 rate, not measured for history): A is two runs,
history and the one-frame control, about 3 h each, about 6 h if not paired; paired on the two GPUs of one Kaggle
session they count once, about 3 h of quota. B's teacher stage is two teachers (load only, load plus velocity),
about 3 h paired; the student about 1 to 1.5 h. Whole path A then B: about 7 to 7.5 h of quota paired, about 13 h
of GPU time. The short scale check before A is extra (under 1 h).

Gates are per scenario, never a sum: comx+10 (stand, walk), comx-10, mass +10 %, standing and walking shove,
landing, nominal and no-pack each have their own line against the reference (`accept_universal.py`, per-case lines
added 2026-11-12; the old 14-case sum let a gain in one case hide a loss in another). Two seed sets, implemented in
`accept_universal.py --set`: `dev` (seeds 0 to 19, files `ua_*`) for picking checkpoints, `final` (seeds 1000 to
1099, 100 episodes, files `uaf_*`, score in `out/accept_<dir>_final.json`) for the verdict on a picked one. The sets
have separate result files, so a final run is never skipped because a dev file exists, and `score` rejects a file
whose seed list or episode count does not match its set. Twenty episodes without a fall bound the fall rate only
below about 14 % (one-sided 95 %), so dev is a screen.

Warm start is not a guarantee during training: iteration 0 equals the start policy, but the 3-iteration smoke policy
fell at 3.0 s (section 8 has the controlled check). Every run keeps the start
checkpoint as a control in the same evaluation, and a checkpoint is chosen on falls, speed and torque; moved history
weights or a falling imitation loss are not evidence of success.

## 7. Torque and step width as constraints (24-784 M3-1, optional)

Lecture M3-1 (Ding Zhao; PDF text layer and the explained page read; no class recording exists) p19-22: maximise
J(pi) subject to J_C(pi) <= d through the Lagrangian L(pi, lambda) = J(pi) - lambda (J_C(pi) - d); PPO-Lagrangian
alternates a PPO step at fixed lambda with lambda <- max(0, lambda + eta (J_C - d)) (p20-22). p22-24: lambda goes to 0
while the constraint holds and grows without bound while it fails, the step size is hard to choose, and the update
is an integral controller, so it oscillates with a phase lag behind J_C (p23). p25-26: the PID Lagrangian (Stooke,
Achiam, Abbeel, ICML 2020) adds proportional and derivative terms and trains more stably. p27: little guarantee,
on-policy only.

Mapping: two constraints, walk leg torque (the acceptance line is a p99 of 0.48 N m; an expectation-type surrogate is
the fraction of ticks above 0.48, or the mean hinge above 0.45) and step width (mean stance width at touchdown, limit
105 mm). Each gets its own lambda that replaces today's hand-set weight (torque hinge at 0.45, weight -12). Extra work
compared with hand-set weights: a per-iteration measurement of both costs inside the training env (step width needs
foot positions at touchdown, which only the evaluator computes today), a lambda update in the worker's iteration hook
written through the reward manager's term cfg (managers deepcopy their cfg, so env.cfg writes are no-ops), a PI or PID
variant against the p23 oscillation, an upper bound on lambda, and an incentive audit at that bound (the audit prices
fixed weights). Not proposed for this round; it is the route if universal3 still misses only these two lines.

## 8. What was built and checked (2026-11-12, Mac mini CPU, no GPU, nothing launched)

Code (team repo `microduck_rl`): `cmu/finetune/flight/history.py` (history observation, warm start, two-input export,
stateful wrapper), `history_smoke.py`, delta `universal3h` and the 61-or-history loaders in `flight_worker.py`,
`universal3h` in `flight_audit.py` and in the launcher's audit check in `kaggle_flight.py`. Here:
`flight_eval.py` (stateful policies), `mini_train_smoke.sh history` and `probe`, `fall_check.sh`; team repo also
`history_probe.py` and `smoke_fall_check.py`.

Smoke (`zsh train/mini_train_smoke.sh history 3 256 150`; `logs/history_smoke.log`, `out/history_smoke.json`):
actor obs 1261, critic 80; history columns equal the last 25 frames (max |diff| 0 over 138 envs without an episode
end), reset back-fills, other envs shift by one frame; padded actor against uni_a on live obs 1.1e-6; iteration-0
export has inputs obs [1, 61] and hist_in [1, 1200], outputs actions and hist_out, unchanged observation_names plus
history_frames 25, history_inputs 48, and equals uni_a (0.0); 3 PPO iterations in 23.3 s at 256 envs; trained export
against the torch actor over 60 steps with a reset 6.0e-7; the history weights moved off zero (|sum| 1274).

Evaluator (`train/flight_eval.py`, nominal manifest, walk, `--stand-s 0`, 2 episodes): the zero-history export
(`ckpt/hist_m0`) and uni_a give identical results (0 falls, 0.1732 m/s median, max tilt 16.7) in
`eval/eqcheck_s0_uni_a.json` and `eval/eqcheck_s0_hist_m0.json`; the 3-iteration smoke policy (`ckpt/hist_smoke`)
loads and runs, and falls at 3.0 s (`eval/eqcheck_s0_hist_smoke.json`).

Why the 3-iteration policy falls although iteration 0 equals uni_a (controlled check,
`cmu/finetune/flight/smoke_fall_check.py`, run on the Mac mini CPU by `zsh train/fall_check.sh "<arm>|<flags>" ...`). Every arm starts from uni_a,
64 envs, 3 PPO iterations, then the same evaluation (nominal walk, 4 episodes, `--stand-s 0`):
`out/fallcheck_<arm>.json` (lr trace, first-layer weight change) and `eval/fallcheck_<arm>.json`.
- Smoke settings (no critic warm-up, cfg lr 1e-3 adaptive): history actor 4 of 4 falls (0.9-2.6 s); history columns
  frozen 4 of 4 (3.0 s); the one-frame universal3 actor 4 of 4 (4.9-13.4 s). In these settings any actor falls, so
  the smoke fall alone says nothing about history.
- Learning rate alone: history actor with lr clamped to 3e-4, no warm-up, 3 of 4 falls; with 1e-5, 0 of 4.
- Launch settings (100 critic-only warm-up iterations with the actor frozen, lr clamped to 3e-4, as `--warmup-iters
  100 --max-lr 0.0003`): one-frame actor 1 of 4 falls (10.9 s); history actor 4 of 4 (3.3-6.1 s); history actor with
  its 1200 history columns frozen 0 of 4; history actor with the optimizer step on those columns scaled by 0.04, 0 of
  4 (0.170 m/s).
- What this supports: the intervention result. Freezing the history columns or scaling their step removes the fall
  under the launch settings; the warm-up and the lr clamp alone do not. So the update of the history branch is what
  breaks the walker in this small test. The weight-change totals (279 summed |dW| on the history block against 14 on
  the 61 current inputs) are not evidence of an abnormal update by themselves: there are 1200 history columns
  against 61, a ratio of 19.7, and the change ratio is 19.3, so the per-column change is the same.
- Consequence for a launch of universal3h or the design B student: the worker needs a separate step scale for the
  history columns. 0.04 is one candidate that kept the walker over 3 iterations; it is not shown that the history
  branch still learns at that scale. Before a full run, a short check (a few hundred iterations) compares two or
  three scales on both questions: does walking survive, and does the policy come to use the history (the
  repeated-frame test in section 6). Not done.
- Early checkpoints: a history run saves at iterations 110, 125, 150 and 200 as well as every 250 (the first is 10
  iterations after the warm-up ends), and each is evaluated on nominal walk and no-pack walk against the model_0
  export before the run is trusted further. On Kaggle the outputs appear only when the kernel ends, so the first
  history run is a short kernel that stops at iteration 250. The evidence here is 64 envs, 4 episodes, one seed,
  CPU; that it carries over to 4096 envs is inference.

Not done: the per-column history step scale in the worker, the teacher delta and the distillation worker (design B),
the walk_brain runtime change, the A7Z loop measurement, the other 17 universal3h audit cases and their gate record,
and any training run.
