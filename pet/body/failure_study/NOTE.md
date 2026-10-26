# Joint failure and walk61: what the policy survives today, and the proposed training randomisation

Problem: register section 11, "walking with a failed non-critical joint" (`docs/PET_ROBOT_FEATURES.md`). Final-goal
link: a duck that loses a head servo on the way to an item (step 2) should still get there. Sim only, 2026-10-26.

## Result

walk61 never fell: 0 falls in 130 runs, whichever head or ankle joint was frozen or weak. Three failures make it
walk badly or not at all:

- **Weak neck_pitch** (P gain halved): 8 of 10 runs never started stepping. They stood on the walk command and moved
  1 mm. The neck cannot hold the head up at KP 100: it sags from 0.35 to about 0.09 rad. The policy then sits in a
  standing gait. This is the only head failure the existing policy does not survive.
- **Frozen left ankle**: walks, limping, at 39 % of the healthy distance (0.11-0.17 m against 0.33-0.38 m).
- **Frozen right ankle**: 60 % of the healthy distance.

Every other head failure, frozen or weak, keeps 93-97 % of the healthy distance. The weak ankles keep 81 % (left) and
108 % (right).

`primitives.py` reads this file. A head joint keeps `walk` and `stand` on the card only when the joint is marked
`still_walks` both frozen and weak: at most 1 fall in 10, and at least half the healthy median distance. As of this
run: head_pitch, head_yaw and head_roll keep walking; neck_pitch does not (weak case).

## Numbers (`results.json`, rows with their exact command in `results.jsonl`)

Each line gives falls out of 10, then forward distance over the 4 s walk as median and range, then the ratio to the
healthy median.

- no fault: 0/10, 0.364 m (0.334-0.378)
- neck_pitch frozen: 0/10, 0.341 m (0.335-0.392), 0.94
- neck_pitch weak: 0/10, 0.001 m (0.001-0.292), 0.00. Eight runs at 0.001 m; two walked 0.232 and 0.292 m.
- head_pitch frozen: 0/10, 0.340 m (0.320-0.360), 0.93
- head_pitch weak: 0/10, 0.353 m (0.315-0.375), 0.97
- head_yaw frozen: 0/10, 0.340 m (0.304-0.368), 0.93
- head_yaw weak: 0/10, 0.346 m (0.327-0.373), 0.95
- head_roll frozen: 0/10, 0.346 m (0.288-0.363), 0.95
- head_roll weak: 0/10, 0.349 m (0.296-0.366), 0.96
- left_ankle frozen: 0/10, 0.141 m (0.110-0.172), 0.39
- left_ankle weak: 0/10, 0.296 m (0.244-0.308), 0.81
- right_ankle frozen: 0/10, 0.217 m (0.189-0.239), 0.60
- right_ankle weak: 0/10, 0.393 m (0.369-0.401), 1.08

No run hit walk_wired.py's guards. Median peak trunk tilt was 6.4-8.0 deg in every condition, against 6.7 deg healthy.
Seven runs died in onnxruntime/MuJoCo teardown on the loaded Mac mini (`recursive_mutex lock failed`). Each was rerun
and finished on its second or third attempt. All 130 runs have results.

## Conditions

- Plant: `guide/firmware/mac/brain_sim_check.py`, unchanged. That is `walk_brain.Brain` (the robot's mode logic), BAM
  XL330 actuators, one tick of sensor and action delay, and walk_wired.py's walk guards (`--wired-guards`). The
  as-built model carries the saddle mass manifest (`guide/print/a7z-saddle/balance/manifest-saddle.json`).
- Supply 7.0 V and 4 % dropped servo reads. Both come from `microduck-sim/CURRENT-STATE.json` (`servo_rail_v`,
  `servo_read_drop_fraction`) through `robot_state_check.py --print-sim-args`. The state check flags both facts as
  stale (verified 2026-10-16 and 2026-10-17). The robot was offline on 2026-10-26, so neither was re-measured.
- Run: stand 1 s, stand61 at zero command until 2 s, walk61 at vx 0.25 for 4 s (CURRENT-STATE `walking_policy`),
  zero command for 3 s. Seeds 0-9 change only the dropped-read pattern, so the spread within a condition is narrow.
- Fault models (`walk_fault.py`), present from the first tick:
  - frozen: a 2 mrad-wide MuJoCo joint limit at the joint's stand angle (`walk_brain.STAND`), with its goal pinned
    there. This is a jammed gearbox, or a servo stuck holding its last goal. The policy still reads the stuck angle.
    A check run held the left ankle within 0.448-0.459 rad while walking; healthy, it swings 0.15-0.59 rad.
  - weak: that joint's P gain halved in every mode.
- Fall: trunk tilt over 45 deg or trunk below 0.04 m. Distance: trunk x displacement over the walk window.
- Run on the Mac mini (`Shawns-Mac-mini.local`, 205 s, 8 workers) from a snapshot of the files the run imports and
  loads, in `~/scratch/pet-body-study-20261026`. A test run matched across the two machines: left ankle weak, seed 0
  went 0.291 m there and 0.286 m here. Reproduce: `~/.venvs/microduck-dyn/bin/python pet/body/failure_study/run_study.py`.

Not covered: a joint frozen away from its stand angle; a limp joint (zero torque); the jaw; the hips and knees; turning;
sit and groundpick. The model's head mass and the real neck load decide the weak-neck sag, so the sag needs one robot
measurement: neck P 100, standing, read the neck angle.

## How published work handles the same problem (read 2026-10-26)

- TOLEBI (bipedal humanoid, arXiv 2602.05596, https://arxiv.org/html/2602.05596v1) trains one policy with
  one random leg joint failed:
  - 90 % of environments are faulted, half with joint locking (PD hold at the failure angle) and half with power
    loss (zero torque).
  - Failures start only once the healthy episode length passes 20 s.
  - A GRU status estimator reports each joint's health to the policy.
  - Success under locking rose from 0.08 (baseline) to 0.81. Healthy success fell from 0.99 to 0.96. Masking alone,
    without the curriculum, cut healthy success to 0.52.
- FT-WBC (legged loco-manipulation, arXiv 2606.24466, https://arxiv.org/html/2606.24466) trains on torque weakening:
  - 95 % of episodes are faulted, with all joints of one leg scaled by k from U(0, 0.25).
  - The share of near-complete weakening ramps from 0 to 0.3 over the first 5,000 iterations.
  - Locked joints are a command clip of +-0.05 rad, used mostly for evaluation.
  - Survival under locked faults was 91 %, against 56 % for a baseline without the fault mechanisms.
- Saving the Limping (quadruped, arXiv 2210.00474, https://ar5iv.arxiv.org/html/2210.00474): teacher-student RL with
  joint locking in simulation, transferred to hardware without fine-tuning. A CoRL 2025 contrastive forward-prediction
  method (https://proceedings.mlr.press/v305/fu25b.html) reports zero-shot adaptation to locked joints it never trained
  on.
- RMA (Kumar, Fu, Pathak, Malik, RSS 2021, https://arxiv.org/abs/2107.04034) puts motor strength among the randomised
  extrinsics. An adaptation module infers them from recent state-action history and runs without fine-tuning on the
  A1. The exact ranges are in the paper's appendix, not verified here.
- Cully, Clune, Tarapore, Mouret 2015 (Nature 521:503, "Robots that can adapt like animals") take another route:
  - Before any damage, they build a repertoire of about 13,000 gaits in simulation (MAP-Elites).
  - After damage, Bayesian optimisation tries repertoire gaits on the real robot and finds a working one within about
    two minutes.
  - The policy is not retrained.
- Bongard, Zykov, Lipson 2006 (Science 314:1118) build the body model from the robot's own small motions. That is the
  babbling step in `inspect.py`.

The gap in our recipe: walk61 never saw a failed joint, and its observation carries no joint health. The weak-neck
freeze is the degenerate "stand still" behaviour. The 2026-10-16 ft1 run (`DECISIONS.md`, reward-change rule in
AGENTS.md) showed that it can look like success on total reward.

## Proposed randomisation for the next walking training (not trained; needs Shawn's go and a budget)

Head first, as the register says. The leg joints make a different robot, so they get the alternatives below.

- **Which joints:** neck_pitch, head_pitch, head_yaw, head_roll. Neck_pitch takes half the draws, because it is the
  only one walk61 does not already survive; the other three share the rest.
- **How often:** 30 % of episodes have one faulted joint. That is lower than TOLEBI's 90 %, because healthy walking
  is the everyday case here and TOLEBI lost healthy success when faults dominated. Faults switch on once healthy
  tracking has converged: the healthy velocity-tracking error stays under its threshold for N iterations. The rate
  ramps from 0 to 0.3 over the first few thousand iterations, as in FT-WBC.
- **Failure modes,** each drawn per faulted episode:
  - weak, 40 %: P gain and torque limit both scaled by U(0.25, 0.75). This covers the weak-neck freeze.
  - frozen, 40 %: locked at an angle drawn within +-0.3 rad of the default, or at the angle where the fault starts.
  - limp, 20 %: zero torque (power loss).
- **Onset:** at a uniformly random time in the episode, so the policy learns the transition.
- **What the policy sees:** first try implicit, with no new input. The stuck angle and the gain loss show in the joint
  positions and the action history the policy already reads (the CoRL 2025 result suggests this can be enough). If
  that does not close the weak-neck case, add four head-health bits from `health.py` (the TOLEBI pattern). That
  changes the 61-input layout, so walk61's runtime would need a matching brain change.
- **Reward:** unchanged velocity tracking. The fault draw must be registered as a delta (`DELTAS`) and pass the existing launch gate
  (`finetune.py::audit`: standing must earn at most the audited share of walking's reward, now also with a weak neck).
  The existing tracking guard stops and selects the run; total reward never does (`DECISIONS.md`, after ft1).
- **Acceptance:** rerun this study on the new policy, same seeds:
  - weak neck_pitch still walks: at least 50 % of the healthy distance, at most 1 fall in 10;
  - healthy distance at least 95 % of walk61's 0.364 m;
  - no condition falls more than now.
  The robot test after that needs Shawn present.

### Leg joints: alternatives to randomisation

- **RMA-style extrinsics** (Kumar 2021): randomise per-joint motor strength and one locked leg joint in the same
  training run. An adaptation module infers them from about 50 steps of history. It covers the ankle limp and a weak
  knee. It costs a teacher-student training run, and the duck's legs carry far less margin than the A1's.
- **Repertoire plus trial and error** (Cully 2015): no retraining. Offline, build a small repertoire in the sim of the
  commands walk61 accepts plus stance offsets: vx, vtheta, yaw trim, the hip-pitch and ankle bias of the stand pose.
  Score each entry with one leg joint locked or weak. On the robot, when `health.py` reports a leg fault, try
  repertoire entries for a few seconds each and pick the one that moves forward without tilting. The frozen ankles
  here (39 % and 60 % distance, no falls) suggest a working gait for one locked ankle may already exist in that
  space. A sweep over vx and stance offsets with the ankle locked would answer it cheaply.
- Recommendation: head randomisation in the next walking run. Cully-style trial and error for the legs, because it
  needs no training and reuses this harness. RMA only if leg damage tolerance becomes a goal of its own.
