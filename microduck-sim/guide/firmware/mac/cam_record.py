"""Record every published camera frame of a robot run, so a run can be watched again afterwards.

Shawn 2026-11-12: "所以你只会截图，完全不看视频是吧". Until now nothing kept the camera picture: a run could only be judged
from single snapshots taken by hand. This reads the shared frame a7z_cam.py publishes (10 fps, 640 x 360 BGR) and writes
each new one as a JPEG named by its wall-clock time, which is the same clock as the "t" of the walk_wired and seepick
logs, so a frame is matched to the head pose and the phase of that moment.

  ~/.venvs/duck-policy/bin/python cam_record.py NAME [--max-s 300]     on the A7Z; frames in ~/duck-video/NAME/
Stops after --max-s, on SIGTERM, or when the camera daemon stops publishing for 5 s.
Copy the directory to the Mac to look at it; never build sheets or videos on the A7Z.
"""
import argparse
import os
import signal
import time

import cv2
import numpy as np

SHM = "/dev/shm/a7z_cam.bgr"
W, H, HDR = 640, 360, 16


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("--max-s", type=float, default=300.0)
    p.add_argument("--quality", type=int, default=70)
    a = p.parse_args()
    out = os.path.expanduser(f"~/duck-video/{a.name}")
    os.makedirs(out, exist_ok=True)
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    t0, last, last_new, n = time.time(), None, time.time(), 0
    while not stop and time.time() - t0 < a.max_s:
        try:
            m = os.path.getmtime(SHM)
        except OSError:
            m = None
        if m is not None and m != last:
            raw = open(SHM, "rb").read()
            if len(raw) >= HDR + W * H * 3:
                img = np.frombuffer(raw, np.uint8, W * H * 3, HDR).reshape(H, W, 3)
                cv2.imwrite(os.path.join(out, f"{m:.3f}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, a.quality])
                last, last_new, n = m, time.time(), n + 1
        elif time.time() - last_new > 5.0:
            break
        time.sleep(0.03)
    print(f"cam_record: {n} frames in {out} over {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    os.nice(15)
    main()
