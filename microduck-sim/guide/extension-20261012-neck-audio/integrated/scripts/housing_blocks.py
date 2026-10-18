#!/usr/bin/env python3
"""Can the bundle's Pi-end contacts sit in multi-way Dupont housings next to the audio Pi-end housings?

Phase 1 put the eight bundle contacts into two 1 x 5 housings (odd row 1, 3, 5, empty 7, 9; even row 2, empty 4, 6, 8,
10). The audio study now uses pin 4 (amplifier Vin) with its own 1-pin housing, so the even-row 1 x 5 cannot be used.
Candidate blocks, each modelled as the convex hull of the V1.8 1-pin receiving housings it replaces (same pitch, same
length): odd 1 x 5 (pins 1..9), even 1 x 1 at pin 2, even 1 x 3 (pins 6, 8, 10). Each block is checked (manifold3d
intersection volume and min_gap) against the audio Pi-end housings (pins 4, 12, 34, 35, 40), the audio jumpers, the
other blocks, the Pi header pins it does not own, and the A3 fan wires except its own wire ends.
Writes ../housing-blocks.json.
"""
import manifold3d as m3

import int_lib as L
from pm_lib import audio_solid, audio_wire_tubes, load_stl_man
from route_scene import pin34_housing
from scene import load_man

BLOCKS = {'odd_1x5_pins_1_3_5_7_9': [1, 3, 5, 7, 9], 'even_1x1_pin_2': [2], 'even_1x3_pins_6_8_10': [6, 8, 10]}


def housing(p):
    if p == 7:     # V1.8 has no pin-7 housing: shift the pin-5 housing by one pitch (-2.54 mm in y)
        return load_man('head_pi_gpio_pin_05_receiving').translate([0, -2.54, 0])
    return load_man(f'head_pi_gpio_pin_{p:02d}_receiving')


def main():
    blocks = {k: m3.Manifold.batch_hull([housing(p) for p in v]) for k, v in BLOCKS.items()}
    others = {'pi_housing_pin04': audio_solid('pi_housing_pin04'), 'pi_housing_pin12': audio_solid('pi_housing_pin12'),
              'pi_housing_pin35': audio_solid('pi_housing_pin35'), 'pi_housing_pin40': audio_solid('pi_housing_pin40'),
              'pi_housing_pin34': pin34_housing(), 'A3_fan_wires': load_stl_man(L.SOL / 'A3_fan_wires-world.stl')}
    for k, M in audio_wire_tubes().items():
        if k != 'audio_wire_amp_gnd_pin14':
            others[k] = M
    for p in range(1, 41):
        others[f'header_pin_{p:02d}'] = load_man(f'head_pi_zero_w_header_pin_{p:02d}')
    out = {'_method': __doc__.strip(), 'blocks': {}}
    for k, B in blocks.items():
        rows = {}
        for o, M in list(others.items()) + [(b, blocks[b]) for b in blocks if b != k]:
            if o.startswith('header_pin_') and int(o[-2:]) in BLOCKS[k]:
                continue
            ov = (B ^ M).volume()
            rows[o] = {'overlapMm3': round(ov, 4), 'gapMm': round(0.0 if ov > 1e-4 else float(B.min_gap(M, 3.0)), 3)}
        fan = rows.pop('A3_fan_wires')
        worst = sorted(rows.items(), key=lambda kv: (-kv[1]['overlapMm3'], kv[1]['gapMm']))[:4]
        out['blocks'][k] = {'pins': BLOCKS[k], 'nearest': dict(worst), 'A3FanWires': fan,
                            'clearOfAllButOwnWires': all(v['overlapMm3'] <= 1e-3 for v in rows.values())}
        print(k, out['blocks'][k]['clearOfAllButOwnWires'], dict(worst), 'fan', fan, flush=True)
    L.jdump(out, L.STUDY / 'housing-blocks.json')


if __name__ == '__main__':
    main()
