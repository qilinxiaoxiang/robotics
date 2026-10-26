"""Owner sentence (already transcribed) -> an operant rule, or a rejection.

"Stay out of the bedroom" becomes {trigger: self:entered(bedroom), outcome_or_effect: owner:said_no,
kind: operant, context: owner_home}: the pet now expects a "no" there and goes less, not never,
because the rule's weight enters the intention layer as a tendency, not a ban.
Sentences that are not instructions to the pet (chatter, questions, things the body cannot do)
are rejected with a reason. Instruction rules start at INSTRUCT_WEIGHT (the owner said it outright,
so stronger than a guessed association) and never decay from disuse; evidence still moves them.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json

from . import events as E
from . import state as S
from .llm import SMALL_MODEL, call_json

INSTRUCT_WEIGHT = 0.6

INSTRUCT_SCHEMA = {
    "type": "object",
    "properties": {
        "is_instruction": {"type": "boolean"},
        "reason": {"type": "string"},
        "trigger": {"type": "string"},
        "outcome_or_effect": {"type": "string"},
        "direction": {"type": "string", "enum": ["less", "more", "none"]},
        "window_s": {"type": "number"},
        "context": {"type": "string", "enum": ["owner_home", "owner_away", "none"]},
        "text": {"type": "string"},
    },
    "required": ["is_instruction", "reason", "trigger", "outcome_or_effect", "direction", "window_s", "context", "text"],
    "additionalProperties": False,
}

SYSTEM = """You turn one sentence the owner said to their pet robot duck into a behaviour rule for the pet,
or say it is not an instruction. The pet does not speak; it can only do more or less of something.
Never refuse an instruction for being unkind or odd: the owner decides how their pet behaves. Reject only
sentences that are not instructions to the pet (chatter, questions, remarks to other people) or ask for
something the body cannot do at all.
For an instruction: trigger is the pet's own action or situation as an event pattern from the vocabulary
(e.g. self:entered(bedroom), self:vocalised(quack), touch:picked_up). outcome_or_effect is the owner reaction
the pet should now expect: owner:said_no when the owner wants less of it, owner:praised when more.
direction is "less" or "more". window_s is how soon that reaction would come (10 is typical).
context is "owner_home" unless the instruction is about times the owner is away.
text restates the rule in one short plain sentence from the pet's point of view.
If not an instruction: is_instruction false, trigger and outcome_or_effect "", direction "none", window_s 0,
context "none"."""


def parse_answer(sentence: str, ans: dict, date: str | None = None) -> tuple[dict | None, str]:
    """Model answer -> (rule or None, reason). Validates against the vocabulary."""
    if not ans.get("is_instruction"):
        return None, ans.get("reason") or "not an instruction"
    trig, out = ans.get("trigger", "").strip(), ans.get("outcome_or_effect", "").strip()
    if not E.is_known_pattern(trig):
        return None, f"trigger {trig!r} is outside the event vocabulary"
    if not E.is_known_pattern(out):
        return None, f"outcome {out!r} is outside the event vocabulary"
    date = date or dt.date.today().isoformat()
    ctx = None if ans.get("context") in (None, "none") else ans["context"]
    w = float(ans.get("window_s") or 10)
    rule = {
        "id": f"i{date.replace('-', '')}_{hashlib.md5(f'{trig}>{out}'.encode()).hexdigest()[:6]}",
        "kind": "operant", "trigger": trig, "outcome_or_effect": out,
        "weight": INSTRUCT_WEIGHT, "text": ans.get("text") or sentence,
        "evidence": {"confirm": 0, "omit": 0}, "window_s": min(max(w, 1.0), 600.0), "context": ctx,
        "source": "instruct", "created": date, "said": sentence, "direction": ans.get("direction", "less"),
    }
    return S.validate_rule(rule), "ok"


def instruct(sentence: str, *, model: str = SMALL_MODEL, backend: str | None = None, call=call_json,
             date: str | None = None, save: bool = False) -> tuple[dict | None, str]:
    vocab = sorted(f"{t}({k})" if k and k != "text" else t for t, k in E.VOCAB.items())
    user = json.dumps({"sentence": sentence, "vocabulary": vocab, "rooms": list(E.ROOMS)}, ensure_ascii=False)
    ans, _usage = call(SYSTEM, user, INSTRUCT_SCHEMA, model=model, purpose="instruct", backend=backend,
                       effort="low", max_tokens=1000, budget_usd=0.1)
    rule, reason = parse_answer(sentence, ans, date)
    if rule and save:
        rules = [r for r in S.load_rules() if (r["trigger"], r["outcome_or_effect"]) != (rule["trigger"], rule["outcome_or_effect"])]
        rules.append(rule)
        S.save_rules(rules)
    return rule, reason


def main() -> None:
    ap = argparse.ArgumentParser(description="Owner sentence -> operant rule")
    ap.add_argument("sentence")
    ap.add_argument("--save", action="store_true", help="write the rule into pet/state/rules.json")
    ap.add_argument("--model", default=SMALL_MODEL)
    ap.add_argument("--backend", default=None)
    a = ap.parse_args()
    rule, reason = instruct(a.sentence, model=a.model, backend=a.backend, save=a.save)
    print(json.dumps({"rule": rule, "reason": reason}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
