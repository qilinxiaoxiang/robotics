#!/usr/bin/env python3
"""Diagnostic: do GND / +3V3 vias land inside the filled inner planes? Run with KiCad's Python on the built board."""
import sys
from pathlib import Path

import pcbnew

board = pcbnew.LoadBoard(str(Path(__file__).resolve().parent / "build" / "board.kicad_pcb"))
for z in board.Zones():
    layer = z.GetLayer()
    poly = z.GetFilledPolysList(layer)
    print("zone", z.GetNetname(), board.GetLayerName(layer), "filled", z.IsFilled(), "outlines", poly.OutlineCount(),
          "area mm2", round(z.GetFilledArea() / 1e12, 1) if z.IsFilled() else None)
    for k in range(poly.OutlineCount()):
        bb = poly.Outline(k).BBox()
        print("  island", k, "x", round(pcbnew.ToMM(bb.GetLeft()), 2), "to", round(pcbnew.ToMM(bb.GetRight()), 2),
              "y", round(pcbnew.ToMM(bb.GetTop()), 2), "to", round(pcbnew.ToMM(bb.GetBottom()), 2))
    inside = total = 0
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetNetname() == z.GetNetname():
            total += 1
            inside += poly.Contains(t.GetPosition())
    print("  vias of this net:", total, "inside the fill:", inside)
vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
print("vias total", len(vias), "types", {v.GetViaType() for v in vias},
      "layers", {(board.GetLayerName(v.TopLayer()), board.GetLayerName(v.BottomLayer())) for v in vias})
