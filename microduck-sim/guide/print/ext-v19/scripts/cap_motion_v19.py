#!/usr/bin/env python3
"""Cap motion hits: does the release cap add contact in a pose the V1.8 robot can reach?

scene_check.py represents the release cap in motion by its difference from the V1.8 cap (head_cap_v19 minus head_cap,
'cap added'). It found that difference overlapping a few parts on other bodies in some joint-sweep or pickup poses.
For every partner it listed (head_cap_v19 'motionOverlaps' in ../checks/scene-check.json) and every pose of every
pose set (scene_check.relation_poses) in which the cap difference overlaps that partner by more than 0.01 mm3, this
script measures, in the same pose, the overlap of the V1.8 head with the same partner: the V1.8 cap and every other
V1.8 part on the head body (head_bottom, face_panel, eye_trim, camera_board, jaw_support, motor14, motor15,
mouth_sliding_ring, the Pi). A pose where the V1.8 head already overlaps that partner cannot be reached by the V1.8
robot either, so the cap difference adds no new restriction there. For single-joint sweeps it also reports the first
angle (from 0 outwards, in the sweep's steps) at which the V1.8 head and the cap difference touch the partner.
Writes ../checks/cap-motion-v19.json.
"""
from __future__ import annotations

import json

import numpy as np

import ext_lib as E
import scene_check as SCN
from motion import pose_sets
from nr_lib import FK, body_of

HEAD_V18 = ['head_bottom', 'face_panel', 'eye_trim', 'camera_board', 'jaw_support', 'motor14', 'motor15',
            'mouth_sliding_ring', 'pi']


def main():
    sc = json.loads((E.OUT / 'checks' / 'scene-check.json').read_text())
    hits = sc['head_cap_v19']['motionOverlaps']
    partners = sorted({h['part'] for h in hits})
    fk = FK()
    sets = pose_sets(fk)
    walk, _, _ = SCN.walking_poses()
    cap19 = E.stl_man(E.PARTS['head_cap_v19'])
    cap18 = E.load_man('head_cap')
    added = cap19 - cap18
    head18 = [('head_cap(V1.8)', cap18)] + [(k, E.load_man(k)) for k in HEAD_V18]
    out = {'_method': __doc__.strip(), 'partners': {}}
    for p in partners:
        pb = body_of(p) or ('trunk_base' if p != 'rear_pack' else 'trunk_base')
        P = E.stl_man(E.PACK_V19) if p == 'rear_pack' else E.load_man(p)
        rec = {'body': pb, 'sets': {}}
        for g, poses in SCN.relation_poses('jaw_soft', pb, sets, walk).items():
            flagged = []
            for q in poses:
                T = fk.part_T(q)
                Tr = np.linalg.inv(T['jaw_soft']) @ T[pb]
                Pm = P.transform(Tr[:3, :])
                if np.any(np.array(E.bbox(Pm))[0] > np.array(E.bbox(added))[1] + 0.1) or \
                        np.any(np.array(E.bbox(Pm))[1] < np.array(E.bbox(added))[0] - 0.1):
                    continue
                ov_new = (added ^ Pm).volume()
                if ov_new <= 0.01:
                    continue
                v18 = {}
                for k, M in head18:
                    o = (M ^ Pm).volume()
                    if o > 0.01:
                        v18[k] = round(o, 2)
                flagged.append({'poseDeg': {a: round(float(np.degrees(v)) if a != 'jaw' else float(v), 1) for a, v in q.items()},
                                'capAddedOverlapMm3': round(ov_new, 3), 'v18HeadOverlapMm3': v18,
                                'blockedOnV18': bool(v18)})
            if not flagged:
                continue
            r = {'posesWithCapAddedOverlap': len(flagged),
                 'notBlockedOnV18': [f for f in flagged if not f['blockedOnV18']],
                 'examples': sorted(flagged, key=lambda f: -f['capAddedOverlapMm3'])[:3]}
            if g == 'sweep':
                # first contact along each swept joint, from 0 outwards
                fc = {}
                for j in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll'):
                    grid = SCN.GRID[j]
                    for sign in (1, -1):
                        vals = sorted([v for v in grid if v * sign > 0], key=abs)
                        a18 = a19 = None
                        for v in vals:
                            q = dict(SCN.Q0, **{j: np.radians(v)})
                            T = fk.part_T(q)
                            Pm = P.transform((np.linalg.inv(T['jaw_soft']) @ T[pb])[:3, :])
                            if a19 is None and (added ^ Pm).volume() > 0.01:
                                a19 = float(v)
                            if a18 is None and any((M ^ Pm).volume() > 0.01 for _, M in head18):
                                a18 = float(v)
                            if a18 is not None and a19 is not None:
                                break
                        if a19 is not None:
                            fc[f'{j}{"+" if sign > 0 else "-"}'] = {'firstContactV18HeadDeg': a18, 'firstContactCapAddedDeg': a19,
                                                                    'capAddedFirst': a18 is None or abs(a19) < abs(a18)}
                r['firstContact'] = fc
            rec['sets'][g] = r
            print(p, g, 'flagged', len(flagged), 'not blocked on V1.8', len(r['notBlockedOnV18']), r.get('firstContact', ''),
                  flush=True)
        out['partners'][p] = rec
    out['summary'] = {'newRestrictions': sum(len(s['notBlockedOnV18']) for r in out['partners'].values() for s in r['sets'].values())
                      + sum(1 for r in out['partners'].values() for s in r['sets'].values()
                            for v in s.get('firstContact', {}).values() if v['capAddedFirst'])}
    print('summary', out['summary'], flush=True)
    E.jdump(out, E.OUT / 'checks' / 'cap-motion-v19.json')


if __name__ == '__main__':
    main()
