#!/usr/bin/env python3
"""Write build/footprints.json: every footprint's reference, footprint name and front-courtyard box in board mm.

Run with KiCad's Python on the built board; fit_check.py reads the result (it runs under a plain numpy Python).
"""
import json
from pathlib import Path

import pcbnew

BUILD = Path(__file__).resolve().parent / "build"
board = pcbnew.LoadBoard(str(BUILD / "board.kicad_pcb"))
edge = board.GetBoardEdgesBoundingBox()
ox, oy = pcbnew.ToMM(edge.GetLeft()), pcbnew.ToMM(edge.GetTop())
out = {"outline_mm": [round(pcbnew.ToMM(edge.GetWidth()), 2), round(pcbnew.ToMM(edge.GetHeight()), 2)], "parts": []}
for fp in board.GetFootprints():
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if bb.GetWidth() == 0:
        bb = fp.GetBoundingBox(False)
    out["parts"].append({
        "ref": fp.GetReference(),
        "footprint": str(fp.GetFPID().GetLibItemName()),
        "box": [round(pcbnew.ToMM(bb.GetLeft()) - ox, 2), round(pcbnew.ToMM(bb.GetTop()) - oy, 2),
                round(pcbnew.ToMM(bb.GetRight()) - ox, 2), round(pcbnew.ToMM(bb.GetBottom()) - oy, 2)],
    })
(BUILD / "footprints.json").write_text(json.dumps(out, indent=1) + "\n")
print(len(out["parts"]), "footprints, outline", out["outline_mm"])
