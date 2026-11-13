"""The detector the pickup uses: the colour filter is fast and proposes, the learned detector decides.

Shawn 2026-11-12: "该下yolo下yolo"; "检测不到是不是因为没有用YOLO，还在用颜色滤镜". The colour filter (orange_target, a few
ms) took the orange inside of the robot's own foot, a far wall and the floor for the ball, and misses a far ball whose
blob is under its area limit. The learned detector (learned_target, YOLO-World s, text prompt "small orange ball")
found every ball in the frames of 2026-11-12 and none of the feet, but one frame costs about 1.05 s on the A7Z
(1 thread, measured 2026-11-12), too slow to steer a walk.

  detect(frame, accept)
    colour candidate near a confirmed sighting (TRACK_PX, TRACK_S)  -> the colour box, no learned pass
    otherwise at most one learned pass every LEARNED_EVERY_S        -> its box, or None
    a colour candidate the learned detector did not confirm         -> None

So a new object costs one learned pass before the robot acts on it, a tracked one is followed at camera rate, and an
empty picture is searched by the learned detector about once a second.
"""
import math
import time

import learned_target
import orange_target

TRACK_PX = 110          # px: a colour box this near the last confirmed or tracked centre is the same object
TRACK_S = 1.5           # s: how long a sighting stays good without a new one
LEARNED_EVERY_S = 1.0   # s: least time between the starts of two learned passes


class BallDetect:
    def __init__(self, hsv_lo, hsv_hi, min_area, now=time.time, learned=learned_target.detect,
                 colour=orange_target.detect):
        self.lo, self.hi, self.min_area, self.now = hsv_lo, hsv_hi, min_area, now
        self.learned, self.colour = learned, colour
        self.track = None        # (cx, cy, t) of the last confirmed or tracked sighting
        self.t_learned = -1e9
        self.stats = dict(colour=0, tracked=0, learned=0, learned_hits=0, rejected=0)

    def _near(self, c, t):
        return (self.track is not None and t - self.track[2] <= TRACK_S
                and math.hypot(c["cx"] - self.track[0], c["cy"] - self.track[1]) <= TRACK_PX)

    def __call__(self, frame, accept=None):
        t = self.now()
        c = self.colour(frame, self.lo, self.hi, self.min_area, accept=accept)
        if c is not None:
            self.stats["colour"] += 1
            if self._near(c, t):
                self.track = (c["cx"], c["cy"], t)
                self.stats["tracked"] += 1
                return c
        if t - self.t_learned < LEARNED_EVERY_S:
            return None
        self.t_learned = t
        self.stats["learned"] += 1
        y = self.learned(frame, accept=accept)
        t = self.now()
        if y is None:
            if c is not None:
                self.stats["rejected"] += 1
            return None
        self.stats["learned_hits"] += 1
        self.track = (y["cx"], y["cy"], t)
        return y
