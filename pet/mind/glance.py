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
EVERY_S = 4.0       # at most one glance this often
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


FISHEYE_F_PX = 359.5    # U20CAM equidistant fisheye focal length on the 640 x 360 published frame (face-view-20261029)
FRAME_W = 640
SCENE_PROMPT = ("This is one frame from the head camera of a small duck robot, about 25 cm tall, standing on the floor. "
                "Its head is turned {where}. Answer with one JSON object and nothing else: "
                "{{\"person\": true|false, \"person_x\": <horizontal centre of the nearest person as a fraction of "
                "the image width from the left, or null>, \"things\": [{{\"name\": \"<2-4 words: doorway, desk, "
                "chair, bed, box, wall corner ...>\", \"x\": <fraction from the left>}}] (at most 4, the biggest or "
                "most useful for finding its way), \"blocked\": true|false (a wall or object within about 20 cm, "
                "filling the lower half of the picture), \"summary\": \"<under 20 words>\"}}. Image: {path}")


def bearing_in_frame(x_frac: float) -> float:
    """Degrees left of the camera axis for a point at x_frac of the image width (left of picture = + = left)."""
    return (0.5 - float(x_frac)) * FRAME_W / FISHEYE_F_PX * 57.2958


def rel_text(rel_deg: float) -> str:
    r = (rel_deg + 180.0) % 360.0 - 180.0
    if abs(r) < 15:
        return "ahead"
    if abs(r) > 150:
        return "behind you"
    return f"{abs(r):.0f} deg to your {'left' if r > 0 else 'right'}"


class Scene:
    """What the pet has seen, by direction. Feed it frames, the head command and the body heading (degrees from the
    session start, + = left; tether.Tether.yaw_deg); at each head pause it asks the vision model once and keeps a small
    map of directions: the person (taken to be the owner: the only person at home at night, stated in the note) and
    up to a dozen things. Directions are world bearings in the start frame, so they stay right when the body turns."""

    PERSON_KEEP_S = 120.0
    THING_KEEP_S = 600.0

    def __init__(self, vision, log_path):
        self.vision = vision
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending = None
        self.frame = None          # (t_a7z, jpeg bytes, local receive time)
        self.head = (0.0, 0.0)
        self.head_since = None
        self.done_for = None
        self.last_t = 0.0
        self.body_deg = 0.0
        self.log = open(log_path, "a")
        self.count = 0
        self.person = None         # (world bearing deg, local time)
        self.things = {}           # name -> (world bearing deg, local time)
        self.blocked_at = None     # world bearing deg where the last glance saw a wall within ~20 cm

    def set_head(self, yaw: float, pitch: float, now: float):
        h = (round(yaw, 3), round(pitch, 3))
        if h != self.head or self.head_since is None:
            self.head, self.head_since = h, now

    def set_body(self, body_deg: float, now: float, turning: bool):
        if turning or abs(body_deg - self.body_deg) > 3.0:
            self.head_since = now      # the body moved: wait for the picture to settle again
        self.body_deg = body_deg

    def feed_frame(self, t: float, jpeg: bytes, now: float):
        self.frame = (t, jpeg, now)

    def busy(self) -> bool:
        return self.pending is not None

    def poll(self, now: float, active: bool) -> list[dict]:
        """-> results: {"text", "person_rel", "blocked"}; also fires the next look when the head has held still."""
        out = []
        if self.pending is not None and self.pending[0].done():
            fut, where, t_req, body_deg, head_yaw = self.pending
            self.pending = None
            try:
                text, meta = fut.result()
                ans = json.loads(text[text.index("{"):text.rindex("}") + 1])
                out.append(self._take(ans, where, now, body_deg, head_yaw))
                self.log.write(json.dumps({"t": round(t_req, 2), "where": where, "body_deg": round(body_deg, 1),
                                           "answer": ans, **meta}) + "\n")
                self.count += 1
            except Exception as e:
                self.log.write(json.dumps({"t": round(t_req, 2), "where": where, "error": str(e)[:200]}) + "\n")
            self.log.flush()
        if (active and self.pending is None and self.frame is not None and self.head_since is not None
                and self.done_for != self.head_since and now - self.head_since >= STILL_S
                and now - self.last_t >= EVERY_S and self.frame[2] - self.head_since >= STILL_S):
            where = where_text(*self.head)
            self.pending = (self.pool.submit(self.vision.describe, self.frame[1], where, SCENE_PROMPT), where, now,
                            self.body_deg, self.head[0])
            self.done_for, self.last_t = self.head_since, now
        return out

    def _take(self, ans: dict, where: str, now: float, body_deg: float, head_yaw: float) -> dict:
        axis = body_deg + head_yaw * 57.2958
        res = {"text": f"looking {where}: {ans.get('summary', '')}".strip(), "person_rel": None,
               "blocked": bool(ans.get("blocked"))}
        if ans.get("person") and ans.get("person_x") is not None:
            b = axis + bearing_in_frame(ans["person_x"])
            self.person = (b, now)
            res["person_rel"] = b - self.body_deg
            res["text"] += f" A person is there ({rel_text(b - self.body_deg)}); I take it to be my owner."
        for th in (ans.get("things") or [])[:4]:
            try:
                self.things[str(th["name"])[:30]] = (axis + bearing_in_frame(th["x"]), now)
            except (KeyError, TypeError, ValueError):
                continue
        if len(self.things) > 12:
            for k in sorted(self.things, key=lambda k: self.things[k][1])[:len(self.things) - 12]:
                del self.things[k]
        self.blocked_at = axis if res["blocked"] else (None if abs(axis - (self.blocked_at or 1e9)) < 30 else
                                                       self.blocked_at)
        return res

    def person_rel(self, now: float) -> float | None:
        """Degrees from where the body faces now to the person last seen (+ = left), or None if too old."""
        if self.person is None or now - self.person[1] > self.PERSON_KEEP_S:
            return None
        return (self.person[0] - self.body_deg + 180.0) % 360.0 - 180.0

    def describe(self, now: float) -> str:
        parts = []
        pr = self.person_rel(now)
        if pr is not None:
            parts.append(f"my owner (a person) {rel_text(pr)}, seen {now - self.person[1]:.0f} s ago")
        for name, (b, t) in sorted(self.things.items(), key=lambda kv: -kv[1][1]):
            if now - t <= self.THING_KEEP_S:
                parts.append(f"{name} {rel_text(b - self.body_deg)}")
        if self.blocked_at is not None:
            parts.append(f"something within 20 cm {rel_text(self.blocked_at - self.body_deg)}")
        return ("Around you, relative to where you face now: " + "; ".join(parts[:10]) + ".") if parts else \
            "You have not looked around yet: you do not know what is around you."

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.log.close()
