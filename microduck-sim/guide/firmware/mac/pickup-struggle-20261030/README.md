# Pickup struggle, 2026-10-30 01:33 (local)

**Cause.** The graded hold did engage when Shawn lifted the duck by the head: the legs went soft and the policy had no authority for about 0.4 s in the air. Then his hand shifted on the head. The grip reading dipped for 0.15 s, the hold handed part of the authority back, and the policy's own leg motion drew 329 mA. `hold.py` reads summed leg current as weight on the feet, so it decided the robot had been set down (`landed`). It then gave walk61 full authority at full gain while the robot was still in the hand. The legs thrashed for 1.45 s until the action limit stopped the policy and switched to the open-loop stand.

**Fix (proposed in `proposed.diff`, not applied).** Once a lift has started, keep the hold until the hand really lets go or the feet are really loaded. Count a landing only from leg current read while the legs are paused, and only after it has lasted 0.1 s.

Evidence is the brain log on the A7Z, `~/duck-logs/duck_wired_log_app1030-040713.jsonl`, with stdout in `duck_wired_app1030-040713.out`. The excerpt here, `log_app1030-040713_0533.jsonl`, covers 18 s (t 1793338396-1793338414) with the fields used below. `replay.py` feeds the logged touch counts and leg currents through `hold.py` and reproduces the logged `s` and `landed` tick for tick. Times below are seconds after t = 1793338402.0 (05:33:22.0 UTC, 01:33:22 EDT).

## 1. The pickup and the state the brain was in

**Before the grip.** The brain was in walk mode at zero command (`{"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0}`). The survey turns at 01:24-01:25 had stepped, so the policy at zero command was walk61, not stand61 (`walk_brain.Brain.stepped`, logged `policy: "walk"`). The command had been zero since 01:25:41, longer than `QUACK_REST_S` (2 s), so `hold_allowed` was true and `hold_on` was true on every tick. Before the grip the robot stood still: tilt 3.6 deg, gyro 0.00 rad/s, |action| <= 0.09, summed leg current 163-182 mA. The grip stop did not latch because the command was already zero (`grip_stop` false).

**The pickup is the only one in the window.** Between 01:16:40 and 01:35:52, 10 s summaries show head-pad coverage above zero only at 01:33:22-01:33:31. The other disturbances in the window are the survey turns, with no hand on the head.

- **+0.46 s:** the first pad rises (coverage 0.07). It reaches 0.46 by +0.94 s, and engagement `e` climbs with GRIP_TAU 0.6 s.
- **+1.08 s:** the estimator sets `airborne`, with `s` 0.49 and load share 0.03. The tilt is still the standing 3.6 deg. It starts changing at +1.3 s and reaches 18 deg by +2.4 s. The lift therefore happened between about +1.0 and +2.0 s; see finding 3 on why the load share cannot time it.
- **+2.26 to +2.59 s, held correctly in the air:** `s` 0.00, `kp_leg` 80, `kp_neck` 500, logged |action| 0.00, leg current 94-117 mA, `e` 0.40-0.43, tilt 11-18 deg, gyro up to 1.8 rad/s. The policy kept running underneath, and its raw action grew from 0.09 to 1.00 rad (left ankle), as expected for a policy whose feet are off the floor.

## 2. What the legs did, and why the hold let go

**The hand shift, +2.59 to +2.73 s.** Pad coverage fell 0.41 -> 0.32 -> 0.22 -> 0.17 and `e` followed it quickly (LETGO_TAU 0.06 s): 0.41 -> 0.37 -> 0.28 -> 0.21. Coverage never fell below GATE_LO (0.1), so a hand was still on the head. The grip gate `(e - 0.1) / 0.3` fell from 1 to 0.37. That cut `h_load` and raised `s` 0.00 -> 0.11 -> 0.53 -> 0.82, with `kp_leg` 80 -> 93 -> 131 -> 179.

**The policy's own motion read as foot load, +2.70 to +2.77 s.** The raw action of about 1 rad, now scaled by `s` 0.5-0.9, moved the legs: the largest goal-minus-position error went from 5 deg to 29 deg and then 53 deg. Leg current rose 96 -> 153 -> 320 -> 329 mA. With the calibration in `~/.duck_hold.json` (air 138 mA, standing 294 mA), 329 mA is a load share of 0.80. That passed LANDED (0.8), so at +2.77 s `landed` became true. From then on `held = h_load = (1 - load) * gate`, which is about 0. `s` reached 1.0 and `kp_leg` 200 by +2.88 s.

**The struggle, +2.77 to +4.22 s.** Walk61 had full authority in the hand. |action| peaked at 2.45 rad (left knee, +3.11 s), 2.88 rad (+3.62 s) and 3.25 rad (head yaw, +4.22 s). Summed leg current peaked at 2769 mA (+3.73 s), gyro reached 8.55 rad/s and tilt ranged 7-25 deg. The tilt stop stayed off, correctly, because `carried` was true with `e` > 0.3.

**The stop, +4.22 s (05:33:26 UTC).** Stdout: `STOP -> stand: policy action over 3.0 rad in 3 of the last 10 ticks (last 3.25)`. The stop wrote `{"mode": "stand"}` to the control file, which is the stand command seen later. In stand mode the hold does not apply (`hold_allowed` needs walk mode), so the robot hung at the open-loop STAND at kp 400. It was stiff but quiet: |action| 0, tilt up to 30 deg, leg current 450-875 mA during the 0.5 s ramp, then 139-238 mA from +4.9 s. The robot was set down at about +8.7 s (tilt back to 2.6 deg) and the hand left at +9.4 s. At 01:35:22 the runner commanded walk mode again.

## 3. Root cause

**Primary.** `HoldEstimator.update` ends a lift on an instantaneous signal and confirms landing with a signal the robot itself produces. A hand that only shifts on the head shrinks the grip gate and returns authority within 0.1 s. Leg current then measures the policy's own effort, so the first legs to move "prove" a landing. That latches `landed` and hands full authority back in the air. The loop reinforces itself: more authority causes more motion, more current, a higher load share and more authority. This is not the policy reacting to unloaded feet while held (it was scaled to 0 then), not a mode switch on lift, and not missing pads: the pads read the hand the whole time, with `touch_age` <= 0.033 s.

**Contributing: the leg-current calibration no longer separates floor from air.** On the floor in this run, summed leg current was 155-185 mA under walk61 at kp 200 and 146-162 mA in the open-loop stand at kp 400. The calibration expects 294 mA standing, so the load share on the floor reads 0.15-0.30. A head grip on the floor therefore already looks like an unloaded robot: `airborne` was set at +1.08 s while the tilt still read the standing 3.6 deg. A real landing at kp 80 (the 263 mA that load 0.8 needs) has never been shown on this robot. Pollen found the same thing on their robot and removed current from their detector's inputs.

**History of the same symptom.** Before the hold existed (10-20 and 10-23), 4 of 5 head lifts struggled. On 10-24 the grip-stop latch cleared on a zero command (shoot.py take 2). On 10-29 a shifted XIAO touch stream left the hold blind (fixed in 75fa414). This is a fourth failure in the same feature, and the first with the hold working as designed. The weak point is the load signal, not the switches around it.

## 4. Pollen's robotd: how it handles being held

Source: pollen-robotics/microduck at 7d866d0 (2026-10-29), `duck-control/src/pickup.rs`, `robotd/src/pickup.rs` and the `[pickup]` section of `deploy/robotd.toml`.

- **Inputs:** one second (50 rows) of gyro, projected gravity, joint positions and velocities, and the previous tick's target with a "was paused" flag. The output is p(held) from an 8k-parameter temporal CNN trained only in simulation. Version 2 (2026-10-03) adds head grips, sustained holds at any orientation and 180 deg turns. Current is in the row layout but the shipped model drops it: in simulation current separated held from standing "far better than it does on a real robot". There is no hand sensor.
- **Decision with hysteresis:** pause after p > 0.8 for 5 ticks (0.1 s). Resume only after p < 0.35 for 4 ticks, and only once the pause is at least 0.3 s old, "so one confident tick cannot flicker it". Their evaluation reports about 1.5 false mid-carry resumes per hour.
- **The pause itself:** the policy's output is replaced by a 0.3 s linear ramp to `PAUSE_POSE` (the walking policy's mean stance at zero command) at the policy gain. Only the walking and standing networks are watched. It is on by default.

**Compared with our hold.** Ours ends a lift as soon as the grip reading dips (a 0.06 s time constant, no minimum pause). Pollen resumes only on sustained evidence after a minimum pause. Ours confirms a landing from current that the robot generates; theirs uses no current at all. Our pause equivalent (s = 0, goal = default stance at kp 80) is close to theirs.

## 5. Proposed fix (smallest change, `hold.py` only)

`proposed.diff` applies cleanly to the current tree (`git apply --check`). It changes `hold.py` and `test_hold.py`; `walk_wired.py` and `walk_brain.py` are unchanged. Two rules:

- **Lift latch.** Once `airborne`, the lift ends only when the hand lets go (`e < GATE_LO`, the existing release path) or a set-down is confirmed. During the lift, `held` is 1 and `h_load` is 1, so `s` targets 0 and the legs stay at KP_LEG_MIN. A hand that shifts or regrips no longer returns authority.
- **Quiet landing.** `landed` needs `load_f > LANDED` for LAND_S = 0.1 s, counted only while the authority `s` <= S_QUIET = 0.1. That way the current comes from the floor pushing on legs that hold the pause pose, not from the policy moving them.

```diff
+LAND_S = 0.1                # s the load share must stay over LANDED, read with the legs paused, to count as set down
+S_QUIET = 0.1               # authority at or below which the leg current is the floor's push, not the policy's motion
...
         if self.e < GATE_LO:
             self.airborne = self.landed = False
+            self.land_s = 0.0
+        elif self.airborne and not self.landed:
+            quiet_load = self.load_f is not None and self.load_f > LANDED and self.s <= S_QUIET
+            self.land_s = self.land_s + dt if quiet_load else 0.0
+            self.landed = self.land_s >= LAND_S
         elif self.h_load > AIRBORNE:
             self.airborne = True
-        elif self.airborne and self.load_f is not None and self.load_f > LANDED:
-            self.landed = True
-        held = self.h_load if self.landed else max(self.a_touch * self.e, self.h_load)
+        lifted = self.airborne and not self.landed
+        if lifted:
+            self.h_load = 1.0  # the legs stay soft and the neck stiff for the whole lift
+        held = 1.0 if lifted else self.h_load if self.landed else max(self.a_touch * self.e, self.h_load)
```

**Desk checks done, robot untouched:**

- **Unit tests:** with the patched `hold.py` and test file, `test_hold` runs 29 of 29 OK. These include the walk_wired integration tests that use the real Brain and policies with a fake servo link. Against the unpatched `hold.py`, the new test `test_a_hand_shifting_on_the_head_in_the_air_keeps_the_hold` fails, so it pins this incident. One existing assertion changes: a set-down with the hand still on now stays at kp 80 for LAND_S plus load smoothing (7 ticks, 0.14 s) before the gain returns, where before the gain followed the first tick of load.
- **Replay of the logged inputs:** the unpatched estimator reproduces the logged `s` and the `landed` latch at +2.77 s. The patched one holds `s` 0.000 and `kp_leg` 80 through the hand shift and the 320-329 mA ticks. It reaches `landed` only at +2.86 s, after the replay has fed it 0.1 s of the 762-2005 mA thrash that the deployed code produced. With the fix, the robot would not have produced that current. In this lift, a hanging robot drew 92-117 mA at kp 80, and 139-238 mA at kp 400 in the open-loop stand once its ramp had settled (from +4.9 s). The 263 mA that load 0.8 needs therefore did not occur for 0.1 s without policy motion. A violent shake was not covered.
- **Expected side effect:** with today's calibration, a set-down with the hand still on the head will probably not confirm a landing, because floor currents seen today were 146-185 mA. The robot would then stand soft (kp 80, default stance) until the hand leaves. After that, `e < GATE_LO` returns authority within about 0.1 s, the release path measured at 0.02-0.09 s on 10-23. The deployed hold already behaves almost the same way on the floor (`s` near 0.2 and kp near 100 under a grip). This is not verified on the robot.

**Not changed:** the stop that sends a held robot into the stiff open-loop STAND. The fix keeps the policy from reaching the action limit while the robot is held, so that path should no longer run during a lift.

## 6. Robot check that would confirm it

Shawn runs it, with the brain restarted on the patched `hold.py`. The restart is the robot session's call, because the pet-mind runner is using the robot now. Log to `--log /tmp/duck_wired_log_holdfix.jsonl`.

1. **Walk61 at zero command (today's case).** Walk mode, a short on-the-spot turn, zero command for over 2 s. Lift by the head, then shift or regrip the hand on the head 3 times over 5 s while tilting about ±20 deg. Set it down with the hand still on, wait 2 s, then let go.
2. **Stand61.** Restart walk mode with no stepping, then repeat step 1.

**Pass (from the log):** from airborne until the hand leaves, `hold_on` true, `hold.s` <= 0.05 and `kp_leg` 80 on every in-air tick, `landed` false in the air, |action| <= 0.1, summed leg current <= 300 mA, and no STOP line in stdout. After the hand leaves, `s` >= 0.95 within 0.1 s, no fall, and the catch |action| <= 1.8 rad (the 10-29 catch peaked at 1.72).

**Also read from the same log:** summed leg current at `s` 0 and kp 80 on the floor (set down, hand on) against in the air. If they differ by less than 20 %, as today's numbers suggest, current cannot confirm a landing. The landing signal should then move to IMU and kinematics, as Pollen's detector does (gravity steady, gyro quiet, joint positions settled), and `legs_stand_ma` in `~/.duck_hold.json` should no longer drive it.
