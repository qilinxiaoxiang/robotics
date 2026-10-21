# MicroDuck beak pickup: per-step status, env analysis, order of attack, roadmap (2026-10-21, reading only)

Problem 9 of the MicroDuck review. Repo root `/Users/xiangzheng/code/robotics`; paths below are relative to `microduck-sim/` unless they start with `DECISIONS.md`. No sim, robot or training was run; every claim is a quote from a file (file:line) or is marked **inference**. "Robot" = shown on the physical duck; "sim" = shown in a simulation.

Current robot facts used (the only source: `CURRENT-STATE.json`):
- `walking_policy` = "walk61.onnx (Pollen BEST_alpha_walking, runtime-overlay/models) at 0.25 m/s, 4 s walks; KP_RL 200, stand mode KP 400" (verified 2026-10-18).
- `imu_rate_hz` 50, `servo_read_drop_fraction` 0.04, `servo_rail_v` 7.0 (walking), `imu_added_delay_ms` 0.
- `servo_bus_hosts`: "Mac over OpenRB USB (walk_wired.py) or A7Z over J12 UART2 /dev/ttyAS2 at 500 kbaud".
- `leg_joint_friction_unloaded`: "no binding joint ... right ankle WITH its foot not re-measured since the 10/16 bind".

Goal and scope (`PROJECT-CONTEXT.json`): `goal` = "camera-guided beak pickup and reinforcement-learning experiments: perceive the target, align, grasp, lift, and assess success"; `required_capabilities` = camera_observation, visual_alignment, learned_jaw_control, pickup_success_check, single_source_power; `scope_rule` = "Manual positioning and scripted pickup are component bring-up tests. They do not replace the visual learning goal or complete its MVP."

## 1. Status of the four steps

### Step 1: find the object (orange printed part)

Robot (2026-10-16, Pi Zero W head, Camera Module 3 Wide):
- Detector: `CAMERA.md:11` "57/57 stream frames hit the orange printed part at cx 52.5 +/- 0.22 px, cy 459.3 +/- 0.09 px"; HSV threshold, largest blob (`PICKUP.md:14-15`).
- Live projection with the duck standing: `PICKUP.md:43-45` "projected the orange part at x 0.358 m, y 0.224 m from pixel (53, 459), steady to 1 mm. Whether that is the true position is the calibration question".
- Calibration done once, at one distance only: `PICKUP.md:63-66` "object at 0.285 m ... `--pitch-offset 9.25` (residual 0.4 mm; ... height and pitch are nearly degenerate at one point; ... the second-distance check decides whether it holds)"; `PICKUP.md:81-82` "Shawn stopped the calibration there (the camera will be swapped)".

Sim: `PICKUP.md:19-20` rendered checks "1-7 mm error for 0.1-0.8 m"; closed-loop sim projects the blob's base, "within 1.3 cm in x for objects whose base is in the frame (0.15-0.6 m)" (`PICKUP.md:101-104`).

Not shown / open:
- The head board is now the Radxa A7Z and its camera is not up: `microduck_rl/cmu/ROBOT.md:24` "the A7Z camera path is not yet brought up (the camera numbers in `mac/CAMERA.md` were measured on the Pi Zero W)"; `PROJECT-CONTEXT.json:1025` "Camera 90 degree image rotation and the perception pipeline on the A7Z (pickup) are not yet run on this board."
- Detector weakness: `CAMERA.md:12` "the detector keys on a colour range, not an object model"; `PICKUP.md:16-17` "the duck's own orange parts are a false-positive source".
- No end-to-end camera latency figure (`PICKUP.md:127`).

**Inference:** step 1 was shown once on the old head and has to be re-shown on the A7Z. It needs no walking and no training.

### Step 2: walk to it

Robot:
- `guide/firmware/mac/robot-runs-20261018/README.md:9` "1018d, walk61, 0.25 m/s, for_s 3, two walks ... Both clean: tilt at most 7 and 5 deg"; `:7` 1018a walked 4 s then "walked into a laptop ... tipped forward".
- `robot-runs-20261019-a7z/README.md:9,13` two walks on the floor with bare V1.22 feet "Tripped forward at 1.3 s" / "at 1.2 s"; `:14` on a silicone mat "Clean ... so the floor trips were the bare V1.22 feet slipping, not the A7Z latency".
- The pickup loop's own walking fell: `PICKUP.md:85-86` "bursts at 0.10-0.15 m/s with the head commanded down diverged within 0.8-1.5 s"; the rewritten approach "Not retried on the robot" (`PICKUP.md:89`, `:132-133`).
- The fine-tuned candidate is worse on the robot: `DECISIONS.md` D-017 Outcome "on the robot it lost balance at 2.5-4 s in three of three walks at 0.20 m/s" (also `CURRENT-STATE.json` walking_policy.candidates).

Sim:
- walk61's envelope: `PICKUP.md:86-88` "walk61 does not step below vx 0.25, does not turn in place, does not walk backwards, and stops stepping when a head command is active"; `ROBOT.md:101-103` adds "stops in a random stride phase, so a 2 s burst moves 1 to 21 cm".
- Closed loop `pickup_sim.py`: three placements picked up, no fall, but 28-225 s and 4-31 bursts (`PICKUP.md:107-111`; traces `pickup-sim-20261016/sim4_*.log`, e.g. `sim4_rightfront.log:61` `"bursts": 23 ... "grip_dist_m": 0.0241`). Why slow: `PICKUP.md:112-115` "the pickup window is a 3 cm circle, so the last step lands in it about one time in three and each miss costs a 35-50 s search loop".

The gap itself (`microduck_rl/cmu/SIM2REAL.md`): `:3-4` "On the robot the same policies walk 3 to 4 s at 0.25 m/s and then wobble and fall more often than not"; `:27-28` trunk gyro change "1.0 to 1.3 rad/s on the robot against 0.17 to 0.30 in the sim"; `:38-43` leg joints realise "6 to 19 % of the policy's 0.02 to 0.04 rad corrections"; `:44` "Falls begin with a yaw-rate spike of 6 to 10 rad/s"; `:57-59` the sim "Does not reproduce: the stiction band at gain 200 ..., the trunk's broadband 5 to 25 Hz shake, the yaw-rate spikes, and therefore the falls after 4 s"; `:82` "Sim improvements that do not address the measured failure mode do not transfer." Open tests `:95-110` (air-vs-floor spectra, backlash, stiction fit, Pollen's low-pass and 0.9 scale, 3-tick coast, free the ankle).

Also open on the robot side: the A7Z reset four times when hot (`robot-runs-20261019-a7z/README.md:19,30`), and the open-loop stand (NEUTRAL, KP 400) tips forward within ~20 s since 10/20 (`stand-gap-20261021/README.md:3,24`). Neither is a walking policy problem, but both cost robot session time.

**Inference:** step 2 is the only step whose failure mode is not reproduced by the sim, so it cannot be closed by training alone; the robot-side tests in SIM2REAL.md are the path.

### Step 3: bend down and keep balance

Robot (2026-10-16): `PICKUP.md:83-84` "groundpick phase 0.33 held (tilt 37 deg, legs and neck within 0.1 rad of the sim pose), rise handed back to stand61 at 2.6 deg tilt; actions peaked 2.10 rad on the rise"; head commands on stand61 "0.3 / 0.6 / 0.8 commanded -> 0.41 / 0.64 / 0.82 reached, tilt unchanged" (`:80`).

Sim: `PICKUP.md:29-31` "phase 0.33 held 4 s, no fall, trunk 34-35 deg, mouth tip 22 mm over the floor and 69 mm ahead of the mid-foot point, rise to standing (end tilt 0.3 deg)". `SIM2REAL.md:54-56` lists "the ground-pick crouch and rise" among what the sim reproduces.

Not shown / open:
- The crouch is blind: `PICKUP.md:124-126` "The ground-pick policy was trained without an object or a jaw; it does not aim the mouth at anything, so the final centimetres are blind and the approach tolerance (window 6 x 6 cm) decides success."
- Crouch with the jaw open and an object under the beak: the run order asks for it (`PICKUP.md:67-69` "Then the same with `"jaw": "open"` during the descent") but the 2026-10-16 robot list (`PICKUP.md:72-90`) records only the plain crouch; the real mouth height under servo sag is unmeasured (`PICKUP.md:122`; D-015 "Not yet shown").
- The sim-vs-real agreement for a quasi-static pose is good (0.1 rad), unlike walking.

**Inference:** balance in the crouch is solved by Pollen's policy on this robot; what is missing is aiming (object in the loop) and the jaw-open variant. This is a sim/training task plus a short guarded robot check, with no walking in it.

### Step 4: pick it up with the beak

Robot (2026-10-16): `PICKUP.md:78-79` "Jaw: closed 2042, open 2442 (35 deg by hand, neck-limited at STAND); open -> 20.1 deg, grip on a finger -> 14.1 deg HOLDING; a goal on the closed stop hums (rest at 2 deg); P gain 400 hummed, `--jaw-kp` default 200". Grip law: `jaw_ctl.py:9-12` Operating Mode 5, Goal Current 100 mA, "a 'grip' command aims SQUEEZE_DEG past the closed reference and the current limit, not the position loop, holds the object. A jaw that stops GRIP_MIN_DEG or more from closed while gripping holds something."

Sim:
- The pickup closed loop fakes the grip: `pickup_sim.py:4-6` "Only the jaw is faked (the model has no jaw): a 'grip' holds when the mouth tip is within GRIP_REACH of the object centre, and the object then follows the mouth tip" (GRIP_REACH 0.035 m, `:43`).
- Beak lab (separate web simulator with a jaw joint): `microduck-beak-lab/README.md:49` "the initial network completed 0/12, the trained network 12/12, and the scripted controller 12/12"; `:51` ground ball "trained and scripted jaws each completed 4/4"; `:53` "Dimensions, materials, and actuator settings have not been calibrated on hardware." Its learner: `overlay/rl/README.md:21-27` SB3 PPO, "Actions: close/open jaw motor targets, rate-limited to 0.6 rad/s", observations from "simulator state, not vision or measured hardware sensors" (`jaw_env.py:18-19` Box 20-D, Discrete(2)). `PROJECT-CONTEXT.json` training.remaining_transfer_work: "Replace privileged state with real observations and validate perception, alignment, trained jaw integration, calibration, success assessment and power on hardware."

Limits (software only; `guide/firmware/pi/JAW-LIMIT.md:1` "the jaw limit stays in software ... Do not store an ID15 EEPROM limit and do not raise it again"): `jaw_limits.json` jaw_max_open_deg 25, head_pitch_max_while_jaw_open_deg 65, jaw_min_usable_open_deg 5, pose cap from the CAD table `jaw_pose_caps.json` (`jaw_limits.py:6-16`). `JAW-LIMIT.md:61-63` "The recorded policy runs stay inside the cap ... keep at least 5.6 degrees between the jaw and its cap" (those were simulated pickups, not the real crouch). The cap at the real crouch head pose has not been read from a robot log.

Not shown: any object gripped from the floor; the jaw open during a crouch; D-015 revisit trigger "the jaw cannot hold a 4 cm object at 100 mA" untested. Object constraints `PICKUP.md:122-123`: "at least 4 cm tall ..., a colour the duck does not wear ..., light enough for a 100 mA jaw".

**Inference:** step 4's hardware is commissioned (calibration, current-mode grip, limits), the grasp itself has never met a floor object on the robot or in the as-built sim. It is a short guarded robot test once step 3 lands the mouth over the object.

## 2. What Pollen's ground-pick env trains, and the smallest change for steps 3 and 4

Source: `microduck_rl/src/mjlab_microduck/tasks/microduck_ground_pick_env_cfg.py` (cfg) and `tasks/mdp.py`.

Scene and model:
- Robot only: `cfg:157` `cfg.scene.entities = {"robot": MICRODUCK_GROUND_PICK_ROBOT_CFG}`; flat plane (`cfg:604-605`). **No object in the scene.** The "payload" is a force, not a body: `cfg:280-283` "Poids aléatoire 'dans la bouche' au relever (objet soulevé, 10-40 g/épisode) ... applique le POIDS de l'objet comme force externe au mouth_tip, gaté sur la remontée"; `mdp.py:3227-3241` `sample_mouth_payload` 0.01-0.04 kg, `:3244-3260` `apply_mouth_payload_force`.
- **The jaw is not a joint.** `cfg:217-220` "the passive jaw joints are no longer part of the articulation, so joint_pos is the clean 14-joint layout: 0-4 left leg, 5-8 neck/head, 9-13 right leg"; `robot/microduck_constants.py:157` "jaw linkage in the new model has no XML actuator", `:166` actuator targets `^(?!passive_).*`; `robot/microduck/robot_walk.xml:214-216` `jaw_soft` is a body under the `head_roll` hinge, no jaw hinge; the `mouth_tip` site is `robot_walk.xml:257-258`.
- Why the beak stays closed: there is no jaw degree of freedom to open, and the task is "crouch to bring its mouth tip AS CLOSE AS POSSIBLE to the ground WITHOUT touching it (correctly oriented, mouth pointing down)" (`cfg:3-5`). The policies "never see the jaw" (`ROBOT.md:39-40`); on the robot `jaw_ctl.py` drives ID15 separately.

Observation (61-D, same as walking): `cfg:6-7` "The obs/action spaces are identical to the walking policy"; command slot = phase `[cos(2π·phase), sin(2π·phase), 0]` (`cfg:13-14`; `mdp.py:5239-5243`), head(4) and body(6) slots zero-padded (`cfg:445-456`). Phase period 4 s, random phase at reset (`mdp.py:5245-5250`, `randomize_phase` default True, `cfg:465-467` does not override it). Segments at `cfg:108-111`: descent [0, 0.375), low hold [0.375, 0.425), rise [0.425, 0.80), standing rest [0.80, 1). Noise, delays, IMU misalignment 6°, encoder bias as velocity (`cfg:391-443`).

Rewards (weight): mouth_ground_proximity_phased 3.0, Gaussian on mouth_tip z with std 0.10 m, target 0 (`cfg:187-199`; `mdp.py:3129-3144`); mouth_perpendicular_phased 2.0, mouth x-axis pointing down (`cfg:205-215`); ground_pick_return_pose legs 6.0 std 0.3 and neck 6.0 std 0.15 (`cfg:222-248`); return_upright 4.0 (`cfg:255-265`); neck_vel_descent -0.1 (`cfg:270-278`); payload hook 0.0 (`cfg:284-294`); upright 0.2, body_ang_vel -0.05, angular_momentum -0.02 (`cfg:299-305`); feet_grounded 3.0 (`cfg:312-316`); feet_flat -2.0 (`cfg:324-330`); action_rate_l2 -2.0 with curriculum -0.8 → -1.5 → -2.0 (`cfg:339-341`, `:622-632`); neck_action_rate -1.0; joint_torques -5e-3; self_collisions -1.0; head_impact_penalty -2.0 on the neck subtree vs terrain above 1 N (`cfg:364-368`; `mdp.py:1786-1806`). Terminations: the velocity base plus `nan_state` (`cfg:471-474`). DR: CoM, head CoM, mass/inertia, BAM friction scale, armature, pushes ±0.15 m/s every 3-6 s, foot friction 0.7-1.3 (`cfg:39-64`, `:496-597`). Runner: 512/256/128 ELU actor with obs normalisation (`cfg:669-706`).

Pieces to reuse:
- Object in the scene: the ball-kick env already does it. `microduck_ball_kick_env_cfg.py:191-194` `cfg.scene.entities = {"robot": ..., "ball": MICRODUCK_BALL_CFG}` (`robot/microduck/ball.xml` 70 mm 15 g sphere); `mdp.py:6102-6117` `reset_ball_in_front_of_foot` places it in the robot yaw frame with ±1.5 cm DR; `mdp.py:6219-6233` `ball_pos_in_base` gives the object position relative to the root in the base frame. There it is critic-only ("the actor stays blind to the ball", `cfg:388-390`); for pickup the actor must see it (the camera supplies it).
- Deployment-shaped phase: the roller-crouch env starts every episode standing, `microduck_roller_crouch_env_cfg.py:385-394` `"randomize_phase": False` "comme au déploiement (le bouton lance le cycle à phase 0)"; it also shows a directive pose-by-phase reward built from a pose read on the real robot (`:72-88`, `:175-186`). Not reusable: its rollers robot and entry velocity.
- Last-mile spawns: `mdp.py:4488-4508` `set_random_crouch_state` (reverse curriculum for crouch→stand) for the rise-with-payload mile.
- Beak lab: its acceptance checker (opposing contact, lift, hold, release, penetration bound; `GROUND_RESULTS.md:39-54`) is the model for a sim success criterion; its jaw policy does not transfer (privileged obs, other simulator, uncalibrated). `docs/RESEARCH_SCOPE.md:7` "The existing balance policy can stay fixed. Begin with a small rigid object and joint head–jaw actions".
- D-016 gates (`DECISIONS.md` D-016): reward audit against the degenerate policy and the smoke test before any paid run.

What a "crouch with the beak open, object in view, grip, rise" policy needs (**design inference**):
1. An object entity (4-9 cm tall box or cylinder, 10-40 g) spawned in a window around the mouth landing spot (`pickup.py:50` MOUTH_X 0.069 m) with placement DR growing from ±1 cm to about ±5 cm, the error the walk leaves.
2. Its position in the actor obs without changing the 61-D layout: the body_command slots are constant zero in this env (`cfg:445-456`) and in the runtime (`walk_brain.py:525` `obs = np.concatenate([state, self.last_action, command, head, np.zeros(6)])`). Two of them can carry the object (x, y) in the foot frame, which `target_ground.py` already produces. If the layout changed instead (62-64 inputs), these break: the single concatenation at `walk_brain.py:525`, `OBS_NAMES` at `:100`, the shared-metadata assert at `:265`, `brain_sim_check.py` and `pickup_sim.py` (they import the same Brain), and the hot-swap contract that lets walk61/stand61/groundpick share one buffer (`microduck_rl/AGENTS.md` Invariants: "Obs layout is 61D ... never delete a slot"). The same AGENTS.md warns "A command input that is never non-zero has dead weights forever", so a policy that reads the object slots is trained with them non-zero from step 0 (fine-tuning alpha_ground_pick would have to grow those weights from zero).
3. The jaw: keep it scripted in current mode at the mode boundary, as today (`pickup.py:15-18` crouch `{"mode": "groundpick", "phase": 0.33, "jaw": "open"}` → grip → lift). Reasons: the Pollen model has no jaw joint (adding one changes the 14-output action contract, `walk_brain.py:530-531`); the hardware grip is current-limited and does not need a policy to choose a force; the beak lab shows a learned jaw matching, not beating, the scripted one (12/12 vs 12/12, 4/4 vs 4/4). `learned_jaw_control` stays a required capability for the stage after the whole-body crouch works, with the beak-lab checker ported to the training env; this ordering changes implementation order only (scope_rule).
4. Rewards: replace mouth_ground_proximity (any xy, height 0) by mouth-to-object proximity (3-D distance from `mouth_tip` to a grasp point just above the object centre, std about 0.03 m) gated on the descent and hold; keep mouth_perpendicular, feet_grounded, feet_flat, return pose, return_upright, head_impact_penalty (its secondary match is "terrain" only, `cfg:146`, so touching the object is not penalised); keep the 10-40 g payload hook for the rise and switch it on only when the mouth tip reached the object (the scripted grip); the head needs a collision geom for object contact (`cfg:235-236` "head geoms have no collision mesh"; the allcollisions family names "shells, head shells, jaw", `microduck_constants.py:19`).
5. Curriculum: `randomize_phase=False`; placement window ±1 → ±5 cm; action_rate as in Pollen; crouch-state spawns for the rise. Audit per D-016 with Pollen's alpha_ground_pick as the degenerate baseline (it crouches without aiming; the new term must pay aiming visibly more).
6. Export with the normaliser (`uv run scripts/export.py`), rehearse in `brain_sim_check.py --gp-*` on the as-built model at the real condition (`sim_suite.sh` flags from `CURRENT-STATE.json`), then the robot.

Smallest change, in one sentence: copy the ground-pick cfg, add the ball-kick object entity with a reset placer, write (x, y) into two body slots for the actor, swap the height reward for a mouth-to-object reward, start at phase 0, and keep the jaw scripted.

## 3. Order of attack: must walking come first?

Claim: steps 3 and 4 can be developed now with the robot placed by hand, and doing so makes step 2 easier. Evidence:
- Steps 3 and 4 were already shown on the robot without walking (`PICKUP.md:78-84`), and the crouch matches the sim within 0.1 rad; walking's failure mode (5-25 Hz trunk shake while stepping, yaw-rate spikes, `SIM2REAL.md:27-44`) is absent from a quasi-static crouch (`cfg:62` pushes ±0.15 "geste quasi-statique").
- What makes walking "unreliable for pickup" is the 3 cm window, not only the falls: `PICKUP.md:112-115` the last step lands in it one time in three; `:131` "a crouch policy trained with the object in view would remove the lottery". An aiming crouch with a ±5 cm window asks the walk only to stop within 5 cm, so step 3 lowers step 2's precision requirement.
- `scope_rule`: manual positioning is bring-up, not the MVP, so step 2 is still on the MVP path; its robot-side tests (`SIM2REAL.md:95-110`) are independent of the pickup env and can run in parallel.
- Step 1 on the A7Z is independent of all others and blocks the MVP (camera_observation); for step-3 bring-up the object position can be measured by hand, which is exactly the scope_rule's component test.

Dependency graph in words:
- Step 1 (A7Z camera + detector + calibration) blocks the closed loop on the robot; depends on nothing. Robot time, standing only.
- Step 3 learned (pickup env, audit, smoke, train, as-built suite) blocks step 4 on the robot and the MVP; depends on nothing. Sim only, Mac mini; training needs Shawn's go and a cost cap.
- Step 3/4 scripted bring-up (crouch with jaw open, object by hand, grip, rise) blocks nothing but de-risks step 4 and measures the real mouth height (corrects MOUTH_X); depends on nothing; one guarded robot session.
- Step 2 (walking gap, SIM2REAL tests, soles) blocks the MVP; independent of the pickup env; its target window comes from step 3's policy.
- Step 4 learned jaw: after step 3 works on the robot.
- MVP join: step 1 + step 2 + step 3 policy + step 4 scripted grip in `pickup.py`, then the success check.
Three lanes run in parallel: A sim (pickup env), B robot bring-up (A7Z camera; crouch+jaw by hand), C walking gap (robot tests). Lane B and C share robot time with Shawn guarding; A does not.

## 4. Roadmap (current metric → target → next experiment → gate)

Targets below are proposals for Shawn to set; they are not measured values.

Step 1 find: current 57/57 frames and 1 mm steady projection on the Pi Zero W camera, calibrated at one distance; A7Z camera not run. Target: A7Z stream at 10 fps, detector on the target in ≥ 95 % of frames with the duck's own parts rejected, projection within 3 cm at two distances in 0.15-0.50 m (the D-015 revisit threshold is 3 cm at 0.3 m). Next: bring the camera up on the A7Z, run `pickup.py --observe` and `--calibrate 0.30`, check at 0.50 m. Gate: no sim; robot standing on stand61 with Shawn guarding, no walking.

Step 2 walk: current walk61 0.25 m/s clean 3-4 s on grippy surfaces (10/18, 10/19 mat), trips on bare V1.22 feet, pickup bursts not retried since the two falls, sim 3/3 with 4-31 bursts. Target: 10 of 10 bursts of 1-2 s at 0.25 m/s without a guard trip, approach ending inside the crouch window in ≤ 3 approaches. Next: soles on the V1.22 feet; SIM2REAL tests 4 and 5 (Pollen's 0.9 scale + target low-pass, 3-tick coast) in `sim_suite.sh` real cases, then on the robot. Gate: as-built suite at the real condition shows no fall, then robot with Shawn guarding.

Step 3 crouch: current Pollen groundpick on the robot, 37° tilt, rises, blind. Target: an aiming crouch policy: mouth tip within 2 cm of the grasp point for an object anywhere in a ±5 cm window, hold, rise with 40 g, no fall, in ≥ 90 % of as-built sim episodes at the real condition; then 8 of 10 hand-placed robot trials, tilt under the 55° guard. Next: build the env (section 2), `finetune.py::audit`-style reward audit vs alpha_ground_pick, 64-env 5-iteration smoke; training only with Shawn's go under a cost cap. Gate: smoke → audit PASS → as-built `brain_sim_check.py --gp` suite → robot.

Step 4 grip: current finger held at 14.1° at 100 mA; no floor object; jaw-open crouch not recorded. Target: a 4-9 cm, ≤ 40 g object gripped from the floor and held through the rise (jaw ≥ 3° from closed, object off the floor) in 8 of 10 hand-placed trials; the pose cap leaves ≥ 15° at the crouch head pose (read the clamp log). Next (one guarded session, no walking): stand61 → `groundpick` 0.33 with `"jaw": "open"` → object placed under the beak by hand → `"jaw": "grip"` → `"phase": 1.0`; log the mouth tip from the joints and correct MOUTH_X. Gate: `test_pickup_modes.py` fake-link tests; robot with Shawn.

MVP join: `pickup.py` end to end on the robot from 0.3-0.6 m, scored by the pickup_success_check (jaw holding and object lifted after the rise), 5 of 10 trials.

## 5. Per-step acceptance text for PROJECT-CONTEXT.json (new `final_goal` entry)

- find_object: "On the A7Z head camera the detector locks the orange target in at least 95 % of frames with the duck's own orange parts rejected, and the floor projection is within 3 cm of the measured object position at two distances between 0.15 and 0.50 m, logged by `pickup.py --observe` with the robot standing on stand61."
- walk_to_object: "From 0.3-0.6 m away, `pickup.py` (0.25 m/s bursts, head at the default pose) stops the robot with the object inside the crouch policy's capture window in at most three approaches and without a guard trip in 8 of 10 robot trials with Shawn guarding, after the as-built sim suite at the real condition shows no fall."
- crouch_and_balance: "The learned crouch policy brings the mouth tip within 2 cm of the grasp point of an object placed anywhere in its ±5 cm window, holds, and rises back to stand61 with a 40 g payload without a fall in 90 % of as-built sim episodes at the real condition, then in 8 of 10 hand-placed robot trials with tilt under the 55° guard."
- pick_up: "With the jaw opened during the descent and the current-limited grip (100 mA) at the hold, a 4-9 cm, at most 40 g object is held through the rise (jaw at least 3° from closed, object off the floor) in 8 of 10 hand-placed robot trials, and the pose cap leaves at least 15° of opening at the crouch head pose."
- final_goal (MVP): "The four steps run as one closed loop from `pickup.py` with no manual positioning: object seen, approached, crouched over, gripped and lifted in 5 of 10 robot trials from a 0.3-0.6 m start, each scored by the pickup success check; the learned jaw then replaces the scripted grip as the next stage."
