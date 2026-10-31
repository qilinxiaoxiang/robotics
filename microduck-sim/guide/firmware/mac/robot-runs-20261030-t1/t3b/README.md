# t3b on the robot (2026-10-30 night, G4 of the t3 plan, Shawn's waiver of the neck-depth and distance lines)

Candidate `models-t3b-best` (fork `cmu/whole/runtime-overlay/models-t3b-best`, run t3b iteration 900; copied to the A7Z
overlay, walk61.onnx sha256 c6e30cd6...). Gates before this: G1 0.239 rad; G2 in the calibrated sim 2.3 / 5.1 action
jumps per s at neck -0.4 / -0.8 with no falls (t2b 11.0 / 11.5, T1 17-21), neck held at -0.25 / -0.44 (60 % of the
command), tilt at -0.8 13-15 deg; G3 drop8 0 of 6, suite walks 10-30 % shorter than walk61. Record in the fork's
`cmu/finetune/modal/FINETUNE-DELTA.md` "Run t3 progress".

## Written before the first robot step

1. **States the change does not cover**: vx 0.1-0.2, lateral and turning commands (the anchor holds walk61's states at
   vx 0 and 0.25-0.30 with any head command; outside that band the reward alone shaped t3b), so every step here stays at
   vx 0.25, vtheta 0. The head outputs on head-command states are shaped only by the head rewards: the robot will bow
   less than t2b did (t2b reached -0.40..-0.48 for -0.4 and -0.58..-0.76 for -0.8 on this robot; t3b is expected near
   -0.25 and -0.45).
2. **Is the sim blind to the failure being tested?** No longer: the calibrated setting (gyro noise 0.25 x leg speed,
   friction 1.4) reproduced the 10/30 robot rows within 2x (walk61 default 2.1 robot / 3.4 sim, t2b neck -0.4 14 / 11,
   T1 17-22 / 17-21) and shows t2b falling in 2 of 6 neck rows where the robot breached the stop rule. Its known miss is
   t2b's default-head row (robot 1.7, sim 5.7), an over-report. This is the first candidate that sim predicts calm.

**Expected**: walk and walk_neck under 5 jumps per s and under 10 deg peak tilt; neck_hold standing near -0.45; speed
below walk61's. **Stop rule**: a fall, walking tilt above 9 deg, or more than 5 jumps per s ends the test.

Before the test the name-call loop (`namecall.py --name mochi --turn --spotter oww ...`, its retry shell) was stopped
on the A7Z because it writes head commands into the control file; the robot-live bridge writers were left running
(phone app untouched during the test). Restart afterwards from `~/rt/microduck-sim/guide/firmware/mac`:
`until ~/.venvs/duck-policy/bin/python namecall.py --name mochi --turn --spotter oww --oww-threshold 0.5 --own-repeat-threshold 0.3; do sleep 10; done`.

## Steps (Shawn at the robot, `t1_robot_test.py`), results filled in as they come
