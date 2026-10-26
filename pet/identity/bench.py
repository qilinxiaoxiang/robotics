"""Measure CPU latency and sanity-check embeddings on this machine.

Face: the InsightFace sample group photo (samples/t1.jpg, fetched by
fetch_models.sh) plus a 1280x720 resize of it (the U20CAM-720P frame size);
same-identity check uses photometric/geometric augmentations of each face
(no real-person datasets).
Voice: macOS `say` text-to-speech voices stand in for speakers (synthetic,
no human recordings). Clips go to out/tts/ (gitignored) and are deleted
unless --keep-audio.

    pet/.venv/bin/python -m pet.identity.bench
Writes out/bench.json.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np

from .face import FacePipeline, cosine
from .voice import (ENROL_PHRASE, SAMPLE_RATE, StillWindow, VoiceEmbedder, VoiceVerifier, load_wav,
                    speech_seconds)

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

TTS_VOICES = ["Samantha", "Daniel", "Karen", "Moira", "Rishi", "Tessa", "Fred", "Ralph"]
TEST_LINES = [
    "I am going to the kitchen to make some tea.",
    "Did you see where I left my keys this morning?",
    "The weather is nice today, let's take a walk.",
]


def _pct(xs, q):
    return float(np.percentile(np.asarray(xs), q))


def bench_face(reps: int) -> dict:
    img = cv2.imread(str(HERE / "samples" / "t1.jpg"))
    if img is None:
        raise SystemExit("samples/t1.jpg missing; run fetch_models.sh")
    res = {}
    fp = FacePipeline(num_threads=2)
    for name, frame in [("t1_1280x886", img), ("t1_1280x720", cv2.resize(img, (1280, 720)))]:
        fp.analyze(frame)  # warm-up
        det, emb, tot = [], [], []
        for _ in range(reps):
            t0 = time.perf_counter()
            faces = fp.analyze(frame)
            tot.append((time.perf_counter() - t0) * 1e3)
            det.append(faces[0].timings_ms["detect"])
            emb.append(faces[0].timings_ms["embed_all"] / max(1, sum(f.usable for f in faces)))
        res[name] = {"faces": len(faces), "detect_ms_p50": _pct(det, 50), "detect_ms_p90": _pct(det, 90),
                     "embed_per_face_ms_p50": _pct(emb, 50), "frame_total_ms_p50": _pct(tot, 50)}

    # Identity sanity: each face vs augmented versions of itself and vs others.
    faces = fp.analyze(img)
    base = [f.embedding for f in faces if f.embedding is not None]
    same, diff = [], []
    augs = {
        "flip": lambda im: cv2.flip(im, 1),
        "dark": lambda im: cv2.convertScaleAbs(im, alpha=0.6, beta=-10),
        "blur": lambda im: cv2.GaussianBlur(im, (5, 5), 1.5),
        "half": lambda im: cv2.resize(cv2.resize(im, None, fx=0.5, fy=0.5), (im.shape[1], im.shape[0])),
        "jpeg30": lambda im: cv2.imdecode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 30])[1], 1),
    }
    for an, fn in augs.items():
        fa = fp.analyze(fn(img))
        for f in fa:
            if f.embedding is None:
                continue
            c = (f.bbox[:2] + f.bbox[2:]) / 2
            if an == "flip":
                c[0] = img.shape[1] - c[0]
            j = int(np.argmin([np.linalg.norm(c - (g.bbox[:2] + g.bbox[2:]) / 2) for g in faces]))
            for k, b in enumerate(base):
                (same if k == j else diff).append(cosine(f.embedding, b))
    res["identity_check"] = {
        "same_face_augmented_cos_min": min(same), "same_face_augmented_cos_mean": float(np.mean(same)),
        "different_people_cos_max": max(diff), "different_people_cos_mean": float(np.mean(diff)),
        "n_same": len(same), "n_diff": len(diff)}

    # IPD gate: shrink until faces fall below 10 px.
    gate = []
    for s in (1.0, 0.5, 0.3, 0.2, 0.15, 0.1):
        small = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        fa = fp.analyze(small)
        gate.append({"scale": s, "detected": len(fa), "usable": sum(f.usable for f in fa),
                     "ipd_px": [round(f.ipd_px, 1) for f in fa]})
    res["ipd_gate"] = gate
    return res


def make_tts(dirp: Path) -> dict[str, dict[str, Path]]:
    """TTS clips per voice: the enrolment phrase at 3 speaking rates (a human
    repeats it with different timing, same pitch) and 3 unrelated test lines."""
    if shutil.which("say") is None or shutil.which("afconvert") is None:
        raise SystemExit("needs macOS say/afconvert")
    dirp.mkdir(parents=True, exist_ok=True)
    clips: dict[str, dict[str, Path]] = {}
    jobs = [(f"enrol{k}", ENROL_PHRASE, rate) for k, rate in enumerate((165, 185, 205))]
    jobs += [(f"test{i + 1}", t, 180) for i, t in enumerate(TEST_LINES)]
    for v in TTS_VOICES:
        clips[v] = {}
        for key, text, rate in jobs:
            aiff = dirp / f"{v}_{key}.aiff"
            wav = dirp / f"{v}_{key}.wav"
            r = subprocess.run(["say", "-v", v, "-r", str(rate), "-o", str(aiff), text], capture_output=True)
            if r.returncode != 0:
                break
            subprocess.run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{SAMPLE_RATE}", "-c", "1",
                            str(aiff), str(wav)], check=True, capture_output=True)
            aiff.unlink()
            clips[v][key] = wav
        if len(clips[v]) != len(jobs):
            del clips[v]
    return clips


def _fit(x: np.ndarray, seconds: float) -> np.ndarray:
    n = int(seconds * SAMPLE_RATE)
    if len(x) >= n:
        return x[:n]
    return np.pad(x, (0, n - len(x)))


def bench_voice(reps: int, keep: bool) -> dict:
    tts = OUT / "tts"
    clips = make_tts(tts)
    emb = VoiceEmbedder(num_threads=2)
    res: dict = {"voices": list(clips), "model": "3dspeaker CAM++ zh+en advanced 16k"}
    x = _fit(load_wav(clips[TTS_VOICES[0]]["test1"]), 2.5)
    emb.embed_speech(x)
    lats = []
    for _ in range(reps):
        lats.append(emb.embed_speech(x).latency_ms)
    res["latency_2p5s_window_ms_p50"] = _pct(lats, 50)
    res["latency_2p5s_window_ms_p90"] = _pct(lats, 90)
    for sec in (2.0, 3.0):
        xs = _fit(load_wav(clips[TTS_VOICES[0]]["test1"]), sec)
        res[f"latency_{sec:.1f}s_window_ms_p50"] = _pct([emb.embed_speech(xs).latency_ms for _ in range(reps)], 50)

    ver = VoiceVerifier(emb)
    for v, c in clips.items():
        ver.enroll(v, [load_wav(c[f"enrol{k}"]) for k in range(3)])
    still = StillWindow()
    still.mark(0.0, False)
    same, diff, rows = [], [], []
    correct = 0
    total = 0
    for v, c in clips.items():
        for k in ("test1", "test2", "test3"):
            w = _fit(load_wav(c[k]), 2.5)
            r, scores = ver.verify_window(w, 0.0, 2.5, still)
            if not r.ok:
                rows.append({"voice": v, "clip": k, "rejected": r.reason})
                continue
            total += 1
            best = max(scores, key=scores.get)
            correct += best == v
            accepted = [kk for kk, sc in scores.items() if sc >= ver.threshold]
            rows.append({"voice": v, "clip": k, "best": best, "own": round(scores[v], 3),
                         "accepted_at_threshold": accepted})
            same.append(scores[v])
            diff.extend(s for kk, s in scores.items() if kk != v)
    res["verification"] = {
        "windows": total, "top1_correct": correct,
        "same_voice_cos_min": min(same), "same_voice_cos_mean": float(np.mean(same)),
        "other_voice_cos_max": max(diff), "other_voice_cos_mean": float(np.mean(diff)),
        "threshold": ver.threshold,
        "false_accepts_at_threshold": sum(len([a for a in r.get("accepted_at_threshold", []) if a != r["voice"]]) for r in rows),
        "false_rejects_at_threshold": sum(1 for r in rows if "own" in r and r["own"] < ver.threshold),
        "rows": rows}
    # Still-window gate.
    still.mark(1.0, True)
    r, _ = ver.verify_window(_fit(load_wav(clips[TTS_VOICES[0]]["test1"]), 2.5), 0.0, 2.5, still)
    res["moving_window_rejected"] = (not r.ok, r.reason)
    if not keep:
        shutil.rmtree(tts, ignore_errors=True)
    return res


def bench_real_wavs(dirp: Path, emb: VoiceEmbedder | None = None) -> dict:
    """Optional: sherpa-onnx's public speaker test clips (<name>-sr-N.wav to
    enrol, <name>-test-sr-N.wav to test). Not stored in the repo."""
    emb = emb or VoiceEmbedder()
    fs = sorted(dirp.glob("*.wav"))
    spk = lambda f: f.name.split("-")[0]
    ver = VoiceVerifier(emb)
    for s in sorted({spk(f) for f in fs}):
        enrol = [load_wav(f) for f in fs if spk(f) == s and "-test-" not in f.name]
        embs = [emb.embed(x) for x in enrol]
        c = np.mean(embs, 0)
        ver.enrolled[s] = c / np.linalg.norm(c)
    out, same, other, ok = [], [], [], 0
    for f in fs:
        if "-test-" not in f.name:
            continue
        x = load_wav(f)
        n = int(3.0 * SAMPLE_RATE)
        if len(x) <= n:
            w = x
        else:  # the 3 s window with the most speech, as a live caller would pick
            starts = range(0, len(x) - n + 1, SAMPLE_RATE // 4)
            w = x[max(starts, key=lambda st: speech_seconds(x[st:st + n])):][:n]
        r = emb.embed_speech(w)
        if not r.ok:
            out.append({"clip": f.name, "rejected": r.reason})
            continue
        sc = {k: float(v @ r.embedding) for k, v in ver.enrolled.items()}
        ok += max(sc, key=sc.get) == spk(f)
        same.append(sc[spk(f)])
        other += [v for k, v in sc.items() if k != spk(f)]
        out.append({"clip": f.name, "scores": {k: round(v, 3) for k, v in sc.items()}})
    return {"dir": str(dirp), "windows": len(same), "top1_correct": ok,
            "same_cos_min": min(same), "other_cos_max": max(other), "rows": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--keep-audio", action="store_true")
    ap.add_argument("--skip-voice", action="store_true")
    ap.add_argument("--real-wavs", type=Path, help="dir with sherpa-onnx <name>-sr-N.wav test clips")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    out = {"machine": f"{platform.machine()} {platform.processor()} {platform.platform()}",
           "cpu": subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True,
                                 text=True).stdout.strip(),
           "threads": 2, "date": time.strftime("%Y-%m-%d %H:%M"),
           "face": bench_face(a.reps)}
    if not a.skip_voice:
        out["voice"] = bench_voice(a.reps, a.keep_audio)
    if a.real_wavs:
        out["voice_real_wavs"] = bench_real_wavs(a.real_wavs)
    (OUT / "bench.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
