# Layer A2 tracker: measured acceptance (2026-10-30)

Plan: `microduck_rl-grasp/cmu/grasp/PLAN-continuous-vision.md` section 3, A2: an open-vocabulary detector that takes a
word seeds a video tracker that keeps the id across frames (the Helpful DoggyBot recipe, arXiv 2410.00231), on the
Mac mini, consuming the head camera stream. Criteria: 10 fps end to end on the live stream, track age
(t_out - t_cap) under 0.3 s, the id held through a 2 s occlusion.

Everything below was measured on Shawn's Mac mini (Apple M4, 16 GB, macOS 27.0.1, python 3.12 in the uv venv,
torch 2.15.0 with MPS, ultralytics 8.4.193) against the robot standing at home with torque on, camera service
`duck-camera` active, Mac mini to A7Z over Tailscale (ping 5-7 ms). No servo was commanded.

## Result

- Models: **YOLO-World v2 m** (`weights/yolov8m-worldv2.pt`, text prompts through CLIP ViT-B/32) on MPS, seeding
  **BoT-SORT** (ultralytics, `botsort_duck.yaml`: sparse-optical-flow camera motion compensation, no ReID,
  40-frame lost buffer, low thresholds for open-vocabulary scores). Alternatives measured below.
- Live, 60 s, query `wall outlet,cable,orange ball` (what the camera saw at the time; the ball had left the view):
  see "Live stream" for the exact numbers of the final (BoT-SORT) run and of the ByteTrack run before it.
- Occlusion: the id is held through a synthetic 2 s (20-frame) blank over the target on recorded live frames, both
  with a still picture and with the picture swaying 10 and 25 px (a moving head); ByteTrack held it only with the
  still picture, which is why BoT-SORT is the default.
- 10 fps is met: the camera publishes 10 fps and the tracker processes 9.7-9.9 of them over 60 s with zero frames
  skipped (the first 3 warm-up frames are excluded; the few frames received before the model finished loading are
  the difference between "received" and "frames").

## Candidate measurements (detector only, `bench.py`, 96 recorded live frames every 3rd of 298, 640 x 360, imgsz 640)

Queries `orange ball, laundry basket, cardboard box, bucket, person` (person: none in view, correctly 0 everywhere).
"hits" = frames with at least one detection of that word at conf >= 0.05; the orange ball is 8 x 9 px at ~1.3 m.

- YOLO-World v2 **s**, MPS: 17.2 ms p50 / 17.9 p90 (58 fps); orange ball 59/96 (median conf 0.07), basket 94, box 96, bucket 96.
- YOLO-World v2 s, CPU: 37.9 / 38.0 ms (26 fps); same detections.
- YOLO-World v2 **m**, MPS: **31.3 / 32.4 ms (32 fps); orange ball 96/96 (median conf 0.39)**, basket 92, box 96, bucket 96.
- YOLO-World v2 m, CPU: 77.1 / 77.7 ms (13 fps); same detections. CPU alone would still reach 10 fps, with no margin.
- YOLO-World v2 l, MPS: 51.0 / 51.8 ms (20 fps); orange ball 91/96 (0.17), basket 96, box 96, bucket 96.
- YOLOE-11 s (seg, MobileCLIP text prompts), MPS: 20.8 / 21.9 ms (42 fps); orange ball 92/96 (0.13), basket 85, box 1, bucket 78.
- YOLOE-11 m, MPS: 43.9 / 44.8 ms (23 fps); orange ball 91/96 (0.12), basket 78, box 0, bucket 79.
- Florence-2-base (transformers 5.22, `<OPEN_VOCABULARY_DETECTION>`, one generate per query), MPS, 27 frames,
  3 queries: 713 ms per frame (1.4 fps); finds all three in every frame but gives no confidence. Far too slow for
  the 10 fps loop; usable only as a slow seeder, not needed since YOLO-World m already finds the ball.

Chosen: YOLO-World m on MPS. It is the smallest model that sees the 8 px ball in every frame with a usable score,
at 31 ms (46-52 ms measured inside the live loop, where JPEG decode and the tracker share the time budget), which
leaves half the 100 ms frame period free. Files: `runs/bench_live.json`, `runs/bench_live_florence.json` on the Mac mini.

Query words tried on the recorded ruler frames (`camera-calib-20261030/bend-20261030/frames`, 195 frames of the
bent head looking at a pink ruler on the floor): `ruler`, `red ruler`, `pink ruler`, `orange ball`, `basket`,
`laundry basket`, `chair`, `person`, `ball`. YOLO-World s and m find no ruler in the bent-head frames (the ruler is a
blurred strip cut by the right edge, out of focus at 10 cm) and only a 0.04-0.05 "red ruler" on two of the four
`ruler/` shots; `laundry basket` is found (0.13-0.46) in the last 2 s of the sequence when the head is up and the
room is in view. The ruler frames are therefore not a usable detection or occlusion test set; the recorded live
frames (`testdata/live_home`, 298 frames, 30 s, orange ball, bucket, laundry basket, cardboard box in view) are.

## Live stream (`tracker.py --source ssh-a7z`, 60 s each)

Frames travel A7Z -> Mac mini as JPEG (q80) over ssh with their a7z_cam header (`a7z_frames.py`), so t_cap is the
daemon's capture stamp (arrival at the A7Z minus the assumed 0.10 s `a7z_cam.LATENCY_S`), converted to the Mac
mini's clock with the UDP-measured offset (A7Z clock 22-50 ms behind the Mac mini, round trip 5 ms). Age therefore
includes that assumed 0.10 s capture latency. "drops" = frames that arrived while the previous one was still being
processed and were skipped (the tracker always takes the newest frame).

- Run 1, YOLO-World m + ByteTrack, `orange ball` only (the robot had been turned to face a wall; nothing found,
  every line carried empty tracks): 595 frames in 60.08 s = **9.85 fps**, age p50 0.194 / p90 0.232 / max 0.324 s,
  inference p50 45.9 ms, drops 0, received 599.
- Run 2, YOLO-World m + ByteTrack, `wall outlet,cable,orange ball`: 587 frames in 60.08 s = **9.72 fps**, age
  p50 0.199 / **p90 0.236** / max 0.308 s, inference p50 51.2 ms, drops 0, received 599, tracks in 583 of 584 frames,
  `wall outlet` id 1 in 582 frames (a second outlet id 2 in 521).
- Run 3, YOLO-World m + **BoT-SORT** (the default), `wall outlet,cable,orange ball`: 595 frames in 60.1 s =
  **9.85 fps**, age **p50 0.206 / p90 0.247 / max 0.321 s**, inference (detector + tracker with motion compensation)
  p50 57.8 / p90 62.4 / max 67.9 ms, **drops 0**, received 598, tracks in 592 of 592 frames, `wall outlet` id 1 in
  588 frames (the second outlet held id 3 for 454 frames, then id 771 for 105: that one sits at the picture's edge and
  flickers). Files `runs/live60_botsort.json`, `.jsonl`, annotated frames `runs/live60_botsort/`.

Criterion 1 (10 fps end to end): met, 9.7-9.9 processed fps against a 10 fps camera, zero skipped frames.
Criterion 2 (age under 0.3 s): met at p50 and p90 (0.21 / 0.25 s with BoT-SORT); the maximum over 60 s touches
0.31-0.32 s on one or two frames (the ssh pipe's jitter). The budget is: 0.10 s assumed capture latency + ~30 ms
A7Z poll and JPEG encode + ~10 ms transfer + decode + 46-58 ms detector and tracker.

## Occlusion (`occlusion_test.py`, recorded live frames, 20 blank frames = 2 s at 10 fps from frame 100 of 297)

Pass 1 finds the target's dominant id and median box; pass 2 paints a grey block over the box (+12 px) in frames
100-119 and checks the id before equals the id after; "inside" = detections inside the block while blanked (must
be 0, proof the detector really lost it). `--sway A` translates every frame by (A sin, A/2 cos) of a 3 s period,
a stand-in for head motion (up to 5 px per frame at A = 25).

- orange ball (8 x 9 px), still picture, ByteTrack: HELD, id 1 before and after, refound in the first frame after the
  block, 0 inside. BoT-SORT: HELD, id 1.
- orange ball, sway 10 px: ByteTrack ID CHANGED (33 -> 50); **BoT-SORT HELD (id 1)**.
- orange ball, sway 25 px: ByteTrack never confirmed a track at all (every detection id -1; the Kalman/IoU
  association cannot follow an 8 px box moving 5 px per frame); **BoT-SORT HELD (id 1, refound in the first frame after the block, 0 inside)**.
- bucket (78 x 116 px), sway 25 px: ByteTrack ID CHANGED (1 -> 13); **BoT-SORT HELD (id 1)**.
- The bent-head ruler sequence (`testdata/bend_room`, 46 frames) has the laundry basket only in its last 20 frames,
  too short for before + 2 s + after, so it gives no occlusion verdict.

Criterion 3 (id held through a 2 s occlusion): met with BoT-SORT in every case tried; ByteTrack fails as soon as
the picture moves, so it is not the default. Not yet tested: a real occluder on the live stream (nobody was there to
put one in), and a moving target.

## Interface

`track_iface.py`: one JSON line per processed frame, empty `tracks` when nothing is found:
`{"t_cap": float, "frame": int, "tracks": [{"name", "u", "v", "w", "h", "id", "conf"}], "t_out": float}`,
u, v the box centre in continuous 640 x 360 pixel coordinates (duck_kin convention), w, h the box size, id the
tracker id (-1 = a detection the tracker has not confirmed), conf the detector score. Consumers measure age as
t_out - t_cap. Not yet attached: head/neck angles and IMU gravity at capture time (the plan's interface lists them;
they come from the A7Z's brain state, a second source to join on t_cap, left for the layer B work).

## Commands

Deploy (MacBook -> Mac mini, one way; sources are canonical in this directory, weights stay on the Mac mini):

    ~/code/robotics/microduck-sim/guide/firmware/mac/tracker/deploy.sh

First-time environment on the Mac mini (python 3.12 via uv; torch with MPS, ultralytics, CLIP for the text prompts):

    ssh mac-mini 'cd ~/code/robotics/microduck-sim/guide/firmware/mac/tracker && /opt/homebrew/bin/uv sync --python 3.12'
    # optional Florence-2 candidate: ... uv sync --python 3.12 --extra florence
    # weights: ultralytics downloads yolov8m-worldv2.pt into weights/ on first use when run from that directory;
    # the ones measured here: cd weights && ../.venv/bin/python -c "from ultralytics import YOLO; YOLO('yolov8m-worldv2.pt')"

Live tracking (the robot's camera service must be active, `ssh a7z systemctl is-active duck-camera`; the sender
holds the camera the way the app's viewer does and starts the daemon only if nothing runs it):

    ssh mac-mini 'cd ~/code/robotics/microduck-sim/guide/firmware/mac/tracker && .venv/bin/python tracker.py \
        --query "orange ball" --source ssh-a7z --out runs/tracks.jsonl --duration 60 --stats runs/tracks.json'

The acceptance runs above:

    .venv/bin/python tracker.py --query "wall outlet,cable,orange ball" --source ssh-a7z --out runs/live60_botsort.jsonl \
        --quiet --stats runs/live60_botsort.json --duration 60 --report 30 --save-dir runs/live60_botsort --save-every 100
    .venv/bin/python record.py testdata/live_home --duration 30
    .venv/bin/python bench.py testdata/live_home "orange ball,laundry basket,cardboard box,bucket,person" --every 3 \
        --candidates yw-s:mps,yw-s:cpu,yw-m:mps,yw-m:cpu,yw-l:mps,ye-s:mps,ye-m:mps --out runs/bench_live.json
    .venv/bin/python bench.py testdata/live_home "orange ball,laundry basket,bucket" --every 10 --candidates flo-b:mps
    .venv/bin/python occlusion_test.py testdata/live_home "orange ball" --at 100 --tracker botsort_duck.yaml
    .venv/bin/python occlusion_test.py testdata/live_home "orange ball" --at 100 --tracker botsort_duck.yaml --extra "--sway 25"
    .venv/bin/python occlusion_test.py testdata/live_home "bucket" --at 100 --tracker bytetrack_duck.yaml --extra "--sway 25"
    .venv/bin/python probe_detect.py testdata/bend "ruler,red ruler,pink ruler,orange ball" --every 15 --weights weights/yolov8m-worldv2.pt

Recorded frames on the Mac mini: `testdata/bend` (the ruler sequence, copied from
`camera-calib-20261030/bend-20261030/frames`), `testdata/ruler`, `testdata/live_home` (recorded 2026-10-30 01:43
with `record.py`). Results: `runs/*.json`, `runs/*.jsonl`, annotated frames in `runs/live60_*/`.

## Open

- A real occluder and a moving target on the live stream (the synthetic blank and sway stand in for them).
- Age max touches 0.31-0.32 s on single frames over 60 s; p90 is 0.24 s. Sending frames on a UDP socket instead of
  the ssh pipe would remove the pipe's jitter if those single frames matter to layer B.
- Head/neck angles and IMU gravity at t_cap are not in the line yet (layer B joins them from the brain state).
- "ruler" is not a word YOLO-World knows on this camera; the ball, bucket, basket, box and outlet are.
