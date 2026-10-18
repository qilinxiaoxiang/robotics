#!/usr/bin/env python3
"""Slack needed by each free span of a route as a function of head yaw alone (FK only, taut spans; seconds to run).
Answers how much loop the yaw crossing needs for a chosen hand-turning limit (the V1.8 guide allows about +-80 deg).
Writes yaw-slack.json. Usage: yaw_slack.py [route ...]
"""
import json
import sys

import numpy as np

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import FK, HERE, jdump, rnd  # noqa: E402


def main():
    spec = json.loads((HERE / 'route-candidates.json').read_text())
    names = sys.argv[1:] or [r['name'] for r in spec['routes']]
    fk = FK()
    out = {'_method': __doc__.strip()}
    for r in spec['routes']:
        if r['name'] not in names:
            continue
        pts = np.array([p[:3] for p in r['points']], float)
        bodies = [p[3] for p in r['points']]
        spans = [i for i in range(len(pts) - 1) if bodies[i] != bodies[i + 1]]
        rows = []
        for lim in (35.0, 60.0, 80.0, 90.0, 120.0, 170.0):
            worst = {i: 0.0 for i in spans}
            for a in np.arange(-lim, lim + 1e-6, 1.0):
                for roll in (-25.0, -21.4, 0.0, 9.9, 25.0):
                    T = fk.part_T({'head_yaw': np.radians(a), 'head_roll': np.radians(roll)})
                    W = np.array([T[b][:3, :3] @ p + T[b][:3, 3] for p, b in zip(pts, bodies)])
                    for i in spans:
                        worst[i] = max(worst[i], float(np.linalg.norm(W[i + 1] - W[i]) - np.linalg.norm(pts[i + 1] - pts[i])))
            rows.append({'yawLimitDeg': lim, 'rollsDeg': [-25, -21.4, 0, 9.9, 25],
                         'slackPerSpanMm': {f'{bodies[i]} -> {bodies[i + 1]}': rnd(worst[i], 1) for i in spans}})
            print(r['name'], lim, rows[-1]['slackPerSpanMm'], flush=True)
        out[r['name']] = rows
    jdump(out, HERE / 'yaw-slack.json')


if __name__ == '__main__':
    main()
