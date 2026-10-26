"""No-LLM intention: drives pick directly. Used when the model is offline or its answers fail validation twice.

A drive is chosen by a softmax over drive scores (with a penalty on the drive chosen last time), then 1-3
primitives whose tags serve that drive, with random in-range parameters. Posture is fixed first when a chosen
primitive needs it (stand before walking, sit before resting).
"""
from __future__ import annotations

import math
import random

from .body import BodyCard, check_condition

DRIVE_TAGS = {"bored": ["play", "explore", "locomotion"], "miss_owner": ["social", "orient", "locomotion"],
              "tired": ["rest"], "curious": ["explore", "orient"], "battery": ["rest"], "idle": ["orient", "rest"]}


class FallbackPolicy:
    def __init__(self, body: BodyCard, rng: random.Random, temperature=0.12):
        self.body, self.rng, self.temperature = body, rng, temperature
        self.last_drive, self.last_prims = None, []

    def choose_drive(self, drives: dict, thresholds: dict, facts: dict) -> str:
        scores = {k: float(drives.get(k, 0)) for k in DRIVE_TAGS if k != "idle"}
        if facts.get("owner_visible"):
            scores["miss_owner"] = max(scores["miss_owner"], 0.4)  # owner in view: social is always on the table
        if scores.get("tired", 0) > thresholds.get("tired_rest", 0.7):
            scores["tired"] += 0.5
        if self.last_drive in scores:
            scores[self.last_drive] -= 0.08
        act = thresholds.get("act", 0.35)
        scores = {k: s for k, s in scores.items() if s >= 0.5 * act}  # a drive near zero is not a reason to act
        if not scores or max(scores.values()) < act:
            scores["idle"] = act
        z = max(scores.values())
        w = {k: math.exp((s - z) / self.temperature) for k, s in scores.items()}
        r, acc = self.rng.random() * sum(w.values()), 0.0
        for k, v in w.items():
            acc += v
            if r <= acc:
                return k
        return max(scores, key=scores.get)

    def _ok(self, name, facts, posture):
        f = {**facts, "standing": posture == "standing", "sitting": posture == "sitting", "lying": posture == "lying"}
        return all(check_condition(c, f) is not False for c in self.body.primitives[name].get("preconditions", []))

    def _posture_fix(self, name, facts, posture):
        """A primitive that makes `name` runnable from this posture, or None."""
        for fixer, p in self.body.primitives.items():
            want = p.get("effects", {}).get("posture")
            if want and want != posture and self._ok(fixer, facts, posture) and self._ok(name, facts, want):
                return fixer, want
        return None

    def compose(self, drives: dict, thresholds: dict, facts: dict) -> dict:
        drive = self.choose_drive(drives, thresholds, facts)
        self.last_drive = drive
        tags = DRIVE_TAGS[drive]
        posture = facts.get("posture", "standing")
        cands = [n for n, p in self.body.primitives.items() if set(p.get("tags", [])) & set(tags)
                 and n not in ("stop", "stand", "sit", "rise")]
        if not facts.get("owner_home"):
            cands = [n for n in cands if n != "approach_owner"] or cands
        cands.sort(key=lambda n: (n in self.last_prims, self.rng.random()))
        steps, total = [], 0.0
        for name in cands[: self.rng.randint(1, 3)]:
            if not self._ok(name, facts, posture):
                fix = self._posture_fix(name, facts, posture)
                if not fix:
                    continue
                steps.append({"primitive": fix[0], "params": {}})
                total += self.body.step_seconds(fix[0], {})
                posture = fix[1]
            spec = self.body.primitives[name].get("params", {})
            params = {k: round(self.rng.uniform(lo, hi), 2) for k, (lo, hi) in spec.items()}
            if "times" in params:
                params["times"] = int(round(params["times"]))
            if "seconds" in params:
                params["seconds"] = round(min(params["seconds"], max(spec["seconds"][0], 25 - total)), 1)
            secs = self.body.step_seconds(name, params)
            if total + secs > 28:
                break
            steps.append({"primitive": name, "params": params})
            total += secs
            posture = self.body.primitives[name].get("effects", {}).get("posture", posture)
        if not any(s["primitive"] not in ("stand", "sit", "rise") for s in steps):
            wait = "wait" if "wait" in self.body.primitives else next(iter(self.body.primitives))
            steps = [{"primitive": wait, "params": {"seconds": 5} if "seconds" in
                      self.body.primitives[wait].get("params", {}) else {}}]
        self.last_prims = [s["primitive"] for s in steps]
        return {"intention_text": f"[{drive}] " + ", ".join(self.last_prims), "steps": steps,
                "duration_s": min(30.0, sum(self.body.step_seconds(s["primitive"], s["params"]) for s in steps)),
                "abort_if": ["stranger_present"] if drive != "curious" else [], "mood_note": drive}
