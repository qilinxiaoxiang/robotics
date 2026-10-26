"""Body card reader and the precondition grammar (see pet/state/README.md).

The mind knows a body only through its card: which events it can perceive, which primitives it may call, their
parameter ranges, preconditions and durations. Nothing here knows about joints beyond the card's listing.
"""
from __future__ import annotations

import re

BOOL_FACTS = {"standing", "sitting", "lying", "owner_visible", "stranger_present", "touched", "owner_home",
              "can_locomote"}
NUM_FACTS = {"battery", "hour", "tired", "bored", "miss_owner", "curious"}
_CMP = re.compile(r"^\s*([a-z_]+)\s*(<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)\s*$")
_OPS = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}

# Which sensor kind a percept needs. Percepts not listed here are world facts every body knows (time, battery).
PERCEPT_SENSOR = {"sound": "mic", "face": "camera", "face_lost": "camera", "stranger_leaves": "camera",
                  "touch": "touch"}


def check_condition(cond: str, facts: dict) -> bool | None:
    """True/False for a machine-readable condition, None when the text is outside the grammar (unchecked)."""
    c = (cond or "").strip().lower()
    if not c:
        return True
    m = _CMP.match(c)
    if m:
        name, op, value = m.group(1), m.group(2), float(m.group(3))
        if name not in NUM_FACTS or name not in facts:
            return None
        return _OPS[op](float(facts[name]), value)
    neg = c.startswith("not ")
    name = c[4:].strip() if neg else c
    if name not in BOOL_FACTS:
        return None
    value = bool(facts.get(name, False))
    return not value if neg else value


def closest_to_zero(lo: float, hi: float) -> float:
    return min(max(0.0, lo), hi)


class BodyCard:
    def __init__(self, card: dict):
        self.card = card
        self.name = card.get("name", "body")
        self.sensor_kinds = {s.get("kind") for s in card.get("sensors", [])}
        self.primitives = {p["name"]: p for p in card.get("primitives", [])}
        self.fixed_location = card.get("fixed_location")
        self.notes = list(card.get("notes", []))
        self.failed = [a.get("name") for a in card.get("actuators", []) if a.get("ok") is False]

    @property
    def can_locomote(self) -> bool:
        return any("locomotion" in p.get("tags", []) for p in self.primitives.values())

    def perceives(self, percept: dict) -> bool:
        need = PERCEPT_SENSOR.get(percept.get("kind"))
        return need is None or need in self.sensor_kinds

    def step_seconds(self, name: str, params: dict) -> float:
        p = self.primitives[name]
        if "seconds" in p.get("params", {}):
            return float(params["seconds"])
        return float(p.get("duration_s_typical", min(3.0, float(p.get("duration_s_max", 3)))))

    def tags(self, name: str) -> list:
        p = self.primitives.get(name)
        return list(p.get("tags", [])) if p else []

    def describe_primitives(self) -> list[str]:
        out = []
        for name, p in self.primitives.items():
            params = ", ".join(f"{k} {lo:g}..{hi:g}" for k, (lo, hi) in p.get("params", {}).items())
            needs = f" needs: {', '.join(p['preconditions'])};" if p.get("preconditions") else ""
            eff = f" then posture={p['effects']['posture']};" if p.get("effects", {}).get("posture") else ""
            tags = f" [{', '.join(p.get('tags', []))}]" if p.get("tags") else ""
            out.append(f"{name}({params}){needs}{eff} max {p.get('duration_s_max', 0):g}s{tags}")
        return out
