# Which postures let the head camera see a person's face (2026-10-29)

Simulation and kinematics only (Mac mini batches, MacBook renders). Nothing ran on the robot, nothing was trained,
no default was changed. The problem is PET_ROBOT_FEATURES section 2, "Look up at a person": the face model needs
an inter-pupil distance (IPD) of at least 10 px and degrades past 15-30 deg of upward pitch.

## Answer

**Best today: stand61 at zero command with the head command at its pitch cap** (`{"head": {"head_pitch": -0.75}}`,
the trained -1.10 delta). The policy lifts the head to -0.73 rad and drops its own neck to -0.27, which puts the
camera's optical axis 30 deg above the horizontal at 0.27 m (top of frame 59 deg). It holds with 2.0 deg of tilt.
It sees a seated owner (face 1.1 m) from 1.0 m with 17.5 px IPD, a crouching person from 0.5 m (31 px), a child from
0.5 m (26 px), and a standing adult (1.6 m) only between 1.0 m (14 px, face seen from 53 deg below) and 2.2 m (the
10 px limit). The stand61 neck command does nothing (the policy sets the neck itself), and the head roll command is
tracked (+0.40 rad reached), which only rolls the picture by 25 deg.

**Best cheap addition: the seat (sitstand61) with the same head command.** Seated, the policy follows the head
command to -0.49 rad with the neck at +0.29 and the trunk 2 deg back: camera at 0.21 m, 47 deg up, top of frame
75 deg. A standing adult's face is in frame from 0.5 m (16 px) and 1.0 m (13 px), a seated owner from 0.3-2.0 m,
with at most 2.2 deg of tilt during the head move. The seat is Pollen's trained resting state and the robot already
sits on command; what is new is a head command of -1.10 delta while seated, which Pollen trained small and slow
(sitlook.json uses -0.3..+0.6) and the robot has only run at those sizes. The cost is a 2 s sit and a marginal
rise (sit-rise-20261029). Walking at 0.25 m/s with `head_pitch -0.75` also reaches 47 deg (walk61 keeps its neck at
+0.14), but a look-up while walking has never run on the robot (the robot-tested head commands while walking pitch
down only, approach.py HEAD_PITCH_WALK).

**Not worth building.** Every open-loop look-up falls backward on the as-built model: even `head_pitch -0.30`
from the D-030 stand at KP 400 falls at 1.8-1.9 s at every calibrated COM offset (the backward margin of that stand
is about 1 mm of COM, and the head is a large share of the mass). The beg (hips back) and the tiptoe (ankles
forward) fall in 1.2-1.4 s. A 6 s entry ramp changes nothing (the falls are static). The only open-loop look-up
that holds leans the whole robot 20 deg forward on the ankles first (7 of 11 with the 2 s ramp, 4 of 11 with 6 s),
standing with no forward margin; the neck-forward head-up pose holds 3 of 11 and 0 of 11 with the slow ramp. Lying
on the back gives the widest view (camera 0.12 m up, 27-89 deg selectable by head pitch, a standing adult in frame
from 0.3-1.0 m) but needs the get-up, which is 50/50 in simulation and has never run on the robot. Yawing the head
sideways and rolling it does not buy elevation: head roll is +-0.31 (policy) or +-0.44 rad (hinge), so at 90 deg of
yaw it gives at most 18-25 deg, while pitch alone already reaches the vertical; the yawed poses also roll the picture
by 60-115 deg. No trunk-pitch command exists: walk61/stand61 carry 6 body-pose slots that walk_brain zero-pads and
that Pollen trained at weight 0 (velocity env); Pollen's velstand env enables standing body roll/pitch control, but
we do not run velstand (getup study: 44/50, not a walk61 replacement).

**Practical rules** (numbers for the 640 x 360 published frame, 63 mm IPD):
- A person who looks at the duck presents a near-frontal face whatever the geometry; the 15-30 deg pitch limit
  bites only when they look straight ahead. Then the face is seen from below by the line-of-sight angle: standing
  adult 53 deg at 1 m and 34 deg at 2 m (never under 30 deg inside the 2.26 m IPD range), seated person 40 deg at
  1 m and 23 deg at 2 m, crouching person 28 deg at 1 m. So: ask the owner to look at the duck, or to crouch.
- Standing adult: back away to 1.0-2.0 m and look up (stand61 head cap), or sit and look up from 0.5-1.0 m.
- Owner on a sofa (face about 1.1 m): 1.0-2.0 m with the stand61 head cap, 0.3-2.0 m seated. The 1.0 m render
  below is this case.
- Child (1.0 m): 0.5-2.0 m with the stand61 head cap. Crouching person (0.8 m): 0.5-2.0 m.
- IPD alone limits the range to 2.26 m on axis (f 359.5 px x 0.063 m / 10 px), less off axis and for the taller
  faces (a standing adult at 2.0 m is at 2.4 m range, 9.4 px: too far).
- The default stand61 head (neck 0.349, head 0.349; camera level, 0.245 m) sees no face closer than 2 m except a
  crouching person at 1 m; the D-030 open-loop stand (neck 0.25) points the camera 6 deg down.

## Camera

U20CAM-720P on the face, plug edge up (D-023), lens centre and axis from the CAD (`u20cam_mount.json`), published
by a7z_cam.py as 640 x 360 (the 1280 x 720 MJPEG shrunk by two and turned upright). `u20cam_intrinsics.json` is the
datasheet default: equidistant fisheye, f = 320 / rad(51) = 359.5 px from the manual's 102 deg horizontal field,
no calibration yet. Vertical half angle 180 / 359.5 rad = 28.7 deg (57.4 deg top to bottom), horizontal 51.0 deg.
`duck_kin.Intrinsics.vfov_deg` reports 53.2 deg, the pinhole formula; the renders use that, so their frame edges
are 2 deg short of the real ones. The brief's "fx 360 on 1280 x 720" is the same lens: on the full frame f would be
719 px, but pet/identity/face.py letterboxes its input to 640 px wide, so a 1280 frame is detected at the same
scale; the IPD numbers here are at the 640 x 360 scale that the published frame and the detector share.

## How each number was produced

- `facegeom.py`: numpy kinematics on `duck_kin.DuckKin()` (as-built chain from duck_kin.json, U20CAM mount).
  From joints q and the trunk gravity gb it gives the camera position in the foot frame, the optical-axis elevation,
  the image roll (angle from image-up to world-up in the image plane; the frame rotation before detection), and for
  a face centre at horizontal distance D and height H whether it projects inside 640 x 360 through the fisheye model,
  its IPD in px (two points 63 mm apart across the line of sight, both projected) and the line-of-sight angle.
- `headsearch.py`: 0.1 rad grid over the four head joints in two boxes (policy: NEUTRAL +- HEAD_RANGE
  1.10/1.10/1.40/0.31 clamped to the hinge ranges; open loop: the hinge ranges, neck -1.571..1.047, head_pitch
  +-1.571, head_yaw +-2.967, head_roll +-0.436), legs at STAND, trunk upright; 123k and 383k forward-looking poses.
  `results/headsearch.json`.
- `collide.py`: the as-built model (plugged manifest) posed with feet flat, mj_forward, contacts between robot hulls
  deeper than 1 mm (hulls: trunk_base, hips, legs, feet, jaw_soft; the neck bodies carry none). `results/collide.json`.
- `sim_batch.py` on the Mac mini (`~/sims/face-view-20261029/rt`, a copy of the bvh-refit-20261029 snapshot with
  today's CURRENT-STATE.json; brain_sim_check.py md5 c9958e60, walk_brain.py dec6855e, evaluate_delay.py 04dbfcda
  as in this repository), every run at 7.0 V and 4 % dropped reads from CURRENT-STATE.json, cmu plugged manifest
  (V1.35 saddle, 6530B, camera lead). Sets `policy_head` (stand61 at zero command, head command through
  brain_sim_check --dance, 14 s, mean pose over 10-14 s, seeds 0-2), `walk_head` (walk61 0.25 m/s for 6 s with
  --head-pitch, window 4-8 s), `sit` (--sit-at 4, --sit-head deltas, 20 s, window 14-20 s, seeds 0-1), `gp`
  (groundpick phase 0.4 held 4 s), `openloop`/`openloop2`/`openloop3`/`openloop4` (stand-gap comsim on
  stand-pose-study stand_sim: walk_brain stand mode, KP 400, start from the measured stand61 pose, 2 s ramp, hold
  to 8 s; COM moved -2.0, -2.5, -3.0 mm as the stand-saddle calibration, seeds 0-2, plus 0.1 m/s pushes each way at
  4 s at -2.5 mm), `lying` (getup_sim face-up placement, KP 50 for 1.5 s, KP 400 for 3 s). The camera numbers of a
  policy run come from the pose the sim reached (mean q and gb over the window), not from the command. Every row in
  `results/<set>.jsonl` carries its command line or arguments; `summarize.py` writes `results/summary.json`.
- Rounds 1-2 of the open-loop set added N(0, 0.03 rad) start noise on all 14 joints; the STAND control then fell
  7 of 11 and held 11 of 11 without it, so that noise is a different stance, not an initial condition. Round 3 (the
  numbers quoted here) starts from the stand61 pose exactly and takes its spread from the COM range, the pushes and
  the read-drop seeds, as stand-saddle-20261026 did. Round 4 repeats four of them with a 6 s entry ramp (see below).
- `render_views.py` (MacBook, one process under sim_host_guard): the model's head_camera moved to the U20CAM mount
  with the pinhole vertical FOV, a person stand-in (box body, sphere head at the face height, eyes 63 mm apart),
  `results/renders/<scene>_camera.png` and `_side.png`; `make_scenes.py` builds the scenes from the reached poses.

## 1. Postures the robot can hold today

Camera numbers from the sim-reached pose; "seen" = inside the frame with IPD >= 10 px; "from below" = line of
sight angle when the person looks straight ahead. Heights: standing adult 1.6 m, seated 1.1 m, child 1.0 m,
crouching 0.8 m.

- **Open-loop stand (D-030, neck 0.25, head 0.349)**, kinematic at the sim rest tilt: camera 0.24 m, axis 6 deg
  down (sim rest pitch 6 deg nose-down adds to it), top edge +23 deg. Highest face centre in frame: 0.45 m at
  0.5 m, 0.67 m at 1 m, 1.09 m at 2 m. Seen: child and crouching at 2 m only. Head at its hinge limits: every head-up
  target falls (section 2).
- **stand61 at zero command, default head**: trunk 3.5 deg back in the sim, camera 0.25 m, axis +3 deg, top +32 deg.
  Highest face 0.56 / 0.87 / 1.5 m at 0.5 / 1 / 2 m. Seen: crouching at 1 m; seated, child, crouching at 2 m.
- **stand61, head command caps** (`policy_head`, 3 seeds each, no fall, tilt 2.0 deg):
  `head_pitch -1.10` delta reaches neck -0.27 / head -0.73: camera 0.27 m, axis +30.0 deg, top +58.6, image roll
  -2 deg. Highest face 1.10 / 1.92 / 3.57 m. Seen: child and crouching at 0.5 m; adult (14.0 px, 53 deg below),
  seated (17.5 px, 40 deg), child, crouching at 1 m; seated, child, crouching at 2 m (adult 9.4 px fails).
  `head_pitch -0.80`: axis +21.9, top +50.6; seen crouching at 0.5 m, seated/child/crouching at 1 m.
  `head_pitch -0.50`: axis +9.9, top +38.5; seen child/crouching at 1 m, seated/child/crouching at 2 m.
  Neck commands +0.40 and -0.30 with head -1.10: the policy returns neck -0.29 and -0.26 either way (axis 29.8 and
  30.0). `head_roll +0.31` with head -1.10: roll reached 0.40, axis 30.4, image roll -24.5 deg (the frame must be
  turned 24.5 deg before detection). `head_yaw -0.80` with roll -0.31 and head -1.10: axis 19.3 deg, view heading
  -77 deg, image roll +33 deg: worse than pitch alone.
- **walk61 at 0.25 m/s with `head_pitch` (absolute, approach.py style)**: -0.75 reaches neck +0.14 / head -0.68,
  axis +46.7 deg, top +75.4, tilt 7.5 deg, no fall, image roll -6 deg. Seen: adult at 0.5 m (16.4 px, 69 deg below)
  and 1 m (13.7 px, 53 deg), seated/child/crouching at 0.3-1 m. -0.40: axis +33.5; -0.15: axis +24.3. Never
  robot-run with the head up.
- **sitstand61 seat** (`sit`, 2 seeds each, no fall): trunk 4.5 deg back with the default head (gb x -0.08), seat
  trunk height 0.059 m, camera 0.19 m, axis +7.0 deg, top +35.7; seen crouching at 1 m, seated/child/crouching at
  2 m. Seated head commands: -0.30 delta reaches head +0.05 (axis +22.3, top +51.0); -0.60 reaches -0.18 (axis
  +33.6, top +62.3, seated adult at 1 m 13.5 px); -1.10 reaches -0.49 with the neck 0.29 and the trunk 1.9 deg back
  (axis +46.6, top +75.3, camera 0.21 m; adult at 0.5 m 15.8 px / 70 deg, at 1 m 13.3 px / 54 deg; seated at 0.5 m
  22.5 px, 1 m 17.0 px, 2 m 10.6 px; seated max tilt 2.2 deg). Neck +0.50 with head -0.60 reaches neck 0.60 / head
  -0.16 with the trunk level (axis +43.8). The seated policy tracks the head command at about 45 %.
- **groundpick61 bow (phase 0.4)**: neck -1.57, camera 0.03 m above the floor, axis -72 deg, trunk 14.6 deg
  forward, tilt 34.6 deg: sees nothing above the floor. Recorded only.
- **Trunk pitch on command**: none. walk61/stand61/kick observe [twist 3, head_pose 4, body_pose 6]; walk_brain.py
  hands zeros in the 6 body slots (np.zeros(6), seepick excepted); microduck_velocity_env_cfg.py keeps body_pose
  tracking at weight 0, so the walking and standing policies never learned to hold a trunk pitch. Pollen's velstand
  env (ENABLE_BODY_CONTROL, standing-only roll/pitch/height) is the trained route to a commanded lean; it is not the
  policy we run.

## 2. Postures the body could do but we do not have

Static holds in the open-loop stand (`openloop3`: 11 runs each: COM -2.0/-2.5/-3.0 mm x seeds 0-2, pushes
+-0.1 m/s at -2.5 mm; 2 s ramp from the stand61 pose, held to 8 s; fall = tilt over 45 deg).

- **STAND control**: 11 of 11 held, rest pitch 6.4 deg nose-down (2.1 deg at -3.0 mm), both pushes held.
- **Head up alone**: `head_pitch -0.30`, -0.45, -0.60, -0.90: 0 of 11 each, every run falls backward at 1.5-1.9 s
  (before the ramp ends), at every COM offset. Kinematic gain if it held: -0.60 gives axis +37 deg, -0.90 +66 deg.
- **Head up with the legs leaned forward** (ankles): -0.60 with ankle -0.10: 0 of 11; -0.90 with ankle -0.10: 0 of
  11; -0.90 with ankle -0.20: 7 of 11 (held at -2.5 and -3.0 mm, fell at -2.0 mm and under the forward push),
  resting 20 deg nose-down with the camera at 0.26 m and the axis +46 deg (top +75): the same view as the seat,
  standing on the toes of its stance with no margin forward. -0.90 with hips -0.15 forward: 0 of 11.
- **Neck stretched forward, head fully up** (neck -0.47, head -1.571; neck -0.97, head -1.571): 3 of 11 (held only
  at -2.0 mm, rest pitch -1.4 deg, axis +64 deg, top +93: a standing adult in frame from 0.3-1.0 m) and 0 of 11.
  With ankle -0.10 added: 0 of 11. Not usable at the calibrated COM.
- **Slow ramp what-if** (`openloop4`, the same poses with a 6 s entry ramp instead of walk_brain's 2 s): STAND 11
  of 11; head -0.30 falls at 4.0-4.1 s and -0.60 at 3.1-3.6 s, i.e. part way through the slower ramp, so the falls
  are static (the COM leaves the support) and not the head's swing; -0.90 with ankle -0.20 holds 4 of 11 (fewer than
  with the 2 s ramp); neck -0.47 / head -1.571 falls 11 of 11 at 5.3-6.9 s. The 3 of 11 above were the fast ramp
  arriving before the slow fall; the pose does not hold.
- **Beg** (hips 0.15 and 0.30 rad back with the head up): 0 of 11 each, falls at 1.2-1.3 s. The trunk lean back
  moves the COM the wrong way; the backward margin is about 1 mm.
- **Tiptoe** (ankles 0.30 forward, head -0.60): 0 of 11, falls at 1.4 s (the model's feet are flat soles; the lean
  that lifts the heel tips the trunk forward then the head swing takes it back).
- **Head roll** (0.436 with head -0.60): 0 of 11, same as the pitch alone; roll adds no elevation while facing
  forward (image roll 25 deg).
- **Yawed-back head** (neck -1.571 forward-down, head_pitch +0.13, yaw -2.967, roll -0.24: the pose from the search
  with the most forward camera at 78 deg elevation): 0 of 11, falls at 1.1 s; collision check clear; image roll
  -113 deg, view heading -54 deg. The head hanging forward and turned round is a different robot.
- **Lying on the back** (`lying`, face-up placement as the get-up study, servos holding): trunk 0.046 m up, camera
  0.12 m, axis +89 deg with the stand head (picture rolled 36 deg: looking at the ceiling), +60 deg with head_pitch
  +1.15 toward the feet (image roll 0: a standing adult in frame from 0.3-1.0 m, seated from 0.3-1.0 m, 15 px at
  0.5 m), +27 deg at head_pitch +1.57. The widest usable view the body can give, at the price of the get-up
  (getup-20261026: stand61 recover 50/50 in sim, never on the robot) and the saddle, board and heatsink taking the
  robot's weight on the floor.

What each would take: the open-loop candidates are keyframes held like the D-030 stand, which the sim rejects at the
calibrated COM (only the 20 deg forward lean on the ankles holds, 7 of 11); a stable look-up stand is a learned pose
(stand61 with a body-pose command, i.e. Pollen's velstand recipe) or a seat, which exists. Lying down needs the
get-up on the robot first.

## Head-chain search (four joints together)

`headsearch.py` scores every 0.1 rad combination of neck_pitch, head_pitch, head_yaw and head_roll by the camera's
optical-axis elevation while the view still points forward or sideways (not past the vertical, not behind).

- Pitch alone reaches the vertical in both boxes: policy box neck +0.40 / head -1.10 deltas give 85.9 deg (camera
  0.25 m); hinge box neck 0.25 / head -1.271 gives 87.1 deg. Both collide with the trunk hull (6-17 mm and 4 mm,
  `results/collide.json`): the head tips back into the saddle. The deepest clear pitch-only look-up is head -1.10
  delta with the neck forward of 0.05 (neck -0.30 delta clear, +0.40 collides) in the policy box, and neck -0.47 /
  head -1.571 (63 deg) in the hinge box.
- With the head yawed 90 deg the roll axis becomes the elevation axis, but head_roll is only +-0.31 (policy, 18 deg)
  or +-0.436 rad (hinge, 25 deg), and head_pitch then turns the view sideways. Best yawed poses: policy box 44 deg
  (neck +0.40, head -1.10, yaw -0.8, roll -0.31; view heading -86 deg, image roll +102 deg), hinge box 80 deg only
  with the neck fully down and the head turned 170 deg back (neck -1.571, yaw -2.967), image roll -65 to -115 deg.
  Shawn's example (neck stretched forward -0.75 delta, yaw +1.40 to the left, roll -0.31): axis +3.3 deg kinematic,
  +1.8 deg in the sim (stand61 reached neck -0.51 / head -0.76 / yaw 1.46 / roll -0.41), view heading +81 deg, image
  roll -2 deg, camera 0.24 m. The neck forward lowers the camera; yaw plus roll does not lift the view.
- Best 2-3 head-chain poses, ranked by elevation that the model also balances and does not collide:
  1. stand61 head -1.10 delta, neck free (policy sets -0.27), roll 0: axis +30 deg, image roll -2 deg, holds.
     Gain over the default head: +27 deg. The policy ignores the neck command, so no head-chain combination
     beats this on stand61.
  2. seated head -1.10 delta: axis +47 deg, image roll +2 deg, holds (tilt 2.2 deg). Gain over plain standing
     pitch: +17 deg.
  3. open-loop neck -0.47 / head -1.571: axis +64 deg, image roll 0, clear of the trunk, holds 3 of 11 with the
     2 s ramp and 0 of 11 with a 6 s ramp. Gain over the stand61 cap: +34 deg, but it does not balance.
  No yawed pose makes the list: the best yawed pose that holds is the policy's 19 deg (image roll +33 deg); the
  78 deg yawed-back pose falls.
- Image rotation: the rolled poses need the frame turned by the listed image roll before detection (face.py has no
  rotation step today); unrolled look-ups need none (|roll| <= 6 deg in every held pose above).

## Renders (`results/renders/`)

Camera view and side view, person stand-in, pinhole 53.2 deg vertical; the red circle marks the computed face
centre.
- `stand61_default_seated_person_1.0m`: seated owner at 1 m, camera level: face above the frame.
- `stand61_hp-1.10_seated_person_1.0m`: the same owner with the head cap: face at the upper middle, 17.5 px.
- `stand61_hp-1.10_adult_0.5m`: standing adult at 0.5 m with the head cap: face above the frame.
- `walk61_hp-0.75_adult_1.0m`: walking look-up, adult at 1 m: in frame, 13.7 px.
- `sit_hp-1.10_adult_0.5m`, `sit_hp-1.10_seated_person_1.0m`: seated look-up: in frame.
- `groundpick_bow_adult_0.5m`: floor only.
- `openloop_nk-0.47_hp-1.571_adult_0.5m`: the neck-forward open-loop look-up (held 3 of 11): in frame, 16 px.
- `lying_hp+0.80_adult_0.5m`: kinematic head pose; the sim-settled head sits 0.1 rad lower (axis 60 vs 39 deg).

## Measured vs estimated

Measured in the as-built sim: stand61 head caps, walk61 look-up, the seat and its head commands, the groundpick bow,
every open-loop candidate, lying on the back, the self-collision of every head candidate. Kinematic only: the
default-head camera numbers (trunk tilt taken from the sim rest), the head-chain search, the face projection
(fisheye datasheet model, no lens calibration, lens centre from the CAD with the entrance pupil assumed 3 mm behind
the lens front), the person heights. Not measured: the real camera's pitch offset on the face (cam_calib.py
--mount), the real stand61 trunk tilt with the head up, and the face model's actual pitch tolerance on the duck's
frames (the 15-30 deg figure is the 2026-10-26 survey's).
