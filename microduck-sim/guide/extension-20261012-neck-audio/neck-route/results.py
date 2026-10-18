#!/usr/bin/env python3
"""Collect the study's headline measurements into neck-route-results.json (one place for the README numbers).

Reads the outputs of the other scripts (it computes nothing new except file hashes) and records, for every V1.8 world
file, whether its sha256 still matches print/world/v18-sources.json (the study must leave V1.8 untouched).
Rerun order: make_nonotch_cap.py, occ.py, occ.py cables, corridor_search.py [cables], corridor.py [cables], kin_check.py,
sections.py, motion.py, yaw_slack.py, jaw_check.py, connector_fit.py, disconnect.py, loop_space.py, figures.py,
results.py (all but yaw_slack.py and results.py under run_bounded_cad.py).
"""
import hashlib
import json
import sys

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import HERE, WORLD, jdump  # noqa: E402


def load(name):
    p = HERE / name
    return json.loads(p.read_text()) if p.exists() else None


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    cap = load('nonotch-cap.json')
    corr = load('corridors.json')
    sec = load('sections.json')['sections']
    mot = load('motion.json')
    fit = load('connector-fit.json')
    dc = load('disconnect.json')
    kin = load('kin-check.json')
    src = json.loads((WORLD / 'v18-sources.json').read_text())['files']
    v18 = {f: {'recorded': r.get('sha256'), 'now': sha(WORLD / f), 'unchanged': sha(WORLD / f) == r.get('sha256')}
           for f, r in src.items() if (WORLD / f).exists()}
    out = {
        'studyDate': '2026-10-12',
        'frame': 'robot frame mm (x forward, y left, z up), MJCF trunk_base at q = 0',
        'scripts': ['nr_lib.py', 'make_nonotch_cap.py', 'occ.py', 'corridor_search.py', 'corridor.py', 'kin_check.py',
                    'sections.py', 'motion.py', 'yaw_slack.py', 'jaw_check.py', 'connector_fit.py', 'disconnect.py',
                    'loop_space.py', 'figures.py', 'results.py'],
        'v18FilesUnchanged': all(v['unchanged'] for v in v18.values()),
        'v18Files': v18,
        'notchlessCap': {k: cap.get(k) for k in ('xorOutsideEditBoxMm3', 'notchMaterialRestoredMm3', 'hoodMaterialRemovedMm3', 'seamShellXorMm3_0p6mm',
                                                  'volumes', 'output')} if cap else None,
        'corridors': {k: {'exactNarrowestRadiusMm': v.get('exactNarrowestRadiusMm'), 'narrowestAt': v.get('narrowestAt'),
                          'boundedBy': v.get('boundedBy')} for k, v in (corr or {}).items() if isinstance(v, dict) and 'exactNarrowestRadiusMm' in v},
        'sections': {k: {'plane': v['plane'], 'label': v['label'],
                         'q0DiameterWithCablesMm': v['q0']['withExistingCables'].get('diameterMm'),
                         'q0DiameterPartsOnlyMm': v['q0']['partsOnly'].get('diameterMm'),
                         'q0BoundedBy': v['q0']['withExistingCables'].get('boundedBy'),
                         'minDiameterWithCablesPolicyRollMm': round(2 * v['minWithCablesPolicyMm'], 2),
                         'minDiameterPartsOnlyPolicyRollMm': round(2 * v['minPartsOnlyPolicyMm'], 2),
                         'capacityQ0': v['q0'].get('capacityWithExistingCables'),
                         'capacityWorstPolicyRoll': (v.get('worstPolicyRoll') or {}).get('capacityWithExistingCables')}
                     for k, v in sec.items()},
        'motion': {r: {'lengthAtQ0Mm': v['lengthAtQ0Mm'],
                       'slackNeededMm': {s: x['slackNeededMm'] for s, x in v['sets'].items()},
                       'perFreeSpanSlackMm': {s: [{'span': f"{f['from']} -> {f['to']}", 'slackMm': f['slackNeededMm'], 'worstPoseDeg': f['worstPoseDeg']}
                                                  for f in x['freeSpans']] for s, x in v['sets'].items()},
                       'pinch': {s: x['pinch'] for s, x in v['sets'].items()},
                       'perSegment': {s: x.get('perSegment') for s, x in v['sets'].items()}}
                   for r, v in (mot or {}).items() if not r.startswith('_')},
        'connectorFit': {k: {'atQ0': v['atQ0'], 'threadingPose': v['threadingPose'], 'worstPolicyRoll': v['worstPolicyRoll'],
                             'housingFitsAtSomeRoll': v['housingFitsAtSomeRoll']} for k, v in (fit or {}).get('passages', {}).items()},
        'inlineDisconnect': {'envelope': dc.get('envelope'), 'chosen': dc.get('chosen'),
                             'candidates': [{k: c[k] for k in ('orientation', 'centreQ0', 'sizeMm', 'clearAllSets', 'clearPolicyAndPickup')} | {
                                 'sets': {s: {k: x[k] for k in ('overlapPoses', 'minGapMm', 'minGapPart')} for s, x in c['sets'].items()}}
                                 for c in dc.get('candidates', [])]} if dc else None,
        'jawVsNeckWires': load('jaw-check.json'),
        'yawSlack': load('yaw-slack.json'),
        'loopSpaceBesideBracket': load('loop-space.json'),
        'kinematicsCheck': {k: kin.get(k) for k in list(kin)[:6]} if kin else None,
        'labels': {'measurement': 'every number above is computed by the listed scripts from the closed audit solids, '
                                  'the MJCF and the guide cable paths',
                   'inference': 'connector outlines other than the 2.54 mm Dupont pitch, wire diameters, clip and screw '
                                'suggestions, and every judgement in the README marked (inference)'},
    }
    jdump(out, HERE / 'neck-route-results.json')
    print('v18 unchanged:', out['v18FilesUnchanged'], {f: v['unchanged'] for f, v in v18.items()})


if __name__ == '__main__':
    main()
