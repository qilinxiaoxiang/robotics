# MicroDuck head touch: findings (2026-10-21, robot off, A7Z offline)

Repo: /Users/xiangzheng/code/robotics (paths below are relative to microduck-sim/ unless absolute). Nothing under the
repo was edited; sims ran with `timeout 600`, one process at a time. Evidence classes: [code] = read from the file at
the cited line, [log] = computed tonight from an archived robot log, [sim] = as-built MuJoCo run tonight, [state] =
CURRENT-STATE.json, [paper] = published source read tonight, [vendor] = a company's own page, [inference] = my reading.

## Q1. What the touch system delivers now

**Firmware (XIAO ESP32-S3).** `guide/extension-20261015-touch/firmware/touch_xiao/touch_main.cpp` [code]:
- Rate: line 13 `static const uint32_t PERIOD_MS = 20;`, lines 38-41 gate `loop()` on `millis()`: one scan of the five
  pads every 20 ms (50 Hz). Line 3: "Reads the five copper pads with the ESP32-S3 touch peripheral at 50 Hz".
- Filtering: none. Line 44 `for (int i = 0; i < 5; i++) v[i] = touchRead(PAD_PINS[i]);` is the raw count; no baseline,
  threshold, debounce or smoothing in the file. Line 4: "raw counts; on the S3 a touch raises them".
- Block: line 5 "I2C slave 0x2A on D4 (SDA) / D5 (SCL): a 24-byte block, uint32 LE sequence number then the five uint32
  LE counts"; `onRequest()` lines 17-29 serialises seq, L1, R1, L2, R2, M little-endian. Pads line 6: "L1 D0 (GPIO1,
  T1), R1 D1 (GPIO2, T2), L2 D2 (GPIO3, T3), R2 D3 (GPIO4, T4), M D8 (GPIO7, T7)".
- Serial twin: line 51 prints `T,<ms>,<L1>,<R1>,<L2>,<R2>,<M>` at 50 Hz (USB on the Mac only).
- Trap: `touch_live_a7z.py:151-153` "touch_main.cpp leaves max_meas_time_us at 0, so a pad that never charges holds the
  scan on that pad forever and the other pads keep their last count (2026-10-20: M shorted, the four others frozen)".

**Readers.** [code]
- `firmware/touch_live_a7z.py`: `/dev/i2c-N` of TWI0 (lines 57-61, node `twi@2510000`), `os.read(bus, 24)` (line 114),
  `time.sleep(0.02)` (line 156): a 50 Hz display, delta against the first block (`start_v`, line 137), bar full at
  `FULL = 2000` (line 19). Display only.
- `firmware/touch_live.py`: the same bar over USB serial on the Mac (lines 13-39).
- `firmware/touch_bench.py`: PLAN.md acceptance item 2 (`RATIO_MIN = 5.0` line 27, `CROSS_MAX = 0.20` line 28). The only
  recorded run, `touch_bench_20261020_212038.json` (2026-10-20 21:19, "1.7 mm PLA", pad L1 on the bench): rest_median
  19537, rest_noise_std 122, touch_delta -8, ratio -0.1, **pass: false**. Its 5 s touch phase holds 251 samples (50 Hz
  confirmed); the 10 s rest phase holds 2270 lines (a serial backlog). The quantitative fingertip signal through the
  wall is NOT on record as passing.
- `microduck_rl/cmu/simulator/desktop/duck-telemetry.py` (piped over SSH by `app/a7z-bridge.mjs:39` as `duck-telemetry
  fast touch [bus]`): class `Touch`, `PERIOD = 0.1` (line 136), a thread reading one block per period (lines 242-278);
  docstring lines 17-21: "A thread reads it about 8 times a second through TWI0 ... The newest block rides on every
  record". `state()` (lines 280-292): seq, five counts, ok/bad, bus, `stuck` (saturated > 2 s).
- Monitor card `microduck_rl/cmu/simulator/app/src/robot-live.js:27-58`: `TOUCH_FULL = 2000`, zero from the first block
  or the 归零 button (lines 29, 37, 44), bar `(v - touchZero) / 2000`, red when saturated; card in `app/robot-live.html:87-89`.

**Current state** [state] `CURRENT-STATE.json` `a7z_touch_bus` (verified 2026-10-21): "XIAO ESP32-S3 at I2C 0x2A on
/dev/i2c-0 = TWI0 (2510000.twi, engine mode) on A7Z header pins 29 (PB2, SCL, blue) and 31 (PB3, SDA, green), 3V3 red
pin 17, GND black pin 25 ... a plain 24-byte read returns the block aligned (no filler byte); all five head pads (L1,
R1, L2, R2, M) rise when pressed; rest counts 22100-26300". Source: "100/100 reads of 24 bytes in 2.3 s with 0.01 s CPU
in total; robot monitor 611 reads 0 lost on /dev/i2c-0 ... Pads: 2026-10-20 Shawn pressed each pad on the robot monitor
and all five bars rose." The rise per pad is not recorded (bar scale 2000 counts).

**Pad geometry** [code] `touch_routes.json:25-61`: l1 18 mm at (40, 22), r1 18 mm at (40, -22), l2 12 mm at (20, 27),
r2 12 mm at (20, -27), m 12 mm at (48, 0) (robot frame mm, x forward, y left); `bringup/A7Z-TOUCH.html` ("L1、R1：18 ×
18 mm ... L2、R2、M：12 × 12 mm"); D-013. L1/R1 are 44 mm apart; L1 -> L2 is 20 mm back; M sits 8 mm ahead of the
L1/R1 row on the centre line. A front-to-back stroke crosses M then L1/R1 then L2/R2 (20-28 mm: 0.2-0.7 s at the
3-10 cm/s people stroke at, PLAN.md:48).

**Does a touch enter the control loop?** No. [code] `grep -n -i touch guide/firmware/mac/walk_wired.py walk_brain.py
duck_sense.py` returns only `walk_brain.py:72` ("without touching", the ground-pick policy). The brain's loop
(`walk_wired.py:429-764`) reads the servo bus (line 431), the IMU (lines 445-446) and the control file (line 447); no
pad read, no pad field in the tick log (lines 730-742). The pads reach only the monitor card.
- Rate on the brain: 0 Hz. Rate on the monitor: about 8-10 blocks/s; the firmware's 50 Hz is decimated 5-6x.
- Latency to the monitor [inference from the periods]: 20 ms scan + up to 100 ms telemetry poll + up to 100 ms record
  period (`PERIOD = 0.1 if "fast"`, duck-telemetry.py:36) + SSH/page draw: about 0.15-0.3 s, up to ~0.6 s at the
  0.5 s record period. Not measured tonight.
- Cost of putting it in the loop: one 24-byte kernel read is about 0.1 ms CPU (CURRENT-STATE: 100 reads = 0.01 s CPU)
  and ~2.5 ms wall at 100 kHz; on a thread like `Link._local_imu` (walk_wired.py:135-157) it adds nothing to the 20 ms
  tick. Only when the brain runs on the A7Z (the Mac brain over USB has no path to the XIAO).

Unverified / closing check:
- Fingertip delta vs noise per pad in the closed head: a 10 s rest + 5 s touch per pad on the A7Z through
  `touch_live_a7z`-style reads; pass = delta >= 5x rest std on every pad and cross-trigger < 20 % (PLAN.md item 2).
- Scan time of the five `touchRead` calls inside the 20 ms: compare the serial `ms` stamps with the host clock over 60 s.

## Q2. Servo signals at 50 Hz, Present Current, and what a touch looks like in the logs

**Sync read today.** [code] `walk_wired.py:90` `ADDR_TORQUE, ADDR_P_GAIN, ADDR_GOAL, ADDR_VEL = 64, 84, 116, 128`; line
431 `got = link.sync_read(ADDR_VEL, 8, IDS + [JAW_ID], timeout=0.018)`; line 437 `vel[k], pos[k] = struct.unpack("<ii",
got[i])`: Present Velocity (128, 4 B) + Present Position (132, 4 B) for IDs 1-15. Goals: line 678. Log fields lines
738-739: `acc=acc, imu_seq=imu_seq, pos_tick=list(pos), vel_tick=list(vel), goal_tick=goal_written, cmd=want,
servo_v=servo_v` (README 10/19 line 3 agrees).
- Voltage: lines 725-728, one servo per tick round robin after the goal write, `timeout=0.003`; README 10/19 line 29:
  "`servo_v` returned None on most ticks (3 ms timeout after the goal write); the round-robin voltage read needs a
  longer timeout or its own slot before it counts as 50 Hz coverage."
- Timing: README 10/19 line 12 "servo sync read 8.5 vs 5.2 ms, loop 12.2 vs 5.7 ms" (A7Z 500 kbaud vs Mac 1 Mbaud).

**Present Current / Present Load.** [vendor] ROBOTIS e-Manual XL330-M288 (read tonight,
https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/): 124 Present PWM (2 B), **126 Present Current (2 B, 1 mA)**, 128
Present Velocity (4 B), 132 Present Position (4 B), 144 Present Input Voltage, 146 Present Temperature; **no "Present
Load" on the XL330** (that register is on the XL430 family). The manual notes the XL330 measures current at its input
power source, not the motor phases. Nothing reads 126 at 50 Hz today [code]: `pi/current_watch.py` is a bench tool
("Present Current (XL330 address 126, 2 bytes, 1 mA)"); `pi/microduck_rt/constants.py` has `PRESENT_CURRENT_UNIT_A =
0.001` and a current proxy for when it is not read.
- Cost to add [inference from `pi/dxl_fast.py:43-47` `want = len(ids) * (11 + size)` and PLAN.md:17-19 "reading
  126..135 as one 10-byte block adds current for every servo in the same packet"]: `sync_read(126, 10, ...)` and
  unpack `<hii`. The instruction packet grows 0 bytes; each of 15 status packets grows 2 bytes: +30 bytes = +0.3 ms at
  1 Mbaud (Mac), +0.6 ms at 500 kbaud (A7Z), inside the same transaction, so no new slot and no new timeout, unlike the
  voltage read. Expected read 5.5 ms Mac / 9.1 ms A7Z. Unverified until a log row's `read_ms` after the change.
- What current is worth [log] `robot-runs-20261018/ankle-probe-20261019/leg_probe_a7z_1019.out` (feet off, duck held):
  unloaded leg joints at P 400 hold with `cur_mA` 0-23 and `hold_err` 1-21 ticks. No loaded (standing) current record
  exists; the first 10-byte-block log on stand61 gives it.

**What an impact on the head looks like.** [log] `robot-runs-20261018/duck_wired_log_1018d.jsonl.gz` (README line 9:
"After the second walk stand61 sat still for 20 s, had bursts from +26 s (possibly a touch), then a growing in-place
oscillation from +34 s; largest actions on head_yaw; 3-of-10 guard at +39.9 s"). Analysed with `scratchpad/an_1018d.py`,
times relative to `walk_t0_1018f` = 1792359594.268:
- The 10/18 rows carry `q, dq, action, gb, gyro_body, quat` but **no `acc`** (keys checked; `acc` joined the row on
  10/19). IMU accel for a touch exists in no archived log; gyro and gravity do.
- Quiet stand61 (+8 to +24 s): |gyro_body| mean 0.00-0.06 rad/s, max 0.17; gb (+0.066, -0.012, -0.998); head actions
  <= 0.11 rad. Static head offsets while quiet: measured (neck_pitch, head_pitch, head_yaw, head_roll) = (0.431, 0.023,
  -0.430, -0.097) rad against goals default + action = (0.24, 0.30, 0.00, -0.045): errors (0.19, 0.28, 0.43, 0.05) rad
  that do not move. [inference] a head-error feature must use the *change* of the error, never its absolute value.
- Burst 1 (+26 s): |gyro| mean 0.79, max 2.64 rad/s; head actions jump to 0.60 (neck_pitch) / 0.53 (head_yaw) / 0.40
  (head_roll); head_roll error 0.05 -> 0.12 rad; gb unchanged within 0.01; legs' max action 1.24 rad.
- Burst 2 (+29.4 to +29.6 s): gyro_body reached (0.39, 0.39, 4.19) then (-0.27, -1.89, **6.04**) rad/s (a yaw-rate
  spike); measured neck_pitch 0.43 -> 0.81-0.88 rad and head_yaw -0.43 -> -0.65 rad within 0.1 s while gb stayed within
  0.1 of upright; head actions reached 1.16 (neck_pitch) and 1.14 (head_yaw). [inference] head joints displaced 0.2-0.45
  rad from goal in 0.1 s with the trunk hardly tilting: consistent with a hand on the head, not with a trunk
  disturbance. Not provable from this log (no pads, no acc).
- From +34 s the oscillation grows (|gyro| mean 1.6-2.9 rad/s, head actions 0.6-1.2), the 3-of-10 guard trips at
  +39.9 s (action 3.61), open-loop stand mode, the robot creeps and falls (+40 s gb x -0.95).
- Lesson: on stand61 a touch shows as a gyro burst plus a step in head-joint error with gravity unchanged, and the
  policy answers a head push with large head actions, which here started a divergence. Reactions must go through the
  head EMA (HEAD_ALPHA 0.2) and the quack-style ramp, never a step.

Closing check: one labelled session of pads + brain log (acc now in the rows) on stand61; every labelled touch must show
the pad delta first and the gyro/head-error signature within 2 ticks.

## Q3. Classifier: stroke vs pat (relaxed vs angry)

**Literature.**
- CoST, Jung, Poel, Poppe, Heylen, *J. Multimodal User Interfaces* 11(1):81-96, 2017, DOI 10.1007/s12193-016-0232-9
  [paper, abstract via research.utwente.nl]: 7805 captures, 14 gestures (grab, hit, massage, pat, pinch, poke, press,
  rub, scratch, slap, squeeze, stroke, tap, tickle) in gentle/normal/rough variants on a pressure grid around a
  mannequin arm; "Recognition of these 14 gesture classes using various classifiers yielded accuracies up to 60 %";
  "gentle gestures proved to be harder to classify than normal and rough gestures". ICMI 2014 version: 54 % Bayesian /
  53 % SVM on the rough variants (search summary, not read).
- Touch Challenge '15 (Jung, Cang, Poel, MacLean, ICMI 2015; PDF read, `scratchpad/pdfs/challenge2015.txt`): CoST best
  61.3 % (Ta et al., random forest, Table 2 line 160); HAART (7 classes incl. no-touch, 8 s windows at 54 Hz) best 70.9 %
  (line 177); "Frequent confusions between touch gestures for the CoST data ... 'grab-squeeze', 'hit-pat-slap-tap',
  'rub-stroke', and 'scratch-tickle'" (lines 172-174). Features borrowed from speech and action recognition (lines
  145-146): pressure statistics over time, contact area, temporal/frequency descriptors.
- Cang, Bucci, Strang, Allen, MacLean, Liu, "Different Strokes and Different Folks", ICMI 2015 (PDF read,
  `scratchpad/pdfs/cang2015.txt`): six gestures + no-touch (constant, pat, rub, stroke, tickle, scratch) on a fabric
  multitouch pressure sensor; "For a stationary sensor, a random forest model achieved 90.0% recognition accuracy
  (chance 14.2%) when trained on all data, but as high as 94.6% (mean 89.1%) when trained on the same individual. A
  curved, flexing surface achieved 79.4% overall but averaged 85.7% when trained and tested on the same individual"
  (lines 22-26); "91.4% on a firm, flat surface, 90.3% on a foam, curved surface, and 88.4% on a foam, curved, moving
  surface" (lines 79-80); constant 92.7 % and pat 88.9 % were the best-recognised gestures (lines 340-341); "seven
  features across these three dimensions (frame ... area under the curve" (lines 311-315).
- Flagg & MacLean 2013 (furry zoomorphic machine), as cited in PLAN.md:44-47: nine gestures "at 94% per person and 86%
  across 16 people"; FSRs rejected because they "don't function well on curved surfaces" and are "insensitive to light
  touches".
- Haptic Creature (Chang, MacLean, Yohanan, EuroHaptics 2010): FSR network, four gestures (pat, stroke, poke, squeeze),
  average 77 % in the densest region. [secondary: search summary only]
- Paro: "twelve tactile sensors covering its fur, touch-sensitive whiskers" (Wikipedia citing WSJ 2010); "Paro loves to
  be petted"; sensors "Light sensor, temperature sensor, tactile sensors (body and whiskers), microphone array"
  (robotsguide.com). The stroke-vs-hit distinction often attributed to Paro was NOT verified tonight (Shibata's deck
  exceeded the fetch limit; parorobots.com certificate error).
- Sony aibo ERS-1000 [vendor, helpguide.sony.net]: head and jaw "Capacitive type touch sensor", back "Pressure
  sensitive/capacitive type touch sensor" (TP0001970140); "When you pet your aibo on the head or back or under the chin,
  aibo takes it as 'a compliment.'" and "When you tap your aibo on the back, aibo takes it as 'a scolding.'"
  (TP0001970100); lift (TP0001970098): "When aibo senses that it is 'being lifted,' aibo lets all the body joints relax
  for safety and then takes the posture of lying down." and "Do not lift aibo by grasping its head, ear, front paw, back
  paw, or tail".
- Reading across them [inference]: stroke vs pat is separated by motion across sensors (travelling contact, longer
  duration) versus repeated short contacts (high rise slope, several rises); intensity (gentle/normal/rough; pat vs
  hit/slap) is the hardest axis in every CoST study and is separable only by peak pressure and rise rate, which on five
  capacitive pads map to peak delta, rise slope and the head's mechanical response (gyro, acc, head-error jump).
  Within-person models score 5-10 points higher than cross-person ones (Cang 2015, Flagg 2013), which fits a
  one-performer (Shawn) first session.

**Feature set** (`scratchpad/touch-gesture/features.py`): duration; number of pads on (delta > max(5x rest std, 150
counts), both from the recording); peak delta and second peak; max rise slope (counts per tick); onset spread between
pads; order score along L1 -> R1 -> M (+1 that way, -1 reversed, 0 otherwise); number of rises of the strongest pad
(taps) and inter-tap interval; simultaneity (>= 2 pads with onsets within 100 ms); IMU |acc| peak deviation from 9.81
and |gyro_body| peak; the head-joint error *jump* from the window start; the share of M. Expected separation: stroke =
ordered onsets, spread > 0.15 s, one rise per pad; pat = onsets within 0.1 s on neighbouring pads, 1-3 rises 0.2-0.6 s
apart; angry pat = same with rise slope and peak in the top band plus a gyro/acc/head-error jump. Model: multinomial
logistic regression on standardised features (`train_touch.py`, numpy, seconds on the Mac); a tiny GRU only if the hand
features plateau under 85 %.

**Data-collection protocol.**
1. Live bar first: `touch_live_a7z.py` on the A7Z for 30 s while Shawn presses each pad once; every bar rises, none red.
   Then the per-pad rest/touch calibration (Q1 check) sets the thresholds.
2. Robot on stand61 (walk mode, zero command), Shawn guarding, brain on the A7Z (tick log with acc/gyro/q/action at
   50 Hz). `record_touch.py --out ~/duck-logs/touch_<session>.jsonl` shows the bar and takes label keys: s stroke
   (front-to-back, M/L1/R1 -> L2/R2, 3-10 cm/s, one pass), p relaxed pat (2-3 light pats), a angry pat (2-3 hard quick
   pats), c carry grip (M+L1+R1 held, no lift), n none.
3. Counts: stroke x30, relaxed pat x30, angry pat x30, carry grip x15, plus 5 min of no-touch on stand61 with quack
   head moves and two 3 s walks (negatives). Performer: Shawn (session 1); a second performer later. Hold-out: the
   last third of every class. About 25 minutes of robot time.
4. Label tool: key at start / space at end in the same JSONL; no video.
5. Layout proposal (drafts in `/private/tmp/claude-501/-Users-xiangzheng-code-robotics/74602e44-fa79-4564-a436-c7a3c8ce2ecd/scratchpad/touch-gesture/`):
   `guide/extension-20261015-touch/gesture/record_touch.py` (A7Z), `features.py`, `train_touch.py` (Mac), `data/<date>/`
   (recordings + the matching `duck_wired_log_<suffix>.jsonl.gz`), `models/touch_lr.json`, `README.md`. Runtime
   consumer: a `TouchSense` thread in `walk_wired.py` on the A7Z (like `Link._local_imu`) that reads the block each
   tick, applies the thresholds, runs the model on a closed episode and writes `touch_event` into the tick log and the
   control-file reaction (Q4).
6. Acceptance: held-out accuracy >= 85 % over stroke / relaxed pat / angry pat (Cang 2015 within-person 85-95 % on a
   richer sensor is the ceiling; PLAN.md item 5 asks 18/20 per gesture), relaxed<->angry confusion <= 15 % each way,
   zero events in the 5 min no-touch recording (PLAN.md item 5). If angry vs relaxed cannot reach 15 % on pads alone,
   the acc/gyro/head-error features decide; if still not, merge the pats and keep "angry" as a threshold on the
   physical response only.

## Q4. Reactions inside the trained envelope

**Envelope.** [code] `microduck_rl/src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py:49` `HEAD_POSE_CMD_RESAMPLE_S =
(2.0, 5.0)`; final ranges lines 662-664 and 825: "neck_pitch / head_pitch: ±1.10 rad ... head_yaw : ±1.40 rad ...
head_roll : ±0.31 rad". Runtime `walk_brain.py:79-81` `HEAD_RANGE = (1.10, 1.10, 1.40, 0.31)`, `HEAD_ALPHA = 0.2`;
`head_target()` lines 379-386 takes absolute model-rad targets and clips the delta from default (0.3491, 0.3491, 0, 0);
obs slots 55-58 (lines 75-78), EMA per tick (line 517). Signs: `pi/joint_signs.py:7` "head_pitch -1 (+ = beak down)";
walk_wired.py:259 "head_pitch negative looks up".
- Template [code] `walk_wired.py:265-269`: `QUACK_HEAD = ({"head_roll": (0.08, 0.18), "head_yaw": (0.0, 0.25)},
  {"head_pitch": (0.15, 0.30, -1), "head_roll": (0.0, 0.10)})`, `QUACK_HEAD_S = 1.6`, `QUACK_HEAD_RAMP_S = 0.5`,
  `QUACK_REST_S = 2.0`; `quack_head_share()` lines 276-279 (raised cosine up, hold, down); gate `quack_head_block()`
  lines 282-303: allowed in walk mode at zero command (stand61, or walk61 >= 2 s after a stop) and seated; refused
  while "walking", "sitting down", "standing up", "a head command is active", and in open-loop stand mode ("open-loop
  stand mode cannot rebalance", "it tipped over there on 2026-10-20"). `quack_head_pose()` lines 306-310.
- Sim gate [code] `brain_sim_check.py:383-387` `--quack-at --quack-roll --quack-yaw --quack-pitch` runs the same gate
  and profile (lines 174-181), reports `quack_head_ran`, `quack_head_reached`, `quack_peak_tilt`, `fell_at`.

**Sim runs tonight** [sim] (`--model asbuilt --manifest microduck_rl/cmu/model/manifests/plugged.json --volt 7.0
--drop 0.04`, the base of `teleop_sim_batch.py:33`; about 4 s each):
- Nuzzle-sized move on stand61 (`--walk-s 0 --quack-at 4 7 --quack-roll 0.28 --quack-yaw 0.45 --quack-pitch -0.35`,
  seeds 0/1/2): ran to the end both times; reached head_pitch -0.23, head_yaw 0.39, head_roll 0.37-0.38 (roll overshoots
  the 0.28 command, yaw/pitch under-reach); peak tilt during the move 1.3-1.5°, max tilt 4.0°, max action 0.42, 0 action
  jumps, no fall.
- Flinch-sized move (`--quack-roll -0.3 --quack-yaw -0.6 --quack-pitch 0.4`, head down and away, seed 0): reached pitch
  0.54, yaw -0.57, roll -0.27; peak tilt 1.0°, max action 0.63, no fall.
- Seated nuzzle (`--sit-at 4 --quack-at 9`, seed 0): reached pitch -0.29, yaw 0.39, roll 0.23; seated tilt 1.2°, move
  peak tilt 1.5°, no fall (the sit itself peaks 10.6°).
Moves up to roll 0.3 / yaw 0.6 / pitch 0.4 with 0.5 s raised-cosine edges are inside what stand61 and the seat absorb
in the as-built sim. On the robot stand61 has held head yaw 0.6 / pitch 0.6 with "tilt unchanged" (D-015 amendment)
and the quack moves; the larger roll has not run on the robot.

**Reactions as command sequences** (control file `{"mode":"walk","vx":0,...,"head":{...}}` with the quack profile;
absolute targets = default + delta; "toward the hand" = the side whose pads rose):
- Stroke -> cat-like head rub on stand61: two bumps of 1.6 s, 0.3 s apart: head_roll +0.25 toward the hand, head_pitch
  -0.30 (nose up into the hand), head_yaw +0.30 toward the hand; second bump roll 0.20, yaw 0.15; optional quack on the
  second. Gate `quack_head_block == None`. Needs: a `--head-seq`-style reuse of the quack profile in `walk_wired.py`
  (sign and amplitude from the classifier); no policy change.
- Relaxed pat -> flinch: one fast bump, 0.8 s with 0.25 s edges: head_pitch +0.35 (duck down), head_yaw -0.4 away,
  head_roll -0.15. Sim passed at 0.4/0.6/0.3 with 0.5 s edges; the 0.25 s edge needs its own sim run (`QUACK_HEAD_RAMP_S`
  is a constant; a per-move ramp argument is the code change). A "shake" (yaw ±0.4 at 2 Hz) is outside the template:
  training resampled targets every 2-5 s through a 0.2 EMA, so a 2 Hz oscillation is outside the trained command
  statistics: new-policy item, or a sim flag first.
- Angry pat -> turn away or sit. [code] D-015 amendment: walk61 "does not step below vx 0.25, does not turn in place,
  does not walk backwards and stops stepping while a head command is active"; ROBOT.md:99-103 agrees. Possible today:
  (a) look away: head_yaw -0.8 away (inside ±1.40), held 2 s; (b) sit: `{"mode":"sit"}` (sitstand61, walk_brain.py:89-95,
  347-368; guard `--max-tilt-sit` 30; the seat peaks 10.6° in sim); (c) a body turn only as a forward arc
  `{"mode":"walk","vx":0.25,"vtheta":-0.8,"for_s":1.2}` (10-20 cm, part-turn; vtheta clipped ±0.8 at walk_brain.py:510;
  head at default while stepping; the walking-gap fall risk per SIM2REAL.md). Turn in place / backward step need a new
  policy: the env has `TURN_IN_PLACE_FRACTION = 0.15` (lines 25, 654) but the deployed walk61 does not turn on this
  robot (D-015). Recommendation: (a) + (b): look away, and sit if the angry pat repeats within 5 s.
- Carry grip (M+L1+R1 held) -> carry mode (Q5).
New policy needed for: the shake, the turn in place, any reaction while stepping. Everything else runs on stand61 /
sitstand61 as trained.

## Q5. Carry mode (spec only)

Reference [vendor]: aibo "lets all the body joints relax for safety and then takes the posture of lying down" when
lifted; after set-down "If aibo keeps lying down, wait for a while until aibo starts moving or say 'up'". Our rule set
differs on one point: "hold until told" forbids torque off and hold timers, so "relax" means a low gain, never off.

**Signals for "lifted".** [log] `robot-runs-20261019-a7z/duck_wired_log_1019d.jsonl.gz` (README: stand from side-lying,
"crept and fell forward after about 21 s in open-loop stand mode"; Shawn righted it twice), `scratchpad/an_lift.py`:
- Rows carry `acc`, `pos_tick`, `goal_tick` (keyed by joint name there). Righting at 96.0 s: gb (+0.97, 0.00, -0.25)
  (on its face) -> (-0.02, -0.03, -0.99) within 0.5 s; |acc| mean 9.25, max 11.28 m/s² in that bin against 9.6-10.3 at
  rest; second righting at 154 s: |acc| max 11.8; the falls at 105-106 s: |acc| max 12.0. A lift/set-down shows as a
  0.5-1 s gravity swing and |acc| excursions of 1.5-2.5 m/s² from g.
- Leg position error (|pos_tick - goal_tick| mean over the ten leg servos, KP 400 open-loop stand): 14-21 ticks in every
  state (standing 21, on its face 19-20, just righted 15). [inference] the KP 400 deadband/sag dominates (SIM2REAL.md:
  static sag 0.05-0.067 rad = 33-44 ticks under load; the leg probe held 1-21 ticks unloaded), so "leg error drops when
  the feet leave the floor" is NOT supported by the archived log and cannot be the trigger. The loaded/unloaded
  separation that exists is Present Current (0-23 mA unloaded hold, leg probe) once the 10-byte block is read (Q2); the
  loaded value is unmeasured.
- No archived log shows a lift while on stand61. The policy keeps running while lifted level (`walk_brain.py:473`
  `upright = grav_body[2] < -0.5`; only past 60° does the step stop and hold the last goal, lines 538-539), with no
  contact input in its 61-D observation: the legs keep "balancing" in the air = the struggling Shawn sees.

**Mode `carry`** (reuses `walk_brain.Brain` and `walk_wired.py` names and guards):
- Trigger (A7Z brain only): pads M, L1 and R1 all on (delta > the Q1 threshold) for `CARRY_GRIP_S = 0.4` s (20 ticks)
  while `brain.mode == "walk"` at zero command (the `quack_head_block` gate) or `stand`; AND lift evidence within
  `CARRY_LIFT_S = 2.0` s: |acc| outside 9.81 ± 1.2 m/s² for >= 2 consecutive ticks, or gb changing > 0.10 over 0.5 s, or
  (once read) summed leg Present Current below the unloaded band for 0.3 s. A grip without lift evidence inside 2 s is
  dropped (logged `carry_armed_timeout`); a lift without the grip (push, fall) never enters carry. A pat touches M or
  one of L1/R1 for < 0.3 s, so the 0.4 s three-pad hold filters it; a stroke crosses the pads in sequence.
- Entry: `{"mode":"carry"}` in the control file (written by the touch thread; also by hand for tests). `Brain.tick`:
  `carry` joins `TORQUE_MODES` (fresh-sample wait as for stand, lines 410-417); smoothstep ramp (lines 463-471) from the
  present goals to `CARRY_POSE` over 1.5 s, `CARRY_POSE` = STAND with hip_pitch +0.25, knee +0.35, ankle -0.10 (a mild
  tuck, feet 3-4 cm up; exact numbers from the sim), head at default; `KP_CARRY = 120` legs, 80 head (today
  `walk_wired.py:665-667` writes one kp to all 14 IDs; a per-joint kp dict is the small change). Torque stays on;
  `{"mode":"off"}` remains the only release (lines 453-471). Tilt guard and action limits do not apply (lines 634-662
  run for `POLICY_MODES` only); `IMU_LOST_S` holds goals as today (line 315).
- While carried: policy off, goals = tuck, head touches ignored.
- Release: M+L1+R1 all off for `CARRY_RELEASE_S = 0.5` s AND settle: gb z < -0.90, |acc| within 9.81 ± 0.5, |gyro_body|
  < 0.3 rad/s, all for 1.0 s. Then the existing sequence: `{"mode":"stand"}` (2.0 s ramp to STAND at KP 400, lines
  426-427, starting from the current goals, line 421) -> `{"mode":"walk","vx":0,"vy":0,"vtheta":0}` (stand61 at the
  first fresh upright sample, lines 453-455). Pads off but no settle (still swinging): stay in carry. Set down with the
  hand still on the head: the tuck holds at low gain (it squats) until the hand leaves.
- Risks: (1) a pat drops the legs: prevented by the three-pad 0.4 s grip AND lift evidence; test: 0.2 s M-only and
  0.2 s M+L1+R1 presses on stand61 change nothing. (2) release in the air: only a 2 s ramp to STAND in the hand (legs
  extend slowly), harmless; the 1 s settle rule makes it rare; test: pads off with gb z -0.6 stays in carry. (3) set down
  while tucked: squat on the tuck at KP 120, STAND ramp once the pads are off; the sim must show the ramp from
  `CARRY_POSE` to STAND stands up (flag to add: `--carry-at T --set-down-at T2`). (4) a saturated/stuck pad (0x3FFFFF
  freezes the scan): any block with a saturated count or a non-advancing seq is ignored for entry and exit; "touch
  stale" printed once. (5) the Mac brain (USB) has no pads: `carry` accepted by hand for bench tests, never triggered.
- Tests (style of `test_teleop_modes.py`: `World`, `run_wired` with `hooks`, assertions on `self.log_lines`, text,
  `last_log`), proposed `test_carry_modes.py`: `test_carry_enters_from_stand61_only_with_grip_and_lift`,
  `test_pat_never_enters_carry`, `test_grip_without_lift_times_out`, `test_carry_holds_through_imu_loss_and_tilt` (torque
  True in every row, no "torque off" line), `test_release_needs_pads_off_and_settle` (gb z -0.6 stays; upright + quiet
  1 s -> "mode -> stand" then "mode -> walk" with policy stand), `test_carry_never_releases_torque` (no Torque 0 write in
  `world.log`), `test_stale_touch_block_is_ignored`.

## What I ran tonight
- Read: AGENTS.md, PROJECT-CONTEXT.json, CURRENT-STATE.json, DECISIONS.md D-010..D-018, SIM2REAL.md, ROBOT.md, the touch
  firmware/readers/bench, touch_routes.json, A7Z-TOUCH.html (text), PLAN.md, walk_wired.py, walk_brain.py, duck_sense.py,
  dxl_fast.py, duck-telemetry.py, robot-live.js/html, a7z-bridge.mjs, duck-command.py, the env cfg, brain_sim_check.py,
  test_teleop_modes.py, the 10/18 and 10/19 run READMEs, the XL330 e-Manual, the aibo help pages, the CoST abstract, the
  two ICMI 2015 PDFs.
- Computed: `an_1018d.py` (burst window of 1018d), `an_lift.py` (1019c/d/e righting events).
- Sims (as-built, real condition, 4 s each): nuzzle seeds 0/1/2, flinch, seated nuzzle.
- Drafts: `touch-gesture/record_touch.py`, `features.py` (toy stroke gives order +1, spread 0.6 s, simultaneity 0),
  `train_touch.py`; all compile.

## Unverified items and the closing check
1. Fingertip delta >= 5x noise per pad in the closed head: per-pad 10 s rest / 5 s touch on the A7Z; the only bench
   record (10/20) FAILED on L1 (delta -8, noise 122).
2. Touch-to-brain latency and the scan time: serial `ms` vs host clock over 60 s.
3. Present Current cost: a log row's `read_ms` after the 126 x 10-byte sync read; expect +0.3 / +0.6 ms.
4. Loaded vs unloaded leg current (standing on stand61 vs lifted), same read; needed for the carry evidence, since leg
   position error does not separate them (1019d).
5. A touch on stand61 with pads + acc in one log: the labelled session of Q3 (pads first, gyro/head-error within 2 ticks).
6. Reaction amplitudes on the robot: roll 0.28 and the 0.25 s flinch edge are sim-only; first robot run with Shawn
   guarding, stand61, one bump at a time, logged.
7. Carry: `CARRY_POSE` stand-up from the tuck, sim flag `--carry-at/--set-down-at` first, then the robot.
8. Paro's stroke-vs-hit distinction: secondary sources only; not needed for the design.
