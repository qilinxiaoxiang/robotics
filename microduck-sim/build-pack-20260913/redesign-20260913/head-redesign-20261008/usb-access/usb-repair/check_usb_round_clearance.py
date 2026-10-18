"""Supplement one USB receiving-mesh check with a continuous round-cable bound.

Run with the same arguments as check_planned_usb.py through the CAD guard.
It reuses that entry point's exact plan, source validation and selected FK poses.
"""
from pathlib import Path
import hashlib, json, math, os, runpy, sys

assert os.environ.get('MICRODUCK_BOUNDED_CAD') == '1'
D = Path(__file__).resolve().parent
H = D.parent.parent
ns = runpy.run_path(str(D / 'check_planned_usb.py'))
a = ns['args']
assert a.obstacle not in ('self', 'export')
np = ns['np']
helper = H / 'cabling-release-20261008/neck-repair/segment_capsule_clearance.py'
sys.path.insert(0, str(helper.parent))
from segment_capsule_clearance import check

rows = []
ob = ns['ob']
for index, case in ns['cases']:
    current = ob
    if a.domain or a.pose_indices:
        poses, _ = ns['fk']({k: np.deg2rad(v) for k, v in case['jointDegrees'].items()})
        base = ns['baseline']
        head_delta = poses['jaw_soft'] @ np.linalg.inv(base['jaw_soft'])
        body_delta = poses[ns['body']] @ np.linalg.inv(base[ns['body']])
        current = ob.transform((np.linalg.inv(head_delta) @ body_delta)[:3])
    for name, points in [('scFlexibleReceiving', ns['scPoints']),
                         ('acFlexibleReceiving', ns['acPoints'])]:
        chord = float(np.linalg.norm(np.diff(points, axis=0), axis=1).max())
        assert chord <= .250001, ('Unbounded centerline discretization', chord)
        # The generator uses exact R10 circular arcs and exact line segments.
        # Every chord's arc deviation is at most R-sqrt(R²-(chord/2)²).
        sagitta = 10 - math.sqrt(100 - (chord / 2) ** 2) + 1e-9
        evidence = {'watertight': True, 'positiveVolume': True,
                    'sourceSha256': hashlib.sha256(json.dumps(ns['hashes'], sort_keys=True).encode()).hexdigest(),
                    'validation': 'The reused entry point validates the source solid and any geometry-preserving topology normalization.'}
        result = check(points, 2.25, sagitta, current, source_evidence=evidence)
        rows.append({'poseIndex': index, 'moving': name, 'obstacle': a.obstacle,
                     'nativeRigidBlocked': bool(case['nativeShellOriginalBottomIntersectionsMm3']),
                     'maximumChordMm': chord, 'result': result})
hashes = dict(ns['hashes'])
for path in (Path(__file__), helper):
    hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
out = ns['outdir'] / (a.obstacle + ns['selectionSuffix'] + '-round.json')
report = {'status': 'CONTINUOUS_ROUND_CABLE_BOUND_AT_SELECTED_POSES',
          'allClear': all(r['result']['passed'] for r in rows),
          'coverageComplete': all(r['result']['coverageComplete'] for r in rows),
          'checks': rows, 'sourceHashes': hashes, 'assemblyAccepted': False,
          'boundary': 'Full round cable along each exact line/arc route at selected poses. Joint interpolation, uncertain physical dimensions, plug mating, and restraints are separate.'}
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'roundClear': report['allClear'], 'pairs': len(rows),
                  'inconclusive': sum(not r['result']['passed'] for r in rows)}))
