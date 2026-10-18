#!/usr/bin/env python3
"""Release speaker retainer V1.9 (K2 frame) = the audio study retainer, re-exported through manifold3d and checked.

Source: guide/extension-20261012-neck-audio/audio/study-solids/speaker_retainer-world.stl, built by
audio/scripts/build_study.py: a flat 1.6 mm frame (speaker outline + 2.2 mm outside, 2.0 mm inset inside), two ears
with Ø2.4 clearance holes at +-14.6 mm along the speaker's short axis, and an open notch at the lead end. It presses
the speaker's back rim onto a 1.0 mm closed-cell foam ring in the cap collar; 2 x M2 x 6 TAP into the collar bosses.
Writes ../speaker_retainer_v19-world.stl and ../checks/retainer-build-v19.json.
"""
from __future__ import annotations

import json

import numpy as np

import ext_lib as E
import meshcheck as MC

SRC = E.AUDIO / 'study-solids' / 'speaker_retainer-world.stl'
SRC_SHA = '625f06facb0411d50230bf22874d92d53ea38dba9b255f6c0d7f446634b7fa49'


def main():
    assert E.sha(SRC) == SRC_SHA, 'study retainer changed'
    M = E.stl_man(SRC)
    frame = json.loads((E.AUDIO / 'study-build.json').read_text())['speakerFrame']
    n = np.array(frame['n_front'])
    out = E.PARTS['speaker_retainer_v19']
    E.tm(M).export(out)
    rep, _ = MC.check(out)
    # plate thickness and flatness along the speaker normal
    v = E.tm(E.stl_man(out)).vertices
    h = v @ n
    rec = {'source': {'path': SRC, 'sha256': SRC_SHA}, 'release': {'path': out, 'sha256': E.sha(out),
                                                                  'volumeMm3': M.volume(), 'bodies': len(M.decompose())},
           'speakerNormal': n, 'thicknessAlongNormalMm': float(h.max() - h.min()),
           'distinctFaceLevelsAlongNormal': sorted({round(float(x), 3) for x in h}), 'check': rep}
    E.jdump(E.rnd(rec, 5), E.OUT / 'checks' / 'retainer-build-v19.json')
    print(json.dumps(E.rnd({k: rec[k] for k in ('release', 'thicknessAlongNormalMm', 'distinctFaceLevelsAlongNormal')}, 4),
                     default=str))
    print({k: rep[k] for k in ('clean', 'watertight', 'bodies', 'edgesSharedByMoreThanTwoFaces', 'coincidentFaceGroupsByGeometry',
                               'needleFacesInradiusBelow1e-4')}, rep['faceSeparationTest']['defectFacesFailingAllEps'])


if __name__ == '__main__':
    main()
