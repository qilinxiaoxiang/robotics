# Universal stand/walk policy: plan (not launched; waits for Shawn's go)

Goal (Shawn, 2026-11-11): one stand/walk policy for any back load from 0 to about 1 kg, "就像人扛着一个重物和不扛重物都能适应";
the pack stays fitted (FP-R4 in `../REQUIREMENTS.json`), so full pack and pack-with-batteries-out are the states that
matter most. Sim only. Nothing is deployed; the runtime, the A7Z and the team repo are untouched.

## Conclusion first
- The cheapest variant is enough to try: today's 61-input actor unchanged (single frame), the load varied per training
  env with the real pack's mass, COM and inertia, and the load given to the critic only. The runtime needs no change.
- Today's evidence says the start point is fq2 1999. In the per-load probe (`out/payload_probe.json`, Mac mini, 20
  episodes each) it already stands and walks with 0 falls at every load from 25 % of the pack to the full pack and with
  the batteries out. Its only gap is the light robot: without the pack it walks too fast (0.163 m/s on a 0.25 command)
  and falls 2 of 20, where walk61 falls 0 at 0.090 m/s. The universal run has to close that gap without losing the
  with-pack result.
- One Kaggle T4 pair (free, about 6.7 h, one quota session): run A from fq2 1999, run B from walk61. No Modal.
- Not ready to launch yet: the incentive audit fails with the full pack (standing earns 0.821 of walking, gate 0.80;
  section 4), and two new requirements came from Shawn's video review: no toe-out (fq2 walks at 21-22 deg against
  walk61's 4-7, section 7), and the bend falls with the pack in 20 of 20 (a bend-policy job, section 8). Head motion
  with the pack is fine (0 falls).
- Fallback if the universal policy fails the gate: keep two policy sets and let the A7Z pick by pack detection
  (FP-R2). That works in sim today: fq2 1999 for every pack state, stand61/walk61 without the pack.

## 1. What the actor sees, and is that enough to feel the load
Actor input (61 numbers, one frame, no history), the same as walk61/stand61 and the runtime's `walk_brain`:
trunk angular velocity (3), gravity direction from the IMU (3), 14 joint angles, 14 joint velocities, the 14 previous
actions, and the command block (twist 3, head pose 4, body pose 6, zero in walking). It never sees mass or COM.
The load still shows: under KP 200 a heavier trunk makes the joints sag, so (previous action minus joint angle) grows
with load, and the IMU shows the extra lean and slower sway. fq2 1999 proves a single frame carries enough of this: one
policy holds 0.24 to 0.96 kg with no falls. What it does not do yet is change its gait for the light robot.
Literature, cheapest first:
- Base-mass randomisation with a plain proprioceptive actor: legged_gym adds -1 to +1 kg to the base
  (`added_mass_range`, Rudin et al. 2021); Walk These Ways uses -1 to +3 kg (Margolis and Agrawal 2022). Both checked
  on GitHub 2026-11-10. This is variant 1 here.
- Asymmetric actor-critic (Pinto et al. 2017, arXiv 1710.06542, checked 2026-11-11): the critic gets privileged
  simulator state, the actor only what the robot measures. Here the critic gets payload kg and loaded trunk COM (4
  numbers; critic 76 to 80 inputs). The critic is new anyway, so the worker's 100-iteration critic warm-up covers it.
- RMA (Kumar, Fu, Pathak, Malik, RSS 2021, arXiv 2107.04034, checked 2026-11-11): a base policy plus an adaptation
  module that estimates the hidden parameters (payload among them) from recent state-action history. That needs a
  history input, so the runtime would change. Fallback 2 only.

## 2. How the load is varied
Training model: the robot compiled without the pack (`manifests/flightpack-none.json`, 960.5 g, the mass report's
"duck without pack"). Each env then carries a payload on trunk_base built from the real pack parts of the latest sim
snapshot (`sim/out/manifest_pack_nominal.json`, commit d2de61ac: 74 parts, 955.1 g; the two flight batteries 302 g,
the rest 653.1 g). The training snapshot of rounds 1-3 was 1899 g in all; the latest is 1915.6 g. The universal run
and its probes use the latest one.
Each env draws one state at the start of the run:
- full pack, 40 % of envs (0.955 kg);
- pack with the batteries out (charging), 25 % (0.653 kg);
- no pack, 10 % (0);
- the whole pack scaled by s ~ U(0, 1.15), 25 % (0 to 1.10 kg, every part at its own position).
Mass, COM and inertia per state are exact. They are summed as pseudo-inertia matrices, so the "full" state equals the
robot compiled with the full pack: smoke check, mass 1.30744 kg both ways, COM equal to 0.01 mm, largest matrix
difference 3.7e-9 (`out/universal_smoke.json`).
Kept from the existing recipe: the trunk ±5 % mass/inertia scale (now folded into the same event), the per-reset trunk
COM offset with its curriculum up to ±15 mm (applied to the loaded trunk), the head COM offset, pushes, motor gain,
friction, IMU and encoder noise, delay and voltage randomisation, drop_z 0.12-0.15 m, the EMA velocity tracking of
ft3, and fq2's torque hinge (weight -12 above 0.45 N m). Dropped: the pack-only trunk_mass_scale and
trunk_inertia_d ranges, which the explicit payload replaces.
Code: `microduck_rl/cmu/finetune/flight/payload.py` (event, critic term) and the `universal` delta in
`flight_worker.py`. Mac mini smoke (`train/mini_train_smoke.sh run`, 64 envs, CPU): env builds, actor 61 / critic 80
inputs, sampled payloads 0 to 0.988 kg (23 full, 20 batteries out, 7 none, 14 scaled), trunk mass equal to the drawn
value within 1.2e-7 kg after two more resets (no build-up), 2 PPO iterations ran (`logs/universal_smoke.log`).

## 3. Start point, length, where it runs
- Run A: from fq2 1999 (holds every pack state already; must learn the light robot).
- Run B: from walk61 (holds the light robot; must learn the pack). B answers whether starting from the light walker
  gives a calmer no-pack gait; A is the expected winner.
- No payload curriculum at first: fq2 already survives the full range, and walk61 meets the full mix from step 0 as
  round 1's walk61 fine-tunes did. If run B is still falling at every saved checkpoint by 1500 iterations, a curriculum
  (smax from 0.5 to 1.15) is the change for a next round.
- 5000 iterations each, 4096 envs, saves every 250, cap 10 h. On one Kaggle T4 that is about 6.7 h (1000 iterations
  take about 80 min, `microduck_rl/cmu/finetune/kaggle/README.md`). Both runs in one paired session on the two T4s, one
  quota session. Kaggle GPU quota 24.45 of 30 h left at 00:45 (refresh 2026-11-14); the scratch pair still running
  ends about 05:00, then about 20 h are left, and this pair leaves about 13 h.
- Modal is not used for training. Checkpoint probes run on the Mac mini (free).

## 4. Incentive audit and stop rule
Audit in the exact universal env, pinned to one load at a time (`flight_audit.py --jobs universal`, Mac mini CPU,
256 envs, 15 s): with the full pack, fq2 walking against fq2 standing (zero command), fq2 stepping in place and old
walk61; without the pack, walk61 walking against stand61 standing, walk61 stepping in place and fq2. Pass: the walker
wins on reward and on velocity tracking in every pair, and standing earns at most 80 % of walking at both loads (the
ft1-calibrated gate, DECISIONS D-016). Result (2026-11-11 01:29, `out/universal_audit.json`): FAIL, so the recipe
as written is not launched.
- With the full pack, fq2 standing still under walk commands earns 0.821 of fq2 walking (gate 0.80) and slightly more
  velocity-tracking reward (1.107 against 1.062 per second). In the training env fq2 walks only 0.051 m/s along its
  commands, and standing collects 0.80 per second of the posture reward against walking's 0.32; air time (1.25 against
  0.06) is what keeps walking ahead at all. Stepping in place 0.83 (passes, barely).
- Without the pack: standing 0.774, stepping in place 0.90, fq2 on the light robot 0.78; all lose to walk61 walking.
- old walk61 with the pack earns 0.23 (falls 45 per env-minute); it is flagged only because a falling robot's
  tracking term per second is high, not a risk.
- The style term of section 7 would make it worse (it tightens posture while walking), so the next step before any
  launch is one reward change and a re-audit, in this order: velocity tracking weight 2 to 3 (or its std from
  sqrt(0.05) down), then the stance-foot-heading term, each re-audited in this env at every pinned load until standing is
  at most 0.80 of walking and walking wins tracking. The audit then also runs at 2048 envs on the training GPU, the size
  of the earlier gates (this one is 256 envs on CPU).
Stop rule on the task metric, never on total reward: Kaggle is blind until the session ends, so the in-run stops are
the worker's caps and its stepping floor (walk command answered below 0.03 m/s); the reward guard stays off. After the
session every saved checkpoint from 1000 on gets a short probe (walk, 10 episodes, no pack, batteries out, full pack);
the best two per run get the full gate below. A run whose checkpoints fail the no-pack walk at every save after 2500
is not extended.

## 5. Acceptance (the existing probe, policy from the first tick)
Probe: `brain_sim_check.py --volt 7.6 --drop 0.036` through `train/flight_eval.py`, 20 episodes of 20 s per case,
vx 0.25 for 15 s, turns ±0.3 rad/s. All references are rerun on the same machine as the candidate: the same fq2 1999 and
the same manifest gave 5 falls in 20 no-pack walks on Modal and 2 on the Mac mini, so cross-machine counts are not
compared. The universal policy replaces the specialists only if all three hold:
- With the pack (the 14 with-pack cases of `make_suite.py`, 280 episodes, `--stand-s 0`): falls no more than fq2 1999's
  on the same machine (3 of 280 on Modal), nominal walk at least 0.099 m/s (90 % of fq2's 0.110), walk torque p99 at
  most 0.48 N m (fq2 0.462).
- Without the pack, started as the no-pack robot starts today (0.3 s open-loop stand, then the policy; stand, walk,
  turnL, turnR, 80 episodes): 0 falls (stand61/walk61: 0), walk at least 0.082 m/s (90 % of 0.0915) and at most 0.15
  m/s (walk61 0.090 here; fq2's 0.163 counts as the overspeed that falls), turns within 10 % of ±0.3.
- Partial loads: 25 %, 50 %, 75 % of the pack and batteries out, stand and walk, 0 falls each (fq2 1999: 0 at all of
  them), walk at least 0.07 m/s (fq2 with the batteries out: 0.078), hip p99 at most 0.45 N m and at most 1 % of time
  at or above 95 % of 0.538 N m.

## 6. Hip servos under continuous walking, per load (fq2 1999, Mac mini probe, `out/payload_probe.json`)
Numbers are the worst hip servo (yaw, roll or pitch, either leg): median over 20 episodes of its p99 |torque|, its mean
|torque|, and the share of time at or above 95 % of the 0.538 N m clamp, all ticks after 1 s.
- No pack (fq2, today's start): walk p99 0.342, mean 0.117, 0.3 % of time near the limit (walk61: p99 0.193, mean
  0.084, 0 %).
- 0.24 kg (25 %): walk p99 0.312, mean 0.127, 0 %.
- 0.48 kg (50 %): walk p99 0.314, mean 0.135, 0 %.
- 0.65 kg (batteries out): walk p99 0.353, mean 0.141, 0 %.
- 0.72 kg (75 %): walk p99 0.326, mean 0.139, 0 %.
- 0.96 kg (full pack): walk p99 0.345, mean 0.140, 0.01 %; standing mean 0.173 (32 % of the clamp, held continuously).
The hips are not the limit: their p99 stays at 58-66 % of the clamp at every load. The ankles carry the most at full
pack (p99 0.464, 0.18 % of time near the limit). The probe is 15 s of walking; it shows torque, not heat. Mean hip
torque with the pack is about 1.7 times walk61's without it, and standing with the pack holds 0.17 N m on the hips
without pause, so a long walk or a long stand is a servo-temperature question the sim cannot answer.
Today's stand61/walk61 with any pack: hips at the clamp (p99 0.538, 1-41 % of time near the limit) and falls (20 of 20
from 50 % load up; at 25 % walk 3 of 20).

## 7. Style requirement: no toe-out (外八)
Shawn, 2026-11-11, after `video/fq2_1999_walk.mp4`: "训练完成以后走路怎么有点外八 有点难看啊。。。".
Measured (`style_eval.py`, Mac mini, 20 episodes, `out/style_bend_head.json`; stance foot yaw against the trunk heading,
toe-out positive, from the trained start pose):
- walk61 without the pack (the gait he knows): toe-out 7.3 deg left, 4.2 right (p95 9.6 / 5.5); hip yaw -6.1 / +3.2
  deg; hip roll -4.2 / +4.3 (the trained 5 deg inward stance); step width 94 mm; foot roll at touchdown -0.1 / +0.5.
- fq2 1999 with the pack: toe-out 21.3 left, 22.2 right (p95 25.0 / 24.8): about 16 deg more per foot. Hip yaw
  -21.1 / +22.7 deg; hip roll 0.1 / -0.9 (the inward 5 deg is gone); step width 119 mm (+25 mm); feet land rolled 4-9
  deg onto the inner edge (outer edge up).
- Standing with the pack fq2 holds 3.7 / 2.9 deg (stand61 without it: 0 / -1).
- The joint is the hip yaw: in stance the foot's yaw relative to the trunk follows hip yaw one to one (fitted gain
  -0.9 to -1.1), and the hip yaw offset (15-19 deg more than walk61) matches the extra toe-out. Trunk yaw oscillation
  is the same (p95 2.3 deg against walk61's 2.5), so it is not body wobble. The hip roll change widens the stance on
  top of it.
- It came with the pack, not with the torque hinge: fw1 1250 (round 1, no hinge) already walks at 19-20 deg, fw1 3000
  at 18-19, fq1 2499 at 13-20. fq2 keeps it without the pack too (15-18 deg, 0.163 m/s).
What permits it: the only leg-posture term is mjlab's `variable_posture` "pose" reward (weight 1.0,
exp(-mean over the 10 leg joints of (q - default)^2 / std^2)), whose walking std is 0.3 rad (17 deg) for hip yaw, so a
21 deg hip yaw costs at most about a quarter of a 1.0-weight term, while the pack makes the wide splayed stance cheaper
in balance and torque. No term looks at foot heading.
Training requirement: add a stance foot heading term, a cost on (stance foot yaw relative to trunk heading - walk61's
mean)^2 per foot in contact (target 7 deg left, 4 deg right, from the walk61 numbers above), plus the walking hip yaw
std tightened from 0.3 to 0.15 rad. Its weight is set by the incentive audit (the term must not make standing or
falling cheaper than walking at any load), not guessed.
Acceptance: stance toe-out mean within 5 deg of walk61's per foot (at most 12 deg left and 9 deg right), p95 at most
15 deg, step width at most 105 mm, at every load (none, batteries out, full), measured with `style_probe.sh toe`.

## 8. Bending and head motion with the pack
Shawn, 2026-11-11: "另外弯腰那些还能做吗 头部运动那些". Runtime facts: walk mode puts the head command in the policy's 4
head-pose observation slots (neck, head pitch, head yaw, head roll as deltas from the default, eased 0.2 per 50 Hz tick,
`walk_brain.head_target`, ranges ±1.10/±1.10/±1.40/±0.31 rad); the policy itself drives the head joints. fq2 and fs1
were trained with those commands up to the full range (the head_pose curriculum is at its last stage from the start
of every fine-tune). The bend is a different policy: walk_brain switches to groundpick61 (Pollen's, beak closed) or
seepick61 (the pick); the stand slot only holds before and after.
Results (pack fitted, policy from the first tick, 20 episodes each, `out/style_bend_head.json`):
- Bend, groundpick61 to phase 0.33 held 4 s (PICKUP.md's command; the logged pick-pose phase): 20 of 20 falls with the
  pack, all at 2.6 s, 0.6 s into the descent, with fq2 or fs1 in the stand slot. The trunk never pitches forward more than
  14 deg (35-40 deg without the pack); it tips back to 72-79 deg nose-up and falls backward or to the right. Hip pitch
  torque p99 is at the 0.538 N m clamp on both sides. Cause: the 1 kg behind and above the hips needs more hip-pitch
  torque than the servos have to rotate the trunk forward, and groundpick61 never saw the pack. Without the pack
  (today's stand61) the bend reaches the floor (mouth 2.1 cm, tilt 35 deg) and holds; 18 of 20 then fall at 10.0 s, the
  hand-back from the rise to stand61, a gap of the current 960 g robot model that the older default model does not
  show (0 of 3). The seeing pick could not be run with the flight manifests (the probe stops with "repeated name 'jaw' in body"; likely
  its seepick hook adds a jaw the battery-model manifest already brings, not checked further), so the bend result is groundpick61 only.
- Head scan while standing (approach.py's scan, 1 s dwell, head pitch 0.5-1.4, yaw ±0.6, neck down to -0.4, two cycles):
  0 falls for fq2 and fs1 with the pack; trunk pitch excursion 2.6 deg (fq2) and 4.6 (fs1) median; leg p99 0.22-0.25 N
  m; head pitch reached 0.45-1.24, yaw ±0.6, neck down to -0.30 (fq2) / -0.41 (fs1). stand61 without the pack: 2.5 deg.
- Walking with the head down (vx 0.25, head pitch 0.5 and 1.1, approach.py's walking range): fq2 with the pack 0 falls,
  0.105 m/s both, trunk pitch excursion 5.6 / 7.1 deg median (max 10.2), leg p99 0.45-0.46. walk61 without the pack:
  0 falls but at head pitch 1.1 it stops walking (0.000 m/s).
- The quack tilt (`--quack-at`) did not run in this probe (head yaw stayed at 0.01 rad in every case, pack or not);
  not counted.
Training requirement: the universal run cannot fix the bend, since the bend is groundpick61/seepick61. A with-pack bend
needs its own fine-tune of the bend policy on the payload env (`universal` payload event, same states), started from
groundpick61 (and seepick61 for the pick), with hip-pitch torque inside the clamp. Acceptance for it: the PICKUP.md
bend (phase 0.33, 4 s hold, rise) with the pack fitted and with the batteries out, 18 of 20 without a fall through the
hand-back to the stand slot, mouth within 3 cm of the floor, hip pitch p99 at most 0.50 N m. Head motion needs no new
term (0 falls now); the universal acceptance adds the standing scan and the two walking head pitches above at every load,
0 falls each.

## 9. Failure modes and fallbacks
- No-pack gait stays fast and falls (the fq2 gap): raise the no-pack share from 10 % to 20 % in the next round, or
  start from run B's checkpoints.
- With-pack falls rise above fq2's: lower the scaled share, keep full and batteries-out at 65 %.
- The single frame cannot tell light from heavy fast enough after a load change: fallback 2a, a pack-present flag in
  one of the body-pose command slots that are zero in walking (the A7Z already detects the pack, FP-R2; the runtime
  fills the slot); fallback 2b, a short observation history (RMA-style). Both change the runtime, so both need
  Shawn's go first.
- Fallback 3 (works in sim today): two policy sets selected by pack detection, fq2 1999 for every pack state including
  batteries out, stand61/walk61 without the pack.
