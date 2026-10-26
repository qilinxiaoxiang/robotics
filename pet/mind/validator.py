"""Validator: the only door from a model's answer to the body.

Admits only primitives (or validated skills) from the body card, numeric params inside their ranges, satisfied
preconditions (posture is tracked across the steps through each primitive's effects; a parameterless posture primitive
whose posture already holds and whose precondition fails is dropped as a no-op), at most MAX_STEPS steps and a
bounded duration. There is no field through which a raw joint command could pass: a step is a primitive name plus
its declared parameters, nothing else.
"""
from __future__ import annotations

from .body import BodyCard, check_condition, closest_to_zero

MAX_STEPS = 6
MAX_DURATION_S = 30.0
MAX_SKILL_STEPS = 6


def skill_steps_ok(skill: dict, body: BodyCard) -> list[str]:
    """Errors for a skill on this body, ignoring preconditions (checked when it runs)."""
    errs = []
    steps = skill.get("steps") or []
    if not steps or len(steps) > MAX_SKILL_STEPS:
        errs.append(f"skill {skill.get('name')}: needs 1-{MAX_SKILL_STEPS} steps")
    for s in steps:
        errs += _param_errors(s.get("primitive"), s.get("params") or {}, body, where=f"skill {skill.get('name')}")
    return errs


def usable_skills(skills: list, body: BodyCard) -> dict:
    """Skills whose steps all validate on this body, by name. Skills shadowing a primitive are dropped."""
    return {s["name"]: s for s in skills or [] if s.get("name") and s["name"] not in body.primitives
            and not skill_steps_ok(s, body)}


def _param_errors(name, params, body: BodyCard, where="step") -> list[str]:
    if name not in body.primitives:
        return [f"{where}: unknown primitive '{name}' (allowed: {', '.join(body.primitives)})"]
    if not isinstance(params, dict):
        return [f"{where}: params of {name} must be an object"]
    spec = body.primitives[name].get("params", {})
    errs = []
    for k, val in params.items():
        if k not in spec:
            errs.append(f"{where}: {name} has no parameter '{k}' (has: {', '.join(spec) or 'none'})")
            continue
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            errs.append(f"{where}: {name}.{k} must be a number, got {val!r}")
            continue
        lo, hi = spec[k]
        if not lo <= val <= hi:
            errs.append(f"{where}: {name}.{k}={val} outside [{lo}, {hi}]")
    return errs


def _expand(steps, body, skills, errs):
    """Expand skill calls into primitive steps; returns [(primitive, params, skill_name_or_None, guards)]."""
    out = []
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            errs.append(f"step {i + 1}: must be an object")
            continue
        name, params = s.get("primitive"), s.get("params") or {}
        extra = set(s) - {"primitive", "params"}
        if extra:
            errs.append(f"step {i + 1}: unexpected keys {sorted(extra)}; a step is only primitive + params")
        if name in skills and name not in body.primitives:
            if params:
                errs.append(f"step {i + 1}: skill {name} takes no params")
            sk = skills[name]
            for j, inner in enumerate(sk["steps"]):
                out.append((inner["primitive"], dict(inner.get("params") or {}), name,
                            sk.get("guards", []) if j == 0 else []))
            continue
        errs += _param_errors(name, params, body, where=f"step {i + 1}")
        out.append((name, dict(params), None, []))
    return out


def validate(obj, body: BodyCard, skills: dict, facts: dict, max_steps=MAX_STEPS,
             max_duration=MAX_DURATION_S) -> tuple[dict | None, list[str], list[str]]:
    """Returns (intention or None, errors, unchecked conditions).

    The intention is {intention_text, steps: [{primitive, params, seconds, skill}], duration_s, abort_if, mood_note}
    with every parameter filled in.
    """
    errs, unchecked = [], []
    if not isinstance(obj, dict):
        return None, ["answer must be one JSON object"], unchecked
    steps = obj.get("steps")
    if not isinstance(steps, list) or not steps:
        return None, ["steps must be a non-empty list"], unchecked
    if len(steps) > max_steps:
        errs.append(f"{len(steps)} steps; at most {max_steps}")
    expanded = _expand(steps, body, skills, errs)
    if errs:
        return None, errs, unchecked
    posture = facts.get("posture", "standing")
    out_steps, total = [], 0.0
    for i, (name, params, skill, guards) in enumerate(expanded):
        prim = body.primitives[name]
        filled = {k: params.get(k, closest_to_zero(lo, hi)) for k, (lo, hi) in prim.get("params", {}).items()}
        f = {**facts, "standing": posture == "standing", "sitting": posture == "sitting",
             "lying": posture == "lying"}
        if (prim.get("effects", {}).get("posture") == posture and not prim.get("params") and not guards
                and any(check_condition(c, f) is False for c in prim.get("preconditions", []))):
            continue  # sit while already sitting: nothing to do, not an error
        for cond in list(guards) + list(prim.get("preconditions", [])):
            ok = check_condition(cond, f)
            if ok is None:
                unchecked.append(f"{name}: {cond}")
            elif not ok:
                kind = f"skill {skill} guard" if cond in guards else f"precondition of {name}"
                errs.append(f"step {i + 1}: {kind} '{cond}' not satisfied (posture {posture})")
        secs = body.step_seconds(name, filled)
        if secs > float(prim.get("duration_s_max", secs)):
            errs.append(f"step {i + 1}: {name} lasts {secs}s, max {prim['duration_s_max']}s")
        total += secs
        posture = prim.get("effects", {}).get("posture", posture)
        out_steps.append({"primitive": name, "params": filled, "seconds": secs, "skill": skill})
    if not out_steps and not errs:
        errs.append(f"every step only sets the posture it already has ({posture})")
    duration = obj.get("duration_s", total)
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        errs.append("duration_s must be a number")
        duration = total
    if duration > max_duration:
        errs.append(f"duration_s {duration} > max {max_duration}")
    if total > max_duration:
        errs.append(f"steps take {total:.1f}s > max {max_duration}s")
    abort_if = obj.get("abort_if") or []
    if not isinstance(abort_if, list) or not all(isinstance(a, str) for a in abort_if):
        errs.append("abort_if must be a list of strings")
        abort_if = []
    for a in abort_if:
        if check_condition(a, facts) is None:
            unchecked.append(f"abort_if: {a}")
    if errs:
        return None, errs, unchecked
    return {"intention_text": str(obj.get("intention_text", "")).strip()[:200], "steps": out_steps,
            "duration_s": max(float(duration), total), "abort_if": abort_if[:4],
            "mood_note": str(obj.get("mood_note", "")).strip()[:80]}, [], unchecked
