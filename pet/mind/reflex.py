"""Reflex table: the immediate reaction to an interrupt, before the intention layer hears about it.

Each entry is a list of steps; each step lists alternative primitives in order of preference, so one table serves
any body (the duck turns its head, the arm turns its camera). A step whose alternatives are all missing on this
body is skipped. Param value "direction" is replaced by the event's direction, clamped to the parameter's range.
"""
from __future__ import annotations

from .body import BodyCard

ORIENT = [("turn_head", {"yaw": "direction", "pitch": 0.1}), ("turn_camera", {"yaw": "direction", "pitch": 0.1})]
REFLEXES = {
    "sound": [ORIENT],
    "face_owner": [ORIENT],
    "face_stranger": [[("stop", {})], ORIENT],
    "touch": [[("stop", {})], [("nod", {"times": 1})]],
    "face_lost": [],
}
# Events after which the intention layer re-plans at once; others resume the interrupted intention.
SALIENT_SOUNDS = {"keys_jingle", "doorbell", "door_slam", "door", "name_called"}


def reflex_key(percept: dict) -> str | None:
    kind = percept.get("kind")
    if kind == "face":
        return "face_owner" if percept.get("who") == "owner" else "face_stranger"
    return kind if kind in REFLEXES else None


def is_salient(percept: dict) -> bool:
    kind = percept.get("kind")
    if kind == "sound":
        return percept.get("label") in SALIENT_SOUNDS
    return kind in ("face", "touch", "stranger_leaves", "expect", "owner_said")  # owner_said: pet/state/README.md


def reflex_steps(percept: dict, body: BodyCard) -> list[dict]:
    """Primitive steps (not yet validated) for this percept on this body."""
    key = reflex_key(percept)
    steps = []
    for alternatives in REFLEXES.get(key, []):
        for name, params in alternatives:
            if name not in body.primitives:
                continue
            spec = body.primitives[name].get("params", {})
            out = {}
            for k, v in params.items():
                if k not in spec:
                    continue
                if v == "direction":
                    v = float(percept.get("direction", 0.0))
                lo, hi = spec[k]
                out[k] = round(min(max(v, lo), hi), 2)
            steps.append({"primitive": name, "params": out})
            break
    return steps
