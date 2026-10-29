"""Perception in: sensor records from the robot -> mind percepts (pet/state/README.md event kinds).

While the brain runs it owns the servo bus and the head touch pads, so the pads arrive in its tick log (`touch`, raw
counts of L1 R1 L2 R2 M; CURRENT-STATE a7z_touch_bus), and duck_sense.py, which reads the same pads and IMU while no
brain runs, has quit. The adapters here therefore take the brain's rows (touch counts, body gyro) and the remote agent's
extra records (sound levels, camera frames); a duck_sense.py line, when one is available, feeds the same bump detector.

- TouchDetector: pad counts rise over their rest baseline (hold.py PAD_LO) -> one `touch` per press.
- BumpDetector: a body-gyro spike while the pet holds still -> `bump` (not in the reflex table: the mind only notes it).
- SoundOnset: a level step over the running floor -> `sound` (label `noise`, direction from the front/back pair when
  both read).
- FaceAdapter: frames -> `face` / `face_lost` through pet/identity when its models and database exist, else through
  the `recognise` callable handed in (tests).
- ScriptedEvents: events at offsets from the session start, for the dry run and the simulated day.
"""
from __future__ import annotations

import base64
import json
import math
import time
from pathlib import Path

PADS = ("L1", "R1", "L2", "R2", "M")
PAD_LO = 150.0          # counts over the rest baseline that count as a touch (hold.py default before calibration)
BASELINE_TAU_S = 5.0    # rest baseline tracking of untouched pads (hold.py BASELINE_TAU)
TOUCH_MIN_S = 0.15      # a press must last this long
TOUCH_RELEASE_S = 0.3   # pads back under the threshold this long end the press
SIDE = {"L1": "left", "L2": "left", "R1": "right", "R2": "right", "M": "head"}
BUMP_GYRO = 2.5         # rad/s body rate while the pet holds still (quiet stand61 reads under 0.5)
BUMP_QUIET_S = 2.0      # one bump per this many seconds
SOUND_STEP_DB = 10.0    # onset: level this far over the running floor
SOUND_FLOOR_TAU_S = 4.0
SOUND_QUIET_S = 2.0
FACE_SEEN_FRAMES = 2    # consecutive frames with the same person before a `face` event
FACE_LOST_S = 5.0


class TouchDetector:
    def __init__(self, pad_lo=None):
        self.pad_lo = list(pad_lo) if pad_lo else [PAD_LO] * len(PADS)
        self.base = None
        self.last_t = None
        self.on_since = None
        self.off_since = None
        self.pressed = None
        self.events = 0

    def feed(self, counts, t: float) -> list[dict]:
        if not counts or len(counts) != len(PADS) or any(c is None for c in counts):
            return []
        counts = [float(c) for c in counts]
        if self.base is None:
            self.base = list(counts)
            self.last_t = t
            return []
        dt = max(0.0, t - (self.last_t or t))
        self.last_t = t
        a = 1.0 - math.exp(-dt / BASELINE_TAU_S) if dt else 0.0
        rises = []
        for k, c in enumerate(counts):
            d = c - self.base[k]
            if d < self.pad_lo[k]:
                self.base[k] += a * (c - self.base[k])
            rises.append(d)
        active = [PADS[k] for k, d in enumerate(rises) if d >= self.pad_lo[k]]
        out = []
        if active:
            self.off_since = None
            if self.on_since is None:
                self.on_since = t
            elif self.pressed is None and t - self.on_since >= TOUCH_MIN_S:
                self.pressed = active
                where = "head" if len(active) > 1 or active == ["M"] else SIDE[active[0]]
                self.events += 1
                out.append({"kind": "touch", "where": where, "pads": active})
        else:
            if self.off_since is None:
                self.off_since = t
            elif t - self.off_since >= TOUCH_RELEASE_S:
                self.on_since = None
                self.pressed = None
        return out


class BumpDetector:
    def __init__(self, threshold=BUMP_GYRO):
        self.threshold = threshold
        self.last_t = -1e9

    def feed(self, gyro_body, t: float, still: bool) -> list[dict]:
        if not still or gyro_body is None:
            return []
        try:
            mag = math.sqrt(sum(float(v) ** 2 for v in gyro_body))
        except (TypeError, ValueError):
            return []
        if mag >= self.threshold and t - self.last_t >= BUMP_QUIET_S:
            self.last_t = t
            return [{"kind": "bump", "rate": round(mag, 2)}]
        return []


class SoundOnset:
    """Levels in dB per channel (agent `sound` records: ch0/ch1 front pair, ch2 back; CURRENT-STATE a7z_audio_capture)."""

    def __init__(self, step_db=SOUND_STEP_DB):
        self.step_db = step_db
        self.floor = None
        self.last_t = None
        self.last_event_t = -1e9

    def feed(self, db, t: float) -> list[dict]:
        vals = [v for v in (db or []) if v is not None]
        if not vals:
            return []
        level = max(vals)
        if self.floor is None:
            self.floor, self.last_t = level, t
            return []
        dt = max(0.0, t - (self.last_t or t))
        self.last_t = t
        out = []
        if level - self.floor >= self.step_db and t - self.last_event_t >= SOUND_QUIET_S:
            self.last_event_t = t
            direction = None
            if len(db) >= 3 and db[0] is not None and db[2] is not None:
                direction = 0.0 if db[0] >= db[2] else math.pi  # front or behind; left/right needs the ear mics
            out.append({"kind": "sound", "label": "noise", "direction": direction, "db": round(level, 1)})
        else:
            self.floor += (1.0 - math.exp(-dt / SOUND_FLOOR_TAU_S)) * (level - self.floor)
        return out


class FaceAdapter:
    """frames -> face / face_lost. `recognise(frame_bgr) -> [{"who": "owner" | "known:<name>" | "stranger", "x": -1..1}]`."""

    def __init__(self, recognise=None):
        self.recognise = recognise or identity_recogniser()
        self.enabled = self.recognise is not None
        self.streak = {}      # who -> consecutive frames seen
        self.seen_t = {}      # who -> last frame time
        self.present = set()

    def feed_jpeg(self, jpeg_b64: str, t: float) -> list[dict]:
        if not self.enabled:
            return []
        try:
            import cv2
            import numpy as np
            img = cv2.imdecode(np.frombuffer(base64.b64decode(jpeg_b64), dtype=np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return []
        return self.feed_frame(img, t)

    def feed_frame(self, frame, t: float) -> list[dict]:
        if not self.enabled:
            return []
        try:
            people = list(self.recognise(frame) or [])
        except Exception:
            return []
        out = []
        now_seen = {p.get("who", "stranger") for p in people}
        for p in people:
            who = p.get("who", "stranger")
            self.streak[who] = self.streak.get(who, 0) + 1
            self.seen_t[who] = t
            if who not in self.present and self.streak[who] >= FACE_SEEN_FRAMES:
                self.present.add(who)
                direction = -1.2 * float(p.get("x", 0.0)) if p.get("x") is not None else None  # left of picture = +yaw
                out.append({"kind": "face", "who": who, "direction": direction})
        for who in list(self.streak):
            if who not in now_seen:
                self.streak[who] = 0
        return out + self.tick(t)

    def tick(self, t: float) -> list[dict]:
        out = []
        for who in list(self.present):
            if t - self.seen_t.get(who, t) >= FACE_LOST_S:
                self.present.discard(who)
                out.append({"kind": "face_lost", "who": who} if who != "stranger" else {"kind": "stranger_leaves"})
        return out


def identity_recogniser(db_path=None):
    """pet/identity face pipeline + log-odds identity against the enrolled database, or None when unavailable."""
    try:
        from pet.identity.face import FacePipeline
        from pet.identity.memory import Memory
        from pet.identity.whois import Whois, scores_against
    except Exception:
        return None
    db = Path(db_path) if db_path else Path(__file__).resolve().parents[1] / "identity" / "data" / "identity.sqlite"
    if not db.exists():
        return None
    try:
        pipe = FacePipeline()
        mem = Memory(db)
    except Exception:
        return None
    whois = Whois()  # one person in view at a time, as pet/identity/demo.py tracks it

    def recognise(frame):
        """The largest usable face in the frame, as one {"who", "x"} once the log-odds decision is not 'unsure'."""
        faces = [f for f in pipe.analyze(frame, max_num=1) if f.usable and f.embedding is not None]
        if not faces:
            return []
        f, now = faces[0], time.time()
        whois.observe(now, "face", scores_against(mem.centroids("face"), f.embedding), f.quality)
        dec = whois.decide(now, mem.label)
        if dec.label == "unsure":
            return []
        w = frame.shape[1]
        return [{"who": dec.label, "x": float((f.bbox[0] + f.bbox[2]) / 2 / w * 2 - 1)}]

    return recognise


class ScriptedEvents:
    """[(offset_s, event), ...] delivered once their offset has passed."""

    def __init__(self, items, t0: float):
        self.items = sorted(((float(o), dict(e)) for o, e in items), key=lambda x: x[0])
        self.t0 = t0

    @classmethod
    def from_file(cls, path, t0: float):
        items = []
        for ln in Path(path).read_text().splitlines():
            if ln.strip():
                o = json.loads(ln)
                items.append((o.pop("at"), o))
        return cls(items, t0)

    def due(self, now: float) -> list[dict]:
        out = []
        while self.items and self.items[0][0] <= now - self.t0:
            out.append(self.items.pop(0)[1])
        return out


# A 30-minute session for the dry run and the simulated day: the scripted-day beats (run_scenario.SCENARIO) in half an
# hour, so the mind meets touch, a salient sound, the owner leaving and returning and a stranger. Directions in radians,
# positive to the pet's left.
DEFAULT_SESSION = [
    (5, {"kind": "face", "who": "owner"}),
    (60, {"kind": "touch", "where": "head"}),
    (180, {"kind": "sound", "label": "keys_jingle", "direction": 1.2}),
    (240, {"kind": "face_lost", "who": "owner"}),
    (250, {"kind": "owner_leaves", "direction": 1.2}),
    (700, {"kind": "sound", "label": "doorbell", "direction": 1.0}),
    (720, {"kind": "face", "who": "stranger", "direction": 0.8}),
    (900, {"kind": "stranger_leaves", "direction": 1.2}),
    (1200, {"kind": "owner_returns", "direction": 1.2}),
    (1230, {"kind": "face", "who": "owner", "direction": 0.6}),
    (1260, {"kind": "touch", "where": "head"}),
    (1500, {"kind": "lights", "level": 0.3}),
    (1700, {"kind": "touch", "where": "head"}),
]
