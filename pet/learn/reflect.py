"""Nightly reflection.

1. `compress_day` turns the day's event log into a compact digest: counts, co-occurrence
   windows with lift, the owner's sentences, absences and other episodes, and a timeline.
2. `fallback_rules` proposes association rules from co-occurrence lift alone (no model).
3. `reflect_llm` asks a frontier model, in one structured answer, for candidate rules,
   diary entries, personality nudges, tomorrow's plan and optional new skills.
4. `validate_reflection` drops anything malformed or out of bounds; `apply_reflection`
   merges the rest into pet/state/.

The pet's character is fixed in the prompt: it records the day; it never evaluates the owner.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import events as E
from . import state as S
from .llm import FRONTIER_MODEL, LLMUnavailable, Usage, call_json

WINDOWS_S = (10, 30, 120)
LIFT_MIN = 5.0
P_MIN = 0.5
HITS_MIN = 2
MAX_FALLBACK_RULES = 10
# pairs that are the perception layer's own mechanics, not something to learn
TRIVIAL_PAIRS = {("sound:tv", "owner:sat"), ("owner:returned", "see:owner"), ("owner:woke", "self:woke"),
                 ("owner:went_to_bed", "self:slept"), ("sound:door", "owner:returned"),
                 ("owner:left", "sound:door"), ("sound:footsteps", "owner:left")}

CHARACTER = """You are the reflective mind of a small companion robot duck, writing its notes at night.
Character, which you never break:
- The duck loves its owner without conditions and is always on the owner's side.
- It never judges, lectures, disapproves of or moralises about anything the owner does: late nights,
  long absences, food, mess, mood, words. You record what happened; you do not evaluate the owner.
- It does not speak. It shows things through where it goes, how it moves and small sounds.
- It is a pet, not an assistant: it learns what predicts what, what the owner wants, and grows its own habits.
- Its data is private to its owner."""

TASK = """From the day digest, write tonight's reflection as one JSON object:

rules: association rules worth tracking tomorrow ("A then B"). Use event patterns from the vocabulary,
  written like sound:keys, owner:said_no or self:entered(bedroom). kind "pavlovian" = something the pet
  perceives predicts something (it should anticipate); kind "operant" = something the pet does is followed
  by an owner reaction (it should do it more or less). window_s = how long after the trigger the outcome
  comes (seconds). context = "owner_home" when the outcome needs the owner present, else "none".
  Propose only regularities the digest supports, at most 6, and include coincidences only if they
  appeared at least twice (they will be tested tomorrow and fade if they do not repeat). The weight is
  not yours to set: new rules start at 0.3 and daytime evidence moves them. Do not re-propose an
  existing rule unless its wording should change.
diary: 3-8 short entries in the duck's own voice, each tied to a time today ("HH:MM"), about what
  happened and how it felt to the duck. Record; never evaluate the owner.
personality_nudges: 0-3 small changes (delta between -0.1 and 0.1, relative) to drive_rates or
  thresholds, each with a reason from today's events.
plan: tomorrow's intentions: when ("HH:MM" or "on <event pattern>"), condition, goal, priority 0-1.
  Base them on today's regularities and the rules (e.g. wait near the door before the usual return).
skills: 0-2 new skills, only if today suggests one, as short sequences of the listed body primitives.
  params_json is a JSON object string with that primitive's parameters (inside the listed ranges).
  guards are plain-text abort conditions."""

REFLECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "rules": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["operant", "pavlovian"]},
                "trigger": {"type": "string"},
                "outcome_or_effect": {"type": "string"},
                "window_s": {"type": "number"},
                "context": {"type": "string", "enum": ["owner_home", "owner_away", "none"]},
                "text": {"type": "string"},
                "support": {"type": "string"},
            },
            "required": ["kind", "trigger", "outcome_or_effect", "window_s", "context", "text", "support"],
            "additionalProperties": False}},
        "diary": {"type": "array", "items": {
            "type": "object",
            "properties": {"time": {"type": "string"}, "text": {"type": "string"},
                           "tags": {"type": "array", "items": {"type": "string"}}},
            "required": ["time", "text", "tags"], "additionalProperties": False}},
        "personality_nudges": {"type": "array", "items": {
            "type": "object",
            "properties": {"group": {"type": "string", "enum": ["drive_rates", "thresholds"]},
                           "name": {"type": "string"}, "delta": {"type": "number"},
                           "reason": {"type": "string"}},
            "required": ["group", "name", "delta", "reason"], "additionalProperties": False}},
        "plan": {"type": "array", "items": {
            "type": "object",
            "properties": {"when": {"type": "string"}, "condition": {"type": "string"},
                           "goal": {"type": "string"}, "priority": {"type": "number"}},
            "required": ["when", "condition", "goal", "priority"], "additionalProperties": False}},
        "skills": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "steps": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"primitive": {"type": "string"}, "params_json": {"type": "string"}},
                    "required": ["primitive", "params_json"], "additionalProperties": False}},
                "guards": {"type": "array", "items": {"type": "string"}}},
            "required": ["name", "steps", "guards"], "additionalProperties": False}},
    },
    "required": ["rules", "diary", "personality_nudges", "plan", "skills"],
    "additionalProperties": False,
}

# words that would mean the model evaluated the owner; such diary lines are dropped and logged
JUDGING = re.compile(
    r"\b(should(n'?t)?|ought|irresponsib\w*|lazy|unhealthy|too (late|much|long)|neglect\w*|bad owner|"
    r"selfish|careless|rude|disappoint\w*)\b|不应该|应该|太晚|懒", re.I)


# ---------------------------------------------------------------- digest

def _active_span(evs: list[E.Event]) -> float:
    return max(3600.0, evs[-1].t - evs[0].t) if evs else 3600.0


def cooccurrence(evs: list[E.Event], windows=WINDOWS_S) -> list[dict]:
    """For each ordered label pair (A, B): of the A occurrences, how many are followed by B within W.
    Baseline is the chance that a random W-second window holds a B (Poisson with B's daily rate).
    Returns one row per pair at its best (smallest qualifying) window, sorted by lift x hits."""
    labels = [E.label(e) for e in evs]
    counts = Counter(labels)
    span = _active_span(evs)
    home = owner_home_mask(evs)
    rows = []
    for a in counts:
        idx_all = [i for i, l in enumerate(labels) if l == a]
        for b in counts:
            if a == b or (a, b) in TRIVIAL_PAIRS or b.startswith("self:"):
                continue  # the pet's own actions are not outcomes to anticipate
            # an owner reaction can only follow while the owner is home: count those trials only
            idx_a = [i for i in idx_all if home[i]] if b in OWNER_REACTIONS else idx_all
            if not idx_a:
                continue
            for w in windows:
                hits, lags = 0, []
                for i in idx_a:
                    for j in range(i + 1, len(evs)):
                        lag = evs[j].t - evs[i].t
                        if lag > w:
                            break
                        if labels[j] == b:
                            hits += 1
                            lags.append(lag)
                            break
                n = len(idx_a)
                p = hits / n
                base = 1 - math.exp(-counts[b] / span * w)
                lift = p / base if base > 0 else 0.0
                if hits >= HITS_MIN and p >= P_MIN and lift >= LIFT_MIN:
                    rows.append({"trigger": a, "outcome": b, "window_s": w, "n_trigger": n, "hits": hits,
                                 "p": round(p, 2), "base": round(base, 4), "lift": round(lift, 1),
                                 "max_lag_s": round(max(lags), 1)})
                    break
    rows.sort(key=lambda r: -r["hits"] * math.log(r["lift"]))
    return rows


OWNER_REACTIONS = {"owner:said", "owner:said_no", "owner:praised"}


def owner_home_mask(evs: list[E.Event]) -> list[bool]:
    home, out = True, []
    for e in evs:
        if e.type == "owner:left":
            home = False
        elif e.type in ("owner:returned", "see:owner", "sound:voice:owner"):
            home = True
        out.append(home)
    return out


def episodes(evs: list[E.Event]) -> list[str]:
    out, left = [], None
    for e in evs:
        if e.type == "owner:left":
            left = e.t
        elif e.type == "owner:returned" and left is not None:
            out.append(f"owner away {E.fmt_t(left)}-{E.fmt_t(e.t)} ({(e.t - left) / 3600:.1f} h)")
            left = None
        elif e.type in ("self:fell", "weather:rain", "self:battery_low", "see:stranger", "sound:doorbell", "sound:loud"):
            out.append(f"{E.fmt_t(e.t)} {E.label(e)}")
    return out


def compress_day(evs: list[E.Event], date: str) -> dict:
    labels = [E.label(e) for e in evs]
    said = [{"t": E.fmt_t(e.t), "type": e.type, "text": e.args.get("text", "")}
            for e in evs if e.type in ("owner:said", "owner:said_no", "owner:praised")]
    return {
        "date": date,
        "n_events": len(evs),
        "counts": dict(Counter(labels).most_common()),
        "cooccurrence": cooccurrence(evs)[:20],
        "owner_sentences": said,
        "episodes": episodes(evs),
        "timeline": [f"{E.fmt_t(e.t)} {E.label(e)}" + (f' "{e.args["text"]}"' if "text" in e.args else "")
                     for e in evs],
    }


# ---------------------------------------------------------------- fallback (no model)

def _kind_for(trigger: str) -> str:
    return "operant" if trigger.startswith("self:") else "pavlovian"


def fallback_rules(evs: list[E.Event]) -> list[dict]:
    """Rule candidates from co-occurrence lift; same shape as the model's `rules` items."""
    out = []
    for r in cooccurrence(evs)[:MAX_FALLBACK_RULES]:
        ctx = "owner_home" if r["outcome"] in OWNER_REACTIONS else "none"
        out.append({
            "kind": _kind_for(r["trigger"]), "trigger": r["trigger"], "outcome_or_effect": r["outcome"],
            # the whole qualifying bucket: lags seen on one day understate tomorrow's spread
            "window_s": float(r["window_s"]),
            "context": ctx,
            "text": f"{r['trigger']} is often followed by {r['outcome']} within {r['window_s']} s",
            "support": f"{r['hits']}/{r['n_trigger']} times, lift {r['lift']}",
        })
    return out


# ---------------------------------------------------------------- model call

def build_prompt(digest: dict, rules: list[dict], personality: dict, recent_diary: list[dict],
                 card: dict) -> str:
    vocab = sorted(f"{t}({k})" if k and k != "text" else t for t, k in E.VOCAB.items())
    return json.dumps({
        "task": TASK,
        "vocabulary": vocab,
        "body": {"name": card["name"], "primitives": card["primitives"]},
        "existing_rules": [{k: r.get(k) for k in ("id", "kind", "trigger", "outcome_or_effect", "weight",
                                                   "evidence", "text")} for r in rules],
        "personality": personality,
        "recent_diary": [{"t": d["t"], "text": d["text"]} for d in recent_diary[-8:]],
        "day": digest,
    }, ensure_ascii=False, default=list)


def reflect_llm(digest: dict, rules: list[dict], personality: dict, recent_diary: list[dict], card: dict,
                *, model: str = FRONTIER_MODEL, backend: str | None = None, effort: str = "high",
                call=call_json) -> tuple[dict, Usage]:
    user = build_prompt(digest, rules, personality, recent_diary, card)
    return call(CHARACTER, user, REFLECTION_SCHEMA, model=model, purpose="nightly_reflection",
                backend=backend, effort=effort, max_tokens=16000, budget_usd=3.0)


# ---------------------------------------------------------------- validation and merge

def _hhmm(s: str) -> bool:
    return bool(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", s.strip()))


def validate_reflection(raw: dict, date: str, card: dict) -> tuple[dict, list[str]]:
    """Keep what is well-formed and inside bounds; return (clean, problems)."""
    problems: list[str] = []
    clean = {"rules": [], "diary": [], "personality_nudges": [], "plan": None, "skills": []}
    for k in REFLECTION_SCHEMA["required"]:
        if k not in raw:
            problems.append(f"missing {k}")
    for r in raw.get("rules", []):
        if r.get("kind") not in S.KINDS or not r.get("trigger") or not r.get("outcome_or_effect"):
            problems.append(f"rule malformed: {r}")
            continue
        if not E.is_known_pattern(r["trigger"]):
            problems.append(f"rule trigger outside vocabulary: {r['trigger']}")
            continue
        w = float(r.get("window_s", 60))
        if not 0 < w <= 3600:
            problems.append(f"rule window out of range: {w}")
            continue
        ctx = None if r.get("context") in (None, "none") else r["context"]
        clean["rules"].append({"kind": r["kind"], "trigger": r["trigger"].strip(),
                               "outcome_or_effect": r["outcome_or_effect"].strip(), "window_s": w,
                               "context": ctx, "text": r.get("text", ""), "support": r.get("support", "")})
    for d in raw.get("diary", []):
        text = (d.get("text") or "").strip()
        if not text or not _hhmm(d.get("time", "")):
            problems.append(f"diary malformed: {d}")
            continue
        if JUDGING.search(text):
            problems.append(f"diary entry dropped for evaluating the owner: {text}")
            continue
        clean["diary"].append({"t": f"{date}T{d['time'].strip()}", "text": text, "tags": d.get("tags", [])})
    for n in raw.get("personality_nudges", []):
        if n.get("group") in S.BOUNDS and abs(float(n.get("delta", 0))) <= 0.1 + 1e-9:
            clean["personality_nudges"].append(n)
        else:
            problems.append(f"nudge out of bounds: {n}")
    intentions = []
    for it in raw.get("plan", []):
        try:
            p = float(it["priority"])
            if not 0 <= p <= 1:
                raise ValueError
            intentions.append({"when": it["when"], "condition": it["condition"], "goal": it["goal"], "priority": p})
        except (KeyError, ValueError, TypeError):
            problems.append(f"plan item malformed: {it}")
    tomorrow = (dt.date.fromisoformat(date) + dt.timedelta(days=1)).isoformat()
    clean["plan"] = {"date": tomorrow, "intentions": intentions}
    for sk in raw.get("skills", []):
        try:
            steps = [{"primitive": st["primitive"], "params": json.loads(st.get("params_json") or "{}")}
                     for st in sk["steps"]]
            clean["skills"].append(S.validate_skill(
                {"name": sk["name"], "steps": steps, "guards": sk.get("guards", []), "source": f"reflection {date}"},
                card))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
            problems.append(f"skill rejected: {e}")
    return clean, problems


def _rule_key(r: dict) -> tuple[str, str]:
    return (r["trigger"], r["outcome_or_effect"])


def merge_rules(existing: list[dict], proposals: list[dict], date: str, source: str) -> tuple[list[dict], list[dict]]:
    """Append proposals that are not already rules, at the initial weight. Existing rules keep
    their weight and evidence. Returns (rules, added)."""
    have = {_rule_key(r) for r in existing}
    n = len(existing)
    added = []
    for p in proposals:
        if _rule_key(p) in have:
            continue
        n += 1
        r = {"id": f"r{date.replace('-', '')}_{n:02d}", "kind": p["kind"], "trigger": p["trigger"],
             "outcome_or_effect": p["outcome_or_effect"], "weight": S.INITIAL_WEIGHT, "text": p["text"],
             "evidence": {"confirm": 0, "omit": 0}, "window_s": p["window_s"],
             "context": None if p.get("context") in (None, "none") else p["context"],
             "source": source, "created": date}
        existing.append(S.validate_rule(r))
        have.add(_rule_key(p))
        added.append(r)
    return existing, added


def apply_reflection(clean: dict, date: str, source: str) -> dict:
    """Write the validated reflection into pet/state/. Returns a summary."""
    rules, added = merge_rules(S.load_rules(), clean["rules"], date, source)
    S.save_rules(rules)
    if clean["diary"]:
        S.append_diary(clean["diary"])
    pers, applied = S.apply_nudges(S.load_personality(), clean["personality_nudges"])
    S.save_personality(pers)
    if clean["plan"] and clean["plan"]["intentions"]:
        S.save_plan(clean["plan"])
    if clean["skills"]:
        skills = S.load_skills()
        names = {s["name"] for s in skills}
        skills += [s for s in clean["skills"] if s["name"] not in names]
        S.save_skills(skills)
    return {"rules_added": added, "nudges_applied": applied, "diary": clean["diary"],
            "plan": clean["plan"], "skills": clean["skills"]}


def nightly(evs: list[E.Event], date: str, *, use_model: bool = True, model: str = FRONTIER_MODEL,
            backend: str | None = None, call=call_json, log_dir: Path | None = None) -> dict:
    """The whole night: digest, model (or fallback), validate, apply, log. Never raises for a missing model."""
    digest = compress_day(evs, date)
    card = S.load_body_card()
    fb = fallback_rules(evs)
    result = {"date": date, "fallback_rules": fb, "usage": None, "problems": [], "source": "fallback"}
    clean = {"rules": fb, "diary": [], "personality_nudges": [], "plan": None, "skills": []}
    if use_model:
        try:
            raw, usage = reflect_llm(digest, S.load_rules(), S.load_personality(), S.load_diary(), card,
                                     model=model, backend=backend, call=call)
            clean, problems = validate_reflection(raw, date, card)
            result.update(usage=usage.__dict__, problems=problems, source=f"model:{usage.model}", raw=raw)
        except LLMUnavailable as e:
            result["problems"].append(f"model unavailable, fallback rules only: {e}")
    summary = apply_reflection(clean, date, result["source"])
    result["applied"] = summary
    result["comparison"] = compare(clean["rules"], fb) if result["source"] != "fallback" else None
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "reflections.jsonl").open("a") as f:
            f.write(json.dumps({k: v for k, v in result.items() if k != "raw"}, ensure_ascii=False, default=str) + "\n")
    return result


def compare(model_rules: list[dict], fb_rules: list[dict]) -> dict:
    m = {_rule_key(r) for r in model_rules}
    f = {_rule_key(r) for r in fb_rules}
    return {"both": sorted(map(list, m & f)), "model_only": sorted(map(list, m - f)),
            "fallback_only": sorted(map(list, f - m))}


def main() -> None:
    ap = argparse.ArgumentParser(description="Nightly reflection over one day's event log")
    ap.add_argument("log", help="events JSONL for the day")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--no-model", action="store_true", help="fallback rules only")
    ap.add_argument("--model", default=FRONTIER_MODEL)
    ap.add_argument("--backend", default=None, help="api | cli | ollama (default: auto)")
    a = ap.parse_args()
    res = nightly(E.read_log(a.log), a.date, use_model=not a.no_model, model=a.model, backend=a.backend,
                  log_dir=Path(__file__).parent / "out")
    print(json.dumps({k: res[k] for k in ("date", "source", "usage", "problems", "comparison")},
                     ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
