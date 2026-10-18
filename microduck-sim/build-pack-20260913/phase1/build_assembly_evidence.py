"""Derive a Phase 1 print subset and mass/geometry sensitivity inputs.

Frozen source models remain unchanged. New masses are engineering approximations;
the original model's lumped battery/electronics mass stays a swept uncertainty.
"""
from pathlib import Path
import collections
import copy
import hashlib
import json
import sys
import numpy as np
import trimesh

P = Path(__file__).resolve().parent
A = P.parent / 'assembly'
OLD = P.parents[1] / 'hardware-design-20260912/whole-robot-20260912'
S = P / 'simulation'
S.mkdir(exist_ok=True)

def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')

source = json.loads((A / 'print-manifest.json').read_text())
defer = {'Audio carrier', 'Camera tilt foot', 'Camera cradle', 'Voltage-alarm and EN-switch carrier'}
rows = [copy.deepcopy(r) for r in source['instances'] if r['name'] not in defer]
for r in rows:
    r['file'] = str((A / r['file']).resolve())
    assert hashlib.sha256(Path(r['file']).read_bytes()).hexdigest() == r['sha256']
assert len(rows) == 85
dump(P / 'print-manifest.json', {'instances': rows, 'count': 85,
    'meaning': '78 retained source/stock instances and 7 current parts; includes 14 idlers and 14 caps as a stocking allowance, not an installed count.',
    'deferred_parts': sorted(defer), 'source_manifest': str(A / 'print-manifest.json')})
groups = collections.OrderedDict()
for r in rows:
    group = groups.setdefault(r['name'], [])
    group.append(r)
text = '# Phase 1 print list\n\nPrint this 85-instance subset. Printing material and fasteners remain RoboClub-first. This subset retains the torso interfaces, jaw repairs and future electronics mounting interfaces.\n\n'
text += 'Use PLA at original scale. The prepared project uses X1 Carbon / 0.4 mm / Cool Plate / 0.2 mm layers / four walls / 30% gyroid / automatic tree supports. Match the actual machine, nozzle and plate, then slice again if they differ. A slicer result is a manufacturing estimate, not a physical print.\n\n'
text += 'The quantity below counts print stock. Fourteen idlers and fourteen caps are an upper-bound allowance; install one only where the joint construction needs it. Record spare copies separately.\n\n'
for name, rs in groups.items():
    counts = collections.Counter(r['file'] for r in rs)
    text += f'- **{name}: {len(rs)} total.** '
    text += '; '.join(f'[{Path(f).name}]({f}) × {n}' for f, n in counts.items()) + '\n\n'
text += 'Deferred prints: camera cradle, camera tilt foot, audio carrier, voltage-alarm/ENA-switch carrier. Source community-6, community-12 and community-24 are superseded; do not print them. Keep the integrated torso support and its empty regulator-pocket cover. The power shelves and battery cradle are part of that structural print and remain empty.\n'
(P / 'PRINT-LIST.md').write_text(text)

sys.path.insert(0, str(OLD / 'assembly'))
from assembly_fk import fk, raw

def mesh_mass(identifier, body, mesh, sign=1):
    props = mesh.mass_properties
    # Coordinates are mm and solid PLA density is 1.24 g/cm3.
    return {'id': identifier, 'body': body, 'mass_kg': sign * props['volume'] * 1.24e-6,
        'position_m': (props['center_mass'] * .001).tolist(),
        'inertia_about_com_kg_m2': (sign * props['inertia'] * 1.24e-12).tolist(),
        'accounting': 'Uniform solid PLA approximation, not received or slicer-derived installed mass.'}

full = json.loads((OLD / 'dynamics/full-mass-base.json').read_text())
removed = {'battery','servo_regulator','logic_regulator','audio_carrier','camera_pitch_foot','camera_cradle','camera_module3_wide','amp','speaker','head_cap'}
parts = [copy.deepcopy(r) for r in full['parts'] if r['id'] not in removed]
parts.append(mesh_mass('current-relieved-cap', 'jaw_soft', trimesh.load(A / 'mouth-clearance/head-cap-mouth-clearance-assembly.stl', force='mesh')))
parts.append(mesh_mass('current-fuse-carrier', 'trunk_base', trimesh.load(A / 'service-mounts/fuse-bank-body.stl', force='mesh')))
parts.append(mesh_mass('current-jaw-support', 'jaw_soft', trimesh.load(A / 'mouth-support/motor-support-coaxial-assembly.stl', force='mesh')))
for g in fk()[1]:
    if g['body'] == 'jaw_soft' and g['mesh'] in ['motor_support','seeed_bearing__configuration_default']:
        parts.append(mesh_mass('remove-' + g['mesh'], 'jaw_soft', raw(g['mesh']).apply_transform(g['local']), -1))
dump(S / 'mass-manifest.json', {'parts': parts, 'removed_phase2_ids': sorted(removed),
    'retained_allowances': 'Original head fasteners 11.8 g, head wire 4 g and trunk wires/hardware 25 g retained as allocations. Additional 20 g and 40 g trunk wiring uncertainty tested separately.',
    'pi': 'Pi remains in the original lumped head inertia; Phase 1 runtime uses a borrowed Pi.',
    'jaw': '15th motor and jaw source geometry remain in original lumped head inertia. Jaw held closed in gait regression, not actuated by the 14-action walking policy.',
    'unresolved': 'Original source inertias lump masses. Old battery removal 0/60/120 g and old electronics removal 15 g are hypotheses, not teardown measurements. Printed source feet remain the original dynamics contact approximation; community-print friction is not measured.'})
geom = json.loads((OLD / 'dynamics/full-geometry.json').read_text())
keep = []
for r in geom['parts']:
    fn = Path(r['mesh']).name
    if any(x in fn for x in ['battery-max','large_regulator','small_regulator','audio_carrier','camera_','amp_','speaker_']):
        continue
    if fn == 'head_cap_assembly.stl':
        r['mesh'] = str(A / 'mouth-clearance/head-cap-mouth-clearance-assembly.stl')
    keep.append(r)
geom['remove_meshes'] += ['motor_support','seeed_bearing__configuration_default']
keep += [{'body':'jaw_soft','mesh':str(A / 'mouth-support/motor-support-coaxial-assembly.stl')},
         {'body':'trunk_base','mesh':str(A / 'service-mounts/fuse-bank-body.stl')}]
geom['parts'] = keep
geom['collision_method'] = 'Same original dynamics contact geometry. New CAD meshes are visual only; separate sampled mesh checks are required for rigid interference. No cable contact model.'
dump(S / 'geometry-manifest.json', geom)
dump(S / 'source-hashes.json', {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
    OLD / 'dynamics/full-mass-base.json', OLD / 'dynamics/full-geometry.json',
    OLD / 'delay-repair-20260912/evaluate_delay.py', OLD / 'delay-repair-20260912/compensation.py',
    A / 'print-manifest.json']})
print(json.dumps({'print_count':len(rows),'mass_parts':len(parts),'geometry_parts':len(keep)}))
