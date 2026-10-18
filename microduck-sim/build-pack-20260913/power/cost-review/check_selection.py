"""Reproduce the finite power choice and nominal mounting compatibility.

Manufacturer curve readings are approximate inputs, not measurements by us.
CAD paths stay relative to the simulator workspace. Requires trimesh/numpy.
"""
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
import trimesh

P = Path(__file__).resolve().parent
BUILD = P.parents[1]
OLD = BUILD.parent / 'hardware-design-20260912/whole-robot-20260912/assembly'
design = json.loads((OLD/'compact-battery/design.json').read_text())
old_mesh_path = OLD/'compact-battery/large_regulator-envelope-body.stl'
old_mesh = trimesh.load(old_mesh_path, force='mesh')
mount_code = (OLD/'build_compact_battery.py').read_text()
assert '[-54.931,-16.069]' in mount_code and '[-12.7,12.7]' in mount_code
cad_pitch = [54.931-16.069, 25.4]
new_pitch = [1.53*25.4, 1*25.4]
battery_box = design['battery']['dimensions']
anker_box = [104,52.3,26]
fits = [x for x in itertools.permutations(anker_box)
        if all(a <= b for a,b in zip(x,battery_box))]
criteria = {'servo_rail_v':5, 'servo_startup_screen_a':8.5,
            'whole_robot_walking_assumption_a_at5v':5.2,
            'battery_low_v':6.6, 'battery_full_v':8.4}
checks = {
    'new_board_hole_pattern_matches_existing_mount': bool(np.allclose(cad_pitch,new_pitch)),
    'new_board_nominal_plan_matches_old_envelope': bool(np.allclose(old_mesh.extents[:2],[43.2,31.8],atol=.001)),
    'dimensioned_new_profile_below_old_reserved_height': bool(6.1+1.57+1.8 < old_mesh.extents[2]),
    'nominal_underside_projection_clears_2mm_shelf_spacing': 2 > 1.8,
    '14a_conservative_graph_reading_exceeds_8p5a_screen': 14 > criteria['servo_startup_screen_a'],
    'low_battery_has_dropout_headroom_before_wiring_sag': 6.6 > 5+.3,
    'checked_anker_pack_exceeds_every_axis_aligned_slot_orientation': not fits,
    'checked_anker_single_5v_port_below_walking_assumption': 3 < 5.2,
    'cheaper_2866_curve_below_unchanged_screen': 7.0 < 8.5,
    'cheaper_5571_curve_below_unchanged_screen': 8.0 < 8.5,
}
result = {
    'checked_date':'2026-09-13', 'problem_ids':['P5','P6'],
    'verdict':'SELECT_GEA8502S60E2_PLUS_D42V110F5_KEEP_S13V30F5',
    'criteria':criteria, 'checks':checks, 'all_checks_passed':all(checks.values()),
    'mechanical':{'existing_cad_hole_pitch_mm':cad_pitch,'new_board_hole_pitch_mm':new_pitch,
                  'old_reserved_box_mm':old_mesh.extents.tolist(),
                  'new_dimensioned_height_sum_mm':6.1+1.57+1.8,
                  'nominal_underside_clearance_mm':round(2-1.8,3),
                  'both_boards_edge_tolerance_mm':.3,'both_boards_hole_location_tolerance_mm':.1,
                  'print_geometry_changed':False,
                  'scope':'Nominal mounting/profile comparison only. Check board underside, spacer edges and solder against actual print before tightening. Frozen old box omits detailed underside component shapes; no claim of complete component-level collision proof.'},
    'electrical':{'graph_current_screen_a':14,'graph_conditions':'room temperature, still air, no additional heat sink',
                  'dropout_screen_v_at_up_to10a':.3,
                  'startup_pulse_duration_and_enclosed_temperature_measured':False},
    'cost_usd':{'battery':17.99,'old_servo_regulator':79.95,'new_servo_regulator':59.95,
                'logic_regulator':17.95,'old_battery_and_two_boards':115.89,
                'new_battery_and_two_boards':95.89,'saved':20,
                'excludes':'charger, protection parts, wiring, connectors, shipping and tax'},
    'source_hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()
                     for f in [old_mesh_path,OLD/'compact-battery/design.json',OLD/'build_compact_battery.py',
                               *sorted((P/'sources').glob('*dimensions.pdf')),
                               P/'sources/5671-0J13892.png',P/'sources/5671-0J13895.jpg',
                               P/'sources/2866-0J7442.png',P/'sources/5571-0J13530.png']},
    'hardware_tests':0,
}
(P/'selection-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['source_hashes']},indent=2))
assert result['all_checks_passed']
