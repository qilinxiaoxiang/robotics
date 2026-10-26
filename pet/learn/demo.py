"""Seven synthetic days through the whole loop: day -> matcher (Rescorla-Wagner) -> night ->
reflection -> next day. `python -m pet.learn.demo`.

State lives in pet/learn/out/state/ (never pet/state/), so the demo cannot overwrite the pet's real mind.
Nights use the statistical fallback so the run is offline and reproducible; one extra reflection on
day 1 goes to the frontier model (API key, else the claude CLI, else skipped) and is compared with
the fallback. Acceptance checks are printed at the end and set the exit code.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

from . import events as E
from . import llm
from . import match as M
from . import reflect as R
from . import retrieve
from . import rw
from . import state as S

OUT = Path(__file__).resolve().parent / "out"
START = dt.date(2026, 11, 2)
TARGETS = {
    "keys -> owner leaves": ("sound:keys", "owner:left"),
    "bedroom -> owner says no": ("self:entered(bedroom)", "owner:said_no"),
    "TV -> doorbell (spurious)": ("sound:tv", "sound:doorbell"),
}


def find(rules, key):
    return next((r for r in rules if (r["trigger"], r["outcome_or_effect"]) == key), None)


def plot(history, trials_by_day, path_all, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"keys -> owner leaves": "#2b6cb0", "bedroom -> owner says no": "#c05621", "TV -> doorbell (spurious)": "#718096"}
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    days = sorted(history)
    for name in TARGETS:
        ys = [history[d].get(name) for d in days]
        ax.plot(days, [y if y is not None else float("nan") for y in ys], "o-", label=name, color=colors[name])
    ax.axhline(0.75, ls=":", color="#2b6cb0", lw=1)
    ax.axhline(0.8, ls=":", color="#c05621", lw=1)
    ax.set_xlabel("end of day")
    ax.set_ylabel("rule weight V")
    ax.set_ylim(0, 1)
    ax.set_title("Rule weights after each day (rules are born at night 1 at 0.3)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path_all, dpi=120)
    plt.close(fig)
    for d, trials in trials_by_day.items():
        fig, ax = plt.subplots(figsize=(7.5, 3.2))
        for name in TARGETS:
            pts = [(t["t"] / 3600, t["weight"], t["result"]) for t in trials if t["name"] == name]
            if not pts:
                continue
            xs, ys, res = zip(*pts)
            ax.step(xs, ys, where="post", color=colors[name], label=name)
            for x, y, r in pts:
                ax.plot(x, y, "o" if r == "confirm" else "x", color=colors[name], ms=5)
        ax.set_xlim(6, 24)
        ax.set_ylim(0, 1)
        ax.set_xlabel("hour of day (o confirmation, x omission)")
        ax.set_ylabel("V")
        ax.set_title(f"Day {d}: trials during the day")
        if ax.get_legend_handles_labels()[0]:
            ax.legend(loc="lower right", fontsize=7)
        fig.tight_layout()
        fig.savefig(out_dir / f"day{d}.png", dpi=110)
        plt.close(fig)


def real_reflection(day1_events, date, backend, model):
    """One frontier-model reflection on day 1 in its own state dir; returns a printable summary."""
    S.STATE_DIR = OUT / "state_llm"
    shutil.rmtree(S.STATE_DIR, ignore_errors=True)
    b = llm.available_backend(backend)
    if b is None:
        return {"skipped": "no ANTHROPIC_API_KEY, no ant profile, no claude CLI"}
    try:
        res = R.nightly(day1_events, date, use_model=True, model=model, backend=b, log_dir=OUT)
    except Exception as e:  # noqa: BLE001  network, refusal, quota: report, do not crash the demo
        return {"skipped": f"model call failed: {type(e).__name__}: {e}"}
    (OUT / "reflection_day1.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return {"backend": b, "source": res["source"], "usage": res["usage"], "problems": res["problems"],
            "comparison": res["comparison"],
            "rules": [f"{r['kind']}: {r['trigger']} -> {r['outcome_or_effect']} ({r['window_s']:.0f} s)"
                      for r in res["applied"]["rules_added"]],
            "diary": [d["text"] for d in res["applied"]["diary"]],
            "plan": res["applied"]["plan"]["intentions"] if res["applied"]["plan"] else [],
            "nudges": res["applied"]["nudges_applied"],
            "skills": res["applied"]["skills"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-llm", action="store_true", help="skip the frontier-model reflection")
    ap.add_argument("--backend", default=None, help="api | cli | ollama (default auto)")
    ap.add_argument("--model", default=llm.FRONTIER_MODEL)
    ap.add_argument("--fuzzy-model", action="store_true", help="small model for fuzzy 'no' sentences (default keywords)")
    a = ap.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    S.STATE_DIR = OUT / "state"
    shutil.rmtree(S.STATE_DIR, ignore_errors=True)
    (OUT / "days").mkdir(exist_ok=True)
    fuzzy = M.FuzzyJudge(use_model=a.fuzzy_model, backend=a.backend)

    history: dict[int, dict] = {}
    trials_by_day: dict[int, list] = {}
    day1 = None
    for d, evs in E.iter_days(a.days, a.seed):
        date = (START + dt.timedelta(days=d - 1)).isoformat()
        E.write_log(OUT / "days" / f"day{d}.jsonl", evs)
        day1 = day1 or (evs, date)
        # daytime: matcher updates weights in place
        rules = S.load_rules()
        m = M.Matcher(rules, fuzzy)
        m.feed_all(evs)
        m.end_of_day()
        names = {r["id"]: n for n, k in TARGETS.items() if (r := find(rules, k))}
        trials_by_day[d] = [{**x, "name": names[x["rule"]]} for x in m.log if x["rule"] in names]
        rules = rw.decay_unused(rules, m.used_ids)
        S.save_rules(rules)
        # night: reflection (fallback) proposes new rules, diary stays empty without a model
        res = R.nightly(evs, date, use_model=False)
        rules = S.load_rules()
        history[d] = {n: (r["weight"] if (r := find(rules, k)) else None) for n, k in TARGETS.items()}
        added = ", ".join(f"{r['trigger']}->{r['outcome_or_effect']}" for r in res["applied"]["rules_added"])
        print(f"day {d} {date}: {len(evs)} events, {sum(1 for x in m.log if x['result'] != 'void')} trials; "
              + "; ".join(f"{n} {v:.2f}" if v is not None else f"{n} -" for n, v in history[d].items())
              + (f"  | new tonight: {added}" if added else ""))

    plot(history, trials_by_day, OUT / "weights_by_day.png", OUT)
    (OUT / "weights_by_day.json").write_text(json.dumps(history, indent=2))
    final_rules = S.load_rules()

    keys4 = history.get(4, {}).get("keys -> owner leaves")
    bed = [history[d]["bedroom -> owner says no"] for d in history if d >= 4 and history[d]["bedroom -> owner says no"]]
    bed_mean = sum(bed) / len(bed) if bed else None
    spur = [history[d]["TV -> doorbell (spurious)"] for d in sorted(history)]
    spur_born = next((v for v in spur if v is not None), None)
    spur_end = spur[-1]
    checks = {
        "keys rule > 0.75 by end of day 4": keys4 is not None and keys4 > 0.75,
        "bedroom rule settles near 0.8 (mean of days 4-7 within 0.65-0.95)": bed_mean is not None and 0.65 <= bed_mean <= 0.95,
        "spurious rule decays (end weight below its birth weight, or forgotten)": spur_born is not None and (spur_end is None or spur_end < spur_born * 0.6),
    }

    # retrieval smoke check on a few diary lines (the fallback writes no diary)
    sample = [{"t": "2026-11-02T08:55", "text": "The keys jingled and then the door closed; the flat went quiet."},
              {"t": "2026-11-02T19:36", "text": "I went into the bedroom and heard 'no', so I waddled back to the hallway."},
              {"t": "2026-11-02T22:05", "text": "The TV came on and the doorbell rang right after."}]
    hits = retrieve.retrieve("主人拿起钥匙要出门", k=1, entries=sample)

    llm_summary = {"skipped": "--no-llm"} if a.no_llm else real_reflection(day1[0], day1[1], a.backend, a.model)

    print("\nfinal rules:")
    for r in sorted(final_rules, key=lambda r: -r["weight"]):
        print(f"  {r['weight']:.2f}  {r['kind']:9s} {r['trigger']} -> {r['outcome_or_effect']}  "
              f"(+{r['evidence']['confirm']} / -{r['evidence']['omit']})")
    print("\nretrieval: query '主人拿起钥匙要出门' ->", hits[0]["text"] if hits else None,
          f"[{retrieve.MODEL_NAME if retrieve._model() else 'hash'}]")
    print("\nfrontier-model reflection on day 1:")
    print(json.dumps(llm_summary, ensure_ascii=False, indent=2, default=str))
    if llm_summary.get("usage"):
        u = llm_summary["usage"]
        print(f"\ncost of that night: ${u['cost_usd']:.4f} ({u['input_tokens']} in + {u['cache_read_tokens']} cache read"
              f" + {u['cache_write_tokens']} cache write, {u['output_tokens']} out tokens, {u['seconds']} s, "
              f"{u['backend']}, {u['cost_basis']})")
    if fuzzy.usages:
        print(f"fuzzy matcher: {len(fuzzy.usages)} small-model calls, ${sum(x.cost_usd for x in fuzzy.usages):.4f}")
    print("\nacceptance:")
    for k, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {k}")
    print(f"\nplots: {OUT / 'weights_by_day.png'} and {OUT}/day1..{a.days}.png")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
