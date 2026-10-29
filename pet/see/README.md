# pet/see: open-vocabulary object detector for the pickup chain

Problem: step 1 of the fetch goal (`docs/PET_ROBOT_FEATURES.md` section 7, PROJECT-CONTEXT `final_goal`) finds the
object with an HSV threshold (`microduck-sim/guide/firmware/mac/orange_target.py`, hue 5-22), so the duck generalises
to one colour. `pet/see/detect.py` replaces that with a text-prompted detector that returns the same dict
`orange_target.detect` returns, so `approach.py` and `seepick.py` keep their geometry (`project`, `measure`) and
only the injected `detect` function changes. "Bring me the orange block" becomes "bring me the keys".

## What was chosen and why

**YOLO-World v2 small (`yolov8s-worldv2`, ultralytics) with its CLIP ViT-B/32 text tower**, run on the Mac mini as an
HTTP service; the A7Z sends JPEG frames and gets boxes back. It is the only one of the three candidates that meets the
2 fps budget on a CPU: 12.4 fps on the Mac mini (M4, 10 cores, 16 GB), 13.8 fps on the MacBook (M1 Pro). OWLv2 base
and Grounding DINO tiny are 20 to 50 times slower on the same CPUs (0.2 to 0.6 fps) and need 0.6 to 0.7 GB of weights
each; OWLv2 has the better precision on the orange part (no false positives in the measured subset) and is the model
to revisit if a GPU (Modal, or MPS on the Mac mini) enters the loop.

Measured 2026-10-29 (`out/bench_*.json`; one process per model, torch CPU, 640 x 360 frames, median of the per-frame
calls after one warm-up call; the Mac mini numbers were taken with load average 6-10 from other jobs, so they are
upper bounds):

- YOLO-World v2 s, Mac mini CPU: load 0.3 s, first call 1.1 s, median 80.7 ms (12.4 fps), p90 237 ms, RSS 270 MB
  after load, 489 MB peak. Pinned to 4 threads: 157 ms (6.4 fps). Weights 25 MB plus the 124 MB CLIP text tower
  (or the 28 KB prompt bank, see below).
- YOLO-World v2 s, MacBook CPU (load average 11): median 72.8 ms (13.8 fps), p90 121 ms, RSS 319 MB after load,
  462 MB peak.
- OWLv2 base patch16 ensemble, MacBook CPU: load 7.8 s, first call 7.2 s, median 1767 ms (0.57 fps), p90 2141 ms,
  RSS 413 MB after load, 959 MB peak, weights 593 MB. Mac mini, architecture only (random weights, the disk had
  no room for the file): median 2407 ms (0.42 fps), RSS 902 MB after load, 1.3 GB peak.
- Grounding DINO tiny, MacBook CPU (load average 16-78 from other work, so pessimistic; the quiet smoke test gave
  3.2 s): load 7.7 s, first call 7.2 s, median 3842 ms (0.26 fps), p90 8371 ms, RSS 399 MB after load, 2.5 GB peak,
  weights 658 MB. Mac mini, architecture only: median 4141 ms (0.24 fps), RSS 849 MB after load, 2.8 GB peak.

Quality on the evidence frames (`out/frames/`, 25 frames: 4 real head-camera snapshots and 21 synthetic frames made
by pasting cut-outs of Shawn's own photos and three drawn objects onto the real floor frame; `synth.py` documents
every source and `manifest.json` carries the kind, the pasted boxes and the own-body masks). One prompt at a time,
as the pickup chain runs it; a hit is IoU >= 0.3 with the pasted box; the horizon row is 60 (the shoes and the bin
top in the real floor frame are above it):

- YOLO-World (conf 0.10, with the prompt synonyms below): hit rate 0.62 over 21 positives (13 hits, 1 wrong box,
  7 misses), 6 false positives over 104 negative frame-prompt pairs (0.058), 1 of them on the duck's own foot.
  Per object: orange printed part 8/11 (the misses are the two smallest pastes, 22-40 px, and the ankle part with the
  yellow sole), small ball 3/3, remote control 2/3, drawn keys 0/3 (the drawing is too crude to count against the
  model), bucket 0/1 with 3 false positives on the orange part ("bucket" is what CLIP calls the orange hip cover).
  The 4 real frames (floor, table with the cable, sleeve, blurred duck parts) produced no detection for any of the
  five prompts, i.e. no false positives on real pixels.
- OWLv2 (conf 0.15, every second synthetic frame): hit rate 0.67 over 9 positives (orange part 3/5, ball 1/1,
  remote 2/2, bucket 0/1), 0 false positives over 66 negatives, 0 on the duck's parts.
- Grounding DINO (conf 0.30, same subset): hit rate 1.0 over 9 positives but 46 false positives over 66 negatives
  (0.70), 11 of them on the duck's own feet; it boxes something for most prompts on most frames (the whole table as
  "remote control" at 0.51 on the real table frame). Recall without precision is useless to a controller that walks
  toward the first accepted box.

Prompt wording matters more than the model (`out/prompt_study_yolo-world.json`, conf 0.02, 11 orange-part frames
against 7 object-free frames): "orange block", "orange plastic part", "orange piece", "orange 3d printed part" and
"orange" score 0.00 on the printed part; "orange toy" scores median 0.24 (min 0.10) with at most 0.10 on the duck's
own feet; "orange object" 0.09. `detect.SYNONYMS` therefore expands "orange block" to "orange block | orange toy |
orange object" and reports the label the caller used. Any prompt can carry its own alternatives with "|".

The duck's own orange parts: `approach.project` drops anything that lands under the body (x < 0.03 m) and
`below_horizon` drops boxes that reach above the horizon; both still apply because the detector returns the same
bbox. On top of that `OpenVocabDetector` / `DetectorClient` take `body_mask` (reject boxes that lie mostly in the
mask) and `negatives` (prompts such as "robot foot" whose hits are dropped; the matcher then has a better name for
the feet than the object's). In the measured set the feet produced 1 own-part false positive out of 14 feet-in-view
negatives with "orange block" and none with the other prompts; the pass with `--negatives "robot foot"` gave the
same counts (`out/bench_xiangzhengdeMacBook-Pro_yolo-world_negatives.json`).

Evidence pictures: `out/sheet_yolo-world.jpg`, `out/sheet_owlv2.jpg`, `out/sheet_gdino.jpg` (every frame-prompt pair
that had an object or a detection; orange boxes are all detections, the blue box is the chosen one, the green cross
its footprint point `base_cx`, the cyan line the horizon), `out/frames/cutouts.jpg` (the pasted cut-outs).

## Round trip from the robot

`approach.py` ignores frames older than `FRAME_MAX_AGE_S = 0.6` s at the time it looks. Measured from the MacBook to
the Mac mini service over Tailscale (`out/roundtrip_mini.json`, 24 calls, 33 KB JPEG at quality 85, Mac mini busy
with other jobs): round trip median 249 ms, p90 390 ms, max 528 ms, of which the model took median 148 ms. Add the
camera's own 100 ms publish period and a frame is 0.35 to 0.5 s old when the answer arrives: inside the budget,
with little margin while the Mac mini runs sims. An idle Mac mini (81 ms per call) leaves about 0.35 s of margin.
The A7Z is not measured (nothing ran on the robot today); its client cost is one JPEG encode of a 640 x 360 frame
(a few ms) and an HTTP POST, no torch.

## Files

- `detect.py`: `OpenVocabDetector(prompts, device, backend)`, `DetectorClient(url, prompts)`, `select()` (the
  orange_target rule: best accepted box -> `cx, cy, base_cx, area, bbox, n_blobs` plus `score, label`), `serve()`
  (HTTP, `POST /detect?prompts=a|b&conf=0.1` with a JPEG body, `GET /health`), `TextEncoder` (HF CLIP text tower,
  the `clip` package, or `models/prompt_bank.npz`), `annotate()`, CLI.
- `synth.py`: builds `out/frames/` with provenance. `bench.py`: latency, memory and quality per backend.
- `tests/test_detect.py`: 15 tests with `tests/fixture_frame.png` (a real floor frame with the orange part pasted at
  (271, 208, 98, 92) and the duck's feet at the bottom) and `fixture_body.png`; the last test needs the weights.
- `models/` (git-ignored): `yolov8s-worldv2.pt`, `clip-text-b32/`, `prompt_bank.npz`, `owlv2-base-patch16-ensemble/`,
  `grounding-dino-tiny/`, `clip-vit-base-patch32/`.

## Run

```sh
uv venv ~/.venvs/duck-see --python 3.12
uv pip install --python ~/.venvs/duck-see/bin/python torch torchvision transformers ultralytics pyzmq \
    opencv-python-headless pillow numpy pytest "git+https://github.com/ultralytics/CLIP.git"
# weights (MacBook): HF snapshot of google/owlv2-base-patch16-ensemble, IDEA-Research/grounding-dino-tiny and
# openai/clip-vit-base-patch32 into pet/see/models/, yolov8s-worldv2.pt through ultralytics; the CLIP text tower is
# saved with CLIPTextModelWithProjection.save_pretrained(models/clip-text-b32) in fp16 (124 MB)
~/.venvs/duck-see/bin/python -m pytest pet/see/tests -q
~/.venvs/duck-see/bin/python pet/see/detect.py image.jpg --prompts "keys" --out annotated.jpg
~/.venvs/duck-see/bin/python pet/see/synth.py && ~/.venvs/duck-see/bin/python pet/see/bench.py --backend yolo-world --draw pet/see/out/draw_yolo-world
```

Mac mini service (the venv there was made from the uv cache: torch 2.11, transformers 5.19, ultralytics 8.4.192;
`~/code/robotics/pet/see/` holds `detect.py`, `models/yolov8s-worldv2.pt` and `models/prompt_bank.npz`; there is no
CLIP text tower on the Mac mini because its disk had 0.2 to 2 GB free today, so prompts must be in the bank, which
`--build-bank` extends on the MacBook):

```sh
ssh mac-mini 'cd ~/code/robotics && nohup ~/.venvs/duck-see/bin/python pet/see/detect.py --serve --port 8765 \
    --backend yolo-world --prompts "orange block" > /tmp/duck-see-serve.log 2>&1 &'
curl -s http://100.72.167.113:8765/health      # Mac mini Tailscale address
```

## Proposed change to approach.py and seepick.py (not applied; other agents own those files)

Both build the detector in `main()` from `orange_target`; the replacement is a flag and one import, the controllers
do not change:

```diff
 # approach.py main()
-    ap.add_argument("--hsv-lo", default="5,120,120")
-    ap.add_argument("--hsv-hi", default="22,255,255")
+    ap.add_argument("--hsv-lo", default="5,120,120")
+    ap.add_argument("--hsv-hi", default="22,255,255")
+    ap.add_argument("--object", default=None, help="object name for the open-vocabulary detector, e.g. 'keys'")
+    ap.add_argument("--see", default="http://100.72.167.113:8765", help="pet/see service URL (Mac mini)")
     ...
-    lo, hi = (tuple(int(v) for v in a.split(",")) for a in (args.hsv_lo, args.hsv_hi))
-    detect = lambda f, accept=None: orange_target.detect(f, lo, hi, MIN_AREA, accept=accept)  # noqa: E731
+    if args.object:
+        sys.path.insert(0, os.path.expanduser("~/rt"))     # the A7Z checkout root that holds pet/
+        from pet.see.detect import DetectorClient
+        client = DetectorClient(args.see, [args.object], min_area=MIN_AREA, negatives=("robot foot",))
+        detect = lambda f, accept=None: client.detect(f, accept)  # noqa: E731
+    else:
+        lo, hi = (tuple(int(v) for v in a.split(",")) for a in (args.hsv_lo, args.hsv_hi))
+        detect = lambda f, accept=None: orange_target.detect(f, lo, hi, MIN_AREA, accept=accept)  # noqa: E731
```

```diff
 # seepick.py main()
-    p.add_argument("--color", default="orange", choices=sorted(COLORS))
+    p.add_argument("--color", default="orange", choices=sorted(COLORS))
+    p.add_argument("--object", default=None, help="object name for pet/see instead of a colour")
+    p.add_argument("--see", default="http://100.72.167.113:8765")
     ...
-    detect = lambda f, accept=None: orange_target.detect(f, lo, hi, ap.MIN_AREA, accept=accept)  # noqa: E731
+    if a.object:
+        from pet.see.detect import DetectorClient
+        client = DetectorClient(a.see, [a.object], min_area=ap.MIN_AREA, negatives=("robot foot",))
+        detect = lambda f, accept=None: client.detect(f, accept)  # noqa: E731
+    else:
+        detect = lambda f, accept=None: orange_target.detect(f, lo, hi, ap.MIN_AREA, accept=accept)  # noqa: E731
```

`seepick.measure` reads `det["bbox"]` for the width and `approach.project` reads `base_cx` and the box bottom; both
keys are present. `DetectorClient.detect` returns None on a timeout or a lost connection, which the controllers
already treat as "nothing seen this frame". The `--observe` mode prints "no orange object" for a None; the wording
is the only cosmetic difference.

## Open items

- Nothing ran on the robot: the A7Z client cost and the Tailscale path from the A7Z (Wi-Fi) are not measured.
- The real-frame set is four snapshots; none shows the printed part. The hit rates above come from pasted cut-outs
  of Shawn's photos (orange hip covers, the ankle part, the bucket) and three drawn objects; the first robot run
  with `a7z_cam.py --snap` on real objects replaces them.
- The Mac mini had 0.2 to 2 GB of free disk during this work; the 350 MB venv is there, the 0.6 GB weights of the
  two rejected models are not.
- The camera moved to the saddle after `u20cam_mount.json` was fitted (section 7 note); the detector does not
  change that calibration debt.
