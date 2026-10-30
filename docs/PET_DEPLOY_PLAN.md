# Pet behaviours on the duck: deployment plan

Problem IDs: `PET_ROBOT_FEATURES.md` sections 2, 3 and 4 (knowing people, memory, initiative). Every piece below exists
off the robot and was verified in sim or on the Mac (`PET_ROBOT_LOG.md`, 2026-10-26 to 10-29); none of it has run on
the robot. This plan moves them onto the duck one at a time, cheapest risk first. Each stage has a visible behaviour,
what is built for it, a robot session Shawn runs, and the numbers that accept or reject it. A stage starts only after
the previous one is accepted, except where it says "parallel". Robot facts come from `microduck-sim/CURRENT-STATE.json`.

Current robot (checked 2026-10-30 03:13 UTC over ssh): brain `walk_wired.py` running on the A7Z in walk mode at zero
command (stand61, upright, gravity z -1.00), the U20CAM daemon `a7z_cam.py` running, touch pads live, three
microphones capturing (CURRENT-STATE `a7z_audio_capture`).

## Stage 1. Looking around (东张西望), head only

- **Behaviour.** The duck stands still and moves only its head: looks left and right, up, nods, pauses, returns to
  centre; a touch on a head pad stops it and gets a nod. An intention every 10-25 s, chosen by Haiku through
  `pet/mind`, never the same sequence twice in a row.
- **Exists.** `pet/mind/runner.py --robot --allow head` (RUNNER.md, session 1). Sim day: 100 intentions, 0 falls,
  0 brain refusals.
- **Built for this stage.** `--save-frames`: every camera frame the runner receives is saved with the brain row
  nearest its capture time (joint angles, head command, IMU quaternion). This makes the robot's first labelled set of
  real head-camera frames with the head pose attached, which stage 2 needs (the detector has never scored a real frame).
- **Robot session (Shawn).** Duck on the floor, upright, app open as the stop; press the app's stand button so the
  control file holds a plain zero-command walk (it holds `"jaw": "open"` now, which the runner refuses); then on the
  MacBook: `pet/.venv/bin/python -m pet.mind.runner --robot --allow head --minutes 10 --cam-hz 1 --save-frames`.
  Touch a head pad two or three times during the session.
- **Accept.** At least 20 intentions in 10 min; 0 falls, 0 guard trips, 0 brain refusals; trunk tilt max under 5 deg
  (sim head-only max 1.3); every pad touch logged and followed by a nod within 1 s; at least 300 saved frames with a
  matching row (row within 0.1 s of the frame).
- **Reject or stop.** Any fall or guard trip ends the session; the runner already stops itself on them.

## Stage 2. Seeing what is around (看见东西)

- **Behaviour.** While it looks around, the duck notices things: at each head pause it names what is in view
  (cup, shoes, chair, person, ball, bag ...). A new thing gets a longer look (head holds, small tilt); a person gets
  a look-up.
- **Exists.** `pet/see/detect.py` (YOLO-World v2 small, prompt bank, HTTP service on the Mac mini, 12 fps CPU; 0
  detections on the 4 real frames so far). `pet/identity` for faces. U20CAM lens and mount calibration
  (commits `b8870fa`, `bee9a70`) to turn a pixel into a direction.
- **To build.** (a) A household prompt bank (about 30 everyday objects plus person) tuned on stage 1's real frames:
  label 60 of them by hand, measure hit rate and false positives per prompt, drop prompts that fire on the duck's
  own body. (b) `SceneAdapter` in `pet/mind/perception.py`: frame -> detector -> percept `see:<label>` with a
  bearing (azimuth, elevation in the body frame from the head joint angles and the camera calibration), only at head
  pauses (motion blur). (c) The runner feeds these percepts to the mind, which already re-plans on salient events;
  `look_at(azimuth, elevation)` primitive for the longer look.
- **Off-robot check.** Replay stage 1's saved frames through the adapter: per-label precision and recall on the 60
  hand-labelled frames, bearing error against the tile-grid calibration points.
- **Robot session.** Three known objects placed around the duck at about 0.5 m (left, front, right), 10 min, head
  only.
- **Accept.** Each placed object reported in at least 2 of its in-view pauses; bearing within 10 deg of the measured
  placement; false labels under 1 per minute; round trip frame -> percept under 0.6 s (the A7Z-to-Mac-mini median was
  0.25 s).

## Stage 3. Remembering what it saw (记住)

- **Behaviour.** The duck keeps a memory of what it has seen and where (from where it stands). Moving or removing an
  object is noticed: it looks at the old spot, finds it empty, holds the look, then looks around for it. After a brain
  restart or the next day it still remembers. Asked "钥匙在哪" (stage 6), it turns its head to where it last saw the
  keys.
- **To build.** `pet/state/sightings.jsonl` (label, time, body heading from the IMU yaw, bearing, confidence,
  thumbnail path) and an object memory that merges repeated sightings into "keys, usually at bearing B, last seen at
  T"; expectation check on every pause (an object expected in view and not detected = `missing:<label>` percept, a
  surprise); the mind prompt gets the few most relevant memories; `pet/learn`'s day log gets the sightings, so the
  night's reflection writes them into the diary.
- **Limit stated now.** Bearings are in the standing duck's frame with IMU yaw for heading; once the duck walks, they
  need localisation (`PET_ROBOT_FEATURES.md` section 5), which is not in this plan.
- **Accept.** In a 15 min robot session with one object moved and one removed after minute 5: both noticed (a
  `missing` percept and a look at the old bearing) within two look-arounds; memory file survives a runner restart and
  the restarted runner reports the remaining objects without re-seeing them first.

## Stage 4. Knowing the owner (认人), parallel with stage 3

- **Behaviour.** When Shawn crouches in front of the duck or sits on the sofa 1-2 m away, the duck looks up at him and
  greets (nod, small quack later); a stranger gets a longer, wary look.
- **Exists.** `pet/identity` (SCRFD + MobileFaceNet, familiarity memory); face-view study: the camera sees a crouching
  adult at 1 m or a seated owner at 1-2 m with the head pitched up in stand61.
- **To build.** Enrol Shawn's face from the duck's own camera (frames from stages 1-2 where he is in view, from below),
  not from the Mac webcam; the stage 2 person detection drives the head up before recognition runs.
- **Accept.** Crouching at 1 m: recognised in at least 8 of 10 approaches; a stranger photo held at 1 m: 0 owner
  matches.

## Stage 5. Turning to its name (叫名字转头)

- **Exists.** `namecall.py` (onset detector, SRP-PHAT direction, `pet/express` take). Measured on the robot: the ears
  hear through their holes since the repair, but below 1.5 kHz all three microphones hear the head cavity.
- **Waits on hardware.** A closed foam ring round each ear microphone port (Shawn), then the snap test: low-band ear
  lag 9-11 samples. Until then only the head-only acknowledgement (`--mute`, any voice) is useful, without a reliable
  direction.
- **Accept.** 8 calls at 1 m from eight directions, head turns toward the caller within 30 deg in at least 6.

## Stage 6. Hearing the owner (听懂话)

- **Exists.** `pet/voice` (listen + SenseVoice + Haiku intent -> `pet/state/inbox/`), runner `--inbox`.
- **To build.** One shared microphone capture on the A7Z so namecall and voice listen at once.
- **Accept.** 10 spoken commands from 1 m (stop, come, look left, where are the keys): correct task in at least 8.

## Stage 7. Walking about (走动), guarded

- **Exists.** RUNNER.md session 2 (`--allow head,walk`: walk, approach_owner, wander, bow; robot-tested speeds only).
- **Accept.** 10 min, Shawn guarding, 0 falls; any fall goes to `fix-reported-failure-first` before a retry.

## Stage 8. Night reflection on a real day

- **Exists.** `pet/learn` reflection ($0.13 per night), runner writes the learn day log.
- **To build.** The night job reads the robot sessions' logs and sightings, writes the diary and rules, and the next
  session's prompt shows them.
- **Accept.** After a day with stages 1-3 running, the next morning's first intentions mention something from the
  diary (an object, a place, the owner's visit).

Sitting and resting (`sit`, `rest`) join only after the evidence-based sit hand-over in `walk_brain.py` is deployed and
passes the three-seat robot test (`guide/firmware/mac/sit-rise-20261029/README.md`).
