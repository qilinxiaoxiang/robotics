import math

import numpy as np
import pytest

from pet.identity.memory import DAY_S, FamiliarityMemory, MemoryConfig, familiarity_score
from pet.identity.synth import Identity, run_synthetic

T0 = 1_800_000_000.0


@pytest.fixture
def rng():
    return np.random.default_rng(1)


def mem(**kw):
    return FamiliarityMemory(":memory:", MemoryConfig(**kw))


def n_persons(m):
    return len(m.persons())


@pytest.mark.parametrize("hdb", [True, False])
def test_new_person_needs_three_similar_samples(rng, hdb):
    m = mem(use_hdbscan=hdb)
    who = Identity(rng, "visitor")
    for day in (1, 2):
        m.add_sample(T0 + day * DAY_S, "face", who.sample(rng, "face"), 0.9)
        m.consolidate(now=T0 + day * DAY_S + 3600)
        assert n_persons(m) == 0, f"person created from {day} sample(s)"
    m.add_sample(T0 + 3 * DAY_S, "face", who.sample(rng, "face"), 0.9)
    rep = m.consolidate(now=T0 + 3 * DAY_S + 3600)
    assert n_persons(m) == 1
    assert rep["created"][0][2] == 3


@pytest.mark.parametrize("hdb", [True, False])
def test_unrelated_strangers_never_become_a_person(rng, hdb):
    m = mem(use_hdbscan=hdb)
    for i in range(40):
        m.add_sample(T0 + i * 60, "face", Identity(rng, f"s{i}").sample(rng, "face"), 0.9)
    m.consolidate(now=T0 + DAY_S)
    assert n_persons(m) == 0


def test_low_quality_samples_do_not_count(rng):
    m = mem()
    who = Identity(rng, "v")
    for i in range(5):
        m.add_sample(T0 + i, "face", who.sample(rng, "face"), 0.1)
    m.consolidate(now=T0 + 3600)
    assert n_persons(m) == 0


def test_owner_samples_link_to_pinned_owner(rng):
    m = mem()
    owner = Identity(rng, "owner")
    oid = m.register_owner("shawn", t=T0)
    m.enroll(oid, "face", [owner.sample(rng, "face") for _ in range(5)], t=T0)
    for i in range(6):
        m.add_sample(T0 + DAY_S + i * 5, "face", owner.sample(rng, "face"), 0.9)
    m.consolidate(now=T0 + 2 * DAY_S)
    assert [p["id"] for p in m.persons()] == [oid]
    assert m.encounter_stats(oid)["sightings"] == 11
    assert m.familiarity(oid, T0 + 100 * DAY_S) == 1.0  # pinned


def test_fragments_merge_by_centroid(rng):
    m = mem()
    who = Identity(rng, "v")
    # Two fragments of one person (e.g. created under a stricter earlier config).
    a = m._new_person(T0)
    b = m._new_person(T0 + 10)
    for pid, day in ((a, 1), (b, 2)):
        ids = [m.add_sample(T0 + day * DAY_S + i, "face", who.sample(rng, "face"), 0.9) for i in range(4)]
        m._assign(ids, pid)
        m._update_centroid(pid, "face")
    rep = m.consolidate(now=T0 + 3 * DAY_S)
    assert rep["merged"] and rep["merged"][0][:2] == (a, b)   # older survives
    assert [p["id"] for p in m.persons()] == [a]
    st = m.encounter_stats(a)
    assert st["sightings"] == 8 and st["days_seen"] == 2


def test_fragments_merge_by_shared_track(rng):
    """Two looks too different for centroid merging, seen in one continuous track."""
    m = mem()
    who = Identity(rng, "v")
    g = rng.standard_normal(512)
    g -= (g @ who.face) * who.face
    g /= np.linalg.norm(g)
    look2 = 0.3 * who.face + math.sqrt(1 - 0.09) * g
    for i in range(4):
        m.add_sample(T0 + DAY_S + i, "face", who.sample(rng, "face"), 0.9, track="a")
    for i in range(4):
        m.add_sample(T0 + 2 * DAY_S + i, "face", who.sample(rng, "face", centre=look2), 0.9, track="b")
    m.consolidate(now=T0 + 2.5 * DAY_S)
    assert n_persons(m) == 2  # not similar enough to link or merge by centroid
    for i in range(4):
        c = who.face if i % 2 else look2
        m.add_sample(T0 + 3 * DAY_S + i, "face", who.sample(rng, "face", centre=c), 0.9, track="c")
    rep = m.consolidate(now=T0 + 3.5 * DAY_S)
    assert n_persons(m) == 1, rep
    assert "track c" in rep["merged"][0][2]


def test_pinned_owner_survives_merge_and_two_pinned_never_merge(rng):
    m = mem()
    owner = Identity(rng, "owner")
    oid = m.register_owner("shawn", t=T0 + 100)  # younger than the fragment
    m.enroll(oid, "face", [owner.sample(rng, "face") for _ in range(5)], t=T0 + 100)
    frag = m._new_person(T0)
    ids = [m.add_sample(T0 + i, "face", owner.sample(rng, "face"), 0.9) for i in range(4)]
    m._assign(ids, frag)
    m._update_centroid(frag, "face")
    rep = m.consolidate(now=T0 + DAY_S)
    assert rep["merged"][0][:2] == (oid, frag)
    assert m.owner_id() == oid
    # A second pinned person with the same face is left alone.
    m.db.execute("INSERT INTO persons(name, kind, pinned, created_t) VALUES ('twin', 'known', 1, ?)", (T0,))
    twin = m.db.execute("SELECT max(id) FROM persons").fetchone()[0]
    m.enroll(twin, "face", [owner.sample(rng, "face") for _ in range(3)], t=T0)
    rep = m.consolidate(now=T0 + 2 * DAY_S)
    assert rep["merged"] == []


def test_voice_cluster_links_to_face_person_by_cooccurrence(rng):
    m = mem()
    who = Identity(rng, "v")
    for i in range(4):
        t = T0 + DAY_S + i * 20
        m.add_sample(t, "face", who.sample(rng, "face"), 0.9)
        m.add_sample(t + 2, "voice", who.sample(rng, "voice"), 0.9)
    rep = m.consolidate(now=T0 + 2 * DAY_S)
    assert n_persons(m) == 1
    pid = m.persons()[0]["id"]
    assert set(m.centroids("voice")) == {pid}
    assert any(l[3] == "co-occur" for l in rep["linked"])


def test_retention_deletes_only_old_unknown_samples(rng):
    m = mem(unknown_retention_days=3)
    who = Identity(rng, "v")
    for i in range(3):
        m.add_sample(T0 + i, "face", who.sample(rng, "face"), 0.9)   # becomes a person
    m.add_sample(T0 + 5, "face", Identity(rng, "s1").sample(rng, "face"), 0.9)  # stranger, old
    m.add_sample(T0 + 4 * DAY_S, "face", Identity(rng, "s2").sample(rng, "face"), 0.9)  # stranger, recent
    rep = m.consolidate(now=T0 + 4.5 * DAY_S)
    assert rep["deleted_unknown"] == 1
    left = m.db.execute("SELECT COUNT(*) FROM samples WHERE person_id IS NULL").fetchone()[0]
    assert left == 1
    assert m.db.execute("SELECT COUNT(*) FROM samples WHERE person_id IS NOT NULL").fetchone()[0] == 3


def test_known_sample_cap_keeps_sightings(rng):
    m = mem(known_sample_cap=5)
    who = Identity(rng, "v")
    for i in range(12):
        m.add_sample(T0 + i * 1000, "face", who.sample(rng, "face"), 0.9)
    m.consolidate(now=T0 + DAY_S)
    pid = m.persons()[0]["id"]
    assert m.db.execute("SELECT COUNT(*) FROM samples WHERE person_id=?", (pid,)).fetchone()[0] == 5
    assert m.encounter_stats(pid)["sightings"] == 12


def test_familiarity_grows_with_encounters_and_days_and_decays():
    f = familiarity_score
    assert f(0, 0, None) == 0.0
    assert f(1, 1, 0) < f(5, 1, 0) < f(5, 3, 0) < f(20, 10, 0) < 1.0
    assert f(10, 5, 0) > f(10, 5, 7) > f(10, 5, 30)
    cfg = MemoryConfig()
    assert f(10, 5, cfg.fam_recency_tau_days) == pytest.approx(f(10, 5, 0) / math.e)


def test_familiarity_from_memory_grows_with_visits(rng):
    m = mem()
    who = Identity(rng, "v")
    fams = []
    for day in range(1, 6):
        for i in range(3):
            m.add_sample(T0 + day * DAY_S + i * 5, "face", who.sample(rng, "face"), 0.9)
        m.consolidate(now=T0 + day * DAY_S + 3600)
        fams.append(m.familiarity(m.persons()[0]["id"], T0 + day * DAY_S + 3600))
    assert all(b > a for a, b in zip(fams, fams[1:])), fams
    assert m.encounter_stats(m.persons()[0]["id"])["days_seen"] == 5


def test_synthetic_scenario_end_to_end():
    r = run_synthetic(verbose=False)
    h = {x["day"]: x for x in r["history"]}
    tp = r["truth_of_person"]
    created = {d: [tp[pid] for _, pid, _ in x["created"]] for d, x in h.items()}
    # neighbour: glimpses on days 2, 3 -> nothing; the third (day 5) -> a person
    assert not any("neighbour" in c for d in (2, 3, 4) for c in created[d])
    assert any(c == "neighbour" for c in created[5])
    # strangers never become persons
    assert not any("stranger" in str(v) for v in tp.values())
    # the cousin's two fragments merge on day 11
    assert h[11]["merged"]
    survivors = [p for p in r["persons_final"] if p["merged_into"] is None]
    assert sorted(tp[p["id"]] for p in survivors) == ["cousin", "friend", "neighbour", "owner"]
    nb = next(pid for pid, n in tp.items() if n == "neighbour")
    fam = lambda d: h[d]["persons"][nb]["familiarity"]
    assert fam(12) > fam(7) > fam(5)
    fr = next(pid for pid, n in tp.items() if n == "friend")
    assert h[14]["persons"][fr]["familiarity"] < h[4]["persons"][fr]["familiarity"]
