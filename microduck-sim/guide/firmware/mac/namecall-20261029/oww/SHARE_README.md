# MicroDuck wake word "Mochi": data and brief for retraining

Ryan, this package holds everything we have for training the duck's name detector, cut into short clips. The current model (`models/mochi_v4.onnx`) misses too many of Shawn's real calls. The goal is a model that answers his calls reliably on the robot without waking on ordinary talk.

## What the robot runs now

- The A7Z (2 GB RAM, CPU only) runs openWakeWord's frozen front end (`melspectrogram.onnx` and `embedding_model.onnx`, which give 96 features per 80 ms frame) and our small DNN head (`mochi_v4.onnx`, input 16 frames = 1.28 s).
- Audio comes from two head microphones ("ears") at 16 kHz. Each ear is scored as its own stream, every 80 ms, and the score is the larger of the two.
- It wakes at a score of 0.7. A second chance also fires when two runs of at least 0.4 start 1 to 5 s apart.
- A drop-in replacement is easiest as another openWakeWord head: an ONNX file that takes `[1, 16, 96]` embedding features and returns one probability. A different architecture is fine too if it streams in real time on one CPU thread next to the walking controller. Tell us its input contract.

## The problem, with evidence

- On 2026-11-12 00:56, in a quiet room, Shawn called four times. v4 scored the calls 0.60, 0.21, 0.49 and 0.90, so only one call was answered.
- The same call's score moved between 0.01 and 0.62 when the 80 ms frame grid shifted by 10 ms. The model is on the edge for calls it has not seen.
- Raising the gain made it worse (call 3: median 0.21 at +0 dB, 0.05 at +14 dB). The level is not the cause.
- v4 learned from 77 real calls recorded on 10-29 and 10-30, plus web and TTS clips. On the 32 held-out calls of those days it hears 22 at 0.7.

## Package layout

- `positives/train/`: 99 calls (77 from 10-29/10-30, 22 mined from the life log of 11-02 to 11-11), each cut once without augmentation as the two-ear mix and each ear alone (`*_mix_*`, `*_ear0_*`, `*_ear1_*`), 0.30 s before the word to 0.35 s after. Times are in `manifest.jsonl`.
- `positives/heldout/`: 49 calls never trained on, 1 s before to 2 s after each call start. These are the 32 held-out calls of 10-29/10-30, 13 calls from the 11-11 evening, and the four calls Shawn counted on 11-12 (`counted_by_shawn` in the manifest). `counted_20261112_0056_3ch.wav` is that 13 s moment in three channels (ear 0, ear 1, back microphone), including the duck's own quack after the last call.
- `negatives/train/`: 1517 two-second clips with no call. The name prefix is the kind: `life`, `life6` and `live` are Shawn talking at home or near the robot, `own` is the duck's own quack, `calls` is room sound between calls.
- `negatives/heldout_talk/`: 187 two-second clips (6.2 min) of held-out no-call talk, for the false-wake check.
- `background/`: RoboClub room sound and robot motion noise (servo and footstep sound while walking), used as augmentation background.
- `synthetic_set/`: a macOS TTS set (`manifest.json` kinds: `pos`, `pos_zh`, `neg_word`, `speech`). Its 28 min of `speech` is our false-wake check on continuous speech.
- `web/`: "mochi" and near-miss clips cut from public videos; `web_heldout.json` lists the held-out videos.
- `models/`: `mochi_v4.onnx` and the openWakeWord training config it came from (`mochi_v4_train_config.yml`, paths are on our Mac mini).
- `scripts/`: our data prep and scoring scripts, for reference. Paths are hard-coded to our machine.

For privacy, the talk clips are 2 s long with 2 s gaps between them and opaque names, so they cannot be joined back into conversations. Please keep the package within the team.

## Acceptance

A new model is ready for the robot when it meets all of these at a threshold of 0.7:

- The four counted calls each score at least 0.7 at 7 or more of 8 frame offsets (shift the audio 0, 10, ..., 70 ms before streaming; score each ear alone and take the larger). `scripts/score_v6.py` does this.
- At least 28 of the 32 held-out 10-29/10-30 calls are heard (v4: 22/32).
- Zero false wakes on `negatives/heldout_talk/`.
- At most one false wake on the 28 min of synthetic speech (v4: 1).

Please report v4 and your model side by side on the same checks.

## Suggestions

- Train for shift and level robustness. Our round-6 plan cut each positive with start jitter of up to 0.12 s, trailing room of 0.05 to 0.35 s and gain of -12 to +6 dB, from the two-ear mix and from each ear alone.
- The openWakeWord recipe also needs its general negative features, which are not in this package: `openwakeword_features_ACAV100M_2000_hrs_16bit.npy` (17.3 GB) and `validation_set_features.npy` (0.18 GB) from the Hugging Face dataset `davidscripka/openwakeword_features`.
- 99 real calls from one speaker is still little. If you have a speech model that already knows phonemes or keywords (a pretrained keyword-spotting or speech embedding model you can fine-tune), it may generalise better than a head on frozen features. Check the A7Z budget before choosing it.
- The 22 mined calls came from a template matcher plus v4 itself, so they lean toward calls v4 already half-hears. The 13 evening and 4 counted calls are the fairest test of new-call recall.
- Some talk in `negatives/train` may contain a call the miner missed (its recall was about 56% on known calls). If a negative scores very high, listen to it before trusting it.

Questions go to Shawn.
