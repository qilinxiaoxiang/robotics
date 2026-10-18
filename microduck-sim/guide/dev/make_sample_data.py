#!/usr/bin/env python3
"""Development fixture for the guide viewer. NOT a build instruction.

Converts the current full-build mesh export into guide schema v1 with two chapters (left leg, torso), eight steps,
approach vectors, one reference photo and two invented cables between the motor10 and motor9 bounds. The step text,
cable routes, statuses and quantities are placeholders that exercise the viewer; the meshes are real.

    python3 guide/dev/make_sample_data.py [--src full-build-data-current.json] [--out guide/dev/sample-data.json]
"""
from __future__ import annotations

import argparse
import base64
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent.parent
LEG_GUIDE = SIM / 'build-pack-20260913' / 'redesign-20260913' / 'leg-guide-20261006'
DEFAULT_SRC = LEG_GUIDE / 'full-build-data-current.json'
PHOTO = LEG_GUIDE / 'washer-6-preview.png'
FOV_DEG = 32.0

STATUS_BY_KIND = {'print': 'printed', 'motor': 'owned', 'fastener': 'purchased', 'electronics': 'purchased'}
STATUS_OVERRIDE = {'ankle': 'reprint', 'passive': 'new-print', 'ring10_torso': 'assembled'}
MODULES = ('left-leg', 'right-leg', 'torso', 'power', 'imu')


def center(b):
    return [(b[0][a] + b[1][a]) / 2 for a in range(3)]


def union(bounds):
    lo = [min(b[0][a] for b in bounds) for a in range(3)]
    hi = [max(b[1][a] for b in bounds) for a in range(3)]
    return [lo, hi]


def camera_for(bounds, direction=(1.0, 1.1, 0.75), margin=1.08):
    b = union(bounds)
    c = center(b)
    radius = math.dist(b[0], b[1]) / 2
    dist = radius / math.sin(math.radians(FOV_DEG) / 2) * margin
    norm = math.sqrt(sum(d * d for d in direction))
    pos = [round(c[a] + direction[a] / norm * dist, 1) for a in range(3)]
    return {'position': pos, 'target': [round(x, 1) for x in c]}


def main() -> None:
    ap = argparse.ArgumentParser(description='Build the viewer development fixture.')
    ap.add_argument('--src', type=Path, default=DEFAULT_SRC)
    ap.add_argument('--out', type=Path, default=HERE / 'sample-data.json')
    args = ap.parse_args()

    src = json.loads(args.src.read_text())
    parts = []
    bounds = {}
    for p in src['parts']:
        if p.get('moduleId') not in MODULES:
            continue
        kind = p.get('partKind')
        parts.append({
            'key': p['key'],
            'name': p['name'],
            'color': p['color'],
            'module': p['moduleId'],
            'status': STATUS_OVERRIDE.get(p['key'], STATUS_BY_KIND.get(kind, 'owned')),
            'positionB64': p['positionB64'],
            'indexB64': p['indexB64'],
            'bounds': p['bounds'],
        })
        bounds[p['key']] = p['bounds']

    stage1 = ['thigh', 'plate', 'ring7', 'motor7', 'motor8']
    stage2 = ['lower', 'ankle', 'foot', 'smallring', 'motor6', 'washer6']
    stage3 = ['hip', 'yaw', 'passive', 'ring8', 'ring9', 'motor9', 'washer9']
    torso = ['torso_base', 'ring10_torso', 'ring5_torso']
    power = ['power_support', 'regulator_insert', 'regulator']
    left = stage1 + stage2 + stage3 + ['motor10']
    missing = [k for k in left + torso + power if k not in bounds]
    if missing:
        raise SystemExit(f'source data lacks parts: {missing}')

    def cam(keys, **kw):
        return camera_for([bounds[k] for k in keys], **kw)

    # Two invented cables between the motor10 and motor9 bounds (placeholder routes, not the real harness).
    b10, b9 = bounds['motor10'], bounds['motor9']
    c10, c9 = center(b10), center(b9)
    x10, x9 = b10[1][0], b9[1][0]          # +x faces
    y10, y9 = b10[1][1], b9[1][1]          # +y (outer, left) faces
    dxl_path = [
        [x10 + 0.6, c10[1] + 3.0, c10[2] - 4.0],
        [x10 + 5.0, c10[1] + 5.0, b10[0][2] + 2.0],
        [max(x10, x9) + 7.0, c10[1] + 6.0, (b10[0][2] + b9[1][2]) / 2],
        [x9 + 5.0, c9[1] + 5.0, b9[1][2] - 6.0],
        [x9 + 0.6, c9[1] + 3.0, c9[2] + 4.0],
    ]
    p5v_path = [
        [c10[0] - 6.0, y10 + 0.6, c10[2]],
        [c10[0] - 9.0, y10 + 5.0, b10[0][2] + 1.0],
        [(c10[0] + c9[0]) / 2 - 8.0, max(y10, y9) + 7.0, (b10[0][2] + b9[1][2]) / 2],
        [c9[0] - 3.0, y9 + 5.0, b9[1][2] - 8.0],
        [c9[0], y9 + 0.6, c9[2] - 2.0],
    ]
    rnd = lambda path: [[round(v, 2) for v in pt] for pt in path]
    cables = [
        {'id': 'fx-dxl-10-9', 'label': 'Bus lead ID10 → ID9 (fixture)', 'kind': 'dxl', 'color': '#6a3df0', 'radius': 0.9,
         'path': rnd(dxl_path), 'from': 'ID10 hip yaw · port B', 'to': 'ID9 hip roll · port A', 'lengthMM': 60,
         'note': 'Fixture route for viewer testing.'},
        {'id': 'fx-5v-10-9', 'label': '5 V test lead (fixture)', 'kind': 'power-5v', 'color': '#e53935', 'radius': 0.8,
         'path': rnd(p5v_path), 'from': 'ID10 side test pad', 'to': 'ID9 side test pad', 'lengthMM': 75},
    ]
    photo = 'data:image/png;base64,' + base64.b64encode(PHOTO.read_bytes()).decode() if PHOTO.exists() else None

    screws = lambda q, size='M2 × 6': {'item': f'{size} self-tapping screw', 'qty': q, 'kind': 'fastener'}
    steps = [
        {
            'id': 'll-thigh-frame', 'chapter': 'left-leg', 'title': 'Lay out the thigh frame',
            'show': [], 'add': ['thigh', 'plate'], 'context': [],
            'approach': {'plate': [0, 30, 0]},
            'camera': cam(['thigh', 'plate']),
            'prepare': [
                {'item': 'Left thigh body', 'qty': 1, 'kind': 'printed'},
                {'item': 'Thigh reinforcing plate', 'qty': 1, 'kind': 'printed', 'note': 'Flat side faces outward.'},
                screws(4), {'item': '1.5 mm hex driver', 'qty': 1, 'kind': 'tool'},
            ],
            'instructions': ['Place the thigh body with both motor seats facing you.', 'Press the plate onto the outer face and drive four screws finger-tight.'],
            'checks': ['The plate sits flush with no gap at the corners.', 'All four screws are seated.'],
            'warnings': [],
        },
        {
            'id': 'll-knee-hip-motors', 'chapter': 'left-leg', 'title': 'Seat the knee and hip-pitch motors',
            'show': ['thigh', 'plate'], 'add': ['motor7', 'motor8', 'ring7'], 'context': [],
            'approach': {'motor7': [0, 42, 0], 'motor8': [0, 42, 6], 'ring7': [0, 28, 0]},
            'camera': cam(stage1),
            'prepare': [
                {'item': 'XL330 servo, ID7', 'qty': 1, 'kind': 'electronic'},
                {'item': 'XL330 servo, ID8', 'qty': 1, 'kind': 'electronic'},
                {'item': '22 mm sliding ring', 'qty': 1, 'kind': 'printed'}, screws(8),
            ],
            'instructions': ['Slide ID7 into the lower seat, horn outward.', 'Slide ID8 into the upper seat.', 'Fit the sliding ring over the ID7 horn.'],
            'checks': ['Both horns turn freely by hand.', 'Cable ports face the rear.'],
            'warnings': ['Do not force a horn while the servo is powered.'],
        },
        {
            'id': 'll-lower-leg', 'chapter': 'left-leg', 'title': 'Build the lower leg and foot',
            'show': stage1, 'add': stage2, 'context': [],
            'approach': {'lower': [0, 0, -36], 'ankle': [-30, 0, 0], 'foot': [0, 0, -44], 'smallring': [0, 22, 0], 'motor6': [0, 42, 0], 'washer6': [0, 16, 0]},
            'prepare': [
                {'item': 'Lower-leg link', 'qty': 1, 'kind': 'printed'},
                {'item': 'Left ankle bracket', 'qty': 1, 'kind': 'printed', 'note': 'Reprint required in the fixture status.'},
                {'item': 'Left foot', 'qty': 1, 'kind': 'printed'},
                {'item': 'XL330 servo, ID6', 'qty': 1, 'kind': 'electronic'},
                {'item': '0.5 mm metal washer', 'qty': 1, 'kind': 'fastener'}, screws(10),
            ],
            'instructions': ['Join the lower-leg link to the ID7 horn.', 'Seat ID6 in the ankle bracket, washer between horn and bracket.', 'Attach the foot.'],
            'checks': ['The ankle pivots without rubbing the washer.'],
            'warnings': [],
            'images': [{'src': photo, 'caption': 'Washer between the ID6 horn and the ankle bracket (existing review render).'}] if photo else [],
        },
        {
            'id': 'll-hip-roll', 'chapter': 'left-leg', 'title': 'Fit the hip bracket and roll motor',
            'show': stage1 + stage2, 'add': stage3, 'context': [],
            'approach': {'hip': [0, 0, 38], 'yaw': [0, 0, 48], 'passive': [0, -26, 0], 'ring8': [0, 26, 0], 'ring9': [26, 0, 0], 'motor9': [0, 0, -40], 'washer9': [14, 0, 0]},
            'camera': cam(stage1 + stage2 + stage3, direction=(1.0, 1.25, 0.5)),
            'prepare': [{'item': 'Hip bracket', 'qty': 1, 'kind': 'printed'}, {'item': 'XL330 servo, ID9', 'qty': 1, 'kind': 'electronic'}, screws(12)],
            'instructions': ['Fit the hip bracket over ID8.', 'Lower ID9 into the roll seat.', 'Close with the roll support plate.'],
            'checks': ['The leg rolls ±20° without contact.'],
            'warnings': [],
        },
        {
            'id': 'll-hip-yaw', 'chapter': 'left-leg', 'title': 'Mount the hip yaw motor and run its bus lead',
            'show': [k for k in left if k != 'motor10'], 'add': ['motor10'], 'context': [],
            'approach': {'motor10': [0, 0, 46]},
            'camera': cam(['motor10', 'motor9', 'hip', 'yaw'], direction=(1.2, 1.0, 0.45)),
            'prepare': [{'item': 'XL330 servo, ID10', 'qty': 1, 'kind': 'electronic'}, {'item': '3-pin JST EH lead, 60 mm', 'qty': 1, 'kind': 'cable'}],
            'instructions': ['Lower ID10 onto the yaw link.', 'Plug the bus lead into ID10 port B and route it down the +x side to ID9 port A.'],
            'checks': ['The lead clears the yaw sweep in both directions.', 'Both connectors click.'],
            'warnings': ['Keep the lead outside the sliding ring path.'],
            'cables': ['fx-dxl-10-9'],
        },
        {
            'id': 'll-harness-check', 'chapter': 'left-leg', 'title': 'Add the 5 V test lead and check the harness',
            'show': ['left-leg'], 'add': [], 'context': [],
            'camera': cam(['motor10', 'motor9'], direction=(0.6, 1.4, 0.4), margin=1.5),
            'prepare': [{'item': '5 V test lead, 75 mm', 'qty': 1, 'kind': 'cable'}, {'item': 'Multimeter', 'qty': 1, 'kind': 'tool'}],
            'instructions': ['Route the 5 V lead along the outer face.', 'Measure continuity end to end.'],
            'checks': ['Continuity reads below 1 Ω.', 'Neither lead is pinched.'],
            'warnings': [],
            'cables': ['fx-5v-10-9'],
        },
        {
            'id': 't-base', 'chapter': 'torso', 'title': 'Fit the torso base and sliding rings',
            'show': ['left-leg'], 'add': torso, 'context': ['right-leg'],
            'approach': {'torso_base': [0, 0, 40], 'ring10_torso': [0, 0, 26], 'ring5_torso': [0, 0, 26]},
            'prepare': [{'item': 'Torso base plate', 'qty': 1, 'kind': 'printed'}, {'item': 'Torso sliding ring', 'qty': 2, 'kind': 'printed'}, screws(6, 'M2 × 8')],
            'instructions': ['Lower the base plate onto both hip yaw horns.', 'Press the two sliding rings into their pockets.'],
            'checks': ['The base sits level on both legs.'],
            'warnings': [],
        },
        {
            'id': 't-power', 'chapter': 'torso', 'title': 'Install the power support and regulator',
            'show': ['left-leg'] + torso, 'add': power, 'context': ['right-leg', 'imu'],
            'approach': {'power_support': [40, 0, 0], 'regulator_insert': [0, 0, 30], 'regulator': [0, 0, 36]},
            'camera': cam(torso + power + ['motor10', 'motor5'], direction=(1.0, -0.4, 0.9)),
            'prepare': [{'item': 'Integrated power support', 'qty': 1, 'kind': 'printed'}, {'item': 'DFR1202 converter', 'qty': 1, 'kind': 'electronic'}, screws('as needed', 'M2 × 6')],
            'instructions': ['Slide the power support in from the front.', 'Drop the regulator insert and converter into the support.'],
            'checks': ['The converter output pads face up.'],
            'warnings': ['Do not connect a battery in this fixture step.'],
        },
    ]
    data = {
        'schemaVersion': 1,
        'title': 'MicroDuck assembly guide · DEVELOPMENT FIXTURE',
        'subtitle': 'Viewer test data: real meshes, placeholder steps and cables',
        'revision': 'fixture-20261009',
        'units': 'mm',
        'frame': 'x forward, y left, z up',
        'parts': parts,
        'chapters': [
            {'id': 'left-leg', 'title': 'Left leg (fixture)', 'summary': 'Fixture chapter: left-leg parts appear a few at a time. Placeholder text, not a build instruction.'},
            {'id': 'torso', 'title': 'Torso (fixture)', 'summary': 'Fixture chapter: torso base and power support, with the right leg as ghost context.'},
        ],
        'steps': steps,
        'cables': cables,
        'legend': [
            {'kind': 'dxl', 'color': '#6a3df0', 'label': 'DYNAMIXEL TTL bus'},
            {'kind': 'power-5v', 'color': '#e53935', 'label': '5 V supply'},
        ],
    }
    args.out.write_text(json.dumps(data, separators=(',', ':')))
    tri = sum(len(base64.b64decode(p['indexB64'])) // 12 for p in parts)
    print(json.dumps({'out': str(args.out), 'parts': len(parts), 'triangles': tri, 'steps': len(steps), 'cables': len(cables), 'bytes': args.out.stat().st_size}))


if __name__ == '__main__':
    main()
