"""Who is this? Log-odds fusion of face and voice (and later silhouette) cues.

One `Whois` instance tracks one person in view (one face track, or the voice
heard while that track is the only person present). Each observation turns
the cosine similarity to every known person's centroid into a log-likelihood
ratio (LLR) and adds it to that person's accumulator; all accumulators decay
toward 0 with time constant `tau_s`, so old evidence fades when the person
leaves and a new person starts from "unsure".

    LLR_c = clip(slope * (cos_c - match_cos), -max_llr, +max_llr) * quality
    L_c(t) = L_c(t_prev) * exp(-(t - t_prev) / tau_s) + LLR_c

A separate "stranger" accumulator gains evidence when the best similarity to
anyone is below `stranger_cos`:

    LLR_stranger = clip(slope * (stranger_cos - max_c cos_c), -max_llr, +max_llr) * quality

Each accumulator is clamped to +-max_abs (as in occupancy-grid log-odds), so a
long run of agreeing frames cannot build up evidence that takes minutes to
overturn; frame-rate observations are correlated, so callers should also
rate-limit (the demo feeds faces at <= 4 Hz).

Decision: a person wins when L >= accept and leads the runner-up by margin;
"stranger" when its accumulator >= accept; otherwise "unsure". Confidence is
sigmoid(L) of the reported label.

Cues: face and voice are anchors. A non-anchor cue (silhouette, OSNet later)
only reinforces candidates an anchor already supports (L_c > 0) and never adds
stranger evidence, so clothing alone cannot name or reject anyone.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class CueModel:
    name: str
    match_cos: float       # cosine at which same/different are equally likely
    slope: float           # LLR per unit cosine
    max_llr: float         # per-observation clip
    stranger_cos: float    # best cosine below this is evidence for a stranger
    anchor: bool = True


DEFAULT_CUES = {
    # buffalo_sc: different people <= 0.22, same-person (augmented) >= 0.92 in
    # bench.py; in-the-wild same-person pairs typically 0.4-0.8.
    "face": CueModel("face", match_cos=0.40, slope=12.0, max_llr=4.0, stranger_cos=0.25),
    # CAM++ zh+en: same >= 0.71, other <= 0.48 on real test speech (3 s windows).
    "voice": CueModel("voice", match_cos=0.60, slope=12.0, max_llr=3.0, stranger_cos=0.45),
    # Placeholder for the Tier 2 silhouette cue; calibrate before enabling.
    "silhouette": CueModel("silhouette", match_cos=0.60, slope=6.0, max_llr=1.5, stranger_cos=0.0, anchor=False),
}

STRANGER = "stranger"


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class Decision:
    label: str                   # 'owner' | 'known:<name>' | 'stranger' | 'unsure'
    confidence: float            # sigmoid of the winning accumulator (0.5 = no evidence)
    person_id: int | None
    log_odds: dict = field(default_factory=dict)


class Whois:
    def __init__(self, cues: dict[str, CueModel] | None = None, tau_s: float = 20.0,
                 accept: float = 2.2, margin: float = 1.0, max_abs: float = 6.0):
        self.cues = dict(cues or DEFAULT_CUES)
        self.tau_s = tau_s
        self.accept = accept          # sigmoid(2.2) ~ 0.90
        self.margin = margin
        self.max_abs = max_abs        # sigmoid(6) ~ 0.9975
        self.L: dict = {}
        self.t: float | None = None

    def register_cue(self, cue: CueModel) -> None:
        self.cues[cue.name] = cue

    def reset(self) -> None:
        self.L.clear()
        self.t = None

    def _decay_to(self, t: float) -> None:
        if self.t is not None and t > self.t:
            f = math.exp(-(t - self.t) / self.tau_s)
            for k in self.L:
                self.L[k] *= f
        if self.t is None or t > self.t:
            self.t = t

    def observe(self, t: float, cue: str, scores: dict, quality: float = 1.0) -> dict:
        """scores: {person_id: cosine to that person's centroid in this cue}.
        Returns the LLRs added (for logging)."""
        cm = self.cues[cue]
        self._decay_to(t)
        q = max(0.0, min(1.0, quality))
        added = {}
        for pid, s in scores.items():
            llr = max(-cm.max_llr, min(cm.max_llr, cm.slope * (s - cm.match_cos))) * q
            if not cm.anchor and (self.L.get(pid, 0.0) <= 0.0 or llr < 0):
                continue
            self.L[pid] = self._clamp(self.L.get(pid, 0.0) + llr)
            added[pid] = llr
        if cm.anchor:
            best = max(scores.values()) if scores else -1.0
            llr = max(-cm.max_llr, min(cm.max_llr, cm.slope * (cm.stranger_cos - best))) * q
            self.L[STRANGER] = self._clamp(self.L.get(STRANGER, 0.0) + llr)
            added[STRANGER] = llr
        return added

    def _clamp(self, v: float) -> float:
        return max(-self.max_abs, min(self.max_abs, v))

    def decide(self, t: float | None = None, labeler=None) -> Decision:
        if t is not None:
            self._decay_to(t)
        people = {k: v for k, v in self.L.items() if k != STRANGER}
        ranked = sorted(people.items(), key=lambda kv: kv[1], reverse=True)
        lab = labeler or (lambda pid: f"known:p{pid}")
        snap = {str(k): round(v, 3) for k, v in self.L.items()}
        if ranked:
            pid, lb = ranked[0]
            runner = ranked[1][1] if len(ranked) > 1 else 0.0
            if lb >= self.accept and lb - max(runner, self.L.get(STRANGER, 0.0)) >= self.margin:
                return Decision(lab(pid), sigmoid(lb), pid, snap)
        ls = self.L.get(STRANGER, 0.0)
        if ls >= self.accept and (not ranked or ls - ranked[0][1] >= self.margin):
            return Decision(STRANGER, sigmoid(ls), None, snap)
        top = max([ls] + [v for _, v in ranked]) if (ranked or STRANGER in self.L) else 0.0
        return Decision("unsure", sigmoid(top), None, snap)


def scores_against(centroids: dict[int, np.ndarray], vector: np.ndarray) -> dict[int, float]:
    v = np.asarray(vector, dtype=np.float32)
    v = v / (np.linalg.norm(v) + 1e-12)
    return {pid: float(c @ v) for pid, c in centroids.items()}
