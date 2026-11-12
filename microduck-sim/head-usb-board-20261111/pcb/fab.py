#!/usr/bin/env python3
"""Write JLCPCB's assembly files from build/pos.csv (kicad-cli pcb export pos) and lcsc_parts.json.

  build/fab/bom.csv   Comment, Designator, Footprint, LCSC Part #   (one row per LCSC number)
  build/fab/cpl.csv   Designator, Mid X, Mid Y, Layer, Rotation     (every assembled part)
Parts with "dnf" or no LCSC number (test pads) are left out of both. Fails if a placed footprint has no row in
lcsc_parts.json or a row names a ref that is not on the board. KiCad's positions and angles are corrected
per footprint by jlc_placement.json (JLCPCB places the body centre and uses its own zero angles).
Run: python3 fab.py   (after run.sh fab)
"""
import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "build" / "fab"


def main():
    parts = json.loads((HERE / "lcsc_parts.json").read_text())
    fix = json.loads((HERE / "jlc_placement.json").read_text())["footprints"]
    row_of = {}
    for p in parts:
        for r in p["refs"]:
            if r in row_of:
                sys.exit(f"{r} is in two rows of lcsc_parts.json")
            row_of[r] = p
    pos = list(csv.DictReader((HERE / "build" / "pos.csv").open()))
    placed = {r["Ref"]: r for r in pos}
    missing = sorted(set(placed) - set(row_of))
    # bare test pads are not in the placement export and have no part
    ghost = sorted(r for r in set(row_of) - set(placed) if row_of[r].get("lcsc") and not row_of[r].get("dnf"))
    if missing or ghost:
        sys.exit(f"parts table and board disagree: on the board without a row {missing}; rows not on the board {ghost}")
    OUT.mkdir(parents=True, exist_ok=True)
    used = [p for p in parts if p.get("lcsc") and not p.get("dnf")]
    with (OUT / "bom.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for p in used:
            w.writerow([p.get("mpn") or p["value"], ",".join(sorted(p["refs"])), p["footprint"], p["lcsc"]])
    n = 0
    with (OUT / "cpl.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for p in used:
            for r in sorted(p["refs"]):
                q = placed[r]
                c = fix.get(q["Package"], {})
                rot = float(q["Rot"])
                dx, dy = c.get("offset_mm", (0.0, 0.0))        # footprint frame, y down; KiCad turns counter-clockwise
                a = math.radians(rot)
                x = float(q["PosX"]) + dx * math.cos(a) + dy * math.sin(a)
                y = float(q["PosY"]) - (-dx * math.sin(a) + dy * math.cos(a))    # the export's y points up
                w.writerow([r, f"{x:.4f}mm", f"{y:.4f}mm",
                            "Top" if q["Side"].lower().startswith(("f", "t")) else "Bottom",
                            f"{(rot + c.get('rot_deg', 0)) % 360:.0f}"])
                n += 1
    skipped = sorted(r for p in parts if p not in used for r in p["refs"])
    print(f"bom.csv: {len(used)} lines; cpl.csv: {n} parts; not assembled: {' '.join(skipped)}")


if __name__ == "__main__":
    main()
