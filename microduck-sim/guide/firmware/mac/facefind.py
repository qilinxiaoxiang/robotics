"""Face finder for the duck's eye: the newest published camera frame -> where the nearest face is, as angles off the
camera axis, a few times a second on the A7Z CPU.

Reads the 640 x 360 BGR frame that a7z_cam.py publishes in /dev/shm (holding the daemon alive while this runs), runs
the SCRFD-500MF detector of pet/identity (InsightFace buffalo_sc, ONNX, the same files the owner enrolment uses; no
embedding here) and keeps the largest face: 120 ms per frame on the A7Z at the 640 px detector size on 2026-10-30
(first live frame), so RATE_HZ 4 costs about half of one core. namecall.py's attention phase reads latest() at
50 Hz and turns the angles into head commands (NAMECALL.md 12).

Angles: the U20CAM is an equidistant fisheye with f = 359.5 px (face-view-20261029/README.md), so a pixel r from the
centre lies r / f rad off the axis; a face right of centre gives yaw_err > 0 (turn the head right, i.e. head_yaw
down), a face above the centre gives pitch_err > 0 (look up).
"""
import os
import sys
import threading
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
for p in (HERE, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

F_PX = 359.5          # equidistant fisheye focal length, 640 x 360 frame (manual: 102 deg horizontal field)
RATE_HZ = 4.0         # detector runs on at most this many frames per second
DET_SIZE = 640        # SCRFD input; 320 halves the time but loses faces under about 24 px (a standing adult past 1 m)
STALE_S = 1.0         # a result older than this is not a sighting any more


def face_angles(bbox, w, h, f_px=F_PX):
    """(yaw_err, pitch_err, size) in rad for a face box (x1, y1, x2, y2) in a w x h frame: + right, + up; size = the
    box height as an angle."""
    x1, y1, x2, y2 = [float(v) for v in bbox]
    cx, cy = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
    return (cx - 0.5 * w) / f_px, (0.5 * h - cy) / f_px, (y2 - y1) / f_px


class FaceFinder:
    """Background thread: frames -> self.latest(): None, or dict(t, yaw_err, pitch_err, size, score, ms, n) for the
    largest face in the newest analysed frame (t = that frame's capture time); faces() lists the last frame's faces.

    pipeline: an object with detect(img_bgr, max_num) -> (dets (n, 5) x1 y1 x2 y2 score, kps); the default is
    pet.identity.face.FacePipeline. frames: a callable returning (bytes, t, idx) or None (a7z_cam.read_frame).
    """

    def __init__(self, pipeline=None, frames=None, hold=None, rate_hz=RATE_HZ, det_size=DET_SIZE, shape=None, now=time.time):
        self.pipeline, self.frames, self.hold_fn, self.now = pipeline, frames, hold, now
        self.rate_hz, self.det_size, self.shape = rate_hz, det_size, shape
        self.lock = threading.Lock()
        self.result = None
        self.last_idx = None
        self.n_frames = 0
        self.ms = []
        self.err = None
        self.release = None
        self.stop_ev = threading.Event()
        self.thread = None

    # --- lifecycle
    def start(self):
        if self.frames is None or self.hold_fn is None or self.shape is None:
            import a7z_cam
            self.frames = self.frames or a7z_cam.read_frame
            self.hold_fn = self.hold_fn or a7z_cam.hold
            self.shape = self.shape or (a7z_cam.H, a7z_cam.W)
        if self.pipeline is None:
            from pet.identity.face import FacePipeline
            self.pipeline = FacePipeline(det_size=self.det_size)
        self.release = self.hold_fn()
        self.thread = threading.Thread(target=self._loop, name="facefind", daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.stop_ev.set()
        if self.thread is not None:
            self.thread.join(timeout=2.0)
        if self.release is not None:
            try:
                self.release()
            except Exception:
                pass
            self.release = None

    # --- results
    def latest(self, now=None, stale_s=STALE_S):
        """The newest sighting, or None when there is none or it is older than stale_s."""
        with self.lock:
            r = self.result
        if r is None or "yaw_err" not in r:
            return None
        if (self.now() if now is None else now) - r["t"] > stale_s:
            return None
        return r

    def faces(self):
        with self.lock:
            return list(self.result["faces"]) if self.result else []

    # --- work
    def analyse(self, img, t):
        """One frame -> the result dict (also stored); used by the thread and by tests."""
        h, w = img.shape[:2]
        t0 = time.perf_counter()
        try:
            dets, _ = self.pipeline.detect(img, max_num=0)
        except Exception as e:      # a detector failure must not take the listener down
            self.err = repr(e)
            return None
        ms = (time.perf_counter() - t0) * 1000.0
        self.ms.append(ms)
        if len(self.ms) > 200:
            del self.ms[:100]
        faces = []
        for d in np.asarray(dets).reshape(-1, 5):
            yaw, pitch, size = face_angles(d[:4], w, h)
            faces.append(dict(yaw_err=round(yaw, 4), pitch_err=round(pitch, 4), size=round(size, 4), score=round(float(d[4]), 3)))
        faces.sort(key=lambda f: -f["size"])
        res = dict(t=t, ms=round(ms, 1), n=len(faces), faces=faces)
        if faces:
            res.update({k: faces[0][k] for k in ("yaw_err", "pitch_err", "size", "score")})
        with self.lock:
            # keep the last sighting when this frame has none: latest() ages it out by STALE_S
            if faces or self.result is None or "yaw_err" not in self.result:
                self.result = res
            else:
                self.result = dict(self.result, seen_t=t, ms=res["ms"], n=0)
        self.n_frames += 1
        return res

    def _loop(self):
        period = 1.0 / self.rate_hz
        h, w = self.shape
        next_t = 0.0
        while not self.stop_ev.is_set():
            now = time.monotonic()
            if now < next_t:
                time.sleep(min(0.02, next_t - now))
                continue
            fr = self.frames()
            if fr is None or fr[2] == self.last_idx:
                time.sleep(0.02)
                continue
            self.last_idx = fr[2]
            next_t = now + period
            img = np.frombuffer(fr[0], np.uint8).reshape(h, w, 3)
            self.analyse(img, fr[1])

    def stats(self):
        ms = self.ms[-50:]
        return dict(frames=self.n_frames, ms_mean=round(float(np.mean(ms)), 1) if ms else None, err=self.err)


if __name__ == "__main__":
    # live check on the A7Z: print sightings for a few seconds
    ff = FaceFinder().start()
    try:
        t_end = time.time() + float(sys.argv[1]) if len(sys.argv) > 1 else time.time() + 10
        while time.time() < t_end:
            time.sleep(0.25)
            r = ff.latest()
            print(time.strftime("%H:%M:%S"), ff.stats(), None if r is None else {k: r[k] for k in ("yaw_err", "pitch_err", "size", "score", "ms")},
                  flush=True)
    finally:
        ff.stop()
