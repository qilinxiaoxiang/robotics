#!/usr/bin/env python3
"""Step 7: assemble findings.json from the measured outputs of steps 1-6.

Every number comes from the JSON written by the measuring scripts; this script adds the classification,
explanation and fix text. Classes: a = real design interference, b = guide data error, c = intended contact,
d = display-mesh artifact.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
J = lambda n: json.loads((HERE / n).read_text())  # noqa: E731
DEPTH = 0.1

pairs_src = J('pairs-raw.json')
pairs_disp = J('pairs-display.json')
cables_raw = J('cables-raw.json')
steps_raw = J('steps-raw.json')
search = J('approach-search.json')
whatif = {r['scenario']: r for r in J('whatif.json')}
cfix = {r['cable']: r for r in J('cable-fix.json')['cables']}
tray = J('tray-port.json')
pishift = J('pi-shift.json')
swing = J('cap-swing.json')


def r(x, n=2):
    return round(float(x), n)


def loc(p):
    comps = sorted(p.get('components', []), key=lambda c: -c['volumeMm3'])
    if not comps:
        return None
    lo = [min(c['bounds'][0][i] for c in comps) for i in range(3)]
    hi = [max(c['bounds'][1][i] for c in comps) for i in range(3)]
    return {'largestComponentCentroid': comps[0]['centroid'], 'components': len(comps), 'bounds': [lo, hi]}


# ---------------------------------------------------------------- final-scene part pairs
from pair_classes import PAIR_TEXT, pair_class  # noqa: E402


src_vol = {frozenset([p['a'], p['b']]): p['volumeMm3'] for p in pairs_src['pairs']}
out_pairs = []
for p in sorted(pairs_src['pairs'], key=lambda p: -p['volumeMm3']):
    if p.get('depthMm', 0) <= DEPTH:
        continue
    cls, why, fix = pair_class(p['a'], p['b'])
    out_pairs.append({'a': p['a'], 'b': p['b'], 'depthMm': p['depthMm'], 'volumeMm3': r(p['volumeMm3']), 'location': loc(p),
                      'method': 'exact boolean (manifold3d) on closed source solids', 'class': cls, 'explanation': why, 'fix': fix})
DISPLAY_FIX = ('build_guide_data.py: motor12 and motor14 are decimated to a mesh that deviates up to 2.59 mm from the source '
               '(solids-report.json; the other XL330 motors deviate 0.018 mm). Build both from the same decimated XL330 mesh as the '
               'other motors, placed by each motor\'s sourceTransformWorld, or raise MOTOR_TARGET for these two until the two-sided '
               'deviation is <= 0.2 mm. Re-run pairs_display.py: these overlaps must drop to 0.')
for p in sorted(pairs_disp['pairs'], key=lambda p: -p['volumeMm3']):
    if p.get('depthMm', 0) <= DEPTH:
        continue
    sv = src_vol.get(frozenset([p['a'], p['b']]), 0.0)
    if sv > 0.01:
        continue  # already reported from the source solids
    out_pairs.append({'a': p['a'], 'b': p['b'], 'depthMm': p['depthMm'], 'volumeMm3': r(p['volumeMm3']), 'location': loc(p),
                      'method': 'exact boolean on the viewer display meshes (closed); source-solid overlap volume 0', 'class': 'd',
                      'explanation': f'Only the decimated viewer mesh enters {p["b"] if "motor" in p["a"] else p["a"]}; the source solids '
                                     f'do not overlap ({r(sv, 3)} mm3). See png/06-motor14-display-decimation.png.',
                      'fix': DISPLAY_FIX})

# ---------------------------------------------------------------- cables
TERMINAL = {  # (cable, part, end) -> why the end inside the part is intended
    ('dxl-r5', 'openrb_board', 'start'): 'Plug end in the OpenRB -Y side header mouth.',
    ('dxl-l10', 'openrb_board', 'start'): 'Plug end in the OpenRB +Y side header mouth.',
    ('vin20', 'regulator', 'start'): 'Pigtail soldered to the DFR1202 VIN/GND pads.',
    ('vin20', 'xt30_robot', 'end'): 'Wire enters its XT30 male housing.',
    ('tether', 'xt30_robot', 'start'): 'Tether leaves its mating XT30 female.',
    ('vout', 'regulator', 'start'): 'Soldered to the DFR1202 5 V/GND pads.',
    ('vout', 'junction_j', 'end'): 'Terminates in star junction J.',
    ('feed-r', 'junction_j', 'start'): 'Leaves star junction J.',
    ('feed-l', 'junction_j', 'start'): 'Leaves star junction J.',
    ('feed-n', 'junction_j', 'start'): 'Leaves star junction J.',
    ('orb-pwr', 'junction_j', 'start'): 'Leaves star junction J.',
    ('pi-trunk', 'junction_j', 'start'): 'Leaves star junction J.',
    ('uart', 'openrb_board', 'start'): 'Soldered to OpenRB J12 pads 3 and 4.',
}
ROUTE_OF = {'dxl-r5': 'dxl5 (guide path index i = routes.json index i-1; path[0] is the port mouth)',
            'dxl-l10': 'dxl10 (guide path index i = routes.json index i-1)', 'dxl-n12': 'dxl12 (guide path index i = routes.json index i-1)',
            'uart': 'uart_lower (guide path 1..5 = uart_lower 0..4; later points are the shared trunk/bundle routes, offset)',
            'orb-pwr': 'openrbpwr', 'i2s': 'head_i2s', 'dxl-14-15': 'ttl-15-14', 'dxl-11-13': 'ttl-13-11'}


def cable_fix_text(cid):
    c = cfix.get(cid)
    if not c:
        return 'Move the route waypoints of these segments clear of the part by radius + 0.5 mm (not computed).'
    moves = '; '.join(f"routes.json {m['route']}[{m['index']}]: {m['from']} -> {m['to']}" for m in c['waypointMoves'])
    after = c['midRouteFindingsAfter']
    worst = max([f['depthMm'] for f in after], default=0)
    state = ('re-verified: no mid-route penetration > 0.1 mm remains (drawn spline and polyline)' if not after else
             f're-verified: {len(after)} mid-route finding(s) remain, deepest {worst} mm ({", ".join(sorted({f["part"] for f in after}))})')
    return f'{moves}. Clearance target tube radius + 0.5 mm; {state}; polyline length {c["polylineLengthMm"][0]} -> {c["polylineLengthMm"][1]} mm.'


dr = [f for f in cables_raw['findings'] if f['mode'] == 'drawn-spline']
pl = [f for f in cables_raw['findings'] if f['mode'] == 'polyline']


def same(f, L):
    return any(g['cable'] == f['cable'] and g['part'] == f['part'] and set(g['segments']) & set(f['segments']) for g in L)


out_cables = []
for f in dr + [x for x in pl if not same(x, dr)]:
    key = (f['cable'], f['part'], f['atEnd'])
    poly = next((g for g in pl if g['cable'] == f['cable'] and g['part'] == f['part'] and set(g['segments']) & set(f['segments'])), None)
    rec = {'cable': f['cable'], 'segment': f['segments'], 'part': f['part'], 'depthMm': f['depthMm'],
           'polylineDepthMm': poly['depthMm'] if poly and f['mode'] == 'drawn-spline' else None,
           'shownInViewer': f['mode'] == 'drawn-spline', 'centrelineInsideMm': f['centrelineInsideMm'], 'deepestPoint': f['deepestPoint'],
           'atEnd': f['atEnd'], 'route': ROUTE_OF.get(f['cable'])}
    if key in TERMINAL:
        rec.update({'class': 'c', 'explanation': TERMINAL[key], 'fix': 'No change.'})
    elif f['cable'] == 'vout' and f['part'] == 'fuse_main':
        rec.update({'class': 'c', 'explanation': 'The 10 A main fuse holder is spliced into vout; the fuse envelope is placed on the vout '
                    'route, so vout runs through its own fuse.', 'fix': 'No change.'})
    elif f['part'] == 'openrb_tray' and f['cable'] in ('dxl-r5', 'dxl-l10'):
        side = '-Y port (link R, dxl-r5)' if f['cable'] == 'dxl-r5' else '+Y port (link L, dxl-l10)'
        t = tray['sides'][side]
        rec.update({'class': 'a', 'explanation': (
            f'The first segment leaves the OpenRB side header and runs straight through the tray side rail. The rail inner face is '
            f'{t["mouthToRailInnerFaceMm"]} mm outside the header mouth and covers {t["mouthWidthBlockedByRailMm"]} mm of its 10 mm width '
            f'over the full mouth height, so no plug can be seated (assumed plug + wire-exit envelope overlaps the tray by '
            f'{t["plugEnvelopeVsTrayMm3"]} mm3). The guide tells the builder to plug links R and L into these ports.'),
            'fix': ('Printed-part change, reprint openrb_tray: cut each side rail at x -66.2..-58.0 (to its front end), |y| 13.0..15.7, '
                    'from z -49.4 up (print/tray/tray.py: subtract this box after the rails are unioned). Checked on the notched tray: '
                    f'plug envelope overlap {t["plugEnvelopeVsNotchedTrayMm3"]} mm3, cable segment 0 depth '
                    f'{t.get("cableSeg0DepthMm", {}).get("notched")} mm (was {t.get("cableSeg0DepthMm", {}).get("current")} mm). '
                    f'The rail keeps {tray["railAtNotch"]["heightMm"]} of {tray["railAtNotch"]["fullRailHeightMm"]} mm height at the notch; '
                    'its stiffening effect there was not computed.')})
    else:
        rec.update({'class': 'b', 'explanation': (
            f'Route shortcut: the drawn tube passes {f["depthMm"]} mm into {f["part"]}'
            + (f' with {f["centrelineInsideMm"]} mm of centreline inside the solid' if f['centrelineInsideMm'] else '')
            + ('' if f['mode'] == 'drawn-spline' else ' (raw polyline only; the drawn spline clears it)')
            + '. The A* routes were searched on 1 mm voxels without the tube radius or the guide envelopes (J, fuse); a real cable '
              'lies against the part instead.'),
            'fix': cable_fix_text(f['cable']) if f['mode'] == 'drawn-spline' else (
                'No viewer change: the drawn spline clears the part. Only the raw route polyline, in the bundle route shared with the '
                'other head wires, cuts this corner; leave it unless cut lengths are taken from the raw polyline.')})
    out_cables.append(rec)

# ---------------------------------------------------------------- steps
st = {s['step']: s for s in steps_raw['steps']}
srch = {(s['step'], json.dumps(s['movers'])): s for s in search}


def coll(step, mover=None):
    cs = [c for c in st[step]['pathCollisions'] if mover is None or c['moving'] == mover]
    agg = {}
    for c in cs:
        a = agg.setdefault(c['obstacle'], [0, 0])
        a[0] = max(a[0], c['maxExcessVolumeMm3'])
        a[1] = max(a[1], c['worst']['thicknessMedianMm'])
    return ', '.join(f'{o} {r(v[0], 1)} mm3 / {r(v[1], 2)} mm' for o, v in sorted(agg.items(), key=lambda kv: -kv[1][0]))


def wi(sid):
    w = whatif.get(sid)
    if not w:
        return f'{sid}: not run'
    if w['clean']:
        return f'{sid}: clean'
    return f'{sid}: ' + ', '.join(f'{k} {v["excessMm3"]} mm3 / {v["thicknessMm"]} mm' for k, v in w['collisions'].items())


def best(step, movers):
    s = srch.get((step, json.dumps(movers)))
    if not s:
        return 'not searched'
    b = s['bestClosestToOriginal']
    return (f'{s["directionsTried"]} straight vectors screened, {s["cleanCount"]} clean; best {b["vector"]} '
            f'({b["check41"]["excessVolumeMm3"]} mm3 at 41 samples' + (f', {", ".join(b["check41"]["obstacles"])}' if b['check41']['obstacles'] else '') + ')')


out_steps = []


def S(step, cls, issue, fix, evidence):
    out_steps.append({'step': step, 'class': cls, 'issue': issue, 'fix': fix, 'evidence': evidence})


pd = st['pd-tether']
S('pd-tether', 'b', f'Bench step draws the torso before chapter 3 installs it ({", ".join(pd["drawnButNotPresent"])}) and '
  f'{len(pd["robotContextDrawnWithBench"])} robot parts around the bench harness, so the XT30 looks mounted on the robot.',
  "steps.py pd-tether: context=[] (the tether is soldered on the bench).", 'steps-raw.json drawnButNotPresent / robotContextDrawnWithBench')
sv = st['servo-ids']
S('servo-ids', 'b', f'Bench step draws ID11-ID15 and the OpenRB at their robot poses with both legs as context '
  f'({len(sv["robotContextDrawnWithBench"])} robot parts), suggesting they are already mounted.',
  'steps.py servo-ids: context=[].', 'steps-raw.json robotContextDrawnWithBench')
S('converter (chapter 3 to the end)', 'b', 'xt30_robot is added only in bench steps (pd-tether, splices, bench-test) and never '
  'installed, so it is missing from every robot step after the harness chapter while the vin20 cable is drawn ending at it.',
  "steps.py converter: add=['regulator_insert', 'regulator'] + ctx.keys('xt30_robot'), approach xt30_robot [-20, 0, 0] (" +
  wi('xt30-with-converter') + ').', 'step resolution in steps_audit.py: xt30_robot absent from the installed set at close')
S('torso-base', 'b', 'torso_base [0,0,-28] and both rings rise through the installed legs: ' + coll('torso-base', 'torso_base') + '; ring10: '
  + coll('torso-base', 'ring10_torso') + '. Base and rings sit between hip-yaw motors ID10/ID5 (above, z -3..23) and the yaw brackets on '
  'their horns (below), so no straight path exists while those motors are drawn installed (' + best('torso-base', ['torso_base']) + ').',
  'Draw motor10 and motor5 as parts of this step, not of the pre-installed legs, and install in this order: rings [0, 0, 28], base '
  '[0, 0, 28], hip-yaw motors [0, 0, 28], power support [-28, 0, 0] (' + '; '.join(wi(x) for x in (
      'torso-rings-before-base-motors-off', 'torso-base-from-above-motors-off', 'hip-yaw-motors-onto-base', 'power-support-after-base'))
  + '). Instruction text must say to take ID5 and ID10 off their horns before fitting the base and to refit them after.',
  'png/07-torso-base-sandwich.png; approach-search.json; whatif.json')
S('converter', 'b', 'regulator_insert [0,0,40] and regulator [0,0,48] drop through the power support: ' + coll('converter') + '. The insert '
  'starting pose already cuts the bay roof at (-30.8, 0.1, 31.7), so the bay is closed from above; the instructions seat the converter '
  'in the insert first.',
  "group={'label': 'Converter seated in its insert', 'approach': [-40, 0, 0]} for regulator_insert + regulator (" + wi('converter-group-from-rear')
  + '), and instruction text "Slide the insert into the bay from the rear". Separate vectors fail: ' + wi('converter-regulator-from-rear') + '.',
  'steps-raw.json; whatif.json')
S('tray', 'b', 'openrb_tray [0,0,-30] rises through the lower deck: ' + coll('tray') + '. The tray drops over four deck standoffs that '
  'stand 3.3 mm above its underside, so it must be slid in lifted and then lowered; ' + best('tray', ['openrb_tray']) + '.',
  'Two-leg approach path [[-30, 0, 4], [0, 0, 4], [0, 0, 0]] (' + wi('tray-two-stage') + '; 3 mm lift: ' + wi('tray-two-stage-lift3').split(': ')[1]
  + '). This needs the viewer to accept a waypoint list; with a straight vector only, use [-29.7, 0.8, 4.2] (least overlap).',
  'approach-search.json; whatif.json')
S('board', 'b', 'openrb_board [-30,0,0] grazes the tray front lips: ' + coll('board') + '. The real motion is front edge under the lips '
  'with the rear tilted 0.085 rad (print/tray/insertion-path.json).', "approach {'openrb_board': [-15, 0, 0]} (" + wi('board-short-slide') + ').',
  'approach-search.json; whatif.json')
S('imu-board', 'b', 'imu_sh4_receiving [-12,-8,0] passes through imu_clamp: ' + coll('imu-board') + '.',
  "approach {'imu_sh4_receiving': [-1.6, -14.3, 1.1]} (" + best('imu-board', ['imu_sh4_receiving']) + ', imu_board in place); imu_board [-24, 0, 0] unchanged ('
  + wi('imu-board-from-rear') + '). Not [0, 14.4, 0]: ' + wi('imu-plug-sideways') + '.',
  'steps-raw.json alternatives; whatif.json')
S('jaw', 'b', 'jaw_frame [30,0,0] passes through the co-added jaw_support and mouth ring: ' + coll('jaw') + '. The instructions build '
  'the jaw as one unit on the bench.', "group={'label': 'Jaw unit with ID15', 'approach': [0, 0, 30]} (" + wi('jaw-as-group-from-above') + ').',
  'approach-search.json (jaw group); whatif.json')
S('head-bottom', 'a',
  'head_bottom [0,0,-30] rises through the closed jaw: ' + coll('head-bottom') + '; ' + best('head-bottom', ['head_bottom'])
  + '. The one-piece jaw frame wraps the shell front floor (pivot arms inside the shell, beak and lower pad below it), so no order '
  'works with the released parts. Checked: ' + '; '.join(wi(x) for x in (
      'head-bottom-jaw-open-30', 'head-bottom-before-jaw-from-below', 'jaw-support-after-head-bottom', 'jaw-group-after-head-bottom',
      'moving-jaw-after-shell-and-support', 'moving-jaw-swing-in-after-shell')) + ' (straight-direction screens: '
  + ', '.join(f"{x} {whatif[x].get('cleanStraightDirections')}/32 clean" for x in ('jaw-group-after-head-bottom', 'moving-jaw-after-shell-and-support'))
  + '). This agrees with the negative control in head-redesign-20261008/jaw-access/negative-control.json (unsplit jaw rejected).',
  'Printed-part change (reprint 4 parts), from the existing candidate head-redesign-20261008/jaw-access/: split the jaw at world '
  'Y = -30 into jaw_main and a passive cheek joined by two M2.5x8 TAP screws, with internal relief in lower_pad_jaw_access and '
  'head_bottom_clearance (outer surfaces unchanged). Guide order then becomes: shell from below (verified here: '
  + wi('head-bottom-before-jaw-from-below').split(': ')[1] + '), ID15 in the support from above (' + wi('jaw-support-after-head-bottom').split(': ')[1]
  + '), jaw main + pad from the motor side at 30 deg open, cheek from the passive side, two screws. The candidate\'s own report '
  'leaves material, strength and physical fit unverified; re-run this audit on its STLs before release.',
  'png/04-head-bottom-approach-through-jaw.png; whatif.json; head-redesign-20261008/README.md "Jaw and lower-shell access"')
S('face', 'b', 'face_panel [40,0,0] slides through the head_bottom lip: ' + coll('face') + '.',
  "approach {'face_panel': [0, 0, 40]} (" + wi('face-from-above') + '); eye_trim [50, 0, 0] after the face: ' + wi('eye-trim-after-face').split(': ')[1] + '.',
  'steps-raw.json alternatives; whatif.json')
S('camera', 'b', 'camera_retainer [-30,0,0] starts inside jaw_support and passes through the three clamp screws drawn at their final '
  'pose: ' + coll('camera') + '.', "approach {'camera_retainer': [-22.5, 0, 0], 'camera_clamp_screw_1': [-10, 0, 0], "
  "'camera_clamp_screw_2': [-10, 0, 0], 'camera_clamp_screw_3': [-10, 0, 0]}; the screw heads sit behind the retainer, so they are "
  "driven forward into the face (" + wi('camera-retainer-short') + '; ' + wi('camera-screws-from-rear') + '; from the front fails: '
  + wi('camera-screws-from-front').split(': ')[1] + ').', 'approach-search.json; whatif.json')
S('speaker', 'b', 'On the bench the cap lies roof down, which is +z in the robot frame; speaker, keeper and cradle come from +z through '
  'the roof: ' + coll('speaker') + '. The instructions trap the speaker in the cage before fixing it.',
  "group={'label': 'Speaker cage', 'approach': [0, 0, -20]} (" + wi('speaker-cage-down') + ').', 'whatif.json')
S('amp', 'b', 'amplifier [0,0,20] comes through the cap roof: ' + coll('amp') + '.', "approach {'amplifier': [0, 0, -20]} (" + wi('amp-down') + ').', 'whatif.json')
S('pi', 'b', 'Pi group [0,0,25] comes through the cap roof: ' + coll('pi') + '.', "group approach [0, 0, -25] (" + wi('pi-group-down') + ').', 'whatif.json')
pis = {(c['dx'], c['clipX']): c for c in pishift['candidates']}
p0, p1, p2 = pis[(-4.6, None)], pis[(-4.6, 52.6)], pis[(-4.6, 53.6)]
sw = '; '.join(f"pivot x {w['pivotXZ'][0]}, z {w['pivotXZ'][1]}, {w['theta0Deg']} deg: "
               + ', '.join(f'{k} {v["excessMm3"]} mm3' for k, v in w['collisions'].items()) for w in swing)
S('cap-on', 'a', 'Lowering the populated cap [0,0,40] carries the 2x20 housing, already plugged on the Pi header, through the camera stack '
  'that hangs over it (housing front x 78.97; clamp screws from x 74.88, board 75.13, retainer 75.48, face lip 77.1): ' + coll('cap-on')
  + '; ' + best('cap-on', 'group') + '. Without the housing the cap goes on cleanly, but the housing cannot be plugged after the cap '
  'is down, the face cannot go on after the cap, and no rear-then-forward path exists because the Pi rail sits 3.2 mm in front of '
  'jaw_support (x 52.3) and motor15. Checked: ' + '; '.join(wi(x) for x in (
      'cap-on-without-gpio', 'gpio-after-cap-along-pins', 'cap-on-face-absent', 'face-camera-unit-after-cap', 'cap-on-dogleg-back3',
      'cap-on-dogleg-back5', 'cap-on-dogleg-back5-high')) + '; cap tilted rear-up and swung closed about a front axis (cap-swing.json): '
  + sw + '. The design\'s own closure check (head-redesign-20261008/current-closure/shell-closure-summary.json) held the Pi, header '
  'and housing envelopes fixed while only the cap shell moved, so it did not cover this case.',
  'Printed-part change, reprint head_cap: seat the Pi 4.6 mm further back. Move both Pi rails (x 55.5..62.0, |y| 25.8..32.2, '
  'z 114.4..143.6) and both upper posts (|y| 7.95..12.55, z 141.7..145.0) by [-4.6, 0, 0], then trim the moved features to x >= 52.8 '
  '(0.5 mm clear of jaw_support). Checked in pi-shift.json: the moved Pi group and features have no new final-pose overlap '
  f'({p1["finalPoseNewOverlap"] or "none"}), stay inside the cap hull, and the descent of the modified populated cap is clean with '
  f'the trim at x 52.6 ({p1["descentClean"]}) and at x 53.6 ({p2["descentClean"]}); x 52.8 removes more than the 52.6 case, so it '
  'cannot add a collision. Without the trim the moved rail sweeps through jaw_support (' + ', '.join(
      f'{k} {v["excessMm3"]} mm3' for k, v in p0['descentCollisions'].items()) + '). Housing front to camera screws after the shift: '
  '0.5 mm. Guide data after the reprint: move pi, the header, the Pi components and the GPIO receiving envelopes by [-4.6, 0, 0] in '
  'build_guide_data.py and the cable ends at the housing (pi-trunk, imu, uart, i2s) by the same amount. Not checked: CSI ribbon slack '
  '(flexible, 200 mm), Pi USB plug access (usb-access study), the four M2.5 screw bosses in the trimmed rails, rail stiffness.',
  'png/05-cap-on-gpio-through-camera.png; whatif.json; pi-shift.json; cap-swing.json')
S('close', 'b', 'upper_pad [30,0,0] slides through the closed jaw and the shell: ' + coll('close') + '; ' + best('close', ['upper_pad'])
  + '. The pad sits between the shell front floor and the lower pad, so it can only go in with the jaw open.',
  'Show the jaw opened 30 deg about its ring axis (jaw_frame and lower_pad rotated +30 deg about +y through x 26.1, z 118.62) and '
  "approach {'upper_pad': [0, 0, -15]} (" + wi('upper-pad-jaw-open-30-below') + '; then the jaw closing 30 -> 0 deg onto the pad: '
  + wi('upper-pad-swing-check-jaw-closed-on-pad').split(': ')[1] + '). This needs a per-step part rotation in the viewer. From the '
  'front it still fails with the jaw open: ' + wi('upper-pad-jaw-open-30-front').split(': ')[1] + '. Matches head-redesign-20261008/README.md: '
  'final shell fastening requires a 30 deg open jaw and the upper pad absent.', 'whatif.json')

findings = {'pairs': out_pairs, 'cables': out_cables, 'steps': out_steps}
(HERE / 'findings.json').write_text(json.dumps(findings, indent=1, ensure_ascii=False))
from collections import Counter  # noqa: E402
print('pairs', Counter(p['class'] for p in out_pairs), 'cables', Counter(c['class'] for c in out_cables),
      'steps', Counter(s['class'] for s in out_steps))
