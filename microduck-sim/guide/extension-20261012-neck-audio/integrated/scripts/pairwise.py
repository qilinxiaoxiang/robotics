#!/usr/bin/env python3
"""Task 3: exact checks of every integrated part and wire, against the V1.8 head and against each other.

Head = V1.8 head solids with head_cap replaced by the integrated study cap (check_lib.Head, read-only on V1.8).
New parts: the integrated cap's added material, every audio part (speaker, retainer, amplifier, amp housings, the five
Pi-end housings on pins 4, 12, 34, 35, 40), the audio wires (five jumpers, two speaker leads), the Pi screws, and the
A3 neck-bundle solids (group tube in the head, fan wires, the two in-head clips). Each carries its mount:
  cap    rides on the cap (checked over the 40 mm cap descent against everything already on the robot)
  lower  fixed to the lower head
  free   the A3 group between the head clip and the cap clip (lies loose; checked static and over the sweeps)
Checks (manifold3d intersection volume and min_gap):
  scene    static vs every head-fixed V1.8 solid and the Pi group; head roll -25..+25 (1 deg) vs the yaw body;
           jaw 0..40 (1 deg); cap descent (0.5 mm steps) for cap parts (check_lib.Head)
  pairs    every new part against every other new part (static), and cap parts against lower parts over the descent
Intended contacts (screw threads in pilots, seated faces, wire ends in their own housings, clip hooks on the group) are
listed in INTENDED and do not fail. Usage: pairwise.py scene|pairs [part ...]. Writes ../pairwise-<mode>.json.
"""
from __future__ import annotations

import itertools
import json
import sys
import time

import numpy as np

import int_lib as L
from check_lib import Head, bbox, man_from_tm  # noqa: E402
from pm_lib import audio_solid, audio_wire_tubes, load_stl_man  # noqa: E402
from route_scene import pin34_housing  # noqa: E402

AUDIO = ['speaker', 'speaker_retainer', 'amplifier', 'amp_housings', 'amp_screws_envelope', 'speaker_screws_envelope',
         'speaker_leads_envelope', 'pi_housing_pin04', 'pi_housing_pin12', 'pi_housing_pin35', 'pi_housing_pin40']
A3 = {'A3_group_free': 'free', 'A3_group_cap_held': 'cap', 'A3_fan_wires': 'cap', 'A3_clip_cap': 'cap',
      'A3_clip_head': 'lower', 'A3_group_slot_to_clip': 'lower'}
PIN_OF = {'pi_housing_pin04': '04', 'pi_housing_pin12': '12', 'pi_housing_pin34': '34', 'pi_housing_pin35': '35',
          'pi_housing_pin40': '40'}
WIRE_HOUSING = {'audio_wire_amp_vin_pin04': 'pi_housing_pin04', 'audio_wire_amp_bclk_pin12': 'pi_housing_pin12',
                'audio_wire_alt_gnd_pin34': 'pi_housing_pin34', 'audio_wire_amp_lrc_pin35': 'pi_housing_pin35',
                'audio_wire_amp_din_pin40': 'pi_housing_pin40'}
INTENDED = {
    ('speaker_screws_envelope', 'head_cap'): 'screw thread in the collar boss pilot',
    ('speaker_screws_envelope', 'speaker_retainer'): 'screw through the retainer hole, head on the retainer',
    ('amp_screws_envelope', 'head_cap'): 'screw thread in the amp post pilot',
    ('amp_screws_envelope', 'amplifier'): 'screw through the board hole, head on the board',
    ('speaker_retainer', 'head_cap'): 'retainer seated on the collar bosses',
    ('amplifier', 'head_cap'): 'board seated on the amp posts',
    ('amp_housings', 'amplifier'): 'housings on the right-angle header',
    ('speaker_leads_envelope', 'speaker_retainer'): 'leads pass the retainer notch',
    ('speaker_leads_envelope', 'audio_wire_spk_plus'): 'same leads', ('speaker_leads_envelope', 'audio_wire_spk_minus'): 'same leads',
    ('speaker_leads_envelope', 'speaker'): 'leads soldered at the speaker pads (speaker side, by the maker)',
    ('audio_wire_spk_plus', 'speaker'): 'lead end at its speaker pad', ('audio_wire_spk_minus', 'speaker'): 'lead end at its speaker pad',
    ('audio_wire_spk_plus', 'amplifier'): 'lead end clamped in the terminal block', ('audio_wire_spk_minus', 'amplifier'): 'lead end clamped in the terminal block',
    ('pi_screws', 'head_cap'): 'Pi screw thread in the rail pilot', ('pi_screws', 'pi'): 'Pi screw through the board, head on it',
    ('A3_clip_cap', 'pi'): 'clip tab seated on the Pi under the E-pi-04 head', ('A3_clip_cap', 'pi_screws'): 'E-pi-04 passes the clip tab',
    ('A3_clip_cap', 'A3_group_cap_held'): 'hook holds the group', ('A3_clip_cap', 'A3_group_free'): 'hook holds the group',
    ('A3_clip_head', 'jaw_support'): 'clip tab seated on jaw_support under the H-jaw_support-03 head',
    ('A3_clip_head', 'A3_group_free'): 'hook holds the group', ('A3_clip_head', 'A3_group_slot_to_clip'): 'hook holds the group',
    ('A3_group_free', 'A3_group_cap_held'): 'same group', ('A3_group_free', 'A3_group_slot_to_clip'): 'same group',
    ('A3_group_cap_held', 'A3_fan_wires'): 'group splits into the fan',
    ('cap_added_vs_V18', 'amp_screws_envelope'): 'screw thread in the new amp post pilot',
    ('cap_added_vs_V18', 'speaker_screws_envelope'): 'screw thread in the new collar boss pilot',
    ('cap_added_vs_V18', 'pi_screws'): 'Pi screw thread in the reinforced rail pilot',
    ('cap_added_vs_V18', 'head_bottom'): 'closed-notch rim continues the V1.8 0.2 mm seat bands on head_bottom (seat_bands.py)',
}
for w, h in WIRE_HOUSING.items():
    INTENDED[(w, h)] = 'jumper end in its own housing'
    INTENDED[(w, 'amp_housings')] = 'jumper end in its amp housing'
for h, pin in PIN_OF.items():
    INTENDED[(h, f'head_pi_zero_w_header_pin_{pin}')] = 'housing on its own header pin'
for pin in (1, 2, 3, 5, 6, 8, 9, 10):
    INTENDED[('A3_fan_wires', f'head_pi_gpio_pin_{pin:02d}_receiving')] = 'wire end at its bundle housing'


def intended(a, b):
    if a.startswith('audio_wire_amp_') and b.startswith('audio_wire_amp_') or \
            a.startswith('audio_wire_alt_') and b.startswith('audio_wire_amp_') or \
            b.startswith('audio_wire_alt_') and a.startswith('audio_wire_amp_'):
        return 'wire on wire: the five audio jumpers lie together where their hand-set runs meet (audio study paths)'
    return INTENDED.get((a, b)) or INTENDED.get((b, a))


def parts():
    P = {'cap_added_vs_V18': (load_stl_man(L.SOL / 'cap_added_vs_V18-world.stl'), 'cap')}
    for k in AUDIO:
        P[k] = (audio_solid(k), 'cap')
    P['pi_housing_pin34'] = (pin34_housing(), 'cap')
    for k, M in audio_wire_tubes().items():
        if k != 'audio_wire_amp_gnd_pin14':
            P[k] = (M, 'cap')
    P['pi_screws'] = (load_stl_man(L.PIM / 'study-solids' / 'A-pi_screws_envelope-world.stl'), 'cap')
    for k, mnt in A3.items():
        P[k] = (load_stl_man(L.SOL / f'{k}-world.stl'), mnt)
    return P


def scene_mode(names):
    H = Head(cap_override=load_stl_man(L.INTEGRATED_CAP))
    P = parts()
    out, fails = {}, []
    t0 = time.time()
    for k, (M, mnt) in P.items():
        if names and k not in names:
            continue
        skip = ('head_cap',) if k == 'cap_added_vs_V18' else ()
        st = H.static(k, M, skip=skip)
        for r in st:
            r['intended'] = intended(k, r['with'])
            if r['overlapMm3'] > 1e-3 and not r['intended']:
                fails.append({'part': k, **r})
        rec = {'mount': mnt, 'static': st[:6], 'roll': H.roll_sweep(M, 1.0), 'jaw': H.jaw_sweep(M, 1.0)}
        if rec['roll']['overlapMm3'] > 1e-3 or rec['jaw']['overlapMm3'] > 1e-3:
            fails.append({'part': k, 'sweep': True, 'roll': rec['roll'], 'jaw': rec['jaw']})
        if mnt == 'cap':
            rec['descent'] = H.descent(M, 0.5)
            for o, d in rec['descent'].items():
                if d['excessMm3'] > 1e-3:
                    fails.append({'part': k, 'descent': o, **d})
        out[k] = rec
        print(f'{k:32s}', [(r['with'], r['overlapMm3'], r['gapMm']) for r in st[:2]], 'roll', rec['roll'].get('gapMm'),
              'jaw', rec['jaw'].get('gapMm'), 'descent', {o: d['minGapAlongPathMm'] for o, d in rec.get('descent', {}).items()},
              f'{time.time() - t0:.0f}s', flush=True)
    return {'parts': out, 'failures': fails}


def pairs_mode():
    P = parts()
    rows, fails = [], []
    for a, b in itertools.combinations(P, 2):
        A, ma = P[a]
        B, mb = P[b]
        Ab, Bb = bbox(A), bbox(B)
        pad = 6 if not ({ma, mb} == {'cap', 'lower'}) else 6 + 40
        if np.any(Ab[0] - 6 > Bb[1]) or np.any(Bb[0] - 6 > Ab[1]):
            if pad == 6:
                continue
        ov = (A ^ B).volume()
        g = float(A.min_gap(B, 6))
        row = {'a': a, 'b': b, 'mounts': [ma, mb], 'overlapMm3': round(ov, 4), 'gapMm': round(g, 3), 'intended': intended(a, b)}
        if {ma, mb} == {'cap', 'lower'}:
            C, Lw = (A, B) if ma == 'cap' else (B, A)
            worst, gmin = 0.0, 99.0
            for dz in np.arange(0.0, 40.0 + 1e-9, 0.5):
                Cz = C.translate([0, 0, float(dz)])
                if np.any(bbox(Cz)[0] - 6 > bbox(Lw)[1]) or np.any(bbox(Lw)[0] - 6 > bbox(Cz)[1]):
                    continue
                ex = (Cz ^ Lw).volume() - ov
                worst = max(worst, ex)
                if ex <= 1e-9:
                    gmin = min(gmin, float(Cz.min_gap(Lw, 6)))
            row['descent'] = {'excessMm3': round(worst, 4), 'minGapAlongPathMm': round(gmin, 3)}
            if worst > 1e-3 and not row['intended']:
                fails.append({**row, 'what': 'descent'})
        if row['gapMm'] >= 6 and 'descent' not in row:
            continue
        rows.append(row)
        if ov > 1e-3 and not row['intended']:
            fails.append(row)
    rows.sort(key=lambda r: (-r['overlapMm3'], r['gapMm']))
    return {'pairs': rows, 'failures': fails, 'partsChecked': list(P)}


def main():
    mode = sys.argv[1]
    names = sys.argv[2:]
    res = scene_mode(names) if mode == 'scene' else pairs_mode()
    res['_method'] = __doc__.strip()
    res['ok'] = not res['failures']
    path = L.STUDY / f'pairwise-{mode}.json'
    if mode == 'scene' and names and path.exists():
        prev = json.loads(path.read_text())
        prev['parts'].update(res['parts'])
        prev['failures'] = [f for f in prev['failures'] if f.get('part') not in names] + res['failures']
        prev['ok'] = not prev['failures']
        res = prev
    L.jdump(res, path)
    print('FAILURES', json.dumps(res['failures'], default=float)[:4000])


if __name__ == '__main__':
    main()
