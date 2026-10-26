"""Rigidity and cost across the runs in pet/mind/out/ (each run_scenario call leaves a summary.json there).

    pet/.venv/bin/python -m pet.mind.compare

Cost per day extrapolates the measured calls to an awake day (AWAKE_HOURS, intentions at the measured rate) at
Claude Haiku 5.5 API list price, without prompt caching.
"""
from __future__ import annotations

import json
from pathlib import Path

from .backends import api_cost_usd
from .body import BodyCard
from .metrics import rigidity
from .state import load_body_card

OUT = Path(__file__).resolve().parent / "out"
AWAKE_HOURS = 16


def load_runs() -> list[dict]:
    runs = []
    for p in sorted(OUT.glob("*/summary.json")):
        s = json.loads(p.read_text())
        calls = [json.loads(line) for line in (p.parent / "calls.jsonl").read_text().splitlines() if line.strip()]
        s["dir"] = p.parent.name
        history = [json.loads(line) for line in (p.parent / "intentions.jsonl").read_text().splitlines() if line]
        body = BodyCard(load_body_card({"microduck": "duck", "omx_f_arm": "arm"}.get(s["body"], s["body"])))
        s["rigidity"] = rigidity(history, body)
        s["call_records"] = calls
        runs.append(s)
    return runs


def cost_per_day(s: dict) -> dict | None:
    calls = [c for c in s["call_records"] if "input_tokens" in c]
    if not calls:
        return None
    intentions_per_hour = s["rigidity"]["intentions"] / (s["awake_minutes"] / 60)
    calls_per_intention = len(s["call_records"]) / max(1, s["rigidity"]["sources"].get("llm", 0)
                                                       + s["rigidity"]["sources"].get("fallback", 0))
    mean_in = sum(c["input_tokens"] for c in calls) / len(calls)
    mean_out = sum(c["output_tokens"] for c in calls) / len(calls)
    calls_day = intentions_per_hour * calls_per_intention * AWAKE_HOURS
    return {"intentions_per_awake_hour": round(intentions_per_hour, 1), "calls_per_day": round(calls_day),
            "mean_input_tokens": round(mean_in), "mean_output_tokens": round(mean_out),
            "api_usd_per_call": round(api_cost_usd(mean_in, mean_out), 6),
            "api_usd_per_day": round(calls_day * api_cost_usd(mean_in, mean_out), 3),
            "measured_api_usd_this_run": round(sum(c.get("api_cost_usd", 0) for c in calls), 4)}


def main():
    rows = []
    for s in load_runs():
        r = s["rigidity"]
        row = {"run": s["dir"], "intentions": r["intentions"],
               "distinct_action_sequences": r["distinct_action_sequences"],
               "distinct_texts": r["distinct_intention_texts"], "distinct_with_params": r["distinct_with_params"],
               "repeat_of_previous_rate": r["repeat_of_previous_rate"],
               "longest_identical_run": r["longest_identical_run"], "entropy_bits": r["sequence_entropy_bits"],
               "primitives_used": r["primitives_used"],
               "sources": r["sources"], "most_common": r["most_common"],
               "context": {k: v for k, v in r.items() if "share" in k or "posture" in k or "owner" in k},
               "calls": s["calls"], "cost": cost_per_day(s)}
        rows.append(row)
        print(f"{row['run']}: {row['intentions']} intentions, {row['distinct_action_sequences']} distinct sequences, "
              f"{row['distinct_texts']} distinct texts, repeat {row['repeat_of_previous_rate']:.0%}, "
              f"longest run {row['longest_identical_run']}, entropy {row['entropy_bits']} bits")
        print(f"    used: {', '.join(row['primitives_used'])}")
        print(f"    context: {row['context']}")
        if row["cost"]:
            c = row["cost"]
            print(f"    {c['calls_per_day']} calls/awake day, {c['mean_input_tokens']} in + "
                  f"{c['mean_output_tokens']} out tokens/call, ${c['api_usd_per_day']}/day at API price; latency p50 {s['calls']['latency_p50_s']} s "
                  f"p90 {s['calls']['latency_p90_s']} s; valid {s['calls']['ok']}/{s['calls']['calls']}")
    (OUT / "comparison.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
