#!/usr/bin/env python3
"""Compare complete tether power paths. A calculation is not a hardware test."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def screen():
    old = json.loads((ROOT.parent / 'power/power_inputs.json').read_text())
    copper = old['wiring']['copper_ohm_m_at20C']
    thermal_factor = 1 + 0.00393 * (40 - 20)
    # All wire lengths are one-way. Both positive and return are counted.
    # Contact/splice allowances are assumptions, not manufacturer guarantees.
    paths = {
        'jack_18awg_0p100m_loop': 2 * .100 * copper['18'] * thermal_factor,
        'internal_16awg_0p1m_loop': 2 * .1 * copper['16'] * thermal_factor,
        'barrel_contacts_loop_allowance': .020,
        # Positive: jack/F0, F0/trunk, trunk split, four-way fanout.
        # Return: jack/trunk, trunk split, four-way fanout = seven joints.
        'main_splices_loop_allowance': 7 * .005,
        'group_20awg_0p15m_loop': 2 * .15 * copper['20'] * thermal_factor,
        # Branch fuse input/output and positive/return Y = four joints.
        'group_splices_loop_allowance': 4 * .005,
        'servo_22awg_0p1m_loop': 2 * .1 * copper['22'] * thermal_factor,
        'servo_jst_contacts_loop_after_test_max': 2 * .020,
    }
    scenarios = [
        ('allocated_walking', 3.8, 1.5, .75),
        ('initial_supervisor_boundary', 5., 2.25, 1.3),
        ('meanwell_nameplate_boundary', 6., 2.25, 1.3),
        ('old_unmeasured_startup_assumption', 8.5, 2.94, 1.47),
        ('adafruit_nameplate_boundary', 10., 3., 1.5),
    ]
    sources = [
        {'id': 'meanwell', 'part': 'GST60A05-P1J', 'rating_a': 6.,
         'low_v': 4.75, 'high_v': 5.25, 'ripple_pp_v': .120,
         'factory_16awg_max_m': 1.05, 'source_temp_allowance_v': 5 * .0003 * 15,
         'reference_plane': 'plug terminal explicitly stated in manufacturer note 2',
         'url': 'https://www.meanwell.com/Upload/PDF/GST60A/GST60A-SPEC.PDF'},
        {'id': 'adafruit', 'part': '658 / JYH5Z-0501000-BY', 'rating_a': 10.,
         'low_v': 4.5, 'high_v': 5.35, 'ripple_pp_v': .240,
         'factory_16awg_max_m': 1.2, 'source_temp_allowance_v': 0.,
         'reference_plane': 'OEM PDF does not explicitly identify voltage reference plane',
         'url': 'https://cdn-shop.adafruit.com/product-files/658/C726-004__jyh5z-0501000-by__5v10a.pdf'},
    ]
    for source in sources:
        source['cases'] = []
        factory_r = 2 * source['factory_16awg_max_m'] * copper['16'] * thermal_factor
        for tag, total, group, motor in scenarios:
            drops = {
                'jack_leads_v': total * paths['jack_18awg_0p100m_loop'],
                'internal_trunk_v': total * paths['internal_16awg_0p1m_loop'],
                'barrel_contacts_v': total * paths['barrel_contacts_loop_allowance'],
                'main_splices_v': total * paths['main_splices_loop_allowance'],
                'main_fuse_hot_drop_model_v': total / 10 * .100,
                'group_wire_v': group * paths['group_20awg_0p15m_loop'],
                'group_splices_v': group * paths['group_splices_loop_allowance'],
                'group_fuse_hot_drop_model_v': group / 3 * .131,
                'servo_tail_v': motor * paths['servo_22awg_0p1m_loop'],
                'servo_contacts_v': motor * paths['servo_jst_contacts_loop_after_test_max'],
            }
            post_plug_drop = sum(drops.values())
            # Whole p-p ripple is subtracted, not a claim about its waveform.
            floor = source['low_v'] - source['ripple_pp_v'] - source['source_temp_allowance_v']
            low_plug = floor - post_plug_drop
            extra_cord = total * factory_r
            low_internal = low_plug - extra_cord
            source['cases'].append({
                'name': tag, 'assumed_total_servo_a': total,
                'assumed_worst_group_a': group, 'assumed_worst_servo_a': motor,
                'drops_after_plug_v': drops, 'factory_cord_drop_sensitivity_v': extra_cord,
                'low_endpoint_from_published_plug_v': low_plug,
                'extra_pessimistic_endpoint_subtracting_factory_cord_again_v': low_internal,
                'nominal_5v_at_plug_dc_endpoint_v': 5. - post_plug_drop,
                'within_source_current_rating': total <= source['rating_a'],
                'above_3p7v_even_with_extra_cord_subtraction': low_internal >= 3.7,
                'above_old_4p5v_gate_from_plug': low_plug >= 4.5,
                'above_4p0v_gait_screen_from_plug': low_plug >= 4.0,
                'within_initial_software_current_screen': total <= 5. and group <= 2.25 and motor <= 1.3,
            })
        source['static_high_with_full_ripple_and_temperature_allowance_v'] = (
            source['high_v'] + source['ripple_pp_v'] + source['source_temp_allowance_v'])
    return {
        'verified_date': '2026-09-13', 'problem_ids': ['P5', 'P6'],
        'evidence_kind': 'static resistance sensitivity calculation; no hardware measurements',
        'selected_source': 'Mean Well GST60A05-P1J, 5V 6A; motor rail only',
        'selected_mating_lead': 'Tensility 10-06257; conservative published rating 11.25A',
        'assumed_wire_temperature_c': 40,
        'meanwell_source_temperature_sensitivity_c': [25, 40],
        'path_resistance_ohm': paths, 'sources': sources,
        'excluded_from_proof': [
            'actual walking/startup/current distribution and gait transfer',
            'actual connector, solder-joint and hot fuse resistances',
            'load transients, regenerative voltage and current-monitor latency',
            'electrical fuse opening coordination under a short circuit',
            'final cable bend radius, route length and tether disturbance',
            'delivery date, borrowed AC cord and lab test-equipment availability',
        ],
        'decision': 'Select Mean Well with the mating jack leads shortened to 100mm for staged commissioning of all 15 servos within a 5A total motor envelope. The static 4.0V endpoint screen passes narrowly under its assumptions. Preserve the negative old4.5V gate; a4.0V gait release also requires the revised low-voltage gait regression and physical walking/pick acceptance. Adafruit658 is rejected for its wider low-output bound, despite its larger current label.',
    }


if __name__ == '__main__':
    data = screen()
    mw, ada = data['sources']
    # Protect the decision-relevant positive and negative comparison results.
    assert mw['cases'][1]['within_source_current_rating']
    assert mw['cases'][1]['above_3p7v_even_with_extra_cord_subtraction']
    assert not ada['cases'][1]['above_3p7v_even_with_extra_cord_subtraction']
    assert not mw['cases'][1]['above_old_4p5v_gate_from_plug']
    assert mw['cases'][1]['above_4p0v_gait_screen_from_plug']
    assert not mw['cases'][3]['within_source_current_rating']
    (ROOT / 'power-screen.json').write_text(json.dumps(data, indent=2) + '\n')
    for source in data['sources']:
        for row in source['cases']:
            print(source['part'], row['name'],
                  round(row['low_endpoint_from_published_plug_v'], 3),
                  round(row['extra_pessimistic_endpoint_subtracting_factory_cord_again_v'], 3),
                  'source current valid:', row['within_source_current_rating'])
