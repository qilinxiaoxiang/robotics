"""Bring guide/content/fasteners.json to the Dual Lock mount (2026-10-31). Idempotent: a record already carrying
'duallock' is left alone.

- C-rear_frame-01..04 (bench box front plate to the pack posts) become DL-plate-01..04: the same four M2 x 6 at
  (+-16.1, 26.0) and (+-16.1, -36.5), now through the 3 mm Dual Lock plate (x -48..-45, dia 2.2 holes, build.json) into
  the pack post pilots (x -45..-40.2, dia 1.6, from the C-rear_frame stack): 3.0 mm of thread less 0.3 mm lead-in,
  1.8 mm of pilot past the tip. Step 'duallock-plate'. Not ray cast: the numbers are the plate build and the post stack.
- BP-fix-01..04 (battery backpack front plate to the posts) are removed: the backpack sticks on with Dual Lock.
- The screws inside both backpacks (C-xl4015-*, C-pd5991-*, C-rear_lid-*, BP-cap-*) move with their box, SHIFT_MM in x.
- counts are recomputed from the records.
    python3 update_fasteners.py"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAST = HERE.parents[3] / 'guide' / 'content' / 'fasteners.json'
G = json.loads((HERE / 'guide-world.json').read_text())
SHIFT_MM = G['shiftMm'][0]
MOVE_PREFIX = ('C-xl4015-', 'C-pd5991-', 'C-rear_lid-', 'BP-cap-')
DROP = {f'BP-fix-0{i}' for i in range(1, 5)}
TAG = 'Dual Lock mount 2026-10-31 (print/back-plate/duallock-plate-20261031/update_fasteners.py)'


def plate_screw(r):
    n = r['id'][-2:]
    r.update(id=f'DL-plate-{n}', step='duallock-plate', throughPart='duallock_plate', throughParts=['duallock_plate'],
             intoPart='rear_pack', center=[-48.0, r['center'][1], r['center'][2]], engagementMm=2.7, tipMarginMm=1.8,
             verified=False,
             evidence='Dual Lock plate build.json (2026-10-31): plate x -48..-45, dia 2.2 holes at (+-16.1, 26.0) and (+-16.1, -36.5), '
                      'thread_in_post 3.0; post pilot x -45..-40.2 dia 1.6 from the C-rear_frame ray cast of 2026-10-14 (posts unchanged). '
                      '3.0 mm of thread less 0.3 mm lead-in = 2.7 mm, 1.8 mm of pilot past the tip. Pan head (dia 4.0, x -49.5..-48) on '
                      'the rear face outside the Dual Lock area (|y| <= 13.5). Not ray cast on the plate mesh.',
             note='Dual Lock plate corner to the pack post, the V1.8 cover screw reused; screwed for good.',
             role='Dual Lock back plate to pack post',
             stack=[{'part': 'duallock_plate', 'fromMm': 0.0, 'toMm': 3.0, 'holeDiameterRangeMm': [2.2, 2.2]},
                    {'part': 'rear_pack', 'fromMm': 3.0, 'toMm': 6.0, 'holeDiameterRangeMm': [1.6, 1.6]}],
             source='print/back-plate/duallock-plate-20261031/build_plate.py (outline = rear-pack build_cover(), posts unchanged)',
             reuseNote='The same four M2 x 6 the V1.8 pack cover and the box front plates used.', duallock=TAG)
    r.pop('driverClearAtStepMm', None)
    r['checks'] = {k: v for k, v in r.get('checks', {}).items() if k in ('throughClearanceOk', 'pilotInTapRange', 'engagementOk', 'noBottoming')}
    return r


def main():
    F = json.loads(FAST.read_text())
    out = []
    for r in F['screws']:
        if r.get('duallock'):
            out.append(r)
        elif r['id'] in DROP:
            continue
        elif r['id'].startswith('C-rear_frame-'):
            out.append(plate_screw(r))
        elif r['id'].startswith(MOVE_PREFIX):
            r['center'] = [round(r['center'][0] + SHIFT_MM, 3), r['center'][1], r['center'][2]]
            r['duallock'] = f'{TAG}: moved {SHIFT_MM} mm in x with its box'
            out.append(r)
        else:
            out.append(r)
    F['screws'] = out
    by_step, by_spec = {}, {}
    for r in out:
        by_step[r['step']] = by_step.get(r['step'], 0) + 1
        by_spec[r['spec']] = by_spec.get(r['spec'], 0) + 1
    c = F['counts']
    c.update(total=len(out), byStep=by_step, bySpec=by_spec, verified=sum(1 for r in out if r.get('verified')))
    F['updated'] = '2026-10-31'
    FAST.write_text(json.dumps(F, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: c[k] for k in ('total', 'verified')}), by_step.get('duallock-plate'), by_step.get('bp-mount'), by_step.get('box-frame'))


if __name__ == '__main__':
    main()
