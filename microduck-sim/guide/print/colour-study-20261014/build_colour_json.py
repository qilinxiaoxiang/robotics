"""Write colour_as_built.json: the printed colour of every visible MicroDuck part, each with its source and quote.
    python3 build_colour_json.py
Stock (community) parts: the 10/1 batch. Original plate 1 was printed orange and plate 5 black (COLOR-PLAN.md); the other
61 instances were regrouped into four single-colour jobs (04-FOUR-COLOR-20260929/color-layout.json). Our own prints: the
"color" field of release-V1.6-final/final-V1.6.json and release-V1.8/V1.9/V1.11 scripts/rows.json. Grams come from
object_grams.json (per-object extrusion in the sliced Elegoo G-code that was released for that colour)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRINT = HERE.parent
PRINTING = PRINT.parents[1] / 'build-pack-20260913/redesign-20260913/printing'
PLAN = PRINTING / 'COLOR-PLAN.md'
LAYOUT = PRINTING / '04-FOUR-COLOR-20260929/color-layout.json'
ORIG = PRINTING / 'color-analysis-20260929/original-current-colors.json'
GRAMS = {Path(r['file']).name: r['objects'] for r in json.loads((HERE / 'object_grams.json').read_text())}

plan_quote = next(l for l in PLAN.read_text().splitlines() if l.startswith('Keep original plate 1 orange'))[:63]
stock_colour, stock_src = {}, {}
for pl in json.loads(ORIG.read_text())['current_plates']:
    if pl['plate'] in (1, 5):
        for o in pl['objects']:
            stock_colour[o['name']] = 'Orange' if pl['plate'] == 1 else 'Black'
            stock_src[o['name']] = (f'{PLAN.relative_to(PRINT.parents[2])}: "{plan_quote}"; {o["name"]} is on original '
                                    f'plate {pl["plate"]} ({ORIG.name} current_plates)')
for g, v in json.loads(LAYOUT.read_text())['groups'].items():
    for plate in v['placements']:
        for r in plate:
            n = Path(r['record']['source']).name
            stock_colour[n] = g.capitalize()
            stock_src[n] = f'{LAYOUT.relative_to(PRINT.parents[2])}: groups.{g} placements include "{n}"'


def gram(gfile, prefix):
    for k, v in GRAMS.get(gfile, {}).items():
        if k.startswith(prefix):
            return v
    return None


P1 = 'MicroDuck_Elegoo_plate_1.gcode'
OR4 = 'MicroDuck_Elegoo_orange_FLAT.gcode'
YE4 = 'MicroDuck_yellow.gcode'


def stock(key, name, f, mjcf, visible, gfile=None):
    return {'key': key, 'name': name, 'colour': stock_colour[f], 'origin': 'stock print, 10/1 batch', 'file': f,
            'mjcfMesh': mjcf, 'visible': visible, 'source': stock_src[f],
            'grams': gram(gfile, f) if gfile else None, 'gramsSource': gfile}


def release(rows, key, name, mjcf_or_world, visible, gfile=None, gprefix=None, installed=True, note=None):
    path = PRINT / rows
    data = json.loads(path.read_text())
    items = data['parts'] if isinstance(data, dict) else data
    row = next(r for r in items if r['key'] == key)
    rec = {'key': key, 'name': name, 'colour': row['color'], 'origin': rows.split('/')[0], 'render': mjcf_or_world,
           'visible': visible, 'installed': installed,
           'source': f'guide/print/{rows}: key "{key}", "color": "{row["color"]}"',
           'grams': gram(gfile, gprefix or key) if gfile else None, 'gramsSource': gfile}
    if note:
        rec['note'] = note
    return rec


V18 = 'zhengxia_V1.8_{}_Elegoo-Centauri-Carbon_{}.gcode'
parts = [
    # torso
    stock('shell_left', 'Left torso side shell', 'community-8.stl', 'left_shell', 'large: whole left side of the torso', OR4),
    stock('shell_right', 'Right torso side shell', 'community-10.stl', 'right_shell', 'large: whole right side of the torso', OR4),
    stock('torso_base', 'Torso base plate', 'community-34.stl', 'trunk_base', 'underside and between the hips'),
    stock('pcb_locker', 'Torso cross piece (banana_pcb_locker)', 'community-26.stl', 'banana_pcb_locker', 'small, top rear of torso'),
    release('release-V1.8/scripts/rows.json', 'rear_pack', 'Rear electronics pack (V1.8)', 'world/rear_pack.stl',
            'back of the torso, under the box', V18.format('Orange', '3h28m'), 'rear_pack',
            note='V1.9 pack (release-V1.9 rows.json, Orange) supersedes it with the same colour; v20-source/README.md says the robot keeps the V1.9 rear pack.'),
    release('release-V1.8/scripts/rows.json', 'rear_pack_cover', 'Rear pack cover (V1.8)', 'not rendered (replaced by the box)',
            'back face of the pack today', V18.format('Black', '44m'), 'rear_pack_cover',
            note='Retired by the V1.10/V1.11 rear converter box; installed until the box is printed and fitted.'),
    release('release-V1.11/scripts/rows.json', 'rear_frame', 'Rear converter box frame (layout F, V1.11)', 'world/rear_frame.stl',
            'large: whole back of the robot', installed=False,
            note='Released, not printed yet (memory microduck-build-state, 2026-10-14). Changing its colour costs nothing extra.'),
    release('release-V1.11/scripts/rows.json', 'rear_lid', 'Rear converter box lid (layout F, V1.11)', 'world/rear_lid.stl',
            'large: rear face', installed=False, note='Released, not printed yet.'),
    # legs (both sides)
    stock('hip_left', 'Left hip bracket', 'community-14.stl', 'hip_l', 'medium, top of left leg', P1),
    stock('hip_right', 'Right hip bracket', 'community-60.stl', 'hip_l (hip_l_2 body)', 'medium, top of right leg', OR4),
    stock('thigh_left', 'Left thigh body', 'community-74.stl', 'upper_leg_left', 'large: outer thigh', P1),
    stock('thigh_right', 'Right thigh body', 'community-72.stl', 'upper_leg_right', 'large: outer thigh', P1),
    stock('thigh_plate_left', 'Left thigh reinforcing plate', 'community-22.stl', 'upper_leg_rigidity_plate', 'inner thigh'),
    stock('thigh_plate_right', 'Right thigh reinforcing plate', 'community-20.stl', 'upper_leg_rigidity_plate', 'inner thigh'),
    stock('lower_left', 'Left lower-leg link', 'community-30.stl', 'leg', 'shin'),
    stock('lower_right', 'Right lower-leg link', 'community-32.stl', 'leg', 'shin'),
    stock('ankle_left', 'Left ankle bracket', 'community-66.stl', 'ankle_left', 'medium, ankle', P1),
    stock('ankle_right', 'Right ankle bracket', 'community-64.stl', 'ankle_right', 'medium, ankle', P1),
    stock('foot_left', 'Left foot', 'community-44.stl', 'foot_left (+ sole_left)', 'large: foot', YE4),
    stock('foot_right', 'Right foot', 'community-46.stl', 'foot_right (+ sole_right)', 'large: foot', YE4),
    stock('yaw_left', 'Left yaw-to-roll link', 'community-36.stl', 'yaw2roll', 'hip, between torso and thigh'),
    stock('yaw_right', 'Right yaw-to-roll link', 'community-38.stl', 'yaw2roll', 'hip'),
    stock('roll_left', 'Left roll support plate', 'community-50.stl', 'bearing_roll', 'hip'),
    stock('roll_right', 'Right roll support plate', 'community-51.stl', 'bearing_roll', 'hip'),
    stock('rings', '22 mm sliding rings (all joints)', 'community-53.stl', 'seeed_bearing__configuration__22x16x4', 'small rings at joints'),
    stock('ankle_rings', '14.6 mm ankle rings', 'community-62.stl', 'seeed_bearing__configuration_default', 'small'),
    # neck
    stock('neck_link_a', 'Neck side link A', 'community-16.stl', 'neck', 'thin plate on the neck side', P1),
    stock('neck_link_b', 'Neck side link B', 'community-18.stl', 'neck', 'thin plate on the neck side', OR4),
    release('release-V1.6-final/final-V1.6.json', 'neck_pitch_integrated_1mm_seats', 'Head-pitch bracket (V1.6)', 'neck_pitch', 'neck'),
    stock('head_yaw_link', 'Head yaw-to-roll link', 'community-70.stl', 'yaw_roll_motion', 'under the head'),
    stock('idlers', 'Printed idler horns and caps', 'community-55.stl', 'not in the MJCF', 'small'),
    release('release-V1.8/scripts/rows.json', 'neck_pitch_ring', 'Head-pitch sliding ring (V1.8)', 'world/neck_pitch_ring.stl', 'small',
            V18.format('Black', '44m'), 'neck_pitch_ring'),
    # head
    release('release-V1.9/scripts/rows.json', 'head_cap_v19', 'Head cap (V1.9)', 'world/head_cap.stl', 'large: whole top and back of the head',
            'zhengxia_V1.9_Orange_Elegoo-Centauri-Carbon_3h56m.gcode', 'head_cap_v19',
            note='V1.8 cap (release-V1.8 rows.json head_cap, Orange, 42.44 g) is the same colour; v20-source/README.md says the robot keeps the V1.9 cap.'),
    release('release-V1.8/scripts/rows.json', 'head_bottom', 'Lower head shell with the upper beak (V1.8)', 'world/head_bottom.stl',
            'large: upper beak and head underside', V18.format('Yellow', '2h56m'), 'head_bottom'),
    release('release-V1.8/scripts/rows.json', 'jaw_frame', 'Jaw frame with the lower lip (V1.8)', 'world/jaw_frame.stl',
            'large: lower beak', V18.format('Yellow', '2h56m'), 'jaw_frame'),
    release('release-V1.8/scripts/rows.json', 'face_panel', 'Face panel (V1.8)', 'world/face_panel.stl',
            'large: the flat face around the eye; the only white part', V18.format('White', '10m'), 'face_panel'),
    release('release-V1.8/scripts/rows.json', 'eye_trim', 'Eye trim ring (V1.8)', 'world/eye_trim.stl', 'medium: ring around the camera eye',
            V18.format('Black', '44m'), 'eye_trim'),
    release('release-V1.6-final/final-V1.6.json', 'jaw_support_original', 'Jaw support (V1.6)', 'motor_support', 'inside the head'),
    release('release-V1.6-final/final-V1.6.json', 'mouth_sliding_ring', 'Mouth sliding ring (V1.6)', 'not rendered', 'inside the beak hinge'),
    release('release-V1.9/scripts/rows.json', 'speaker_retainer_v19', 'Speaker retainer (V1.9)', 'not rendered', 'inside the cap',
            installed=False, note='Printed, not installed (memory microduck-build-state 2026-10-14).'),
    release('release-V1.9/scripts/rows.json', 'clip_torso_v19', 'Neck-bundle wire clips x4 (V1.9)', 'not rendered', 'small',
            installed=False, note='Printed, not installed. Same for clip_bracket/clip_head/clip_cap_v19, all Orange.'),
]
non_printed = [
    {'key': 'servos', 'name': '15 x ROBOTIS XL330 servos', 'colour': 'Black (dark grey case)', 'mjcfMesh': 'xl330',
     'source': 'purchased; the guide part colour for motors is a dark grey; ROBOTIS XL330 cases are black plastic',
     'visible': 'large: every joint, hip and neck; the biggest dark area on the robot'},
    {'key': 'openrb', 'name': 'OpenRB-150', 'colour': 'PCB (rendered blue-green)', 'render': 'world/openrb-board-upright.stl',
     'source': 'build_guide_data.py openrb_board color #2d6fb5', 'visible': 'inside the pack'},
    {'key': 'xl4015', 'name': 'Two ROBOTIS kit XL4015 converters', 'colour': 'blue PCB', 'render': 'back-plate/layout-F render STLs',
     'source': 'layout-F/render_spec_final.json rgba [0.12, 0.3, 0.9]', 'visible': 'through the box windows'},
    {'key': 'pd5991', 'name': 'Adafruit 5991 USB-C PD trigger', 'colour': 'black PCB', 'render': 'layout-F/pd5991_F-world.stl',
     'source': 'layout-F/render_spec_final.json rgba [0.03, 0.03, 0.03]', 'visible': 'bottom of the box'},
    {'key': 'camera', 'name': 'Camera Module 3 Wide', 'colour': 'green PCB, black lens', 'render': 'world/camera_board.stl',
     'source': 'purchased', 'visible': 'the lens shows as the pupil of the eye'},
    {'key': 'pi', 'name': 'Pi Zero W, IMU, speaker, wires', 'colour': 'electronics', 'source': 'purchased', 'visible': 'hidden inside'},
]
out = {
    'checked': '2026-10-14',
    'scope': 'Actual printed colour of every visible part on the robot as built (V1.8 printed set + V1.9 Orange plate on the 10/1 stock), '
             'plus the released, not yet printed V1.11 rear converter box. The guide viewer colours are display colours and are not used.',
    'colourCount': {c: sorted(p['key'] for p in parts if p['colour'] == c) for c in ('Orange', 'Yellow', 'White', 'Black')},
    'parts': parts,
    'nonPrinted': non_printed,
    'filamentOnHand': 'Not recorded in any parts sheet, manifest or memory file. Shawn prints at the club, loading one spool per plate; '
                      'every release since V1.4 used all four colours (Orange, Yellow, White, Black), so all four exist there; '
                      'quantities are unknown.',
}
(HERE / 'colour_as_built.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
print(json.dumps(out['colourCount'], indent=1))
