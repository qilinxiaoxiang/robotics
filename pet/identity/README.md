# Owner identity (face + voice + familiarity memory)

Problem: Tier 1 "Owner identity, local" in `docs/PET_ROBOT_FEATURES.md`. The pet must tell its owner from known people and strangers by face and voice, on the robot, and grow familiarity with people it meets. Backbones are never retrained: we store embeddings by day, cluster at night, and count encounters.

## Pieces

- `face.py`: InsightFace `buffalo_sc` run directly with onnxruntime: SCRFD-500MF detection (640x640 letterbox), 5-point similarity alignment to the ArcFace template, MobileFaceNet 512-d embedding. Each face reports inter-pupil distance (IPD) in px; faces under 10 px IPD are rejected before embedding. A rough pitch/yaw is estimated from the 5 landmarks (nose position between the eye and mouth lines; positive pitch = face seen from below). It is uncalibrated and for logging and quality weighting only.
- `enroll_face.py`: owner enrolment from 5 poses, 3 frames each: front, left, right, camera below chest height, camera on the floor. The two low poses match the robot's view from 15 cm. `--images` enrols from files.
- `voice.py`: speaker embedding through sherpa-onnx, CAM++ (3D-Speaker, Chinese+English training data). Energy voice-activity detection keeps only speech frames, and a window needs at least 1.2 s of speech. `VoiceVerifier` enrols from the fixed phrase said 3 times and verifies only 2-3 s windows. `StillWindow` refuses a window when the motion loop marked the robot as moving inside it (plus 0.3 s of ring-down).
- `enroll_voice.py`: records the phrase "Hey little duck, it is me again, come over here and say hello." 3 times (`--wavs` for files).
- `memory.py`: SQLite store of `samples {t, modality, vector, quality, provisional_id, track, person_id}`, `persons`, `centroids`, and `sightings` (timestamps only). `consolidate()` is the nightly step, run per modality:
  1. Cluster the unassigned samples with HDBSCAN (DBSCAN as the fallback).
  2. Prune each cluster and split it into groups in which every member is similar (cosine at or above the pair threshold) to at least 2 others. This is the ">= 3 similar samples" rule.
  3. Link each group to a known person by centroid. If no centroid matches, link it through co-occurrence with the other modality (a voice heard while a known face was in view). Otherwise create a new person.
  4. Count leftover single samples close to a known person as encounters.
  5. Merge fragments: persons whose centroids agree, or who were both seen in one continuous track.
  6. Delete unknown samples older than `unknown_retention_days` (default 14). Cap stored vectors per known person at 200; their sightings stay.
  Familiarity = (1 - exp(-(log(1+encounters)/2 + days_seen/4)/2)) x exp(-days_since_last_seen/21). Encounters are sightings more than 10 min apart. The owner is registered manually, pinned at familiarity 1, never merged away, and never merged with another pinned person.
- `whois.py`: per-track log-odds fusion. Each observation adds `clip(slope * (cos - match_cos)) * quality` to each person's accumulator and stranger evidence when the best cosine is low. All accumulators decay with tau = 20 s and are clamped to +-6. The output is `owner | known:<name> | stranger | unsure` with sigmoid confidence. Cues are `CueModel` entries. Face and voice are anchors. A non-anchor cue (a placeholder `silhouette` entry for the later OSNet cue, uncalibrated and fed by nothing yet) can only reinforce a person an anchor already supports.
- `demo.py`: live webcam + microphone demo, a recorded-input mode, and the synthetic replay. `bench.py`: latency and sanity measurements written to `out/bench.json`. `synth.py`: generated embedding days.

## Run

```sh
/opt/homebrew/bin/python3.12 -m venv pet/.venv
pet/.venv/bin/pip install -r pet/identity/requirements.txt
sh pet/identity/fetch_models.sh            # weights + sample image, sha256-checked
pet/.venv/bin/python -m pytest pet/identity/tests -q
pet/.venv/bin/python -m pet.identity.demo --synthetic   # no camera needed
```

Live, from Terminal.app (the Claude app process has no camera or microphone access). Terminal.app asks for camera and microphone permission on first use; if it does not, enable it under System Settings > Privacy & Security > Camera / Microphone.

```sh
cd ~/code/robotics
pet/.venv/bin/python -m pet.identity.enroll_face --name shawn    # SPACE per pose, 5 poses
pet/.venv/bin/python -m pet.identity.enroll_voice --name shawn   # Enter, say the phrase, x3
pet/.venv/bin/python -m pet.identity.demo                        # q quit, c consolidate, m moving, s screenshot
```

The demo draws each face with its IPD (red below 10 px), pitch and yaw. It shows who-is-this with its confidence, familiarity, voice score and latency, and the face pipeline's ms/frame. Everyone writes to `pet/identity/data/identity.sqlite` unless you pass `--db`.

## Measured on this Mac (Apple M1 Pro, CPU, 2 threads, onnxruntime 1.31, 2026-10-26)

From `pet/.venv/bin/python -m pet.identity.bench` (`out/bench.json`):

- **Face detection:** SCRFD-500MF at 640x640 takes 20 ms median (23 ms p90) per 1280x720 frame.
- **Face embedding:** MobileFaceNet takes 7.3 ms per face.
- **Live demo loop:** one face per frame measured 28.7 ms median on the recorded 1280x720 clip.
- **Face sanity check:** the InsightFace sample photo has 6 faces, all detected. A face against its own augmented copies (flip, dark, blur, half resolution, JPEG q30) scored cosine >= 0.92. Different people scored <= 0.22.
- **IPD gate:** shrinking the photo, all 6 faces are still detected at 0.2x, but only 1 has IPD >= 10 px; at 0.15x none passes.
- **Voice latency:** CAM++ on a 2.5 s window takes 26 ms median (27 ms p90), including feature extraction. A 2 s window takes 24 ms and a 3 s window 26 ms.
- **Voice, synthetic speakers:** 8 macOS text-to-speech voices stood in for speakers. Each was enrolled with the phrase at 3 speaking rates and tested on 3 other sentences. Top-1 was 24/24; same-voice cosine was >= 0.70 and other-voice <= 0.56. At the 0.60 threshold there were 0 false accepts and 0 false rejects.
- **Voice, real speech:** sherpa-onnx's own public test clips (3 speakers, Mandarin) gave top-1 7/7. Same-speaker cosine was >= 0.71 and other-speaker <= 0.48.
- **Speaker model choice:** on the same real clips the English-only VoxCeleb CAM++ ranked only 3/7 (other-speaker cosine up to 0.94), so the default is the zh+en CAM++.

These are Mac numbers. The A7Z has not been measured; its A76/A55 cores will be slower by an unmeasured factor.

## What goes to the A7Z NPU

Source: [Radxa Cubie A7Z NPU development](https://docs.radxa.com/en/cubie/a7z/app-dev/npu-dev), read 2026-10-26.

- **Toolchain:** the NPU is a Vivante VIP9000. The ACUITY toolkit imports ONNX (also TF/TFLite/PyTorch/Caffe/Darknet/Keras), quantizes to uint8, per-channel int8, int16, bf16 or mixed, and exports an NBG `.nb` file that the VIPLite driver runs.
- **Operator support:** the docs publish no operator support list, so operator coverage for our two models is unverified.
- **Closest data point:** the Model Zoo has RetinaFace-ResNet50 at 320x320 uint8. Radxa reports 15.7 ms inference and 63.7 fps (inference only) on the A733. That is a different, larger face detector, not SCRFD; we have not run anything on the NPU.
- **Planned NPU candidates:** SCRFD-500MF and MobileFaceNet. Both are plain conv/BN/PReLU/add networks with static shapes (*inferred* to convert). For the NPU, export SCRFD at a fixed 640x640 (or 320x320) input. The anchor decode, NMS and alignment stay on CPU in `face.py`. After quantization, re-check the same/different cosine margin with `bench.py`, since uint8 may cost accuracy (ACUITY's quantization-accuracy guide covers mixed int16).
- **Stays on CPU:** speaker embedding (fbank features + CAM++ in sherpa-onnx; 26 ms per 2.5 s window on the Mac, run at most once a second, and only in still windows). Clustering, SQLite and fusion also stay on CPU.
- **Fallback:** if the NPU conversion fails, the whole face pipeline runs on CPU through onnxruntime unchanged. Its A7Z speed is unmeasured.

## Licences

- **InsightFace `buffalo_sc`:** the model pack (SCRFD + MobileFaceNet weights) is released by InsightFace for **non-commercial research use only**; the code is MIT. Fine for Shawn's own robot. A commercial product needs a licence from InsightFace or a different face model. The weights are downloaded by `fetch_models.sh` into `models/`, which is gitignored and never committed.
- **CAM++ (3D-Speaker, ModelScope `iic/speech_campplus_sv_zh_en_16k-common_advanced`):** the 3D-Speaker repository and sherpa-onnx are Apache-2.0; the model card's own licence field was not checked.
- **`samples/t1.jpg`:** the InsightFace package's public test image, used only by `bench.py`. It is gitignored.

## Privacy rule

- **What is stored:** embeddings, quality and timestamps only, on the device. `demo.py` and the enrol tools never write frames or audio, except a screenshot when you press `s` in the demo.
- **Retention:** samples that never became a person are deleted after `unknown_retention_days`. Raw images or audio of non-owners must not be kept past the day; nothing in this package creates them.
- **Repository:** the database (`data/`), samples and demo output are gitignored.
- **Erasing a person:** delete their `persons` row together with their `samples` and `sightings`.

## Known limits

- **One person per track:** the demo tracks only the largest face. Memory merges fragments seen in one track, so a track must never hold two people. The demo therefore starts a new track when the box jumps (IoU < 0.3) or the face embedding drifts (cosine to the track < 0.3). A multi-person tracker must keep the same guarantee.
- **Thresholds:** face thresholds (match 0.40, cluster pair 0.35) follow the buffalo_sc bench and common ArcFace practice. They have not been tuned on Shawn's face from the robot's low camera; redo `bench.py`-style checks with real enrolment data.
- **Pitch/yaw:** the estimate is a geometric approximation. The yaw sign was checked on a turned face in the sample photo; the pitch sign has not been checked against ground truth.
- **Untested on hardware:** the live webcam/microphone path has not been exercised in this environment. It was tested with a recorded video plus WAV through `--video/--wav --headless`.
