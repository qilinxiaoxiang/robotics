"""Owner-identity demo.

Live, webcam + microphone (run from Terminal.app; it needs camera and
microphone permission under System Settings > Privacy & Security):
    pet/.venv/bin/python -m pet.identity.demo
  keys: q quit | c consolidate now (the nightly step) | m toggle "robot moving"
        (voice is not verified while moving) | s save a screenshot to out/

Recorded input instead of devices (also used to test this file headlessly):
    pet/.venv/bin/python -m pet.identity.demo --video clip.mp4 --wav speech.wav --headless

Synthetic embedding days (no camera, no microphone):
    pet/.venv/bin/python -m pet.identity.demo --synthetic

Enrol the owner first with enroll_face / enroll_voice (same --db).
Nothing but embeddings is written to the database. Screenshots are saved only
when you press s.
"""
from __future__ import annotations

import argparse
import collections
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DEFAULT_DB = HERE / "data" / "identity.sqlite"
TRACK_SAME_COS = 0.30   # below this the "same track" face is someone else


def iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def put_lines(frame, lines, scale=0.6):
    """White text on a dark band (readable over any background)."""
    h = int(26 * scale / 0.6)
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 8 + h * len(lines)), (0, 0, 0), -1)
    for i, s in enumerate(lines):
        cv2.putText(frame, s, (10, h * (i + 1)), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)


class AudioSource:
    """Rolling 16 kHz mono buffer from the microphone or a WAV file (played in real time)."""

    def __init__(self, wav: Path | None, seconds: float = 6.0):
        from .voice import SAMPLE_RATE
        self.sr = SAMPLE_RATE
        self.buf = collections.deque(maxlen=int(seconds * self.sr))
        self.lock = threading.Lock()
        self.t_last = 0.0
        self.stream = None
        self._stop = False
        if wav is not None:
            from .voice import load_wav
            data = load_wav(wav)
            threading.Thread(target=self._play, args=(data,), daemon=True).start()
        else:
            import sounddevice as sd
            self.stream = sd.InputStream(samplerate=self.sr, channels=1, dtype="float32",
                                         blocksize=1600, callback=self._cb)
            self.stream.start()

    def _cb(self, indata, frames, t, status):
        with self.lock:
            self.buf.extend(indata[:, 0])
            self.t_last = time.time()

    def _play(self, data):
        step = 1600
        for i in range(0, len(data), step):
            if self._stop:
                return
            with self.lock:
                self.buf.extend(data[i:i + step])
                self.t_last = time.time()
            time.sleep(step / self.sr)

    def last(self, seconds: float) -> tuple[np.ndarray, float]:
        with self.lock:
            n = int(seconds * self.sr)
            x = np.array(self.buf, dtype=np.float32)[-n:]
            return x, self.t_last

    def close(self):
        self._stop = True
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()


def run_live(a):
    from .face import FacePipeline
    from .memory import FamiliarityMemory
    from .voice import StillWindow, VoiceEmbedder
    from .whois import Whois, scores_against

    mem = FamiliarityMemory(a.db)
    if mem.owner_id() is None:
        print("note: no owner enrolled in", a.db, "- run enroll_face / enroll_voice first; "
              "everyone will be 'stranger' or 'unsure'.")
    fp = FacePipeline()
    voice = None if a.no_mic else VoiceEmbedder()
    still = StillWindow()
    moving = False

    if a.video:
        cap = cv2.VideoCapture(str(a.video))
    else:
        cap = cv2.VideoCapture(a.camera)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        sys.exit("Camera/video not available. From Terminal.app, allow camera access "
                 "(System Settings > Privacy & Security > Camera) and retry.")
    audio = None
    if voice is not None:
        try:
            audio = AudioSource(a.wav)
        except Exception as e:  # no mic permission / device
            print(f"microphone unavailable ({e}); continuing face-only")
            voice = None

    track_id, track_box, track_emb, whois = 0, None, None, Whois()
    last_face_store = 0.0
    last_face_obs = 0.0
    last_voice_t = 0.0
    voice_status = "voice: waiting"
    decision = whois.decide(time.time(), mem.label)
    frames = 0
    lat = collections.deque(maxlen=30)
    log_rows = []
    OUT.mkdir(exist_ok=True)
    t_start = time.time()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            now = time.time()
            frames += 1
            still.mark(now, moving)
            t0 = time.perf_counter()
            faces = fp.analyze(frame)
            lat.append((time.perf_counter() - t0) * 1e3)
            usable = [f for f in faces if f.embedding is not None]
            main = max(usable, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])) if usable else None
            if main is not None:
                # New track when the box jumps or the face embedding changes: a
                # track must never hold two people, because memory merges
                # persons seen in one track.
                if (track_box is None or iou(track_box, main.bbox) < 0.3
                        or float(track_emb @ main.embedding) < TRACK_SAME_COS):
                    track_id += 1
                    track_emb = main.embedding.copy()
                    whois = Whois()  # new person in view: start from unsure
                track_box = main.bbox
                track_emb = track_emb * 0.8 + main.embedding * 0.2
                track_emb /= np.linalg.norm(track_emb)
                if now - last_face_obs >= 0.25:   # <= 4 Hz: frames are correlated
                    whois.observe(now, "face", scores_against(mem.centroids("face"), main.embedding),
                                  main.quality)
                    last_face_obs = now
                if now - last_face_store > 1.0:   # at most 1 face sample/s into memory
                    mem.add_sample(now, "face", main.embedding, main.quality,
                                   provisional_id=decision.label, track=f"live{int(t_start)}-{track_id}")
                    last_face_store = now
            # voice: every second, on the last 2.5 s, only in still windows
            if voice is not None and now - last_voice_t > 1.0:
                last_voice_t = now
                x, t_end = audio.last(2.5)
                if len(x) >= int(2.4 * 16000):
                    if not still.is_still(t_end - 2.5, t_end):
                        voice_status = "voice: skipped (robot moving)"
                    else:
                        r = voice.embed_speech(x)
                        if r.ok:
                            sc = scores_against(mem.centroids("voice"), r.embedding)
                            whois.observe(now, "voice", sc, r.quality)
                            mem.add_sample(now, "voice", r.embedding, r.quality, provisional_id=decision.label,
                                           track=f"live{int(t_start)}-{track_id}" if main is not None else None)
                            best = max(sc.items(), key=lambda kv: kv[1]) if sc else None
                            voice_status = (f"voice: {r.speech_s:.1f}s speech, {r.latency_ms:.0f} ms, best "
                                            + (f"{mem.label(best[0])} {best[1]:.2f}" if best else "n/a"))
                        else:
                            voice_status = f"voice: {r.reason}"
            decision = whois.decide(now, mem.label)
            fam = mem.familiarity(decision.person_id, now) if decision.person_id else 0.0

            for f in faces:
                x1, y1, x2, y2 = f.bbox.astype(int)
                col = (0, 200, 0) if f.usable else (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
                for p in f.kps.astype(int):
                    cv2.circle(frame, tuple(p), 2, (0, 255, 255), -1)
                txt = f"IPD {f.ipd_px:.0f}px p{f.pitch_deg:+.0f} y{f.yaw_deg:+.0f}"
                if not f.usable:
                    txt += " (too small)"
                cv2.putText(frame, txt, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
            lines = [f"who: {decision.label}  conf {decision.confidence:.2f}  familiarity {fam:.2f}",
                     voice_status,
                     f"face {np.median(lat):.0f} ms/frame | track {track_id} | {'MOVING' if moving else 'still'}"
                     f" | q quit c consolidate m move s shot"]
            put_lines(frame, lines)
            log_rows.append((frames, decision.label, round(decision.confidence, 3), len(faces),
                             [round(f.ipd_px, 1) for f in faces], voice_status))

            if a.headless:
                if frames in a.save_frames:
                    cv2.imwrite(str(OUT / f"demo_frame_{frames:04d}.jpg"), frame)
                if a.max_frames and frames >= a.max_frames:
                    break
                if a.video and a.wav:
                    time.sleep(1 / 15)  # roughly real time so the WAV player keeps pace
                continue
            cv2.imshow("pet identity", frame)
            k = cv2.waitKey(1) & 0xFF
            if k == ord("q"):
                break
            if k == ord("m"):
                moving = not moving
            if k == ord("s"):
                p = OUT / f"demo_{time.strftime('%Y%m%d-%H%M%S')}.jpg"
                cv2.imwrite(str(p), frame)
                print("saved", p)
            if k == ord("c"):
                print("consolidate:", mem.consolidate())
    finally:
        cap.release()
        if audio:
            audio.close()
        cv2.destroyAllWindows()
    print(f"{frames} frames, face pipeline median {np.median(lat):.1f} ms/frame")
    for r in log_rows[:: max(1, len(log_rows) // 10)]:
        print("  frame", *r)
    print("final:", decision.label, f"{decision.confidence:.2f}")
    mem.close()
    return log_rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--synthetic", action="store_true", help="replay generated embedding days")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--video", type=Path, help="video file instead of the webcam")
    ap.add_argument("--wav", type=Path, help="16 kHz WAV instead of the microphone")
    ap.add_argument("--no-mic", action="store_true")
    ap.add_argument("--headless", action="store_true", help="no window (recorded input)")
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--save-frames", type=int, nargs="*", default=[])
    a = ap.parse_args(argv)
    if a.synthetic:
        from .synth import run_synthetic
        run_synthetic(days=a.days, seed=a.seed, out_dir=OUT)
        print(f"\nwrote {OUT / 'synthetic_familiarity.png'} and {OUT / 'synthetic_run.json'}")
        return
    run_live(a)


if __name__ == "__main__":
    main()
