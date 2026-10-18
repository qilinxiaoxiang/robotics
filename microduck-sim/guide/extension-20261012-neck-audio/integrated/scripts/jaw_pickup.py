#!/usr/bin/env python3
"""Task 4: does the open jaw hit the neck in the beak-pickup postures? (independent of any wiring)

Pose set: the 27 pickup postures of neck-route/motion.py (neck_pitch -90/-60/-45, head_pitch 0/45/90, head_yaw
-24.6/0/34, head_roll 0; 27 x jaw {0, 40} = the 54 pickup poses), with the jaw swept 0..40 deg in 2 deg steps.
For each posture and jaw angle: exact overlap volume (manifold3d intersection) and smallest gap (min_gap, 10 mm search)
between the jaw frame and every part below the head (torso shell and parts, ID12/ID11 cases and links, head-pitch
bracket and ring, idlers). The rest of the head is checked against the same parts at jaw 0 for comparison.
Overlap depth = extent of the overlap solid along its thinnest principal axis; onJawAtRestMm = overlap centroid in the jaw rest frame.
Classes: 'interference' = overlap > 0.01 mm3 (the solids would have to pass through each other); 'contact' = no
overlap but gap < 0.2 mm; 'clear' = gap >= 0.2 mm.
Kinematics: MJCF (nr_lib.FK); part-to-body assignment checked in neck-route/kin_check.py. Writes ../jaw-pickup.json.
"""
from __future__ import annotations

import itertools
import json
import time

import numpy as np

import int_lib as L
from nr_lib import FK, BODY_OF, ia_lib, load_solid  # noqa: E402

D2R = np.radians
BELOW = ['shell_right', 'shell_left', 'torso_base', 'rear_pack', 'rear_pack_cover', 'openrb_board', 'motor12', 'motor11',
         'neck_link_a', 'neck_link_b', 'neck_pitch', 'neck_pitch_ring', 'idler11', 'idler_cap11', 'idler12', 'idler_cap12']
HEAD_REST = ['head_bottom', 'jaw_support', 'face_panel', 'head_cap', 'motor14', 'motor15', 'mouth_sliding_ring',
             'motor13', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b']
JAW_STEPS = np.arange(0.0, 40.0 + 1e-9, 2.0)


def tf(M, T):
    return M.transform(T[:3, :].tolist())


def cls(ov, g):
    return 'interference' if ov > 0.01 else ('contact' if g < 0.2 else 'clear')


def main():
    t0 = time.time()
    fk = FK()
    man = lambda k: ia_lib.to_manifold(*load_solid(k))  # noqa: E731
    jaw = man('jaw_frame')
    below = {k: (man(k), BODY_OF[k]) for k in BELOW}
    rest = {k: (man(k), BODY_OF[k]) for k in HEAD_REST}
    rows = []
    for n, h, y in itertools.product((-90.0, -60.0, -45.0), (0.0, 45.0, 90.0), (-24.6, 0.0, 34.0)):
        q = dict(neck_pitch=D2R(n), head_pitch=D2R(h), head_yaw=D2R(y), head_roll=0.0)
        per_jaw = []
        for a in JAW_STEPS:
            T = fk.part_T({**q, 'jaw': float(a)})
            J = tf(jaw, T['jaw'])
            hits = []
            for k, (M, b) in below.items():
                P = tf(M, T[b])
                g = float(J.min_gap(P, 10.0))
                if g >= 10.0:
                    continue
                X = J ^ P
                ov = X.volume()
                row = {'part': k, 'overlapMm3': round(ov, 3), 'gapMm': round(g, 3), 'class': cls(ov, g)}
                if ov > 0.01:
                    # where on the jaw: overlap centroid mapped back to the jaw frame at rest (q = 0, jaw 0)
                    v = np.asarray(X.to_mesh().vert_properties)[:, :3]
                    c = v.mean(0)
                    Ti = np.linalg.inv(T['jaw'])
                    row['onJawAtRestMm'] = np.round(Ti[:3, :3] @ c + Ti[:3, 3], 1).tolist()
                    row['overlapDepthMm'] = round(float(np.ptp(v @ np.linalg.svd(v - v.mean(0), full_matrices=False)[2][2])), 2)
                hits.append(row)
            hits.sort(key=lambda r: (-r['overlapMm3'], r['gapMm']))
            per_jaw.append({'jawDeg': float(a), 'nearest': hits[:3]})
        # the rest of the head against the same parts (jaw 0): is the posture itself blocked without the jaw?
        T = fk.part_T({**q, 'jaw': 0.0})
        head_hits = []
        for k, (M, b) in rest.items():
            H = tf(M, T[b])
            for kb, (Mb, bb) in below.items():
                if bb == b or (b == 'yaw_roll_motion' and kb in ('neck_pitch', 'neck_pitch_ring')):
                    continue      # same body, or the yaw link's own bearing on the bracket ring
                P = tf(Mb, T[bb])
                g = float(H.min_gap(P, 2.0))
                if g < 0.2:
                    head_hits.append({'head': k, 'part': kb, 'overlapMm3': round((H ^ P).volume(), 3), 'gapMm': round(g, 3)})
        first = lambda c: next((r['jawDeg'] for r in per_jaw if r['nearest'] and any(x['class'] in c for x in r['nearest'])), None)  # noqa: E731
        last_clear = None
        for r in per_jaw:
            if r['nearest'] and r['nearest'][0]['class'] != 'clear':
                break
            last_clear = r['jawDeg']
        at40 = per_jaw[-1]['nearest'][0] if per_jaw[-1]['nearest'] else None
        row = {'poseDeg': dict(neck_pitch=n, head_pitch=h, head_yaw=y, head_roll=0.0),
               'firstJawDegWithContactOrInterference': first(('contact', 'interference')),
               'firstJawDegWithInterference': first(('interference',)),
               'largestClearJawDeg': last_clear,
               'at40': at40,
               'maxOverlapMm3': max((x['overlapMm3'] for r in per_jaw for x in r['nearest']), default=0.0),
               'partsTouched': sorted({x['part'] for r in per_jaw for x in r['nearest'] if x['class'] != 'clear'}),
               'headWithoutJawAt0': head_hits,
               'sweep': per_jaw}
        rows.append(row)
        print(n, h, y, 'first contact', row['firstJawDegWithContactOrInterference'], 'first interference',
              row['firstJawDegWithInterference'], 'at40', at40, 'head@0', head_hits[:2], f'{time.time() - t0:.0f}s', flush=True)
    summ = {
        'postures': len(rows), 'pickupPoses': 2 * len(rows),
        'jaw0': {c: sum(1 for r in rows if (r['sweep'][0]['nearest'] and r['sweep'][0]['nearest'][0]['class'] == c)) for c in ('interference', 'contact')},
        'jaw40': {c: sum(1 for r in rows if (r['at40'] and r['at40']['class'] == c)) for c in ('interference', 'contact', 'clear')},
        'jaw40ByPart': {},
        'posturesWithAnyInterference0to40': sum(1 for r in rows if r['firstJawDegWithInterference'] is not None),
        'posturesBlockedWithoutJaw': sum(1 for r in rows if r['headWithoutJawAt0']),
    }
    for r in rows:
        if r['at40'] and r['at40']['class'] != 'clear':
            k = f"{r['at40']['part']}:{r['at40']['class']}"
            summ['jaw40ByPart'][k] = summ['jaw40ByPart'].get(k, 0) + 1
    out = {'_method': __doc__.strip(), 'summary': summ, 'postures': rows}
    L.jdump(out, L.STUDY / 'jaw-pickup.json')
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
