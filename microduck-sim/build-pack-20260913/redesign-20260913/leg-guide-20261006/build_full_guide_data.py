"""Export installed MicroDuck geometry and auditable, ordered assembly operations.

Reads the accepted left leg without rebuilding it. Community prints are native
3MF meshes; current additions use their assembly/body STLs. Supplier envelopes
are labeled separately. This program never changes CAD or printer files.
"""
from pathlib import Path
import base64
import collections
import copy
import hashlib
import itertools
import json
import re
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

OUT = Path(__file__).resolve().parent
REDESIGN = OUT.parent
SIM = OUT.parents[2]
ASSEMBLY = SIM / 'build-pack-20260913/assembly'
OLD = SIM / 'hardware-design-20260912/whole-robot-20260912'
sys.path.insert(0, str(OLD / 'assembly'))
from assembly_fk import fk, raw, XML

SOURCE_NS = {'__file__': str(ASSEMBLY / 'prepare_geometry.py')}
exec((ASSEMBLY / 'prepare_geometry.py').read_text().split('rows=[]')[0], SOURCE_NS)
INVENTORY = {r['id']: r for r in json.loads((ASSEMBLY / 'community-print-inventory.json').read_text())['objects']}
REFINED = {r['id']: r for r in json.loads((ASSEMBLY / 'source-surface-refinement.json').read_text())}
BODIES, GEOMS = fk()
COLORS = {'Orange': '#ff8000', 'Black': '#202020', 'Yellow': '#ffff00', 'White': '#f4f4ef',
          'Motor': '#40454b', 'Metal': '#b7c4d0', 'Electronics': '#3d7268'}
MOTOR_ROLES = {1: 'Right ankle pitch', 2: 'Right knee pitch', 3: 'Right hip pitch', 4: 'Right hip roll', 5: 'Right hip yaw',
               6: 'Left ankle pitch', 7: 'Left knee pitch', 8: 'Left hip pitch', 9: 'Left hip roll', 10: 'Left hip yaw',
               11: 'Head pitch', 12: 'Neck pitch', 13: 'Head yaw', 14: 'Head roll', 15: 'Jaw'}
MOTOR_FRAMES = {1: ('leg_2', 0), 2: ('upper_leg_right', 0), 3: ('upper_leg_right', 4),
                4: ('bearing_roll', 1), 5: ('trunk_base', 9), 6: ('leg', 2),
                7: ('upper_leg_left', 1), 8: ('upper_leg_left', 4), 9: ('yaw2roll', 1),
                10: ('trunk_base', 4), 11: ('neck', 2), 12: ('neck', 1),
                13: ('yaw_roll_motion', 1), 14: ('jaw_soft', 7), 15: ('jaw_soft', 2)}
COLOR_SOURCE = SIM / 'team-share-20261001/02-STL-and-Editable-Projects/STL-Instance-Manifest.json'
STOCK = json.loads(COLOR_SOURCE.read_text())['instances']
GROUP_COLOR = {'old-orange-plate1': 'Orange', 'orange': 'Orange', 'old-black-plate5': 'Black',
               'black': 'Black', 'yellow': 'Yellow', 'WHITE': 'White'}
SOURCE_HASHES = {}
def tracked(path):
    path = Path(path)
    SOURCE_HASHES[str(path.relative_to(SIM))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path

def geom(body, mesh, index=None):
    return next(g for g in GEOMS if g['body'] == body and g['mesh'] == mesh and (index is None or g['index'] == index))

def decode(p):
    return trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']), dtype='<f4').reshape(-1, 3),
                          np.frombuffer(base64.b64decode(p['indexB64']), dtype='<u4').reshape(-1, 3), process=False)

LEFT = json.loads(tracked(OUT / 'leg-data.json').read_text())
PARTS = copy.deepcopy(LEFT['parts'])
for p in PARTS:
    p['moduleId'] = 'left-leg'
    p['geometryKind'] = p.get('geometryKind', 'manufacturer-cad' if p['key'].startswith('motor') else 'community-print')
    p['approachVector'] = [0, 28, 0]
    if p['sourceId']:
        p['stockFileName'] = f"community-{p['sourceId']}.stl"
    if p['key'].startswith('washer'):
        p['partKind'] = 'fastener'
    elif p['key'].startswith('motor'):
        p['partKind'] = 'motor'
    else:
        p['partKind'] = 'print'

def color_for(print_name, preferred=None):
    matches = [r for r in STOCK if Path(r['file']).name.split('_', 1)[1] == print_name]
    available = {GROUP_COLOR[r['reference_group']] for r in matches}
    if not available:
        raise ValueError(f'Missing recorded print color: {print_name}')
    if preferred:
        assert preferred in available, (print_name, preferred, available)
        return preferred
    assert len(available) == 1, (print_name, available)
    return available.pop()

def add_mesh(key, name, mesh, body, matrix, module, color, desc, aliases='', source_id=None,
             reference='', index=0, geometry_kind='community-print', print_name=None, source_path=None):
    assert key not in {p['key'] for p in PARTS}, key
    pos = np.asarray(mesh.vertices, dtype='<f4')
    faces = np.asarray(mesh.faces, dtype='<u4')
    p = dict(key=key, name=name, color=COLORS[color], colorName=color, sourceId=source_id,
             sourceName=INVENTORY[source_id]['source_name'] if source_id else name,
             body=body, referenceMesh=reference, index=index, stage=0, moduleId=module,
             description=desc, aliases=aliases, bounds=mesh.bounds.tolist(), center=mesh.bounds.mean(0).tolist(),
             dimensions=np.sort(mesh.extents)[::-1].round(1).tolist(), triangles=len(mesh.faces),
             positionB64=base64.b64encode(pos.tobytes()).decode(), indexB64=base64.b64encode(faces.tobytes()).decode(),
             sourceTransformWorld=np.asarray(matrix).tolist(), geometryKind=geometry_kind,
             approachVector=[0, -28, 0] if module == 'right-leg' else [28, 0, 0],
             partKind='print' if print_name else 'motor' if reference == 'xl330' else 'electronics')
    if print_name:
        p['stockFileName'] = print_name
    if source_path:
        p['sourceFile'] = str(tracked(source_path).relative_to(SIM))
    PARTS.append(p)
    return p

def source_matrix(oid):
    r = REFINED.get(oid, INVENTORY[oid])
    t = np.eye(4)
    t[:3, :3] = r.get('rotation', r.get('source_to_reference_rotation'))
    t[:3, 3] = r.get('translation', r.get('source_to_reference_translation_mm'))
    return t

def add_community(key, name, oid, body, ref, module, desc, index=None, matrix=None, preferred=None):
    g = geom(body, ref, index)
    t = np.asarray(matrix) if matrix is not None else g['world'] @ source_matrix(oid)
    m = SOURCE_NS['mesh']('3D/3dmodel.model', str(oid)).apply_transform(t)
    return add_mesh(key, name, m, body, t, module, color_for(f'community-{oid}.stl', preferred), desc,
                    f"{oid} · {INVENTORY[oid]['source_name']}", oid, ref, g['index'], print_name=f'community-{oid}.stl')

def match_rigid(source, target):
    """Discrete native-axis registration; preserve source geometry and handedness."""
    tree = cKDTree(target.vertices)
    candidates = []
    for rotation in SOURCE_NS['rot']:
        vertices = source.vertices @ rotation.T
        shift = target.bounds.mean(0) - (vertices.min(0) + vertices.max(0)) / 2
        distances = tree.query(vertices + shift)[0]
        candidates.append((float(np.quantile(distances, .95)), rotation, shift))
    error, rotation, shift = min(candidates, key=lambda x: x[0])
    t = np.eye(4); t[:3, :3] = rotation; t[:3, 3] = shift
    return t, error

LEFT_BY_KEY = {p['key']: p for p in LEFT['parts']}
MOTOR_NATIVE = decode(LEFT_BY_KEY['motor8']).apply_transform(np.linalg.inv(LEFT_BY_KEY['motor8']['sourceTransformWorld']))
def add_motor(sid, module):
    body, index = MOTOR_FRAMES[sid]
    g = geom(body, 'xl330', index)
    return add_mesh(f'motor{sid}', f'XL330 · ID{sid} · {MOTOR_ROLES[sid]}', MOTOR_NATIVE.copy().apply_transform(g['world']),
                    body, g['world'], module, 'Motor',
                    'Manufacturer XL330-M288-T geometry. ID is a planned MicroDuck label; read and set each actual motor separately with torque disabled.',
                    f'XL330-M288-T · planned ID{sid}', reference='xl330', index=index, geometry_kind='manufacturer-cad')

# The right leg uses its own native opposite-hand components and real FK frames.
add_community('right_thigh', 'Right thigh body', 72, 'upper_leg_right', 'upper_leg_right', 'right-leg', 'Orange open frame with two motor seats; right-hand version.')
add_community('right_plate', 'Right thigh reinforcing plate', 20, 'upper_leg_right', 'upper_leg_rigidity_plate', 'right-leg', 'Thin black plate spanning the stationary case corners of ID2 and ID3.')
add_community('right_lower', 'Right lower-leg link', 32, 'leg_2', 'leg', 'right-leg', 'Long black stepped link between the knee and ankle axes.')
right_ankle = add_community('right_ankle', 'Right ankle bracket', 64, 'ankle_right', 'ankle_right', 'right-leg', 'Orange compact fork, source64; opposite version of source66.')
mirror = np.eye(4); mirror[1, 1] = -1
foot_target = decode(LEFT_BY_KEY['foot']).apply_transform(mirror)
foot_source = SOURCE_NS['mesh']('3D/3dmodel.model', '46')
right_foot_t, RIGHT_FOOT_ERROR = match_rigid(foot_source, foot_target)
foot_points, _ = trimesh.sample.sample_surface(foot_source.copy().apply_transform(right_foot_t), 2000, seed=31)
foot_surface_distances = trimesh.proximity.closest_point(foot_target, foot_points)[1]
RIGHT_FOOT_SURFACE_P95 = float(np.quantile(foot_surface_distances, .95))
RIGHT_FOOT_SURFACE_MAX = float(max(foot_surface_distances))
# Opposite-hand printed feet have small local feature differences and different
# tessellation. Their shared surfaces establish placement; retaining-hole rays
# below establish the screw interface independently, not by assumed symmetry.
assert RIGHT_FOOT_SURFACE_P95 < .005, RIGHT_FOOT_SURFACE_P95
add_community('right_foot', 'Right foot', 46, 'ankle_right', 'foot_right', 'right-leg', 'One combined broad yellow foot with its own raised pivot; native right-hand print.', matrix=right_foot_t)
add_community('right_hip', 'Right hip bracket', 60, 'hip_l_2', 'hip_l', 'right-leg', 'Orange bridge joining perpendicular ID4 and ID3 outputs.')
add_community('right_yaw', 'Right yaw-to-roll link', 38, 'bearing_roll', 'yaw2roll', 'right-leg', 'Short angled black link with an integrated rear retainer.')
add_community('right_passive', 'Right roll support plate', 51, 'bearing_roll', 'bearing_roll', 'right-leg', 'Tall narrow black plate closing the opposite side of the hip-roll motor case.')
for key, body, idx, sid in [('ring2', 'upper_leg_right', 1, 2), ('ring3', 'hip_l_2', 2, 3), ('ring4', 'bearing_roll', 3, 4)]:
    add_community(key, f'22 mm sliding ring · ID{sid}', 53, body, 'seeed_bearing__configuration__22x16x4', 'right-leg', 'Black printed annular support; source53 represents identical copied stock.', index=idx)
ring_target = decode(LEFT_BY_KEY['smallring']).apply_transform(mirror)
ring_source = SOURCE_NS['mesh']('3D/3dmodel.model', '68')
right_ring_t, RIGHT_RING_ERROR = match_rigid(ring_source, ring_target)
assert RIGHT_RING_ERROR < .01, RIGHT_RING_ERROR
add_community('right_smallring', 'Right 14.6 mm ankle ring', 68, 'ankle_right', 'seeed_bearing__configuration_default', 'right-leg',
              'Single printed sleeve. Inner fit on the lower-link boss is tight; ankle rotation occurs at its outside and the orange pocket, subject to real dry-fit.', matrix=right_ring_t)
for sid in range(1, 6): add_motor(sid, 'right-leg')

# Fixed torso and current replacements. Body STLs already use body coordinates.
add_community('torso_base', 'Torso base plate', 34, 'trunk_base', 'trunk_base', 'torso', 'Black flat base locating both hip-yaw motors.')
add_community('shell_left', 'Left torso shell', 8, 'trunk_base', 'left_shell', 'torso', 'Orange left side shell, including the neck-pitch output seat.')
add_community('shell_right', 'Right torso shell', 10, 'trunk_base', 'right_shell', 'torso', 'Orange right side shell, including the opposite neck-pitch support.')
for key, idx, sid in [('ring10_torso', 0, 10), ('ring5_torso', 11, 5)]:
    add_community(key, f'Torso sliding ring · ID{sid}', 53, 'trunk_base', 'seeed_bearing__configuration__22x16x4', 'torso', 'Black Ø22 printed support at the hip-yaw seat.', index=idx)

def add_file(key, name, assembly_file, body, module, desc, print_name=None, geometry_kind='current-print'):
    path = tracked(assembly_file)
    t = BODIES[body]
    m = trimesh.load(path, force='mesh').apply_transform(t)
    return add_mesh(key, name, m, body, t, module, color_for(print_name) if print_name else 'Electronics', desc,
                    print_name or name, reference=key, geometry_kind=geometry_kind, print_name=print_name, source_path=path)

add_file('power_support', 'Integrated power support', OLD / 'assembly/compact-battery/power-support-integrated-body.stl', 'trunk_base', 'torso',
         'Orange replacement for original source12, retaining original motor interfaces and the power-module cavity.', 'power-support-integrated-print.stl')
add_file('fuse_carrier', 'Eleven-fuse carrier', ASSEMBLY / 'service-mounts/fuse-bank-body.stl', 'trunk_base', 'power',
         'Black two-row carrier: five lower and six upper positions. Insulated leads are retained without crushing fuse bodies.', 'fuse-bank-print.stl')
add_file('regulator_insert', 'Open regulator insert', REDESIGN / 'regulator-open-insert-body.stl', 'trunk_base', 'power',
         'Black open frame for DFR1202, held at existing support-band positions. Insulating edge liner and removable narrow ties; no new screw holes.', 'regulator-open-insert-print.stl')
add_file('regulator', 'DFR1202 converter envelope', REDESIGN / 'dfr1202-envelope-body.stl', 'trunk_base', 'power',
         'Supplier installation envelope 8×26×30 mm. Component details are not modeled; actual ties must clear components and exposed pads.', geometry_kind='supplier-envelope')
add_file('imu_clamp', 'Torso IMU clamp', OLD / 'assembly/trunk-imu/imu_clamp_holder_body.stl', 'trunk_base', 'imu',
         'Orange holder that clamps to the fixed torso rails. Two pressure screws retain the holder; four separate cover screws retain its rear cover.', 'imu_clamp_holder_print.stl')
add_file('imu_cover', 'IMU rear cover', OLD / 'assembly/trunk-imu/imu_rear_cover_body.stl', 'trunk_base', 'imu',
         'Black thin cover, installed alone without the removed voltage-alarm carrier.', 'imu_rear_cover_print.stl')
add_file('imu_board', 'BNO085 installation envelope', OLD / 'assembly/trunk-imu/imu_28x25x8_envelope_body.stl', 'trunk_base', 'imu',
         '28×25×8 mm installation envelope. Record actual board orientation with the axis markings visible.', geometry_kind='supplier-envelope')

add_community('neck_link_a', 'Neck side link A', 16, 'neck', 'neck', 'neck', 'Orange thin side link for the two neck motors; source16.', index=0)
add_community('neck_link_b', 'Neck side link B', 18, 'neck', 'neck', 'neck', 'Orange opposing thin side link, source18. Its saved placement differs from link A.', index=3)
add_community('neck_pitch', 'Head-pitch bracket', 28, 'neck_pitch', 'neck_pitch', 'neck', 'Black cross bracket joining the two sides of ID11 and the head-yaw output.')
add_community('neck_pitch_ring', 'Head-pitch sliding ring', 53, 'neck_pitch', 'seeed_bearing__configuration__22x16x4', 'neck', 'Black Ø22 printed support at the head-yaw output.', index=1)
add_community('head_yaw_link', 'Head yaw-to-roll link', 70, 'yaw_roll_motion', 'yaw_roll_motion', 'neck', 'Black fork supporting the perpendicular head yaw/roll motors.')
for key, idx in [('head_roll_ring_a', 2), ('head_roll_ring_b', 3)]:
    add_community(key, 'Head-roll sliding support ring', 53, 'yaw_roll_motion', 'seeed_bearing__configuration__22x16x4', 'head', 'Black Ø22 support on the head-roll axis.', index=idx)
for sid in [11, 12, 13]: add_motor(sid, 'neck')

# Two neck idler/cap pairs use the actual printed sources. Manufacturer solids
# establish the rear-axis seat, rather than treating spare stock as installed.
import cadquery as cq
MOTOR_STEP = tracked(REDESIGN / 'fastener-audit/sources/X330_3d.stp')
shape = cq.importers.importStep(str(MOTOR_STEP)).val()
step_to_motor = np.array([[0, 0, -1, -8], [-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
IDLER_REGISTRATION = []
for oid, solid_index, keybase, name in [(55, 10, 'idler', 'Printed rear idler horn'), (59, 11, 'idler_cap', 'Printed rear idler cap')]:
    v, f = shape.Solids()[solid_index].tessellate(.08)
    reference = trimesh.Trimesh([[q.x, q.y, q.z] for q in v], f, process=False).apply_transform(step_to_motor)
    source = SOURCE_NS['mesh']('3D/3dmodel.model', str(oid))
    # Compare sampled surfaces because print/manufacturer tessellation differs.
    candidates = []
    points, _ = trimesh.sample.sample_surface(source, 500, seed=17)
    for rotation in SOURCE_NS['rot']:
        vertices = source.vertices @ rotation.T
        shift = reference.bounds.mean(0) - (vertices.min(0) + vertices.max(0)) / 2
        d = trimesh.proximity.closest_point(reference, points @ rotation.T + shift)[1]
        candidates.append((float(np.quantile(d, .95)), rotation, shift))
    error, rotation, shift = min(candidates, key=lambda x: x[0])
    assert error < .03, (oid, error)
    t = np.eye(4); t[:3, :3] = rotation; t[:3, 3] = shift
    IDLER_REGISTRATION.append({'sourceId': oid, 'manufacturerSolid': solid_index, 'surfaceP95Mm': error, 'sourceToMotor': t.tolist()})
    for sid in [11, 12]:
        body, idx = MOTOR_FRAMES[sid]; mt = geom(body, 'xl330', idx)['world'] @ t
        add_mesh(f'{keybase}{sid}', f'{name} · ID{sid}', source.copy().apply_transform(mt), body, mt, 'neck', 'Black',
                 'One of only two installed printed neck idler/cap pairs. Twelve additional printed pairs are stock allowances, not installed joints.',
                 f'Native source{oid}; choose a recorded black copy', oid, keybase, idx, print_name=f'community-{oid}.stl')

add_community('head_bottom', 'Bottom head shell', 2, 'jaw_soft', 'bottom_head_shell', 'head', 'Yellow lower shell with four support pilots and three cap-closure seats.')
add_community('face_panel', 'Front face panel', 76, 'jaw_soft', 'face_part', 'head', 'White face panel with the Pi pilot holes; Pi faces inward. Captured by matching head-shell rim.')
add_community('eye_trim', 'Eye trim', 48, 'jaw_soft', 'noenoeil', 'head', 'Black circular cosmetic trim. Dry-seat in the matching face-panel opening; this is not the camera mount.')
add_community('jaw_frame', 'Moving jaw frame', 4, 'jaw_soft', 'jaw', 'head', 'Yellow moving lower jaw frame with curved asymmetric output screw seats.')
add_community('upper_pad', 'Fixed upper lip pad', 40, 'jaw_soft', 'soft_mouth_top', 'head', 'White thin upper contact pad attached to the fixed shell. Do not bond across the jaw gap.')
add_community('lower_pad', 'Moving lower lip pad', 42, 'jaw_soft', 'jaw_soft', 'head', 'White lower contact pad that moves with the jaw frame.')
add_file('jaw_support', 'Coaxial jaw motor support', ASSEMBLY / 'mouth-support/motor-support-coaxial-assembly.stl', 'jaw_soft', 'head',
         'Black revised motor support. Integral 10.4 mm sliding seat replaces the old separate mouth ring.', 'motor-support-coaxial-print.stl')
for sid in [14, 15]: add_motor(sid, 'head')
HEAD_MANIFEST = OLD / 'electrical/head-layout/final/head-mesh-mass-manifest.json'
head_manifest = json.loads(tracked(HEAD_MANIFEST).read_text())
head_rows = {r['id']: r for r in head_manifest['pieces']}
add_file('head_cap', 'USB-service head cap', REDESIGN / 'head-cap-usb-service-body.stl', 'jaw_soft', 'electronics',
         'Orange current cap: jaw clearance, USB service window and restored third closure boss. Older cap is superseded.', 'head-cap-usb-service-print.stl')
for key, name, module, filename, desc in [
    ('audio_carrier', 'Audio carrier', 'electronics', 'audio_carrier_print.stl', 'Black slotted carrier for MAX98357A and speaker. Narrow ties through 2.4×1.2 mm slots; keep diaphragm free.'),
    ('camera_pitch_foot', 'Camera pitch foot', 'camera', 'camera_pitch_foot.stl', 'Black base attached to the cap with two shorter M3×10 screws.'),
    ('camera_cradle', 'Camera cradle', 'camera', 'camera_cradle.stl', 'Black camera cradle with four PCB mounting corners and one M3 tilt hinge.')]:
    add_file(key, name, head_rows[key]['mesh_file'], 'jaw_soft', module, desc, filename)
for key, source_key, name, kind in [('pi', 'pi_retained', 'Pi Zero board reference', 'form-factor-reference'),
                                  ('openrb', 'openrb', 'OpenRB-150 controller', 'manufacturer-cad'),
                                  ('camera_board', 'camera_module3_wide', 'Camera Module 3 Wide', 'manufacturer-installation-mesh'),
                                  ('amplifier', 'amp', 'MAX98357A envelope', 'supplier-envelope'),
                                  ('speaker', 'speaker', '8 Ω 1 W speaker envelope', 'supplier-envelope')]:
    module = 'camera' if key == 'camera_board' else 'electronics'
    add_file(key, name, head_rows[source_key]['mesh_file'], 'jaw_soft', module,
             'Installation geometry from the current head layout. Actual received board/form factor and plugs require fit checks.' if key == 'pi' else
             'Current installed electronics geometry. Supplier boxes represent fit envelopes rather than detailed component shapes.', geometry_kind=kind)

SCHEDULE = json.loads(tracked(REDESIGN / 'assembly-fasteners.json').read_text())
SCREWS = [copy.deepcopy(c) for c in SCHEDULE['connections'] if c.get('servo_ids')]
for c in SCREWS:
    sid = c['servo_ids'][0]
    c.update(partKey=f'motor{sid}', ownerLabel=f'Motor ID{sid} · {MOTOR_ROLES[sid]}', screwKind='motor-joint')
    original_left = next((r for r in LEFT['screws'] if r['id'] == c['id']), None)
    if original_left is not None:
        c['stage'] = original_left['stage']
    if c.get('washer_mm'):
        c['washerKey'] = f'washer{sid}'
SCREWS.append(copy.deepcopy(next(c for c in LEFT['screws'] if c['id'] == 'left-foot-retainer')))
SCREWS[-1].update(partKey='ankle', ownerLabel='Left ankle to foot', screwKind='print-joint')
right_foot_screw = copy.deepcopy(SCREWS[-1])
right_foot_screw.update(id='right-foot-retainer', component='Right ankle bracket to combined right foot', servo_ids=[1],
                        partKey='right_ankle', ownerLabel='Right ankle to foot', source_ids=[64, 46],
                        world_center_mm=(mirror @ np.r_[right_foot_screw['world_center_mm'], 1])[:3].tolist(),
                        world_axis=(mirror[:3, :3] @ right_foot_screw['world_axis']).tolist(),
                        evidence='Native right foot46 registered by a proper rigid transform to the opposite-hand target of accepted foot44; matching right ankle64 retaining axes are checked below. Length is conditional on the same measured pilot engagement; physical fit unverified.')
SCREWS.append(right_foot_screw)
E_PART = {'pi': 'pi', 'openrb': 'openrb', 'audio_carrier': 'audio_carrier', 'camera_pcb_10': 'camera_board',
          'camera_foot': 'camera_pitch_foot', 'camera_hinge': 'camera_cradle', 'head_cap_closure': 'head_cap',
          'motor_support_frame': 'jaw_support', 'fuse_carrier': 'fuse_carrier', 'imu_rear_cover': 'imu_cover', 'imu_clamp': 'imu_clamp'}
for group in SCHEDULE['connections']:
    if group.get('servo_ids'): continue
    transform = BODIES[group['coordinate_frame']]
    for i, point in enumerate(group['hole_centers_mm']):
        c = copy.deepcopy(group)
        c.update(id=f"E-{group['id']}-{i + 1:02d}", groupId=group['id'], quantity=1, category='mount', servo_ids=[],
                 length_mm=float(re.search(r' x (\d+)', group['spec'])[1]), partKey=E_PART[group['id']],
                 ownerLabel=group['component'], screwKind='electronics-mount',
                 world_center_mm=(transform @ np.r_[point, 1])[:3].tolist(),
                 world_axis=(-transform[:3, :3] @ np.array(group['axis'])).tolist(),
                 washer_mm=0, auditAxisMeaning='insertion; guide world_axis is outward')
        if group.get('nut_quantity'): c['nut_quantity'] = 1
        if group.get('washer_quantity'): c['washer_quantity'] = 2 if group['id'] == 'camera_hinge' else 1
        SCREWS.append(c)

for c in SCREWS:
    if c.get('washer_mm') and c['servo_ids'][0] in [1, 4]:
        sid = c['servo_ids'][0]
        m = trimesh.creation.annulus(r_min=1.35, r_max=2.5, height=.5, sections=64)
        direction = np.array(c['world_axis']); t = trimesh.geometry.align_vectors([0, 0, 1], direction)
        t[:3, 3] = np.array(c['world_center_mm']) + direction * .25
        p = add_mesh(f'washer{sid}', f'0.5 mm metal washer · ID{sid}', m.apply_transform(t), MOTOR_FRAMES[sid][0], t,
                     'right-leg', 'Metal', 'Metal washer directly under the rear-center screw head, outside the printed retainer: ID2.7, OD5, thickness0.5 mm.',
                     'DIN433 / ISO7092 M2.5', reference='specified_washer', geometry_kind='specified-fastener-envelope')
        p.update(fastenerId=c['id'], partKind='fastener')

# Electronics hardware uses the same nominal envelopes and seat locations as
# electronics_audit.py. Head-plane datum includes the head-side M3 washer.
E_MODULE = {'pi': 'electronics', 'openrb': 'electronics', 'audio_carrier': 'electronics',
            'camera_pcb_10': 'camera', 'camera_foot': 'camera', 'camera_hinge': 'camera',
            'head_cap_closure': 'head-close', 'motor_support_frame': 'head',
            'fuse_carrier': 'power', 'imu_rear_cover': 'imu', 'imu_clamp': 'imu'}
for c in SCREWS:
    if not c.get('groupId'): continue
    module_id = E_MODULE[c['groupId']]
    direction = np.array(c['world_axis']); head_point = np.array(c['world_center_mm'])
    body = 'trunk_base' if module_id in ['power', 'imu'] else 'jaw_soft'
    c['hardwareKeys'] = []
    if c.get('nut_quantity'):
        diameter = float(re.match(r'M([\d.]+)', c['spec'])[1])
        af, height = (4., 1.6) if diameter == 2 else (5.5, 2.4)
        mesh = trimesh.creation.cylinder(radius=af / np.sqrt(3), height=height, sections=6)
        hole = trimesh.creation.cylinder(radius=diameter / 2, height=height + 1, sections=64)
        mesh = trimesh.boolean.difference([mesh, hole], engine='manifold')
        if c['groupId'] == 'camera_pcb_10':
            # Match the real hex pockets: arbitrary zero-angle hexes intersect their walls.
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 6, [0,0,1]))
        t = trimesh.geometry.align_vectors([0, 0, 1], direction)
        distance = c['length_mm'] - c['tip_beyond_nut_mm'] - height / 2
        t[:3, 3] = head_point - direction * distance
        key = 'nut_' + c['id']
        p = add_mesh(key, f'M{diameter:g} nut · {c["component"]}', mesh.apply_transform(t), body, t, module_id, 'Metal',
                     f'Specified smooth hex-nut envelope: across flats {af:g} mm, height {height:g} mm. Thread details are not modeled.',
                     f'M{diameter:g} nut · AF{af:g} × {height:g}', reference='specified_nut', geometry_kind='specified-fastener-envelope')
        p.update(partKind='fastener', fastenerId=c['id'])
        c['nutKeys'] = [key]; c['hardwareKeys'].append(key)
    if c.get('washer_quantity'):
        distances = [.25] if c['groupId'] == 'camera_foot' else [.25, c['stack_mm']['ears_plus_gap'] + .75]
        c['washerKeys'] = []
        for i, distance in enumerate(distances):
            mesh = trimesh.creation.annulus(r_min=1.6, r_max=3.5, height=.5, sections=64)
            t = trimesh.geometry.align_vectors([0, 0, 1], direction)
            t[:3, 3] = head_point - direction * distance
            key = f'washer_{c["id"]}_{i + 1}'
            p = add_mesh(key, f'M3 washer · {"head" if i == 0 else "nut"} side', mesh.apply_transform(t), body, t, module_id, 'Metal',
                         'Specified M3 washer: ID3.2, OD7, thickness0.5 mm. At the hinge, one washer sits on each outside ear face.',
                         'Metal M3 washer · ID3.2 OD7 × 0.5', reference='specified_washer', geometry_kind='specified-fastener-envelope')
            p.update(partKind='fastener', fastenerId=c['id'])
            c['washerKeys'].append(key); c['hardwareKeys'].append(key)
        c['washerKey'] = c['washerKeys'][0]

def ids(sids=None, category=None, group=None):
    return [c['id'] for c in SCREWS if (sids is None or c.get('servo_ids') and c['servo_ids'][0] in sids)
            and (category is None or c['category'] in category)
            and (group is None or c.get('groupId') in group)]

MODULES = []
def module(mid, title, prerequisites=None, checks=None):
    row = dict(id=mid, title=title, operations=[], prerequisites=prerequisites or [], checks=checks or [])
    MODULES.append(row)
    return row
def operation(mod, kind, title, add=None, screws=None, text='', highlight=None, retention=None):
    hardware = [key for sid in (screws or []) for key in next(c for c in SCREWS if c['id'] == sid).get('hardwareKeys', [])]
    mod['operations'].append(dict(id=f"{mod['id']}-{len(mod['operations']) + 1:02d}", kind=kind,
                                  title=title, add=(add or []) + hardware, screwIds=screws or [], text=text,
                                  highlightKeys=highlight or add or [], retentionNotes=retention or []))
def place(mod, title, add, text, highlight=None): operation(mod, 'place', title, add, text=text, highlight=highlight)
def fasten(mod, title, screws, text, add=None, retention=None): operation(mod, 'fasten', title, add, screws, text, retention=retention)

def leg_operations(right=False):
    offset = -5 if right else 0
    k = (lambda key: 'right_' + key if key not in ['ring7', 'ring8', 'ring9'] else 'ring' + str(int(key[4:]) - 5)) if right else lambda key: key
    a, knee, hp, roll, yaw = [s + offset for s in [6, 7, 8, 9, 10]]
    mod = module('right-leg' if right else 'left-leg', 'Right leg · IDs1–5' if right else 'Left leg · IDs6–10',
                 checks=['Torque off: align shafts and dry-fit each joint before final tightening.',
                         'Ring outside must permit rotation against its orange pocket; tight CAD inner fit can expand the sleeve.',
                         'No separate rear idler/cap pairs at these leg joints. Four ID5/ID10 torso case screws are in the torso module.'])
    side = 'RIGHT' if right else 'LEFT'
    place(mod, 'Seat the thigh motors and reinforcing plate', [k('thigh'), f'motor{knee}', f'motor{hp}', k('plate')], f'Use the {side} orange thigh and black 1 mm plate. Seat both motors; planned labels are not verified motor addresses.')
    mod['operations'][-1].update(partApproachVectors={k('thigh'): [0,0,0], f'motor{knee}': [0,45 if right else -45,0], f'motor{hp}': [0,45 if right else -45,0], k('plate'): [0,45 if right else -45,0]})
    fasten(mod, 'Fasten four case corners', ids([knee, hp], ['case']), 'Two M2×8 TAP case screws per motor, four total. Match stationary case holes; do not drill solid locating pegs.')
    place(mod, 'Place the knee support ring', [k('ring7')], 'Seat the black Ø22×4 support ring at the opposite knee support.')
    mod['operations'][-1].update(partApproachVectors={k('ring7'): [0,45 if right else -45,0]})
    fasten(mod, 'Retain both thigh rear centers', ids([knee, hp], ['rear_center']), 'One M2.6×6 TAP rear-center retainer per motor; no washer at these two centers.')
    place(mod, 'Prepare the ankle as a loose bench subassembly', [k('ankle'), k('smallring'), f'motor{a}'],
          f'Use the {side} ankle off the knee. First seat the sleeve from inside the empty fork into its passive pocket, then bring the bare motor into the open fork from above. Keep the lower link and all case/output screws off for these two partial approaches. Do not push the sleeve through the smaller outside lip.')
    mod['operations'][-1].update(partApproachVectors={k('ankle'): [0, 0, 0], k('smallring'): [0, -10 if right else 10, 0], f'motor{a}': [0, 0, 30]},
                                  assemblyPathIds=[('right-' if right else '') + s for s in ['ring-inside-pocket', 'bare-motor-into-open-fork']],
                                  isolatedPartKeys=[k('ankle'), k('smallring'), f'motor{a}'],
                                  assemblyPathStatus='source-contact-fit-check' if right else 'sampled-clear-partial',
                                  assemblyPathScope='Right sleeve entry is sampled clear; the right bare motor has a 0.00093 mm nominal mating-face overlap and does not pass the strict volume threshold. This is an illustrative approach requiring actual fit checks.' if right else
                                  'Two sampled partial paths in an isolated bench ankle; complete link closure and actual print fit are not validated.')
    if right:
        mod['operations'][-1]['text'] += ' The native right motor has a 0.00093 mm mating-face overlap; its strict zero-intersection test did not pass. The motor approach is a reference illustration, not a collision-free certificate. Confirm the actual printed fit.'
    fasten(mod, 'Hold the sleeve and motor loose; do not install screws yet', [],
           'Check that the sleeve is at the passive pocket shoulder and the bare motor is seated. No screws are installed in this holding/check operation; keeping the case untrapped preserves access for the link fit.',
           retention=['Keep the subassembly supported on the bench. Do not fasten its output or case before the following fit checkpoint.'])
    mod['operations'][-1]['isolatedPartKeys'] = [k('ankle'), k('smallring'), f'motor{a}']
    place(mod, 'Dry-fit the lower link and sleeve/boss closure', [k('lower')],
          'Fit the lower link, locating pegs and boss to the loose ankle/motor subassembly. The source Ø10 boss overlaps the Ø9.65 sleeve bore, so this closure needs actual printed fit/compliance evidence. No rigid sliding path is demonstrated. Stop if it cannot seat without forcing or damage; do not use screws to pull it through the sleeve.')
    mod['operations'][-1].update(animationBlockedReason='Physical fit checkpoint: untouched boss/sleeve geometry overlaps in the nominal source pose (left measured overlap 14.9586 mm³). Complete rigid closure has not been validated; show the target for inspection without an animated path through solids.',
                                  assemblyPathStatus='physical-check-required', requiresPhysicalFit=True,
                                  isolatedPartKeys=[k('ankle'), k('smallring'), f'motor{a}', k('lower')])
    fasten(mod, 'After the fit checkpoint, fasten ankle case, rear and output', ids([a], ['case', 'rear_center', 'horn']),
           'Only after full passive-side seating and alignment: two M2×10 TAP case screws, one M2.6×8 TAP rear-center with one 0.5 mm metal washer, and four M2×4 TAP output screws. Rear stack: head → washer → printed shoulder → motor rear pilot. Start loosely, seat evenly, then hand-snug.', [f'washer{a}'])
    mod['operations'][-1].update(conditionalOnPreviousPhysicalFit=True,
                                  isolatedPartKeys=[k('ankle'), k('smallring'), f'motor{a}', k('lower'), f'washer{a}'])
    place(mod, 'Bring the fitted lower/ankle module to the knee', [], 'After the ankle fit checkpoint and scheduled fasteners, bring the completed lower-link subassembly to the moving knee output and opposite support seat.',
          highlight=[k('lower'), k('ankle'), k('smallring'), f'motor{a}'])
    mod['operations'][-1].update(moveKeys=[k('lower'), k('ankle'), k('smallring'), f'motor{a}', f'washer{a}'], approachVector=[0, 28 if right else -28, 0],
                                  conditionalOnPreviousPhysicalFit=True)
    fasten(mod, 'Fasten the knee output', ids([knee], ['horn']), 'Four M2×5 TAP; the audited stack gives 2.2 mm entry. M2×6 exceeds the 3 mm manufacturer output limit.')
    place(mod, 'Seat the combined foot', [k('foot')], f'Use the native {side} yellow combined foot and align its retaining pilot with the ankle.')
    mod['operations'][-1].update(motionStop={'start': [0,0,-32], 'stop': [0,0,-3.99505615234375], 'movingKeys': [k('foot')], 'contactPair': k('foot')+'--'+k('ankle'), 'reason': 'The retaining features obstruct straight vertical insertion. This measured preview stops clear. Full fitting or a rotation path remains unverified; do not pull the foot into place with its screw.'})
    fasten(mod, 'Retain the foot', ['right-foot-retainer' if right else 'left-foot-retainer'], 'One M2×6 TAP at the print-to-print retaining hole; the registered boss gives 4 mm pilot engagement. Keep hand-snug and verify actual fit.')
    mod['operations'][-1].update(conditionalOnPreviousPhysicalFit=True)
    mod['operations'][-1]['text'] = 'Only after the foot has been fully seated by an actual fit check: ' + mod['operations'][-1]['text']
    place(mod, 'Prepare hip-yaw output on the open bench', [k('yaw'), f'motor{yaw}'], 'Put the short yaw-to-roll link on the bench and align the yaw output. Keep the roll motor, passive support and hip bridge off: the roll motor otherwise blocks all four inward-facing yaw screw tool paths.')
    mod['operations'][-1].update(isolatedPartKeys=[k('yaw'), f'motor{yaw}'], partApproachVectors={k('yaw'): [0, 0, 0], f'motor{yaw}': [0, 0, 45]})
    fasten(mod, 'Fasten hip-yaw output before fitting the roll motor', ids([yaw], ['horn']), 'Four M2×6 TAP. Work through the empty roll-motor cavity; complete all four while the inside screw heads remain reachable.')
    mod['operations'][-1].update(isolatedPartKeys=[k('yaw'), f'motor{yaw}'], access='The roll motor must still be absent. A Ø3 mm ×45 mm straight driver envelope is clear at all four yaw output screws in this bench state.')
    bench = [k('yaw'), f'motor{yaw}', f'motor{roll}', k('passive'), f'washer{roll}']
    place(mod, 'Seat hip-roll motor and its passive support on the bench', [f'motor{roll}', k('passive')], 'Keep the yaw/roll group separate from the thigh. Seat the roll motor, then its tall passive support from the open side. Leave the roll support ring for the hip bridge subassembly.')
    mod['operations'][-1].update(isolatedPartKeys=bench, partApproachVectors={f'motor{roll}': [45, 0, 0], k('passive'): [45, 0, 0]})
    fasten(mod, 'Fasten hip-roll case and rear center on the bench', ids([roll], ['case', 'rear_center']), 'Four M2×8 TAP, two through each support. One M2.6×6 TAP plus one 0.5 mm metal washer at the rear center.', [f'washer{roll}'])
    mod['operations'][-1]['isolatedPartKeys'] = bench
    thigh_group = [k(x) for x in ['thigh','plate','lower','ankle','smallring','foot','ring7','ring8','hip','ring9']]+[f'motor{a}',f'motor{knee}',f'motor{hp}',f'washer{a}']
    place(mod, 'Build the hip bridge on the thigh before joining the roll group', [k('ring8'), k('hip'), k('ring9')], 'Keep the completed yaw/roll group on the bench. Seat the hip-pitch ring first, then the orange hip bridge on the thigh, then the roll support ring in the bridge. Closing two perpendicular axes at once would trap the bridge.')
    mod['operations'][-1].update(isolatedPartKeys=thigh_group, partApproachVectors={k('ring8'): [0,45 if right else -45,0], k('hip'): [0,45 if right else -45,0], k('ring9'): [-45,0,0]})
    fasten(mod, 'Fasten hip-pitch output while the roll group is separate', ids([hp], ['horn']), 'Four M2×6 TAP at the hip-pitch output. The roll output remains unfastened until the following single-axis join.')
    mod['operations'][-1]['isolatedPartKeys'] = thigh_group
    place(mod, 'Join the completed yaw/roll group to the hip bridge', [], 'Move the yaw link, yaw motor, roll motor, passive support and rear washer as one fixed bench assembly toward the single roll axis. Do not move the bridge through the two perpendicular seated shafts.', highlight=bench)
    mod['operations'][-1].update(moveKeys=bench, approachVector=[-45,0,0])
    fasten(mod, 'Fasten the remaining hip-roll output', ids([roll], ['horn']), 'Four M2×6 TAP. Check the complete detached chain with torque off; this pictured pose is not calibrated zero.')
    return mod

leg_operations(); leg_operations(True)
m = module('torso', 'Open torso · connect both legs', ['left-leg', 'right-leg'], ['Support the robot during assembly; installed motors remain torque-off.', 'Keep both side shells off until the neck is placed.'])
place(m, 'Place base and power support with the sides open', ['torso_base', 'power_support', 'ring10_torso', 'ring5_torso'], 'Fit the integrated power support and black base around ID5/ID10. Add both Ø22 supports. Do not install the orange side shells yet; they close the two ID12 shaft seats.')
fasten(m, 'Fasten the six accessible torso case locations', [c['id'] for c in SCREWS if c.get('servo_ids') and c['servo_ids'][0] in [5,10] and c['category']=='case' and c['component'] not in ['left_shell','right_shell']], 'Use each listed length. The two shell-to-yaw-case M2×10 screws are deliberately deferred to neck closure.')
m = module('power', 'Converter and fuse carrier', ['torso'], ['Keep the whole power system disconnected. Source negotiation, polarity and loaded-voltage tests are separate commissioning.'])
place(m, 'Wire the converter in its loose open insert', ['regulator_insert', 'regulator'], 'Seat DFR1202 with a thin insulating edge liner. Connect its input and output leads while the terminal faces are accessible; leave their free ends insulated. Keep thermal surface and airflow open.')
m['operations'][-1].update(isolatedPartKeys=['regulator_insert','regulator'], wiringStage=2, beforeClose=['Identify IN+/IN− and OUT+/OUT− on the actual converter.', 'Fit and label the disconnected leads before retaining the insert.'])
fasten(m, 'Retain converter at the existing band slots', [], 'Fit the wired insert to the power support and use removable narrow ties at the two existing band positions. Keep ties off the inductor, chips and exposed pads.', retention=['No screw holes are specified for this insert.'])
place(m, 'Populate the fuse carrier before mounting it', ['fuse_carrier'], 'Load five lower and six upper slots through their open ends and route the insulated leads before the carrier is fixed. Reserve F0–F10 labels from the wiring guide.')
m['operations'][-1].update(wiringStage=3, beforeClose=['Verify fuse value and label at all eleven positions.', 'Seat leads in the four tie paths without crushing fuse bodies.'])
fasten(m, 'Fasten the populated fuse carrier', ids(group=['fuse_carrier']), 'Four M2×20 machine screws and four M2 nuts. Keep each nut reachable while starting its screw; the old regulator board is absent.')
m = module('imu', 'Torso IMU · connect before cover', ['torso'], ['Record the board axis markings while they remain visible.'])
place(m, 'Place IMU holder and board', ['imu_clamp', 'imu_board'], 'Place the orange holder on the fixed rails and seat BNO085. Connect and route its four leads with the cover absent.')
m['operations'][-1].update(wiringStage=7, beforeClose=['Confirm the 3.3 V, GND, SDA and SCL endpoints from Wire.', 'Photograph the actual board axes and route the lead through the cover exit.'])
fasten(m, 'Clamp the holder to the rails', ids(group=['imu_clamp']), 'Two M2×5 screws into the existing 1.6 mm pilots; tighten gently.')
place(m, 'Place cover after checking the IMU lead exit', ['imu_cover'], 'Fit the black cover only after its lead is connected, labeled and outside the seam. The obsolete alarm carrier is absent.')
fasten(m, 'Fasten IMU rear cover', ids(group=['imu_rear_cover']), 'Four M2×6 screws into existing plastic pilots, no nuts. M2×8 would pass the shortened boss.')
m = module('neck', 'Neck, yaw and roll · access before closure', ['torso'], ['Only IDs11/12 use separate printed idler+cap pairs.', 'Prepare the pitch/yaw and roll/fork as separate bench subassemblies before joining them.'])
neck_base = ['neck_link_a','neck_link_b','motor11','motor12','idler11','idler12','idler_cap11','idler_cap12']
place(m, 'Prepare both neck motors on the open bench', neck_base, 'Seat both motors between the orange links and install the two printed rear idler/cap pairs. Keep the torso shells off so the ID12 rear-center screw is reachable.')
m['operations'][-1]['isolatedPartKeys'] = neck_base
fasten(m, 'Fasten neck cases and rear centers before the shells', ids([11,12], ['case','rear_center']), 'Case corners: four M2×8 and four M2×10 TAP. Rear centers: one M2.6×6 TAP each, no washer. Finish both rear centers before adding the side shells.')
m['operations'][-1].update(isolatedPartKeys=neck_base, access='Work from both exposed sides on the bench; the right torso shell would block the ID12 rear-center driver 3.4 mm beyond the head.')
yaw_pitch = ['neck_pitch','neck_pitch_ring','motor13']
place(m, 'Prepare yaw motor and loose head-pitch bracket', yaw_pitch, 'Attach ID13 to the still-detached black pitch bracket. Keep this bracket off ID11: ID11 blocks the four inward-facing yaw output screws once joined.')
m['operations'][-1]['isolatedPartKeys'] = yaw_pitch
fasten(m, 'Fasten head-yaw output while the pitch bracket is detached', ids([13], ['horn']), 'Four M2×5 TAP at the ID13 output. Tighten all four now, before attaching this bracket to ID11.')
m['operations'][-1].update(isolatedPartKeys=yaw_pitch, access='Enter from the underside of the detached pitch bracket. Do not mount it on ID11 until all four output screws are complete.')
roll_fork = ['head_yaw_link','motor14','head_roll_ring_a','head_roll_ring_b']
place(m, 'Prepare roll motor on the separate empty yaw fork', roll_fork, 'Fit ID14 and its support rings to the black fork while ID13 is still in the separate pitch-bracket subassembly. The open yaw-motor cavity is needed for the roll output screws.')
m['operations'][-1]['isolatedPartKeys'] = roll_fork
fasten(m, 'Fasten head-roll output before inserting the yaw motor', ids([14], ['horn']), 'Four M2×6 TAP. Use a compact right-angle driver through the empty yaw-motor cavity; a long straight shaft is blocked by the opposite fork wall.')
m['operations'][-1].update(isolatedPartKeys=roll_fork, access='The fork leaves 24.5 mm from screw head to opposite wall. Keep the working tip and elbow within 20 mm, with the handle exiting through the open cavity. Check the actual driver before starting; ID13 must remain absent.', toolEnvelope={'type':'right-angle','bitDiameterMm':3,'projectionFromHeadMm':20,'physicalToolFitVerified':False})
place(m, 'Join the roll fork to the prepared yaw motor', [], 'Bring the completed roll/fork group to ID13, leaving the neck-motor group separate until the yaw case screws are secured.', highlight=roll_fork+yaw_pitch)
m['operations'][-1].update(moveKeys=roll_fork, isolatedPartKeys=roll_fork+yaw_pitch)
fasten(m, 'Fasten the yaw motor case to the fork', ids([13], ['case']), 'Four M2×10 TAP. The yaw output and roll output screws were already completed with their tool corridors open.')
m['operations'][-1]['isolatedPartKeys'] = roll_fork+yaw_pitch
place(m, 'Join the completed upper neck to ID11', [], 'Align both ID11 output/idler seats with the prepared black pitch bracket. Keep the entire group supported.', highlight=yaw_pitch+roll_fork)
m['operations'][-1].update(moveKeys=yaw_pitch+roll_fork, isolatedPartKeys=neck_base+yaw_pitch+roll_fork)
fasten(m, 'Fasten both head-pitch output sides', ids([11], ['horn']), 'Eight M2×6 TAP, four per side. These outward-facing screws stay reachable after the inner yaw and roll screws have been completed.')
place(m, 'Lower the neck into the still-open torso', [], 'Position ID12 above the open base with both orange side shells absent. Route the motor leads through their exits now; do not trap a plug behind a shaft seat.', highlight=neck_base+yaw_pitch+roll_fork)
m['operations'][-1].update(moveKeys=neck_base+yaw_pitch+roll_fork, approachVector=[0,0,50], wiringStage=4, beforeClose=['Check ID11–ID14 plug orientation and preserve a loose loop at each rotating axis.', 'Pass free plugs through openings before seating or tying the harness.'])
fasten(m, 'Support and inspect the open neck-to-torso fit', [], 'Hold the neck on a bench support. No screw is added here: inspect both shaft centers and lead exits before closing the sides.')
place(m, 'Bring the two torso shells in from opposite sides', ['shell_left','shell_right'], 'Fit each orange shell over its ID12 output/idler seat and yaw-case mounting seat. Do not force an assembled neck between two already-fixed shells.')
m['operations'][-1].update(partApproachVectors={'shell_left':[0,40,0],'shell_right':[0,-40,0]}, beforeClose=['ID12 rear-center screw is complete.', 'No motor cable crosses a shell seam or a rotating support.'])
fasten(m, 'Fasten neck outputs and the two shell case screws', ids([12], ['horn'])+[c['id'] for c in SCREWS if c.get('servo_ids') and c['servo_ids'][0] in [5,10] and c['category']=='case' and c['component'] in ['left_shell','right_shell']], 'Eight M2×6 TAP around the two ID12 output sides, then one M2×10 TAP shell-to-yaw-case screw on each side.')
m = module('head', 'Open head shell and jaw motor', ['neck'], ['Leave the moving jaw frame and both lip pads off until the cap closure screws are complete.'])
place(m, 'Seat the lower shell and jaw support around ID14', ['head_bottom','jaw_support'], 'Fit the yellow lower shell and revised support to the already-fastened roll motor. Its output screws are complete. Keep face, moving jaw and cap separate.')
fasten(m, 'Fasten jaw support to bottom shell', ids(group=['motor_support_frame']), 'Four M2.5×6 TAP, no nuts. Insert through the black support toward shell pilots; head diameter≤4 mm and height≤1.5 mm.')
place(m, 'Seat the jaw motor and connect its lead', ['motor15'], 'Seat ID15 in the revised support, leaving the moving jaw off. Connect its lead now; the integral sliding seat replaces the old separate mouth ring.')
m['operations'][-1].update(wiringStage=4, beforeClose=['ID15 plug is seated and the lead is outside the jaw sweep.', 'Keep all four jaw-output screw holes empty until the cap is closed.'])
fasten(m, 'Inspect jaw-motor retention with the shell open', [], 'No additional case-corner screws are specified. Inspect the printed locating/retaining features; do not add a screw to an unverified wall.')
m = module('electronics', 'Detached face, cap, controller and audio', ['head'], ['Mount and connect each board while its supporting face or cap is on the bench.', 'Current Pi mount targets the Zero form factor.'])
face_group = ['face_panel','eye_trim','pi']
place(m, 'Prepare Pi on the detached face panel', face_group, 'Place the face panel inward-side up on the bench. Confirm the actual Pi has the supported Zero form factor, then dry-seat it on the pilots with the cosmetic eye trim. Keep this whole face separate from the jaw motor and support.')
m['operations'][-1]['isolatedPartKeys'] = face_group
fasten(m, 'Fasten and connect Pi before fitting the face', ids(group=['pi']), 'Four M2.5×6 TAP, no nuts. Support the detached cap and face together: the camera end is already latched. Connect the GPIO housing and the remaining Zero ribbon end without pulling the ribbon; preserve slack between both bench groups.')
m['operations'][-1].update(isolatedPartKeys=face_group, wiringStage=8, access='Drive the four screws from the inward-facing board side on the bench. The installed jaw motor/support obstruct two of these straight tool corridors.', beforeClose=['Actual board and header match the checked mount envelope.', 'Ribbon contacts face the correct connector contacts; close its latch without creasing the ribbon.'])
cap_group = ['head_cap','openrb']
place(m, 'Prepare OpenRB on the detached cap', cap_group, 'Keep the cap upside down on the bench. Fit OpenRB to its four posts with both screw heads and nut faces reachable; leave the USB service window clear.')
m['operations'][-1]['isolatedPartKeys'] = cap_group
fasten(m, 'Fasten OpenRB with its underside accessible', ids(group=['openrb']), 'Four M2×18 machine screws and four M2 nuts. Hold each nut while starting the screw; do not substitute TAP screws.')
m['operations'][-1]['isolatedPartKeys'] = cap_group+[k for c in SCREWS if c.get('groupId')=='openrb' for k in c.get('hardwareKeys',[])]
audio_group = cap_group+['audio_carrier','amplifier','speaker']
place(m, 'Prepare audio on the same detached cap', ['audio_carrier','amplifier','speaker'], 'Fit the carrier, insulated amplifier and speaker while the cap remains on the bench. Keep diaphragm free and orient electrical terminals toward their exits.')
m['operations'][-1]['isolatedPartKeys'] = audio_group
fasten(m, 'Fasten carrier and connect audio before closure', ids(group=['audio_carrier']), 'Two M2×25 machine screws and two M2 nuts. Retain each device with two narrow tie loops through the existing slots; attach the audio leads while both sides remain accessible.')
m['operations'][-1].update(isolatedPartKeys=audio_group+[k for c in SCREWS if c.get('groupId') in ['openrb','audio_carrier'] for k in c.get('hardwareKeys',[])], wiringStage=9, beforeClose=['Speaker rim is restrained and diaphragm free.', 'Connect labeled amplifier and speaker leads; keep exposed joints insulated.'])
m = module('camera', 'Camera and tilt mount on detached cap', ['electronics'], ['Keep the cap on the bench until every internal connector and nut is checked.'])
place(m, 'Place camera pitch foot on the detached cap', ['camera_pitch_foot'], 'Align the foot with the cap bosses. Reach the cap underside for both M3 nuts before fitting the cradle.')
fasten(m, 'Fasten camera foot while both nut faces are open', ids(group=['camera_foot']), 'Two M3×10 screws, two 0.5 mm washers and two M3 nuts. Retain the nuts before adding the cradle.')
place(m, 'Place cradle in its tilt hinge', ['camera_cradle'], 'Align the cradle ears with the hinge; preserve tilt adjustment.')
fasten(m, 'Fasten tilt hinge', ids(group=['camera_hinge']), 'One M3×20 screw, two washers and one M3 nut. One washer sits outside each ear.')
place(m, 'Place camera PCB and route its ribbon', ['camera_board'], 'Seat the board on its four standoffs. Pass the free ribbon through its cap opening before plugging the camera end in; protect the lens and retain a smooth hinge loop.')
m['operations'][-1].update(wiringStage=8, beforeClose=['Correct camera end of SC1892 is seated and latched.', 'Ribbon clears the tilt hinge and has no sharp fold.'])
fasten(m, 'Fasten camera PCB', ids(group=['camera_pcb_10']), 'Four M2×10 machine screws and four M2 nuts. Check all four nuts; M2×8 leaves the nut partly unengaged.')
m = module('head-close', 'Close wired head, then jaw and pads', ['electronics','camera','head','wiring'], ['Complete the disconnected wiring inspection before either head half is closed.', 'Jaw and lip pads stay off until both front closure screws are complete.'])
place(m, 'Fit the connected face subassembly to the open shell', [], 'Bring the prewired face/Pi group to the shell rim. Keep the ribbon, GPIO and USB leads clear of the jaw motor and the three cap screw corridors.', highlight=face_group)
m['operations'][-1].update(moveKeys=face_group, beforeClose=['All four Pi screws and its inaccessible connector latches are complete.', 'A smooth service loop remains between face, cap and neck.'], wiringStage=10)
fasten(m, 'Inspect connectors and seams before bringing the cap down', [], 'With source disconnected, trace both endpoints and polarity of every lead in Wire. Inspect all three closure seats. Do not close over an unseated plug or trapped lead.')
place(m, 'Bring the populated cap to the head rim', [], 'Lower the complete wired cap/camera group to the rim. Leave the moving jaw and both lip pads off so the two front closure screws remain reachable.', highlight=['head_cap','head_bottom','face_panel'])
cap_move = ['head_cap','openrb','audio_carrier','amplifier','speaker','camera_pitch_foot','camera_cradle','camera_board']+[p['key'] for p in PARTS if p.get('fastenerId','').startswith(('E-openrb','E-audio_carrier','E-camera'))]
m['operations'][-1].update(moveKeys=cap_move, approachVector=[0,0,32], prerequisiteIds=['wiring'], beforeClose=['No cable crosses a rim seam or covers a screw head.', 'All three closure bosses are aligned; jaw frame and lip pads are absent.'])
fasten(m, 'Fasten the three-point cap closure before the jaw', ids(group=['head_cap_closure']), 'Three M2.5×8 TAP, no nuts. Drive the two front screws from below with the jaw and lip pads absent, then the center neck-end screw.')
m['operations'][-1]['access']='The two front screw corridors run through the space later occupied by the upper pad, lower pad and moving jaw. Install those only after all three cap screws are complete.'
place(m, 'Install the moving jaw after head closure', ['jaw_frame'], 'Align the jaw frame with ID15 and the opposite integral support. Keep its cable outside the moving gap.')
fasten(m, 'Fasten the asymmetric jaw output', ids([15], ['horn']), 'Use two M2×6 and two M2×7 TAP at the exact curved seats. These outward-facing jaw screws remain accessible after cap closure.')
place(m, 'Fit the fixed and moving lip pads last', ['upper_pad','lower_pad'], 'Dry-seat each pad on its own mating feature. Do not bond across the jaw gap. The pads cover access to the two front cap screws, so install them last.')
fasten(m, 'Check retention and hand-operated cable clearance', [], 'With torque disabled, check pad retention and gently sweep jaw, head and neck through their intended range. Stop at cable tension, rubbing or pinching; relocate the service loop before powering.', retention=['Printed fit and actual cable clearance remain physical checks, separate from the digital path audit.'])

modules_by_id = {m['id']: m for m in MODULES}
# Ownership follows first assembly introduction, making module isolation truthful.
for p in PARTS:
    p['moduleId'] = next(m['id'] for m in MODULES if any(p['key'] in op['add'] for op in m['operations']))
modules_by_id['power']['contextPartKeys'] = ['power_support']
modules_by_id['neck']['contextPartKeys'] = ['torso_base','power_support','motor5','motor10']
modules_by_id['head']['contextPartKeys'] = ['motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']
modules_by_id['camera']['contextPartKeys'] = cap_group
modules_by_id['head-close']['contextPartKeys'] = ['head_cap','head_bottom','jaw_support','motor15','face_panel','pi','eye_trim']
# Camera work is a real detached-cap bench assembly, not motion through the head.
for op in modules_by_id['camera']['operations']:
    op['isolatedPartKeys'] = cap_move
# Every operation can be addressed independently of its display number.
for m in MODULES:
    for i, op in enumerate(m['operations'],1):
        op['id'] = f"{m['id']}-{i:02d}"

def validate_foot_retainer():
    """Compare actual right retaining surfaces with the accepted left interfaces."""
    by = {p['key']: p for p in PARTS}
    results = []
    for key, leftkey in [('right_ankle', 'ankle'), ('right_foot', 'foot')]:
        c = right_foot_screw; direction = np.array(c['world_axis']); origin = np.array(c['world_center_mm'])
        # Probe annulus outside the Ø2.2 clearance / Ø1.6 pilot, away from triangulated edge ambiguity.
        basis = np.eye(3)[int(np.argmin(np.abs(direction)))]
        radial = np.cross(direction, basis); radial /= np.linalg.norm(radial)
        points = origin + radial * 1.5 - direction * 30
        right_hits = decode(by[key]).ray.intersects_location([points], [direction])[0]
        left_origin = (mirror @ np.r_[origin, 1])[:3]
        left_direction = mirror[:3, :3] @ direction
        left_radial = mirror[:3, :3] @ radial
        left_hits = decode(by[leftkey]).ray.intersects_location([left_origin + left_radial * 1.5 - left_direction * 30], [left_direction])[0]
        ra = np.sort((right_hits - origin) @ direction)
        la = np.sort((left_hits - left_origin) @ left_direction)
        assert len(ra) == len(la), (key, ra, la)
        error = float(np.max(np.abs(ra - la)))
        assert error < .02, (key, error, ra, la)
        results.append(dict(key=key, intersectionsFromHeadMm=ra.tolist(), oppositeHandErrorMm=error))
    # Independently discriminate real clearance/pilot at the mirrored datum.
    # Empty center/core and material immediately outside the pilot must both
    # hold; matching a far-away exterior annulus alone would be insufficient.
    direction = np.array(right_foot_screw['world_axis']); origin = np.array(right_foot_screw['world_center_mm'])
    basis = np.eye(3)[int(np.argmin(np.abs(direction)))]
    u = np.cross(direction, basis); u /= np.linalg.norm(u); v = np.cross(direction, u)
    angles = np.arange(16) * np.pi / 8 + .123
    for key, depths, core_radius, annulus_radius in [('right_ankle', [.2, .75, 1.3], .9, 1.5),
                                                   ('right_foot', [2.1, 4.5, 6.9], .65, .9)]:
        mesh = decode(by[key])
        radial = np.cos(angles)[:, None] * u + np.sin(angles)[:, None] * v
        core = np.vstack([origin - direction * depth + radial * core_radius for depth in depths])
        annulus = np.vstack([origin - direction * depth + radial * annulus_radius for depth in depths])
        core_material = mesh.contains(core); annulus_material = mesh.contains(annulus)
        assert not any(core_material), (key, 'pilot/clearance core obstructed')
        assert all(annulus_material), (key, 'missing surrounding threaded/clearance wall')
        results.append(dict(key=key, depthsFromHeadMm=depths, coreProbeRadiusMm=core_radius,
                            outerProbeRadiusMm=annulus_radius, coreMaterialHits=int(sum(core_material)),
                            surroundingMaterialHits=int(sum(annulus_material)), probesPerSet=len(core)))
    return results

FOOT_CHECK = validate_foot_retainer()
# Verify ring stock equivalence from original source coordinates, then allocate
# distinct printed stock instances. A representative source53 is not 11 prints.
ring_ids = [53, *range(87, 104)]
ring_equivalence = {}
base_ring = SOURCE_NS['mesh']('3D/3dmodel.model', '53')
for oid in ring_ids:
    t, error = match_rigid(SOURCE_NS['mesh']('3D/3dmodel.model', str(oid)), base_ring)
    assert error < .01, (oid, error)
    ring_equivalence[oid] = error
allocations = []; used = set()
for p in PARTS:
    if p['partKind'] != 'print': continue
    candidates = [r for r in STOCK if GROUP_COLOR[r['reference_group']] == p['colorName'] and
                  (Path(r['file']).name.split('_', 1)[1] == p['stockFileName'] or
                   p['sourceId'] == 53 and re.fullmatch(r'community-(53|8[7-9]|9\d|10[0-3])\.stl', Path(r['file']).name.split('_', 1)[1]))]
    chosen = next((r for r in candidates if r['manifest_instance_index'] not in used), None)
    assert chosen is not None, ('Printed stock over-allocated', p['key'], p['stockFileName'])
    used.add(chosen['manifest_instance_index']); p['stockManifestIndex'] = chosen['manifest_instance_index']
    p['stockReferenceGroup'] = chosen['reference_group']; p['stockFile'] = chosen['file']
    allocations.append({'partKey': p['key'], **chosen})

from reviewed_motion import apply as apply_reviewed_motion
apply_reviewed_motion(MODULES, PARTS, SCREWS)
for p in PARTS:
    p['moduleId']=next(m['id'] for m in MODULES if any(p['key'] in op['add'] for op in m['operations']))

ALL_KEYS = {p['key'] for p in PARTS}; ALL_SCREWS = {c['id'] for c in SCREWS}
adds = collections.Counter(); used_screws = collections.Counter()
for mod in MODULES:
    assert len(mod['operations']) % 2 == 0
    for i, op in enumerate(mod['operations']):
        assert op['kind'] == ('place' if i % 2 == 0 else 'fasten')
        assert set(op['add']) <= ALL_KEYS and set(op['screwIds']) <= ALL_SCREWS
        adds.update(op['add']); used_screws.update(op['screwIds'])
    mod['ownedPartKeys'] = [p['key'] for p in PARTS if p['moduleId'] == mod['id']]
    context = set(mod.get('contextPartKeys', []))
    context.update(key for op in mod['operations'] for key in op['highlightKeys'])
    context.update(key for op in mod['operations'] for key in op.get('moveKeys', []))
    context.update(c['partKey'] for c in SCREWS if any(c['id'] in op['screwIds'] for op in mod['operations']))
    mod['partKeys'] = list(dict.fromkeys(mod['ownedPartKeys'] + sorted(context)))
assert set(adds) == ALL_KEYS and set(adds.values()) == {1}, ('part coverage', adds)
assert set(used_screws) == ALL_SCREWS and set(used_screws.values()) == {1}, ('screw coverage', used_screws)
assert len([p for p in PARTS if p['partKind'] == 'motor']) == 15
assert len(SCREWS) == 118 + 34 + 2
for c in SCREWS:
    assert np.isclose(np.linalg.norm(c['world_axis']), 1, atol=1e-6)
    c['moduleId'] = next(mod['id'] for mod in MODULES if any(c['id'] in op['screwIds'] for op in mod['operations']))
by_key = {p['key']: p for p in PARTS}
for original in LEFT['parts']:
    # Explicitly retain every accepted left-leg triangle and vertex payload.
    p = by_key[original['key']]
    assert p['positionB64'] == original['positionB64'] and p['indexB64'] == original['indexB64']
for p in PARTS:
    m = decode(p)
    assert len(m.faces) == p['triangles'] and len(m.vertices) > 0
    assert np.isfinite(m.vertices).all() and np.max(m.faces) < len(m.vertices)
    assert np.allclose(m.bounds, p['bounds'], atol=1e-5)
for sid in range(1, 16):
    expected = geom(*[MOTOR_FRAMES[sid][0], 'xl330', MOTOR_FRAMES[sid][1]])['world']
    assert np.allclose(by_key[f'motor{sid}']['sourceTransformWorld'], expected, atol=1e-10)
for path in [XML, SOURCE_NS['SOURCE'], ASSEMBLY / 'community-print-inventory.json', ASSEMBLY / 'source-surface-refinement.json', COLOR_SOURCE, REDESIGN / 'ASSEMBLY-STEPS.md']:
    tracked(path)
PATH_REPORT_FILE = OUT / 'assembly-path-investigation.json'
path_report = json.loads(tracked(PATH_REPORT_FILE).read_text())
assert path_report['input_sha256'][str(OUT / 'leg-data.json')] == hashlib.sha256((OUT / 'leg-data.json').read_bytes()).hexdigest()
for side in ['left_native_inputs', 'right_native_inputs']:
    for key, record in path_report[side].items():
        part = by_key[key]
        assert hashlib.sha256(base64.b64decode(part['positionB64'])).hexdigest() == record['position_payload_sha256']
        assert hashlib.sha256(base64.b64decode(part['indexB64'])).hexdigest() == record['index_payload_sha256']
        assert np.allclose(part['sourceTransformWorld'], record['source_transform_world'], atol=1e-10)
totals = collections.Counter()
for c in SCREWS: totals[c['spec']] += c['quantity']
coverage = dict(passed=True, sourcePrintedStockInstances=len(STOCK), installedPrintInstances=len(allocations),
                installedMotorCount=15, modeledMeshCount=len(PARTS), motorJointScrews=118,
                electronicsMountScrews=34, footRetainers=2, totalIndividualScrews=len(SCREWS),
                operations=sum(len(m['operations']) for m in MODULES), sourceStockAllocation=allocations,
                specifiedSmallWashers=4, specifiedM3Washers=4, specifiedM2Nuts=14, specifiedM3Nuts=3,
                acceptedLeftMeshPayloadsUnchanged=True, screwAndPartOperationCoverageExactlyOnce=True,
                retainedStock=[r for r in STOCK if r['manifest_instance_index'] not in used],
                ringStockNativeEquivalenceP95Mm=ring_equivalence,
                exclusions=['Unused copied rings and twelve spare idler/cap pairs remain printed stock.',
                            'Original PCB retaining strip26 and old small regulator cover are retained stock, not current installed parts.',
                            'Old cap/support/regulators/alarm/battery/camera geometry is superseded; no print job is requested.'],
                rightFootRegistrationP95Mm=RIGHT_FOOT_ERROR, rightSleeveRegistrationP95Mm=RIGHT_RING_ERROR,
                rightFootCommonSurfaceP95Mm=RIGHT_FOOT_SURFACE_P95, rightFootLocalSurfaceDifferenceMaxMm=RIGHT_FOOT_SURFACE_MAX,
                rightFootRetentionReadback=FOOT_CHECK, neckIdlerRegistration=IDLER_REGISTRATION,
                physicalAssemblyVerified=False)
DATA = dict(schemaVersion=1, problem='P5', checked='2026-10-07', units='mm', parts=PARTS, screws=SCREWS,
            screwTotals=dict(totals), modules=MODULES, motorRoles=MOTOR_ROLES, coverage=coverage,
            leftPartKeys=[p['key'] for p in LEFT['parts']], leftScrewIds=[c['id'] for c in LEFT['screws']],
            sourceHashes=SOURCE_HASHES, physicalAssemblyVerified=False,
            assemblyPathInvestigation={k: path_report[k] for k in ['result_scope', 'native_final_lower_sleeve_material_overlap_mm3', 'physical_fit_verified', 'proposed_sequence']},
            partialPaths=path_report['paths'][:2], rightPartialPaths=path_report.get('right_paths', []),
            notes=['Assembly snapshot uses original zero-joint FK and current redesigned body geometry; it is not a calibrated motor pose.',
                   'GeometryKind distinguishes native printed meshes, manufacturer CAD, specified washers and supplier installation envelopes.',
                   'Electronics audit axis is insertion; all guide world_axis values are outward, so screw insertion is -world_axis.',
                   'Motion in the viewer demonstrates assembly approach, not torque-enabled robot motion or proved physical clearance.'])
(OUT / 'full-build-data.json').write_text(json.dumps(DATA, separators=(',', ':')) + '\n')
print('FULL_BUILD_DATA_PASS', json.dumps({k: v for k, v in coverage.items() if k not in ['sourceStockAllocation', 'retainedStock', 'ringStockNativeEquivalenceP95Mm', 'neckIdlerRegistration']}))
