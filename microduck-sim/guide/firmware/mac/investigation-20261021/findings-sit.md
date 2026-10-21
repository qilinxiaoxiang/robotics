# MicroDuck remote "sit" does not sit: findings (2026-10-21)

Problem 3 of the remote-control bring-up: on the remote page the "坐下 / 站起" button does not make the duck sit; standing up works. Robot off tonight; everything below is from code, tonight's A7Z logs (local copies) and the as-built MuJoCo sim. No robot was moved and no repo file was edited.

## Root cause

**Evidence (robot log).** Both sits tonight ran exactly as the Brain designs them, and the legs never moved.

- `/private/tmp/claude-501/stand/duck_wired_app1021-040436.out:114-127`: `mode -> sit`, `sit: posture flag 1`, four status lines, `sit: standing up (posture flag 0) for 2.0 s`, `mode -> walk`, `mode -> sit`, `sit: posture flag 1`; `:187-190`: `sit: standing up (posture flag 0) for 2.0 s` ... `mode -> stand`. No `refused`, no `STOP` line in either run tonight (`grep refused|STOP` on both `.out` files: nothing).
- Tick log `duck_wired_log_app1021-040436.jsonl` (times from the first row): sit 1 at 95.93 s from stand61 (`cmd {"mode":"sit"}`), `sit_phase` prep -> down at 96.73 s (+0.80 s) -> seated at 98.74 s (+2.01 s); at 99.93 s (4.00 s after the sit) the control file read `{"mode":"walk","vx":0,...}` -> rise -> walk at 101.95 s. Sit 2 at 103.21 s -> down 104.02 -> seated 106.03; seven quacks 108-116 s; at 156.16 s the file read `{"mode":"stand"}` -> rise -> stand at 158.16 s. `policy == "sitstand"`, `sit_flag == 1.0`, `kp == 200` on every seated row; of the 2530 sit-2 ticks only 1 had no action (1 dropped read, 0 invalid IMU, sample age at most 36 ms).
- Joints did not move. Mean model-rad positions (servo-order names from `pi/microduck_rt/constants.py` `MOTOR_TO_ID`): robot stand61 before sit 1 vs robot "seated" (120-150 s): left_knee 0.025 -> 0.025, right_knee -0.043 -> -0.034, left_ankle 0.477 -> 0.448, right_ankle -0.437 -> -0.492, hip pitches -0.429/0.371 -> -0.425/0.439. The seat in the plugged as-built sim (same Brain, `teleop-sim-check.json:274-302`, trunk z 0.1155 -> 0.0573 m) has left_knee 1.335, right_knee -1.36, ankles 0.077/-0.103. Body gravity stayed `[+0.08 -0.07 -0.99]` (about 6 deg tilt) the whole time: the duck stood on the sitstand policy for 53 s and the Brain called it "seated" by its timer (`walk_brain.py:352-353`: `elif s["phase"] == "down" and now - s["t"] >= SIT_SETTLE_S: s.update(phase="seated", t=now)`).
- The policy itself never commanded a seat on the robot. Seated-phase actions: max |a| 0.21 rad, knees -0.199/+0.211 (wrong direction and small); in the sim the seated actions are knees +1.168/-1.17, max |a| 1.17. First 0.5 s after the flag flipped: sim goals move knees 0.17/-0.31 rad and ankles 0.27 rad and the joints follow by 0.06-0.08 rad; robot goals move at most 0.10 rad and the joints move 0.000-0.004 rad (head joints did follow: head_pitch -0.040 for a -0.041 goal change).

**Mechanism (offline replay, scratchpad `replay_sit.py`).** Rebuilding the 61-input observation from the logged rows (`gyro_body`, `gb`, `q`-default, `dq`, previous action, `[flag,0,0]`, head, zeros) and running `sitstand61.onnx` reproduces the logged robot actions to 0.001 rad (291 ticks), so the Brain fed the policy exactly what `walk_brain.py:499-504` says. With every sensor block frozen and only the action fed back, the policy is a fixed point in both worlds (robot: left-knee action stays -0.21 for 50 ticks; sim first flag-1 tick: stays -0.15). Swapping single blocks (gyro, gravity, joint pos, joint vel, head) between the robot's and the sim's first flag-1 observation changes the fixed point by at most 0.08 rad, and a gravity sweep of -6..+9 deg pitch, +-4 deg roll moves the knee action only between +0.3 and -0.25. So no observation offset explains it: the sim's descent is a closed loop that starts from the physical response to the policy's first small moves (knees/ankles about 0.1-0.3 rad). On the robot the loaded leg servos did not respond to those moves, the observation never changed, and the policy stayed in its standing fixed point for as long as the flag was 1.

**Sim reproduction.** `brain_sim_check.py --model asbuilt --manifest ../../../microduck_rl/cmu/model/manifests/plugged.json --volt 7.0 --drop 0.04 --walk-s 0 --sit-at 4 --unsit-at 10 --seed 0` (the CURRENT-STATE real condition: `CURRENT-STATE.json:78-79` servo_rail_v 7.0, `:37-38` servo_read_drop_fraction 0.04; the `teleop_sim_batch.py` invocation):

- friction x1 (as 10/20): sits, flag1 4.82 s, seated trunk z 0.0573 m, peak tilt 10.6 deg, stands up at 10 s, stable 0.18 s after; left knee passes 1.0 rad 0.92 s after the flag. Matches `teleop-sim-check.json` (seed 0: 0.0573 / 10.6 / 0.18).
- `--imu-pitch 8` (sim gravity x +0.069, the robot's +0.07): still sits (trunk z 0.0596, knee action 1.23). The robot's forward-pitched gravity reading is not the cause.
- `--bam-friction-scale 3.0` (`brain_sim_check.py:75,393`: scales BAM's stiction and load friction): reproduces tonight's signature exactly: flag1 4.82, "seated" declared, trunk z stays 0.1151 (standing 0.1155), seated knee actions -0.106/-0.036, max |a| 0.285, left knee 0.08 rad at 6.8 s (robot: 0.02). x1.5 still sits; x2.0 and x2.5 make stand61 fall before the sit (2.1-2.2 s), so x3.0 is the first level at which stand61 holds and the sit stalls. It is a proxy for the measured real servo response (jitter sim-ID 10/17: servo amplitude ratio 0.2-0.45 against the sim's 0.25-0.75), not a measurement.
- At friction x3.0 none of the runtime levers restores the sit: `--kp-rl 300` (trunk z 0.1148), `--kp-rl 400` (0.1148), `--breakaway` (the stand-mode stiction push, 0.1147), from the open-loop STAND instead of stand61 (0.1148). At friction x1 `--kp-rl 400` sits but the stand-up diverges (max tilt 44.6 deg, 87 action jumps). The stall is a fixed point of the policy, not a gain shortfall the Brain can tune away.

**Root cause, one sentence.** The loaded leg servos (XL330 at P 200 on the 7.0 V bench rail) do not follow the first 0.1-0.3 rad moves of Pollen's sitstand policy, so its closed-loop descent never begins; the Brain, the quack gate and the remote page then declare "seated" by timer with the duck still standing. It is the same servo-response gap as the standing and walking gaps (CURRENT-STATE `leg_joint_friction_unloaded`: the loaded case is still unmeasured; memory "servo deadband = gain": loaded joints ignore steps under about 0.05 rad), not a command, timing, file or model problem.

### What is not the cause (checked)

- Command sequence: the page writes `{"mode":"sit"}` (`robot-remote.js:112`), the Brain accepts it from stand or walk (`walk_brain.py:301-305`), flag 0 for 0.8 s then 1 (`:93-95, :350-353`), as Pollen's simulator does (`microduck-simulator/app/src/game/game.js:1680-1688`, 800 ms sit timer, 2000 ms stand timer) and robotd (`control.rs:448-475` sit_toggle, `:628-633` `c.twist = [1.0, 0.0, 0.0]`; `robotd-params/src/lib.rs:1781,1784` rise 1.0 s, ramp 2.0 s; ours rises 2.0 s, `UNSIT_S`).
- No joystick or periodic walk command overwrote the sit: tonight's two runs contain no command with `vx 0.25` or `for_s` at all; walking was never used. The first sit was ended 4.00 s after it began by an explicit `walk` zero command (the "坐下 / 站起" toggle reading the brain mode `sit` -> `站起`, `robot-remote.js:103,112`, or the 闭环站立 key; both write `WALK_ZERO`, indistinguishable in the log).
- `sitstand61.onnx` present and loaded: `install_teleop.sh:54,117` copies and asserts all six policies; sha256 in `runtime-overlay/source-lock.json`; the log shows `policy: "sitstand"` rows, so the A7Z copy loaded.
- Guards: `--max-tilt-sit 30` (`walk_wired.py:254,657-659`) never tripped (tilt 6 deg); the hard action limit never tripped (max |a| 0.28); no `STOP ->` line; no IMU loss during the sits (`imu_valid` true on every row).
- Run app1021-035737 (319 s): no sit command ever reached the control file (commands were only `stand` and `walk` zero); if sit was pressed there, the page refused it locally (`robot-remote.js:110-111`, brain mode not sit/stand/walk) or the A7Z was offline; the log cannot tell.
- The 82d5f87 fix (head command while seated reaching the policy) is unrelated to the stall: `head_cmd` was zero on every sit row tonight (no `head_cmd` key).

## What I ran

- `git show 8bbaef9`, `git show 82d5f87`; read `walk_brain.py`, `walk_wired.py`, `robot-live.html`, `src/robot-remote.js`, `a7z-bridge.mjs`, `desktop/duck-command.py`, `desktop/duck-telemetry.py`, `install_teleop.sh`, `test_teleop_modes.py`, `teleop_sim_batch.py`, `teleop-sim-check.json`, `brain_sim_check.py`, Pollen `game.js` and robotd `control.rs` (scratch checkout of another session).
- Logs: local copies `/private/tmp/claude-501/stand/duck_wired_{app1021-035737,app1021-040436}.out` and `duck_wired_log_app1021-*.jsonl` (the only copies found by the `find`; `stand-gap-20261021/` holds no `tonight.log`).
- `~/.venvs/microduck-walk/bin/python -m unittest test_teleop_modes -k sit -v`: 4 sit tests OK (they test timing on a fake world whose goals become positions at once, so they cannot see a stall).
- `brain_sim_check.py` sit runs listed above (one process at a time, `timeout 600`, about 3 s each; the script re-execs under `~/.venvs/microduck-dyn`); tick logs in the scratchpad (`sim_sit_seed0.jsonl`, `sim_sit_pitch8.jsonl`, `sim_sit_fric{1.5,2.0,3.0}.jsonl`).
- `replay_sit.py` (scratchpad): offline ONNX replay and block-swap experiment.

## Patch (scratchpad only, not applied)

`/private/tmp/claude-501/-Users-xiangzheng-code-robotics/74602e44-fa79-4564-a436-c7a3c8ce2ecd/scratchpad/sit-stall.patch` (`git apply --check` passes against the working tree):

- `walk_brain.py`: `SIT_KNEE_MIN = 0.6`; at the first policy tick whose phase is `seated`, if both |knee| are under it, print `sit: STALLED, still standing on the sitstand policy: knees ... ; the leg servos did not follow the policy's first moves. Any stand or walk command stands it up as usual.` and log `sit_stalled` on every seated row. Behaviour is otherwise unchanged: the policy keeps balancing (it did for 53 s tonight) and the normal stand-up path applies.
- `duck-command.py`: `NOTE` regex gains `sit: STALLED` so the page's `op: read` notes carry it (a page follow-up would show it after the 坐下 button, like `checkTorque` does for torque).

Failing test `scratchpad/test_sit_stall.py` (fake link whose leg servos 1-10 start at the stand pose and never follow a goal, head servos do): on the repo code `AssertionError: 'sit: STALLED' not found` (the timer still declares `seated` with knees at 0.0); with the patch applied at import (`sit_patch_monkey.py`, same code) it passes, and the 17 existing `test_teleop_modes` tests still pass.

Runs:

```
SIT_PATCH=0 ~/.venvs/microduck-walk/bin/python -m unittest test_sit_stall -v   # FAILED (failures=1)
SIT_PATCH=1 ~/.venvs/microduck-walk/bin/python -m unittest test_sit_stall -v   # OK
```

The patch makes the failure visible; it does not make the duck sit. Nothing in the Brain can: the sim at robot-like friction stalls at P 300, P 400 and with the breakaway push.

## Unverified

- Whether the real servos complete the sit once motion starts (the fixed-point mechanism on hardware). The sim says yes at friction x1 and no lever helps at x3; only the robot can show which side of that line it sits on.
- Whether `--breakaway` was on in tonight's launch (`~/duck-run.sh` is on the A7Z, offline; `install_teleop.sh:8` lists its flags without it, so most likely off). The sim says it would not have helped.
- The loaded leg-joint response at P 200 (CURRENT-STATE `leg_joint_friction_unloaded` covers the unloaded case only).
- `--bam-friction-scale 3.0` is a proxy; the real deficit is not that number.
- Whether a sit press happened in run 035737.

## Robot acceptance for the next powered session (Shawn guarding, bench supply)

1. Deploy the patch with `microduck-sim/guide/firmware/a7z/install_teleop.sh`, restart the brain (`~/duck-run.sh <suffix>` on the A7Z, comes up in monitor mode), open `robot-live.html`.
2. 闭环站立 (Y): expect `torque on at present positions`, `mode -> walk`, page `大脑：走/闭环站立 · 扭矩开`, tilt under 10 deg, then wait 3 s.
3. Press 坐下 (R) once. Expected stdout: `mode -> sit`, then 0.8 s later `sit: posture flag 1`. Expected log rows: `policy == "sitstand"`, `sit_phase` prep (0.8 s) -> down (2.0 s) -> seated, `sit_flag` 0 then 1, `kp` 200. Expected motion ("works"): within 1 s of the flag line the knees fold (log `q` for left_knee and right_knee beyond +-1.0 rad; the sim reaches 1.0 rad 0.92 s after the flag and settles at 1.33/-1.36), trunk about 6 cm lower, peak tilt about 10-11 deg, then level (sim seated tilt 0.8-0.9 deg), no `STOP ->` line, no `sit: STALLED` line. User timing: nothing visible for 0.8 s, descent in the next second, settled by about 3 s after the press.
4. If instead `sit: STALLED ... knees +0.0x / -0.0x` prints with the duck still standing (tonight's signature), the Brain is not the problem; do the discriminating hardware check with the flag at 1: tip the trunk back and press the hips down a few centimetres by hand. If the policy then completes the sit without a fall, the fixed-point mechanism is confirmed on the robot and the repair is on the servo-response side (loaded leg friction, or a policy trained on the measured response); if it does not, reopen the observation side.
5. Press 坐下 / 站起 again (R, page shows mode `坐`): expect `sit: standing up (posture flag 0) for 2.0 s`, after 2 s `mode -> walk`, stand61 holding under 10 deg tilt (stand-up worked both times tonight from the standing stall; from a real seat it is sim-only so far: stable 0.16-0.18 s after the hand-back).

Note for the page: the 坐下 / 站起 toggle reads the brain mode from the telemetry (`robot-remote.js:103`, `duck-telemetry.py:345`, 0.1 s fast records); a second press within that window, or after a stand-up while the mode still reads `sit`, sends the opposite command. Tonight's first sit was ended that way after 4.0 s.
