"""Speaker embedding and verification with sherpa-onnx (CAM++, 3D-Speaker).

Model: 3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx (CAM++,
3D-Speaker, Chinese+English training data, 16 kHz) from the sherpa-onnx
`speaker-recongition-models` release. Any model from that list works by passing
`model_path`. Chosen 2026-10-26 by bench.py: on sherpa-onnx's own real-speech
test clips it ranked 7/7 test windows correctly with the best same/other margin;
the English VoxCeleb CAM++ ranked 3/7 (see README).

Rules from the 2026-10-26 survey:
- verify on 2-3 s windows of speech;
- enrol with the same fixed phrase, repeated 3 times;
- verify only in still windows: servo whine and footfalls during walking are
  loud in the head mics, so the caller declares when the robot was still and
  `VoiceVerifier.verify_window` refuses otherwise.
"""
from __future__ import annotations

import time
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sherpa_onnx

SAMPLE_RATE = 16000
MODEL_DIR = Path(__file__).resolve().parent / "models"
DEFAULT_MODEL = MODEL_DIR / "campplus_zh_en_advanced.onnx"
ENROL_PHRASE = "Hey little duck, it is me again, come over here and say hello."
MIN_SPEECH_S = 1.2        # speech frames inside a window needed for an embedding
WINDOW_S = (2.0, 3.0)     # accepted window length
# Same-speaker cosine for the default model: real test speech same >= 0.63,
# other <= 0.48 (3 s windows); two similar TTS voices reach 0.56 (bench.py, 2026-10-26).
VOICE_MATCH_COS = 0.60


def load_wav(path: str | Path) -> np.ndarray:
    """16-bit PCM WAV -> float32 mono in [-1, 1] at its own rate (must be 16 kHz)."""
    with wave.open(str(path), "rb") as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError(f"{path}: need 16-bit PCM, got {8 * sw}-bit")
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    if sr != SAMPLE_RATE:
        raise ValueError(f"{path}: need {SAMPLE_RATE} Hz, got {sr}")
    return x


def speech_mask(x: np.ndarray, frame_s: float = 0.03, rel_db: float = 25.0,
                abs_floor: float = 1e-3) -> np.ndarray:
    """Energy VAD: frame is speech if its RMS is within rel_db of the loudest
    frames and above an absolute floor. Cheap and adequate for still windows."""
    n = int(frame_s * SAMPLE_RATE)
    m = len(x) // n
    if m == 0:
        return np.zeros(0, bool)
    rms = np.sqrt((x[: m * n].reshape(m, n) ** 2).mean(1) + 1e-12)
    ref = np.percentile(rms, 95)
    return (rms > ref * 10 ** (-rel_db / 20)) & (rms > abs_floor)


def speech_seconds(x: np.ndarray) -> float:
    return float(speech_mask(x).sum() * 0.03)


@dataclass
class VoiceResult:
    ok: bool
    reason: str = ""
    embedding: np.ndarray | None = None
    speech_s: float = 0.0
    latency_ms: float = 0.0
    quality: float = 0.0


class StillWindow:
    """Tracks robot motion so voice is verified only when it was still.

    Feed `mark(t, moving)` from the motion loop (e.g. any servo goal change
    above a threshold, or |gyro| above a threshold, sets moving=True).
    `is_still(t0, t1)` is True only if no moving mark fell in [t0 - margin, t1].
    The margin covers servo ring-down after the last motion.
    """

    def __init__(self, margin_s: float = 0.3, horizon_s: float = 30.0):
        self.margin_s = margin_s
        self.horizon_s = horizon_s
        self._moving: deque[float] = deque()
        self._last_t = -1e18

    def mark(self, t: float, moving: bool) -> None:
        self._last_t = max(self._last_t, t)
        if moving:
            self._moving.append(t)
        while self._moving and self._moving[0] < t - self.horizon_s:
            self._moving.popleft()

    def is_still(self, t0: float, t1: float) -> bool:
        if t0 < self._last_t - self.horizon_s:
            return False  # outside what we remember
        lo = t0 - self.margin_s
        return not any(lo <= tm <= t1 for tm in self._moving)


class VoiceEmbedder:
    def __init__(self, model_path: str | Path = DEFAULT_MODEL, num_threads: int = 2):
        if not Path(model_path).exists():
            raise FileNotFoundError(f"{model_path} missing; run pet/identity/fetch_models.sh")
        cfg = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(model_path), num_threads=num_threads, debug=False, provider="cpu")
        self.ext = sherpa_onnx.SpeakerEmbeddingExtractor(cfg)
        self.dim = self.ext.dim

    def embed(self, x: np.ndarray) -> np.ndarray:
        s = self.ext.create_stream()
        s.accept_waveform(sample_rate=SAMPLE_RATE, waveform=x.astype(np.float32))
        s.input_finished()
        if not self.ext.is_ready(s):
            raise ValueError("audio too short for an embedding")
        e = np.asarray(self.ext.compute(s), dtype=np.float32)
        return e / (np.linalg.norm(e) + 1e-12)

    def embed_speech(self, x: np.ndarray) -> VoiceResult:
        """Embed only the speech frames of x (keeps silence out of the embedding)."""
        t0 = time.perf_counter()
        mask = speech_mask(x)
        sp = mask.sum() * 0.03
        if sp < MIN_SPEECH_S:
            return VoiceResult(False, f"speech {sp:.1f}s < {MIN_SPEECH_S}s", speech_s=sp)
        n = int(0.03 * SAMPLE_RATE)
        y = x[: len(mask) * n].reshape(len(mask), n)[mask].reshape(-1)
        e = self.embed(y)
        lat = (time.perf_counter() - t0) * 1e3
        q = float(min(1.0, sp / 2.5))
        return VoiceResult(True, embedding=e, speech_s=sp, latency_ms=lat, quality=q)


class VoiceVerifier:
    """Enrol a speaker from 3 repetitions of the fixed phrase; verify windows."""

    def __init__(self, embedder: VoiceEmbedder, threshold: float = VOICE_MATCH_COS):
        self.embedder = embedder
        self.threshold = threshold
        self.enrolled: dict[str, np.ndarray] = {}

    def enroll(self, name: str, clips: list[np.ndarray]) -> np.ndarray:
        if len(clips) < 3:
            raise ValueError("enrolment needs the phrase 3 times")
        embs = []
        for c in clips:
            r = self.embedder.embed_speech(c)
            if not r.ok:
                raise ValueError(f"enrolment clip rejected: {r.reason}")
            embs.append(r.embedding)
        c = np.mean(embs, axis=0)
        c /= np.linalg.norm(c)
        self.enrolled[name] = c
        return c

    def verify_window(self, x: np.ndarray, t0: float, t1: float,
                      still: StillWindow | None) -> tuple[VoiceResult, dict[str, float]]:
        dur = len(x) / SAMPLE_RATE
        if not (WINDOW_S[0] - 0.05 <= dur <= WINDOW_S[1] + 0.05):
            return VoiceResult(False, f"window {dur:.2f}s not in 2-3 s"), {}
        if still is not None and not still.is_still(t0, t1):
            return VoiceResult(False, "robot moved during window"), {}
        r = self.embedder.embed_speech(x)
        if not r.ok:
            return r, {}
        scores = {k: float(np.dot(v, r.embedding)) for k, v in self.enrolled.items()}
        return r, scores


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Embed WAV files and print pairwise cosine")
    ap.add_argument("wavs", nargs="+")
    a = ap.parse_args()
    emb = VoiceEmbedder()
    es = []
    for p in a.wavs:
        r = emb.embed_speech(load_wav(p))
        print(f"{p}: ok={r.ok} speech={r.speech_s:.2f}s latency={r.latency_ms:.1f}ms {r.reason}")
        es.append(r.embedding)
    for i in range(len(es)):
        for j in range(i + 1, len(es)):
            if es[i] is not None and es[j] is not None:
                print(f"  cos({i},{j}) = {float(np.dot(es[i], es[j])):.3f}")
