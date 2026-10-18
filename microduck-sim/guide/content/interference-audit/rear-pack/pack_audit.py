#!/usr/bin/env python3
"""Collect the V1.8 rear-pack audit results (no geometry): every pairs / cables / steps finding that involves a torso
part or a torso cable, with the intended-contact classification for the pack seams, plus the registration of the
pack, cover, upright OpenRB and turned IMU display meshes against their print/world files. Reads the chain outputs in
the parent directory (pairs-raw.json, cables-raw.json, steps-raw.json, solids-report.json, v18-registration.json,
v16-registration.json) and print/rear-pack/checks.json; writes pack-audit.json next to this script and prints the
torso findings. This file is the incremental evidence referenced by the V1.8 release rows for rear_pack and
rear_pack_cover.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent
sys.path.insert(0, str(AUDIT))
from ia_lib import load_guide  # noqa: E402

GUIDE = AUDIT.parents[1]
CHECKS = GUIDE / 'print/rear-pack/checks.json'
PAIR_THRESH = 0.1

TORSO_MODULES = {'torso', 'controller', 'electronics', 'harness', 'power', 'imu'}
TORSO_PARTS = {'rear_pack', 'rear_pack_cover', 'openrb_board', 'regulator', 'xt30_robot', 'imu_board', 'imu_sh4_receiving',
               'torso_base', 'motor10', 'motor5', 'shell_left', 'shell_right', 'motor12'}
TORSO_CABLES = {'dxl-r5', 'dxl-l10', 'dxl-n12', 'vin20', 'tether', 'orb-pwr', 'pi-trunk', 'imu', 'uart'}
TORSO_STEPS = {'pack-in', 'torso-fasten', 'leg-join', 'board', 'orb-power', 'converter', 'converter-plug', 'leg-links',
               'imu-board', 'imu-plug', 'pack-cover', 'neck-lower-in', 'shells', 'unpowered'}

# Intended contacts around the pack (class c): (a, b) unordered.
INTENDED = {
    frozenset(('rear_pack', 'torso_base')): 'pack lower tabs under the torso base on the hip-yaw case screws (same tabs as the power support)',
    frozenset(('rear_pack', 'motor10')): 'pack plate and upper tab against the ID10 case',
    frozenset(('rear_pack', 'motor5')): 'pack plate and upper tab against the ID5 case',
    frozenset(('rear_pack', 'openrb_board')): 'OpenRB back face on the four pads; trimmed header tails over the plate',
    frozenset(('rear_pack', 'regulator')): 'DFR1202 envelope on the two feet, front edge behind the lips',
    frozenset(('rear_pack', 'imu_board')): 'BNO085 rear edge between the two fins, bottom edge on the shelf',
    frozenset(('rear_pack', 'rear_pack_cover')): 'cover plate on the post ends',
    frozenset(('rear_pack_cover', 'regulator')): 'cover lip over the DFR1202 top edge',
    frozenset(('imu_board', 'imu_sh4_receiving')): 'STEMMA QT plug in the BNO085 socket',
    frozenset(('rear_pack', 'shell_left')): 'left shell lower edge over the pack T-head',
    frozenset(('rear_pack', 'shell_right')): 'right shell lower edge over the pack T-head',
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    g = load_guide()
    mods = {p['key']: p['module'] for p in g['parts']}
    torso = lambda k: k in TORSO_PARTS or mods.get(k) in TORSO_MODULES
    out = {'guideRevision': g.get('revision'), 'frame': 'robot frame (mm, x forward, y left, z up)',
           'scope': 'pairs, cables and steps findings involving the rear pack, its cover and the parts it carries; registration of their display meshes'}

    pr = json.loads((AUDIT / 'pairs-raw.json').read_text())
    pairs = []
    for r in pr['pairs']:
        if r['volumeMm3'] <= 1e-6 or not (torso(r['a']) or torso(r['b'])):
            continue
        if not ({r['a'], r['b']} & {'rear_pack', 'rear_pack_cover', 'openrb_board', 'regulator', 'xt30_robot', 'imu_board', 'imu_sh4_receiving'}):
            continue
        key = frozenset((r['a'], r['b']))
        pairs.append({'a': r['a'], 'b': r['b'], 'volumeMm3': round(r['volumeMm3'], 4), 'depthMm': r.get('depthMm', 0.0),
                      'over0.1': r.get('depthMm', 0.0) > PAIR_THRESH, 'intended': INTENDED.get(key),
                      'components': [{k: c[k] for k in ('volumeMm3', 'centroid', 'bounds', 'thicknessMedianMm') if k in c} for c in r.get('components', [])[:3]]})
    pairs.sort(key=lambda p: -p['depthMm'])
    out['pairs'] = {'candidatePairs': pr['candidatePairs'], 'packOverlapping': len(pairs),
                    'packOver0.1': [p for p in pairs if p['over0.1']],
                    'packUnder0.1': [{k: p[k] for k in ('a', 'b', 'volumeMm3', 'depthMm', 'intended')} for p in pairs if not p['over0.1']],
                    'unclassifiedOver0.1': [p for p in pairs if p['over0.1'] and not p['intended']]}

    cr = json.loads((AUDIT / 'cables-raw.json').read_text())
    cab = [f for f in cr['findings'] if f['cable'] in TORSO_CABLES or torso(f['part'])]
    out['cables'] = {'cablesChecked': len(cr['coverage']), 'allFindings': len(cr['findings']), 'packFindings': cab,
                     'midRoutePackFindings': [f for f in cab if f['atEnd'] is None],
                     'coverage': {c: v for c, v in cr['coverage'].items() if c in TORSO_CABLES} if isinstance(cr['coverage'], dict) else None}

    sr = json.loads((AUDIT / 'steps-raw.json').read_text())
    steps = []
    for s in sr['steps']:
        if s['step'] not in TORSO_STEPS and not any(torso(k) for k in s.get('add', [])):
            continue
        steps.append({'step': s['step'], 'chapter': s['chapter'], 'bench': s['bench'], 'add': s['add'], 'approach': s.get('approach'),
                      'drawnButNotPresent': s.get('drawnButNotPresent', []), 'pathCollisions': s.get('pathCollisions', []),
                      'heldPoseOverlaps': s.get('heldPoseOverlaps', [])})
    out['steps'] = {'stepsChecked': len(sr['steps']), 'premature': sum(bool(s.get('drawnButNotPresent')) for s in sr['steps']),
                    'pathCollisionsAll': sum(len(s['pathCollisions']) for s in sr['steps']), 'packSteps': steps,
                    'packStepsWithProblems': [s for s in steps if s['pathCollisions'] or s['drawnButNotPresent'] or s['heldPoseOverlaps']]}

    sol = json.loads((AUDIT / 'solids-report.json').read_text())
    out['solids'] = {'parts': sol['parts'], 'closed': sol['closed'], 'notClosed': sol['notClosed'],
                     'packSources': {r['key']: {'source': r['source']['kind'], 'closure': r['closure'][:60], 'volumeMm3': r.get('volumeMm3'),
                                                'displayVsSolidMaxMm': max(r['displayVsSolid']['displayToSolidMaxMm'], r['displayVsSolid']['solidToDisplayMaxMm'])}
                                     for r in sol['records'] if r['key'] in ('rear_pack', 'rear_pack_cover', 'openrb_board', 'regulator', 'xt30_robot', 'imu_board', 'imu_sh4_receiving')}}
    for name in ('v18-registration.json', 'v16-registration.json'):
        p = AUDIT / name
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        if name == 'v16-registration.json':
            out['registrationV16'] = {'parts': len(d), 'same': sum(bool(r.get('guideShowsReleasedGeometry')) for r in d),
                                      'superseded': [r['key'] for r in d if r.get('supersededBy')], 'retired': [r['key'] for r in d if r.get('retired')],
                                      'notSame': [r['key'] for r in d if not r.get('guideShowsReleasedGeometry') and not r.get('supersededBy') and not r.get('retired')]}
        else:
            out['registrationV18'] = {'parts': [r for r in d.get('parts', []) if r['key'] in ('rear_pack', 'rear_pack_cover', 'openrb_board', 'imu_board', 'imu_sh4_receiving')],
                                      'allSame': all(r.get('guideShowsWorldFile') for r in d.get('parts', []))}

    chk = json.loads(CHECKS.read_text())
    sweep = chk.get('check5_walkingSweep', {})
    out['packChecks'] = {'file': str(CHECKS), 'sha256': sha(CHECKS),
                         'walkingSweepAdoptedMinGapMm': {side: {'pitchChain': sweep[side]['adopted']['pitchChain']['minGapMm'], 'hipBodies': sweep[side]['adopted']['hipBodies']['minGapMm']}
                                                         for side in ('left', 'right') if side in sweep},
                         'walkingSweepNote': 'run before the two subtractive edits (window lowered to z -34, cover pilots 4.8 deep); both remove material only'}
    for k in ('check1_fit', 'check2_interfaceTabs', 'check3_envelopes', 'check4_cableRooms', 'check6_assembly', 'check7_print'):
        for kk, v in chk.items():
            if kk.startswith(k.split('_')[0] + '_'):
                out['packChecks'][kk] = v.get('pass', v.get('passed')) if isinstance(v, dict) else v
    out['packChecks']['keys'] = sorted(chk.keys())

    (HERE / 'pack-audit.json').write_text(json.dumps(out, indent=1))
    print('pairs over 0.1 involving pack parts:')
    for p in out['pairs']['packOver0.1']:
        print(f"  {p['a']} x {p['b']}: depth {p['depthMm']} mm, {p['volumeMm3']} mm3, {'intended: ' + p['intended'] if p['intended'] else 'NOT CLASSIFIED'}")
    print('pack cable findings:', [(f['cable'], f['mode'], f['part'], f['segments'], f['depthMm'], f['atEnd']) for f in cab])
    print('pack steps with problems:', [(s['step'], [c['moving'] + '>' + c['obstacle'] + f" {c['maxExcessVolumeMm3']}" for c in s['pathCollisions']], s['drawnButNotPresent'], s['heldPoseOverlaps']) for s in out['steps']['packStepsWithProblems']])
    print(json.dumps({'solids': {k: out['solids'][k] for k in ('parts', 'closed', 'notClosed')}, 'registrationV16': out.get('registrationV16'),
                      'v18': out.get('registrationV18'), 'packChecks': {k: v for k, v in out['packChecks'].items() if k != 'keys'}}))


if __name__ == '__main__':
    main()
