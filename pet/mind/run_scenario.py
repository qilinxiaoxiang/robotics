"""A scripted day in the simulated home, at accelerated time.

    pet/.venv/bin/python -m pet.mind.run_scenario --body duck                  # model if reachable, else fallback
    pet/.venv/bin/python -m pet.mind.run_scenario --body arm --backend fallback

Awake segments run second by second through the full mind; the hours between them pass asleep (drives only, no
model calls). Writes pet/mind/out/<body>-<backend>/: behaviour.log (the day as a reader follows it), intentions.jsonl,
calls.jsonl (tokens, latency, cost per model call), drives.png, summary.json (rigidity numbers and cost).
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

from .backends import BackendError, CallLog, make_backend
from .body import BodyCard
from .metrics import rigidity
from .mind import Mind
from .state import EXAMPLES, SharedState, load_body_card
from .world import World, clock

OUT = Path(__file__).resolve().parent / "out"
DAY = "2026-10-27"


def hm(s: str) -> float:
    h, m = s.split(":")
    return int(h) * 3600 + int(m) * 60


# (segment start, end, [(time, event)]). Directions are radians, positive = to the pet's left.
SCENARIO = [
    ("07:30", "07:45", [("07:30", {"kind": "lights", "level": 1.0}),
                        ("07:32", {"kind": "owner_moves", "room": "kitchen"}),
                        ("07:40", {"kind": "owner_moves", "room": "living room"}),
                        ("07:42", {"kind": "touch", "where": "head"})]),
    ("08:10", "08:30", [("08:12", {"kind": "owner_moves", "room": "hallway"}),
                        ("08:18", {"kind": "sound", "label": "keys_jingle", "direction": 1.2}),
                        ("08:20", {"kind": "owner_leaves", "direction": 1.2})]),
    ("12:55", "13:10", [("13:00", {"kind": "sound", "label": "doorbell", "direction": 1.2}),
                        ("13:01", {"kind": "stranger_arrives", "room": "living room", "direction": 1.0}),
                        ("13:06", {"kind": "stranger_leaves", "direction": 1.2})]),
    ("18:25", "18:45", [("18:29", {"kind": "sound", "label": "keys_jingle", "direction": 1.2}),
                        ("18:30", {"kind": "owner_returns", "room": "hallway", "direction": 1.2}),
                        ("18:32", {"kind": "owner_moves", "room": "living room"}),
                        ("18:34", {"kind": "touch", "where": "head"}),
                        ("18:40", {"kind": "owner_moves", "room": "kitchen"})]),
    ("21:15", "21:35", [("21:16", {"kind": "owner_moves", "room": "living room"}),
                        ("21:22", {"kind": "lights", "level": 0.3}),
                        ("21:30", {"kind": "owner_moves", "room": "bedroom"}),
                        ("21:32", {"kind": "charge_start"})]),
]
SCENE_NOTES = {"07:30": "MORNING: owner wakes up, makes breakfast, sits down",
               "08:10": "LEAVING: owner gets ready, keys jingle, owner leaves",
               "12:55": "ALONE: the doorbell rings, a stranger (the cleaner) comes in and goes",
               "18:25": "RETURN: keys at the door, owner comes home",
               "21:15": "EVENING: sofa, lights dim, owner goes to bed"}


def pick_backend(name: str):
    if name != "auto":
        return make_backend(name)
    for cand in ("anthropic", "claude-cli"):
        try:
            b = make_backend(cand)
            if cand == "anthropic" and not _anthropic_has_key():
                continue
            return b
        except (BackendError, ImportError, ValueError):
            continue
    return None


def _anthropic_has_key() -> bool:
    import os
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or Path.home().joinpath(".config/anthropic").exists())


def run_day(body_name: str, backend, seed=7, state_dir=EXAMPLES, out_dir: Path | None = None, verbose=True):
    rng = random.Random(seed)
    body = BodyCard(load_body_card(body_name))
    shared = SharedState(state_dir)
    world = World(body, rng, hm(SCENARIO[0][0]))
    tag = f"{body.name}-{backend.name if backend else 'fallback'}"
    out_dir = out_dir or OUT / tag
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    calls = CallLog(out_dir / "calls.jsonl")
    mind = Mind(body, shared, world, backend=backend, rng=rng, call_log=calls, today=DAY)
    printed = 0

    def flush():
        nonlocal printed
        if verbose:
            for line in mind.lines[printed:]:
                print(line, flush=True)
        printed = len(mind.lines)

    mind.log(f"=== {body.name} with {backend.name if backend else 'no model (fallback)'}; "
             f"senses: {', '.join(sorted(body.sensor_kinds))}; "
             f"{'walks' if body.can_locomote else 'fixed in the ' + str(body.fixed_location)} ===")
    for i, (start, end, events) in enumerate(SCENARIO):
        t0, t1 = hm(start), hm(end)
        if world.t < t0:
            mind.sleep(t0)
        mind.log(f"--- {SCENE_NOTES[start]} ---")
        evq = sorted((hm(t), ev) for t, ev in events)
        last_snap = world.t
        while world.t < t1:
            while evq and evq[0][0] <= world.t:
                _, ev = evq.pop(0)
                mind.perceive(world.apply(ev))
            mind.tick(1.0)
            if world.t - last_snap >= 300:
                s = mind.drives.snapshot()
                mind.log("  drives " + " ".join(f"{k[:5]} {s[k]:.2f}" for k in
                                                ("bored", "miss_owner", "tired", "curious", "battery"))
                         + f" | mood v {s['valence']:+.2f} a {s['arousal']:.2f} | in {world.pet_room}, {world.posture}")
                last_snap = world.t
            flush()
    mind.log("--- night: asleep ---")
    flush()

    (out_dir / "behaviour.log").write_text("\n".join(mind.lines) + "\n")
    with (out_dir / "intentions.jsonl").open("w") as f:
        for h in mind.history:
            f.write(json.dumps(h) + "\n")
    summary = {"body": body.name, "backend": backend.name if backend else "fallback", "seed": seed,
               "awake_minutes": sum(hm(e) - hm(s) for s, e, _ in SCENARIO) / 60,
               "rigidity": rigidity(mind.history, body), "calls": calls.summary()}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    plot(mind, out_dir / "drives.png", f"{body.name}, {summary['backend']}")
    return summary, mind


def plot(mind: Mind, path: Path, title: str):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    tr = mind.trace
    hours = [r["t"] / 3600 for r in tr]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True)
    for k, c in (("bored", "#1f77b4"), ("miss_owner", "#d62728"), ("tired", "#7f7f7f"), ("curious", "#2ca02c"),
                 ("battery", "#ff7f0e")):
        a1.plot(hours, [r[k] for r in tr], label=k, color=c, lw=1.2)
    a1.set_ylabel("drive (0-1)")
    a1.set_ylim(-0.02, 1.02)
    a1.legend(loc="upper left", ncol=5, fontsize=8)
    a2.plot(hours, [r["valence"] for r in tr], label="valence", color="#9467bd")
    a2.plot(hours, [r["arousal"] for r in tr], label="arousal", color="#8c564b")
    a2.axhline(0, color="#bbbbbb", lw=0.6)
    a2.set_ylabel("mood")
    a2.set_ylim(-1, 1)
    a2.legend(loc="upper left", fontsize=8)
    for i, (start, end, _) in enumerate(SCENARIO):
        for a in (a1, a2):
            a.axvspan(hm(start) / 3600, hm(end) / 3600, color="#f2f2f2", zorder=0)
        a1.text(hm(start) / 3600, 1.03 + 0.06 * (i % 2), SCENE_NOTES[start].split(":")[0], fontsize=7,
                transform=a1.get_xaxis_transform())
    a2.set_xlabel("hour of day (shaded = awake segments; between them the pet sleeps)")
    fig.suptitle(f"Drives and mood over the scripted day: {title}", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--body", default="duck", help="duck | arm | live | path to a body card")
    ap.add_argument("--backend", default="auto", help="auto | anthropic | claude-cli | ollama | fallback")
    ap.add_argument("--state-dir", default=str(EXAMPLES), help="directory with rules/plan/diary/personality/skills")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    backend = pick_backend(a.backend)
    summary, _ = run_day(a.body, backend, a.seed, a.state_dir, verbose=not a.quiet)
    r, c = summary["rigidity"], summary["calls"]
    print(f"\n{summary['body']} / {summary['backend']}: {r['intentions']} intentions, "
          f"{r['distinct_action_sequences']} distinct action sequences, {r['distinct_intention_texts']} distinct texts, "
          f"repeat-of-previous {r['repeat_of_previous_rate']:.0%}, longest identical run {r['longest_identical_run']}, "
          f"entropy {r['sequence_entropy_bits']} bits; sources {r['sources']}")
    if c["calls"]:
        print(f"model calls {c['calls']} ({c['ok']} valid), tokens in {c['input_tokens']} out {c['output_tokens']}, "
              f"API-equivalent ${c['api_cost_usd']:.4f}, latency p50 {c['latency_p50_s']}s p90 {c['latency_p90_s']}s")


if __name__ == "__main__":
    main()
