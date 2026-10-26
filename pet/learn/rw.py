"""Rescorla-Wagner weight updates for association rules.

  confirmation:  V <- V + alpha * (lambda - V)
  omission:      V <- V + alpha * (0 - V)
  unused:        V <- V * exp(-dt_days / tau_days)   (slow decay toward 0)

alpha is the learning rate (salience of trigger x outcome). One value per rule kind by
default; a rule may carry its own `alpha`.
"""
from __future__ import annotations

import math

ALPHA = {"pavlovian": 0.3, "operant": 0.15}
LAMBDA = 1.0
DECAY_TAU_DAYS = 10.0  # a rule untouched for 10 days keeps ~37 % of its weight
FORGET_BELOW = 0.05    # rules that fall under this are dropped at night


def alpha_for(rule: dict) -> float:
    return float(rule.get("alpha", ALPHA.get(rule.get("kind"), 0.15)))


def rw_update(v: float, alpha: float, present: bool, lam: float = LAMBDA) -> float:
    target = lam if present else 0.0
    v = v + alpha * (target - v)
    return min(1.0, max(0.0, v))


def confirm(rule: dict) -> dict:
    rule["weight"] = round(rw_update(rule["weight"], alpha_for(rule), True), 4)
    rule.setdefault("evidence", {"confirm": 0, "omit": 0})["confirm"] += 1
    return rule


def omit(rule: dict) -> dict:
    rule["weight"] = round(rw_update(rule["weight"], alpha_for(rule), False), 4)
    rule.setdefault("evidence", {"confirm": 0, "omit": 0})["omit"] += 1
    return rule


def decay(v: float, dt_days: float, tau_days: float = DECAY_TAU_DAYS) -> float:
    return v * math.exp(-max(0.0, dt_days) / tau_days)


def decay_unused(rules: list[dict], used_ids: set[str], dt_days: float = 1.0) -> list[dict]:
    """Apply one night's decay to every rule that saw no trial today; drop forgotten ones.
    Rules from owner instructions (source == 'instruct') never decay: what the owner says stays."""
    kept = []
    for r in rules:
        if r["id"] not in used_ids and r.get("source") != "instruct":
            r["weight"] = round(decay(r["weight"], dt_days), 4)
        if r["weight"] >= FORGET_BELOW or r.get("source") == "instruct":
            kept.append(r)
    return kept
