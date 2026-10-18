# Servo-rail current on a 2S LiPo, 2026-10-15

Problem (P5, energy on the body): size a 2S LiPo wired straight to the MicroDuck servo bus (15 XL330-M288-T; bus 6.4 V empty, 7.4 V nominal, 8.4 V full). This folder estimates the bus current from the as-built V1.9 simulation running walk61/stand61 and checks the model against the one current reading taken on the real robot. Evidence that would change the numbers: a 50 Hz log of summed Present Current while the real robot walks on the rail it will use.

Every number below is simulation unless it is marked **measured** or **implied**.

## Result at 7.4 V (simulation)

Bus current is what the pack delivers to the servo bus. It includes 15 × 17 mA standby (0.255 A) and excludes the Pi, camera and amplifier. Each line gives mean / highest 1 s mean / highest 100 ms mean / highest 20 ms mean.

- **stand61, 10 s from STAND:** 0.49 / 0.93 / 1.66 / 2.13 A. The peaks come from the first second, when stand61 moves the robot from STAND to its own pose. Steady part (2 to 10 s): 0.43 / 0.45 / 0.46 / 0.46 A.
- **walk61 vx 0 from STAND:** 0.37 / 0.37 / 0.39 / 0.45 A. walk61 does not step at this command; the robot stands.
- **walk61 vx 0.15 from STAND:** 0.35 / 0.36 / 0.39 / 0.45 A. It does not step either (4 mm in 10 s).
- **walk61 vx 0.1 after 2 s at vx 0.3:** 0.61 / 0.64 / 0.81 / 0.88 A. Slowest command that keeps stepping (0.33 m in 10 s, each foot lifts about twice per second); the closest thing to walking in place.
- **walk61 vx 0.15 after 2 s at vx 0.3:** 0.63 / 0.66 / 0.90 / 0.99 A (0.62 m in 10 s).
- **walk61 vx 0.3 from STAND:** 0.71 / 0.87 / 1.44 / 2.14 A (1.68 m in 10 s).
- **Sit to stand (BEST_alpha_sitstand), 8 s:** 0.48 / 1.26 / 4.56 / 5.73 A; mean over the rise (1 to 4 s) 0.66 A. At least one servo reaches the 1.47 A current limit during the rise.

Motor share of the mean bus current by group (standby excluded), left leg / right leg / head and neck:

- stand61 0 to 10 s: 0.114 / 0.102 / 0.016 A
- walk61 vx 0 from STAND: 0.050 / 0.052 / 0.015 A
- walk61 vx 0.15 from STAND: 0.026 / 0.059 / 0.014 A
- walk61 vx 0.1 after start: 0.150 / 0.184 / 0.024 A
- walk61 vx 0.15 after start: 0.173 / 0.176 / 0.024 A
- walk61 vx 0.3: 0.230 / 0.197 / 0.031 A
- sit to stand 0 to 8 s: 0.089 / 0.110 / 0.029 A

What this means for the pack (servo rail only):

- **Continuous:** about 0.7 A walking and 0.4 to 0.5 A standing. Each 1000 mAh of usable capacity gives about 84 min of continuous vx 0.3 walking.
- **Short peaks:** about 2.2 A over 20 ms when walking or when stand61 takes over from STAND; 5.7 A over 20 ms and 4.6 A over 100 ms during sit to stand (6.6 A and 5.0 A with the factory 1.75 A servo current limit).
- **Ceiling:** if all 15 servos saturate at their current limit at full duty at once, the bus carries 15 × 1.47 A / 0.9 = 24.5 A (29.2 A at 1.75 A). Falls and stalls were not simulated; they can approach this briefly.
- **Supply voltage matters little:** at 6.6 V walking vx 0.3 is 0.75 / 0.92 / 1.53 / 1.99 A and at 8.2 V 0.70 / 0.87 / 1.45 / 2.16 A; stand61 steady 0.45 A at both; sit to stand 20 ms peak 5.5 A (6.6 V) and 4.9 A (8.2 V). Full lists are in `results.json` (`summary`).

## Why the battery current is much lower than summed motor current

A servo's H-bridge draws its duty cycle times the motor current from the bus. A servo that holds a load against gravity carries motor current at a low duty: a knee holding the stand61 pose carries about 0.26 A at about 0.7 V across the motor, so it draws about 0.03 A from a 7.4 V bus. The summed motor current Σ|τ|/kt therefore overstates the battery current:

- walk61 vx 0.3 at 7.4 V: motor-current sum mean 2.53 A, highest 1 s 2.85 A, 100 ms 4.00 A, 20 ms 5.42 A; group means left leg 1.09 A, right leg 1.04 A, head and neck 0.40 A. The bus current is 0.71 A mean, 3.5 times lower.
- walk61 vx 0.3 at 5 V: mean 3.12 A, 1 s 3.37 A, 20 ms 4.22 A; groups 1.18 / 1.27 / 0.68 A. This sits inside the range of the older 5 V proxy file `guide/content/interference-audit/open-issues/evidence/leg-current.json` (phase-1 candidate policy, older model, 33 traces): 14-servo mean 2.0 to 3.4 A, highest 1 s 2.0 to 3.5 A, peak 2.7 to 5.5 A; left leg 0.87 to 1.29 A, right leg 0.80 to 1.32 A, head 0.33 to 0.80 A. That file is a motor-current sum and is not a battery current. Its peak is one 50 Hz sample; here the 20 ms value is a mean of eight 2.5 ms samples.

At 7.4 V walking, 2.26 W of the 3.05 W motor input is copper loss (I²R) and 0.74 W leaves as mechanical work.

## Sanity check against the real robot at 5 V

**Measured** (2026-10-13, `guide/firmware/pi/stand.py`, STAND_POSE, KP 400, jaw torque-off, standing unassisted on the 5 V bench supply): about 0.165 A summed |Present Current| over 14 servos (`stand.py:185-186`; XL330 Present Current is motor current in 1 mA units). The value comes from the bring-up record; the raw printout was not kept.

Same quantity (summed |motor current|) in the 5 V simulation:

- Static KP 400 STAND hold, nominal model: falls backward at 0.6 s, as in `realgap-20261014/README.md` section 2, so there is no hold to compare.
- Static hold with COM +10 mm (ends at body gravity x +0.18, close to the robot's +0.08 to +0.17): 1.24 A, 7.5 times the measurement.
- Static hold with hip-pitch zero +8 deg (ends at gravity x +0.10, inside the robot's +0.08 to +0.17): 0.51 A, 3.1 times.
- stand61 at KP 200, 2 to 10 s: 1.68 A, 10 times. Most of it is the two hip-roll servos (0.20 and 0.27 A, mirrored signs) plus the knees (0.30 and 0.28 A). The same hip-roll servos carry 0.02 A in the static STAND hold, so the stand61 pose most likely squeezes the legs against each other through the feet (inference).

**Implied** (`stand_log_check.py`): the 2026-10-14 wired log holds the same STAND goal at KP 400 in about 16 minutes of stand-mode rows (44,965 quiet, upright samples). Feeding its measured position errors through the BAM control law at 5 V (35.7 mA per degree of error at a stalled joint) gives 0.53 A (10th to 90th percentile 0.52 to 0.53 A), 3.2 times the measurement. The left hip yaw (4.1 deg error, 0.15 A) and left knee (3.1 deg, 0.11 A) carry half of it. The log does not record whether the robot stood or was held.

Reading:

- The model overestimates holding current by a factor of 3 to 10.
- The BAM law applied to the robot's own errors lands next to the +8 deg sim hold, so part of the gap sits between the BAM control law and the Present Current reading. Three causes fit: Present Current reads low at small currents, the robot was loaded differently on 10/13 than on 10/14, or the real servo puts out about a third of BAM's PWM per degree of small error. The saved logs cannot separate them: the 10/13 hold kept no position errors and the 10/14 log kept no currents.
- Effect on the estimate: holding current reaches the pack as copper loss divided by the bus voltage, so it shrinks with the square of the current. At 7.4 V the motor share of the stand61 estimate is 0.18 A of 0.43 A; the rest is datasheet standby. If real holding current is 3 to 10 times lower, standing draws 0.26 to 0.28 A. The walking mean shares the same static load and is probably high as well. The dynamic peaks (swing, foot strike, sit to stand) are not tested by this measurement in either direction.
- The check that settles it is one hold that logs Present Current and Present Position together, plus a 50 Hz summed Present Current log while walking, on the rail the robot will use.

## Method

Runs (one seed, nominal COM, V1.9 as-built mass with the 90 g battery removal, BAM xl330 m6, 50 Hz policy, KP 200 for policies):

- **Policy runs** copy the `realgap-20261014/policy_test.py:21-77` loop with no injected gaps: feet flat at STAND, stand61 from t = 0, one tick sensor and one tick action delay. Walk cases run stand61 for 3 s, then walk61 at the command for 10 s (window 3 to 13 s), as in `margins.py`. The stand case runs stand61 for 10 s.
- **Starting the gait:** from rest walk61 lifts no foot at vx 0, 0.1, 0.15 or 0.2, nor at vx 0 with yaw rate 0.5 or 1.0 rad/s; it steps at 0.25 and 0.3. Once stepping it keeps stepping down to vx 0.1 and stops within a step at vx 0. The "after 2 s at vx 0.3" cases run walk61 at 0.3 from 3 to 5 s, then at the target command from 5 to 15 s (window 5 to 15 s).
- **Sit to stand** copies `realgap-20261014/sitstand_volt.py:11-30`: SIT keyframe, community BEST_alpha_sitstand, sit command for 1 s, then stand, no delays.
- **Static holds** follow `realgap-20261014/ramp_test.py`: KP 400, STAND target, 5 s, window 2 to 5 s.
- **Voltages:** 7.4 V for all cases, 6.6 V and 8.2 V for the policy and sit-to-stand cases, 5.0 V for the sanity check and one walk. Current limit 1.47 A everywhere; 1.75 A repeated for 7.4 V walk vx 0.3 (no change: 0.71 / 0.87 / 1.44 / 2.17 A) and sit to stand (0.50 / 1.33 / 4.95 / 6.59 A).

Bus-current model, applied at every 2.5 ms sim step for each of the 14 simulated joints:

- τ = `d.actuator_force`, the BAM electromagnetic torque kt·I. MuJoCo applies the gearbox friction separately (`bam/mujoco.py:157-163`), so τ includes the torque the motor spends on friction. ω = the joint speed the BAM controller used for that step.
- I = τ/kt, V_m = I·R + ke·ω with ke = kt in SI units, P = V_m·I. V_m reproduces the BAM command voltage vin·duty; it never exceeded the bus voltage and reached it only during sit to stand (at 6.6 V, and at 7.4 V with the 1.75 A limit).
- I_bus = Σ max(P, 0) / V_bus / η + 15 × 0.017 A, with η = 0.9 for the H-bridge and board, an assumption. Regenerating motors are dropped. Letting their power offset other motors on the shared bus lowers the walking mean by 1 % (0.705 A).
- Proxy = Σ|τ|/kt over the 14 joints, no standby.
- Windows are rolling means over 400, 40 and 8 steps (1 s, 100 ms, 20 ms); the reported value is the highest one in the case window.
- The jaw (ID15) is not in the model; only its standby is counted.

## Parameter sources

BAM is `better_actuator_models` 1.0.1 in `~/.venvs/microduck-dyn/lib/python3.12/site-packages/bam/`.

- **kt = 0.36601 N·m/A at the output shaft**, also used as ke in V·s/rad: `bam/params/xl330/m6.json:2`. Cross-check: the e-manual's 5 V stall point gives 0.52 N·m / 1.47 A = 0.354 N·m/A.
- **R = 2.8114 Ω**: `bam/params/xl330/m6.json:3`. The e-manual stall point gives 5.0 V / 1.47 A = 3.40 Ω, which includes the driver.
- **Control law:** `bam/actuator.py:251` duty = Δq · kp · error_gain; `:258-264` the current limiter narrows the duty window so |I| ≤ max_current given the back-EMF; `:267` |duty| ≤ max_pwm = 1; `:269` V = vin · duty; `:294-296` τ = kt·V/R − kt²·ω/R. error_gain = 4096/(2π)/(256·885) = 0.002877 per rad from `bam/dynamixel/actuator.py:80-82,95-96`.
- **Voltage handling in the model:** `delay-repair-20260912/evaluate_delay.py:68` sets vin from the run's `voltage`. There is no supply sag: `evaluate_delay.py:112` passes wire_resistance 0.0, and with a resistance of 0 `bam/mujoco.py:104-112` leaves vin unchanged. The fit voltage of m6 is not recorded; the XL330 class default is vin 7.5 V (`bam/dynamixel/actuator.py:93`). Higher vin raises the voltage per degree of error, so the servos act stiffer.
- **Current limit:** `evaluate_delay.py:69` default 1.47 A (the 5 V stall current); BAM's XL330 default 1.75 A (`bam/dynamixel/actuator.py:99`); the community runtime uses 1.75 A (`guide/firmware/pi/microduck_rt/constants.py:59`); the servo's Current Limit register (38) starts at 1750 mA, range 0 to 1750 (e-manual). The torque clamp `evaluate_delay.py:70-71,78` (forcerange = min(vin·kt/R, I_max·kt)) never bound in these runs.
- **Friction:** `bam/model.py:114-197`, load-dependent gearbox friction written to MuJoCo frictionloss and damping every step.
- **Datasheet values** (ROBOTIS XL330-M288 e-manual, https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/, checked 2026-10-15): input voltage 3.7 to 6.0 V, recommended 5.0 V; stall 0.52 N·m at 5.0 V and 1.47 A; standby current 17 mA; Present Current (126) unit 1 mA; Max Voltage Limit (32) initial 70, range 31 to 70, 0.1 V units; Shutdown (63) initial 53, bit 0 = Input Voltage Error.

## Servo voltage limits on a 2S pack

These are facts for the battery decision; the estimate above does not depend on them.

- The XL330-M288-T is rated 3.7 to 6.0 V. Its Max Voltage Limit cannot be set above 7.0 V, and the factory Shutdown value 53 includes the Input Voltage Error bit, so a servo that sees more than 7.0 V clears its torque.
- A 2S pack stays above 7.0 V from full charge (8.4 V) down to 3.5 V per cell, which covers most of its discharge. With factory settings the servos would drop torque over that range.
- `PROJECT-CONTEXT.json` (`current_build.servo_rail_7v_20261014`) records that Pollen feeds its servos 7.2 V with Shutdown 52 (bit 0 cleared), and that this build chose the 6.8 V rail (D-007) to keep the factory protection. `guide/firmware/pi/check_voltage_limit.py` fails any rail outside 6.5 to 7.0 V.
- The policies were trained with vin 6.5 to 8.2 V (`microduck_rl/src/mjlab_microduck/robot/microduck_constants.py:126`); a freshly charged 8.4 V pack starts just above that range.

## Limits

- Simulation only. The 5 V check shows holding current is overestimated by 3 to 10 times; walking and sit-to-stand peaks have no hardware check.
- One seed, flat floor, nominal model. The real robot sits about 10 mm or 10 deg further forward (`realgap-20261014`); those variants were not run here.
- Averaged PWM model: continuous motor current within each PWM period, constant η = 0.9, standby constant with voltage, regeneration dropped.
- No pack or wiring sag. At the 2 A walking peaks a 50 mΩ pack and harness lose about 0.1 V.
- Falls, pushes and recovery were not simulated. The jaw's holding current, the Pi, camera, IMU and amplifier are outside this estimate.
- The no-step band below vx 0.25 from rest is a property of this simulation; the real robot may start stepping at a different command.

## Files

- `power_runs.py`: all cases and the bus-current analysis; writes `results.json`. `~/.venvs/microduck-dyn/bin/python power_runs.py` takes about 50 s on 4 workers.
- `stand_log_check.py`: implied hold current from the real robot's position errors; reads `/tmp/duck_wired_log.jsonl` (2026-10-14) and is folded into `results.json` when that file exists.
- `results.json`: `meta` (parameters and formula), `summary` (headline windows at 6.6, 7.4 and 8.2 V), `real_stand_log_check`, and `cases` (every run with outcome, per-window bus and proxy statistics, group and per-joint currents, power split, gait metrics).
