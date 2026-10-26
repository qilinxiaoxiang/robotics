"""Reads the shared state files (pet/state/README.md). Every file is optional; a missing or broken file means
defaults, never a crash. The mind only reads these files."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .body import check_condition

STATE_DIR = Path(__file__).resolve().parents[1] / "state"
EXAMPLES = STATE_DIR / "examples"
PERIODS = {"morning": (5, 12), "afternoon": (12, 17), "evening": (17, 22), "night": (22, 29), "any": (0, 24)}


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def _load_jsonl(path: Path) -> list:
    out = []
    try:
        for line in path.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    return out


class SharedState:
    def __init__(self, state_dir: Path | str = STATE_DIR):
        d = Path(state_dir)
        self.dir = d
        self.rules = [r for r in _load_json(d / "rules.json", []) if isinstance(r, dict)]
        self.plan = _load_json(d / "plan.json", {}) or {}
        self.diary = [e for e in _load_jsonl(d / "diary.jsonl") if isinstance(e, dict)]
        self.personality = _load_json(d / "personality.json", {}) or {}
        self.skills = [s for s in _load_json(d / "skills.json", []) if isinstance(s, dict)]
        self.body_card = _load_json(d / "body_card.json", None)

    def rules_text(self, min_weight=0.2) -> list[str]:
        rs = sorted((r for r in self.rules if float(r.get("weight", 0)) >= min_weight),
                    key=lambda r: -float(r.get("weight", 0)))
        return [f"{r.get('text') or (str(r.get('trigger')) + ' -> ' + str(r.get('outcome_or_effect')))} "
                f"(w={float(r.get('weight', 0)):.2f})" for r in rs]

    def expectations(self, percept: dict) -> list[dict]:
        """Pavlovian rules triggered by this percept, as 'expect' pseudo-events."""
        keys = {percept.get("kind"), percept.get("label")} - {None}
        return [{"kind": "expect", "outcome": str(r.get("outcome_or_effect", "")), "weight": float(r.get("weight", 0)),
                 "rule": r.get("id")}
                for r in self.rules if r.get("kind") == "pavlovian" and r.get("trigger") in keys
                and float(r.get("weight", 0)) >= 0.2]

    def active_plan(self, hour: float, today: str, facts: dict, top=3) -> list[str]:
        items = []
        for it in self.plan.get("intentions", []) or []:
            if not isinstance(it, dict) or not _when_covers(str(it.get("when", "any")), hour):
                continue
            cond = str(it.get("condition", "") or "")
            ok = check_condition(cond, facts)
            if ok is False:
                continue
            note = "" if ok is True else f" (if: {cond})"
            items.append((int(it.get("priority", 0) or 0), f"{it.get('goal', '')}{note}"))
        stale = " (stale)" if self.plan.get("date") and self.plan.get("date") != today else ""
        return [text + stale for _, text in sorted(items, key=lambda x: -x[0])[:top]]

    def retrieve_diary(self, context_words: set, k=3) -> list[str]:
        scored = []
        for e in self.diary:
            text = str(e.get("text", ""))
            if not text:
                continue
            words = set(re.findall(r"[a-z_]+", text.lower()))
            tags = {str(t).lower() for t in e.get("tags", [])}
            score = 2 * len(tags & context_words) + len(words & context_words)
            if score:
                scored.append((score, str(e.get("t", ""))[:16].replace("T", " "), text))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [f"{t} {text}" for _, t, text in scored[:k]]


def _hm(s: str) -> float:
    h, m = s.strip().split(":")
    return int(h) + int(m) / 60


def _when_covers(when: str, hour: float) -> bool:
    w = when.strip().lower()
    try:
        if w in PERIODS:
            lo, hi = PERIODS[w]
            return lo <= hour < hi or lo <= hour + 24 < hi
        if "-" in w:
            a, b = (_hm(x) for x in w.split("-", 1))
            return a <= hour < b if a <= b else hour >= a or hour < b
        a = _hm(w)
        return a <= hour < a + 0.5
    except ValueError:
        return False


def load_body_card(which: str) -> dict:
    """'duck' / 'arm' -> example card; anything else is a path. pet/state/body_card.json is used for 'live'."""
    if which in ("duck", "arm"):
        return json.loads((EXAMPLES / f"{which}_body_card.json").read_text())
    if which == "live":
        return json.loads((STATE_DIR / "body_card.json").read_text())
    return json.loads(Path(which).read_text())
