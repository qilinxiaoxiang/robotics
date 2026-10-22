# MicroDuck head touch and the graded hold: test procedure for 2026-10-22

Final-goal step: none of the four (`PROJECT-CONTEXT.json` `final_goal`). Shawn asked for it on 2026-10-21: lift the duck by
the head without the policy fighting, rebalance at once when the hand leaves, and react to strokes and pats like a pet.

**Acceptance for today:**
1. Every head pad rises at least 5x its resting noise under a fingertip (D-013 revisit condition).
2. Leg current standing and leg current lifted differ by at least 20 %, so "feet unloaded" can be measured.
3. With the hold ON, five lifts by the head: no `STOP ->` line, no hardware error, the legs stay near the standing pose
   in the air, and the robot is back on stand61 and steady within 1 s of the hand leaving, each time.
4. With the hold ON, strokes and pats never lower the authority below the hand-only floor (s >= 0.4) and the robot does
   not tip.
5. Labelled data for the stroke / light pat / hard pat classifier: 10 of each.

## What changed in the code (not on the robot until step 0)

- `walk_wired.py` computes the hold estimate every tick and logs it (`hold`, `legs_ma`, `hold_on`). It only acts while
  `/tmp/duck_hold.json` on the A7Z says `"on": true`, so the first half of today runs exactly as before.
- When on, in walk mode at zero command (stand61 or walk61 at rest): the grip on the head pads and the unloaded feet
  scale the policy's actions toward the default stance (`s`), soften the leg gains (to P 80) and stiffen the neck (to
  P 500); the hand leaving gives the authority back within 0.1 s and a loaded foot restores the leg gain within 0.25 s.
  Feet off the ground without a hand on the head (a fall) changes nothing. Carried with the grip on, the 30 deg tilt
  stop does not fire.
- It refuses to act before the leg currents are calibrated (step 2). After a lift has touched down, only the foot load
  counts until the hand leaves, so a robot set down with the hand still on its head balances on its own at once.
- Simulation (`sim/README.md`, as-built model, stand61): lifted by the head without the hold, the policy flails (actions
  up to 3.1 rad, legs swinging 2 rad, neck at the servo's torque limit) and with a rigid grip the tilt stop locks it in
  STAND and it falls after release, which matches what you see. With the hold: legs still in the air, neck under its
  limit, stable 0.0-0.16 s after release in all four lift runs.
- Why the neck stiffens: hanging from the head puts 0.20 N m on neck_pitch against 0.026 standing (as-built model,
  0.84 kg). That is about 40 % of the XL330's stall torque, and at P 200 the neck would sag roughly 20 deg.

## Step 0: install and start (10 min)

1. Charge or connect the supply. Robot on its side, power up.
2. Mac: `ssh a7z hostname` answers.
3. Mac: `microduck-sim/guide/firmware/a7z/install_teleop.sh`. It must end with `all N files match` and `== done`
   (it now also copies `hold.py` and the walk_wired change with Present Current and the touch pads in the log).
4. Start the brain: `ssh a7z '~/duck-run.sh hold1022a'`. Its first lines must include `touch: pads L1/R1/L2/R2/M on
   /dev/i2c-0` and `hold: off (estimate logged only)`.
5. Put the robot on its feet in the app (stand), then walk at zero command (stand61).
6. Mac, in this folder: `bash hold.sh`. The live view opens in the Terminal: five pad bars, leg current, neck current,
   tilt, the hold estimate. Press each pad once and watch its bar rise before going on.

## Step 1: data, hold OFF (about 25 min, the session program guides each step)

The program shows one step at a time in Chinese. Enter starts a trial, Enter ends it, `n` next step, `b` back,
`x` marks the last trial bad, `q` quits (labels are saved as you go; quitting also switches the hold off so the next
brain start never inherits it).

0. Stand quietly 30 s, nobody touching (resting noise, standing leg current).
1. One fingertip on each pad for 3 s, three times per pad (rise per pad, cross-talk).
2. Hand hovering 1-2 cm above the head for 3 s, three times (does the pad see the hand coming).
3. Grip the head the way you lift it, without lifting, 3 s, five times (which pads a lifting hand covers).
4. Lift slowly by the head 3-4 cm, hold 3 s, set down, five times. This is today's behaviour: say in chat what it did
   (struggle, lock up). The log shows whether "lock up" is the action stop, a hardware error, or neither.
5. Lift by the body (not the head), three times.
6. Strokes front to back x10, light pats x10, hard pats x10.

## Step 2: calibrate and switch the hold ON (5 min)

1. In the program press `c`. It prints the pad thresholds and the standing / lifted leg current. It refuses when the
   two currents are less than 20 % apart; then stop here and send me the printout (acceptance 2 failed, the unload
   signal needs another source).
2. Press `h`. The brain prints `hold: ON, leg load calibrated`.

## Step 3: test the hold (10 min)

1. Repeat step 4 of the program five times (lift by the head). Watch: legs relax and stay near the standing pose,
   no flailing, set it down, let go, it stands on its own.
2. Strokes and pats, three of each: the robot keeps standing; the `s` bar never drops below 0.4.
3. If anything goes wrong, press `h` again: within half a second the brain reads the hold as off and ramps the
   policy's authority back to full over about 0.1 s (never a single jump); then it behaves as in step 1.

## Step 4: pull the data (2 min)

Mac: `bash hold.sh pull`, then `python3 hold_analyze.py data/<log> data/<labels>` prints the report. I read it with you:
acceptance 1-5, the calibration, what "lock up" was, and the first classifier numbers.

## Not today

- Pet reactions (lean into a stroke, flinch from a hard pat, the patience budget): they need the classifier, which
  needs today's labelled data.
- Tiptoe: needs a stance policy with a body-height command (the same policy as final-goal step 3's crouch).
- Lifting by the body has no pads: today it is recorded only, the hold does not act on it.
