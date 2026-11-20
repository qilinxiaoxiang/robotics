# Pet robot: progress log

Dated entries, newest last. Findings, Shawn's decisions and upstream changes go here the same turn they arrive; the current register is `PET_ROBOT_FEATURES.md`. Robot facts stay in `microduck-sim/CURRENT-STATE.json`.

## Pollen upstream watch

Re-run these when the topic comes up; append what changed below.

```bash
cd ~/code/robotics/microduck-sim/microduck_rl && git fetch upstream -q && git for-each-ref --sort=-committerdate --format='%(committerdate:short) %(refname:short)' refs/remotes/upstream | head -12
```

```bash
curl -sL "https://huggingface.co/api/models/pollen-robotics/microduck-policies/commits/main" | python3 -c "import json,sys; [print(c['date'][:10], c['title'][:110]) for c in json.load(sys.stdin)[:12]]"
```

```bash
gh api repos/pollen-robotics/microduck/commits -q '.[0:12][] | "\(.commit.author.date[0:10]) \(.commit.message | split("\n")[0] | .[0:100])"'
```

State as of 2026-10-26:
- `microduck_rl` upstream: `develop` and `improve_standup_velstand` at 2026-10-12; `ground-grasp` at 2026-10-10 (16 commits, local branch of Rémi's, not merged); `pickup_detector`, `one_leg_stand`, `spring_v2`, `velstand_kp120`, `mjlab_1_6` branches.
- HF `pollen-robotics/microduck-policies`: ten policies; `velstand.onnx` v8 2026-10-12 (smooth get-up, yaw tracked), v7 2026-10-05 (body roll/pitch while standing), v5 2026-09-14 (default walk slot); `alpha_sitstand` v6 2026-10-01; `alpha_ground_pick.onnx` unchanged since 2026-09-02 (episodic, 2.8 s, phase command, hands back at phase 0.7). No ground-grasp policy exported yet.
- `pollen-robotics/microduck` (robotd, Rust): release 0.17.8 on 2026-10-19; `duck-control/src/pickup.rs` is a "somebody is holding the robot" detector (8k-parameter temporal CNN, v2 2026-10-03), not object pickup; 2026-10-19 `udp-pad`: the duck opens its mouth and the laptop plays the sound.

## 2026-10-26

- **Walking is stable** (Shawn); recorded as `walking_stability` in CURRENT-STATE. Heat is no longer a bottleneck since the A7Z moved to the saddle (D-022/D-028). Battery backpack in the making. Old fall records (10/16-10/18) are history, not gaps.
- **Get-up**: Pollen's get-up is a learned policy. Our `stand61.onnx` has the same SHA256 as `BEST_alpha_stand.onnx` (the StandUp policy, `microduck_standup_env_cfg.py`: face-down / face-up / sitting starts, curriculum to {0.15, 0.20, 0.30, 0.35}). Our `walk_brain.py` `Brain.tick()` gate (`grav_body[2] >= -0.5` -> skip inference, freeze goals) blocks it. robotd removed its fall gate ("the fall verdict is a report, not a rule"); `limp_fall` = predicted fall -> limp -> gyro quiet -> 1 s ramp home -> stand policy at zero command. `velstand` v8 adds protected falls and get-up to the walk policy. Implementation started in `microduck-sim/guide/firmware/mac/getup-20261026/` (subagent, 2026-10-26).
- **Pollen's pickup, corrected record.** The shipped `alpha_ground_pick` is a blind episodic bow: the beak points 86 deg down, mouth tip 2.7 cm above the floor, forehead dome lower than the lips, final approach 2 cm horizontal over the last 3 cm (Rémi's own measurement in `docs/superpowers/specs/2026-10-10-ground-grasp-design.md` on the `ground-grasp` branch: "beautiful but rarely grasps"). The old training model had no jaw joint and the convex hulls filled the mouth, so nothing could ever enter it. On the robot it is aim-and-hope: pick succeeds only when the object happens to be where the move lands (Shawn's "纯遥控，对的准就能捡到"). The `ground-grasp` branch (2026-10-10, Rémi) changes the environment: opening jaw (`passive_mouth` + beak boxes), a scripted mouth schedule (opens on the way down, closes at phase 0.30-0.36, squeezes 1.0 N m/rad), a free randomised object 10 cm in front with only +-1 cm placement noise ("a small area that succeeds a lot"), vertical last 6 cm, flat (0.8-1.2 cm) and tall (3.2-5.1 cm) variants, overrun and head-impact penalties. The policy is still blind to the object: robustness is sought through placement DR, not perception. Not exported to HF as of 2026-10-26.
- **Our differentiator for the course project**: perception-conditioned grasp. `cmu_aim_pick_env_cfg.py` already aims the beak at a measured grasp point with an error-gated window (UMI-on-Legs-style sigma curriculum) instead of hoping the object sits in the +-1 cm zone; the detector (step 1) and approach (step 2) feed it. That, plus the language-to-skill chaining and get-up integration, is the "Pollen cannot do this" story.
- **Pet direction surveys** (four, this day): navigation (Nav2 + SLAM Toolbox needs a 2D lidar; mono VIO fails on walking robots; relocalisation against a phone-built hloc map is the monocular route), person recognition (buffalo_sc face, CAM++/ECAPA voice, >= 10 px IPD, upward pitch degrades, Immich's >= 3 rule for new persons, GCC-PHAT with a third mic for front/back, YOLOv8n 12.6 ms on the A733 NPU per Radxa), olfaction (BME688 detects strong VOC events only; owner-by-smell unreachable), get-up (above). URLs are in the session transcript of 2026-10-26.
- **Shawn's decisions**: no smell sensor; no lidar, monocular only; daytime behaviour chosen by a small model, not rule matching ("可以笨，不能刻板"); nightly reflection by a frontier model; end-to-end pet model as the long-term goal; private data is the owner's responsibility; the pet is unconditionally supportive and never moralises; pickup must become robust, not aim-and-hope.
- **Open**: VL53L5CX ToF for stair edges not bought; ear mics not soldered; `pet/identity/` and the get-up sequence in progress (subagents); `pet/mind/` and `pet/learn/` briefs rewritten for the three-layer design, not yet dispatched.
- **`pet/identity/` delivered** (commit `b6d70ac`, subagent, verified here: 25 tests pass, `pet/identity/out/bench.json`). Mac M1 Pro CPU: SCRFD-500MF 20 ms per 720p frame, MobileFaceNet 7.3 ms per face, CAM++ 26 ms per 2.5 s window. Speaker model changed from the English VoxCeleb CAM++ (3/7 on real clips) to the zh+en CAM++ `3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced` (7/7; sherpa-onnx has no ECAPA). Synthetic 14-day run: a neighbour becomes a person on the third glimpse (day 5), strangers never do and are deleted after retention. Live webcam/mic never ran (no camera access in this process): Shawn runs `enroll_face`, `enroll_voice`, `demo` from Terminal.app. Face thresholds untuned for a 15 cm camera. NPU: Radxa publishes no operator list; nothing run on the A733.
- **Get-up delivered in sim** (commit `b135faf` + the walk_wired guard commit, verified here: 9 get-up tests and 60 existing tests pass). stand61 with the recover sequence: 50/50 from face-down, face-up, side, seated, pushed (as-built model, saddle mass, 7.0 V, 4 % drops), median 2.2-2.5 s up, longest saturation 0.50 s on left hip pitch, largest action 5.09 rad. A second blocker the survey missed: `walk_wired.py`'s 30 deg tilt stop and 3.0 rad action limit stopped every face-down rise; both now step aside only while `brain.getup` is set (no global override). velstand v8: shapes and metadata match, 44/50 under the sequence, failures stuck on the back, 0/50 under the 3.0 rad limit; not a walk61 replacement. CURRENT-STATE fact `getup` added (sim only). Not verified: saddle collision shape (none in the model), real XL330 overload trip time, whether the saddle is on the robot. Robot trial command in `getup-20261026/README.md`; needs Shawn: soft mat, face-down, 20 V 5 A charger, monitor command as the stop.
- **"One mind, several bodies"** (Shawn's idea 2026-10-26): recorded as register section 11. Mapping to the literature: body schema / self-modelling (Lipson 2006), cross-embodiment through a body card read by the intention layer (our architecture already has the seam), damage tolerance by failure randomisation / RMA (Kumar 2021) / repertoire recovery (Cully 2015 Nature), morphology-general learned policies (SMP 2020, MetaMorph 2022) as frontier. Concrete next pieces: body card file for duck and OMX-F; boot-time self-inspection (bus scan + motor babbling); neck-servo failure randomisation in the next walking training. Not started.
- **Shawn 2026-10-26, direction**: several body forms are certain, so transfer, not per-body training, is the line; damage adaptation is unavoidable ("adapt like animals": a quadruped goes on three legs, a biped is harder, limp and favour the joint); plan for both in the overall design now. Dispatched three sessions: `pet/mind` (three-layer motivation engine, small-model intention layer), `pet/learn` (nightly frontier-model reflection, daytime matching), `pet/body` (body card schema, boot-time self-inspection on the duck and the OMX-F, failure randomisation study for walking).
- **Three sessions delivered, verified here** (tests re-run: mind 33, learn 22, body 24 + 1 skipped; commits `90ea8f2`, `326122a`, `4fe7d50`).
  - `pet/mind/`: drives + mood, small-model intention layer, validator, reflexes, skills, offline fallback; `pet/state/README.md` is the shared file contract. A simulated duck day through `claude -p` (subscription): 349 intentions, 162 distinct action sequences, 4.6 % repeats of the previous intention, entropy 6.8 bits, list-price equivalent about $0.16-0.18 per simulated day; the arm card made the model gesture instead of walk. Fallback (drives only) is comparable in entropy but has no language and no plan following. API and Ollama backends only offline-tested; nothing on the robot.
  - `pet/learn/`: nightly reflection by Opus 5.5 ($0.133 per night via `claude -p`, 36 s), Rescorla-Wagner matcher, owner instructions, diary retrieval. 7-day demo: keys -> owner leaves rule 0.3 -> 0.66 / 0.88 / 0.9x by days 2-4; bedroom rule settles near 0.8 with visible omission dips; spurious rule decays. The Anthropic API SDK path was not exercised (no key on this Mac).
  - `pet/body/`: `inspect.py` (bus scan, device enumeration, babbling; `--dry-run` and `--sim` both write a valid card), `health.py`, example cards duck and OMX-F arm. Joint-failure study (walk61, 7.0 V, 4 % drops, 10 seeds, ran on the Mac mini in 205 s): 0 falls in 130 runs. Head joints frozen or weak keep 93-97 % of the healthy 0.364 m, except a weak neck_pitch: 8/10 runs never step (head sags 0.35 -> 0.09 rad, policy stays in the standing gait). Frozen left ankle walks at 39 %, frozen right ankle 60 %, weak ankles 81 % / 108 %. Proposed randomisation for the next training: neck gain and head-joint freezes; ankle freezes need the Cully/RMA route (`pet/body/failure_study/NOTE.md`). No real-robot command run.
- **Aliveness / personality on any body** (Shawn 2026-10-26): recorded as register section 12 (animation principles as an expressive motion layer, attention, living stillness, fallibility, body-agnostic channels, learned style as a course option). Not started.
- **Name-call response and expressive abstraction** (Shawn 2026-10-26): technique and cross-body channel abstraction added to register section 12. Current head path is a first-order low-pass (HEAD_ALPHA 0.2), so it can never anticipate or overshoot. Dispatched session `pet-express` (sim and Mac only).
- **One principle under the drives** (Shawn 2026-10-26): register section 13; homeostasis + expected surprise (active inference) as the single objective from which survival and curiosity both fall out; proposed A/B against the hand-written drives in pet/mind. Not started.
- **`pet/express/` delivered** (commit `7f5f625`, verified here: 28 tests pass; evidence in `pet/express/out/`). Expressive intents -> semantic channels (ATTEND/ORIENT/POSTURE/GESTURE/VOCALISE) -> per-body actuators; spring-damper gaze with affect-set stiffness/damping, anticipation, five takes (quick_snap, curious_turn, double_take, groggy, glance) with per-sample jitter, no-repeat, habituation, resampled quacks synced to head arrival. 300 duck name-calls: latency 0.12-1.14 s (median 0.46), overshoot up to 37 %, 182 distinct quack pitches, zero consecutive identical takes. Duck sim under stand61 with walk_brain's own head path: 360 calls over 9 takes in real (7.0 V, 4 % drops) and stress (6.6 V, 8 %) conditions, zero falls, trunk tilt max 1.29 deg (today's path 0.63 deg). Same intent rendered on duck, arm and vacuum cards (`same_intent_3_bodies.png`). Not on the robot; the arm's wrist pitch sign unverified.

## 2026-10-29

- **Hardware state (Shawn)**: speaker connected; three microphones capture as one 4-channel stream (CURRENT-STATE `a7z_audio_capture`, back mic on DIN3 verified on the bench 2026-10-29); U20CAM runs on the earlier camera's 1 m cable; boot self-check (`pi/duck_selfcheck.py`, speaker sweep heard by the three mics) reports into the phone app. Shawn: "基本上已经是个完全形态了".
- **Inventory answer for Shawn (what runs on the robot today)**: open-loop stand, stand61, walk61 with heading hold and head commands, sitstand61, groundpick61 (closed-beak bow), kicks, quack playback, touch pads, IMU, camera, mics, blackbox, graded hold, phone app. Off the robot: approach.py (sim 21/21, never run on the A7Z robot), get-up (sim 50/50), seeing pick (seepick61 from sp-b-1027: 78-81 % in the training eval, 0/96 in the deployment rehearsal, held off the robot), and every `pet/` layer (identity, mind, learn, body, express: sim only).
- **Pollen's model count, checked against HF `pollen-robotics/microduck-policies` manifest.json (2026-10-29)**: ten separately trained ONNX networks sharing one 61-input / 14-action contract at 50 Hz: alpha_walking, velstand (walk + stand still + get-up + body tilt, the default walk slot since v5), alpha_stand, alpha_sitstand (one network, posture flag in the vx slot), alpha_ground_pick (episodic, phase command), roller, roller_crouch, roulade, ball_kick_left, ball_kick_right. Head tilt is a command input to the walk/stand policy (slots 55-58), not a model; quack is a sound file played by robotd (the mouth is a joint command). robotd picks one network per mode; our `walk_brain.py` does the same with seven files (walk, stand, groundpick, seepick, sitstand, kick left/right).
- **Dispatched three background agents** (Agent tool; the app's session-start card has no always-allow, so no `start_session`): (1) seeing-pick gap diagnosis: seepick61 in the training env's own eval on the rehearsal's draws, then bisect actuators / compensate / mouth replica / camera / neck clamp, note in `guide/firmware/mac/seepick-gap-20261029/`; (2) `namecall.py`: call detection + GCC-PHAT direction on the three mics + a pet/express take + quack, A7Z-deployable, robot plan in `NAMECALL.md`; (3) `pet/mind/runner.py`: intentions to the brain's control file, posture and refusal readback, percepts in, `--dry` and `--sim`, 30-minute sim day. No training, nothing on the robot.
- **`namecall.py` delivered, sim and Mac only** (`microduck-sim/guide/firmware/mac/namecall.py`, plan and evidence in `namecall-20261029/NAMECALL.md`, `results/`; 29 new tests pass, `pet/express` 28 still pass). The first pet behaviour written for the robot: 4-channel I2S0 capture (`a7z_audio_capture`) -> voice-band onset detector (12 dB over a tracked floor, 6 dB rise, confirm block, 2.5 s refractory, deaf during its own quack and take) -> GCC-PHAT on the three pairs summed on a 1 deg grid (SRP-PHAT) with the head CAD geometry (ears 77 mm apart, back mic at x -19.9, y -11) -> `pet/express` `acknowledge` take through walk_brain's head path (EMA pre-inverse, targets capped at +-1.2 rad yaw, outputs inside HEAD_RANGE) -> zero-command walk with `head` in the control file at 50 Hz, only while the file is its own or a plain zero walk -> pitched duck call via `duck_sound.Voice` at arrival. Refuses without a brain holding the I/O lock, without walk-at-zero or stand in the brain's tick log, or while `duck_selfcheck.py` holds the sound card. Synthetic direction, free field: mean 0.9 deg / max 3.3 at 20 dB SNR, no mirror errors; the report's real-room expectation stays about 10 deg. Duck sim under stand61 (Mac mini, 7.0 V, 4 % drops): 72 calls, 71 detected (one clap missed), 0 false alarms, 0 falls; azimuth error mean 1.4 deg (max 7.0, 12 calls from behind all resolved); head latency from the sound median 0.40 s (p90 0.72), decided 60 ms after onset; overshoot median 0.12 rad (max 0.52, double_take); trunk tilt median 0.45 deg, max 0.99; stress 6.6 V / 8 %: same detections, 0 falls, tilt max 0.89. Keyword spotting measured (sherpa-onnx zipformer 3.3M int8: RTF 0.017 on the M1 Pro, estimated 0.07 of an A7Z core cool and 0.32 throttled at 416 MHz) and left out: over the quarter-core budget beside the brain when throttled; onset detection only, `--kws` hook later. No recorded A7Z 4-channel wav in the repository to replay. Robot test for Shawn: `install_namecall.sh`, brain in walk at zero command, `namecall.py --mute --once 3` (head only), then `--once 5` with sound; checks the ear channel order (`--swap-ears`), front/back, false triggers, and whether the 16-bit quack playback shifts the capture (self-check's I2S0 note). Proposed, not made: `head_raw` want key in walk_brain, a `quack_file` key in walk_wired so the jaw opens with the chosen call.
- **Voice chain built off the robot** (`pet/voice/`, background agent): `listen.py` cuts one utterance per sentence out of the A7Z-format 4-channel stream (ears downmixed, namecall onset detector, trailing silence, 1-8 s, 16 kHz out; also a WAV or a Mac microphone); `stt.py` is one `transcribe()` over two backends, local SenseVoice small via sherpa-onnx (default) and ElevenLabs Scribe v2 (Keychain key, 401 today); `intent.py` asks Haiku through `claude -p` for task / rule / ignore and validates with `pet/mind`'s validator or `pet/learn`'s instruct parser; `voice.py` writes `pet/state/inbox/` (new section in `pet/state/README.md`). Measured on 20 `say` clips (en Samantha, zh Tingting): SenseVoice 8.3 % error (en WER 10.7 %, zh CER 6.2 %), median 0.15 s per clip at 4 threads on the MacBook; Whisper base 41.7 % (traditional characters, Mandarin hallucinations) at 0.31 s; the listen+SenseVoice chain on the robot-format clips 13.3 % (`out/stt_bench.md`). Intent 20/20 (`out/intent_eval.md`), median 4.9 s, $0.0073 for the run. End-to-end dry run from the 把橙色方块叼来 clip: STT read 雕 for 叼, Haiku still composed look_around -> walk -> groundpick, validated (`out/e2e-zh01-robot-wav/`). The Mac mini had 558 MiB free on its data volume, so models and benchmarks ran on the MacBook under `nice`; moving them needs space freed there first. Not done: the runner's pickup of `inbox/tasks`, any run on the robot's microphones, a shared capture so namecall.py and voice.py can listen at once.
- **Pickup target decision (Shawn, D-031)**: the first robot pickup stays the 1.0-1.5 cm orange ball ("直接上球"); the block-first ordering is rejected. Reason recorded in D-031: the training object is already the ball, and the 10/27 rehearsal's failure (beak 23 mm sideways during the close, neck pitch pinned at its range limit) does not depend on the object. Levers before any retraining: inner-tube lip liner (friction 1.1, in range; jaw marks redone after lining) and jaw close timing, both measured by the gap agent in the rehearsal. Retraining needs a separate go.
- **Voice chain verified here**: commit `bab3655`, 22 tests pass, evidence in `pet/voice/out/` (SenseVoice 8.3 % error on 20 synthetic clips, Whisper base 41.7 %, ElevenLabs 401; Haiku intent 20/20, end-to-end Chinese robot-format clip to a validated task in 8.8 s). Runner does not read `inbox/tasks` yet. Mac mini data volume has 558 MiB free: deploy there needs space first.
- **Seeing-pick gap found, sim only** (`microduck-sim/guide/firmware/mac/seepick-gap-20261029/README.md`, background agent; no training, nothing on the robot). The 0/96 rehearsal was the harness, not the policy: seepick61 in its own env on the rehearsal's exact 54 draws scores 0.94 (ball 0.92, box 0.95; weak only at x -0.03, 0.56). Defect 1: `evaluate_delay.load` edits body inertias after compile and MuJoCo's collision bounding volumes stay in the old axes, so the beak sank 16 mm into the floor with no contact (`--bvh-refit`: 0 -> 12/54). Defect 2: the as-built MJCF runs the pyramidal cone at impratio 1 where the training env runs elliptic / 10 ("sticky friction"); under pyramidal a pinched box creeps out and a ball rolls out whatever the torque or friction (`--sp-cone elliptic --sp-impratio 10`: 12 -> 24/54). Residual = jaw torque: the training jaw is 1.0 N m/rad with 0.5 N m effort ("assume enough beak torque"), the runtime gives the XL330 100 mA = 0.037 N m. Sweep on the corrected replica: 100 mA 24/54 (ball 5/27), 150 mA (the EEPROM ceiling) 49/54 (ball 23/27, box 26/27), 300/600 mA 50/54, training jaw 54/54; KP 400 alone 28/54. Ball levers (Shawn's two, ball only, 27 runs each): lip friction at 150 mA, bare PLA 0.35 -> 7, 0.5 -> 15, inner-tube lining 1.1 -> 22 (at 100 mA: 0, 0, 7), the ball does not squirt sideways (world travel 3-10 mm, mostly backward under the upper beak, which touches first in 20-26 of 27); close timing: the first touch comes at phase 0.34-0.40, never before the trained close start, so a close on first lip contact changes nothing (0 of 27 fire); the current is what makes the close fast enough (pinched at phase 0.40: 3/27 at 100 mA, 20/27 at 150). New: after the hand-back to stand61, 8 of 23 held balls leave the beak within 3 s (boxes none). Beak geometry: printed V1.36 = Pollen CAD within 0.2 mm, replica tighter by about 2 mm, a 10.6-14.4 mm ball fits all three. Fixes by location: (d) harness flags applied, loader-level BVH refit proposed (moves every as-built sim baseline, Shawn's call); (a) `jaw_ctl.GOAL_CURRENT_MA` 100 -> 150 as a proposed diff only; (b) next training run models the jaw at the deployed torque, waits for the go; (c) line the two pad faces with inner tube, no reprint. Commits: `gap_trace.py --exact/--object-yaw` on `cmu/grasp` (689918dd).
- **`pet/see/` delivered, Mac and Mac mini only (nothing on the robot)**: open-vocabulary detector as a drop-in for `orange_target` in the pickup chain (`pet/see/detect.py`: `OpenVocabDetector`, `DetectorClient`, HTTP service; README has the proposed `main()` diffs for approach.py / seepick.py, not applied). Chosen: YOLO-World v2 small + CLIP ViT-B/32 text prompts, 12.4 fps on the Mac mini CPU (80.7 ms median, load avg 6), 13.8 fps on the MacBook; OWLv2 base 0.57 fps and Grounding DINO tiny 0.26 fps on the MacBook CPU, both rejected on latency (GDINO also on precision: 46 false positives over 66 negatives). Quality on 25 evidence frames (4 real head-camera snapshots, 21 synthetic pastes of Shawn's own photos and drawn objects, labelled in `pet/see/out/frames/manifest.json`): YOLO-World hit rate 0.62 (orange printed part 8/11, ball 3/3, remote 2/3, drawn keys 0/3), 6 false positives over 104 negatives, 1 on the duck's own foot; 0 detections on the 4 real frames. Finding: the prompt wording decides more than the model; "orange block" scores 0.00 on the printed part, "orange toy" 0.24, so `detect.SYNONYMS` expands the pickup object's name. Round trip MacBook -> Mac mini service over Tailscale: median 249 ms, p90 390 ms (model 148 ms on a busy Mac mini), inside `FRAME_MAX_AGE_S` 0.6 s with little margin while sims run there. Blockers seen: the Mac mini root volume had 0.2-2.2 GB free (its `~/.cache/uv` holds 8.3 GB), so only the 25 MB YOLO weights and a prompt bank live there; the two rejected models were timed there with random weights. 15 tests pass (`pet/see/tests`).
- **Jaw grip current 100 -> 150 mA** (Shawn "改 150 mA", D-031 addendum): applied in `jaw_ctl.py`, 59 pickup-mode tests pass, CURRENT-STATE `jaw_grip_current_ma` added (deployed false: A7Z off). Deploy = `guide/firmware/a7z/install_teleop.sh` then `~/duck-run.sh` on the A7Z (pkill + restart of walk_wired; torque is kept across the restart).
- **Open-vocabulary detector verified here**: commit `fe31603`, 15 tests pass; YOLO-World v2 s 12-14 fps on CPU, OWLv2 and Grounding DINO rejected (< 0.6 fps); 0 detections on the four real head-camera frames so far, so prompts must be tuned on robot frames before it replaces `orange_target`.
- **BVH refit across every as-built sim baseline** (`microduck-sim/guide/firmware/mac/bvh-refit-baselines-20261029/README.md`, background agent, Mac mini, sim only, no default changed). Every baseline ran twice with the same seeds and real flags (7.0 V, 4 % drops), without and with the collision-box refit applied inside `evaluate_delay.load`, harnesses unchanged. The refit moves the boxes of the head (`jaw_soft`, geometry up to 37 mm outside its stale box), trunk (18-39 mm), thighs and shins (32 mm) and hips (10 mm); the feet are unaffected. Identical result rows with and without: sim_suite 10 cases, kicks, groundpick, approach 22 runs (11/11 without drift, 7/11 with robot drift), namecall (72 calls, 71 detected, 0 falls), joint-failure study (130 runs, 0 falls); teleop changes one sit-stand run (peak tilt 41.6 -> 39.5 deg). **Get-up stays 50/50**; without the refit the beak sank up to 40.8 mm (37 of 50 runs) and the trunk up to 7.9 mm into the floor with no contact. The study's "2 side starts went down again" were that artefact (head under the floor during the push-up) and vanish (0); longest saturation 0.50 s -> 0.38 s; medians 2.20-2.48 s. Variants: IMU 4 deg 50 -> 46/50 (re-falls while standing, window-edge noise), walk_wired 3.0 rad guard 33 -> 26/50 (real head contact makes rises ask for more action, so the guard must keep stepping aside), velstand 44 -> 44. Proposed (not applied): refit inside `evaluate_delay.load`; it would need the `getup` fact's saturation line, the get-up README variants and `teleop-sim-check.json` refreshed. Seen, not caused by the refit: sim_suite com+5 falls in the open-loop STAND phase at 0.84 s (reference: no fall), approach with drift 7/11 (v4 record 9/11).
- **Live runner for `pet/mind` (`pet/mind/runner.py`, `RUNNER.md`, 60 tests)**: writes the brain's control file the way the app does (whole, atomic), reads the tick log and stdout back (fall = body gravity z past -0.5 for 0.3 s, guard trips, refusals, `sit: STALLED`, seated/standing) and stops the intention on any of them, and pauses when the app writes. Perception from the brain's rows (pads, gyro bumps), A7Z mic levels and camera frames through `pet/identity`. Modes `--dry`, `--sim` (fake_pi + walk_brain), `--robot` (an agent sent over ssh; nothing installed on the A7Z). Not run on the robot. **30-minute simulated day** on the Mac mini (Haiku 5.5 through `claude -p`, `--allow head,walk`): 100 intentions, 295 steps (turn_head 90, wait 72, look_around 37, nod 34, walk 28, approach_owner 17, bow 11, stop 5, wander 1), 575 commands, 3 validator rejections in 103 calls (approach_owner while the owner was away, twice; a skill guard), **0 brain refusals, 0 falls**, 0 guard trips, peak tilt 34.7 deg, model latency p50 6.6 s / p90 8.3 s, $0.05 at list price. 41 distinct sequences in 100, entropy 4.81 bits, 2 % repeats. The 2026-10-26 scripted day on 100-intention windows: 5.69 bits mean (5.01-6.11), 65 distinct, 4.6 % repeats over the day: less variety now, with sit and rest left out and the owner in view for only 3 of 100 intentions. Fallback batch, 3 x 10 min: 51-54 intentions each, 0 falls, 0 refusals, 4.46-4.74 bits. Evidence `pet/mind/out/runner-20261029/`.
- **Three sim falls found on the way, all on the brain side** (rows around each in `pet/mind/out/runner-20261029/falls/`): (1) `bow` sent ground-pick phase 1.0, which is phase 0 for the policy (`[cos 2 pi phi, sin 2 pi phi]`), so it began a new descent and fell at the switch to stand61; the runner now sends 0.9, walk_wired's `GP_DONE_PHASE`. (2) `walk_brain.py` ends the sit-to-stand rise on a 2.0 s timer (`UNSIT_S`) while the as-built knees cycle between 1.3 and 0.7 rad: through fake_pi the stand-up fell in 7 of 8 tries, and 3 of 3 through stand mode first; `brain_sim_check.py --sit-at 5 --unsit-at 45` does not fall but peaks at 44.4 deg. A rise that ends on the knees is proposed in `RUNNER.md` (not applied); simulated days run without `sit`. (3) Host stalls of 0.38 s (Mac mini during a 1 GB copy) and 1.0 s (MacBook at load average 94) toppled the 50 Hz sim brain; heavy runs moved to the Mac mini, the model calls reach the MacBook's `claude` through `pet/mind/claude_bridge.py`.
- **Voice inbox wired into the runner** (`pet/mind/inbox.py`, `--inbox`): a task file is renamed `.done` when taken and runs in place of the current intention through the same validator and readback; its outcome (`done`, `replaced by a newer request`, `stopped ...: fell`, `refused`, `dropped`) is an `owner_task` event and a line in the mind's recent events. A rule file goes into `rules.json` (pet/learn's `validate_rule`, same trigger and outcome replaced) and the live `pet.learn.match.Matcher`; "good duck" lifts valence by 0.4; the session is also written as a pet/learn day log. Traces on the Mac mini with the real voice files (把橙色方块雕来, "Stop going in the bedroom", 好鸭子真乖, 过来 / 停下 / 坐下): **B** (`--allow head,walk`): fetch done in 19 s (`groundpick` mapped to `bow`), rule added at weight 0.6, praise felt, 过来 replaced by 停下 5 s later, 停下 done, 坐下 refused (sit not allowed), 0 falls. **C** (all primitives): 过来, 停下, then 坐下 seated 3 s later, done; the model's own stand-up 12 s later fell (fall 2 above). **A**: 过来 came 2 s into a sit the model had chosen; the brain's stand-up fell and the next two requests were dropped while the runner was stopped. After the rule, the model's next intention in A: "I'll steer away from the bedroom and search for the orange block the owner asked for."
- **BVH refit applied in `evaluate_delay.load`** (`bvh-refit-baselines-20261029/README.md`, "Applied" and "Causes"; sim only, team repo copies stale until the next `sync_from_robotics.py`, nothing pushed). `brain_sim_check.py --bvh-refit` is a no-op (same summary md5 with and without), 39 unit tests pass. Re-verified: get-up 50/50, none going back down, longest saturation 0.38 s (CURRENT-STATE `getup` updated, old value superseded), IMU 4 deg 46/50, guard 3.0 26/50, velstand 44/50; `teleop-sim-check.json` regenerated. The three older-record differences: sim_suite com+5 falling and approach-with-drift 7/11 both come from D-030's neck 0.25 run on the stale 10-15 asbuilt model (on the plugged model +5 mm holds), so the references are stale; the teleop sit-stand seed 2 at about 40 deg comes from the V1.35 saddle manifest (`87979d52`), the robot's current mass model (the 10-19 and in-between manifests give 10-12 deg).
- **Sit-to-stand rise ends on evidence in `walk_brain.py`** (`microduck-sim/guide/firmware/mac/sit-rise-20261029/README.md`; sim only, not deployed to the A7Z, nothing pushed). The cause of the runner's falls is loop delay: sitstand61's rise finishes in 0.7-1.9 s with the sim's default 40 ms loop delay. With fake_pi's zero delay its knees cycle 1.4 -> 0.6 -> 1.4 rad for 6-8 s on the 10-15 model and fall backward on the current one. The current V1.35-saddle mass model adds tilt (17-33 deg against 3.6 deg on the 10-19 model). Pollen's simulator (2 s timer), infer_policy (stays on sitstand) and robotd (1 s, then velstand, kp 160 with low-pass) all wait a fixed time, and their settings do not rescue our model in sim. The 2 s `UNSIT_S` timer is replaced: knees under `SIT_KNEE_MIN`, pitch rate under 1.0 rad/s and tilt under 12 deg, held 0.3 s, hand over; not up in 4 s gives "sit: RISE FAILED", re-seats and waits for a sit. Runner-path seats: 10 of 16 fell before, 0 of 16 after, but none of the 16 stood (all gave up). In-process real conditions: 7 of 8 up in 1.3-1.5 s, seed 2 re-seats instead of a 35 deg crouch. Still failing: rises that fall during the rise (zero sensor delay 8 of 8, one compensated seed), and `{"mode": "stand"}` after a sit (4-5 of 7 fall even after 4 s of stand61; the same switch without a sit holds 8 of 8). 106 tests pass. For pet/mind: `brain_link.py` should treat "sit: RISE FAILED" like STALLED, and the runner should stand up with a walk command, never `stand`.
- **Runner follows the new sit hand-over** (after `faf5b73`): `brain_link` reads "sit: RISE FAILED" as a refused stand; standing up from a seat now writes `{"mode": "sit"}` then the zero walk (re-arms a failed rise, never the open-loop stand); the runner's dry brain mimics the evidence hand-over (up after 1.4 s) instead of the 2 s timer. 61 mind tests pass. Not on the robot; `walk_brain.py` with the hand-over is not deployed (A7Z off, needs Shawn at the robot for the three-seat test in `guide/firmware/mac/sit-rise-20261029/README.md`).
- **First robot recording of Mochi calls holds no usable call** (`namecall-20261029/recordings/calls_201411.wav`, git-ignored; 180 s, duck on the floor in stand, Shawn about 2 m away, duck turned 45 deg by hand between calls, head touched while turning). No voiced (harmonic) segment anywhere, SenseVoice finds no "Mochi" in overlapping 12 s chunks; every loud event (26-30, 37, 45, 54, 63, 75, 83, 144, 175 s) is broadband clicks from touching the head. `analyze_calls.py`'s eight "calls" were those touches, so its 122 deg mean error says nothing about direction. Between touches the 300-3000 Hz level stays within about 3 dB of the floor, so a call at 2 m, if made, sits at or under the robot's own noise. Background noise (quiet stretch, ears / back): 30-100 Hz -41 dBFS, 100-300 Hz -48, 300-1000 Hz -60, 1-4 kHz -67; 30-700 Hz coherent across the three mics (0.9-0.99) with few-sample delays, lines at 120 and 252 Hz. The A7Z fan (pwm-fan, state 4 of 4 at 47 C) adds only above 4 kHz (fan off: -5 dB at 4-12 kHz, under 1 dB below), so the low-frequency field comes from elsewhere (servos holding stand or the room; torque stays on, not separated). Next: `live_level.sh` on the A7Z prints the 300-3000 Hz level over the floor for each mic every 0.2 s; first check what a call at 1 m and 2 m reaches without touching the robot, then the eight directions with the duck untouched and Shawn walking around it.
- **Correction: the calls are in `calls_201411.wav`** (Shawn heard them clearly in the voice-band +30 dB copy, e.g. 00:20-00:22). Found by template match on the 21.75 s call: 21.75, 34.08, 42.43, 51.07, 59.79, 68.55, 80.31, 88.15 s (the last faint), one between each pair of head touches; SenseVoice hears them as "What지" / "What's it". Each sits only about 5 dB over the floor in 300-3000 Hz, under the detector's 12 dB threshold, which is why the onset picker and the whitened view missed them. Direction is still wrong with every method tried: the deployed 64 ms window and 0.6 s accumulated GCC-PHAT both return about -109 deg for every call (a steady source dominates), noise-subtracted GCC scatters (mean error 78 deg), and time-frequency-masked GCC (bins 3-10 dB over the per-bin noise) returns -40 to -130 deg for all eight. Masked pair lags hardly change as the duck turns 315 deg (left-right -6 to -9.3 samples, left-back +0.7 to +5) and do not close (left-right + right-back differs from left-back by up to 13 samples), so these lags are not one plane wave on the modelled geometry. Not separated yet: low SNR versus a channel timing or geometry fault. Next test: `test_burst.wav` (three broadband bursts) from a phone 1 m away at head height, eight directions, duck untouched, recorded with `record_calls.sh`.
- **The calls carry no direction at the microphones; loudness is not the cause.** A synthetic "Mochi" (macOS `say`) rendered on the modelled head geometry and inserted into quiet stretches of the same recording at the real calls' level (median 2.9 dB over the floor, 300-3000 Hz, 0.6 s) is localised with 0 deg error in all eight directions by the masked GCC (deployed 64 ms window: mean 26 deg at that level, 4 deg at +5 dB). On the real calls neither cue moves as the duck turns: masked left-right lag stays -6 to -9 samples, and the left ear is louder than the right by 1.1 to 5.9 dB in every direction, including -90 deg where the right ear faces Shawn (1-4 kHz, call power minus floor). The ears are meant to hear through dia 1.6 holes in the cap side walls (D-025); a common internal path, a blocked hole or a mic port facing away from its hole would give exactly this. Check: finger snaps 3 cm from each ear hole with `live_level.sh` running.
- **Snap test, 15 cm from each microphone opening** (`live_level.sh` raw copy a7z:~/duck-logs/live_204536.raw; Shawn snapped left ear, right ear, back, 1-8 kHz, 30 ms windows). Back microphone hears the outside: back snaps put it 5-6 dB over the right ear and 10 samples earlier, side snaps 5 dB under the ears. Ear pair does not: left-ear snaps L-R +3.1/+3.5 dB, lag -2.2/-1.2 samples; right-ear snaps L-R -0.1/-0.1 dB, lag -1.1/-1.1 samples. A source 15 cm off one ear should give about 10.8 samples (the full 77 mm) and a clear level flip; both ears behave as if fed through one shared path. Both ear channels carry independent self-noise (1-4 kHz coherence 0.2 in the quiet floor), so two live microphones, not one copied channel. Next: is each ear's dia 1.6 wall hole open and is the INMP441's port (the hole through the board) facing it, sealed by the foam ring.
- **Cover test: covering an ear hole changes nothing** (a7z:~/duck-logs/live_204926.raw; Shawn snapped about 15 cm out: left open, left with a finger on the hole, right open, right covered; groups read from the pauses at 22.8-25.2, 27.2-28.4, 30.7-31.7, 33.6-35.9 s). Strong snaps (over 40 dB), ear-minus-ear level in 1-8 kHz: left open +5.0 / -1.1 dB, left covered +0.3; right open (R louder) 3.4 / 1.5 dB, right covered 2.4 / 1.9. Snap-to-snap spread within one step (up to 6 dB) is larger than any covered-versus-open change, and the left-right lag stays within about 2 samples throughout. The ears do not hear through their wall holes; the cap has to come off to check hole, port orientation and foam seal.
- **Back microphone hears through its hole** (a7z:~/duck-logs/live_205910.raw; snaps about 15 cm behind the head, hole open then covered). Open (12.5, 13.5 s): back 2.5-4.4 dB over the ears, and at 13.5 s it leads both ears by 10.6-10.8 samples (a source behind predicts about 12). Covered (16.5, 17.0 s): back minus right ear +1.3 / -2.7 dB and the lead is gone (right-back -4.5 / -1.1 samples). Only two strong snaps per step, so the size is rough; the direction of the change is clear. The fault is in the two ears only.
- **Name mode for "Mochi" built, recall too low** (`namecall.py --name mochi`, `namecall-20261029/NAMECALL.md` section 9, `results/kws_mochi.json`). sherpa-onnx keyword spotter (public gigaspeech 3.3M int8) on the ear downmix; keywords are the spellings the model itself writes for "Mochi" (MARCHY, MALCHY, MORGY ...). On macOS `say` clips rendered on the head geometry: 30 % caught at 20 dB, 19 % at 10 dB (English voices 38 %, Chinese 13 %), 19-25 false wakes per hour of speech, 0 of 96 own quacks, direction at the word 2.6 deg mean, decision 0.44 s after the word ends. A7Z: 9 % of an A76 core (25 % of an A55, not real time when throttled), brain ticks undisturbed. `--any-voice` stays the default; next is fine-tuning the spotter on real "Mochi" recordings.
- **Ears repaired** (Shawn opened the cap, cleared the ear holes and re-seated the boards; a7z:~/duck-logs/live_221322.raw, same snap-and-cover test). Right ear open: leads the left by 10.2-10.9 samples (77 mm predicts 10.8) and is 2-6 dB louder; covered: lead and level gone. Left ear open: 2-6 dB louder than the right, lead 7-9 samples on two of three snaps; covered: equal. A finger touching a hole lifts only that microphone by 25-37 dB. All three microphones now hear through their own holes; next the 2 m Mochi recording again.
- **Second 2 m recording, ears open** (`recordings/calls_221619.wav`, git-ignored; duck untouched, Shawn walked round it). Background holds continuous Chinese speech from a loudspeaker (courtroom dialogue: 原告 / 被告 / 律师), so a second voice source sits in every window. SenseVoice finds "Mochi" at about 47, 56, 64, 72, 80, 88, 95 s (8 s spacing; the first call near 39 s is not confirmed). Calls are 1-9 dB over the floor at the ears. Masked SRP on the confirmed windows: the four side calls land on the correct side (+45 -> +51..+63, +90 -> +57..+63, -90 -> -54..-57, -135 -> -39) while +135, 180 and -45 do not; estimates compress toward the front, consistent with a steep elevation (Shawn standing, mouth about 1.4 m above the microphones) and with the competing loudspeaker. Not settled: the exact call times (Shawn is checking the voice-band copy) and the loudspeaker's direction. Next recording: loudspeaker off, 1 m first, then 2 m.
- **2 m calls replayed through the real chain: detector rebuilt, localiser rebuilt, direction still not recoverable** (`microduck-sim/guide/firmware/mac/namecall.py`, `namecall-20261029/NAMECALL.md` section 10, `replay_calls.py`, `results/replay_221619.json`; 52 namecall tests pass; nothing on the robot). Call times by ear from Shawn: 39.3, 47.1, 55.6, 63.8, 71.6, 79.8, 88.0, 95.1 s; the calls themselves sit 0.5-1.0 s after each (SNR spectrograms: a voiced "Mo" with 3-4 harmonics at 600-1000 Hz, then a "chi" burst at 3-5 kHz, 0.3 s in all). New default detector (`--detector bins`): per-bin SNR over a tracked noise spectrum plus a harmonicity check at the onset; defaults 9 dB, 8 bins, 3 confirming blocks, voicing 0.4: 6 of 8 calls, 3.1 false triggers per minute with the corridor loudspeaker (all of them its speech), 0.8 per minute on the earlier no-loudspeaker recording, 2 of 9 head touches; the most permissive setting finds 7 of 8 at 14 per minute. New default localiser (`--localiser call`): masked SRP-PHAT over the whole call (0.8 s), elevation prior 35 deg, band 1.5-8 kHz, back mic for front/back: on the five real calls it localised, 1 within 30 deg (+135 -> +138), side right on 2 of 4, front/back right on 4 of 4; acceptance (6 of 8 within 30 deg) not met. Cause, measured: under 1.5 kHz all three microphones hear the call through the head cavity, not through their holes. The masked left-right lag in 300-1200 Hz is 0 to 4 samples whatever the direction (free field predicts 6-9), the back microphone hears every call 3-9 samples after both ears, calls from behind included (it should lead by 9), and it is 1.5-4 dB louder than the ears in that band from every direction, while above 4 kHz the ears are louder from every direction, 180 included; the same pattern sits in the quiet-stretch noise and in the near-field snaps (right-back -3 samples where +6 is predicted). A sound entering at the beak and the mouth-floor speaker pocket and filling the cap reaches the ears first and the back seat 60 mm later, from wherever it came. Above 1.5 kHz the ear pair is aliased (77 mm) and the 0.1 s burst is mostly reverberant (PHAT peaks 0.1-0.3 with equal mirror lobes). Synthetic calls score 0 deg because they have neither the cavity nor the room. Hardware check before more recordings: cover the beak and the mouth-floor pocket and snap 15 cm off each ear; if the low-band ear lag grows from 3 to 9-11 samples the cavity path is confirmed and the fix is sealing the head cavity from the mouth (foam, or sealed chambers behind the microphone holes). Cost on the MacBook: detector 0.3 % of a core, localiser 24 ms per call; A7Z estimate 1.2 % cool, 6 % throttled, localiser 95 / 460 ms once per call. Next robot test: `install_namecall.sh`, then `listen_only.sh 600` with the loudspeaker off (listen only), then `namecall.py --mute --once 3` with the brain in walk at zero.
- **Low band carries no ear delay even at 15 cm** (post-repair snap recording live_221322.raw re-read per band). 2500-8000 Hz: the right-ear snap gives the full +10.2 sample lead and 4-6 dB level difference. 300-1200 Hz: lag 0.0 samples for every snap, open or covered, left or right, and covering a hole does not reduce that ear's low band. The snaps hold little energy under 1.2 kHz, so this band is partly the coherent servo-noise floor; the whole-call analysis in NAMECALL.md section 10 shows the same on the voiced calls. Reading: below about 1.5 kHz the microphones hear the cap cavity (uniform pressure, fed through the neck exit, jaw gaps and the thin wall), not their holes. Shawn: the speaker pocket is sealed with a foam ring and its ports sit under the closed jaw; the neck exit cannot be sealed. The fix that does not need a sealed head: a closed foam ring round each microphone port (the ears have two strips with open ends today, which let cavity pressure into the port), so each microphone hears only its wall hole. Check after: the same snap test, low-band lag 9-11 samples, then a 1 m Mochi round.
- **Face-view postures, sim and kinematics only** (`microduck-sim/guide/firmware/mac/face-view-20261029/README.md`; feature "Look up at a person", section 2). U20CAM on the face: 640 x 360 published frame, equidistant fisheye f 359.5 px, 28.7 deg vertical half angle, 63 mm IPD reaches the face model's 10 px at 2.26 m range. Measured in the as-built sim (plugged manifest, 7.0 V, 4 % drops, Mac mini): stand61 at zero command with the head command at its cap (`head_pitch` -1.10 delta) reaches head -0.73 while the policy drops its own neck to -0.27 (neck commands are ignored), camera 0.27 m, axis +30 deg, top of frame +59, tilt 2.0: a seated owner at 1 m (17.5 px, 40 deg below), a crouching person from 0.5 m, a child from 0.5 m, a standing adult only at 1.0-2.2 m (14 px at 1 m, 53 deg below). The seat follows the same command to head -0.49 (neck 0.29, trunk 2 deg back, tilt 2.2): axis +47 deg, top +75, a standing adult in frame from 0.5 m (16 px) and 1 m (13 px), seated owner 0.3-2 m; walk61 at 0.25 m/s with head_pitch -0.75 also gives +47 deg (never robot-run head-up). Groundpick bow: camera 0.03 m, axis -72. No trunk-pitch command exists (walk_brain zero-pads the 6 body slots; velocity env body_pose weight 0; Pollen's velstand has it, we do not run velstand). Open-loop stand: every head-up keyframe falls backward on the as-built model (head -0.30 at 1.8 s, every COM offset -2.0..-3.0 mm; beg and tiptoe at 1.2-1.4 s; a 6 s ramp changes nothing, the falls are static); only a 20 deg forward lean on the ankles with head -0.90 holds 7 of 11 (axis +46). Start-pose noise of 0.03 rad tips even STAND (7 of 11), so round 3 used the COM range, pushes and read-drop seeds as the spread. Lying on the back: camera 0.12 m, axis 27-89 deg by head pitch, adult in frame from 0.3-1 m, needs the get-up. Four-joint head search (0.1 rad grid, policy and hinge boxes): pitch alone reaches the vertical but neck-back poses collide with the trunk hull (4-17 mm); head roll is +-0.31/0.44 rad so yaw 90 + roll buys at most 18-25 deg; Shawn's neck-forward yaw-left roll pose gives +2 deg in the sim; no yawed pose beats pitch, and they roll the picture 60-115 deg. Rules: the person should look at the duck (then the 15-30 deg pitch limit does not bite; looking straight ahead a standing adult is 53 deg below at 1 m, 34 at 2 m, never under 30 inside IPD range), back to 1-2 m from a standing adult or sit and look up from 0.5-1 m, owner on a sofa at 1-2 m, crouching person at 1 m is the best case (28 deg, 20 px). Renders of the camera view in `results/renders/`.

## 2026-10-30

- **Deployment plan for the pet behaviours** (Shawn: start deploying them on the duck one item at a time, observe, look around, remember): `docs/PET_DEPLOY_PLAN.md`, eight stages with behaviour, what exists, what to build, the robot session and acceptance numbers: 1 looking around (head only), 2 seeing what is around (open-vocabulary detector on real frames, bearings), 3 remembering sightings (object memory, missing-object surprise), 4 knowing the owner (parallel), 5 name call (waits on the foam rings), 6 hearing the owner, 7 guarded walking, 8 night reflection on a real day.
- **Stage 1 prepared**: runner `--save-frames` (`pet/mind/perception.py` `FrameRecorder`; the A7Z agent now forwards `q`, `head_cmd`, `quat`), 62 mind tests pass. Read-only robot check over ssh (brain in walk at zero, camera daemon running, nothing written): 19 frames in 20 s, all matched to a brain row within 0.07 s, joint angles present. At neutral head pitch the frame is mostly the tile floor, so stage 2's look-arounds must pitch the head up. The control file holds `"jaw": "open"` next to the zero walk, which the runner's start check refuses; the app's stand button clears it. Not yet run: the 10-minute head-only session (Shawn at the robot).
- **Stage 1 first robot session cut short** (`pet/mind/out/runner-20261030-stage1/`): runner `--robot --allow head` started on the robot 01:16:55, three Haiku intentions (look_around, turn_head, nod), 0 falls, 0 refusals; stopped by me at 01:17:36 when Shawn asked to move the duck back from the end of its charging cable. Not accepted; to be rerun.
- **Tether problem (Shawn 2026-10-30)**: the charging cable leaves the backpack at its lower left rear, so a cable always trails behind on the left; the duck must not trip on it and must not walk so far that it runs out; when the cable is out too far it has to walk back; it may turn on the spot to look around and locate the cable and the coil on the floor. `pet/mind/glance.py` (frame -> Haiku vision description, 3.7 s, under $0.001) and `pet/mind/survey.py` (turn on the spot to +90, 0, -90, 0, never a full circle; look left, ahead, right with the head pitched down at each stop; frames saved with joint angles and IMU quaternion).
- **First survey run: the left turn on the spot did not turn** (`pet/mind/out/survey-20261030-012122/`). Command walk vx 0, vtheta +0.3 for 11 s: the brain's turn output rose to its cap +1.35 (vtheta + 3.0 x ARC_LEAD 0.35), walk61 stepped in place, the body ended 15 deg to the right by the IMU quaternion and 10 deg right by the integrated body yaw rate (same sign, so not a sign error); the survey stopped itself. Duck position: a wall fills the frame at head yaw +1.2 (very close on its left), a door frame on the right, open floor ahead; no cable in any of the three looks (the cable trails behind, outside head yaw +-1.2 plus the lens). Not separated yet: wall contact on the left, drag of the cable, or a rightward bias of walk61 turning in place on the robot (its in-place drift was never measured, walk_brain SPIN notes).
- **Cause of the failed left turn: the duck hit the wall** (Shawn watched it: "碰到了"). The turn on the spot was blocked by contact on the left, so it says nothing yet about cable drag or an in-place bias. Lesson for the tether logic: check the clearance on the turning side before a turn (the left look showed the wall filling the frame). `survey.py --right-first` added for the open-floor rerun.
- **Survey on open floor works; turning on the spot works on the robot** (`pet/mind/out/survey-20261030-012432/`, `--pre-walk 0.25,-0.3,2.5 --right-first`). Walk-out arc: commanded right turn at 0.3 rad/s for 2.5 s gave only 7.7 deg (about 43 expected). Turns on the spot (vx 0, vtheta +-0.3, brain turn output up to its cap): right to -80.9 deg in 11.4 s, back to +0.4 in 7.2 s, left to +106.0 in 8.0 s (stopped at 85, 16 deg overshoot), back to -0.7 in 9.2 s; no fall, no guard. Cable: seen only in the looks at body +106 deg (head yaw +1.2, ahead), i.e. facing about 175 deg from the start heading: a slack grey cable over the floor to Shawn's desk, with loops near the desk; Haiku called it slack and found no coil (`pile_visible` false in all 15 looks, the loops not counted as one). In the other 13 looks no cable. Scene by Haiku matches the frames (doorway, box, laundry basket, bed frame, chair, the wall again close at +106 ahead). So the cable can be checked by turning round, not seen while walking forward; "don't go too far" needs odometry from a known start, with a look back as the check.
- **First robot session with cable limits** (`pet/mind/out/runner-20261030-tether1/`, `--tether 1.0`, stopped at 3 min on Shawn's report): 11 Haiku intentions, 0 falls, 0 refusals, 0 guard trips; the guard refused one approach_owner walk (would end 1.31 m out, limit 0.85, room 0.44 m) and the mind chose head turns instead. The model chose vx 0.1 walks twice (4 s, 5 s); the odometry's 0.6 m/s per vx is measured only at vx 0.25, so the 0.41 m it booked is an overestimate (safe side). Shawn: it never saw him, it was slow, it did not know where it was. Causes: no camera input reached the mind (face recognition off, glance only used for the cable); vx 0.1 barely steps; approach_owner walked straight ahead with no bearing.
- **Fix: `--see`** (`glance.Scene`, runner): vision model at each head pause -> person and things with bearings in the start frame (fisheye f 359.5 px + head yaw + IMU heading); the prompt lists them relative to where the duck faces; startup look left/ahead/right; approach_owner turns closed-loop toward the owner then walks; robot walks sent as tested (vx 0.25, spin +-0.3); the cable guard is told the planned turn of a closed-loop turn. 70 mind tests pass. Real frame with Shawn on the chair: person found at x 0.42 (8 deg left of the axis), chair, cabinet, cable named; 9.4 s, $0.0017.
- **`--see` session fell; cause: the brain stalled 348 ms on a page fault, not the cable reflex** (`pet/mind/out/runner-20261030-see1/`, brain log `duck_wired_log_app1030-040713.jsonl`, blackbox `b0043-128f4cfe-sys.jsonl`). Startup looks found no person (Shawn was behind it); the mind wandered toward the doorway; at 0.52 m out the cable reflex started a +176 deg turn on the spot (vx 0, vtheta +0.3) straight from the vx 0.25 walk. The turn itself was steady for 8.4 s (yaw 0 -> +100 deg, body tilt under 8 deg). At 01:43:56.92 one brain tick took 348 ms (`loop_ms`; bus read 9.4 ms, so not the servos): walk61 stood on its last mid-step goals, the body tipped 28 deg and swung 30 deg back in yaw, the first fresh policy action was 3.5 rad on the left hip pitch, the guard switched to open-loop stand and the duck fell at 57.6 s. The blackbox shows the brain in D state in `filemap_fault` at 56.9 and 57.2 s: its code pages had been pushed out (afterwards RSS 11 MB, 42 MB in swap) by a `python3` started over ssh at 01:43:50 that loaded the whole 671 MB brain log into memory (memory available 1435 -> 850 MB, kswapd busy). That command came from another Claude session in this repo; my own later copies of the same log caused further 1-7 s stalls while the duck stood. Brain loop stalls over 100 ms in the session: 2 in 232,706 walk ticks before the reader, 14 in 44,833 stand ticks while the log was being read. Fix: `walk_wired.py` locks its pages in RAM at start (`mlockall` with MCL_ONFAULT; `/etc/security/limits.d/90-duck-memlock.conf` lifts radxa's 245 MB memlock limit, installed by `install_teleop.sh`) and writes its tick log from a separate thread (the blackbox also caught it waiting in `jbd2_journal_get_write_access`). Installed on the A7Z and checked (`memory lock: on`); active from the next `~/duck-run.sh`. AGENTS.md now forbids parsing brain logs on the A7Z. Acceptance still to run: restart the brain, stand at zero walk, run the same whole-log reader, and require no tick over 40 ms and zero major faults in the brain.
- **Memory-lock fix accepted on the robot** (Shawn: 现在重启验收; `microduck-sim/guide/firmware/a7z/brain_stall_check.py`, results in `a7z/stall-check-20261030/`). Old brain before the restart (pid 1186, 30 s quiet, zero walk): VmLck 0, 39.7 MB of it in swap, 1395 major faults since its start, longest tick 29 ms. Brain restarted with `~/duck-run.sh app1030-015959` at 01:59:59, start line "memory lock: on", then zero walk (stand61): VmLck 925 MB of address space, RSS 70 MB, swap 0. Load: the same whole-log `json.loads` reader on the A7Z over the 730 MB log for 90 s (five runs, each stopped by a 1.4 GB `ulimit -v`), MemAvailable down to 168 MB (850 MB at the fall), kswapd busy, iowait up to 64 %. Brain: 4306 ticks, longest 33.5 ms, 0 over 40 ms, 0 major faults, never in D state in the blackbox; the duck stood throughout. Fact `a7z_brain_memory_lock` in `microduck-sim/CURRENT-STATE.json`. The pickup-struggle `hold.py` patch is still not applied (this brain runs the old hold logic).
- **Hold patch, robot run 1 (02:08-02:11, `duck_wired_log_app1030-020818.jsonl`, scratch copy `holdfix.jsonl`)**: Shawn: no struggle in the hand, but set down it fell and never went back to closed-loop stand. Cause: at 02:09:32 R2 read about 1400 counts under its rest value a few times (bad blocks); the rest baseline sank with them and afterwards the untouched pad read as a full hand (e stuck at 0.142, over GATE_LO), so the lift never ended and the set-down duck stood at kp 80 and s 0 until it sagged over. Fix in `hold.py` `pad_levels`: a reading more than `pad_lo` under the baseline counts as no touch and does not move the baseline. Leg current at kp 80 does not tell the floor: 101-125 mA in the air, 124-145 set down with the hand on (calibrated air 138, stand 294).
- **Hold patch, robot run 2 (02:13-02:16, `duck_wired_log_app1030-021340.jsonl`, `holdfix2.jsonl`)**: Shawn: struggled during the hand change, but set down it went back to closed-loop stand. Set-down: the hand left at 02:15:50.04, s 1.0 at 50.29, stood. Regrip at 02:15:45: the hand moved R1 -> L2, coverage under GATE_LO for 0.17 s, e (falling with LETGO_TAU 0.06 s, rising with GRIP_TAU 0.6 s) under GATE_LO from 45.24 to 45.78; the lift ended at 45.24, s 0.99 by 45.35, walk61 flailed in the hand (action up to 2.3 rad, legs 1-2.3 A, gyro up to 12 rad/s) until 48.2, and its own current read as load 1.0, so the lift could not be detected again. Body gyro separates the hand from the floor: rolling 0.2 s max |gyro| 0.5-1.0 rad/s just before the regrip, 0.02-0.05 set down before the release; in the hand it stays under 0.2 rad/s only for short stretches (0.3 s at most, 02:10:44.75).
- **Fix for the regrip** (`hold.py`): mid-lift the hand counts as present while coverage or e is at least GATE_LO, and the lift ends on an empty grip only after REGRIP_S 0.5 s, or at once when |gyro| has stayed under STILL_W 0.2 rad/s for STILL_S 0.2 s (resting on something). `walk_wired.py` passes the IMU gyro magnitude, `brain_sim_check.py` the sim's. 35 hold tests pass, four new (regrip in the air keeps the hold, still set-down release hands back within 0.2 s, a short still stretch before a regrip keeps it, no gyro ends after REGRIP_S). Replay of run 2 through the new estimator (`pickup-struggle-20261030/regrip_replay.py`, leg current in the flail window replaced by 119 mA): s 0 and kp 80 through the whole regrip, the release on the floor hands back on the same ticks as the robot did. Installed on the A7Z 02:22.
- **My brain restart at 02:22:37 knocked the duck over**: I restarted with `~/duck-run.sh app1030-022237` to load the fix while Shawn was testing name-call with another session (`namecall.py`: head poses, then at 02:22:33 a body turn on the spot vx 0, vtheta 0.3 for 13 s; the brain was upright, gravity z -0.996, until its last tick 4 s into the turn). My earlier restarts at 01:59:59 (the memory-lock acceptance), 02:08:56 and 02:13:33 and my zero-walk writes after them also cut into those name-call takes; the 02:10:58 `{"mode": "stand"}` was not from this session. I had read the control file seconds earlier (zero walk) and did not check again. The restart cut walk61 mid-step; the new brain's first IMU sample shows the duck on its side (gravity in the body [-0.32, 0.91, 0.26], legs splayed). Rule for later restarts: read the last 2 s of commands and the running drivers in the same step, restart only when nothing drives the duck. Robot retest of the regrip fix not run yet.
- **Regrip fix accepted on the robot** (Shawn: ok了; brain `getup1030-062931` started 02:29:31 with the new `hold.py`, log slice copied to the Mac). Two lifts by the head with regrips: 02:35:04-02:35:14 (10 s, pads empty 0.12 and 0.04 s mid-air) and 02:35:33-02:35:43 (9.5 s, pads empty 0.33 s mid-air). Through both lifts s stayed 0.00 and the leg gain at 80-89, policy action 0, leg current at most 128 mA (run 2's regrip: action 2.3 rad, up to 2.3 A). Set-downs: the first ended on the 0.5 s allowance with the body still swaying at 0.4 rad/s, the second on stillness (0.43 s still); both stood afterwards, tilt at most 10 deg and action at most 0.22 rad in the next 1.5 s. The longest mid-air regrip, 0.33 s, is two thirds of REGRIP_S.
- **Name call on the robot at home (quiet room), 05:41-06:23 UTC** (`namecall.py`, logs a7z:~/duck-logs/namecall_20261030-05*.jsonl, 061020, 062135). First response worked once (05:43: call judged -89.5 deg, Shawn was at the right rear; head to the cap, quack) and then the microphones went dead for the rest of the run: **on the A7Z sound card the start of a playback stream silences a running capture** (-50 -> -150 dBFS in 0.5 s, back only when arecord is reopened). Fix in `namecall.py`: a silent playback stream on the ALSA default device (dmix) is opened before the capture and held (`PlaybackKeepAlive`); quacks mix into it and the mics recover 0.5 s after the quack. Second finding: with the stream open the capture ran at 44.1 kHz because the dmix slave rate was 44100 (shared I2S clock); `/etc/asound.conf` on the A7Z and `bringup/scripts/pi_audio_setup.sh` now say 48000. CURRENT-STATE `a7z_audio_capture` updated.
- **Pitch sign in the express card was inverted**: `pet/express/cards/duck.json` mapped gaze pitch "up" to +head_pitch and -neck_pitch; on this robot +head_pitch looks DOWN (approach.py HEAD_PITCH_WALK, NEAR_HEAD) and the first name-call pitched the head down to 0.51. Now gaze pitch -> -1.0 head_pitch, +0.25 neck_pitch, head_pitch limit +-1.10 (= HEAD_RANGE), and `namecall.py` LOOK_PITCH 1.1 = the look-up cap (head_pitch -0.75, camera 30 deg up, face-view-20261029): a caller is a standing person, the planar microphone array cannot measure elevation, so the duck always looks up at a face. Test `test_response_looks_up_to_a_standing_face`.
- **Quacks dropped by habituation**: the take library's `vocal_events` drops the call at random on habituated or glancing takes (novelty x0.75 per call, 40 s recovery); on the robot the second to fourth answers had no quack. Shawn: the feature is fine, but skip the call only when he has really repeated it. `namecall.py` now adds its own quack when the take has none and novelty >= 0.3 (about the fifth call inside 15 s; one call every 30 s is always answered).
- **Body turn toward a caller behind** (`namecall.py` `_start_turn` / `_turn_tick`, `--no-turn`): the head cannot reach a caller beyond 1.2 rad (the servo reached 0.95 on the robot). From the moment the take's head arrives, the body turns on the spot (walk61 vtheta 0.3, the robot-tested turn, 7-13 deg/s measured, TURN_RATE 0.17 rad/s assumed) while the head tracks the caller in the turning frame (yaw = bearing - estimated rotation, pitch up) and so unwinds to centre as the body comes round; the turn ends TURN_KEEP 0.3 rad short, the head eases home over 1 s, the control file returns to the zero-command walk. First version turned after the head had come home; Shawn: unnatural, a person turns head and body together; rewritten before the second robot try. First robot turn (06:22:33, caller at 162 deg): upright and turning for 4 s, then cut by the pet-mind session's brain restart at 06:22:37; the duck fell (brain kill keeps the mid-step goals). Not yet seen to the end on the robot.
- **Who wrote the control file**: 05:59:59, 06:08:56, 06:13:33, 06:22:37 brain restarts and the vtheta -0.3 writes came from the pet-mind session (it has stopped until Shawn tells it in its own session); the 06:10:58 `{"mode": "stand"}` came from neither session, source unknown (the app?).
- **Get-up, first robot trial, from the right side: did not rise** (CURRENT-STATE `getup`; run getup1030-062931). The first attempt never started: `walk_wired.py`'s 30 deg tilt stop fired on the first walk tick, 0.2 s before the brain's lying debounce armed the sequence (fixed: recover mode skips the tilt stop in walk mode, the brain owns falls; walk_wired tests and the 9 getup tests pass). Second attempt: LIMP 0.2 s -> POSE 1 s -> RISE: the legs moved for 0.5 s (left hip pitch 1059 ticks from goal, 850 mA peak), then stand61 settled into a static pose on the side (action constant 2.62 rad, right hip roll 130 ticks off its goal, 50-70 mA, trunk gravity unchanged for 4.5 s) and GAVE UP at 5 s. The real duck on its side does not roll onto its feet as the sim duck does; face-down and face-up starts untried on the robot.
- **Get-up, second robot trial, from a forward lean: the re-arm threw the duck onto its side and the side rise repeated trial 1** (CURRENT-STATE `getup`; run getup1030-062931, log lines 15546-15900). Shawn set the duck "face down"; it rested on its beak in a 38 deg forward lean (gravity [-0.61, +0.04, -0.79]), which the brain's lying test (gravity z >= -0.5) does not count as lying, so the sequence did not arm. Re-arming by a command change (vtheta 0.01, then zero) took the brain from the kp 50 gave-up hold straight into walk at kp 200: the policy acted at up to 3.3 rad from the asymmetric hold pose (knees -0.58/+1.02), a `{"mode": "stand"}` from the app side arrived 0.3 s later (kp 400), and 0.6 s after the re-arm the duck lay on its LEFT side (gravity y -0.91). LIMP -> POSE -> RISE then ran from the side and gave up at 5 s exactly like trial 1 (static, gravity [-0.52, -0.85, +0.07], head pitch and neck at 340-360 mA against the floor, no faults). Shawn righted it by hand at 06:37; brain back in walk at zero command. Three robot facts: stand61 at zero command cannot roll the duck from its side onto its feet (the sim's 10/10 side rises are wrong about the real duck); a beak-down lean is not "lying"; re-arming from the hold must not hand the policy a non-standing pose at full gain. Face-up start untried. Next design step, sim first: a scripted roll-to-prone plus push-up keyframe sequence before stand61 takes over, and a re-arm that passes through LIMP/POSE instead of walk.
- **Name call at home, table test: the microphones hear Shawn, the public keyword model does not; a body turn tripped the duck** (namecall.py; runs namecall_listen_065404, nc_run3 06:47, namecall_table_0735; recordings `~/duck-logs/live_073135.raw` on the A7Z, `calls_0722*.wav`). Facts from the audio: Shawn's calls reach the ear microphones at -27 to -38 dBFS in the voice band, 11 to 17 dB over the home floor of -48 to -50 (last night's lab recordings sat at -13 over a -21 floor, the whole path 25 to 30 dB louder; the mics, driver and arecord path are unchanged). The CallDetector finds every call (6 of 6 in the 103 s open-ended recording). The sherpa-onnx gigaspeech 3.3M keyword spotter fired on none of them at thresholds 0.25 down to 0.01 and input gains 0 to 38 dB; its own recogniser transcribes his "Mochi" as ONCE, MONTY, MAINTING, I, a different string each time, so no keyword spelling can catch it (the synthetic evaluation of 2026-10-29 already gave 30 % recall at 20 dB SNR, 13 % for Chinese voices). Decision: the public model is out; a spotter trained on Shawn's own calls replaces it (recordings in hand: 16 labelled calls of 10/29 in `namecall-20261029/recordings/`, the 10/29 `live_*.raw` sessions and today's six; plan below, not started). Any-voice at home is unusable as a trigger: in two minutes it answered nine "calls" (servo noise, its own quacks' echoes, a source at 98 to 110 deg) while Shawn said nothing. Table test with any-voice at 07:35: a face was locked and followed at 07:36:03; six seconds later a noise "behind" (az -159 deg, margin 0.345, just over the 0.3 gate) started a body turn (vtheta -0.3) although the face was in view; 2.3 s into the turn the duck stumbled forward (gravity x -0.34 at 3.5 s), a `{"mode": "stand"}` from the phone remote arrived mid-stumble (kp 400) and it fell on its front left. Changes (namecall.py, installed): the body turn is opt-in (`--turn`), off by default; with `--turn` a face in view also vetoes it. Also: fixed-length recordings missed Shawn's calls twice (07:20, 07:22); captures that wait on him now run until he says stop (`live_level.sh 36000`, raw kept). A call from 20 cm in front localised at +164 deg (margin 0.6): near-field callers break the far-field bearing; untreated. The 06:10:58 and 07:36:12 `stand` writes came from the robot-live phone remote (A7Z PID 6497, `app/a7z-bridge.mjs`).
- **Mochi spotter from Shawn's voice, plan (needs his go before training)**: positives = every call the detector cuts from the saved recordings (10/29 scripted 16, 10/29 live sessions, today's 6; each checked by ear), negatives = the rest of those recordings, the duck's own quacks and the 22 min of speech used on 10/29; features = log-mel of the ear downmix at 16 kHz; model = a small CNN (tens of kB) trained on the Mac in minutes, run on the A7Z inside KeywordGate at the detector's onsets only (so the cost stays at the call rate, not continuous); acceptance = at least 9 of 10 held-out calls at 1 to 3 m, under one false wake per 10 min of speech and none on its own quacks, then the table test again. More variety (distance, tone, other rooms) is recorded only if the held-out score says so, with the open-ended recorder.
- **T1, the body follows the head (fork `cmu/finetune/modal/FINETUNE-DELTA.md`, "Run t1 plan"; Shawn nodded 10/30)**: the as-built CPU sim (plugged manifest, new `brain_sim_check.py --neck-pitch`) reproduces walk61's robot behaviour: standing, the neck reaches a third of the command (-0.4 -> -0.125, -0.8 -> -0.26 absolute; robot -0.09), and at vx 0.25 any head command stops the stepping (7 mm in 6 s). So the limit is the policy, not sim-to-real. Fine-tune delta `DELTA_T1`: forward-only vx 0..0.30 with 15 % exact-zero envs, head commands biased to looking down (neck -1.10..+0.40, head_pitch -0.30..+1.00, yaw +-0.90) held 3-8 s, ft3's EMA velocity tracking, head_pose_bias 5.0 at tau 0.5 s; actor input unchanged (61 numbers, no camera). Degenerate audit from the cfg constants (`tests/test_t1_delta.py`): ignoring the neck loses 0.66/s, standing under 0.15-0.30 m/s loses 0.7-1.9/s plus air_time; creeping at 0.05 m/s is indistinguishable from standing, so the lowest trained speed is 0.10. Kaggle T4 (free, 15.9 h left today): audit-t1 and smoke-t1 pushed 10/30; the 1000-iteration run follows a PASS. Sim acceptance script `cmu/finetune/t1_sim_accept.py` (nine rows, including standing on the fine-tuned policy after a step, since walk mode uses stand61 before the first step). **Result (10/30 05:50)**: audit PASS (stand/walk 0.748, falls 0.19), smoke PASS, run t1 1000 iterations in 81 min on one T4, no guard stop; speed along the command 0.035 -> 0.182 m/s, low-command speed 0.026 -> 0.165, tracking error 0.270 -> 0.207, best reward at iteration 800. Acceptance on it800 (`models-t1-best`): with the neck at -0.4 / -0.8 the duck walks 1.09 / 0.95 m in 6 s (walk61: 7 mm) and the neck ends at -0.39 / -0.71; after a 2 s walk it stands with the neck held; with head pitch 1.2 it walks 1.3 m. Sim suite (plugged, real cases): no falls, more distance in every case (2.06 m vs 1.17 at vx 0.25; steps at 0.20 where walk61 does not), but 3-4 deg more peak tilt and 14-27 action jumps per 10 s against walk61's 1-10, the same jitter pattern ft3 had before it fell on the robot; stress cases drop8_imu35 and bare-feet floor fall (report only). Standing rows before any step still run Pollen's stand61 (unchanged, neck stays up): a deployment question. Robot test pending; the A7Z was off Tailscale at 05:55.
- **T1 on the robot: the neck follows, the gait falls** (`microduck-sim/guide/firmware/mac/robot-runs-20261030-t1/`, 10/30 10:27-10:29, Shawn at the robot, `t1_robot_test.py`). models-t1-best (it800). Neck: -0.4 commanded -> -0.38..-0.42 while walking at 0.25 m/s; -0.8 -> -0.70..-0.92 walking and -0.816 held 10 s standing after the walk at 1.9 deg tilt (walk61 reached -0.09). Gait: the plain 0.25 m/s walk with no head command fell sideways 3.4 s in (tilt 6.5 -> 12 deg, then 29 deg still walking, guard at 36); the two head walks stayed up but tilted 18-20 deg at the stop. Against walk61's five 0.25 m/s walks on the same robot the same day (`--see` session, seek windows of the A7Z log, nothing parsed there): peak tilt 13.8-29.3 vs 7.4-8.6 deg, action p95 1.77-2.06 vs 0.91-1.19, action jumps over 0.5 rad per tick 17-22 vs 1.4-2.7 per s, servo read misses alike. A 29 deg reading in a later stand step was Shawn lifting the duck (leg current 300 -> 130 mA, zero policy output), not a fall. Same failure as ft3 on 10/17-18: the sim suite showed the jitter (14 vs 1 jumps per 10 s) but no sim case fell. Not deployable; walk61 back on the A7Z at 10:29 (CURRENT-STATE `walking_policy` candidates updated). Next design question before any new run: why fine-tunes from walk61 come out jittery on the robot, and how published fine-tuning recipes keep action smoothness (literature pass first).
- **Own Mochi spotter trained on Shawn's voice, replacing the public keyword model** (`microduck-sim/guide/firmware/mac/ownkws.py`, trainer `namecall-20261029/train_mochi.py`, model `namecall-20261029/models/mochi_own.npz` 83 kB, report `results/mochi_own.json`). Recipe of the 18-763 lecture 21 Edge Impulse keyword lab (spectral features, a small time convolution, the keyword against other-speech and noise classes): 40-band log-mel over 1 s windows with the per-band mean removed, three conv + max-pool layers, a global max over time, softmax over mochi / speech / noise; numpy inference on the A7Z, 5 ms per score every 100 ms, 6 % of one core. Data: 56 calls cut as 0.2-1.0 s voiced runs from Shawn's open-ended home session (`live_141734.raw`, 110-226 s; Whisper large-v3-turbo could not read his calls at this level, so the cut is acoustic), 40 augmented windows each (word position, home-floor noise 3-20 dB SNR, speed 0.9-1.1, gain); speech = 6000 Google Speech Commands v0.02 words mixed into the robot's home floor, the 10/29 lab conversation, the duck's quacks, the synthetic near-miss words; noise = quiet robot stretches and the Speech Commands background files. The 10/29 by-ear call times were not used (off by more than 1 s, lab acoustics). Held out: the last quarter of the session 14/14 at P 0.5 and 13/14 at 0.9; the 07:31 table-test session 4/6 at 0.5 and 3/6 at 0.9; false wakes on 28 min of synthetic continuous speech at the robot's floor 2.1/h at 0.5, 0 at 0.9. Threshold 0.9 stored in the model. Replays of the real recordings through the whole namecall chain still fire on sounds whose content is unknown (live_073014: 5, live_141734 0-110 s: 2), so real-room false wakes are the open number; first live listen-only run started 14:33 (A7Z rebooted about 14:11, brain in monitor mode). `namecall.py --name mochi` now uses this spotter (`--spotter own`, default; `--spotter sherpa` keeps the public model).
- **Why T1 jitters: mostly speed** (fork `cmu/finetune/modal/FINETUNE-DELTA.md`, "Why T1 jitters"; `cmu/simcheck/speed_matched.py`). walk61 under-tracks: at vx 0.25 it covers 1.17 m in 10 s in the as-built sim, T1 2.06 m. At walk61's actual speed (T1 command 0.10-0.15) T1 makes 3-5 action jumps per 10 s at 5.7-8.5 deg peak tilt, against walk61's 1 at 6.3, and still steps with the neck down (-0.4 -> -0.46, -0.8 -> -0.74..-0.85). Robot jumps run about 15 times the sim for both policies, so the sim ranks jitter correctly. Literature pass (LCP gradient penalty lambda 0.002, CAPS, humanoid-gym second-difference term, Wolczyk 2024 fine-tune forgetting with a KL anchor, gSDE): our recipe has only a first-difference action-rate reward and no anchor to walk61. Next, zero cost: T1 on the robot at 0.10-0.15 m/s with the neck down (`t1_robot_test.py walk_at 0.10 -0.4`, new step); a smoothness-constrained, walk61-anchored fine-tune only if a faster T1 is needed, after Shawn's nod.
- **Own spotter live, 14:34 and 14:38 home runs; the extra answers were Shawn's repeated calls, not the duck hearing itself; half the recognised names were dropped by namecall** (`namecall-20261029/recordings/raw/live_nc_143806.raw`, log `namecall_ownkws_143806.jsonl`, both on the Mac). 14:34 listen-only without sound: about ten recognitions, which looked like no reaction, so listen-only now answers each name with a quack. 14:38 with the quack: in the first 176 s (quiet room) no hit; from Shawn's first call at 179.8 s to 208 s the spotter fired ten times, every 2.2-3.3 s, and the duck quacked five times. I first read this as the duck re-triggering on its own quack; the evidence refutes that. (1) All 48 QuackBank calls played through the head speaker and recorded by the head mics (`record_own_quacks.sh`, `own_quacks_144713.raw`; the first attempt recorded -140 dBFS after one quack because it opened playback without the keep-alive stream) give zero hits even at P 0.5. (2) The quacks appear in the capture within 0.07 s of their log time and last about 0.2 s; the hits fall between them. (3) The detector, replayed without the quacks, finds nine voiced onsets in that stretch, all from -146 to -166 deg (one +155) and none in the 176 s before. (4) Whisper without a prompt hears one repeated short word at 184, 188, 193, 201 and 205 s. So someone called about ten times from behind-left; Shawn remembers about two calls and one answer, which is still to be squared with him by ear (`namecall-20261029/recordings/live_nc_143806_176-212.wav`, sent to him). Dropped names: three because the call began inside the detector's post-quack deafness, the localiser found no voice bins and the name was skipped; two by the 2.5 s refractory, shared with any-voice mode, while one spoken Mochi keeps the spotter over threshold for up to ~1.2 s and Shawn calls every 2.2-3 s. Fixes in `namecall.py`: a recognised name without a bearing is answered (quack, no head move, extends attention; `no_direction` in the call record), and name mode has its own refractory `KW_REFRACTORY_S` 1.5 s (`--kw-refractory`). Replay of the 14:38 audio now gives eight answers to the ten hits. 66 namecall tests pass, three new. Installed; live listen-only rerun started 14:55 (`--save-raw`), runs until Shawn says stop.
- **14:55 live run: too many answers; the last five were not calls** (`namecall-20261029/recordings/raw/live_nc_145512.raw`, `recordings/namecall_ownkws_145512.jsonl`). 18 names answered in 185 s; Shawn: the last five (126.8, 129.1, 132.9, 142.2, 148.8 s in the raw) came without any call. Ruled out: (1) the silence namecall feeds the spotter while it quacks; the same audio scored continuously gives the same hits within 0.4 s. (2) The quack itself: each false hit comes before its quack, and the previous quack lies outside the 1 s window. (3) A loudness gate: the five false hits stand 10-22 dB over the voice-band floor, Shawn's recognised calls in the training session 8.5-36 dB (p10 11). Quiet stretches (0-20, 60-95, 150-185 s) give no hit; false hits come only while sound is around, and the spotter is sure of them (P 0.94-1.0). Working hypothesis: every positive is Shawn's voice through the duck's ears at home, and almost every negative is other speakers (Speech Commands, synthetic speech) or the lab room, so the model can separate the classes by speaker and room instead of by the word. Test and fix: record Shawn's ordinary speech at home through the duck (no "Mochi"), open-ended; score it with the current model (the hypothesis predicts many hits); add it and the five confirmed false windows as speech negatives, keep part of it held out, retrain. Shorter name refractory (1.5 s) let these hits chain every 2.3-2.8 s; it stays, because the hits themselves are the fault.
- **T1 slow walks on the robot disprove the speed explanation** (`microduck-sim/guide/firmware/mac/robot-runs-20261030-t1/`, "Follow-up", 11:00-11:01). 0.10 m/s with the neck at -0.4: stayed up, neck -0.38..-0.47, but 13.5 action jumps per s (walk61 1.4-2.7, T1 at 0.25 17-22), mean tilt 5.3 vs 3.4-4.0, and 15.5 deg at the stop. 0.15 m/s with the neck at -0.8: fell at 2.7 s; the trunk held about 11 deg of roll to the same side as the morning fall without correcting, then pitched forward with the neck dipping to -1.16 and actions climbing to 3.4-4.1. Slowing down cut the jitter by a third only; the sim's matched-speed rows (3-5 jumps per 10 s) were wrong about the robot. T1 is not deployable at any tested speed; walk61 back at 11:01. The remaining route is a training-side smoothness constraint (LCP gradient penalty, second-difference term, KL anchor to walk61), plan first, Shawn's nod before any run.
- **T1 forgot walk61's gait; t2 plan written** (`robot-runs-20261030-t1/sensitivity.py`, fork FINETUNE-DELTA.md "Run t2 plan"). On the robot's own logged states: T1's input Jacobian is only ~10 % above walk61's (so not sensor-noise gain, LCP left out), but on walk61's own 0.25 m/s walks with the head at default T1's actions differ from walk61's by 0.71 rad (73 % of walk61's action size); its jumps are hip roll / hip pitch / knee corrections, and on the robot it walks 2-5 deg to the falling side and up to 5 deg further forward than walk61, which the sim does not show. Plan t2 = T1 + a behaviour-cloning anchor to walk61 on default-head, 0 or 0.25-0.30 m/s states (Wolczyk 2024), 20 % default-head envs, betas 0.5 and 2.0 paired on one free Kaggle job; gates: offline distance <= 0.25, T1's sim rows, suite plus drop8_imu35 (needs Shawn's word), then the robot. Waiting for Shawn's nod.

## 2026-10-30 afternoon: t2 implemented, smoke passed, paired run training

Shawn nodded to the t2 plan ("点头，跑"). t2 = T1 + a behaviour-cloning anchor to walk61 on default-head states at vx 0
or 0.25-0.30, 20 % default-head envs, betas 0.5 (t2a) and 2.0 (t2b). One extra finding while building it: rsl_rl kept
updating the actor's input normalizer during T1 (exported mean off by up to 0.025, divisor by 0.042); t2 freezes it at
walk61's, verified exact in the smoke export. G1 is now a script, `guide/firmware/mac/robot-runs-20261030-t1/action_distance.py`
(T1 0.711, walk61 0.000, gate 0.25). Kaggle smoke: both jobs ran to export. The paired 1000-iteration job
`microduck-t2a` is training on the free T4s. Details in fork `cmu/finetune/modal/FINETUNE-DELTA.md`, "Run t2".
- **False answers to walking and standing up; spotter retraining with all our recordings as negatives** (Shawn: the five false answers at 14:55 came while he said nothing, only stood up and walked). A voicing gate does not separate them (Shawn's recognised training calls measure 0 voiced ms as often as the walking windows), nor does loudness. Data now (`namecall-20261029/mochi_labels.json`): negatives = every call-free stretch of every robot recording (10/29 lab conversation, the RoboClub no-speech recording with head touches, the snap and cover tests, the RoboClub 2 m session outside its calls with the corridor loudspeaker, the 48 own quacks, the table test away from its calls, the 14:38 run outside 176-212 s, the 14:55 run's quiet parts and 125-140 s of walking, Shawn's 15:01 ordinary-speech recording 0-100 s) plus ESC-50 (2000 environmental clips, 50 classes, `~/data/esc50`) and Speech Commands; held-out real negatives never trained on: 14:55 run 140-185 s and 15:01 speech 100-144 s (89 s). Findings by run (held-out real false hits at P 0.9 / held-out call recall / false wakes per hour on 28 min synthetic speech): v1 original 5 / 17 of 20 / 0; whole-window positives with the new negatives 8 / 17 of 20 / 0, and the scan showed the cause: it fired every second through the whole call session, gaps included, so it had learned that session's background (all positives came from it); words cut tight and laid onto other recordings' backgrounds 3 / 15 of 20 / 6; plus the 10/29 RoboClub calls (by-ear times 39.3-95.1 s, word = loudest 0.3 s of voice band 0.2-1.6 s after each) half on their own background 3 / 18 of 22 / 36, all on other backgrounds 3 / 17 of 22 / 140. The RoboClub cuts stand only 3-15 dB over the lab noise and carry the corridor loudspeaker's speech, which teaches "babble = Mochi"; they become a noisy-room recall test, and noise robustness comes from home calls laid onto the lab's noise. Training moved to the Mac mini (`~/mochi-train`, venv duck-see + scipy): the MacBook was swapping (7.1 GB swap, load 44-89) and a 7 min run took over 45 min. Two variants run there in parallel: A = home calls on all backgrounds, B = A plus the 262 synthetic-voice Mochi clips of `mochi_set.py` (openWakeWord-style: many voices so the shared cue is the word).

## 2026-10-30 night: the sim now ranks jitter like the robot, with one known false alarm

Study `guide/firmware/mac/jitter-20261018/` ("2026-10-30 targets", 58 settings, six robot rows from today). One setting
for all policies, `--gyro-noise-dq 0.25 --bam-friction-scale 1.4` (gyro vibration proportional to leg speed plus BAM
friction x1.4), reproduces five of six rows within 2x: walk61 2.1 -> 2.7 jumps/s; T1 default head 21.8 -> 17.2 and
falls in one seed; T1 neck -0.4 17.1 -> 15.7; t2b neck -0.4 14.0 -> 11.4; t2b neck -0.8 13.6 -> 13.3. The miss is t2b
with the default head: robot 1.7, sim 8.1 (the anchor's protection has no sim counterpart), so the sim orders
T1 > t2b > walk61 as the robot does but over-reports t2b's calm row. Mechanism: the same loop on both sides (both legs'
hip pitch and knee in phase at 1.7-2.2 Hz, a trunk-pitch bounce), the sim at half the robot's amplitude; the robot's
extra trunk gyro is above 5 Hz and grows with the shaking, so the gap is trunk shake per unit of leg motion (play or
foot-strike), not the joints. Refuted as the single cause: leg deadband 0.04+ and friction x1.5 (walk61 stops stepping),
any extra IMU delay (stand61 falls at 2.2 s; the robot has none), head mass, read drops, ankle play, sole and floor
friction, robotd filters, constant gyro noise. Use for t3: a candidate must keep the neck rows within 2x of walk61's
default-head jumps in this setting; the t2b default-head row is the known false alarm. Discriminating the >5 Hz power
(trunk motion against IMU mount vibration) needs a 200 Hz gyro capture during one walk61 walk, when the robot is
next used anyway.

## 2026-10-30 evening: t2b on the robot. Walks like walk61, shakes like T1 once the neck is commanded

With the default head t2b walked 0.25 m/s like walk61 (peak tilt 8.7 deg, 1.7 action jumps per s; T1 21.8 and fell).
With the neck at -0.4 it shook like T1: 16.4 deg and 14 jumps per s (T1 17.6 and 17.1); with -0.8, 10.8 deg and 13.6
per s, and standing it held the neck at -0.64 (T1 -0.82). No fall; the walk_neck step crossed the 9 deg stop rule.
The anchor only covered default-head states, and that is exactly where it worked. The sim shows 0-2 jumps per 10 s for
t2b with the same neck commands (robot about 140), so the sim misses head-down shaking about tenfold for both
fine-tunes, and gates built on it cannot judge the next round. Input sensitivity is not higher than walk61's on these
states. Detail: `guide/firmware/mac/robot-runs-20261030-t1/t2b/README.md`. Brain back on walk61 at 16:02:05.

## 2026-10-30 evening: t2 gates. The anchor kept walk61's gait but the neck reaches less far; not on the robot

t2b (beta 2.0) passes G1: its actions on walk61's own robot walks are 0.22 rad from walk61's (T1 0.71). In the sim it
jumps like walk61 (2-4 per 10 s on the real cases, T1 5-27) and falls in 1 of 6 drop8_imu35 seeds (walk61 0, T1 3).
It fails G2 and G3 by small margins: neck -0.8 reaches -0.686 walking (tolerance 0.10, off 0.114); drop8 seed 0 falls;
vx 0.25 has 4 jumps per 10 s against the allowed 3. G2's 0.6 m walking-path threshold was set from T1's speed, and
walk61's own plain walk covers 0.45 m in that sim, so that row says t2b walks slower than T1, not that it stops.
t2a (beta 0.5) fails G1 (0.30). Candidate saved as runtime-overlay/models-t2b-best (README has the numbers);
`t1_robot_test.py restart t2b` loads it. Not robot-tested: the plan needs G2 and G3 passed or Shawn's waiver.
Shawn waived G2 and G3 the same evening ("豁免，上机测 t2b"): only the robot shows whether the anchor removes T1's
jitter. models-t2b-best is on the A7Z overlay (hashes match); `t1_robot_test.py` no longer stops when the control
file is missing after an A7Z reboot.

## 2026-10-30 afternoon: Mochi spotter v2, a three-seed ensemble

Mac mini runs of the all-negatives recipe (`namecall-20261029/train_mochi.py`, `mochi_labels.json`), scored on the same
held-out set (28 calls: 14 home, 6 table, 8 RoboClub noisy-room; 89 s of held-out real non-calls from the 14:55 walking
run and Shawn's 15:01 ordinary speech; 28 min synthetic speech). Single seeds of recipe A (home calls cut tight and laid
onto every recording's background, ESC-50 and Speech Commands negatives) differed by several false hits and calls on the
same audio. Adding the 262 synthetic-voice Mochi clips (B) gave over 2000 false wakes per hour on synthetic speech: the
model learned "synthetic voice = Mochi". A final fit with all calls trained was worse than A. Training on the RoboClub
cuts taught the corridor loudspeaker's babble as Mochi, so they stay a held-out noisy-room test. Deployed: the mean of
three A seeds (A, A1, A2) packed in one file (`models/mochi_own.npz`, `ownkws.pack_ensemble`, `OwnModel` averages the
members), threshold 0.7: calls 20 of 28 (home 12/14, table 3/6, RoboClub 5/8), synthetic speech 0 per hour, held-out
real false hits 1 (142.1 s, walking). The v1 model at its 0.9 threshold on the same set: 19 of 28, 5 false hits. At 0.9
the ensemble has no false hit but finds 15 of 28. Report `results/mochi_own.json`, from `eval_mochi.py`. Caveat: the
held-out real negatives come from sessions whose other parts were trained on. Not yet on the duck: the A7Z was off
Tailscale from about 12:00; install and the live listen-only run follow when it is back.

## 2026-10-30 night: Mochi spotter v3-v5, the data catalog, life log, and the switch to the standard recipe

What the day's runs showed (all on the 28-call held-out set of the v2 entry plus 124 s of held-out real room sounds):
v3 matched the shortcut cues instead of dropping data. Synthetic-voice Mochi positives with same-voice synthetic
speech as negatives (`tts_speech.py`, 38 clips in the same 28 voices) still woke on 235 of 561 held-out synthetic
sentences, so they are out for good; the synthetic speech stays as negatives. RoboClub calls trained in folds
(`--robo-fold 0/1`, odd or even calls held out) found 6-7 of the 8 noisy-room calls but added real false hits.
v4 used every recording: calls_201411's eight lab calls (used as negatives for a day, found by rereading this log),
each microphone as its own sample (`to_mono16.py --mics`, NAME@ch0/1/2), gap negatives between calls, and the
`mine_life.py` labels of the two namecall runs. Best fold-0 ensemble (M0+M0s1) at 0.9: 23 of 28 calls, synthetic
speech 0 per hour, 1 real false hit, noisy room 7 of 8; per-mic samples lifted calls_201411 from 1 of 4 to 3-4 of 4.
The remaining failure is false hits on Shawn's ordinary speech (live_150103 100-144 s): one speaker's positives teach
"Shawn's voice", and every seed draws a different line through it (F4 seeds: 7, 13, 16 of 20 calls).
v5 fixed the seed spread at its cause: constant learning rate, no batch norm, last-epoch weights. Batch norm (folded
into the conv weights at export), one-cycle learning rate and an exponential moving average of the weights; the export
test `test_exported_model_matches_torch_with_batch_norm_folded` holds the numpy model to the torch one.
Data: `AUDIO-DATA.md` lists every recording, download and generated set with its labels (the catalog did not exist;
two sources were misused for lack of it). `life_log.py` records 3-mic 16 kHz segments round every voice, name and answer
from boot (`namecall.py --life-log`, 8 GB cap, index `life_index.jsonl`), and `mine_life.py` labels them without anyone
marking: sure calls (spotter P >= 0.9 and template z >= 3), repeated calls (a similar event 1-8 s from a sure call),
quiet negatives, doubtful hits; on Shawn's ordinary speech it finds 0 calls, on the 14:38 and 14:55 runs 8 and 10.
The lesson that cost the day: keyword spotting is a named task with a standard recipe, and the 18-763 lecture 21
notebook Shawn had shown holds it (Speech Commands, thousands of speakers, no own recording: the word is the only
shared cue). The hand-rolled single-speaker pipeline was patched round after round instead. Rule updated
(`claude-config/rules/common/literature-before-experiments.md`): a named task starts from the mature routes, a shown
reference is a recipe to diff, a hand-rolled pipeline that fails twice stops. Now running on the Mac mini, same held-out
set: (1) the class recipe with real people saying "mochi" from YouTube (`~/data/mochi_web`: 1.9k word cuts, 1.7k cuts
with context, 5k same-sentence and same-video negatives, videos hashing to 0 mod 10 held out; `train_mochi.py --web`),
runs W0s0/W0s1 (fold 0) and W4s0 (all data); (2) openWakeWord's pipeline (frozen pretrained speech embedding, small
head, thousands of TTS voices) in `~/mochi-train/oww`. The better one on the held-out set goes on the duck.

## 2026-10-30 17:00: the class recipe on our CNN learns the word but not precisely enough; negatives are the gap

Web data final: 1686 verified "mochi" cuts from 80 videos and 65 channels (`AUDIO-DATA.md`). Trained with the class
recipe on our 1 s log-mel CNN (W0s0/W0s1 fold 0, W4s0 all data, with the 1925-cut pre-verification set): on the
held-out web videos the word is learned, 159 of 170 clips at 0.9 with 17-22 of 489 negative windows firing
(3.5-4.5 %); on the duck's held-out calls 20-21 of 32 at 0.9 (old recipe V0s0 21 of 32), the RoboClub lab calls
rise to 3-4 of 4; real held-out room sounds 0 false hits at 0.9. But synthetic speech wakes 91-195 times per hour
(old recipe 0): 113 of 561 sentences fire, 83 of them with no near-miss word ("the weather today is mild",
"the battery needs another hour"), so it is not a sound-alike problem; a window false rate of 3.5 % on open speech is
hundreds of wakes per hour at 10 windows a second. The old recipe's 0 per hour came from its positives being one
voice (synthetic speech is trivially "not Shawn"), not from precision. The gap is negatives: about 2 h of open
speech (Speech Commands words, 5k web windows, 15 min TTS, the duck recordings) against 1686 positives; the standard
wake-word recipe trains against thousands of hours of speech (openWakeWord: ACAV100M features) or a frozen
pretrained embedding. Next, both: LibriSpeech dev-clean and test-clean (10.5 h, 80 speakers) as `--neg-speech` with
held-out speakers giving false wakes per hour on real speech, and the openWakeWord run (in progress on the Mac mini).
Also tried: ensembles of old-recipe and web-recipe members (E1, E2), results below.
E1 (V0s0 + W0s0 + W0s1) and E2 (V0s0 + V0s1 + W0s0 + W0s1), probabilities averaged, fold-0 held-out set at 0.9:
E1 21 of 32, E2 22 of 32 (home 10/14, table 2/6, RoboClub 3/4 and 4/4, 14:38 run 3/4), synthetic speech 0 per hour,
real room sounds 0 false hits. The old-recipe members veto other voices, so the ensemble finds only 0-3 of 170
held-out web clips: it is a Shawn's-voice model with the web members' precision, not a general "mochi" spotter. E2
replaces the v2 ensemble on the duck as the interim model (best on every held-out number so far); the general model
waits on LibriSpeech negatives and openWakeWord.

## 2026-10-30 16:30: in-place turns stall on the robot, not in sim; points to the charger lead

Shawn's long in-place turns (vx 0, vtheta +-0.5, run walk611030-160205) each turned for 1-4 s (15-35 deg/s), then
stepped in place with net yaw near 0 (right turn 16:11:53-16:12:33: about -50 deg in 40 s). The heading hold then
pins walk61's turn input at -1.55 (outside the trained +-1), but as a result of the stall. In the as-built sim the same
turns run 26-29 deg/s for 25 s with head down, floor mu 0.5, servo friction x1.5 or IMU pitch 4 deg; only an external
yaw torque stalls them (0.010 N m halves a right turn, 0.020 N m reverses it), so the policy can push only about
0.01-0.015 N m in place. The duck is tethered to its USB-C charger lead; a dragged or wound lead gives that torque in
either direction. Check: the same turn with the lead held up. Record and scripts:
`microduck-sim/guide/firmware/mac/turn-inplace-20261030/`.
Live, home, listen-only, v2 ensemble at 0.7, 15:56-16:21 EDT: 6 wakes in 25 min with nobody calling (the life log's
auto-labelling finds no call and no doubtful event in any of the 33 segments; the hits sit at the room's own level).
E2 at 0.9 installed 16:21 (A7Z copy sha256 36fb5f51...), listener restarted. The A7Z clock ran on UTC until 16:08 EDT
(listener times before that are UTC); now America/New_York.

## 2026-10-30 16:45: the in-place stall matches a twisted lead, not a dragged one

Shawn held the lead up for the head-up turns and the duck still stalled. In the as-built sim nothing on the robot side
stalls a 25 s in-place turn (floor grip, soft soles, foot play, sole twisting friction, head at the top, servo
friction); shaking and servo following were the same in turning and stalled seconds on the robot. A restoring torque
of 0.010 N m per rad of turn (`brain_sim_check.py --yaw-spring`) reproduces it exactly: 70-90 deg in 4 s, then rocking
with the command pinned at 1.5. A held lead still twists with the duck. Check: turn the held end with the duck.

## 2026-10-30 17:00: why walk61 turns with only about 0.01 N m

The hip-yaw servos draw 15-46 mA while turning or stalled (11-13 mA standing), with 5-24 deg position errors: about
0.002-0.012 N m per hip of the XL330's 0.52 N m. walk61 was trained with x/y velocity pushes only, never a yaw push or
torque, under a pose reward that pulls the hip yaws home, so its turning gait needs almost no torque and it does not
push harder when blocked. A higher servo gain falls in sim (kp 400, 800), as walk61 was trained at kp 200. Remedy
that changes the authority: retrain with yaw torque disturbances (needs Shawn's nod); meanwhile keep the lead from
twisting.

## 2026-10-30 17:00-17:20: openWakeWord fails on the duck; LibriSpeech negatives; live test findings

openWakeWord (upstream main 368c037, frozen Google speech embedding + small head, `~/mochi-train/oww` on the Mac mini,
venv `~/.venvs/oww`): 6000 piper TTS positives spelled "mo chee" (espeak reads "mochi" as MAH-chai), 3510 web clips,
ACAV100M features (5.6 M rows), our duck negatives, MIT RIRs. Its own validation: recall 0.54, 0 false/h. On our
held-out set: 1 of 22 duck calls at 0.5-0.8, 0 at 0.9; web held-out 20 of 170 at 0.5 with 0 false. Fits the A7Z
(2.6 MB, 0.9 ms per 80 ms frame on the M4) but not usable: the duck's calls reach it through the head cavity
(NAMECALL.md 10.4) and nothing in its training sounds like that.
LibriSpeech dev+test clean (10.5 h, 80 speakers) as negatives with the verified web set (L0s0/L0s1 fold 0, L4s0 all):
real speech by held-out speakers 15-26 false wakes in 30 min at 0.9 (22-32/h), synthetic speech 42-57/h, duck calls
18-22 of 32, web held-out 144-150 of 160. More negatives cut the false rate by about a third, not by the 100x needed.
Live full behaviour 16:51-16:54 (E2 at 0.9, Shawn seated at the duck's 11 o'clock, about 30 deg left): five answers,
of which Shawn counts two false (16:54:27 and 16:54:32 by their audio: no "Mochi" shape). The direction was wrong on
every call (160, 87, 158, 126, -18 deg): replaying the five through `CallLocaliser` in other bands confirms 10.4,
the low band reads "front" for any caller. The face was never found: the camera, looking down, showed only his shoes
(`scratchpad/snap_now.jpg`). Body turn (`--turn`) stopped before it turned away from him. Next: person detection to
follow the body up to the face (agent working), the camera searches in front before the sound bearing is trusted,
and sealing each microphone to its own hole (foam gasket) plus the mouth-to-cavity path.

## 2026-10-30 18:00: the charger lead as a training disturbance

`guide/firmware/mac/tether.py` models the 3 m braided lead as forces on the trunk, not as a cable: hanging weight,
floor drag that grows with the distance walked (short walks drag only the near part), random snags, a taut pull
capped by the power bank sliding, and a twist torque that slips past 0.005-0.03 N m (Shawn: keep it moderate).
Parameters are drawn per episode. walk61 with the lead in the eval sim: walks as far as without (1.32-1.48 m in 12 s),
in-place turns 12-23 deg/s against 28, no falls. The fine-tune delta `tether` puts the same model in 80 % of the
training envs; the reward audit passes (standing earns 0.788 of walking, gate 0.8). Kaggle smoke tether-smoke (paired, 6 iterations) COMPLETE 22:40 UTC; run tether-a/tether-b (seeds 1, 2, 1000 iterations) pushed 18:40 EDT on Shawn's go. Result 20:30: with the lead in-place turns 7-25 -> 23-29 deg/s and 12 s walks 1.1-1.25 -> 2.3-3.2 m, no falls, but action jumps 8-82 against walk61's 0-5 in the real suite cases (ft3 4-13), so both seeds are rejected for the robot (fork ae149b40, FINETUNE-DELTA.md 'Result'). The training sim saw no jitter; the lead goes on top of t3 once t3 passes its jitter gates. t3+tether prepared on fork branch cmu/t3-tether (audit t3a_tether_asbuilt PASS 0.803, walk61 falls 0.465/env-min; smoke rc 0); not started because t3 failed G2 on every neck row, while its default-head rows were smoother than walk61 (0.47-1.5 vs 3.38 jumps/s). On Shawn's "用 t3b 训" t3b+tether ran 21:17-22:46 (seeds 1, 2, 1000 iterations). Result 23:06 (fork cmu/t3-tether, FINETUNE-DELTA.md 'Result (2026-10-30 22:51-23:06)'): lead turns 17/16 -> 26/26.5 deg/s (worst seed 12/7 -> 20/19), walks with the lead 1.20 -> 1.37 m, calibrated-sim jitter 3.38 -> 0.87 jumps/s, no falls in any lead or real case. Best candidate t3bt_a (seed 1 final) passes every five-seed real case except vx0.2 (stands still like walk61 but tilts 4.6 vs 2.4 deg); it fell in 1 of 5 drop8_imu35 stress seeds (walk61 0). Both best checkpoints stand still with the 4 deg IMU pitch offset, rejected. The stored suite reference from 10/19 no longer matches the sim (walk61 fails against it), so this run judged against its own walk61 rows. Robot G4 waits for Shawn's call on the vx0.2 miss.
E2 on held-out real speech (LibriSpeech speakers it never heard): 0 false wakes in 30 min at 0.7 and 0.9; its live
false answers come from Shawn's own talk. E3 = E2 with its two Shawn's-voice members retrained on everything the life
log heard (his ordinary talk as negatives, the two answers he confirmed false, his three confirmed calls, 20k
LibriSpeech windows): at 0.9 duck calls 22 of 34 (the two new live calls 2 of 2), synthetic speech, real speech and
real room sounds all 0. Packed as `models/mochi_own.npz` (sha256 4bd159aa...); not on the duck yet (A7Z offline on
Tailscale since about 17:25).

## 2026-10-30 18:10 Body-to-face search installed (commit 02ae5331)

- **Installed** on the A7Z with E3 (`mochi_own.npz` sha256 4bd159aa...); file hashes match the Mac; YOLOX-Tiny loads in the duck-policy venv. `install_namecall.sh` had no entry for `personfind.py` or the model, so the finder would have fallen back to faces only; fixed in the same commit.
- **CPU on the A7Z** (saved 16:54 shoes frame, 20 s each, brain not running, A7Z just rebooted): face only 0.91 cores at 4.0 Hz, 121 ms per frame; face + person 1.48 cores, face rate 3.2 Hz, person 250 ms per frame at 1.6 Hz, person found at box [2, 1, 162, 184]. The person detector runs only on frames with no face, so with a face in view the cost is unchanged.
- **Not yet measured:** the same with the brain running (the 16:52 live log showed the face detector at 425-440 ms per frame then, not 120 ms), and the live behaviour with Shawn. Waiting for him at the duck.

## 2026-10-30 18:53-19:01 Live test with person search (RoboClub, people talking nearby)

- **Calls:** one answer in about 8 min (18:53:41, heard at -28 deg, face found 3.2 s later, bearing_seen -8.5 deg). Shawn says he called several times before it answered. E3 spotter scores in life segment 185304_961 before the answer: 0.83 at 28.4 s, 0.78 at 30.7 s, 0.42 at 33.4 s, then 0.92 at 35.5 s (answered); the 2-3 s spacing is Shawn's repeat rhythm. In the next 4+ min of other people talking the maximum was 0.70. Two machine checks could not confirm which windows are calls: `mine_life.py` found no call (template likeness 2.0 < 3.0, even the answered one) and would have labelled the 4-7.5 s peak region a negative, so its labels for these segments are not used; SenseVoice (the web-set verifier) reads no "mochi" in duck-ear audio, the answered call included.
- **Head swing:** after the face lock the commanded head yaw swung between -0.5 and +0.15 rad with a 2.2 s period for 40 s. Measured: head joint 247 ms behind the command (corr 0.98), face frames 160-200 ms to analyse. The tracker added 0.6 x the frame offset to the commanded gaze, re-correcting motion the head had not made. Fixed in 6cbb10ad (target from the measured head pose at the frame's capture time; simulated with these delays: old 2.4 rad swing, new under 0.03 rad). Installed, not yet live-tested.
- **CPU:** namecall used 3.4-4.0 cores live (bench on a saved frame: 1.5); brain ticks stayed at 20.4 ms median, 46 ms max. Cause not yet found.

## 2026-10-30 19:00-19:40 Fine-tune t3: the sim gap goes into training, reward audit passes

- **t3 = t2b + three changes** (fork commits 1bb0560c..675add5a, plan in `cmu/finetune/modal/FINETUNE-DELTA.md` "Run t3 plan"): the jitter sim-ID's gap in the training DR (BAM friction 1.0-1.4; gyro noise proportional to leg speed, k 0.15-0.35, on the actor's gyro only), a second-difference action penalty `action_acc_l2`, and the anchor extended to head-command states with a counterfactual target (walk61's leg actions on the same state with the head command zeroed; t3a beta_legs 0 = anchor on default-head states only, t3b beta_legs 1). 18 CPU tests pass.
- **Reward audit** (two Kaggle runs, 17 min): friction 1.0-1.5 made walk61 fall 0.527 per env-minute (limit 0.5; t2b env 0.193), so the top is the study's calibrated 1.4. Attribution run: friction alone 0.328, vibration alone 0.344, both at 1.4 0.432, PASS. walk61's own action_rate_l2 mass doubles under the vibration noise (-0.086 -> -0.199/s): the sim now shows the robot's mechanism, the actor reacting to high-frequency gyro content. action_acc weight -0.58 (mass-matched to action_rate_l2 on walk61). Standing earns 0.804 of walking (max 0.83).
- **Next in this turn:** paired smoke smoke-t3a/smoke-t3b, then the paired 1000-iteration run, then G1 (`action_distance.py`), G2 (`cmu/finetune/g2_jitter.py`, calibrated sim), G3 (`sim_suite.py` plugged + drop8_imu35 seeds 0-5). Robot only if all pass and the two pre-robot lines are written.

## 2026-10-30 19:50-20:50 Name spotter round 2, the eight-direction recording, what the three microphones give

- **E3 is a voice detector, not a word model.** It scores 0.95 on a call slice played backwards (0.98 forwards) and 0.8-0.9 on each microphone alone. That is the mechanism behind Shawn's complaint ("I call and it does not answer, I talk and it answers"): 4 false answers 19:57-20:08 (all labelled negative in `namecall-20261029/life_labels_1030_live.json`; their bearing_seen rows are not call labels) and 12 more 20:21-20:31.
- **openWakeWord round 2** (`namecall-20261029/oww/prep_v2.py`, `run_v2.sh` on the Mac mini: 63 duck-ear calls x 30 copies plus single-ear copies, 1000 life negatives, 50000 steps; model `namecall-20261029/models/oww/mochi_v2.onnx`, scores `results/mochi_v2*.json`): the "8/14 on held-out home calls" figure is an artefact of the test set, five of the six misses are E3-made spans of 0.2-0.4 s (fragments); gain +0..+18 dB changes nothing. On the only certain set, Shawn's eight calls at 2 m from eight directions (`eightdir_20261030.json`), v2 catches 8/8 with each ear scored as its own stream (ear mix 7/8: the +135 deg call was 0.01 on the mix, 0.87 on the right ear), and fires 0 times in the 8.7 min of Shawn moving and talking before them, where E3's live rule would have fired 3 times plus 4 repeat pairs; 0 false on 11.7 min held-out life talk, 28 min synthetic speech, 489 web negatives. `ownkws.OwwSpotter` now streams each ear (`per_ear=True`, test in `test_ownkws.py`); the production feed path over the whole recording answers 8/8 and nothing else. Not yet live: the A7Z went offline at 20:31.
- **The 15 "camera-confirmed" calls of 18:53-19:47 are not a test set**: they were E3 triggers confirmed only by a face in view afterwards; v2 and the official openwakeword runtime score 0.00 on all 15.
- **Direction, answering "一个方程能搞定吧"**: the free-field equation tau = d sin(theta)/c is right (snap at the ear: 10.2-10.9 samples against 10.8). At 2 m it fails because the sound reaches the ears by two paths, through the 1.6 mm ear holes and through the beak/mouth opening into the cap cavity, 0.2-0.5 ms apart, the same order as the cue itself, so the paths add and cannot be separated in time; whole-word 1.5-6 kHz lags on the eight calls are within one 48 kHz sample in every direction (about 8 dB over the room in that band). First-wavefront windows (precedence) need a sharp onset and "Mo" has none on 7 of 8 calls. What does carry direction: the 2.5-4 kHz left-right level difference gives the side on 6 of 6 side calls (+3.3, +3.4, +1.2 dB at +45/+90/+135; -0.9, -2.1, -0.4 at -45/-90/-135), with a right-ear offset to calibrate out; the 300-1200 Hz ILD had r 0.74 with the bearing on the 15 earlier slices. The route is a measured table of this head (ILD per band, back-mic cavity delay) inverted at run time, as shelled robot heads do, instead of the free-field equation; one call per direction so far, a second round with three calls per direction validates it. `bearing_cues.py` holds the cue extraction.
- Register: `namecall-20261029/REQUIREMENTS.json` R1-R3 updated with this evidence (0/10 met; R1 gap = E3 false answers, R2 gap = live run with v2 pending).

## 2026-10-30 21:05-21:50 Fine-tune t3 result: calm under head commands in the calibrated sim, neck only 60 % deep

- **Run** (paired Kaggle, 1000 iterations each, 80 min, no guard stop): t3a (anchor on default-head states only) and t3b (anchor also on head-command states, leg outputs, counterfactual target). Candidate `cmu/whole/runtime-overlay/models-t3b-best` (iteration 900).
- **G1** action distance from walk61 on 649 robot states: t3a 0.19-0.21, t3b 0.24 (gate 0.25), all pass.
- **G2, the sim that predicted t2b's failure** (`cmu/finetune/g2_jitter.py`, gyro noise dq 0.25 + friction 1.4, three seeds, 10 s): action jumps per s with a neck command, t3b 2.3 (-0.4) and 5.1 (-0.8), no falls in 9 rows; same sim, same rows: t2b 11.0 / 11.5 with 2 falls of 6 (robot 14), T1 17-21, every seed fell (robot 17-22); walk61 default head 3.4 (robot 2.1). t3a fell in 3 of 6 head rows, which its design predicted. Cost: t3b lowers the neck to -0.25 for the -0.4 command and -0.44 for -0.8, where t2b reaches -0.40..-0.44 and -0.72..-0.76 in the same sim (so it is the policy's choice, not the sim); peak tilt at -0.8 13-15 deg (gate 12). The plan's "0.6 m in 6 s" path line came from the uncalibrated sim and is unusable here (walk61 itself does 0.80 m in 10 s); against walk61, t3b walks 0.75-0.80 m under a neck command.
- **G3**: drop8_imu35 seeds 0-5, t3b best 0 of 6 falls (walk61 0, t2b 1, T1 3). Plugged suite: no falls, 0-2 action jumps on the real cases (walk61 2-4), but 10-30 % shorter walks than walk61 on every real case, so the suite's distance rule fails.
- **Standing**: under the plan as written t3b fails G2 (neck depth, tilt at -0.8) and G3 (distance), so no robot test tonight; the two pre-robot lines are written in FINETUNE-DELTA.md for whenever Shawn weighs a waiver. Prediction for the robot: calm walks with a neck command, a shallower bow than t2b (-0.25 / -0.45), slower than walk61. If depth matters first, t4 = t3b with head tracking priced on the escapable part (L1 on a 1 s EMA) or head_pose_bias raised from 5; audit, then a paired run; nothing queued without a nod. Kaggle: 2026-10-31 week started at 00:00 UTC, 30 h.

## 2026-10-30 21:00-21:30 First live run of the word spotter v2: 9 of 17 home calls heard, one side wrong by 180 deg

- **Run** (`namecall_20261030-210005.jsonl`, v2 per ear 0.5/0.3, ILD side rule, Shawn calling from all sides at home): 8 answers in 21:01-21:07, 0 false answers; Shawn: 响应不太高, RoboClub 大概 1/5 能唤醒, 从背后叫的时候能转身, 有一次我在右边叫的 它去往左边转身.
- **Every call counted** (`namecall-20261029/results/events_2100_20261030.json`): the life recording holds 20 voice events; Whisper small transcribes 17 as the name and 3 as talk. v2 scored 9 calls >= 0.5 (one landed inside the previous answer), the other 8 calls 0.00-0.20; the 3 talk events 0.00-0.02. The misses are the quieter calls (6-9 dB over the room against 11-13 dB for the heard ones) and two fast doubles; a threshold does not reach them, the model has to learn them. Whisper on 2.5 s slices is the clip check Shawn asked for (切出来的短片段的正确性): the name is transcribed as Mochi/モチ/마치 on every clear call and never on the three talk slices.
- **Side**: the camera then found Shawn on the side the duck chose on 6 of 6 calls (the ILD overrode the SRP once, 21:07:21, and was right). 21:03:09: SRP margin 0.05, LR -2.6 dB and the right ear's v2 score all said right; the duck turned right 77 deg, scanned, found nobody and gave up, while the calls before and after found him on the left: a single reflection can turn every cue round at 2 m indoors. Two live LR readings were floor artefacts (-107 dB from a 1e-14 floor; 0.0/0.0 on a 7 dB call).
- **Fixes** (installed 21:21, not yet live-tested; namecall paused for the t3b robot test): `level_cues` uses a 10 dB spectral floor and reports the band SNR, the side rule needs SNR >= 3 dB; when the back turn's search finds nobody the body turns on the same way (time cap, about 120 deg) and any body turn stops at the first face or person in view (`test_a_back_turn_that_finds_nobody_turns_on_until_the_camera_sees_someone`; 62 namecall tests pass).
- **Next**: round 3 of the spotter with a clip gate (word 0.45-1.0 s and a Whisper transcript of the name, or a protocol recording with a known count), tonight's 25 certified calls as positives, RoboClub noise mixed in; Mac mini run after Shawn's go. Register updated: R1 holds on this run, R2 gap (9/17), R3 gap (one 180 deg miss, recovery turn built).

## 2026-10-30 21:30-22:15 Name spotter round 3: clip gate, tonight's calls, RoboClub noise; three more held-out calls of 32

- **Shawn's go** 21:31 (训第三轮). **Clip gate** (`namecall-20261029/oww/clip_gate.py`, results in `results/clip_gate_20261030.json`): every positive candidate gets a 2.5 s window; Whisper small must read the name (auto language, then English with the prompt) unless the recording is a protocol one, and the clip is the 0.3-1.0 s two-band envelope burst nearest the candidate (Whisper's own word timestamps were useless: one "word" over the whole window), with the labelled word length as the fallback for the 2 m RoboClub protocol calls and tonight's peak-timed events. 109 of 124 candidates pass (91 read by Whisper); the 15 failures are live_141734 fragments and merged pairs.
- **Data** (`oww/prep_v3.py`, `data/counts_v3.json`): 77 training calls (live_141734 before 190 s, the 14:38/14:55 home calls, two 16:52 life calls, calls_221619, tonight's 17) -> 3850 clips with per-ear copies; negatives add calls_200910 0-520 s (Shawn talking at home, no call); 152 RoboClub 2 s room chunks join the background pool at duplication rate 3. Held out, never trained on: calls_200910 (8), calls_201411 (8), live_073135 (5), live_141734 from 190 s (11).
- **Result** (`results/mochi_v3_extra.json`, `mochi_v2_on_v3_heldout.json`, `compare_v3_20261030.json`): single-stream held-out 21/32 (v2 18/32) at 0.5, 0 false on 11.7 min held-out talk; per-ear on tonight's 17 calls 11/17 (v2 9/17, in-sample for v3), eight-direction peaks 0.96-0.98 on all eight, but a talk event ("What?") scores 0.67 and the day's 84 min of life audio one false peak at 0.5 (v2 0). The four quietest calls of tonight stay at 0.00-0.08 although they were in the training set: the fixed speech-embedding front end does not separate them from the room at 6-9 dB; more data of the same kind will not reach them.
- **Deployed** 22:12 as namecall's default (`--oww-model mochi_v3.onnx --oww-threshold 0.7`, repeat 0.3), not yet live-tested; namecall stays paused until the t3b session hands the duck back. Mac mini run 21:47-22:05 (aug 3 min, train 10 min).
- **Next**: a soft "hm?" at 0.3-0.7 that invites the repeat (the repeat rule confirms at 0.3); automatic gated harvesting of life-log calls (pet learns from life); a duck-audio front end if the ceiling holds.

## 2026-10-31 16:34 t3bt_a robot walk 1: fell under a starved brain

- **Run**: on Shawn's "上机器人试" the A7Z brain was restarted with `models-t3bt-a` (hash checked), closed-loop stand 1.1 deg. Shawn ran `t1_robot_test.py walk` (0.25 m/s, default head, battery backpack, no charger lead): forward fall 1.4 s in (12.5 deg at 1.1 s, 30 deg at 1.4 s, guard to stand).
- **Brain condition at the fall** (slice `/tmp/t1-robot/163444.jsonl`, read on the Mac): 38.8 Hz instead of 50, 17 % stale servo reads, IMU age median 35 ms / p90 66 ms; namecall (222 % CPU) + two a7z_cam.py + blackbox.py, load 7.6, 52 % iowait. The stand 3 min earlier ran 47.4 Hz, 1 % stale. The robot's recorded condition is 4 % drops and a fresh 50 Hz IMU, so this was harsher than sim's drop8_imu35 stress case, where t3bt_a fell in 1 of 5 seeds and walk61 in none: the walk shows load intolerance, not the policy at normal condition. namecall paused 16:35:04 by its session (sent no commands); with the cameras and blackbox still running the brain stands at 30-32 Hz.
- **Cause found** (three parallel checks, verified against b0052 kmsg and the brain logs; CURRENT-STATE `servo_read_drop_fraction`): the CPU-load reading above was wrong. At 16:33:35, 61 s before walk 1, the head touch bus (TWI0 2510000.twi, XIAO 0x2a) jammed ("Arbitration lost", then bus not idle / STOP failed on every transfer, 34.7 failed transfers and about 100 kernel lines per s, never recovered). Console loglevel 4 sends each line to the 115200 serial console (about 10 ms each, interrupts off on 5.15), the servo UART ttyAS2 has no DMA and shares CPU6 with mmc0, so replies arrive late or lost; IMU fell 193 -> 75/s. The brain's reply parser trusted the length field, so one lost byte read 0xFDFF as a length and blanked every servo read for 5.5-6.8 s (14 times in the t3bt log; walk 2 hit one at 16:35:10.67 and fell). Same touch jam on 10/30 about 21:29 on the bench supply. Code, servo EEPROM and OpenRB firmware unchanged; battery not the cause (healthy on it 16:31-16:33:20). Fixed in code (bb9e9b06, not yet on the A7Z): the parser rejects lengths over 64 and bad CRCs, test_walk_wired_parser (3 of 4 cases fail on the old code). Open: why the XIAO jams the bus, console loglevel, a touch reader that stops after repeated bus errors, and `--supply bench` switching the battery guard off on the pack. t3bt_a's two walks both ran inside the fault, so they do not judge the policy.
- **17:12 deployed, 17:20 confirmed** (Shawn: "都部署"): cc0593d7 on the A7Z with sha256 readback (parser checks, touch back-off, battery guard on, console loglevel 1 live). The app's telemetry also reads the touch bus at 10 Hz while the brain runs; it backs off too since microduck-simulator 8439ab6 (team repo 47b92885). At about 17:20 the touch bus jammed again, harder (about 145 error lines per s), with the old brain code still running: 47.2-47.5 Hz, 3 of 1500 ticks missing, IMU 182-196/s, standing. The quiet console alone removed the starvation. Still open: why the XIAO jams TWI0, and the brain restart that loads the new code.
- **17:50 why TWI0 jams (analysis, A7Z offline since about 17:22)**: the bus has only the chips' internal pull-ups (duck-twi0-touch.dts `bias-pull-up` plus the XIAO core's slave pull-ups; typical about 100 k and 45 k, about 30 k together) and since D-022 runs from the head down the neck to the saddle beside the servo and amplifier wires. At an assumed 50-100 pF the rise time is about 1.3-2.6 us against the 1 us limit at 100 kHz (estimate, not measured). b0052 kmsg: "Arbitration lost" first, then 1059 x status 0x50 (master mid-read, waiting for the next byte) and 294 x bus not idle / STOP failed; it never recovered in that boot. touch_main.cpp has no I2C timeout or watchdog, so a wedged slave stays wedged until power-off. Next, without opening the head: at the next boot read the TWI0 line-state register during a jam (SDA low: nine-clock recovery from the A7Z clears it; SCL held low by the XIAO: only a XIAO reset clears it, which needs a firmware watchdog), and drop the bus clock to 25 kHz in the overlay.
- **18:30 touch must recover by itself** (Shawn: "另外你说出现问题 触摸板自己不能恢复 只能走路 这个解决方案是完全不能接受的", "为什么你会觉得这种残疾方案可以接受呢"): the earlier "walking is safe, enough" answer is withdrawn. Fault register `microduck-sim/FAULTS.json` (touch-twi0-jam, four occurrences, hypotheses H1 signal margin, H2 master pauses under load, H3 slave firmware; `faults_check.py` OPEN). New in the b0052 kmsg: three lone STOP-failed warnings 16:31:29-16:33:12 before the jam, then every read acks the address and stalls after the first byte. b0053's jam began about 17:17:40 (touch age 127 s at 17:19:47), 6 min after namecall restarted; 16:58-17:11 without namecall was clean. Self-recovery written: touch_main.cpp restarts its I2C slave when a line is held low 30 ms, task watchdog, "RS" restart command (compiled with esp32 3.3.12, not flashed: the XIAO's USB-C needs the head open); walk_wired.py sends RS while jammed (tests pass). Onset test `guide/firmware/a7z/twi0_jam_test.py` (idle / capture / load / both) runs the moment the A7Z answers; it has been unreachable since about 17:22.


## 2026-10-31 Charger-lead work paused (D-035)

- **Shawn**: 现在换成电池了 似乎也不需要充电线拖拽了 那个可以暂停. The duck runs on the battery backpack; tether fine-tunes, tether gates and the runner's `--tether` cable guard are paused. t3bt_a stays the walking candidate, judged on the no-lead cases only; the next fine-tune drops the tether delta.

## 2026-10-31 17:11-17:21 Name spotter v3, first live run

- **Run** (`namecall_20261031-171120.jsonl`, v3 per ear 0.7, `--no-person`, deployed walk61 brain started by the app at 16:59, home): 3 calls, 3 answers (kw_p 0.96, 0.89, 0.86), 0 false answers. Every call ended with the face found and the gaze held about 8 s.
- **Side**: Shawn stood front-left each time (face at +61, +36, +54 deg). The SRP (time difference) read behind-left once and right twice; the ILD (level difference) read left on all three (+7.0, +11.9, +8.4 dB). Call 2's ILD had band SNR 2.7 dB, under the 3 dB gate added 10/30, so the wrong SRP side was used and the face came only after 7.4 s; call 3's ILD overrode the SRP and was right.
- **Open**: misses are not counted; the A7Z dropped off Tailscale about 17:21 before the life log was pulled. Next lever for side: lower the ILD SNR gate or weight the ILD by its size (an 11.9 dB difference is not a floor artefact), checked on the 10/30 21:00 and 10/31 17:11 call records before a change.
- **Microphone seals** (Shawn, 2026-10-31 18:1x, head open: 目前已经是这样做的了呀): each microphone port already has a closed foam ring, so the 10/29 note about open-ended strips is out of date. No snap test has been recorded since the rings went in; whether the 300-1200 Hz ear lag now follows the free-field prediction (9-11 samples at 15 cm) is unmeasured. Next: a four-snap test when the A7Z is back, then move the time-difference band down if the low band carries the lag; otherwise the low band enters through the wall itself and direction stays on the level difference plus the camera.
- **Correction** (Shawn, same minute: 虽然不是完全闭合 就是剪了4块泡沫棉围成一个矩形这样弄得): the seal round each port is four foam pieces laid as a rectangle, so its corners may leak. Advice given: while the head is open, replace each rectangle with one foam piece with a punched hole over the port, or lay the four pieces so each end butts against the next piece's side (no corner-to-corner joints), and press the board so the foam compresses; the snap test decides either way.
- **Shawn** (18:2x): 封头腔不可能的 但是麦克风背面倒是可以想想办法能不能围起来. Advice: a small cup over each microphone board, hot-glued to the inner wall round its rim with the wire exiting through a glue-filled notch, so the board sits in its own sealed pocket and the head cavity never reaches the port; opening the wall holes from 1.6 to 3 mm also offered. Acceptance stays the snap test.

## 2026-10-31 18:55-19:20 Touch bus: firmware bugs found, held-line recovery verified, onset test running

- **XIAO dead after boot** (f629c8c0 and 069aec6a in the robot): the esp32 3.3.12 slave init refuses to start while either line is low ("bad pin state", "Bus busy") and never retries. The line watchdog restarted the XIAO while the booting A7Z held the lines, so the slave never came up (XIAO serial: reset reason 3, one line restart, slave silent; reproduced by holding SCL 200 ms from the A7Z: 0 of 25 reads). Fix: Wire.begin retried every 100 ms; after the same hold, 25 of 25.
- **Task-watchdog restarts on the bench**: with the USB cable in and the Mac's port closed, each serial write waited 2 s in HWCDC; two lines outlasted the 3 s watchdog. Fix: setTxTimeoutMs(0) (86f9f7c7); closed 12 s and open-unread 12 s, no restart.
- **Recovery (T2)**: the XIAO holds SDA or SCL low on command (HD/HC), as a slave out of step does. Watchdog paused: stuck about 17 s until the pause ends. Watchdog on: 10 of 10 back in 0.02-0.16 s, the kernel driver recovering by itself.
- **Triggers tested** (FAULTS.json): mid-read master pauses 5 ms to 3 s (H2): none persist, ruled out. Aborted reads, one extra SCL edge, a false START/STOP: none persist, on the original firmware either. One over-read (32 bytes) reproduces the 10/29 0x55 shift; it stays until RS, and the brain's parser accepts it.
- **Running**: T1 condition both, 20 min, original firmware on the XIAO, to catch the real jam's line state. The new firmware goes back on after it.
- **After the glue** (Shawn 19:4x: hot glue over all three microphone backs, wall holes opened from 1.6 to 3 mm; touched the left microphone while gluing). Snap test 19:44:22-19:47:05, a7z:~/duck-logs/snap1031.raw, 15 cm, open then covered for left, right, back (analysis scratchpad snaps.py, 30 ms windows). Left microphone works: quiet floor -40.4 dBFS (right -42.0, back -41.4), left snaps the loudest of all. 300-1200 Hz level difference now follows the side: left snaps L-R +13 to +21 dB, right snaps -6 to -12 dB (10/29 before the repair: covering a hole did not change that ear's low band). Covering the left hole drops its low band about 8 dB and its high band about 10 dB; covering the back hole drops its high band about 8 dB; covering the right hole changed nothing (right covered -11 to -16 dB like right open), so the right seal or the finger did not close. 2.5-8 kHz time differences have the right sign (left snaps L earlier by 13-18 samples, right snaps R earlier by 11-12). The low-band time difference cannot be judged from snaps (GCC peaks 0.01-0.04, snaps carry little energy under 1.2 kHz); calls decide it.
- **Onset found** (20:03-20:11, brain in stand as the only touch reader, four 2-minute cells): capture off 0 events (hands off and gripped); capture on and gripped 5; capture on, hands mostly off 2. Every event ended by itself. Earlier in the evening the real jam was caught at 19:19 (XIAO holding SDA low; two SCL clocks freed it) and three real onsets at 19:46 recovered within 0.19 s on the new firmware. Cause: microphone I2S clocks coupling into the touch pair; a hand on the head raises the rate. Proposed root fix: 2.2 kOhm pull-ups from SDA and SCL to 3V3 at the XIAO and/or a separate route for the touch pair; acceptance is the same cells test with 0 events.
- **Same evening, charger backpack back on** (Shawn: 我现在又把charger pack换上了): brain log reads 7.2 V idle, so the lead trails again and t3bt_a's lead training applies; D-035's pause of new tether work stands, but tethered walks are the robot's condition again. CURRENT-STATE `power` updated.

## 2026-10-31 20:17-20:20 t3bt_a on the robot, charger lead on: stands and walks like walk61

- Brain restarted with `models-t3bt-a` at 20:17:56 (namecall idle, brain in stand at zero command). Closed-loop stand 0.3-0.4 deg; 0.25 m/s walk 3 s, default head, no fall: tilt max 7.8 deg, 3.33 jumps/s, 4.3 % missing reads (walk61 on the same robot 6.4-7.5 deg, 2.01/s; T1 29.3 deg, 21.8/s). Slices and README: `microduck-sim/guide/firmware/mac/robot-runs-20261030-t1/t3bt/`.
- Found on the way: `--supply auto` armed the battery guard on the charger rail (7.2 V idle; `pi/battery.py` assumes the 7 V rail sits at 6.80 V). It did not trigger; a trigger would only stop the walk, but its stop marker would then block torque until 7.6 V, which the charger rail never reads.

## 2026-10-31 20:19-20:50 Name call after the glue: side right, look too small, deaf while turning

- **Run** (`namecall_20261031-201951.jsonl`, v3 0.7, --no-person, t3bt brain in walk): 4 calls, 4 answers, 0 false; camera found Shawn at 127, 84 and -58 deg (18.5, 11.4, 3.4 s), the fourth not at all after 230 deg of body turn. Shawn: the first look turned only a little though he stood straight left, then it scanned for a long time; calling again during the search got no answer.
- **Why the look was small**: every first look goes to bearing_prior.json's look_deg, 35.4 deg, fitted on 10/30 from 15 calls with callers 8-65 deg off. Refit on the 12 camera-confirmed calls since 10/30 21:00: look 61.5 deg (true folded 32-88).
- **Which cue is right**: on those 12 calls the left-right ear lag sign gave the side 12 of 12, the three-microphone SRP 5 of 12 (it read -26.8 deg for the 127 deg caller). The level difference agrees with the lag wherever it is over its SNR gate. The lag magnitude saturates at 10-13 samples for any caller beyond about 35 deg, so it gives the side, not the angle; front/back is still unknown from sound.
- **Why calls during the search were ignored**: the program's own body turn writes vtheta 0.3, and the brain-command gate skipped every call while any walking command ran (20:20:38 skip at 74.9 deg). Also the spotter scored under 0.1 on the calls spoken while the body turned (life index scores 20:21:33-20:22:00).
- **Fix** (namecall.py, tests 71 pass): side = lag sign when |lag| >= 2 samples, then level, then SRP; look_deg 61.5; a call during the own turn ends it (turn_done by "call") and re-aims from where the body points. Not yet on the A7Z: it went offline at about 20:45. Next: install, live check; a turn-noise training round if the spotter stays deaf while turning.

## 2026-10-31 evening: T2 (pick from picture features) build started, Shawn's go to train once the audit passes

- Shawn: 为什么不训练 ... 还在等什么呢; then 过了就训. T2 had waited behind T1 in the plan order although it does not depend on T1. Build (background agent, fork branch cmu/grasp): new task with slots 55-60 = [u, v, width, age, holding, visible] from a fisheye U20CAM sim camera with the measured mount, head-gain and bow-height spread, warm start from seepick61, 61-D kept, no frame history in v1. Go recorded: Kaggle smoke and run follow as soon as the CPU tests and the do-nothing-vs-warm-start reward audit pass.
- **Front/back** (Shawn 20:5x: 前后也要能判断准 ... 该训就训): the back microphone's two lags do carry front/back. A fit of the azimuth to the three pairs' own lags (`CallLocaliser.pair_fit`) on the 12 confirmed calls: median 7 deg, 11 of 12 within 30 deg, front/back 11 of 12; the SRP over the same audio median 84 deg. namecall now uses the fit, and a call fitted behind with a clear margin turns the body at once instead of searching in front first. The pre-glue 10/30 eight-direction recording replays at median 43 deg, so a post-glue eight-direction set is the acceptance test.
- **Round 4 prepared** (motion noise): `record_motion_noise.py` (A7Z: about 65 s of body turns both ways at vtheta 0.3 and head sweeps, nobody talking), `oww/motion_to_bg.py` (2 s clips per ear and mix, first 20 % of each segment held out), `oww/run_v4.sh` (round 3 data plus the motion clips as background at rate 5), `oww/eval_motion.py` (the eight held-out home calls with the held-out motion noise added at its recorded level, v3 against v4). Waiting for the A7Z (offline).
- **T2 built, audited, running** (fork cmu/grasp `645db672`, notes `cmu/grasp/T2-PIXEL.md`): task `Mjlab-SeeingPickPix-FromPick-MicroDuck-CMU-Plugged`, slots 55-60 = [u, v, width, age, holding, visible] from the calibrated U20CAM fisheye (fx 534.2) with mount, head gain and bow-height randomisation. 22 tests pass (rerun here). CPU audit 16 envs: stand61 1.93 reward/s against warm start 9.53 (0.20) and 14.05 in the +-1 cm window (0.14), gate 0.8, PASS; perfect aim (oracle) 17.84 with 69 % holds. Kaggle smoke spx-smoke COMPLETE (T4, 5 iterations, ONNX 61 -> 14).
- **Export bug found and fixed** (`5d2cc4da`): `grasp_worker.py` copied the newest .onnx beside the checkpoint instead of the file export.py wrote, so every `<task>_<it>.onnx` of the 10/27 sp runs and of the smoke was the same file; re-export with `--onnx-file` gives distinct models. The 10/27 sp-a/sp-b ONNX per iteration are therefore not what their names say (their `.pt` files are the truth); seepick61 on the robot still picked the ball on 10/30.
- **Run** spx-a / spx-b (seeds 1, 2, paired on two T4s, 4096 envs, 3000 iterations or 11 h, checkpoint every 100, stop at 500 if grasp_held never paid) pushed after the fix, RUNNING. Quota before: 28.4 h left this week. Open: far start states (20-25 cm, +-45 deg) may be out of the bite's reach because seepick61 never steps; detection noise values are guesses; runtime diff `cmu/grasp/T2-runtime.diff` not applied.

## 2026-10-31 21:07-22:00 Spotter round 4 from the life log: the duck is deaf while its body turns, and training does not fix it

- **Data**: no new recording. `oww/life_motion_bg.py` cut the body turns (65 s) and head sweeps of the 10/30 20:21, 10/30 21:00 and 10/31 20:19 name-call runs out of the always-on life log, masked voiced 60 ms frames (energy and periodicity, so footsteps stay) and the logged calls, and gave 167 two-second windows x 3 streams; the 10/31 turns at 20:21:33 and 20:21:49 are held out.
- **Training**: round 4 (`run_v4.sh`, motion clips at rate 5) on the Mac mini. The first start died at 21:14 and the Mac mini panicked at 21:28 (watchdog) because another session's RIG CAD memtest (`rig-cad-perf`, python3.12, 19-27 GB each on a 16 GB machine) ran out the memory; the spotter job used 0.3-1.2 GB. Resumed from the stored features, `mochi_v4.onnx` 21:46.
- **Result** (`oww/eval_motion.py`, `results/motion_v3_v4.json`; the eight held-out home calls plus the held-out turn noise, threshold 0.7): at the live post-glue call level v3 3/8, v4 3/8; at 0 dB v3 1/8, v4 2/8; clean 8/8 both. Head-sweep noise at the live level: v3 7/8. Held-out sets: duck calls 22/32 (v3 21/32), web videos 36/170 (27/170), false wakes on 28 min of speech 1 (2), life talk 0 (0). v4 is the new default.
- **Why**: during a body turn the voice band at the ears is 4-11 dB louder than a call from 2 m (300-3000 Hz, +6 to +13 dB over standing). It is structure-borne: coherence between the three microphones is 0.3-0.5 below 1.5 kHz and under 0.2 above, and the level is the same before and after the glue. A Wiener filter on the learned turn spectrum (0-2/8) and a voiced-frame detector for stopping the turn (4/8 calls, one false stop per eight noise windows; removed) do not get past it.
- **Open**: calls spoken while the body turns stay mostly unheard. The remaining routes are behaviour (turn in steps with short listening pauses; the walk policy's stop-start must pass a sim check before the robot) or mechanics (decoupling the microphones from the shell vibration). With the pair-lag localiser the body turns only for a caller behind, so long turning searches should be rare; the next live run counts how many calls fall inside a turn.

## 2026-11-01 01:55-02:30 Hearing the name while the body turns: a speech-enhancement front end works offline

- **Shawn**: 能在转身的时候听到我们人的声音就可以 ... 不管你用什么方式。
- **More motion data**: the 10/30 15:56-16:29 life log was continuous (file names UTC before 16:08 EDT) and covers the t2b walks and Shawn's in-place turns; `life_motion_bg.py` now also cuts motion from brain-log command rows: 360 windows (was 167).
- **Noise shape**: impacts, not servo hum. Between impacts the 300-1000 Hz level is near standing (-61.3 vs -62.1 dB), the impacts reach -53.5 and a 2 m call sits at -58.9 (median frames).
- **Trials** (`oww/make_turn_mixes.py`, `oww/score_mixes.py`, `results/turn_frontend_20261101.json`, live call level, threshold 0.7): DeepFilterNet3 per ear with a +30 dB pre-gain, then v3: 7/8 (raw 2/8), clean 8/8, one peak over 290 s of all motion audio, at 10/31 20:21:57 inside a turn where a two-syllable word was spoken (probably a real call v3 had missed). Without the pre-gain DF removes the quiet 2 m call too (clean 1/8). RNNoise 1/8; round 5 (v5) hears 6/8 raw but wakes 7 times on held-out life talk: rejected. v4 stays the spotter.
- **Next**: DF only while the duck's own body turns (the program knows when), so behaviour outside turns is unchanged. It needs a streaming runtime on the A7Z (PyTorch DF costs 0.04 x real time per channel on the Mac mini; the A7Z cost with the brain running is unmeasured, the duck has been offline since 10/31 20:45).

## 2026-11-01 02:10-02:30 Product direction: a head glance instead of a body turn, answering while seated, the fetch demo; walking is the hard listening case

- **Shawn** (requirements R11-R14 in `microduck-sim/guide/firmware/mac/namecall-20261029/REQUIREMENTS.json`, his words there; D-038): no body turn, because it is slow and nobody waits for it; the head glances as far as balance allows, like a cat that looks without getting up, and a caller behind is ignored. Seated, the duck answers with a head tilt and stays seated. Background goal: the fetch demo (call, look, follow the waved orange ball, "go fetch it", follow the throw, walk to the ball, pick it up with the beak, walk back). Hearing the name while walking, then stopping to wait, is a core function.
- **Head range**: namecall's YAW_CAP is 1.2 rad (69 deg); the walk, stand and sitstand policies were trained to head_yaw +-1.40 rad (80 deg; the joint model allows +-2.97, so 1.40 is the training limit). The U20CAM sees 62 deg wide (fx 534.2 px, 640 px), so the glance sees +-100 deg now and +-111 deg at 1.40: the whole front half either way. Seated: sitstand61 was trained with the same head command and head roll +-0.31 rad (18 deg tilt); walk_brain passes it while seated, but namecall writes only walk commands and takes over only a zero walk, so a seated duck does not answer yet.
- **Walking overlay** (`oww/make_turn_mixes.py ... walk`, `results/walk_frontend_20261101.json`): the eight held-out home calls over 38 s of 10/30 walking audio. Walking is 3 dB louder than turning in the median and 6 dB at p90 (heel strikes). At the live call level: raw v3 1/8; DeepFilterNet3 (+30 dB) then v3 2/8, v4 4/8 with two noise peaks over 0.5. The turn front end does not carry over. A lower threshold while walking has no measurable margin on 32 s of noise.
- **Gap**: 54 s of walking audio in all. The next data come from the always-on life capture during ordinary walks (no recording session needed), split by walk for a held-out test; then a spotter trained on DeepFilterNet output with calls overlaid on walking noise at the live level.

## 2026-11-01 02:35-03:10 Head-only glance (R11) and seated answer (R12) built and checked on the as-built sim

- **Shawn**: 先做这两项.
- **Trap found**: the expression library hands part of any gaze past its 1.2 rad orient_threshold to a body turn and counter-rotates the head, so raising the cap alone would have left a 1.40 look at 0.60. namecall now switches that share off; a test fails at 0.603 with the old threshold.
- **Code** (namecall.py): YAW_CAP 1.40; seated: the brain gate accepts a finished seat, the writer keeps `{"mode": "sit", "head": ...}` and never writes a walk, the head adds a 0.25 rad tilt toward the caller and moves at most 1.0 rad/s without the pre-inverse snap, and no body turn is planned from a seat. 55 tests pass.
- **Sim** (`namecall-20261029/glance-20261101/README.md`; as-built manifest of 2026-11-01 = battery variant + D-037 battery position and top plugs + head microphones and touch board, all estimates; 7.0/7.8 V, 17 % dropped reads, 3 seeds): standing 18/18 no fall, tilt change <= 1.6 deg, head yaw 1.23-1.31 rad (1.08-1.18 at the old cap), camera sees about +-104 deg. Seated: never knocked over, tilt change <= 5.1 deg, yaw 1.10 left and 0.85 right, tilt 0.2 rad.
- **Separate finding**: the sit-down itself tips backward to about 63 deg in 6 of 32 sim seats at the 10/31 read-drop rate (17 %) on the 11/01 model, 0 of 32 at 4 %; the battery plan model 8-9 of 32 at either rate; the bench-supply model 0-2. A seated answer needs a seat that holds first.
- **Not done**: robot check (A7Z offline since 10/31 20:45); the team repo copy of namecall is not synced.

## 2026-11-01 13:20-13:50 Sit-down tip in the sim traced to the fault-state read-drop rate

- **Shawn**: 真机目前不会后翻 可以查下什么原因.
- **Robot** (`namecall-20261029/glance-20261101/real_sits.py`, `real_sits.txt`, backed-up A7Z brain logs 10/21-10/30): 22 sit-downs folded the knees to about 1.3 rad and none tipped. Reads dropped on 0-4.2 % of the sit-down ticks (median 1.5 %); peak trunk tilt 4.4-11.8 deg (median 6.0).
- **Sim at the robot's rates** (`glance_sim.py --sit-entry`, 8 seeds, 7.2/8.0 V, 2026-11-01 and plugged models, Mac mini): 0 of 96 sit-downs tipped at 0, 1.5 and 4 % drops; peak tilt 6.0-8.0 deg. At 17 %: 3 of 16 and 2 of 16 tipped.
- **Cause**: the 03:10 entry used 17 %, the 10/31 touch-bus fault value of CURRENT-STATE `servo_read_drop_fraction`; the robot never sat down at that rate. The sim and the robot agree. A sit-down during a read-drop fault is untested on the robot. R12 gap updated.

## 2026-11-01 T2 picture pick: trained, works only near the landing spot

- spx-a / spx-b ran the full 11 h on Kaggle (2544 / 2434 iterations). The start-window curriculum stalled at +-3 cm,
  training success 0.41-0.47 (needs 0.5 to widen), the same stall as the 10-27 seeing pick.
- Eval at 512 envs (`microduck_rl-grasp/cmu/grasp/seeing-pix-eval.json`): spx-b_2400 picks 72 % within +-1 cm,
  70 % within +-3 cm, 32 % within +-8 cm, 18 % over the full 8-25 cm, +-45 deg set; falls 2-12 of 512.
  With the picture zeroed it drops to 6 % at +-3 cm, so the policy does use the camera.
- Cause of the low full-set number: reach. The beak bites at 10 +- 1.2 cm forward whatever the ball distance; the
  pick never steps. Next: the walker / gaze hand-over must stop with the ball within +-3 cm of the spot 8.7 cm
  in front of the feet, or the pick needs a stepping phase. Details: `cmu/grasp/T2-PIXEL.md` (commit 2d4dd54e, cmu/grasp).

## 2026-11-01 Walk-up stop accuracy against the T2 bite window

- approach_sim.py, 12 mm ball, 25 placements 0.3-0.9 m and +-40 deg (`microduck-sim/guide/firmware/mac/approach-handover-20261101/README.md`).
- As deployed (stop at 14.5 cm, accept bearing 25 deg): 23/25 arrive, no falls, but only 52 % end within T2's +-3 cm
  window: the ball sits about 2.5 cm too far and 10-20 deg left.
- Sim-only change, stop at 12.5 cm, accept bearing 18 deg and range up to 11.7 cm: 23/25 arrive and 92 % end in the
  window; with the camera pitch 2 deg off 76-80 %. Expected walk-up-then-bite in sim about 65 %.
- approach.py is unchanged. The robot's faster walk (0.15 vs 0.11 m/s) coasts further after the stop; not tested.

## 2026-11-01 T2 brain-harness matrix and first robot deployment

Matrix (`microduck-sim/guide/firmware/mac/t2-chain-20261101/README.md`): spx-b_1800 is the best T2 candidate in the as-built harness, far below its Kaggle numbers and below seepick61; spx-b_2400 scores 0 here. On the real sphere jaw current does not change the result, correcting the earlier attribution to jaw force. Prediction before the robot run: the beak lands beside the ball and does not hold it. `t2pick.py` runs it on the A7Z and holds the driver lease.

First robot run with T2 (2026-11-01 21:01, `seepick.py --t2`): found, walked and held the real ball at 150 mA on try 2, against my prediction that it would not hold. Fell 0.9 s after the hand-back: T2 with the holding bit keeps the neck at -1.14 rad, stand61 throws it back. In the sim, seepick61 finishing the rise from phase 0.50 gives peak gyro 1.17 against 3.56 and 3 of 6 held to the end against 0. Details: `microduck-sim/guide/firmware/mac/t2-chain-20261101/README.md`.

## 2026-11-01 21:40: T2 retests, in-place stall at a fixed heading, camera lost

Runs 2 and 3 of `seepick.py --t2` did not hold the ball, so the rise repair is still untested with a real hold. The right-turn guard that ended them is the 10/30 stall: turn_test shows it at a fixed heading (-50 to -55 deg, spring-back about 20 deg), and from +89 deg the same right command runs freely. That rules out a weak right turn and supports the twisted-lead reading of 10/30; the lead check itself has not been done. The spring-back also explains the bearing jumps in approach's face state. During the test the U20CAM dropped off USB (error -71, rebind did not help). Details: `microduck-sim/guide/firmware/mac/t2-chain-20261101/README.md`, `microduck-sim/FAULTS.json`.

## 2026-11-01 21:55: T2 runs 4 to 6, 22 problems listed, A7Z offline

The duck now finds the ball by itself and walks to about 20 cm (run 5, 0.28 m walked), but no bite since run 2: close-range turning loses to spring-back and short spins, and false wrong-way stops use up tries. The camera plug dropped twice on a right-spin lurch. My et7304 driver unbind at 21:52 took the A7Z offline. Full list: `microduck-sim/guide/firmware/mac/t2-chain-20261101/README.md`.

## 2026-11-01 22:40: why the A7Z went offline

The flight recorder stops at 21:52:11, within a second of my et7304 driver unbind, with no panic or watchdog text; the next boot is a cold boot at 22:37:58 right after Shawn re-plugged. Not a Wi-Fi or SD fault: Wi-Fi link and CPU were normal up to the last row, and the boot was clean. Open: why the 22:01 power cycle left no boot record. Details: `microduck-sim/guide/firmware/mac/t2-chain-20261101/README.md` item 23.

## 2026-11-01 23:30 MicroDuck T2 evening data analysed

Real T2 picks: 2 (x 0.100 y -0.021 held, x 0.122 y -0.005 missed). As-built sim sweep with the real sphere: held 0 of 60 from dx +2 to +6, 2 of 6 at dx +1. T2 window tightened to x 0.085-0.115, y -0.035 to +0.005; timed creep from x 0.135; aim gate on the last sighting; creep steering. Run 8 try 2 was in place and ended by a false detection. In-place turning is unsolved: right 10 deg/s, left 19 deg/s median against 29 commanded, input clamped outside the trained range; walk61 never retrained for it. Details: microduck-sim/guide/firmware/mac/t2-chain-20261101/README.md items 24-33. Not yet run on the robot.

## 2026-11-01 23:50 T2 closes at a fixed spot on the robot

Run 9: full flow, no fall, two picks in the window, both empty. FK on the logged joints: mouth tip x 0.118-0.122, y 0.003-0.006 at phase 0.35 in all four robot picks whatever the ball; the picture feeds T2 for only 0.35 s. Working window about +-0.7 cm around x 0.100 y -0.021 (one hold). Head yaw moves the tip 0.060 m/rad; no head correction exists for x. Testing a yaw_off on the T2 goal in the sim. README items 34-37.

## 2026-11-01 23:40 Run 10 spin fall, spin clamp

Run 10 fell in an in-place turn. Spin rate collapses at input 1.5 and up (about 0 deg/s, against 18-27 at 1.0-1.5). SPIN_TURN_MAX lowered to 1.25 as a test, head fixed during in-place turns, near-ball bearing finished on the IMU. yaw_off on T2's head yaw deployed, sim only so far (dy -2: pad error 2.1 to 0.8 cm). README items 38-40.

## 2026-11-01 23:35 Run 11 fall: head motion during spins

My head change for run 10 caused run 11's fall: head pitch dropped 0.9 rad in 0.6 s at a walk-to-spin change. All three spin falls that evening had the head moving during the spin. A spin now holds its entry head command. Camera dropped off USB again at the fall (third drop); needs a re-plug. Not yet run on the robot.

## 2026-11-01 23:45 Run 12: no fall, walked over the ball

Spins held the head and did not fall. The duck walked over the ball because my tightened window sent a seen ball at x 0.086 into a creep, and the aim gate threw out the real ball after the first creep. Both fixed in seepick.py. README items 42-44.


### 2026-11-02 00:50 dock task, first audit failed
Shawn stopped the hand-written control line and handed the training line over ("你来接受吧"). New task Mjlab-Dock-MicroDuck-CMU-Plugged (microduck_rl branch cmu/dock, commit 8611d729, cmu/grasp/DOCK.md): walk61 warm start, T2 picture slots as the only ball input, head as policy action, stop with the ball at T2's fixed closing spot. First audit (Mac mini, 16 envs, reward/s): stand 2.59, walk_over 1.09, intended 2.90 (docked 0/16), oracle 8.04, warm 1.60. Gate failed: stand/intended 0.89 > 0.8. Causes: upright/pose terms pay a motionless robot 2.71/s; the scripted driver never docked. Fix in progress: cut the standing family, add a negative potential on ball-to-spot error, audit at curriculum stage 0 with a driver that must dock in half the episodes, add head-motion and torque disturbances during turns. Sim foot condim 3 vs 6 both turn in place at 8-10 deg/s against 29 commanded, so the sim already reproduces the robot's weak turn; the dock policy has to learn its own turning. Literature: HOMIE 2502.13013, Disney 2501.05204, Digit 2404.19173, soccer 2511.03996, VBC 2403.16967, IndustReal 2305.17110. Open risk: the spot is in the picture only with head pitch about 1.45 rad and walk61 stops stepping under head commands.

### 2026-11-02 03:55 dock task: audit passed on margins, smoke passed, paired run launched
Second audit (64 envs, stage0 = ball within 5 cm): stand -4.48/s, walk_over -4.81, intended -1.16, oracle +5.61, warm -6.41. Rewards are negative away from the spot (dock_error cost), so the gate is a margin: degenerate policies earn well under the driver, docked earns 10/s over standing. The scripted walk61 driver never docked within 1 cm (its creeps are 1-10 cm), so the min-docked check was dropped and noted as a yardstick limit. Branch cmu/dock commit 03669960. Kaggle smoke dock-smoke: 5 iterations, 64 envs, saved ONNX, dock metrics logged (docked_ema, fall_ema, dock_error), 2.08 s/it at 64 envs. Paired run pushed: dock-a seed 1, dock-b seed 2, 4096 envs, 3000 iters, 11 h cap, stop rule dock-stop-iter 500 / dock-min 0.05 / fall-max 0.3. Watcher writes t2-chain-20261101/dock-a-watch.log and fetches at the end. Quota after this run: about 5.5 h left this week.

### 2026-11-02 12:20 dock-a/dock-b stopped at 500 iterations: the policy learnt to die by walking over the ball
Both seeds stopped by the task-metric rule (docked_ema never reached 0.05; max 0.002 and 0.003), 0.9 h each, 1.8 h quota. Cause from the training log: walked_over terminations rose 178 -> 456 per iteration and the mean episode length fell 77 -> 9 steps while per-episode return rose from -22 to -5. The per-step cost on the ball-to-spot error made any termination the cheapest escape, and walked_over cost nothing. The audit missed it because it compared reward per second, not return per episode (a 9-step episode scores well per second). Fix: no per-step cost, upright/pose weights 0 (nothing pays standing), shaping is progress and hold only (>= 0), one-off costs on the two bad endings (fall 120, walked over 60), audit gated on return per episode. Rerunning tests and audit on the Mac mini before the next push.

### 2026-11-02 12:45 dock reward v3 audit PASS, second paired run launched
Third audit (return per episode, stage0): stand -11.3, walk_over -48.2, intended +8.6 (docked 34 %), oracle +45.0, warm -17.8; PASS. Tests 23 pass. Branch cmu/dock commit 44603e89. Pushed dock-c (seed 1) and dock-d (seed 2), same flags as dock-a/b; watcher log t2-chain-20261101/dock-c-watch.log. Quota left before this run: about 14.8 h.

## 2026-11-02 12:35 Name call: what stands today, CPU after the touch jam fix

Not a resident ability: no service, duck-run.sh or app starts namecall.py. The A7Z still holds the 10/30 22:18 namecall.py and v3; the side and bearing fits, v4, head glance (R11) and seated answers (R12) are local only. The register's "A7Z offline" notes were stale: it came back on 11/01 and the install was never rerun. Last live name-call run: 10/31 20:19-20:33 (v3 0.7, --no-person, 4 calls, 4 answers, 0 false). CPU in that run, with the jam fixed (b0056 flight recorder, duck_wired_log_t3bt1031-201756): whole-system busy 41-42 % of 8 cores against 19-24 % before it, about 1.6 cores for namecall; brain 46.8 Hz, 0-0.5 % of ticks missing a read, in walk mode at zero command. Against 10/31 16:34 under the jam: 38.8 Hz, 17 % stale. So the starved brain was the kernel error flood, as Shawn says. Capture still makes bus errors (no pull-ups yet) and they now recover within 0.19 s. Not measured: a walk with namecall running on the fixed system, and how the 1.6 cores split between listening and the face detector.

## 2026-11-02 13:05 Right knee ID2 silent with a red light after the pack ran flat

At 12:33 the pack ran flat with the brain on `--supply bench` (guard off), rail 7.2 -> 4.5 V; ID2 answered to the last tick at 23-30 mA with no fault. After the restart on a full pack (8.0-8.2 V) ID2 answers nothing: no ping, read or broadcast reply, no bytes at all, Reboot has no effect, red light (Shawn). The other 14 answer, all with Shutdown 52, hw 1 (input voltage only), 25-28 C, torque off. So not the 8 V rail by itself and not a latched error the brain can clear. Brain 39 Hz is the 10 ms sync-read timeout on the silent ID (app label "overheat protection" is wrong), and the stand gate (`imu_valid and fresh`) blocks open-loop stand on missing joints with a message that blames the IMU. namecall was not running (refused: no brain). "Stop torque" reboots only servos that report a latched error, so it never reaches a silent one. Not known: whether the brownout or plugging in the full pack killed it.

## 2026-11-02 14:00 Right knee ID2: the servo had fallen back to factory settings; restored

Removed and alone on a separate OpenRB at 4.9 V, it answers at 57600 as ID 1, error 0, hw 0, and every setting reads factory: baud 1, RDT 250, Shutdown 53, homing 0, limits factory. On the duck's bus, fixed at 1 Mbaud, that reads as silence, also to Stop Torque and Reboot. Factory Shutdown 53 keeps the input-voltage bit, so on the 8 V pack (limit 7.0 V) it alarms, which fits the red light; the other 14 hold 52 and stay on. Cause of the reset is inferred, not proven: the only event before it is the 12:33 flat pack (rail 4.5 V), and the robot's run code holds no factory-reset instruction and writes no ID. A broadcast reset would have hit all 15. ROBOTIS documents no brownout reset for the XL330 that I found; an MX-28 owner reports self resets on bad power (poppy.discourse.group/t/mx-28-motors-factory-reset-by-themselves/3331). Restored with mac/restore_factory_servo.py: at 1 Mbaud now ID 2, baud 3, RDT 0, opmode 3, Shutdown 52, torque 0, hw 0, position 1590. Not yet refitted. Open: knee zero check before torque; `--supply bench` left the pack without a low-voltage stop.

## 2026-11-02 14:20 Why the battery guard did not act on the 12:33 flat pack

The brain started at 01:08 on the charger pack with `--supply bench` (log app1102-010842). Shawn changed to the 2S pack around 12:22 and pressed the phone's backpack switch; ~/duck-supply reads battery from 12:23:58. duck-command.py restarts a brain only in monitor or off, and this one was in walk with torque on, so it kept the old setting and kept logging until 12:33: the guard stayed off, with no warning that it had. Rail per minute: 7.2 at 12:24, 7.1 at 12:30, 7.0 at 12:31, 6.7 at 12:32, 5.5 median at 12:33, last reads 4.6 V. Inferred: armed, it would have warned at about 12:31 and stopped at about 12:32-12:33, but its stop only ends walking and keeps torque on, and nothing can cut the pack, so a robot left standing still drains. The brain started at 12:53 runs `--supply battery`. Open, not changed: the switch not taking effect on a driving brain; no action below the 6.6 V stop.

## 2026-11-02 15:00 Battery guard gaps closed in code; rescue tool for a factory-reset servo, untested on hardware

Backpack switch: `walk_wired.py --supply-file ~/duck-supply` reads it once a second, so a driving brain changes guard too. New floor: after the battery stop, 6.2 V on three samples makes the robot sit and turns torque off (6 s at most, by Shawn's go on 11-02; the only exception to hold-until-told). App: battery warnings in the status line and live panel. Tests: 22 fake-world guard tests pass, including the 12:33 trace; not run on the robot, and sitting at 6.2 V has never been tried. Not deployed: A7Z offline. driver-lease test not run here (vite not installed on this Mac).

Freeing ID 1 does not help: the servo is unreachable because of the 57600 baud, not its ID; only it listens at 57600, so there is no clash with the real ID1 as long as the ID is written before the baud. `pi/rescue_factory_servo.py --id N` draws 57600 frames with 1 Mbaud bytes inside a carrier packet the OpenRB forwards, then reads success back at 1 Mbaud. No flash, no opening. Passes a software 16x UART model at +-2 % clock error; the first version failed that model (a stop-region glitch synced the receiver early). The real servo's receiver is unknown. Next: test on a separate OpenRB with a factory-state servo, before relying on it.

## 2026-11-02 14:10 Right knee refitted one hole off (90 deg); found before torque

With both legs held symmetric by Shawn, torque off: left knee tick 1496 (-3.5 deg), right knee tick 1568 (-87.2 deg). Mirrored, the right should read about +3.5 deg, tick 2600; it is 1032 ticks off, 90.7 deg, one step of the horn's four-hole pattern. The live view tracked both knees as they moved, so the encoder and link move together. Fix: lower link off the ID2 horn, horn turned until the right knee reads about 0 deg, link back on. Torque stays off until the reading agrees.

## 2026-11-02 14:00 Right knee link refitted, brain back with the guard on

The agent turned the detached ID2 horn to tick 2564 under torque (27 deg/s, 15 mA, no load), Shawn screwed the link back; 13 mA under hold, then torque off and profile velocity restored to 0. Torque off, right 2565 (+0.4 deg), left 1463-1468 (about -6 deg), the right leg was not moved again. Six degrees is far from a hole step (90 deg); the stand test decides the rest. Brain started by duck-run.sh on the A7Z, 49.7 Hz, 15 answer, --supply battery --supply-file; the switch tested live in monitor: bench -> guard off, battery -> guard on within a second. Pack 7.4 V idle. The guard's floor is still untested on the robot.

## 2026-11-02 14:12 Low-battery calls did not sound; one name call looked the wrong way

Shawn saw about 5 % and the duck stayed quiet. The brain log's last row (14:09:17) reads 6.8 V, guard `warn`, walk at zero. The running brain started 13:55, before the alarm code went in, so it had the guard states but no calling. The next brain start loads it. The calling has not been heard on the robot yet. Shawn powered off at about 14:09.

Name call in answer mode, 14:02-14:08: 9 calls, 9 quacks, no known false answer, faces found on 8. At 14:06:32 Shawn was on the left and the duck looked right: the ear-pair lag was +5.5 at peak 0.229, the weakest of the run, and it overrode the SRP side and the +6.49 dB level. Lag now decides only at peak 0.35 or more (`SIDE_LAG_MIN_PEAK`), which sends that call left. This threshold rests on one failure and 7 right calls from one session; older logs on the A7Z were not checked because it is off. Not on the robot yet.

App correction: the battery reading first went into the generated `microduck_rl/cmu/simulator` copy; it now lives in `microduck-simulator` (commit df3dea6) and is deployed to the Mac mini and the Mac vite server.

## 2026-11-02 15:30 Name call runs as a service, face finder on demand

Shawn: "先起起来 以后自动启动好了 如果功耗不高的话". The face finder now runs only around a call. Idle name call fell from about 1.5 cores to 0.39, the brain rose from 45.6 to 48.2 Hz, CPU temperature from 52 to 47 C. Battery power was not measured. `duck-namecall.service` runs `namecall_boot.py`, which waits for the brain in walk mode at zero velocity and restarts name call after it exits; records in `~/duck-logs/namecall_boot.jsonl`. Enabled at 15:28 and disabled again at 15:30:02 with the rollback Shawn asked for ("快回滚"; sudo log, corrected 2026-11-06); a real power-on and a call on this version are still to be checked. The App does not show this service's health yet.

### 2026-11-02 18:40 dock-c/dock-d stopped at 100 iterations by the fall rule; v4 reward in test
Both seeds: fall_ema 0.20 at iteration 10 rising to 0.34 at 100, episode length 300-370 steps (no early-death exploit this time), progress 0.06 per episode, hold 0, return falling -57 -> -103, action std growing 0.25 -> 0.49. Reading: with progress and hold as the only positive terms the task signal was too sparse; the entropy bonus (0.01) inflated the std with nothing to oppose it and the noisy walker fell. Also the warm start's forward bias (SYNTH_B vx 0.1) walked it past a ball already within 5 cm (audit: end error 17 cm from 5 cm starts). v4: dense bounded positive closeness exp(-(err/0.05)^2) at 10/s, entropy 0, forward bias 0, fall rule only after iteration 300; stillness thresholds to be set from stand61's measured trunk speed (the oracle docked only 66 % under the chosen 0.03 m/s). Quota used so far on dock: 1.8 + 0.5 h.

### 2026-11-02 20:35 dock v4 audit PASS, third paired run dock-e/dock-f launched
Audit a6 (return per episode, stage0): stand +6.9, walk_over -41.8, intended +68.2 (docked 25 %), oracle +144.2 (docked 69 %), warm -1.4; PASS; tests 23 pass; cmu/dock commit 350ccefd. Stillness measured: stand61 trunk speed median 0.0015 m/s, p90 0.10 m/s; the tether yaw spring (which no longer exists on the battery robot, D-035) is off; body torque 0.03 N m. Open: oracle docked share caps at 69 % (settling, head wander or ball contact; per-env trace to do). Pushed dock-e/dock-f, same stop rule with --fall-after 300; watcher t2-chain-20261101/dock-e-watch.log. Quota used on dock so far: 2.3 h of 30.

### 2026-11-03 12:50 dock-e/dock-f finished: first policy that docks, plateau at 17-23 % from 5 cm starts; work paused on Shawn's word
Both seeds ran the full 3000 iterations (5.2 h each). The task metric docked_ema (ball within 1 cm of T2's spot, still, upright, judged over the last 0.5 s) went from 0 to a plateau by iteration 750: dock-e 0.20-0.23 (max 0.26), dock-f 0.13-0.19 (max 0.21). Falls 2-4 %, action std converged to 0.02 by iteration 1000, the curriculum window stayed at 5 cm (advance needs 0.5). The oracle (stand61 with the ball held on the spot) scores 69 % on the same metric, so the policy reached about a third of the ceiling and stopped. Checkpoints in microduck_rl cmu/dock cmu/grasp/policies/ (dock-e_2999, dock-f_2999, dock-e_1000). Not done, in order of value: (1) dock_eval.py on the checkpoints and a per-env trace of why the oracle itself is only 69 % (settling, head wander or ball contact); (2) a look at what the plateaued policy does in the failing 80 % (walks past, stops short, never still); (3) only then a reward or observation change. Kaggle quota: 7.5 h used on dock, 9.7 h left this week (reset 2026-11-07). Shawn: "把进展记录下来吧 其他先停下好了"; nothing else is running.


## 2026-11-04 Mochi response deployed and boot service enabled

Problems P5/P6: make the existing name response available without manual process startup. Initial live inspection found `duck-namecall.service` disabled/inactive despite the earlier November 2 enablement record; the cause of the intervening disablement was not established. The old supervisor also waited for a stationary motor brain, so enabling it alone could not provide a cold-boot response without starting motor control.

Deployed `namecall.py --audio-only`, a supervisor that chooses audio-only or guarded stationary/seated head response, and the corrected service ordering. No motor brain starts automatically. The service waits for audio selfcheck, reaps capture helpers before mode changes, and restarts after failures. A live service restart returned to one listener and one capture process. Installed files matched the canonical source hashes.

Live acceptance: three detected Mochi calls, three unmuted quack events and face detections; Shawn replied “ok了” to the request to verify audible calls and head turns. All 77 name-response and supervisor regression checks passed. Actual cold power-on and seated physical response were not exercised; moving-call stop and complete fetch remain open.

Current configuration belongs to `microduck-sim/CURRENT-STATE.json` fact `a7z_namecall_start`. Evidence: `microduck-sim/guide/firmware/mac/namecall-20261029/boot-acceptance-20261104.json`; acceptance register R16 remains partial because cold-boot observation is outstanding. Deployment implementation commit: `1c3bfef8`.

## 2026-11-05 Idea: a small thing to flick, and the pet answers

Shawn, reading the Steve Jobs biography: Jony Ive once designed a pen with a small ball on the cap to flick, for a playful emotional bond with the pen. He wants the same kind of small human-pet interaction on the pet robot, with the pet reacting (teased, comfortable, or similar). Recorded as an idea in `PET_ROBOT_FEATURES.md` section 14; nothing designed or built.

## 2026-11-05 Business thinking: companionship, brand, participation, older users

Shawn's unfinished thinking, recorded with his words in `PET_ROBOT_FEATURES.md` section 15: pet robot and community are both a companionship business; build a brand that gives users identity and emotional value; let users take part (extend features, teach skills, analyse the pet's daily data); a companion robot for middle-aged and older people with emotional interaction and healthcare monitoring as a possible entry point, with authorised data export; older and young users as one axis, professional and everyday as a possible second axis, not settled. No decision taken.

## 2026-11-05 Feature matrix by path certainty

Shawn: plan a feature matrix as well as a product matrix, separating what can ship soon from what needs a path found. First cut in `PET_ROBOT_FEATURES.md` section 16: Lane A quick, Lane B path known, Lane C find a path. Each big promise (teach it, it keeps learning, it watches over health) splits across the lanes, so it can ship shallow while the frontier version stays research. Four standard web searches back the Lane C and regulation notes; coverage is thin and marked as a first read. Not yet reviewed by Shawn.

## 2026-11-05 Open question: generalise across robot forms at all?

Shawn, from the Jobs biography (NeXT as a brain for many machines, Apple later running only on its own hardware): the project may not need the generalisation route. Recorded in `PET_ROBOT_FEATURES.md` section 15 as open; section 11 and the existing body cards (duck, OMX arm, vacuum) are unchanged. No decision taken.

## 2026-11-09 Sim-vs-robot scorecard: the sim never predicts a fall

Problem P5 (sim-to-real for MicroDuck motion). Shawn asked whether the simulation is good enough, after reading about sensitivity analysis and adversarial data collection for sim-to-real gaps. Test: replay 12 recorded robot runs (six 10/18 walks, six 11/06 seeing-pick runs) in the as-built sim with the same brain code, the same commands (`brain_sim_check.py --cmd-replay`, new) and the logged supply and dropped-read share, three seeds each. Result: 5 of 12 outcomes match, all of them runs where nothing happened; all 7 misses are robot falls or guard trips where the sim stayed up. Trunk jitter in the sim is 0.10-0.44 of the robot's. The earlier get-up and bend gaps point the same way. A sim pass is therefore no evidence the robot stays up. Card and method: `microduck-sim/guide/firmware/mac/scorecard-20261109/README.md`. The ankle limit was already in every as-built route at 1.36 rad (D-040). Shawn's plan for this week: fit the short head camera cable and tie the Dupont leads down, then run the four test sets in that README as new card rows (straight walks, air walk, in-place turns, held bend after the ankle leads move to the front socket).

## 2026-11-10 Scorecard corrected: the replayed stop command, not the plant, made the sim's falls

Problem P5. A recount in the strategy session found two reading errors, both fixed and rerun on the Mac mini. (1) The card read sim falls from the tick log, which never holds the falling tick (brain_sim_check.py writes the row before the physics step and stops in the step that passes the limit); it now reads the sim's own `fell_at`. With that, the sim seemed to follow 10 of 13 robot falls, 0.5-0.9 s late. (2) The run ledger lost or misplaced falls that began in a short zero-command balance or just after a switch to stand; each fall is now charged to one action: 14 falls, walks 63/67, turns 33/35 (all at 0.5 rad/s), balance 92/98. A control then replaced the robot's own stand command, which its controllers write when the robot is already tipping (robot 15-49 deg, sim 3-7 deg at that moment), with walk at zero command: the sim stayed up in 12 of 13 ledger falls and 4 of 4 card falls. So the sim reproduces 1 of 17 robot falls by itself, falls on its own in 3 actions the robot survived, and an upright sim robot tips over within a second of a walk-to-stand switch (not tested on the robot). Evidence: `microduck-sim/guide/firmware/mac/scorecard-20261109/README.md`, `control-nostand.json`, `scorecard-auto.json`.

## 2026-11-10 Flying MicroDuck: feasibility and first design for hopping onto a table

Problem P0 (side exploration of the MicroDuck body, Shawn's idea after a Handmade Geng video: jetpack plus a second battery, fly up onto a table and down again; "所有方案都可以改，包括涵道电机，喷气背包等"). Report: `~/code/reports/20261110-flying-microduck.html`, source `~/code/reports/src/20261110-flying-microduck.md`, sizing script `~/code/reports/assets/20261110-flying-microduck/calc.py`. Nothing bought, nothing built, no decision by Shawn yet.

Findings (duck mass 960 g is the component estimate in `microduck-sim/CURRENT-STATE.json`, never weighed):
- Four 50 mm EDFs (previous session's plan): pack about 670 g, take-off 1.63 kg. Vendor thrust 750-950 g per fan, the only independent bench tests 440-680 g, so thrust-to-weight 1.2-1.5; hover 0.8-1.2 kW.
- Four 64 mm EDFs: thrust-to-weight 2.0-2.5 but the pack is about 1.03 kg (take-off 1.99 kg).
- Four 76 mm ducted props (3 inch, T-Motor F2004 KV3000 + Gemfan D76, vendor bench 794 g at 4S): pack about 430 g, take-off 1.39 kg, thrust-to-weight 1.7-2.3, hover 560-660 W, about 2.8 floor-table-floor round trips on a 4S 1300 mAh pack. Recommended in the report.
- Published precedent closest to this: Jet-HR2 (17 kg, four 90 mm EDFs, take-off at thrust-to-weight 1.17, 2 s, caught by poles, yaw oscillation). ArduPilot documents loss of attitude and altitude control at motor saturation.
- Proposed control split: separate ArduPilot flight controller for attitude, downward optical flow plus rangefinder, A7Z sends take-off / move / land over MAVLink. The 0.75 m rangefinder step at the table edge has no ready-made handling.

Evidence that would change the decision: a single-prop bench test below 520 g at 4S (thrust-to-weight under 1.5); the duck failing to stand or walk with 430 g of dummy mass at shoulder height (zero-cost first test); the real weight differing from 960 g.

Not established: whether the walking policy (trained at 0.96 kg) walks with the pack; how the pack attaches to the trunk; noise; drift under optical flow. A naive held-pose MuJoCo check of standing under load was abandoned because the held pose fell even without load, so it says nothing either way.

### 2026-11-10 Flying MicroDuck, design corrected to a twin-booster jetpack (problem P0)

Shawn's requirements, in his words:
- Look: "你这不就成了一个肩膀上架着一个四旋翼无人机了吗 看着一点都不炫酷啊". The ducted-prop quad recommended above is withdrawn.
- Default premise: "能不能在不影响我们之前那些行为的基础上 或者至少重新训练模型就能做到之前那些行为的基础上 让它变成飞行版". This was always the premise ("这不是默认的要求吗"), not a changed requirement.
- Method: "现在要你计算和出设计 仿真走路承重也只要算就知道". No simulation for this study.

Design (all by calculation, sources in the report):
- One nacelle per side, two 50 mm EDFs in tandem in each (centre y = +-103 mm, z 146..208 mm), above and outside the legs (leg top z 113, outer y 71), below the head (z 215). Total width about 266 mm.
- 6S supply from two 3S 1300 mAh packs in series, one in each pylon between trunk side and nacelle; the existing charger charges 3S. Combined COM moves about 2 mm back and 12 mm up.
- Pack about 705 g, take-off about 1665 g. Thrust-to-weight about 2.0 with the vendor 6S figure (1240 g per fan, vendor only) derated to two thirds; 3.0 on the vendor figure. Hover 0.83 to 1.19 kW, 61 to 87 s, about 2.8 round trips.
- Static single-support joint torque vs the model limit 0.96 N m (`microduck-sim/extensions/flight-20261110/leg_load.py`): today hip roll 20 %; with the pack hip roll 33 %, hip pitch 22 %, ankle 17 %, knee 13 %. A back-mounted battery variant reaches hip pitch 45 %, ankle 39 % and was rejected.
- Control unchanged: ArduPilot quad mixing on the four fans, optical flow plus rangefinder, A7Z over MAVLink. Yaw authority is the weakest axis.
- True-scale 3D page built from the sim meshes: `microduck-sim/extensions/flight-20261110/flying-duck-3d.html` (built by `build_page.py` from `template.html` and `duck_mesh.json`; both large files are generated and not committed).

Evidence that would change the decision: a single 6S fan measuring under 625 g on the bench (thrust-to-weight under 1.5); the real weight differing from 960 g; a retrained policy that cannot walk at 1.67 kg.

Not established: walking, turning and get-up with the pack (needs retraining with the new mass, not started, needs Shawn's nod); pack-to-trunk mounting; yaw authority; noise.

## 2026-11-10 Flying MicroDuck, detailed design: four 50 mm EDFs on 4S ("四涵道喷气背包")

Shawn's decisions, in his words: "那不是4助推器吗 为什么叫双助推器 ... 感觉还是4个电机好一点"; "遥控可以省掉，我们做页面的就行"; "货源只有一款也太局限了，换都不好换" (about the single-source 6S 50 mm fan); "64太大太重了 就按50来做 细化一下 出个页面 细化一下所有细节". Calculation and geometry only, no simulation.

Page (Chinese, self-contained, true-scale 3D with stand / real logged bend / head-scan poses): `microduck-sim/extensions/flight-20261110/flying-duck-design.html`, built by `build_design.py` from `design-template.html` and `duck_poses.json` (`export_duck_poses.py`; generated files not committed). It supersedes the 6S "twin-booster" layout in the entry above and in `~/code/reports/20261110-flying-microduck.html`.

- Design: 4 x QX-Motor 50 mm 12-blade QF2611 4000KV on 4S (vendor 950 g each, CW and CCW sold), two per side nacelle at y +-110, z 131..195; 2 x 4S 850 mAh in parallel beside the trunk; Kakute H7 V2 + Tekko32 F4 4in1 50A on the right rear; MicoAir MTF-01 flow + range at the right rear looking down; external compass; ArduPilot QUAD X, fans canted 6 deg fore-aft for yaw; A7Z over a spare UART (MAVLink), control and stop from the robot-live page, GCS failsafe land at 2 s (the minimum; the earlier "about 1 s" was wrong).
- Corrections to the earlier entry: the A7Z is on the trunk roof saddle, not in the head; the back carries the battery backpack; SpeedyBee F405 V4 is ruled out (its ArduPilot build lacks optical flow); the tube over the trunk top is removed (the head hits it). Mount: the V1.39 back plate reprinted as a wing plate on the same 4 x M2 pattern, screws in shear.
- Numbers (`mass_budget.json`, `leg_load.py`, `pack_geometry.json`, `sweep_check.py`, `sweep_result.txt`): pack 730 g, total 1690 g; thrust-to-weight 2.25 on the vendor figure, 1.5 at two thirds of it; hover 53 to 97 s, 2.0 to 3.7 table round trips; COM 4.5 mm back and 7 mm up, heel margin 11 to 7 mm; single-support hip roll 33 % of the 0.96 N.m model limit (20 % today); forward-kinematics clearance: stand >= 23 mm, 1046 logged real bend rows >= 16 mm, pickup head scan >= 7 mm, legs at half joint range >= 2 mm; full-range leg poses and far-back head poses hit the pack (get-up with the pack does not work in this layout; head needs a software limit).

Evidence that would change the decision: one fan measuring under 634 g on 4S (683 g if the fan weighs 113 g); rear_pack screw posts too shallow for the wing plate (2.7 mm engagement recorded as unverified); a retrained policy that cannot walk at 1.69 kg.

Not established: real fan thrust, mass and housing size (vendor claims only, no independent test of this unit); XT30 current rating at 22 to 41 A per pack; yaw source (compass near 40 to 80 A leads); height hold across the table edge; A7Z spare UART (never enabled); walking, turning and bending with the pack (retraining not started, needs Shawn's nod); sit and kick poses; side-fall strength. No CAD, no DESIGN-CONTRACT entry, nothing ordered.

2026-11-10, Shawn on the single-fan bench gate: "不用 默认推力够". The design proceeds on the vendor thrust figure (950 g per fan); no separate fan bench test. The first tethered hover reads thrust from the hover throttle. The 634 g gate above is withdrawn; fan mass and housing size are still measured on arrival.

2026-11-10, Shawn on the detailed page: "现在这个设计 挡住了usb口还是其一，其二是你打算固定在saddle上是吧 ... 目前saddle是靠3M胶粘贴在侧壳上的，强度不够". Checked against `guide/print/world` STLs and `guide/content/fasteners.json`:
- He was right about the ports: the wing plate was drawn full width up to world z 182 at x -49..-45, straight behind the saddle rear window (y -29..26.5, world z 168..178) with the two USB-C sockets, the HDMI socket and the camera plug. Corrected: the plate centre is the present back plate (|y| 18.6, z 76..149.5), a cross beam to z 165 carries the wings, only the ends beyond |y| 37 rise to z 182.
- The pack does not mount on the saddle (taped, carries only the A7Z). Load chain is screws only: wing plate, 4 x M2 x 6 (DL-plate-01..04, 2.7 mm in 1.6 pilots) into rear_pack, 4 x M2 x 10 (S10-case-069/072, S05-case-074/076) into the ID5/ID10 hip-yaw cases, plus the two roof screws shell to pack bar. Hover load: about 4 N shear per plate screw and about 5 N pull-out on the top pair (thrust 34 mm ahead of the plate, rows 62.5 mm apart). Crash prying on these four screws is not assessed and is the weakest link.
- Saddle route, if wanted: the only screw points are the two roof holes (-21.5, +-20) into the pack bar (the D-022 V1 scheme); they sit under the A7Z board, which is why D-028 V3 went to tape. It needs a saddle redesign (board fitted after), not new shells.

2026-11-10, Shawn: "现在没装背板，是直接battery pack装在openRB盒子上的". The V1.39 Dual Lock back plate is printed but not fitted; recorded in `microduck-sim/CURRENT-STATE.json` (`backpack_swap_plugs`). For the jetpack: the wing plate is an added 3 mm layer between the OpenRB box and the battery backpack at the unfitted plate's position and hole pattern; the backpack moves 3 mm back and either shares the four post screws (M2 x 10) or goes on Dual Lock. The real backpack position equals the sim model (no 8.7 mm shift).

2026-11-10, Shawn chose "共用螺丝": the battery backpack and the wing plate share the four post screws. From `guide/print/rear-pack/build_rear_pack.py` (posts 5 mm deep, dia 1.6 pilots 4.8 deep) and `guide/print/back-plate/battery-backpack-20261015/build_bp.py` (2 mm front plate): M2 x 6 bites 4.0 mm today; with the wing plate the centre is 3.5 mm thick and the screws become M2 x 10 (bite 4.5 mm, 0.3 short of the pilot bottom). A 3 mm plate would bottom out with M2 x 10 and leave 3.0 mm with M2 x 8. Not checked on the robot.

2026-11-10, sourcing follow-up. Shawn: "XT60和线，robo club都有现成的，不用买" (pigtails removed from the Pyrodrone cart, $240.92); "一体板 ... 如果它就是最好的选择的话就它吧" (checked: not the better choice, the stack stays: the AIO listing contradicts itself on 35 A vs 45 A, 45 A leaves 1.3x over the fans' 34 A full-throttle claim against 1.6x for the 55 A stack, and twelve 16 AWG fan leads plus two battery leads would land on one 25 mm board, for $18); "指南针没用就删掉" (kept: ArduPilot's compass-less page gives Copter no yaw source without GPS, so optical-flow position hold needs a compass; the onboard one sits millimetres above the ESC current, B = mu0 I / 2 pi r is about 1 mT at 1 cm for 50 A against 0.05 mT for the Earth, so the external module away from the leads is the usable one; still to be proven on the bench). A wider fan-source search is running. Shawn also lifted the no-simulation limit for the next phase: "查完之后，定下来所有东西的尺寸和规格，就可以计算所有东西了，该跑仿真跑仿真". Training runs still need his nod on a shown plan.

2026-11-10, compass. Shawn: "但是我们有IMU和摄像头 室内飞行足够了吧", then "删掉". The external M10G-5883 module is out of the Pyrodrone cart (subtotal $219.93) and out of the design. ArduPilot's parameter list gives EK3_SRC1_YAW the values 0 None, 1 Compass, 2 GPS, 3 GPS with compass fallback, 6 ExternalNav, 8 GSF, so the plan is: the A7Z sends the BNO085 yaw as ExternalNav yaw (6), or no yaw source (0), with the FC's onboard QMC5883L as a third route. No bench evidence yet that flow velocity plus yaw-only ExternalNav, or yaw source None, arms and holds position in GUIDED; if all three fail the module can still be ordered (about a week).

2026-11-10, fan sourcing follow-up. Shawn asked for a US-stock fan and whether the ARESWEI unit is better than the QX. US stock with both rotations: only ARESWEI 50 mm 11-blade 4650KV 4S on Amazon (CW B0H4KJLR6P, CCW B0H4KSDT77, $39.99 each, four about $171 with tax, delivery about Nov 12 to 15). Its listing images carry a dimension drawing in inches rounded to 0.1 (so about +-1.3 mm): overall 3.3 in (84 mm, spinner to motor end), inlet lip OD 2.3 in (58 mm), duct OD 2.0 in (51 mm; the bullet text says "60mm outer duct", the listing contradicts itself), housing length 1.3 in (33 mm), motor OD 0.9 in (23 mm), rotor 1.9 in (48 to 49 mm), leads about 5.5 in with 3.5 mm bullets, two moulded mounting ears with one screw hole each (hole size and spacing not given), removable inlet ring. Claims: 980 g and 40 A at 4S, 520 g and 22 A at 3S, 77 g. Evidence of quality: 4.7 stars from 8 ratings, no review text on the saved pages, no independent test or forum thread found (web search 2026-11-10); the outline matches the generic 50 mm 11-blade family sold as Powerfun and FMS. QX QF2611 for comparison: maker drawing in mm (lip 63.0, duct 54.0, housing 39.08, motor 25.8, overall about 75.8), no ears, an established EDF maker sold through several shops. No evidence that either is the better built. Fan choice still open with Shawn.

2026-11-10, fan choice and order condition. Shawn accepted the QX recommendation ("行") and set the order condition: "那跑仿真吧 跑跑看 确实能跑起来 我们就下单 接线图指南 pin 线 这些都没问题了 我们就下单". Two background agents started: flight simulation (extensions/flight-20261110/sim/) and pin-level wiring (extensions/flight-20261110/wiring/). Nothing is ordered until both pass.

2026-11-10, walking with the pack is an order condition too. Shawn: "不仅要出飞行仿真 走路仿真也要做 会不会装上去就不会走路了". Added to the simulation agent's scope: today's robot policies with the pack as dead weight against the same cases without it (falls, speed, joint torque against servo limits, static COM margin), no training; a retraining plan would need his nod.

2026-11-10, thrust-assisted walking. Shawn: "理论上能不能通过这个背包 让鸭子走得更稳更快 飞奔 这个你也可以研究一下 因为也不必要非此即彼，背包可以半开，和走路同时使用的，对吗". Added to the simulation agent as a third part, not an order condition: literature note first (LEONARDO, Harpy, reduced-gravity gait), then zero-training rollouts of today's walking policy with constant weight offload, with a roll/pitch damping loop on differential thrust, and with a forward thrust component; battery minutes at each setting. My answer to him before results (reasoning, not evidence): partial thrust is possible because throttle is continuous; the expected gain is balance (thrust torque on the trunk does not depend on foot contact), pure weight offload alone lowers traction and step frequency so it does not by itself make walking faster; speed needs a forward thrust component or flight phases; cost is battery minutes and a policy that never saw thrust.

2026-11-10, flight pack CAD and wiring check returned. CAD (commit 0a940d32): eight printed parts, draft slices for H2S, X1C and Elegoo, not released (guide chapter and print gate pending); all-up mass 1887 g with real part masses (pack 927 g); wing root is the weak point at about 10 g side or fore-aft impact. Wiring (commit 6b58d3cc, extensions/flight-20261110/wiring/): netlist complete at pin level; ESC-to-FC lead is straight-through, MTF-01 on FC UART4, A7Z pins 14/16/18 (UART4) to FC UART1 with only ground shared; I checked the FC serial order, PWM pins and the default current scale 40.2 against the ArduPilot MicoAir743v2 hwdef. Two settings must change (BATT_AMP_PERVLT 78.43 for the 12.75 mV/A sensor; AM32 6 poles, KV 4000). Open: hover current estimated 52 to 106 A total (factor two between methods, no measurement), so XT60 loading is unknown until a tethered hover; QX bullet size and CW convention unpublished; stack box contents unknown; the A7Z spare UART has never been enabled and the board did not answer ssh today. Not in any cart: female bullets (2.0 and 3.5 mm), heat-shrink, one SH1.0 4-pin to Dupont lead, M3 nylon standoffs and nuts; RoboClub wire gauge (12 and 16 AWG silicone) unconfirmed. About 30 solder joints.

2026-11-10, first flight and walking simulation of the flight pack (commit f6f91a8a, extensions/flight-20261110/sim/out/results.json). With-pack mass 1896.7 g (duck 960.5 g estimated, never weighed; pack 936.2 g), COM moves 4 mm back and 5 mm up. Airborne: thrust-to-weight 2.08 at the vendor figure (950 g per fan at 16.2 V), hover throttle 72 %, hover current 50.3 A total, about 2.5 minutes of hover on 80 % of 2 x 1300 mAh; controller is an ArduPilot-style stand-in. Ground: with the pack as dead weight today's stand61 and walk61 fall in 18 of 18 runs (0.54 to 5.7 s), 0 of 6 without the pack; joint torque is not the limit (0.117 N.m against 0.538). Open-loop stand holds only at ankle trim -4 degrees (+-1 degree falls). After every landing the duck falls once the fans stop (11 to 12 s), so the full floor-table-floor task does not complete. Take-off drifts 0.30 to 0.62 m forward, cause not yet isolated (pitch moment arm about 36 mm); one take-off hit the table side. Throttle cut from 0.3 m: 2.44 m/s, 15.6 g vertical; table strike up to 10 g horizontal, the wing-root limit. Not yet run: airborne perturbation batch, thrust-assisted walking. Order condition not met; agent continues with the drift cause, perturbations, zero-training ground fixes and a training plan document for Shawn's approval.

2026-11-10, training go for the with-pack policies. Shawn: "我觉得你可以训一训看看 ... 反正我们Kaggle每周的时间还在，对吧？30个小时你慢慢训呗，你有一晚上的时间可以慢慢训一训，因为我们明早可以看一看效果". A training agent started (extensions/flight-20261110/train/): plan file and reward audit before launch, fine-tune stand and walk on the with-pack model (fans off, mass 1.7 to 2.1 kg, COM +-10 mm), Kaggle free GPU only, evaluation in the probe that failed, nothing deployed to the robot. My answer to his physics question: standing and walking with the pack break no hardware limit that the simulation shows (static joint torque 22 % of the servo limit, COM inside the foot), so that part is a policy problem; the flight part has one item that may be hardware (pitch authority from the fore-aft fan spacing, cause of the take-off drift still being isolated) and one that is unmeasured (real fan thrust).

2026-11-10, compute for the flight-pack work. Shawn approved Modal's free credit and parallel runs: "Modal上面这个月也有了一些新的30块钱免费额度，所以总共有50多块钱了，也是可以用的 ... 没关的东西，其实完全可以撒出去并行跑。Kaggle上也可以几个一起跑，Modal上也可以几个一起跑，Mac mini上能用就用". Training agent told: Modal allowed under a code-enforced 35 USD cap (70 % of the real balance if that is lower), no top-ups; independent runs go out concurrently on Kaggle, Modal and the Mac mini. Simulation agent told to fan its independent batches out on the Mac mini.

2026-11-10, qwinout checkout as it really is (read in Shawn's Chrome, guest checkout filled to the payment step, not paid). Shipping to Pittsburgh 15217: "Standard with tracking (10-15 Working days)" free, "Expedited (3-5 days)" 35 USD (the policy page had said 25 USD and a 3 USD tracked option). Total with expedited 135.00 USD, no tax line shown. Payment methods offered: PayPal and Bank Deposit only, no direct card field. Shawn says he has no US PayPal account. Fans are not ordered.

2026-11-10, ARESWEI provenance and size, second pass (Shawn doubted that only listing images exist). Found: Areswei is an RC jet brand; Turbines RC lists its "Robotech Veritech VF-1J" twin 50 mm EDF jet kit (449 USD, twin 40 A ESCs, one 4S pack), so the Amazon fan is that maker's own spare unit. Amazon listing fields: model HDS001, part number HDN001, sold by "XianTou Direct", shipped by Amazon, free returns until 2027-01-31, delivery Thursday Nov 12 (read in Shawn's Chrome 2026-11-10). No maker website, manual or mm drawing found (searches: brand name, VF-1J spare unit, HDS001, rcgroups; turbines-rc and the second ASIN B0HCHB2SQT refused curl). Size from pixel-scaling the listing's side-view drawing, two anchors give a 3 % spread: overall 81 to 84 mm, inlet lip OD 58 to 60 mm (text says 60), duct OD at the rear rim 53 to 54.5 mm, housing length 33.5 to 34.5 mm, motor can OD 25 to 26 mm, one moulded ear with a screw boss on each side. The printed inch labels (2.0 and 0.9 in) do not match the drawing's own proportions, so they are loose. In practice the same class as the QX (duct 54.0, motor 25.8, lip 63.0, housing 39.1), but not to clamp-fit accuracy: measure on arrival. Coupon on both ASINs: seller coupon "Save 10% on 涵道", shown as claimed in his account (4.00 USD off at checkout), expires 2026-11-23; terms say a one-time-use coupon applies to the lowest priced qualifying item only, and do not say whether this one is one-time, so the saving is between 4 and 16 USD and shows on the checkout page.

2026-11-10, fans changed to the Amazon ARESWEI unit. Shawn: "可以的，我已经加进了4个，你可以帮我把它清掉". qwinout cart cleared (read back 0 items). His Amazon cart held 4 CCW units; corrected to 2 CW (B0H4KJLR6P) + 2 CCW (B0H4KSDT77). Checkout review page read back, not placed: items 199.95 (four fans 159.96 + charger 39.99), coupon savings -16.00 (the 10 % coupon applies to all four in one order, so separate orders are not needed), tax 12.88, total 196.83 USD, delivery Thursday Nov 12. The capacitor line is in the cart but unticked. parts_flight_pack and procurement.json updated. CAD, wiring and simulation must switch to the ARESWEI envelope (4650KV, 11 blades, 980 g claimed, 3.5 mm bullets, screw ears); nacelle bore waits for calipers on arrival.

2026-11-10, fans ordered. Shawn: "下单了已经 反正可以退的 其他你继续推进把". Amazon order history read back: 2 x ARESWEI CCW + 2 x ARESWEI CW, order total 154.04 USD with tax, arriving Thursday Nov 12; the charger and the capacitor were not in the order and stay in the cart. parts_flight_pack updated to ordered. Still in carts, not ordered: Pyrodrone (stack, MTF-01, two batteries, straps, SH cable kit, 219.93 USD) and Amazon (charger 39.99, capacitors 6.99).

2026-11-10, flight sim second round (commit 8e98d55c, files in microduck-sim/extensions/flight-20261110/sim/out/; QX thrust point unless noted; simulation only, nothing measured on hardware). Take-off drift: cause is controller setup, not fan layout (pitch margin 3.42 at full thrust, 2.1 at 80 %, need 2; out/authority.json). Main cause is hover trim computed from the mass-report COM instead of the true COM in the start pose (1 mm COM error = 2.8 % hover thrust in pitch); second, the ground attitude target was the nose-down resting pitch; a slow thrust ramp tips the duck over. With calibrated trim, level target and a fast ramp drift is 0.10-0.12 m. Airborne perturbation batch from a 0.3 m hover: 228 of 261 runs land on the intended surface, 215 of 261 under the stricter bar (tilt under 35 deg, error under 0.15 m). Always fails: 70 % of vendor thrust, 50 ms sensor delay, 80 % thrust on the table descent, nose-heavy COM (+5, +10 mm) or a weak front fan on the climb. Needs at least 90 % of vendor thrust; same for ARESWEI. ARESWEI from the seller point (980 g, 40 A at 16.8 V): hover 59 A total, 2.1 min, take-off peak about 144 A total (39 A per ESC channel), one table round trip about 326 mAh, about 6 trips per charge; if the fans are 30 % less efficient hover is 86.5 A and 1.4 min; 60 % less puts one ESC channel at 62 A, over its 55 A rating. Ground: no zero-training option makes the duck stand with the pack (battery position, servo gains, thrust ramp-down, crouch all fall); hip pitch XL330 sits at its 0.538 N.m limit under 1.9 kg. Only fans at 40-50 % of weight with the attitude loop keep it up (1 of 10 falls standing 20 s at 40 %; about 17 A, 7 min on ARESWEI). Part C: thrust offload does not make walking faster (0.4 m/s falls 4 of 5 at 50 % offload) and is steadier only compared with the pack as dead weight; needs a policy trained with thrust in the loop. Open: real thrust, inlet loss, ground effect, ArduPilot tuning.

2026-11-10, Pyrodrone refund policy read from its site: returns within 30 days only for new, unused, unopened items; store credit by default unless a refund is requested first; buyer pays return shipping; promotional items final sale; 3 % fee on cancellations. Shawn's rule for today: buy what is returnable, wait on what is not. Capacitor: Shawn will look at RoboClub on 2026-11-11, not bought.

2026-11-10, flight pack small parts carted on Amazon (not ordered; all three show FREE refund/replacement until 2027-01-31). Amass 3.5 mm bullets, 20 pairs, B07CR81N69, 9.99 USD, Thu 11-12: the only 3.5 mm pack with a traceable rating (Amass GC3514 25 A continuous, 50 A max at resellers; the Amazon generic packs publish none). AvrestYPT 610 pcs M3 nylon kit, B0H25CJN5K, 9.99 USD, Thu 11-12: the only Amazon kit found whose lid chart holds both M3x8+6 male-female spacers and M3x8 screws (the common 260/620/640-piece kits stop at 6/10/15/20 mm and 6/12/20 mm screws). Minidodca Qwiic kit, B0D5VKR885, 8.88 USD, Wed 11-11: its 20 cm SH1.0-to-female-Dupont lead covers the 170 mm FC-to-A7Z run; the Pyrodrone SH kit tops out at 15 cm and would need a Dupont crimp. Ticked subtotal 28.86 USD. Not carted: heat-shrink (sourcing policy keeps it club-first), 12/16 AWG silicone wire (club, gauges unconfirmed), USB-C data cable (use one at hand). RoboClub INVENTORY lists 1000 uF and 3300 uF electrolytics in Cabinet D, voltage and ESR not recorded. Records: extensions/flight-20261110/procurement.json small_parts_2026_11_10, CURRENT-STATE.json parts_flight_pack.

2026-11-10, flight pack requirements from Shawn. (1) No caliper step: "你他妈的画的那些15项，图片里不都有了吗？还让我他妈量什么呀". Fan dimensions come from the listing drawing (3.3 / 2.3 / 2.0 / 1.3 / 0.9 inch, each rounded to 0.1 inch); the nacelle clamp is being changed to accept the whole rounding band, and the measurement sheet is deleted. (2) Strength: "还要考虑PLA的强度。如果PLA强度不够，是不是还要换其他材料？或者增加厚度，以及增加关节连接地方的支撑之类的，这个你能算吗". Strength check dispatched (hand calculations plus open-source finite-element runs, output in microduck-sim/extensions/flight-20261110/strength/); no result yet.

2026-11-10, flight pack strength check done (commit 4471412f, microduck-sim/extensions/flight-20261110/strength/README.md and results.json; hand calculations plus a coarse voxel finite-element model; geometry of commit 1b392541; calculation only, nothing tested physically). At a safety factor of 2 in PLA: wing-plate root fails (peak thrust x1.5 SF 1.1, 15.6 g landing 0.55, lift by one nacelle 0.69, 10 g fore-aft 0.33-0.45, 10 g sideways 0.51) because the fans sit ahead of the root and every vertical load also twists it; nacelle clamp fails at assembly (snug screw preload bends the 3.4 mm collar wall, SF 0.42); tray flange screws SF 1.2 at landing. A topple onto a nacelle end (131 N in the sim) breaks every load path (root SF 0.07-0.14); no section or material fixes that. Passing: tray deck, ear pockets, fan retention by clamp friction, post screws outside the topple. Biggest unknown: M2 pull-out strength in printed pilots (no published value). Agent's proposed root fix: PA-CF at 100 % infill plus a bonded 3 mm carbon rod; RoboClub stocks PLA only, so a carbon-spar concept that keeps PLA is being sized. Clamp wall, tray flange and lug fillet fixes sent to CAD; the wing root waits for Shawn's choice.

2026-11-10, flight pack strength: decision and rerun. Shawn chose M2 x 12 for the four shared post screws ("用 M2×12"); CAD commit 6fa0d176 (root band solid 8.5 mm, backpack back 3.4 mm, orange plate 100 % infill, inner tray flange raised with a third screw, pack 967.2 g). Sim recheck (d2de61ac): pitch margin 2.15 at 80 % thrust on the ARESWEI point, duck with pack 1915.6 g, COM x -12.6 mm, nominal hover and table up/down 3 of 3. Strength rerun (f9a4dc2e, voxel FEA, PLA): peak thrust x1.5 SF 3.1, lift by one nacelle 1.84, 15.6 g landing 1.37, 10 g fore-aft 1.28, 10 g sideways 1.51, topple 0.26; no geometry in the available space reaches 2; PA-CF would. Shawn's decision on the crash cases: "不用考虑极端情况。如果只是局部不够强，其实缠一些胶带也可以增加一些强度". So the wing plate stays PLA; crash and topple cases are no longer design gates; normal-use cases (thrust, handling) are. Local tape reinforcement at the root is allowed.

2026-11-11, flight pack print gate. Guide chapter written (microduck-sim/extensions/flight-20261110/guide/, 31 steps, commit f78a3548); first gate run failed on 24 cable penetrations (the duck's camera USB cable through the wing plate's left arm, new leads through boards and under the batteries); CAD commit 480610d1 re-routed every lead, opened the windows so finished XT60 leads pass, and changed the ten nacelle clamp screws to M2 x 12 for driver clearance (14 x M2 x 12 in total). Gate now: solids 155/155, pairs 0, cables 0, steps 0 in the flight chapter and 2 old chapter-12 bp-hatch collisions (failing since 9f9a09e0; the modelled hatch still has the V1.41 tongues and bumps while Shawn holds the real one with foam tape). Shawn: "记为例外放行": those two are an exception for this release only. Slices of the earlier geometry were renamed STALE-do-not-print; re-slice after the strength rerun on 480610d1.

2026-11-11, with-pack stand and walk training result (commit 647f5c34; microduck-sim/extensions/flight-20261110/train/out/results.json, RUNLOG.md; simulation only, nothing deployed). Chosen policy fq2 iteration 1999 (fine-tuned from walk61, round 3 with a hinge cost on joint torque above 0.45 N.m). Probe: as-built model with a 936 g pack, 7.6 V, 3.6 % dropped reads, policy from the first tick, 20 episodes x 20 s per case. With the pack, 14 cases: 3 falls in 280 episodes (old stand61/walk61: 279 of 280). Stand 0/20, walk 0/20 at 0.110 m/s (old walk61 without the pack 0.0915), turn left 0/20, turn right 1/20; mass +10 % and COM x +/-10 mm 0 falls standing and walking; 0.5 N.s shove 1/20 standing, 1/20 walking; landing hand-over 0/20 both. Walking joint torque p99 0.462 N.m of the 0.538 limit, 0.75 % of steps at or above 95 % of it. Without the pack this policy falls 5/20 walking, so the no-pack duck keeps the old policies. Finding for the robot: the runtime's open-loop stand mode falls in 0.54 s with the pack, so with the pack the policy must take over from the first tick. Spend: Modal metered 14.51 USD at 22:40 plus the tail of two runs, billed 0 (credits), cap 35; Kaggle 3.43 h of 30 h used; two from-scratch Kaggle runs end about 05:00. Not shown: servo softening at twice the load, real pack mass and COM (current CAD pack is about 996 g, inside the +10 % case), real landing.

2026-11-11, flight pack lug screws to M3. FlightPack-D1 slices (commit 821288b7) were verified (six files, 100 % infill, Textured PEI, gate RELEASED_WITH_EXCEPTION) but not printed. Shawn asked whether M2 holds ("M2的螺丝撑得住吗 如果撑不住的 M3 M4 M5其实roboclub也是有的"). From strength/README.md: post, tray and clamp screws pass in normal use; the six lug screws (nacelle inner half to arm web) are at SF 1.29 when the duck is lifted by one nacelle, on an unmeasured low pull-out estimate (120 N at 4.8 mm bite). Shawn: "改成 M3" for those six. CAD agent dispatched: contract first, M3 fits from print_fit.py, lug-case rerun, gate, re-slice; the 821288b7 delivery folder is renamed STALE until the new one exists. My estimate of about SF 1.9 with M3 is a diameter scaling, to be replaced by the rerun.

2026-11-11, flight pack M3 lug screws delivered (commit 5c258a93). Six lug screws are M3 x 12 (bite 6.8 mm; teardrop pilot 3.1, clearance 3.5 from print_fit.py; thinnest wall 2.45 mm). Pull-out is still an assumption: the M2 range scaled by pilot diameter x bite (x2.04), low value 245 N. Lug screws: lift by one nacelle SF 1.29 -> 2.64, peak thrust 2.81 -> 5.74; with M3 x 10 (bite 4.8) 1.86 / 4.05. Wing plate unchanged (lift 1.79 left, 1.73 right). Gate RELEASED_WITH_EXCEPTION (two bp-hatch records only). Slices verified by the coordinator: six files, 100 % infill, Textured PEI, thumbnails; Orange H2S 3h45m 117.6 g, Black H2S 8h36m 136.7 g. RoboClub inventory lists M3 screws and M3 x 10 but not M3 x 12: stock of that length unconfirmed.

2026-11-11, flight pack: toe-out, bend, head motion and flight clip findings (simulation only; train/out/style_bend_head.json, universal_audit.json, commit d11d05d9; sim/out/pack_visual/). Pack now drawn in the sim (visual geoms, results bit-identical; f536678f). Toe-out, 20 episodes: walk61 without pack stance foot yaw 7.3 deg left / 4.2 right, step width 94 mm; fq2 1999 with pack 21.3 / 22.2 deg, 119 mm; source is the hip yaw joints (-21 / +23 deg against -6 / +3); already present in fw1 before the torque cost; the pose reward tolerates it (hip yaw std 0.3 rad) and no term looks at foot heading. Head: standing scan (pitch 0.45 to 1.24, yaw +/-0.6) 0 falls with fq2 and fs1; walking with head pitch 0.5 and 1.1, 0 falls with fq2; quack not really executed in the probe. Bend (groundpick61 to phase 0.33, 4 s hold) with the pack: 20 of 20 fall about 0.6 s into the bend, trunk reaches 14 deg nose-down then goes over backwards, hip pitch torque at the 0.538 limit; the bend is a separate policy, so the universal stand/walk training does not fix it. Also: on the current 960 g no-pack model the bend falls 18 of 20 at the hand-back to stand61 (old default model 0 of 3), cause not yet found, real-robot evidence not yet compared. Universal plan written (train/UNIVERSAL-PLAN.md) but its incentive audit fails: standing still earns 0.821 of the walking reward with the pack (gate 0.80). Flight clip: the hover take-off and landing are fine (touchdown tilt 1.1 deg) and the duck falls after disarm because flight.py holds the legs open-loop instead of running the with-pack policy; joining the two is dispatched. No training launched.

2026-11-11, flight pack full sequence in one simulation (sim/ commits a45500a4, 53e67116; sim/out/fullseq_handover/, sim/README.md "Full sequence"; simulation only). The leg policy fq2 1999 is now run inside flight.py with a hand-over: policy stands, at estimated foot height 3 cm in the climb the legs go to the Brain stand pose, at 3 cm in the descent they go back to the policy; held-legs mode stays the default and reproduces the old rows. Full-sequence success (airborne success, never past 45 deg in the 5 s after disarm, feet on the wanted surface, no nacelle contact): ARESWEI nominal thrust 9 of 9 (hover, table up, table down, 3 seeds each); 90 % thrust airborne 9 of 9, full 6 of 9 (three end crouched and leaning on a nacelle, about 21 deg); 80 % thrust airborne 1 of 9, full 0 of 9. Cost of the moving legs at take-off: drift 0.45 to 0.62 m against 0.07 m held, pitch excursion about 20 deg; at 80 % thrust two table-up runs hit the table edge (held legs: 3 of 3). Policy running in the air with zero command is not usable (legs flail, 4 of 27 airborne). Assumes walk_wired.py gets the flight controller's range height over MAVLink in real time, a link that does not exist yet.

2026-11-11, flight pack bend statics (train/bend_statics.py, train/out/bend_statics.json, battery_room.json; gravity-only static torques, feet flat, COM at least 5 mm inside the support; a lower bound, dynamics not verified). Bending to the floor with the pack is inside the servo torque. Along the existing groundpick61 path (206 poses): full pack 1.916 kg hip pitch 0.283 / 0.239 N.m, knee 0.457 / 0.507, ankle 0.360 / 0.354; batteries out 1.614 kg hip 0.224, knee 0.416, ankle 0.303; no pack hip 0.202, knee 0.304. A straighter-knee, deeper-hip bend (mouth 2.9 cm off the floor, trunk 32 deg forward) needs hip 0.19, knee 0.24, ankle 0.09 at full pack, but leaves the COM about 9 mm from the support edge. So the 20 of 20 falls come from the bend policy never having seen the pack, not from torque: a training task (fine-tune groundpick61 with the pack), not a hardware block. Battery room in CAD: 1 mm forward, 1 mm down, effectively none; moving batteries forward would raise the knee torque anyway. One battery only (1.761 kg): feasible, not needed. No training launched.

2026-11-11, flight pack training plans ready, nothing launched (train/UNIVERSAL-PLAN.md, BEND-PLAN.md, rm_chosen.json, out/reward_design.json, out/audit2_chosen_*.json, out/handback_diff.json; commit 66b65c72). Reward redesign passes the incentive audit at full pack, batteries out and no pack (degenerate / walking reward at most 0.797, gate 0.80): command range narrowed to what the runtime sends (x -0.05..0.30, y +/-0.05, yaw +/-0.5), air time 3 to 6, velocity tracking 2 to 3, upright 2 to 0.5, head pose tracking 2 to 1, hip yaw std 0.30 to 0.15, new stance-foot-heading term weight -8. Accepted walking speed at least 0.15 m/s on the 0.25 command at every load (today fq2 with pack 0.105, walk61 no pack 0.090). Shawn's speed hypothesis for the toe-out ("肯定是没把移动速度考虑进去") checked: speed alone does not separate the splayed gait (fq2 0.100 m/s against walk61 0.057 in the training env, same tracking score); the foot-heading term does (0.50 against 0.10 per second). Bend plan: fine-tune groundpick61 and seepick61 on the payload env, Kaggle, about 3 h first run. No-pack hand-back falls in sim traced to the trunk_base mass update (+129 g, COM about 13 mm back and up, D-037 backpack and A7Z parts); the robot's 2026-11-06 logs show 5 of 5 hand-backs with the backpack standing (to walk mode, not stand61), so this is a sim-versus-robot difference still open. Quack head tilt with the pack: 0 falls of 20. Kaggle: 24.45 of 30 h left at 00:45 before the scratch pair's remaining hours.

2026-11-11, flight pack training go. Shawn saw both plans (universal stand/walk policy 0 to 1 kg with foot-heading and speed terms; bend fine-tune with the pack) and said "两个都跑". Scope: Kaggle free quota only, as written in train/UNIVERSAL-PLAN.md and train/BEND-PLAN.md; the bend launches only after its own incentive audit passes. Dispatched to the training agent; nothing deployed to the robot.

2026-11-11, flight pack training launch state (agent report, Kaggle; train/RUNLOG.md). Launch fault: the Kaggle kernel copied only top-level assets/ files, so start policies under assets/init/ were missing. Universal A (from fq2 1999) in kernel microduck-fk-uni-a exited at start on 04:03; only universal B (from walk61) trained there (expected end 10:45). The first bend push (05:46) errored 06:01 with FileNotFoundError for groundpick61.onnx. Fixed in the launcher kaggle_flight.py (init/ copy added to the generated kernel entry; shared kernel_entry.py untouched). Relaunched 06:04 as microduck-fk-uni-a2: GPU0 universal A as approved (fq2 1999, universal2, 5000 iterations, cap 10 h), GPU1 bend fk-bend-a2 (groundpick61, 2500 iterations or 3 h, one seed); expected end 12:50, latest 16:10. Bend reward changed before launch to bend3 = bend2 plus the runtime dwell (half the envs hold phase 0.33 for 4 s each cycle), because the training env held the low point only 0.2 s while the acceptance command in PICKUP.md holds 4 s; audit rerun with the dwell passes at all three loads (worst degenerate share 0.73, squat-and-stay at full pack; gate 0.80). Scratch reference pair ended 05:44 at the 10 h cap (iteration 7400): 20 of 20 stand and walk without falls at full pack, but walking speed 0.0001 m/s on the 0.25 command, so Pollen's recipe from scratch learned to stand, not to walk with the pack. Quota forecast about 24.3 of 30 h used, about 5.7 h left for seepick61. Not yet verified by me: kernel status and result files; acceptance runs after the pulls.

2026-11-11, flight pack: Shawn ordered the Pyrodrone cart (MicoAir 743 V2 stack, 2 x CNHL 1300 mAh 4S, MTF-01, SH1.0 cable kit, 2 straps; subtotal $219.93) with USPS Priority Mail, 2 business days; 11-11 is a postal holiday, so about Sat 11-14 to Mon 11-16. Amazon comparison done first (procurement-amazon-compare-20261111.json): same stack on Amazon $118.99 but arrives 11-24 to 12-04; no CNHL 1300 mAh 4S there (1500 mAh pack is 5 mm thicker, 23 g heavier, does not fit the trays); nothing eligible. Amazon small parts (SH-to-Dupont lead kit, 3.5 mm bullets, M3 nylon standoff kit, capacitor; charger separate) not ordered: he checks RoboClub today. Steel M3x12 lug screws: RoboClub, on his word. parts_flight_pack in microduck-sim/CURRENT-STATE.json updated.

2026-11-11, flight pack: what a move to bigger fans would touch (Shawn asked; desk check, no CAD, nothing bought). Vendor listings only, no independent tests: XFly 64 mm 12-blade 4S (2840 KV3200) 1250 g, 40 A, 135 g (cmldistribution.co.uk); FD/Powerfun-type 64 mm 11-blade 3500KV 4S 1460 g, 52 A, 874 W, 150 g (turbines-rc.com); QX 64 mm 2822 3500KV 1250 g at 67 A max continuous (racer.lt). Current design numbers from design_facts.py: 4 x 980 g vendor thrust, sim thrust-to-weight 1.96, hover 15 to 28 A per fan (60 to 112 A total), sim ESC channel peak 40 A against the 55 A ESC, sim pack peak 73 A against 2 x 1300 mAh 130C, one table trip 182 mAh of 2600. Reading: batteries are not the limit (current far inside the rating; capacity gives about 11 table trips in sim), so no bigger battery is needed for thrust; a 40 A class 64 mm fan keeps the 55 A ESC and FC, a 52 A one leaves almost no margin, a 67 A one needs a new ESC. Geometry: fan pitch front to rear is 64 mm and the fan lip is 58 to 60 mm, so a 64 mm fan (duct wider than 64) cannot keep the pitch: both nacelles and the wing plate arms change (both plates reprinted), width grows from 280 mm; head-scan clearance is only 1.5 mm today. Mass: about +58 g per fan, about +230 g plus larger nacelles, total about 2.15 to 2.2 kg from 1.92; with 4 x 1250 g the vendor thrust-to-weight goes from about 2.05 to about 2.3, a gain of about 12 %. Legs: the existing bend path is already at knee 0.507 N.m of the 0.538 limit at 1.916 kg (train/out/bend_statics.json), so +14 % mass exceeds it on that path (the straighter-knee bend at 0.24 keeps room); walking and bend policies retrain. Fan outer diameters for the 64 mm units were not found in the listings.

2026-11-11, flight pack: why the 80 % thrust flights fail in the simulation (Shawn: lift is enough, so why can't it fly). Cause is the sim's stand-in controller, not thrust or pitch authority: its thrust model assumes the vendor 980 g per fan, so at 80 % every commanded newton gives 0.8 N. After lift-off the altitude loop commands about 1.0 x weight, 0.85 x arrives, the duck sinks back onto the floor within a second while the climb integrator is still small, then skids on unloaded feet and tips; 1.5 of the 1.8 s mixer saturation comes after the floor re-contact, 0.04 s in the air. Test: one diagnostic flag (`flight.py --ctl-thrust-known`, controller told the real thrust, like a measured ArduPilot MOT_THST_HOVER): 80 % airborne 9 of 9 held legs and 9 of 9 with the leg hand-over (8 of 9 standing 5 s after disarm), against 1 of 9 published; nominal rows unchanged. With the thrust known, 70 % still flies (9 of 9), 60 % does not (thrust-to-weight 1.21). Real-pack consequence: the hover thrust fraction is 0.56 at vendor thrust and 0.75 at 80 %, above ArduPilot's MOT_THST_HOVER ceiling 0.6875 (parameter list; clamp in AP_MotorsMulticopter.h), so below about 85 % of vendor thrust the learned hover value saturates; the sim with the feed-forward capped that way still flies 9 of 9 at 80 %. Before free flight: measure thrust, set MOT_THST_HOVER from a tethered hover (CTUN.ThO), keep MOT_HOVER_LEARN at 2. The design page line "at 80 % only 1 gets airborne" reflects the controller artefact. Detail: microduck-sim/extensions/flight-20261110/sim/README.md, sim/out/t80_diag/.

2026-11-11, full-flow demo simulation for the final-project office hours (microduck-sim/guide/firmware/mac/fullflow_sim.py, fullflow-20261111/README.md; simulation only). One as-built MuJoCo run: name call ("Mochi!") with namecall.py's head-only glance up to the owner and a quack, the voice command "go find the orange ball", head-camera search with orange_target.detect, walk61 to the 12 mm ball, seepick61 pick (seepick rehearsal harness, 150 mA jaw), walk back and beak open at the owner's feet. Voice lines are timed triggers and the walks steer on sim truth. Four seeds: three delivered, picks held on 3 of 5 attempts (seed 0 is the 50 s demo video, seed 3 shows a miss and a retry). Finding: in this sim every pick that held lost the ball within 1.5 s of the hand-back to stand61 (neck swing 0.39 -> 0.11 rad; ball pinched at the beak tip, jaw reading 0.01 deg, where the robot held at 9.5 deg on 11-06); the 1.0 s sp_blend trial did not keep it. The video therefore pins the ball in the beak after a held pick and labels it "carry assisted". Carrying while walking has never been trained or tried on the robot.

2026-11-11, flight pack training: universal run B (fk-uni-b, from walk61, 5000 iterations on Kaggle, free) FAILS acceptance (train/out/accept_uni_b.json, accept_uni_b_best.json; reference accept_fq2_1999.json; 36 cases x 20 episodes on the Mac mini). With pack 92 falls of 280 (best checkpoint 83) against 1 for fq2 1999, all in walking cases; walk torque p99 0.54 N.m against the 0.48 limit; full load walk falls 17 of 20 between 5 and 10 s at 0.151 m/s with leg torque at the clamp 12 to 46 % of the time. No pack: 0 falls of 80, 0.231 m/s (fq2 0.163, 2 falls); mean toe-out now inside limits (8.8 / 2.3 deg), step width 117 mm still over 105. Loads 25 % pass, 50 % passes on the best checkpoint only, 75 % and no-battery fail. Head-down walking at full load falls 18 and 20 of 20. Reading: B learned a fast, narrow-toed gait that the servos cannot hold under the heavy loads; fq2 1999 stays the with-pack reference. Open: the no-pack speed band 0.082 to 0.15 contradicts the 0.15 m/s floor. Clips train/video/uni_b_walk_pack.mp4 (falls backward at 7.8 s) and uni_b_walk_nopack.mp4. Universal A and bend (kernel fk-uni-a2) still running. Nothing deployed to the robot.

2026-11-11 (late), flight pack training, second Kaggle batch (kernel fk-uni-a2, free): both runs FAIL acceptance; nothing deployed. Universal run A (fk-uni-a2, from fq2 1999, universal2, 5000 iterations; train/out/accept_uni_a.json): walks every load at 0.167 to 0.180 m/s, 0 falls standing and walking at 0, 25, 50, no-battery and full load, toe-out mean 5 to 8 deg and p95 at most 13.9 (limits met), no pack 0 falls of 80. Fails: 37 falls of 280 in the 14 with-pack cases against 1 for fq2 1999 (COM 10 mm forward: stand 5, walk 19, down in about 0.9 s with torque saturated from the first tick; 0.5 N.s shove while walking 11; mass +10 % walk 2), walk torque p99 0.53 against 0.48, 75 % load saturation 1.08 % against 1 %, step width 123 mm against 105 (no better than fq2), full-load head-down 1.1 walk 3 falls of 20. Best checkpoint worse (44 falls). Reading: best universal candidate so far, fixes toe-out and slow with-pack walking, but brittle to pack offset and pushes. Bend run (fk-bend-a2, from groundpick61, bend3, stopped by the 3 h cap at iteration 1900; accept_bend_bend_a2.json): learned a squat, not a bend: knee at the joint limit (median 1.575 rad of 1.571; original 0.58 to 0.63), trunk pitch 13 to 16 deg against 25 to 45, knee torque p99 0.538 (clamp) at all loads; runtime no-fall 2 / 19 / 4 of 20 at full / no-battery / no pack, every fall 0.8 to 1.8 s after hand-back to the fq2 stand policy at 10.5 s. D-027 asks for a bend, not a squat, so this is a reward-design miss, not a tuning miss. Acceptance ran on the Mac mini and waited about 8 h behind another session's fullflow sim. Clips: train/video/uni_a_walk_pack.mp4, uni_a_walk_nopack.mp4, bend_a2_bend_pack.mp4 (seed 0 does not fall; 18 of 20 do). accept_universal.py lost two redundant speed lines (0.099, 0.07) covered by the 0.15 floor.

2026-11-12, flight pack training, next round planned and audited, NOT launched (microduck-sim/extensions/flight-20261110/train/NEXT-PLAN.md, commit 14d3a424; microduck_rl 871b007c). Causes: run A's COM failure is a coverage gap (1.2 % of full-pack resets reached +10 mm whole-robot; statically 0.161 N m, out/plan_statics.json); bend3 paid the squat 1.72x the bend at batteries out. universal3 (from run A final): whole-robot COM x U(-12, 12) mm at every load, pushes +-0.35 m/s, step-width cost above 100 mm, torque hinge -20, capped progress-along-command reward 8 (stepping in place earned 0.843 of the walk without it). bend4 (from the original groundpick61): trunk-pitch band 25-45 deg cost, knee beyond 1.25 rad cost, stand pose at rest, in-episode hand-back to the stander in a quarter of cycles, bend guard on knee/pitch/falls. Incentive audits PASS at full / batteries out / no pack for both (out/audit_gate.json, checked 11-12). Hand-back baseline with every cycle handing back: stander falls 13.4 / 9.5 / 3.1 per minute after groundpick61's bend. Open: sim ankle stop 1.36 rad against the robot's about 1.25 (model change, undecided). Shawn 11-12: "好，出来了就启动训练". Not launched: Kaggle GPU quota 2.66 h left of 30 at 05:28 EST (another session's microduck-play-a is running), the paired run needs about 3.6 h, refresh 2026-11-14T00:00 (no zone printed). Waiting on Shawn's choice of compute (Kaggle after refresh, or Modal under the 35 USD cap).

2026-11-12 11:50 EST, flight pack training launched on Kaggle (free): kernel shawnxiang9527/microduck-fk-uni3, jobs fk-uni3 (universal3 from run A) and fk-bend4 (bend4 from groundpick61), paired on two GPUs, RUNNING. Settings as NEXT-PLAN.md except the time cap: 2.2 h instead of 3.5 h, because the quota still read 2.66 h at 11:43 (microduck-play-a had completed) and those hours lapse at the 11-14 refresh; checkpoints every 250 iterations, 2000 iterations will not be reached. This is a first segment for early evidence on the reward changes, not the full planned run; whether a full-length rerun is needed after the refresh is decided from its acceptance. Nothing deployed to the robot.

2026-11-12, flight pack training: where the Kaggle week went (Shawn asked why 27 h gave no accepted policy; from train/RUNLOG.md quota readings). Of 27.34 h used, this work took about 24.5 h, other sessions (play-smoke, play-a) about 2.9 h. (1) 10.2 h: from-scratch pair fk-scratch-s1/s2, launched blind with a 10 h cap and no task-metric stop; it learned to stand and ignore the walk command (0.001 m/s), reference only. (2) 6.7 h: kernel fk-uni-a ran only run B (from walk61, FAIL); run A died at start on a missing init file (kernel entry did not copy assets/init), so A needed a second session. (3) 0.25 h: fk-bend-a, same missing file. (4) 6.9 h: fk-uni-a2 = run A (FAIL, best candidate) + bend3 (FAIL, squat). (5) 0.4 h smokes. Process causes: runs of 5 to 10 h whose failure showed only after the end (Kaggle log blind until the kernel ends, no task-metric stop on the scratch and bend3 runs); incentive audits priced only the degenerate policies listed (stand, step in place), not the squat, which bend3 paid 1.72x the bend; the training randomization was not checked against the acceptance cases (COM +10 mm reached in 1.2 % of resets); a launch bug not caught because the smoke used a different start file. Not established: whether a single-frame actor can meet the universal COM/shove lines at all. Correction to the 11-12 chat line 'no usable policy': fq2 1999 (Modal, 11-10) walks with the full pack in sim with 1 fall of 280 but misses the later requirements (0.109 m/s under the 0.15 floor, toe-out about 21 deg, no-pack 2 falls); no checkpoint passes the current acceptance.

2026-11-12, flight pack training, next plan direction (Shawn): the universal policy plan must use the teacher-student distillation taught in 16-831 (his words: "方案里把课上讲的师生蒸馏用上"; lecture 6 privileged information and DAgger, lecture 11 teacher-student and asymmetric critic). Until now only PPO and an asymmetric critic from that course were used; three plans postponed the history input the literature (RMA) names for payload. A background agent is writing microduck-sim/extensions/flight-20261110/train/HISTORY-PLAN.md (no training launched); Shawn reads the plan before any run ("方案出来了给我看"). The Kaggle run fk-uni3/fk-bend4 will be read only on the failing cases (COM +10 mm, walking shove), not the full 36-case acceptance. kaggle_flight.py now refuses a run push without a task-metric stop (microduck_rl 9abdc5c0).

2026-11-12, flight pack: history-input plan written, nothing launched (microduck-sim/extensions/flight-20261110/train/HISTORY-PLAN.md, robotics 699bb70c, microduck_rl 2159120e). Finding that corrects the 11-12 chat explanation: the comx+10 failure of run A is not an observability problem. fq2 1999, also one frame, holds comx+10 with 0 falls of 40 (eval/ua_fq2_1999_comx+10_*.json, rechecked), and a linear probe reads forward COM from one frame at 0.1 s (R2 0.61); payload mass is not readable from one frame (R2 about 0) and is from 0.5 s of history (0.47). So run A lost a robustness fq2 had; history is a candidate for the mass-dependent lines (torque, 75 % load saturation) and the shove. Plan: decision rule on the universal3 checkpoints (comx+10 and walking shove only); if history is needed, design B = the 16-831 teacher-student recipe (lecture 6 p13, lecture 11 p32-33, slides rechecked): PPO teacher seeing payload kg, loaded COM and trunk velocity, then a DAgger student seeing the 61 inputs plus 25 past frames (0.5 s) of 48 values, 1261 inputs; the teacher is the gate (if it still falls, stop). Student observation, two-input ONNX (obs 61 unchanged + state), warm start and evaluator are built and smoke-tested on the Mac mini; the teacher delta, the distillation worker, the walk_brain change (about 15 to 20 lines) and the A7Z timing are not done. RMA Table II numbers rechecked on arxiv (62.4 randomization only, 73.5 RMA, 76.2 expert). Waiting for Shawn's read of the plan.

2026-11-12 13:05, flight pack history plan, review fixes (outside review passed on by Shawn; robotics 712e183e, a8d4a506, 58ef4f52; microduck_rl d0820622; Mac mini CPU only, no training). (1) Probe redone with the same 61 current inputs with and without the 25-frame history, per-env time since reset, 1024 envs, 256 held out (out/history_probe.json): whole-robot COM x readout RMSE 3.8 mm from 61 inputs against 3.3 mm with history (pooled, target spread 6.8 mm); at offsets of +8 mm or more both underestimate (bias -3.5 against -2.6 mm); payload 266 g against 205 g (spread 290 g). A linear readout only: it does not show what the policy uses or whether 2 to 4 mm suffices, so coverage against information for comx+10 stays open; fq2 holding comx+10 on one frame is an existence proof only. (2) The 3-iteration smoke fall: with the real launch settings (100 warm-up iterations, lr 3e-4) the history actor falls 4 of 4 after 3 PPO iterations, the one-frame actor 1 of 4, history columns frozen 0 of 4, history columns' step scaled by 0.04 0 of 4, lr 1e-5 0 of 4 (eval/fallcheck_*.json, rechecked; 64 envs, 4 episodes, one seed). Cause: Adam moves the 1200 zero-initialised history weights at the full rate. A history run needs a separate step scale for those columns (not added), and the first checkpoint after warm-up is evaluated against the start policy before a run continues. (3) accept_universal.py now has one fall line per with-pack scenario; the 14-case sum is information only. Plan changes: the teacher is a gate on distilling that teacher, not a bound; design A with a fixed budget against a one-frame control comes before B; 20 episodes is a screen (fall-rate bound about 14 %), picks are rerun at 100 on unused seeds. A7Z loop figure 23.6 ms was the closed head on 10-22; the current installation is unmeasured for the two-input ONNX.

2026-11-12 13:20, flight pack history plan, second outside review (passed on by Shawn), all four points accepted. accept_universal.py now has two seed sets: dev (seeds 0-19, ua_* files) for picking, final (seeds 1000-1099, 100 episodes, uaf_* files, out/accept_<dir>_final.json) for the verdict; score rejects a file whose seeds or count do not match (tested on uni_a: dev verdict unchanged, final all missing, a 100-episode request on dev files refused). Corrections: the 279 against 14 weight-change totals are not evidence of an abnormal update (1200 against 61 columns is 19.7, the change ratio 19.3); what the fall check supports is the intervention (freezing or scaling the history columns removes the fall), and 0.04 is a candidate scale, not shown to let the history branch learn. A better design A shows the whole change helps, not that the past is used: a picked checkpoint gets a repeated-current-frame evaluation. Decision rule: stop at A if it meets acceptance; torque and step width no longer exclude history in advance. Budget per run: A = history + one-frame control (about 3 h quota paired, 6 GPU h), B teachers two runs (about 3 h paired) + student 1 to 1.5 h; first history kernel stops at iteration 250 with saves at 110/125/150/200.

2026-11-12 15:00, flight pack training, Kaggle kernel fk-uni3 result (free quota; both jobs hit the 2.2 h cap at iteration 1500 of 2000; no guard fired). universal3 FAILS and is worse than its start (run A): dev seeds, 20 episodes, falls for comx+10 stand / comx+10 walk / walking shove / mass+10 walk / nominal walk / no-pack walk: run A 5 / 19 / 11 / 2 / 0 / 0; it 250 13 / 20 / 12 / 2 / 1 / 0; it 500 0 / 20 / 20 / 20 / 19 / 12; it 750 1 / 20 / 20 / 19 / 20 / 18; it 1000 11 / 20 / 20 / 20 / 20 / 20; it 1250 0 / 20 / 20 / 19 / 19 / 7; it 1500 0 / 20 / 20 / 20 / 20 / 12 (eval/ua_uni3_*.json; best = it 250). Torque p99 at the 0.54 clamp from it 500 on; upright speeds 0.21 to 0.35 m/s on the 0.25 command (run A 0.167 to 0.188), no-pack 0.34 at it 500. Reading: between 250 and 500 the policy sped up and lost the with-pack walk; the new progress-along-command reward (weight 8) paid for speed the servos cannot hold under load. In the training env the speed on moving commands rose 0.123 to 0.219 m/s and the tracking error fell 0.237 to 0.193, so the track guard read it as improvement while episode length fell 782 to 697 and reward 88 to 55. Misses: the incentive audit priced only lazy policies (stand, step in place, lean), not an over-fast one; the stop metric had no fall or episode-length term. The run does not answer coverage against information for comx+10 (confounded by the collapse); only comx+10 standing improved (5 to 0 falls at 1250 and 1500). bend4 training-env guard windows: hold knee 0.78 to 1.17 rad, trunk pitch 21 then 29 to 31 deg, mouth 1.6 to 2.4 cm, hand-back falls per stander-minute 21.4 to 2.3; acceptance running on the Mac mini. Nothing deployed.

2026-11-12 15:05, flight pack bend4 acceptance (fk-bend4, iteration 1500 of 2000, from groundpick61; out/accept_bend_bend4.json; reference bend_gp61ref; Mac mini): verdict FAIL, closest so far. Runtime sim, PICKUP command, rise and hand-back to the fq2 stander included: 20 of 20 without a fall at full, batteries out and no pack (original groundpick61 0 of 20 at each; bend3 2 / 19 / 4). Torque p99 runtime: hip pitch 0.39 / 0.35 / 0.28, ankle 0.34 / 0.32 / 0.22 (limit 0.50, pass); knee 0.538 / 0.524 / 0.415 (fails with the pack). Posture in the training env at the hold: knee 1.18 / 1.17 / 1.15 rad (original 0.58 to 0.63, bend3 squat 1.575), trunk pitch median 27.9 / 27.8 / 27.1 deg with one held episode per load outside 25 to 45 (the line requires every episode), mouth median 2.4 / 2.2 / 2.2 cm, within 3 cm in 17 of 20, 17 of 17, 17 of 18 held episodes. Training-env falls 3 / 5 / 7 of 20 against 0 in the runtime sim: the two sims disagree here too. One clip (seed 0, full pack, video/bend4_bend_pack.mp4): ankle 0.89 rad at the lowest point, under the robot's 1.25 rad stop; other seeds not checked for the ankle. Reading: a bend with deeply bent knees (between the original bend and the squat), stable through the hand-back in the runtime sim; fails on knee torque with the pack and on the every-episode posture lines. Nothing deployed.

### 2026-11-12 16:15 Flight pack: pickup measured with the pack, the seeing pick falls 20 of 20 (FP-R7)

Shawn rejected bend4 ("捡不起东西了 不能接受"); recorded as FP-R7 in `microduck-sim/extensions/flight-20261110/REQUIREMENTS.json`.
The bend acceptance had no pickup measure (mouth within 3 cm was the stand-in), so the pickup was measured with the policy
that picks on the robot, seepick61, in the runtime sim (`style_eval.py --case stand --extra='--stand-s 0 --walk-at 1 --walk-s 0
--wired-guards --sp-at 4 --sp-cone elliptic --sp-impratio 10 --sp-shape ball --sp-size 0.012'`, 20 seeds, results `train/eval/pk_*.json`).

- No pack, original stander: ball held at the hand-back 11 of 20 (5 still held 3 s later), box 14 (12), no falls.
- No pack, fq2 stander: ball 15 (12), box 16 (16), 1 fall.
- Batteries out, and full pack: 0 of 20 held, 20 of 20 falls (tilt guard over 55 deg), ball and box alike.

Reading: bend4 was fine-tuned from groundpick61, the blind bend with no item in its inputs; it is not the pickup policy.
The pickup with the pack needs seepick61 trained with the pack, accepted by "held" counts per load. Not started; needs
Shawn's nod and Kaggle quota (refresh 2026-11-14T00:00). Mac mini ssh hung twice after the remote job had finished
(result file written, no remote process); the hung client was killed and the script went on.

### 2026-11-12 16:40 Flight pack: plan for the pickup with the pack (seepick61 fine-tune), shown to Shawn, NOT launched

Shawn: "可以，出方案" (to: train the policy that really picks, accept by held counts). Correction to the 16:15 entry:
BEND-PLAN.md (approved 11-11) already had groundpick61 first and seepick61 second and recorded the seeing pick's
20 of 20 falls with the pack; the defect was the order and a bend acceptance without a pickup measure, not an unknown.
How it fails with the pack (`train/eval/pk_bend4_{load100,nobatt}_ball.json`): falls about 1 s after the switch, at phase
0.155 of the descent, lips still 4 to 8 cm up, hip pitch and knee at the 0.538 N m clamp, mostly backward or sideways.
Plan: fine-tune seepick61 (sp-b-1027_2000) in its own env (`microduck_rl-grasp`, `cmu_seeing_pick_env_cfg.py`) with
one change, the pack load drawn per episode (none, batteries out, full); actor inputs and reward unchanged; stop and
acceptance on held counts per load; pre-launch checks without quota (start policy in the training env against the
runtime-sim numbers, reward audit at the pack loads, Mac mini smoke). Launch needs Shawn's nod and the 11-14 quota.

### 2026-11-12 17:05 Flight pack: Shawn allows Modal for the pickup fine-tune

Shawn: "没必要等吧 你看看不是浪费时间就上modal上去跑 或者看看有没有其他羊毛可以薅". Reading: the seepick61-with-pack
fine-tune may launch on Modal once the pre-launch checks show it is worth running; the 35 USD project cap stays.
Modal this month: 17.57 USD metered (`modal billing report --for "this month" --json`, 61 app rows, full days only;
nothing ran on Modal today), no live apps, no alert mail (`modal_watch.py` clean). Credits were covering all usage
(billed 0.00 on 11-11); the Credits tab could not be read today (Chrome is signed out of modal.com). Other free compute
checked: Kaggle quota is used up until the 11-14 refresh; no other free GPU is set up on Shawn's accounts.

### 2026-11-12 17:25 Compute: AWS credit to be used for training; free-compute search dispatched

Shawn: "其他能薅的要你派agents出去搜和找啊" and "哦对 我们有150元的aws额度 不用也是浪费". Two search agents are out (public
free-GPU offers; CMU resources plus credits already in his mail, course files and past sessions). AWS, read-only check
with the `default` CLI profile in us-east-1: on-demand G and VT quota 16 vCPUs, G spot quota 8 vCPUs, P quota 0; one
instance exists, i-0229118871664e9a9 (g5.4xlarge, c3-carla, stopped), which belongs to the 24-784 session and is not
ours to touch (it needs the whole on-demand quota when running, so training uses the spot quota). Month-to-date net
cost reads 0.00 USD (Cost Explorer); the credit balance itself is not readable from the CLI and was not verified.
An agent is building `extensions/flight-20261110/train/aws_train.py` (spot GPU, self-terminating, S3 checkpoints,
dollar cap) with a smoke of at most 1 USD; no training launched on AWS.

### 2026-11-12 19:10 Compute: Modal balance read, AWS credit source, 16-831 follow-up drafted

- Modal Credits tab (signed in with the CMU Google account at Shawn's word, 2026-11-12): 36.61 USD of credit left in
  total = 24.22 of the 500 USD Nova hackathon grant (expires 2026-11-30) + 12.40 of this month's 30 USD plan credit.
  `modal billing summary`: metered 17.60 this month, credits -17.60, billed 0.00. Usage limit and spend limit 85 USD.
- The 150 USD AWS credit is the 24-784 course credit (second batch, sent to AWS 2026-11-06; Cost Explorer shows credit
  records from 11-07). It shares the account with the Challenge 3 machine (due 11-28); anything beyond it bills the card.
- 16-831 AWS project credit: late request 9-15, Prof. Shi 9-16 "I can try but no guarantee", nothing since. Follow-up
  drafted in the same thread in the CMU mailbox (draft only, not sent), asking whether AWS's Free-plan skip that hit
  24-784 also hit the 16-831 credits.
- Free-compute search (two agents): nothing usable today beats AWS + Modal; large pools (Chameleon, ACCESS Jetstream2,
  Bridges-2) need a faculty lead and 1 to 14 days.

### 2026-11-12 20:05 Compute: AWS spot launcher built and smoke-tested (no training run)

- `microduck-sim/extensions/flight-20261110/train/aws_train.py` (guide `AWS.md` beside it) runs any worker command on
  one g5.xlarge spot instance (A10G; g4dn as capacity fallback) that terminates itself at command end and at a
  wall-clock limit computed from the dollar cap and the current spot price. Outputs go to the Mac mini every minute
  over SSH, not S3: the CLI user has no S3 write or IAM role permissions, so the instance holds no credentials.
- Measured: 2.4 s per PPO iteration at 4096 envs (flight worker, packwalk), setup 2-8 min, so 1000 iterations cost about
  $0.40 against about $0.95 on Modal A10. Resume, fetch, stop, both self-termination paths and the leftover sweep
  passed; the smoke cost about $0.24 and nothing is left running.
- Spot capacity is intermittent: two of five launch commands found none in any zone at first.

### 2026-11-12 20:16 Flight pack: seepick61-with-pack fine-tune prepared and checked, not launched (FP-R7)

Built in `microduck-sim/microduck_rl-grasp` (branch cmu/grasp, commit 7fc17f36): task
`Mjlab-SeeingPick-Pack-FromPick-MicroDuck-CMU-Current`, the seeing-pick env with one change, a pack load drawn on
trunk_base at every reset (none 0.30, batteries out 0.30, full 0.40; mass and COM from the flight env's `payload.py`
and manifests, imported). Robot model flightpack-none (the pack is defined against it; sp-b-1027 trained on the
retired "plugged" model, kept for comparison). Actor inputs and rewards unchanged. Start = sp-b-1027 `model_2500.pt`
(its actor is the robot's seepick61.onnx; the grasp worktree's `sp-b-1027_2000.onnx` is a byte copy from the old export
bug) with its critic: the payload (kg, COM x y z) is appended to the critic's 93 inputs with zero weights, the actor is
frozen for 50 iterations while the critic learns the pack, curricula held at the checkpoint's step counter.
Pre-launch checks, all on the Mac mini (`microduck-sim/extensions/flight-20261110/train/out/spk_prelaunch_summary.json`):
- The env reproduces the runtime-sim result. seepick61, 256 episodes per load: no pack 191 held (75 %), 15 falls;
  batteries out 2 held, 254 falls; full 1 held, 253 falls (median fall 0.7 to 0.8 s). On the old plugged model: no
  pack 200 held, 4 falls; full 1 held, 251 falls. Runtime sim (FP-R7, 20 seeds): no pack 11 to 16 of 20 held, 0 to 1
  falls; both pack loads 0 of 20 held, 20 of 20 falls.
- Reward audit (reward per second, 128 episodes). No pack: seepick61 19.3 (a successful hold 22.6), stand61 2.4, fq2
  standing 0.75, blind bow (groundpick61) 0.03. Batteries out: seepick61 0.28, fq2 1.04, stand61 -2.6, blind -3.0,
  seepick61 with the pack weight carried by an upward force 7.7 (35 held, 62 falls; a successful hold 18.8). Full:
  seepick61 -0.22, fq2 1.43, stand61 -3.2, blind -2.7, carried 4.6 (22 held; hold 15.3). So at the pack loads standing
  still (fq2) out-earns seepick61 as it is, by about 1 to 1.6 per second, while a hold earns 15 to 19 per second, about
  ten times standing. Inference, not measured: the actor does not see the load and a third of episodes have no pack,
  where bowing earns 19 per second, so giving up the bow costs more than it gains unless the actor learns to tell the
  load from its own joints.
- Contradictions to the plan: the training env lets hip pitch and knee reach 0.641 N m (p99 in every case) while the
  runtime sim clamps at 0.538, so the fine-tune can learn torque the runtime will not give; the runtime-sim acceptance
  (`train/accept_seepick.py`) catches it but the env does not. Even with the weight carried, seepick61 still falls in
  half the pack episodes, so the pack's COM and inertia matter beyond its weight.
- Modal path (`cmu/grasp/seepick_pack_modal.py`): L4, detached spawn, one Volume per run with the trainer logs on it,
  2 retries that resume from the newest checkpoint, checkpoint and ONNX every 100, stop at iteration 300 if held_full
  and held_nobatt were never above zero, dollar cap from L4 + 4 cores + 16 GiB (1.117 USD/h, default 6 USD), import
  check and Warp kernel compile at image build. Smoke spk-smoke-1112c (4096 envs, exact configuration, 180 s): started,
  logged per-load keys, wrote model_0 to model_5 on the Volume, exported ONNX as they appeared; 8.4 s per iteration.
  The first smoke reached no iteration: Warp compiled CUDA kernels for over 100 s on a cold container (292 s at image
  build), hence the compile step in the image. The L4 took about 20 minutes to schedule. Modal spend today 0.18 USD,
  no live app, `modal_watch.py` clean. Resume tested on the mini (CPU): a second call resumed from model_3 at
  iteration 3, kept the warm-up count and summed both attempts' time.
- Estimate for 1000 iterations: Modal L4 about 2.4 h, about 2.7 USD (worst case 3.9 USD at SPK_HOURS 3.5); Kaggle T4
  about 3.5 h at sp-b-1027's 12.75 s per iteration. A stop at iteration 300 costs about 0.8 USD on Modal.
- Launch (not run): from microduck_rl-grasp, `SPK_RUN=spk1 SPK_HOURS=3.5 MICRODUCK_GPU=L4
  ~/code/robotics/omx-local/.venv/bin/modal run --detach cmu/grasp/seepick_pack_modal.py::run --max-dollars 6`;
  fetch `modal volume get microduck-seepick-spk1 runs/spk1 <dir>`; recipe in `cmu/grasp/PLAN-seeing-pickup.md`.
- Tests: 14 new CPU tests pass; the existing seeing-pick test file passes 3 of 3 reruns after one failure of its
  camera-position test (0.051 m against 0.04, object 1.5 m away; the env fixture has no fixed seed).

### 2026-11-12 21:25 Flight pack: pickup-with-pack fine-tune spk1 launched on Modal (FP-R7)

Go: Shawn 2026-11-12 "你看看不是浪费时间就上modal上去跑". Pre-launch gate passed: the training env reproduces the
runtime sim (seepick61, 256 episodes per load, after the torque fix: no pack 190 held / 10 falls, batteries out 1 / 254,
full 0 / 253; runtime sim 11-16 of 20 held without the pack, 0 of 20 with it). Torque ceiling: the training env ran the
bam default 1.75 A (0.641 N m) against the runtime sim's 1.47 A (0.538 N m); the pack task now uses 1.47 A and 7.2-8.2 V
(`microduck_rl-grasp` 28dd49d0). The robot itself logged up to 2.06 A in position mode (11-02..11-06 tick logs), so both
sims are below the robot; the flight walking env has the same 1.75 A vs 0.538 mismatch (not changed yet).
Launch 20:59 EST from `microduck_rl-grasp` 28dd49d0: `SPK_RUN=spk1 SPK_HOURS=3.5 MICRODUCK_GPU=L4 modal run --detach
cmu/grasp/seepick_pack_modal.py::run --max-dollars 6`; app ap-R4vLTDvI2CuzYOLzy4C3sv, call
fc-01M79BDGQMRCVA03PN2BNZGGXT, args read back: 4096 envs, 1000 iterations, save every 100, seed 1, check at 300 on the
pack-load held keys, cap 3.5 h = 3.91 USD (6 USD argument), start sp-b-1027 model_2500.pt (actor = seepick61).
Image build about 20 min; at 21:25 the app is detached with no task yet (waiting for an L4). Modal credit before
the run 36.61 USD. Watch: scratchpad spk_wait.sh (checkpoint, stop or alert mail).

### 2026-11-12 21:40 Flight pack: reward audit on the 1.47 A pack env still pays the hold (FP-R7)

Rerun of the hold-reward audit (seepick_prelaunch.sh nonebase, Mac mini, 128 episodes per case) on the env spk1 trains
in (1.47 A, 7.2-8.2 V). Reward per second, 1.47 A (1.75 A before):
- No pack: seepick61 19.38 (19.27), its successes 22.69; stand61 2.04 (2.43), fq2 0.95 (0.75), blind bow 0.44 (0.03).
- Batteries out: carried hold 7.49 (7.70; 34 held, 64 falls; successes 18.11), fq2 1.35 (1.04), seepick61 0.30, stand61
  -2.97, blind -2.91.
- Full pack: carried hold 4.44 (4.59; 22 held, 79 falls; successes 14.73), fq2 1.83 (1.43), seepick61 -0.15, stand61
  -2.97, blind -2.57.
A held pick still pays 8 to 13 times the best degenerate policy (fq2 standing still) at every load, so the lower
ceiling did not change the incentive. Every leg-pitch p99 sits at the 0.538 N m clamp at both pack loads, as in the
runtime sim. Outputs: extensions/flight-20261110/train/out/spk_audit_*.json and spk_prelaunch_summary.json (the two
plugged start cases are still the 1.75 A run); the 1.75 A results are kept in out/i175/.

### 2026-11-12 22:20 Flight pack: spk1 stopped at iteration 325, no learning on the pack loads (FP-R7)

Stopped by hand (`modal app stop -y ap-R4vLTDvI2CuzYOLzy4C3sv`), `modal_watch.py` afterwards: 0 live apps, 0 alert
mails. Cost 0.92 USD (2976 s on L4, about 9.1 s per iteration at 4096 envs). Volume `microduck-seepick-spk1`.
Curve, 50-iteration means of the training log (with exploration noise): held without pack 0.33, 0.35, 0.32, 0.31,
0.31, 0.33, 0.34; held batteries out 0.0035, 0.0053, 0.0026, 0.0023, 0.0031, 0.0034, 0.0038; held full 0.0028,
0.0038, 0.0018, 0.0012, 0.0014, 0.0011, 0.0012; fell batteries out 0.926 -> 0.991; fell full 0.883 -> 0.987.
The falls got more frequent, not fewer. Iteration-100 acceptance (dev seeds, fq2 stander, `train/eval/spa_spk1_100_*`):
no pack ball 4/20 held (start policy 15/20), box 13/20; batteries out and full 0/20 held, 20/20 falls about 0.7 s
after the switch, leg torque p99 0.38-0.49 N m (below the 0.538 clamp).
Where the start policy breaks (seepick61, fq2 stander, ball, 20 seeds, runtime sim, `train/eval/pk_bend4_load0*_ball.json`):
25 % load (0.239 kg) 0 held, 18 falls, 17 to the right, 1.0-1.6 s after the switch; 50 % 0 held, 20 falls; 75 % 0 held,
20 falls. At 25 % the legs are not torque-limited (clamp fraction 1-2 % per joint, 0.4 % without the pack), the pack's
added mass sits 3 mm right of centre and its fans at y = +-0.11 m add roll inertia: the fall is the unchanged bend
motion meeting a different body, not a strength limit.
Reading:
1. The jump from no pack to 0.65 kg gave PPO almost no successes to learn from (0.2-0.5 % by chance), while the cliff
   is below 0.24 kg. The load has to grow from zero in small steps.
2. The rising fall rate fits an early-fall incentive: at full load the start policy earns -0.15 per second and
   standing with stand61 -2.97, so an episode that ends early by falling can cost less than one that stays up without
   picking. The pre-launch audit compared do-nothing policies and never priced "fall early". Next audit prices it.
3. The in-run stop ("pack success never above zero by iteration 300") could not fire because chance successes exist
   from the start (check_best 0.0112). The next stop is on the curriculum level reached.
Published recipe this follows: automatic curricula that widen a randomized physical parameter only while the success
rate at the edge holds (automatic domain randomization, OpenAI 2019, arXiv 1910.07113; the terrain-level curriculum
in Rudin et al. 2021, arXiv 2109.11978).

### 2026-11-13 00:55 Flight pack: spk2 (load-scale curriculum) built and checked, not launched (FP-R7)

Task `Mjlab-SeeingPick-PackCurriculum-FromPick-MicroDuck-CMU-Current` (microduck_rl-grasp commit 01caed31): the
spk1 pack env (1.47 A, 7.2-8.2 V, same start and critic) with the load as a share s of the full pack, every pack part's
mass and inertia x s at its own position (make_payload_manifests.py's scaling; at s = 0.25 the payload pseudo-inertia
equals flightpack-load025's pack parts, a test). 25 % of episodes at s = 0, the rest U[0, s_max].
Start-policy cliff (seepick61 in the training env, kicks and distractors off, 256 episodes per s, Mac mini CPU, held at
the episode end, its ratio to s = 0, successes, falls, median fall time):
s 0.00 (0 kg) 172/256 = 0.672, 1.00, 191, 27, 1.32 s; s 0.02 (0.019 kg) 171 = 0.668, 0.994, 179, 33, 1.40 s;
s 0.05 (0.048 kg) 160 = 0.625, 0.93, 172, 38, 1.44 s; s 0.10 (0.096 kg) 141 = 0.551, 0.82, 146, 55, 1.12 s;
s 0.15 (0.143 kg) 111 = 0.434, 0.645, 113, 95, 1.18 s; s 0.20 (0.191 kg) 96 = 0.375, 0.558, 99, 119, 1.08 s.
On the L4 (seed 1): s 0.50 seepick61 falls 236/256; s 1.00 held 1, falls 253. Three of four leg-pitch joints at the
0.538 N m clamp at p99 from s = 0; the right knee reaches it from s = 0.05.
s = 0 against the pinned no-pack load (spk1's path): 172 held, 27 falls (Mac mini, seeds 1-8, 32 envs) and 181, 10
(spk1 start check, same seeds) against 184, 16 on the L4 (seed 1). The model fields after reset match (trunk mass
identical, trunk COM offsets uniform within +-3 mm: std 1.68/1.70/1.86 mm against 1.79/1.70/1.78 mm over 256 envs, total
mass 0.9663 +- 0.0105 against 0.9666 +- 0.0104 kg); the scale path takes extra random draws at startup, so the episodes
differ. The spread is between draws, not a changed load.
Chosen: s_start 0.08, step 0.01 (9.6 g; about 0.026 of the ratio between 0.10 and 0.20, about one standard error of a
decision window of about 900 top-slice episodes), FRAC 0.8 (above the start policy at 0.15, just below it at 0.10; its
0.06-0.08 slice holds about 0.9), top slice s >= 0.75 s_max, a decision every 10 iterations with at least 300 top and
200 no-pack episodes.
Fall-early audit (full-episode returns in seeing_pack_check.py's units; fall at 0.7 s = seepick61's mean return
accumulated by 0.7 s; stand still = fq2 stander episodes that did not fall; held pick = seepick61 successes, carried
seepick61 at s 1.0): s 0.00 4.35 / 12.68 / 87.05; 0.02 4.28 / 13.38 / 89.55; 0.05 4.17 / 13.24 / 87.17; 0.10 3.98 /
12.16 / 86.94; 0.15 3.79 / 12.31 / 86.65; 0.20 3.59 / 13.72 / 84.12; 0.50 2.45 / 13.22 / 76.06; 1.00 1.55 / 12.91 /
61.17. The start policy's own return falls from 73.2 (s 0) to 39.9 (0.20), 4.6 (0.50) and 0.24 (1.00). Falling early
never beats standing still, so no penalty: SPK2_FALL_PENALTY = 0 and the after audit equals the before one. The
early_end term was checked anyway: at fall_penalty 10 every fallen episode gets exactly -10.0, every other episode 0
(s 0.20, L4). spk1's reading 2 (an early-fall incentive) is refuted for these loads; at full load the start policy
earns less than standing (0.24 against 12.9), which the curriculum keeps out of reach until the lighter loads are held.
In-run stops: `[spk-stop] no rise` when s_max is still 0.08 at iteration 100 (the start policy passes the first
decisions; 100 iterations are about 15 min and 0.28 USD on the L4 at 9.1 s per iteration); `[spk-stop] no-pack loss`
when the s = 0 held rate over 50 iterations is below 0.7 x its mean over iterations 0-49. model_best.pt by s_max, ties
by top-slice held; checkpoints every 100. Launch: Modal L4 1300 iterations, 4 USD ceiling in code (worker cap 3.5 h,
3.91 USD), or AWS spot through aws_train.py; commands in microduck_rl-grasp/cmu/grasp/PLAN-seeing-pickup.md.
Checks and where they ran: tests 29 passed (Mac mini, 10 s); cliff s 0-0.20 Mac mini, 22:25-23:45 (s 0.05-0.20 as two
8 x 16-env waves each; 32-env parts hit the 590 s cap at load 29); fall-early audit runs, early_end check and control
on a Modal L4 (one process, 424 s of runs, 17 min waiting for an L4); curriculum smoke Mac mini 00:27-00:40 (64 envs,
CPU): s_max 0.10 -> 0.13 in three forced decisions, the resume restored s_max 0.13 with rises 3 and went on to 0.14,
and the forced case stopped with "in-run stop: no rise: s_max 0.100 still at its start 0.100 at iteration 2 (limit 2;
last ratio 0.00, need 2.0)" in the run record. Modal billed 0.224 USD for the checks (spk2chk-a 0.006 + 0.116 with the
image build, spk2chk-b 0.102; `modal billing report`), 0 live apps after. The first check call failed (policies not in
the image, 0.12 USD) and a build was stopped by another session's edit in the worktree; the Modal image is now built
from a snapshot of the worktree.

### 2026-11-13 01:10 Flight pack: load-curriculum run spk2 launched on Modal (FP-R7)

Pre-launch checks read back from `train/out/spk2_prelaunch_summary.json` (entry 00:55): start policy held at end per
256 episodes 172 / 171 / 160 / 141 / 111 / 96 at load scale 0 / 0.02 / 0.05 / 0.10 / 0.15 / 0.20; falling at 0.7 s
earns 1.6-4.4 per episode against 12-14 for standing still and 61-90 for a held pick at every scale, so no fall
penalty was added. Go: Shawn's standing word for this run (2026-11-12 "你看看不是浪费时间就上modal上去跑").
Launch 00:56 EST from `microduck_rl-grasp` 01caed31: `SPK_TASK=curriculum SPK_RUN=spk2 SPK_HOURS=3.5 MICRODUCK_GPU=L4
modal run --detach cmu/grasp/seepick_pack_modal.py::run --max-iters 1300 --max-dollars 4`; app
ap-gXXVrmMeQb1BGugd2jM3WE, call fc-01M79R680J8XEBGYR4VVAJRWCE, Volume microduck-seepick-spk2; args read back: 4096
envs, 1300 iterations, save every 100, seed 1, cap 3.5 h = 3.91 USD; image carries SPK_TASK=curriculum. Curriculum:
25 % of envs without pack, the rest uniform in [0, s_max], s_max from 0.08 in steps of 0.01 when the top slice holds
0.8 of the no-pack rate over 10 iterations. In-run stops: s_max still 0.08 at iteration 100; no-pack held below 0.7 of
its first-50-iteration mean. At 01:08 the app is detached and waiting for an L4. Modal spend so far today: spk1 1.02
USD, spk2 checks 0.24 USD. Watch: scratchpad spk2_wait.sh.

### 2026-11-13 01:45 Flight pack: spk2 is learning, s_max 0.08 -> 0.14 by iteration 110 (FP-R7)

First iteration about 01:18 EST (about 20 min wait for an L4). At iteration 111: 0.357 USD at iteration ~100, about
9.5 s per iteration. Curriculum decisions every 10 iterations: s_max 0.08, 0.09 (it 20), 0.10 (50), 0.11 (70), 0.12
(80), 0.13 (90), 0.14 (110); 6 rises in 11 decisions; ratio at the decisions 0.71-0.88 against the 0.8 needed.
Per-slice rates with exploration noise, iteration 10 -> 110: no pack held 0.37 -> 0.42, fell 0.27 -> 0.14; scale
0-0.05 held 0.34 -> 0.38, fell 0.35 -> 0.15; scale 0.05-0.10 held 0.26 -> 0.36, fell 0.45 -> 0.21; scale 0.10-0.20
(from iteration 80) held 0.20 -> 0.33, fell 0.43 -> 0.27. No-pack 50-iteration mean 0.381 against reference 0.348,
so neither in-run stop is near. Unlike spk1 the fall rate drops at every load.
Defect: the worker exported only the iteration-0 ONNX to the run folder; model_100.pt and the trainer's own ONNX are
in runs/spk2/logs/rsl_rl/seeing_pick_pack_curriculum/2026-11-13_06-17-42_spk2/. The trainer's ONNX fetched at 01:38
(differs from the iteration-0 file, max weight difference 0.11; only iterations 0 and 100 had been saved) is staged
as train/ckpt/spk2_100/seepick61.onnx with the fq2 stander; runtime-sim pickup test (ball, no pack and 25 % load)
running on the Mac mini.

### 2026-11-13 01:50 Flight pack: early spk2 policy stops falling but lands the beak 2 cm right in the runtime sim (FP-R7)

Runtime-sim pickup test (12 mm ball, 20 dev seeds, fq2 stander) of the trainer's ONNX fetched 01:38 (saved between
iteration 100 and 130; staged as train/ckpt/spk2_100, passive_mouth dropped from its metadata, graph untouched):
- No pack: 5 held (1 still held 3 s later), 0 falls. Start policy: 15 held (12), 1 fall.
- 25 % load: 6 held (4), 1 fall. Start policy: 0 held, 18 falls.
Where it misses: pad at close in the switch-time root frame, mean y -0.0191 m (start policy -0.0058); object minus pad
mean [0.001, 0.020] m, sd 5 mm, so a steady offset, not scatter; the policy's item slots read y 0.003 at close. At
25 % load the offset is [0.004, 0.034], sd [0.015, 0.038]. Control with the original stander before the pick: 5 held,
0 falls, so the stander is not the cause. spk1 iteration 100 had no offset (y -0.0057) but 12 mm scatter and 4 held.
Reading: the fine-tune removed the falls (the balance part works) but the body ends about 2 cm right of the item and
the item estimate does not show it; the training env counts these as held more often than the runtime sim does
(training held at s = 0 rose 0.37 -> 0.42 over the same iterations). Cause not found yet; diagnosis dispatched
(same policy in the training env with the same probe, then the sim differences one at a time). spk2 keeps running
(0.40 USD at iteration 130): its balance gain is real and later checkpoints are needed to see whether the offset grows.

### 2026-11-13 02:15 Flight pack: spk2 at iteration 310 holds 9 of 20 at 25 % load in the runtime sim (FP-R7)

Training: s_max 0.08 -> 0.30 by iteration 310 (21 rises by 290), no-pack held 50-iteration mean 0.39-0.41 against
reference 0.348, 0.96 USD at iteration 326, about 9.5 s per iteration. Runtime-sim pickup test of the trainer's ONNX
saved at iteration 310 (train/ckpt/spk2_320, fq2 stander, ball, 20 dev seeds):
- No pack: 4 held (1 at end), 3 falls. Start policy 15 held.
- 25 % load (0.239 kg): 9 held (8 at end), 0 falls. Start policy 0 held, 18 falls; the 01:38 file 6 held.
- 50 % load (0.478 kg, above s_max): 0 held, 12 falls. Start policy 0 held, 20 falls.
The 2 cm lateral offset of the 01:38 file is gone: object minus pad at close [0.003, 0.006] without pack and
[0.004, 0.004] at 25 %, like the start policy's [0.007, 0.006]. Open: without the pack the fine-tuned policy holds
4-5 of 20 in the runtime sim while training reports the s = 0 held rate rising; it does better at 25 % than at zero.
Diagnosis continues with the agent (same policy in the training env at s = 0, body at s = 0 against the runtime
"none" manifest, failure stage of the no-pack episodes).

### 2026-11-13 03:00 Flight pack: spk2 at iteration 590 balances to 50 % load, the pinch is what fails (FP-R7)

Training: s_max 0.51 at iteration 590 (43 rises), no-pack held 50-iteration mean 0.43 against reference 0.348, 1.76
USD at iteration 601. Runtime-sim pickup test of the trainer's ONNX saved at iteration 590 (train/ckpt/spk2_600, fq2
stander, ball, 20 dev seeds), held (still held 3 s later) / falls:
- No pack 2 (0) / 0; 25 % load 5 (3) / 0; 50 % load 6 (3) / 1; 75 % load 1 (1) / 10.
Start policy: 15 (12) / 1, then 0 held with 18, 20 and 20 falls. So the falls are gone up to 50 % load.
Stage counts without pack: beak contact 20, pinched 3, holding bit 2, held 2 (start policy 20, 16, 11, 15); the lower
jaw touches first in 5 of 20 (start policy 0). Beak position at close is like the start policy's (object minus pad
[0.006, 0.003], lip_min 0.0003, pad height 0.020, tilt 46 deg). The no-pack held count fell with training (5, 4, 2 at
about iteration 120, 310, 590) while training's own s = 0 held rate rose 0.37 -> 0.43: the fine-tune drifts to a
pinch that works in the training env's beak-ball contact and not in the runtime sim's. Diagnosis with the agent now
targets the contact and jaw model difference and the head/jaw actions in the close window. spk2 keeps running for
the balance result (how far s_max goes at the 0.538 N m ceiling).

### 2026-11-13 03:35 Flight pack: the training jaw closes twice as fast as the runtime XL330, and spk2 lifts on that timing (FP-R7)

Diagnosis of why spk2 picks better in the training env and worse in the runtime sim. Compute: Mac mini CPU probes, and
Modal L4 (2 calls of 12 and 13 probes, billed 0.108 USD; spk2 app untouched).
Cause, with the runtime traces of bend4 (start) and spk2_600 on seeds 0, 2, 3, 5 and 7 (bend4 held, spk2 missed):
- The jaw is scripted the same in both sims (open 0.02-0.10, close ramp 0.34-0.40). Jaw angle at phase 0.36 / 0.38 /
  0.40 / 0.42: training mouth 18.4 / 9.2 / 0.2 / -1.9 deg; runtime XL330 20.2 / 17.4 / 11.1 / 3.5 deg.
- Mean lip height (lip_up, jaw_tip_bottom) at the same phases: spk2_600 lifts at the same time in both sims (training
  1.2 / 2.8 / 9.6 / 32.2 mm, runtime 1.9 / 2.7 / 9.7 / 29.9 mm). The runtime start policy stays down until 0.40
  (0.0 / 1.8 / 2.9 / 20.3 mm); the same policy in training lifts early (7.5 / 5.7 / 8.6 / 27.1 mm).
- Per seed, lip 8 mm above its minimum at phase 0.395-0.405 with the jaw at 9.5-13.1 deg for spk2 (no pinch in any of
  the 5), and at 0.405-0.415 with the jaw at 7.2-10.3 deg for bend4 (pinched at 0.400-0.405 in all 5).
- So spk2 lifts while the slow runtime jaw is still open, and the ball stays behind; the training jaw is closed by
  then. The start policy's runtime success rests on its lift being late in the runtime sim, a margin the fine-tune
  removed. The training reward pays the lift from phase 0.37 (grasp_lift phase_start = close_start + 0.03).
Matched jaw in training (iteration-590 ONNX, s = 0, ball, 16 envs, mouth kp 0.55 N m/rad, effort 0.0549 N m), by
mouth damping: 0.03 -> 14/16 held, jaw 5.9 deg at 0.40; 0.06 -> 10/16, 8.1 deg; 0.10 -> 4/16, 10.6 deg (runtime
11.1). The start policy at damping 0.10: 4/16, jaw 11.1 deg at 0.40. Default mouth: spk2_600 27/32, start 22/32;
kp and effort alone (damping 0.01): spk2_600 22/32, jaw 5.8 deg at 0.40, too fast, which is why the earlier
runtime-mouth test (256 envs: start 203 -> 195, p320 229 -> 219) did not separate the policies.
Ruled out, with numbers:
- Contact solver is the same: the pack env reads elliptic, impratio 10, timestep 0.005 (cfg readback).
- Beak friction: runtime beak mu 0.01 in training cost both policies 3-5 %; training mouth in the runtime (beak 1.5,
  1500 mA jaw) left spk2_320 at 15 of 20 contact-no-pinch.
- Body: runtime "none" manifest and training s = 0 both 0.96045 kg, COM within 0.22 mm.
- Head, neck and jaw actions in the close window: neck pitch differs by at most 0.30 rad (0.38-0.42), head pitch,
  yaw and roll by at most 0.12, 0.08 and 0.11 rad before phase 0.42.
- Lateral: spk2_600 starts the pick with a larger trunk yaw transient after the stand61 switch (ball bearing -12.2
  deg at phase 0.05 against -5.4, gyro z peak 3.1 against 1.8 rad/s) and arrives with the ball -3.9 deg off against
  +1.2. Training: trunk yaw at close +2.5 deg (spk2_600) and -2.7 deg (start), object minus pad y -0.001 and 0.009 m.
  Feeding the runtime's stand61 last action into the first observation changed nothing (spk2_600 57/64, start 54/64).
- Earlier (02:00-02:50): goal clamp, floor mu 0.5, window 0.03, observation delay 1 did not reproduce the gap; action
  delay 1 broke both policies.
Proposal (not launched): make the training mouth match the runtime jaw's timeline (stiffness 0.55, effort 0.0549,
damping 0.10, checked by the probe's jaw angle at phase 0.38-0.42 against 17.4 / 11.1 / 3.5 deg). Both policies fail
under it (4/16), so the close must be re-learned; freezing the start policy's head and jaw would keep a lift timing
that already fails in the training env with the matched jaw. Worker fix: grasp_worker.py exports each checkpoint
once its size is unchanged across two 30 s polls and copies model_best.pt live; the mini smoke exported model_4
51 s after it was saved, before model_6 existed. 16-env samples: about plus or minus 2 envs each.

### 2026-11-13 04:05 Flight pack: spk3 built and checked, NOT launched (FP-R7)

spk3 = spk2's curriculum with the training jaw matched to the runtime jaw, no reward change (grasp_lift start stays at
phase 0.37). Code in `microduck-sim/microduck_rl-grasp` (branch cmu/grasp, commit 64dd5fdc): task
`Mjlab-SeeingPick-PackSpk3-FromPick-MicroDuck-CMU-Current` (spk2's task unchanged), runner SeeingPickPackSpk3Runner,
tests `tests/test_cmu_seeing_pick_pack_spk3.py` (38 passed with the spk2 and pack cfg tests, Mac mini). Checks: one
Modal L4 call `microduck-spk3chk-a` (17 jobs, 552 s in the container; ledger 0.226 USD counting the 5 min L4 queue,
cap 0.50), smoke and runtime-sim check on the Mac mini. spk2 untouched (iteration about 900 at 04:00).

Runtime jaw, read from the runtime code and `microduck-sim/CURRENT-STATE.json`: XL330 BAM m6 at jaw kP 200, Goal Current
150 mA (`jaw_grip_current_ma`), 7.6 V: torque ceiling min(7.6 kt/R, 0.150 kt) = 0.0549 N m, BAM static stiffness
4.33 N m/rad (the code comment's 0.55 is wrong), armature 0.0018. spk3 mouth: stiffness 0.55, effort 0.0549, damping 0.10
(a fit to the runtime timeline, not the BAM stiffness).

Jaw angle (deg, mean of 256 envs, s = 0, ball) at phase 0.36 / 0.38 / 0.40 / 0.42 / 0.45; runtime 20.2 / 17.4 / 11.1 / 3.5:
- spk3 mouth, seepick61: 20.1 / 17.0 / 11.6 / 6.6 / 2.1 (minus runtime -0.1 / -0.4 / +0.5 / +3.1). spk2 model_best:
  19.9 / 17.1 / 11.7 / 6.7 / 2.3. Within 0.5 deg at 0.40, so damping stays 0.10; at 0.42 it lags 3 deg (end of close).
- spk2's fast mouth, spk2 model_best: 18.0 / 11.0 / 0.0 / -2.2 / -1.3.
- kP 4.33 (BAM), effort 0.0549, damping 0.04, seepick61: 18.5 / 14.1 / 6.9 / 0.6 / -1.3 (4.2 deg fast at 0.40).
- Held at the end in that probe (check placement): seepick61 63/256 matched against 170/256 at kP 4.33; spk2 best
  84/256 matched against 225/256 fast.

Floor (no-pack held at the episode end, training placement: window 0.04, kicks, distractors; 256 envs, s = 0):
- seepick61, fast jaw: noise 76/256 = 0.297 (spk2's in-run reference with the same policy and jaw: 0.348, so the in-run
  measure reads x1.17), deterministic 0.551.
- seepick61, matched jaw: noise 0.141, deterministic 0.199.
- spk2 model_best (iteration 860, s_max 0.69), fast jaw: noise 0.340, deterministic 0.605.
- spk2 model_best, matched jaw: noise 0.148, deterministic 0.301.
Floor 0.25 (in-run units, 0.21 in check units): halfway between broken (0.14-0.15) and working (0.30); 0.72 of the
working in-run 0.348. s_start 0.08, step 0.01, frac 0.8 as spk2.

Stops: no-pack held 50-iteration mean below 0.25 at iteration 400. Allowance: 50 critic warm-up iterations (actor
frozen) + 50 to fill the window, then the start (about 0.17 in-run) must gain 0.08; spk2 gained 0.05 per 100
iterations after its warm-up (0.353 at 50, 0.402 at 150), so 160-200 iterations, allowed 300 (1.5 x 200). Second stop:
after the floor was first reached, that mean below 0.7 x its own best 50-iteration mean. model_best = highest s_max
among checkpoints taken while the 50-iteration mean is at or above the floor.

Start policy (spk2 model_best, matched jaw, check placement, deterministic, 256 episodes), held at end / success / falls:
s = 0: 89 (0.348) / 94 / 3; s = 0.10: 108 / 115 / 1; s = 0.25: 122 (0.477) / 132 / 3; s = 0.50: 135 (0.527) / 142 / 8;
s = 1.00: 80 / 84 / 89. It still balances to s = 0.5; the pinch is the deficit, and the start holds more with load than
without it, as spk2 did.

Degenerate-policy audit under the matched jaw (episode returns; fall at 0.7 s / fq2 stander standing still (not fallen,
n) / held pick from the start policy's successes):
- s = 0: 4.93 / 13.06 (199) / 92.29; s = 0.10: 4.85 / 12.16 (211) / 91.62; s = 0.25: 4.67 / 14.11 (215) / 90.60;
  s = 0.50: 4.34 / 13.87 (232) / 88.60; s = 1.00: 3.03 / 14.01 (210) / 73.88.
- Falling early never beats standing still, and a held pick beats both by 5 x or more at every s.

Smoke (Mac mini CPU, 64 envs, start = spk2 model_best through SEEPICK_PACK_INIT; init line: actor + critic from the file,
md5 1c4bff00..., iteration 860, critic 97 -> 97 as saved, common_step_counter 80688):
- A, ratio always passes (frac 0) and floor 1.1: 3 decisions, 3 "rise blocked by the floor", s_max stays 0.080.
  Live export: model_2.onnx written 03:52:22, model_4.pt 03:53:53, model_4.onnx 03:53:59 (each about 6 s after its
  checkpoint, while the run went on). A hit the 290 s smoke timeout at iteration 5 of 8 (about 48 s per CPU iteration),
  so it wrote no run record; the stop path is covered by B and the tests.
- B, floor 0: s_max 0.08 -> 0.09 -> 0.10, model_best at iterations 1 and 2, exports 0, 2, 3 and best, exit 0.
- Runtime sim, smoke iteration-4 ONNX copied unchanged into train/ckpt/spk3_smoke4 (fq2 stander), style_eval 2 episodes
  (ball, the FP-R7 pickup flags): loads as it is, 0 falls, held at the hand-back 2 of 2, at the end 1 of 2.

Open: with the matched jaw the training env holds less than the runtime sim with the same policy and jaw settings
(seepick61 deterministic 63/256 = 0.25 in the probe against 15 of 20 in the runtime sim with the fq2 stander), so the
matched mouth makes the training env harder than the runtime, not equal to it; the next runtime-sim checkpoint tests
will show whether spk3's training rate carries over.

Launch (after spk2 has ended; the launcher refuses while microduck-seepick-spk2 has a live app), from microduck_rl-grasp:

    SPK_TASK=spk3 SPK_RUN=spk3 SPK_HOURS=3.5 SPK_INIT=microduck-seepick-spk2:runs/spk2/model_best.pt MICRODUCK_GPU=L4 \
      ~/code/robotics/omx-local/.venv/bin/modal run --detach cmu/grasp/seepick_pack_modal.py::run --max-iters 1300 --max-dollars 4

Rate 1.117 USD/h (L4 + 4 cores + 16 GiB), cap min(3.5 h, 4 / 1.117) = 3.5 h = 3.91 USD over all attempts; the spk3
task's ceiling in code is 4 USD. Nothing deployed.

## 2026-11-13 16:00 Right hip ID3 and ID4 silent at boot; in-place 57600 rescue does not work; jaw ID15 left at 57600 by the test

After a boot on the 2S pack (7.8 V) the bus scan answers 13/15: ID3 and ID4 silent, Shawn sees one red light on the right leg. Brain 39 Hz from the sync-read timeouts, so the remote greys the policy buttons (same signature as 11-02 ID2). Cause not established; whether the pack ran flat before is not checked. With ID1-3 unplugged and ID4 alone on the chain, `pi/rescue_factory_servo.py --id 4 --unplugged 1 2 3` (new flag) failed 3 tries, and a 96-combination timing sweep (bit clock +-2 %, 17-20 frames, idle gaps, phase) failed too. Control test: jaw ID15 set to 57600 with a normal 1 Mbaud write (it went silent as expected), then 72 drawings of "baud = 1 M" to ID15 (bit clock +-1.5 %, 17-19 frames, edge shift 0/3/5/7 us, phase): it never came back. So a 57600 waveform drawn with 1 Mbaud bytes through openrb_dual_host does not reach an XL330; the tool cannot work, and ID4's silence says nothing yet about ID4. State now: ID3, ID4 silent (unknown settings), ID15 at 57600 with ID 15 and its other settings intact, torque off, brain stopped. Fix needs a real 57600 transmitter: the spare OpenRB on the Mac (`mac/restore_factory_servo.py`), or A7Z UART0 TX (header pin 8, /dev/ttyAS0, now the serial console) wired to the bus data line with a broadcast write (untested). Also this turn: `tailscale set --ssh` on the A7Z made the Mac mini remote's ssh wait for a browser check; turned off again.

### 2026-11-13 16:45 Flight pack: spk2 finished (s_max 0.86), spk3 with the runtime jaw launched (FP-R7)

spk2 ended at its 3.5 h cap, iteration 1296, 3.81 USD: s_max 0.86 (78 rises), no-pack held 50-iteration mean 0.44;
training slices at the end: s 0.50-0.75 held 0.35 fell 0.19, s 0.75-1.0 held 0.31 fell 0.29. Runtime sim, its
exported best ONNX (train/ckpt/spk2_best, fq2 stander, ball, 20 dev seeds), held / pinched / falls:
none 1 / 1 / 0; 25 % 1 / 2 / 0; 50 % 1 / 3 / 7 (right); 75 % 2 / 3 / 2; batteries out 0 / 0 / 17 (right);
full 3 / 3 / 14 (12 backward).
- The pinch is gone at every load (the fast training jaw, entry 03:35).
- Falls: 0-2 of 20 at 0, 25 and 75 %, 7 at 50 %; the full pack still falls 14 of 20.
- Batteries out (0.653 kg, COM x -0.027 m against the scaled pack's -0.018) falls 17 of 20 although 75 % of the full
  pack (0.716 kg) falls 2: the scale curriculum only trains scaled copies of the full pack, so the no-battery mass
  distribution is not covered. FP-R7 counts that load; a later run has to put it in the curriculum.
spk3 (matched jaw 0.55 / 0.0549 / 0.10, start spk2 model_best, floor 0.25, s_start 0.50 from f181a38b) was first
launched at 04:50 but the session ended during the launch and nothing started (0 live apps at 16:33). Relaunched
16:34 EST from `microduck_rl-grasp` f181a38b: `SPK_TASK=spk3 SPK_RUN=spk3 SPK_HOURS=3.5
SPK_INIT=microduck-seepick-spk2:runs/spk2/model_best.pt MICRODUCK_GPU=L4 modal run --detach
cmu/grasp/seepick_pack_modal.py::run --max-iters 1300 --max-dollars 4`; app ap-FNHETdeMUdmTJBAQlPUI3m, waiting for
an L4 at 16:40. Modal spend on this task so far: spk1 1.02, spk2 3.81, checks about 0.80 USD.
Scripts now in the repo (the session scratchpad was wiped): train/pickup_ckpt.sh, train/spk_wait.sh.

## 2026-11-13 17:00 OpenRB reflashed with a 57600 rescue path (Shawn: "现在直接刷"); jaw ID15 and hip ID4 restored on the robot

openrb_dual_host now takes a packet addressed to ID 253 (4-byte baud, raw bytes): bus to that baud, write, back to 1 Mbaud. Built with OpenRB-150:samd 0.2.1 (GCC 7.2.1, same generation as the 10-15 known-good build), flashed over USB by 1200-baud touch and the recorded bossac command; images in ~/.cache/microduck-fw/odh-rescue-20261113b.bin (running) and dual-20261018-ran (previous). First image accepted any baud: a 4 Mbaud request hung the bridge in flush() (bus dead, USB still up); second image whitelists 9600/57600/115200/2 M/3 M. Results: jaw ID15 back with one 57600 write. ID4 was at factory settings (read after rescue: RDT 250, Shutdown 53), now ID 4, RDT 0, Shutdown 52, torque off, position 2010. So ID4 really had fallen back to factory; the cause is still inferred (pack ran flat overnight), not proven. `pi/rescue_factory_servo.py` rewritten for this path (`--id N`, `--baud-only N`); the drawing code is removed. ID3 pending: its cable is still unplugged. A scan in the first ~0.3 s after a rescue write returns nothing; the tool waits.

## 2026-11-13 17:10 ID3 restored; 15/15

Right leg plugged back whole; `rescue_factory_servo.py --id 3` brought ID3 back on the first try with the robot's settings. Scan 15/15. Three servos (ID3, ID4 at factory settings; cause still inferred) restored in place, no spare board.

## 2026-11-13 17:40 Red light again after the rescue: latched voltage alarm on ID3 and ID4, cleared by Reboot

Shawn pressed stand; a red light came back. Registers: all 15 Shutdown 52, hw 1 (input voltage only), but ID3 and ID4 torque 0 while the other legs read 1. The factory Shutdown 53 had tripped on the 7.8 V pack at power-up, and that alarm stays latched after Shutdown is rewritten to 52; the brain's torque-off path does not reboot it because it masks the input-voltage bit. Reboot (0x08) to ID3 and ID4 cleared it (hw 0, torque 0). Sending it under a running brain broke every sync read (35 Hz, all IDs missed; cause not examined, likely the rebooted servos' RAM setup); a brain restart fixed it (49.7 Hz, misses 1). `rescue_factory_servo.py` now reboots the servo after writing its settings.

### 2026-11-13 17:25 Flight pack: spk3 iteration 100 picks with the pack in the runtime sim (FP-R7)

spk3 started 16:50 on an L4 (16 min queue), iteration 153 at 17:12, 0.46 USD. Training (matched jaw) at iteration
~150: no-pack held 0.56, s_max 0.59 from 0.50, 5 floor blocks early. Runtime sim, exported iteration-100 ONNX
(train/ckpt/spk3_100, fq2 stander, ball, 20 dev seeds; train/eval/pk_spk3_100_*_ball.json), held at hand-back
(still held 3 s later) / pinched / falls:
none 19 (13) / 20 / 1; 25 % 20 (16) / 20 / 0; 50 % 17 (15) / 18 / 0; 75 % 14 (14) / 14 / 3 (right);
batteries out 7 (7) / 8 / 12 (right); full 5 (3) / 5 / 16 (15 right).
Reference: start policy seepick61 without pack 15 (12), 1 fall; spk2 best 0-3 held at every load.
- The matched jaw was the cause of the lost pinch: one change, pinched 1-3 of 20 -> 14-20 of 20 up to 75 %.
- No pack, 25 % and 50 % now meet or beat the original pick policy's no-pack count.
- Batteries out (12 falls) and full (16 falls) still fail on balance, falling right. s_max is only 0.59 at this
  checkpoint, so full is beyond what this checkpoint trained on; batteries out is the uncovered mass distribution.
Run continues to its cap (1300 iterations / 3.5 h / 4 USD); next runtime test at the iteration-400 checkpoint.

### 2026-11-13 18:50 Flight pack: spk3 stopped at iteration ~681 (1.96 USD); best runtime checkpoint is iteration 300 (FP-R7)

Stopped by hand (`modal app stop`, 0 live apps after): the runtime sim got worse while training kept improving.
Training: s_max rose by 0.01 at every 10-iteration decision from iteration 60 and reached 1.00 by about 560;
at 560 the training slices read held 0.55 (none), 0.60 (s 0.50-0.75), 0.46 (s 0.75-1.0).
Runtime sim (fq2 stander, ball, 20 dev seeds; train/eval/pk_spk3_<it>_<load>_ball.json), held (at end) / falls:
- it 100: none 19 (13) / 1; 25 % 20 (16) / 0; 50 % 17 (15) / 0; 75 % 14 (14) / 3; nobatt 7 / 12; full 5 (3) / 16
- it 300: none 19 (15) / 0; 25 % 20 (20) / 0; 50 % 19 (18) / 0; 75 % 14 (12) / 3; nobatt 3 / 13; full 5 (1) / 19
- it 400: 50 % 14 / 1; 75 % 10 / 1
- it 500: 50 % 13 / 5; 75 % 14 / 5
- it 600: none 19 (18) / 0; 25 % 16 (15) / 0; 50 % 6 (5) / 12; 75 % 5 / 9; nobatt 12 / 8; full 3 / 16
Falls are to the right, 1.3 to 1.5 s after the switch to the pick policy (during the bend), with leg torque at the
0.538 N m ceiling 10 to 16 % of the time. The leg ceiling is the same in training (1.47 A, limit_servos).
Reading: (1) the jaw fix holds (pinched 19-20 of 20 at none/25/50 % at it 300, above seepick61's 15 without a pack);
(2) the training env overstates balance under heavy load: it reports 0.46 held at s 0.75-1.0 where the runtime
falls 16-19 of 20, and once s_max passed about 0.8 the policy moved to a bend that works only in training;
(3) the curriculum's rise test (top slice >= 0.8 x no-pack) never blocked, so it cannot see this. Not yet known:
which training-vs-runtime difference lets the loaded bend balance in training. Next: diagnose that difference
before any further run. Best policy so far: train/ckpt/spk3_300.
Modal spend on this task: spk1 1.02, spk2 3.81, spk3 1.96, checks about 0.80 USD.

### 2026-11-13 19:37 Flight pack: the runtime sim's heavy-load falls come from 20 ms of extra loop delay (FP-R7, spk3diag)

Cause: the runtime sim (brain_sim_check defaults `--sensor-delay 1 --action-delay 1`) runs about 40 ms from sample
to applied goal; training runs 15-30 ms on the joints (BAM `delay_min_lag 3`, `delay_max_lag 6` physics steps,
joint_pos lag 0, joint_vel lag 1) and 0-60 ms on the IMU terms (lag 0-3 policy steps); the robot measures 16 ms
joint sample to goal write (median, p10-p90 15.2-17.4) and 21 ms IMU age (15.7-27.2), pooled over 27 866 policy
ticks of 23 wired logs (robot-runs-20261030-t1, -20261106-seepick, -20261111-seepick; `train/out/spk3diag/robot_ages.txt`).
So the runtime sim adds about one tick (20 ms) that neither training nor the robot has.

Runtime sim, one setting changed, fq2 stander, 12 mm ball, 20 dev seeds, held / falls (`train/eval/pkd3_*.json`):
- it 600, 50 %: base 6 / 12; sd0 20 / 0; ad0 20 / 0. 75 %: base 5 / 9; sd0 20 / 0; ad0 20 / 0.
  full: base 3 / 16; sd0 19 / 0; ad0 19 / 1. nobatt: base 12 / 8; sd0 19 / 1; ad0 20 / 0. none: 20 / 0 either way.
- it 300, full: base 5 / 19; sd0 14 / 5; ad0 11 / 2. nobatt: 3 / 13; 18 / 1; 18 / 1. 75 %: 14 / 3; 18 / 0; 20 / 0.
- Refuted at it 600, 50 %: hip-roll goal clamp widened to the training action clip (hrwide) 7 / 11; servo read drop 0
  (drop0) 7 / 11; wired guards off 6 / 12 (so the termination and guard definition do not cause it).
- sd2 (60 ms) makes the stander itself fall 20 / 20 with no pack, so it says nothing about pick margin.
Training env (spk2diag_probe.py, 256 envs, seed 1, matched jaw; `train/out/spk3diag/*.json`), success / falls of 256,
plain vs od1 (the runtime's extra 20 ms on the 34 proprioceptive inputs):
- it 600: s 0.50 232 / 0 vs 197 / 25 (joints only, jd1: 221 / 6); s 0.75 231 / 1 vs 192 / 27; s 1.00 218 / 10 vs
  152 / 45; s 0.00 od1 224 / 7. Runtime goal clamp at s 0.75: 232 / 3 (refuted).
- it 300: s 0.50 232 / 1 vs 193 / 29.
Training-side falls point forward/backward, runtime-side falls right; the two scripts' direction labels were not
reconciled. Not checked: payload COM/inertia, floor friction and the stander-to-pick hand-over in the loaded cases
(the latency change alone restores the runtime results); the training probes at nobatt (budget stop); the real robot.

Proposal (not run): (1) the acceptance runtime sim should use the robot's measured one-tick loop, `--sensor-delay 0
--action-delay 1`, for every policy; that side disagrees with the robot logs. (2) Next training run, single change:
randomize an extra 0-1 policy-step lag (0-20 ms) on joint_pos and joint_vel obs, so the bend keeps a margin up to
the old runtime latency. (3) The rise test needs a robustness signal: the top slice's fall rate under that lag, since
training at s 0.50 reads 0 falls while +20 ms gives 25 of 256.

Scripts: `train/spk3diag_runtime.sh`, `spk3diag_table.py`, `spk3diag_clamps.py`, `spk3diag_train_table.py`,
`spk3diag_robot_ages.py`, `spk3diag_modal_batches.sh`, `flight_eval.py` (SPK3DIAG_JOINT_RANGE); worktree
`cmu/grasp/spk3diag_modal.py`, `spk3diag_cfgdump.py`, `spk2diag_probe.py` (`--joint-obs-delay`, fall direction).
Modal: 10 calls, wall-time ledger 0.706 USD (`cmu/grasp/.spk3diag_spend.json`, queue time included; bill lower).

### 2026-11-13 19:45 Flight pack: original pick policy under the shorter loop delay; decision for spk4 (FP-R7)

Checked the 19:37 entry's runtime numbers from the `pkd3_*.json` files (they match). Added the original pick policy
(`train/ckpt/bend4`) under `--sensor-delay 0` (about 24 ms sample to applied goal): no pack 6 held (6 at end), 0 falls,
against 15 (12) at the default 44 ms; full pack 0 held, 20 falls (`eval/pkd3_bend4_{none,load100}_sd0_ball.json`).
So the original policy's pinch is better at the longer delay and spk3's balance is better at the shorter one: neither
delay setting is shown to be the robot's. The robot logs give 16 ms joint age at the brain tick; the time from goal
write to servo motion is not in them.
Decision: the shared runtime gate stays as it is (44 ms). FP-R7 is judged at both delays, and the next run (spk4)
changes one thing: the joint position and velocity inputs get a random extra lag of 0 to 1 policy step, so the loaded
bend has to hold from about 15 to 50 ms. Start: spk3 `model_600.pt` (s_max already 1.0; under the extra 20 ms it scores
152 / 256 at full load in training, above the floor).
spk3 it 600 at the short delay, held (at end) / falls: none 20 (19) / 0; 50 % 20 (20) / 0; 75 % 20 (20) / 0;
batteries out 19 (18) / 1; full 19 (18) / 0.

### 2026-11-13 20:30 Flight pack: spk4 launched, spk3 plus a 0-1 step extra joint lag (FP-R7)

Task `Mjlab-SeeingPick-PackSpk4-FromPick-MicroDuck-CMU-Current` (worktree cmu/grasp, commit 0450e680): spk3's env, jaw,
floor, stops and model_best rule, one change: the actor's joint_pos and joint_vel inputs are 0 or 1 extra policy step
(20 ms) old (`extra_lag_obs` in `cmu_seeing_pick_pack_env_cfg.py`). Sampling: one draw per env per episode at reset,
uniform over {0, 1}, the same lag for both inputs, on top of spk3's (joint_pos 0, joint_vel 1 step). IMU lags, critic
and rewards unchanged. Curriculum s_start 1.00 (cap), so s_max stays at 1.0 and model_best is the first iteration the
floor holds; the numbered checkpoints are the ones to test.
Start check, spk3 `model_600.pt` in the spk4 env (256 envs, seed 1, matched jaw, deterministic, check placement),
success / falls (split lag 0 | lag 1): s 0: 236 / 1 (121 / 1 | 115 / 0); 0.25: 239 / 2 (123 / 0 | 116 / 2); 0.50:
232 / 6 (121 / 0 | 111 / 6); 0.75: 227 / 5 (116 / 1 | 111 / 4); 1.00: 213 / 10 (109 / 5 | 104 / 5); batteries out
222 / 3. Without the lag at 1.00: 216 / 8 (spk3diag 218 / 10 with the ONNX). Floor measure (s 0, noise, training
placement): held at end 138 / 256 = 0.54 with the lag, 144 without; floor 0.21 in these units, so s_start stays 1.00.
Joints-only lag costs much less than the 19:37 od1 (IMU plus joints: 152 / 45 at 1.00).
Smoke on Modal (64 envs, 5 iterations): init from model_600 (md5 b7a00091..., critic 97 as saved), s_max 1.000,
ONNX 0 / 2 / 4 exported live, exit 0. Tests: spk2 curriculum, spk3, spk4 files 30 passed (Mac mini CPU).
Launch 20:23: app ap-3Vsc82biLU44TdTTkkcIpl, call fc-01M7BTDV6THGGBH3MJNR8S7KXC, Volume microduck-seepick-spk4,
`--run-name spk4 --num-envs 4096 --max-iters 800 --save-interval 100 --max-hours 2.5 --max-dollars 3.0 --seed 1`,
retries 2. L4 from 20:26, 8.9 s per iteration (about 2.0 h for 800). The first launch at 20:16 failed in its image
build (stopped together with the smoke's status call), relaunched once. Modal bill so far: check 0.046, smoke 0.193
(incl. the stopped status rebuild), spk4 0.12 USD at iteration 6.

### 2026-11-13 22:50 Flight pack: spk4 finished; iteration 300 picks at every load at both loop delays (FP-R7)

spk4 (spk3 + joint position and velocity inputs 0 or 1 policy step older, one draw per env per episode; start spk3
`model_600.pt`, s_max 1.0 throughout) ran all 800 iterations on a Modal L4, 20:26 to 22:29, 2.28 USD; app
ap-3Vsc82biLU44TdTTkkcIpl ended by itself, watch clean, 0 live apps. Checkpoints every 100 on Volume
`microduck-seepick-spk4` `runs/spk4/`.
Runtime pickup test (fq2 stander, 12 mm ball, 20 seeds), held (still held 3 s later) / falls. "44 ms" is the runtime
default, "24 ms" is `--sensor-delay 0`; "new seeds" are seeds 100-119, never used before.
- it 300 (ONNX md5 de6579e9), 44 ms: none 18 (12) / 0; 25 % 20 (17) / 0; 50 % 20 (19) / 0; 75 % 19 (19) / 1;
  batteries out 19 (17) / 0; full 13 (12) / 5. New seeds: 16 (9) / 0; 19 (15) / 0; 19 (18) / 0; 18 (17) / 0;
  18 (18) / 2; 18 (15) / 0.
  24 ms: none 19 (18) / 0; 25 % 18 (16) / 0; 50 % 18 (17) / 0; 75 % 19 (19) / 0; batteries out 18 (18) / 2;
  full 16 (16) / 2. New seeds: none 20 (19) / 0; 50 % 20 (20) / 0; batteries out 18 (18) / 1; full 16 (16) / 1.
- it 400, 44 ms: none 17 (13) / 0; 25 % 18 (14) / 0; 50 % 19 (16) / 1; 75 % 15 (15) / 3; batteries out 19 (19) / 0;
  full 15 (15) / 3. New seeds: 18 (16) / 0; 15 (14) / 1; 15 (15) / 0; 14 (14) / 3; 20 (20) / 0; 16 (14) / 2.
  24 ms: 19 (18) / 0; 20 (19) / 0; 20 (20) / 0; 19 (19) / 0; 16 (16) / 0; 18 (18) / 0. New seeds: none 20 (20) / 0;
  50 % 20 (20) / 0; batteries out 19 (19) / 0; full 18 (18) / 0.
- Original pick policy (bend4), 44 ms: none 15 (12) / 0, new seeds 14 (12) / 0; every pack load 0 or 1 held,
  18 to 20 falls, on both seed sets.
- Other checkpoints, 44 ms, 75 % / batteries out / full: it 100 16 / 4, 6 / 13, 1 / 19; it 200 16 / 4, 5 / 13,
  3 / 15; it 500 18 / 1, 16 / 2, 8 / 9; it 600 12 / 6, 6 / 11, 2 / 18 (24 ms full 12 / 8); it 700 9 / 9, 4 / 15,
  1 / 19.
Reading: iterations 300 and 400 hold at every load at both delays and at least match the original policy's no-pack
count; the checkpoints before and after do not, so the policy drifts during training and the checkpoint is chosen
by the runtime test only (training's own numbers and model_best do not show it). Weakest cells of it 300: full pack at
44 ms (13 and 18 of 20, 5 falls in 40) and "still held 3 s later" with no pack at 44 ms (12 and 9, original 12 and 12).
Candidate: it 300. Simulation only: nothing is on the robot.
Tests now run detached on the Mac mini (`train/pickup_batch.sh`, `mini_pickup_batch.sh`, `pickup_table.py`) because
the MacBook slept with its lid closed and stalled an ssh-driven test for an hour.
Modal for this task so far: spk1 1.02, spk2 3.81, spk3 1.96, spk4 2.28, checks and diagnosis about 1.75 USD.

## 2026-11-17 Computing model for the pet robot: fast system, slow system, memory, consolidation

Source: Shawn's voice conversation with ChatGPT (share 6afd0f70-039c-83ea-a758-6a0f7d34b12e, second half), his follow-up
questions the same day, and four literature passes (sources reopened 2026-11-17 where marked "checked"). Nothing here is
built or trained; training needs Shawn's nod on a plan first.

**Shawn's line of thought (his positions, in order).**
1. Hardware follows workload. "不能拿着锤子找钉子": no robot chip question before the model architecture is settled. ROS is
   plumbing, not the load. The π0.7 load is transformer inference throughout, so it does not call for a new chip by itself.
2. The fast system may want a different architecture. The brain controls a body with a state that is carried forward and
   updated, closer to a recurrent system than to re-reading a context window; transformers get order from an add-on
   (position encoding), recurrent models have it in the update. He asked whether such models, pretrained on video and
   action rather than language, would learn the physical world better. Status: hypothesis, no evidence at scale.
3. Fast and slow are coupled, not isolated: separate modules, a shared world state, different rates, and skills that move
   from slow to fast with practice (distillation plus RL plus habit). RL trains the fast system while the slow one is frozen.
4. Learning runs on several time scales: state update every step (no weight change), small modules over hours, replay and
   consolidation overnight (hippocampus and cortex, sleep replay). "白天快学、晚上巩固".
5. Goal: applications, not theory. The pet robot needs continual learning, long-term memory, a fast body system and a slow
   planner. Today it has per-task RL policies glued by ChatGPT/Claude-written code, which does not generalise.

**π0.7 facts (arXiv 2604.15483v1, 2026-04-16, checked).**
- Three models, not four systems: the VLA (about 5B: Gemma3 4B VLM, 400M vision encoder in the MEM video-history design,
  860M flow-matching action expert), a high-level language policy on the same architecture, and a subgoal-image world
  model initialised from BAGEL (14B mixture of transformers). "Hippocampus" is our analogy, not PI's.
- "The π0.7 model and the high-level policy ... use a single NVIDIA H100 GPU for inference": 38 ms minimal, 127 ms worst
  case. The 4 H100 are the world model only ("4-way tensor parallelism on 4xH100", 8-bit, 25 denoising steps in 1.25 s,
  nearly 10,000 tokens), run asynchronously while the robot keeps moving.
- Memory: up to six past frames per camera at 1 s stride, compressed to one frame's token count; text memory is the
  history of subtask instructions. MEM (arXiv 2603.03596): video memory to about 54 s, rewritten text summary to 15 min,
  within one task.
- No recurrent or state-space layer in any PI paper read (agent report; "recurrent" and "state space" do not occur in the
  π0.7 text, checked).
- An H100 is PI's choice, not a requirement: π0 ran 73 ms on an RTX 4090 (arXiv 2410.24164); third-party π0.5 on Jetson
  AGX Thor about 44 to 54 ms quantised (agent report, not reopened).

**Recurrent architectures (agent report; Mamba-3 abstract checked).**
- Mamba is not the newest or the strongest: Mamba-3 (arXiv 2603.15569, 2026-03) exists, trained only to 1.5B. Large
  models that win are hybrids (mostly recurrent or linear layers plus a few attention layers: NVIDIA 8B study arXiv
  2406.07887, Qwen3-Next, Kimi Linear). Pure fixed-state models are weak at exact retrieval and copying.
- Speed: the gain shows with long histories or long decodes. For a short context (a few images, short text) prefill can
  be slower than attention (Mamba-3 latency table, agent-reported, not reopened). A VLA control step is mostly that
  short prefill plus iterative denoising, so swapping the backbone would not make π0.7 faster.
- No fully recurrent VLA at 2B+ pretrained on large robot data with released weights. Downloadable recurrent checkpoints
  are text models (Mamba-2 hybrid 8B, xLSTM-7B, RWKV-7, RecurrentGemma) or small VLMs (Cobra). Robot uses so far are small:
  MaIL (CoRL 2024), LRAM/xLSTM (ICML 2025, sim only), Mamba action expert in SmolVLA (arXiv 2608.21407, checked title),
  AnolisVLA (arXiv 2603.15046, checked title), DASH asynchronous fast/slow (arXiv 2611.11854, checked title).

**Fast + slow + memory + continual learning on one robot (agent report).**
- Each piece is published separately: dual systems (Helix 02 at 1 kHz / 200 Hz / 7-9 Hz, GR00T N1, Fast-in-Slow, DASH);
  within-task memory (MEM, MemER, MemoryVLA); map memory (ReMEmbR); post-deployment learning (π*0.6 Recap, RL Token
  with a frozen VLA and a small online actor-critic head, HIL-SERL); sleep-style consolidation in sim ("When Robots
  Sleep", arXiv 2606.17493); DayDreamer (arXiv 2206.14176, checked title) learned to walk on a real quadruped in 1 hour.
- No published system runs all four on one robot, and none was found on a low-cost or pet robot. Closest: EmbodiedRSI
  (arXiv 2610.10498, checked title; frozen model, no fast motor loop), PI's separate papers, Learning to Forget on ARMAR-7.

**What fits MicroDuck (project inference, not built).**
- Fast body system, onboard, 50 Hz: one recurrent policy that follows a command vector (velocity, head, posture, later a
  small skill latent) instead of one policy per task. Trained in sim with RL from scratch; a few million parameters at
  most, so a pretrained Mamba adds nothing here. The recurrent state is also the standard answer to what the pickup tests
  showed (sensitivity to delay and pack load are partial-observability problems).
- Slow system, Mac mini or cloud, 1 to 5 Hz: a VLM that outputs commands or latents, not code.
- Memory, Mac mini: episodic log plus a fact store with retrieval (already the direction of the always-on capture).
- Consolidation, while charging: replay the day's logs, update small modules only, pass the sim suite before anything
  reaches the robot.
- Not recommended: a VLA onboard (no source shows one at 50 Hz on a 2 GB ARM CPU; no demonstrations to train it), or
  fine-tuning a multi-billion recurrent language model for body control.
- First test that could refute the recurrent fast system: same sim budget, MLP versus GRU/LSTM versus small Mamba core,
  scored on the existing pickup table (pack loads, 24 and 44 ms delay, held 3 s later) and push recovery. If the
  recurrent core is not clearly better on the delay and load cells, the architecture question is closed for this robot.

## 2026-11-17 Computing model, corrections after Shawn's review

- Shawn: PI's approach is not what we mean by fast and slow systems ("和我们想象中的人脑这样的快慢系统根本就不是一回事"). Agreed
  reading: π0.7 is one imitation-trained transformer prompted at several levels (subtask text, one generated subgoal
  image, the VLA conditioned on both); MEM is within-task memory in a context window. No state carried between calls, no
  memory across days, no learning after deployment in that paper. Shared with us: only the high-level-to-low-level split.
- Shawn: "充电时巩固" does not fit this robot: the 2S Tattu 650 pack is charged outside the robot on the HTRC balance
  charger, robot off (CURRENT-STATE `parts_battery_charging`, `power`). Correction to the entry above: consolidation runs
  on the Mac mini from logs already sent over Wi-Fi (run ledger `~/duck-walks/episodes.jsonl`); the robot can be off.
  New weights and facts load at the next start. Self-docking and charging while running is a separate product feature
  (always-present pet), not a prerequisite for learning. Not designed, no parts chosen.
- Open design point Shawn raised: fast/slow/memory are not yet specified clearly. Working definition proposed in chat
  (by time scale: reflex 20 ms onboard, situation 1 s to minutes on the Mac mini, episodes across days, consolidation
  overnight; real logs choose what to practise, the sim does the practising). Proposal only.

## 2026-11-17 Memory requirements from Shawn; what already exists; sound direction; recurrent policy route

**Correction to the two entries above.** The layer split proposed in chat today was not new: `PET_ROBOT_FEATURES.md`
section 0 (2026-10-26) already fixes reflex (A7Z) / intention (Mac mini, 10-30 s) / reflection (nightly), and `pet/`
holds code for it: `pet/identity` (face and voice enrolment, familiarity memory with nightly consolidation, fusion),
`pet/learn` (event log of 41 types, nightly reflection into diary and rules, Rescorla-Wagner, retrieval), `pet/mind`
(drives, intentions, validator, reflexes, runner, glance, survey). Built and tested off the robot; no pet service is
listed in CURRENT-STATE `a7z_background_processes`, live status not checked today. Today's additions are the recurrent
reflex policy and the slow-to-fast skill transfer; the rest is integration of what exists.

**Shawn's memory requirements (his words, 2026-11-17).** "今天给我换了这个模型，或者给我换了那个模型"; "今天我做了什么，
让我去点球；今天标定了，比如左腿脑袋做了微调"; "今天开机时看到了谁 ... 建一个图库，把我们十几个人、这只鸭子的16831课队友
的声音和脸录进去"; "看见了谁、谁开机了、他们在干什么". He also wants it to keep taking in what it hears and write down
what happened (like ChatGPT's memory), and to go and look when curious. Mapping to what exists:
- model swap, calibration, actions done: already recorded as data by the run ledger (`run_ledger.py`: one meta line per
  brain start with code and policy hashes, arguments, gains, IMU trims; one record per action with outcome). Missing: a
  bridge that turns those into `pet/learn` events (new types needed, e.g. model changed, calibration changed).
- who was seen at power-on: `pet/identity` does this off the robot. Missing: enrolment of the teammates (faces from
  photos, voice from a spoken phrase; each person's consent), and the live hookup at boot.
- what people are doing: not covered. Needs a vision-language caption of a keyframe on the Mac mini or in the cloud.
- what it hears: `life_log.py` already keeps voice-triggered three-microphone segments; `mine_life.py` pulls them to the
  Mac mini. Missing: transcription of those segments into events and the nightly diary.
- curiosity look: `pet/mind/glance.py` and the name-call head path exist; missing: a trigger on unexplained events.

**17-720 lecture of 2026-11-17 (microphone arrays, beamforming, angle of arrival).** No slide deck is posted: the
course site's row for Nov 17 lists six papers only, and Canvas files hold nothing new (both read 2026-11-17). The six
papers and the Bartlett/MVDR tutorial are already saved under the course's `Reading-08-Microphone-Arrays/Papers/`.
- The duck already estimates direction (GCC-PHAT / SRP-PHAT on three microphones, `namecall.py`, NAMECALL.md).
- "Listen only to that direction" with this head, by arithmetic: three microphones give at most 10 log10(3) = 4.8 dB
  against diffuse noise with delay-and-sum; 77 mm ear spacing aliases above 343 / (2 x 0.077) = 2.2 kHz; MVDR can null
  at most two point sources. The loudest noise is the duck's own servos (requirements R2, R13), close and not from one
  direction, where a beamformer helps least. The head is the steerable part: turn to the sound, then sum the two ears.
  The reading "Hybrid Neural Networks for On-device Directional Hearing" (beamformer plus a small network) is the
  matching recipe and joins the open R2 item (denoising on the A7Z). Offline test possible on the saved three-channel
  life segments with known bearings; not run.

**Recurrent reflex policy: route (not launched; training needs Shawn's nod).**
- Current policy: MLP 512-256-128, 61 inputs (`microduck_velocity_env_cfg.py`), rsl_rl 5.0.1 (has `rnn_model.py`).
- The plumbing already exists in `extensions/flight-20261110/train/HISTORY-PLAN.md` and `cmu/finetune/flight/history.py`
  (plan not approved, not launched): an actor that sees its last K frames, warm-started so that at iteration 0 it equals
  the existing 61-input policy, and an ONNX contract where the runtime feeds a state tensor back each tick. A GRU uses
  the same contract with its hidden state in place of the frame stack.
- Order proposed: (1) history design A against a one-frame control, fixed budget, existing acceptance tables; (2) only
  if history helps, a GRU student distilled from the existing policies (DAgger), then RL fine-tune; (3) command
  conditioning for several skills. An MLP cannot be fine-tuned into a GRU; its behaviour is carried over by distillation.

## 2026-11-17 Shawn's correction: architecture and model sizes, not implementation steps

- "什么十几位队友？整天扯淡": the teammate-gallery reading of his dictated note was wrong; removed from the register. Who
  gets enrolled is his call, not assumed.
- He asked for a system architecture with a size estimate and an implementation path per model, deployable on the duck,
  covering long and short-term memory, instruction following, companionship and its own intentions; the previous reply
  drifted into integration tasks. Architecture summary given in chat the same day (four layers by time scale, four
  kinds of memory, size per model; sizes other than the walking policy and buffalo_sc are estimates, not measured).

## 2026-11-17 Skill transfer, quality-rated data, and which pretrained models are usable as they are

- Shawn accepts two limits of the four-layer architecture: the brain is not in the body, and there is no single
  unified model.
- Skill transfer splits in two. Decision transfer (the reflex layer learns the slow layer's repeated choices) is
  behaviour cloning and routine. Motor-skill transfer needs simulation and on-robot acceptance; that acceptance is the
  uncertain part (our own walking fine-tunes scored better in sim and worse on the robot).
- Quality-conditioned training (Shawn's proposal, after pi0.7's "episode metadata that describes the data quality",
  checked in the paper): the small policy gets an extra quality input; data = real logs rated from run-ledger outcomes
  plus sim-generated good examples; each new skill needs one success criterion, not a shaped reward. Limit: conditioning
  cannot produce behaviour absent from the data, so the sim-generated good examples are required. The pi*0.6
  advantage-labelling detail is from recollection, not reopened.
- Shawn pasted a ChatGPT list of small pretrained models (RoboMamba, Mamba policies, SmolVLA, Octo, TinyVLA, DINOv2,
  V-JEPA) and asked whether we can use them directly. Abstracts reopened 2026-11-17:
  - RoboMamba (arXiv 2406.04339): vision encoder + Mamba language model, a policy head of 0.1 % of the parameters
    predicting SE(3) end-effector poses, for arm manipulation.
  - Octo (arXiv 2405.12213): transformer policy trained on 800k Open X-Embodiment trajectories, "generalist policies
    for robotic manipulation", fine-tuned to new action spaces in hours on a consumer GPU.
  - SmolVLA (arXiv 2506.01844): small VLA trained on community data from affordable arms, runs on consumer GPUs or CPUs,
    asynchronous chunked inference.
  - Drama (arXiv 2410.08893): Mamba world model, 7M parameters, Atari100k only (not a robot result).
  - Project inference: every pretrained robot policy on the list learned arm manipulation, so none carries knowledge of
    a walking biped's legs; their pretrained action knowledge does not transfer to the duck's reflex layer. Usable as
    they are: the frozen vision encoders (DINOv2-Small, about 22M parameters, figure from recollection) as the eyes of
    the perception layer, and the architecture pattern (frozen encoder + small recurrent core + small action head)
    trained by us in sim. Not checked: the pasted claims about Mamba-2 "8x" state, TTT/Titans adapting on robots within
    seconds, Mamba inside Cosmos, tactile fusion at 500 to 1000 Hz, and 60 Hz on a Jetson Orin.

## 2026-11-17 Sim-pretrained fast system on the A7Z: Shawn's five points

- Shawn: MuJoCo already is the dynamics model; calibration against real logs should not be needed; the fast system is
  a single-frame ViT/CNN plus a multi-frame Mamba on the duck, sized with headroom; the slow system stays on the
  computer. Asked for the largest model the duck can run and whether that is enough for routine behaviour.
- Agreed corrections: a separately learned dynamics model is not needed for pretraining (MuJoCo is the dynamics); it
  was dropped from the list. Calibration is not a gate: randomize the body over a range around the already measured
  facts and let the recurrent core adapt. The remaining check is whether real logs fall inside the randomized family.
- A7Z budget from microduck-sim/CURRENT-STATE.json (read 2026-11-17): brain compute 6 to 7 ms of a 20 ms tick, loop
  already at 20.5 to 21.6 ms; camera service about 20 % CPU and the flight recorder about 30 %; the brain locks about
  925 MB of the 2 GB; MemAvailable fell to 168 MB under a heavy load on 2026-10-30.
- Size estimate (project inference, nothing benchmarked on the A7Z): 50 Hz motor core stays near 1M parameters; vision
  runs in its own process at 5 to 15 Hz. Comfortable total 5 to 10M parameters (CNN encoder 3 to 5M on the NPU, Mamba or
  GRU core 2 to 5M on CPU, head under 1M), 20 to 40 MB. Ceiling about 25 to 30M (a DINOv2-Small-class ViT) at 2 to 5
  frames per second, and only if the NPU runs transformer layers, which is unverified. First measurement before any
  training: time random-weight models of these sizes on the A7Z beside the running brain.
- Correction the same day, from the maker's published figures (Radxa docs, Cubie A7Z NPU model zoo, read 2026-11-17,
  https://docs.radxa.com/en/cubie/a7z/app-dev/npu-dev/model-zoo; Allwinner A733, Vivante VIP9000 NPU, "3 TOPS@INT8",
  inference time only, 8-bit unless noted): CLIP image encoder 224x224 (63.7 MB model file) 13.7 ms; MobileNetV2
  224x224 (3.6 MB) 2.0 ms; YOLO11s 640x640 (6.9 MB) 31.9 ms; two-layer LSTM with 128 hidden units (1.1 MB) 1.2 ms; Lite
  Transformer, 16 tokens, 16-bit, 24 ms. So the NPU does run transformer layers and the size estimate above was too
  low: a ViT image encoder of the CLIP class (tens of millions of 8-bit weights) fits at the camera's 10 frames per
  second, and an LSTM core costs about 1 ms. Revised budget: encoder up to the CLIP-image class (about 64 MB) on the
  NPU, recurrent core as LSTM or GRU on the NPU or CPU, total 60 to 70 MB. Not covered by these sources: Mamba layers
  are not in the zoo (state file parts_a7z_extensions and earlier sessions hold no NPU benchmark either), the page does
  not name the CLIP variant, and the figures are for an idle board, not beside the brain.

## 2026-11-18 Unified multi-skill motor core: size of the training job, 16-831 lecture 22, expected benefit

- Deployed Pollen policies, read from the ONNX files in `whole-robot-20260912/runtime-overlay/models`: MLP
  61 -> 512 -> 256 -> 128 -> 14 with ELU, 197,896 parameters, 794 KB, no memory, one file per task (walk61, stand61,
  sitstand61, kick, groundpick61, seepick61). Our own `learned_target.onnx` is a YOLO-class CNN, 9.73M parameters, 39 MB.
- Shawn's direction: one model for all motor skills is of interest; an end-to-end eye-plus-body model was discussed and
  not recommended as the first step (rendering cost, visual sim gap, 10 Hz camera against 50 Hz control).
- Measured size of one of our runs (cmu/finetune/modal/FINETUNE-DELTA.md): 4096 envs x 24 steps x 1000 iterations =
  98.3M steps = 546 hours of simulated duck time; 56 min on a Modal L4 ($1.05), 82 to 83 min on a free Kaggle T4, 82 to
  114 min on the Mac mini. These were fine-tunes from walk61.
- Estimate for a multi-skill recurrent core (not a plan, no run approved): 5,000 to 20,000 iterations, 0.5 to 2
  billion steps, 7 to 27 hours on one T4. Earlier cost estimates in this project ran about ten times off, so this is a
  range to be replaced by a 40-iteration bench before any run.
- 16-831 lecture 22 (Sim2Real, Guanya Shi, 2026-11-17; explained page in the course folder, week 12) maps onto this:
  domain randomization (already used; too wide makes the policy conservative, and it cannot cover effects the sim has
  no equation for, such as backlash); privileged teacher then history-only student with DAgger (the recipe for the
  recurrent core; the lecture says plain PPO on history is the harder way); real-to-sim (system identification narrows
  the randomization range, a residual or actuator model covers the missing effects); perception randomization in RPL
  (camera pose, field of view, pixel dropout, noise) for a later vision stage. This qualifies the earlier "no
  calibration needed": not a gate, but identification pays off and backlash-type effects need it.
- Expected benefit, by source: unification gives no policy swap between skills and combined commands (walk while the
  head looks down); memory gives adaptation (slip, payload, delay); neither gives more speed or stronger turns, which
  are set by the command range trained and the servo limits. Evidence for the combined-command gap: walk61 moves 7 mm in
  6 s under a head command where the t1 fine-tune walks 0.95 to 1.16 m (sim), and t1 then fell on the robot.
- 2026-11-18 Shawn: "那来试试吧"; "Kobo" was a dictation error for Kaggle. Kaggle quota read the same day: 0 of 30 GPU
  hours used, refresh 2026-11-21.
- Existing work found before planning (microduck-sim/extensions/flight-20261110/train): the universal stand/walk line
  (UNIVERSAL-PLAN.md, approved 2026-11-11) already trains one 61-input policy over all back loads; uni_a and uni_b fail
  its acceptance gate (out/accept_uni_a.json, accept_uni_b.json); universal3 (kernel fk-uni3) stopped at iteration 1500
  on its time cap and no acceptance file for it was found; HISTORY-PLAN.md holds the history-student design with the
  student side implemented and the privileged teacher and distillation worker not written. The first step of the trial
  is therefore the unevaluated universal3 gate (dispatched to a background agent, Mac mini, sim only), then the
  teacher-student run proposed to Shawn; no training launched.
- 2026-11-18 Shawn: the earlier universal line was load training for the future jet pack; the new model should cover
  that load range too, "这样换喷气背包时就不用换一个新的模型了". Folded into the proposed run: the payload event of
  UNIVERSAL-PLAN.md section 2 (no pack, batteries out, full pack, any load 0 to about 1.1 kg) stays on in every skill,
  the teacher sees load and COM, the student infers them from its history. Acceptance therefore runs every skill at
  every load state. Project inference: the mechanism that covers load is the history input, not parameter count; the
  one-frame runs failed on forward-COM and shove cases at 197,896 parameters and more width was never the tested fix.
- 2026-11-18 Shawn: "可以开跑呗". Approved scope: Kaggle free quota only, cap 10 GPU-hours, sim only, nothing deployed.
  Dispatched to a background agent: privileged teacher + history student (DAgger) for stand, walk and head-follow at
  every load state, with a control arm on the second GPU; plan file to be written at
  microduck-sim/extensions/flight-20261110/train/TEACHER-STUDENT-PLAN.md. The bend is not in this round (the earlier
  line kept it as a separate policy with a hand-back); it follows once this round has an accepted walker.
- 2026-11-18 Shawn's correction: this is meant to be a new architecture (single-frame CNN or ViT, recurrent core such
  as Mamba), so what is the old model for. The dispatched brief had the student as the existing history-window MLP,
  which is not recurrent. Changed before any long run: student = recurrent core carrying its own state (GRU or LSTM,
  61 inputs per tick, single-step ONNX with state in and out), second arm = small Mamba core if it installs and exports
  cleanly, otherwise the history-window MLP. The old MLP policies keep two roles: warm start for the privileged teacher
  and baseline in acceptance; their weights are not loaded into the student. No image input in this round: the encoder
  stays a separate module that will feed a small target vector.
- 2026-11-18 Shawn asked whether 0.5 s is enough. The recurrent student has no fixed window; its trained horizon is the
  backpropagation segment, which would have defaulted to the 24-step rollout (0.48 s). Set to about 100 steps (2 s) with
  state carried across segments, and the run now reports a measured adaptation time per load state. Project inference:
  load, delay, friction and shove show within a few tenths of a second; remembering where a seen object was needs
  seconds and belongs to a later round with a target input.
- 2026-11-18 Acceptance of the earlier one-frame universal3 run (`microduck-sim/extensions/flight-20261110/train/out/accept_uni3_best.json`,
  `accept_uni3_1500.json`; top-level verdict FAIL in both, read by the main session; per-line figures from the
  evaluation agent's RUNLOG entry): best checkpoint fails 12 of 30 gate lines (uni_a 10), final checkpoint 23 of 30.
  Forward COM +10 mm walking falls 20 of 20 at every checkpoint from 250 to 1500. Longer one-frame training made the
  nominal and no-pack walks worse. This supports the memory-based teacher-student round.
- 2026-11-18 Teacher-student round status at 03:42 EST (RUNLOG.md "Teacher-student round"): code written, Mac mini
  smokes done 01:33, Kaggle benches done (0.42 h quota; LSTM student 306,830 parameters, Mamba student 277,134,
  both export to a stateful ONNX), incentive audit PASS, session 1 `microduck-ts-teach` (privileged teacher and
  one-frame control, 1000 iterations, 1.6 h cap) pushed 02:10 and RUNNING. Shawn before sleeping: "你自己冒烟完继续往下训吧".
  The build agent continues through student distillation and acceptance without stopping, inside the same limits
  (Kaggle free quota, 10 GPU-hours, simulation only, nothing to the robot or team repo, no push).
- 2026-11-18 Teacher-student round, result at 09:00 EST (files in `microduck-sim/extensions/flight-20261110/train/out/`:
  `ts_compare.json`, `accept_ts_lstm.json`, `accept_ts_mamba.json`, `accept_tsc_750.json`, `accept_tsc_999.json`,
  `ts_gate.json`, `adapt_*.json`; verdicts and per-load falls read by the main session from `ts_compare.json`).
  No policy of this round beats the start point (run A, uni_a). Failed gate lines: start 10, one-frame control 22
  and 23, LSTM student 27, Mamba student 25. Walk falls of 20 at none / 25 / 50 / 75 % / batteries out / full:
  start 0/0/0/0/0/0 at 0.17 to 0.18 m/s; control 750 20/8/3/1/5/6; control 999 2/0/0/9/10/19; LSTM 20/19/6/6/9/17;
  Mamba 17/15/17/13/15/20. Every policy trained with the universal3 recipe walks 0.26 to 0.36 m/s with leg torque
  p99 at the 0.54 N m clamp in the runtime simulation; standing is fine (0 to 2 falls). Agent-reported, not
  rechecked: teacher passed its gate only at iteration 750; students settle 0.2 to 0.3 s after a reset and 0.7 to
  1.2 s after a zeroed state; with the state zeroed every call both students fall 20/20, so they use their memory.
  Evaluator fault fixed on the way: the stateful session wiped the recurrent state on every dropped servo read; the
  robot runtime would need the same rule. Kaggle quota used 4.77 h plus a diagnostic session still running
  (`microduck-ts-lstm-a`, students distilled from run A itself, cap 1.7 h). Project inference: the main failure is
  the training recipe (a fast gait the runtime simulation does not hold), shared by the one-frame control, not the
  recurrent core as such; the students add imitation error on top. Next: the diagnostic result, then a one-switch-
  at-a-time comparison of the training env against the runtime simulation for the control policy.
- 2026-11-18 Diagnostic result at 09:55 EST (`microduck-ts-lstm-a`, students distilled from run A itself, 140
  iterations; `out/accept_ts_lstm_a.json`, `out/accept_ts_mamba_a.json`, `out/ts_compare.json`, numbers read by the
  main session). Walk falls of 20 at none / 25 / 50 / 75 % / batteries out / full: start 0/0/0/0/0/0, Mamba student
  0/0/0/0/0/0, LSTM student 0/0/0/0/0/9, all at 0.17 to 0.19 m/s. Failed gate lines: start 10, Mamba 11, LSTM 14.
  Hard cases with pack (start / Mamba / LSTM): comx+10 walk 19 / 14 / 18, walking shove 11 / 10 / 16, mass+10 walk
  2 / 5 / 13. Conclusion: a recurrent student carries over to the runtime simulation when the teacher's gait does;
  the earlier student falls came from the teacher (universal3 gait), not from the recurrent core. The Mamba core
  copied the teacher more closely than the LSTM here (one run each, no repeat). The student does not yet beat its
  teacher: it was given nothing the teacher lacks. Quota used 6.41 h of the 10 h cap. Still open: which single
  difference between the training env and the runtime simulation makes the universal3 gait fall (separation test
  started 09:35 on the Mac mini, no result yet).
- 2026-11-18 Separation result at 11:00 EST (RUNLOG.md "Question: the one-frame control ..."; files
  `microduck-sim/extensions/flight-20261110/train/eval/sep_<policy>_<load>_<switch>.json` and `out/tsep_*.json`; the
  fall counts for base, sensor delay 0, action delay 0, compensation, no dropped reads and no current limit were read
  by the main session from the sep files). Cause: control-loop dead time. The runtime simulation gives the policy
  readings one tick old and applies each goal one tick later, about 40 ms from measurement to servo; the training
  env delays only the command by 15 to 30 ms and reads joints with no delay. Runtime walk falls of 20 for the
  one-frame control at iteration 999, full pack: base 19, sensor delay off 0, action delay off 0, Brain compensation
  on 0; no dropped reads 20, no current limit 18. Start point at full pack: 0 at the runtime delay, 20 with one more
  tick of action delay. Agent-reported, not rechecked: friction, supply, mass model, contact model, ramp and goal
  clamp do not remove the falls; in the training env the same cliff sits about 20 ms later, and where that 20 ms
  offset comes from is not found. Consequence for the next recipe: train with the runtime's loop timing (joint and
  IMU readings one tick old, command 20 ms late, margin toward 60 ms) and pick checkpoints on runtime-simulation
  falls. Not adopted: the Brain's compensation switch (a robot runtime change, only measured). Not launched: any new
  training; it waits for Shawn's nod on the plan. Kaggle quota left in the cap: 3.59 h.
- 2026-11-18 Round 2 approved by Shawn ("开跑") and dispatched to the build agent: retrain the privileged teacher with
  the runtime simulation's loop timing (readings one tick old, action 20 ms late, dead time randomised toward 60 ms),
  verify on the Mac mini that the new training env reproduces the runtime ordering (start point holds, the round-1
  control falls) before any Kaggle time, pick the teacher checkpoint on runtime-simulation falls, distil one Mamba
  student. Budget: the remaining 3.59 h of the 10 h Kaggle cap; simulation only, nothing deployed, no push. Round-1
  code is in local commits robotics c2aabda1 and microduck_rl d3c8bc2d (agent-reported).
- 2026-11-18 11:44 Shawn: "超了也没事 主要是太慢了呀". The 10 h cap on the round is lifted; the limit is the Kaggle free
  weekly quota (30 h, about 4 h kept unused). Still free quota only, simulation only, nothing deployed, no push.
  Speed first: the build agent stops the serial Mac mini pre-launch cells, launches teacher arms now with two delay
  settings bracketing the unexplained 20 ms offset, and starts the Mamba student as soon as one teacher checkpoint
  passes selection in the runtime simulation.
- 2026-11-18 Shawn's correction: "不是 我是说超了可以用modal和aws". Modal and AWS are allowed for round 2, for
  speed. Dollar limit set by the main session, not by Shawn: 10 USD in total, enforced in the launchers, each run's
  price, hours and dollars recorded in RUNLOG.md. Kaggle runs already pushed keep going; paid compute carries the
  extra parallel arms (more teacher delay settings, control, students started as soon as a teacher is selected).
- 2026-11-18 12:31 Shawn confirmed the 10 USD limit ("这个数没问题") and asked whether training had started. It had
  not: the round-2 prelaunch chain hung from 12:01 on a dead ssh connection to the Mac mini (second occurrence today,
  first at 09:36) while the build agent waited on it. Main session killed the hung ssh call and told the agent to
  push the teacher with the delta that already passed its incentive audit (universal4tb), add ssh keepalive and a
  local time limit to every Mac mini call, and launch the second delta when its audit passes.
- 2026-11-18 12:33 Round 2 teachers pushed to Kaggle, both RUNNING at 12:40 (status read by the main session):
  `microduck-ts2-teach` (delta universal4t, readings one tick old, dead time 40 to 65 ms) and `microduck-ts2-teach-b`
  (universal4tb, 55 to 80 ms); from run A final, 1000 iterations, saves every 125, 1.6 h limit, expected end about
  14:10. Agent-reported: incentive audit PASS for both deltas at three loads; the training env does not reproduce the
  runtime ordering at any dead time, hence two delay arms selected in the runtime simulation; the runtime evaluator
  now feeds the teacher's 7 privileged inputs; ssh stall fixed with `train/ssh_guard.sh`. Modal and AWS not used: the
  agent declined to spend on a relayed authorization, and two Kaggle sessions cover the current arms.
- 2026-11-18 14:23 Round 2 teachers selected in the runtime simulation (walk vx 0.25, 20 episodes each at none /
  batteries out / full / COM x +10 mm / 0.5 N s shove; falls read by the main session from `eval/pk_*.json`):
  start point 0/0/0/19/11 = 30 (0.17 to 0.19 m/s); Mamba-A 0/0/0/14/10 = 24; round-1 teacher 750 14/13/18/20/20 = 85.
  Teacher A (40 to 65 ms): 125 0/0/1/19/11 = 31; 250 0/0/0/20/0 = 20 (0.27 to 0.33 m/s); 375 14/0/0/20/17 = 51;
  500 0/0/6/11/0 = 17; 625 to 999 not evaluated yet. Teacher B (55 to 80 ms): 125 36; 250 29; 375 23;
  500 0/0/0/20/0 = 20 (0.25 to 0.38 m/s); 625 59; 750 98; 875 79; 999 91.
  Finding: training with loop delay removes nominal and shove falls at 0.25 m/s and above, but only at early
  checkpoints; longer training walks faster and falls again. COM x +10 mm still falls 20/20 for both picks.
  Chosen by the agent: A-250 and B-500. Open: A-500 (the only checkpoint better than the start point at COM x +10,
  with 6 full-pack falls) and A 625 to 999; the agent was told to evaluate them and record the choice in RUNLOG.md.
  Kaggle RUNNING at 14:35: `microduck-ts2-mamba` (two Mamba students, from A-250 and B-500, 140 iterations, expected
  end about 16:05) and `microduck-ts2-ctrl` (one-frame controls universal4 and universal4b, expected about 15:40).
  Both teacher sessions COMPLETE. No paid compute used.
- 2026-11-18 14:30 Teacher A late checkpoints (runtime simulation, same five cases, read by the main session from
  `eval/pk_t2a_*.json`): 625 0/0/0/17/6 = 23; 750 0/0/0/20/0 = 20; 875 0/0/0/20/0 = 20; 999 0/0/0/0/0 = 0
  (0.23 to 0.34 m/s; agent-reported leg torque p99 still at the 0.538 N m clamp). A-999 is the only checkpoint that
  walks COM x +10 mm, and the first policy in this project with zero falls in all five cases above 0.23 m/s. Unlike
  teacher B (55 to 80 ms), teacher A (40 to 65 ms) did not degrade with longer training. Open: 875 to 999 flips COM x
  from 20/20 to 0/20, so a second seed set is being run to rule out a seed accident.
  Main-session decision 14:50 (speed first): cancel the Kaggle session with the A-250 and B-500 students, both
  dominated by A-999, and push Mamba and LSTM students of A-999 at once instead of waiting about 70 minutes for a
  free slot. Modal was considered and not used: the distillation worker has no dollar cap and no tested resume, the
  Modal client is not installed in the project venv, and set-up would have taken most of the time it saved.
- 2026-11-18 14:37 The cancel did not happen (the decision above was made about 14:33, not 14:50): the Kaggle CLI has
  no cancel, the SDK call needs a session id no endpoint returns, and a new version push is refused while two GPU
  sessions run. The only command-line route is `kaggle kernels delete`, a permanent delete, which needs Shawn's own
  confirmation and was not run. Default path: the A-999 students push by themselves (`ts2_push_when_free.sh`, every
  2 minutes) when the control session ends about 15:40, result about 17:25. Shawn can stop `microduck-ts2-mamba` in
  the Kaggle web page to start them about an hour earlier.
- 2026-11-18 14:50 Second seed set (2000 to 2019, 20 episodes each, read by the main session from `eval/pk2_*.json`):
  A-999 COM x +10 mm walk 1/20 falls, shoved walk 0/20; A-875 COM x +10 mm 20/20. The 875 to 999 difference is not a
  seed accident. A-999 students still wait for a free Kaggle GPU session.
- 2026-11-18 15:39 A-999 students pushed to Kaggle as `microduck-ts2-mamba-c` (Mamba on GPU 0, LSTM on GPU 1, 140
  iterations, 1.7 h limit, expected end by 17:25), in the slot freed by the control session. The older student
  session `microduck-ts2-mamba` was never cancelled and runs to about 16:05. Agent-reported quota 12.29 h of 30.
- 2026-11-18 16:35 One-frame controls of round 2 (same universal4 / universal4b recipes without privileged inputs or
  memory), runtime-simulation selection, falls of 20 at none / batteries out / full / COM x +10 mm / shove, read by the
  main session from `eval/pk_c2*.json`. Short delay (40 to 65 ms): 125 = 39; 250 = 27; 375 0/0/4/0/9 = 13
  (0.21 to 0.30 m/s); 500 = 23; 625 = 29; 750 = 61; 875 = 40; 999 20/1/0/15/18 = 54. Long delay (55 to 80 ms): 34 to
  77, none better than the start point (30). Chosen control: c2a_375. Reference: teacher A-999 0, start point 30,
  Mamba-A 24. Finding: loop delay in training also helps a one-frame policy (best 13 against 30), but its checkpoints
  swing between 13 and 61 and the last one is worse than the start point, while the privileged teacher ends at 0.
  The first selection pass failed on every cell (control ONNX exported without metadata); rebuilt from the start
  policy as template and rerun (agent-reported). A-999 students still training, end by 17:25.
- 2026-11-18 17:50 A-999 students finished (Mamba stopped by the 1.7 h cap at iteration 132, LSTM reached 140).
  Runtime-simulation selection, falls of 20 at none / batteries out / full / COM x +10 mm / shove, read by the main
  session from `eval/pk_{s2c,l2c}_*.json`. Mamba: 100 1/0/6/1/5 = 13; 132 0/0/0/12/5 = 17 (0.26 to 0.32 m/s);
  80 = 20; 60 = 20; 120 0/0/1/20/8 = 29. LSTM: 40 = 20; 140 0/0/2/9/11 = 22; 100 = 77. Reference: teacher A-999 0,
  control c2a_375 13, start point 30. The students do not reproduce the teacher in the runtime simulation.
  In the training env they do (`kaggle/out/ts2-mamba-c/runs/ts2-mamba-c/progress.csv`, iteration 132: student 1.19
  falls per env-minute against the teacher's 1.29, speed 0.230 against 0.233, action MSE 0.0042 and still falling).
  So the open gap is between the training env and the runtime simulation, or in what the student must infer without
  the privileged inputs. Checks ordered by the main session: teacher with privileged inputs held constant or zeroed;
  students with dropped reads off / sensor delay 0 / action delay 0; and both students continued to 300 iterations
  on the idle Kaggle session. Agent-reported: older students from A-250 and B-500 best 18 and 13 (the latter barely
  walks), full acceptance of c2a_375 fails 14 lines and s2a_120 fails 9; Kaggle quota 14.44 h of 30.
- 2026-11-18 17:59 `microduck-ts2-mamba-d` pushed and RUNNING (status read by the main session): both A-999 students
  continued to iteration 300 (Mamba from 132, LSTM from 140), beta 0, saves every 20, 2.3 h limit, end by 20:25.
  Agent-reported: `distill_worker.py` gained `--resume-pt` (3-iteration smoke on the Mac mini passed); the old
  checkpoints hold no optimizer state, so Adam restarts; lr-final lowered from 2e-4 to 5e-5 so the rate keeps
  falling. The runtime gap checks run on the Mac mini in parallel with the acceptance batch.
- 2026-11-18 18:10 Mac mini kernel panic and automatic reboot (`panic-full-2026-11-18-181042`: watchdog timeout, no
  watchdogd check-in for 91 s). Cause: the main session ordered the runtime gap checks in parallel with the student
  acceptance batch; at 18:07 the machine (10 cores, 16 GB) had 33 flight-sim workers, 20.56 of 20.99 GB swap used
  and load 21 to 47. Back at 18:11; ports 5180, 5181, 8766 and 5050 answer. All simulation jobs there were lost,
  the Kaggle session is unaffected. Rule from now: one simulation job at a time on the Mac mini, 8 workers at most,
  enforced by a lock and a swap pre-flight in the launch scripts; gap checks first, acceptance after.
- 2026-11-18 18:16 Mac mini limit in place (agent-reported, lock file seen by the main session): `train/mini_lock.sh`,
  one simulation job at a time, pre-flight refuses above 4 GB swap used or 10 simulation processes, evaluator pool
  capped at 8; refusal, stale-lock and queueing tested. Gap checks restarted alone at 18:16.
  First gap-check result (read by the main session from `eval/bc_t2a_999_*priv*.json`): teacher A-999 on a full-pack
  robot with its privileged inputs set to the no-pack constants, with only payload and COM replaced, or all zeroed
  falls 20/20 in the COM x +10 mm and shove cases, at 0.4 to 1.0 s. The teacher's actions depend sharply on the seven
  privileged inputs; a student starting from an empty state cannot know them in the first half second. Ordered next:
  a sanity cell (no-pack robot with no-pack constants must give 0/20) and a precision sweep (payload input x0.9 /
  0.75 / 0.5, COM x input off by 5 and 10 mm, velocity inputs zeroed).
- 2026-11-18 18:50 Runtime gap checks done (falls of 20 at COM x +10 mm walk / shoved walk, read by the main session
  from `eval/bc_*.json`). Teacher A-999 as is 0 / 0. Mamba student s2c_132 as is 12 / 5: dropped servo reads off
  0 / 0; sensor delay 0 20 / 20; action delay 0 20 / 20 (falls from 3.2 s). Teacher drives the first 2 s then hands
  over 8 / 4, first 5 s 6 / 2, all falls after 8.5 s, so the falls are not a cold-start inference problem.
  s2c_100 as is 1 / 5: drops off 0 / 20 (all at 1.2 s); sensor delay 0 1 / 0; action delay 0 0 / 0.
  Reading: the recurrent students are tuned to the exact timing of their training env. The runtime ingredient the
  training env lacks is dropped ticks (robot value 0.036, `microduck-sim/CURRENT-STATE.json`
  servo_read_drop_fraction: the policy is skipped, its state not updated, the last action held), and that alone
  explains s2c_132's falls; neighbouring checkpoints react in opposite ways, so one checkpoint proves nothing.
  Main-session decision: add dropped ticks (0 to 8 % per env) to the distillation env, train one Mamba resumed from
  132 and one from scratch on the free Kaggle session, keep the no-drop continuation as comparison, and accept a
  student only if it holds under the selection cases and all three timing switches.
- 2026-11-18 19:15 Teacher A-999 precision sweep on its privileged inputs, full pack, falls of 20 at plain walk /
  COM x +10 mm walk, one input group changed at a time (read by the main session from `eval/bp_t2a_999_*.json`).
  Sanity (no-pack robot, no-pack constants): 0. Payload input x0.9, x0.75, x0.5: 0 / 0 each (speed falls to 0.16 to
  0.20 m/s at x0.5). Trunk COM x input -5 mm: 10 / 20; -10 mm: 20 / 20; +5 mm: 0 / 0. Velocity inputs zeroed:
  20 / 20. So a student must infer trunk velocity and the fore-aft COM to a few millimetres (one-sided); payload
  mass itself is not critical. Dropped-tick distillation is implemented as a `--drop-max` switch of
  `distill_worker.py` on the audited universal4 env (agent-reported); its smoke is queued on the Mac mini.
- 2026-11-18 18:30 `microduck-ts2-mamba-e` pushed, RUNNING (status read by the main session): Mamba with dropped ticks
  (`--drop-max 0.08`), GPU 0 resumed from s2c_132 for 160 more iterations at beta 0, GPU 1 from scratch for 160
  iterations, saves every 20, 2.3 h limit, end by 20:55. The no-drop continuation `microduck-ts2-mamba-d` keeps
  running as the comparison (end by 20:25). Agent-reported: smoke drop fraction 0.039 to 0.047, export equal to the
  model; Kaggle quota 14.98 h of 30, about 24 h if both sessions run to their limits (26 h is the ceiling that keeps
  4 h unused). Earlier log times after 18:30 in this file were written a few minutes fast.
- 2026-11-18 18:35 Shawn: "如果Mac mini变成瓶颈，那我们就不再依赖Mac mini好了。我们应该是有额度的，还怕什么？用呗。
  如果预计额度会花超，那你用一下Mac mini也无妨。如果额度还可以，就先不用全挤在Mac mini上，阻塞我们的进度吧。"
  Applied: checkpoint selection and timing-switch evaluation move to Modal CPU (`train/flight_eval_modal.py`, one
  container per episode, 0.0473 USD per core-hour plus memory), launched by the main session; the Mac mini keeps one
  serial queue (teacher switch reference, acceptance of s2c_132, comparison table). The round's paid total stays
  under the 10 USD Shawn confirmed; if a projection exceeds it, the work goes back to the Mac mini queue. Modal
  billing summary before the first run: metered 28.37 USD this period, all covered by credits, billed 0.00.
  First run 18:40: 200-episode parity check against the Mac mini results (`eval/spec_md_smoke.json`).
- 2026-11-18 18:50 Teacher A-999 under the timing switches (falls of 20 at COM x +10 mm / shove; files
  `eval/bc_t2a_999_*_{nodrop,sdelay0,adelay0}.json`, agent-reported, file check by the main session below in the
  commit): drops off 0 / 0; sensor delay 0 20 / 20; action delay 0 20 / 20. The teacher itself only walks inside
  the loop delay it was trained on (40 to 65 ms); one tick less is outside that range. Consequences: (1) student
  acceptance = five selection cases plus drops off; the two delay switches are recorded, not required; (2) open
  robustness item for a later round: widen the delay range in teacher training so a policy survives a loop that is
  one tick shorter or longer than the runtime simulation's.
- 2026-11-18 18:38 Modal evaluation parity (main session, `eval/md_*.json`, app ap-L0rKXBydNZWvPoLSHD0sLR, 200
  episodes in 2 min 13 s, about 0.2 USD, no live app left): s2c_132 COM x / shove as is 11 / 6 on Modal against
  12 / 5 on the Mac mini; drops off 0 / 0 on both. Borderline episodes differ by about one in twenty between hosts.
  Same run: s2c_80 with drops off 20 / 0, sensor delay 0 20 / 20, action delay 0 20 / 20. New
  `train/ts2_modal_spec.py` writes the Modal spec for the seven acceptance cells per checkpoint (five selection
  cases plus drops off at COM x and shove) with the Mac mini's file names, skips existing results and prints the
  ranking; about 0.13 USD per checkpoint.
- 2026-11-18 19:10 Full acceptance, read by the main session from `out/accept_t2a_999.json` and
  `out/accept_s2c_132.json` (the information line not counted). Teacher A-999: 10 failed lines, of which falls: stand
  shove 2, stand landing 1, walk landing 1 (4 falls over the 14 with-pack cases against the start point's 37); the
  rest is effort and style: walk torque p99 0.54 N m (limit 0.48, start point 0.53), hip p99 0.42 to 0.47 with
  saturation 1.4 to 3.2 % at half load, three-quarter load and batteries out, toe-out at all three loads (left mean
  up to 14.3 deg against 12). Walks 0.23 to 0.29 m/s. Student s2c_132: 21 failed lines, 35 falls over the 14 cases
  (COM x walk 12, shoved walk 5, mass +10 % walk 4, one or two in most others), hip p99 0.46 to 0.53, toe-out.
  Agent-reported comparison (`out/ts_compare.json`): failed lines start point 10, Mamba-A 11, control c2a_375 14,
  s2a_120 9; adapt_eval of s2c_132 in the training env settles 0.14 to 0.22 s after reset and still falls 4 to 6 of
  64 after a 0.26 m/s push. Reading: the teacher removes nearly all falls but pays with torque at the clamp and
  toe-out; the no-drop student keeps the effort cost and loses the robustness.
- 2026-11-18 20:11 Selection of the no-drop continuation (`microduck-ts2-mamba-d`, ended 19:59; Mamba s2d_140 to
  s2d_300 and LSTM l2d_160 to l2d_300, 17 checkpoints) on Modal, main session, 2380 episodes, app
  ap-JaxWJQfACMbEGfjhlohl9C, estimate 2.2 USD (round total about 2.4 of 10), no live app left. Read from
  `eval/pk_*` and `eval/bc_*` with `ts2_modal_spec.py --table` (falls of 20 at none / nobatt / full / COM x / shove,
  then drops off at COM x / shove). Mamba: 140 0/0/4/11/2 + 20/0; 160 0/0/2/20/10 + 0/0; 180 0/0/1/15/1 + 20/0;
  200 0/0/0/16/6; 220 0/0/0/8/1; 240 0/0/1/7/2; 260 0/0/0/7/0; 280 0/0/0/11/1; 300 0/0/0/7/0 (drops off 0/0 from
  200 on). LSTM: best l2d_220 16 and l2d_240 22, the rest 23 to 43, drops off 20/20 at five of eight. Best:
  s2d_260 and s2d_300, 7 falls each, all at COM x +10 mm with dropped ticks (fall times 0.7 to 3.4 s plus late
  ones at 10 to 15 s); walk 0.23 to 0.34 m/s; leg torque p99 at the 0.538 clamp in every cell, saturation
  fraction up to 0.18 to 0.21 at COM x. Reading: longer distillation without drops took the Mamba student from 17
  (s2c_132) to 7 and cleared the shove; the remaining failure is exactly forward COM plus dropped reads, the case
  the dropped-tick run (`microduck-ts2-mamba-e`, ends by 20:55) trains for. LSTM stays unstable between
  checkpoints and is dropped from further selection unless the dropped-tick run changes that.
- 2026-11-18 20:31 Selection of the dropped-tick Mamba trained from scratch (`microduck-ts2-mamba-e` GPU 1,
  `--drop-max 0.08`, s2f_20 to s2f_160) on Modal, main session, 1120 episodes, estimate 1.0 USD (round total about
  3.4 of 10), no live app left. Falls of 20 at none / nobatt / full / COM x / shove, then drops off at COM x / shove
  (`ts2_modal_spec.py --table`): 20 5/0/6/17/17 + 3/7; 40 0/0/0/9/5 + 0/0; 60 0/0/3/14/5 + 0/0; 80 1/0/0/6/1 + 0/0;
  100 0/2/3/20/11 + 20/0; 120 0/0/0/8/1 + 0/0; 140 0/0/5/17/4 + 20/0; 160 0/0/3/16/3 + 20/0. Best s2f_80 8 and
  s2f_120 9, against the no-drop continuation's s2d_260 / s2d_300 at 7. Reading: at 160 iterations training with
  dropped ticks has not removed the COM x +10 mm failure (6 to 20 of 20) and the checkpoints swing between 8 and
  36, the same swing the no-drop student showed before iteration 200; it is not yet evidence for or against
  dropped-tick training. The resume arm of that session (from s2c_132) crashed with a segfault 70 s in (agent's
  reading: two arms compiling the same kernel cache, not verified); the agent re-pushed `microduck-ts2-mamba-g`
  (ends by 22:50): s2c_132 with drops to iteration 292 (s2g) and s2f_160 with drops to 320 (s2h). Kaggle quota
  18.32 of 30 h, about 23 h if both arms run out.
- 2026-11-18 22:39 Selection of the dropped-tick continuations (`microduck-ts2-mamba-g`, ended 22:28) on Modal, main
  session, 2380 episodes, estimate 2.2 USD. Falls of 20 at none / nobatt / full / COM x / shove, then drops off at
  COM x / shove (`ts2_modal_spec.py --table`). s2g (s2c_132 continued with drops): 140 0/0/0/4/2; 160 0/0/1/7/3;
  180 1/0/1/10/2; 200 0/0/0/6/0; 220 0/0/2/8/0; 240 0/0/0/7/3; 260 0/0/1/8/2; 280 0/0/1/7/2 (all drops off 0/0);
  292 1/0/1/9/1 + 20/0. s2h (from scratch with drops, continued to 320): totals over five 15 to 24, COM x 11 to 20,
  drops off at COM x 20/20 at five of eight. Best s2g_140 and s2g_200 at 6, against no-drop s2d_260 / s2d_300 at 7:
  no difference beyond the one-in-twenty host noise. No student holds COM x +10 mm with dropped reads (4 to 10 of
  20 for the s2g line).
- 2026-11-18 22:55 Dropped-read dose check at COM x +10 mm (Modal, 160 episodes, about 0.15 USD, files
  `eval/dr_*_comx_{d018,d072}.json`; rate 0 and 0.036 from the selection files). Falls of 20 at drop rate
  0 / 0.018 / 0.036 / 0.072: teacher A-999 0/0/0/0; s2d_300 (no drops in training) 0/8/7/14; s2g_140 0/1/4/8;
  s2g_200 0/2/6/14. Reading: the students' falls at forward COM rise with the dropped-read rate and vanish at zero,
  while the stateless teacher is untouched even at twice the robot's rate; training with drops helps at half the
  rate (1 to 2 against 8) and not at the robot's rate or above. The remaining gap is therefore in how the recurrent
  student carries its state across a skipped tick at forward COM, not in the teacher or the walk itself. Round paid
  total about 5.8 of 10 USD; no live Modal app; Kaggle 20.33 of 30 h; nothing running on Kaggle or the Mac mini.
- 2026-11-18 23:25 State catch-up diagnostic (agent on the Mac mini under the lock, files `eval/cu_*.json` read by the
  main session; switch FLIGHT_CATCHUP=1 in `flight_eval.py`, default off): on a call after skipped ticks the
  recurrent state is first stepped once per skipped tick on the previous observation. Falls of 20 at COM x +10 mm
  with the switch against without (Modal reference): s2d_300 8 / 7; s2g_140 2 / 4; s2g_200 7 / 6; s2g_200 at drop
  0.072 13 / 14; s2g_200 plain full-load walk 0 / 0. No effect beyond host noise. The main session's guess (the
  state standing still over a skipped tick causes the falls) is refuted. Caveat from the agent: no counter confirms
  the catch-up branch fired; episodes differ from the reference. Still open: why the stateless privileged teacher
  rides through a held action at forward COM and the students do not. Round 2 ends here on results: teacher A-999
  0 of 100 in selection; best students s2g_140 / s2g_200 6 and s2d_260 / s2d_300 7, all remaining falls at forward
  COM with dropped reads. Any further training is a new direction and waits for Shawn's nod.
- 2026-11-19 00:10 Cause diagnosis on Shawn's "先查原因" (agent on the Mac mini under the lock; main session read
  `out/ts2_cause_swap.json`, `ts2_cause_shadow.json`, `ts2_cause_parity.json`; every switch has a fire counter).
  COM x +10 mm, drop 0.036, seeds 0 to 19, falls of 20 for s2g_200 | s2d_300. Student alone 7 | 8, drops off 0 | 0.
  Teacher action on the 1 tick after each skipped tick 5 | 11, on 3 ticks 4 | 10, on 3 ticks at random times
  (control) 8 | 10. Reverse, teacher drives and the student acts on the 3 ticks after each skip 0 | 0. Teacher with
  Gaussian action noise 0.08 rad 0, with 0.15 rad 16 (12 with drops off). Teacher drives the first 2 s, then the
  student alone 1 | 2; first 4 s 1 | 5. Shadow log: leg |student - teacher| median / p90 on the first tick after a
  skip 0.053 / 0.138 against 0.051 / 0.130 with no skip nearby (s2g_200), so skips do not enlarge the difference;
  falls cluster before 4 s (5 of 7 | 7 of 8), seeds 0 and 11 fall at 0.7 to 0.8 s before the walk command starts
  at 2.0 s; in the first 2 s at zero command the student walks forward at 0.084 | 0.087 m/s (teacher 0.006).
  Parity at a skipped tick (last-action slot, joint and IMU reading age, delay queues): no mismatch between
  runtime simulation and training; only the heading-hold turn command steps more after a skip (median 0.040
  against 0.022 rad/s), also present with drops off. Verdict: the actions right after a skipped tick are not the
  cause; the student's start from an empty state at forward COM is (it creeps instead of standing, then meets the
  walk onset near the edge, where a dropped read tips it). The earlier handover result on s2c_132 (8 and 6 of 20)
  was a less trained checkpoint. Not settled: whether the start fails for lack of coverage in distillation or
  because the COM cannot be inferred before motion; follow-up check dispatched (`out/ts2_cause_start.json`).
- 2026-11-19 01:00 Start-up cause (agent on the Mac mini under the lock; main session read
  `out/ts2_cause_start.json`). s2g_200, COM x +10 mm, drop 0.036, seeds 0 to 19, falls of 20. Empty state 7 (walks
  0.084 m/s at zero command in the first 2 s, 16 of 20 episodes creep above 0.05 m/s); warm state taken from the
  end of a finished episode with the same pack 0, no creep (0.005 m/s); warm state taken from a no-pack episode
  20, all at 0.54 to 0.58 s. Empty state at zero command for 20 s: 2 falls (0.70, 0.82 s), creep ends by itself
  after 2 s. Empty state with nominal pack or no pack 0 falls, creep 0.024 and 0.007 m/s. Landing start with empty
  state 13 (12 before 2 s), teacher 0. Reading: the recurrent state holds the load and COM estimate; correct state
  = no fault, wrong state = immediate fall, empty state needs about 1.5 s of motion to converge and the robot
  creeps meanwhile. Coverage is not the cause (agent-reported from code and a 256-env CPU run: 19.4 % of resets
  start at zero command, state zeroed at every reset, COM range reaches +11.5 mm; in the distillation env the same
  empty start creeps only 0.004 to 0.008 m/s, 1 to 4 falls of 256). Not separated: why the empty start is harmless
  in the distillation env and harmful in the runtime simulation (start pose, neck pitch off by 0.099 rad, and loop
  timing remain). Consequence for the product goal: a pack swap with the policy running needs a state reset or a
  re-warm, because the old pack's state on the new pack falls 20 of 20. Next check dispatched, no training: a
  deployable 61-input policy drives the first 1 to 2 s at zero command while the student builds its state
  (`out/ts2_warmup.json`).
- 2026-11-18 23:41 Clock correction: the two entries above stamped "2026-11-19 00:10" and "01:00" were written at
  about 23:05 and 23:30 on 2026-11-18. Warm-up rule on Modal (main session, 540 episodes in about 2 min, about
  0.5 USD, round total about 6.3 of 10; `flight_eval_modal.py` now passes an "env" dict per eval so FLIGHT_*
  switches run there; files `eval/wm_ts_start_*.json`). Driver = start-point stand policy for the first N ticks,
  student shadows, then drives. Falls of 20, N=100, s2g_200 | s2g_140: none 0 | 0, nobatt 0 | 0, full 0 | 0,
  COM x 12 | 6, shove 4 | 4, COM x drops off 0 | 0, shove drops off 0 | 0, COM x drop 0.072 13 | 9, COM x landing
  11 | 9. N=50, s2g_200: COM x 10, shove 2, COM x 0.072 15, landing 7. Five COM x falls are at 0.86 to 1.58 s,
  inside the warm-up: the start-point stand policy itself falls at forward COM with dropped reads. Verdict: the
  rule is refuted with this driver (worse than no warm-up: 6 and 4 at COM x, 0 at shove), and the robot's current
  overlay policies fall 20 of 20 with the pack, so no deployable driver exists. Shawn asked why the check sat in
  the Mac mini queue: it did because the Modal evaluator could not pass the diagnostic switches; fixed in this
  entry, diagnostics go to Modal from here (agent allowance 1.5 USD). Next, no training: separate what makes the
  empty-state start harmful in the runtime simulation and harmless in the distillation env.
- 2026-11-18 23:50 Shawn: "不需要我点头吧？你自己排查原因，然后自己去开训就行了。搞快一点，不要搞很久。我们背包其实已经可以装了，
  材料都到了，就在等你这个模型训练。" The fix round is launched without a further nod; the pack hardware is waiting on
  this model. Route chosen by the main session: correct the student directly in the runtime simulation (DAgger in
  the target simulator: the student drives runtime episodes from an empty state on Modal, teacher A-999 labels every
  tick, fine-tune s2g_200 on the aggregated data, held-out seeds 0 to 19 and 2000 to 2019 for evaluation). It does
  not need the cause of the env gap; the start-gap diagnosis is cut to the batch already running. Success = held-out
  COM x 0 to 1 of 20 with the other six cells 0 and zero-command creep under 0.02 m/s; report at once if round 2
  does not move the COM x cell. Modal allowance for the task 3.5 USD (round total under 10).
- 2026-11-19 00:16 Runtime-simulation DAgger round 1 (agent; main session read `out/dagger/eval_s2r1_8.json`).
  s2r1_8 = s2g_200 fine-tuned on 600 runtime episodes (527,955 called ticks, seeds 10000 to 10599, teacher labels
  on all ticks). Held-out seeds 0 to 19, falls of 20: none 6, nobatt 0, full 0, COM x 20, shove 17, COM x drops off
  20, shove drops off 20; COM x drop 0.072 20, landing 20, stand-only COM x 0. The start is fixed (zero-command
  creep at COM x 0.016 m/s against 0.084) and the walk is broken: 0.32 m/s, falls at the shove (8.44 s) and at the
  end of the walk command (17.22 s). Agent's reading (inference): imitating the teacher on all ticks from this
  small pool overwrote what the distillation had taught about shoves and stopping. Next, already running: same
  data, teacher labels only on the first 150 called ticks (3 s), the student's own recorded action as the target
  afterwards (s2r1a). Modal spend for the task about 0.8 USD (round total about 7.1 of 10).
- 2026-11-19 00:50 DAgger round 2 (agent; main session read `out/dagger/eval_s2r2_4.json`). s2r2_4: pool of rounds
  1 and 2 (1800 episodes, 911,199 called ticks), teacher labels on the first 150 called ticks with weight 5, the
  collecting student's own action as the target afterwards. Held-out seeds 0 to 19, falls of 20: none 0, nobatt 1
  (18.62 s), full 0, COM x 3 (3.20, 5.74, 17.38 s), shove 0, COM x drops off 0, shove drops off 0: seven cells 4
  (s2g_200 6). Outside the seven: COM x drop 0.072 9 (was 14), landing 5 (was 13), stand-only 0. Zero-command creep
  at COM x 0.010 m/s (was 0.084). Remaining COM x falls sit about 1 s after the walk command starts, at the edge
  of the 3 s teacher-label window. Round 3 launched by the agent: 1000 episodes of 10 s, teacher labels on the
  first 250 ticks. Modal spend for the task about 2.0 to 2.6 of 3.5 USD (agent's estimate).
- 2026-11-19 01:25 DAgger round 3 (agent; main session read `out/dagger/eval_s2r3_3.json`, `_s2000.json`,
  `eval_s2g_200_s2000.json`). s2r3_3: pool of three rounds (2800 episodes, 1,377,296 called ticks), teacher labels
  on the first 250 ticks, own-action anchor afterwards. Falls of 20, seeds 0 to 19 | 2000 to 2019: none 0 | 0,
  nobatt 0 | 0, full 0 | 0, COM x 3 | 1, shove 0 | 1, COM x drops off 0 | 0, shove drops off 0 | 0; seven cells
  3 | 2 (s2g_200: 6 on the first set; COM x 6 and shove 1 on the second). Outside the seven: drop 0.072 5 | 4
  (s2g_200 14 | 11), landing 4 | 5 (13 | 11), stand-only 0 | 0. Zero-command creep at COM x 0.0095 | 0.008 m/s
  (0.084 | 0.110). Remaining COM x falls at 15.3 to 17.4 s (late walk and the stop), outside the teacher-labelled
  window; neighbouring epoch s2r3_6 is worse (COM x 4, shove 2), so the cells are at the noise level of 20 seeds.
  Bill check by the main session: `modal billing summary` metered 29.33 USD against 28.37 before the first
  evaluation run at 18:40, so the whole round has really cost about 1 USD; the per-episode estimates in the
  entries above (totals of 5.8 to 7.1 USD) were about ten times too high. Round 4 on: 3000 full-length episodes
  per round, teacher labels over the whole episode with a decreasing own-action anchor, selection on 60 held-out
  seeds per cell; spend tracked by the bill (keep metered under 35.00).
- 2026-11-19 01:55 DAgger round 4 (agent; main session read `out/dagger/eval60_*.json`). s2r4_1: pool of four
  rounds (5800 episodes, 4,171,787 called ticks), teacher labels over the whole episode plus an own-action anchor of
  weight 1 after tick 250, first saved epoch. Falls of 60 per cell (seeds 0-19, 2000-2019, 3000-3019), none /
  nobatt / full / COM x / shove / COM x drops off / shove drops off: s2r4_1 0/0/0/0/1/0/0 = 1 of 420; s2g_200
  0/0/0/18/3/0/0 = 21; s2r3_3 7. Outside the seven (drop 0.072 / landing / stand-only at COM x): s2r4_1 4/3/0,
  s2g_200 39/37/7. Check on seeds never used for the pick (4000-, 5000-, 6000-): s2r4_1 0/0/0/0/1/0/0 = 1, extra
  2/6/0; s2g_200 0/0/0/21/1/0/0 = 22, extra 40/30/8. Zero-command creep at COM x 0.0062 m/s on both sets (s2g_200
  0.101 and 0.093). Stop rule met. Caution: the next saved epoch s2r4_2 collapses (161 of 420, COM x 60 of 60), so
  the fine-tune is not stable from epoch to epoch and s2r4_1's standing rests on its own 120 held-out seeds per
  cell; no further training on this pool. Full acceptance, agent-reported: s2r3_3 12 failed lines (s2c_132 21,
  teacher 10, start point 10); s2r4_1 acceptance running on the Mac mini. Bill: metered 30.12 USD (baseline 28.37,
  so about 1.8 USD for the whole round).
- 2026-11-19 03:45 Full acceptance of s2r4_1 (agent on the Mac mini; main session read
  `logs/accept_score_s2r4_1.log`): 10 failed lines (teacher 10, start point 10, s2c_132 21, s2r3_3 12). Falls over
  the 14 with-pack cases 5 (start point 37): rear COM (comx-10) stand 2 and walk 2 of 20, same two seeds at 1.28
  and 1.66 s in the start; shoved stand 1. Forward COM stand and walk 0, shoved walk 0, both landings 0, mass +10 %
  0, no-pack 80 episodes 0, head-motion lines pass at all three loads. Effort and style lines fail as for the
  teacher: walk torque p99 0.54 N m (limit 0.48), hip lines at load050 (saturation 1.4 %), load075 (p99 0.45,
  3.9 %), nobatt (p99 0.467, 3.6 %), toe-out at none / nobatt / full (left mean up to 13.7 deg against 12, p95 up
  to 17.5 against 15). Walk 0.25 to 0.34 m/s. New weak point outside the seven selection cells: the start at rear
  COM (agent's inference: the forward-creep correction took some rear margin; s2g_200 fell 0 of 49 at comx-10 in
  round-1 collection, s2r3_3 8 of 163 in round 4). Round 5 launched on the main session's decision: nine selection
  cells (adds comx-10 stand and walk), comx-10 sampled as heavily as comx+10, half learning rate, at least 8
  evaluated checkpoints, stop at 3 of 540 with no cell above 2 of 60. Bill 30.09 to 30.20 USD metered.
- 2026-11-19 02:54 Clock note: the entry above stamped 03:45 was written at about 02:10. DAgger round 5 (agent; main
  session read `out/dagger/eval60_s2r5_{2,8,avg}*.json`). Pool r1 to r5, 8800 episodes; learning rate 2.5e-5,
  gradient clip 1.0, eight checkpoints plus a weight average. Nine cells (the seven plus rear-COM stand and walk),
  falls of 540, seeds 0/2000/3000 | 4000/5000/6000: s2r5_2 4 | 3, s2r5_8 4 | 4, s2r5_avg 4 | 9, s2r4_1 9 | 13.
  The seven original cells: s2r5_2 0 | 3 (COM x 2, shove 1), s2r5_8 0 | 2. Rear COM: s2r5_2 2 and 2 | 0 and 0,
  s2r5_8 2 and 2 | 1 and 1; stand and walk fall on the same episodes before the walk command, so the pair counts
  one fault twice. Curve over the eight checkpoints 18, 4, 10, 11, 9, 12, 10, 4: still uneven. Report cells for
  s2r5_avg (60 each, two groups): COM x drop 0.072 8 | 3, forward-COM landing 8 | 6, rear-COM landing 5 | 9, COM y
  +10 walk 3 | 3, COM y -10 walk 0 | 0. Stop line (3 of 540, confirmed) not met; round 6 running with landing
  starts at 22 % of episodes, s2r5_8 driving. Main session: round 6 is the last, then pick on the six-group sum and
  run the full acceptance. Bill 31.17 USD metered (baseline 28.37).
- 2026-11-19 03:47 DAgger round 6, the last (agent; main session read `out/dagger/eval60_s2r6_4*.json`). Pick
  s2r6_4. Nine cells, falls of 540, seeds 0/2000/3000 | 4000/5000/6000: 2 | 3 (rear-COM stand 1 and walk 1 on each
  group, the same episode counted twice; forward COM 0 | 1; all other cells 0). Eight distinct cells x 120 seeds:
  s2r6_4 3 of 960, s2r5_2 5, s2r5_8 5 (agent-reported sums). Zero-command creep at forward COM 0.0064 m/s. The
  round's nine candidates range 2 to 15 on the selection group, so only this one beats round 5 and 3 against 5 of
  960 is inside the noise; it is the pick by the stated rule. Collection r6: 3000 episodes, s2r5_8 driving.
  Full acceptance of s2r6_4 running on the Mac mini, report cells on Modal.
- 2026-11-19 04:50 Final result of the fix round (agent; main session read `logs/accept_score_s2r6_4.log` and
  `out/dagger/eval60_s2r6_4*.json`). Pick `train/ckpt/s2r6_4` (walk61.onnx, stand61.onnx, model_4.pt). Full
  acceptance: 9 failed lines (s2r4_1 10, teacher 10, start point 10, s2c_132 21). Falls over the 14 with-pack cases
  3 (start point 37): nominal landing stand 1, nominal landing walk 1, plus one in a line that still passes
  against its reference. Forward-COM stand and walk, rear-COM stand and walk, shoved stand and shoved walk, mass
  +10 %, no pack (80 episodes), head motion at three loads: all pass. Effort and style fail as for the teacher:
  walk torque p99 0.54 N m (limit 0.48); hip p99 / saturation at load050 0.431 / 1.9 %, load075 0.461 / 4.1 %,
  nobatt 0.477 / 4.0 %; toe-out at none / nobatt / full (left mean 11.4 to 13.3 deg against 12, p95 up to 17.9
  against 15). Walk 0.24 to 0.34 m/s. Report cells, falls of 60 on the two seed groups: forward-COM drop 0.072
  3 | 3, forward-COM landing 10 | 9, rear-COM landing 3 | 7, COM y +10 walk 4 | 2, COM y -10 walk 0 | 0,
  forward-COM stand 0 | 0. Weakest remaining case: the landing start at forward COM (19 of 120). No round 7.
  Modal bill 32.52 USD metered against the 28.37 baseline: 4.15 USD for everything since 18:40, under the 10 USD
  cap; no live app. Open for a later round (teacher retraining): torque and hip effort, toe-out, delay-range
  robustness. Next, dispatched: runtime support for the recurrent policy in the repository with a tick-for-tick
  parity test and a deployment checklist; nothing deployed.
- 2026-11-19 04:20 Clock note: the entry above stamped 04:50 was written at about 04:00. Robot-trial readiness of
  s2r6_4 in the repository (agent commit 37aaf151; main session read the diff, `train/out/ts2_runtime_parity.json`
  and `ts2_policy_cost.json`). `guide/firmware/mac/walk_brain.py` now runs policies with a `state_in` input: state
  fed back, kept over up to 5 skipped control ticks, zeroed on entry after a longer gap, shared by walk61 and
  stand61 of one file, reset by `reset_policy_state()` or a new `policy_reset` value in the command file; plain
  61-input policies take the old `sess.run` path. Parity with the evaluation wrapper: 15 episodes (forward COM,
  shoved nominal, no pack; seeds 0 to 4; default drops), 14,476 policy ticks, 524 skipped ticks, same ticks and
  slots, max action difference 0.0, no falls on either side. One call, one thread: s2r6_4 0.058 ms against 0.008 ms
  for the current walk61 on the Mac mini (7.1x); the A7Z is not measured (agent's estimate 2.5 to 9 ms of the 20 ms
  tick, from the 0.6 to 1.3 ms noted for 61-input policies in walk_brain). Checklist: RUNLOG.md section
  "Robot-trial readiness of s2r6_4". Not done and not verified: nothing copied to the A7Z; whether the A7Z's code
  matches the repository (last recorded hash 2026-10-23); the team-repo copy `microduck_rl/cmu/mac/walk_brain.py`
  is not synced; `deploy_policy.py` only accepts single-input models; CURRENT-STATE.json entries servo_rail_v,
  walking_policy, walk_speed_vx025 are STALE. The robot trial waits for Shawn's word.

### 2026-11-19 15:45 s2r6_4 on the A7Z (Shawn: "可以，上机"), files and timing only, no motion yet

- A7Z tree against the repository before the copy: `walk_brain.py` and `walk_wired.py` on the A7Z are dated 2026-11-13 16:23 and carry a pick revision (`PICK_REVISIONS`, `seepickpix_r161.onnx`, `rise_old`) that is in no commit of this repository; the repository has `write_run_meta` and the IMU placeholder print the A7Z lacks. Overwriting would have removed the pick revision, so the recurrent change (37aaf151) was merged onto the A7Z file with `git merge-file` (clean, compiles). Copies kept in `microduck-sim/extensions/flight-20261110/train/a7z-20261119/` (before and merged). The session that wrote the pick revision is not found (`transcript_search.py PICK_REVISIONS`, `seepickpix_r1`: 0 sessions); open item: bring that code into the repository.
- Copied: `~/policies/s2r6_4/` (walk61 = stand61 sha256 3b509e76fb33, plus copies of the eight other deployed files), merged `walk_brain.py` (sha256 019565e3edab, previous file `walk_brain.py.bak-20261119`), `~/duck-policy` -> `/home/radxa/policies/s2r6_4`. `walk_wired.py` on the A7Z unchanged.
- One policy call on the A7Z (`ts2_policy_cost.py`, 1000 calls, SoC 34.6 C): recurrent median 0.53 ms, p99 0.75, max 0.91; current walk61 0.12 ms; ratio 4.4. The earlier 2.5 to 9 ms guess was far too high.
- Brain started with the new set (`duck_wired_s2r6_1119a.out`, monitor mode, no goals sent): loads without an assertion, 49.7 Hz, IMU 196/s, battery 8.1 V, robot lying on its side.
- Shawn: the jet pack is not fitted yet; first test is plain standing with the remote. Scope note for him: s2r6_4 replaces stand and walk only; pick, sit and kick are the unchanged deployed policies.
- CURRENT-STATE.json `walking_policy` carries the trial under `on_trial`.

### 2026-11-19 16:00 s2r6_4 fails on the robot at standstill: action chatter the simulation does not punish

- Robot, no jet pack, Shawn on the remote (log `duck_wired_log_s2r6_1119a.jsonl`; last 9000 rows kept as `microduck-sim/extensions/flight-20261110/train/a7z-20261119/robot_s2r6_4_stand_fall.jsonl`, scripts `an1.py`, `an2.py` beside it). Stand mode held level. Walk mode at zero command (stand61 slot): 192 ticks, 4.4 s, then "STOP -> stand: body tilt over 30.0 deg". 8 skipped ticks.
- What the policy did: from the first tick the leg actions are 0.5 to 1.1 rad and flip sign every few ticks. 76 tick-to-tick jumps over 0.5 rad in 4.4 s (172 per 10 s), median step 0.40 rad, action rms 0.48 rad, gyro rms 1.2 to 1.5 rad/s, leg current median 0.66 A, peak 3.9 A. Loop 43 to 47 Hz in walk mode (the 2026-11-17 walk61 run on the same board: 46 to 48 Hz).
- The simulation had the signal and the selection ignored it. `action_jumps` median per 15 s walk episode, no pack: deployed walk61 2, start point ts_start 3, teacher t2a_999 63, s2r6_4 68.5 (118 at COM x +10 mm). Every student inherits the teacher's chatter; torque p99 at the 0.54 N m clamp was the same symptom. CURRENT-STATE.json `walking_policy` already records that candidates with 5 to 27 jumps per 10 s (ft3, t1) fell on this robot while walk61 (0 to 10) walks. Round 2 selected on simulated falls only. This failure was predictable before the robot test and I did not state it.
- Gap, stated as a mechanism: the simulated servos and floor absorb a 0.4 rad per tick chatter (the robot stays up in simulation), the real ones turn it into trunk motion, which feeds back through the IMU into larger actions.
- Robot back on the deployed set 15:26 A7Z clock (`~/duck-policy` deleted, brain restarted, monitor mode, upright). A7Z call time and merged runtime stay valid.
- Not done: the simulated standstill tick log of s2r6_4 for a like-for-like step size (MacBook swap 14.6 of 15.4 GB, Mac mini swap 4.4 GB over the lock's 4.1 GB limit at 15:24).

### 2026-11-19 16:40 Like-for-like standstill in simulation: the chatter is absent, not under-reported

- Runtime simulation, no pack, stand mode 0.3 s then walk mode at zero command for 20 s, seed 0, default dropped reads (`microduck-sim/extensions/flight-20261110/train/ts3_like.sh`, statistics `ts3_chatter_stats.py`, result `train/out/chatter/like_base_stats.json`, tick logs `like_base_s2r6_4.jsonl`, `like_base_walk61.jsonl`).
- s2r6_4 simulated: 1 jump over 0.5 rad in 19.7 s (0.5 per 10 s), median step 0.001 rad, p90 0.004, action rms 0.26, gyro rms 0.05 / 0.08 / 0.17 rad/s, no fall, 48.3 policy ticks/s. Robot: 172 per 10 s, median step 0.40 rad, gyro rms 1.2 to 1.5, fall at 4.4 s, 41.6 policy ticks/s (184 in 4.42 s).
- walk61 simulated: 0 jumps, median step 0.002 rad, action rms 0.08, gyro rms 0.003 / 0.03 / 0.015.
- The entry is the same in both worlds: first three s2r6_4 actions on joint index 4 are -0.83, -1.14, -1.16 in simulation and -0.77, -1.01, -0.95 on the robot (same stand pose, body gravity x -0.072 against -0.055). After that they part: simulated steps fall to 0.014 rad by 0.5 to 1 s and 0.002 by 2 s; the robot stays at 0.42 to 0.47 rad per tick, eases to 0.27 at 2 to 3 s, then grows to 0.67 and falls.
- So the simulated loop is stable at standstill and the real loop is not: the policy's start kick decays in simulation and is sustained on the robot (largest spectral line of the busiest joint 2.7 Hz, plus tick-to-tick sign flips). The 68.5 jumps per 15 s in the walking cells measure something else (a rough gait); a standstill jump gate on today's simulation would have passed s2r6_4. Next: find the simulation condition that sustains it.

### 2026-11-19 17:40 Matched cell for the s2r6_4 standstill fall: position gain 400 in the runtime simulation

- Sweeps on Modal, no pack, s2r6_4 against the deployed walk61, standstill (zero command 20 s) and walking (vx 0.25, 15 s): `microduck-sim/extensions/flight-20261110/train/ts3_gap_sweep.py`, results `train/out/chatter/gap_a.json` (25 conditions, 3 seeds, standstill), `gap_b.json` (13), `gap_c.json` (7), `gap_d.json` (2 conditions, 10 seeds). 470 episodes, Modal metered 32.45 to 32.49 USD.
- No effect on the s2r6_4 standstill (0 to 0.5 jumps per 10 s, no fall): action delay 2 ticks, 43 Hz loop (new switch `FLIGHT_SLOW_LOOP_MS=3.2`), BAM friction x0.2 / 0.5 / 1.5, joint play 1 / 2 / 4 deg, foot play 2 deg, supply 8.2 V, 35 Hz IMU with 8 % drops, floor friction 0.5, softer soles, position gain 250 and 300. Not usable: sensor delay 2 or 3 ticks and IMU delay +1 tick end both policies the same way with zero jumps (the Brain treats the sample as too old; the jitter study found the same).
- The jitter study's matched condition of 2026-10-30 (gyro noise 0.25 x rms leg joint speed, BAM friction x1.4; `guide/firmware/mac/jitter-20261018/README.md`, now also `FLIGHT_GYRO_NOISE_DQ` in `flight_eval.py`): s2r6_4 falls while walking 3 of 3 at 2.8 to 4.0 s with 95 to 137 jumps per 10 s, walk61 walks 3 of 3 with 18 to 22; the s2r6_4 standstill stays quiet (0.5 to 1), because that noise needs leg motion.
- Position gain (`--kp-rl`, the Brain's KP_RL, 200 on the robot) is the one switch that reproduces the standstill: at 350 s2r6_4 chatters at standstill (13 to 34 jumps per 10 s) and falls walking 3 of 3; at 400 on 10 seeds it falls at standstill 7 of 10 (1.5 to 8.6 s, median 2.9 s; robot 4.4 s) with 15 to 137 jumps per 10 s (median 79; robot 172) and falls walking 10 of 10, while walk61 stands 10 of 10 with 0 jumps and walks 8 of 10 (10 to 58 jumps per 10 s; robot ledger 63 of 67 walks upright). At 425 walk61 falls walking 7 of 10, at 450 it falls standing: too harsh. One standstill tick log at 400 (`train/out/chatter/like_kp400_stats.json`): 97.5 jumps per 10 s, median step 0.32 rad (robot 0.40), gyro rms 1.1 / 1.8 / 2.2 rad/s (robot 1.2 / 1.3 / 1.5), busiest action index 12 in both.
- Gain plus vibration together (350 with 0.25, 400 with 0.15) drop s2r6_4 at standstill 3 of 3 in 1.5 to 7.4 s but also drop walk61 while walking 3 of 3, so they are not the cell.
- What gain 400 stands for (inference, not measured): it doubles the loop gain around the policy. It is not a claim that the real servos are twice as stiff: in the robot log the leg servos follow the chattering goals less than the simulated ones at gain 400 (position std over goal std 0.35 to 0.45 against 0.6 to 0.7; `train/ts3_servo_response.py`, `train/out/chatter/servo_response.json`), while the trunk gyro is as large. The robot turns a given joint motion into more trunk rate than the model (the 2026-10-17 jitter finding: joints 1.5 to 2x, trunk gyro 4 to 6x). The cell is a stand-in for that missing gain, chosen because it separates the two policies the way the robot did.
- Required cell from now on: `gain400` = `--kp-rl 400`, no pack, standstill and walking, judged against walk61 in the same cell.

### 2026-11-19 18:30 Chatter gates: every policy of the flight lineage fails them, the "smooth" start included

- Gate script `microduck-sim/extensions/flight-20261110/train/ts3_gates.py` (spec, Modal run, score; exit 1 on any failed line), wired into `train/ts_accept.sh` before the acceptance run: a candidate that fails gets no acceptance and no robot checklist. Lines, 10 seeds each, reference = the deployed walk61 in the same cell: G1 action distance from walk61 on walk61's own robot walks at most 0.25 rad (the t2b gate; log copied to `train/gates/walk61_see_walks.jsonl`, 649 states, 5 walks; recurrent state carried inside a walk); G2 no pack as simulated, G3 no pack gain400, G4 nominal pack as simulated, G5 nominal pack gain400, each standstill and walking, on falls and on action jumps over 0.5 rad per 10 s (limit max(1.5 x walk61, walk61 + 2)).
- Check of the G1 code against a recorded value: t1 gives 0.711 rad, the figure of 2026-10-30; walk61 against itself 0.0; ft2-it125 0.194.
- walk61 reference (`train/out/gates/gates_s2r6_4.json`, key walk61): standstill 0 falls and 0 jumps in both cells; walking as simulated 0 falls, median 0.75 jumps per 10 s; walking gain400 2 falls of 10 (6.6 s, 17.9 s), median 18.5.
- s2r6_4: FAIL, 11 lines (`train/out/gates/gates_s2r6_4.json`). G1 1.099 rad. Walking as simulated 33.75 jumps per 10 s against a limit of 2.75; gain400 standstill 7 falls of 10, walking 10 of 10; pack walking 72 jumps per 10 s; pack gain400 standstill 8 of 10, walking 10 of 10. The gates would have stopped it on the first line.
- ts_start, the lineage's low-jump start: FAIL, 8 lines (`gates_ts_start.json`). G1 1.454 rad. It passes G2 (walking 1.5 jumps per 10 s) and still falls at gain400: standstill without pack 8 of 10 (4.1 to 12.4 s, median 95.85 jumps per 10 s), walking 10 of 10 without and with the pack; pack walking as simulated 3.5 jumps against 2.75. Low jump count in the simulation as it is does not mean robust to loop gain.
- Teacher t2a_999 (`gates_t2a_999.json`, no G1): FAIL, 10 lines: walking 32.5 jumps per 10 s without pack, 68 with; gain400 walking 10 of 10 falls without pack, pack gain400 standstill 10 of 10.
- Consequence for the training fix: starting from ts_start does not carry walk61's robustness. The only policy that passes G3 is walk61, and every flight policy sits 1.1 to 1.5 rad from it on robot states. The fix starts from or anchors to walk61 and trains under position-gain randomisation that includes 400, with the smoothness terms.
- Modal: 280 episodes, metered 32.50 to 32.52 USD; `modal_watch.py` clean.

### 2026-11-19 19:00 Chatter fix: literature note and the training design (universal5t)

Clock note: the headings 16:40, 17:40, 18:30 and 19:00 of this round were stamped ahead of the real clock (EST). Real times: about 14:10, 15:00, 15:40 and 16:05. Entries from 19:30 on carry the real clock.

### 2026-11-19 19:30 universal5t: incentive audit fixed and passed, smoke passed, teacher pair launched on Kaggle

- Three hours lost (16:05 to 19:14): the audit chain ran as a background shell of the session and was stopped five minutes after the turn ended, with its Mac mini job. Chains that outlive a turn now run detached: on the Mac mini `train/ts3_mini_chain.sh` started by `train/ts3_mini_start.sh` (parent launchd, heartbeat `~/flight-heartbeat/<name>.txt` there); on the MacBook light watchers through `train/detach.py`.
- First audit (weights action rate -2, action acceleration -0.6, progress 8; `train/out/audit_g1_none.json`): FAIL at no pack on one line, stepping in place earns 0.84 of the intended walk (line 0.80); stand 0.732. Priced offline from the same rollouts: with the old audited weights it is already 0.803 once the position gain is drawn 0.8 to 2.2, because ts_start walks worse there (6.5 falls per env-minute, 0.121 m/s). So the gain range itself made not walking pay; the gate was kept and the incentive changed: progress along the command 8 to 14.
- Second audit (`train/out/audit_g2_{none,full,nobatt}.json`, 128 envs, 250 steps, gate recorded in `train/out/audit_gate.json` for universal5t and universal5): PASS at every load. Share of the intended walk's reward: no pack stand 0.612, step in place 0.709, lean forward 0.503, lean back 0.534; full pack 0.453, 0.503, 0.424, 0.458; batteries out 0.502, 0.618, 0.442, 0.460.
- Smoke on the Mac mini in the launch configuration (delta universal5t, anchor on, 64 envs, 5 PPO iterations, both start policies; logs `~/flight-heartbeat/ts3smoke_smoke_{a,b}.log` there): env 68 inputs, iteration-0 export equals the start policy (0.0), exports reproduce the actor (6e-07, 3e-07), anchor steps run on 408 no-pack rows. Leg distance to walk61 on those rows at the start: 1.39 rad from ts_start, 0.44 rad from walk61 itself (the target is walk61 with the head command zeroed, so this is how much walk61's legs move with the head command).
- Launched 19:26, Kaggle kernel `microduck-ts3-teach-a`, two T4: `ts3-teach-a` from ts_start and `ts3-teach-b` from walk61, both delta universal5t, 1000 iterations, warm-up 100, learning-rate clamp 1e-4, save every 125, `--max-hours 1.6`. In-trainer stop on the task metric: `--track-guard 2.0` (velocity-tracking error over twice the warm-up value, or speed along the command under half of it, or under 0.03 m/s on 0.15 to 0.30 m/s commands, on two saves); the reward guard is off. Quota 20.34 h used before; plan about 1.7 h, so about 22.0 of the 26 h ceiling.
- After the kernel: `train/ts3_after_teach.sh` (detached, heartbeat `train/logs/ts3_teach_heartbeat.txt`) fetches, stages every save as `ckpt/t3a_<iter>` and `ckpt/t3b_<iter>` and scores the chatter gates on Modal (8 cells, 10 seeds, teacher mode).
- Sourced note: `microduck-sim/extensions/flight-20261110/train/CHATTER-LITERATURE.md` (Lipschitz-constrained policies arXiv 2410.11825, CAPS arXiv 2012.06644, Disney BDX arXiv 2501.05204, gain randomisation arXiv 2401.16889 and 2510.07094, BAM friction arXiv 2410.08650, the behaviour-cloning anchor of Wolczyk et al. ICML 2024).
- Measured on walk61's robot walks (`guide/firmware/mac/robot-runs-20261030-t1/sensitivity.py`, 130 states): input-to-action Jacobian norm, median, walk61 10.7, ts_start 15.4; on the joint-position inputs 4.2 against 8.3, on the gyro 0.73 against 1.13. The flight lineage feeds joint position back about twice as strongly as walk61, which fits the matched cell (twice the servo gain breaks ts_start and not walk61).
- In the training env the teacher t2a_999 does not show as the rougher policy: with the position gain drawn 0.8 to 2.2, no pack, its action-rate sum is 0.26 per s and its action-acceleration sum 0.27 against 0.53 and 0.79 for ts_start, and it falls 2.9 per env-minute against 6.5 (`train/out/audit_d1_none.json`). The runtime simulation counts 32.5 jumps per 10 s for the same teacher walking. The training env does not see this chatter, so a larger action-rate weight alone would not have removed it; the gain range is the term that makes a high-gain policy pay.
- Design `universal5t` (`microduck_rl/cmu/finetune/flight/flight_worker.py`, `smooth_terms.py`): round 2's env (loop delay 40 to 65 ms, load range) plus one position-gain scale per env per episode 0.8 to 2.2; action-rate weight -1 to -2 and a new action-acceleration term at -0.6 (Disney's 3 to 1); behaviour-cloning anchor to walk61 on no-pack rows (beta 2.0, the t2b value), legs always, head only at a zero head command; no-pack share of resets 10 to 20 %. No action filter (`microduck_rl/AGENTS.md`).

### 2026-11-19 20:10 Flight chatter fix: parallel teacher arms on Modal and a second Kaggle pair

- Shawn 19:44 lifted the compute caps ("能并行就并行 资源以用完为限"): Kaggle the whole weekly quota, Modal up to 70.00 USD metered. Run record: `microduck-sim/extensions/flight-20261110/train/RUNLOG.md` "Round 3 parallel arms".
- Running now, simulation only (seven teacher runs): Kaggle `microduck-ts3-teach-a` (ts3-teach-a from ts_start, ts3-teach-b from walk61, seed 1, since 19:26) and `microduck-ts3-teach-c` (the same two with seed 2, since 20:07); Modal A10 `ts3m-w61long` (walk61 start, 2500 iterations instead of 1000), `ts3m-b05` and `ts3m-b6` (ts_start start, anchor weight 0.5 and 6.0 instead of 2.0), since 20:03.
- Modal A10 measured 0.32 iterations per s at 4096 envs (Kaggle T4 0.19): 1000 iterations about 52 min and 1.25 USD. Metered 32.59 USD before the three launches; their caps sum to 8.93 USD worst case.
- Finding: the gain range cannot simply be widened. With the position-gain scale drawn 0.8 to 3.0 the start policy's own walk falls 12.1 times per env-minute at no pack (6.5 at 0.8 to 2.2) and stepping in place earns 1.208 of its reward, so the incentive audit fails (`train/out/audit_kp30_none.json`) and that arm was not launched.
- Gates are scored on every 125-iteration save of the Modal arms while they train (`train/ts3m_watch.py`, heartbeat `train/logs/ts3m_heartbeat.txt`); the Kaggle kernels hand over their saves only at the end (`train/logs/ts3_teach_heartbeat.txt`, `train/logs/ts3_teach_cd_heartbeat.txt`).
- 20:21 first gate results (saves 125 and 250, teacher gates G2 to G5, 10 seeds, `train/logs/gates_m3*_score.log`): none passes yet. The walk61-start arm at 250 passes every no-pack line, gain400 included, and the gain400 pack lines; it fails only the pack at nominal gain (10 of 10 falls at 0.76 s). The two ts_start arms at 250 stand in all four cells (gain400 standstill fell 5 to 6 of 10 at save 125, 0 at 250) but walk badly: 8 to 10 falls of 10 with the pack, 8 to 9 at no-pack gain400. The anchor weight (0.5 against 6.0) makes no visible difference at this point.
- 20:16 the walk61-start arm stopped itself at iteration 250 on the tracking guard: walk61 does not walk at all in the training env with the pack (speed along the command -0.04 from the first save), and the guard assumes a start policy that walks. The Kaggle walk61-start arms carry the same guard and are expected to have stopped at 250 as well. Relaunched 20:22 on Modal as `ts3m-w61g` with a grace period (`--track-grace 1000`: the stepping check applies from iteration 1000), heartbeat `train/logs/ts3m2_heartbeat.txt`.
- 20:27 the walk61-start save 250's pack failure (10 of 10 falls at 0.76 s at nominal gain) is a real backward fall, not a gate artifact: the policy holds walk61's stance and the legs give way under the pack (ankle 0.46 to 0.78 rad in 0.7 s, leg force only about 0.1 N m); at twice the position gain the servos hold the stance by themselves, so those lines pass. The pack-carrying ts_start arm crouches within 0.3 s instead. `train/logs/ts3_first_second.log`.
- 20:52 Modal budget corrected: 18.45 USD of credit left, metered must stay at or under 51.00 USD (36.37 at 20:49); no new Modal training, students train on Kaggle. Worst-case sum for what is running plus all gate scoring plus 4 USD for the students: 48.93 USD with the walk61 arm scored every 250 iterations. A bill guard stops every Modal app of this work at 50.00 (`train/logs/ts3_bill_heartbeat.txt`). The first passing teacher save now starts its Kaggle student kernel by itself (`train/logs/ts3_distill_heartbeat.txt`). All watchers still run on the MacBook and pause with its lid: the Mac mini has no Modal or Kaggle login (`train/HANDOFF-mac-mini-cloud-login.md`).
- Saves up to 875 of the ts_start arms still fail (3 to 5 lines): walking with the pack at nominal gain falls 8 to 10 of 10 while the same saves mostly pass at twice the gain. Reading, not yet tested: the gain scale 0.8 to 2.2 is hidden from the teacher, and one behaviour for the whole range has settled on the stiff end.
- 20:54 tested (`train/out/gain_split.json`, runtime simulation, walking with the pack, 10 seeds per gain): two late ts_start saves fall 10 of 10 at gain scale 0.8 and 1.0 and 1 to 5 of 10 from 1.25 to 2.2. The failure does concentrate at the robot's own gain and below. With the pack no gain is clean, so the hidden gain is one cause, not the only one.
- 20:58 fix queued: delta `universal5tg`, the same training with the gain scale added to the teacher's privileged inputs (the student has to infer it, as it does the load); smoked on the Mac mini; the pair (ts_start start, walk61 start) goes into the next free Kaggle session (`train/logs/ts3_push_tg_heartbeat.txt`).
- 23:01 all teacher arms finished, 66 saves scored, none passes. The gain input removed the falls: the walk61-start gain-input teacher at save 750 fails one line only (walking with the pack: action jumps median 3.5 per 10 s against 2.75), later saves get worse (20.25 at 875, 68.5 and 5 falls of 10 at 999).
- 23:05 diagnosis (training log of that arm, plus one tick-logged pack walk per save on the Mac mini; `train/RUNLOG.md` 23:03 and 23:05): the saves do not swing, they drift one way. With the pack, save 750 walks at 0.07 m/s for a 0.25 command with 5 jumps per episode, save 875 at 0.14 m/s with 41, save 999 at 0.20 m/s with 158. The jumps are in head yaw and the right hip (roll, yaw), not at foot strike. In training the speed terms rose by 0.65 per episode over that stretch while the two smoothness terms cost only 0.33 more, so speed with the pack is being bought with jumps. The anchor to walk61 and the no-pack gates do not move; the learning rate was flat on its clamp.
- 23:18 fix launched on Kaggle (one kernel, two GPUs, `microduck-ts3-teach-k`): (a) the same teacher continued from save 750 with both smoothness weights doubled (incentive audit PASS at all three loads, standing earns 0.40 to 0.65 of walking), half the learning rate and a save every 25 iterations; (b) a Mamba student distilled from save 750 as it is. A detached follow-up scores the student on all gates and the teacher saves on theirs (`train/logs/ts3_pair_k_heartbeat.txt`). Kaggle quota: 4.72 h before, about 2.7 h expected after.
