"""Recheck the frozen populated cap against current integrated rigid geometry.

USB plugs and external cables are inserted after cap fastening and deliberately
absent during this operation. No source or generated STL is changed here.
"""
from pathlib import Path
import json, hashlib, base64, io
import numpy as np
import trimesh
import manifold3d as mf

D = Path(__file__).resolve().parent
H = D.parent
G = H.parent / 'leg-guide-20261006'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = G / 'full-build-data.json'
source_bytes = source.read_bytes()
source_hash = hashlib.sha256(source_bytes).hexdigest()
data = json.loads(source_bytes)
config = json.loads((H / 'viewer-candidate.json').read_bytes())
assert not config.get('transforms'), 'This world-mesh verifier requires identity transforms'
loaded = {}

def man(mesh):
    return mf.Manifold(mf.Mesh(np.asarray(mesh.vertices, np.float32), np.asarray(mesh.faces, np.uint32)))

def load(relative):
    path = (H / relative).resolve()
    loaded[str(path.relative_to(H))] = sha(path)
    return man(trimesh.load(path, force='mesh'))

def hits(a, b):
    aa = np.array(a.bounding_box()).reshape(2, 3)
    bb = np.array(b.bounding_box()).reshape(2, 3)
    if np.any(aa[0] >= bb[1]) or np.any(bb[0] >= aa[1]):
        return 0.
    return max(0., float((a ^ b).volume()))

cap_path = D / 'curved-cap-final-candidate-world.stl'
cap_hash_before = sha(cap_path)
cap_mesh = trimesh.load(cap_path, force='mesh')
assert cap_mesh.is_watertight and len(cap_mesh.split()) == 1
scene = {}
for part in data['parts']:
    key = part['key']
    if key in config['removedParts']:
        continue
    if key in config['replacementMeshes']:
        scene[key] = load(config['replacementMeshes'][key])
    else:
        scene[key] = man(trimesh.Trimesh(
            np.frombuffer(base64.b64decode(part['positionB64']), '<f4').reshape(-1, 3),
            np.frombuffer(base64.b64decode(part['indexB64']), '<u4').reshape(-1, 3), process=True))
absent = []
for part in config['additionalParts']:
    if part.get('plugEnvelope') or part['mesh'].startswith('usb-access/full-harness/'):
        absent.append({'key': part['key'], 'reason': 'External USB assembly follows cap fastening'})
        continue
    scene[part['key']] = load(part['mesh'])
moving_keys = ['head_cap', 'openrb', 'amplifier', 'speaker', 'speaker_cradle',
               'speaker_keeper', 'curved_cap_hardware']
moving = {key: scene[key] for key in moving_keys}
fixed = {key: value for key, value in scene.items() if key not in moving}
rows, peak = [], {}
for dz in np.arange(40, -.0001, -.25):
    contacts = {}
    for key, solid in moving.items():
        moved = solid.translate([0, 0, dz])
        for obstacle, other in fixed.items():
            volume = hits(moved, other)
            if volume > 1e-4:
                pair = key + '--' + obstacle
                contacts[pair] = volume
                peak[pair] = max(peak.get(pair, 0), volume)
    rows.append({'offsetZmm': float(dz), 'intersectionsMm3': contacts})
assert sha(cap_path) == cap_hash_before
old_path = D / 'populated-cap-assembly.json'
archive = D / 'populated-cap-assembly-construction-history.json'
if not archive.exists():
    archive.write_bytes(old_path.read_bytes())
original = json.loads(archive.read_bytes())
report = {key: original[key] for key in [
    'problemIds', 'stlSimplificationToleranceMm', 'stlRepairRounds',
    'replacedSourceHardware', 'usbCOpeningRemovedMm3', 'railRelief']}
report.update({
    'sourceDataSha256': source_hash, 'stlReadbackVerified': True,
    'shellWatertight': cap_mesh.is_watertight, 'shellBodies': len(cap_mesh.split()),
    'frozenCapSha256': cap_hash_before, 'geometryRegenerated': False,
    'constructionHistory': {'path': archive.name, 'sha256': sha(archive),
        'scope': 'Historical construction metrics only; old USB receiving mesh was a cutting tool, not a closure obstacle. Current closure is rechecked below.'},
    'closurePath': {'startOffsetMm': [0, 0, 40], 'endOffsetMm': [0, 0, 0],
        'stepMm': .25, 'moving': moving_keys, 'fixed': list(fixed), 'samples': rows,
        'peakIntersectionsMm3': peak, 'absentUntilAfterClosure': absent},
    'sceneSelection': {'removedParts': config['removedParts'],
        'replacementMeshes': config['replacementMeshes'],
        'additionalParts': [{'key': p['key'], 'mesh': p['mesh'],
                            'plugEnvelope': p.get('plugEnvelope', False)} for p in config['additionalParts']]},
    'loadedMeshHashes': loaded,
    'sourceHashes': {path.name: sha(path) for path in [cap_path, Path(__file__), archive]},
    'physicalFitVerified': False, 'manufacturingAccepted': False,
})
old_path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'capSha256': cap_hash_before, 'samples': len(rows),
                  'fixedCount': len(fixed), 'peakIntersectionsMm3': peak,
                  'geometryRegenerated': False}, indent=2))
if peak:
    raise SystemExit(1)
