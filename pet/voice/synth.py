"""Synthetic test clips for the voice chain, made with macOS `say -o` (written to files, never played).

    pet/.venv/bin/python -m pet.voice.synth            # writes out/clips/<id>.wav (16 kHz mono) and <id>.robot.wav

Every clip exists twice: a 16 kHz mono WAV (what stt.py eats) and a "robot-format" 4-channel 48 kHz S32_LE WAV with
the sentence on ch0 and ch1 (the ears, right ear 0.3 ms later and 1 dB quieter: a speaker a little to the left), the
same at -6 dB on ch2 (the back mic) and zeros on ch3, with 0.8 s of pink room noise before and after at -50 dBFS, so
listen.py segments it the way it will segment the A7Z stream (CURRENT-STATE a7z_audio_capture). The sentence list is
the same 20 commands the intent test uses, in both languages; out/clips/index.json records id, text, lang and voice.
"""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

from .listen import ROBOT_CHANNELS, ROBOT_FS, STT_FS

HERE = Path(__file__).resolve().parent
CLIPS = HERE / "out" / "clips"

# (id, text, lang, say voice). Tingting is the natural zh_CN voice, Samantha the natural en_US one.
SENTENCES = [
    ("en01", "Fetch the orange block.", "en", "Samantha"),
    ("en02", "Come here.", "en", "Samantha"),
    ("en03", "Sit down.", "en", "Samantha"),
    ("en04", "Stop.", "en", "Samantha"),
    ("en05", "Stay out of the bedroom.", "en", "Samantha"),
    ("en06", "Good duck.", "en", "Samantha"),
    ("en07", "Look at me.", "en", "Samantha"),
    ("en08", "Turn around.", "en", "Samantha"),
    ("en09", "Open your beak.", "en", "Samantha"),
    ("en10", "Walk forward a little.", "en", "Samantha"),
    ("zh01", "把橙色方块叼来。", "zh", "Tingting"),
    ("zh02", "过来。", "zh", "Tingting"),
    ("zh03", "坐下。", "zh", "Tingting"),
    ("zh04", "停。", "zh", "Tingting"),
    ("zh05", "别进卧室。", "zh", "Tingting"),
    ("zh06", "好鸭子。", "zh", "Tingting"),
    ("zh07", "看着我。", "zh", "Tingting"),
    ("zh08", "转个身。", "zh", "Tingting"),
    ("zh09", "张嘴。", "zh", "Tingting"),
    ("zh10", "往前走一点。", "zh", "Tingting"),
]


def say_to_wav(text: str, voice: str, out_wav: Path, fs: int = STT_FS) -> None:
    """`say -o` writes an AIFF; afconvert turns it into 16-bit mono PCM at fs. Nothing is played."""
    aiff = out_wav.with_suffix(".aiff")
    subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{fs}", "-c", "1", str(aiff), str(out_wav)], check=True)
    aiff.unlink()


def read_mono(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path)) as w:
        fs, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    assert sw == 2, f"{path}: expected 16-bit"
    x = np.frombuffer(raw, "<i2").reshape(-1, ch).astype(np.float32) / 2 ** 15
    return x.mean(axis=1), fs


def pink(n: int, rng: np.random.Generator) -> np.ndarray:
    """Pink-ish noise (1/f shaped white noise), unit RMS."""
    white = rng.standard_normal(n)
    spec = np.fft.rfft(white)
    f = np.fft.rfftfreq(n)
    spec[1:] /= np.sqrt(f[1:])
    x = np.fft.irfft(spec, n)
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-12)


def robot_format(mono16: np.ndarray, out_path: Path, pad_s: float = 0.8, noise_dbfs: float = -50.0,
                 speech_dbfs: float = -20.0, seed: int = 0) -> None:
    """16 kHz mono speech -> 4-channel 48 kHz S32_LE WAV shaped like the A7Z capture (see module docstring)."""
    rng = np.random.default_rng(seed)
    up = np.repeat(mono16, ROBOT_FS // STT_FS)                     # zero-order hold, then a light smoothing
    k = np.ones(3) / 3
    up = np.convolve(up, k, mode="same")
    up = up / (np.max(np.abs(up)) + 1e-9) * 10 ** (speech_dbfs / 20)
    pad = int(pad_s * ROBOT_FS)
    n = len(up) + 2 * pad
    speech = np.zeros(n, np.float32)
    speech[pad:pad + len(up)] = up
    delay = int(round(0.0003 * ROBOT_FS))                           # right ear 0.3 ms later
    right = np.zeros(n, np.float32)
    right[delay:] = speech[: n - delay] * 10 ** (-1 / 20)
    chans = np.zeros((n, ROBOT_CHANNELS), np.float32)
    chans[:, 0] = speech
    chans[:, 1] = right
    chans[:, 2] = speech * 10 ** (-6 / 20)
    noise = 10 ** (noise_dbfs / 20)
    for c in range(3):
        chans[:, c] += pink(n, rng) * noise
    # 24-bit left-justified in 32-bit frames, as the INMP441 delivers them (namecall.i2s_to_float shifts >> 8)
    q = np.clip(chans * 2 ** 23, -2 ** 23, 2 ** 23 - 1).astype(np.int32) << 8
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(ROBOT_CHANNELS)
        w.setsampwidth(4)
        w.setframerate(ROBOT_FS)
        w.writeframes(q.tobytes())


def main(argv=None) -> int:
    CLIPS.mkdir(parents=True, exist_ok=True)
    index = []
    for cid, text, lang, voice in SENTENCES:
        wav = CLIPS / f"{cid}.wav"
        say_to_wav(text, voice, wav)
        mono, fs = read_mono(wav)
        assert fs == STT_FS
        robot_format(mono, CLIPS / f"{cid}.robot.wav", seed=int(cid[2:]))
        index.append({"id": cid, "text": text, "lang": lang, "voice": voice, "seconds": round(len(mono) / fs, 2),
                      "wav": wav.name, "robot_wav": f"{cid}.robot.wav"})
        print(f"{cid}  {len(mono) / fs:4.2f} s  {voice:9s} {text}")
    (CLIPS / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    print(f"{len(index)} clips in {CLIPS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
