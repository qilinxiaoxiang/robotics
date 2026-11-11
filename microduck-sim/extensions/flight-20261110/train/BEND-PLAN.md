# Bend with the pack: fine-tune plan for groundpick61 (approved 2026-11-11)

Approval: Shawn, 2026-11-11, asked by the coordinator whether this plan and UNIVERSAL-PLAN.md may run on Kaggle:
"两个都跑". Scope: groundpick61 first (about 3 h), seepick61 with the same recipe only after the bend passes; Kaggle
free quota only, launched only after the section 5 audit passes and a Mac mini smoke; nothing deployed.

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
0.45 N m, summed over every actuator), so the policy learns to stay inside the clamp; the two mouth costs of
section 5 (delta `bend2`); and the runtime's held crouch (delta `bend3`, `bend_terms.held_phase_command_class`): in
half the envs the phase stops at 0.33 for 4 s once per cycle, then runs on to the rise. Pollen's env never holds (it
passes 0.375-0.425 in 0.2 s), while PICKUP.md and the acceptance below hold phase 0.33 for 4 s, so without it the
accepted command would be a state the fine-tune never trains on. Kept: the existing
domain randomisation of the velocity env (gains, friction, delay, voltage, IMU noise).

## 4. Start checkpoint and compute
Start from groundpick61 (`ckpt/bend_spec/groundpick61.onnx`, Pollen's alpha_ground_pick, sha ffbf5109) loaded into
the actor the way the flight worker loads walk61, with the 100-iteration critic warm-up. seepick61 (same layout) gets
the same recipe for the pick after the bend passes. Kaggle T4 only (free quota), no Modal, no MacBook. One run of
about 3 h first; stopped on the task metrics in section 6, never on total reward.

## 5. Incentive audit before launch (run 2026-11-11; result first, method below)
Result (`microduck_rl/cmu/finetune/flight/bend_audit.py`, Mac mini, 128 envs, 400 steps per behaviour,
`out/bendaudit_base_*.json`): Pollen's ground-pick reward FAILS at every load, even without the pack. Degenerate /
intended reward per second:
- none: stand 1.058, half bend 0.769, stay down 0.895.
- full: stand 1.209, half bend 0.981, stay down 1.072, sit back 0.629.
- batteries out: stand 1.170, half bend 0.988, stay down 1.078, sit back 0.449.
Why: standing collects the return-pose, return-upright and feet terms almost as fully as the bend does (legs 2.19 /
1.97 per s without the pack), while the bend pays action rate (-1.0 against -0.37), the torque hinge (-0.55 against
-0.20) and head contact; the mouth terms it gains (proximity 0.66, orientation 0.59) do not cover that. A robot that
stays down earns more proximity than the bend (1.11 against 0.66). groundpick61 itself falls 13-16 times per
env-minute in this env (the 960 g model's trunk_base load, the same cause as the hand-back falls).
Redesign (`bend_terms.py`, priced offline by `bend_design.py`, `out/bend_design.json`): two windowed costs on the mouth
tip height, weight -240 each: above 3 cm during the low hold (phase 0.33-0.45) and below 18 cm during the standing
rest (phase 0.85-1.0). Every other weight unchanged (delta `bend2`). Priced ratios after: full stand 0.592, half bend
-0.01, stay down 0.154, sit back 0.153; batteries out stand 0.521, half 0.125, stay 0.235, sit back 0.034; none stand
0.440, half 0.073, stay 0.171. 723 of 6,075 grid designs pass; this one has the fewest changes (two) and, among those, the largest margin.
Weaker costs fail: at -160 / -160 standing with the full pack still earns 0.891. The intended bend pays part of the hold
cost itself (groundpick61 reaches the floor only at phase 0.375), so its reward falls from 5.7 to 3.0 per s at full.
Live confirmation in the env (`out/bendaudit_chosen_*.json`, 2026-11-11): PASS at every load with the priced ratios
to the third decimal; the gate is recorded in `out/audit_gate.json` (delta bend2).
The launched delta is bend3 (bend2 plus the held crouch of section 3), re-audited with the hold running
(`out/bendaudit_hold_*.json`; hold check 22-24 % of env-steps at phase 0.33, longest 4.04 s):
- none: stand -1.226, half bend 0.123, stay down 0.337 (intended 7.84 per s);
- full: stand -2.359, half bend 0.274, stay down 0.732, sit back 0.527 (2.97 per s);
- batteries out: stand -1.797, half bend 0.189, stay down 0.618, sit back -0.081 (4.71 per s).
PASS at every load; gate recorded for bend3 (`out/audit_gate.json`), Mac mini 2-iteration smoke passed
(`logs/bend3_smoke.log`: held command built, groundpick61 loaded, 2 PPO iterations in 4.5 s).
Standing pays the hold cost for 4 s more per cycle; staying down comes closer to the gate (0.73) because the intended
bend now spends 4 s of each held cycle low itself.

Method:
Price each candidate behaviour with the bend env's own reward, deterministic, 128 envs, at full / batteries out / no
pack, the way `flight_audit.py` does for the walker:
- intended: groundpick61 following the phase command (descend, hold, rise, rest; 4 s period);
- stand: a stander at zero command that never bends (stand61 without the pack, fq2 with it, since stand61 falls with
  the pack);
- half bend: groundpick61 shown a phase clamped at 0.15;
- stay down: groundpick61 shown a phase clamped at 0.40 (it never rises);
- sit back (pack loads): groundpick61 on the real pack dynamics, today's backward fall.
No policy bends with the pack yet, so at the pack loads the groundpick61 cases run with the payload's weight carried
by an upward force at the payload COM: the motion is the bend the fine-tune should learn and the payload still counts
in every reward. The intended reward is lowered by the static extra torque cost of the same bend (from
`bend_statics.py`, x1.5: -0.005 per s full, -0.001 batteries out); the compensated degenerate cases keep their
too-low torque cost. Both errors favour the degenerate side.
Pass: every degenerate behaviour earns at most 0.80 of the intended per second at every load. The Kaggle launcher
refuses a bend delta without that PASS (`audit_gate.py`).

## 6. Acceptance (sim, 20 episodes per state, `style_probe.sh` bend case)
Two probes: `style_probe.sh bend` on the runtime sim (falls, hand-back, torque p99), and
`microduck_rl/cmu/finetune/flight/bend_accept.py` in the training env (`mini_train_smoke.sh bendaccept`: the same
command, the payload pinned per load, mouth tip height and trunk pitch over the hold, per-actuator p99), since the
runtime probe does not record the mouth.
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
