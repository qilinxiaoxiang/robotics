"""Persisted mind state: plain JSON files under pet/state/ (shared with pet/mind).

Schemas (pet/state/README.md is canonical; these match the brief it was written from):
  rules.json        [{id, kind: operant|pavlovian, trigger, outcome_or_effect, weight 0-1, text,
                      evidence: {confirm, omit}}]
                    optional keys written by pet/learn and ignored by readers that do not need them:
                      window_s (trigger -> outcome window, default 60), context ("owner_home" or null),
                      source ("reflection"|"fallback"|"instruct"), created, last_used (ISO dates)
  plan.json         {date, intentions: [{when, condition, goal, priority}]}
  diary.jsonl       {t, text, tags, embedding?}
  personality.json  {drive_rates, thresholds, traits_text}
  skills.json       [{name, steps: [{primitive, params}], guards: [text], source}]
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import events as E

REPO = Path(__file__).resolve().parents[2]
STATE_DIR = Path(os.environ.get("PET_STATE_DIR", REPO / "pet" / "state"))

KINDS = ("operant", "pavlovian")
CONTEXTS = (None, "owner_home", "owner_away")
INITIAL_WEIGHT = 0.3

DEFAULT_PERSONALITY = {
    "drive_rates": {"social": 1.0, "explore": 1.0, "rest": 1.0, "play": 1.0, "hunger": 1.0},
    "thresholds": {"social": 0.6, "explore": 0.6, "rest": 0.7, "play": 0.6, "hunger": 0.8},
    "traits_text": "A small, curious duck. Loves its owner without conditions and is always on their side.",
}
# Nightly nudges move a value by at most MAX_NUDGE (relative) and never outside BOUNDS.
BOUNDS = {"drive_rates": (0.5, 2.0), "thresholds": (0.3, 0.9)}
MAX_NUDGE = 0.10

# Built-in duck primitives, used when pet/state/body_card.json and examples are absent.
DUCK_PRIMITIVES = {
    "stand": {}, "sit": {}, "sleep_pose": {},
    "walk": {"vx": (-0.15, 0.25), "vtheta": (-0.3, 0.3), "duration_s": (0.5, 20)},
    "turn_to": {"target": ["owner", "sound", "door", "object"]},
    "go_to": {"place": ["door", "bed", "owner", "charger", "window", "kitchen", "living_room", "hallway"]},
    "look": {"pitch": (-0.6, 0.4), "yaw": (-1.0, 1.0)},
    "head_tilt": {"side": ["left", "right"]},
    "nod": {}, "shake_head": {},
    "mouth": {"state": ["open", "close"]},
    "vocalise": {"kind": ["quack", "soft_quack", "chirp", "happy_trill"]},
    "wiggle": {}, "wait": {"duration_s": (1, 600)},
    "follow": {"target": ["owner"], "duration_s": (5, 300)},
}


def path(name: str) -> Path:
    return STATE_DIR / name


def _read_json(p: Path, default):
    if not p.exists():
        return default
    return json.loads(p.read_text())


def _write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(p)


# ---------------------------------------------------------------- rules

def validate_rule(r: dict) -> dict:
    """Return a normalised copy or raise ValueError."""
    for k in ("id", "kind", "trigger", "outcome_or_effect", "weight", "text"):
        if k not in r:
            raise ValueError(f"rule missing {k}: {r}")
    if r["kind"] not in KINDS:
        raise ValueError(f"rule kind {r['kind']!r}")
    w = float(r["weight"])
    if not 0.0 <= w <= 1.0:
        raise ValueError(f"rule weight {w} outside 0-1")
    ev = r.get("evidence") or {}
    out = dict(r)
    out["weight"] = w
    out["evidence"] = {"confirm": int(ev.get("confirm", 0)), "omit": int(ev.get("omit", 0))}
    if out.get("context") not in CONTEXTS:
        raise ValueError(f"rule context {out.get('context')!r}")
    if "window_s" in out:
        out["window_s"] = float(out["window_s"])
        if not 0 < out["window_s"] <= 3600:
            raise ValueError("window_s must be in (0, 3600]")
    return out


def rule_is_matchable(r: dict) -> bool:
    """A rule whose trigger and outcome are both vocabulary patterns can be tracked by match.py.
    Operant rules from owner instructions may have a behavioural effect instead (e.g. 'go less');
    those are matched on their trigger only (use counts), never confirmed or omitted."""
    return E.is_known_pattern(r["trigger"]) and E.is_known_pattern(r["outcome_or_effect"])


def load_rules() -> list[dict]:
    return [validate_rule(r) for r in _read_json(path("rules.json"), [])]


def save_rules(rules: list[dict]) -> None:
    _write_json(path("rules.json"), [validate_rule(r) for r in rules])


# ---------------------------------------------------------------- plan

def validate_plan(p: dict) -> dict:
    if "date" not in p or not isinstance(p.get("intentions"), list):
        raise ValueError("plan needs date and intentions[]")
    for it in p["intentions"]:
        for k in ("when", "condition", "goal", "priority"):
            if k not in it:
                raise ValueError(f"intention missing {k}: {it}")
        it["priority"] = float(it["priority"])
        if not 0 <= it["priority"] <= 1:
            raise ValueError("priority must be in 0-1")
    return p


def load_plan() -> dict | None:
    p = _read_json(path("plan.json"), None)
    return validate_plan(p) if p else None


def save_plan(p: dict) -> None:
    _write_json(path("plan.json"), validate_plan(p))


# ---------------------------------------------------------------- diary

def validate_diary(e: dict) -> dict:
    if not isinstance(e.get("t"), str) or not isinstance(e.get("text"), str) or not e["text"].strip():
        raise ValueError(f"diary entry needs t (ISO string) and text: {e}")
    e = dict(e)
    e["tags"] = [str(x) for x in e.get("tags") or []]
    return e


def load_diary() -> list[dict]:
    p = path("diary.jsonl")
    if not p.exists():
        return []
    return [validate_diary(json.loads(line)) for line in p.read_text().splitlines() if line.strip()]


def append_diary(entries: list[dict]) -> None:
    p = path("diary.jsonl")
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        for e in entries:
            f.write(json.dumps(validate_diary(e), ensure_ascii=False) + "\n")


def save_diary(entries: list[dict]) -> None:
    p = path("diary.jsonl")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(validate_diary(e), ensure_ascii=False) + "\n" for e in entries))


# ---------------------------------------------------------------- personality

def validate_personality(p: dict) -> dict:
    for k in ("drive_rates", "thresholds", "traits_text"):
        if k not in p:
            raise ValueError(f"personality missing {k}")
    for group, (lo, hi) in BOUNDS.items():
        for name, v in p[group].items():
            if not lo <= float(v) <= hi:
                raise ValueError(f"{group}.{name}={v} outside [{lo}, {hi}]")
    return p


def load_personality() -> dict:
    return validate_personality(_read_json(path("personality.json"), json.loads(json.dumps(DEFAULT_PERSONALITY))))


def save_personality(p: dict) -> None:
    _write_json(path("personality.json"), validate_personality(p))


def apply_nudges(p: dict, nudges: list[dict]) -> tuple[dict, list[dict]]:
    """nudges: [{group, name, delta, reason}] with delta relative (+0.05 = 5 % up).
    Each delta is clipped to +-MAX_NUDGE and the result to BOUNDS. Returns (new, applied)."""
    p = json.loads(json.dumps(p))
    applied = []
    for n in nudges:
        g, name = n.get("group"), n.get("name")
        if g not in BOUNDS or name not in p[g]:
            continue
        d = max(-MAX_NUDGE, min(MAX_NUDGE, float(n.get("delta", 0))))
        lo, hi = BOUNDS[g]
        old = float(p[g][name])
        new = round(max(lo, min(hi, old * (1 + d))), 4)
        p[g][name] = new
        applied.append({"group": g, "name": name, "from": old, "to": new, "reason": n.get("reason", "")})
    return p, applied


# ---------------------------------------------------------------- skills / body card

def load_body_card() -> dict:
    """{'name', 'primitives': {name: {param: (lo, hi) | [choices]}}} from pet/state/body_card.json,
    else the first card in pet/state/examples/, else the built-in duck list."""
    for p in [path("body_card.json"), *sorted(path("examples").glob("*body_card*.json"))]:
        if p.exists():
            card = json.loads(p.read_text())
            prims = card.get("primitives", {})
            if isinstance(prims, list):  # list form [{name, params:{...}}]
                prims = {x["name"]: x.get("params", {}) for x in prims}
            return {"name": card.get("name", p.stem), "primitives": prims, "source": str(p)}
    return {"name": "microduck (built-in list)", "primitives": DUCK_PRIMITIVES, "source": "built-in"}


def _param_ok(spec, v) -> bool:
    if isinstance(spec, (list, tuple)) and len(spec) == 2 and all(isinstance(x, (int, float)) for x in spec):
        return isinstance(v, (int, float)) and spec[0] <= v <= spec[1]
    if isinstance(spec, list):
        return v in spec
    if isinstance(spec, dict) and ("min" in spec or "max" in spec):
        return isinstance(v, (int, float)) and spec.get("min", -1e9) <= v <= spec.get("max", 1e9)
    return True  # unknown spec shape: accept, the body layer validates again


def validate_skill(s: dict, card: dict) -> dict:
    if not s.get("name") or not isinstance(s.get("steps"), list) or not s["steps"]:
        raise ValueError(f"skill needs name and steps: {s}")
    prims = card["primitives"]
    for st in s["steps"]:
        prim = st.get("primitive")
        if prim not in prims:
            raise ValueError(f"skill {s['name']}: unknown primitive {prim!r}")
        params = st.get("params") or {}
        spec = prims[prim] or {}
        for k, v in params.items():
            if k not in spec:
                raise ValueError(f"skill {s['name']}: {prim} has no param {k!r}")
            if not _param_ok(spec[k], v):
                raise ValueError(f"skill {s['name']}: {prim}.{k}={v!r} out of range")
    s = dict(s)
    s["guards"] = [str(g) for g in s.get("guards") or []]
    s.setdefault("source", "reflection")
    return s


def load_skills() -> list[dict]:
    return _read_json(path("skills.json"), [])


def save_skills(skills: list[dict]) -> None:
    card = load_body_card()
    _write_json(path("skills.json"), [validate_skill(s, card) for s in skills])
