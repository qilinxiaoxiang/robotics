#!/usr/bin/env python3
"""Collect the V1.8 head audit results (no geometry): every pairs / cables / steps finding that involves a head part,
with the intended-contact classification for the known seams, plus the registration and screw-probe results.
Reads pairs-raw.json, cables-raw.json, steps-raw.json, solids-report.json, v18-registration.json,
v16-registration.json and camera-screws-v18.json; writes v18-audit.json and prints the head findings.
"""
from __future__ import annotations

import json

from ia_lib import HERE, load_guide

HEAD_MODULES = {'head', 'head-close', 'camera', 'electronics'}
HEAD_EXTRA = {'motor14'}
PAIR_THRESH = 0.1

# Intended contacts in the head (class c in findings.json): (a, b) unordered.
INTENDED = {
    frozenset(('head_bottom', 'head_cap')): 'cap seam: the cap rim sits in the lower-shell seat',
    frozenset(('face_panel', 'eye_trim')): 'eye trim pressed into the face opening (push fit, pegs and key in their holes)',
    frozenset(('face_panel', 'head_bottom')): 'face bottom edge standing on the lower-shell rim',
    frozenset(('face_panel', 'camera_board')): 'camera PCB on the four face lands; the two locating pegs in the board holes',
    frozenset(('speaker', 'speaker_cradle')): 'speaker rim in its cradle',
    frozenset(('speaker', 'speaker_keeper')): 'speaker rim under its keeper',
    frozenset(('jaw_frame', 'mouth_sliding_ring')): 'sliding ring pressed on the jaw arm boss',
    frozenset(('jaw_support', 'motor15')): 'ID15 clamped in the jaw support pocket',
    frozenset(('head_bottom', 'motor15')): 'ID15 clamped by the lower shell',
    frozenset(('head_bottom', 'motor14')): 'ID14 case resting in the lower shell',
    frozenset(('jaw_support', 'motor14')): 'ID14 case under the jaw support',
    frozenset(('jaw_support', 'mouth_sliding_ring')): 'sliding ring in its support seat',
    frozenset(('pi', 'head_pi_zero_w_header_base')): 'header soldered to the Pi',
    frozenset(('head_pi_zero_w_header_base', 'head_pi_zero_w_gpio_solder_tails')): 'header pins through their base',
    frozenset(('pi', 'head_pi_zero_w_gpio_solder_tails')): 'header pins through the Pi board',
}


def is_head(key, mods):
    return mods.get(key) in HEAD_MODULES or key in HEAD_EXTRA


def main():
    g = load_guide()
    mods = {p['key']: p['module'] for p in g['parts']}
    out = {'guideRevision': g.get('revision'), 'headModules': sorted(HEAD_MODULES | HEAD_EXTRA)}

    pr = json.loads((HERE / 'pairs-raw.json').read_text())
    pairs = []
    for r in pr['pairs']:
        if r['volumeMm3'] <= 1e-6 or not (is_head(r['a'], mods) or is_head(r['b'], mods)):
            continue
        key = frozenset((r['a'], r['b']))
        pin_pair = {r['a'], r['b']}
        pin_contact = (any(k.startswith('head_pi_zero_w_header_pin_') for k in pin_pair)
                       and any(k.startswith('head_pi_gpio_pin_') or k in ('head_pi_zero_w_header_base', 'head_pi_zero_w_gpio_solder_tails', 'pi') for k in pin_pair))
        why = INTENDED.get(key) or ('header pin in its soldered base / jumper-wire end on its pin' if pin_contact else None)
        pairs.append({'a': r['a'], 'b': r['b'], 'volumeMm3': round(r['volumeMm3'], 4), 'depthMm': r.get('depthMm', 0.0),
                      'over0.1': r.get('depthMm', 0.0) > PAIR_THRESH, 'intended': why,
                      'components': [{k: c[k] for k in ('volumeMm3', 'centroid', 'bounds', 'thicknessMedianMm')} for c in r.get('components', [])[:3]]})
    pairs.sort(key=lambda p: -p['depthMm'])
    out['pairs'] = {'candidatePairs': pr['candidatePairs'], 'headOverlapping': len(pairs),
                    'headOver0.1': [p for p in pairs if p['over0.1']], 'headUnder0.1': [{k: p[k] for k in ('a', 'b', 'volumeMm3', 'depthMm', 'intended')} for p in pairs if not p['over0.1']]}

    cr = json.loads((HERE / 'cables-raw.json').read_text())
    cab = [f for f in cr['findings'] if is_head(f['part'], mods) or f['cable'] in ('csi', 'i2s', 'spk', 'pi-trunk', 'imu', 'uart')]
    out['cables'] = {'cablesChecked': len(cr['coverage']), 'allFindings': len(cr['findings']),
                     'headFindings': cab, 'midRouteHeadFindings': [f for f in cab if f['atEnd'] is None]}

    sr = json.loads((HERE / 'steps-raw.json').read_text())
    steps = []
    for s in sr['steps']:
        head_step = s['chapter'] in ('head', 'head-elec', 'bundle', 'power-up') or any(is_head(k, mods) for k in s.get('add', []))
        if not head_step:
            continue
        steps.append({'step': s['step'], 'chapter': s['chapter'], 'bench': s['bench'], 'add': s['add'], 'approach': s.get('approach'),
                      'drawnButNotPresent': s.get('drawnButNotPresent', []), 'pathCollisions': s.get('pathCollisions', []),
                      'heldPoseOverlaps': s.get('heldPoseOverlaps', [])})
    out['steps'] = {'stepsChecked': len(sr['steps']), 'premature': sum(bool(s.get('drawnButNotPresent')) for s in sr['steps']),
                    'pathCollisionsAll': sum(len(s['pathCollisions']) for s in sr['steps']),
                    'headSteps': steps,
                    'headStepsWithCollisions': [s for s in steps if s['pathCollisions'] or s['drawnButNotPresent'] or s['heldPoseOverlaps']]}

    sol = json.loads((HERE / 'solids-report.json').read_text())
    out['solids'] = {'parts': sol['parts'], 'closed': sol['closed'], 'notClosed': sol['notClosed'],
                     'headSources': {r['key']: {'source': r['source']['kind'], 'closure': r['closure'][:60], 'volumeMm3': r.get('volumeMm3'),
                                                'displayVsSolidMaxMm': max(r['displayVsSolid']['displayToSolidMaxMm'], r['displayVsSolid']['solidToDisplayMaxMm'])}
                                     for r in sol['records'] if r['key'] in ('face_panel', 'eye_trim', 'head_bottom', 'head_cap', 'camera_board', 'pi')}}
    for name in ('v18-registration.json', 'v16-registration.json', 'camera-screws-v18.json'):
        p = HERE / name
        if p.exists():
            d = json.loads(p.read_text())
            if name == 'v16-registration.json':
                out['registrationV16'] = {'parts': len(d), 'same': sum(bool(r.get('guideShowsReleasedGeometry')) for r in d),
                                          'superseded': [r['key'] for r in d if r.get('supersededBy')],
                                          'notSame': [r['key'] for r in d if not r.get('guideShowsReleasedGeometry') and not r.get('supersededBy')]}
            elif name == 'v18-registration.json':
                out['registrationV18'] = d
            else:
                out['screws'] = {k: {kk: v[kk] for kk in ('engagementMm', 'pilotDiameterRangeMm', 'tipMarginMm', 'tipPart', 'intrusions', 'headClash',
                                                          'driverClearAtStepMm', 'driverClearOnRobotMm', 'driverRobotObstacle', 'preEngagementContact', 'checks')}
                                 for k, v in d['screws'].items() if not k.startswith('_')}
                out['screws']['_cameraBoardToJumperEnds'] = d['screws'].get('_cameraBoardToJumperEnds')
    (HERE / 'v18-audit.json').write_text(json.dumps(out, indent=1))
    print('pairs over 0.1 involving head parts:')
    for p in out['pairs']['headOver0.1']:
        print(f"  {p['a']} x {p['b']}: depth {p['depthMm']} mm, {p['volumeMm3']} mm3, {'intended: ' + p['intended'] if p['intended'] else 'NOT CLASSIFIED'}")
    print('head cable findings:', [(f['cable'], f['mode'], f['part'], f['segments'], f['depthMm'], f['atEnd']) for f in cab])
    print('head steps with problems:', [(s['step'], [c['moving'] + '>' + c['obstacle'] + f" {c['maxExcessVolumeMm3']}" for c in s['pathCollisions']], s['drawnButNotPresent']) for s in out['steps']['headStepsWithCollisions']])
    print(json.dumps({'solids': {k: out['solids'][k] for k in ('parts', 'closed', 'notClosed')}, 'registrationV16': out.get('registrationV16'),
                      'v18same': [(r['key'], r['guideShowsWorldFile']) for r in out.get('registrationV18', {}).get('parts', [])]}))


if __name__ == '__main__':
    main()
