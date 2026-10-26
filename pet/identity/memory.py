"""Familiarity memory: embeddings by day, clustering at night.

Daytime: every usable face/voice observation is stored as an embedding row
{t, modality, vector, quality, provisional_id}. No images or audio are stored.

Night (`consolidate()`), per modality:
1. cluster the unassigned samples (HDBSCAN, fallback DBSCAN) on unit vectors;
2. prune each cluster to members that are similar (cosine >= pair threshold)
   to at least `min_samples_new_person - 1` other members. This is the
   ">= 3 similar samples" rule (Immich's minimum-faces rule): three loosely
   related strangers never become a person, because a centroid of three random
   unit vectors is ~0.58 cosine from each of them, while their pairwise
   cosine stays near 0;
3. link each surviving cluster to a known person by centroid cosine; if none
   matches, link it through co-occurrence with the other modality (a voice
   heard while a known face was in view); otherwise create a new person;
4. assign leftover single samples that sit close to a known person's centroid
   (an encounter, not enough to found a person);
5. recompute centroids, merge fragments (two persons whose centroids agree),
   delete unknown samples older than the retention window, cap stored samples
   per known person.

Familiarity = f(encounters, days seen, recency): see `familiarity()`.
The owner is registered manually, pinned, and never merged away or deleted.
"""
from __future__ import annotations

import math
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MODALITIES = ("face", "voice")
DAY_S = 86400.0


@dataclass
class MemoryConfig:
    # Pairwise cosine for two samples to count as "similar" (the >= 3 rule).
    # Face: buffalo_sc different people stayed <= 0.22 in bench.py;
    # voice: real test speech other-speaker <= 0.40.
    pair_cos: dict = field(default_factory=lambda: {"face": 0.35, "voice": 0.55})
    # Cluster centroid -> person centroid to link to an existing person.
    link_cos: dict = field(default_factory=lambda: {"face": 0.45, "voice": 0.60})
    # Person centroid <-> person centroid to merge fragments (stricter).
    merge_cos: dict = field(default_factory=lambda: {"face": 0.55, "voice": 0.70})
    # A single leftover sample counts as an encounter with a person above this.
    single_cos: dict = field(default_factory=lambda: {"face": 0.40, "voice": 0.60})
    min_samples_new_person: int = 3
    min_quality: float = 0.3
    unknown_retention_days: float = 14.0
    known_sample_cap: int = 200          # per person per modality (enrolment kept)
    co_occur_s: float = 10.0             # cross-modality linking window
    track_merge_min: int = 2             # samples of EACH person in one track to merge them
    encounter_gap_s: float = 600.0       # sightings further apart = new encounter
    fam_encounter_scale: float = 6.0     # log1p(encounters) / scale
    fam_day_scale: float = 4.0           # days seen / scale
    fam_recency_tau_days: float = 21.0   # e-folding of familiarity after last seen
    use_hdbscan: bool = True


SCHEMA = """
CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    kind TEXT NOT NULL DEFAULT 'known',      -- 'owner' | 'known'
    pinned INTEGER NOT NULL DEFAULT 0,
    created_t REAL NOT NULL,
    merged_into INTEGER                      -- set when a fragment is merged away
);
CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    t REAL NOT NULL,
    modality TEXT NOT NULL,
    vector BLOB NOT NULL,                    -- float32 L2-normalised
    quality REAL NOT NULL,
    provisional_id TEXT,                     -- daytime whois label, or 'enrol'
    track TEXT,                              -- tracker id: samples of one continuous track/visit
    person_id INTEGER REFERENCES persons(id)
);
CREATE INDEX IF NOT EXISTS samples_mod_person ON samples(modality, person_id);
CREATE INDEX IF NOT EXISTS samples_t ON samples(t);
CREATE TABLE IF NOT EXISTS centroids (
    person_id INTEGER NOT NULL REFERENCES persons(id),
    modality TEXT NOT NULL,
    vector BLOB NOT NULL,
    n INTEGER NOT NULL,
    PRIMARY KEY (person_id, modality)
);
-- Timestamps only (no biometrics): kept after sample vectors are capped.
CREATE TABLE IF NOT EXISTS sightings (
    person_id INTEGER NOT NULL REFERENCES persons(id),
    t REAL NOT NULL,
    modality TEXT NOT NULL,
    sample_id INTEGER UNIQUE
);
CREATE INDEX IF NOT EXISTS sightings_person ON sightings(person_id, t);
"""


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32).reshape(-1)
    return v / (np.linalg.norm(v) + 1e-12)


def _blob(v: np.ndarray) -> bytes:
    return _unit(v).astype(np.float32).tobytes()


def _vec(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)


def cluster_unit_vectors(x: np.ndarray, min_samples: int, pair_cos: float,
                         use_hdbscan: bool = True) -> np.ndarray:
    """Labels (-1 = noise) for unit vectors. HDBSCAN on euclidean distance of
    unit vectors (monotone in cosine); DBSCAN with eps from pair_cos if
    HDBSCAN is unavailable or fails."""
    n = len(x)
    if n < min_samples:
        return -np.ones(n, dtype=int)
    if use_hdbscan:
        try:
            from sklearn.cluster import HDBSCAN
            return HDBSCAN(min_cluster_size=min_samples, min_samples=min_samples - 1, allow_single_cluster=True,
                           metric="euclidean", copy=True).fit_predict(x)
        except Exception:  # pragma: no cover - fallback path
            pass
    from sklearn.cluster import DBSCAN
    eps = math.sqrt(max(0.0, 2.0 - 2.0 * pair_cos))
    return DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean").fit_predict(x)


def prune_similar(x: np.ndarray, idx: np.ndarray, pair_cos: float, k: int) -> np.ndarray:
    """Keep members similar to >= k-1 other kept members; iterate to a fixpoint."""
    keep = np.asarray(idx)
    while len(keep) >= k:
        s = x[keep] @ x[keep].T
        np.fill_diagonal(s, -1.0)
        ok = (s >= pair_cos).sum(1) >= k - 1
        if ok.all():
            return keep
        keep = keep[ok]
    return keep[:0]


def similar_groups(x: np.ndarray, idx: np.ndarray, pair_cos: float, k: int) -> list[np.ndarray]:
    """Prune a cluster with `prune_similar`, then split it into connected
    components of the similarity graph (edge = cosine >= pair_cos). A density
    cluster can hold two groups that are not similar to each other (two looks
    of one person, or two people); each group must pass the >= k rule alone."""
    keep = prune_similar(x, idx, pair_cos, k)
    if len(keep) == 0:
        return []
    adj = (x[keep] @ x[keep].T) >= pair_cos
    seen = np.zeros(len(keep), bool)
    groups = []
    for s in range(len(keep)):
        if seen[s]:
            continue
        stack, comp = [s], []
        seen[s] = True
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in np.where(adj[u] & ~seen)[0]:
                seen[v] = True
                stack.append(v)
        g = prune_similar(x, keep[np.array(comp)], pair_cos, k)
        if len(g) >= k:
            groups.append(g)
    return groups


class FamiliarityMemory:
    def __init__(self, path: str | Path = ":memory:", config: MemoryConfig | None = None):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)
        self.cfg = config or MemoryConfig()

    def close(self):
        self.db.close()

    # persons -------------------------------------------------------------
    def register_owner(self, name: str = "owner", t: float | None = None) -> int:
        row = self.db.execute("SELECT id FROM persons WHERE kind='owner' AND merged_into IS NULL").fetchone()
        if row:
            return row[0]
        cur = self.db.execute("INSERT INTO persons(name, kind, pinned, created_t) VALUES (?, 'owner', 1, ?)",
                              (name, time.time() if t is None else t))
        self.db.commit()
        return cur.lastrowid

    def owner_id(self) -> int | None:
        row = self.db.execute("SELECT id FROM persons WHERE kind='owner' AND merged_into IS NULL").fetchone()
        return row[0] if row else None

    def _new_person(self, t: float) -> int:
        cur = self.db.execute("INSERT INTO persons(name, kind, pinned, created_t) VALUES (NULL, 'known', 0, ?)", (t,))
        pid = cur.lastrowid
        self.db.execute("UPDATE persons SET name=? WHERE id=?", (f"p{pid}", pid))
        return pid

    def persons(self, include_merged: bool = False) -> list[dict]:
        q = "SELECT id, name, kind, pinned, created_t, merged_into FROM persons"
        if not include_merged:
            q += " WHERE merged_into IS NULL"
        return [dict(zip(("id", "name", "kind", "pinned", "created_t", "merged_into"), r))
                for r in self.db.execute(q + " ORDER BY id")]

    def label(self, pid: int) -> str:
        row = self.db.execute("SELECT kind, name FROM persons WHERE id=?", (pid,)).fetchone()
        if row is None:
            return f"p{pid}"
        return "owner" if row[0] == "owner" else f"known:{row[1]}"

    def resolve(self, pid: int) -> int:
        """Follow merges to the surviving person id."""
        seen = set()
        while pid not in seen:
            seen.add(pid)
            row = self.db.execute("SELECT merged_into FROM persons WHERE id=?", (pid,)).fetchone()
            if not row or row[0] is None:
                return pid
            pid = row[0]
        return pid

    # samples -------------------------------------------------------------
    def add_sample(self, t: float, modality: str, vector: np.ndarray, quality: float,
                   provisional_id: str | None = None, track: str | None = None) -> int:
        """Store one observation. `track` names one continuous face track (or a
        visit with a single person present); fragments found in the same track
        are merged at night."""
        assert modality in MODALITIES, modality
        cur = self.db.execute(
            "INSERT INTO samples(t, modality, vector, quality, provisional_id, track) VALUES (?, ?, ?, ?, ?, ?)",
            (t, modality, _blob(vector), float(quality), provisional_id, track))
        self.db.commit()
        return cur.lastrowid

    def enroll(self, pid: int, modality: str, vectors: list[np.ndarray], t: float | None = None,
               quality: float = 1.0) -> None:
        """Manual enrolment (owner): samples are assigned and never pruned."""
        t = time.time() if t is None else t
        for v in vectors:
            cur = self.db.execute(
                "INSERT INTO samples(t, modality, vector, quality, provisional_id, person_id) "
                "VALUES (?, ?, ?, ?, 'enrol', ?)", (t, modality, _blob(v), quality, pid))
            self.db.execute("INSERT OR IGNORE INTO sightings(person_id, t, modality, sample_id) VALUES (?,?,?,?)",
                            (pid, t, modality, cur.lastrowid))
        self._update_centroid(pid, modality)
        self.db.commit()

    def centroids(self, modality: str) -> dict[int, np.ndarray]:
        return {pid: _vec(b) for pid, b in self.db.execute(
            "SELECT c.person_id, c.vector FROM centroids c JOIN persons p ON p.id=c.person_id "
            "WHERE c.modality=? AND p.merged_into IS NULL", (modality,))}

    def _update_centroid(self, pid: int, modality: str) -> None:
        rows = self.db.execute("SELECT vector, quality FROM samples WHERE person_id=? AND modality=?",
                               (pid, modality)).fetchall()
        if not rows:
            self.db.execute("DELETE FROM centroids WHERE person_id=? AND modality=?", (pid, modality))
            return
        x = np.stack([_vec(b) for b, _ in rows])
        w = np.array([max(q, 0.05) for _, q in rows], dtype=np.float32)
        c = _unit((x * w[:, None]).sum(0))
        self.db.execute("INSERT OR REPLACE INTO centroids(person_id, modality, vector, n) VALUES (?,?,?,?)",
                        (pid, modality, c.tobytes(), len(rows)))

    def _assign(self, sample_ids, pid: int) -> None:
        for sid in sample_ids:
            sid = int(sid)
            self.db.execute("UPDATE samples SET person_id=? WHERE id=?", (pid, sid))
            t, m = self.db.execute("SELECT t, modality FROM samples WHERE id=?", (sid,)).fetchone()
            self.db.execute("INSERT OR IGNORE INTO sightings(person_id, t, modality, sample_id) VALUES (?,?,?,?)",
                            (pid, t, m, sid))

    # consolidation -------------------------------------------------------
    def _co_occurring_person(self, sample_ids, modality: str) -> int | None:
        """Person seen in the other modality within co_occur_s of most members."""
        other = [m for m in MODALITIES if m != modality]
        votes: dict[int, int] = {}
        w = self.cfg.co_occur_s
        for sid in sample_ids:
            t = self.db.execute("SELECT t FROM samples WHERE id=?", (int(sid),)).fetchone()[0]
            rows = self.db.execute(
                f"SELECT DISTINCT person_id FROM sightings WHERE modality IN ({','.join('?' * len(other))}) "
                "AND t BETWEEN ? AND ?", (*other, t - w, t + w)).fetchall()
            for (p,) in rows:
                p = self.resolve(p)
                votes[p] = votes.get(p, 0) + 1
        if not votes:
            return None
        p, v = max(votes.items(), key=lambda kv: kv[1])
        return p if v * 2 > len(sample_ids) else None

    def consolidate(self, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        cfg = self.cfg
        k = cfg.min_samples_new_person
        report = {"t": now, "linked": [], "created": [], "singles": 0, "merged": [], "deleted_unknown": 0}
        for m in MODALITIES:
            rows = self.db.execute(
                "SELECT id, vector FROM samples WHERE modality=? AND person_id IS NULL AND quality>=? "
                "AND t<=? ORDER BY t", (m, cfg.min_quality, now)).fetchall()
            if rows:
                ids = np.array([r[0] for r in rows])
                x = np.stack([_vec(r[1]) for r in rows])
                labels = cluster_unit_vectors(x, k, cfg.pair_cos[m], cfg.use_hdbscan)
                groups = [g for lab in sorted(set(labels) - {-1})
                          for g in similar_groups(x, np.where(labels == lab)[0], cfg.pair_cos[m], k)]
                for members in groups:
                    c = _unit(x[members].mean(0))
                    cents = self.centroids(m)
                    best, best_cos = None, -1.0
                    for pid, pc in cents.items():
                        s = float(pc @ c)
                        if s > best_cos:
                            best, best_cos = pid, s
                    if best is not None and best_cos >= cfg.link_cos[m]:
                        target = best
                        report["linked"].append((m, best, len(members), round(best_cos, 3)))
                    else:
                        co = self._co_occurring_person(ids[members], m)
                        if co is not None and co not in cents:
                            target = co
                            report["linked"].append((m, co, len(members), "co-occur"))
                        else:
                            target = self._new_person(now)
                            report["created"].append((m, target, len(members)))
                    self._assign(ids[members], target)
                    self._update_centroid(target, m)
                # Leftover singles that match a known person: an encounter.
                cents = self.centroids(m)
                if cents:
                    pids = list(cents)
                    cmat = np.stack([cents[p] for p in pids])
                    left = self.db.execute(
                        "SELECT id, vector FROM samples WHERE modality=? AND person_id IS NULL AND quality>=? "
                        "AND t<=?", (m, cfg.min_quality, now)).fetchall()
                    for sid, b in left:
                        s = cmat @ _vec(b)
                        j = int(np.argmax(s))
                        if s[j] >= cfg.single_cos[m]:
                            self._assign([sid], pids[j])
                            report["singles"] += 1
            for (pid,) in self.db.execute("SELECT id FROM persons WHERE merged_into IS NULL").fetchall():
                self._update_centroid(pid, m)
        report["merged"] = self._merge_fragments()
        report["deleted_unknown"] = self._retention(now)
        self.db.commit()
        return report

    def _merge_pair(self, a: int, b: int, why: str, s: float, people: dict) -> tuple | None:
        pa, pb = people[a], people[b]
        if pa["pinned"] and pb["pinned"]:
            return None  # two pinned people are never merged automatically
        # Survivor: pinned first, then older, then lower id.
        ka = (pa["pinned"], -pa["created_t"], -a)
        kb = (pb["pinned"], -pb["created_t"], -b)
        keep, drop = (a, b) if ka >= kb else (b, a)
        self.db.execute("UPDATE samples SET person_id=? WHERE person_id=?", (keep, drop))
        self.db.execute("UPDATE sightings SET person_id=? WHERE person_id=?", (keep, drop))
        self.db.execute("DELETE FROM centroids WHERE person_id=?", (drop,))
        self.db.execute("UPDATE persons SET merged_into=? WHERE id=?", (keep, drop))
        for mm in MODALITIES:
            self._update_centroid(keep, mm)
        return (keep, drop, why, round(s, 3))

    def _merge_candidates(self):
        """Yield (a, b, why, strength): centroid agreement in any modality, or
        both persons seen in one continuous track (a tracker cannot hold two
        people, so these are fragments of one person)."""
        for m in MODALITIES:
            cents = self.centroids(m)
            pids = sorted(cents)
            for i, a in enumerate(pids):
                for b in pids[i + 1:]:
                    s = float(cents[a] @ cents[b])
                    if s >= self.cfg.merge_cos[m]:
                        yield a, b, m, s
        rows = self.db.execute(
            "SELECT track, person_id, COUNT(*) FROM samples WHERE track IS NOT NULL AND person_id IS NOT NULL "
            "GROUP BY track, person_id").fetchall()
        by_track: dict = {}
        for tr, pid, n in rows:
            if n >= self.cfg.track_merge_min:
                by_track.setdefault(tr, []).append(pid)
        for tr, pids in by_track.items():
            pids = sorted(set(self.resolve(p) for p in pids))
            for i, a in enumerate(pids):
                for b in pids[i + 1:]:
                    yield a, b, f"track {tr}", 1.0

    def _merge_fragments(self) -> list[tuple]:
        merged = []
        while True:
            people = {p["id"]: p for p in self.persons()}
            done = None
            for a, b, why, s in self._merge_candidates():
                if a in people and b in people and a != b:
                    done = self._merge_pair(a, b, why, s, people)
                    if done:
                        break
            if not done:
                return merged
            merged.append(done)

    def _retention(self, now: float) -> int:
        cut = now - self.cfg.unknown_retention_days * DAY_S
        n = self.db.execute("DELETE FROM samples WHERE person_id IS NULL AND t < ?", (cut,)).rowcount
        # Cap stored vectors of known persons (sightings keep the history).
        for pid, m in self.db.execute("SELECT DISTINCT person_id, modality FROM samples WHERE person_id IS NOT NULL").fetchall():
            self.db.execute(
                "DELETE FROM samples WHERE id IN (SELECT id FROM samples WHERE person_id=? AND modality=? "
                "AND (provisional_id IS NULL OR provisional_id!='enrol') ORDER BY t DESC LIMIT -1 OFFSET ?)",
                (pid, m, self.cfg.known_sample_cap))
        return n

    # familiarity ---------------------------------------------------------
    def encounter_stats(self, pid: int) -> dict:
        ts = [r[0] for r in self.db.execute("SELECT t FROM sightings WHERE person_id=? ORDER BY t", (pid,))]
        if not ts:
            return {"encounters": 0, "days_seen": 0, "last_seen": None, "sightings": 0}
        enc = 1 + sum(1 for a, b in zip(ts, ts[1:]) if b - a > self.cfg.encounter_gap_s)
        days = len({int(t // DAY_S) for t in ts})
        return {"encounters": enc, "days_seen": days, "last_seen": ts[-1], "sightings": len(ts)}

    def familiarity(self, pid: int, now: float | None = None) -> float:
        """0..1. Saturating in encounters (log) and distinct days, decayed by
        time since last seen. The pinned owner is always 1."""
        now = time.time() if now is None else now
        row = self.db.execute("SELECT pinned FROM persons WHERE id=?", (pid,)).fetchone()
        if row and row[0]:
            return 1.0
        st = self.encounter_stats(pid)
        return familiarity_score(st["encounters"], st["days_seen"],
                                 None if st["last_seen"] is None else (now - st["last_seen"]) / DAY_S, self.cfg)


def familiarity_score(encounters: int, days_seen: int, days_since_last: float | None,
                      cfg: MemoryConfig | None = None) -> float:
    cfg = cfg or MemoryConfig()
    if encounters <= 0 or days_since_last is None:
        return 0.0
    strength = math.log1p(encounters) / cfg.fam_encounter_scale * 3.0 + days_seen / cfg.fam_day_scale
    base = 1.0 - math.exp(-strength / 2.0)
    recency = math.exp(-max(0.0, days_since_last) / cfg.fam_recency_tau_days)
    return float(base * recency)
