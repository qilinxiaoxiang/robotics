#!/usr/bin/env python3
"""Read build/drc.json (kicad-cli pcb drc) and say whether the board passes.

Waived: courtyard overlaps between two J_* connectors only (the 2.54 mm headers stand on one 2.54 mm grid, see
placement.py). Everything else, and every unconnected item, fails.
Run: python3 check_drc.py [--placement]   (--placement ignores unconnected items, for the stage before routing)
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

d = json.loads((Path(__file__).resolve().parent / "build" / "drc.json").read_text())
bad, waived = [], 0
for v in d.get("violations", []):
    refs = [re.sub(r"^Footprint ", "", i["description"]) for i in v["items"]]
    if v["type"] == "courtyards_overlap" and all(r.startswith("J_") for r in refs):
        waived += 1
        continue
    bad.append((v["type"], refs, v.get("description", "")))
unconnected = d.get("unconnected_items", [])
print(f"violations {len(bad)} (waived connector courtyards {waived}), unconnected {len(unconnected)}")
print(Counter(b[0] for b in bad).most_common())
for t, refs, desc in bad[:40]:
    print(" ", t, [r[:60] for r in refs])
for u in unconnected[:25]:
    print("  open:", [i["description"][:60] for i in u["items"]])
ok = not bad and (not unconnected or "--placement" in sys.argv)
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
