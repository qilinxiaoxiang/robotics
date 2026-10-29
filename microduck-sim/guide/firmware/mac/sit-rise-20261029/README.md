# Sit-to-stand rise: why it limit-cycles, and a hand-over on evidence (2026-10-29)

Simulation only (Mac mini, `~/sims/bvh-refit-20261029/rt`). Nothing ran on the robot and nothing was deployed to the A7Z.

**Result.** The sitstand61 rise is marginal on the current as-built model, and whether it finishes, cycles or falls
depends on the control loop's delay. A fixed 2.0 s timer (`UNSIT_S`) therefore handed stand61 an arbitrary state.
`walk_brain.py` now ends the rise on evidence. Both knees must be under `SIT_KNEE_MIN`, the pitch rate under 1.0 rad/s
and the tilt under 12 deg, all held for 0.3 s. A rise that is not up after 4.0 s sits back down ("sit: RISE FAILED")
and stays seated until `{"mode": "sit"}` re-arms the stand-up.

On the runner path (fake_pi + walk_brain over UDP), the change turns 10 falls in 16 seats into 0 falls in 16. The cost
is that none of those 16 seats stands up: in that loop the rise never settles within 4 s. In-process at the real
conditions, 7 of 8 seats stand up 1.30-1.46 s after the command, about 0.6 s sooner than before.

Two failures remain that the hand-over cannot fix:
- **Falls during the rise itself.** A fast loop makes the rise fall backward, and one seed falls with compensation on.
- **The open-loop stand after a sit.** Switching to `{"mode": "stand"}` after a sit still falls about half the time,
  even after 4 s of quiet stand61. The same switch without a sit holds 8 of 8.

## Cause

Every run below uses the as-built plant at the real conditions from `microduck-sim/CURRENT-STATE.json`: 7.0 V and 4 %
dropped reads. The manifest is the plugged manifest of microduck_rl 87979d52 unless named. The run sits at 4 s and
stands up at 10 s. Commands are `rise_batch.py SET`; rows are in `results/<set>.jsonl`.

**Loop delay decides the rise.** `brain_sim_check.py` defaults to a 1-tick sensor delay plus a 1-tick action delay
(40 ms). fake_pi's servo emulation answers within the tick (brain read 12 ms, applied age 17 ms). Set `fakepi_like` runs
fake_pi's plant in-process: the 10-15 manifest, no BVH refit, no drops. It ran under the old timer so the 14 s rise
is honoured; rows are in `results/before/fakepi_like*.jsonl`. `results/fakepi_like.jsonl` is the same set under the
new hand-over.
- **Default 40 ms delay:** up in 0.74-1.32 s, tilt 5 deg.
- **Zero delay, no compensation:** the knees cycle 1.4 -> 0.6 -> 1.4 rad (13 crossings) and only settle at 5.8 s.
- **Zero delay with `--compensation`** (walk_brain's Wi-Fi main default, used by the runner): 17 crossings, up at
  8.1 s.
- **Zero delay on the current manifest:** falls backward, 75 deg (`long_fp_sd0_ad0_now`). Removing either delay alone
  on the current manifest also falls backward: `long_sd0` 4 of 4 and `long_ad0` 4 of 4, peaks 76-82 deg.

The robot's loop sits between these regimes: a 15 ms pipeline plus half a 50 Hz period, per CURRENT-STATE
`imu_added_delay_ms`. The cycle the runner agent saw is the zero-delay case of this loop. It is not a fake_pi defect.

**The mass model adds tilt.** With the 40 ms delay (set `cause`), rise tilt peaks at:
- **10-19 manifest:** 3.6 deg, up in 0.8 s.
- **10-15 as-built:** 5-6 deg.
- **V1.29 saddle:** 10-11 deg.
- **Current manifest:** 17-33 deg. Seed 2 crouches at 40 deg with a knee at 0.46 rad and falls when stand61 takes over.

**Other factors tested:**
- **Rail voltage:** 7.4 V and 8.0 V lower the tilt slightly (14-20 deg). It is a minor factor.
- **BVH refit:** a stale BVH changes nothing (set `stale`).
- **D-030 neck:** not involved. The walk-mode sit runs the sitstand policy, which commands the neck itself.
- **Posture flag:** unchanged. It is 0 for the rise and 1 for the seat, as in Pollen's simulator.

**Pollen's own handling**, read from source on 2026-10-29:
- **Simulator** (`microduck-simulator/app/src/game/game.js:1660-1688`): leaving a sit sets the flag to 0 and switches
  modes after 2000 ms with `lastAction` zeroed. Ours copied that timer.
- **infer_policy** (`microduck_rl/scripts/infer_policy.py:808-845`, `toggle_sit`): stays on the sitstand session after
  the flag flips and holds the stand. The source says: "Do NOT swap to the standing policy here". A velocity command
  switches back later.
- **robotd** (github pollen-robotics/microduck @6cdfdaa; `robotd-params/src/lib.rs:1779-1784`, `robotd/src/control.rs`):
  rises for `DEFAULT_SITSTAND_RISE_S` = 1.0 s and then hands to velstand ("velstand owns the tail of the rise"). It
  rises at standing gain 0.8 x 200 = 160, with leg/head target low-pass 0.7/0.5.
- **robotd settings in our sim** (set `cause`): they do not rescue the current model.
  - **kp 160:** 4 of 4 fall during the rise.
  - **Low-pass alone:** 2 of 4 fall.
  - **Both together:** 1 of 4 falls and one crouches at 41 deg.
  - **HF `alpha_sitstand.onnx` v6** (a6f102d9, branch sitstand_no_fall_back) in place of our sitstand61 (c6c40e35):
    no fall, but peaks of 13-35 deg.
  - **A 1 s timer to stand61** (set `handover`, `timer1_now`): seed 2 falls.

No Pollen route ends the rise on the robot's state. Each one either waits a fixed time or never leaves the sitstand
policy. On their mass model the rise is quick (our 10-19 model: 0.8 s, 3.6 deg), so a timer works there. On ours it
does not.

## The change (walk_brain.py)

- **`UNSIT_S` removed.** It is replaced by `RISE_UP_S` 0.3 s, `RISE_QUIET_RATE` 1.0 rad/s (body pitch rate),
  `RISE_UPRIGHT_DEG` 12 deg (the brain's tilt reading, trim included) and `RISE_GIVEUP_S` 4.0 s.
- **The up test.** `Brain.tick` evaluates it on every rise tick and logs `sit_up` plus the reason. `route()` hands over
  after 0.3 s of continuous "up" and prints `sit: up after X s, handing over`.
- **Give-up.** After 4 s without "up" the brain prints `sit: RISE FAILED ...`, returns to the seat (phase `down`,
  flag 1), clears the queued command and refuses stand-ups. A later `{"mode": "sit"}` re-arms it and prints
  `sit: stand-up re-armed`.
- **Why the upright test.** Knees alone are not enough: a duck lying on its back has straight knees (set `ba_sd0`,
  tilt 67 deg).
- **Tests** (`test_teleop_modes.py`): the two older integration tests now use a scripted sitstand stand-in, because the
  fake world has no physics. Four new tests cover:
  - the hand-over when up;
  - a rise that never comes up, sits back down and waits for a sit;
  - the re-arm and a second stand-up;
  - straight knees on a 20 deg body, which do not count as up.
- **Test result:** 106 pass (`test_teleop_modes`, `test_sit_stall`, `test_sit_runaway`, `test_stance_switch`,
  `test_yaw_trim`, `test_pickup_modes`, `getup-20261026/test_getup`).

## Before and after

"Before" is `walk_brain.py` from e4a92b4 (md5 8b319f5a), in the copy `var-before20261029`. "After" is the working tree
(md5 dec6855e). The script is `before_after.sh`. Before rows are in `results/before/`, after rows in `results/`.

**In-process, set `ba`** (current manifest, 7.0 V, 4 % drops):
- **No compensation, 8 seeds:**
  - **Before:** hands over at 2.0 s every time. Seed 2 is handed over at knee 0.505 into a 35.5 deg crouch.
  - **After:** 7 seeds up in 1.30-1.46 s, knee 0.07-0.15, tilt after at most 6.3 deg. Seed 2 gives up and re-seats
    at 5.7 deg.
- **Compensation, 8 seeds:**
  - **Before:** seed 2 falls during the rise. Seed 5 is handed over at knee 0.535 into 32.8 deg.
  - **After:** 6 seeds up in 1.32-1.88 s. Seed 5 re-seats at 4.4 deg. Seed 2 still falls during the rise.
- **Sensor delay 0, 8 seeds:** the rise falls backward 8 of 8, before and after. Before, stand61 runs on a duck lying
  on its back. After, the brain asks for the seat on its back. Neither helps.
- **10-19 manifest:** up at 0.82 s instead of 2.0 s.
- **7.4 V:** up at 1.28-1.30 s.

**Teleop sit cases** (`teleop_sim_batch.py`, 3 seeds each; `teleop-sim-check.json` regenerated): no falls before or
after.
- **`sit_stand_from_stand61`:** peaks before 21.2/13.8/39.5 deg, after 21.2/13.8/37.2 deg. Stable after the hand-over:
  before 0.18/0.18/2.46 s, after 0.28/0.32 s, and seed 2 re-seated (no stable stand).
- **`sit_stand_from_STAND`:** peaks unchanged. Stable before 2.42/0.18/0.16 s, after 1.08/0.34/0.76 s.
- **Other cases:** the kick and ground-pick cases are unchanged.

**Runner path** (`fakepi_seat.py`: fake_pi + walk_brain main loop as `pet/mind/runner.py` launches it, 10-15 config,
7.0 V; summary from `seat_summary.py`):
- **Compensation on (the runner's default):**
  - **Before:** 8 of 8 fell, with and without the BVH refit.
  - **After:** 0 of 12 fell, including 4 seats via `{"mode": "stand"}`. All 12 gave up and re-seated upright (body g_z
    -1.00). Knees at the give-up were 0.64-1.33 rad, cycling.
- **Compensation off:**
  - **Before:** 2 of 8 fell and 6 stood.
  - **After:** 0 of 4 fell and 0 stood; all 4 gave up.
- **Why none stood:** this loop needs 5.8-8.1 s to settle (cause above). A 4 s give-up refuses it, where the 2 s timer
  sometimes got lucky.

**Open-loop stand after a sit** (sets `ba_tostand`, `stand_route`, `stand_switch`):
- **Direct `{"mode": "stand"}` at the stand-up:** fell 2 of 4 before and 3 of 4 after. The earlier hand-over gives the
  2 s stand ramp a less settled start.
- **Through stand61 first:** fell 5 of 7 with the stand at 2 s and 4 of 7 at 4 s; with compensation, 2 of 3 at 4 s.
- **Without a sit, the same stand61 -> stand switch** holds 8 of 8 at 7.0 V and 4 of 4 at 7.4 V. Its peak is 4.6-4.8
  deg.
- **What differs.** At the switch the joint angles match within 0.02 rad (`stand_entry.py`). After a sit, stand61
  holds larger goal-to-measured errors at the knees and ankles, 93-115 ticks against 71-85 (`stand_goals.py`). The ramp
  releases that preload and the trunk pitches back.
- **Status:** the mechanism is not isolated further. The open-loop stand is the wrong successor to a sit. Pollen's
  successor is always velstand, our stand61.

## Robot test proposed (not run; Shawn at the robot, hands ready)

1. **Deploy.** Install this `walk_brain.py` on the A7Z (`install_teleop.sh`), then start the brain with `duck-run.sh`
   with the wired log as usual: `/tmp/duck_wired_<suffix>.out` and `--log /tmp/duck_wired_log_<suffix>.jsonl`.
2. **Sit.** From stand61 (walk at zero command), send `{"mode": "sit"}` from the app and wait for the seat, about 3 s.
3. **Stand up.** Send a walk at zero command. Read the brain's line: `sit: up after X s, handing over` or
   `sit: RISE FAILED (knees ..., pitch rate ..., tilt ...)`.
4. **Repeat.** Three seats. After a give-up, send `{"mode": "sit"}` before the next stand-up.
5. **Never `{"mode": "stand"}` after a sit.** The open-loop stand after a sit falls in the sim.
6. **Read back from the log.** Collect:
   - the rise time;
   - the peak trunk tilt during the rise;
   - knee crossings of 1.0 rad;
   - the state at the hand-over.

   `walk_wired.py` trips its sit guard at 30 deg (`MAX_TILT_SIT_DEG`), and the in-process rise peaks at 17-33 deg. A
   guard trip is a result, not a fault.

**Reading the outcome:**
- **Up in under 2 s, tilt under 25 deg:** the robot's loop is in the finishing regime and the hand-over is the fix.
- **RISE FAILED with knees cycling:** the robot is in the fast-loop regime. The rise needs a policy trained on our mass
  model; a longer give-up is not the fix.

## Not done / for others

- **`pet/mind/brain_link.py`** treats "sit: STALLED" as a refusal (line 300). It should treat "sit: RISE FAILED" the
  same way. The runner's `DryBrain` (`pet/mind/runner.py:847-920`) still mimics the 2.0 s `UNSIT_S` timer. The runner
  should stand up via a walk command, never `{"mode": "stand"}`, after a sit. These were not edited (owned by the
  pet/mind agents).
- **Team repo:** the microduck_rl copy of walk_brain.py is stale until the next `cmu/sync_from_robotics.py`. Nothing was
  pushed.
- **Not run:** `long_v19` errored because the v19 config is missing in the snapshot. There was no robot run.
- **Open:** the mechanism of the open-loop stand falls after a sit. The real fix for the rise is a sitstand policy
  trained on the current mass model and loop delay. That training needs Shawn's nod first.

## Files

- **Scripts:**
  - `rise_run.py`: one run with a condition patched in.
  - `rise_batch.py`: sets and metrics.
  - `fakepi_seat.py`, `fakepi_cause.sh`, `seat_summary.py`: the runner path.
  - `before_after.sh`.
- **Diagnostics:** `compare_rise.py`, `compare_seat.py`, `seat_timing.py`, `show_ticks.py`, `stand_entry.py`,
  `stand_goals.py`.
- **Logs:** `*.out` logs are gitignored; their numbers are quoted above. Tick logs are on the Mac mini under
  `~/sims/sit-rise-20261029/ticks/`, and seat folders under `~/sims/sit-rise-20261029/seat-*`.
