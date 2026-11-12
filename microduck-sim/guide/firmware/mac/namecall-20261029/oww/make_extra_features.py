"""openWakeWord features (N, 16, 96) of our own negatives, run after `train.py --augment_clips` (which writes
total_length into the yaml):
  real_negative_features.npy  2 s clips of the duck's call-free recordings (data/real_neg), embedded as they are
                              and once more at a random gain of -12..+6 dB
  web_negative_features.npy   mochi_web neg / neg_adjacent clips of the training videos, through the same
                              augment_clips pipeline (backgrounds, RIRs) as the positives
"""
import glob
import os
import sys
import wave

import numpy as np
import yaml
import openwakeword
from openwakeword.data import augment_clips
from openwakeword.utils import AudioFeatures

OWW = "/Users/shawnxiang/mochi-train/oww"
cfg = yaml.safe_load(open(os.path.join(OWW, "mochi.yml")))
L = int(cfg.get("total_length", 32000))   # train.py's rule gives 32000 for 0.5-1.0 s clips; run_train.sh checks it
print("total_length", L, flush=True)
out = os.path.join(cfg["output_dir"], cfg["model_name"])
F = AudioFeatures(inference_framework="onnx", ncpu=4)
rng = np.random.default_rng(0)


def read16(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16)


def fit(x):
    if len(x) >= L:
        return x[:L]
    return np.concatenate([x, np.zeros(L - len(x), np.int16)])


def embed(clips):
    feats = []
    for k in range(0, len(clips), 256):
        feats.append(F.embed_clips(np.stack(clips[k:k + 256]), batch_size=64, ncpu=4))
    return np.concatenate(feats).astype(np.float32)


# real room negatives: as recorded + one gain-jittered copy
files = sorted(glob.glob(os.path.join(OWW, "data", "real_neg", "*.wav")))
clips = [fit(read16(p)) for p in files]
jit = [np.clip(c.astype(np.float32) * 10 ** (rng.uniform(-12, 6) / 20), -32768, 32767).astype(np.int16) for c in clips]
feats = embed(clips + jit)
np.save(os.path.join(out, "real_negative_features.npy"), feats)
print("real_negative", len(files), "clips ->", feats.shape, flush=True)

# web negatives through augment_clips (same backgrounds and RIRs as the positives)
files = sorted(glob.glob(os.path.join(OWW, "data", "web_neg", "*.wav")))
bg = [i.path for d in cfg["background_paths"] for i in os.scandir(d) if i.name.endswith(".wav")]
rir = [i.path for d in cfg["rir_paths"] for i in os.scandir(d) if i.name.endswith(".wav")]
feats = []
n = 0
for batch in augment_clips(files, total_length=L, batch_size=cfg["augmentation_batch_size"],
                           background_clip_paths=bg, RIR_paths=rir):
    feats.append(F.embed_clips(batch, batch_size=64, ncpu=4).astype(np.float32))
    n += len(batch)
    if n % 512 < cfg["augmentation_batch_size"]:
        print("  web_neg", n, "/", len(files), flush=True)
feats = np.concatenate(feats)
np.save(os.path.join(out, "web_negative_features.npy"), feats)
print("web_negative", len(files), "clips ->", feats.shape, flush=True)
