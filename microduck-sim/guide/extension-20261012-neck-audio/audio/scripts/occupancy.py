#!/usr/bin/env python3
"""Volumes the audio extension occupies, for integration with the parallel neck-route study. Writes ../occupancy.json.

Rigid parts: exact bounds of every study solid (STL in ../study-solids). Flexible wires: bounds of each hand-set tube
(../wire-routes.json) plus a split into 'above z 135' (under the roof) and 'below z 135' (in front of the Pi).
If the neck-route study's notch-less cap exists, its change against the V1.8 cap is intersected with the audio cap
additions and every audio solid (exact booleans; read-only use of that file).
"""
from __future__ import annotations

import json

import manifold3d as m3
import numpy as np
import trimesh

from check_lib import man_from_tm
from scene import STUDY
from wires import R_JUMPER, R_LEAD, tube_manifold

S = STUDY / 'study-solids'
RIGID = ['speaker', 'speaker_leads_envelope', 'speaker_retainer', 'speaker_screws_envelope', 'amplifier',
         'amp_housings', 'amp_screws_envelope', 'cap_added_material', 'pi_housing_pin04', 'pi_housing_pin12',
         'pi_housing_pin14', 'pi_housing_pin35', 'pi_housing_pin40']


def bounds(M):
    return np.round(np.array(M.bounding_box()).reshape(2, 3), 2).tolist()


def main():
    out = {'frame': 'robot frame, mm, x forward, y left, z up', 'rigid': {}, 'wires': {}}
    mans = {}
    for k in RIGID:
        M = man_from_tm(trimesh.load(S / f'{k}-world.stl', force='mesh'))
        mans[k] = M
        out['rigid'][k] = {'bounds': bounds(M), 'volumeMm3': round(M.volume(), 1), 'stl': str(S / f'{k}-world.stl')}
    W = json.loads((STUDY / 'wire-routes.json').read_text())
    for name, poly in W.items():
        T = tube_manifold(np.asarray(poly, float), R_LEAD if name.startswith('spk') else R_JUMPER)
        mans['wire_' + name] = T
        lo = T.trim_by_plane([0, 0, -1], -135.0)   # keep z <= 135
        hi = T.trim_by_plane([0, 0, 1], 135.0)     # keep z >= 135
        out['wires'][name] = {'bounds': bounds(T), 'belowZ135': None if lo.is_empty() else bounds(lo),
                              'aboveZ135': None if hi.is_empty() else bounds(hi)}
    below = {k: v['bounds'] for k, v in out['rigid'].items() if v['bounds'][0][2] < 135}
    out['summary'] = {
        'aboveZ135': 'speaker, collar, retainer, amplifier, amp housings, amp posts and every wire run between the amp '
                     'and the Pi top edge (x -15..57 under the roof, |y| <= 19; over the Pi top edge at x 56..66, '
                     'y -11..10, z 144..149)',
        'belowZ135_rigid': below,
        'belowZ135_flexible': {k: v['belowZ135'] for k, v in out['wires'].items() if v['belowZ135']},
        'corridorNote': 'Below z 135 the audio extension adds only the five Pi-end housings (pins 4, 12, 14, 35, 40, '
                        'x 59.5..74.4) and the five jumper drops in front of the Pi between the housing ends and the '
                        'face plate (x 64.8..77.1). The lower head (head_bottom up to the header pins from below, '
                        'x < 59 under the Pi, the neck opening) is untouched; pins 12/14 use a lane at z 111.9..114.6, '
                        'x 75.7..77.1, y 8.2..17.0 that a bundle arriving from below at the housing ends must share.'}
    nn = STUDY.parent / 'neck-route' / 'study-solids' / 'head_cap-no-notch.stl'
    if nn.exists():
        v18 = man_from_tm(trimesh.load(STUDY.parents[1] / 'print/world/head_cap.stl', force='mesh'))
        nc = man_from_tm(trimesh.load(nn, force='mesh'))
        change = (nc - v18) + (v18 - nc)
        out['neckRouteNotchlessCap'] = {
            'file': str(nn), 'changeVsV18Mm3': round(change.volume(), 2), 'changeBounds': bounds(change),
            'overlapWithAudioCapAdditionsMm3': round((change ^ mans['cap_added_material']).volume(), 4),
            'overlapWithAudioSolidsMm3': {k: round((nc ^ M).volume(), 4) for k, M in mans.items()
                                          if k not in ('cap_added_material', 'speaker_screws_envelope', 'amp_screws_envelope')
                                          and (nc ^ M).volume() > 1e-4},
            'note': 'read-only check against the neck-route study file as it existed when this ran'}
    (STUDY / 'occupancy.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out['summary'], indent=1)[:2500])
    print(json.dumps(out.get('neckRouteNotchlessCap'), indent=1))


if __name__ == '__main__':
    main()
