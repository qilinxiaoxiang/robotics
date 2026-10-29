"""The voice layer's inbox, read by the live runner (contract: pet/state/README.md, "Inbox from the voice layer").

`pet/voice/` writes three things under `<state>/inbox/`; this module reads them and hands each to its consumer:

- `owner_said.jsonl`: one line per spoken sentence. Each new line becomes an `owner_said` percept for the mind (salient,
  so the mind re-plans) and `owner:said(text)` plus the reaction (`owner:praised` / `owner:said_no`) for pet/learn.
  `result: ignore, reaction: praised` ("good duck") is the praise the drives feel. Lines already in the file when the
  runner starts are history and are skipped: a sentence said while no runner was listening is not acted on later.
- `tasks/<stamp>.json`: a validated intention. `translate_task` maps it onto the runner's body card (the voice layer
  validates against `pet/state/body_card.json`, whose names differ: `groundpick` is the runner's `bow`) and the runner
  re-validates it against the real posture, prepends `stand` when a sitting body is asked to move, and runs it in
  place of the current intention. The file is renamed `.done` when it is taken, before the first step, so it never
  runs twice, even across a crash.
- `rules/<stamp>.json`: an owner instruction as an operant rule. `merge_rule` puts it into `rules.json` the way
  pet/learn specifies (a rule with the same trigger and outcome is replaced), the runner hands it to its live
  `pet.learn.match.Matcher`, and the file is renamed `.done`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .body import BodyCard

# names the voice layer's card (pet/state/body_card.json, from pet/body's self-inspection) uses for a runner primitive
ALIASES = {"groundpick": "bow"}


def mark_done(path: Path) -> Path:
    """The contract's consumption mark: rename to <name>.done (never delete)."""
    done = path.with_name(path.name + ".done")
    os.replace(path, done)
    return done


class VoiceInbox:
    """New sentences, task files and rule files since the last poll."""

    def __init__(self, inbox_dir: Path | str, from_start: bool = False):
        self.dir = Path(inbox_dir)
        self.said_path = self.dir / "owner_said.jsonl"
        self.offset = 0
        if not from_start and self.said_path.exists():
            self.offset = self.said_path.stat().st_size

    def new_said(self) -> list[dict]:
        p = self.said_path
        try:
            size = p.stat().st_size
        except FileNotFoundError:
            return []
        if size < self.offset:  # the file was replaced
            self.offset = 0
        if size == self.offset:
            return []
        with p.open("rb") as f:
            f.seek(self.offset)
            data = f.read()
        end = data.rfind(b"\n")
        if end < 0:
            return []  # a line still being written
        self.offset += end + 1
        out = []
        for raw in data[:end].splitlines():
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            if isinstance(d, dict):
                out.append(d)
        return out

    def _files(self, sub: str) -> list[Path]:
        d = self.dir / sub
        if not d.is_dir():
            return []
        return sorted(p for p in d.glob("*.json") if p.is_file())

    def new_tasks(self) -> list[Path]:
        return self._files("tasks")

    def new_rules(self) -> list[Path]:
        return self._files("rules")


def translate_task(task: dict, body: BodyCard) -> tuple[dict, list[str]]:
    """The task's intention as a model-style answer for `validator.validate` on the runner's card, plus notes on what
    was renamed or left out (unknown primitive, parameter the runner's primitive does not take)."""
    intent = task.get("intention") or {}
    notes, steps = [], []
    for s in intent.get("steps") or []:
        if not isinstance(s, dict):
            continue
        name = s.get("primitive")
        mapped = ALIASES.get(name, name)
        if mapped != name:
            notes.append(f"{name} -> {mapped}")
        if mapped not in body.primitives:
            notes.append(f"{name} left out (not on this body card or not allowed)")
            continue
        spec = body.primitives[mapped].get("params", {})
        params = {k: v for k, v in (s.get("params") or {}).items() if k in spec}
        dropped = sorted(set(s.get("params") or {}) - set(spec))
        if dropped:
            notes.append(f"{mapped}: parameter{'s' if len(dropped) > 1 else ''} {', '.join(dropped)} not taken")
        steps.append({"primitive": mapped, "params": params})
    said = str(task.get("said", "")).strip()
    text = str(intent.get("intention_text") or f"The owner said: {said}").strip()
    abort_if = [a for a in intent.get("abort_if") or [] if isinstance(a, str)]
    # "sit, abort if not standing" would abort itself the moment the seat is reached: a condition the task's own
    # posture change makes true is left out
    ends_in = {body.primitives[s["primitive"]].get("effects", {}).get("posture") for s in steps} - {None}
    for a in list(abort_if):
        words = a.strip().lower().split()
        if len(words) == 2 and words[0] == "not" and ends_in - {words[1]}:
            abort_if.remove(a)
            notes.append(f"abort condition '{a}' left out (the task itself changes the posture)")
    return {"intention_text": text[:200], "steps": steps, "abort_if": abort_if,
            "mood_note": "asked by the owner"}, notes


def merge_rule(rules_path: Path, rule: dict) -> tuple[list[dict], str]:
    """pet/learn's merge: replace a rule with the same trigger and outcome, else append. Returns (rules, what)."""
    from pet.learn.state import validate_rule  # pet/learn's own validator: the rule goes in exactly as it accepts it
    rule = validate_rule(rule)
    try:
        rules = json.loads(rules_path.read_text())
        if not isinstance(rules, list):
            rules = []
    except (OSError, ValueError):
        rules = []
    key = (rule["trigger"], rule["outcome_or_effect"])
    what = "added"
    for i, r in enumerate(rules):
        if isinstance(r, dict) and (r.get("trigger"), r.get("outcome_or_effect")) == key:
            rules[i] = rule
            what = f"replaced {r.get('id')}"
            break
    else:
        rules.append(rule)
    tmp = rules_path.with_name(rules_path.name + ".runner.tmp")
    tmp.write_text(json.dumps(rules, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, rules_path)
    return rules, what
