"""Cut lengths of the head wires (amplifier, XIAO, microphones) for the V2 roof saddle (D-028: header at the front edge).

Each wire = its route inside the head up to the exit (guide-data.json cable paths, plus the left-board harness for the
microphone SD and GND, plus the back-board harness for the back SD) + the exit-to-front-wall span from head_sweep_v2.py
+ a tail from the bundle's crossing point on the front wall top (z 64.6) along the wall to the wire's own pin row, back over
the open header strip to the Dupont housing and down to the pin top (a7z-saddle/build/pins.json) + 15 mm for the bends at
both ends, rounded up to 5 mm. No head wire goes under the saddle (D-028 contract). Three spans are given: HOME (head
straight), the trained head range and the full joint range (the open-beak bend of D-027 reaches far forward).
Writes head-wire-lengths.json.   python3 head_wire_lengths.py"""
import json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
MS = HERE.parents[1]
GUIDE = json.loads((MS / 'guide' / 'data' / 'guide-data.json').read_text())
PINS = json.loads((MS / 'guide' / 'print' / 'a7z-saddle' / 'build' / 'pins.json').read_text())['pinTop']
SW = json.loads((HERE / 'head-sweep-v2.json').read_text())
EXIT, WALL = SW['exit'], SW['splice']
CAB = {c['id']: c for c in GUIDE['cables']}
WIRES = {  # cable id: (pin, harness inside the head before the gather point)
    'amp-vin': (4, None), 'amp-bclk': (12, None), 'amp-lrc': (35, None), 'amp-gnd': (39, None), 'amp-din': (40, None),
    'touch-pin17': (17, None), 'touch-pin25': (25, None), 'touch-pin29': (29, None), 'touch-pin31': (31, None),
    'mic-gnd': (34, 'mic-l'), 'mic-sd': (38, 'mic-l'), 'mic-sd3': (10, 'mic-b'),
}


def length(p):
    return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))


def in_head(cid, harness):
    p = CAB[cid]['path']
    k = min(range(len(p)), key=lambda i: math.dist(p[i], EXIT))
    if math.dist(p[k], EXIT) > 1.5:
        raise SystemExit(f'{cid} does not pass the head exit {EXIT}')
    return length(p[:k + 1]) + (length(CAB[harness]['path']) if harness else 0.0)


def tail(pin):
    x, y, z = PINS[str(pin)]
    return length([WALL, [WALL[0], y, WALL[2]], [x, y, 65.5], [x, y, z]])


def r5(v):
    return 5 * math.ceil(v / 5)


span = {'home': SW['home']['routedMm'], 'trained': SW['trained']['maxRoutedMm'], 'full': SW['full']['maxRoutedMm']}
out = {'source': 'bringup/a7z/head_wire_lengths.py', 'exit': EXIT, 'frontWallTop': WALL, 'spanMm': span, 'wires': {}}
for cid, (pin, harness) in WIRES.items():
    ih, t = in_head(cid, harness), tail(pin)
    out['wires'][cid] = {'pin': pin, 'inHeadMm': round(ih), 'tailMm': round(t),
                         'outsideMm': {k: round(v + t) for k, v in span.items()},
                         'cutMm': {k: r5(ih + v + t + 15) for k, v in span.items()}}
(HERE / 'head-wire-lengths.json').write_text(json.dumps(out, indent=1) + '\n')
for cid, w in out['wires'].items():
    print(f"{cid:12s} pin {w['pin']:>2}  outside {w['outsideMm']}  cut {w['cutMm']}")
