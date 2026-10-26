"""Enrol the owner's face from 5 angles, including from below.

Amazon Astro registers a face from several head poses. MicroDuck's camera
sits ~15 cm above the floor, so it mostly sees a standing person from below,
where MobileFaceNet degrades past 15-30 deg upward pitch. Two of the five
poses therefore put the camera low.

Live (run from Terminal.app, which needs camera permission):
    pet/.venv/bin/python -m pet.identity.enroll_face --name shawn
Offline (testing, or photos you took of yourself):
    pet/.venv/bin/python -m pet.identity.enroll_face --name shawn --images a.jpg b.jpg ...

Only embeddings are stored (pet/identity/data/identity.sqlite); frames are not.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from .face import Face, FacePipeline
from .memory import FamiliarityMemory

DEFAULT_DB = Path(__file__).resolve().parent / "data" / "identity.sqlite"

POSES = [
    ("front", "Camera at eye level. Look straight at it."),
    ("left", "Camera at eye level. Turn your head a little to YOUR left, keep eyes on the lens."),
    ("right", "Camera at eye level. Turn your head a little to YOUR right, keep eyes on the lens."),
    ("below", "Hold the camera at chest height or lower and look DOWN at it (the robot's usual view)."),
    ("floor", "Put the camera on the floor ~1 m in front of you, stand, and look down at it."),
]
PER_POSE = 3
MIN_QUALITY = 0.25


def best_face(faces: list[Face]) -> Face | None:
    usable = [f for f in faces if f.usable and f.embedding is not None]
    if not usable:
        return None
    return max(usable, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))


def draw(frame, f: Face | None, lines: list[str]):
    if f is not None:
        x1, y1, x2, y2 = f.bbox.astype(int)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
        for p in f.kps.astype(int):
            cv2.circle(frame, tuple(p), 2, (0, 255, 255), -1)
    from .demo import put_lines
    put_lines(frame, lines)


def enrol_live(fp: FacePipeline, camera: int) -> list[tuple[str, Face]]:
    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        sys.exit("Camera not available. Run from Terminal.app and allow camera access "
                 "(System Settings > Privacy & Security > Camera).")
    got: list[tuple[str, Face]] = []
    try:
        for name, prompt in POSES:
            print(f"\n[{name}] {prompt}\n  Press SPACE to capture, q to abort.")
            taken: list[Face] = []
            capturing = False
            last = 0.0
            while len(taken) < PER_POSE:
                ok, frame = cap.read()
                if not ok:
                    continue
                f = best_face(fp.analyze(frame))
                status = "no usable face" if f is None else \
                    f"IPD {f.ipd_px:.0f}px pitch {f.pitch_deg:+.0f} yaw {f.yaw_deg:+.0f} q {f.quality:.2f}"
                draw(frame, f, [f"pose {name}: {prompt[:70]}", status,
                                f"captured {len(taken)}/{PER_POSE}  " + ("capturing..." if capturing else "SPACE to start")])
                cv2.imshow("enrol face", frame)
                k = cv2.waitKey(1) & 0xFF
                if k == ord("q"):
                    sys.exit("aborted, nothing stored")
                if k == ord(" "):
                    capturing = True
                now = time.time()
                if capturing and f is not None and f.quality >= MIN_QUALITY and now - last > 0.4:
                    taken.append(f)
                    last = now
                    print(f"  got {len(taken)}: {status}")
            got += [(name, f) for f in taken]
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return got


def enrol_images(fp: FacePipeline, paths: list[str]) -> list[tuple[str, Face]]:
    got = []
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            print(f"skip {p}: unreadable")
            continue
        f = best_face(fp.analyze(img))
        if f is None:
            print(f"skip {p}: no usable face (IPD >= 10 px)")
            continue
        got.append((Path(p).stem, f))
    return got


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="owner")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--images", nargs="*")
    a = ap.parse_args(argv)
    fp = FacePipeline()
    got = enrol_images(fp, a.images) if a.images else enrol_live(fp, a.camera)
    if len(got) < 3:
        sys.exit(f"only {len(got)} usable faces; need >= 3")
    embs = np.stack([f.embedding for _, f in got])
    c = embs.mean(0)
    c /= np.linalg.norm(c)
    print("\npose        IPD   pitch  yaw   quality  cos-to-mean")
    for (name, f), e in zip(got, embs):
        print(f"{name:10s} {f.ipd_px:5.0f} {f.pitch_deg:+6.0f} {f.yaw_deg:+5.0f}  {f.quality:6.2f}   {float(e @ c):.3f}")
    low = [f for n, f in got if n in ("below", "floor")]
    if low and max(f.pitch_deg for f in low) < 5:
        print("note: the low-camera poses did not measure an upward view (pitch < +5 deg); "
              "the pitch estimate is rough, but consider redoing them with the camera lower.")
    mem = FamiliarityMemory(a.db)
    pid = mem.register_owner(a.name)
    mem.enroll(pid, "face", [f.embedding for _, f in got], quality=1.0)
    print(f"\nenrolled {len(got)} face embeddings for owner '{a.name}' (person {pid}) in {a.db}")
    mem.close()


if __name__ == "__main__":
    main()
