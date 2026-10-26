"""Synthetic embedding days: shows the >= 3 rule, fragment merging, familiarity
growth/decay and whois fusion without a camera or microphone.

Each identity is a random unit centre in 512-d; a sample is
unit(centre + sigma * g), g ~ N(0, I / dim), so cos(sample, centre) ~
1 / sqrt(1 + sigma^2). Face sigma 1.0 gives same-person pairwise cosine ~0.5
(buffalo_sc in-the-wild range); voice sigma 0.75 gives ~0.64 (CAM++ real
speech same-speaker 0.63-0.74 in bench.py). Different identities are ~0.

Cast (day 0 = enrolment):
- owner: enrolled (5 face angles + 3 voice phrases), seen every day;
- neighbour: one face glimpse on days 2, 3 and 5 -> becomes a person on night 5
  (the third similar sample), then visits on days 7, 9, 10 and 12;
- friend: one visit on day 4 (4 face + 3 voice samples) -> person that night,
  voice linked by co-occurrence; never returns, familiarity decays;
- cousin: day 8 in dim light and day 9 in daylight (two face sub-centres
  ~0.3 cosine apart) -> two fragment persons; on day 11 one continuous track
  contains both looks, and the track rule merges the fragments that night;
- strangers: two different one-off faces every day; never become persons and
  are deleted after the retention window.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .memory import DAY_S, FamiliarityMemory, MemoryConfig
from .whois import Whois, scores_against

DIM = 512
FACE_SIGMA = 1.0
VOICE_SIGMA = 0.75


def unit(v):
    return v / np.linalg.norm(v)


class Identity:
    def __init__(self, rng, name):
        self.name = name
        self.face = unit(rng.standard_normal(DIM))
        self.voice = unit(rng.standard_normal(DIM))

    def sample(self, rng, modality, centre=None, sigma=None):
        c = self.face if modality == "face" else self.voice
        c = c if centre is None else centre
        s = (FACE_SIGMA if modality == "face" else VOICE_SIGMA) if sigma is None else sigma
        return unit(c + s * rng.standard_normal(DIM) / np.sqrt(DIM))


def _shifted(rng, centre, cos):
    """A unit vector at the given cosine from centre (lighting/glasses sub-centre)."""
    g = rng.standard_normal(DIM)
    g -= (g @ centre) * centre
    g = unit(g)
    return unit(cos * centre + np.sqrt(1 - cos ** 2) * g)


def build_schedule(rng):
    owner, nb, fr, cz = (Identity(rng, n) for n in ("owner", "neighbour", "friend", "cousin"))
    cz_dim = _shifted(rng, cz.face, 0.55)
    cz_day = _shifted(rng, cz.face, 0.55)
    visits = []  # (day, hour, who, [(modality, vector)])

    def visit(day, hour, who, faces, voices, centre=None):
        centres = centre if isinstance(centre, list) else [centre] * faces
        obs = [("face", who.sample(rng, "face", c)) for c in centres]
        obs += [("voice", who.sample(rng, "voice")) for _ in range(voices)]
        rng.shuffle(obs)
        visits.append((day, hour, who.name, obs))

    for d in range(1, 15):
        visit(d, 8.0, owner, 4, 2)
        visit(d, 19.0, owner, 4, 2)
    for d in (2, 3, 5):
        visit(d, 13.0, nb, 1, 0)
    for d in (7, 9, 10, 12):
        visit(d, 15.0, nb, 3, 2)
    visit(4, 17.0, fr, 4, 3)
    visit(8, 20.0, cz, 4, 0, centre=cz_dim)
    visit(9, 11.0, cz, 4, 0, centre=cz_day)
    visit(11, 16.0, cz, 4, 0, centre=[cz_dim, cz_day, cz_dim, cz_day])  # one track, light changes
    for d in range(1, 15):
        for k in range(2):
            s = Identity(rng, f"stranger-d{d}-{k}")
            visit(d, 10.0 + 3 * k, s, 1, 1 if k == 0 else 0)
    visits.sort(key=lambda v: (v[0], v[1]))
    return owner, [nb, fr, cz], visits


def run_synthetic(days: int = 14, seed: int = 0, db_path=":memory:", out_dir: Path | None = None,
                  config: MemoryConfig | None = None, verbose: bool = True) -> dict:
    rng = np.random.default_rng(seed)
    cfg = config or MemoryConfig(unknown_retention_days=7.0)
    mem = FamiliarityMemory(db_path, cfg)
    owner, others, visits = build_schedule(rng)
    t0 = 1_800_000_000.0 - (1_800_000_000.0 % DAY_S)  # a midnight, fixed for reproducibility

    oid = mem.register_owner("owner", t=t0)
    mem.enroll(oid, "face", [owner.sample(rng, "face") for _ in range(5)], t=t0 + 9 * 3600)
    mem.enroll(oid, "voice", [owner.sample(rng, "voice") for _ in range(3)], t=t0 + 9 * 3600)

    history = []
    whois_log = []
    truth_of_person: dict[int, str] = {oid: "owner"}
    for day in range(1, days + 1):
        for vi, (vd, hour, who, obs) in enumerate(visits):
            if vd != day:
                continue
            w = Whois()
            t = t0 + day * DAY_S + hour * 3600
            for i, (m, v) in enumerate(obs):
                ts = t + 2.0 * i
                mem.add_sample(ts, m, v, quality=0.9, provisional_id=None, track=f"v{vi}")
                w.observe(ts, m, scores_against(mem.centroids(m), v), quality=0.9)
            dec = w.decide(labeler=mem.label)
            whois_log.append({"day": day, "hour": hour, "truth": who, "label": dec.label,
                              "confidence": round(dec.confidence, 3), "n_obs": len(obs)})
        now = t0 + (day + 1) * DAY_S - 3600  # 23:00
        rep = mem.consolidate(now=now)
        # Attribute persons to ground truth for reporting (majority of samples' visit).
        persons = mem.persons()
        fam = {}
        for p in persons:
            st = mem.encounter_stats(p["id"])
            fam[p["id"]] = {"label": mem.label(p["id"]), "familiarity": round(mem.familiarity(p["id"], now), 3),
                            **{k: v for k, v in st.items() if k != "last_seen"}}
        n_unknown = mem.db.execute("SELECT COUNT(*) FROM samples WHERE person_id IS NULL").fetchone()[0]
        history.append({"day": day, "created": rep["created"], "linked": rep["linked"], "merged": rep["merged"],
                        "singles": rep["singles"], "deleted_unknown": rep["deleted_unknown"],
                        "unknown_samples_kept": n_unknown, "persons": fam})
    # Ground truth for each surviving person: nearest synthetic identity centre.
    centres = {"owner": owner.face, **{o.name: o.face for o in others}}
    for p in mem.persons():
        c = mem.centroids("face").get(p["id"])
        if c is not None:
            truth_of_person[p["id"]] = max(centres, key=lambda n: float(centres[n] @ c))
    for p in mem.persons(include_merged=True):
        if p["merged_into"] is not None:
            truth_of_person[p["id"]] = truth_of_person.get(mem.resolve(p["id"]), "?") + f" (merged into p{mem.resolve(p['id'])})"
    result = {"history": history, "whois": whois_log, "truth_of_person": truth_of_person,
              "persons_final": mem.persons(include_merged=True)}
    if verbose:
        _print(result)
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "synthetic_run.json").write_text(json.dumps(result, indent=1, default=str))
        _plot(result, out_dir)
    mem.close()
    return result


def _print(r):
    tp = r["truth_of_person"]
    for h in r["history"]:
        ev = []
        ev += [f"NEW {m} p{pid}({tp.get(pid, '?')}) from {n} samples" for m, pid, n in h["created"]]
        ev += [f"MERGE p{d}->p{k} ({m}, {s})" for k, d, m, s in h["merged"]]
        ev += [f"link {m}->p{pid} n={n} ({how})" for m, pid, n, how in h["linked"] if pid != 1]
        fam = ", ".join(f"{v['label']}={v['familiarity']:.2f}(enc {v['encounters']}, days {v['days_seen']})"
                        for v in h["persons"].values())
        print(f"night {h['day']:2d}: unknown kept {h['unknown_samples_kept']:2d}, deleted {h['deleted_unknown']:2d} | "
              + ("; ".join(ev) or "-"))
        print(f"          {fam}")
    print("\nwhois per visit (truth -> label @ confidence):")
    for w in r["whois"]:
        if w["truth"].startswith("stranger") and w["day"] not in (1, 14):
            continue
        print(f"  day {w['day']:2d} {w['hour']:5.1f}h {w['truth']:18s} -> {w['label']:14s} @ {w['confidence']:.2f}"
              f" ({w['n_obs']} obs)")


def _plot(r, out_dir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tp = r["truth_of_person"]
    days = [h["day"] for h in r["history"]]
    series: dict[str, list] = {}
    for h in r["history"]:
        for pid, v in h["persons"].items():
            series.setdefault(f"p{pid} ({tp.get(int(pid), '?')})", [None] * len(days))
    for i, h in enumerate(r["history"]):
        for pid, v in h["persons"].items():
            series[f"p{pid} ({tp.get(int(pid), '?')})"][i] = v["familiarity"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    for name, ys in series.items():
        ax[0].plot(days, [np.nan if y is None else y for y in ys], marker="o", label=name)
    for h in r["history"]:
        for k, d, m, s in h["merged"]:
            ax[0].axvline(h["day"], color="grey", ls=":", lw=1)
            ax[0].text(h["day"], 0.02, f" merge p{d}->p{k}", rotation=90, fontsize=8, color="grey")
    ax[0].set_xlabel("day (value after that night's consolidation)")
    ax[0].set_ylabel("familiarity")
    ax[0].set_ylim(0, 1.05)
    ax[0].set_title("Familiarity per person")
    ax[0].legend(fontsize=8, loc="lower left")
    ax[1].plot(days, [h["unknown_samples_kept"] for h in r["history"]], marker="s", label="unknown samples kept")
    ax[1].plot(days, [len(h["persons"]) for h in r["history"]], marker="o", label="persons")
    ax[1].bar(days, [h["deleted_unknown"] for h in r["history"]], alpha=0.3, label="unknown deleted (retention)")
    ax[1].set_xlabel("day")
    ax[1].set_title("Memory size (strangers never become persons)")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "synthetic_familiarity.png", dpi=120)
    plt.close(fig)
