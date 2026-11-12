# Where the robot moves without its encoders seeing it (2026-11-12)

Question: is there play (a loose screw, horn or bracket) worth hunting for, and where? Answered from the logs that
exist, without taking the robot apart. Robot logs: Mac mini `~/duck-walks/raw/duck_wired_log_app1102..app1111`
(11-11 is after the cable tidy). Sim: the scorecard's replays of the 11-02..11-06 walks (`~/duck-walks/scorecard-auto`),
which have no play. Current fact: `leg_play` in `microduck-sim/CURRENT-STATE.json`.

## Result

- **No static play.** In 0.5 s windows with all ten leg encoders still (within 3 ticks), the trunk moves at most
  0.06 deg (p90 pitch and roll, 35742 windows in every log since 11-02, `frozen_swing.py`). That is the rigid level of
  the 10/19 one-piece ankle; the loose two-half ankle of 10/21 gave 2.2 deg with the same test. In quiet stance there is
  nothing loose to find.
- **While walking, the left leg's pitch axis gives way.** With one foot carrying the robot, the trunk tilt the IMU
  measures is compared with the tilt the stance leg's encoders give with that foot flat (`tilt_gap.py`). Binned over
  the stance (`stance_profile.py`), the pitch gap on the left foot sweeps from +3.2 to -6.9 deg (about 10 deg) with a
  spread of 4-10 deg inside each bin; on the right foot it sweeps about 3 deg (-1.5 to +1.4), and the sim about 3 deg
  with a spread of 1.3-2.1. Roll is like the sim's on both feet. The 11-02..06 logs give the same numbers (left +2.3 to
  -6.3), so the cable tidy did not change it.
- **Which pitch joint.** Hip pitch, knee and ankle turn about parallel axes, so the trunk alone cannot separate them.
  The gap's tick-to-tick change at load reversals of each joint, against the sim's (`tilt_gap.py` joints), is raised
  most for the left ankle (0.88-0.91 robot, 0.64 sim) and both hip yaws (1.06-1.21 robot, 0.66-0.84 sim); the knees and
  hip pitches match the sim. Weak evidence, but it points at the left ankle-to-foot chain (ankle horn, two-half
  bracket, V1.22 slip-fit foot, sole) before the knee or the hip.
- **A few degrees of play does not explain it.** Servo-to-link play of 2 and 4 deg (total) on every leg joint in the
  sim (`brain_sim_check.py --joint-play`, a passive hinge after each servo as in Pollen's `add_backlash.py`) raises
  the sim's pitch gap only from about 3 to 4 deg on the same walk.

The large spread inside each stance bin says the give is not a fixed sole shape (that would repeat stride to stride);
it is something that yields differently each step under the full-body load on the left foot.

## Which modelled effect closes the gap (`gap_sweep.py`, 2026-11-12)

The scorecard's gap: the robot fell in 36 replayed actions (walk, turn, zero-command balance) of 11-02..11-11 where
the sim stayed up, and its trunk jitter (scorecard definition) is about 3 times the sim's. Each effect below was added
alone to the as-built sim and the same robot commands replayed (36 robot-fell and 24 robot-up actions, 3 seeds),
scored with the scorecard's own rules (fall over 45 deg inside the robot's window, falls within 1 s of a replayed
stand counted as the switch's). `gap-sweep.json`, `gap-sweep-com.json`.

- base: sim falls in 1 of 93 robot-fell runs, 0 of 72 robot-up; jitter 0.19 against the robot's 0.59.
- play, each alone, reproduces 10-16 % of the robot's falls and fells no robot-up run: head/neck play 8 deg 15/93,
  leg play 4 deg 14/93, soft sole 13/93, foot play +-3 deg 11/93, all joints 4 deg 10/93. Jitter stays 0.16-0.22.
- more servo friction (deadband) is not the cause: x1.5 gives 5/93 and 3/72 false falls; x2.0 raises jitter to 0.38
  but fells 49 of 72 runs the robot walked through.
- COM 5 mm forward: 4/30, no false falls. 3 mm back or more: the sim falls backward in its opening open-loop stand,
  before the replay starts, so the backward shift is untested; 10 mm either way fells every run.
- dropped reads at 10 %: 6/93. Everything combined (friction x1.5, 4 deg play everywhere, foot play): 16/93 with
  10/72 false falls, jitter 0.23.

No modelled effect brings the jitter near the robot's, and the play effects together explain about a sixth of the
robot's extra falls. The rest is unmodelled. Shawn found loose screws on 2026-11-12 and walking felt steadier after
he tightened them, so structural looseness beyond a few degrees at one joint is the first candidate.

Training with that play does not help (2026-11-12): play-a (play randomised per episode, head 8, ankles 6, other leg
joints 4 deg total) and its no-play twin playctl-a both cut the falls in the five play sims from walk61's 63 to 44
and 43 of 465 (`gap-sweep-play-a.json`, `gap-sweep-playctl-a.json`), so the gain is the shared fine-tune, and both
fail the jitter gate. Detail in the team repo's `cmu/finetune/modal/FINETUNE-DELTA.md`.

Supply voltage is not it either: over 442 robot actions with a logged voltage the fall rate is 9 % at 7.2-7.5 V and
5 % above 8.1 V; walking trains on 6.5-8.2 V with load sag (`microduck_constants.py` vin_range since 2026-06-29).

## Second pass, 2026-11-12: existing logs only, no robot test

Windows rebuilt from the brain logs (Mac mini `~/sims/fall-onset-20261112/`): 153 forward walks 11-02..11-12, 17 fell.
Of the scorecard's 36 "robot fell, sim up" actions about 10 are the robot being handled (zero command, gyro under
0.5 rad/s), and its balance replays start from a clean sim stand, so a fall that begins after a walk stops cannot
reproduce there.

Established:

- IMU roll was never trimmed. At quiet stand the robot reads +2 to +3 deg of roll in every log (sim 0), the left foot
  is 3 to 5 deg off flat by its encoders and the right under 1.5 (`foot_flat_check.py`). A sim sensor rolled by
  `--imu-roll -3` (with `--imu-pitch 2`) reads +2.5 deg at stand, +2.0 deg mean while walking, swings left 0.18 s /
  right 0.26 s and lifts left 10.7 mm / right 17.6 mm; the robot reads +2 to +5 deg walking, 0.17 / 0.28 s and
  12.5 / 19.7 mm. The left-knee load (robot L/R mean error -204 / +80 ticks) follows too. A lateral COM shift of 6 mm
  gives the same gait but no part on the robot is heavy enough for it. With `walk_brain.IMU_ROLL_TRIM_DEG = -3`
  (env `MICRODUCK_IMU_ROLL_TRIM`, default 0, not on the robot) the sim reads 0.00 deg and swings 0.24 / 0.24 s.
  Unexplained: the one session with a symmetric gait and no fall (11-02 12:13, 18 walks) has the same stand reading.
- No sim run passes the sensor pitch that the brain's 4 deg pitch trim undoes: the sim policy sees +3.9 deg at stand,
  the robot +1 to +2.6. `--imu-pitch 2` matches the robot.
- Two falls follow a control-loop stall: 11-11 22:55:06 (251 ms, 0.44 s before onset) and 11-12 00:26:58 (176 ms,
  0.14 s). Four gaps over 100 ms in 658 s of walking; the other 15 falls have no gap over 45 ms in their last 2 s.
- Falls by time upright before the walk: 5 of 22 within 10 s of being stood up, 3 of 58 after 80 s. By the largest
  turn command the policy saw: 0 of 25 under 0.5, 6 of 24 at 1.9 or more (walk61 trained on 1.0; the sim's own
  heading hold never exceeds 0.5). By supply: 8 of 37 at 7.85 V or more, 9 of 98 below.
- Ruled out: a servo gain change on ID2 after its 11-02 factory reset, a hidden static angle in either leg, a gyro
  bias after start, foot scuffing (robot clearance 12.5 / 19.7 mm).

- The 2 deg left hip roll zero offset tried from the 11-11 23:38 log (`pi/joint_signs.py`) does not help: robot gait
  unchanged (45 walks with it, swing 0.17 / 0.27 s), sim gait worse with it (0.14 / 0.28 s against 0.18 / 0.26) and
  0.22 / 0.26 s with the IMU roll trimmed (0.24 / 0.24 without the offset). Removed from the file 2026-11-12; the A7Z
  copy keeps it until the next deploy (robot offline at the time).

Not reproduced: fed the robot's own turn signal (`--turn-replay`), 17 fell + 30 up walks, seed 0, the sim falls 0 of
17 with every gap alone and together: floor mu 0.25, COM +-6..18 mm, friction x1.5, joint play 2 deg, 8.1 V, IMU
pitch 2 and roll -3. All together its yaw-rate rms is 1.00 rad/s (robot 0.95), so the wobble is matched and the falls
are not. Training on these gaps therefore has no evidence behind it.

Scripts: `compact_logs.py`, `fall_onset.py`, `turn_cmd_stats.py`, `turn_replay_sweep.py`, `fall_trace.py`,
`swing_clearance.py`, `stance_asym.py`, `foot_flat_check.py`; sim flags `--turn-replay`, `--com-y`, `--imu-roll`.

## Files

- `frozen_swing.py`: static check (stand_check.py check 1, any torque-on mode).
- `tilt_gap.py`: IMU tilt minus stance-leg kinematic tilt; per-foot spread, tick-to-tick change, per-joint load
  reversals. `play_locate.py`: model loading and log reading (its gyro-rate comparison is not used: rates
  differentiated from quantised, dropped encoder reads were noisier than the signal).
- `stance_profile.py`: the gap binned over the stance phase.
- `run_all.sh`, `run_profile.sh`: the Mac mini runs; outputs `robot-*.json`, `sim-*.json`, `prof-*.json`.
- `smoke.sh`: one walk replayed with 0, 2 and 4 deg of `--joint-play`.

Log fields: `q` is in servo-ID order (`walk_brain.NAMES`), not `OBSERVATION_DOF_ORDER`; `goal_tick` is a dict keyed
by servo ID; `pos_tick` a list in servo-ID order.
- `gap_sweep.py`: the effect-by-effect replay sweep above (Mac mini, about 40 min for 1980 sims at 9 jobs);
  `run_candidates.sh TAG...` runs it for fine-tune candidates in `models-<TAG>/`.
- `drive_bouts.py`: short test walks driven from the Mac through the app's command writer and its driver lease.
- `wiggle_live.py`: live per-joint encoder readout while a part is pushed by hand (read-only).
- `free_minimac_disk.py`: deletes files over 5 MB in old `~/sims` studies on the Mac mini.
