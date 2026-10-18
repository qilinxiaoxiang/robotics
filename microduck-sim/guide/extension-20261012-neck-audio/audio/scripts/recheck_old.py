#!/usr/bin/env python3
"""Re-check the pre-V1.8 audio parts (speaker cage of speaker-mount-repair, amplifier of amp-mounts and the four cap
roof posts) against the current V1.8 head. Writes ../old-positions-recheck.json."""
from __future__ import annotations

import json

import trimesh

from check_lib import Head, cable_clearance, man_from_tm
from scene import SIM, STUDY

HL = SIM / 'build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout'
PARTS = {
    'speaker': SIM / 'build-pack-20260913/redesign-20260913/workflow-review-20261009/central-cad/fusion-C-meshes/speaker.stl',
    'speaker_cradle': HL / 'speaker-mount-repair/speaker_cradle-candidate-world.stl',
    'speaker_keeper': HL / 'speaker-mount-repair/speaker_keeper-candidate-world.stl',
    'speaker_screw_1_envelope': HL / 'speaker-mount-repair/speaker-screw-1-receiving-world.stl',
    'speaker_screw_2_envelope': HL / 'speaker-mount-repair/speaker-screw-2-receiving-world.stl',
    'amplifier_old_model': HL / 'head-flexible-harness/amp-mounts/amplifier_plusY1.stl',
    'amp_screw_0_envelope': HL / 'head-flexible-harness/amp-mounts/amp_screw_0.stl',
    'amp_screw_1_envelope': HL / 'head-flexible-harness/amp-mounts/amp_screw_1.stl',
}


SPEAKER_T = [[0.0, -1.0, 0.0, 37.0], [1.0, 0.0, 0.0, -18.5], [0.0, 0.0, 1.0, 3.0], [0, 0, 0, 1]]


def main():
    H = Head()
    rows = {}
    for name, p in PARTS.items():
        m = trimesh.load(p, force='mesh')
        if name == 'speaker':   # source mesh is in the CAD frame; speaker-mount-repair/candidate.json speakerTransformUnchanged
            m.apply_transform(SPEAKER_T)
        M = man_from_tm(m)
        skip = ('head_cap',) if 'screw' in name else ()
        rows[name] = {'file': str(p), 'boundsMm': [[round(x, 2) for x in r] for r in m.bounds], 'static': H.static(name, M, skip=skip)[:6], 'roll': H.roll_sweep(M, 2.0),
                      'jaw': H.jaw_sweep(M, 2.0), 'descentWithCap': H.descent(M, 1.0), 'cables': cable_clearance(M)}
        print(name, json.dumps({k: rows[name][k] for k in ('roll', 'jaw')}), rows[name]['static'][:2],
              rows[name]['cables'], flush=True)
    # The four removed roof posts: candidate cap minus the V1.8 cap, checked as cap material.
    cand = man_from_tm(trimesh.load(SIM / 'guide/print/candidates/head-cap-v18-with-audio-posts/head_cap-world.stl',
                                    force='mesh'))
    posts = cand - H.get('head_cap')
    rows['four_roof_posts(candidate cap minus V1.8 cap)'] = {
        'volumeMm3': round(posts.volume(), 2), 'static': H.static('posts', posts, skip=('head_cap',))[:6],
        'roll': H.roll_sweep(posts, 2.0), 'jaw': H.jaw_sweep(posts, 2.0), 'descentWithCap': H.descent(posts, 1.0),
        'cables': cable_clearance(posts)}
    out = {'what': 'Pre-V1.8 audio parts (positions unchanged) checked against the V1.8 head solids, the head-roll and '
                   'jaw sweeps, the cap-on descent and the head_csi / bundle_head centrelines.',
           'method': 'check_lib.py (exact manifold3d booleans and min_gap); sweeps in 2 deg steps, descent 1 mm steps',
           'parts': rows}
    (STUDY / 'old-positions-recheck.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
