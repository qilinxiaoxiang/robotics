"""Simulated home: ground truth (who is where) and the percepts a given body gets from it.

The scenario changes the truth (owner moves, leaves, a stranger arrives, a sound); World turns each change into the
percepts this body can actually sense (no camera: no faces; no mic: no sounds; owner visible only in the same room).
"""
from __future__ import annotations

import random
from collections import deque

from .body import BodyCard

ROOMS = ["bedroom", "hallway", "living room", "kitchen"]
NEIGHBOURS = {"bedroom": ["hallway"], "hallway": ["bedroom", "living room", "kitchen"],
              "living room": ["hallway", "kitchen"], "kitchen": ["living room", "hallway"]}


def clock(t: float) -> str:
    t = int(t) % 86400
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def period(hour: float) -> str:
    return ("morning" if 5 <= hour < 12 else "afternoon" if hour < 17 else "evening" if hour < 22 else "night") \
        if hour >= 5 else "night"


class World:
    def __init__(self, body: BodyCard, rng: random.Random, t0: float, pet_room="living room"):
        self.body, self.rng, self.t = body, rng, t0
        self.pet_room = body.fixed_location or pet_room
        self.posture = "standing"
        self.owner_home, self.owner_room = True, "bedroom"
        self.stranger_room = None
        self.owner_last_seen_t = None
        self.owner_last_room = "bedroom"
        self.sound_direction = None
        self.touched_until = -1.0
        self.lights = 1.0
        self.charging = False
        self.recent_events = deque(maxlen=40)   # (t, text)
        self.recent_behaviours = deque(maxlen=40)  # (t, text, signature)
        self._was_visible = self.owner_visible
        self._stranger_seen = False

    @property
    def hour(self) -> float:
        return (self.t % 86400) / 3600

    @property
    def owner_visible(self) -> bool:
        return self.owner_home and self.owner_room == self.pet_room and "camera" in self.body.sensor_kinds

    @property
    def stranger_present(self) -> bool:
        return self.stranger_room is not None and self.stranger_room == self.pet_room and \
            "camera" in self.body.sensor_kinds

    def facts(self, drives: dict) -> dict:
        return {"posture": self.posture, "owner_visible": self.owner_visible, "owner_home": self.owner_home,
                "stranger_present": self.stranger_present, "touched": self.t < self.touched_until,
                "can_locomote": self.body.can_locomote, "battery": drives.get("battery_level", 1.0),
                "hour": self.hour, **{k: drives[k] for k in ("tired", "bored", "miss_owner", "curious") if k in drives}}

    def note(self, text: str):
        self.recent_events.append((self.t, text))

    def apply(self, ev: dict) -> list[dict]:
        """Change the truth; return the percepts this body gets (already filtered by its sensors)."""
        kind, out = ev["kind"], []
        if kind == "owner_moves":
            self.owner_room = ev["room"]
        elif kind == "owner_leaves":
            self.owner_home, self.owner_room = False, None
            out.append({"kind": "sound", "label": "door_slam", "direction": ev.get("direction", 1.0)})
        elif kind == "owner_returns":
            self.owner_home, self.owner_room = True, ev.get("room", "hallway")
            out.append({"kind": "sound", "label": "door", "direction": ev.get("direction", 1.0)})
        elif kind == "stranger_arrives":
            self.stranger_room = ev.get("room", "hallway")
            out.append({"kind": "sound", "label": "footsteps", "direction": ev.get("direction", 1.0)})
        elif kind == "stranger_leaves":
            if self.stranger_present:
                out.append({"kind": "stranger_leaves"})
            self.stranger_room = None
            self._stranger_seen = False
            out.append({"kind": "sound", "label": "door", "direction": ev.get("direction", 1.0)})
        elif kind == "sound":
            out.append({"kind": "sound", "label": ev["label"], "direction": ev.get("direction", 0.0)})
        elif kind == "touch":
            if self.owner_home:  # the owner walks over to pet it
                self.owner_room = self.pet_room
                out += self.visibility_changes()
            if self.owner_visible:
                self.touched_until = self.t + 5
                out.append({"kind": "touch", "where": ev.get("where", "head")})
        elif kind == "lights":
            self.lights = ev.get("level", 1.0)
            out.append({"kind": "lights", "level": self.lights})
        elif kind in ("charge_start", "charge_end"):
            self.charging = kind == "charge_start"
        out = [p for p in out if self.body.perceives(p)]
        return out + self.visibility_changes()

    def visibility_changes(self) -> list[dict]:
        """Face / face_lost percepts when what the camera sees changed (owner or stranger came into view)."""
        out = []
        vis = self.owner_visible
        if vis and not self._was_visible:
            out.append({"kind": "face", "who": "owner"})
        elif self._was_visible and not vis and "camera" in self.body.sensor_kinds:
            out.append({"kind": "face_lost", "who": "owner"})
        if vis:
            self.owner_last_seen_t = self.t
            self.owner_last_room = self.owner_room
        self._was_visible = vis
        if self.stranger_present and not self._stranger_seen:
            out.append({"kind": "face", "who": "stranger"})
            self._stranger_seen = True
        return out

    def move_pet(self, primitive: str, params: dict) -> str | None:
        """Locomotion outcome in the simulated home; returns the new room or None."""
        if self.body.fixed_location or "locomotion" not in self.body.tags(primitive):
            return None
        if primitive == "approach_owner" and self.owner_home:
            target = self.owner_room
            if target != self.pet_room and (target in NEIGHBOURS[self.pet_room] or params.get("seconds", 0) >= 8):
                self.pet_room = target
                return target
            if target != self.pet_room:
                self.pet_room = next(r for r in NEIGHBOURS[self.pet_room] if r == "hallway" or r == target)
                return self.pet_room
            return None
        moving = primitive == "wander" or (params.get("vx", 0) >= 0.1 and params.get("seconds", 0) >= 5)
        if moving and self.rng.random() < 0.45:
            self.pet_room = self.rng.choice(NEIGHBOURS[self.pet_room])
            return self.pet_room
        return None

    def describe(self) -> str:
        if self.owner_home:
            seen = "in view" if self.owner_visible else f"somewhere at home (last seen in {self.owner_last_room})"
            owner = f"owner {seen}"
        else:
            owner = "owner out of the house"
        if self.owner_last_seen_t is not None and not self.owner_visible:
            owner += f", last seen {int(self.t - self.owner_last_seen_t) // 60} min ago"
        parts = [owner, "a stranger in view" if self.stranger_present else "no stranger",
                 "being touched" if self.t < self.touched_until else "not touched",
                 f"lights {'dim' if self.lights < 0.5 else 'on'}"]
        if self.charging:
            parts.append("charging")
        return ", ".join(parts)
