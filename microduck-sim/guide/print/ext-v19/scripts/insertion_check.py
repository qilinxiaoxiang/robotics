#!/usr/bin/env python3
"""Connector insertion with plug and wire exit, V1.9 scene.

Each female Dupont housing is pulled straight off its pins by TRAVEL (12 mm) along the pin axis; the moving solid is
the housing plus a wire-exit stub (r 0.65 mm, 6 mm straight out of the housing's back before the wire bends). The swept
solid (hull of start and end; the housings are boxes, so the hull is the exact sweep up to the stub) is tested with
exact manifold3d booleans against:
  state A (cap on): every part at q = 0 (release cap, V1.9 pack, new parts);
  state B (cap lifted, how the Pi housings are actually plugged): the cap-group parts in place and the lower-head
  parts 40 mm lower.
Housings: the eight Pi-header housings of the neck bundle (guide meshes head_pi_gpio_pin_XX_receiving), the five
Pi-header housings of the amp jumpers (pins 4, 12, 34, 35, 40) and the six amp-header housings (audio study solids).
Excluded per housing: the board and pins it plugs onto and the neighbouring housings in the same header (they touch).
For every housing that hits something, the free pull before the first contact is found by bisection (0.1 mm), with
and without the wire stub. A Dupont female contact leaves a 2.54 mm header pin after about 6 mm of pull (inference
from the usual 5.8-6.0 mm mating length).
Writes ../checks/insertion-v19.json.
"""
from __future__ import annotations

import json

import manifold3d as m3
import numpy as np

import clips_v19 as C
import ext_lib as E
import scene_check as SCN

TRAVEL = 12.0
STUB_L, STUB_R = 6.0, 0.65
NEW = {'head_cap_v19', 'speaker_retainer_v19', 'clip_torso_v19', 'clip_bracket_v19', 'clip_head_v19', 'clip_cap_v19',
       'resistor_envelope_v19', 'pi_mini_hdmi_envelope_assumed'}


def sweep(H, d, travel=TRAVEL, stub=True):
    V = np.asarray(H.to_mesh().vert_properties)[:, :3]
    proj = V @ d
    far = V[proj > proj.max() - 1e-6]
    cen = far.mean(0)
    S = H + E.cyl(cen - 0.05 * d, d, STUB_L, STUB_R, 24) if stub else H
    if travel <= 0:
        return S
    return m3.Manifold.batch_hull([S, S.translate((travel * d).tolist())])


def free_travel(H, d, obstacles, stub):
    """Largest pull (0.1 mm steps, up to TRAVEL) before the swept housing (with or without the wire stub) overlaps any of
    the obstacles by more than 1e-3 mm3; 0 if it already overlaps at rest."""
    def hits(t):
        S = sweep(H, d, t, stub)
        return any((S ^ O).volume() > 1e-3 for O in obstacles)
    if not hits(TRAVEL):
        return TRAVEL
    if hits(0.0):
        return 0.0
    lo, hi = 0.0, TRAVEL
    while hi - lo > 0.1:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if hits(mid) else (mid, hi)
    return round(lo, 1)


def main():
    man = E.ia_lib.manifest()
    capT = np.eye(4)
    capT[2, 3] = -40.0
    scene = {}
    for k in man:
        if k in ('head_cap', 'rear_pack'):
            continue
        scene[k] = (None, SCN.is_cap_group(k), (E.ia_lib.manifest()[k].get('bounds')))
    newp = SCN.new_parts()
    _, n_pi, _, _ = C.cap_frame()
    jobs = []
    for k in man:
        if k.startswith('head_pi_gpio_pin_') and k.endswith('_receiving'):
            jobs.append((k, E.load_man(k), n_pi, 'pi'))
    for nm in ('pi_housing_pin04', 'pi_housing_pin12', 'pi_housing_pin35', 'pi_housing_pin40'):
        jobs.append((nm, E.stl_man(E.AUDIO / 'study-solids' / f'{nm}-world.stl'), n_pi, 'pi'))
    jobs.append(('pi_housing_pin34', newp['pi_housing_pin34'][0], n_pi, 'pi'))
    amp = E.stl_man(E.AUDIO / 'study-solids' / 'amp_housings-world.stl')
    for i, b in enumerate(sorted(amp.decompose(), key=lambda m: E.bbox(m)[0][1])):
        jobs.append((f'amp_housing_{i}', b, np.array([1.0, 0, 0]), 'amp'))
    housing_names = {j[0] for j in jobs} | {'amp_housings'}
    cache = {}

    def solid(k):
        if k not in cache:
            if k in newp:
                cache[k] = newp[k][0]
            elif k == 'rear_pack':
                cache[k] = E.stl_man(E.PACK_V19)
            else:
                cache[k] = E.load_man(k)
        return cache[k]

    obstacles = [k for k in man if k != 'head_cap'] + list(newp)
    out = {'_method': __doc__.strip(), 'travelMm': TRAVEL, 'stub': [STUB_L, STUB_R], 'housings': {}}
    for name, H, d, kind in jobs:
        Sw = sweep(H, d)
        bb = E.bbox(Sw)
        rec = {'pullDirection': d, 'kind': kind, 'A': {}, 'B': {}}
        for k in obstacles:
            if k in housing_names or k == name:
                continue
            if kind == 'pi' and (k == 'pi' or k.startswith('head_pi_zero_w_header') or k == 'head_pi_zero_w_gpio_solder_tails'):
                continue
            if kind == 'amp' and k == 'amplifier':
                continue
            capg = newp[k][2] if k in newp else SCN.is_cap_group(k)
            if k in newp or k == 'rear_pack' or 'bounds' not in man.get(k, {}):
                b0 = np.array(E.bbox(solid(k)), float)
            else:
                b0 = np.array(man[k]['bounds'], float)
            M = None
            for state in ('A', 'B'):
                ob = b0 if (state == 'A' or capg) else b0 + [0.0, 0.0, -40.0]
                if np.any(ob[0] > np.array(bb[1]) + 1.0) or np.any(ob[1] < np.array(bb[0]) - 1.0):
                    continue
                if M is None:
                    M = solid(k)
                Mo = M if (state == 'A' or capg) else M.transform(capT[:3, :])
                ov = (Sw ^ Mo).volume()
                if ov > 1e-3:
                    rec[state][k] = {'overlapMm3': round(ov, 3), 'newPart': k in NEW}
                else:
                    g = float(Sw.min_gap(Mo, 1.0))
                    if g < 1.0:
                        rec[state].setdefault('_near', {})[k] = round(g, 3)
        # free pull before the first contact, per state, for the parts it hits (housing alone and with the wire stub)
        for state in ('A', 'B'):
            hit = [k for k in rec[state] if k != '_near']
            if not hit:
                continue
            obs = []
            for k in hit:
                capg = newp[k][2] if k in newp else SCN.is_cap_group(k)
                M = solid(k)
                obs.append(M if (state == 'A' or capg) else M.transform(capT[:3, :]))
            rec[state]['_freeTravelMm'] = {'housingOnly': free_travel(H, d, obs, False),
                                           'withWireStub': free_travel(H, d, obs, True)}
        out['housings'][name] = E.rnd(rec, 3)
        hitsA = [k for k in rec['A'] if not k.startswith('_')]
        hitsB = [k for k in rec['B'] if not k.startswith('_')]
        print(name, 'A', hitsA, rec['A'].get('_freeTravelMm'), 'B', hitsB, rec['B'].get('_freeTravelMm'),
              'nearB', rec['B'].get('_near', {}), flush=True)
    newhits = sorted({(h, s, k) for h, r in out['housings'].items() for s in ('A', 'B') for k, v in r[s].items()
                      if not k.startswith('_') and v['newPart']})
    out['collisionsWithNewParts'] = [list(x) for x in newhits]
    E.jdump(out, E.OUT / 'checks' / 'insertion-v19.json')
    print('collisions with new parts', newhits)


if __name__ == '__main__':
    main()
