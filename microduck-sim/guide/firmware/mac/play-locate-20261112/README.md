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
