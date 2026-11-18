# Teacher-student round: one recurrent motor policy for every load (2026-11-18)

Problem: one fast-system motor policy (requirement FP-R3 plus head-follow). Approval: Shawn, 2026-11-18, "可以开跑呗".
Limits: Kaggle free GPU quota only, at most 10 quota-hours for the round; simulation only, nothing deployed, nothing
pushed. Bend, squat, kick, pick and sit-stand are not in this round.

Design changes from Shawn on 2026-11-18, both applied before any long run:
- the student is a new recurrent network trained from scratch, not the history-window MLP ("我们这次不是要训练一个
  全新架构的模型吗？就是单帧用CNN或者ViT，时序用Mamba这种递归。之前的模型还有意义吗？");
- the student's memory must not be limited to the 24-step PPO rollout (0.48 s): backpropagation runs over 100 ticks
  (2 s), the state is carried across segments, and the adaptation time is measured.

## 1. Start point and why

`accept_universal.py` on the universal3 checkpoints (dev seeds 0 to 19; `out/accept_uni3_best.json`,
`out/accept_uni3_1500.json`, `out/accept_uni_a.json`, another session, 2026-11-18):
- universal3 at iteration 1500 walks 0.26 to 0.30 m/s on the 0.25 command with the hip torque at the clamp and
  falls in every pack walk (20 of 20 nominal, 20 of 20 comx+10, 19 of 20 batteries out, 12 of 20 no pack).
- its best-reward checkpoint (iteration 250) is close to run A final and a little worse (comx+10 stand 13 falls
  against 5, nominal walk 1 against 0).
- run A final (`ckpt/uni_a`) is the best one-frame policy over all loads: 0 falls in the nominal, no-pack, 25 / 50 /
  75 %, batteries-out and full-pack walks at 0.17 to 0.18 m/s. Its failed lines: comx+10 walk 19 of 20 falls,
  comx+10 stand 5, mass +10 % walk 2, walking shove 11 (reference fq2 1999: 0, 0, 0, 1), walk torque p99 0.53 N m
  (line 0.48), step width 123 mm (line 105), head-down walk at full pack 3 falls.

Start point for the teacher and for the control arm: run A final, `ckpt/ts_start/walk61.onnx` (copy of
`ckpt/uni_a/walk61.onnx`, sha256 3aadc94a921d4961). The failed lines are the ones a policy that knows the load and
the centre of mass could fix, which is the reason for a privileged teacher (HISTORY-PLAN.md section 6).

Known risk carried into this round: the universal3 recipe run from this same start (fk-uni3, learning-rate clamp
3e-4) peaked in training reward at iteration 250 (88) and fell to 55 by 1500, and the later checkpoints fall in the
runtime simulation. The reward and randomization are not changed here (they are the audited ones). The one optimizer
change, in both arms alike: learning-rate clamp 1e-4 instead of 3e-4, and a save every 100 iterations so an early
checkpoint can be picked on falls, speed and torque.

## 2. What each network sees

- One-frame policies (start point, control arm): the 61 numbers of the runtime contract per tick (48 proprioception,
  twist 3, head pose 4, body pose 6). MLP 512-256-128.
- Teacher (PPO, delta `universal3t`): the same 61 plus 7 simulator-only numbers (`flight/teacher.py`): payload mass
  (kg), loaded-trunk centre of mass x, y, z (m, the columns the critic already had), trunk linear velocity x, y, z in
  the trunk frame (m/s). 68 inputs, same MLP. Warm start: run A's weights with zero weights on the 7 new inputs and
  fixed input statistics for them; iteration-0 export equals the start policy (0.0 on 256 random frames, Mac mini).
  The critic is unchanged (80 inputs).
- Student (new, `flight/recurrent.py`): 61 numbers per tick and its own state, nothing else. Encoder
  Linear(61+8, 128) + ELU, a recurrent core, head Linear(256, 128) + ELU + Linear(128, 14) on [core output, encoder
  output]. The 8 extra encoder inputs are a zero-filled "target vector" slot created inside the network for a later
  vision encoder; it is not an ONNX input. No weights come from the old policies; only the input mean and scale are
  taken from the teacher's normalizer.
  - LSTM arm: two layers, 128 hidden, 306,830 parameters, state 512 numbers.
  - Mamba arm: two blocks (d 128, expand 2, state 16, conv 4), single-step pure PyTorch, 277,134 parameters, state
    9,728 numbers. Exports to ONNX without mamba-ssm.
  - ONNX: single step, inputs `obs [1, 61]` and `state_in [1, S]`, outputs `actions [1, 14]` and `state_out`; the
    state is zero at policy start. `train/flight_eval.py` and `train/style_eval.py` already carry any second
    input/output pair as state, so the evaluators are unchanged; `--hist-repeat` (state always zero) is the
    no-memory control.
- Board facts (Radxa Cubie A7Z model zoo, read 2026-11-17): the NPU has a published LSTM example (two layers, 128
  hidden, 1.2 ms) and no Mamba example. Both student cores are under 1 M parameters; the LSTM arm is the published
  shape.

## 3. Reward and randomization: universal3, unchanged

Reward delta against universal3: none. `universal3t = universal3 + the 7 actor columns` (`flight_worker.py`); the
students are distilled in the plain universal3 env. Sources: NEXT-PLAN.md and `rm_universal3.json` (the launcher
refuses a push when `flight_worker.UNIVERSAL3_MODS` differs from that file).
- Payload at every reset, in every env (`payload.trunk_payload`): full pack 40 %, batteries out 25 %, no pack 10 %,
  scaled U(0, 1.15) x full 25 % (UNIVERSAL-PLAN.md section 2; smoke draw 0 to 0.988 kg).
- Whole-robot centre of mass x +-12 mm; pushes +-0.35 m/s (rm_universal3.json).
- Commands: forward -0.05 to 0.30 m/s, sideways +-0.05, turn +-0.5 rad/s (runtime ranges). Head pose commands
  already at full range in every env because the fine-tune starts with the curricula finished: neck pitch +-1.10,
  head pitch +-1.10, head yaw +-1.40, head roll +-0.31 rad, resampled every 2 to 5 s. Measured in the teacher env
  (Mac mini smoke): 68 % of walking env-steps carry a head command above 0.3 rad. So head-pose commands while walking
  need no new sampling and no new incentive.

## 4. Incentive audit (before launch)

`flight_audit.py --jobs universal3t`, Mac mini CPU, 128 envs x 400 steps, one case per job, run A final as the
intended walker, the same 18 cases as universal3: stand, step in place, lean forward, lean back at full / batteries
out / none over the training command range (`out/audit_ts_<case>_<load>.json`) and stand and step in place for
commands of 0.15 to 0.30 m/s forward only (`rm_ts_fast.json`, `out/audit_tsfast_<case>_<load>.json`). Pass: every
degenerate case earns at most 0.80 of the walk per second and less tracking reward. Result (2026-11-18 02:09, gate
recorded in `out/audit_gate.json`, delta universal3t, 18 files): PASS at full / batteries out / none. Share of the
walk's reward per second: stand 0.549 / 0.536 / 0.558, step in place 0.715 / 0.748 / 0.717, lean forward 0.529 /
0.515 / 0.558, lean back 0.523 / 0.514 / 0.535; fast commands: stand 0.499 / 0.513 / 0.488, step in place 0.614 /
0.635 / 0.590. Worst 0.748 (line 0.80). The walk earns 10.18 / 10.27 / 10.14 per s at 0.140 / 0.137 / 0.156 m/s. The
numbers match the universal3 audit (worst 0.718) within its run-to-run spread, as expected: the reward is the same.
The students use no reward. Their env is the universal3 env, whose gate (`out/audit_gate.json`, 2026-11-12) stands.

Stops, all on task metrics: PPO arms `--track-guard 2.0` (velocity tracking error against the warm-up baseline) and
the low-command speed floor, reward guard off (`--guard-fraction 0`); distillation stops when the student-driven envs
do not step (speed on 0.15 to 0.30 m/s commands under max(0.03, half the teacher's)) or fall more than 4 x the
teacher's rate + 1 per env-minute on two saves after iteration 120. Every job has `--max-hours`.

## 5. Distillation (`flight/distill_worker.py`, DAgger)

Each iteration is one 100-tick segment (2 s) in 4096 envs. The teacher labels every visited state from the student's
61 inputs plus the 7 privileged numbers read from the simulator. The teacher drives all envs for 2 iterations (its
falls and speed there are the baseline), then a share falling linearly to 0 over 40 iterations; the student drives
the rest, half of them with 0.10 rad action noise. Loss: mean squared action error, backpropagated through the whole
100-tick segment from the segment's start state; 2 epochs, minibatches of whole envs, Adam 1e-3 falling to 2e-4,
gradient clip 1.0. The student state is zeroed where an episode ends and carried (detached, not reset) into the next
segment, so the memory horizon is not the segment. BPTT length used: 100 ticks (2 s) for both cores; it fits the T4 (section 6), so it was not shortened.

## 6. Runs and budget

Bench (Kaggle T4 x 2, 4096 envs, 2026-11-18, kernels `microduck-ts-bench-t` and `microduck-ts-bench-mamba256`, both
COMPLETE; 0.42 h of quota for the two sessions):
- Teacher PPO, 40 iterations: 0.19 to 0.20 it/s (5.1 s per iteration, as universal3), 5.0 GB.
- LSTM distillation, 12 iterations of 100 ticks, minibatch 512 envs (16 gradient steps per iteration): 0.040 it/s
  (25 s per iteration, about 21 s of it simulation), 5.4 GB.
- Mamba distillation, 12 iterations: minibatch 256 (32 steps per iteration) 0.025 it/s (40 s), 8.8 GB; minibatch 512
  0.030 it/s (33 s), 12.4 GB of the T4's 15 GB, too close to the limit.
- With the iteration-0 teacher (= run A) as the label source, 12 iterations took the students from 65 to 80 falls
  per env-minute to: Mamba minibatch 256 1.36 (teacher-driven envs 1.42, speed 0.128 against 0.134 m/s), Mamba
  minibatch 512 5.2, LSTM minibatch 512 40. More gradient steps per iteration help, so both arms run minibatch 256.
- Setup (uv sync, imports) 3.5 min per session.

- Session 1, `ts-teach` (GPU 0) + `ts-ctrl` (GPU 1): teacher `universal3t` and one-frame control `universal3`, both
  from `/root/assets/init/ts_start.onnx`, seed 1, learning-rate clamp 1e-4, warm-up 100, save every 100.
  1000 iterations = 1.43 h at 0.195 it/s plus setup; `--max-hours 1.6`, about 1.55 h of quota.
- Teacher gate (HISTORY-PLAN.md section 6): the teacher must beat the control at the same iteration in the same env
  on falls per env-minute at equal or higher speed, per load (`ts_round.sh teval`, the intended walk alone at full,
  batteries out and none; the runtime evaluators cannot feed privileged inputs). The teacher checkpoint is the one
  with the fewest falls whose control twin still passes the runtime screen (comx+10 walk and stand, nominal walk,
  no-pack walk, walking shove). If no teacher checkpoint beats the control, the students are still distilled from the
  best teacher checkpoint and the report says the gate failed.
- Session 2, `ts-lstm` (GPU 0) + `ts-mamba` (GPU 1): the two students from `/root/assets/init/ts_teacher.onnx`.
  Identical settings but the core: 240 iterations of 100 ticks, 2 epochs, minibatch 256, teacher share to 0 over 30
  iterations, save every 20. Mamba 40 s per iteration = 2.7 h, LSTM about 29 s = 1.9 h; `--max-hours 2.75`, about
  2.8 h of quota (the session lasts as long as the slower arm).
- Quota: 0.42 h used by the benches + about 1.55 h + about 2.8 h = about 4.8 h of the 10 h cap. The rest is held
  back; nothing else is planned on it.

## 7. Acceptance (Mac mini, runtime simulation, policy from the first tick)

For the LSTM student, the Mamba student, the control arm and the start point, identical cases and seeds:
- `accept_universal.py run/score` (36 cases, dev seeds 0 to 19, reference fq2_1999 and uni_a): every line per load
  state (none, 25 / 50 / 75 %, batteries out, full; mass +10 %, COM x +-10 mm, shoves, landing, head scan and
  head-down walks).
- Added case, `accept_head.py`: walk with neck pitch 0.5 rad and head yaw 0.6 rad at none, 25 / 50 / 75 %,
  batteries out and full pack: falls of 20 and distance (median upright speed x 15 s).
- No-memory control: the picked student once more with `--hist-repeat` (state held at zero) on the decision cases;
  only a clear loss shows that the memory is used.
- Adaptation time, `flight/adapt_eval.py` per load (full, batteries out, none; 64 envs, pushes off): the student's
  action error against the teacher per tick after a reset, after a 0.26 m/s push and after its state is zeroed while
  walking; settle time = first tick from which the median error stays within 1.5 x the steady value + 0.005 rad for
  10 ticks (`out/adapt_<student>_<load>.json`).
Training reward and imitation loss are not evidence; a student is chosen on falls, speed and torque.
