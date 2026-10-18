#!/usr/bin/env python3
"""Merge the per-route evaluation pieces (eval-<route>-<tag>.json) and the local calculations into ../clearances.json."""
import json, glob, os
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(HERE), 'clearances.json')
routes = {}
for f in sorted(glob.glob(os.path.join(HERE, 'eval-*.json'))):
    d = json.load(open(f)); r = d['route']
    R = routes.setdefault(r, {'description': d['description'], 'groupRadiusMm': d['groupRadiusMm'], 'lengthAtQ0Mm': d['lengthAtQ0Mm'],
                              'points': d['points'], 'excludedObstacles': d['excludedObstacles'], 'sets': {}, 'partMin': {}, 'rollTable': [], 'jawTable': []})
    for s, v in d['sets'].items():
        if s not in R['sets'] or v['posesChecked'] > R['sets'][s]['posesChecked']:
            R['sets'][s] = v
    for k, v in d['partMin'].items():
        if k not in R['partMin'] or v['clearanceMm'] < R['partMin'][k]['clearanceMm']:
            R['partMin'][k] = v
    for row in d['rollTable']:
        (R['rollTable'] if row['set'] == 'rollSweep' else R['jawTable']).append(row)
for r in routes.values():
    r['partMin'] = dict(sorted(r['partMin'].items(), key=lambda kv: kv[1]['clearanceMm']))
    seen = set(); r['rollTable'] = [x for x in r['rollTable'] if not (x['poseDeg']['head_roll'] in seen or seen.add(x['poseDeg']['head_roll']))]
    seen = set(); r['jawTable'] = [x for x in r['jawTable'] if not (x['poseDeg']['jaw'] in seen or seen.add(x['poseDeg']['jaw']))]
    r['summary'] = {s: {'slackNeededMm': v['slackNeededMm'], 'minClearanceMm': v['pinch']['clearanceMm'], 'pinchPart': v['pinch']['part'],
                        'pinchSegment': v['pinch']['routeSegment'], 'pinchPoseDeg': v['pinch']['poseDeg'], 'posesWithTautSpanThroughASolid': v['tautSpanThroughSolids']['poses'],
                        'complete': v['posesChecked'] == v['poses']} for s, v in r['sets'].items()}
    def first_neg(rows, key, sign):
        rows = sorted(rows, key=lambda x: sign * x['poseDeg'][key])
        for x in rows:
            if sign * x['poseDeg'][key] > 0 and x['minClearanceMm'] < 0: return x['poseDeg'][key]
        return None
    r['rollWindow'] = {'clearanceAtRestMm': next((x['minClearanceMm'] for x in r['rollTable'] if x['poseDeg']['head_roll'] == 0), None),
                       'firstNegativeRollDegWhereGroupIsSqueezed': first_neg(r['rollTable'], 'head_roll', -1),
                       'firstPositiveRollDegWhereGroupIsSqueezed': first_neg(r['rollTable'], 'head_roll', 1),
                       'method': 'rollSweep: head roll alone, -25..+25 deg in 2.5 deg steps, yaw/pitch 0, jaw closed; clearance = exact distance from the taut route centreline to the nearest part on another body, minus the 1.7 mm group radius; negative = the group is squeezed'}
out = {'_doc': 'Head-wire route study 2026-10-14 (guide/print/head-wires-20261014). Robot frame mm (x forward, y left, z up), q = 0 unless a pose is given. Model: taut straight spans between route points riding on their MJCF bodies (neck-route/motion.py), exact distances to the current audit solids (interference-audit cache), 1.7 mm group radius for the eight wires lying two deep (inference from V1.9). Negative clearance on a free span (different bodies at its ends) is the taut-line artefact also present in the V1.9 release numbers (route-v19-motion.json); negative clearance on a span whose both ends ride on the head is a real squeeze between the head and another body.',
       'jointRangesDeg': {'mjcf': {'neck_pitch': [-90, 60], 'head_pitch': [-90, 90], 'head_yaw': [-170, 170], 'head_roll': [-25, 25]},
                          'walkingFramesRecorded': {'neck_pitch': [-22.6, 44.0], 'head_pitch': [-0.9, 68.2], 'head_yaw': [-26.8, 34.0], 'head_roll': [-21.4, 11.2]},
                          'policyBox': {'neck_pitch': [-22.6, 39.8], 'head_pitch': [5.9, 68.2], 'head_yaw': [-24.6, 34.0], 'head_roll': [-21.4, 9.9]},
                          'handTurningLimitYawDeg': 80, 'rollSignConvention': 'MJCF head_roll axis is -x at (8.1, 0, 115.6); positive roll tilts the crown towards +y (robot left)'},
       'entries': {'designedSlotMinusY': {'freeWidthAtRestMm': 4.41, 'at': [16.94, -26.73, 129.08], 'boundedBy': ['head_yaw_link (yaw body)', 'jaw_support (head)'], 'source': 'extension-20261012-neck-audio/neck-route/README.md (measured)'},
                   'leftRearTrianglePlusY': {'freeWidthAtRestMm': 6.30, 'at': [13.85, 12.65, 127.29], 'boundedBy': ['head_yaw_link (yaw body) 3.15', 'motor15 (head) 3.16', 'jaw_support (head) 3.43'],
                                             'belowTheFloor': {'freeWidthMm': 6.9, 'at': [13.6, 13.0, 98.8], 'boundedBy': 'neck_pitch bracket rear-left corner'},
                                             'sharedWith': 'ID11-to-ID13 servo cable (ttl-13-11), centreline at (13.8, 12.2, 127.3); its X3P cable is about 3 mm across, so about 3.3 mm of the 6.3 mm is left for the eight wires', 'source': 'neck-route/corridors.json entry-1 (measured), route B in its README'}},
       'cableDistancesAtQ0': json.load(open(os.path.join(HERE, 'cable_distances_q0.json'))),
       'capLift40mm': json.load(open(os.path.join(HERE, 'cap_lift.json'))),
       'partClearancesAtQ0': {'_doc': 'q = 0, centreline-to-surface distance minus 1.7 mm, nearest point of the whole route to each named head/neck part (scratch/part_dist_q0.py). Inside/outside comes from the nearest face normal, which fails far from the surface on non-convex parts: designed/hybrid speaker_tape -99.5 and motor13 -53.06, and hybrid neck_pitch -3.0, are such artefacts (the motion model gives motor13 0.28 for the designed route at rest and nothing closer than motor11 0.47 for the hybrid at rest). Use the motion-model partMin for cross-body parts; use this table for the head-fixed parts (speaker, retainer, amplifier, Pi, camera, clips).',
                              'values': (json.load(open(os.path.join(HERE, 'part_dist_q0.json'))) if os.path.exists(os.path.join(HERE, 'part_dist_q0.json')) else 'job did not complete')},
       'routes': routes}
json.dump(out, open(OUT, 'w'), indent=1)
for r, v in routes.items():
    print(r, v['lengthAtQ0Mm'], {s: (x['slackNeededMm'], x['minClearanceMm'], x['pinchPart'], x['complete']) for s, x in v['summary'].items()}, v['rollWindow'])
