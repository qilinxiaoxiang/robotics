"""Bring guide/content/fasteners.json to the battery backpack V2 rev B and the screwed bench box (2026-11-20).
Idempotent: run it again and the file comes out the same.

- Removed: BP-cap-01..03 and BP-bar-01..04 (V1.40 backpack, replaced) and DL-plate-01..04 (the Dual Lock back plate is not
  fitted, CURRENT-STATE backpack_swap_plugs 2026-11-10).
- Restored: C-rear_frame-01..04 (bench box front plate to the pack posts, step 'box-frame'), exactly as they were before
  the Dual Lock change (git commit e8e7b0c7^), and the screws inside the bench box (records tagged 'duallock') moved back
  +8.7 mm in x with their box (to_guide_world.py writes the box in its screwed pose again).
- Added: BV2-fix-01..04 (step 'bv2-frame': backpack frame to the pack posts, four M2 x 6 from inside) and BV2-cap-01..04
  (step 'bv2-cap': two M2 x 8 into the high bosses, two M2 x 6 into the wing columns), from SCREWS.json and build.json.
    python3 update_fasteners.py"""
import json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
FAST = HERE.parents[1] / 'content' / 'fasteners.json'
PRE_DL = 'e8e7b0c7^:microduck-sim/guide/content/fasteners.json'
DL_SHIFT = 8.7
DROP_PREFIX = ('BP-cap-', 'BP-bar-', 'DL-plate-', 'BV2-')
TAG = 'battery V2 rev B guide 2026-11-20 (print/battery-v2-cad-20261120/update_fasteners.py)'
S = json.loads((HERE / 'SCREWS.json').read_text())['screws']


def rec(id_, step, spec, L, center, thru, into, engagement, stack, evidence, note):
    return {'id': id_, 'step': step, 'spec': f'M2 × {L} TAP', 'kind': 'TAP', 'diameterMm': 2.0, 'lengthMm': float(L),
            'headDiameterMm': 4.0, 'headHeightMm': 1.5, 'nut': None, 'washer': None, 'center': center, 'axis': [1.0, 0.0, 0.0],
            'throughPart': thru[0], 'throughParts': thru, 'intoPart': into, 'engagementMm': engagement, 'verified': False,
            'evidence': evidence, 'note': note, 'stack': stack, 'source': 'print/battery-v2-cad-20261120/build_v2.py', 'bv2': TAG}


def bv2_records():
    out = []
    fix = [s for s in S if s['id'].startswith('fix')]
    for i, s in enumerate(fix, 1):
        out.append(rec(f'BV2-fix-0{i}', 'bv2-frame', 'M2 x 6', 6, [-47.0, s['seat'][1], s['seat'][2]], ['bv2_frame'], 'rear_pack', 3.7,
                       [{'part': 'bv2_frame', 'fromMm': 0.0, 'toMm': 2.0, 'holeDiameterRangeMm': [2.5, 2.5]},
                        {'part': 'rear_pack', 'fromMm': 2.0, 'toMm': 6.0, 'holeDiameterRangeMm': [1.6, 1.6]}],
                       'build_v2.py SCREWS (+-16.1, 26) and (+-16.1, -36.5): front wall x -47..-45 (2.0 mm, 2.5 clearance), pack post pilot '
                       'x -45..-40.2 dia 1.6 (C-rear_frame ray cast 2026-10-14, posts unchanged): 4.0 mm of thread less 0.3 mm lead-in, '
                       '0.8 mm of pilot past the tip. Driver lanes checked in checks/access.json.',
                       'Backpack frame front wall to the pack post, from inside the empty frame.'))
    cap = [s for s in S if s['id'].startswith('cap')]
    spec = {c['id']: c for c in json.loads((HERE / 'build' / 'build.json').read_text())['cap_screws']}
    for i, s in enumerate(cap, 1):
        c = spec[s['id']]
        L = s['length']
        through = 1.7
        blind = c['pilot'] != 'through'
        boss = c['pilot'] if blind else c['boss']
        stack = [{'part': 'bv2_cap', 'fromMm': 0.0, 'toMm': 1.7, 'holeDiameterRangeMm': [2.5, 2.5]},
                 {'part': 'bv2_frame', 'fromMm': through, 'toMm': through + boss, 'holeDiameterRangeMm': [1.95, 1.95]}]
        out.append(rec(f'BV2-cap-0{i}', 'bv2-cap', f'M2 x {L}', L, list(map(float, s['seat'])), ['bv2_cap'], 'bv2_frame',
                       round(min(L - through, boss) - 0.3, 2), stack,
                       f'build_v2.py CAP_SCREWS {s["id"]}: head seat x -75.55, cap plate 1.7 (2.5 clearance), '
                       + (f'frame wing column with a {boss:g} mm blind 1.95 pilot (H2S print_fit).' if blind
                          else f'frame boss {boss:g} mm with a 1.95 through pilot (H2S print_fit).'),
                       'Cap to the frame ' + ('wing column.' if blind else 'boss.')))
    return out


def main():
    F = json.loads(FAST.read_text())
    pre = json.loads(subprocess.run(['git', 'show', PRE_DL], cwd=REPO, capture_output=True, text=True, check=True).stdout)
    frame = [r for r in pre['screws'] if r['id'].startswith('C-rear_frame-')]
    assert len(frame) == 4
    out = []
    for r in F['screws']:
        if r['id'].startswith(DROP_PREFIX) or r['id'].startswith('C-rear_frame-'):
            continue
        if r.get('duallock'):
            r['center'] = [round(r['center'][0] + DL_SHIFT, 3), r['center'][1], r['center'][2]]
            r.pop('duallock')
        out.append(r)
    out += frame + bv2_records()
    F['screws'] = out
    by_step, by_spec = {}, {}
    for r in out:
        by_step[r['step']] = by_step.get(r['step'], 0) + 1
        by_spec[r['spec']] = by_spec.get(r['spec'], 0) + 1
    c = F['counts']
    c.update(total=len(out), byStep=by_step, bySpec=by_spec, verified=sum(1 for r in out if r.get('verified')))
    F['updated'] = '2026-11-20'
    FAST.write_text(json.dumps(F, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: c[k] for k in ('total', 'verified')}), {k: by_step.get(k) for k in ('box-frame', 'bv2-frame', 'bv2-cap')})


if __name__ == '__main__':
    main()
