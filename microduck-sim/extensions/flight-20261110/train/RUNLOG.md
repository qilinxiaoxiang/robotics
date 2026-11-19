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
- 06:01 fk-bend-a ERROR at start, both jobs: "FileNotFoundError: /root/assets/init/groundpick61.onnx". Cause: the
  shared kernel_entry.py copies only assets/* and assets/manifests/* to /root/assets; the start policies added under
  assets/init/ never reached the kernel. The same applies to the universal kernel pushed 04:03: its pulled source shows
  fk-uni-a with --onnx /root/assets/init/fq2_1999.onnx and no init copy, so run A (from fq2 1999) died at start and
  only run B (from walk61, /root/assets/walk61.onnx) is training; the paired kernel stays RUNNING on B alone and its
  log is blind until the end. Fix in kaggle_flight.py's own copy of the entry (copies assets/init/*, records the list);
  the shared entry is unchanged. Pushed source of the new kernel checked: the init copy is in it, staged
  groundpick61.onnx sha ffbf5109 equals the local file.
- 06:04 Kaggle kernel shawnxiang9527/microduck-fk-uni-a2, paired: fk-uni-a2 (GPU 0) = universal run A exactly as
  approved (fq2 1999, universal2, 5000 iterations, cap 10 h, track guard 2.0, seed 1); fk-bend-a2 (GPU 1) = the bend
  run (groundpick61, bend3, 2500 iterations or 3 h, seed 1; the plan's one first run of about 3 h). One session for
  both, since run B holds the other session until about 10:45. Expected end of the kernel about 12:50 (5000 iterations
  at 0.21 it/s plus setup), latest 16:10 (cap); the bend job finishes about 09:15 but its output comes with the kernel.
  Quota estimate: 12.75 used + run B 4.7 + this kernel 6.9 = about 24.3 of 30 h, about 5.7 h left for seepick61.
- 06:06 Universal acceptance reference rerun on the Mac mini (`accept_universal.py run fq2_1999`, 36 cases, 20
  episodes each, eval/ua_fq2_1999_*.json; score out/accept_fq2_1999.json). fq2 1999: with pack 1 fall in 280, nominal
  walk 0.109 m/s, p99 0.46; no pack 2 walk falls of 80, walk 0.163 (above the 0.15 band), turns 0.299 / -0.302;
  partial loads 0 falls, walk 0.078-0.122, hip p99 at most 0.353; speed floor 0.15 missed at every pack load; toe-out
  18.4 / 14.6 (none), 21.9 / 21.3 (batteries out), 21.3 / 22.2 (full), step width 119-122 mm; head motion 0 falls
  with the pack and batteries out, 1 / 7 / 6 falls without the pack (scan, head pitch 0.5, 1.1). These are the
  same-machine references for the candidates.
- 06:19 fk-uni-a2 RUNNING 15 min after the push (GPU present, past setup); fk-uni-a (run B) RUNNING. A paired kernel
  stays RUNNING if only one of its jobs dies, so per-job health is known only at the end. Next: 10:45 fetch fk-uni-a
  (run B), 12:50 fetch fk-uni-a2 (run A and the bend), then `accept_universal.py run/score`, `accept_bend.sh
  fetch/runtime/env/video`, and the walk clips with the pack drawn.
- 11:30 Universal run B (fk-uni-b, from walk61, 5000 iterations) acceptance on the Mac mini, final (iteration 4999,
  ckpt/uni_b, sha aa1ad6de) and best by reward (about 4000, ckpt/uni_b_best, sha c51cd111); 36 cases, 20 episodes;
  scores out/accept_uni_b.json and out/accept_uni_b_best.json, reference fq2 1999 from the same machine. Verdict FAIL
  for both. Final / best / fq2: with-pack falls 92 / 83 / 1 of 280 (walk cases 5-20 of 20 each; stands, turns, stand
  shove and landing 0); nominal walk 0.162 / 0.143 / 0.109 (pass); walk torque p99 0.54 / 0.54 / 0.46 (limit 0.48,
  fail); no pack 0 / 0 / 2 falls (pass), walk 0.231 / 0.216 / 0.163 (section 5 band 0.082-0.15 fail; the band
  contradicts the section 4 floor 0.15); turns within 10 % (pass); load025 pass; load050 final fails on saturation
  3.7 %, best passes; load075 walk falls 12 / 2, sat 12.2 % / 5.3 % (fail); batteries out sat 5.1 % / 2.6 % (fail);
  load100 walk falls 17 / 16 at 5-10 s (fail); speed floor 0.15 final pass (min 0.151), best fail (0.139); toe-out
  means now within 12 / 9 at every load, but step width 117 / 113 mm at none / batteries out and p95 18.1 at full
  (final fail; best fails width at every load); head motion final 0/0/1 none, 0/1/12 batteries out, 0/18/20 full.
  Refutation: it walks (0.14-0.23 m/s at every load, stands 0.000); nominal and load100 manifests add 1.252 / 1.268 kg
  against 0.313 kg for none. Cause read from the numbers: walking with the heavy pack at 0.14-0.17 m/s drives leg
  torque into the clamp (sat 12-46 %) and it falls after 5-10 s. Clips (final): video/uni_b_walk_pack.mp4 (pack
  drawn from sim/out/visual/flightpack-nominal.json, falls backward at 7.8 s) and video/uni_b_walk_nopack.mp4 (no
  fall, 0.233 m/s, 3.5 m). Not run: clips of the best checkpoint; p99 for the shove and landing cases (flight_eval
  gives falls only). fk-uni-a2 untouched.
- 22:55 Universal run A (fk-uni-a2, from fq2 1999, universal2, 5000 iterations, "max_iters reached") and the bend
  run (fk-bend-a2, from groundpick61, bend3, stopped by the 3 h cap at iteration 1900) acceptance on the Mac mini,
  from the coordinator's download (no Kaggle refetch). Staged ckpt/uni_a (sha 82a7493c), ckpt/uni_a_best (0c96219f),
  ckpt/bend_a2 (81081369) and ckpt/bend_a2_best (704ee5d3; its weights equal the final's, only run_path differs, so
  every bend number is the same for both), fq2 1999 in the bend stand slot; reference ckpt/bend_gp61ref = the original
  groundpick61. The Mac mini was held by another session's fullflow sim from about 14:25 to 22:38; uni_a_best lost
  5 cases in that window, filled afterwards. accept_universal.py: the 0.099 and 0.07 speed lines dropped (the 0.15
  floor covers them, coordinator's decision), extra reference columns (--ref a,b,c). New score_bend.py; bend_accept.py
  records the leg pose at the lowest mouth sample, knee and ankle p99.
  Universal A final (out/accept_uni_a.json), FAIL: with-pack falls 37 of 280 (fq2 1, uni_b 92): comx+10 stand 5 and
  walk 19 at about 0.9 s (saturated from the first tick), walk shove 11, mass+10 walk 2; nominal walk, landing, turns 0.
  Walk p99 0.53 (limit 0.48). No pack 0 falls, 0.167 m/s, turns within 10 %. Loads 25/50/nobatt pass, 75 fails on
  saturation 1.08 % only, full pack walk 0 falls (uni_b 17). Speed floor pass (min 0.167). Toe-out means and p95
  within limits at every load, step width 123 mm (limit 105) fails at every load. Head motion 0 falls at none and
  batteries out, 3 at full (head pitch 1.1). Best (out/accept_uni_a_best.json), FAIL: 44 with-pack falls (walk
  shove 17, comx+10 walk 12, mass+10 walk 10), 3 no-pack walk falls, load050 saturation 1.4 %, full walk 2 falls.
  Bend (out/accept_bend_bend_a2.json, same for _best), FAIL: runtime no-fall 2 / 19 / 4 of 20 at full / batteries
  out / none, all falls 11.3-12.3 s, after the rise and the hand-back to the fq2 stander (original groundpick61: 0 of
  20 at every load, falls at 2.5 s in the descent with the pack, 10 s without); training env mouth within 3 cm in
  9/17, 7/17, 14/17 held episodes (medians 3.0 / 3.2 / 2.5 cm), trunk pitch 16 / 14 / 13 deg (limit 25-45; original
  34-44); runtime p99 hip 0.538 / 0.431 / 0.533, knee 0.538 at every load, ankle 0.538 / 0.394 / 0.38 (limit 0.50).
  The policy squats: knee at its 1.571 rad joint limit at the lowest point (median |q| 1.575 at every load, original
  0.58-0.63), hip pitch near 0, trunk 13-16 deg; trunk height 0.066 m against 0.117 standing. It did not straighten
  the knee. Clips: video/uni_a_walk_pack.mp4 (pack drawn, no fall, 0.177 m/s), video/uni_a_walk_nopack.mp4 (no fall,
  0.169 m/s), video/bend_a2_bend_pack.mp4 (seed 0, pack drawn, a squat with the head on the floor, no fall).

## Next round plan (2026-11-12, NEXT-PLAN.md; nothing launched)
- 00:35-03:20 The queued audits stalled: the universal3 batteries-out and no-pack jobs (five cases each) hit the
  590 s timeout without writing audit.json, and the queue waited for a verdict line that a timeout never prints.
  Fix: one case per job (`flight_audit.py --cases`), and the queue scripts now wait for another session's sims with
  a 60 min limit instead of ignoring the busy check.
- 03:23-04:52 universal3: stepping in place earned 0.843 of the walk at batteries out (FAIL) because the Gaussian
  tracking pays 0.89 at 0.03 m/s; added a capped progress-along-command term (weight 8). All 18 cases PASS at every
  load, worst 0.718 (out/audit3_u3e_*, out/audit3_u3efast_* for commands of 0.15-0.30 m/s); gate recorded.
- 04:55-05:34 bend4: in-episode hand-back to run A's walker (a quarter of cycles, 2 s) and a bend guard on task
  metrics, both checked on the Mac mini (guard test, 3-iteration smokes). Audit PASS at every load: squat -16.7 /
  -4.1 / -1.5 of the bend (bend3 paid it 1.72 / 1.00); gate recorded. Hand-back survival with every cycle handed back:
  13.4 / 9.5 / 3.1 stander falls per minute. No ankle cost: groundpick61 itself exceeds the robot's 1.25 rad stop.
  Kaggle 26.75 of 30 h used at 03:30 (another session's play-a kernel running), refresh 2026-11-14T00:00:00.

## History plan follow-up (2026-11-12 afternoon; code only, nothing launched)
- 13:30-14:00 New session. fk-uni3 (pushed 11:44 by the earlier session) still RUNNING. Added: history step scale in
  the worker (`--history-step-scale`, refused without it for a history actor; hook check 0 of 4 falls, same weight
  changes as the earlier 0.04 arm), `--hist-repeat` in both evaluators (checked on hist_m0 and fc_h_warm100),
  `screen_checkpoints.py` for the five decision cases per checkpoint, a template argument in `ckpt2onnx.py`.
  Details: HISTORY-PLAN.md section 8.


## AWS launcher (2026-11-12 evening; smoke only, no training run)
- 18:45-20:05 `train/aws_train.py` (+ `aws_boot.sh`, `aws_pull.py`, `AWS.md`): one spot GPU instance per run in
  us-east-1, self-terminating, dollar cap turned into a wall-clock limit from the current spot price, outputs pulled to
  the Mac mini (`~/code/microduck-train-aws/<run>/`) every minute, `--resume` from the newest checkpoint, `fetch` into
  `train/aws/out/<run>/`. No S3 and no instance role: the CLI user lacks `s3:CreateBucket`/`s3:PutObject` and
  `iam:CreateRole`/`iam:PassRole` (simulate-principal-policy), so the instance carries no credentials (AWS.md).
- Smoke `awssmoke1`, attempt 1 (i-0129118d7aca29401, g5.xlarge spot us-east-1f, $0.5058/h): setup 125 s (uv sync
  57 s; torch 2.9.1+cu128, CUDA on A10G, mujoco 3.10.0, warp 1.12.0), flight_worker packwalk from walk61 (exact,
  0.00 diff), 64 envs 6 iterations 1.23 s/it, then 4096 envs 12 iterations: 2.25-2.43 s per iteration (0.41 it/s),
  checkpoints model_0/4/8/11 and ONNX exported; command end -> final pull -> ack -> "Client.InstanceInitiatedShutdown"
  -> terminated, no volume left.
- Attempt 2 (`--resume`, i-06c2aed29ba8d77cf, same type and zone; the first try found no spot capacity anywhere):
  setup 476 s (uv sync 409 s, slow downloads), "[init] resumed from model_11.pt at iteration 11", iterations 12-15,
  then the command slept on purpose; the wall timer (720 s) powered it off: last pull 00:38:37Z, timer 00:39:34Z,
  InstanceInitiatedShutdown -> terminated.
- `stop` test `awsstop1` (i-010535f327607804d, g4dn.xlarge spot us-east-1d after seven g5 refusals): final pull,
  terminate by Run tag. `stop --run c3-carla` finds nothing (the filter needs Project=microduck-train).
- Smoke cost about $0.24 (about 31 instance-minutes, mostly g5.xlarge spot). Final `sweep`: billable none; free key
  pair microduck-train and security group microduck-train-ssh kept; no puller left; c3-carla still stopped.
- Cost basis for 1000 iterations at 4096 envs: g5.xlarge spot 2.4 s/it = 40 min + 2-8 min setup, about $0.40 at the
  current price ($0.51 at the 1.25x max price); Modal A10 ($1.42/h, fq2 ran 2000 iterations in about 80 min) about
  $0.95; Modal L4 ($1.117/h) has no measured rate here, $0.75 at A10 speed.

## Teacher-student round (2026-11-18; TEACHER-STUDENT-PLAN.md; Kaggle free quota, cap 10 h; sim only)
- 00:40-01:27 Code: `flight/teacher.py` (7 privileged actor columns, padded warm start, torch rebuild of an MLP ONNX),
  `flight/recurrent.py` (LSTM and single-step Mamba students, stateful ONNX `obs` + `state_in` -> `actions` +
  `state_out`), `flight/distill_worker.py` (DAgger, 100-tick BPTT, state carried across segments), delta
  `universal3t`, `flight_worker.py --distill`, `teacher_smoke.py`, `adapt_eval.py`, launcher flags and assets;
  `train/ts_round.sh`, `ts_audit_all.sh`, `ts_gate.sh`, `accept_head.py`. Start point chosen from the other
  session's acceptance (`out/accept_uni3_best.json`, `accept_uni3_1500.json`, `accept_uni_a.json`): run A final.
- 01:27-01:33 Mac mini smokes (CPU, 64 envs). Teacher: obs 68 / 80, privileged columns equal the simulator read
  (0.0), 68 % of walking env-steps carry a head command above 0.3 rad, iteration-0 export equals run A (0.0), 3 PPO
  iterations, trained export equals the torch actor (6e-7) (`out/teacher_smoke.json`). Distillation, 3 iterations
  of 100 ticks each: LSTM (306,830 parameters, state 512) and Mamba (277,134, state 9,728), ONNX equals torch over
  a sequence (2e-7, 3e-7) (`out/distill_smoke_{lstm,mamba}.json`); both smoke ONNX run through `flight_eval.py`
  with the state carried (they fall at 1.1 s, as 3-iteration students should).
- 01:33-01:49 Kaggle benches, 4096 envs, both COMPLETE, 0.42 h of quota: `microduck-ts-bench-t` (teacher PPO 0.19 to
  0.20 it/s; LSTM distillation 25 s per 100-tick iteration, 5.4 GB) and `microduck-ts-bench-mamba256` (Mamba 40 s
  at minibatch 256, 8.8 GB; 33 s at minibatch 512, 12.4 GB). After 12 iterations on run A's labels the Mamba
  student at minibatch 256 fell 1.36 times per env-minute against 1.42 for the teacher-driven envs.
- 01:33-02:09 Incentive audit of `universal3t`, 18 cases, PASS at every load, worst 0.748 (step in place,
  batteries out); gate recorded (`out/audit_ts_*`, `out/audit_tsfast_*`).
- 02:10 Session 1 pushed: kernel `microduck-ts-teach` = `ts-teach` (teacher, GPU 0) + `ts-ctrl` (one-frame control,
  GPU 1), both from run A final, 1000 iterations, learning-rate clamp 1e-4, `--max-hours 1.6`, saves every 250.
- 02:12 `adapt_eval.py` checked on the Mac mini with the bench Mamba student (`logs/adapt_benchmamba_full.log`).
- 02:15 Added head case on the start point (`accept_head.py`, walk with neck 0.5 rad and head yaw 0.6 rad): 0 falls
  of 20 at none / 25 / 50 / 75 % / batteries out / full, 0.164 to 0.178 m/s (`out/accept_head_uni_a.json`).
- 03:45 Session 1 COMPLETE, 1.58 h of quota (2.00 h used in total). Both arms reached iteration 999 (0.184 to
  0.186 it/s). Training log: teacher reward 80 -> 86, episode length 764 -> 838 steps, speed along the command 0.12
  -> 0.24 m/s; control reward 84 -> 63, episode length 757 -> 718, speed 0.12 -> 0.22.
- 03:47-04:09 Teacher gate, the intended walk alone in the teacher env (128 envs x 500 steps, 21 env-minutes per
  cell, so a cell holds only 3 to 18 falls; `out/ts_gate.json`). Falls per env-minute at full / batteries out /
  none: start 0.42 / 0.42 / 0.52 at 0.14 to 0.16 m/s; teacher 500: 0.52 / 0.47 / 0.42, control 500: 0.80 / 0.38 /
  0.33; teacher 750: 0.33 / 0.14 / 0.28, control 750: 0.61 / 0.80 / 0.56; teacher 999: 0.75 / 0.56 / 0.70, control
  999: 0.84 / 0.66 / 0.52. All trained checkpoints walk 0.22 to 0.30 m/s. Torque-margin cost per s at full: teacher
  -0.128 / -0.112 / -0.095, control -0.177 / -0.145 / -0.184 (start -0.087). Gate: passed at iteration 750 only (16
  falls against 42 over the three loads at equal speed); at 500 and 999 the teacher is not separable from the
  control on falls, and it keeps the lower torque cost at every iteration. Teacher used for the students:
  iteration 750 (`ckpt/ts_teacher/teacher.onnx`, sha256 3fb696c8763b0c97).
- 04:03 Session 2 pushed: kernel `microduck-ts-lstm` = `ts-lstm` (GPU 0) + `ts-mamba` (GPU 1), 240 iterations of
  100 ticks, minibatch 256, `--max-hours 2.75`. Expected end about 06:55.
- 04:10 Control-arm acceptance started on the Mac mini (`ts_accept.sh tsc_750 tsc_999`).
- 04:22 Kaggle kept session 2 QUEUED for about 19 minutes; RUNNING from about 04:22.
- 04:10-04:41 Control arm in the runtime simulation (`out/accept_tsc_750.json`, `out/accept_tsc_999.json`, both
  FAIL, 22 and 23 failed lines; start point `out/accept_uni_a.json` 10). The trained one-frame policies overshoot the
  0.25 m/s command (0.27 to 0.36 m/s; in the training env they walked 0.23 to 0.30) with the leg torque p99 at the
  0.54 N m clamp and fall: walk falls of 20 at none / 25 / 50 / 75 % / batteries out / full: iteration 750: 20 / 8 /
  3 / 1 / 5 / 6, iteration 999: 2 / 0 / 0 / 9 / 10 / 19, start point 0 at every load at 0.17 to 0.18 m/s. Same
  pattern as fk-uni3: the universal3 recipe trains a faster walk that the runtime simulation does not hold. The
  learning-rate clamp of 1e-4 did not prevent it. Table: `out/ts_compare.json` (`ts_compare.py`).
  `accept_universal.py score` crashed on a case with no upright episode (speed None); one comparison made None-safe.
- 04:43 Pipeline check, not a result: the 12-iteration bench Mamba student (labels from run A itself) in six runtime
  cases: stands (0 falls with and without the pack), walks 0.20 to 0.29 m/s and falls 18 of 20 in the nominal walk
  where run A falls 0 (`eval/ua_ts_benchmamba_*.json`). A coarse imitation does not carry run A's runtime behaviour.
- 07:10 Session 2 COMPLETE, 2.77 h of quota (4.77 h used in total, benches included). Both students reached
  iteration 240 (LSTM 0.0335 it/s = 30 s per iteration, 2.02 h; Mamba 0.0247 it/s = 40 s, 2.72 h), no stop fired.
  Student-driven envs at iteration 240 (training env, noise on half of them): LSTM 0.65 falls per env-minute at
  0.244 m/s, action error 0.0027 rad^2; Mamba 0.67 at 0.243 m/s, 0.0023 rad^2; the teacher-driven envs of the first
  32 iterations 1.25 and 0.82 at 0.24 m/s. Final checkpoints staged as `ckpt/ts_lstm` and `ckpt/ts_mamba` (the same
  ONNX in both runtime roles), acceptance started.
- 07:17 Evaluator fault found and fixed. `flight_eval.py::_StatefulSession` zeroed the state after every control
  tick without a policy call; the runtime Brain skips ticks on a dropped servo read (37 of 1000 ticks in a standing
  episode, `ts_statecheck.py`), so the recurrent state was wiped 38 times in 20 s. Right for a history window (the
  graph back-fills it), wrong for a recurrent state. Now a policy whose second input is named `state_in` keeps its
  state over gaps of up to 5 ticks (`RECURRENT_MAX_GAP`); history policies are unchanged. After the fix: 1 zeroing
  per episode (the start). The first student acceptance (before the fix) was stopped and redone with `--redo`.
  The same rule is needed in the robot runtime before a recurrent policy could ever run there.
- 07:24 With the state carried, six cases, falls of 20 (stand / stand no pack / walk / walk no pack / walk 50 % /
  walk comx+10): LSTM 2 / 0 / 16 / 20 / 6 / 20, Mamba 1 / 0 / 20 / 17 / 17 / 20; walking falls come 0.6 to 1.5 s
  after the walk command starts, speeds of the upright episodes 0.21 to 0.36 m/s, leg torque p99 at the clamp.
- 07:25 Diagnostic session pushed (not in the original plan, inside the quota cap): kernel `microduck-ts-lstm-a` =
  `ts-lstm-a` + `ts-mamba-a`, the same distillation with run A itself as the teacher (`ts_teacher_m0.onnx`, privileged
  weights zero), 140 iterations, `--max-hours 1.7`. Question it answers: do the students fall in the runtime
  simulation because of the teacher's faster gait (the control arm falls too) or because a recurrent student does
  not carry over to the runtime simulation at all.
- 07:52 Full acceptance with the state carried (dev seeds 0 to 19, `out/accept_ts_lstm.json`, `out/accept_ts_mamba.json`,
  side by side in `out/ts_compare.json`, head-command walk in `out/accept_head_uni_a.json`): LSTM student FAIL, 27
  failed lines; Mamba student FAIL, 25; control 750 FAIL 22; control 999 FAIL 23; start point (run A) FAIL 10.
  Walk falls of 20 at none / 25 / 50 / 75 / nobatt / full: start 0/0/0/0/0/0 (0.17 to 0.18 m/s); control 750
  20/8/3/1/5/6; control 999 2/0/0/9/10/19; LSTM 20/19/6/6/9/17; Mamba 17/15/17/13/15/20. Head-command walk
  (neck 0.5, yaw 0.6): start 0 everywhere; control 750 20/1/0/2/3/3; control 999 0/0/3/8/7/20; LSTM 20/18/8/12/9/17;
  Mamba 16/19/20/16/18/20. Standing: all 0 falls except full pack LSTM 2, Mamba 1. Every universal3-trained
  policy walks 0.19 to 0.36 m/s with leg torque p99 at the 0.54 N m clamp; the start point stays at 0.44 to 0.53.
  No policy of this round beats the start point; the recurrent students are worse than their one-frame control.
- 07:59 Adaptation time (`adapt_eval.py`, student in the training env against teacher 750, 50 Hz ticks,
  `out/adapt_<lstm|mamba>_<full|nobatt|none>.json`). Ticks until the action error settles after a reset: LSTM
  15 / 15 / 13, Mamba 13 / 14 / 10 (full / nobatt / none), about 0.2 to 0.3 s. After a push: LSTM 19 / 12 / 3,
  Mamba 21 / 6 / 2. After re-entry with a zero state while moving: LSTM 56 / 58 / 35, Mamba 42 / 37 / 33
  (0.7 to 1.2 s). Steady action error 0.033 rad with pack, 0.05 rad without.
- 08:06 No-memory control (`ts_nomem.py`, acceptance walk with `--hist-repeat`, state zero at every call, files
  `eval/un_<dir>_walk_<load>.json`): both students fall 20/20 at none, 50 %, batteries out and full pack, against
  20/6/9/17 (LSTM) and 17/17/15/20 (Mamba) with the state carried. The students do use their state; it does not
  make them walk better than the one-frame control.
- 09:05 Diagnostic session `microduck-ts-lstm-a` COMPLETE (1.64 h of quota; total for the round 6.41 h of the 10 h
  cap, `kaggle_flight.py quota`). Both arms reached iteration 140 with run A as the teacher: LSTM 0.0336 it/s, action
  MSE 0.0016, training-env falls 0.78 per env-min at 0.138 m/s (teacher 1.12); Mamba 0.0252 it/s, MSE 0.0010, falls
  0.73 (teacher 0.79). Staged as `ckpt/ts_lstm_a`, `ckpt/ts_mamba_a` (final ONNX + `model_140.pt`).
- 09:35 Full acceptance of the diagnostic students (`out/accept_ts_lstm_a.json`, `out/accept_ts_mamba_a.json`,
  `out/ts_compare.json`, `out/accept_head_uni_a.json`): Mamba from run A FAIL with 11 failed lines, LSTM from run A
  FAIL with 14, start point 10. Walk falls of 20 at none / 25 / 50 / 75 / nobatt / full: Mamba-A 0/0/0/0/0/0 at 0.17
  to 0.18 m/s, LSTM-A 0/0/0/0/0/9 at 0.17 to 0.19 m/s; head-command walk Mamba-A 0/0/0/0/0/2, LSTM-A 0/0/0/1/0/4.
  With pack: comx+10 walk 14 (Mamba-A), 18 (LSTM-A), start 19; walking shove 10, 16, start 11; mass+10 walk 5, 13,
  start 2. Reading: a recurrent student carries over to the runtime simulation when its teacher's gait does (the
  Mamba student matches run A line for line, the LSTM is weaker at full pack). The falls of `ts_lstm` and `ts_mamba`
  therefore come from the teacher they copied (iteration 750, the universal3 gait that also falls as the one-frame
  control), not from the recurrent core or the evaluator.

### Why the universal3-trained policies fall in the runtime simulation (2026-11-18 09:40 to 11:00, Mac mini CPU only)

Question: the one-frame control (`tsc_750`, `tsc_999`) walks in the training env and falls in the runtime simulation.
Method: the same ONNX in the runtime simulation with one difference switched at a time (`ts_sep.py`, 20 seeds, result
files `eval/sep_<dir>_<load>_<tag>.json`, logs `logs/ts_sep*.log`), then the opposite switch in the training env
(`ts_tsep.sh`, `flight_audit.py --delay-mods` and the case `walk025` = vx 0.25 held, 128 envs x 10 s, result files
`out/tsep_<name>_<load>_<tag>.json`).

Answer: the dead time of the control loop. The runtime simulation hands the policy readings that are one tick old
(joints and IMU, `--sensor-delay 1`) and applies each goal one tick later (`--action-delay 1`): 40 ms from measurement
to the servo. The training env delays only the command, 15 to 30 ms (`delay_min_lag 3`, `delay_max_lag 6` at 5 ms),
and reads joint positions with no delay. Taking 20 ms out of the runtime loop in any of three ways removes the falls.

- Runtime simulation, walk falls of 20, base / `--sensor-delay 0` / `--action-delay 0` / `--compensation` (the Brain
  extrapolates the stale reading; off by default in `walk_wired.py` and in the probe): `tsc_999` full pack 19 / 0 / 0 / 0;
  `tsc_999` batteries out 10 / 0 / 0 / 0; `tsc_999` no pack 2 / 0 / 0 / 2; `tsc_750` full pack 6 / 0 / 0 / 3;
  `tsc_750` batteries out 5 / 0 / 0 / 0; `tsc_750` no pack 20 / 7 / 5 / 4; LSTM student full pack 17 / 0 / 0 / 1; Mamba
  student full pack 20 / 0 / 0 / 1; LSTM student no pack 20 / 13 / 13 / 14 (it walks 0.39 m/s there, a second problem);
  start point full pack 0 / 0 / 0 / 0.
- Switches that do not remove the falls (`tsc_750` no pack / `tsc_999` full pack, base 20 / 19): no dropped reads 20 / 20;
  supply 8.2 V 14 / 15; servo current limit raised from 1.47 A to the training env's 1.75 A 20 / 19, and removed 20 / 18
  (leg torque p99 then 0.80 to 0.86 N m, so the 0.538 N m clamp is not the cause); friction 0.9 and 1.1 20 / 16 and
  20 / 19; floor friction 0.8 and 1.2 20 / 20 and 20 / 19; elliptic contact cone 20 / 19; earlier mass model 20 / 19;
  walk ramp 20 / 20; heading hold limited to the trained 1.0 rad/s 20 / 16; heading hold off 4 / 19 (without it the
  no-pack robot wanders 50 to 200 degrees in 15 s, so it is not a fix); goal clamp widened 13 / 10; command 0.20
  instead of 0.25 10 / 5; servo gain 250 16 / 9, 160 20 / 20.
- Leg torque at the clamp is a symptom of the delayed loop: with either delay off, p99 drops from 0.538 to 0.49 N m
  (`tsc_999` no pack) and from 0.534 to 0.45 to 0.46 N m (start point, full pack).
- Dead time against falls, runtime simulation at full pack (4 / 20 / 24 / 44 / 64 ms): `tsc_999` 0 / 0 / 0 / 19 / 20;
  `tsc_750` 0 / 0 / 0 / 6 / 20; start point 0 / 0 / 0 / 0 / 20 (at 64 ms every policy falls within 2 s, standing).
- Training env, falls per env-minute at vx 0.25 held, trained delays / 40 ms / 60 ms dead time: `tsc_750` no pack
  0.56 / 2.2 / 15.9 (80 ms: 42); `tsc_999` full pack 0.47 / 0.80 / 20.6; start point no pack 0.52 / 0.80 / 7.5 (80 ms: 30.3); start
  point full pack 0.75 / 1.45 / 16.1 (80 ms: 50.0). With the env's own sampled commands at 40 ms: 0.56 and 0.89, unchanged.
- Reading: both simulations have the same cliff, and the runtime simulation reaches it about 20 ms earlier (falls from
  44 ms; the training env from 60 ms). The start point sits below the cliff at the runtime's 44 ms; the universal3
  fine-tune, trained at 15 to 30 ms with fresh joint readings, bought its faster walk (0.27 to 0.36 against 0.17 m/s)
  with that margin. Where the 20 ms offset between the two simulations comes from is not found (same nominal dead time
  of 40 ms gives 19 of 20 falls in one and 0.8 per minute in the other; servo gain moves it, model, contact and torque
  limit do not).
- Consequence for the next recipe: train with the runtime's loop, joint and IMU readings one tick old and the command
  20 ms late, with margin toward 60 ms, and pick checkpoints on runtime-simulation falls, not on training-env falls.
  Turning on the Brain's compensation is a runtime change on the robot and was only measured here, not adopted.
- Tool changes for this study: `flight_eval.py` (FLIGHT_BRAIN_SET, FLIGHT_CFG_SET, diagnostics only), `ts_sep.py`,
  `ts_tsep.sh`, `ts_round.sh tdelay`, `train/delay/*.json`, `flight_audit.py --delay-mods` and the `--cases walk025`
  diagnostic case (never part of the launch verdict). One stale-connection stall of the Mac mini ssh at 09:36 was
  cleared by stopping the session's own local processes and rerunning.

### Round 2: teachers with the runtime loop delay (2026-11-18, TEACHER-STUDENT-PLAN.md section 8)

- 11:10 to 11:45 Step 1 check, training env against runtime ordering (128 envs, 10 s, full pack, vx 0.25 held, falls
  per env-minute, `tsc_999` / start point): 40 ms 0.80 / 1.45; 45 ms 2.16 / 2.11; 50 ms 4.92 / 3.94; 55 ms 10.3 / 8.3;
  60 ms 20.6 / 16.1 (`out/tsep_{c999,start}_full_w25{runtime,d45,d50,d55,d60}.json`). The ordering of the runtime
  simulation (44 ms: `tsc_999` 19 of 20, start point 0 of 20) is not reproduced at any dead time; both degrade
  together. With random pushes off `tsc_999` at 45 ms falls 0.19 per env-minute (`out/tsep_c999_full_np45.json`): the
  training env's falls under delay come with its pushes. The remaining no-push cells were stopped at 11:45 on the
  coordinator's instruction (speed first); the open offset is bracketed by two training arms instead.
- 11:46 Deltas (`flight_worker.py`): `universal4t` / `universal4` = universal3t / universal3 plus joint and IMU
  readings one tick old and a command lag of 4-9 physics steps kept 2 s per env (dead time 40-65 ms);
  `universal4tb` / `universal4b` the same with 7-12 steps (55-80 ms). Teacher smoke on the Mac mini with
  `universal4tb` passed (obs 68, export equal to the start policy, 3 PPO iterations; `logs/teacher_smoke.log`).
- 11:50 to 12:33 Incentive audit, 128 envs, 250 steps, start point as the intended walk, reward ratio of stand / shuffle /
  lean forward / lean back to the intended walk (limit 0.80): `universal4tb` full 0.64 / 0.61 / 0.58 / 0.60, batteries
  out 0.65 / 0.65 / 0.58 / 0.59, none 0.63 / 0.67 / 0.57 / 0.55; `universal4t` full 0.59 / 0.68 / 0.55 / 0.54, batteries
  out 0.60 / 0.68 / 0.54 / 0.51, none 0.61 / 0.67 / 0.54 / 0.53. PASS at every load for both
  (`out/audit_r2universal4t*_*.json`, gate `out/audit_gate.json`). The start point in these envs falls 8.3 / 5.7 / 4.5
  per env-minute (55-80 ms) and 2.4 / 0.8 / 1.3 (40-65 ms) at full / batteries out / none.
- 12:01 to 12:31 Second occurrence of the Mac mini ssh stall (first 09:36): the `universal4t` batteries-out audit had
  ended on the mini (file time 12:02) and the local ssh sat on a dead connection for 30 minutes until the coordinator
  stopped it. Fix: `train/ssh_guard.sh`, sourced by `ts_round.sh` and `mini.sh`: keepalives (15 s x 4), connect
  timeout 20 s, a local 640 s limit above the remote `timeout 590`, one retry after the mirror's remote jobs have
  ended. Checked with a forced over-limit call (ends at the limit, retried once, returns 142) and a normal call.
- 12:33 Kaggle, both private, one T4 each, both from run A final (`ts_start.onnx`), 1000 iterations, warm-up 100,
  learning-rate clamp 1e-4, save every 125, `--track-guard 2.0`, `--max-hours 1.6`: `microduck-ts2-teach-b`
  (`ts2-teach-b`, delta `universal4tb`) and `microduck-ts2-teach` (`ts2-teach`, delta `universal4t`). Both RUNNING at
  12:35; expected end about 14:10. Quota before the push 6.41 h of 30.
- 12:36 to 12:43 Runtime evaluator for teachers: `flight_eval.py` `_PrivSession` feeds a 68-input ONNX its seven
  privileged values from the simulator (payload kg from the manifests, trunk COM from the model, trunk velocity from
  the free joint). Check against the training env: full pack 0.9551 kg and COM (-0.0219, -0.0022, 0.0305) m against
  the env's 0.9551 and (-0.0215, -0.0023, 0.0304); no pack 0 kg and (-0.0335, 0.0007, 0.0186) against (-0.0327,
  0.0006, 0.0186). Selection cases (`ts2_pick.py`: runtime walk at none / batteries out / full / COM x +10 mm / 0.5 N s
  shove, falls of 20 each, `eval/pk_<dir>_<case>.json`, `out/ts2_pick.json`):
  round-1 teacher 750 14 / 13 / 18 / 20 / 20 = 85 of 100 (0.25-0.38 m/s, leg p99 at 0.538 N m);
  start point 0 / 0 / 0 / 19 / 11 = 30 (0.17-0.19 m/s); Mamba-A 0 / 0 / 0 / 14 / 10 = 24.
- 12:45 to 13:20 Incentive audit of the one-frame deltas `universal4` and `universal4b`: PASS at every load
  (`out/audit_r2universal4_*.json`, `out/audit_r2universal4b_*.json`). The Tailscale link to the Mac mini dropped
  from about 12:52 to 13:05; `ssh_guard.sh` ended the dead call within a minute, the retry also failed (connect
  timeout), the chain went on and the lost cell (`universal4b` full) was rerun at 13:12.
- 13:21 Push of the control pair (`ts2-ctrl` + `ts2-ctrl-b`) refused by Kaggle: "Maximum batch GPU session count of 2
  reached". It goes up when a teacher session ends. Paid compute (Modal, AWS) not used: the go-ahead reached this
  agent only as a relayed message.
- 14:03 `microduck-ts2-teach-b` COMPLETE (999 iterations, 0.189 it/s, 1.49 h); 14:10 `microduck-ts2-teach` COMPLETE
  (999 iterations, 0.193 it/s, 1.46 h). Quota 9.88 h of 30 after both. 14:03 control pair pushed into the freed
  session: `microduck-ts2-ctrl` = `ts2-ctrl` (`universal4`) + `ts2-ctrl-b` (`universal4b`), one-frame, same settings.
- 14:03 to 14:30 Teacher selection in the runtime simulation (`ts2_stage.sh`, `ts2_pick.py`; falls of 20 at none /
  batteries out / full / COM x +10 mm / 0.5 N s shove, total of 100, speed range of the upright walks;
  `eval/pk_<dir>_<case>.json`, `out/ts2_pick.json`). References: start point 0 / 0 / 0 / 19 / 11 = 30 (0.17-0.19
  m/s); Mamba-A 0 / 0 / 0 / 14 / 10 = 24; round-1 teacher 750 = 85.
  Teacher B (`universal4tb`, 55-80 ms), dirs `ckpt/t2b_<iter>`: 125 0 / 0 / 1 / 20 / 15 = 36; 250 1 / 1 / 0 / 20 / 7 = 29;
  375 0 / 0 / 0 / 20 / 3 = 23; 500 0 / 0 / 0 / 20 / 0 = 20 (0.25-0.38 m/s); 625 10 / 0 / 9 / 20 / 20 = 59; 750 98; 875 79;
  999 91.
  Teacher A (`universal4t`, 40-65 ms), dirs `ckpt/t2a_<iter>`: 125 0 / 0 / 1 / 19 / 11 = 31; 250 0 / 0 / 0 / 20 / 0 = 20
  (0.27-0.33 m/s); 375 14 / 0 / 0 / 20 / 17 = 51; 500 0 / 0 / 6 / 11 / 0 = 17; 625 0 / 0 / 0 / 17 / 6 = 23; 750 0 / 0 / 0 /
  20 / 0 = 20; 875 0 / 0 / 0 / 20 / 0 = 20; 999 0 / 0 / 0 / 0 / 0 = 0 of 100 (0.23-0.34 m/s, leg p99 still at 0.538 N m).
- 14:23 Students pushed before teacher A's later rows existed (rule: nominal walks at 0 falls first, then total; at
  that moment A-250 and B-500, both 20 of 100): `microduck-ts2-mamba` = `ts2-mamba` (teacher `ckpt/ts2_teacher` =
  A-250, env `universal4`) + `ts2-mamba-b` (teacher `ckpt/ts2b_teacher` = B-500, env `universal4b`), Mamba, 140
  iterations of 100 ticks, 2 epochs, minibatch 256, as `ts-mamba-a`. A-250 over A-500: A-500 is the only early
  checkpoint that walks COM x +10 mm better than the start point (11 against 19 falls) but drops the full pack 6 of
  20, and the rule puts the nominal walks first.
- 14:30 A-999 arrived: 0 falls of 100, the only checkpoint that holds the COM x +10 mm walk (0 of 20) and the
  shove, at 0.25 m/s with the full pack. It is the best teacher by the rule. Its students (`ts2-mamba-c` Mamba +
  `ts2-lstm-c` LSTM, teacher `ckpt/ts2a999_teacher`, env `universal4`) are pushed by `ts2_push_when_free.sh` the
  moment Kaggle frees a session (both are taken until about 15:40; running sessions are not cancelled). Reading: the
  shorter delay setting keeps improving in the runtime simulation with training, the longer one peaks at 500 and then
  walks faster than it can hold. The full acceptance set on teacher A-999 itself runs on the Mac mini meanwhile, as
  the ceiling for its students.
- 14:35 Coordinator asked to cancel `microduck-ts2-mamba` (A-250 and B-500 students) so the A-999 students start at
  once. Not done: the Kaggle CLI has no cancel, the SDK's CancelKernelSession needs a session id that no status or
  kernel call returns, a new version pushed to the same kernel was refused ("Maximum batch GPU session count of 2
  reached", the old session kept running), and Shawn's Chrome is not signed in to Kaggle. The remaining command,
  `kaggle kernels delete`, removes the kernel for good and waits for Shawn's own confirmation. `ts2_push_when_free.sh`
  keeps trying every 2 minutes (`logs/ts2_push_when_free.log`). `train/kaggle_cancel.py` is the lookup that found no id.
- 14:31 to 14:47 Full acceptance of teacher A-999 in the runtime simulation with its privileged inputs fed
  (`out/accept_t2a_999.json`, `eval/ua_t2a_999_*.json`, `eval/uh_t2a_999_*.json`; a teacher cannot run on the robot,
  this is the ceiling for its students): FAIL with 10 failed lines, none of them a walking fall. Walk falls 0 of 20 at
  none / 25 / 50 / 75 % / batteries out / full at 0.34 / 0.31 / 0.29 / 0.28 / 0.23 / 0.25 m/s (start point 0.17-0.18);
  head-command walk 0 falls at every load; with the pack COM x +10 mm stand 0 and walk 0 (Mamba-A 7 and 14), COM x
  -10 mm 0, mass +10 % 0 (Mamba-A 5), walking shove 0 (Mamba-A 10), turns 0. Failed lines: standing shove 2 falls,
  landing 1 (stand) and 1 (walk), walk torque p99 0.54 N m against 0.48, hip saturation share at 50 % / 75 % /
  batteries out (1.4 / 3.1 / 3.2 % against 1 %), toe-out at none / batteries out / full (right-foot p95 18 deg at
  none, left mean 13-14 deg with the pack; step width 95-101 mm passes).
- 14:48 Second seed set for the A-999 result (seeds 2000-2019, `eval/pk2_*.json`): A-999 COM x +10 mm walk 1 of 20,
  walking shove 0 of 20; A-875 COM x +10 mm walk 20 of 20 again (falls from 3.0 s). The step from 875 to 999 is not a
  seed accident.
- 14:35-15:39 Cancel of `microduck-ts2-mamba` (students of A-250 and B-500) asked by the coordinator, not possible from
  here: the CLI has no cancel, the SDK call needs a session id the API does not return (`kaggle_cancel.py`), a new
  version push is refused while two sessions run, and Shawn's Chrome is not signed in to Kaggle. `kaggle kernels
  delete` is a permanent deletion and was not run. The session keeps running (end about 16:05), so no quota was saved.
- 15:39:25 `microduck-ts2-ctrl` COMPLETE; `ts2_push_when_free.sh` pushed `microduck-ts2-mamba-c` (ts2-mamba-c on GPU 0,
  ts2-lstm-c on GPU 1; teacher A-999, delta universal4, 140 iterations, 1.7 h cap, seed 1) into the freed session and
  exited. RUNNING at 15:39:50, expected end by 17:25. Quota after the control pair: 12.29 h of 30 used.
- 15:45 Two rules for the rest of the round (coordinator, after the 14:23 push held a slot for 100 minutes):
  (1) a student or follow-up job is pushed only after every saved checkpoint of its teacher or control has been run on
  the selection cases; (2) a blocked slot is reported in one line with the time it clears by itself, never as a
  question whose only route is a permanent delete or a manual click.
- 15:40-16:27 Control pair (one-frame, same reward and loop delay, 1000 iterations each; `ts2-ctrl` universal4 5390 s,
  `ts2-ctrl-b` universal4b 5479 s) fetched and run on the selection cases (`eval/pk_c2a_*`, `pk_c2b_*`,
  `logs/ts2_pick_c2.log`). The first pass failed on every cell with KeyError 'observation_names': a one-frame run's
  `model_0.onnx` carries no metadata; `ts2_stage.sh` now takes the template as a fourth argument and the sixteen
  folders were rebuilt from `ckpt/ts_start/walk61.onnx`. Falls of 100 (none/nobatt/full/comx/shove):
  universal4: 125=39, 250=27 (0/0/0/20/7), 375=13 (0/0/4/0/9), 500=23 (1/0/0/7/15), 625=29, 750=61, 875=40, 999=54;
  universal4b: 125=34, 250=50, 375=42, 500=61, 625=77, 750=57, 875=53, 999=46.
  Control checkpoint: c2a_375 (13; the only one under the start point's 30 by a clear margin, and the only one that
  holds COM x +10 mm). Against it teacher A-999 has 0. The longer-delay control never beats the start point.
- 16:27 `microduck-ts2-mamba` COMPLETE (5720 s and 5735 s, 140 iterations each); checkpoints staged with
  `ts2_stage_student.py` as `ckpt/s2a_<iter>` (from A-250) and `ckpt/s2b_<iter>` (from B-500), selection cases running.
- 16:28-16:51 Selection cases on the first student pair (`eval/pk_s2a_*`, `pk_s2b_*`, `logs/ts2_pick_s2.log`), falls of
  100 (none/nobatt/full/comx/shove). Mamba from A-250: 20=29, 40=18 (0/0/0/14/4), 60=31, 80=22, 100=21,
  120=19 (0/0/0/18/1), 140=26. Mamba from B-500: 20=71, 40=47, 60=20, 80=26, 100=13 (0/0/0/11/2, but 0.07 m/s with no
  pack and 0.09 m/s at COM x), 120=32, 140=33. Both keep their teacher's COM x +10 mm failure (A-250 teacher 20 of 20
  there, B-500 teacher 20 of 20), so neither is better than round 1's Mamba-A (24) where it matters; the shove case
  did improve (1 to 6 of 20 against 10). These two are kept as reference rows only; s2a_120 gets a full acceptance.
- 16:52-17:20 Full acceptance of c2a_375 (control) and s2a_120 (`out/accept_c2a_375.json`, `out/accept_s2a_120.json`,
  `logs/accept_score_*.log`). Control c2a_375: 14 failed lines; with the pack mass +10 % walk 4 falls, walking shove 9,
  walk landing 6, stand landing 1, full-pack walk 4 of 20 (falls at 2.5-2.6 s), 50 % load stand 8, head-down walks 1
  at none and 4 + 8 at full pack, torque p99 0.54, toe-out at three loads. Student s2a_120: 9 failed lines; COM x
  +10 mm walk 18 falls, head-down walks at none 2 + 13, torque p99 0.54, hip saturation and toe-out lines; no other
  falls.
- 17:25 `microduck-ts2-mamba-c` COMPLETE (6154 s; Mamba reached iteration 132 at the 1.7 h cap, LSTM 140). Quota read
  at 17:48: 14.44 h of 30 used. Checkpoints staged as `ckpt/s2c_<iter>` (Mamba) and `ckpt/l2c_<iter>` (LSTM).
- 17:26-17:48 Selection cases on the students of teacher A-999 (`eval/pk_s2c_*`, `pk_l2c_*`, `logs/ts2_pick_c999.log`),
  falls of 100 (none/nobatt/full/comx/shove). Mamba: 20=34, 40=26, 60=20, 80=20 (0/0/0/14/6), 100=13 (1/0/6/1/5),
  120=29 (0/0/1/20/8), 132=17 (0/0/0/12/5). LSTM: 20=56, 40=20 (0/2/0/7/11), 60=26, 80=22, 100=77, 120=23, 140=22
  (0/0/2/9/11). The teacher's 0 of 100 is not reproduced: the best students sit at 13 to 20, about where the first
  pair's students and the control are, and the COM x and shove cells swing from checkpoint to checkpoint
  (COM x 1, 20, 12 of 20 at Mamba 100, 120, 132).
- 17:49 Full acceptance started on s2c_132, s2c_100 and l2c_40, then adapt_eval of s2c_132 at full, nobatt and none
  and the comparison table.
- 17:50-17:59 Continuation of both A-999 students (coordinator: in the training env the Mamba student already matches
  the teacher, action error still falling). `distill_worker.py` got `--resume-pt`: weights from a saved
  `model_<iter>.pt`, iteration count kept, the first `--warmup-iters` iterations teacher-driven without updates (the
  baseline the task-metric stop needs), then beta 0, learning rate from `--lr` at the resume iteration to `--lr-final`
  at `--max-iters`; saves now carry the optimizer state. The two files to continue were saved without it, so Adam
  starts fresh. Smoke on the Mac mini (`ts2_resume_smoke.sh`, 64 envs, `logs/resume_smoke_mamba.log`, `_lstm.log`):
  Mamba resumed at 132 and ran 133-135, LSTM at 140 and ran 141-143, ONNX export 1e-6 from the torch student; both
  ended on the task-metric stop, which at 64 envs compares against a teacher baseline of 0 falls in 2 env-minutes.
  17:59:01 pushed `microduck-ts2-mamba-d` (ts2-mamba-d from `s2c_132`, lr 2.46e-4; ts2-lstm-d from `l2c_140`, lr 2e-4;
  both to iteration 300, lr-final 5e-5, saves every 20, warmup 2, 2.3 h cap, otherwise the settings of the first
  run). Expected end by 20:25.
- 18:10 INCIDENT: the Mac mini kernel-panicked (watchdog timeout from memory thrashing) and rebooted. Cause, mine:
  the acceptance batch (s2c_132, s2c_100, l2c_40), check B (`ts2_bcheck.py`) and the resume smoke ran there together;
  `mini.sh run` only waited for other agents' simulations and let this mirror's own jobs overlap. 18:07 reading by the
  coordinator: swap 20.56 of 20.99 GB, load 21 to 47, 33 simulation python processes on 16 GB RAM. All jobs there
  were lost; result files already written stayed. The acceptance chain was stopped at 18:09 before the reboot.
- 18:12-18:15 Limit put where jobs start: `mini_lock.sh` on the mini (lock file `~/.flight-mirror-sim.lock` with the
  holder's pid, stale lock cleared, waits up to 90 min; then a pre-flight that refuses with exit 4 when swap used is
  over 4096 MB or more than 10 simulation pythons run, after six looks 30 s apart). `mini.sh run` takes the lock
  for every command, `ts_round.sh` and `ts2_resume_smoke.sh` run each job under `mini_lock.sh run`, and
  `flight_eval.py` caps its pool at 8 workers. Tests: forced swap reading 5000 MB gave "REFUSED", exit 4, nothing
  started, lock released; a planted lock of a dead pid was cleared; a second `mini.sh run` started 5 s after the
  first one ended. Readings after the reboot (18:15): swap 0 MB used, load 4.87 / 14.90 / 9.04, no simulation
  python left, no orphan workers. `mini_cut.sh` stops this mirror's jobs and orphan workers by hand.
- 18:16 Check B restarted alone (cells with a result file are skipped); the acceptance batch follows it, one job at
  a time.
- 18:22 Check B done (`ts2_bcheck.py`, `eval/bc_*.json`, `out/ts2_bcheck.json`, `logs/ts2_bcheck.log`); falls of 20 at
  COM x +10 mm walk / walking shove, runtime simulation, selection seeds. Mini after it: swap 1801 MB used, load 10.
  B1 teacher A-999: as is 0 / 0; privileged inputs set to the no-pack constants 20 / 20 (falls at 0.4-0.6 s); payload
  and COM set to no-pack with the true velocity 20 / 20 (0.5-1.0 s); all seven zero 20 / 20 (0.7-0.8 s). Both cases
  carry the full pack, so this is a 0.94 kg error in the payload input: the teacher cannot walk on grossly wrong
  inputs; the precision it needs is the next entry.
  B2 student s2c_132 (as is 12 / 5): dropped servo reads off 0 / 0; sensor delay 0 20 / 20 (falls 3.2-4.2 s); action
  delay 0 20 / 20 (3.4-4.0 s). Student s2c_100 (as is 1 / 5): dropped reads off 0 / 20 (all at 1.2 s, before the
  shove); sensor delay 0 1 / 0; action delay 0 0 / 0. The one runtime ingredient the training env lacks and s2c_132
  is sensitive to is the dropped servo read (--drop 0.036: the Brain skips that tick, the recurrent state is not
  stepped and the last action is held). The delays are trained in; removing them breaks s2c_132. s2c_100 does not
  follow the same pattern (it falls at 1.2 s with reads never dropped), so single checkpoints differ in kind.
  B3 student s2c_132 with teacher A-999 driving the first 100 ticks (2 s) then released: 8 / 4, falls from 8.5 s;
  first 250 ticks (5 s): 6 / 2, falls from 8.5 s. A teacher-driven start does not remove the falls and they come
  seconds after the release, so they are not the student's first-seconds load inference.
- 18:22-18:27 Precision of the teacher's privileged inputs (`ts2_bprec.py`, `eval/bp_t2a_999_*.json`,
  `out/ts2_bprec.json`; teacher A-999, full pack, falls of 20 at plain walk / COM x +10 mm walk, one input group
  changed, the rest true). Sanity: no pack with the no-pack constants 0 of 20 at 0.34 m/s (the replacement is right).
  Payload input x 0.9: 0 / 0; x 0.75: 0 / 0; x 0.5: 0 / 0 (speed down to 0.16 / 0.20 m/s). Trunk COM x input
  -5 mm: 10 / 20; -10 mm: 20 / 20; +5 mm: 0 / 0. Velocity inputs zeroed: 20 / 20 (falls 1.3-2.6 s). So the payload
  mass may be off by half, the COM x must not read more than a few mm further back than it is, and the trunk velocity
  is needed throughout.
- 18:23-18:30 Dropped servo reads in the distillation (coordinator's decision after check B). The runtime simulation
  drops each tick independently (`brain_sim_check.py` line 1356, `rng.random() >= args.drop`), so no extra bursts
  were added. `distill_worker.py --drop-max 0.08`: per env a drop probability uniform in 0 to 0.08, redrawn at reset
  (robot: 0.036, `CURRENT-STATE.json` servo_read_drop_fraction); on a dropped tick the student is not called, its
  state is kept, the previous action stays applied; state zeroed after more than 5 skipped ticks as the evaluator
  does; the teacher labels every tick, the loss counts only the ticks the student ran. It is a worker flag on the
  audited env universal4, not a new delta (the env and its rewards are unchanged, so no new audit). Smoke through the
  lock (`ts2_drop_smoke.sh`, `logs/drop_smoke_scratch.log`, `_resume.log`): dropped-tick fraction 0.039 to 0.047
  (mean of the draw 0.04), ONNX within 1e-6 of the torch student, scratch 3 iterations, resumed 133-136.
  18:30:27 pushed `microduck-ts2-mamba-e` (GPU 0 ts2-mamba-e: Mamba resumed from `s2c_132`, beta 0, to iteration 292,
  lr 2.46e-4 to 5e-5; GPU 1 ts2-mamba-f: Mamba from scratch, 160 iterations, beta over 30; both --drop-max 0.08,
  saves every 20, 2.3 h cap). RUNNING at 18:30:50, expected end by 20:55. Quota read 14.98 h of 30. The no-drop
  continuation `microduck-ts2-mamba-d` keeps running as the comparison.
- 18:31 Mac mini queue, one job at a time: teacher A-999 on the three timing switches, then the acceptance batch.
- 18:31-18:36 Teacher A-999 on the three timing switches (`eval/bc_t2a_999_*_{nodrop,sdelay0,adelay0}.json`), falls of
  20 at COM x +10 mm walk / walking shove: dropped reads off 0 / 0; sensor delay 0 20 / 20 (falls at 3.0 s and
  8.2-8.4 s); action delay 0 20 / 20 (3.0-3.1 s, 8.3 s). The teacher itself needs the loop delay it was trained
  with, so a student cannot be asked to hold with a delay removed; the switch that separates students from the
  teacher is the dropped read alone.
- 18:37 Division of work from Shawn's word at about 18:35 (evaluation may leave the Mac mini): the main session
  selects the checkpoints of `microduck-ts2-mamba-d` and `-e` on Modal; here the Mac mini runs only the acceptance of
  s2c_132, adapt_eval and the comparison table (s2c_100 and l2c_40 acceptance dropped). Two watchers fetch and stage
  the Kaggle checkpoints as `ckpt/s2d_*`, `l2d_*` (no drops) and `s2e_*` (resumed, drops), `s2f_*` (scratch, drops).
- 18:37-18:47 Student s2c_132 (Mamba of teacher A-999, iteration 132, no drops in training), one job at a time; mini
  after it: swap 1066 MB used, load 4.
  Full acceptance (`out/accept_s2c_132.json`, `logs/accept_score_s2c_132.log`): FAIL, 21 failed lines. With the pack:
  COM x +10 mm walk 12 falls, walking shove 5, mass +10 % walk 4 and stand 2, COM x stand 2, standing shove 2, both
  landings 2, nominal stand / walk / turn left / turn right 1 each; torque p99 0.54; hip saturation at 25, 50, 75 %
  and no battery; toe-out at three loads (left mean 13-14 deg, right 4-5). No falls in the per-load walks
  (0.32 / 0.31 / 0.26 / 0.25 / 0.26 / 0.27 m/s from no pack to full) or the head-command walks.
  adapt_eval in the training env universal4, pushes off, 64 envs (`out/adapt_s2c132_{full,nobatt,none}.json`):
  after a reset the action error settles in 7 to 11 ticks (0.14-0.22 s) to 0.042-0.057 rad with 0 falls; after the
  0.26 m/s push 3 to 24 ticks with 4, 6, 5 falls of 64; after re-entry with an empty state 35 to 48 ticks (0.7-1.0 s)
  with 3, 4, 1 falls. Round 1's students settled to about the same error; the falls after the push are the gap.
  Comparison table `logs/ts2_compare.log`, `out/ts_compare.json` (uni_a start point, ts_mamba_a, c2a_375 control,
  t2a_999 teacher, s2a_120, s2c_132): failed lines 10, 11, 14, 10, 9, 21.
- 19:59 `microduck-ts2-mamba-d` COMPLETE (6985 s; no-drop continuation, both arms reached iteration 300). In the
  training env (`kaggle/out/ts2-mamba-d/runs/*/progress.csv`): Mamba action error 0.0036 at 140 to 0.0030 at 300,
  falls 1.13-1.20 per env-min, speed 0.23; LSTM 0.0049 to 0.0038, falls 1.22-1.39. The teacher baseline of a resumed
  run comes from its two warm-up iterations only (0.16 and 0.14 falls per env-min) and is not comparable with the
  first run's whole-run baseline (1.29). Staged without Mac mini work: `ckpt/s2d_{140..300 step 20}` (Mamba, nine)
  and `ckpt/l2d_{160..300 step 20}` (LSTM, eight); their selection runs on Modal in the main session. Quota read:
  17.91 h of 30 used.
- 20:25 `microduck-ts2-mamba-e` ended as ERROR: the resumed arm on GPU 0 (ts2-mamba-e) died with exit -11 (segfault)
  69.6 s after its start, while the simulator's GPU kernels were compiling and before the worker reached the student
  (`kaggle/out/ts2-mamba-e/job_record.json`, `train_ts2-mamba-e.log` ends in the kernel-compile lines). Not the
  resume code; the same code path ran in the smoke and the two arms compile into one kernel cache at the same time.
  The from-scratch arm on GPU 1 (ts2-mamba-f, drops 0 to 0.08) finished its 160 iterations in 6682 s: dropped-tick
  fraction 0.040, action error 0.029 at 20 to 0.0041 at 160 and still falling, falls 1.28 per env-min against the
  teacher's 1.25, speed 0.229 against 0.232. Staged as `ckpt/s2f_{20..160 step 20}` (eight); selection on Modal in the
  main session. Quota read: 18.32 h of 30.
- 20:26:57 pushed `microduck-ts2-mamba-g`: GPU 0 ts2-mamba-g, the lost arm again (Mamba resumed from `s2c_132`, drops,
  beta 0, to iteration 292, lr 2.46e-4 to 5e-5); GPU 1 ts2-mamba-h, the scratch student continued from `s2f_160`
  (drops, beta 0, to iteration 320, lr 2e-4 to 5e-5). Saves every 20, 2.3 h cap, expected end by 22:50.
- 22:28 `microduck-ts2-mamba-g` COMPLETE (7085 s, both arms rc 0, both reached their last iteration; dropped-tick
  fraction 0.039-0.040). In the training env: ts2-mamba-g (resumed from `s2c_132`, drops) action error 0.0039 at 140
  to 0.0032 at 292, falls 1.21-1.34 per env-min, speed 0.23; ts2-mamba-h (scratch student continued, drops) 0.0035 at
  180 to 0.0031 at 320, falls 1.20-1.28, speed 0.23. Staged as `ckpt/s2g_{140..280 step 20, 292}` (nine) and
  `ckpt/s2h_{180..320 step 20}` (eight); selection on Modal in the main session. Quota read: 20.33 h of 30 used,
  9.67 h left; nothing is running on Kaggle or on the Mac mini.
- 22:40-22:45 Diagnostic, no training: does stepping the recurrent state across dropped ticks remove the forward-COM
  falls? `flight_eval.py` FLIGHT_CATCHUP=1 (recurrent policies only, default off): after g - 1 skipped ticks
  (1 < g <= 5) the session is first run g - 1 times on the cached previous observation, state fed through, actions
  discarded. One Mac mini job through the lock (`ts2_catchup.py`, `eval/cu_*.json`, `out/ts2_catchup.json`), walk,
  `--stand-s 0`, seeds 0-19; swap after it 1679 MB, load 8. Falls of 20 with the switch | without (Modal reference):
  s2d_300 COM x +10: 8 (1.7, 2.3, 2.6, 2.8, 3.2, 3.2, 3.4, 17.6 s) | 7 (0.7, 0.8, 2.3, 2.4, 2.7, 3.2, 10.3 s)
  s2g_140 COM x +10: 2 (3.1, 3.4 s) | 4 (3.1, 3.2, 3.4, 7.8 s)
  s2g_200 COM x +10: 7 (0.8, 1.2, 2.7, 2.8, 2.8, 8.9, 12.0 s) | 6 (0.7, 0.8, 2.7, 3.5, 5.3, 10.7 s)
  s2g_200 COM x +10, drop 0.072: 13 (0.8 to 12.5 s) | 14 (0.8 to 16.2 s)
  s2g_200 full pack plain walk: 0 at 0.255 m/s | 0 at 0.250 m/s (the switch does not break normal walking)
  Answer: no. The counts move by one or two episodes in either direction, which is the host difference and seed
  noise; the falls still scale with the drop rate. The stale state is not what makes the students fall on dropped
  ticks; what is left is the held action itself (a 20 ms longer hold that the stateless teacher tolerates and the
  students do not). Whether the switch fired was not instrumented; the episodes differ from the reference runs.
- 22:05-23:00 Cause study, no training: why do the students fall at forward COM with dropped reads while teacher
  A-999 does not? Runtime simulation, walk, comx+10, `--stand-s 0`, seeds 0-19, drop 0.036 unless stated; Mac mini,
  one job at a time through the lock, 8 workers. New default-off switches in `flight_eval.py`, each with counters in
  the episode record (`diag_stat`): FLIGHT_SHADOW=1 (the teacher's action computed beside the student's on every
  called tick, from the same observation plus priv_now()), FLIGHT_SWAP=teach_after:N / student_after:N /
  teach_rand:N:p / teach_noise:s; FLIGHT_HANDOVER and FLIGHT_CATCHUP now count their ticks too. Scripts
  `ts2_cause.py` (cells `eval/cz_<dir>_<cell>.json`, not committed, 13-21 MB for the shadow cells),
  `ts2_cause_analyse.py`, `ts2_parity_env.py` + `.sh` (distillation env universal4, 4 envs, a held action on ticks 30
  and 50). Results: `out/ts2_cause_swap.json`, `out/ts2_cause_shadow.json`, `out/ts2_cause_parity.json`.
  Check 2, causal swap, falls of 20 (s2g_200 | s2d_300); every switch fired (335-664 windows per cell, counters in
  the file): student alone 7 | 8 (drops off 0 | 0); teacher on the 1 tick after every skip 5 | 11; on the 3 ticks
  after every skip 4 | 10; teacher on 3 ticks at random times at the same rate 8 | 10; reverse (teacher drives,
  student on the 3 ticks after every skip, 10 % of the ticks) 0 | 0. The ticks after a skipped tick are not where
  the falls are made.
  Check 1, shadow log: leg-joint |student - teacher|, median / p90 rad, surviving episodes: s2g_200 first tick after
  a skip 0.053 / 0.138, second 0.054 / 0.140, third 0.052 / 0.135, no skip in the last 10 ticks 0.051 / 0.130, drops
  off 0.048 / 0.117; s2d_300 0.068 / 0.174, 0.057 / 0.154, 0.056 / 0.147, 0.055 / 0.139, drops off 0.043 / 0.121
  (falling episodes within 0.01 of these). Time from the last skipped tick to the fall 0.02 to 1.2 s, no joint
  repeats as the largest difference (knees 3 and 3 of 7 and 8). Where the falls are: 5 of 7 and 7 of 8 before 4 s
  (0.7 and 0.8 s on seeds 0 and 11 for both students, the rest of the early ones at the walk start 2.4-3.6 s).
  By window, student driving, drops on: standing start 0-2 s p90 0.26 | 0.22 rad and the robot moves forward at 0.084
  | 0.087 m/s on a zero command (drops off 0.096 | 0.128); the teacher driving the same start stands at 0.006 m/s and
  the students' p90 on the teacher's path is 0.045 | 0.042. Walking from 4 s: student path 0.131 | 0.144, teacher's
  path 0.088 | 0.087.
  Check 3, observation parity at a skipped tick (line references in `out/ts2_cause_parity.json` `reading`): the
  last-action slot is the policy's last output in the runtime and the held applied action in training, equal (0.0
  difference on 17 after-skip ticks and on the held env ticks); joint and IMU readings are one tick old after a skip
  as on any tick (runtime joint-sum residual 0.0016 at one tick of age against 0.30-0.34 at zero or two; gravity
  0.0034 against 0.026; env joint residual lowest at one tick); the sensor queue advances on the skipped tick and
  the held goal is appended to the action queue again, nothing lost. One difference: the runtime's turn command
  (heading hold) steps by a median 0.040 rad/s after a skip against 0.022 on other ticks; training keeps the command
  constant. It is there with drops off as well (0 falls). Constant, not skip-related: joint velocity is 2 ticks old
  in training and 1 in the runtime simulation, for the teacher too.
  Beyond the three checks: teacher with Gaussian action noise 0.08 rad (the students' error size) and drops: 0 of 20;
  0.15 rad: 16 of 20 with drops, 12 without (first fall 2.9 s, none in the standing start). Teacher drives the first
  100 ticks (2 s), then the student alone: 1 | 2 of 20 (4.1 s | 13.2, 16.0 s); first 200 ticks: 1 | 5 (6.9 s | 10.7,
  12.2, 16.6, 17.4, 18.2 s).
  Reading: the students' falls at forward COM with drops are mostly a cold-start effect. Starting with an empty
  state at forward COM the student leaves the teacher's path within the first second (it steps forward where the
  teacher stands) and stays marginal through the walk start; a dropped tick in that stretch tips it (inference: the
  drop is a plain disturbance there, as it is for the noisy teacher, 16 against 12). With the start taken away
  s2g_200 (trained with drops) is left with 1 of 20, s2d_300 (trained without) with 2 to 5 in steady walking.
  Not established: why the cold start goes wrong (COM not yet inferred from history, or a start state the
  distillation env does not produce); the handover result with these 20 seeds only.
- 23:05-23:50 Cold-start study, no training: why does s2g_200 move forward at zero command in the first 2 s at COM x
  +10 mm? Result file `out/ts2_cause_start.json` (`ts2_start.py`, `ts2_start_env.py` + `.sh`,
  `ts2_start_analyse.py`; cells `eval/cz_s2g_200_*.json` and `eval/cz_start_env_*.json`, not committed). New
  default-off switches with counters: `flight_eval.py` FLIGHT_STATE_DUMP / FLIGHT_WARM (save the recurrent state at
  the end of an episode without a fall, start an episode from it), `payload.py` key `com_x_fixed_whole_m`
  (diagnostic envs only). Mac mini, one job at a time through the lock; env runs on its CPU, 256 envs.
  B, runtime simulation, comx+10, drop 0.036, seeds 0-19, forward speed over 0-2 s at zero command and falls of 20:
  empty state 0.084 m/s (first half second 0.160), 7 falls; state of the same seed's finished comx+10 episode 0.005
  m/s, 0 falls in the whole 20 s (20 of 20 states loaded); teacher 0.006, 0. Empty state at other loads: nominal
  0.024 (0.070 in the first half second), 0 falls; no pack 0.007, 0 falls. Zero command for the whole episode,
  empty state: 0.084 m/s in the first 2 s, then under 0.001 for the remaining 18 s, 2 falls (0.70, 0.82 s); warm
  state 0 falls. A state saved at the end of no-pack episodes and used at comx+10: 20 of 20 fall forward at
  0.54-0.58 s. So the state carries the load and COM, the right one removes the creep and every fall, a wrong one
  drops the robot at once, and an empty one costs about 1.5 s of forward steps that grow with the forward COM.
  A, coverage (line references in the file's `training_env.reading`): zero twist on 9.0 % of ticks in the first 8 s
  of a fresh env and at 19.4 % of resets (248 resets; config 0.25 standing x 0.85); the student's state is zeroed at
  every reset; reset = default pose, zero velocity, released at 0.12-0.15 m (the runtime starts at the Brain's
  stand pose on the floor, neck pitch 0.099 rad off the default); COM: the runtime's comx+10 is trunk COM x -6.4
  mm, +11.5 mm in the env's whole-robot terms against a range of +-12 mm: 4 of 300 full-pack draws at or beyond
  it, 28 of 300 beyond +10 mm. Measured in the env, full pack, zero twist, zero head and body commands, empty
  state, 256 envs, 2 s: COM x +11.5 mm student 0.004 m/s, 1 fall (with drops 0.003, 2 falls), teacher 0.001, 0;
  reset on the floor instead of released: student 0.007, 1 fall (with drops 0.008, 4), teacher 0.003, 0; COM x 0:
  student 0.007 and 0.004 on the floor, 1 and 3 falls. The env does not reproduce the creep (0.004-0.008 against
  0.084 m/s). The runtime simulation started the env's way (released 2.5-3.5 cm above the floor, up to 5 deg tilt):
  student 13 of 20 fall, 12 before 2 s; teacher 0.
  Verdicts: A refuted for the four coverage items (they are in the distillation data and the student handles them
  in the env); B supported (the empty state is necessary for the fault and the state is what holds the load).
  Open: the same empty-state start is harmless in the env and harmful in the runtime simulation; which runtime
  difference does that (start pose or loop timing) is not separated.
- 23:20-23:50 Warm-up rule without a privileged teacher, no training: refuted. New default-off switches in
  `flight_eval.py`: FLIGHT_WARMUP="<61-input onnx>:<ticks>" (that policy drives the first ticks while the student
  sees every observation; counters `warmup_driver_ticks`, `student_ticks`) and FLIGHT_VX02=1 (episode field
  `vx_0_2s`, trunk forward speed over the first 2 s). Runner and summary `ts2_warmup.py`, result
  `out/ts2_warmup.json` (Mac mini cells `eval/wu_*`, stopped on the main session's word after s2g_140 lacked only
  the landing cell; the main session's Modal cells `eval/wm_*` are the complete set). Drivers alone, 20 seeds, drop
  0.036: start-point policy (`ckpt/ts_start`, same file as uni_a) at comx+10 19 of 20 fall, 5 before 2 s, 0.096 m/s
  forward in 0-2 s; at full load 0 falls, -0.005 m/s. Runtime overlay stand61/walk61 (`ckpt/overlay_models`, the
  no-pack robot's policies): 20 of 20 fall at comx+10 (18 before 2 s) and at full load (all before 1.3 s). With the
  start-point driver, falls of 20 (none, nobatt, full, comx, shove, comx drop 0, shove drop 0, comx drop 0.072,
  comx landing): s2g_200 N=100 0, 0, 0, 11, 2, 0, 0, 15, 9; N=50 0, 0, 0, 9, 0, 0, 0, 14, 8; s2g_140 N=100 1, 0,
  0, 7, 6, 0, 0, 11, not run. Without warm-up (pk_/dr_/cz_ records): s2g_200 0, 0, 0, 6, 0, 0 (comx drop 0), 14
  (drop 0.072), 13 (landing). No deployable 61-input policy we have stands at comx+10, so there is no driver.
- 11-18 23:50 to 11-19 01:45 DAgger in the runtime simulation (Shawn 11-18 late: training for this fix needs no
  further nod). The student drives brain_sim_check episodes from an empty state on Modal, teacher t2a_999 labels
  every called tick through `priv_now()`; the fine-tune runs on the Mac mini CPU. Tools: `flight_eval.py`
  FLIGHT_DAGGER=<beta> (default off; float16 obs / teacher label / student action, skipped ticks, counters),
  `ts2_dagger_modal.py` (collection -> `out/dagger/r<k>.npz` + `.json`; npz not committed), `ts2_dagger_train.py` +
  `.sh` (stateful as distill_worker.py, 100-tick BPTT, lr 5e-5, minibatch 64 episodes, first 100 ticks weighted),
  `ts2_dagger_spec.py` (ten held-out cells with the 0-2 s forward speed; `flight_eval_modal.py` spec key `seed0`).
  Training seeds 10000-10599, 20000-21199, 30000-30999; evaluation seeds 0-19 and 2000-2019 never collected.
  Falls of 20, seeds 0-19 (none, nobatt, full, comx, shove, comx drop 0, shove drop 0 | comx drop 0.072, comx
  landing, comx stand) and forward speed at zero command 0-2 s in the comx cell; s2g_200 before: 0, 0, 0, 6, 0, 0,
  0 | 14, 13, - and 0.084 m/s.
  Round 1, 600 episodes of 20 s (527,955 ticks), beta 0.5, student s2g_200. Plain imitation of the teacher on every
  tick, `s2r1_8`: 6, 0, 0, 20, 17, 20, 20 | 20, 20, 0; creep 0.016; it walks 0.32 m/s and falls after the shove
  and when the walk command ends. Rejected. From here on `--anchor-after K`: teacher label on the first K called
  ticks of an episode, the collecting student's own action after that (only the start is corrected). K 150:
  `s2r1a_5` 1, 3, 8, 5, 0, 0, 0 | 13, 8, 0, creep 0.047; `s2r1a_10` 1, 6, 1, 3, 0, 0, 0 | 10, 11, 0, creep 0.023
  (a half-learned start falls forward at other loads).
  Round 2, 1200 episodes of 8 s (383,244 ticks), beta 0.2, student s2r1a_10 (comx-10: 69 of 79 fell), pool r1+r2
  from s2r1a_10, K 150, first 100 ticks x5: `s2r2_4` 0, 1, 0, 3, 0, 0, 0 | 9, 5, 0, creep 0.010.
  Round 3, 1000 episodes of 10 s (466,097 ticks), beta 0, student s2r2_4, pool r1+r2+r3 (2800 episodes, 1,377,296
  ticks) from s2r2_4, K 250: `s2r3_3` 0, 0, 0, 3, 0, 0, 0 | 5, 4, 0, creep 0.0095 (comx falls at 15.30, 16.94,
  17.36 s, none at the start); `s2r3_6` 0, 0, 0, 4, 2, 0, 0 | 14, 8, 0 (worse; epochs differ by more than rounds
  on the comx cells). Best: `s2r3_3`. Seeds 2000-2019: s2r3_3 0, 0, 0, 1, 1, 0, 0 | 4, 5, 0, creep 0.008; s2g_200
  on the same seeds (four cells run): comx 6, shove 1, comx drop 0.072 11, comx landing 11, creep 0.110.
  Both seed sets, falls of 40: comx 4 against 12, comx drop 0.072 9 against 25, landing 9 against 24.
  Stop rule (comx 0-1 of 20 with the other six at 0, creep under 0.02): creep met; comx met on seeds 2000-2019 (1,
  with 1 shove fall), not on seeds 0-19 (3). The remaining comx falls are late in the walk or at its end, where the
  target was the student's own action. No distillation-env sequences were mixed in; forgetting is held by the
  anchor term and by keeping every round's data. Results `out/dagger/eval_*.json`, logs `out/dagger/s2r*_log.json`.
  Modal: 4,286 episodes (2,200 of them 8 or 10 s long), estimated 3.0 USD of the 3.5 allowed (not read from the
  bill). Slips: the first smoke crash-looped about 8 min on an import path (no episode ran; app stopped); ssh_guard's
  640 s limit cut the first fine-tune at epoch 14 and restarted it (limit raised for this script; s2r1_8 is that
  run's epoch 8); the first round 3 fine-tune sat 6 min decompressing the npz once per episode (fixed).
  Full acceptance of s2r3_3 (`out/accept_s2r3_3.json`, 36 cases, seeds 0-19): 12 failed lines: one fall each in
  comx+10 walk, comx-10 stand, comx-10 walk, nominal stand with shove; walk torque p99 0.54 against 0.48; hip load
  lines at load 25 / 50 / 75 % and batteries out; toe-out at none, batteries out, full.
- 11-19 01:50-03:40 DAgger round 4 (main session: the Modal bill, not the per-episode estimate, is the budget:
  metered 28.37 USD before this work, 29.33 after rounds 1 to 3, ceiling 35.00). Selection from here on 60 held-out
  seeds per cell (0-19, 2000-2019, 3000-3019; `ts2_dagger_spec.py --spec60 / --sum60` -> `out/dagger/eval60_*.json`),
  falls of 60 (none, nobatt, full, comx, shove, comx drop 0, shove drop 0 | comx drop 0.072, landing, comx stand):
  s2g_200 0, 0, 0, 18, 3, 0, 0 | 39, 37, 7 (seven cells 21 of 420, creep 0.101 m/s); s2r2_4 0, 1, 0, 12, 0, 0, 0 |
  28, 21, 3 (13); s2r3_3 0, 0, 0, 6, 1, 0, 0 | 12, 11, 0 (7, creep 0.0085).
  Round 4: 3000 episodes of 20 s (2,794,491 ticks), student s2r3_3, beta 0, comx+10 902 episodes (110 fell).
  Pool r1-r4, 5800 episodes, 4,171,787 ticks, from s2r3_3: teacher label on every tick, and from tick 250 on a
  second term of weight 1 toward the collecting student's action (`--anchor-w 1.0`); 4.8 min per epoch on the Mac
  mini CPU, every epoch saved and evaluated:
  `s2r4_1` 0, 0, 0, 0, 1, 0, 0 | 4, 3, 0 (seven cells 1 of 420, creep 0.0062);
  `s2r4_2` 3, 0, 1, 60, 37, 60, 0 | 60, 59, 0 (161: the forward-COM walk collapses for one epoch);
  `s2r4_3` 0, 0, 1, 2, 1, 0, 0 | 6, 6, 0 (4); `s2r4_4` 0, 0, 0, 0, 4, 0, 0 | 7, 6, 0 (4).
  Pick: `s2r4_1`. Because it was picked among four on those seeds, it was run on 60 fresh seeds per cell
  (4000-4019, 5000-5019, 6000-6019) beside s2g_200: s2r4_1 0, 0, 0, 0, 1, 0, 0 | 2, 6, 0 (seven cells 1, creep
  0.0062); s2g_200 0, 0, 0, 21, 1, 0, 0 | 40, 30, 8 (22, creep 0.093). Stop rule met (seven cells 0 to 2 over 60
  seeds with comx at most 2). Caution: neighbouring epochs differ from 1 to 161 falls, so a checkpoint of this
  fine-tune is only as good as its own held-out run; nothing here says the next epoch is safe.
  Modal after round 4 and its evaluations: metered 30.20 USD (7,720 further episodes since 29.33: 3,000 collected, 4,720 evaluated)
  Full acceptance of s2r4_1 (`out/accept_s2r4_1.json`, 36 cases, seeds 0-19, Mac mini): 10 failed lines, 20 pass:
  comx-10 stand 2 falls of 20, comx-10 walk 2 of 20, nominal stand with shove 1 of 20; walk torque p99 0.54 against
  0.48; hip load lines at load 50 %, 75 % and batteries out; toe-out at none, batteries out, full. comx+10 stand
  and walk pass. The rearward COM x -10 mm falls are not in the seven selection cells (in round 1 data s2g_200 fell
  0 of 49 comx-10 episodes; s2r3_3 fell 8 of 163 in round 4 data): the fine-tune traded some rearward-COM margin..
- 11-19 DAgger round 5 (main session: nine selection cells = the seven plus comx-10 stand and comx-10 walk, 60 seeds
  per cell on 0-, 2000-, 3000-; lr halved, a save every 33 minibatches, weight average as one more candidate).
  Reference on the nine cells: s2r4_1 9 of 540 (comx-10 stand 4, walk 4, shove 1), s2g_200 22.
  Round 5: 3000 episodes (2,813,194 ticks), student s2r4_1, beta 0, comx+10 781 episodes (32 fell), comx-10 745 (42
  fell), 99 falls in all (`out/dagger/r5.json`). Fine-tune s2r5 from s2r4_1 on r1 to r5 (8800 episodes, 6,984,981
  ticks), lr 2.5e-5, clip 1.0, anchor after tick 250 weight 1, early weight 5, 2 epochs, 8 saves + `s2r5_avg`
  (plain mean of the 8 saved weights) (`out/dagger/s2r5_log.json`).
  Nine cells of 540 per save 1 to 8: 18, 4, 10, 11, 9, 12, 10, 4; s2r5_avg 4 (`out/dagger/eval60_s2r5_*.json`).
  Save 1 to 2 jumps by 14 (above the 10 line); the other neighbours differ by 1 to 6. Seven cells 0 to 2 from save 2.
  Never-used seeds (4000-, 5000-, 6000-), nine cells: s2r5_2 3, s2r5_8 4, s2r5_avg 9, s2r4_1 13
  (`eval60_*_s4000_5000_6000.json`). Six groups together of 1080: s2r5_2 7, s2r5_8 8, s2r5_avg 13, s2r4_1 22.
  The comx-10 stand and walk cells fall on the same episodes (same seed and time, 0.98 to 1.94 s, before the walk
  command at 2 s), so the nine-cell sum counts each rearward start fall twice.
  Report cells of s2r5_avg (selection / never-used, of 60; s2r4_1 selection in brackets): comx+10 drop 0.072 8 / 3 (4),
  comx+10 landing 8 / 6 (3), comx-10 landing 5 / 9 (3), comy+10 walk 3 / 3 (2), comy-10 walk 0 / 0 (0), comx+10
  stand 0 / 0. Landing starts are weaker than s2r4_1.
  Stop rule (nine at most 3 of 540, confirmed) not met: best 4. Modal metered 30.09 before, 31.17 after.
  Round 6 started: s2r5_8 drives 3000 episodes, landing starts 22 % (walk 45 %), otherwise as round 5.
- 11-19 DAgger round 6, the last round of this fix (main session: pick over six seed groups with the rearward COM
  counted once = eight distinct cells x 120 seeds; candidates the round 6 saves plus s2r5_2 and s2r5_8).
  Round 6: 3000 episodes (2,779,944 ticks), student s2r5_8, beta 0, landing starts 612 episodes (34 fell), comx+10
  744 (58 fell), comx-10 755 (56 fell), 141 falls in all (`out/dagger/r6.json`). Fine-tune s2r6 from s2r5_8 on r1 to
  r6, lr 2.5e-5, clip 1.0, anchor after 250 weight 1, early weight 5, 2 epochs, a save every 46 minibatches (8 saves)
  + `s2r6_avg` (`out/dagger/s2r6_log.json`).
  Nine cells of 540, seeds 0-/2000-/3000- then 4000-/5000-/6000-: saves 1 to 8: 12/5, 11/6, 9/8, 2/3, 5/6, 7/5, 15/6,
  10/4; s2r6_avg 6/6; s2r5_2 4/3; s2r5_8 4/4. Neighbour jumps on the first set up to 8 (7 to 15).
  Eight distinct cells of 960: s2r6_4 3, s2r5_2 5, s2r5_8 5, s2r6_6 7, s2r6_avg 7, s2r6_5 8, s2r6_8 8, s2r6_1 10,
  s2r6_2 11, s2r6_3 12, s2r6_7 12. Pick: `s2r6_4` (3 against 5 is a small margin on 960 episodes).
  Report cells of s2r6_4 (first set / second set, of 60): comx+10 drop 0.072 3 / 3, comx+10 landing 10 / 9, comx-10
  landing 3 / 7, comy+10 walk 4 / 2, comy-10 walk 0 / 0, comx+10 stand 0 / 0 (s2r5_8: 2 / 3, 5 / 3, 5 / 6, 4 / 1,
  0 / 0, 0 / 0). The landing start at comx+10 did not improve with 22 % landing starts in the collection.
  Creep at comx+10 0.0064 m/s; walk speed median (six groups): none 0.341 to 0.343, batteries out 0.269 to 0.272,
  full 0.241 to 0.244, comx+10 0.299 to 0.300, comx-10 0.246 to 0.259.
  Full acceptance of s2r6_4 (`out/accept_s2r6_4.json`, 36 cases, seeds 0-19, Mac mini): 9 failed lines, 21 pass
  (s2r4_1 10): nominal landing stand 1 fall of 20 and landing walk 1 of 20 (new); walk torque p99 0.54 against 0.48;
  hip lines load 50 % (p99 0.431, sat 0.0188), 75 % (0.461, 0.0411), batteries out (0.477, 0.0404); toe-out at none,
  batteries out, full. comx-10 stand and walk and the shoved stand, failed by s2r4_1, pass.
  Modal metered 32.49 USD after round 6 and its evaluations (31.17 before; ceiling 35.00). No round 7.

## Robot-trial readiness of s2r6_4 (2026-11-19; repository only, nothing copied to the A7Z, nothing run on the robot)

Runtime support. `guide/firmware/mac/walk_brain.py` now runs a policy file with a second input `state_in` itself
(lines after the change): `import hashlib` (70), `RECURRENT_MAX_GAP = 5` (243-247), the slot table in
`Brain.__init__` (460-468), `Brain.run_policy` and `Brain.reset_policy_state` (500-523), the tick counter and the
`policy_reset` command key at the top of `Brain.tick` (746-750), the policy call (1014). Rules: `state_out` is fed
back; the state survives up to 5 control ticks without a call (dropped servo reads) and starts from zero after a
longer gap; slots loaded from the same file (walk61 and stand61) share one state; `reset_policy_state()` empties it,
and `{"policy_reset": <new value>}` in the command file calls it once per new value. A 61-input policy takes the
same `sess.run` call as before. `microduck_rl/cmu/mac/walk_brain.py` (team repo copy) is untouched;
`flight_eval.py` keeps its wrapper unless `FLIGHT_NATIVE_STATE=1`.

Parity (`ts2_runtime_parity.py`, Mac mini, result `out/ts2_runtime_parity.json`): comx+10, nominal with shove, none,
seeds 0 to 4, default drops, through the wrapper and through the new Brain: 15 episodes, 14,476 policy ticks and 524
skipped ticks, same ticks and slots, max abs action difference 0.0, falls 0 and 0. Current 61-input walk61 through
the old and the new walk_brain (none, seeds 0 and 1): max abs difference 0.0, no falls. State rules (fed back, kept
over a 5-tick gap, zeroed after 6, shared by walk and stand, zeroed by the hook and by a new command id, kept on a
repeated id): all true.

Cost of one call (`ts2_policy_cost.py`, one thread, 3000 calls, `out/ts2_policy_cost.json`): Mac mini 0.058 ms
against 0.008 ms for the current walk61 (ratio 7.1); MacBook 0.080 against 0.020 ms (ratio 4.1). The state is 9728
floats. The A7Z is NOT measured. `walk_brain.session_options` records 0.6 to 1.3 ms per run for a 61-input policy
on the A7Z (2026-10-20); at these ratios that would be about 2.5 to 9 ms of a 20 ms tick (inference, not a
measurement), and CURRENT-STATE.json `a7z_closed_head_thermal_and_resets` records the closed head throttling to
416 MHz with a 23.6 ms loop under a 50 Hz policy load (2026-10-22, before the saddle move). To measure, with
Shawn's go, brain stopped, after copying the script and the model to the board:
`ssh a7z '~/.venvs/duck-policy/bin/python ~/policies/s2r6_4/ts2_policy_cost.py ~/policies/s2r6_4/walk61.onnx ~/rt/microduck-sim/hardware-design-20260912/whole-robot-20260912/runtime-overlay/models/walk61.onnx --calls 1000'`

Deployment checklist (for Shawn's go; every robot step is his or the main session's).
1. Files. Code: `guide/firmware/mac/walk_brain.py` (the one changed file) into the A7Z tree
   `~/rt/microduck-sim/guide/firmware/mac/` (the route `guide/firmware/a7z/install_teleop.sh` uses; it copies and
   never restarts a running brain). Keep the old file as a `.bak` beside it. Not verified: that the A7Z tree equals
   the repository before the copy (the last recorded hash, `policy_goal_guards`, is from 2026-10-23).
   Models: a new directory on the A7Z, `~/policies/s2r6_4/`, holding
   `train/ckpt/s2r6_4/walk61.onnx` and `train/ckpt/s2r6_4/stand61.onnx` (the same file twice, sha1 8a63d9f4...), plus,
   to keep those modes, copies of `groundpick61`, `seepick61`, `sitstand61`, `kick_left61`, `kick_right61` from
   `hardware-design-20260912/whole-robot-20260912/runtime-overlay/models/` (their `default_joint_pos` equals
   s2r6_4's, checked 2026-11-19; the Brain asserts it at start). The deployed `runtime-overlay/models` directory
   is not changed.
   `microduck_rl/cmu/deploy/deploy_policy.py` cannot be used as it is: its contract step demands a single input.
2. Layout the brain expects (`Brain.__init__`): `<models>/walk61.onnx` and `<models>/stand61.onnx` are required,
   the other five are optional and their modes are refused when absent; every file needs obs [1, 61] and the
   metadata `observation_names`, `joint_names`, `action_scale` 1, `default_joint_pos`.
3. Switch. `~/duck-policy` on the A7Z holds the models directory; `~/duck-run.sh`
   (`guide/firmware/a7z/duck-run.sh`) passes it as `--models` at the next brain start. A running brain keeps its
   policies until it restarts. The brain starts in monitor mode and drives nothing until a command
   (`a7z_brain_start`).
4. Way back. Delete `~/duck-policy` and restart the brain: it loads `runtime-overlay/models/walk61.onnx` again
   (`walking_policy`). The new walk_brain.py runs that policy exactly as the old one (parity above), so the code
   can stay; to go all the way back, restore the `.bak`.
5. First checks on the robot, pack fitted, hands near it. (a) Start line of `duck_wired_<suffix>.out` lists the
   model hashes; walk61 and stand61 must be the same hash. (b) Walk mode at zero command (stand61 slot): it should
   stand without creeping; in simulation it moves 0.006 m/s forward in the first 2 s at comx+10. (c) Only then a
   short walk at vx 0.25, 3 to 4 s, then zero command. Simulated walk speed with the pack is 0.24 to 0.30 m/s,
   above the 0.15 m/s the current policy does on the robot (`walk_speed_vx025`); leave room.
   Not verified on the robot: anything. The simulation gap of this robot is recorded (ft3 passed in simulation and
   fell on the robot, `walking_policy`).
6. Handling. Put it down flat and gently before the policy runs: landing starts (released 2.5 to 3.5 cm, up to
   5 degrees tilted) are the weakest case, 19 falls of 120 at COM x +10 mm, 10 of 120 at -10 mm, 1 of 20 at nominal.
   After changing the pack or picking the robot up and putting it down, reset the state: leave walk mode for more
   than 0.1 s (stand or monitor) and re-enter, or write a new `policy_reset` value into the command file, or
   restart the brain. A state carried over from another load fell 20 of 20 in simulation.
7. Watch. Servo temperature and the servo rail: the walk torque p99 sits at 0.54 N m, the model's clamp (0.538,
   1.47 A), and the hip lines exceed the acceptance limits at loads 50 %, 75 % and batteries out. The rail on the
   2S pack reads 7.6 V median, 7.2 V lowest per action (`servo_rail_v`, 2026-11-06). Not verified: where the
   live page shows servo temperature. The walk guards of `walk_wired.py` stay as they are (|action| 1.8 rad in
   walk, 3.0 hard, tilt 30 degrees).
Robot facts above are from `microduck-sim/CURRENT-STATE.json` (several entries there show STALE in the session
notice, including `servo_rail_v`, `walking_policy`, `walk_speed_vx025`); start-up behaviour from
`guide/firmware/mac/walk_brain.py`, `walk_wired.py` and `guide/firmware/a7z/duck-run.sh`.
**Withdrawn 2026-11-19: s2r6_4 fell on the robot at standstill in 4.4 s and fails the chatter gates below. This
checklist is not to be used for it.**

## Round 3: the chatter gap (2026-11-19; simulation only; Modal for batches)
Robot evidence: `docs/PET_ROBOT_LOG.md` 2026-11-19 16:00, `a7z-20261119/robot_s2r6_4_stand_fall.jsonl`.
- Like for like (`ts3_chatter_stats.py`, `ts3_like.sh`, `out/chatter/like_*_stats.json`): simulated standstill of
  s2r6_4 has 0.5 jumps per 10 s, median step 0.001 rad, no fall; robot 172, 0.40 rad, fall at 4.4 s. The simulation
  does not under-report the chatter, it lacks it.
- Matched cell (`ts3_gap_sweep.py`, `out/chatter/gap_{a,b,c,d}.json`): `--kp-rl 400` ("gain400"), no pack. s2r6_4
  falls at standstill 7 of 10 (median 2.9 s), walk61 0 of 10. 25 other conditions leave the standstill quiet.
- Gates (`ts3_gates.py`, first in `ts_accept.sh`; `out/gates/gates_<dir>.json`), 10 seeds, against walk61 in the same
  cell: G1 action distance from walk61 on its robot walks at most 0.25 rad; G2 no pack; G3 no pack gain400; G4 pack;
  G5 pack gain400; falls and jumps per 10 s on each.
  s2r6_4 FAIL 11 lines (G1 1.099); ts_start FAIL 8 (G1 1.454; gain400 standstill 8 falls of 10, walking 10 of 10);
  teacher t2a_999 FAIL 10. walk61 reference: standstill 0 falls 0 jumps in both cells, walking 0 falls 0.75 jumps,
  gain400 walking 2 falls 18.5 jumps. Modal 280 episodes, metered 32.50 to 32.52 USD.
