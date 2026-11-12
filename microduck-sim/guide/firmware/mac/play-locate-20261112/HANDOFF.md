# Handoff: why MicroDuck walks unsteadily on the robot but not in the sim (2026-11-12)

Goal (Shawn): find what makes the real robot fall and wobble more than the sim, put every cause that matters into the
sim, and train with what cannot be removed. "我们仿真不了，就没办法弥合". The deliverable is a walking policy that falls
less on the robot, or a hardware fix, backed by evidence. Analysis alone does not finish it.

Read first: `~/code/robotics/AGENTS.md`, `microduck-sim/CURRENT-STATE.json` (current facts: policy, gains, voltage,
`leg_play`), `microduck-sim/PROJECT-CONTEXT.json`, this folder's `README.md`, and
`microduck-sim/microduck_rl/cmu/finetune/modal/FINETUNE-DELTA.md` (the training runs and results).

## What is known (all on walk61, the deployed policy)

- The robot logs of 11-11 evening and 11-12 00:26 are walk61 after Shawn tightened the loose screws. The robot still
  fell and wobbled in them. Tightening the screws did not close the gap.
- Robot logs: Mac mini `~/duck-walks/raw/duck_wired_log_app1102..app1112-*.jsonl`. Sim replays of the same commands:
  `~/duck-walks/scorecard-auto`. The scorecard counts 36 robot actions where the robot fell and the sim did not, and
  the robot's trunk jitter is about 3 times the sim's (0.59 against 0.19).
- No play in quiet stance (trunk moves at most 0.06 deg with the leg encoders still).
- While walking on the left foot, the trunk pitch the IMU sees differs from the left stance leg's encoder pitch by
  about 10 deg over the stance, with 4-10 deg of stride-to-stride spread. The right foot and the sim show about 3 deg.
  Same in 11-02..06 and 11-11 logs. Weak evidence points at the left ankle-to-foot chain (ankle horn, two-half
  bracket, slip-fit foot, sole).
- Head/neck: Shawn found play between the yellow chassis and the black neck that nothing in the design limits. It
  cannot be tightened away.
- Each modelled effect alone (`gap_sweep.py`, `gap-sweep.json`) reproduces at most 16 % of the robot's falls: head
  play 8 deg 15/93 runs, leg play 4 deg 14/93, soft sole 13/93, foot play 3 deg 11/93. None raises sim jitter above
  0.24. Servo friction x2 raises jitter to 0.38 but fells 49/72 runs the robot walked through. Voltage is not a cause
  (fall rate 9 % at 7.2-7.5 V, 5 % above 8.1 V).
- Training with that play (Kaggle, play-a) and without it (playctl-a) gave the same fall reduction in the play sims
  (63 to 44 and 43 of 465). Both shake more than walk61 in the real-condition suite, so neither went on the robot.
  Training with a few degrees of play adds nothing.

## What is not known (the actual open problem)

About five sixths of the robot's extra falls and most of its extra jitter come from something the sim does not model.
Candidates not yet tested:

1. Structural compliance much larger than 4 deg at the left ankle-to-foot chain. Test: put a compliant hinge (pitch,
   stiffness and damping as free parameters) between the left ankle servo and the foot in the sim, fit it to the
   robot's measured 10 deg stance profile (`stance_profile.py` output `prof-robot-1111.json`), then replay with
   `gap_sweep.py`.
2. The servo model under walking load. 2026-10-17 measurements: trunk gyro 4-6 times sim, broadband 5-25 Hz, servo
   amplitude ratio 0.2-0.45 against sim 0.25-0.75. Test: compare robot and sim spectra of trunk gyro and per-joint
   tracking error in the same replayed walks, and identify which joint carries the excess.
3. Head mass moving on the unconstrained yellow-chassis/black-neck play with more than 8 deg, or with low stiffness
   instead of a free gap.

Each test passes when the sim reproduces most robot falls without felling the 72 robot-up runs, and its jitter
approaches 0.59.

## Tools (this folder)

- `gap_sweep.py`: replays robot commands in the sim under one effect, scored with the scorecard rules.
  `--models DIR --tag T` runs a candidate policy. Exit -6 after the result row is an onnxruntime teardown abort and
  counts as finished.
- `tilt_gap.py`, `stance_profile.py`: IMU tilt minus stance-leg encoder tilt, per foot and per stance phase.
- `run_candidates.sh`, `run_all.sh`, `run_profile.sh`: Mac mini wrappers.
- Real-condition suite: `microduck_rl/cmu/simcheck/sim_suite.py` (on the Mac mini needs
  `PYTHONPATH=~/sims/bam-team`, because the venv's bam lacks `vin_drop_gain`).
- Training: Kaggle free T4s, `microduck_rl/cmu/finetune/kaggle/`. Show Shawn the plan and wait for his nod before
  any run.

## Constraints

- Heavy jobs run on the Mac mini (`ssh mac-mini`). Never parse a log on the A7Z.
- Robot tests: only robot-tested commands (vx 0.25, vtheta 0 or +-0.3). Shawn does not need to be asked before a
  test script is written.
- Push only from main. The team repo is `qilinxiaoxiang/microduck_rl`.
- Do not propose re-walking walk61 to "check the screws": the 11-11 evening and 11-12 logs already are that test.
