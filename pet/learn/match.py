"""Daytime matcher: watches the live event stream and turns each rule's trigger -> outcome
window into a Rescorla-Wagner trial.

For every rule whose trigger and outcome are vocabulary patterns:
  trigger seen (and the rule's context holds)  -> open a trial until t + window_s
  outcome seen inside an open trial             -> confirmation, trial closed
  window expires with no outcome                -> omission
  context breaks during the window (owner left)  -> trial voided, no update
One open trial per rule at a time (a second trigger inside the window is the same trial).

Fuzzy outcomes: a rule expecting owner:said_no or owner:praised is also confirmed by a
plain owner:said(text) whose sentence counts as an instance. `FuzzyJudge` decides that,
with a small model when one is available and a keyword list otherwise.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import events as E
from . import rw
from . import state as S
from .llm import SMALL_MODEL, LLMUnavailable, call_json

DEFAULT_WINDOW_S = 60.0
FUZZY_OUTCOMES = {"owner:said_no", "owner:praised"}

NO_WORDS = re.compile(r"\b(no+|nope|stop|don'?t|not (in )?here|out|get out|bad)\b|不行|不要|别|出去|不可以|停", re.I)
PRAISE_WORDS = re.compile(r"\b(good|well done|nice|clever|that'?s my)\b|乖|真棒|好样的|聪明", re.I)

FUZZY_SCHEMA = {
    "type": "object",
    "properties": {
        "instance": {"type": "boolean"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["instance", "confidence", "reason"],
    "additionalProperties": False,
}

FUZZY_SYSTEM = (
    "You label one sentence the owner said to their pet robot. The pet does not speak and never "
    "judges the owner. Decide only whether the sentence is an instance of the expected owner reaction "
    "named in the rule (for owner:said_no: the owner telling the pet no, to stop, or to leave; for "
    "owner:praised: the owner praising the pet). Return JSON."
)


class FuzzyJudge:
    """judge(rule, sentence) -> bool, cached per (outcome, sentence)."""

    def __init__(self, use_model: bool = False, model: str = SMALL_MODEL, backend: str | None = None):
        self.use_model = use_model
        self.model = model
        self.backend = backend
        self.cache: dict[tuple[str, str], bool] = {}
        self.usages = []

    def keyword(self, outcome: str, sentence: str) -> bool:
        pat = NO_WORDS if outcome == "owner:said_no" else PRAISE_WORDS
        return bool(pat.search(sentence))

    def __call__(self, rule: dict, sentence: str) -> bool:
        outcome = E.parse_pattern(rule["outcome_or_effect"])[0]
        key = (outcome, sentence)
        if key in self.cache:
            return self.cache[key]
        ans = None
        if self.use_model:
            try:
                data, u = call_json(
                    FUZZY_SYSTEM,
                    json.dumps({"rule": {"trigger": rule["trigger"], "expected": outcome, "text": rule["text"]},
                                "sentence": sentence}, ensure_ascii=False),
                    FUZZY_SCHEMA, model=self.model, purpose="fuzzy_match", backend=self.backend,
                    effort="low", max_tokens=400, budget_usd=0.05)
                self.usages.append(u)
                ans = bool(data["instance"]) and float(data["confidence"]) >= 0.5
            except (LLMUnavailable, RuntimeError, KeyError, ValueError):
                ans = None
        if ans is None:
            ans = self.keyword(outcome, sentence)
        self.cache[key] = ans
        return ans


@dataclass
class Trial:
    rule_id: str
    t_open: float
    deadline: float


@dataclass
class Matcher:
    rules: list[dict]
    fuzzy: FuzzyJudge = field(default_factory=FuzzyJudge)
    owner_home: bool = True
    open: dict[str, Trial] = field(default_factory=dict)
    used_ids: set[str] = field(default_factory=set)
    log: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.by_id = {r["id"]: r for r in self.rules}

    def _context_ok(self, rule: dict) -> bool:
        ctx = rule.get("context")
        return ctx is None or (ctx == "owner_home") == self.owner_home

    def _outcome_hit(self, rule: dict, ev: E.Event) -> bool:
        pat = rule["outcome_or_effect"]
        if E.pattern_matches(pat, ev):
            return True
        base, _ = E.parse_pattern(pat)
        if base in FUZZY_OUTCOMES and ev.type == "owner:said":
            return self.fuzzy(rule, ev.args.get("text", ""))
        return False

    def _record(self, kind: str, rule: dict, t: float):
        self.log.append({"t": t, "rule": rule["id"], "result": kind, "weight": rule["weight"]})

    def expire(self, t: float) -> None:
        for rid, tr in list(self.open.items()):
            if tr.deadline < t:
                rule = self.by_id[rid]
                rw.omit(rule)
                self._record("omit", rule, tr.deadline)
                del self.open[rid]

    def feed(self, ev: E.Event) -> None:
        self.expire(ev.t)
        # outcomes first, so an event that closes one trial can open another
        for rid, tr in list(self.open.items()):
            rule = self.by_id[rid]
            if self._outcome_hit(rule, ev):
                rw.confirm(rule)
                self._record("confirm", rule, ev.t)
                del self.open[rid]
        # presence tracking, then void trials whose context broke
        if ev.type == "owner:left":
            self.owner_home = False
        elif ev.type in ("owner:returned", "see:owner", "sound:voice:owner"):
            self.owner_home = True
        for rid in list(self.open):
            if not self._context_ok(self.by_id[rid]):
                self._record("void", self.by_id[rid], ev.t)
                del self.open[rid]
        # triggers
        for rule in self.rules:
            if not E.pattern_matches(rule["trigger"], ev) or not self._context_ok(rule):
                continue
            self.used_ids.add(rule["id"])
            if not S.rule_is_matchable(rule) or rule["id"] in self.open:
                continue
            w = float(rule.get("window_s", DEFAULT_WINDOW_S))
            self.open[rule["id"]] = Trial(rule["id"], ev.t, ev.t + w)

    def feed_all(self, evs) -> None:
        for ev in evs:
            self.feed(ev)

    def end_of_day(self, t_end: float = 24 * 3600) -> None:
        self.expire(t_end + 1)


def run_day(rules: list[dict], evs: list[E.Event], fuzzy: FuzzyJudge | None = None) -> Matcher:
    m = Matcher(rules, fuzzy or FuzzyJudge())
    m.feed_all(evs)
    m.end_of_day()
    return m
