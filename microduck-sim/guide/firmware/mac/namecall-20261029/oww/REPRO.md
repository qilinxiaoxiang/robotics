# Reproducing the Mochi openWakeWord training (v4, v6)

These files sit next to the scripts in the Box zip (`scripts/`). Our root was `/Users/shawnxiang/mochi-train/oww` on a Mac mini (Apple Silicon, macOS, Python 3.11.15). Every script hard-codes that root as `OWW=` or in `mochi.yml`; change it to your own directory.

## Files

- `make_extra_features.py`: builds openWakeWord features (N, 16, 96) for our own negatives after `--augment_clips`. It reads `data/real_neg/*.wav`, embedding each clip as recorded plus one copy at a random -12..+6 dB gain. It also reads `data/web_neg/*.wav` through the same augment_clips pipeline as the positives. It writes `work/mochi/real_negative_features.npy` and `web_negative_features.npy`.
- `train_wrap.py`: runs `openwakeword/train.py --train_model` with the DataLoader forced to `num_workers=0`. Stock train.py fails on macOS with a PicklingError. Nothing else changes, so on Linux you can call train.py directly.
- `psg_shim/generate_samples.py`: makes train.py work with piper-sample-generator 3.2.0. It points to the LibriTTS-R model in `dl/`, runs the generator on CPU (its jit ops fail on MPS), and resamples the output to 16 kHz.
- `run_train.sh`: the four stages, `gen | aug | extra | train | all`.
- `mochi.yml`: the training config. It is identical to `models/mochi_v4_train_config.yml` in the zip, and v6 used the same file.
- `get_rirs_fma.py`: downloads the MIT RIRs to `data/mit_rirs` and the FMA music background to `data/bg16k`, following the openWakeWord training notebook.
- `setup1.sh` .. `setup6.sh`: the setup we ran, in order: clones, downloads, packages, then the pins that fixed breakages.
- `requirements-lock.txt`: `uv pip freeze` of the training venv as it is today.

## Environment

- openWakeWord at commit `368c03716d1e92591906a84949bc477f3a834455` (github.com/dscripka/openWakeWord), installed with `pip install --no-deps -e`.
- piper-sample-generator at commit `2971426a55072f7d22fec416ca7800df8bd23207` (github.com/rhasspy/piper-sample-generator), also `--no-deps -e`, plus `piper-tts==1.3.0`.
- Key pins: torch 2.5.1, torchaudio 2.5.1 (2.9+ needs torchcodec/ffmpeg to load audio), scipy 1.16.3 (1.17 removed `scipy.special.sph_harm`, which `acoustics` needs), numpy 2.2.6, datasets 3.6.0, speechbrain 0.5.16, audiomentations 0.33.0, torch-audiomentations 0.12.0, onnxruntime 1.31.1.
- Downloads go in `dl/`: `openwakeword_features_ACAV100M_2000_hrs_16bit.npy` (17.3 GB), `validation_set_features.npy` (185 MB) from huggingface.co/datasets/davidscripka/openwakeword_features, and `en_US-libritts_r-medium.pt` (204 MB) from the piper-sample-generator v2.0.0 release. The URLs are in `setup1.sh`.
- The target phrase is spelled "mo chee" because espeak reads "mochi" as MAH-chai. Both words are in the CMU dictionary, so no DeepPhonemizer download is needed (its S3 host returns 403).

## Data layout the scripts expect (under the root)

- `data/web_pos/`: real people saying "mochi". `run_train.sh gen` copies it into `work/mochi/positive_train/`.
- `data/real_neg/`, `data/web_neg/`: negatives for `make_extra_features.py`.
- `data/bg16k/`, `data/bg_roboclub/`, `data/bg_motion_train/`: backgrounds at duplication rates 1, 3 and 5.
- `data/mit_rirs/`: room impulse responses.

- `data/duck_pos/`: our duck-recorded calls. `prep_v3.py` cuts them into here and copies them into `work/mochi/positive_train/` after `gen`.

`prep_v3.py` (v4) and `prep_v6.py` (v6) in the zip build these folders from our raw recordings, which are not shared. The Box zip holds the clips already cut, so skip the prep step and place them directly: `positives/train` into `work/mochi/positive_train/` (after `gen`), `web/web_pos` into `data/web_pos`, `negatives/train` into `data/real_neg`, `web/web_neg` into `data/web_neg`, `background/roboclub` into `data/bg_roboclub`, `background/robot_motion` into `data/bg_motion_train`. Use `positives/heldout` and `negatives/heldout_talk` only for scoring.

## Exact commands

One-time synthetic clips (6000 train / 1000 val positives and adversarial negatives from piper):

    ./run_train.sh gen

v4, the model on the robot now:

    nohup ./run_v4.sh > logs/v4_chain.log 2>&1 &

This runs `prep_v3.py`, sets `steps: 50000`, adds the motion background at rate 5, then:

    python openWakeWord/openwakeword/train.py --training_config mochi.yml --augment_clips
    python make_extra_features.py
    python train_wrap.py --training_config mochi.yml --train_model
    python score_oww.py --model models/mochi_v4.onnx --out results/mochi_v4.json
    python score_v2.py  --model models/mochi_v4.onnx --heldout data/duck_heldout_v3.json --out results/mochi_v4_extra.json

`run_train.sh aug` checks that `positive_features_train.npy` has 16 frames (total_length 32000), which `make_extra_features.py` assumes.

v6:

    ZC=5 V4MIN=0.05 nohup ./run_v6.sh > logs/v6_chain.log 2>&1 &

Same stages on `prep_v6.py --zc 5 --v4min 0.05` data. Caveat: our only v6 run never produced a valid model. The `dl/` downloads had been deleted, so `--train_model` failed after augmentation, and the old `mochi.onnx` was copied as v6. The v6 scores in our log are from that stale file, so ignore them. `run_v6.sh` now checks every feature file before it starts and refuses to copy a stale model. v6 has not been rerun since. v4 is the baseline.
