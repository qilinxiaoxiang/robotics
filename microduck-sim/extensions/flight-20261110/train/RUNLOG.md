# Flight-pack training run log

Times are America/New_York, read from `date`. Cost rule: Modal hard cap 35 USD for this work; each launch lists its worst case and the
running total of worst cases; real spend read from `modal billing report` before each new launch.

## 2026-11-10

- 19:01 Kaggle quota: GPU 0.00 h used, 30.00 h left, resets 2026-11-14 00:00. Modal `billing summary`: $0.11 metered
  this month (all credited, billed $0.00); the free-credit balance is not exposed by the CLI (Credits tab only), so the
  35 USD cap is kept and the plan spends far below 70 % of the $30 monthly credit alone (21 USD).
- 19:05 Model check (`check_pack_model.py`, compile only, MacBook): training model = probe model = mass report:
  1.8991 kg with the pack, 0.9605 kg without; COM -12.0, -1.4, 30.0 mm (trunk frame, default pose) in both models;
  trunk_base 1.291 kg. Mass difference 0.0 % (pass, limit 1 %). `out/check_pack_model.json`.
- 19:09 Smoke and audit launched together (all short, dependent long runs wait for them):
  - Kaggle paired smoke `fk-smoke-a` (packscratch, --scratch, 64 envs, 6 iterations) + `fk-smoke-b` (packstand from
    stand61): checks the Kaggle path through flight_worker.py, the scratch path and the stand init. Dataset
    `shawnxiang9527/microduck-flight-src` (private), source digest 6a0066890befc439.
  - Modal `fsmoke2` (packwalk from walk61, 64 envs, 6 then 9 iterations = resume test), L4, worst case 0.75 h x $1.117 = $0.84.
  - Modal `audit1` (flight_audit.py, 2048 envs x 15 s), L4, worst case 1.0 h x $1.117 = $1.12.
  - Modal CPU eval `baseline` (old walk61/stand61, 18 cases x 20 episodes, 1 core each), worst case 360 x 15 min x
    $0.055/h = $5.0 (expected about $0.3).
  - Running total of Modal worst cases: $6.96 (a first audit/smoke pair at 19:09 failed at container start on a path
    bug in flight_modal.py, seconds of CPU, stopped).
- 19:16 Mac mini check: load average 65 on 10 cores and under 1000 free pages, saturated by the flight-sim agent's
  jobs, so evaluations moved to Modal CPU (`flight_eval_modal.py`, same probe, same pins as the mini venv). One test
  episode on the mini reproduced the baseline fall (walk61/stand61, nominal pack, vx 0.25: fell at 0.62 s, the probe's
  own nominal_ss0.3 fell at 0.64 s) and the no-pack walk stayed up (0.090 m/s, peak leg force 0.507 N m).
- 19:20 Modal L4 had no capacity ("waiting to be scheduled on a GPU_L4 worker" for several minutes); audit and smoke moved
  to A10 ($1.10 + 4 cores + 16 GiB = $1.42/h). A second failure: the slim image lacked README.md, so `uv sync` built
  no venv (numpy missing at start); fixed in flight_modal.py, which now also checks the imports at build time.
  Failed attempts cost seconds each. Modal worst case for the A10 audit2 + smoke fsmoke3: 1.0 h x 1.42 + 0.75 h x 1.42 = $2.49;
  running total of worst cases $9.45.
- 19:25 Baseline in the probe (Modal CPU, `eval/baseline_*.json`, old walk61/stand61, 20 episodes x 20 s each):
  with the pack 20 of 20 fall in every case (nominal stand, walk, turn left, turn right; mass +10 %; COM x -10 mm;
  shove; landing) and 19 of 20 at COM x +10 mm; falls come at 0.36 to 1.7 s, before the walk command. Without the
  pack 0 of 20 fall in stand, walk (0.089 m/s at vx 0.25), turn left (+0.297 rad/s) and turn right (-0.296 rad/s);
  p99 of the largest leg force 0.11 N m standing, 0.32-0.33 N m walking or turning. Per-joint during a with-pack
  fall (`eval/diag_baseline_*`): hip pitch at the 0.538 N m clamp 17-35 % of steps, mean 0.23-0.27 N m.
- 19:28 Smoke fsmoke3 (A10) reached iteration 0 (walk61 init exact, 0.00 diff; pack 1899.1 g) and then crashed in the
  worker's save(): finetune_worker commits the Modal Volume "microduck-rl" when `import modal` works, and Modal's
  client is on the subprocess path. flight_worker.py now hides `modal` from the worker (its own try/except then skips
  that commit; flight_modal.py commits this run's Volume), and the image carries FLIGHT_RUN so the container names the
  same Volume. Relaunched as fsmoke4 (worst case $1.07; running total of worst cases $10.52).
- 19:31 Kaggle smoke fk-smoke-a/b COMPLETE (uv sync 871 s, train 128 s): scratch path (random init, std 0.999,
  curricula from 0) and stand61 init (exact) both train and export. Found: the stand job still had moving envs
  (the command term's start value 0.02 holds until a resample), so flight_worker.py now also sets
  commands.twist.rel_standing_envs. Quota after the smoke: read at the next status check.
- 19:31 Reward audit audit2 (A10, 2048 envs x 15 s, `train/out/audit-audit2.json` when fetched; numbers from the log):
  - packwalk PASS. Intended (walk61, no pack) 6.912 /s, track_linear_velocity 1.155 /s, 0.81 falls per env-minute
    (the 3 cm drop starts add falls; 0.19 without them in the 10-30 tether audit), 0.095 m/s along the command.
    Standing still (stand61) 5.39 /s = 0.78 of walking (gate 0.80), track 0.918 of walking; shuffling in place
    (walk61 fed an in-place turn) 6.253 /s = 0.905, track 0.897; falling slowly on the pack model 3.70 /s (walk61) and
    3.80 /s (stand61), 37-42 falls per env-minute. Walking wins on every count; the standing margin is thin (0.78).
  - packstand FAIL as designed: stand61 standing on the light robot earns 6.449 /s (track 1.539) while walk61 fed an
    in-place turn earns 6.988 /s (track 1.914). stand61 is not the best stander under this reward (it came from
    Pollen's standup task, not the velocity task, and falls 1.26 per env-minute with the drop starts). A stand-only
    fine-tune from stand61 would be pulled toward walk61's behaviour, so it is not launched.
  - 19:34 audit3 (worst case $1.42; running total $11.94) asks the next question: does walk61 standing at zero
    command beat walk61 stepping in place under the stand job's reward? If yes, the stand job starts from walk61.
- 19:33 Kaggle round 1 launched: fk-scratch-s1 + fk-scratch-s2 (paired, one T4 each), from-scratch on the pack
  model with Pollen's recipe + pack DR, seeds 1 and 2, 12000 iterations or 10 h, reward guard off (total reward is
  not a criterion), saves every 100 iterations. Question: can the original recipe learn to stand and walk with the
  pack at all, independent of the fine-tunes? Blind until it ends (about 05:00).
- 19:36 Modal billing before launch: metered $0.11 this month, credits cover it, billed $0.00.
- 19:37 Modal round 1 walk fine-tunes launched, both detached (`modal app list`: ap-mUzu829m2Hh98helcvNdzh fw1,
  ap-0sdgAyl0va2BJ0U7FTezuk fw2, "ephemeral (detached)", 1 task each, after the client exited). A10, 4096 envs,
  --delta packwalk, walk61 init, max-lr 3e-4, 100 critic warm-up iterations, 5000 iterations or 3.5 h, guards off,
  saves every 50. Worker dollar cap $4.97; worst case per run $5.67 (3.5 h + 0.5 h timeout at $1.417/h).
  Running total of worst cases $23.28.
  - fw1 (seed 1, init_std 0.25). Question: does fine-tuning walk61 on the pack model recover standing and walking?
  - fw2 (seed 2, init_std 0.4). Question: does more exploration help after the mass doubles?
  Stop and choice by checkpoint probes (falls out of 20 in the brain_sim_check probe), never total reward.
- 19:38 audit3 PASS (`out/audit-audit3.json`): walk61 at zero command on the light robot earns 7.561 /s under the
  stand job's reward (track 1.921, 0.57 falls per env-minute), more than walk61 stepping in place 7.002 /s (0.926),
  stand61 6.724 /s, and falling on the pack model 4.85 /s (0.641) and 4.82 /s (0.637). The stand job starts from walk61.
- 19:39 Modal stand fine-tune fs1 launched, detached (A10, 4096 envs, --delta packstand, walk61 init, seed 3,
  init_std 0.25, max-lr 3e-4, 3500 iterations or 2.5 h, guards off, saves every 50). Worker cap $3.55, worst case
  $4.25. Running total of worst cases $27.53 (cap $35). Question: can a stand-only fine-tune give a with-pack
  zero-command policy that holds still for 20 s, for the stand61 slot?
- 19:45 Probe pipeline `train/probe_ckpt.py` (Volume get, ckpt2onnx, Modal CPU probe) checked on fw1 iteration 0
  (= walk61, 4 episodes): falls 4 of 4 at 0.52-0.54 s, as the baseline. Kaggle quota 0.42 of 30 h used; fk-scratch
  pair RUNNING.
- 19:52 First checkpoint probe (iteration 300, 20 episodes, `eval/probe_*_300*`): every checkpoint fell 20 of 20 at
  0.56-0.96 s, while training episodes already lasted 739 of 1000 steps. Diagnosis (`specs/diag300.json`,
  `specs/diag_olstand.json`, 4 episodes each): the probe's 0.3 s open-loop stand start is the cause. The runtime's
  open-loop stand mode alone (--stand-s 20, old policies) falls at 0.54 s with the pack (0 of 4 upright) and holds
  without it (tilt 2.2 deg); fw1 at iteration 300 started from the first tick (--stand-s 0) fell 0 of 4; supply 8.2 V
  or no dropped reads did not change the fall. So the with-pack probe now starts the policy at the first tick
  (`--stand-s 0`, which is also what the landing hand-over does); flight_eval.py/flight_eval_modal.py take extra probe
  flags per eval for this. The open-loop stand mode itself cannot hold the pack: a runtime finding, not trained here.
  The baseline (old policies) is re-run under the same start: `specs/suite_baseline0.json` -> `eval/baseline0_*`.
- 19:56 Probe at iteration 350 (stand-s 0, nominal pack, 20 episodes):
  - fw1 alone (both slots): stand 0/20 falls; walk 9/20 falls (5.7-8.2 s ...), 0.091 m/s upright; turnL 0/20, +0.301 rad/s.
  - fw2 alone: stand 0/20; walk 0/20 but 0.000 m/s (it stands under vx 0.25: the drift to standing); turnL 0/20, +0.295.
  - fs1 iteration 300 in the stand slot + fw1 350 walking: stand 0/20; walk 0/20 but 0.000 m/s (fw1 does not start
    stepping from fs1's quiet stance); turnL 2/20 falls, +0.303. Trunk height 0.115 m in all still cases (the same as
    the old policy walking without the pack), so they stand, they do not rest the trunk on the floor
    (`eval/z_*`, trunk_z_m added to the episode record).
  Decision: keep all three running; next probe at about iteration 1000.
- 19:58 Baseline under the same start (`eval/baseline0_*`, old stand61/walk61, policy from the first tick, 20 each):
  with the pack 20/20 falls in every case (nominal stand, walk, turnL, turnR, mass +10 %, COM x -10 mm, both shoves,
  both landings; falls 0.48-1.48 s) and 19/20 at COM x +10 mm stand. Without the pack 0/20 everywhere: walk
  0.0915 m/s, turnL +0.2945, turnR -0.297 rad/s; leg force p99 0.109 N m standing, 0.32-0.34 N m walking/turning.
- 20:00 Probe at iterations 450-500: fw1 500, fw2 450 and fs1 450 + fw1 500 all 0/20 falls in stand and walk, but
  0.000 m/s at vx 0.25: all now stand under a walk command. Training rows (`progress.csv`): fw1 episode length
  16.7 -> 758-838 steps of 1000, speed along the command 0.022 -> 0.039 m/s (walk61 without the pack: 0.095 in the
  audit). The policies learned not to fall first; walking is not back yet. Continue; next probe at iteration 1000.
- 20:18 Probe at iteration 1000 (nominal pack, 20 each, policy from the first tick):
  - fw1 1000: stand 0/20, walk 0/20 at 0.085 m/s (old walk61 without the pack: 0.0915), turnL 0/20 at +0.300 rad/s.
    Leg force p99 0.22 N m standing, 0.53 walking, 0.538 turning; share of steps at >= 95 % of 0.538 N m: 0 %, 3.8 %, 7.1 %.
  - fw2 1000: stand 0/20, walk 0/20 at 0.057 m/s, turnL 0/20 at +0.300; saturation 13.7 % walking, 14.6 % turning.
  - fs1 950 in the stand slot + fw1 1000: stand 0/20, walk 0/20 at 0.082 m/s, turnL 0/20 at +0.301.
  Walking with the pack is back in this probe. fw1 leads. Full suite on fw1 1000 launched
  (`specs/suite_fw1_1000.json`). Training continues: the question for the rest of the run is whether the torque
  margin grows (saturation share falls) while tracking holds.
- 20:26 Full suite fw1 1000 (`eval/fw1_1000_*`, 20 each): nominal stand 0, walk 0 (0.085 m/s), turnL 0 (+0.301),
  turnR 0 (-0.299); mass +10 % stand 0, walk 0 (0.077); COM x +10 mm stand 1, walk 1 and 0.000 m/s (it stands under
  the walk command); COM x -10 mm stand 0, walk 0 (0.048); shove 0.5 N s at 8 s stand 4 (9.2-9.7 s), walk 2;
  landing stand 0, walk 0 (0.071); no pack stand 3, walk 18, turnL 18, turnR 19 (trained on the pack only: the
  no-pack robot keeps the old policies). Open points for the rest of the run: shove, COM forward, torque margin.
  Next probe at iteration 2000.
- 20:50 Incident: the first video app (ap-LcFfcXirNbhVx88jtH1JEZ, flight_video_modal.render) crash-looped at
  container start from 20:27, and Modal emailed Shawn at 20:42. Cause (container log): `ModuleNotFoundError: No module
  named 'flight_eval_modal'`: Modal mounts only the entry file at /root, and flight_video_modal.py imports its sibling.
  The local client had returned at 20:30 and the app kept retrying without containers running. Stopped with
  `modal app stop -y` at 20:50. Fix in flight_video_modal.py: the sibling is shipped with add_local_python_source, the
  image build renders one OSMesa frame (a GL problem fails the build, not the start), retries=0, timeout 20 min.
  Rerun once at 20:51. fw1, fw2, fs1 unaffected (detached, all at iteration 1850 at 20:52). Modal metered this month
  $6.31 at 20:52 (credits cover it, billed $0.00); cap $35. From now on every launch is preceded by `modal app list`
  with a check for apps in a failing or restarting state.
- 20:54 Video rerun succeeded (ap-fmKrJjvyMfrSeLa162sFSH completed, build log "osmesa render ok"):
  `video/fw1_1000_walk.mp4` (5.1 MB) and `video/fw1_1000_walk_t10.png`. Key frame checked: upright, mid-stride, both
  feet on or near the floor. The pack is mass and inertia in the probe model (manifest) and has no visible geometry,
  so the picture shows the duck without it.
- 21:01 Full suites at iteration 2000 (`eval/fw1_2000_*`, `eval/fw2_2000_*`, 20 each; falls, then upright speed):
  - fw1 2000: nominal stand 0, walk 1 (0.117 m/s), turnL 1 (+0.301), turnR 1 (-0.300); mass +10 % stand 0, walk 0
    (0.118); COM x +10 stand 2, walk 4 (0.167); COM x -10 stand 0, walk 1 (0.070); shove stand 0, walk 12; landing
    stand 0, walk 1; no pack stand 0, walk 17, turnL 16, turnR 15. Walk saturation (>= 95 % of 0.538 N m) up to 13-31 %.
  - fw2 2000: nominal stand 0, walk 0 (0.116), turnL 2, turnR 0; mass +10 % 0/0 (0.119); COM x +10 stand 1, walk 4;
    COM x -10 0/0 (0.071); shove stand 8, walk 6; landing stand 4, walk 5 (falls at 0.8-1.3 s); no pack stand 0,
    walk 17, turnL 8, turnR 15.
  Reading: from 1000 to 2000 both walk faster (0.085 -> 0.117 m/s at vx 0.25; old walk61 without the pack 0.0915)
  and harder (more steps at the torque limit); the walking shove got worse for fw1 (2 -> 12 of 20). Training pushes
  are ±0.3 m/s velocity kicks, and the eval shove (0.5 N s on 1.9 kg) is 0.26 m/s, inside that range. No relaunch
  yet: the round-2 question is chosen after the 3000-5000 checkpoints.
- 21:08 Stand slot fs1 1950 (`eval/fs1s_*`, zero command throughout, 20 each): nominal 0, mass +10 % 0, COM x +10 0,
  COM x -10 0, shove 0.5 N s 0, landing 0, no pack 0 falls. Leg force p99 0.21-0.36 N m (0.47 under the shove),
  saturation at most 1.6 %. fs1 is the stand-slot policy; the walk slot is still open between fw1 and fw2.
- 21:37 Walk slot at iteration 3000 with fs1 2950 in the stand slot (`eval/r1_3000_*`, 20 each):
  - fw1 3000: walk 0 (0.141 m/s), turnL 0, turnR 0; mass +10 % walk 2; COM x +10 walk 7; COM x -10 walk 20 of 20;
    walking shove 6; walking landing 1; no pack walk 9, turnL 8, turnR 6.
  - fw2 3000: walk 1 (0.142), turnL 0, turnR 2; mass +10 % 0; COM x +10 8; COM x -10 20 of 20; shove 4; landing 0;
    no pack 18-19.
- 21:40 COM x -10 mm separated (`eval/fs1s2950_*`, and probes on the COM x -10 manifest, 20 each): fs1 2950 alone
  falls 2 of 20 standing there (at 0.8-1.0 s); fw1 3000 in both slots falls 1 of 20 walking, fw2 3000 3 of 20; fs1 1950
  handing over to fw1 3000 falls 7 of 20 at 2.8-2.9 s, right after the first walk command. So with the COM 10 mm back
  the failure is the hand-over from fs1's quiet stance to the walk policy's first steps, plus a regression in fs1 from
  1950 to 2950 (0 -> 2 of 20 standing). The pairing is chosen on the whole suite: fs1 + fw, and fw in both slots.
- 21:41 fw1 3000 in both slots (`eval/fw1_3000_*`, 20 each): nominal stand 0, walk 0 (0.146), turnL 0, turnR 0;
  mass +10 % 0/0; COM x +10 stand 14, walk 17; COM x -10 1/1; shove stand 2, walk 10; landing stand 2, walk 3; no pack
  stand 0, walk 11, turnL 7, turnR 8. COM x ±10 mm of the whole robot is the edge of the training randomisation
  (trunk COM ±15 mm on 1.29 of 1.90 kg, capped there in the recipe because a wider range left the support polygon),
  so those cases swing from checkpoint to checkpoint.
- 21:42 Round 2 question: can the walker keep its walking and its falls while leaving torque margin? Every round-1
  walker runs with the leg torque at the 0.538 N m clamp while walking (p99 = 0.538, 13-40 % of steps at >= 95 %).
  On the real robot that is the overload and heat limit. New delta packwalk_tq = packwalk + a hinge cost on each
  actuator's |force| above 0.45 N m, fine-tuned from fw1 3000; its weight is set from audit4 (weight -1 measured,
  other weights computed from the per-term tally), which prices fw1 3000 walking against fs1 1950 standing, fw1
  stepping in place and walk61 falling, all on the pack model. audit4 launched (A10, worst case $0.71; running total
  of worst cases $28.24 of the $35 cap; real metered $6.31 at 20:52).
- 21:47 audit4 (`out/audit-audit4.json`, 2048 envs x 15 s, pack model, torque_margin at weight -1): fw1 3000 walking
  7.620 /s (torque cost 0.026 /s, track 1.170, 0.19 falls per env-minute, 0.082 m/s along the command); fs1 1950
  standing 6.227 (cost 0.052); fw1 stepping in place 6.424 (cost 0.041); walk61 falling 3.589 (cost 0.151). The
  verdict FAILs only on the standing gate: 0.817 > 0.80, and 0.821 without the term, so the round-1 reward itself
  already prices standing at 0.82 of walking on the pack. The hinge cost falls harder on standing and falling than
  on walking, so a larger weight widens the walking margin: weight -8 gives walking 7.438, standing 5.861 (0.788),
  stepping in place 6.135 (0.825), falling 2.43: PASS, with the walker paying 0.21 /s (2.8 % of its reward).
- 21:48 Modal metered $10.64 this month (billed $0.00). modal_watch: only the handled 20:42 alert, three live runs.
  Round 2 launched: fq1 (A10, --delta packwalk_tq --tq-weight -8, init fw1 3000, seed 4, 2500 iterations or 2.5 h,
  guards off). Worker cap $3.55, worst case $4.25; running total of worst cases $32.49 of $35 (real spend is the
  binding number: $10.64 metered). Question: does the walker leave torque margin (lower p99 and saturation in the
  probe) without losing its falls and speed?
- 22:24 Full suites at iteration 4000 (`eval/fw1_4000_*`, `eval/fw2_4000_*`): both walk faster (0.163-0.168 m/s at
  vx 0.25) with more saturation (walk 25-29 % of steps at >= 95 % of the limit) and are more brittle: fw1 4000 mass
  +10 % walk 8, COM x +10 walk 16, walking shove 9, walking landing 4; fw2 4000 COM x +10 20/20 standing and walking,
  COM x -10 5-6. Falls summed over the 14 with-pack cases: fw1 1000 8, fw1 2000 23, fw2 2000 30, fw1 4000 40,
  fw1 3000 50, fw2 4000 59. Robustness peaks early, and later training trades it for speed and torque. Next: suites
  for fw1 750/1250/1500 and fw2 1000/1500 to find the best checkpoint near the peak, then the fs1 pairing.
- 22:31 Peak search (`eval/fw1_750_*`, `fw1_1250_*`, `fw1_1500_*`, `fw2_1000_*`, `fw2_1500_*`): with-pack falls summed
  over the 14 cases: fw2 1000 4, fw1 1250 5, fw1 1000 8, fw1 750 11, fw1 1500 11, fw2 1500 21. fw2 1000 and fw1 750
  stand where they should walk (fw2 1000 0.000 m/s after the landing, fw1 750 0.000 m/s in nominal walk), so falls
  alone would reward a policy that does not walk. Choice rule made explicit: a walk case below 0.03 m/s counts as
  failed, then fewest falls, then speed. fw1 1250 leads: nominal 0/0/0/0 falls, walk 0.100 m/s (old walk61 without
  the pack 0.0915), mass +10 % 0/0, COM x +10 1/1, COM x -10 0/0, shoves 0/1, landings 1/1, walk saturation 2.9 %,
  walk p99 0.532 N m. Next: fs1 1950 in the stand slot with fw1 1250.
- 22:33 fs1 1950 in the stand slot with fw1 1250 (`eval/pair1250_*`): walk cases 0 falls except COM x -10 15 of 20
  (the hand-over from fs1's stance again, at 2.6-3.0 s) and turnR 1, walking shove 1. Summed with fs1's stand cases:
  17 with-pack falls against 5 for fw1 1250 in both slots. Choice: fw1 1250 in both slots (walk61 and stand61 the
  same file; the runtime switches slots at the first walk command).
- 22:33 fw1 (at 4300) and fw2 (at 4450) stopped by the plan's stop rule: their last two probed checkpoints (3000,
  4000) are worse than the earlier ones (fw1 50 and 40 falls, fw2 59 at 4000, against 5-8 at 1000-1250). fs1 ended by
  itself at iteration 3499 (21:56). fq1 (round 2) is at iteration 1000.
- 22:35 Round 2 reading, fq1 1000 full suite (`eval/fq1_1000_*`): with-pack falls 8 of 280 (nominal 0/0/0/0; mass
  +10 % 0/0; COM x +10 1/1; COM x -10 1/1; shoves 1/3; landings 0/0), walk 0.130 m/s, and the torque margin is there:
  walk p99 0.439 N m (fw1 3000, its start: 0.538), saturation 0.6 % walking (fw1 3000: 15 %), turns p99 0.42-0.49.
  Answer to the round-2 question: yes, the hinge cost at weight -8 leaves margin and cut falls from 50 to 8.
- Round 3 question: does the same torque-margin fine-tune from the robust fw1 1250 give both its 5 falls and fq1's
  margin? audit5 first (walker fw1 1250, stander fs1 1950, same reward).
- 22:40 audit5 (`out/audit-audit5.json`, walker fw1 1250): FAIL at every weight. In the training env fw1 1250 tracks
  worse than fs1 standing (track_linear_velocity 1.060 against 1.099; 0.050 m/s along the command), so the reward
  does not prefer its walking over standing, and the torque term cannot change that (it has no tracking part):
  ratios standing/walking 0.832 at weight -1, 0.801 at -8, 0.782 at -12, with the track check failing throughout.
  The round-3 run from fw1 1250 is not launched.
- 22:41 Round 3 instead: fq2 = fq1's recipe from the same start (fw1 3000, audit4 PASS) with weight -12 and another
  seed (5). audit4 at -12: walking 7.334 /s, standing 5.653 (0.771), stepping in place 5.972 (0.814), falling 1.79;
  track checks pass (standing 0.949 of walking). Question: is fq1's result reproducible, and does a stronger margin
  cost cut the shove falls (fq1 1000: 1 standing, 3 walking) without losing speed?
- 22:40 fq2 launched, detached (A10, packwalk_tq weight -12, init fw1 3000, seed 5, 2000 iterations or 2.0 h). Worker
  cap $2.84, worst case $3.54. Modal metered $14.51 before the launch (billed $0.00); with fq1's remaining time and
  fq2's worst case the month stays under about $21 of the $35 cap. This is the last training round (three rounds:
  fw1/fw2/fs1, fq1, fq2).
- 23:17 fq1 1500 and 2000 suites (`eval/fq1_1500_*`, `eval/fq1_2000_*`): with-pack falls 6 and 11 (fq1 1000: 8).
  fq1 1500: nominal 0/0/0/0, walk 0.117 m/s, p99 0.452, saturation 0.8 %; mass +10 % 0/0; COM x +10 1/1; COM x -10
  0/1 (0.036 m/s); shoves 2/1; landings 0/0. fq1 2000 walks faster (0.140) with more falls (walking shove 4, COM x +10
  walk 3). The fq2 1000 evals in the same batch are void: model_1000 did not exist yet (fq2 was at 750), the models
  dir stayed empty and every episode failed; flight_eval_modal.py now marks such an eval `incomplete` and prints it,
  so failed episodes never read as 0 falls.
- 23:23 fq2 1000 suite (`eval/fq2_1000_*`, all 20 of 20 episodes returned): with-pack falls 3 (shove stand 1, landing
  stand 1, landing walk 1), walk 0.081 m/s, walk p99 0.48 N m, saturation <= 2.4 % except COM x -10 walk 8.9 %; but at
  COM x -10 it barely walks (0.020 m/s, below the 0.03 m/s rule), so that case counts as 20 failed episodes.
  Standing after: fw1 1250 5 failures (p99 0.532, sat 2.9 %, 0.100 m/s); fq1 1500 6 (p99 0.452, sat 0.8 %, 0.117 m/s);
  fq1 1000 8; fq2 1000 3 falls + 20 not walking. fq2 1500/2000 and fq1 2500 are probed when saved.
- 00:10 fq1 and fq2 finished by their iteration caps (fq1 2499 at 23:32, fq2 1999 at 00:00, fq2 cost $1.85 by its own
  record). Final suites (`eval/fq1_2499_*`, `eval/fq2_1500_*`, `eval/fq2_1999_*`, all episodes returned): with-pack
  falls fq2 1999 3, fq2 1500 14, fq1 2499 28. Choice by the rule (`out/results.json`, written by make_results.py):
  fq2 1999, the final checkpoint of round 3. With the pack: 3 falls in 280 (turnR 1 at 16.0 s, standing shove 1,
  walking shove 1), no walk case below 0.03 m/s; nominal walk 0.110 m/s (old walk61 without the pack 0.0915), turns
  +0.300/-0.301 rad/s, COM x -10 walk 0.054, COM x +10 walk 0.167; walk p99 0.462 N m and 0.75 % of steps at >= 95 %
  of 0.538 (round-1 walkers: p99 0.538, 13-40 %); single-step peak still touches 0.538 walking and turning, 0.443
  standing. Without the pack: stand 0, walk 5 (at 4.1-13.3 s, 0.158 m/s), turnL 0, turnR 0.
  Baseline (`eval/baseline0_*`): 279 of 280 with-pack falls. Policy files: `policy/walk61.onnx` = `policy/stand61.onnx`
  = fq2 model_1999 (sha256 6aaae79c25c405e5...), for the sim only; nothing is deployed.
- 00:16 Videos of fq2 1999 (Modal OSMesa, both apps completed, no retries): `video/fq2_1999_walk.mp4` and key frame
  `_t10.png` (upright mid-stride at 10 s), `video/fq2_1999_landing.mp4` and `_t1.png` (upright on both feet 1 s after
  the release). The pack has no visible geometry in the model, only its mass and inertia.

## Universal stand/walk plan (2026-11-11, Shawn's direction relayed by the coordinator; nothing launched)
- 00:30 Payload randomisation written (`microduck_rl/cmu/finetune/flight/payload.py`, delta `universal` in
  flight_worker.py): no-pack compile plus the real pack's parts as a per-env payload on trunk_base, states full 40 %,
  batteries out 25 %, none 10 %, scaled 0-1.15 x 25 %, critic gets payload kg + trunk COM. Probe manifests from the
  latest sim snapshot (d2de61ac, pack 955.1 g, batteries 302 g): `make_payload_manifests.py`.
- 00:38 Mac mini smoke (`mini_train_smoke.sh`, uv venv built in the mirror, 64 envs CPU): env builds, actor 61 / critic
  80, sampled payloads 0-0.988 kg, mass exact after resets (1.2e-7 kg), full state = compiled pack model (1.30744 kg both,
  J difference 3.7e-9), 2 PPO iterations in 4.6 s. `out/universal_smoke.json`.
- 00:53 Per-load probe on the Mac mini (`payload_probe.sh`, 20 episodes per case, `out/payload_probe.json`): fq2 1999
  0 falls at 25/50/75 %, batteries out and full pack, stand and walk (walk 0.078-0.122 m/s); no pack walk 2 of 20 at
  0.157-0.163 m/s (with --stand-s 0 and with today's 0.3 s start). stand61/walk61: 0 falls without the pack (walk
  0.090), 3 of 20 walking at 25 %, 20 of 20 from 50 % up. Same fq2 no-pack walk gave 5 of 20 on Modal: probe counts are
  compared on one machine only. Hips (fq2, all loads) p99 0.31-0.35 N m, 0-0.5 % of time near the clamp.
- 00:57 Universal audit started on the Mac mini (256 envs, 750 steps, CPU). Kaggle fk-scratch pair still RUNNING;
  Kaggle quota 5.55 of 30 h used at 00:45. Modal: no live apps; the one alert email is the 20:42 incident, closed.
- Plan written: `UNIVERSAL-PLAN.md`. No training launched; waiting for Shawn's go.
- 01:05-01:27 Shawn's two questions after the fq2 walk video (relayed): toe-out, and bending/head motion with the
  pack. Evaluation only, Mac mini, `style_eval.py` + `style_probe.sh`, results `out/style_bend_head.json`.
  Toe-out (stance foot yaw against the trunk, from the start pose): walk61 no pack 7.3 / 4.2 deg, fq2 with the pack
  21.3 / 22.2 deg; hip yaw -21.1 / +22.7 against -6.1 / +3.2 (gain foot/hip about -1), hip roll's 5 deg inward stance
  gone, step width 119 against 94 mm, trunk yaw oscillation unchanged (2.3 against 2.5 deg). Present already in fw1
  1250 (no torque hinge, 19-20 deg). Only leg-posture term: "pose" weight 1.0, hip yaw walking std 0.3 rad.
  Bend (groundpick61 phase 0.33, PICKUP.md): with the pack 20/20 falls at 2.6 s (fq2 or fs1 in the stand slot), trunk
  tips back to 72-79 deg nose-up, hip pitch p99 at 0.538. Without the pack the bend holds (mouth 2.1 cm) and 18/20 fall at
  the 10.0 s hand-back to stand61 (current 960 g model; default model 0/3). Seeing pick not runnable with the flight
  manifests ("repeated name 'jaw' in body"). Head scan standing: 0 falls (fq2, fs1), pitch excursion 2.6 / 4.6 deg;
  walking with head pitch 0.5 and 1.1: fq2 0 falls, 0.105 m/s; walk61 without the pack stops walking at 1.1. Quack
  tilts did not run in the probe (not counted). Plan sections 7 (style) and 8 (bend, head) added.
- 01:29 Universal audit (Mac mini CPU, 256 envs, 750 steps, `out/universal_audit.json`): FAIL. Full pack: fq2 standing
  under walk commands 0.821 of fq2 walking (gate 0.80) and higher tracking (1.107 against 1.062 per s); fq2 walks only
  0.051 m/s in the training env; posture reward 0.80 standing against 0.32 walking. No pack: stand 0.774, shuffle 0.90,
  fq2 0.78, all lose. Plan section 4 now asks for a tracking-weight change and re-audit before any launch.
- 01:40-03:05 Preparation for the universal and bend plans (evaluation only, Mac mini, no training):
  reward audit `flight_audit.py --jobs universal2 --diag` (stand, step in place, lean +-0.2 rad at full / batteries out
  / none, splayed fq2 against walk61 without the pack), priced offline by `reward_design.py` (`out/reward_design.json`).
  Training-env command ranges give no passing design (walkers 0.05-0.09 m/s, standing tracks as well). Runtime ranges
  (x -0.05..0.30, y +-0.05, yaw +-0.5) make the walker win tracking; with air time 6, tracking 3, upright 0.5, head-pose
  tracking 2 to 1, hip-yaw std 0.15 and foot heading -8 every degenerate ratio is at most 0.80 (worst 0.797, step in
  place without the pack). Splayed fq2 tracks the same as walk61 (1.411 / 1.405) and is faster, so speed alone does not
  remove toe-out. Bend statics (`bend_statics.py`, `out/bend_statics.json`): groundpick61's path needs hip 0.28 / 0.22
  N m at full / batteries out; battery room about 1 mm (`out/battery_room.json`); one battery hip 0.27. Seepick jaw
  error fixed (reused worker wrapped the visual hook twice, `flight_eval.py`); seepick with the pack 20/20 falls, without
  1/20. Quack runs with `--walk-s 0`: 0 falls, yaw 0.25-0.28 reached. Hand-back swap test (`handback_diff.py`): the
  trunk_base load (+129 g, COM 13 mm back and up) alone causes 4/6 falls; the robot's 11-06 logs show 5/5 hand-backs
  without a fall (`robot_handback_scan.py`). Plans: `UNIVERSAL-PLAN.md` sections 4, 7, 8; `BEND-PLAN.md`.
- 04:00 Shawn approved both plans (relayed by the coordinator, his words 2026-11-11: "两个都跑"): the universal pair of
  UNIVERSAL-PLAN.md with rm_chosen.json, and the bend fine-tune of BEND-PLAN.md (groundpick61 first, seepick61 after
  the bend passes). Kaggle free quota only. Kaggle quota at 04:00: 8.75 of 30 h used, 21.25 left (reset 11-14), with
  the scratch pair still running (ends about 05:33 at its 10 h cap); the two plans need about 6.7 h (universal pair,
  cap 10 h) plus about 3 h (bend), so the quota covers both.
- 04:02 Audit gate for Kaggle (`audit_gate.py`, out/audit_gate.json; `kaggle_flight.py push run` refuses a delta without
  a PASS at full / batteries out / none): universal2 PASS from out/audit2_chosen_*.json. Mac mini 2-iteration smoke of
  universal2 from fq2 1999 (out/universal2_smoke.json): reward mods applied, stance_foot_heading active, actor 61 /
  critic 80, payload mass exact, 2 PPO iterations in 4.1 s.
- 04:03:50 Kaggle universal pair pushed, kernel shawnxiang9527/microduck-fk-uni-a (paired): fk-uni-a from fq2 1999
  (seed 1, GPU 0), fk-uni-b from walk61 (seed 2, GPU 1); delta universal2, no-pack compile + payload, 4096 envs, 5000
  iterations, 100 critic warm-up, max-lr 3e-4, saves every 250, cap 10 h, reward guard off, track guard 2.0 (its
  0.03 m/s stepping floor). Expected end about 10:45 (5000 iterations at about 0.21 it/s), at the latest 14:05 (cap).
  Status RUNNING at 04:09, 04:14, 04:19, 04:28.
- 04:30 Bend incentive audit of Pollen's ground-pick reward (`bend_audit.py`, out/bendaudit_base_*.json) FAILS at every
  load (stand / intended 1.06 none, 1.21 full, 1.17 batteries out). Redesign priced offline (`bend_design.py`,
  out/bend_design.json): delta bend2 = two mouth-height costs at -240 (`bend_terms.py`), rm_bend_chosen.json.
- 04:44-04:55 Live confirmation (out/bendaudit_chosen_*.json), PASS at every load, equal to the priced numbers:
  none stand 0.439, half 0.073, stay 0.171 (intended 6.12 per s); full stand 0.592, half -0.013, stay 0.154, sit back
  0.153 (3.05); batteries out stand 0.521, half 0.125, stay 0.235, sit back 0.034 (3.81). Gate recorded:
  `audit_gate.py record bend2` PASS; kaggle_flight.py also checks BEND_MODS_CHOSEN equals rm_bend_chosen.json.
- 04:55 Mac mini 2-iteration bend smoke (out/bend_smoke.json): GroundPick task, delta bend2, mouth_high_at_hold,
  mouth_low_at_rest and torque_margin active, actor 61 / critic 78, groundpick61 loaded, payload mass exact,
  2 PPO iterations in 4.6 s.
- 04:56 Kaggle bend pair push refused: "Maximum batch GPU session count of 2 reached" (scratch pair + universal pair).
  Quota 10.54 h used, 19.46 left. Bend pair goes up when the scratch pair ends (about 05:33).
- 05:02 Gap found before launch: Pollen's ground-pick env never holds the crouch (phase passes 0.375-0.425 in 0.2 s),
  while PICKUP.md and the acceptance hold phase 0.33 for 4 s. Delta bend3 = bend2 plus the runtime's held crouch in
  half the envs (bend_terms.held_phase_cfg; a first version set class_type only, which mjlab ignores since the cfg's
  build() names its class: the audit's hold check read 0.000, that run discarded).
- 05:11 Bend acceptance probe in the training env (`bend_accept.py`, `mini_train_smoke.sh bendaccept`), checked on
  groundpick61 without the pack (eval/bendaccept_gp61_none.json): 11 envs held the full 4 s, mouth median 22.7 mm,
  trunk 34.0 deg, the runtime sim's numbers (PICKUP.md: 22 mm, 34-35 deg). Falls there (11 of 20, in the pre-stand,
  the descent and after hand-back) come from the training env's harsher randomisation; the falls line of the
  acceptance stays with style_probe.sh.
- 05:30 bend3 audit with the hold running (out/bendaudit_hold_*.json; 22-24 % of env-steps held, longest 4.04 s):
  PASS at every load. none stand -1.23, half 0.12, stay 0.34; full stand -2.36, half 0.27, stay 0.73, sit back 0.53;
  batteries out stand -1.80, half 0.19, stay 0.62, sit back -0.08. Gate recorded (bend3), smoke 2 iterations in 4.5 s.
- 05:44 Scratch pair ended (COMPLETE, 10 h cap at iteration 7400 of 12000, both seeds; fetched to
  kaggle/out/fk-scratch-s1). Training log at the end: reward 112 / 111, speed on moving commands 0.001 / 0.002 m/s:
  it learned to stand, not to walk. Reference probe on the Mac mini (final ONNX in both slots, full pack, 20
  episodes, eval/st_scr_*_pack_*.json): s1 walk 0 falls, speed 0.0001 m/s, leg p99 0.24; s1 stand 0 falls;
  s2 walk 0 falls, 0.0001 m/s, p99 0.34, saturation up to 20 %; s2 stand 0 falls. A stander that ignores the walk
  command: Pollen's recipe from scratch does not learn to walk with the pack in 7400 iterations. Reference only.
- 05:46:01 Kaggle bend pair pushed (`push_bend_when_free.sh`, after the scratch pair freed its session), kernel
  shawnxiang9527/microduck-fk-bend-a: fk-bend-a (seed 1, GPU 0) and fk-bend-b (seed 2, GPU 1), both from groundpick61,
  task Mjlab-GroundPick-Flat-MicroDuck, delta bend3, 4096 envs, 2500 iterations or 3 h, 100 critic warm-up, max-lr 3e-4,
  saves every 100, reward guard off, no track guard. RUNNING at 05:46. Expected end about 09:00 (3 h cap plus setup).
  Quota at 05:46: 12.20 of 30 h used, 17.80 left; universal pair up to about 8.3 h more and the bend 3 h fit.
