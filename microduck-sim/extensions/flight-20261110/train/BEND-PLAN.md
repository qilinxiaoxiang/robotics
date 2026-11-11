# Bend with the pack: fine-tune plan for groundpick61 (not launched; waits for Shawn's go)

Goal (Shawn, 2026-11-11: "另外弯腰那些还能做吗"): the PICKUP.md bend (groundpick phase 0.33, 4 s hold, rise, hand-back to
the stand slot) works with the pack fitted, with the batteries out and without the pack. Sim only; nothing is deployed.

## Conclusion first
- The servos can hold a bend that reaches the floor with the full pack. The 20/20 falls are a policy problem:
  groundpick61 never saw the pack and drives the hip into the 0.538 N m clamp while the trunk tips back.
- Static check (`bend_statics.py`, `out/bend_statics.json`): along groundpick61's own no-pack path, the hip pitch
  needs at most 0.28 N m with the full pack and 0.22 with the batteries out; the knee is the highest joint (0.51 / 0.42).
  A straighter-knee bend needs only 0.19 at the hip and 0.24 at the knee with the full pack.
- The fix is a fine-tune of groundpick61 (and seepick61 for the pick) on the payload env, Kaggle only, after the
  bend incentive audit below passes.

## 1. Static torque feasibility (done)
Method: one no-pack groundpick61 episode traced in sim (206 poses, `logs/bend_trace.json`). Each pose is placed with
both soles flat on the floor and the lowest sole point at z = 0; the robot is the full flight-pack model
(`manifests/flightpack-load100.json`, 1.916 kg), the batteries-out model or the no-pack model (960 g). Torque at
each pitch joint is the gravity moment of everything above it, the upper-body load split between the legs by the
lever rule from the COM's position between the soles; neck and head joints carry their own subtrees. Gates: mouth
0-3 cm above the floor, COM inside the support by at least 5 mm, trunk pitch 0-75 deg, no part below the floor.
These are static lower bounds: no inertia, no servo deadband, no contact pushes.

Groundpick61's own path, largest |torque| over the whole bend, left / right (N m; clamp 0.538, target 0.50):
- full pack: hip pitch 0.283 / 0.239, knee 0.457 / 0.507, ankle 0.360 / 0.354, neck 0.237.
- batteries out: hip 0.224 / 0.189, knee 0.336 / 0.416, ankle 0.303 / 0.291.
- no pack: hip 0.202, knee 0.304, ankle 0.186.
At the lowest mouth point (t 4.36 s, mouth 2.3 cm, trunk 34.5 deg, COM margin 10 mm) the full-pack hip needs 0.28.

Alternative bend shape, straighter knee (hip -1.44, knee 0.14, ankle 1.03 rad; trunk 32 deg, mouth 2.9 cm, COM
margin about 9 mm): full pack hip 0.19, knee 0.24, ankle 0.09; batteries out 0.15 / 0.19 / 0.09. Searched over hip,
knee, ankle, neck and head pitch: 1280 bend-like full-pack poses pass every gate with the hip under 0.50, 1065 of
them with every leg joint under 0.50; with the batteries out 1312 have every leg joint under 0.50.

Hardware variants (same method):
- Batteries forward or down: the room in the pack shell is about 1 mm each way (`battery_room.py`,
  `out/battery_room.json`): forward is blocked by the head-scan and random-head poses, down by the leg swing. So
  effectively zero. Even if room were made, forward makes the bend worse (knee 0.535 / 0.561 / 0.588 at 20 / 40 /
  60 mm), and 30 mm down gives hip 0.259, knee 0.496.
- One battery (left side only): hip 0.27 / 0.19, knee 0.44 / 0.42; the best bend shape's worst joint 0.22.
Answer for the battery order: yes, a bend reaching the floor is statically inside the hip limit at full pack and
batteries out; no battery move is needed for it.

## 2. What the bend policy sees
The actor is groundpick61's: 61 inputs, one frame (trunk angular velocity 3, gravity 3, 14 joint angles, 14 joint
velocities, 14 previous actions, command block with [cos 2 pi phase, sin 2 pi phase, 0] in the twist slots). It does
not see the load. The critic gets the payload kg and the loaded trunk COM (the universal run's 4 privileged numbers).
No runtime change: walk_brain's groundpick mode sends the same command.

## 3. Payload states and environment
Task `Mjlab-GroundPick-Flat-MicroDuck` (`microduck_rl/src/mjlab_microduck/tasks/microduck_ground_pick_env_cfg.py`,
Pollen's rewards: mouth proximity, mouth orientation, feet grounded and flat, return pose, return upright, head impact),
on the no-pack 960 g model with the universal payload event (`microduck_rl/cmu/finetune/flight/payload.py`):
full pack 40 %, batteries out 25 %, no pack 10 %, scaled pack U(0, 1.15) 25 %. Added: fq2's torque hinge (-12 above
0.45 N m) on the hip, knee and ankle pitch, so the policy learns to stay inside the clamp. Kept: the existing
domain randomisation of the velocity env (gains, friction, delay, voltage, IMU noise).

## 4. Start checkpoint and compute
Start from groundpick61 (`ckpt/bend_spec/groundpick61.onnx`, Pollen's alpha_ground_pick, sha ffbf5109) loaded into
the actor the way the flight worker loads walk61, with the 100-iteration critic warm-up. seepick61 (same layout) gets
the same recipe for the pick after the bend passes. Kaggle T4 only (free quota), no Modal, no MacBook. One run of
about 3 h first; stopped on the task metrics in section 6, never on total reward.

## 5. Incentive audit before launch (to run; launch only if it passes)
Price each candidate behaviour with the bend env's own reward, deterministic, 128 envs, at full / batteries out / no
pack, the way `flight_audit.py` does for the walker:
- intended: groundpick61 without the pack (it reaches the floor and rises, so its rollout is the target behaviour);
- stand still: stand61 held at every phase (no bend);
- half bend: groundpick61 with the phase command clamped at 0.15 (never reaches the floor);
- sit back: the trunk-back fall path that groundpick61 takes with the pack;
- reach and stay: phase 0.33 held through the return window (never rises).
Pass: every degenerate behaviour earns at most 0.80 of the intended per second at every load. If "reach and stay"
or "stand still" earns more, the return and proximity weights are rebalanced before launch.

## 6. Acceptance (sim, 20 episodes per state, `style_probe.sh` bend case)
- PICKUP.md bend: phase 0.33 held 4 s, then rise and hand-back to the stand slot (fq2 or the universal stander);
  18 of 20 without a fall at full pack, batteries out and no pack.
- Mouth within 3 cm of the floor at the hold; trunk pitch 25-45 deg.
- Hip pitch torque p99 at most 0.50 N m, knee and ankle p99 at most 0.50.
- No regression without the pack: the hand-back gap of today's 960 g model (18 of 20 falls at 10 s) is checked
  separately (`handback_diff.py`), since it is in the stand slot, not the bend.
- The seeing pick (seepick61) with the pack today: fq2 and fs1 in the stand slot both fall 20 of 20 at about 2.9 s,
  the beak on the floor (lip 4.3-4.5 cm), tilt up to 92 deg, leg p99 0.54 (`eval/st_bend_sp_fq2_pack.json`,
  `eval/st_bend_sp_fs1_pack.json`): the same failure as the bend, so the same fine-tune covers it. Without the pack
  (stand61) the seeing pick falls 1 of 20 (at 7.2 s; `eval/st_bend_sp_spec_none.json`), the baseline to keep.
- Hand-back cause (`out/handback_diff.json`): the trunk_base load of today's model (+129 g, COM 13 mm back and up)
  alone turns 0 of 6 falls into 4 of 6; the real robot with the backpack handed back 5 of 5 without a fall on
  2026-11-06 (it hands back to walk61 at zero command, the probe to stand61).
