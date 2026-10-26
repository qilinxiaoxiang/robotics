"""Cut lengths of the head wires (amplifier, XIAO, microphones) for the V2 roof saddle (D-028: header at the front edge), in
two pieces each: component -> gather point (the joints at the cap's left rear corner over the exit) and gather point -> A7Z pin.

component -> gather point: the guide-data.json cable path from the solder pad to the gather point (microphones: the left- and
  back-board harness paths; the right board ends on the left board's pads).
gather point -> pin: gather point down to the head exit (34 mm) + exit to the front wall top in a straight line (D-028
  contract: head wires drop over the front wall, never under the saddle) + along the wall top to the wire's own pin column,
  over the open strip and down into the housing to the pin top (a7z-saddle/build/pins.json).
The exit-to-wall span is the straight distance from head-sweep-v2.json: 37 mm at HOME; the recommended cut takes the larger of its maximum
over the trained head command range (walk_brain HEAD_RANGE) and over the pickup bend (groundpick-head-traj.json, D-027). Every piece gets 10 mm for the two ends and is rounded up to 5 mm;
the left microphone piece also gets the guide's 25 mm so the cap still opens like a lid. Spliced wires (12, 35, 17) are cut as
two pieces; the others are one wire of the summed length (one 10 mm allowance). Writes head-wire-lengths.json.
python3 head_wire_lengths.py"""
import json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
MS = HERE.parents[1]
GUIDE = json.loads((MS / 'guide' / 'data' / 'guide-data.json').read_text())
PINS = json.loads((MS / 'guide' / 'print' / 'a7z-saddle' / 'build' / 'pins.json').read_text())['pinTop']
SW = json.loads((HERE / 'head-sweep-v2.json').read_text())
EXIT, WALL = SW['exit'], SW['splice']
GP = [11.5, 19.5, 132.0]                       # gather point, left rear corner of the cap over the exit (guide-data paths)
CAB = {c['id']: c for c in GUIDE['cables']}
ENDS, CAP_OPEN = 10, 25
WIRES = {  # cable id: (pin, path from the component to the gather point, spliced at the gather point)
    'amp-vin': (4, 'amp-vin', False), 'amp-bclk': (12, 'amp-bclk', True), 'amp-lrc': (35, 'amp-lrc', True),
    'amp-gnd': (39, 'amp-gnd', False), 'amp-din': (40, 'amp-din', False),
    'touch-pin17': (17, 'touch-pin17', True), 'touch-pin25': (25, 'touch-pin25', False),
    'touch-pin29': (29, 'touch-pin29', False), 'touch-pin31': (31, 'touch-pin31', False),
    'mic-gnd': (34, 'mic-l', False), 'mic-sd': (38, 'mic-l', False), 'mic-sd3': (10, 'mic-b', False),
}
SPLICE_IN = {'mic-l': 'mic-l', 'mic-b': 'mic-b'}   # microphone SCK/WS/VDD pieces into the 12/35/17 joints


def length(p):
    return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))


def to_gather(cid):
    p = CAB[cid]['path']
    k = min(range(len(p)), key=lambda i: math.dist(p[i], GP))
    if math.dist(p[k], GP) > 1.5:
        raise SystemExit(f'{cid} does not pass the gather point {GP}')
    return length(p[:k + 1])


def gather_to_pin(pin, span):
    x, y, z = PINS[str(pin)]
    down = length([GP, [10.0, 18.5, 124.0], [10.0, 18.5, 110.0], EXIT])
    return down + span + length([WALL, [WALL[0], y, WALL[2]], [x, y, 65.5], [x, y, z]])


def r5(v):
    return 5 * math.ceil(v / 5)


span = {'home': SW['home']['straightMm'], 'trained': SW['trained']['maxStraightMm'], 'full': SW['full']['maxStraightMm'],
        'pickup': max(SW['trained']['maxStraightMm'], SW['pickup']['maxStraightMm'])}   # recommended: walking head range and the pickup bend
out = {'source': 'bringup/a7z/head_wire_lengths.py', 'gatherPoint': GP, 'exit': EXIT, 'frontWallTop': WALL, 'spanMm': span,
       'endsMm': ENDS, 'capOpenMm': CAP_OPEN, 'wires': {}, 'micPieces': {}}
for cid, (pin, src, spliced) in WIRES.items():
    a = to_gather(src) + (CAP_OPEN if src in ('mic-l', 'mic-b') else 0)
    b = {k: gather_to_pin(pin, v) for k, v in span.items()}
    w = {'pin': pin, 'spliced': spliced, 'toGatherMm': round(a), 'gatherToPinMm': {k: round(v) for k, v in b.items()},
         'outsideMm': {k: round(v - 34) for k, v in b.items()}}
    if spliced:
        w['cut'] = {'toGather': r5(a + ENDS), 'gatherToPin': {k: r5(v + ENDS) for k, v in b.items()}}
    else:
        w['cut'] = {'whole': {k: r5(a + v + ENDS) for k, v in b.items()}}
    out['wires'][cid] = w
for mid in ('mic-l', 'mic-b'):
    out['micPieces'][mid] = r5(to_gather(mid) + CAP_OPEN + ENDS)
out['micPieces']['mic-r'] = r5(length(CAB['mic-r']['path']) + ENDS)
(HERE / 'head-wire-lengths.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
for cid, w in out['wires'].items():
    print(f"{cid:12s} pin {w['pin']:>2}  to gather {w['toGatherMm']:>3}  gather->pin {w['gatherToPinMm']}  cut {w['cut']}")
print('mic pieces', out['micPieces'])
