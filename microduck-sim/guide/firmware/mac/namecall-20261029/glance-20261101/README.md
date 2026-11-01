# Head-only answers on the as-built sim: standing at the 1.40 cap, seated with a tilt (2026-11-01)

Simulation only (Mac mini, `~/sims/glance-20261101/rt`). Nothing ran on the robot; the A7Z has been offline since
2026-10-31 20:45. Requirements R11 and R12 in `../REQUIREMENTS.json`, decision D-038.

**Result.** Standing, the 1.40 rad glance never tips the duck: trunk tilt changes at most 1.6 deg and the trunk drifts at
most 0.3 cm, in 18 of 18 runs. The head yaw joint reaches 1.23-1.31 rad (70-75 deg). At the old 1.2 cap it reached
1.08-1.18. With the camera's 62 deg field of view, the standing glance sees about +-104 deg. Seated, the answer never
knocks the duck over and the knees stay folded in every run. Trunk tilt changes at most 5.1 deg. The head reaches 1.10
rad to the left and only 0.83-0.89 to the right, so seated the camera sees about +94 / -80 deg. The tilt reaches
0.19-0.23 rad (11-13 deg). The sitstand policy takes only about -0.75 of the -1.1 head pitch asked.

**The sit-down holds at the robot's read-drop rate (checked 2026-11-01).** The answer runs above used 17 % dropped
reads. That is the 2026-10-31 touch-bus fault value in CURRENT-STATE `servo_read_drop_fraction`, which the console
loglevel fix of that day brought to 3 in 1500 standing ticks. At 17 % some sim sit-downs tip backward to about 63 deg
before any call. The robot's own sit-downs never ran at that rate:
- **Robot.** `real_sits.py` reads every sit-down in the backed-up A7Z brain logs (`~/Backups/a7z-duck-logs`,
  2026-10-21 to 10-30; output `real_sits.txt`). 22 sit-downs folded the knees to about 1.3 rad and none tipped. Reads
  dropped on 0-4.2 % of the sit-down ticks (median 1.5 %). Peak trunk tilt was 4.4-11.8 deg (median 6.0).
- **Sim at the robot's rates.** `glance_sim.py --sit-entry` ran 8 seeds at 7.2 and 8.0 V on the 2026-11-01 model and
  on the bench-supply `plugged` model (`sitentry_1101.json`, `sitentry_plugged.json`). At 0, 1.5 and 4 % drops, 0 of 96
  sit-downs tipped. Peak tilt was 6.0-8.0 deg, against the robot's median of 6.0.
- **Sim at 17 %.** 3 of 16 sit-downs tipped on the 2026-11-01 model and 2 of 16 on `plugged`.

So the sim agrees with the robot. The earlier tip finding came from the fault-state drop rate, not from the seat or
the mass model. A sit-down during a read-drop fault like the 10/31 one is untested on the robot and tips in the sim.
(The `battery` plan model also tipped 9 of 32 at 4 %. It is not the robot: it lacks the D-037 battery move and the
head sensors.)

## Setup

- **Plant.** `glance_sim.py` uses the plant of `pet/express/duck_sim.py` (getup_sim: the as-built config, BAM servos,
  one tick of sensor and one tick of action delay, dropped reads) with `walk_brain.Brain` in-process.
- **Head path.** The robot's own `namecall.HeadPath` runs with the caller at +90, -90 and +150 deg standing, and +90,
  -90 and +30 deg seated. Each run holds the gaze 6 s, then the head drifts home over 4 s.
- **Conditions.** 7.0 and 7.8 V bracket the stale CURRENT-STATE `servo_rail_v` (7.0 V on the bench supply; the
  robot now runs on the 2S battery). Reads drop 17 % of the time, with 3 seeds per case.
- **Mass model.** `manifest-asbuilt-20261101.json` is built by `glance_sim.py --build-manifest` from
  `variant-asbuilt-20261101.json`, on top of microduck_rl `cmu/model/variants/battery.json`. It adds:
  - the D-037 battery 1.8 mm further back, with its cradle and bars (+3.3 g);
  - plug 1 and the balance plug on top of the box;
  - three INMP441 boards (2 g each, KitsGuru listing), their foam and glue;
  - the XIAO touch board (3 g, OpenELAB wiki) and pads;
  - the microphone and touch wires down the neck.

  Total +20.3 g against the 10/15 plan. All of these masses are estimates until weighed. The D-036 Dual Lock plate
  is not fitted yet (2026-11-02), so the backpacks keep their screwed positions.
- **Results.** `results.json` holds one row per run; a row with `tipped_before_call` is a sit-down that tipped,
  not an answer.

## What the code does (namecall.py)

- **YAW_CAP 1.40.**
- **No body share.** `HeadPath` sets the expressor's `orient_threshold` to infinity. Past the card's 1.2 threshold,
  the library hands part of the gaze to ORIENT, whose head_yaw gain is -1, so a 1.40 look would leave the head at
  0.60. `test_full_glance_reaches_the_trained_yaw_without_a_body_share` fails at 0.603 with the old threshold.
- **Seated answers.**
  - `BrainGate` accepts a brain in sit mode whose tick log says `sit_phase` "seated" and waits while it sits down or
    stands up.
  - `CmdWriter` takes over a `{"mode": "sit"}` file and writes `{"mode": "sit", "head": ...}`, never a walk, so it
    never stands the duck up.
  - `HeadPath` adds `SIT_TILT` 0.25 rad of head roll toward the caller's side and limits the seated head to
    `SIT_HEAD_RATE` 1.0 rad/s, with no pre-inverse snap. 2.0 rad/s gave the same tilt numbers; 1.0 stays because
    Pollen saw fast head jerks tip a seated duck backward.
  - No body turn is planned from a seat.

## Commands

```bash
~/.venvs/microduck-dyn/bin/python glance_sim.py --build-manifest
~/.venvs/microduck-dyn/bin/python glance_sim.py --out results.json
~/.venvs/microduck-dyn/bin/python glance_sim.py --sit-entry 0,0.015,0.04,0.17 --volts 7.2,8.0 --seeds 8 --out sitentry_1101.json
python3 real_sits.py duck_wired_log_app1030-180856.jsonl ...   # the 14 logs listed in real_sits.txt
```
