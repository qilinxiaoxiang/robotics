#!/usr/bin/env python3
"""Jaw first-contact angle over the whole head_yaw range (owner report 2026-10-13: straight ahead clear, turned head
touches the neck). neck_pitch 0, roll 0, head_pitch {-45, 0, 30}, head_yaw 0..170 step 10 plus -45/-90 (symmetry
check); jaw 0..40 deg, parts: head-pitch bracket group, motor 11/12 and neck links, torso. Writes ../margin-yaw.json."""
from __future__ import annotations

import sys
import time

from jn_lib import OUT, Checker, jdump

ALL = ('neck_pitch', 'neck', 'trunk_base')


def main():
    t0 = time.time()
    ck = Checker()
    rows = []
    for hp in (0.0, -45.0, 30.0):
        for y in list(range(0, 171, 10)) + [-45, -90]:
            q = {'neck_pitch': 0.0, 'head_pitch': hp, 'head_yaw': float(y), 'head_roll': 0.0}
            a, hit = ck.first_contact(q, ALL, step=2.0)
            rows.append({**q, 'firstContactJawDeg': a, 'part': hit and hit['part'], 'class': hit and hit['class']})
            print(hp, y, a, hit and hit['part'], f'{time.time() - t0:.0f}s', file=sys.stderr, flush=True)
    jdump({'_method': __doc__.strip(), 'yawMap': rows}, OUT / 'margin-yaw.json')


if __name__ == '__main__':
    main()
