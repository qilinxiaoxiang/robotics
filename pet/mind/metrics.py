"""Rigidity check: how varied is a day of intentions?"""
from __future__ import annotations

import math
import re
from collections import Counter


def _norm(text: str) -> str:
    return re.sub(r"[^a-z ]", "", text.lower()).strip()


def rigidity(history: list[dict], body=None) -> dict:
    """history: Mind.history entries. Repeats are counted on the primitive sequence (what the body does)."""
    n = len(history)
    if not n:
        return {"intentions": 0}
    seqs = [tuple(h["signature"]) for h in history]
    full = [tuple(h["steps"]) for h in history]
    counts = Counter(seqs)
    repeat_prev = sum(1 for a, b in zip(seqs, seqs[1:]) if a == b)
    run = best = 1
    for a, b in zip(seqs, seqs[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    entropy = -sum(c / n * math.log2(c / n) for c in counts.values())
    return {"intentions": n,
            "distinct_intention_texts": len({_norm(h["text"]) for h in history}),
            "distinct_action_sequences": len(counts),
            "distinct_with_params": len(set(full)),
            "repeat_of_previous": repeat_prev,
            "repeat_of_previous_rate": round(repeat_prev / max(1, n - 1), 3),
            "longest_identical_run": best,
            "sequence_entropy_bits": round(entropy, 2),
            "primitives_used": sorted({p for s in seqs for p in s}),
            **_context(history, body),
            "most_common": [[" -> ".join(s), c] for s, c in counts.most_common(3)],
            "sources": dict(Counter(h["source"] for h in history))}


def _share(hs, test):
    return round(sum(1 for h in hs if test(h)) / len(hs), 2) if hs else None


def _context(history: list[dict], body=None) -> dict:
    """Does behaviour depend on the situation? Gestures at the owner should follow the owner; posture should not
    churn. A social gesture is a primitive tagged social and not orient (nod, wave, beckon, approach_owner), so
    turning the head toward a sound does not count."""
    if body is None or "owner_visible" not in history[0]:
        return {}

    def has(h, want, unless=()):
        return any(want in body.tags(p) and not set(unless) & set(body.tags(p)) for p in h["signature"])

    seen = [h for h in history if h["owner_visible"]]
    unseen = [h for h in history if not h["owner_visible"]]
    return {"intentions_owner_in_view": len(seen), "intentions_owner_not_in_view": len(unseen),
            "gesture_share_owner_in_view": _share(seen, lambda h: has(h, "social", ("orient",))),
            "gesture_share_owner_not_in_view": _share(unseen, lambda h: has(h, "social", ("orient",))),
            "locomotion_share_owner_in_view": _share(seen, lambda h: has(h, "locomotion")),
            "locomotion_share_owner_not_in_view": _share(unseen, lambda h: has(h, "locomotion")),
            "posture_changes": sum(h.get("posture_changes", 0) for h in history),
            "rest_share": _share(history, lambda h: has(h, "rest", ("orient",)))}
