#!/usr/bin/env python3
"""No geometry: combine postures.json, trace-check.json and margin-*.json into ../results.json.

Derived limit: for each map line, the largest head_pitch (positive side) at which the jaw is still clear at the
training maximum (0.32 rad = 18.33 deg) and at the V1.8 40 deg, i.e. firstContactJawDeg > that opening.
"""
from __future__ import annotations

import glob
import json
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
J18 = 18.33


def limit(rows, jaw, key='head_pitch'):
    ok = [r[key] for r in rows if r[key] >= 0 and (r['firstContactJawDeg'] is None or r['firstContactJawDeg'] > jaw)]
    bad = [r for r in rows if r[key] >= 0 and r['firstContactJawDeg'] is not None and r['firstContactJawDeg'] <= jaw]
    first_bad = min(bad, key=lambda r: r[key]) if bad else None
    return {'maxClearHeadPitchDeg': max((h for h in ok if first_bad is None or h < first_bad[key]), default=None),
            'firstBlockedHeadPitchDeg': first_bad and first_bad[key],
            'blockingPart': first_bad and (first_bad.get('part') or (first_bad.get('firstContact') or {}).get('part'))}


def main():
    ld = lambda n: json.loads((OUT / n).read_text())  # noqa: E731
    post = ld('postures.json')
    tc = ld('trace-check.json')
    mp = ld('margin-postures.json')['postures']
    nm = ld('margin-neck.json')['neckMap']
    tm = ld('margin-torso.json')['torsoMap']
    rel = []
    for p in sorted(glob.glob(str(OUT / 'margin-release-yaw*.json'))):
        rel += json.loads(Path(p).read_text())['releaseMap']
    res = {'_method': __doc__.strip(),
           'trainingJaw': {'beakRangesSeenRad': post['beakRangesSeenRad'], 'trainJawMaxDeg': J18,
                           'maxJawInAnyTraceDeg': max(t['jawMaxDeg'] for t in post['traces'])},
           'traceFamilies': post['families'],
           'traceCheck': {b: {k: v[k] for k in ('bins', 'binsWithin3mm', 'distinctRowsRechecked', 'rowsInterference',
                                                 'rowsContact', 'minGapMmOverAllRows')} |
                          {'hits': [{k: h[k] for k in ('class', 'rows', 'byFamily', 'byPhase', 'byPart', 'jawDegRange',
                                                       'jointRangeDeg', 'tracesCount', 'worst', 'worstPoseDeg')}
                                    for h in v['hits']]}
                          for b, v in tc['bodies'].items()},
           'pickupPostures': [{'label': p['label'], 'q': p['q'], 'simJawDeg': p['simJawDeg'],
                               'firstContactJawDeg': p['firstContactJawDeg'],
                               'firstContactPart': p['firstContactPart'] and p['firstContactPart']['part'],
                               'marginAboveTrainingJawDeg': (None if p['firstContactJawDeg'] is None
                                                             else round(p['firstContactJawDeg'] - J18, 2))}
                              for p in mp]}
    lines = defaultdict(list)
    for r in nm:
        lines[f"yaw {r['head_yaw']:g}, roll {r['head_roll']:g}"].append(r)
    res['neckGroupLimit'] = {k: {'jaw18.33': limit(v, J18), 'jaw40': limit(v, 40.0)} for k, v in lines.items()}
    lines = defaultdict(list)
    for r in tm:
        lines[f"neck_pitch {r['neck_pitch']:g}"].append(r)
    res['torsoLimit'] = {k: {'jaw18.33': limit(v, J18), 'jaw40': limit(v, 40.0)} for k, v in lines.items()}
    lines = defaultdict(list)
    for r in rel:
        lines[f"neck_pitch 12, yaw {r['head_yaw']:g}, roll 0"].append(r)
    res['releaseLimit1deg'] = {k: {'jaw18.33': limit(v, J18), 'jaw16.5': limit(v, 16.5), 'jaw12': limit(v, 12.0),
                                   'headBlockedWithJawClosedFrom': min((r['head_pitch'] for r in v if r['headWithoutJawJaw0']), default=None),
                                   'firstContactByHeadPitch': {r['head_pitch']: r['firstContactJawDeg'] for r in v}}
                               for k, v in lines.items()}
    (OUT / 'results.json').write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ('neckGroupLimit', 'torsoLimit', 'releaseLimit1deg')}, indent=1)[:6000])


if __name__ == '__main__':
    main()
