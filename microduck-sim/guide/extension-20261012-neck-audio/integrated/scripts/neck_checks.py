#!/usr/bin/env python3
"""Rerun the neck-route motion checks (slack, pinch, wrap: motion.py; jaw against the wire spans: jaw_check.py; yaw slack:
yaw_slack.py) for the final route A3, with the integrated study cap in place of the neck-route notch-less cap.

The neck-route scripts are imported unchanged and redirected: nr_lib.NOTCHLESS_CAP -> the integrated cap, and their HERE
-> ../checks/, which holds route-candidates.json = the A3 route from ../route-A3.json with groupRadiusMm 1.7 (so the
reported pinch clearance is the wire-group surface clearance; centrelineDistanceMm is the centreline distance).
Outputs land in ../checks/ (motion.json, jaw-check.json, yaw-slack.json). Usage: neck_checks.py motion|jaw|yaw
"""
import json
import sys

import int_lib as L

CHECKS = L.STUDY / 'checks'


def main(which):
    CHECKS.mkdir(exist_ok=True)
    r = json.loads((L.STUDY / 'route-A3.json').read_text())['routes'][0]
    r = {**r, 'groupRadiusMm': 1.7}
    L.jdump({'_doc': __doc__.strip(), 'routes': [r]}, CHECKS / 'route-candidates.json')
    sys.path.insert(0, str(L.NR))
    import nr_lib
    nr_lib.NOTCHLESS_CAP = L.INTEGRATED_CAP
    mod = {'motion': 'motion', 'jaw': 'jaw_check', 'yaw': 'yaw_slack'}[which]
    m = __import__(mod)
    m.HERE = CHECKS
    sys.argv = [mod + '.py', r['name']]
    m.main()


if __name__ == '__main__':
    main(sys.argv[1])
