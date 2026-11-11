# Full-flow demo simulation for the final-project office hours (2026-11-11)

One as-built MuJoCo run of the whole story, recorded as a video: the owner calls "Mochi!", the duck glances up at the
owner and quacks, the owner says "Mochi, go find the orange ball", the duck searches, walks to the ball, picks it up
with the learned seeing pick and brings it back to the owner's feet. Final-goal steps 1 to 4 plus the name call, in
one scene. Simulation only; nothing here talks to the robot.

## How it runs

- `../fullflow_sim.py` drives `brain_sim_check.run` through a small hook (`brain_sim_check.STORY`: setup, want,
  after) with the seepick rehearsal's corrected harness: as-built model, plugged manifest, COM -2.25 mm, elliptic cone
  with impratio 10, 4 % read drops, wired guards, servo rail from `microduck-sim/CURRENT-STATE.json` (7.6 V), jaw at
  150 mA (`jaw_grip_current_ma`). Ball: 12 mm, 1 g, friction 0.6, a physical body on the floor from the start.
- Video: a follow camera (1280 x 720, 25 fps, video time = sim time) plus the rendered head camera in the corner, with
  `orange_target.detect`'s box during the search and walk.
- `../fullflow_mux.py` adds the sound: the owner's lines from macOS `say`, one simulator duck chirp for the answer.
- Runs on the Mac mini: `../fullflow_sync.sh run SEED` mirrors the inputs to `~/sims/fullflow-20261111/` there, runs
  one seed and copies the video and events JSON back here.

## What is real and what is scripted

- Real runtime: `walk_brain.Brain` with stand61, walk61 and seepick61; walk_wired's command smoothing, guards and jaw
  path (`jaw_limits`); the pick uses the SeePick camera stand-in with the training noise, delay and drops.
- Scripted: the two voice lines are timed triggers (the name-call spotter and any voice-command parser are not in the
  sim, and no voice command exists on the robot); the head glance copies namecall.py's answer (head only, YAW_CAP
  1.40, LOOK_PITCH 1.1); the walk to the ball and back steers on the sim's true positions (the head camera's detector
  only decides "found" in the search).
- Carry assist: once a pick holds (the harness's own result at the hand-back: pinched, off the floor, lifted over
  1 cm), the ball is pinned between the beak pads with its contacts off until the beak opens at the owner's feet. The
  video says so while it is on.

## Finding: the sim's grip does not survive the hand-back to stand61

Without the assist the ball left the beak within 1.5 s of the hand-back in every run that picked it (seed 0 first
run, seed 2 with the 1.0 s `--sp-blend` trial). Seed 0 traced with `--sp-log`: the ball sat 0.207 m up with both beak
halves pressing (0.32 and 0.27 N) through the whole pick; at the hand-back the neck swung from 0.39 to 0.11 rad and
back within 0.3 s and the ball fell out. The measured jaw opening while holding was 0.01 deg: the 12 mm ball is
pinched at the very tip, where the real robot held its ball at 9.5 deg (2026-11-06). So this sim's hold after the
pick is a tip pinch and says nothing either way about the real carry; carrying the ball while walking has never been
trained or tried on the robot.

## Runs (2026-11-11, final settings, `run_c*.log`, `fullflow_c*.json`)

Four seeds (the seed draws the pick camera's delay, drops and bias). Three of four brought the ball to the owner; picks
held on 3 of 5 attempts.

- **Seed 0, the demo video** (`MicroDuck-fullflow-sim.mp4`, 50 s, local only): walked straight into the window (x
  0.108, y 0.000), picked on the first try (lift 0.198 m), delivered at 43.9 s. No fall, no guard trip.
- **Seed 3** (`MicroDuck-fullflow-sim-retry.mp4`, 80 s, local only): five creeps and back steps left the ball 4.8 cm
  short of the landing spot; the first pick missed, the retry from x 0.107 held; delivered at 75.2 s.
- **Seed 2:** eight creeps, then a pick at y +2.7 cm held; delivered at 65.8 s.
- **Seed 1:** the walk-up overshot (ball at x -0.012, under the feet), the 0.2 m/s back steps did not move the duck,
  the pick at -9.7 cm missed and the ball ended far off; time limit in the second attempt.

Earlier runs on the same day (not kept): with a stop at 0.20 m and creeps from a standstill, walk61 often stepped on
the spot (seed 3: eight 1.5 s bursts, no progress), and every pick that held lost the ball at the hand-back (5 runs).

The creep is the weak part of this scene: from a standstill, short walk61 bursts and back steps move the sim duck
unreliably. The robot's own walk-up (seepick.py) is tuned on the robot and was not copied here.

## Reproduce

```
cd microduck-sim/guide/firmware/mac
./fullflow_sync.sh run 0                        # Mac mini; video + events land in fullflow-20261111/
python3 fullflow_mux.py fullflow-20261111/fullflow_s0.mp4 fullflow-20261111/fullflow_s0.json out.mp4
```
