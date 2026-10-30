# The live runner: pet/mind on the duck's brain

`pet/mind/runner.py` lets the intention layer drive the robot through the brain's control file. It never touches a
servo: it writes the same JSON commands the phone app writes (`{"mode": "walk", ...}`, `{"mode": "sit"}`, head poses,
ground-pick phases), reads the brain's tick log and stdout back, and stops at once when the brain reports a fall, a
guard trip or a refusal. Proven against the simulated duck on 2026-10-29 (`out/runner-20261029/day-30min/`, numbers in
`docs/PET_ROBOT_LOG.md`); not yet run on the robot.

## Off the robot

```sh
cd ~/code/robotics
pet/.venv/bin/python -m pytest pet/mind/tests -q                      # 60 tests, no model, no sim
pet/.venv/bin/python -m pet.mind.runner --dry --minutes 3             # scratch control file + fake brain; claude -p if present
pet/.venv/bin/python -m pet.mind.runner --sim --minutes 30 --allow head,walk   # MuJoCo duck behind walk_brain.py (one sim at a time here)
pet/.venv/bin/python -m pet.mind.runner --sim --minutes 10 --backend fallback --seed 2 --udp 9882 --tag s2 --allow head,walk   # a batch member
```

`--allow head,walk` leaves `sit` and `rest` out of a simulated day on purpose: the brain's stand-up from the seat
is not reliable in the as-built simulation (below, "Sit and stand"), and that is the brain's hand-over, not the
runner's timing. A day with `--allow all` records those falls as `FELL` and stops at the first one.

`--sim` starts `guide/firmware/mac/fake_pi.py` (the as-built mass model at CURRENT-STATE `servo_rail_v`) and
`walk_brain.py` against it, exactly the brain-in-sim path, with its own control file under the output directory.
`sim_host_guard` refuses a second sim on the MacBook, and on 2026-10-29 Shawn asked for every long sim to run on the
Mac mini, so the days and batches run there (`ssh mac-mini`, snapshot `~/sims/pet-runner-20261029/` with hard links
into `~/code/robotics`, interpreter `~/.venvs/microduck-dyn/bin/python`, which also runs the runner). The Mac mini has
no `claude` CLI and a non-interactive ssh shell on the MacBook cannot read its Keychain, so the snapshot's
`bin/claude` is a shim that hands each call to `pet/mind/claude_bridge.py serve`, a spool loop started from a
GUI-session shell on the MacBook (`nice -n 19 pet/.venv/bin/python pet/mind/claude_bridge.py serve`); the runner's
`claude-cli` backend sees an ordinary `claude` on its PATH. A 50 Hz brain in `fake_pi.py` is sensitive to host
stalls: a 0.38 s pause on the Mac mini (a 1 GB copy) toppled two walking ducks of a batch at once, and a 1.0 s pause
on the MacBook at load average 94 toppled a standing one (`out/runner-20261029/falls/*host-stall*`); keep the host
quiet during a day. Each run writes
`out/runner-<date>[-tag]/`: `behaviour.log` (the session as a reader follows it), `intentions.jsonl`, `commands.jsonl`
(every control-file write with its primitive), `events.jsonl` (readback and perception events), `calls.jsonl`,
`summary.json` (intentions, primitives issued, validator rejections, brain refusals, falls, guard trips, yields,
rigidity numbers next to the 2026-10-26 reference), plus the brain's own `brain_log.jsonl` / `brain.out`.

## On the robot

The runner must run where the `claude` CLI is logged in (the intention model is `claude -p` on the subscription). On
2026-10-29 that is the MacBook; the Mac mini has no `claude` on its PATH (checked over ssh), so there use
`--backend fallback` (drives only, no language) or install and log in the CLI first. Both Macs reach the A7Z as
`ssh a7z` over Tailscale (CURRENT-STATE `a7z_network`); the runner needs nothing installed on the A7Z (it sends
`a7z_agent.py` over the ssh session, like the app's `duck-command.py`).

Before the first command:

1. Robot on its feet on the floor, charger or pack connected, you within reach.
2. Phone app (robot-live on the Mac mini :5180): start the brain if it is not running and put it in **walk mode at
   zero command** (the stand button). Leave the app open; it is your stop.
3. In a terminal on the Mac that has `claude`:

```sh
cd ~/code/robotics
pet/.venv/bin/python -m pet.mind.runner --robot --allow head --minutes 10
```

`--cam-hz 1 --save-frames` also saves each head-camera frame (while the camera daemon runs) with the brain row
nearest its capture time (joint angles `q`, `head_cmd`, IMU `quat`, `gb`) to `<out>/frames/` (`frames.jsonl` plus
`img/`); the agent forwards those three row fields for this. Checked read-only on the robot 2026-10-30: 19 frames in
20 s, every one matched to a row within 0.07 s.

Add `--inbox pet/state/inbox --state-dir pet/state` when the voice loop (`pet.voice.voice --robot`) runs beside it
("What the owner says" below). The runner refuses to start unless the control file already holds a zero-command walk and the brain's rows show walk
mode with the body upright. Then it prints the behaviour log live (`INTENT ...`, `step ...`, `body: seated`, ...).

### On the charging cable (`--tether METRES`)

Shawn 2026-10-30: the cable leaves the backpack at the lower left rear and trails behind; the duck must not trip on it
and must not walk so far that it runs out. `--tether 0.8` (how far the cable reaches from where the session starts)
turns on `tether.py`: pose from the IMU quaternion and the walk the brain executes (0.15 m/s at vx 0.25), and three
rules applied in `write()` and every tick, before the mind's commands reach the brain:

- A walk that would end past `limit - 0.15 m` while moving away is not written; the mind is told why and how much
  room is left straight ahead. A turn on the spot that could take the net heading past +-200 deg is refused the same
  way (the cable would wind round the legs).
- A turn on the spot that moves under 10 deg in 4 s is stopped and reported ("my turn to the left got stuck"): on
  2026-10-30 the duck turned into a wall.
- Out past 60 % of the limit for the first time, or past the limit while walking: the runner takes the body, turns on
  the spot toward the start (the way round that keeps the net turn small), looks at the floor with the head down, asks
  the vision model whether the cable is slack or taut (needs `--cam-hz`), and walks back when it is taut or the limit
  was passed. A taut look also lowers the limit to where it happened.

The mind's prompt carries the cable situation (`tether.SITUATION`) and the live distance, bearing to the start and
net turn. Robot session: duck on open floor at the start point, cable slack behind it, app open as the stop:

```sh
pet/.venv/bin/python -m pet.mind.runner --robot --allow head,walk --minutes 10 --cam-hz 1 --save-frames --tether 0.8
```

### The first session, what you will see

- **Session 1, `--allow head` (default).** Only `turn_head`, `look_around`, `nod`, `wait`, `stop`: the head moves
  under stand61 while the legs balance; between intentions the head returns to centre. Expect an intention every
  10-25 s (the model answers in 4-13 s while the body holds). Touch a head pad: the runner logs `[touch]`, the brain's
  reflex is `stop -> nod`, then a new intention that mentions the touch. Clap or speak near it only if you started with
  `--mic hw:0,0` (off by default; the mics may be in use by another process).
- **Session 2, `--allow head,walk`, only with you guarding.** Adds `walk`, `approach_owner`, `wander` (0.2-0.25 m/s,
  turns within +-0.3 rad/s, the robot-tested commands) and `bow` (ground-pick phase 0.4, then 0.9: the policy's
  standing rest; the runner hands back to the zero-command walk when the step ends, on the robot `walk_wired.py` does
  it itself at phase 0.9). Every walking command carries `for_s`, so the brain stops the walk by itself if the runner
  dies. `wander` alternates a slow left and right arc; nothing here knows where the walls are.
- **Session 3, `--allow all`, not before the brain's stand-up from the seat is fixed.** Adds `sit`, `rest` (sit with
  the head down) and `stand`. A seat takes 2.8 s; the runner waits for the brain's `seated` before it believes the
  posture, and a `sit: STALLED` line (legs did not fold) counts as a refusal: the intention stops, the body stays
  "standing" for the mind. Between seated intentions the idle command is the plain sit, not a stand-up. Why last: see
  "Sit and stand" below.

### Sit and stand: what the simulation showed on 2026-10-29

The brain stands up from the seat on a timer: any command other than sit sets the sitstand61 posture flag to 0 for
`UNSIT_S` = 2.0 s and then switches to the wanted mode (`walk_brain.py` lines 126-129, 526-532). In the as-built
MuJoCo duck at 7.0 V the sitstand61 rise does not finish inside those 2 s: the knees go 1.3 -> 0.7 rad and fall back
to 1.3-1.4 rad about twice a second (a limit cycle, the same in every log), so the hand-over to stand61 lands at a
random point of that cycle. Through the brain-in-sim path this runner uses (`fake_pi.py` + `walk_brain.py` over UDP)
the stand-up to walk fell in 7 of 8 tries (two runner days, the three members of the first Mac mini batch, and three
dedicated seats of 30 and 140 s with and without the `rest` head pitch; the one that stood was the first runner day's
first seat), and an owner request that arrived 2 s into a sit fell the same way (`voice-trace-A`). Going through
`{"mode": "stand"}` (the open-loop ramp) first fell 3 times in 3. Logs: `out/runner-20261029/falls/` (rows from 3 s
before to 1 s after each fall).
The brain's own in-process check, `brain_sim_check.py --model asbuilt --sit-at 5 --unsit-at 45`, does not fall but
reports the same marginal rise: peak tilt 44.4 deg, 14 cm of travel and a 34 deg turn before stand61 settles
(seeds 0-2 identical; the sim is deterministic without read drops). On the robot a sitstand61 rise ran away on
2026-10-23 (CURRENT-STATE `policy_goal_guards`). Until the hand-over ends on evidence (proposed diff below), `sit` is
a robot-only experiment with Shawn's hands ready, and simulated days run with `--allow head,walk`.

### Stopping it

- `Ctrl-C` in the runner's terminal: it writes the idle command for the current posture (zero-command walk, or
  plain sit when seated) and exits. The brain keeps holding; torque stays on (the runner never writes `off` or
  `monitor`).
- Any command from the app: the runner sees a control-file value it did not write and **yields**: it clears its
  intention and writes nothing until the file has held an idle command (zero-command walk or sit) for 30 s
  (`--resume-s`), then it takes over again and says `RESUME`. Hold-to-walk, quack and every other app action therefore
  pause it.
- The brain's own stops: a guard trip (`STOP -> stand: tilt ...`, `HARDWARE ERROR`, `IMU LOST`, `BATTERY STOP`) or a
  fall (body gravity z past -0.5 for 0.3 s, the brain's own threshold) stops the runner (`FELL` / `GUARD TRIP` in the
  log). Right the duck, use the app to put the brain back in walk mode at zero command, and after 30 s upright the
  runner resumes. Three refusals within a minute stop it for good (`STOPPED`): check the body before restarting.

### What the owner says (the voice layer)

With `--inbox pet/state/inbox --state-dir pet/state` the runner reads what `pet/voice/` writes there (contract in
`pet/state/README.md`, "Inbox from the voice layer"; code in `inbox.py`), checking twice a second:

- **A task file** (`inbox/tasks/<stamp>.json`, "过来", "停下", "把橙色方块叼来") is renamed `.done` the moment it is taken,
  so it never runs twice, then runs in place of whatever the duck was doing: the current intention stops (`STOP ...:
  the owner asked: 过来`) and the task becomes the intention, source `owner`, with the same validator, the same
  readback, refusal and fall handling as any intention. The voice layer validates against `pet/state/body_card.json`,
  whose names differ: `groundpick` becomes the runner's `bow` (never phase 1.0), a parameter the runner's primitive
  does not take is left out, a primitive the runner does not allow (`--allow head`) is left out, a sitting duck asked
  to move stands first, and "abort if not standing" is left out of a sit. A task that validates to nothing is refused
  with the reason. When it ends the runner logs `OWNER TASK "过来": done` (or `replaced by a newer request`, `stopped
  at step 2/3: fell ...`, `refused: ...`, `dropped: the runner is stopped`), and the mind's next intention sees
  "did what the owner asked" in its recent events.
- **A rule file** (`inbox/rules/<stamp>.json`, "Stop going in the bedroom") is merged into `<state-dir>/rules.json` as
  pet/learn specifies (same trigger and outcome: replaced) with pet/learn's own `validate_rule`, handed to the live
  `pet.learn.match.Matcher`, shown in the next intention's prompt, and renamed `.done`.
- **A sentence line** (`inbox/owner_said.jsonl`) is an `owner_said` percept: salient, so the mind re-plans with "the
  owner said ..." in its recent events, unless it came with a task file (the task is what happens next). "Good duck"
  (`result: ignore, reaction: praised`) lifts valence by 0.4 and settles missing the owner and boredom; `said_no`
  lowers valence. Lines already in the file when the runner starts are history and are skipped.

pet/learn sees the session as its own day log, `learn_events.jsonl` in the output directory (`owner:said`,
`owner:praised`, `owner:said_no`, `self:did(<primitive>)` for every step, `self:fell`, `touch:head`, `see:owner`,
`sound:*`), and the matcher's confirmations and omissions are in the log and in `summary.json` (`learn`). The runner
does not write matcher weights back to `rules.json`; that stays with pet/learn's night.

### What the log records

`behaviour.log` has every intention (source `llm` or `fallback`, the model's latency, the steps, the abort
conditions), every step with its command count, every percept, every brain event (`body: seated`, `brain: walk`,
`brain wrote the file itself`), yields and resumes. `commands.jsonl` is the control-file history with session time
and the primitive behind each write; `events.jsonl` the readback and perception events with wall time; `calls.jsonl`
the model calls with tokens, latency and the raw answer. The brain's own log stays where `duck-run.sh` puts it
(`~/duck-logs/duck_wired_log_<suffix>.jsonl` on the A7Z); `summary.json` carries `brain.max_tilt_deg` and the row count
the runner saw.

## How it fits the brain

- Control file: written whole and atomically (temporary file, rename), as `walk_wired.py` and `duck-command.py`
  write it. The runner never merges fields it did not set and never writes one-shot keys (`jaw`, `jaw_mark`,
  `quack`, `kick`).
- Readback: tick rows give `mode`, `gb` (body gravity), `sit_phase`, `sit_stalled`, `touch`, `gyro_body`; stdout
  gives `X refused: why`, `sit: STALLED`, `STOP -> ...`, `HARDWARE ERROR`, `IMU LOST`, `mode -> ...`. Brain
  hand-backs (`STOP -> zero command: ground pick complete ...`, `walk for_s elapsed`) are recognised by the STOP
  line within 1.5 s of the file change and are not yields.
- Perception while the brain runs: the pads and the IMU are in the brain's rows (`duck_sense.py` quits when a brain
  holds the bus, so its stream is not available then); sound levels come from `arecord` in the agent (`--mic`), face
  frames from the camera daemon's shared frame when it already runs (`--cam-hz 0.5`; the runner never starts the
  camera) through `pet/identity` on the Mac that runs the runner (needs the enrolled `pet/identity/data/identity.sqlite`
  and the downloaded models; otherwise face recognition is off and the log says so).
- Timing: `Mind.tick()` runs on the wall clock in 0.1 s steps; a step starts on the tick after the previous one
  ended (about 0.1 s), and multi-command primitives (`nod`, `look_around`, `wander`) are issued at their offsets within
  1 ms of schedule. The model's call runs in a background thread; the loop keeps reading the body meanwhile, and an
  answer composed before a hard stop is dropped.

## Proposed changes to files other agents own

None are required for the first robot session (head only). The first is needed before `sit` joins a session; the
other two would help later:

- `walk_brain.py` `Brain.command()` (the sit hand-over, lines 526-532): end the rise on evidence instead of the
  `UNSIT_S` timer. The seat already has such a check (`SIT_KNEE_MIN`, "a seat the timer declares is checked against the
  knees"); the rise needs the mirror image. Sketch:

  ```python
  if s["phase"] == "rise":
      knees_up = all(abs(q[n]) < SIT_KNEE_MIN for n in ("left_knee", "right_knee"))
      s["up_for"] = s.get("up_for", 0.0) + 0.02 if knees_up and abs(gyro_body[1]) < 1.0 else 0.0
      if s["up_for"] >= 0.3 or now - s["t"] >= UNSIT_GIVEUP_S:   # e.g. 6.0 s, then hold like a stall
          nxt = self.sit_next or dict(WALK_ZERO)
          ...
  ```

  (q and gyro_body are available where `command()` is called from `tick()`; the sketch names the intent, the owner
  picks the plumbing.) With the hand-over at the top of the knee cycle the 2026-10-29 logs show stand61 settling in
  0.5 s; at the bottom it falls.

- `walk_brain.py` ground pick: a wanted `phase` of 1.0 is the same command as 0.0 (`[cos 2*pi*phi, sin 2*pi*phi]`), so
  the policy starts a new descent; the header's "1.0 then rises and rests standing" misleads a caller (it misled this
  runner: one fall on 2026-10-29). Clamping the wanted phase to `GP_DONE_PHASE` (0.9), or saying 0.9 in the header,
  would close it.

- `walk_brain.py` (Wi-Fi `main`): after a ground pick completes it does not rewrite the control file to the
  zero-command walk the way `walk_wired.py` does, so in `--sim` the runner's own idle write does that job. A
  three-line port of `walk_wired.py` lines 957-960 into `walk_brain.main` would make the two paths identical:

  ```python
  if brain.mode == "groundpick" and info.get("gp_phase", 0.0) >= GP_DONE_PHASE \
          and float(last_cmd[1].get("phase", 0.0)) >= GP_DONE_PHASE:
      write_cmd(args.cmd, {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}, "ground pick complete, stand61 takes over")
      last_cmd = read_cmd(args.cmd, None)
  ```

- `duck_sense.py`: its JSON line has no `touch` field; adding the pad block it already could read would let the
  runner's touch detector work while no brain runs (standby perception). Not needed while the brain owns the pads.
