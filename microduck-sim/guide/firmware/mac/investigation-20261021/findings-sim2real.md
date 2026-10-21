# Problem 8: copying the real MicroDuck's failures into the simulation, one by one

Date 2026-10-21. Reading, logs and literature only; no sim, robot or training was run and the repository was not edited.
Paths are relative to `/Users/xiangzheng/code/robotics/microduck-sim/` unless absolute. `cmu/` means
`microduck_rl/cmu/`. Every current robot fact is from `CURRENT-STATE.json` (read tonight); everything else is history
or study output and is labelled measured (M), modelled (S, from a sim run) or inferred (I).

## 0. BLUF

The as-built suite (`cmu/simcheck/sim_suite.py`) passes every "real" case for walk61 and ft3 (no fall in any of the
five real cases, `cmu/simcheck/reference-walk61.jsonl`), while the robot falls in most walks longer than 4 s, fell
three of three times under ft3, trips at 1.2 s on a smooth floor with bare feet, and tips its open-loop stand within
20 s. Of nine real failures, the sim reproduces one in mechanism but not in time (the open-loop stand's softness at
KP 400), and does not reproduce seven; the ninth (the tilted table) has no measurement at all. The three gaps with the
highest explanatory power per hour of measurement are floor friction of the sole (one tilt test with a phone), the
actuator's behaviour under load at the walking gain (loaded step tests plus a BAM-style pendulum fit at 7.0 V), and
the whole-robot mass and centre of mass plus the foot's pivot (one weighing and a two-scale COM measurement). The
literature's recipe for exactly this situation (cheap servos, encoders and IMU only, no motion capture) is: identify
the actuator on a bench with a known load (Rhoban's BAM, 2024), then close the loop on the remaining gap with real
rollouts, either by adapting the randomisation distribution (SimOpt, 2019) or by a learned residual or delta-action
model (Golemo 2018 on a Dynamixel XL-320 arm; ASAP 2025). The program below orders the measurements so that the
first robot session (friction, slope, mass/COM, foot pivot) already lets the suite reproduce three failures. Rule
carried from D-016 and the training memory: no fine-tune until the suite reproduces the failure the fine-tune is
meant to fix.

## 1. Failure inventory, with what the sim does today

Sim column: what `cmu/mac/brain_sim_check.py` (flags at lines 321-365) and the suite's real cases
(`sim_suite.py:45-54`: nominal 0.3 m/s, vx0.25, vx0.2, com+5, imu_pitch4, base flags `--volt 7.0 --drop 0.04`)
do for the same situation.

### F1. Trip at 1.2 s on a smooth floor with the bare V1.22 feet (2026-10-19)

- M: `guide/firmware/mac/robot-runs-20261019-a7z/README.md:9` "walk61 0.25 m/s for_s 3 on a smooth surface. Tripped
  forward at 1.3 s (tilt 12 -> 37 deg in 0.1 s); actions mean 1.17 / max 2.69 rad in the first 1.2 s against 0.70 /
  1.57 on the clean 10/18 walks"; `:13` second floor walk "Tripped forward at 1.2 s (tilt 13 -> 37 deg in 0.1 s)";
  `:14` on a silicone mat "Clean: actions max 1.16 rad ... With grip the onboard brain walks as well as the Mac brain
  did, so the floor trips were the bare V1.22 feet slipping, not the A7Z latency". `:5` "Feet: V1.22 slip-fit feet,
  no anti-slip sole yet."
- M (tick log `duck_wired_log_1019f.jsonl.gz`, window after `walk_t0_1019f`, read tonight): tilt 6.3 deg at 1.14 s,
  10.3 deg at 1.23 s (that tick not fresh, loop 23 ms), 24.5 deg at 1.30 s with body pitch rate 7.5 rad/s, 41 deg in
  stand mode at 1.38 s. The same window on the mat (`walk_t0_1019i`): tilt 0-5.7 deg, max action 1.08 rad.
- S: foot friction is a constant 1.0 in the model (`microduck_rl/src/mjlab_microduck/robot/microduck_constants.py:146`
  `friction={r"^(left|right)_foot_collision$": (1.0,)}`); `brain_sim_check.py` has no friction flag (lines 321-365),
  the loader supports one (`hardware-design-20260912/whole-robot-20260912/dynamics/evaluate.py:96-100`
  `if 'friction' in config: ... m.geom_friction[floor,0]=config['friction']`), and the stand study used it
  (`guide/firmware/mac/stand-gap-20261021/posesearch.py:51` `friction=0.4`). Training randomised mu 0.7-1.3
  (`microduck_velocity_env_cfg.py:377`).
- Verdict: not reproduced; never attempted for walking. No suite case has a floor friction below 1.0.

### F2. Wobble and falls after 3-4 s at 0.25 m/s, yaw-rate spikes of 6-10 rad/s

- M: `cmu/SIM2REAL.md:3-4` "On the robot the same policies walk 3 to 4 s at 0.25 m/s and then wobble and fall more
  often than not"; `:44` "Falls begin with a yaw-rate spike of 6 to 10 rad/s; the trained pushes are linear only";
  `:27-28` gyro tick-to-tick change std "1.0 to 1.3 rad/s on the robot against 0.17 to 0.30 in the sim"; `:30-33`
  "the trunk gyro jitters 4 to 6 times the sim ... broadband power at 5 to 25 Hz (72 % of roll power above 5 Hz; the
  sim sits under 5 Hz)"; `:36-37` "real walks show action jumps over 0.5 rad on 35 to 46 % of ticks against 1.5 to
  2.7 % in the sim". Reproducible from archived files: `cmu/real-logs/README.md:85-88` first walk of 1018d, 0-3 s,
  real gyro_rms [0.937, 0.925, 1.276] rad/s vs sim [0.499, 0.229, 0.261].
- S: reference rows, all real cases `fell_at` null, `action_jumps` 1-5 (`cmu/simcheck/reference-walk61.jsonl`).
  Yaw pushes exist only as a fine-tune delta (`cmu/finetune/modal/FINETUNE-DELTA.md:41-45`), not in the suite.
- Verdict: not reproduced. The 10/16-17 logs behind the "more often than not" rate were not archived
  (`cmu/real-logs/README.md:63-64`); the fall rate per walk is therefore not a number the suite can be held to yet.

### F3. stand61's growing in-place oscillation after 34 s (1018d)

- M: `guide/firmware/mac/robot-runs-20261018/README.md:9` "After the second walk stand61 sat still for 20 s, had
  bursts from +26 s (possibly a touch), then a growing in-place oscillation from +34 s; largest actions on head_yaw;
  3-of-10 guard at +39.9 s; open-loop stand mode crept forward and fell." Also the first walk of 1018d: guard trip
  8.34 s after the command while standing, "with the body pitching forward in the ticks before it"
  (`cmu/real-logs/README.md:57-60`).
- S: `cmu/real-logs/README.md:97-99` window 6-10 s "the sim stands still (leg_dq 0.0, gyro_rms below 0.01 rad/s)".
  The suite's walks are 10 s (`sim_suite.py:128`); no case holds stand61 for 40 s.
- Verdict: not reproduced.

### F4. Open-loop stand creeps forward and falls at about 20 s; rests at 12 deg where the flat-foot model says 4 deg

- M: `guide/firmware/mac/stand-gap-20261021/README.md:3` "tips forward on the robot within about 20 s since
  2026-10-20 night"; `:8` "tonight 5.5-14.9 deg, settled 2-18 s and then fell forward"; `:9` "IMU pitch minus the
  model's flat-foot trunk pitch at the same joints ... is not constant inside one stand (-7 to +9.6 deg ...): the
  trunk rotates on the feet (toe or heel lift, or foot play on the ankle) while the joints hold"; `gap.json` `ol`:
  model `pitch 4.23`, `real_imu_pitch 12.1`, COM 23.0 mm ahead of the heel edge and 24.7 mm behind the toe edge
  (`toe_minus_com_mm`), patch 47.6 mm. `:7` every logged stand runs KP 400.
- S: `README.md:15` "NEUTRAL at KP 400 ... creeps 0.1 -> 5.7 deg in 60 s, tips onto the toes at about 65 s and
  rests at 11.6 deg, the robot's resting angle tonight" (`com_0.json`: `end_pitch 11.63`, `fell_at null`);
  `com_3.json` (COM +3 mm): `fell_at 8.76`; `com_6.json`: `fell_at 1.2`; `kp_800_0.json`: holds, end pitch 0.66 deg;
  `:20` "at KP 400 the ankle, knee and hip in series are too soft to hold the trunk as an inverted pendulum"; `:14`
  "200 g extra at the head moves the model COM only 10 mm toward the toe"; `:22` "the robot pivots on its feet, the
  sim feet are rigid; the as-built manifest still carries the Pi Zero W head".
- Verdict: the mechanism (softness at KP 400, forward direction, the 12 deg toe-rest) is reproduced; the time is
  not (sim 65 s nominal, 8.8 s at +3 mm; robot about 20 s), and the within-stand pitch wander of -7..+9.6 deg has
  no sim counterpart because the feet are rigid.

### F5. ft3 loses balance at 0.20 m/s on the robot while beating walk61 in the sim

- M: `robot-runs-20261018/README.md:8` 1018b "stepped 2.9 s, then rolled about 20 deg within 0.1 s, trip"; second
  walk "rolled to 27 deg the other way, trip, fell sideways"; `:10` 1018g "At 2.5 s right_hip_pitch and right_knee
  actions over 4 rad, trip, fell". `DECISIONS.md` D-017 outcome: "it999 never falls, walks 24-43 % further than
  walk61, steps at 0.20 m/s where walk61 does not"; CURRENT-STATE `walking_policy.candidates`: "on the robot ... it
  lost balance at 2.5-4 s every time".
- S: `FINETUNE-DELTA.md:264` vx0.2 walk61 0.00 m vs it999 1.56 m, no fall.
- Verdict: not reproduced; the sim ranks the policies the wrong way round. `SIM2REAL.md:82` "Sim improvements that
  do not address the measured failure mode do not transfer."

### F6. The quack head move tipped the robot in open-loop stand (2026-10-20)

- M: `guide/firmware/mac/walk_wired.py:51-52` "never in the open-loop stand mode (it tipped over there on
  2026-10-20)"; `:302` `return "open-loop stand mode cannot rebalance"`.
- S: `brain_sim_check.py:108, 174-181` can run the quack head move (`--quack-at`), but through the same gate
  (`quack_head_block`), so the open-loop case is never simulated. The 10/20 stand study (commit fb4d210) found "no
  fixed pose holds at P 400", consistent with F4.
- Verdict: consistent with the F4 mechanism, but the exact event (KP 400 stand plus a 0.08-0.18 rad head roll over
  1.6 s) has not been run. One sim run would settle it; it needs the gate bypassed in the sim only.

### F7. Ankle stiction and binding; loaded deadband at the walking gain

- M (current): CURRENT-STATE `leg_joint_friction_unloaded`: "no binding joint: unloaded 0.05 rad steps at P 400
  reach 85-115 % on every leg joint, breakaway at most 16 ticks / 21 PWM; both ankles 100 % with breakaway 2-3 ticks
  at PWM 0 (measured with the FEET DETACHED); right ankle WITH its foot not re-measured since the 10/16 bind (20-37
  ticks, PWM 25-49, 27-67 %)". Raw rows: `robot-runs-20261018/ankle-probe-20261019/leg_probe_a7z_1019.out`
  (e.g. right_hip_yaw +33 ticks moved 21, frac 0.64, breakaway 13 ticks / PWM 17).
- M (loaded, history): `SIM2REAL.md:38-43` "Open-loop step tests on the standing robot at gain 400: ankles realised
  0 to 15 % of 0.03 to 0.05 rad steps, knees 0 %, hips 8 to 19 %; at gain 1200 every joint tracks 92 to 107 % with a
  60 ms rise ... In walk logs at gain 200 the leg joints realised 6 to 19 % of the policy's 0.02 to 0.04 rad
  corrections and 30 to 50 % of the stride amplitude, 80 to 100 ms late."
- S: BAM XL330 model M6, parameters `~/.venvs/microduck-dyn/lib/python3.12/site-packages/bam/params/xl330/m6.json`
  (`friction_base 0.0048, friction_stribeck 0.0047, load_friction_motor 0.267, load_friction_external_stribeck
  0.081, friction_viscous 0.0054`), recorded with `vin=7.5` (`bam/dynamixel/actuator.py:93`). `SIM2REAL.md:54-55`
  the sim "Reproduces: the static sag at gain 400 (0.041 rad sim against 0.05 to 0.067 real)"; `:57-59` "Does not
  reproduce: the stiction band at gain 200 (BAM's XL330 fit, from Rhoban's bench at 7.5 V, underestimates friction
  under load)"; `:60-62` "scaling it by 1.5 makes walk61 stop stepping at 0.25 m/s in the sim and 2.0 falls at
  2.3 s, while the real robot steps at 0.25 and 0.20". Knobs that exist: `brain_sim_check.py:364 --bam-friction-scale`,
  `jitter-20261018/jitter_sim.py:8-11 --deadband RAD ... --stiction-scale K`.
- Verdict: not reproduced; a scalar on BAM's budget is the wrong shape (it kills stepping before it reaches the
  measured small-step tracking).

### F8. A7Z resets, and the onboard loop timing

- M: `robot-runs-20261019-a7z/README.md:19` reset 4 "0.24 s into stand61 at zero command. The servo rail read
  7.1-7.3 V up to the last tick ... The SoC was at 84-86 °C ... throttled between 416 MHz and 1.5 GHz, with loop time
  24-33 ms"; `:31` "no reset while the board was cool and the CPU clock steady; all four after 35 min inside the
  closed head"; `:12` "Timing onboard vs the Mac brain (10/18): servo sync read 8.5 vs 5.2 ms, loop 12.2 vs 5.7 ms,
  joint age used 12 vs 6 ms, IMU age used 21 vs 12.5 ms; 50 Hz held, 1-8 stale ticks per walk". CURRENT-STATE
  `imu_added_delay_ms 0`, `servo_read_drop_fraction 0.04`.
- S: integer-tick delays only (`brain_sim_check.py:337-338 --sensor-delay 1 --action-delay 1`, i.e. 20 ms each) and
  a random drop fraction (`--drop`). Training: actuator command delay 3-6 ticks
  (`microduck_constants.py:173-174`), IMU 0-1 tick (`microduck_velocity_env_cfg.py:564-569`).
- Verdict: the reset itself is a power/thermal problem, not a sim object. The timing is inside the trained envelope
  (12-21 ms real vs 20 ms sim delay), and the clean mat walk (F1) ran on the same loop; low priority for the sim.
  A throttled 24-33 ms loop means missed 20 ms ticks, which `--drop` approximates but does not time.

### F9. The tilted RoboClub table

- No measurement exists in the repository (searched the run READMEs, study folders, DECISIONS, memory for
  tilt/slope/level); `PROJECT-CONTEXT.json:43` lists a separate "slope" guide for tonight. I: from the 10/14 gap
  study at 5 V, `hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014/README.md` section 3
  "Ankle zero: -3 to +1 deg walk; +2 deg falls", so a slope of a few degrees is of the same order as the policy's
  tolerance; at 7.4 V the margins were wider (section 3, `volt_margins.py`).
- S: no slope flag; the floor is a plane in `src/mjlab_microduck/robot/microduck/scene.xml` and can be rotated.
- Verdict: unmeasured; one phone-inclinometer reading pins it.

## 2. Knob and measurement map, ordered by explanatory power times cheapness

1. Sole/floor friction (F1; also feeds F2 through slip impacts). Measurement: tilt test, foot or whole robot on the
   actual floor, table and mat, angle at which it starts to slide (mu = tan of that angle), with a phone
   inclinometer; 15 minutes, no robot power. Knob: floor `geom_friction` through `evaluate.py:96-100`, exposed as a
   `brain_sim_check.py --friction` flag and a suite case. Pins the knob directly.
2. Actuator under load at the walking gain (F2, F5, F7). Measurement: (a) loaded step tests at P 200 and 400 on the
   standing robot, all ten leg joints, 0.02/0.03/0.05 rad, both directions, the same metric as
   `ankle_probe_a7z.py` (`frac`, breakaway ticks, PWM); (b) one XL330 on a pendulum with a known mass at 7.0 V
   (BAM's own bench: "a rigid link of length l and a point load of mass m", Duclusaud et al. 2024 Sec. II-A), using
   BAM's record scripts (`bam/dynamixel/all_record.py --vin`). Knob: refit the M6 load-friction terms (the
   `load_friction_*` entries) or add a position deadband (`jitter_sim.py --deadband`); the target is the measured
   fraction table, not a scalar. Half a session; the robot stands, Shawn guards.
3. Mass and centre of mass (F4, F6; the 10/14 study's "roughly 10 mm forward COM or an equivalent sagittal
   calibration error", realgap README section 2). Measurement: kitchen scale for the whole robot in plugged form;
   two-scale COM (scale under the toe edge and under the heel edge in the STAND pose, torque balance); weigh the A7Z
   with header when the head opens (`cmu/model/README.md:67`, "18 g, bounded 15 to 20 g"). Knob:
   `cmu/model/variants/plugged.json` then `make_variants.py`; `--com-x` for the check. 20 minutes.
4. Foot geometry and pivot (F4's 12 vs 4 deg; F1 impacts). Fact: the printed feet's socket is rolled about
   4.8 deg about the front-back axis (`guide/print/foot-slipfit-20261019/README.md:10` "the bracket sits rolled
   -4.84 deg (left) and +4.89 deg (right)"), while the physics keeps the official foot collision
   (`cmu/model/README.md:24`; commit f667384 "physics bit-identical"). Measurement: side-view phone video with a
   ruler while the robot stands at KP 400; feeler gauge under heel and toe; the within-stand IMU-minus-model pitch
   already in `gap_tonight.json`. Knob: a passive ankle-foot play joint (the `-Backlash-` mechanism applied to one
   joint) or a compliant sole contact (`solref` on the foot geoms). Medium cost.
5. Floor slope (F9, F4 direction). Measurement: phone inclinometer on the table, two axes; 2 minutes. Knob: rotate
   the floor plane in the scene.
6. IMU mount offset (all; already in the suite as `imu_pitch4`). Fact: `walk_brain.py:112-115` "The BNO085 on
   this build reads the trunk 4 deg further pitched forward than it is (2026-10-15)", chosen from a sim match, not a
   level. Measurement: the robot on a verified level plate in a known pose, pitch read vs the flat-foot model;
   5 minutes once the slope is known. Knob: `IMU_PITCH_TRIM_DEG`, `--imu-pitch`.
7. Backlash and play (F2's 5-25 Hz content). Measurement: torque reversal with a marker on the link filmed by the
   phone (`SIM2REAL.md:98-100`, hypothesis 2); Pollen's variant adds +-1 deg (`backlash.py:7-8`;
   `add_backlash.py --backlash-deg 2.0`, AGENTS.md). Knob: the backlash model with the measured degrees. Medium.
8. Servo supply sag during steps (F2, minor). Measurement: fix the round-robin `servo_v` read timeout
   (`robot-runs-20261019-a7z/README.md:29`) and log the rail at 50 Hz in a walk. Knob: BAM `vin_drop_gain`
   (`microduck_constants.py:170`).
9. Onboard loop timing and stale ticks (F8). Measurement exists (`loop_ms`, `late`, `missing` fields,
   `cmu/real-logs/README.md:42-45`). Knob: replay the logged tick ages instead of a random `--drop`. Low.
10. Air vs floor gyro spectra (`SIM2REAL.md:95-97`, hypothesis 1): decides between feet (items 1, 4) and links
    (item 7) before either model change is built.

## 3. Literature pass (WebSearch 2026-10-21; the `research-lookup` keys are documented in its SKILL.md:216-219, one of
the two variables is set on this machine; `FINETUNE-DELTA.md:182-183` recorded them as unset on 10/16, so WebSearch
plus the primary pages were used)

- Hwangbo, Lee, Dosovitskiy, Bellicoso, Tsounis, Koltun, Hutter, 2019, Science Robotics 4(26) eaau5872, "Learning
  agile and dynamic motor skills for legged robots". Four-step pipeline: identify physical parameters, train an
  actuator network on bench data, train the policy on both, deploy. The gap they close is "actuator dynamics,
  control-signal delays, low-level controller behavior, and joint compliance"; the network is trained on measured
  torque from ANYmal's series-elastic actuators. Fit for the duck: the structure (measure the actuator first) fits;
  the torque supervision does not, since the XL330 exposes position, velocity, PWM and current only; BAM's pendulum
  replaces the torque sensor with a known load.
- Tan, Zhang, Coumans, Iscen, Bai, Hafner, Bohez, Vanhoucke, 2018, RSS XIV p10, "Sim-to-Real: Learning Agile
  Locomotion For Quadruped Robots". Fitted a servo PD model from sine tests on one motor ("the simulated trajectory
  agrees with the ground truth"), and added latency by keeping "a history of observations and their measurement
  time". Fit: direct; it is the minimal version of item 2.
- Duclusaud, Passault, Padois, Ly, 2024 (arXiv 2410.08650; ICRA 2025 pp. 12091-12097), "Extended Friction Models
  for the Physics Simulation of Servo Actuators" (BAM). Pendulum bench "composed a rigid link of length l and a
  point load of mass m"; four trajectory types (chirp oscillations, slow/fast superposed oscillations, raise/lower
  with a static plateau, lift and drop); identification minimises "the Mean Absolute Error (MAE) between the
  simulated and measured trajectories"; M6 adds load-dependent and quadratic terms. Limitations stated:
  temperature, radial forces and dwell time "not considered"; backlash not mentioned. The package's XL330 parameters
  were recorded at 7.5 V (`bam/dynamixel/actuator.py:93`). Fit: exact; our deviation is that the duck's joints carry
  the body's load at 7.0 V and sit in printed brackets, so a refit on our own bench with our load range is the
  honest step, and the loaded step tests are the validation set.
- Kumar, Fu, Pathak, Malik, 2021, RSS XVII, "RMA: Rapid Motor Adaptation for Legged Robots". A 1-D CNN on the last
  0.5 s of states and actions estimates an "extrinsics" latent trained in simulation; no system identification. Fit:
  only after the sim's randomisation range contains the real plant; today a 1.5x friction scale already stops the
  gait (`SIM2REAL.md:60-62`), so adaptation cannot cover the stiction gap by itself. Useful after items 1-4.
- Chebotar, Handa, Makoviychuk, Macklin, Fox, 2019, ICRA, "Closing the Sim-to-Real Loop: Adapting Simulation
  Randomization with Real World Experience" (SimOpt): "adapt the simulation parameter distribution using a few real
  world roll-outs interleaved with policy training". Fit: this is the loop the program needs once the knobs exist;
  the discrepancy can be computed from encoders plus IMU alone (joint trajectories, gravity vector, gyro spectra),
  which is what `compare.py` already does.
- Golemo, Taiga, Courville, Oudeyer, 2018, CoRL (PMLR 87:817-828), "Sim-to-Real Transfer with Neural-Augmented
  Robot Simulation". A recurrent network learns the difference between simulated and real trajectories and corrects
  the simulator; experiments "used the MuJoCo simulator with added backlash, plus the Poppy Ergo Jr robot" (a
  Dynamixel XL-320 arm). Fit: the closest hardware analogue (cheap Dynamixels, encoder-only logs); a residual on
  joint positions can be learned from our tick logs once the first-principles knobs are set.
- Hanna, Stone, 2017, AAAI, "Grounded Action Transformation for Robot Learning in Simulation": learn an action
  transformation so the simulator's response matches the real robot's; NAO walk 43 % faster. He, Xiao, Lin, Xu,
  Xiong, Wang, Yu, Shi, Tang, Rong, Cui, Wang, Kautz, Hou, Lu, Fan, 2025, RSS XXI p66, "ASAP: Aligning Simulation
  and Real Physics for Learning Agile Humanoid Whole-Body Skills": a delta (residual) action model "outputs
  corrective actions that are added to the real-world recorded actions, so the simulator's dynamics are adjusted to
  better match the real robot", then fine-tune in the corrected sim (Unitree G1). Fit: the delta-action idea needs
  real rollouts replayed in the sim with a state match; ASAP used motion capture, we would match joint trajectories
  and the IMU gravity vector only, which is enough for a per-joint residual but not for base position.
- Torne, Simeonov, Li, Chan, Chen, Gupta, Agrawal, 2024, RSS XX p15, "Reconciling Reality through Simulation: A
  Real-to-Sim-to-Real Approach for Robust Manipulation" (RialTo): digital twins "constructed on the fly from small
  amounts of real-world data", RL inside them, "over 67 %" more robust. Fit: manipulation and geometry-heavy; the
  transferable lesson is "build the twin from the real object", here the printed foot and the weighed masses.
- Abou-Chakra et al., 2025, arXiv 2504.03597 (ICRA 2026 version on the RAI Institute site), "Real-is-Sim: Bridging
  the Sim-to-Real Gap with a Dynamic Digital Twin": the policy acts on a simulator that is "continuously corrected
  with real world measurements" at 60 Hz, the real robot follows the sim. Fit: needs object/base state estimation we
  do not have; not applicable without a position reference.
- Howell, Le Cleac'h, Kolter, Schwager, Manchester, 2022, arXiv 2203.00806, "Dojo: A Differentiable Physics Engine
  for Robotics": gradients through hard contact "useful for ... system identification". Fit: our engine is MuJoCo; a
  gradient-free fit of a handful of parameters (friction, load-friction terms, COM, play) against the logs is the
  practical route, SimOpt-style; a differentiable engine is not needed for ten parameters.
- Pollen's own tooling (this repository): `-Backlash-` task variants with +-1 deg play and the encoder reading
  through it (`tasks/backlash.py:1-27`, `actuator/friction_dr_bam.py:64-83`); `FrictionDRBamActuator` scales BAM's
  velocity-independent budget per env (`friction_dr_bam.py:8-12`), randomised 0.9-1.1
  (`microduck_velocity_env_cfg.py:76`); mass +-5 % (`:73`), IMU misalignment up to 6 deg zero-centred (`:84`, "CANNOT
  compensate a systematic mounting bias"), vin 6.5-8.2 V with load sag (`microduck_constants.py:169-171`), command
  delay 3-6 ticks (`:173-174`). Open Duck Mini v2 (`apirrone/Open_Duck_Mini`, `docs/sim2real.md`, "Not finalized
  yet"): actuators identified with BAM; part masses "override ... with the (pretty accurate) estimation of the
  slicer"; nothing on backlash, IMU, latency or soles.
- Position reference without motion capture: a phone at 60 fps from the side with an AprilTag on the trunk and a
  tape measure on the floor (Wang, Olson, 2016, IROS, "AprilTag 2: Efficient and robust fiducial detection") gives
  trunk x, z and pitch per frame; a plain ruler and the frame timestamps give distance and speed at the centimetre
  level over a 3 s walk, which is all the suite's `dist_x` needs. Encoder-based stance-foot odometry is free but
  assumes no slip, which is exactly the thing under test.

## 4. The program

Rule first (D-016; `SIM2REAL.md:112-114`; memory "training targets the stated failure"): no fine-tune or retrain
until the suite reproduces, at the real condition, the failure that the training is meant to remove; acceptance of
a new policy is fewer falls in that reproduced case and then on the robot.

Session 1 (one robot session, Shawn guarding; items 1-4 need no walking):

1. Sole and floor friction (F1). Real: tilt test of the bare V1.22 foot, the foot with the inner-tube sole, and the
   whole robot (torque off) on the RoboClub floor, the table and the silicone mat; phone inclinometer; record
   mu = tan(angle). Script: none needed (a note in `robot-runs-<date>/README.md`). Model: `--friction` flag in
   `brain_sim_check.py` (loader `evaluate.py:96-100`), suite case `floor_mu_<bare>` and `floor_mu_<sole>`. Proof:
   walk61 at 0.25 m/s on `mu_bare` trips forward with `fell_at` within 0.5 s of 1.2-1.3 s in at least two of three
   seeds, and does not fall on `mu_mat` or `mu_sole`. Value: closes F1 and turns "needs a sole" into a number.
2. Table and floor slope (F9, F4 direction). Real: phone inclinometer along and across the table and the floor
   patch used for walks. Model: rotate the floor plane by the measured angles. Proof: open-loop stand creep direction
   in the sim matches the robot's (forward), and the F4 time-to-fall moves toward 20 s.
3. Mass and centre of mass (F4, F6, the suite's `com+5`). Real: whole-robot weight on a kitchen scale; two-scale COM
   in the STAND pose (toe edge and heel edge); A7Z with header if the head is opened. Model:
   `cmu/model/variants/plugged.json`, `make_variants.py`, `CURRENT-STATE.json` gets a `mass_com` fact. Proof: model
   total within 5 g and COM-to-toe within 2 mm of the measurement; then the open-loop stand at KP 400 in
   `stand_sim.py` falls between 10 and 40 s (robot about 20 s) without a hand-set COM offset.
4. Foot pivot (F4's 12 vs 4 deg). Real: at KP 400 standing, feeler gauge or paper under heel and toe; side video
   with a ruler; the IMU-minus-model pitch series already in `gap_tonight.json`. Model: ankle-foot play joint or
   compliant sole contact. Proof: resting pitch 12 +-2 deg at the robot's measured joints, and the within-stand
   pitch wander reaches at least +-5 deg.

Session 2:

5. Actuator under load at the walking gain (F7, then F2/F5). Real: loaded step tests at P 200 and 400 on all ten leg
   joints with the robot standing (extend `ankle_probe_a7z.py` with a `--loaded` note; same `frac`/breakaway
   metric), plus one XL330 on a pendulum with a weighed mass at 7.0 V through BAM's record script. Model: refit the
   `load_friction_*` terms of `xl330/m6.json` into a CMU parameter file (or a deadband) and load it in
   `evaluate.py`. Proof: per joint, the simulated fraction of a 0.03 rad step at P 200/400 within 10 points of the
   measured one; walk61 still steps at 0.25 m/s in the sim; action jumps over 0.5 rad on at least 20 % of ticks in
   the 0-3 s window (real 35-46 %).
6. Air versus floor (hypothesis 1). Real: the same 3 s walk held in the air and on the floor, gyro spectra by
   `compare.py`. Decision: feet (items 1, 4) or links (item 7) carry the 5-25 Hz content.
7. Backlash and play (F2). Real: torque reversal per leg joint with a marker filmed by the phone; lost motion in
   degrees. Model: the `-Backlash-` mechanism with the measured degrees. Proof: trunk gyro rms in the 0-3 s window
   within a factor of 2 of the real [0.94, 0.93, 1.28] rad/s, with at least half the roll power above 5 Hz.
8. Position reference. Real: phone side video at 60 fps with an AprilTag on the trunk and a tape measure on the
   floor for every walk from now on. Proof: sim `dist_x` within 20 % of the measured distance of the 3 s walks.
9. Servo rail at 50 Hz (F2, minor). Real: fix the `servo_v` read timeout, log a walk. Model: `vin_drop_gain`.
   Proof: the sag amplitude during steps matches within 0.1 V.
10. Replay of the fall (F2, the gate for any training). Sim only, after 1-7: 20 seeds of walk61, 10 s at 0.25 m/s,
    at the measured friction, COM, play and actuator fit. Proof: at least 3 of 20 seeds fall between 3 and 8 s with a
    yaw-rate spike above 6 rad/s in the ten ticks before the fall; the suite then carries that case as `real` and the
    fine-tune acceptance becomes "fewer such falls than walk61".

## 5. What remains unverified

- The tilted table: no measurement anywhere in the repository; the claim is Shawn's observation.
- The A7Z mass (18 g estimate) and the whole-robot weight in each form (`cmu/README.md:58-61`).
- Whether the right ankle still binds with its foot on (CURRENT-STATE: "the foot-on case stays open").
- Whether the 5-25 Hz trunk shake comes from the feet or the links (hypothesis 1 untested).
- The 10/16-17 walk statistics quoted in `SIM2REAL.md` cannot be recomputed (logs not archived).
- The BAM paper's own identification covers MX-64, MX-106 and eRob units; the XL330 parameters are the package's,
  recorded at 7.5 V, and their validation data were not read tonight.
- Whether a `--quack-at` run with the open-loop gate bypassed tips the sim (F6): one run, not done tonight.
