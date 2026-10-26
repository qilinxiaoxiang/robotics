# Get-up after a fall: simulation, walk_brain recover mode, velstand check (2026-10-26)

Pet-robot Tier 1, first item (`docs/PET_ROBOT_FEATURES.md`). Final-goal link: a duck that falls during the walk to an item (step 2) must get up again by itself.

## Result

- `stand61.onnx` (SHA256 `15692687...c2e6fc254`, identical to Hugging Face `pollen-robotics/microduck-policies` `alpha_stand.onnx` at commit `665ae4e`) gets the as-built duck up from every start tried, once two of our own blocks are out of the way. With the new `recover` sequence it stood in 50/50 runs on the saddle model. In 2 side starts the duck went back down after first standing, and both got up again before the run ended.
- The blocks are ours. The first is `Brain.tick()`'s 60 deg gate (`off`: 0/9 lying starts rose). The second is `walk_wired.py`'s 3.0 rad hard action limit: a face-down rise always asks for about 3.2-3.7 rad, so the guard stopped 10 of 10 face-down rises into the open-loop STAND. The tilt stop (30 deg) would stop every rise too.
- `velstand.onnx` v8 (SHA256 `2fc7f8ee...6ccf492`) has the same 61-input layout and metadata as our policies. It is weaker than stand61 here: under `nogate` it fails 2/10 face-up, 3/10 side and 2/10 push starts. It gets stuck lying with actions about 1.57 rad, the "stays on its back" freeze Pollen's v8 notes describe. Under `recover` it fails 2/10 face-up and 4/10 side. **Not a candidate to replace walk61 on this evidence.** Its walking was not simulated.

## Plant and conditions

- Plant: the brain_sim_check.py plant (`ev.load`, the as-built config, BAM XL330 m6 actuators, 2.5 ms steps). Sensor and action delay are one tick each, and the sensor path runs through the Brain's real quaternion and gyro transforms.
- Supply 7.0 V (`servo_rail_v`) and 4 % dropped servo reads (`servo_read_drop_fraction`), both read from `microduck-sim/CURRENT-STATE.json`, as `robot_state_check.py --print-sim-args` gives them (`--volt 7.0 --drop 0.04`).
- Mass model: `guide/print/a7z-saddle/balance/manifest-saddle.json`, the D-022 manifest with a 70 g A7Z module on the torso roof, the head without its board and the USB camera at 10 g. Case `headA7Z` reruns recover with the A7Z in the head (`asbuilt-mass-manifest.json`).
- Start poses follow Pollen's standup reset (`microduck_standup_env_cfg.py`, `mdp.set_random_ground_state`):
  - face_down is +90 deg pitch, face_up is -90 deg with up to +-30 deg log-roll, side is +-90 deg roll.
  - All lying poses start at the policy default joints, with 0.05 rad noise, random yaw and seeds 0-9.
  - sitting uses Pollen's sit keyframe within +-10 deg of upright, held at KP 200. At KP 50 the seat tips back while it settles.
  - Lying starts settle 1.5 s at KP 50 before `{"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0}`.
  - push: standing on stand61, then 8 N for 0.15 s at 2.0 s, in direction 36 deg x seed.
- Success means the trunk's true gravity z stays under -0.85 and the trunk stays above 0.08 m for the last 2 s of a 12 s run (10 s for push), with no guard stop.
- Up time counts from the command, or from the 60 deg crossing for push, to the first 1 s spent standing (gravity z < -0.85, trunk above 0.10 m).
- Loads come from the BAM actuator torque against its limit, 0.538 N m at 7.0 V. "sat" is the time a joint spends at 95 % of that limit or more.

## Numbers (`summary.json`; rows in `results.jsonl`)

Each item gives the success count out of 10, the up time median and maximum, the worst single-joint saturation time, and the maximum |action|.

### stand61-recover, saddle model, guard off

- face_down: 10/10, up 2.46 / 2.82 s, sat at most 0.26 s, action at most 3.70
- face_up: 10/10, up 2.18 / 2.50 s, sat 0.30 s, action 3.35
- side: 10/10, up 2.30 / 5.54 s, sat 0.50 s, action 3.87; 2 seeds went down again once and got up again
- sitting: 10/10, up 0.28 / 3.16 s, sat 0.40 s, action 3.82
- push: 10/10, up 2.38 / 4.10 s after the fall, sat 0.46 s, action 5.09. The predictor fired about 20-40 ms before the 60 deg crossing (LIMP at 2.20-2.26 s for a 2.0 s push).
- The longest saturation over all 50 runs, joint by joint: left hip pitch 0.50 s, right knee 0.46, right hip pitch 0.44, left knee 0.40, neck pitch 0.34, head yaw 0.20, head pitch 0.18. Seconds over 2 s would be needed before an XL330 overload trip becomes likely; see Risks.

### The same sequence with one condition changed

- POSE_S 0.6 (robotd's value): 50/50, about 0.4 s faster (face_down median 2.08 s).
- A7Z in the head (`asbuilt` manifest): 50/50.
- 4 deg IMU pitch (`--imu-pitch 4`, the trim error case): 48/50. One side start was not standing at the end. One push GAVE_UP, which held soft as designed. face_up up time median 3.64 s, max 7.06 s.
- Guard 3.0 kept (walk_wired default): face_down 0/10, face_up 8/10, side 9/10, sitting 9/10, push 7/10.

### Without the sequence

- stand61-nogate (gate removed only), guard off: 50/50. Up is faster (face_down 1.00 s, face_up 0.68 s, push 0.92 s) because the policy acts at once. It stands up from the dynamic fall at walking gain instead of from a still, posed robot. Loads are similar (worst joint 0.66 s, push). The maximum action is higher: 5.83 rad on push, 6.14 rad on one sitting seed.
- stand61-nogate with guard 3.0: face_down 0/10, face_up 5/10, side 10/10, sitting 9/10, push 6/10.
- stand61-off (today's code), 3 seeds per pose: 0/9 lying starts rose; push 1/3, the two others stayed down.

### velstand v8 (`models-velstand/`: velstand.onnx as both walk61 and stand61)

- nogate, guard off: face_down 10/10 (up 0.70 s), face_up 8/10, side 7/10, sitting 10/10 (1.88 s), push 8/10
- recover, guard off: face_down 10/10, face_up 8/10, side 6/10, sitting 10/10, push 10/10; the 6 failures all ended in GAVE_UP
- nogate with guard 3.0: 0/50, because its rises use 3.6-3.9 rad

## Reproduce

```
cd microduck-sim/guide/firmware/mac/getup-20261026
~/.venvs/microduck-dyn/bin/python run_batch.py                 # all cases, 10 seeds (3 for stand61-off); about 13 min serial
~/.venvs/microduck-dyn/bin/python getup_sim.py --start face_down --getup recover --seed 0 --hard-max-action 99 --trace
~/.venvs/microduck-walk/bin/python -m unittest test_getup.py   # Brain sequence on synthetic samples (9 tests)
```

Every row of `results.jsonl` carries its exact `cmd`. velstand.onnx is not in git (`*.onnx` is ignored); fetch it with `curl -L -o velstand-v8/velstand.onnx https://huggingface.co/pollen-robotics/microduck-policies/resolve/665ae4eb20bfe13bca1ef4ea6d4bb6b4a096e448/velstand.onnx`. `velstand-v8/manifest.json` is the Hub manifest of that commit.

## walk_brain.py recover mode

- The switch is `walk_brain.GETUP`, set from the environment variable `DUCK_GETUP`: `off` (the default, unchanged behaviour), `nogate` or `recover`. Wi-Fi `main()` also takes `--getup`, and `Brain(..., getup=...)` overrides it. `walk_wired.py` builds the Brain without arguments, so on the robot the environment variable is the switch.
- `recover` works in walk mode only. Sit, ground pick and kick keep their own guards.
- Detection, IDLE only: robotd's predictor (`fall.rs`). All three must hold: gravity z between -0.90 and -0.5, rising, and -0.5 reached within 0.3 s at the present rate (dgz/dt = -(w x g)_z). This is debounced 60 ms on fresh samples. A robot found lying (gravity z >= -0.5 for 0.2 s) starts the sequence too. A robot in the hand (hold authority s < 1) is never a fall.
- LIMP: KP 50, goals follow the measured joints. It ends once |gyro| < 1 rad/s for 0.2 s, or after 1.5 s.
- POSE: linear ramp from the landed pose to the policy default over POSE_S 1.0 s at KP 160.
- RISE: action history cleared, stand61 at zero command whatever the command file says, KP_RL, no tilt gate, graded hold ignored. It ends after 1 s at gravity z < -0.85, and walk mode then carries on with the command in force.
- GAVE_UP: if the duck is not up 5 s after the hand-over, the present pose is held at KP 50. A changed command (mode or velocity) re-arms the sequence. A mode switch ends any phase. Torque is never switched off.

## Risks

- **walk_wired guards.** `walk_wired.py` now relaxes both walk-mode stops only while the recover sequence owns the robot (`brain.getup` set): the tilt stop is skipped and the hard action limit becomes `GETUP_MAX_ACTION` (6.0 rad; sim rises ask 3.2-5.1). Normal walking keeps the 30 deg stop and the 3.0 rad limit, so the trial command needs no `--max-tilt` or `--hard-max-action` flags. `nogate` mode has no sequence state and is a sim-only switch.
- **Servo overload.** Shutdown 52 (D-014) includes the overload bit. A rise holds hip pitch, knees and neck at the stall torque for up to 0.5 s in sim. A failed rise that kept pushing at KP 200 would hold them there for seconds and could trip overload, which turns that servo's torque off until a reboot. GAVE_UP bounds a failed rise to 5 s and then drops to KP 50. The sim's friction is lower than the real servos' (`microduck-servo-deadband`), so real loads may be higher.
- **Supply.** Stand-up current peaks crashed the A7Z on the 20 V 3 A charger (`power` fact). Use the 20 V 5 A charger or the power bank.
- **Saddle geometry.** The saddle is only a point mass in the model, with no collision shape. A face-up roll over a fitted saddle, and the head hitting it during the rise (the head keep-out is not built), are untested. The same goes for the tether cables.
- **Real lying contacts.** Shells, the jaw and the camera on the face meet the floor with collision meshes from the official MJCF, not the as-built U20 face.

## Proposed CURRENT-STATE.json changes (not made here)

- A new fact `getup` with value "recover mode in walk_brain.py (DUCK_GETUP=recover), sim only: stand61 50/50 from face-down, face-up, side, seated and pushed starts on the saddle model at 7.0 V and 4 % drops; not run on the robot", sourced to this README.
- After a robot run: the measured rise time, the worst |action| and the servo hardware-error status from the log.
