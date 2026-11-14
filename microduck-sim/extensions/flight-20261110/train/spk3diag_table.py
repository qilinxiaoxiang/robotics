"""One line per runtime pickup record (train/eval/pk*_ball.json): held at the hand-back / still held at the end /
pinched / falls (direction counts) / median fall time / guard stops / leg saturation, as pickup_ckpt.sh counts them.
  python3 train/spk3diag_table.py train/eval/pkd3_*.json
"""
import json
import statistics
import sys
from collections import Counter

for f in sys.argv[1:]:
    try:
        d = json.load(open(f))
    except Exception as e:  # noqa: BLE001
        print(f, "missing", e)
        continue
    eps = d["episodes"]
    sp = [e["probe"].get("seepick") or {} for e in eps]
    ev = [s.get("events") or {} for s in sp]
    ft = [e["fell_at"] for e in eps if e["fell_at"] is not None]
    gs = [((s.get("guard") or {}).get("stop_at")) for s in sp]
    print(f.split("/")[-1], "held", sum(bool((s.get("at_handback") or {}).get("held")) for s in sp),
          "at_end", sum(bool((s.get("at_end") or {}).get("held")) for s in sp), "of", len(eps),
          "pinched", sum(e.get("first_pinched_t") is not None for e in ev),
          "falls", len(ft), dict(Counter(e["fall_dir"] for e in eps if e["fell_at"] is not None)),
          "fall_t_med", round(statistics.median(ft), 2) if ft else None,
          "guard_stops", sum(g is not None for g in gs),
          "sat_frac_med", round(statistics.median(e["leg_force_sat_frac"] or 0 for e in eps), 3))
