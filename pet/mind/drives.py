"""Drives and mood: plain arithmetic, updated every simulated second, so behaviour has continuity.

Drives are in 0-1. bored, miss_owner, tired and curious integrate their own rates; battery is a drive derived from
the battery level (0 while the level is comfortable, rising to 1 as it empties). Mood is valence (-1..1) and arousal
(0..1), each relaxing toward a target set by the drives, plus jumps from events.
"""
from __future__ import annotations

import math

DEFAULT_RATES = {"bored": 0.0017, "miss_owner": 0.0004, "tired_active": 0.0012, "tired_idle": 0.00005,
                 "rest_recovery": 0.003, "curious_decay_tau_s": 120.0, "battery_idle": 0.00006,
                 "battery_active": 0.0002, "charge": 0.0005}
DEFAULT_THRESHOLDS = {"act": 0.35, "tired_rest": 0.7, "battery_low": 0.2}
DRIVES = ("bored", "miss_owner", "tired", "curious", "battery")
VALENCE_TAU_S, AROUSAL_TAU_S = 300.0, 60.0


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


class Drives:
    def __init__(self, personality: dict | None = None):
        personality = personality or {}
        self.rates = {**DEFAULT_RATES, **personality.get("drive_rates", {})}
        self.thresholds = {**DEFAULT_THRESHOLDS, **personality.get("thresholds", {})}
        self.v = {"bored": 0.2, "miss_owner": 0.0, "tired": 0.15, "curious": 0.2, "battery": 0.0}
        self.battery_level = 1.0
        self.valence, self.arousal = 0.2, 0.3

    def update(self, dt: float, activity: set, owner_visible: bool, owner_home: bool, hour: float,
               charging: bool = False):
        """activity: the current step's tags, plus 'sleep' while asleep. dt in seconds."""
        r, v = self.rates, self.v
        engaged = activity & {"explore", "play"} or (owner_visible and activity & {"social"})
        if "sleep" in activity:
            v["bored"] -= r["bored"] * dt
        elif engaged:
            v["bored"] -= 3 * r["bored"] * dt
        elif activity & {"rest"} and owner_visible:
            v["bored"] += 0.5 * r["bored"] * dt
        else:
            v["bored"] += r["bored"] * dt
        if owner_visible:
            v["miss_owner"] *= math.exp(-dt / 60.0)
        else:
            v["miss_owner"] += r["miss_owner"] * dt * (1.0 if owner_home else 1.5) * (0.3 if "sleep" in activity else 1)
        if activity & {"rest", "sleep"}:
            v["tired"] -= r["rest_recovery"] * dt * (1.5 if "sleep" in activity else 1.0)
        elif "locomotion" in activity:
            v["tired"] += r["tired_active"] * dt
        elif activity & {"social", "explore", "play", "express"}:
            v["tired"] += 0.4 * r["tired_active"] * dt
        else:
            v["tired"] += r["tired_idle"] * dt
        if hour >= 22 or hour < 6:
            v["tired"] += 3 * r["tired_idle"] * dt
        v["curious"] *= math.exp(-dt / r["curious_decay_tau_s"] * (2.0 if activity & {"explore", "orient"} else 1.0))
        drain = r["battery_active"] if "locomotion" in activity else r["battery_idle"]
        if "sleep" in activity:
            drain *= 0.2  # servos relaxed, camera and model off
        self.battery_level = _clip(self.battery_level + (r["charge"] if charging else -drain) * dt)
        low = 2 * self.thresholds["battery_low"]
        v["battery"] = _clip((low - self.battery_level) / low)
        for k in v:
            v[k] = _clip(v[k])
        target_v = 0.35 - 0.6 * v["miss_owner"] - 0.3 * v["tired"] - 0.3 * v["bored"] - 0.4 * v["battery"]
        if owner_visible:
            target_v += 0.15
        target_a = 0.2 + 0.5 * v["curious"] + 0.2 * v["bored"] - 0.4 * v["tired"] - (0.15 if "sleep" in activity else 0)
        self.valence += (_clip(target_v, -1, 1) - self.valence) * (1 - math.exp(-dt / VALENCE_TAU_S))
        self.arousal += (_clip(target_a) - self.arousal) * (1 - math.exp(-dt / AROUSAL_TAU_S))

    def apply_event(self, percept: dict):
        """Satisfaction and startle from one perceived event."""
        kind, v = percept.get("kind"), self.v
        label, who = percept.get("label", ""), percept.get("who", "")
        if kind == "touch":
            self.valence += 0.35
            self.arousal += 0.15
            v["miss_owner"] *= 0.4
            v["bored"] *= 0.6
        elif kind == "face" and who == "owner":
            self.valence += 0.1 + 0.4 * v["miss_owner"]
            self.arousal += 0.25
            v["curious"] += 0.1
        elif kind == "face" and who == "stranger":
            self.valence -= 0.15
            self.arousal += 0.35
            v["curious"] += 0.4
        elif kind == "sound":
            startle = 0.4 if label in ("door_slam", "doorbell") else 0.2
            self.arousal += startle
            v["curious"] += startle + 0.1
            v["bored"] -= 0.15
            if label == "door_slam":
                self.valence -= 0.1
        elif kind == "face_lost":
            v["miss_owner"] += 0.05
        elif kind == "expect" and "owner_leaves" in percept.get("outcome", ""):
            v["miss_owner"] += 0.3 * float(percept.get("weight", 0))
            self.valence -= 0.1 * float(percept.get("weight", 0))
        for k in v:
            v[k] = _clip(v[k])
        self.valence = _clip(self.valence, -1, 1)
        self.arousal = _clip(self.arousal)

    def snapshot(self) -> dict:
        return {**{k: round(self.v[k], 3) for k in DRIVES}, "battery_level": round(self.battery_level, 3),
                "valence": round(self.valence, 3), "arousal": round(self.arousal, 3)}
