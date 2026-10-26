# pet/body: body card, self-inspection, health

The pet's mind never touches servos. It reads `pet/state/body_card.json` (schema in `pet/state/README.md`): which
sensors the body has, which actuators (model, stall torque, range, `ok`), and which primitives it can run with their
parameter ranges and preconditions. This package writes that card and keeps it true while the robot runs.

- `inspect.py`: boot-time self-inspection. Bus scan, sensor enumeration, motor babbling, primitive discovery, card.
- `health.py`: runtime check. Marks an actuator `ok: false` on a hardware error or a run of unanswered reads, drops
  the primitives that need it, rewrites the card and appends an event to `pet/state/body_events.jsonl`.
- `primitives.py`: the rules table from actuator and sensor sets to the policy library. Duck: walk, stand, sit,
  groundpick, getup, wait, stop, look_around, turn_head, nod, shake_head, beak. OMX-F arm: turn_camera, wave, point, nod,
  look_around, rest_pose, wait, stop, grasp. An unknown body gets only `move_<joint>`. Names follow the mind's examples
  (`pet/state/examples/skills.json`). A failed head joint keeps walking only where the failure study says walk61 still
  walks; where each primitive comes from goes to the card's notes, not its preconditions.
- `profiles.py`: how a scan is recognised (ids and model numbers) and where each body's ranges come from (the duck:
  `walk_brain.JOINT_RANGE` and `pi/jaw_limits.json`; the arm: `omx-local/CURRENT-STATE.json`). Nothing is copied.
- `failure_study/`: walk61 with one head or ankle joint frozen or weak in the as-built sim; `NOTE.md` has the result
  and the proposed training randomisation.
- `fixtures/`: recorded data for the dry run, rebuilt by `python3 -m pet.body.fixtures.make_fixtures`.

## Run without hardware (from the repository root)

```bash
python3 -m pet.body.inspect --dry-run --body duck
```

```bash
python3 -m pet.body.inspect --sim
```

```bash
python3 -m pet.body.inspect --dry-run --body arm --out pet/state/body_card.json
```

```bash
python3 -m pet.body.health --log pet/body/fixtures/duck_health_replay.jsonl --out /tmp/card_replay.json --events /tmp/body_events_replay.jsonl
```

```bash
~/.venvs/microduck-dyn/bin/python -m pytest pet/body/tests -q
```

`--dry-run` uses a recorded bus scan and the real single-joint IMU windows in the duck's tick logs (only four joints
have a window the brain commanded; the others are listed as missing). `--sim` re-executes itself under
`~/.venvs/microduck-dyn` and babbles all 14 policy joints in the as-built MuJoCo duck with the head camera rendered.

## On a live robot (not run yet; needs Shawn at the robot)

Self-inspection owns the servo bus, so the brain must not be running (`walk_wired.py` holds the port). Babbling moves
every joint 0.02, then 0.04, then 0.08 rad at P 200 while the robot stands; it grows only while the trunk tilts less
than 3 deg and returns home past 6 deg. In the as-built sim, 0.05 rad on one hip pitch, ankle or the neck already tips
the standing duck over, which is why the steps start at 0.02 rad. Someone must hold a hand near the robot.

MicroDuck, on the A7Z (servos on J12 UART2 at 500 kbaud, `microduck-sim/CURRENT-STATE.json` servo_bus_hosts; IMU on
i2c-7, touch board on i2c-0). Put the duck in stand mode first so torque is on, stop the brain, then:

```bash
cd ~/rt && python3 -m pet.body.inspect --port /dev/ttyAS2 --baud 500000 --i2c 0 7
```

```bash
cd ~/rt && python3 -m pet.body.inspect --port /dev/ttyAS2 --baud 500000 --i2c 0 7 --babble --i-am-watching
```

The first command only reads (scan, sensors). `~/rt` stands for wherever this repository is deployed on the A7Z; the
babbling run needs `adafruit-circuitpython-bno08x`, `adafruit-extended-bus` (already used by `imu_read.py`) and
OpenCV for the camera term. The jaw (ID15, current-based mode 5) is skipped by babbling.

While the brain runs, health follows its tick log instead of the bus (walk_wired.py already logs `missing` and
`hw_faults` per tick); start it next to the run that writes `/tmp/duck_wired_log_<suffix>.jsonl`:

```bash
python3 -m pet.body.health --log /tmp/duck_wired_log_<suffix>.jsonl --follow
```

OMX-F arm, from the Mac (follower on `/dev/cu.usbmodem1101` in the 2026-10-05 scan; check the port first). The scan is
read-only. The arm has no IMU, so babbling does not apply; health polls the bus directly while nothing else uses it:

```bash
python3 -m pet.body.inspect --port /dev/cu.usbmodem1101 --baud 1000000 --body arm
```

```bash
python3 -m pet.body.health --bus /dev/cu.usbmodem1101 --baud 1000000 --every 5
```

## What is real and what is not

- Real: the arm's bus scan (read-only, 2026-10-05), the duck's answering servos and bus voltage (tick log 2026-10-23),
  the four duck babbling windows (real IMU), the left-ankle hardware fault the health replay finds (run 1019c).
- Not recorded: the duck's servo model numbers (taken from the servo order in `PROJECT-CONTEXT.json`) and any EEPROM
  position limit; the duck card's ranges are the policy's trained ranges.
- Sim only: the 14-joint babbling with camera change, the failure study.
- Never run: every live command above.
