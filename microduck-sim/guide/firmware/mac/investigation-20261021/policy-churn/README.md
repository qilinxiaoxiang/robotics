# Why the duck could not stand on 2026-10-21: free play below the ankle encoders, reproduced in the sim

Problem: final-goal steps 2 and 3 (walk to the item, crouch and keep balance, `microduck-sim/PROJECT-CONTEXT.json`
`final_goal`) need a stable stand. On 2026-10-21 every stand61 run tipped within 4-12 s and the open-loop KP-400 stands fell
within 2-18 s; on 2026-10-19 the same policies and gains held for 42-111 s. Current values (rail, read drops, gains) come
from `microduck-sim/CURRENT-STATE.json`; the logs are `../../robot-runs-20261019-a7z/` and `../../robot-runs-20261021-a7z/`.

## What the robot logs show

- **KP 400 holds the joints.** Open-loop stand, goal minus position: 0.01-0.03 rad on every leg joint on 10/19 and on
  10/21 (`err_model` numbers below). The joints are not soft; the body moves on top of them.
- **stand61 oscillates at 3.5-4.5 Hz on 10/21 and not on 10/19.** `churn_stats.py`: on 10/21 every stand61 run has its
  action and trunk-gyro peak at 3.5-4.5 Hz, leg-action rms 180-620 mrad, trunk yaw rate 1.2-3.1 rad/s rms, largest
  actions on both hip pitches and the neck; each run ends in a tip. On 10/19 (cool board) the runs are quiet
  (1.4-42 mrad, yaw rate 5-89 mrad/s); the hot 10/19-20 run 1019m (loop 20.5 ms, joint age 20.8 ms, more latency than
  10/21) is quiet too (45 mrad). The as-built sim at the real condition is quiet (2 mrad, peak 0.6-0.9 Hz).
- **Not sensor noise.** `churn_replay.py` rebuilds stand61's observation from each logged tick and reproduces the logged
  actions to 0.003 rad; smoothing any one observation block (gyro, gravity, joint position, joint velocity) leaves
  92-101 % of the fast action. The oscillation is the whole loop, policy plus body.
- **The body rocks with every leg encoder frozen.** `stand_check.py`, open-loop stand, 1 s windows in which all ten leg
  encoders stay within 3 ticks and the trunk leans less than 8 deg (past that the foot rocks on its toe on both days):
  trunk pitch range median 0.00, p90 0.06 deg over 421 windows on 10/19; median 1.0, p90 2.2, up to 3.3 deg over 20
  windows on 10/21. Roll in the same windows: p90 0.06 deg on 10/19, median 0.2 and p90 0.8 deg on 10/21, so the motion
  is mostly about the ankle (pitch) axis, which a uniformly soft sole would not single out. Something between the servo
  outputs and the floor turns about the ankle axis without any encoder seeing it.
- **What changed between the two days at the ankle.** Both days ran the V1.22 slip-fit feet with the toe M2 x 6
  (`../../robot-runs-20261019-a7z/README.md`: "Feet: V1.22 slip-fit feet"). The 10/19 runs used the stock one-piece
  orange ankle brackets. On the robot now (Shawn, 2026-10-21) is the V1.24/V1.25 two-half ankle: the stock bracket cut at
  mid shaft, the outer half on the servo horn, the inner half on the V1.22 sleeve, and the two halves held together only
  by the slip-fit foot (0.15-0.19 mm free travel by design) and the countersunk head of the toe screw (5.5 mm2 on each
  half) (`guide/print/ankle-halves-20261020/README.md`). The cut bracket is the only ankle change between a quiet stand
  and the failing one. Whether anti-slip soles were on during the 10/21 runs is not recorded.

## Sim reproduction (`brain_sim_check.py`, as-built model, CURRENT-STATE rail and read drops, seed 0)

New options: `--foot-play DEG [STIFF DAMP]` puts each foot's collision on a hinge about the ankle axis with +-DEG of free
play, a weak centring spring and damping (`evaluate_delay.load`, config `foot_play`), so the ankle encoder does not see
the rotation; `--foot-play-axis roll|yaw` uses a forward or vertical axis instead; `--sole-solref TC DR` softens the
foot-floor contact; `--tick-log` rows now carry `goal_tick`, `pos_tick` and `kp` like the robot log.

- stand61 15 s, no play: quiet, no fall. Extra loop delay of one or two ticks (`--sensor-delay 2 --action-delay 2`):
  falls forward in 0.9 s, so stand61 has little phase margin; the robot's measured ages (joint 12-15 ms, IMU 19-20 ms)
  are below the sim's default 24 ms, so latency alone is not the 10/21 difference.
- Soft contact (`--sole-solref` 0.03-0.08 s, damping 0.3-1): quiet. Servo friction x1.5: quiet. Play +-3/5/6/7 deg:
  quiet. Roll or yaw play +-3-8 deg: quiet.
- **Play +-8 deg about the ankle axis: stand61 oscillates at 3.1-3.6 Hz (actions 206-245 mrad, gyro 520-630 mrad/s,
  yaw axis largest, hip pitches and neck the largest actions) and falls forward at 14.1-14.4 s (seeds 0 and 1).** Same
  frequency band, same axis and same joints as the robot.
- **Play +-8 deg plus BAM friction x3 (the earlier proxy for the robot's weak small-step response): the sit stalls (the
  Brain declares "seated" with the trunk still at 0.115 m, as on the robot) and stand61 falls forward at 12.2 s.** Play
  alone still sits; friction x3 alone stands quietly. One model with both reproduces both 10/21 failures.
- Walk 0.25 m/s with +-8 deg play: no fall in 4 s, but 32 action jumps against 1 and peak tilt 10.6 against 6.3 deg.

The +-8 deg and x3 are fitted proxies, not measurements: the threshold for the oscillation in this model lies between
+-7 and +-8 deg about the ankle axis.

## What to do, and the check

1. Robot off: on each leg hold the lower leg (shin and ankle servo) in one hand and the yellow foot in the other and
   rock the foot gently toe up and toe down. With torque off the ankle turns through the gearbox with even resistance;
   free travel or a click before that resistance is the play. Watch three seams: the cut between the two orange halves,
   the orange block inside the yellow foot (heel end and toe end), and the outer orange half on the servo horn.
   - Outer half moving on the horn: tighten the four M2 x 4 output screws.
   - Halves moving against each other or in the foot: the two-half ankle has nothing else holding it. The repair with
     evidence behind it is the stock one-piece bracket (10/19: quiet stand, quiet stand61) with the V1.22 sleeve,
     slip-fit foot and toe M2 x 6. Keeping the halves needs a new joint between them, which is a print change: its
     connection method goes to Shawn as a picture before any CAD.
   - Tighten the toe M2 x 6 in either case.
2. Next powered session, same procedure as 10/21 (open-loop stand at least 30 s, then stand61 at zero command at least
   10 s), then on the Mac: `python3 investigation-20261021/policy-churn/stand_check.py <copied tick log>`. PASS on both
   lines means the stand is back to the 10/19 state (it passes 1019f and fails app1021-040436).
3. Only then try the sit again; if it still stalls with the play gone, what is left is the servo response (friction proxy).

## Files

`churn_replay.py` (offline replay and block smoothing), `churn_stats.py` (per-run frequency and rms), `stand_check.py`
(acceptance). Sim cases were run serially with `timeout 600`; their tick logs stay in the session scratchpad.
