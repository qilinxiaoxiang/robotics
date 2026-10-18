#!/usr/bin/env python3
"""Extra candidate poses from earlier releases and functional poses, merged with the 10/1 poses.

- head_bottom: the V1.4/V1.5 on-edge pose, taken from the pre-final V1.6 manifest (same source STL and hash).
- head_cap: the V1.4/V1.5 on-edge pose (identity on guide/print/stl/head_cap.stl, per the cap pose study) and the
  rim-down pose (robot upright, open side on the bed) from release-V1.6-cap-pose/pose-candidates.json.

    run_bounded_cad.py ... -- /tmp/microduck-cad-venv/bin/python scripts/history_poses.py 10-1.json OUT.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from orientation_check import load_mesh, normalise  # noqa: E402

FINAL = HERE.parent / 'release-V1.6-final' / 'final-V1.6.json'
CAP_POSES = HERE.parent / 'release-V1.6-cap-pose' / 'pose-candidates.json'
PREFINAL = HERE.parent / 'release-V1.6' / 'complete-incremental-V1.6.json'


def main():
    extras = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    final = {p['key']: p for p in json.loads(FINAL.read_text())['parts']}
    notes = []
    # The V1.4-V1.5 on-edge poses are the sourceToPrint values in the pre-final V1.6 manifest (same source STLs).
    prefinal = {p['key']: p for p in json.loads(PREFINAL.read_text())['parts']}
    hb = final['head_bottom']
    assert prefinal['head_bottom']['sha256'] == hb['sha256']
    new = load_mesh(hb['path'])
    T = np.array(prefinal['head_bottom']['sourceToPrint'])
    notes.append(dict(key='head_bottom', pose='V1.4-V1.5 on-edge', source=str(PREFINAL)))
    extras.setdefault('head_bottom', []).append(dict(name='V1.4-V1.5 on-edge', sourceToPrint=normalise(new, T).tolist()))
    del new
    cap = load_mesh(final['head_cap']['path'])
    for row in json.loads(CAP_POSES.read_text()):
        if row['name'].startswith('current-side-down'):
            extras.setdefault('head_cap', []).append(dict(name='V1.4-V1.5 on-edge', sourceToPrint=normalise(cap, np.array(row['sourceToPrint'])).tolist()))
        if row['name'].startswith('rim-down'):
            extras.setdefault('head_cap', []).append(dict(name='rim-down (robot upright)', sourceToPrint=normalise(cap, np.array(row['sourceToPrint'])).tolist()))
    notes.append(dict(key='head_cap', poses=['V1.4-V1.5 on-edge', 'rim-down (robot upright)'], source=str(CAP_POSES)))
    out.write_text(json.dumps(extras, indent=1) + '\n')
    print(json.dumps(notes, indent=1))


if __name__ == '__main__':
    main()
