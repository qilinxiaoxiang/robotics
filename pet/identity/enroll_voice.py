"""Enrol the owner's voice: the fixed phrase, 3 times.

Live (Terminal.app, needs microphone permission):
    pet/.venv/bin/python -m pet.identity.enroll_voice --name shawn
Offline:
    pet/.venv/bin/python -m pet.identity.enroll_voice --name shawn --wavs a.wav b.wav c.wav

Only the 3 embeddings (and their average) are stored, not the audio.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from .memory import FamiliarityMemory
from .voice import ENROL_PHRASE, SAMPLE_RATE, VoiceEmbedder, load_wav, speech_seconds

DEFAULT_DB = Path(__file__).resolve().parent / "data" / "identity.sqlite"
RECORD_S = 5.0


def record(seconds: float) -> np.ndarray:
    import sounddevice as sd
    x = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    return x[:, 0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="owner")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--wavs", nargs="*")
    a = ap.parse_args(argv)
    emb = VoiceEmbedder()
    clips = []
    if a.wavs:
        clips = [load_wav(p) for p in a.wavs]
    else:
        print(f'Say this phrase each time, in your normal voice, in a quiet room:\n\n  "{ENROL_PHRASE}"\n')
        while len(clips) < 3:
            input(f"[{len(clips) + 1}/3] press Enter, then speak ({RECORD_S:.0f} s) ")
            x = record(RECORD_S)
            sp = speech_seconds(x)
            if sp < 1.2:
                print(f"  only {sp:.1f} s of speech heard; again please (check the input level)")
                continue
            print(f"  ok, {sp:.1f} s of speech")
            clips.append(x)
    if len(clips) < 3:
        sys.exit("need 3 clips")
    embs = []
    for i, x in enumerate(clips):
        r = emb.embed_speech(x)
        if not r.ok:
            sys.exit(f"clip {i + 1} rejected: {r.reason}")
        embs.append(r.embedding)
    m = np.mean(embs, 0)
    m /= np.linalg.norm(m)
    for i, e in enumerate(embs):
        print(f"clip {i + 1}: cos to mean {float(e @ m):.3f}")
    mem = FamiliarityMemory(a.db)
    pid = mem.register_owner(a.name)
    mem.enroll(pid, "voice", embs, quality=1.0)
    print(f"enrolled 3 voice embeddings for owner '{a.name}' (person {pid}) in {a.db}")
    mem.close()


if __name__ == "__main__":
    main()
