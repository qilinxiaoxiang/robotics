#!/usr/bin/env python3
"""Check ../HEAD-USB-BOARD.html against the head USB board's sources, reading the page itself, not the builder.

1. Every board position drawn in the wiring views: its net equals head-usb-board-20261111/sch/netlist.py (pin order) and
   the pad net in pcb/build/board.kicad_pcb, and its place equals that pad's place on the routed board (0.06 mm).
2. Every connector pin of the netlist is on the page, and each is used by exactly one wire or declared empty.
3. Every wire lands on the net its source pad needs (table SOURCE_NET below, written from the part pinouts, not from
   the builder), in the wiring views and in the written lead lists (data-pin / data-net attributes).
Run:  python3 check_head_usb_board.py     (exit 1 on any mismatch)
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BOARD = ROOT / 'head-usb-board-20261111'
PAGE = HERE.parent / 'HEAD-USB-BOARD.html'

# source pad -> net it must reach on the board
SOURCE_NET = {
    'micr.VDD': '+3V3', 'micr.GND': 'GND', 'micr.SCK': 'MIC_SCK', 'micr.WS': 'MIC_WS', 'micr.SD': 'MIC_SD_EARS',
    'micl.VDD': '+3V3', 'micl.GND': 'GND', 'micl.SCK': 'MIC_SCK', 'micl.WS': 'MIC_WS', 'micl.SD': 'MIC_SD_EARS',
    'micb.VDD': '+3V3', 'micb.GND': 'GND', 'micb.SCK': 'MIC_SCK', 'micb.WS': 'MIC_WS', 'micb.SD': 'MIC_SD_BACK',
    'xiao.3V3': '+3V3', 'xiao.GND': 'GND', 'xiao.D5': 'TOUCH_SCL', 'xiao.D4': 'TOUCH_SDA',   # XIAO D4 SDA, D5 SCL (touch_main.cpp)
    'spk.a': 'SPK_P', 'spk.b': 'SPK_N',
    # camera socket circuits (HANDOFF "camera socket pin order"): 1 shield, 2 GND, 3 D+, 4 D-, 5 5 V
    'cam.c1': 'GND', 'cam.c2': 'GND', 'cam.c3': 'CAM_DP', 'cam.c4': 'CAM_DM', 'cam.c5': 'VBUS',
    'a7zusb.u1': 'GND', 'a7zusb.u2': 'GND', 'a7zusb.u3': 'UP_DP', 'a7zusb.u4': 'UP_DM', 'a7zusb.u5': 'VBUS',
}
# the uplink cable's wire colours (CURRENT-STATE parts_a7z_extensions): red 5 V, white D-, green D+, black GND and shield
UP_COLOUR = {'VBUS': '#d7263d', 'UP_DM': '#ffffff', 'UP_DP': '#1f9d55', 'GND': '#1d1d1f'}
EMPTY_OK = {'J_BACK.5', 'J_TOUCH_3V3.2'}        # left empty on purpose


def netlist():
    spec = importlib.util.spec_from_file_location('hub_netlist_check', BOARD / 'sch' / 'netlist.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = {}
    for group in mod.GROUPS.values():
        for ref, kind, value, pins in group:
            if kind.startswith('CONN'):
                for key, net in pins.items():
                    out[f'{ref}.{int(key.split("_")[0])}'] = net
    return out


def pcb_pads():
    """ref.pad -> (x, y, net or None) from the routed board file."""
    text = (BOARD / 'pcb' / 'build' / 'board.kicad_pcb').read_text()
    out = {}
    for chunk in text.split('\n\t(footprint ')[1:]:
        ref = re.search(r'\(property "Reference" "([^"]+)"', chunk).group(1)
        if not ref.startswith('J_'):
            continue
        x0, y0, rot = (float(v or 0) for v in re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', chunk).groups())
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        for pad in chunk.split('\n\t\t(pad ')[1:]:
            num = re.match(r'"([^"]*)"', pad).group(1)
            lx, ly = (float(v) for v in re.search(r'\(at ([-\d.]+) ([-\d.]+)', pad).groups())
            net = re.search(r'\(net (?:\d+ )?"([^"]*)"\)', pad.split('\n\t\t)')[0])
            if num:
                out[f'{ref}.{num}'] = (x0 + lx * c + ly * s, y0 - lx * s + ly * c, net.group(1) if net else None)
    return out


def main() -> int:
    html = PAGE.read_text()
    data = json.loads(re.search(r'<script type="application/json" id="hub-data">(.*?)</script>', html, re.S).group(1).replace('<\\/', '</'))
    nl, pads = netlist(), pcb_pads()
    edge = (json.loads((BOARD / 'pcb' / 'build' / 'footprints.json').read_text())['outline_mm'][0] - 30.0) / 2
    board = {p['id']: p for p in data['modules']['board']['pins']}
    bad = []
    print(f'page: {PAGE.name}, {len(board)} board positions, {len(data["benches"])} wiring views')
    print('position          page net       netlist        routed board   place')
    for pid in sorted(board, key=lambda k: (k.split('.')[0], int(k.split('.')[1]))):
        p = board[pid]
        want = nl.get(pid)
        px, py, pnet = pads[pid]
        ok_net = p['net'] == want == pnet
        ok_pos = abs(p['x'] - edge - px) < 0.06 and abs(p['y'] - edge - py) < 0.06
        ok_role = (p['role'] == 'nc') == (want is None)
        print(f'{pid:17s} {str(p["net"]):14s} {str(want):14s} {str(pnet):14s} {"ok" if ok_pos else "MOVED"}{"" if ok_net and ok_role else "  MISMATCH"}')
        if not (ok_net and ok_pos and ok_role):
            bad.append(pid)
    missing = sorted(set(nl) - set(board))
    if missing:
        bad += missing
        print('netlist pins not on the page:', missing)

    used: dict[str, list] = {}
    n_wires = 0
    for b in data['benches']:
        for w in b['wires']:
            n_wires += 1
            ends = [w['from'], w['to']]
            pin = next(e for e in ends if e.startswith('board.'))[len('board.'):]
            src = next(e for e in ends if not e.startswith('board.'))
            used.setdefault(pin, []).append(w['id'])
            net = board[pin]['net']
            ok = SOURCE_NET.get(src) == net
            if src.startswith('a7zusb.'):
                ok = ok and w['color'] == UP_COLOUR[net] and pin.startswith('J_UP.')
            if not ok or f'{w["ref"]}.{w["pin"]}' != pin or w['net'] != net:
                bad.append(w['id'])
                print(f'WIRE {w["id"]}: {src} -> {pin} ({net}) is wrong')
    for pid in board:
        k = len(used.get(pid, []))
        if (pid in EMPTY_OK and k != 0) or (pid not in EMPTY_OK and k != 1):
            bad.append(pid)
            print(f'{pid}: used by {k} wires')
    print(f'wires: {n_wires} in the views, every one on the net its source needs; '
          f'{len(board) - len(EMPTY_OK)} positions wired once, empty: {", ".join(sorted(EMPTY_OK))}')

    rows = re.findall(r'<li data-pin="([^"]+)" data-net="([^"]*)"( data-empty="1")?', html)
    listed = {}
    for pid, net, empty in rows:
        listed[pid] = listed.get(pid, 0) + 1
        if (net or None) != nl.get(pid) or bool(empty) != (pid in EMPTY_OK):
            bad.append('list ' + pid)
            print(f'LIST {pid}: says {net!r}, netlist {nl.get(pid)!r}')
    if set(listed) != set(board) or any(v != 1 for v in listed.values()):
        bad.append('lists')
        print('written lists do not cover every position once:', sorted(set(board) ^ set(listed)), {k: v for k, v in listed.items() if v != 1})
    print(f'written lead lists: {len(rows)} entries, each position once, nets equal the netlist')
    print('FAIL: ' + ', '.join(bad) if bad else 'PASS')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
