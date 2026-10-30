"""Record the live head-camera stream to a frame directory for offline tests (png per frame + frames.jsonl with the
frame index, capture time and arrival time), through the same ssh-a7z source tracker.py uses.

  record.py testdata/live_home --duration 30
"""
import argparse
import json
import os
import sys
import time

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tracker import SshA7zSource  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--host", default="a7z")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    src = SshA7zSource(a.host)
    t0, n = time.time(), 0
    with open(os.path.join(a.out, "frames.jsonl"), "w") as log:
        for img, t_cap, idx, t_arr, skipped in src.frames():
            cv2.imwrite(os.path.join(a.out, f"f{idx:06d}.png"), img)
            log.write(json.dumps({"frame": idx, "t_cap": t_cap, "t_arr": t_arr, "skipped": skipped}) + "\n")
            n += 1
            if time.time() - t0 >= a.duration:
                break
    src.close()
    print(f"{n} frames in {time.time() - t0:.1f} s -> {a.out}, clock offset {src.offset:+.3f} s")


if __name__ == "__main__":
    main()
