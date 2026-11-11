# Universal stand/walk policy: plan (approved 2026-11-11)

Approval: Shawn, 2026-11-11, asked by the coordinator whether this plan and BEND-PLAN.md may run on Kaggle: "两个都跑".
Scope: the run A / run B pair of section 3 with the section 4 reward (`rm_chosen.json`, delta `universal2`), 5000
iterations each, cap 10 h, Kaggle free quota only; no Modal, no paid compute, no MacBook training, nothing deployed.

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
- The incentive audit now passes at every load with the redesigned reward (section 4: runtime command ranges, air
  time 6, tracking 3, upright 0.5, head-pose tracking 1, hip-yaw std 0.15, stance-foot-heading -8; worst degenerate
  ratio 0.797). That reward carries Shawn's toe-out requirement (section 7; speed alone would not remove it) and his
  speed requirement (at least 0.15 m/s on the 0.25 command at every load). The bend with the pack is a separate
  bend-policy fine-tune (`BEND-PLAN.md`; the servos can hold it statically). Head motion and the quack tilt with the
  pack: 0 falls. Launch waits for Shawn's go.
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
Redesign (2026-11-11, `flight_audit.py --jobs universal2 --diag`, Mac mini, 128 envs, 400 steps per case; priced
offline by `reward_design.py`, `out/reward_design.json`). Cases per load (full, batteries out, none): the intended
walker (fq2 with the pack, walk61 composed with stand61 without it), standing still under walk commands, stepping in
place (yaw 0.3 only), and leaning forward / back 0.2 rad at the hip pitch while standing. Rewards do not change the
dynamics, so one deterministic rollout per case gives every term's raw value; the weighted sum reproduces the measured
reward per second within 0.02 for every case.
- Why weight and std changes alone failed: with the training env's command ranges (x ±0.4, y ±0.3, yaw ±1.0) the
  walkers move only 0.05-0.09 m/s along their commands, so standing tracks about as well (track ratio 1.10 full,
  1.11 batteries out). No tracking weight or std in the grid (weight 2-3, std 0.224/0.15/0.10) made the walker win.
- Change 1, command ranges matched to what the runtime sends (robot-tested commands: vx 0.25, yaw 0 or ±0.3): x
  -0.05..0.30, y -0.05..0.05, yaw -0.5..0.5 m/s and rad/s. Now the walker wins tracking at every load (standing's
  track ratio 0.88 full, 0.97 batteries out, 0.91 none), but reward ratios stay 0.81-0.88 (`out/audit2_cmd_*.json`).
- What standing still earns: upright (1.86 walk / 1.67-1.87 stand per s) and head-pose tracking (1.91 / 1.65-1.77)
  pay any upright robot alike; air time (1.23 / 0.08 full) is the only large walk-only term.
- Change 2, the chosen weights (fewest changes among the passing designs that carry Shawn's style and speed terms):
  air time 3 to 6, velocity tracking weight 2 to 3, upright 2 to 0.5, head-pose tracking 2 to 1, walking hip-yaw std
  0.30 to 0.15, new stance-foot-heading cost weight -8 (section 7). Pose weight 1, tracking std 0.224 unchanged.
  Degenerate / intended reward ratio, before (runtime ranges, old weights) and after:
  full: stand 0.833 to 0.742, step in place 0.846 to 0.765, lean forward 0.756 to 0.653, lean back 0.811 to 0.713;
  batteries out: stand 0.842 to 0.758, step 0.849 to 0.780, lean 0.766 / 0.799 to 0.672 / 0.697;
  none: stand 0.813 to 0.689, step 0.878 to 0.797, lean 0.689 / 0.690 to 0.558 / 0.551.
  Every ratio is at most 0.80 and the walker wins tracking in every pair. Step in place without the pack (0.797) is
  the closest; 203 of the 6,480 grid designs pass, 18 with the style terms.
- Risk of the lower upright weight: falls still end the episode (termination), and the acceptance below counts falls,
  so a policy that trades uprightness for air time fails the gate rather than passing it.
- Live confirmation of the chosen design in the env (`rm_chosen.json` through the worker's `reward_mods`,
  `out/audit2_chosen_*.json`, 03:09-03:20): PASS at full, batteries out and none, every ratio equal to the priced one
  to the third decimal.
- The audit also runs at 2048 envs on the training GPU at the start of the run, the size of the earlier gates.
Accepted walking speed on the 0.25 m/s command (`style_probe.sh`, 20 episodes): at least 0.15 m/s at full pack, at
batteries out and without the pack, with 0 falls at the two pack states and at most 1 of 20 without it, and the
toe-out limits of section 7. Today: fq2 0.105 with the pack, walk61 0.090 without it, fq2 0.163 without it (toe-out 18 /
14 deg).
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
Shawn, 2026-11-11, on the cause: "外八那个问题 肯定是没把移动速度考虑进去 如果外八那么走肯定很慢". Facts behind it: command
0.25 m/s; fq2 with the pack walks 0.105, walk61 without the pack 0.090, fq2 without the pack 0.163 while still toeing out
18 / 14 deg; in the training env velocity tracking pays standing slightly more than walking (1.107 against 1.062 per
second), so speed is in the reward but too weak to matter. Section 4 makes the speed incentive real and tests whether
speed alone would remove the toe-out.
Speed alone does not remove it (audit pair without the pack, same commands, runtime ranges, `out/audit2_cmd_none.json`):
the splayed fq2 gait moves faster along the commands than straight-footed walk61 (0.100 against 0.057 m/s) and
earns the same velocity tracking (1.411 against 1.405 per s; with the tracking std tightened to 0.10 the splayed gait
earns more, 0.446 against 0.396 raw). So a stronger speed term pays toe-out at least as well as a straight foot. What
separates them is the posture and the foot: hip-yaw pose 0.325 against 0.764, foot-heading cost 0.063 against 0.012
raw per s (at weight -8: 0.50 against 0.10 per s). The splayed gait's lower total (0.756 of walk61's under the old
weights, 0.706 under the chosen ones) is confounded by its falls on the light robot (63 against 3 in the audit), so
the foot-heading term and the tighter hip-yaw tolerance are both kept; the speed change stays for Shawn's speed
requirement, not as the toe-out fix.
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
  show (0 of 3). The seeing pick first stopped with "repeated name 'jaw' in body": the probe worker is reused across
  episodes and wrapped the visual hook a second time, adding the jaw twice (fixed in `flight_eval.py`, which restores
  the original hook before each episode). Rerun with the pack: fq2 and fs1 in the stand slot both fall 20 of 20 at
  about 2.9 s, beak on the floor (lip 4.3-4.5 cm), tilt up to 92 deg, leg p99 0.54: the same failure as the bend.
  The static check (`BEND-PLAN.md`) shows the servos can hold a floor-reaching bend with the full pack (hip at most
  0.28 N m on groundpick61's path), so this is a policy fine-tune, not a hardware limit.
- Head scan while standing (approach.py's scan, 1 s dwell, head pitch 0.5-1.4, yaw ±0.6, neck down to -0.4, two cycles):
  0 falls for fq2 and fs1 with the pack; trunk pitch excursion 2.6 deg (fq2) and 4.6 (fs1) median; leg p99 0.22-0.25 N
  m; head pitch reached 0.45-1.24, yaw ±0.6, neck down to -0.30 (fq2) / -0.41 (fs1). stand61 without the pack: 2.5 deg.
- Walking with the head down (vx 0.25, head pitch 0.5 and 1.1, approach.py's walking range): fq2 with the pack 0 falls,
  0.105 m/s both, trunk pitch excursion 5.6 / 7.1 deg median (max 10.2), leg p99 0.45-0.46. walk61 without the pack:
  0 falls but at head pitch 1.1 it stops walking (0.000 m/s).
- The quack tilt first did not run: `brain_sim_check.py`'s walking flag is a time window (walk_at to walk_at +
  walk_s), and `quack_head_block` refuses a tilt while walking, so with the default 10 s walk window every quack was
  blocked. With `--walk-s 0` (`style_probe.sh fixq`, `eval/st_head_quack_*.json`) all three tilts run in 20 of 20
  episodes: fq2 and fs1 with the pack 0 falls, head yaw reached 0.25-0.28 rad and roll 0.12-0.13 (commanded at most
  0.25 / 0.18), trunk tilt peak 6.0-6.5 deg; stand61 without the pack 0 falls, peak 0.7 deg.
- No-pack hand-back (18 of 20 falls at 10 s on the 960 g model, 0 of 3 on the default model): swap test
  (`handback_diff.py`, `out/handback_diff.json`, 6 bend episodes each). Only three bodies differ: trunk_base +129 g
  with its COM 13.4 mm further back and up (x -25.4 to -33.5 mm, z 8.0 to 18.6 mm; the D-037 battery backpack, A7Z
  saddle and heatsink, the USB coil, minus the old XL4015 box), neck +6 g, jaw -2 g. Default model 0 of 6 falls, 960 g
  model 4 of 6; default with only the trunk_base swapped 4 of 6; neck or jaw swapped 0 of 6. The trunk_base load is
  the whole cause. The real robot with the backpack (2026-11-06 logs, `robot_handback_scan.py` over
  `guide/firmware/mac/seepick-fall-20261106/`): 5 hand-backs (2 groundpick, 3 seepick), 0 falls, tilt after the
  hand-back at most 7.4 deg. One difference stays untested: the robot hands back to walk mode (walk61 at zero
  command), the probe to stand61. Report only; the runtime is unchanged.
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
