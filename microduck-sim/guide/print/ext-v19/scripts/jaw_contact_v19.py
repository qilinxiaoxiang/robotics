#!/usr/bin/env python3
"""Jaw opening against the two lower clips: does a V1.9 addition stop the jaw earlier than the V1.8 robot already does?

The scene check found jaw_frame overlapping the torso clip, the bracket clip and the bracket clip's raised screw head
at jaw 40 deg in some policy-box and beak-pickup postures. In those postures the open jaw may already hit V1.8 parts
(neck servo cases, bracket, shells), which the integrated study reported (jaw-pickup.json, neck_checks jaw).
For every posture of the policy box (81 neck/head poses) and the beak-pickup set (27): the jaw at 40 deg is tested
against the V1.9 additions (clip_torso_v19, clip_bracket_v19 and the two raised screw heads). Where it hits, the jaw
is opened from 0 to 40 deg in 0.5 deg steps and two first-contact angles are found (exact manifold3d overlap
> 0.01 mm3):
  theta18 = first contact with any V1.8 part on the torso, neck, bracket or yaw bodies (the jaw's own head parts
            excluded);
  theta19 = first contact with a V1.9 addition.
A new restriction is a posture with theta19 < theta18 (or theta18 none). Also reported against the planned jaw limit
(jaw-neck-check/README.md and HANDOFF-20261013.md open item 3): jaw at most 25 deg, head_pitch at most 65 deg while the
jaw is open.
Writes ../checks/jaw-contact-v19.json.
"""
from __future__ import annotations

import itertools

import numpy as np

import ext_lib as E
import scene_check as SCN
from motion import pose_sets
from nr_lib import FK, body_of

D2R = np.radians
OTHER = ('trunk_base', 'neck', 'neck_pitch', 'yaw_roll_motion')
NEW = ('clip_torso_v19', 'clip_bracket_v19', 'screw_head_S12-horn-025', 'screw_head_S11-horn-040')
JAW_LIMIT, PITCH_LIMIT = 25.0, 65.0


def main():
    fk = FK()
    NP = SCN.new_parts()
    man = E.ia_lib.manifest()
    jaw = E.load_man('jaw_frame')
    old = {}
    for k in man:
        b = body_of(k)
        if b in OTHER and k not in ('head_cap',):
            old[k] = (b, None)
    old['rear_pack'] = ('trunk_base', E.stl_man(E.PACK_V19))
    new = {k: (NP[k][1], NP[k][0]) for k in NEW}
    cache = {}

    def solid(k, d):
        if d[k][1] is not None:
            return d[k][1]
        if k not in cache:
            cache[k] = E.load_man(k)
        return cache[k]

    def bounds(k, d):
        if d[k][1] is not None:
            return np.array(E.bbox(d[k][1]))
        return np.array(man[k]['bounds'])

    def box_world(b0, T):
        c = np.array(list(itertools.product(*zip(b0[0], b0[1]))))
        w = c @ T[:3, :3].T + T[:3, 3]
        return w.min(0), w.max(0)

    def first_contact(q, d):
        """First jaw angle (0.5 deg steps) at which jaw_frame overlaps a part of d; (angle, part, overlap) or None."""
        for a in np.arange(0.0, 40.0 + 1e-9, 0.5):
            qa = dict(q, jaw=float(a))
            T = fk.part_T(qa)
            J = jaw.transform(T['jaw'][:3, :])
            jl, jh = np.array(E.bbox(J))
            for k, (b, _) in d.items():
                lo, hi = box_world(bounds(k, d), T[b])
                if np.any(lo > jh) or np.any(hi < jl):
                    continue
                ov = (J ^ solid(k, d).transform(T[b][:3, :])).volume()
                if ov > 0.01:
                    return {'jawDeg': float(a), 'part': k, 'overlapMm3': round(ov, 3)}
        return None

    sets = pose_sets(fk)
    postures = {}
    for g in ('policy', 'pickup'):
        seen = set()
        for q in sets[g]:
            key = tuple(round(float(np.degrees(q[j])), 2) for j in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll'))
            if key not in seen:
                seen.add(key)
                postures.setdefault(g, []).append(key)
    out = {'_method': __doc__.strip(), 'postures': {g: len(v) for g, v in postures.items()}, 'hits': []}
    for g, keys in postures.items():
        for key in keys:
            q = dict(zip(('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll'), D2R(np.array(key))))
            T = fk.part_T(dict(q, jaw=40.0))
            J = jaw.transform(T['jaw'][:3, :])
            jl, jh = np.array(E.bbox(J))
            hit40 = []
            for k, (b, M) in new.items():
                lo, hi = box_world(bounds(k, new), T[b])
                if np.any(lo > jh) or np.any(hi < jl):
                    continue
                ov = (J ^ M.transform(T[b][:3, :])).volume()
                if ov > 0.01:
                    hit40.append(k)
            if not hit40:
                continue
            t18 = first_contact(q, old)
            t19 = first_contact(q, new)
            a18 = t18['jawDeg'] if t18 else None
            a19 = t19['jawDeg'] if t19 else None
            newly = a19 is not None and (a18 is None or a19 < a18)
            allowed = key[1] <= PITCH_LIMIT
            rec = {'set': g, 'poseDeg': dict(zip(('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll'), key)),
                   'hitAt40': hit40, 'theta18': t18, 'theta19': t19, 'newRestriction': bool(newly),
                   'jawOpenAllowedByPitchRule': bool(allowed),
                   'newRestrictionWithinPlannedLimit': bool(newly and allowed and a19 <= JAW_LIMIT)}
            out['hits'].append(rec)
            print(g, key, 'hit40', hit40, 'theta18', t18, 'theta19', t19, 'new', newly, flush=True)
    out['summary'] = {'posturesHitAt40': len(out['hits']),
                      'newRestrictions': [h['poseDeg'] | {'set': h['set'], 'theta18': h['theta18'] and h['theta18']['jawDeg'],
                                                          'theta19': h['theta19']['jawDeg']}
                                          for h in out['hits'] if h['newRestriction']],
                      'newRestrictionsWithinPlannedLimit': sum(h['newRestrictionWithinPlannedLimit'] for h in out['hits'])}
    print('summary', out['summary'], flush=True)
    E.jdump(out, E.OUT / 'checks' / 'jaw-contact-v19.json')


if __name__ == '__main__':
    main()
