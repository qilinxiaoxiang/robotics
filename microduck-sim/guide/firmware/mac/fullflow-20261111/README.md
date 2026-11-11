# Full-flow demo simulation for the final-project office hours (2026-11-11)

One MuJoCo run of the whole story on the robot as it is now, recorded as a video: the owner calls "Mochi!", the duck
glances up at the owner's face and quacks, the owner says "Mochi, go find the orange ball", the duck searches, walks to
the ball, picks it up with the learned seeing pick and brings it back to the owner. Final-goal steps 1 to 4 plus the
name call, in one scene. Simulation only; nothing here talks to the robot.

Second version, same day. The first version ran the retired charger-pack model (`plugged.json`, white saddle, rear
converter box), drew the jaw fixed to the head so the beak stayed shut around the held ball, and stood the duck on the
floor, where its look-up camera does not have a standing adult's face in the picture. Now:

- Model: `microduck_rl/cmu/model/current.json` (`battery-20261104`: battery backpack, orange V1.35 saddle), passed as
  `--manifest current`; the loaders draw the visual layer that matches the mass manifest.
- Jaw: the drawn jaw (`visual.json` piece "jaw") rides on the `passive_mouth` hinge, so it opens with the beak boxes.
- Table: the duck works on a 1.4 x 1.4 m table top (the sim floor), the owner stands on the room floor beside it (eyes
  1.60 m, 0.85 m above the top), 1.21 m from the duck; the run fails if the trunk comes within 0.10 m of an edge.

## How it runs

- `../fullflow_sim.py` drives `brain_sim_check.run` through a small hook (`brain_sim_check.STORY`: setup, want,
  after) with the seepick rehearsal's corrected harness: the current robot (`--manifest current`), COM -2.25 mm, elliptic cone
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

## Runs (2026-11-11, second version, `run_d*.log`, `fullflow_d*.json`)

Four seeds (the seed draws the pick camera's delay, drops and bias). Two of four brought the ball back; every pick that
was tried on the table held (2 of 2).

- **Seed 3, the demo video** (`MicroDuck-fullflow-sim.mp4`, 47 s, local only): one creep, picked on the first try
  (lift 0.201 m), ball back in front of the owner at 42.8 s. No fall, no guard trip.
- **Seed 2** (`MicroDuck-fullflow-sim-seed2.mp4`, 65 s, local only): seven creeps, picked at y +0.2 cm (lift 0.199 m),
  delivered at 60.7 s.
- **Seed 0:** creeps drifted sideways; stopped by the table-edge check at 44.1 s before a pick.
- **Seed 1:** after eight creeps the ball was 0.39 m off; the pick missed; time limit.

The creep is still the weak part: from a standstill, short walk61 bursts and back steps move the sim duck unreliably.
The robot's own walk-up (seepick.py) is tuned on the robot and was not copied here.

Carry assist (shown on the video while on): after a pick that held, the beak goes to 10 deg (the robot held its ball
at 9.5 deg on 2026-11-06) and the ball, contacts off, slides in 0.6 s from the tip to between the pads, until the beak
opens in front of the owner.

## Reproduce

```
cd microduck-sim/guide/firmware/mac
./fullflow_sync.sh run 3                        # Mac mini; video + events land in fullflow-20261111/
python3 fullflow_mux.py fullflow-20261111/fullflow_s3.mp4 fullflow-20261111/fullflow_s3.json out.mp4
```
