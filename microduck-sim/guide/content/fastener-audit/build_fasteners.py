#!/usr/bin/env python3
"""Compose guide/content/fasteners.json from the screw definitions and the measured evidence in ./evidence.

Inputs (all produced by the scripts in this folder, see README.md):
  evidence/probe-full.json    probe.py --kind full   (full-resolution V1.6 meshes)
  evidence/probe-guide.json   probe.py --kind guide  (meshes the viewer draws)
  evidence/inventory.json     hole_inventory.py      (round holes 1.0-3.8 mm in printed parts and boards)
  evidence/freeplay.json      freeplay.py            (free travel of parts that have no screw)
  evidence/jaw-access.json    jaw_access.py          (front closure screws versus jaw opening)
Writes ../fasteners.json. Pure composition: no geometry is computed here.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

import screw_defs

HERE = Path(__file__).resolve().parent
EV = HERE / 'evidence'
OUT = HERE.parent / 'fasteners.json'
G = HERE.parents[1]

# Thresholds for the per-record checks (mm)
PILOT_RANGE = {'M2': (1.3, 1.8), 'M2.5': (1.9, 2.3), 'M2.6': (2.0, 2.4)}   # probe resolution ~0.1 mm
MIN_ENGAGEMENT = 1.5
RESOLUTION = 0.1
RADII = [0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.5, 1.6, 1.75, 1.9, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5]


def drange(dmin):
    """probe.py reports the largest probed radius that is void in all 8 directions; the true diameter lies between
    that and the next probed radius."""
    if dmin is None or dmin <= 0:
        return None
    r = round(dmin / 2, 3)
    nxt = [x for x in RADII if x > r + 1e-6]
    return [round(2 * r, 2), round(2 * nxt[0], 2) if nxt else None]


def dtxt(dmin):
    r = drange(dmin)
    return 'closed' if r is None else (f'{r[0]}-{r[1]} mm' if r[1] else f'>{r[0]} mm')

NOTES = {
    'S15-horn-046': 'M2 x 7 goes in the front (+x) horn hole, where the jaw frame is 4.1 mm thick. An M2 x 7 in a 3.6 mm position would go 3.4 mm into the horn, past its 3.0 mm tapped depth.',
    'S15-horn-047': 'M2 x 7 goes in the top (+z) horn hole, where the jaw frame is 4.15 mm thick.',
    'S15-horn-045': 'M2 x 6 goes in the bottom (-z) horn hole, where the jaw frame is 3.55 mm thick.',
    'S15-horn-048': 'M2 x 6 goes in the rear (-x) horn hole, where the jaw frame is 3.6 mm thick.',
    'E-imu_clamp-01': 'Pressure screw: it threads 4.0 mm through the holder and its tip bears on the fixed rail. The head stands about 1.8 mm proud when the tip touches; it never seats.',
    'E-imu_clamp-02': 'Pressure screw: it threads 4.0 mm through the holder and its tip bears on the fixed rail. The head stands about 1.8 mm proud when the tip touches; it never seats.',
    'S05-case-075': 'The right shell is modelled 0.45-0.5 mm outboard (-y): its clearance hole wall comes within 0.6 mm of the screw axis. Driving the four right-shell M2 x 6 first (the guide order) pulls the shell onto the idler and should align the hole (inference).',
    'K-head_close-01': 'Front closure screw. At rest the lower lip pad is 2.7 mm below the head; open the jaw by hand 30-35 degrees for a clear straight driver path (the jaw meets the lower shell at about 40 degrees). Fit the upper lip pad after this screw.',
    'K-head_close-02': 'Front closure screw. At rest the lower lip pad is 2.7 mm below the head; open the jaw by hand 30-35 degrees for a clear straight driver path (the jaw meets the lower shell at about 40 degrees). Fit the upper lip pad after this screw.',
    'C-camera_clamp-01': 'At the camera step a straight driver has only 32.6 mm behind this head before the jaw support; use a stubby driver or fit the camera to the face on the bench before the face goes on.',
    'E-amp-01': 'The amplifier hole is modelled 2.4-2.5 mm, a line-to-line fit for M2.5; check the real board.',
    'E-amp-02': 'The amplifier hole is modelled 2.4-2.5 mm, a line-to-line fit for M2.5; check the real board.',
    'S11-horn-033': 'Goes 3.0 mm into the ID11 horn; ROBOTIS gives the horn holes DP 3.0 max, so the tip just reaches the bottom of the tapped hole. Stop at snug.',
    'S11-horn-034': 'Goes 3.0 mm into the ID11 horn; ROBOTIS gives the horn holes DP 3.0 max, so the tip just reaches the bottom of the tapped hole. Stop at snug.',
    'S11-horn-035': 'Goes 3.0 mm into the ID11 horn; ROBOTIS gives the horn holes DP 3.0 max, so the tip just reaches the bottom of the tapped hole. Stop at snug.',
    'S11-horn-036': 'Goes 3.0 mm into the ID11 horn; ROBOTIS gives the horn holes DP 3.0 max, so the tip just reaches the bottom of the tapped hole. Stop at snug.',
    'S14-horn-049': 'On the bench a straight driver has 23 mm before the far fork arm; the guide already calls for a compact right-angle driver.',
}
for i in ('E-pi-01', 'E-pi-02', 'E-pi-03', 'E-pi-04'):
    NOTES[i] = 'M2 self-tapping into a 1.6-1.7 mm rail pilot. The Pi Zero W holes are M2.5 clearance (Raspberry Pi drawing), so M2 passes with play and its 4 mm head still bears on the board.'
for i in ('E-speaker-01', 'E-speaker-02'):
    NOTES[i] = 'Cap post pilot is 2.0-2.1 mm (M2.5 self-tapping). Tip stops 0.26 mm short of the post bottom; M2.5 x 10 would bottom out. The stack has a 2.9 mm air gap between cradle tab and keeper, so stop at snug.'
for i in ('H-jaw_support-01', 'H-jaw_support-02', 'H-jaw_support-03', 'H-jaw_support-04'):
    NOTES[i] = 'Driven from above through the jaw support base plate into the lower head shell boss (2.1-2.2 mm pilot under a 2.8 mm entry chamfer).'
for i in ('S12-rear_center-117', 'S11-rear_center-118'):
    NOTES[i] = 'Rear centre: through the printed idler cap into the ID rear boss (2.1 mm bore, 3.35 mm deep). No washer.'


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fmt_spec(size, length):
    return f'{size} × {length:g}'


def guide_prepare():
    """Fastener items per step as the current guide-data.json states them."""
    d = json.loads((G / 'data/guide-data.json').read_text())
    out = {}
    for s in d['steps']:
        items = [p for p in s['prepare'] if p.get('kind') == 'fastener']
        if items:
            out[s['id']] = items
    return out, d


def checks(s, f, g):
    pp = f['perPart']
    d = s['diameterMm']
    res = {}
    res['fullMeshHit'] = bool(f['holeHit'])
    res['guideMeshHit'] = bool(g['holeHit'])
    exp_seat = 1.8 if s['expect'].get('pressure') else 0.0
    res['seatWithin0_3mm'] = abs(f['seatOffsetMm'] - exp_seat) <= 0.3
    thr_ok = True
    for k in s['throughPart']:
        h = pp.get(k, {})
        if h.get('inShankPath') and h.get('holeDiameterMinMm', 0) < d - RESOLUTION:
            thr_ok = False
    res['throughClearanceOk'] = thr_ok
    into = pp.get(s['intoPart'], {})
    lo, hi = PILOT_RANGE[s['size']]
    pil = into.get('holeDiameterMinMm')
    res['pilotInTapRange'] = pil is not None and lo <= pil <= hi
    res['engagementOk'] = into.get('threadEngagedMm', 0) >= MIN_ENGAGEMENT
    tip = f['tipMarginMm']
    res['noBottoming'] = s['expect'].get('pressure', False) or tip is None or tip >= 0
    res['noIntrusion'] = not f['intrusions']
    res['noHeadClash'] = all(h['maxSolidMm'] <= 0.2 for h in f['headClash'])
    return res


def evidence_text(s, f, g, ck):
    pp = f['perPart']
    parts = []
    for x in f['sequence']:
        k = x['part']
        if k in pp and pp[k].get('inShankPath'):
            parts.append(f"{k} {pp[k]['fromMm']}-{pp[k]['toMm']} mm (hole {dtxt(pp[k].get('holeDiameterMinMm'))})")
    stack = '; '.join(parts)
    into = pp.get(s['intoPart'], {})
    tip = f['tipMarginMm']
    tip_txt = 'pilot open past the tip' if tip is None else f'{tip} mm to the first solid past the tip ({f["firstCoreSolidPart"]})'
    drv = f['driverStep']['clearMm']
    drv_by = next(iter(f['driverStep']['obstacles']), None)
    drv_txt = f'straight 3 mm driver clear {drv} mm at this step' + (f' (then {drv_by})' if drv_by else '')
    return (f"Ray cast, full-resolution V1.6 meshes: head seats on {f['seatPart']} {f['seatOffsetMm']} mm from the nominal centre; "
            f"stack {stack}; thread engagement in {s['intoPart']} {into.get('threadEngagedMm')} mm; {tip_txt}; "
            f"intrusions {len(f['intrusions'])}; {drv_txt}. Guide meshes: {'hit' if g['holeHit'] else 'MISS'} "
            f"(engagement {g['perPart'].get(s['intoPart'], {}).get('threadEngagedMm')} mm).")


def unassigned(inv, defs, probe):
    rows = []
    for part, rec in inv.items():
        for h in rec['holes']:
            s = np.array(h['start']); e = np.array(h['end']); L = np.linalg.norm(e - s)
            ax = (e - s) / max(L, 1e-9); mid = (s + e) / 2
            hit = None
            for dd in defs:
                seat = np.array(probe[dd['id']]['seat']); a = np.array(dd['axis'], float); a /= np.linalg.norm(a)
                if abs(ax @ a) < 0.97:
                    continue
                v = mid - seat; t = v @ a; perp = np.linalg.norm(v - t * a)
                if perp < 0.8 and -4 - L / 2 < t < dd['lengthMm'] + 3 + L / 2:
                    hit = dd['id']; break
            if hit:
                continue
            if part == 'pi' and h['dMedian'] < 1.2:
                continue   # 40-pin header through-holes
            rows.append({'part': part, 'mid': mid, 'axis': ax, 'start': s, 'end': e, 'd': h['dMedian'], 'dMin': h['dMin'], 'dMax': h['dMax'], 'depth': h['depthMm']})
    merged = []
    for r in rows:   # the same hole seen by two slicing axes 10 degrees apart
        for m in merged:
            if m['part'] == r['part'] and np.linalg.norm(m['mid'] - r['mid']) < 2.0 and abs(m['axis'] @ r['axis']) > 0.95:
                if r['depth'] > m['depth']:
                    m.update(r)
                break
        else:
            merged.append(dict(r))
    return merged


CLASSIFY = [
    # (part, predicate on mid, shouldTakeScrew, reason)
    ('head_cap', lambda m: abs(abs(m[1]) - 10.25) < 0.3 and m[2] > 135, 'no',
     'Former OpenRB-150 head mount boss (1.7 mm pilot, 4.4 mm deep). The OpenRB now sits on the torso tray; nothing mounts here.'),
    ('head_cap', lambda m: m[0] < -25, 'no', 'Hood zip-tie slot (3.56 mm). The cap-on step ties the bundle through both slots.'),
    ('face_panel', lambda m: True, 'unknown',
     'Undocumented 2.05 mm hole along x in the face at z 131.1. No part in the V1.6 assembly engages it; purpose not found in steps.py or the face release notes.'),
    ('jaw_support', lambda m: True, 'unknown', 'Small slanted hole (1.2-2.1 mm, 1.4 mm long) above the base plate; no screw or pin in the assembly uses it. Inference: a tie or vent hole.'),
    ('camera_board', lambda m: True, 'no', 'Camera Module 3 Wide mounting hole. The board is clamped by the three-screw retainer and located by its anchors; no screw goes through the board (camera-three-screw-clamp-report.json).'),
    ('jaw_frame', lambda m: m[1] < 0, 'no',
     '2.0 mm hole on the jaw pivot axis in the passive (-y) arm. Nothing lies on its axis within 15 mm; the passive side turns in the mouth sliding ring. Inference: a centring hole, not a screw seat.'),
    ('imu_board', lambda m: True, 'no', 'BNO085 mounting hole; the board sits on the holder locating pins (imu-board step) and the cover tubes stop it from the rear.'),
    ('imu_cover', lambda m: True, 'no', '2.8 mm tube in line with a BNO085 mounting hole, ending about 0.7 mm behind the board; it limits board travel and is empty in the model. Not a screw hole.'),
    ('power_support', lambda m, a: abs(a[2]) > 0.9 and m[2] > -20, 'no', 'Small 1.4-1.6 mm z pilot at the bay edge. Unused in V1.6.'),
    ('power_support', lambda m: abs(abs(m[1]) - 25) < 0.5 and m[2] > 30, 'no',
     'Rear-facing pilot in the power support behind the shell wall; the closed shell covers it with no access hole. Unused in V1.6.'),
    ('power_support', lambda m: m[0] < -20 and m[2] < 0 and m[2] > -40, 'no',
     '1.6 mm pilot in the front wall of the old battery bay (8 in a 2 x 4 pattern). Unused in V1.6. These could retain the DFR1202 insert if the insert gained matching holes (see problems).'),
    ('power_support', lambda m: abs(m[1]) < 1 and m[2] > 0, 'no', '1.6 mm pilot 12 mm long across the support between the hip-yaw motors. Unused in V1.6.'),
    ('power_support', lambda m: m[2] < -50, 'no', 'Former fuse-carrier deck standoff (2.2 mm). The OpenRB tray clears it with a 6 mm cut and is tied down instead.'),
    ('power_support', lambda m: True, 'no', 'Small 1.4-1.6 mm z pilot at the bay edge. Unused in V1.6.'),
    ('shell_left', lambda m: True, 'unknown',
     'Shell-to-shell hole at x -38, z 35: 2.2 mm clearance for 2 mm at the inner boss, behind a 3.5-3.8 mm tapered bore. It pairs with a 1.6 mm, 4.8 mm deep pilot in the right shell. No V1.4 or V1.6 schedule lists a screw here, and a standard M2 head (3.8-4.0 mm) does not fit the 3.5 mm bore floor.'),
    ('shell_right', lambda m: True, 'unknown',
     'Right-shell half of the x -38, z 35 shell-to-shell hole: 1.6 mm pilot 4.8 mm deep at the inner boss behind a 3.0-3.8 mm tapered bore. No schedule lists a screw.'),
]


def classify(r):
    for part, pred, should, reason in CLASSIFY:
        if r['part'] != part:
            continue
        ok = pred(r['mid'], r['axis']) if pred.__code__.co_argcount == 2 else pred(r['mid'])
        if ok:
            return should, reason
    return 'unknown', 'Not classified.'


def main():
    defs = screw_defs.defs()
    F = json.loads((EV / 'probe-full.json').read_text())
    Gp = json.loads((EV / 'probe-guide.json').read_text())
    inv = json.loads((EV / 'inventory.json').read_text())
    free = json.loads((EV / 'freeplay.json').read_text())
    jaw = json.loads((EV / 'jaw-access.json').read_text())
    prep, gd = guide_prepare()

    screws = []
    for s in defs:
        f, g = F[s['id']], Gp[s['id']]
        ck = checks(s, f, g)
        into = f['perPart'].get(s['intoPart'], {})
        verified = all(ck.values())
        stack = [{'part': k, 'fromMm': v['fromMm'], 'toMm': v['toMm'], 'holeDiameterRangeMm': drange(v['holeDiameterMinMm'])}
                 for k, v in f['perPart'].items() if v.get('inShankPath')]
        stack.sort(key=lambda x: x['fromMm'])
        order = {x['part']: x['fromMm'] for x in stack}
        thr = sorted(s['throughPart'], key=lambda k: order.get(k, 99))
        guide_items = prep.get(s['step'], [])
        guide_text = '; '.join(f"{p['qty']} x {p['item']}" for p in guide_items) or 'none listed'
        spec_txt = fmt_spec(s['size'], s['lengthMm'])
        matches = any(spec_txt in p['item'] for p in guide_items)
        screws.append({
            'id': s['id'], 'step': s['step'], 'spec': spec_txt + ' TAP', 'kind': s['kind'],
            'diameterMm': s['diameterMm'], 'lengthMm': s['lengthMm'],
            'headDiameterMm': s['headDiameterMm'], 'headHeightMm': s['headHeightMm'],
            'nut': None, 'washer': None,
            'center': f['seat'], 'axis': [round(float(x), 6) for x in np.array(s['axis']) / np.linalg.norm(s['axis'])],
            'throughPart': thr[0] if thr else None,
            'throughParts': thr, 'intoPart': s['intoPart'],
            'engagementMm': into.get('threadEngagedMm'),
            'verified': verified,
            'evidence': evidence_text(s, f, g, ck),
            'note': ' '.join(x for x in (s['role'] + '.', NOTES.get(s['id'], '')) if x).strip(),
            'role': s['role'],
            'stack': stack,
            'pilotDiameterRangeMm': drange(into.get('holeDiameterMinMm')),
            'tipMarginMm': f['tipMarginMm'],
            'driverClearAtStepMm': f['driverStep']['clearMm'],
            'checks': ck,
            'guideCurrentlySays': guide_text,
            'guideSpecMatches': matches,
            'source': s['source'],
        })

    # unassigned holes
    un = []
    for r in unassigned(inv, defs, F):
        should, reason = classify(r)
        un.append({'part': r['part'], 'center': [round(float(x), 2) for x in r['mid']], 'axis': [round(float(x), 4) for x in r['axis']],
                   'start': [round(float(x), 2) for x in r['start']], 'end': [round(float(x), 2) for x in r['end']],
                   'diameterMm': round(r['d'], 2), 'diameterRangeMm': [round(r['dMin'], 2), round(r['dMax'], 2)], 'depthMm': r['depth'],
                   'shouldTakeScrew': should, 'reason': reason})

    def ft(part):
        return {k: v['freeTravelMm'] for k, v in free[part].items()}

    unfastened = [
        {'joint': 'ID14 (motor14) case to head', 'parts': ['motor14', 'jaw_support', 'head_bottom', 'head_roll_ring_a', 'head_roll_ring_b'],
         'retention': 'Captured with no screw: the jaw support pocket and the lower head shell hold the case once the four support screws are tight. Along -x it is located through the two 22 mm rings between the fork arms (0.18 mm play).',
         'statedInGuide': False, 'freeTravelMm': ft('motor14'), 'risk': 'low'},
        {'joint': 'ID15 (motor15) case to head', 'parts': ['motor15', 'jaw_support', 'head_bottom', 'head_cap'],
         'retention': 'Captured with no screw between the jaw support, the lower head shell and (once closed) the cap; 0.13 mm or less in every direction.',
         'statedInGuide': False, 'freeTravelMm': ft('motor15'), 'risk': 'low'},
        {'joint': 'Face panel to head', 'parts': ['face_panel', 'head_bottom', 'head_cap'],
         'retention': 'Captured between the lower head shell and the cap by the three closure screws; loose until the close step.',
         'statedInGuide': True, 'freeTravelMm': ft('face_panel'), 'risk': 'low'},
        {'joint': 'Eye trim in face panel', 'parts': ['eye_trim', 'face_panel'],
         'retention': 'Push fit with 0.02-0.03 mm side clearance; nothing stops it moving forward (+x) out of the face. The face step says only "fit".',
         'statedInGuide': False, 'freeTravelMm': ft('eye_trim'), 'risk': 'low'},
        {'joint': 'Lower lip pad on jaw frame', 'parts': ['lower_pad', 'jaw_frame'],
         'retention': 'Sits in a jaw-frame pocket; nothing on the jaw holds it upward (+z). Only the upper pad stops it when the mouth is closed, so it can lift out when the jaw opens.',
         'statedInGuide': False, 'freeTravelMm': ft('lower_pad'), 'risk': 'medium'},
        {'joint': 'Upper lip pad on lower head shell', 'parts': ['upper_pad', 'head_bottom'],
         'retention': 'Held by the lower shell in +x, +-y and +z only; it can drop out (-z 0.58 mm to the lower pad) when the jaw opens.',
         'statedInGuide': False, 'freeTravelMm': ft('upper_pad'), 'risk': 'medium'},
        {'joint': 'Speaker in cradle and keeper', 'parts': ['speaker', 'speaker_cradle', 'speaker_keeper'],
         'retention': 'Trapped between cradle and keeper (stated), but the model leaves 1.27 mm axial and 1.1-2.1 mm radial play; it is clamped only after the screws pull the cradle about 1.2 mm up.',
         'statedInGuide': True, 'freeTravelMm': ft('speaker'), 'risk': 'medium'},
        {'joint': 'DFR1202 insert in the old battery bay', 'parts': ['regulator_insert', 'power_support'],
         'retention': 'None. The guide says only "Drop the insert into the bay". In the model it touches nothing but the converter: up to 10.7 mm free to the rear and 1.0-3.9 mm in the other directions.',
         'statedInGuide': False, 'freeTravelMm': ft('regulator_insert'), 'risk': 'medium'},
        {'joint': 'DFR1202 converter in its insert', 'parts': ['regulator', 'regulator_insert'],
         'retention': 'Two narrow ties through the insert tie positions (converter step).', 'statedInGuide': True, 'freeTravelMm': ft('regulator'), 'risk': 'low'},
        {'joint': 'Star junction J and main fuse in the rear bay', 'parts': ['junction_j', 'fuse_main'],
         'retention': 'None stated ("Sit J in the open rear bay"). These are harness items without full-resolution meshes; free travel not measured.',
         'statedInGuide': False, 'freeTravelMm': None, 'risk': 'low'},
        {'joint': 'OpenRB tray to lower deck', 'parts': ['openrb_tray', 'power_support'], 'retention': 'Two ties through deck and tray slots over four standoffs (tray step).',
         'statedInGuide': True, 'freeTravelMm': None, 'risk': 'low'},
        {'joint': 'OpenRB-150 front edge', 'parts': ['openrb_board', 'openrb_tray'], 'retention': 'Front edge under the two tray lips; rear held by two M2 x 6 (board step). Front holes unused.',
         'statedInGuide': True, 'freeTravelMm': None, 'risk': 'low'},
        {'joint': 'BNO085 in IMU holder', 'parts': ['imu_board', 'imu_clamp', 'imu_cover'], 'retention': 'Locating pins plus cover tubes (imu-board, imu-cover steps).',
         'statedInGuide': True, 'freeTravelMm': ft('imu_board'), 'risk': 'low'},
        {'joint': 'Camera board in face', 'parts': ['camera_board', 'camera_retainer', 'face_panel'], 'retention': 'Clamped by the three-screw retainer (camera step).',
         'statedInGuide': True, 'freeTravelMm': None, 'risk': 'low'},
        {'joint': 'Mouth sliding ring', 'parts': ['mouth_sliding_ring', 'jaw_support', 'head_bottom', 'jaw_frame'], 'retention': 'Captured, 0.18 mm or less (jaw step).',
         'statedInGuide': True, 'freeTravelMm': ft('mouth_sliding_ring'), 'risk': 'low'},
        {'joint': 'Head roll rings A and B', 'parts': ['head_roll_ring_a', 'head_roll_ring_b', 'head_yaw_link', 'jaw_support'], 'retention': 'Captured between fork arms and jaw support, 0.18 mm or less (neck-roll step).',
         'statedInGuide': True, 'freeTravelMm': {'a': ft('head_roll_ring_a'), 'b': ft('head_roll_ring_b')}, 'risk': 'low'},
        {'joint': 'Neck pitch ring', 'parts': ['neck_pitch_ring', 'neck_pitch', 'motor13'], 'retention': 'Captured, 0.88 mm axial play (neck-pitch step).',
         'statedInGuide': True, 'freeTravelMm': ft('neck_pitch_ring'), 'risk': 'low'},
        {'joint': 'Hip-yaw rings', 'parts': ['ring5_torso', 'ring10_torso', 'torso_base'], 'retention': 'Captured by the torso base and the leg yaw brackets (torso-base step).',
         'statedInGuide': True, 'freeTravelMm': {'ring5': ft('ring5_torso'), 'ring10': ft('ring10_torso')}, 'risk': 'low'},
    ]

    opened = [a['openDeg'] for a in jaw['angles'] if all(v['jawFreeLengthMm'] == '>80' for v in a['screws'].values())]
    stop = [a['openDeg'] for a in jaw['angles'] if a['jawInterference']]
    problems = [
        {'severity': 'high', 'where': 'pi step (E-pi-01..04)',
         'finding': 'The guide says four M2.5 x 8. The V1.6 cap rails have 1.6-1.7 mm M2 pilots, 4.35 mm long; an M2.5 self-tapping screw would split or strip them. Measured with M2 x 6: 4.15 mm engagement, 0.3 mm to the rail end.',
         'proposedFix': 'Change the pi step to tap(4, "M2 x 6"). No part change. (Alternative: reprint the cap with 2.2 mm rail pilots for M2.5 x 6.)'},
        {'severity': 'high', 'where': 'speaker step (E-speaker-01/02)',
         'finding': 'The guide says two M2 x 6. The cap posts are 2.0-2.1 mm (M2.5 pilots), so an M2 screw gets no thread. The guide display models are already M2.5 x 8. Measured with M2.5 x 8: 2.74 mm engagement, tip 0.26 mm short of the post bottom.',
         'proposedFix': 'Change to tap(2, "M2.5 x 8") and say "stop at snug". Do not use M2.5 x 10 (bottoms out).'},
        {'severity': 'high', 'where': 'amp step (E-amp-01/02)',
         'finding': 'The guide says two M2 x 6. The posts are 2.0-2.1 mm M2.5 pilots, 7.2 mm deep, so M2 gets no thread. Measured with M2.5 x 8: 6.13 mm engagement, 0.77 mm tip margin.',
         'proposedFix': 'Change to tap(2, "M2.5 x 8").'},
        {'severity': 'high', 'where': 'jaw step (S15-horn-045..048)',
         'finding': 'The jaw frame must be screwed to the ID15 horn, but the step lists no screws and no instruction. The four holes differ: the front and top positions are 4.1 mm thick (M2 x 7, 2.5-2.6 mm engagement), the rear and bottom 3.55-3.6 mm (M2 x 6, 2.1 mm engagement). An M2 x 7 in a thin position goes 3.4 mm into a horn tapped 3.0 mm max.',
         'proposedFix': 'Add tap(2, "M2 x 6") and tap(2, "M2 x 7") with the instruction "M2 x 7 in the front and top horn holes, M2 x 6 in the rear and bottom holes".'},
        {'severity': 'high', 'where': 'head-bottom step (H-jaw_support-01..04)',
         'finding': 'The text says "four existing frame screws" but the prepare list has no fastener. They are M2.5 x 6, driven from above through the 1.65 mm jaw support plate into 2.1-2.2 mm bosses (3.3 mm engagement). This joint also clamps the ID14 and ID15 cases, which have no screws of their own.',
         'proposedFix': 'Add tap(4, "M2.5 x 6") and say that these screws are what hold ID14 and ID15 in the head.'},
        {'severity': 'high', 'where': 'close step (K-head_close-01..03)',
         'finding': f'"Close with the existing shell screws" gives no count or size. They are three M2.5 x 8 from below (4.95 mm engagement). At rest the lower lip pad sits 2.74 mm under the two front screw heads, so a driver cannot reach them; the corridor is clear from {min(opened) if opened else "?"} degrees of jaw opening, and the jaw meets the lower shell at about {min(stop) if stop else "?"} degrees.',
         'proposedFix': 'Add tap(3, "M2.5 x 8"). Instruct: "With torque off, open the jaw by hand to about 30-35 degrees to reach the two front screws; drive the rear one straight up. Fit the upper lip pad afterwards."'},
        {'severity': 'medium', 'where': 'camera step (C-camera_clamp-01..03)',
         'finding': '"Existing camera clamp screws" gives no size. They are M2 x 4 self-tapping (2.2 mm engagement, 0.3 mm tip margin). The lower screw (z 119) has only 32.6 mm of straight driver room behind its head before the jaw support at this step.',
         'proposedFix': 'Change the item to tap(3, "M2 x 4"). Either call for a stubby driver, or mount the camera and retainer on the face panel on the bench before the face step.'},
        {'severity': 'medium', 'where': 'speaker cage (speaker_cradle, speaker_keeper)',
         'finding': 'Under each speaker screw there is a 2.9 mm air gap between the cradle tab and the keeper (nothing within 7 mm of the axis), and the speaker has 1.27 mm axial and 1.1-2.1 mm radial play. The screws can only clamp by pulling the cradle about 1.2 mm up onto the speaker rim, which leaves the tabs bending across the rest of the gap.',
         'proposedFix': 'No-reprint option: put a 1-1.2 mm foam ring under the speaker rim and stop the screws at snug. Part option: reprint the cradle with 2.9 mm standoffs under the two tabs so the stack is solid.'},
        {'severity': 'medium', 'where': 'converter step (regulator_insert)',
         'finding': 'The DFR1202 insert has no retention: "Drop the insert into the bay". In the V1.6 model it touches only the converter, with 10.7 mm free travel to the rear and 1.0-3.9 mm in other directions, so it can rattle and load the solder joints.',
         'proposedFix': 'No-reprint option: tie the insert to the power support with one narrow tie, or pack foam behind it. Part option: add two 2.2 mm holes in the insert front wall at two of the eight unused 1.6 mm bay pilots and fit M2 x 6 before seating the converter.'},
        {'severity': 'medium', 'where': 'jaw and close steps (lower_pad, upper_pad)',
         'finding': 'Neither lip pad has a stated retention. The lower pad can lift off the jaw frame when the mouth opens; the upper pad can drop out of the lower shell.',
         'proposedFix': 'State the retention in the guide: a few dots of CA glue or thin double-sided tape on each pad. Put the upper pad on after the closure screws (already the order).'},
        {'severity': 'low', 'where': 'neck-upper-join (S11-horn-033..036)',
         'finding': 'M2 x 6 through the 3.0 mm bracket wall goes 3.0 mm into the ID11 horn; ROBOTIS rates the horn holes DP 3.0 max, so there is no design margin (the CAD model shows 0.3 mm).',
         'proposedFix': 'Keep M2 x 6 and add "stop at snug". Use M2 x 5 (2.0 mm engagement) if a screw bottoms before it clamps.'},
        {'severity': 'low', 'where': 'shells step (S05-case-075)',
         'finding': 'The right shell is placed 0.45-0.5 mm outboard in the assembly model; its yaw-case clearance hole sits 0.5 mm off the ID5 bore, and its horn-screw stack shows a 0.65 mm gap (left side 0.2 mm).',
         'proposedFix': 'No change needed if the four right-shell M2 x 6 go in first (the current order). If the M2 x 10 binds, open the shell hole to 2.4 mm.'},
        {'severity': 'low', 'where': 'imu-holder step (E-imu_clamp-01/02)',
         'finding': 'These are pressure screws: the tip bears on the fixed rail and the head stays about 1.8 mm proud. The guide says only "tighten gently into the plastic pilots".',
         'proposedFix': 'Add: "Turn each until its tip presses the rail; the heads do not seat."'},
        {'severity': 'low', 'where': 'amp step (amplifier PCB)',
         'finding': 'The amplifier mounting holes are modelled 2.4-2.5 mm, a line-to-line fit for M2.5 (inference; no manufacturer drawing on file).',
         'proposedFix': 'Check the real board; if M2.5 does not pass, open the board holes to 2.6 mm. M2 is not an option (no thread in the 2.1 mm posts).'},
        {'severity': 'low', 'where': 'shells (x -38, z 35)',
         'finding': 'An undocumented shell-to-shell hole pair (2.2 mm clearance left, 1.6 mm pilot right) sits behind 3.0-3.8 mm tapered bores. No schedule uses it and a standard M2 head does not fit the bore.',
         'proposedFix': 'Leave empty unless the shell source says otherwise; the shells are held by ten screws.'},
        {'severity': 'low', 'where': 'junction-place step (junction J)',
         'finding': 'J has no stated retention in the rear bay.', 'proposedFix': 'Add one narrow tie from J to the power support.'},
        {'severity': 'low', 'where': 'face step (eye_trim)',
         'finding': 'The eye trim is a push fit and nothing stops it moving forward out of the face.', 'proposedFix': 'State "push fit; one dot of CA glue if it moves".'},
    ]

    # step-by-step reconciliation against the guide's prepare lists and screw wording
    import re
    text_mentions = {}
    for st in gd['steps']:
        lines = [x for x in st['instructions'] + st.get('checks', []) if re.search(r'screw|M2', x)]
        if lines:
            text_mentions[st['id']] = lines
    explain = {
        'jaw': 'Guide lists no screws; the jaw frame needs 2 x M2 x 6 + 2 x M2 x 7 into the ID15 horn.',
        'head-bottom': 'Text says "four existing frame screws" with no prepare item; they are 4 x M2.5 x 6.',
        'camera': '"Existing camera clamp screws" has no size; they are 3 x M2 x 4.',
        'speaker': 'Guide size M2 x 6 is wrong for the 2.0-2.1 mm posts; use M2.5 x 8.',
        'amp': 'Guide size M2 x 6 is wrong for the 2.0-2.1 mm posts; use M2.5 x 8.',
        'pi': 'Guide size M2.5 x 8 is wrong for the 1.6-1.7 mm rail pilots; use M2 x 6.',
        'close': 'Text says "existing shell screws" with no count; they are 3 x M2.5 x 8.',
        'torso-fasten': 'Matches; the two shell-to-yaw-case M2 x 10 the text defers are S10-case-071 and S05-case-075 in the shells step.',
        'prints': 'Text mentions three cap-screw tabs on the lower head shell (close step) and four screw seats on the jaw support (head-bottom step); both are covered by records.',
    }
    recon = []
    step_ids = [st['id'] for st in gd['steps']]
    rec_by_step = {}
    for sc in screws:
        rec_by_step.setdefault(sc['step'], Counter())[sc['spec'].replace(' TAP', '')] += 1
    for sid in step_ids:
        items = prep.get(sid, [])
        recs = rec_by_step.get(sid, Counter())
        if not items and not recs and sid not in text_mentions:
            continue
        guide_c = Counter()
        for it in items:
            m = re.match(r'(M[0-9.]+ \u00d7 [0-9.]+)', it['item'])
            guide_c[m.group(1) if m else it['item']] += int(it['qty'])
        status = 'match' if guide_c == recs else 'mismatch'
        recon.append({'step': sid, 'guidePrepare': dict(guide_c), 'records': dict(recs), 'status': status,
                      'guideTextMentions': text_mentions.get(sid, []), 'explanation': explain.get(sid, '')})

    by_step = Counter(s['step'] for s in screws)
    by_spec = Counter(s['spec'] for s in screws)
    out = {
        'schemaVersion': 1,
        'generated': '2026-10-09',
        'frame': 'robot frame, mm; x forward, y left, z up',
        'conventions': {
            'center': 'head seat point (underside of the head) measured on the full-resolution V1.6 meshes',
            'axis': 'unit insertion direction (direction of travel), = -world_axis of the older records',
            'engagementMm': 'threaded length in intoPart from the measured stack, less 0.3 mm for the tip lead-in',
            'headDimensions': 'assumed pan/cross-recessed head 4.0 x 1.5 mm for M2 and M2.5, 4.5 x 1.8 mm for M2.6 (no purchased-screw drawing on file)',
        },
        'sources': {
            'meshes': 'fastener-audit/evidence/mesh-manifest.json (sha256 of every source)',
            'guideData': {'path': 'guide/data/guide-data.json', 'sha256': sha(G / 'data/guide-data.json')},
            'stepsPy': {'path': 'guide/content/steps.py', 'sha256': sha(G / 'content/steps.py')},
        },
        'counts': {'total': len(screws), 'byStep': dict(by_step), 'bySpec': dict(by_spec),
                   'verified': sum(s['verified'] for s in screws),
                   'fullMeshHit': sum(s['checks']['fullMeshHit'] for s in screws),
                   'guideMeshHit': sum(s['checks']['guideMeshHit'] for s in screws),
                   'guideSpecMatches': sum(s['guideSpecMatches'] for s in screws)},
        'screws': screws,
        'unassignedHoles': un,
        'unfastenedJoints': unfastened,
        'problems': problems,
        'stepReconciliation': recon,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out['counts'], indent=1))
    print('unverified:', [s['id'] for s in screws if not s['verified']], [{k: v for k, v in s['checks'].items() if not v} for s in screws if not s['verified']])
    print('unassigned holes:', len(un), Counter(u['shouldTakeScrew'] for u in un))
    for r in recon:
        print(r['step'], r['status'], r['guidePrepare'], r['records'])


if __name__ == '__main__':
    main()
