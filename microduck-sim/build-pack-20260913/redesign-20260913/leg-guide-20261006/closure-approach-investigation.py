#!/usr/bin/env python3
"""Read unchanged native meshes; measure a lower-link approach that stops clear."""
from pathlib import Path
import base64
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import manifold3d as mf
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[2]
NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02', 'p': 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'}
THRESHOLD = .02
STEP = .25
RETREAT = .5
START = 12.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def investigate():
    data = json.loads((HERE / 'full-build-data.json').read_text())
    rows = {p['key']: p for p in data['parts']}
    sides = [('left-leg', 'lower', ['ankle', 'smallring', 'motor6'], [0., -1., 0.]),
             ('right-leg', 'right_lower', ['right_ankle', 'right_smallring', 'motor1'], [0., 1., 0.])]
    keys = [k for _, moving, fixed, _ in sides for k in [moving] + fixed]
    parts, identities, display = {}, {}, {}
    for key in keys:
        p = rows[key]
        pos = base64.b64decode(p['positionB64'])
        ind = base64.b64decode(p['indexB64'])
        mesh = trimesh.Trimesh(np.frombuffer(pos, dtype='<f4').reshape(-1, 3), np.frombuffer(ind, dtype='<u4').reshape(-1, 3), process=True)
        solid = mf.Manifold(mf.Mesh(np.asarray(mesh.vertices, dtype=np.float32), np.asarray(mesh.faces, dtype=np.uint32)))
        assert solid.status() == mf.Error.NoError, key
        parts[key], display[key] = solid, mesh
        identities[key] = {'sourceId': p['sourceId'], 'sourceTransformWorld': p['sourceTransformWorld'], 'positionPayloadSha256': hashlib.sha256(pos).hexdigest(), 'indexPayloadSha256': hashlib.sha256(ind).hexdigest(), 'triangles': len(mesh.faces), 'manifoldStatus': str(solid.status()), 'volumeMm3': solid.volume()}

    native = SIM / 'Microduck-build-tutorial/microduck3D打印.3mf'
    trees = {}
    with zipfile.ZipFile(native) as archive:
        def native_mesh(path, object_id):
            if path not in trees:
                trees[path] = ET.fromstring(archive.read(path))
            obj = next(o for o in trees[path].findall('m:resources/m:object', NS) if o.get('id') == str(object_id))
            node = obj.find('m:mesh', NS)
            if node is not None:
                vertices = [[float(v.get(k)) for k in ['x', 'y', 'z']] for v in node.findall('m:vertices/m:vertex', NS)]
                faces = [[int(v.get(k)) for k in ['v1', 'v2', 'v3']] for v in node.findall('m:triangles/m:triangle', NS)]
                return trimesh.Trimesh(vertices, faces, process=True)
            pieces = []
            for c in obj.findall('m:components/m:component', NS):
                T = np.eye(4)
                if c.get('transform'):
                    T[:3, :] = np.array([float(x) for x in c.get('transform').split()]).reshape(4, 3).T
                pieces.append(native_mesh(c.get('{' + NS['p'] + '}path', path).lstrip('/'), c.get('objectid')).apply_transform(T))
            return trimesh.util.concatenate(pieces)
        for key in keys:
            if rows[key]['sourceId'] is None:
                continue
            mesh = native_mesh('3D/3dmodel.model', rows[key]['sourceId']).apply_transform(np.array(rows[key]['sourceTransformWorld']))
            a = cKDTree(mesh.vertices).query(display[key].vertices)[0]
            b = cKDTree(display[key].vertices).query(mesh.vertices)[0]
            error = float(max(a.max(), b.max()))
            assert len(mesh.faces) == len(display[key].faces) and error < 2e-5, (key, error)
            identities[key]['nativeReadback'] = {'trianglesMatch': True, 'bidirectionalVertexMaxErrorMm': error, 'serializationToleranceMm': 2e-5}

    paths = {}
    for side, moving, fixed, direction in sides:
        direction = np.array(direction)
        def measure(distance):
            translated = parts[moving].translate(direction * distance)
            return {moving + '--' + key: max(0., float((translated ^ parts[key]).volume())) for key in fixed}
        samples = []
        for distance in np.linspace(START, 0, int(START / STEP) + 1):
            volumes = measure(distance)
            samples.append({'distanceMm': float(distance), 'translation': (direction * distance).tolist(), 'pairOverlapMm3': volumes, 'exceedsThreshold': any(v > THRESHOLD for v in volumes.values())})
        assert max(samples[0]['pairOverlapMm3'].values()) == 0, side
        first = next(i for i, s in enumerate(samples) if s['exceedsThreshold'])
        clear, contact = samples[first - 1]['distanceMm'], samples[first]['distanceMm']
        for _ in range(12):
            middle = (clear + contact) / 2
            if any(v > THRESHOLD for v in measure(middle).values()):
                contact = middle
            else:
                clear = middle
        # The volume threshold permits tiny contact. Retreat farther and require
        # actual zero intersection plus a separately measured positive gap.
        stop = min(START, clear + RETREAT)
        safe_samples = []
        for distance in np.linspace(START, stop, int(np.ceil((START - stop) / STEP)) + 1):
            volumes = measure(distance)
            assert max(volumes.values()) < 1e-9, (side, distance, volumes)
            safe_samples.append({'distanceMm': float(distance), 'translation': (direction * distance).tolist(), 'pairOverlapMm3': volumes})
        stopping = parts[moving].translate(direction * stop)
        gaps = {moving + '--' + key: float(stopping.min_gap(parts[key], 2.)) for key in fixed}
        gap = min(gaps.values())
        assert gap > .1, (side, gaps)
        contact_volumes = measure(contact)
        pair = max(contact_volumes, key=contact_volumes.get)
        frame = lambda t: {'t': t, 'translation': (direction * (START + t * (stop - START))).tolist(), 'quaternion': [0., 0., 0., 1.]}
        path = {'movingKeys': [moving], 'fixedKeys': fixed, 'startTranslation': (direction * START).tolist(), 'stopTranslation': (direction * stop).tolist(),
                'lastClearTranslation': (direction * stop).tolist(), 'contactTranslation': (direction * contact).tolist(), 'thresholdLastSafeTranslation': (direction * clear).tolist(),
                'contactPair': pair, 'contactPairOverlapMm3': contact_volumes, 'stopPairOverlapMm3': measure(stop), 'stopGapMm': gap, 'stopPairGapsMm': gaps,
                'axisCenter': np.mean(np.array(rows[fixed[1]]['bounds']), axis=0).tolist(), 'approachAxis': (-direction).tolist(), 'outwardStartAxis': direction.tolist(),
                'directionRationale': 'Collinear with the actual sleeve/boss axis; the lower link approaches the loose bench subassembly from its passive side. This demonstrates the fitting obstruction, not an author-validated complete assembly order.',
                'samples': safe_samples, 'fullTargetRouteSamples': samples, 'sampleStepMmMaximum': STEP, 'collisionThresholdMm3': THRESHOLD,
                'contactBracketWidthMm': STEP / 2**12, 'retreatFromThresholdBoundaryMm': RETREAT, 'targetPairOverlapMm3': measure(0),
                'result': 'sampled-zero-overlap-approach-stopping-before-contact', 'physicalFitVerified': False, 'completeClosureValidated': False,
                'precondition': 'Isolated loose bench ankle, ring and bare motor already present. Lower link is the only moving part. Knee/thigh, screws and wires are excluded obstacles.',
                'animation': {'movingKeys': [moving], 'fixedKeys': fixed, 'pivotMm': np.mean(np.array(rows[fixed[1]]['bounds']), axis=0).tolist(), 'frames': [frame(t) for t in [0., .25, .5, .75, 1.]], 'stopAtT': 1., 'collisionIntervals': [], 'translationConvention': 'World millimetres added to each unchanged native assembled mesh; quaternion xyzw. t=1 is the measured stopped approach, NOT the nominal assembled target.'}}
        paths[side] = path
        print(side, 'STOP', path['stopTranslation'], 'GAP', gap, 'CONTACT', pair, contact_volumes, flush=True)

    source_paths = [native, SIM / 'build-pack-20260913/redesign-20260913/fastener-audit/sources/X330_3d.stp', SIM / 'microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml', SIM / 'PROJECT-CONTEXT.json']
    result = {'problemIds': ['P5', 'P6'], 'checked': '2026-10-07', 'passedAsBoundedApproachInvestigation': True, 'paths': paths, 'meshIdentities': identities,
              'sourceHashes': {str(p): sha(p) for p in source_paths}, 'scriptSha256': sha(__file__),
              'fullJsonHashDeliberatelyExcluded': 'Full guide may embed this report. Participating position/index payloads and source transforms are bound instead, avoiding circular hashes.',
              'scope': 'Finite actual-solid approach samples plus positive endpoint gap; no continuous separation certificate, complete rigid closure, physical fit, compliance, printing or motor motion validation.',
              'noCadOrPrintChanges': True, 'physicalFitVerified': False}
    (HERE / 'closure-approach-investigation.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    investigate()
    print('CLOSURE_APPROACH_INVESTIGATION_PASS')
