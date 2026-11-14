"""Held / still held 3 s later / falls of the runtime pickup test for staged checkpoints, per load and loop delay.

python3 pickup_table.py <ckpt>...   reads eval/pk_<ckpt>_<load>_ball.json (default delay, about 44 ms) and
eval/pk_<ckpt>sd0_<load>_ball.json (--sensor-delay 0, about 24 ms). Missing files are skipped.
"""
import json
import os
import sys

LOADS = ["none", "load025", "load050", "load075", "nobatt", "load100"]


def row(path):
    d = json.load(open(path))
    eps = [v for v in d.values() if isinstance(v, list) and v and isinstance(v[0], dict)][0]
    sp = [e["probe"].get("seepick") or {} for e in eps]
    held = sum(bool((s.get("at_handback") or {}).get("held")) for s in sp)
    end = sum(bool((s.get("at_end") or {}).get("held")) for s in sp)
    falls = sum(e["fell_at"] is not None for e in eps)
    return f"{held:2d} ({end:2d}) / {falls:2d} of {len(eps)}"


here = os.path.dirname(os.path.abspath(__file__))
for ck in sys.argv[1:]:
    for tag, name in (("44 ms", ck), ("24 ms", ck + "sd0"), ("44 ms held-out seeds", ck + "h"),
                      ("24 ms held-out seeds", ck + "sd0h")):
        cells = []
        for ld in LOADS:
            p = os.path.join(here, "eval", f"pk_{name}_{ld}_ball.json")
            if os.path.exists(p):
                cells.append(f"{ld} {row(p)}")
        if cells:
            print(f"{ck} {tag}: " + "; ".join(cells))
