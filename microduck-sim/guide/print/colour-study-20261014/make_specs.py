"""Write the render specs for the colour options (spec-A.json ... spec-D.json).
    python3 make_specs.py
A as built (colour_as_built.json); B side shells and thighs white; C white upper body (shells, thighs, head cap);
D as built with a white head cap only; E white shells and head cap with the legs as built (the V2.0 reprint set)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRINT = HERE.parent
W = PRINT / 'world'
F = PRINT / 'back-plate/layout-F'
# PLA swatches (sRGB 0..1); the printed colour names come from colour_as_built.json
C = {'Orange': [0.95, 0.45, 0.06, 1], 'Yellow': [1.0, 0.80, 0.10, 1], 'White': [0.93, 0.93, 0.91, 1],
     'Black': [0.11, 0.11, 0.12, 1], 'Servo': [0.17, 0.17, 0.18, 1]}

AS_BUILT = {  # part group -> printed colour (colour_as_built.json)
    'shells': 'Orange', 'thighs': 'Orange', 'hips': 'Orange', 'ankles': 'Orange', 'neck_links': 'Orange',
    'feet': 'Yellow', 'structure': 'Black', 'pack': 'Orange', 'box': 'Orange',
    'head_cap': 'Orange', 'beak': 'Yellow', 'face': 'White', 'eye_trim': 'Black'}
OPTIONS = {
    'A': ('A  as built', {}),
    'B': ('B  white shells + thighs', {'shells': 'White', 'thighs': 'White'}),
    'C': ('C  white upper body + head cap', {'shells': 'White', 'thighs': 'White', 'head_cap': 'White'}),
    'D': ('D  as built + white head cap', {'head_cap': 'White'}),
    'E': ('E  white shells + head cap, legs as built', {'shells': 'White', 'head_cap': 'White'}),
}
MJCF = {  # community MJCF mesh -> part group
    'left_shell': 'shells', 'right_shell': 'shells', 'upper_leg_left': 'thighs', 'upper_leg_right': 'thighs',
    'hip_l': 'hips', 'ankle_left': 'ankles', 'ankle_right': 'ankles', 'neck': 'neck_links',
    'foot_left': 'feet', 'foot_right': 'feet', 'sole_left': 'feet', 'sole_right': 'feet',
    'trunk_base': 'structure', 'banana_pcb_locker': 'structure', 'upper_leg_rigidity_plate': 'structure', 'leg': 'structure',
    'yaw2roll': 'structure', 'bearing_roll': 'structure', 'neck_pitch': 'structure', 'yaw_roll_motion': 'structure',
    'motor_support': 'structure', 'seeed_bearing__configuration__22x16x4': 'structure',
    'seeed_bearing__configuration_default': 'structure'}
HIDE = ['power_support', 'np_f970',  # placeholders render_scene.py meant to drop (its geoms are unnamed)
        'top_head_shell', 'bottom_head_shell', 'jaw', 'face_part', 'noenoeil', 'lens', 'm12_lens_holder', 'soft_mouth_top',
        'jaw_soft', 'speaker', 'elec_rpi_robot_hat_pcb', 'pcb__raspberry_pi_zero_2_w']
HEAD = [('head_cap.stl', 'head_cap'), ('head_bottom.stl', 'beak'), ('jaw_frame.stl', 'beak'), ('face_panel.stl', 'face'),
        ('eye_trim.stl', 'eye_trim')]
VIEWS = [['front34', 150, -12, 0.56, [5, 0, -20]], ['rear34', -35, -12, 0.56, [-10, 0, -20]], ['side', 90, -4, 0.56, [0, 0, -20]]]

for key, (label, change) in OPTIONS.items():
    col = dict(AS_BUILT, **change)
    meshes = [[str(W / f), C[col[g]], f.split('.')[0], 'jaw_soft'] for f, g in HEAD]
    meshes += [[str(W / 'camera_board.stl'), [0.12, 0.3, 0.22, 1], 'camera', 'jaw_soft'],
               [str(W / 'neck_pitch_ring.stl'), C['Black'], 'neck_ring', 'neck_pitch'],
               [str(W / 'rear_pack.stl'), C[col['pack']], 'pack'],
               [str(W / 'rear_frame.stl'), C[col['box']], 'frame'],
               [str(W / 'rear_lid.stl'), C[col['box']], 'lid'],
               [str(W / 'openrb-board-upright.stl'), [0.15, 0.35, 0.2, 1], 'orb'],
               [str(F / 'xl4015_top_7V_render.stl'), [0.12, 0.3, 0.9, 1], 'b0'],
               [str(F / 'xl4015_mid_5V_render.stl'), [0.12, 0.3, 0.9, 1], 'b1'],
               [str(F / 'pd5991_F-world.stl'), [0.03, 0.03, 0.03, 1], 'pd']]
    recolor = {mesh: C[col[g]] for mesh, g in MJCF.items()}
    recolor['xl330'] = C['Servo']
    spec = {'out': str(HERE / 'renders'), 'prefix': key, 'label': label, 'colours': col, 'views': VIEWS, 'size': 700,
            'meshes': meshes, 'recolor': recolor, 'hideMeshes': HIDE}
    (HERE / f'spec-{key}.json').write_text(json.dumps(spec, indent=1) + '\n')
print('ok', list(OPTIONS))
