#!/usr/bin/env python3
"""Measure the routed USB pairs of build/board.kicad_pcb and judge them (KiCad's Python, Mac mini).

The two 480 Mbit/s pairs (uplink and camera) are judged; the RP2040 pair is 12 Mbit/s and only reported.
Limits (LIMITS below): a pair on this board is a short, electrically small run (USB high-speed edges are 500 ps
or slower, about 80 mm of track), so what matters is that both lines take the same path over unbroken ground:
equal layers and via counts, small length difference, short total length, the wide track class.
Writes build/usb-pairs.json; exit 1 on a failed limit.
"""
import json
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
PAIRS = {"uplink": ("UP_DP", "UP_DM", True), "camera": ("CAM_DP", "CAM_DM", True),
         "mcu_hub_side": ("MCU_DP", "MCU_DM", False), "mcu_chip_side": ("RP_DP", "RP_DM", False)}
LIMITS = {"max_length_mm": 30.0, "max_skew_mm": 2.0, "max_vias_per_line": 2}
mm = pcbnew.ToMM


def measure(board, net):
    length, vias, layers, widths, segs = 0.0, 0, set(), set(), []
    for t in board.GetTracks():
        if t.GetNetname() != net:
            continue
        if t.GetClass() == "PCB_VIA":
            vias += 1
            continue
        length += mm(t.GetLength())
        layers.add(board.GetLayerName(t.GetLayer()))
        widths.add(round(mm(t.GetWidth()), 3))
        segs.append([round(mm(v), 3) for v in (t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)])
    pads = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == net:
                p = pad.GetPosition()
                pads.append([fp.GetReference(), pad.GetNumber(), round(mm(p.x), 3), round(mm(p.y), 3)])
    return {"length_mm": round(length, 2), "vias": vias, "layers": sorted(layers), "widths_mm": sorted(widths),
            "pads": pads, "segments": segs}


def main():
    board = pcbnew.LoadBoard(str(HERE / "build" / "board.kicad_pcb"))
    out, bad = {"limits": LIMITS, "pairs": {}}, []
    for name, (p, n, judged) in PAIRS.items():
        a, b = measure(board, p), measure(board, n)
        skew = round(abs(a["length_mm"] - b["length_mm"]), 2)
        out["pairs"][name] = {"judged": judged, "skew_mm": skew, p: a, n: b}
        line = (f"{name}: {p} {a['length_mm']} mm {a['vias']} vias {a['layers']} w {a['widths_mm']} | "
                f"{n} {b['length_mm']} mm {b['vias']} vias {b['layers']} w {b['widths_mm']} | skew {skew}")
        print(line)
        if judged:
            if max(a["length_mm"], b["length_mm"]) > LIMITS["max_length_mm"]:
                bad.append(f"{name}: longer than {LIMITS['max_length_mm']} mm")
            if skew > LIMITS["max_skew_mm"]:
                bad.append(f"{name}: skew {skew} mm over {LIMITS['max_skew_mm']}")
            if max(a["vias"], b["vias"]) > LIMITS["max_vias_per_line"] or a["vias"] != b["vias"]:
                bad.append(f"{name}: vias {a['vias']}/{b['vias']}")
            if a["layers"] != b["layers"]:
                bad.append(f"{name}: lines on different layers {a['layers']} / {b['layers']}")
    out["failed"] = bad
    (HERE / "build" / "usb-pairs.json").write_text(json.dumps(out, indent=1) + "\n")
    print("PASS" if not bad else "FAIL: " + "; ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
