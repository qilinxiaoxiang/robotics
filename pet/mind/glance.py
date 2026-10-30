"""Glance: when the head has held still, one head-camera frame -> a short description by a vision model -> a line in the
mind's recent events ("looking left 70 deg, down 20: a black cable lies on the floor ..."). The intention layer reads
text only; this is how what the pet sees reaches it (docs/PET_DEPLOY_PLAN.md stage 2, model route before the detector).

The call is `claude -p` on the subscription with only the Read tool, run in a background thread, so the runner's loop
keeps reading the body while the model looks. Head directions follow walk_brain's head command: head_yaw positive is
to the pet's left; head_pitch negative is up (as-built sim, face-view-20261029).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .backends import HAIKU

STILL_S = 0.8       # the head command must have held this long before a frame counts (spring settle + frame latency)
EVERY_S = 6.0       # at most one glance this often
PROMPT = ("This is one frame from the head camera of a small duck robot, about 25 cm tall, standing on the floor. "
          "Its head is turned {where}. Describe in at most 35 words what is in view that matters to a small pet on "
          "the floor: objects, people, edges, obstacles, cables (say whether a cable looks slack or pulled taut, and "
          "where it runs). Plain words, no preamble. Image: {path}")


def where_text(yaw: float, pitch: float) -> str:
    side = "straight ahead" if abs(yaw) < 0.15 else f"{abs(yaw) * 57.3:.0f} deg to its {'left' if yaw > 0 else 'right'}"
    tilt = "" if abs(pitch) < 0.1 else f", {abs(pitch) * 57.3:.0f} deg {'up' if pitch < 0 else 'down'}"
    return side + tilt


class ClaudeVision:
    name = "claude-cli vision"

    def __init__(self, model=HAIKU, timeout_s=60):
        exe = shutil.which("claude")
        if not exe:
            raise RuntimeError("claude CLI not found")
        self.exe, self.model, self.timeout_s = exe, model, timeout_s

    def describe(self, jpeg: bytes, where: str, prompt: str = PROMPT) -> tuple[str, dict]:
        d = Path(tempfile.mkdtemp(prefix="pet-glance-"))
        img = d / "frame.jpg"
        img.write_bytes(jpeg)
        cmd = [self.exe, "-p", "--model", self.model, "--tools", "Read", "--allowedTools", "Read",
               "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence", "--output-format", "json",
               prompt.format(where=where, path=img)]
        t0 = time.monotonic()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_s, cwd=str(d),
                               env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "pet-glance"})
            out = json.loads(r.stdout)
        finally:
            img.unlink(missing_ok=True)
            d.rmdir()
        if out.get("is_error"):
            raise RuntimeError(str(out.get("result"))[:200])
        return " ".join(str(out.get("result", "")).split()), {"latency_s": round(time.monotonic() - t0, 2),
                                                              "cost_usd": out.get("total_cost_usd")}


class Glancer:
    """Feed it frames and the runner's head command; it fires one description per head pause."""

    def __init__(self, vision, log_path):
        self.vision = vision
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending = None
        self.frame = None          # (t_wall_a7z, jpeg bytes)
        self.head = (0.0, 0.0)
        self.head_since = None     # local wall time the current head command began
        self.done_for = None       # head_since of the pause already described
        self.last_t = 0.0
        self.log = open(log_path, "a")
        self.count = 0

    def set_head(self, yaw: float, pitch: float, now: float):
        h = (round(yaw, 3), round(pitch, 3))
        if h != self.head or self.head_since is None:
            self.head, self.head_since = h, now

    def feed_frame(self, t: float, jpeg: bytes, now: float):
        self.frame = (t, jpeg, now)

    def poll(self, now: float, active: bool) -> list[str]:
        out = []
        if self.pending is not None and self.pending[0].done():
            fut, where, t_req = self.pending
            self.pending = None
            try:
                text, meta = fut.result()
                out.append(f"looking {where}, I saw: {text}")
                self.log.write(json.dumps({"t": round(t_req, 2), "where": where, "text": text, **meta}) + "\n")
                self.count += 1
            except Exception as e:
                self.log.write(json.dumps({"t": round(t_req, 2), "where": where, "error": str(e)[:200]}) + "\n")
            self.log.flush()
        if (active and self.pending is None and self.frame is not None and self.head_since is not None
                and self.done_for != self.head_since and now - self.head_since >= STILL_S
                and now - self.last_t >= EVERY_S and self.frame[2] - self.head_since >= STILL_S):
            where = where_text(*self.head)
            self.pending = (self.pool.submit(self.vision.describe, self.frame[1], where), where, now)
            self.done_for, self.last_t = self.head_since, now
        return out

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.log.close()
